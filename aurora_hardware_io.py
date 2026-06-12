# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_hardware_io.py
=====================
Cross-hardware sensory intake and interaction layer.

Detects runtime environment at boot and routes all audio capture,
speech recognition, TTS output, camera input, and name-detection
through the correct platform backend — transparently. No caller
needs to know which platform they're on.

Supported platforms
-------------------
  TERMUX   — Android phone/tablet via Termux + Termux:API
             Audio:  termux-microphone-record / termux-speech-to-text
             Camera: termux-camera-photo
             TTS:    termux-tts-speak
             Name:   polling loop on termux-speech-to-text output

  LINUX    — Desktop/laptop with sounddevice + speech_recognition
             Audio:  sounddevice stream → speech_recognition
             Camera: opencv (if available) / still image fallback
             TTS:    pyttsx3 / espeak fallback / print fallback
             Name:   WakeWordListener (PocketSphinx → Google fallback)

  HEADLESS — No audio hardware (CI, server).  File-based PTT only.
             Write aurora_state/voice_trigger.json {"trigger": true, "text": "..."}
             to inject any utterance. Aurora polls every 0.5s.

Wake / name detection
---------------------
All platforms detect "aurora" in the spoken stream and route what
follows to process_external_user_turn(). The caller just provides
a process_turn(text) callback at boot time.

Usage (from subsurface daemon or surface daemon)
-------------------------------------------------
    from aurora_hardware_io import HardwareIO, detect_platform

    hw = HardwareIO(systems=systems)
    hw.start(on_utterance=lambda text: process_turn(text, systems))
    # ... daemon runs ...
    hw.stop()

Or for one-shot STT (e.g. from a tool):
    text = hw.listen_once(timeout=10)

Platform detection
------------------
Auto-detected. Override via environment variable:
    AURORA_PLATFORM=termux|linux|headless
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from aurora_persistence_utils import PERSISTENCE_LOCK, atomic_write_json
except Exception:
    import threading as _threading
    PERSISTENCE_LOCK = _threading.RLock()
    def atomic_write_json(path, data, **kw):
        import json
        with open(path, "w") as _f:
            json.dump(data, _f, **kw)
        return True

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_PLATFORM_OVERRIDE = os.environ.get("AURORA_PLATFORM", "").strip().lower()

_STATE_DIR = Path(__file__).resolve().parent / "aurora_state"
_VOICE_TRIGGER_FILE = _STATE_DIR / "voice_trigger.json"

# Termux-API command availability cache
_TERMUX_CMDS: Optional[Dict[str, bool]] = None


def _termux_cmd(name: str) -> bool:
    global _TERMUX_CMDS
    if _TERMUX_CMDS is None:
        _TERMUX_CMDS = {}
    if name not in _TERMUX_CMDS:
        _TERMUX_CMDS[name] = shutil.which(name) is not None
    return _TERMUX_CMDS[name]


def detect_platform() -> str:
    """Return 'termux', 'linux', or 'headless'."""
    if _PLATFORM_OVERRIDE in ("termux", "linux", "headless"):
        return _PLATFORM_OVERRIDE
    prefix = os.environ.get("PREFIX", "")
    if ("com.termux" in prefix.lower() or
            os.environ.get("TERMUX_VERSION") is not None or
            shutil.which("termux-info") is not None):
        return "termux"
    # Check for any audio backend
    try:
        import sounddevice  # noqa: F401
        return "linux"
    except (ImportError, OSError):
        pass
    try:
        import speech_recognition  # noqa: F401
        return "linux"
    except (ImportError, OSError):
        pass
    return "headless"


PLATFORM = detect_platform()

# Coordinates TTS and STT so they don't fight for Android audio focus.
# Set by _speak_termux before speaking; cleared after. _loop_termux and
# _listen_termux yield immediately when this is set.
_TTS_ACTIVE = threading.Event()

# ---------------------------------------------------------------------------
# Wake-word / name constants
# ---------------------------------------------------------------------------

_WAKE_PATTERNS = re.compile(
    r"\b(aurora|hey\s+aurora|ok\s+aurora|yo\s+aurora)\b",
    re.IGNORECASE,
)
_WAKE_COOLDOWN        = 3.0    # seconds between wake detections
_CONVERSATION_WINDOW  = 30.0   # seconds to stay awake after a turn completes
_WAKE_ACKS = [
    "What's up?",
    "Yeah?",
    "I'm listening.",
    "Go ahead.",
    "Mm?",
    "What do you need?",
]


# ---------------------------------------------------------------------------
# TTS — speak output
# ---------------------------------------------------------------------------

def speak(text: str, block: bool = False) -> None:
    """Speak text on whichever TTS backend is available. Never raises."""
    if not text:
        return
    safe = text.strip()
    if PLATFORM == "termux":
        _speak_termux(safe, block)
    elif PLATFORM == "linux":
        _speak_linux(safe, block)
    # headless: print only
    else:
        print(f"[AURORA] {safe}")


def _speak_termux(text: str, block: bool) -> None:
    if _termux_cmd("termux-tts-speak"):
        # Signal NameListener to pause STT so TTS can get Android audio focus.
        # STT and TTS share the same audio focus on Android; if STT holds focus,
        # TTS silently fails.
        _TTS_ACTIVE.set()
        try:
            if block:
                try:
                    subprocess.run(
                        ["termux-tts-speak", text],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    print(f"[AURORA] {text}")
            else:
                try:
                    subprocess.Popen(
                        ["termux-tts-speak", text],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    print(f"[AURORA] {text}")
        finally:
            _TTS_ACTIVE.clear()
    else:
        print(f"[AURORA] {text}")


def _speak_linux(text: str, block: bool) -> None:
    def _do():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            pass
        if shutil.which("espeak"):
            try:
                subprocess.run(["espeak", text],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass
        print(f"[AURORA] {text}")

    if block:
        _do()
    else:
        threading.Thread(target=_do, daemon=True).start()


# ---------------------------------------------------------------------------
# STT — listen_once
# ---------------------------------------------------------------------------

def listen_once(timeout: float = 10.0, prompt: bool = False) -> Optional[str]:
    """
    Capture one spoken utterance and return the transcript.
    Returns None if nothing was captured or recognition failed.
    Cross-platform: routes to Termux API or sounddevice+SR.
    """
    if prompt:
        speak("Listening.")
    if PLATFORM == "termux":
        return _listen_termux(timeout)
    elif PLATFORM == "linux":
        return _listen_linux(timeout)
    return None


def _parse_stt_output(raw: str) -> Optional[str]:
    """
    Parse termux-speech-to-text output.  Handles all known formats:
      - ["text"]                          (older termux-api)
      - [{"utterances": ["text"]}]        (termux-api 0.50+)
      - {"utterances": ["text"]}          (dict top-level)
      - plain string                      (fallback)
    """
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, str):
                return first.strip() or None
            if isinstance(first, dict):
                utterances = first.get("utterances", [])
                if isinstance(utterances, list) and utterances:
                    return str(utterances[0]).strip() or None
                for v in first.values():
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        if isinstance(data, dict):
            utterances = data.get("utterances", [])
            if isinstance(utterances, list) and utterances:
                return str(utterances[0]).strip() or None
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    return raw.strip() or None


def _listen_termux(timeout: float) -> Optional[str]:
    """Use termux-speech-to-text (blocks until done, respects timeout)."""
    if not _termux_cmd("termux-speech-to-text"):
        return None
    # Yield immediately if TTS is speaking — STT and TTS share Android audio
    # focus; starting STT while TTS is active would cut off speech.
    if _TTS_ACTIVE.is_set():
        return None
    # Keep timeout short so the mic visibly cycles and TTS can get focus soon
    # after setting _TTS_ACTIVE.  Android STT returns as soon as speech ends,
    # so the timeout is only hit on silence/no-input.
    _proc_timeout = max(10.0, timeout + 2.0)
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True, text=True,
            timeout=_proc_timeout,
        )
        raw = result.stdout.strip()
        if raw:
            return _parse_stt_output(raw)
    except subprocess.TimeoutExpired:
        # User didn't speak within Android STT window — not an error
        pass
    except Exception:
        pass
    return None


def _listen_linux(timeout: float) -> Optional[str]:
    """Capture audio via sounddevice then transcribe via speech_recognition."""
    try:
        import sounddevice as sd
        import numpy as np
        import speech_recognition as sr

        sample_rate = 16000
        frames = int(sample_rate * timeout)
        recording = sd.rec(frames, samplerate=sample_rate,
                           channels=1, dtype="int16")
        sd.wait()
        audio_data = recording.flatten().tobytes()

        recognizer = sr.Recognizer()
        audio = sr.AudioData(audio_data, sample_rate, 2)
        try:
            return recognizer.recognize_google(audio)
        except Exception:
            pass
        try:
            return recognizer.recognize_sphinx(audio)
        except Exception:
            pass
    except ImportError:
        pass
    return None


# ---------------------------------------------------------------------------
# Camera — capture_frame
# ---------------------------------------------------------------------------

def capture_frame(save_path: Optional[str] = None) -> Optional[str]:
    """
    Capture one camera frame. Returns path to saved image or None.
    Cross-platform.
    """
    out = save_path or str(_STATE_DIR / "vision_snapshots" / "hw_frame_latest.jpg")
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    if PLATFORM == "termux":
        return _camera_termux(out)
    elif PLATFORM == "linux":
        return _camera_linux(out)
    return None


def _camera_termux(out: str) -> Optional[str]:
    if not _termux_cmd("termux-camera-photo"):
        return None
    try:
        subprocess.run(
            ["termux-camera-photo", "-c", "0", out],
            check=False, timeout=15,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return out if Path(out).exists() else None
    except Exception:
        return None


def _camera_linux(out: str) -> Optional[str]:
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            return None
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(out, frame)
            return out
    except ImportError:
        pass
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Ambient mic recording (background stream for sensory intake)
# ---------------------------------------------------------------------------

class AmbientMicStream:
    """
    Continuous low-level audio stream feeding raw audio chunks into
    aurora's sensory crystal without requiring wake-word detection.
    Used for background sensory intake (ambient audio modality).

    Platform-aware: uses sounddevice on Linux, termux-microphone-record
    polling on Termux, silently inactive on headless.
    """

    def __init__(
        self,
        on_chunk: Callable[[bytes], None],
        sample_rate: int = 16000,
        chunk_duration: float = 0.5,
    ):
        self._on_chunk = on_chunk
        self._sample_rate = sample_rate
        self._chunk_frames = int(sample_rate * chunk_duration)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._termux_proc: Optional[subprocess.Popen] = None

    def start(self) -> bool:
        """Start the stream. Returns True if successfully started."""
        self._running = True
        if PLATFORM == "linux":
            return self._start_linux()
        elif PLATFORM == "termux":
            return self._start_termux()
        return False  # headless — no ambient stream

    def stop(self) -> None:
        self._running = False
        # Send -q to stop any active Termux recording so MicRecorderService is
        # cleanly destroyed before Aurora exits.  Orphaned Popen processes keep
        # the recorder running after Python exits, and Android's onDestroy()
        # then crashes trying to stop an already-idle MediaRecorder.
        if PLATFORM == "termux":
            try:
                subprocess.run(
                    ["termux-microphone-record", "-q"],
                    timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
            if self._termux_proc is not None:
                try:
                    self._termux_proc.terminate()
                except Exception:
                    pass
                self._termux_proc = None

    def _start_linux(self) -> bool:
        try:
            import sounddevice as sd
            import numpy as np

            def _callback(indata, frames, time_info, status):
                if not self._running:
                    return
                try:
                    self._on_chunk(indata.flatten().astype("int16").tobytes())
                except Exception:
                    pass

            self._sd_stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._chunk_frames,
                callback=_callback,
            )
            self._sd_stream.start()
            return True
        except Exception:
            return False

    def _start_termux(self) -> bool:
        """
        Termux doesn't support continuous audio streams from Python.
        Poll termux-microphone-record for short clips instead.
        Each clip is treated as one ambient chunk.
        """
        if not _termux_cmd("termux-microphone-record"):
            return False

        def _poll():
            tmp = str(_STATE_DIR / "ambient_tmp_chunk.wav")
            while self._running:
                try:
                    # Start recording WITHOUT -l: the command blocks until -q is
                    # sent.  Using -l causes MediaRecorder to stop internally
                    # while MicRecorderService is still alive; onDestroy() then
                    # calls stop() on the already-stopped recorder → crash.
                    _proc = subprocess.Popen(
                        ["termux-microphone-record",
                         "-e", "wav", "-r", str(self._sample_rate),
                         "-c", "1", "-f", tmp],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    self._termux_proc = _proc
                    # Record for 2 seconds (check _running so stop() bails fast)
                    _deadline = time.time() + 2.0
                    while self._running and time.time() < _deadline:
                        time.sleep(0.1)
                    # Stop while recorder is ACTIVE — safe stop
                    subprocess.run(
                        ["termux-microphone-record", "-q"],
                        timeout=5,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    self._termux_proc = None
                    try:
                        _proc.wait(timeout=2)
                    except Exception:
                        try:
                            _proc.terminate()
                        except Exception:
                            pass
                    if self._running and Path(tmp).exists():
                        with open(tmp, "rb") as f:
                            data = f.read()
                        # Strip WAV header (44 bytes) to get raw PCM
                        if len(data) > 44:
                            self._on_chunk(data[44:])
                        Path(tmp).unlink(missing_ok=True)
                except Exception:
                    time.sleep(1.0)

        self._thread = threading.Thread(target=_poll, daemon=True,
                                        name="aurora_ambient_termux")
        self._thread.start()
        return True


# ---------------------------------------------------------------------------
# Name / wake detection with follow-up capture
# ---------------------------------------------------------------------------

class NameListener:
    """
    Always-on listener that detects "aurora" (or "hey aurora", "ok aurora")
    in the audio stream and captures the follow-up utterance, then calls
    on_utterance(text). Interrupts immediately when a user turn begins.

    Works on all platforms via platform-appropriate audio backends.
    Never raises — always degrades gracefully.
    """

    def __init__(
        self,
        on_utterance: Callable[[str], None],
        systems: Optional[Dict[str, Any]] = None,
    ):
        self._on_utterance = on_utterance
        self._systems = systems or {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cooldown_until: float = 0.0
        self._conversation_active_until: float = 0.0
        self._paused = threading.Event()

    def start(self) -> None:
        self._running = True
        if PLATFORM == "termux":
            self._thread = threading.Thread(
                target=self._loop_termux, daemon=True, name="aurora_name_termux")
        elif PLATFORM == "linux":
            self._thread = threading.Thread(
                target=self._loop_linux, daemon=True, name="aurora_name_linux")
        else:
            self._thread = threading.Thread(
                target=self._loop_file_ptt, daemon=True, name="aurora_name_file")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        """Pause while Aurora is speaking to avoid self-triggering."""
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def keep_active(self, seconds: float = _CONVERSATION_WINDOW) -> None:
        """Extend the conversation window so no wake word is needed for the next utterance."""
        self._conversation_active_until = time.time() + seconds

    # ---- Termux loop -------------------------------------------------------

    def _loop_termux(self) -> None:
        """
        On Termux: repeated termux-speech-to-text polls.
        Each call blocks until speech is detected (or timeout).
        If transcript contains "aurora", capture follow-up immediately.
        """
        while self._running:
            if self._paused.is_set() or _TTS_ACTIVE.is_set():
                time.sleep(0.2)
                continue
            if time.time() < self._cooldown_until:
                time.sleep(0.5)
                continue
            try:
                text = _listen_termux(timeout=8.0)
                if not text:
                    # No speech — check file PTT while idle
                    self._check_file_ptt()
                    continue
                if _WAKE_PATTERNS.search(text):
                    # Strip wake word; use remainder as the utterance
                    follow = _WAKE_PATTERNS.sub("", text).strip(" ,.!?")
                    if not follow:
                        # Wake word only — acknowledge naturally and listen again
                        import random as _random
                        speak(_random.choice(_WAKE_ACKS))
                        follow = _listen_termux(timeout=12.0) or ""
                        if not follow:
                            # One retry — give the user a moment
                            follow = _listen_termux(timeout=8.0) or ""
                    if follow:
                        self._cooldown_until = time.time() + _WAKE_COOLDOWN
                        self._dispatch(follow)
                elif time.time() < self._conversation_active_until:
                    # Conversation window is open — no wake word needed
                    self._dispatch(text)
                else:
                    # No wake word, outside conversation window — check file PTT
                    self._check_file_ptt()
            except Exception:
                time.sleep(1.0)

    # ---- Linux loop --------------------------------------------------------

    def _loop_linux(self) -> None:
        """
        On Linux: continuous sounddevice capture with RMS VAD.
        Transcribes each speech segment and checks for wake word.
        Falls back to Google online STT if PocketSphinx unavailable.
        """
        try:
            import sounddevice as sd
            import numpy as np
            import speech_recognition as sr
        except ImportError:
            # Degrade to file PTT
            self._loop_file_ptt()
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 350
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        sample_rate = 16000
        chunk_ms    = 25
        chunk_size  = int(sample_rate * chunk_ms / 1000)
        rms_floor   = 0.010
        silence_gap = 20      # chunks of silence → end of utterance
        max_chunks  = 600     # hard cap ~15s

        while self._running:
            if self._paused.is_set():
                time.sleep(0.5)
                continue
            if time.time() < self._cooldown_until:
                time.sleep(0.25)
                continue
            self._check_file_ptt()

            # Collect one speech segment
            speech_buf: List[bytes] = []
            silence_count = 0
            in_speech = False

            try:
                with sd.InputStream(samplerate=sample_rate, channels=1,
                                    dtype="int16", blocksize=chunk_size) as stream:
                    while self._running and not self._paused.is_set():
                        chunk, _ = stream.read(chunk_size)
                        arr = chunk.flatten().astype("float32") / 32768.0
                        rms = float(arr.std())

                        if rms > rms_floor:
                            in_speech = True
                            silence_count = 0
                            speech_buf.append(chunk.flatten().astype("int16").tobytes())
                        elif in_speech:
                            speech_buf.append(chunk.flatten().astype("int16").tobytes())
                            silence_count += 1
                            if (silence_count >= silence_gap or
                                    len(speech_buf) >= max_chunks):
                                break
            except Exception:
                time.sleep(0.5)
                continue

            if not speech_buf or not in_speech:
                continue

            raw = b"".join(speech_buf)
            audio = sr.AudioData(raw, sample_rate, 2)
            text = ""
            try:
                text = recognizer.recognize_google(audio)
            except Exception:
                try:
                    text = recognizer.recognize_sphinx(audio)
                except Exception:
                    pass

            if not text:
                continue

            if _WAKE_PATTERNS.search(text):
                follow = _WAKE_PATTERNS.sub("", text).strip(" ,.!?")
                if not follow:
                    import random as _random
                    speak(_random.choice(_WAKE_ACKS))
                    follow = _listen_linux(timeout=12.0) or ""
                if follow:
                    self._cooldown_until = time.time() + _WAKE_COOLDOWN
                    self._dispatch(follow)
            elif time.time() < self._conversation_active_until:
                self._dispatch(text)

    # ---- Headless / file PTT loop ------------------------------------------

    def _loop_file_ptt(self) -> None:
        """
        Headless fallback: poll voice_trigger.json.
        Write {"trigger": true, "text": "your utterance"} to send input.
        Write {"trigger": true} with no text to trigger a listen_once().
        """
        while self._running:
            self._check_file_ptt()
            time.sleep(0.5)

    def _check_file_ptt(self) -> None:
        try:
            if not _VOICE_TRIGGER_FILE.exists():
                return
            raw = _VOICE_TRIGGER_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not data.get("trigger"):
                return
            # Clear trigger immediately to prevent double-fire
            _VOICE_TRIGGER_FILE.write_text(
                json.dumps({"trigger": False}), encoding="utf-8")
            text = str(data.get("text", "")).strip()
            if not text:
                text = listen_once(timeout=10.0) or ""
            if text:
                self._dispatch(text)
        except Exception:
            pass

    def _dispatch(self, text: str) -> None:
        """Send utterance to callback. Pauses self while processing."""
        self.pause()
        try:
            self._on_utterance(text)
        finally:
            # Keep conversation alive for 30s after each turn so the user
            # can reply or follow up without saying "hey Aurora" again.
            self._conversation_active_until = time.time() + _CONVERSATION_WINDOW
            self.resume()


# ---------------------------------------------------------------------------
# HardwareIO — top-level coordinator
# ---------------------------------------------------------------------------

class HardwareIO:
    """
    Single entry point for all hardware I/O in Aurora's daemon stack.
    Manages NameListener, AmbientMicStream, camera, and TTS as one unit.

    Usage:
        hw = HardwareIO(systems=systems)
        hw.start(on_utterance=lambda text: process_turn(text))
        # ... daemon loop ...
        hw.stop()
    """

    def __init__(self, systems: Optional[Dict[str, Any]] = None):
        self.systems = systems or {}
        self.platform = PLATFORM
        self._name_listener: Optional[NameListener] = None
        self._ambient_stream: Optional[AmbientMicStream] = None
        self._log = systems.get("_log_fn") if systems else None

    def _log_msg(self, msg: str) -> None:
        if self._log:
            try:
                self._log(msg)
                return
            except Exception:
                pass
        print(msg)

    def start(
        self,
        on_utterance: Callable[[str], None],
        enable_ambient: bool = True,
        on_ambient_chunk: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        """
        Start all hardware I/O.

        on_utterance: called with transcript whenever name is detected
                      and follow-up is captured. The full interaction
                      pipeline starts here.
        enable_ambient: start ambient mic stream for background sensory
                        intake into sensory crystal.
        on_ambient_chunk: optional callback for raw PCM chunks. If None
                          and enable_ambient is True, chunks are routed
                          to sensory_crystal in systems automatically.
        """
        self._log_msg(f"  [HW-IO] Platform: {self.platform.upper()}")

        # Name listener
        self._name_listener = NameListener(
            on_utterance=on_utterance,
            systems=self.systems,
        )
        self._name_listener.start()
        self._log_msg(f"  [HW-IO] Name listener started ({self.platform}).")

        # Ambient mic stream
        if enable_ambient:
            chunk_handler = on_ambient_chunk or self._default_ambient_handler
            self._ambient_stream = AmbientMicStream(
                on_chunk=chunk_handler,
                sample_rate=16000,
                chunk_duration=0.5,
            )
            ok = self._ambient_stream.start()
            if ok:
                self._log_msg("  [HW-IO] Ambient mic stream active.")
            else:
                self._log_msg("  [HW-IO] Ambient mic stream unavailable — sensory audio inactive.")

        # File-based PTT always available as universal override
        self._log_msg(
            f"  [HW-IO] File PTT active: write "
            f"{{\"trigger\":true,\"text\":\"...\"}} to {_VOICE_TRIGGER_FILE}"
        )

    def stop(self) -> None:
        if self._name_listener:
            self._name_listener.stop()
        if self._ambient_stream:
            self._ambient_stream.stop()

    def pause_for_tts(self) -> None:
        """Call before Aurora speaks to prevent self-triggering."""
        if self._name_listener:
            self._name_listener.pause()

    def resume_after_tts(self) -> None:
        if self._name_listener:
            self._name_listener.resume()

    def speak(self, text: str, block: bool = False) -> None:
        """Speak text and auto-manage listener pause/resume."""
        self.pause_for_tts()
        try:
            speak(text, block=block)
        finally:
            if block:
                self.resume_after_tts()
            else:
                # Resume after a short delay for async TTS
                threading.Timer(0.5, self.resume_after_tts).start()

    def capture_frame(self) -> Optional[str]:
        """Capture a camera frame. Returns path or None."""
        return capture_frame()

    def listen_once(self, timeout: float = 10.0) -> Optional[str]:
        """Block and capture one utterance. Cross-platform."""
        return listen_once(timeout=timeout)

    def _default_ambient_handler(self, chunk: bytes) -> None:
        """Route ambient PCM chunks into the sensory crystal."""
        try:
            import numpy as np
            sc = (self.systems.get("sensory_crystal") or
                  getattr(self.systems.get("hardware"), "sensory_crystal", None) or
                  getattr(self.systems.get("sensory_integration"), "sensory_crystal", None))
            if sc is None:
                return
            # Convert PCM bytes to float32 normalised array
            arr = np.frombuffer(chunk, dtype="int16").astype("float32") / 32768.0
            # Build a minimal 20-dim audio feature vector from energy
            rms   = float(arr.std())
            zcr   = float(np.mean(np.abs(np.diff(np.sign(arr))))) / 2.0
            # Pad to 20 dims with energy-derived features
            vec20 = [rms, zcr] + [rms * (0.9 ** i) for i in range(18)]
            # 57-dim visual placeholder (empty — audio only)
            vis57 = [0.0] * 57
            sc.observe_frame(
                vec20, vis57,
                session_id="ambient:hw_io",
                audio_conf=min(1.0, rms * 8.0),
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Convenience: inject text as if spoken (for testing / scripted input)
# ---------------------------------------------------------------------------

def inject_utterance(text: str) -> None:
    """
    Write a synthetic utterance to the file PTT trigger.
    Works on all platforms — useful for scripted interaction and testing.

        inject_utterance("aurora what is your current state")
    """
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _VOICE_TRIGGER_FILE.write_text(
        json.dumps({"trigger": True, "text": text}), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Probe — check what's available on this platform
# ---------------------------------------------------------------------------

def probe() -> Dict[str, Any]:
    """Return a dict of available hardware capabilities on this platform."""
    result: Dict[str, Any] = {
        "platform":        PLATFORM,
        "tts":             False,
        "stt":             False,
        "camera":          False,
        "ambient_mic":     False,
        "file_ptt":        True,   # always available
    }
    if PLATFORM == "termux":
        result["tts"]         = _termux_cmd("termux-tts-speak")
        result["stt"]         = _termux_cmd("termux-speech-to-text")
        result["camera"]      = _termux_cmd("termux-camera-photo")
        # Ambient mic stream is disabled on Termux: Android only allows one
        # exclusive mic consumer at a time.  AmbientMicStream and
        # termux-speech-to-text (NameListener STT) conflict — Android
        # forcibly kills MicRecorderService to give STT the mic, causing
        # onDestroy() → MediaRecorder.stop() crash.
        result["ambient_mic"] = False
    elif PLATFORM == "linux":
        try:
            import sounddevice  # noqa: F401
            result["ambient_mic"] = True
            result["stt"]         = True
        except ImportError:
            pass
        try:
            import speech_recognition  # noqa: F401
            result["stt"] = True
        except ImportError:
            pass
        try:
            import pyttsx3  # noqa: F401
            result["tts"] = True
        except ImportError:
            result["tts"] = shutil.which("espeak") is not None
        try:
            import cv2  # noqa: F401
            result["camera"] = True
        except ImportError:
            pass
    return result


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(probe(), indent=2))


# ============================================================================
# SENSORY COMPETENCY (Evolutionary visual + audio perception)
# ============================================================================

"""
AURORA SENSORY COMPETENCY (Companion to Layer 5 & Layer 6)
============================================================
Evolutionary visual and audio perception capabilities for Aurora.

Borrowed architecture from Agora AI's developmental systems, adapted
to Aurora's ontological framework with:
  - ExistenceMode gating
  - IVM-compatible geometry
  - Integration with existing PatternTypes (TEMPORAL, SPATIAL, EMOTIONAL, STRUCTURAL, ABSTRACT)
  - Layer 6 DNA system integration (Gene, FractalAllele, BehavioralCrystal)
  - OETS grounding support

VISUAL COMPETENCY:
  focus              - Attention concentration strength
  motion_sensitivity - Ability to detect and track movement
  recognition_threshold - Confidence needed to identify objects
  detail_orientation - How much fine detail is captured

AUDIO COMPETENCY:
  sensitivity        - Overall audio detection threshold
  voice_isolation    - Ability to separate speech from noise
  emotion_detection  - Recognition of emotional tone in voice

EVOLUTIONARY MECHANICS:
  Sensory competencies evolve through experience:
  - Raw percepts are collected before labeling
  - Clustering promotes stable concepts
  - FractalAlleles form from repeated patterns
  - Genes evolve through generational pressure
  - OETS nodes deepen with grounded sensory experience

DOCTRINE:
  Aurora learns to SEE and HEAR through experience.
  Sensory understanding is not programmed -- it is grown.
  The quality of perception emerges from evolutionary pressure.
  All sensory processing is mode-gated: deeper perception requires higher modes.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import math
import hashlib
import random
import json
import os
import numpy as np
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

# ============================================================================
# IMPORTS FROM AURORA LAYERS
# ============================================================================

from foundational_contract import (
    ExistenceMode, OntologicalClaim, OntologicalViolation, FoundationalContract
)

# Pattern types shared with aurora_expression_perception
from aurora_perception_primitives import PatternType, DimensionalPattern

# DNA structures from Layer 6
from aurora_behavioral_identity import (
    Gene, FractalAllele, GeneEvent, BehavioralFacet, BehavioralCrystal,
    TraitDomain, BehavioralTrait, DNASystem
)

# OETS for semantic grounding (optional)
_OETS_AVAILABLE = False
try:
    from aurora_internal.aurora_ontological_scaffolding import (
        OntologicalScaffoldingEngine, SemanticNode, SemanticRelation, RelationType
    )
    _OETS_AVAILABLE = True
except Exception:
    pass

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    v1 = np.array(v1)
    v2 = np.array(v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


# ============================================================================
# SECTION 1: SENSORY TRAIT DOMAINS -- Extension of Layer 6 TraitDomain
# ============================================================================

class SensoryTraitDomain(Enum):
    """Domains specific to sensory processing -- extend TraitDomain."""
    VISUAL_ACUITY = auto()
    VISUAL_MOTION = auto()
    VISUAL_RECOGNITION = auto()
    VISUAL_DETAIL = auto()
    AUDITORY_SENSITIVITY = auto()
    AUDITORY_VOICE = auto()
    AUDITORY_EMOTION = auto()


# ============================================================================
# SECTION 2: PERCEPT TEMPLATES -- Evolutionary Learning Units
# ============================================================================

@dataclass
class SensoryPerceptTemplate:
    """
    Base template for a learned sensory pattern.
    Evolves through exposure and reinforcement.
    """
    template_id: str
    modality: str                       # "visual" or "audio"
    name: str                           # Human-readable name
    feature_signature: Dict[str, float] = field(default_factory=dict)
    acoustic_centroid: List[float] = field(default_factory=list)  # For audio
    visual_centroid: List[float] = field(default_factory=list)    # For visual
    confidence: float = 0.5             # 0-1 how reliable
    stability: float = 0.0              # 0-1 how stable over time
    usage_count: int = 0
    generation_created: int = 0
    last_matched: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "modality": self.modality,
            "name": self.name,
            "feature_signature": self.feature_signature,
            "acoustic_centroid": self.acoustic_centroid,
            "visual_centroid": self.visual_centroid,
            "confidence": self.confidence,
            "stability": self.stability,
            "usage_count": self.usage_count,
            "generation_created": self.generation_created,
            "last_matched": self.last_matched
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensoryPerceptTemplate':
        t = cls(
            template_id=data.get("template_id", _generate_id("percept")),
            modality=data.get("modality", "unknown"),
            name=data.get("name", "unnamed")
        )
        t.feature_signature = data.get("feature_signature", {})
        t.acoustic_centroid = data.get("acoustic_centroid", [])
        t.visual_centroid = data.get("visual_centroid", [])
        t.confidence = data.get("confidence", 0.5)
        t.stability = data.get("stability", 0.0)
        t.usage_count = data.get("usage_count", 0)
        t.generation_created = data.get("generation_created", 0)
        t.last_matched = data.get("last_matched", time.time())
        return t

    def match(self, features: Dict[str, float] = None,
              centroid: List[float] = None) -> float:
        """Calculate match score against input."""
        score = 0.0
        count = 0

        # Feature-based matching
        if features and self.feature_signature:
            common_keys = set(features.keys()) & set(self.feature_signature.keys())
            if common_keys:
                diffs = [abs(features[k] - self.feature_signature[k]) for k in common_keys]
                score += 1.0 - (sum(diffs) / len(diffs))
                count += 1

        # Centroid-based matching
        if centroid:
            if self.modality == "visual" and self.visual_centroid:
                score += max(0, _cosine_similarity(centroid, self.visual_centroid))
                count += 1
            elif self.modality == "audio" and self.acoustic_centroid:
                score += max(0, _cosine_similarity(centroid, self.acoustic_centroid))
                count += 1

        return score / max(count, 1)

    def update_from_observation(self, features: Dict[str, float] = None,
                                centroid: List[float] = None,
                                learning_rate: float = 0.1):
        """Update template from new observation (moving average)."""
        self.usage_count += 1
        self.last_matched = time.time()
        self.confidence = min(1.0, self.confidence + 0.02)
        self.stability = min(1.0, self.stability + 0.03)

        # Update feature signature
        if features:
            for k, v in features.items():
                if k in self.feature_signature:
                    self.feature_signature[k] = (
                        (1 - learning_rate) * self.feature_signature[k] +
                        learning_rate * v
                    )
                else:
                    self.feature_signature[k] = v

        # Update centroid
        if centroid:
            target = self.visual_centroid if self.modality == "visual" else self.acoustic_centroid
            if target and len(target) == len(centroid):
                updated = [
                    (1 - learning_rate) * t + learning_rate * c
                    for t, c in zip(target, centroid)
                ]
                if self.modality == "visual":
                    self.visual_centroid = updated
                else:
                    self.acoustic_centroid = updated
            elif not target:
                if self.modality == "visual":
                    self.visual_centroid = list(centroid)
                else:
                    self.acoustic_centroid = list(centroid)


# ============================================================================
# SECTION 3: SENSORY CONCEPT MEMORY -- Clustering and Promotion
# ============================================================================

@dataclass
class SensoryConcept:
    """
    A promoted concept from clustered percepts.
    Represents stable understanding of a sensory pattern.
    """
    concept_id: str
    modality: str                       # "visual" or "audio"
    label: str                          # e.g., "face", "human_voice"
    centroid: List[float]               # Average feature vector
    percept_cluster: List[List[float]] = field(default_factory=list)
    label_hypotheses: Dict[str, float] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    confidence: float = 0.5
    stability: float = 0.0
    grounding_links: List[Dict[str, str]] = field(default_factory=list)
    # Each: {"intent": str, "lexeme": str, "oets_node": str}
    times_matched: int = 0
    guidance_count: int = 0
    generation_created: int = 0
    last_accessed: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "modality": self.modality,
            "label": self.label,
            "centroid": self.centroid,
            "percept_cluster": self.percept_cluster[-10:],  # Keep last 10
            "label_hypotheses": self.label_hypotheses,
            "aliases": self.aliases[-12:],
            "confidence": self.confidence,
            "stability": self.stability,
            "grounding_links": self.grounding_links[-20:],
            "times_matched": self.times_matched,
            "guidance_count": self.guidance_count,
            "generation_created": self.generation_created,
            "last_accessed": self.last_accessed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensoryConcept':
        return cls(
            concept_id=data.get("concept_id", _generate_id("concept")),
            modality=data.get("modality", "unknown"),
            label=data.get("label", "unknown"),
            centroid=data.get("centroid", []),
            percept_cluster=data.get("percept_cluster", []),
            label_hypotheses=data.get("label_hypotheses", {}),
            aliases=data.get("aliases", []),
            confidence=data.get("confidence", 0.5),
            stability=data.get("stability", 0.0),
            grounding_links=data.get("grounding_links", []),
            times_matched=data.get("times_matched", 0),
            guidance_count=data.get("guidance_count", 0),
            generation_created=data.get("generation_created", 0),
            last_accessed=data.get("last_accessed", time.time())
        )


class SensoryConceptMemory:
    """
    Manages concept formation from raw percepts.
    Percept-first learning: observe -> cluster -> promote -> ground.
    """

    CLUSTER_THRESHOLD = 3          # Min percepts before promotion
    SIMILARITY_THRESHOLD = 0.85    # Cosine sim for cluster membership

    def __init__(self, modality: str):
        self.modality = modality
        self.raw_percepts: Dict[str, List[List[float]]] = defaultdict(list)
        self.concepts: Dict[str, SensoryConcept] = {}
        self.grounding_log: List[Dict[str, Any]] = []

    def _canonical_label(self, label: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", " ", str(label or "").lower()).strip()
        return " ".join(cleaned.split())

    def _iter_labels(self, concept: SensoryConcept) -> List[str]:
        labels = [str(concept.label or "").strip()]
        labels.extend(str(alias or "").strip() for alias in list(concept.aliases or []))
        return [label for label in labels if label]

    def _find_concept_entry(self, label: str) -> Tuple[Optional[str], Optional[SensoryConcept]]:
        target = self._canonical_label(label)
        if not target:
            return None, None
        for key, concept in self.concepts.items():
            if self._canonical_label(key) == target:
                return key, concept
            for alias in self._iter_labels(concept):
                if self._canonical_label(alias) == target:
                    return key, concept
        return None, None

    def _register_alias(self, concept: SensoryConcept, alias: str) -> None:
        alias_text = str(alias or "").strip()
        if not alias_text:
            return
        if self._canonical_label(alias_text) == self._canonical_label(concept.label):
            return
        existing = {
            self._canonical_label(item): str(item)
            for item in list(concept.aliases or [])
            if str(item or "").strip()
        }
        existing.setdefault(self._canonical_label(alias_text), alias_text)
        concept.aliases = list(existing.values())[:12]

    def _merge_concepts(self, target: SensoryConcept, source: SensoryConcept) -> SensoryConcept:
        if target is source:
            return target
        if target.centroid and source.centroid and len(target.centroid) == len(source.centroid):
            merged = [
                ((ta * max(target.times_matched, 1)) + (sa * max(source.times_matched, 1)))
                / max(target.times_matched + source.times_matched, 1)
                for ta, sa in zip(target.centroid, source.centroid)
            ]
            target.centroid = merged
        elif source.centroid and not target.centroid:
            target.centroid = list(source.centroid)
        target.percept_cluster.extend(list(source.percept_cluster or []))
        target.percept_cluster = target.percept_cluster[-20:]
        target.confidence = min(1.0, max(target.confidence, source.confidence))
        target.stability = min(1.0, max(target.stability, source.stability))
        target.times_matched += int(source.times_matched or 0)
        target.guidance_count += int(source.guidance_count or 0)
        target.last_accessed = max(float(target.last_accessed or 0.0), float(source.last_accessed or 0.0))
        for alias in self._iter_labels(source):
            self._register_alias(target, alias)
        hypotheses = defaultdict(float)
        for mapping in (target.label_hypotheses, source.label_hypotheses):
            for name, score in dict(mapping or {}).items():
                hypotheses[str(name)] += float(score or 0.0)
        target.label_hypotheses = dict(hypotheses)
        target.grounding_links.extend(list(source.grounding_links or []))
        target.grounding_links = target.grounding_links[-30:]
        return target

    def _rename_or_alias_concept(
        self,
        concept: SensoryConcept,
        *,
        old_key: Optional[str],
        new_label: str,
        prefer_rename: bool,
    ) -> Tuple[str, SensoryConcept]:
        new_label = str(new_label or "").strip()
        if not new_label:
            return str(old_key or concept.label or ""), concept
        canonical_new = self._canonical_label(new_label)
        existing_key, existing = self._find_concept_entry(new_label)
        if existing is not None and existing is not concept:
            merged = self._merge_concepts(existing, concept)
            self._register_alias(merged, concept.label)
            if old_key in self.concepts and self.concepts.get(old_key) is concept:
                del self.concepts[old_key]
            self.concepts[existing_key] = merged
            return existing_key, merged

        if prefer_rename and canonical_new:
            previous_label = str(concept.label or "").strip()
            if previous_label and self._canonical_label(previous_label) != canonical_new:
                self._register_alias(concept, previous_label)
            concept.label = new_label
            if old_key in self.concepts and old_key != new_label and self.concepts.get(old_key) is concept:
                del self.concepts[old_key]
            self.concepts[new_label] = concept
            return new_label, concept

        self._register_alias(concept, new_label)
        if old_key and old_key not in self.concepts:
            self.concepts[old_key] = concept
        return str(old_key or concept.label or new_label), concept

    def guide_label(
        self,
        label: str,
        feature_vector: List[float],
        *,
        role: str = "guided_label",
        source_text: str = "",
        note: str = "",
        oets_node: str = "",
    ) -> Dict[str, Any]:
        label = str(label or "").strip()
        if not label:
            return {"matched": False, "reason": "missing_label"}

        feature_vector = [float(v or 0.0) for v in list(feature_vector or [])]
        matched = self.find_matching_concept(feature_vector, threshold=0.74) if any(feature_vector) else None
        matched_key = None
        if matched is not None:
            for key, concept in self.concepts.items():
                if concept is matched:
                    matched_key = key
                    break
        direct_key, direct = self._find_concept_entry(label)
        concept = matched or direct
        concept_key = matched_key or direct_key
        created = False

        if concept is None:
            concept = SensoryConcept(
                concept_id=_generate_id(f"{self.modality}_concept"),
                modality=self.modality,
                label=label,
                centroid=feature_vector[:],
                percept_cluster=[feature_vector[:]] if any(feature_vector) else [],
                label_hypotheses={label: 1.0},
                confidence=0.72,
                stability=0.34,
                guidance_count=1,
            )
            concept_key = label
            self.concepts[concept_key] = concept
            created = True
        else:
            prefer_rename = role in {"person_identity", "voice_identity"} or concept.label.startswith("unknown_")
            concept_key, concept = self._rename_or_alias_concept(
                concept,
                old_key=concept_key,
                new_label=label,
                prefer_rename=prefer_rename,
            )
            concept.guidance_count += 1
            concept.last_accessed = time.time()

        if any(feature_vector):
            if concept.centroid and len(concept.centroid) == len(feature_vector):
                concept.centroid = [
                    (0.8 * float(old)) + (0.2 * float(new))
                    for old, new in zip(concept.centroid, feature_vector)
                ]
            else:
                concept.centroid = feature_vector[:]
            concept.percept_cluster.append(feature_vector[:])
            concept.percept_cluster = concept.percept_cluster[-20:]

        hypothesis_key = concept.label if concept.label else label
        concept.label_hypotheses[hypothesis_key] = max(
            float(concept.label_hypotheses.get(hypothesis_key, 0.0) or 0.0),
            1.0,
        )
        concept.confidence = min(1.0, concept.confidence + (0.12 if role in {"person_identity", "voice_identity"} else 0.08))
        concept.stability = min(1.0, concept.stability + (0.10 if role in {"person_identity", "voice_identity"} else 0.06))
        concept.times_matched += 1
        concept.grounding_links.append({
            "intent": role,
            "lexeme": label,
            "oets_node": oets_node,
            "timestamp": time.time(),
            "source_text": str(source_text or ""),
            "note": str(note or ""),
        })
        concept.grounding_links = concept.grounding_links[-30:]
        self.grounding_log.append({
            "modality": self.modality,
            "concept": concept.label,
            "intent": role,
            "lexeme": label,
            "oets_node": oets_node,
            "timestamp": time.time(),
            "source_text": str(source_text or ""),
            "note": str(note or ""),
        })
        self.grounding_log = self.grounding_log[-200:]
        return {
            "matched": True,
            "created": created,
            "label": concept.label,
            "concept_id": concept.concept_id,
            "aliases": list(concept.aliases or []),
            "confidence": round(float(concept.confidence or 0.0), 4),
            "stability": round(float(concept.stability or 0.0), 4),
        }

    def record_percept(self, label: str, feature_vector: List[float]):
        """Store raw percept for later clustering."""
        self.raw_percepts[label].append(feature_vector)
        # Limit raw percepts per label
        if len(self.raw_percepts[label]) > 50:
            self.raw_percepts[label] = self.raw_percepts[label][-30:]

    def cluster_and_promote(self, label: str, generation: int = 0) -> Optional[SensoryConcept]:
        """
        Attempt to promote raw percepts into a stable concept.
        Requires enough observations for reliable clustering.
        """
        percepts = self.raw_percepts.get(label, [])
        if len(percepts) < self.CLUSTER_THRESHOLD:
            return None

        # Calculate centroid
        centroid = np.mean(percepts, axis=0).tolist()

        if label in self.concepts:
            # Update existing concept
            concept = self.concepts[label]
            old_centroid = np.array(concept.centroid)
            new_centroid = np.array(centroid)
            concept.centroid = (0.7 * old_centroid + 0.3 * new_centroid).tolist()
            concept.confidence = min(1.0, concept.confidence + 0.05)
            concept.stability = min(1.0, concept.stability + 0.03)
            concept.percept_cluster.extend(percepts)
            concept.percept_cluster = concept.percept_cluster[-20:]
        else:
            # Create new concept
            concept = SensoryConcept(
                concept_id=_generate_id(f"{self.modality}_concept"),
                modality=self.modality,
                label=label,
                centroid=centroid,
                percept_cluster=percepts[-10:],
                label_hypotheses={label: 1.0},
                confidence=0.7,
                generation_created=generation
            )
            self.concepts[label] = concept
            logger.info(f"[SENSORY] Promoted {self.modality} concept: {label}")

        # Clear raw percepts after promotion
        self.raw_percepts[label] = []
        return concept

    def find_matching_concept(self, feature_vector: List[float],
                              threshold: float = None) -> Optional[SensoryConcept]:
        """Find the best matching concept for a feature vector."""
        threshold = threshold or self.SIMILARITY_THRESHOLD
        best_match = None
        best_score = threshold

        for concept in self.concepts.values():
            if concept.centroid:
                score = _cosine_similarity(feature_vector, concept.centroid)
                if score > best_score:
                    best_score = score
                    best_match = concept

        if best_match:
            best_match.times_matched += 1
            best_match.last_accessed = time.time()

        return best_match

    def add_grounding(self, concept_label: str, intent: str,
                      lexeme: str, oets_node: str = ""):
        """Ground a sensory concept to language/intent."""
        if concept_label in self.concepts:
            self.concepts[concept_label].grounding_links.append({
                "intent": intent,
                "lexeme": lexeme,
                "oets_node": oets_node,
                "timestamp": time.time()
            })
        self.grounding_log.append({
            "modality": self.modality,
            "concept": concept_label,
            "intent": intent,
            "lexeme": lexeme,
            "oets_node": oets_node,
            "timestamp": time.time()
        })

    def prune(self, max_concepts: int = 100, min_confidence: float = 0.3):
        """Prune low-confidence concepts."""
        if len(self.concepts) <= max_concepts:
            return

        # Remove lowest confidence concepts
        sorted_concepts = sorted(
            self.concepts.items(),
            key=lambda x: x[1].confidence
        )
        for label, _ in sorted_concepts[:len(self.concepts) - max_concepts]:
            if self.concepts[label].confidence < min_confidence:
                del self.concepts[label]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modality": self.modality,
            "concepts": {k: v.to_dict() for k, v in self.concepts.items()},
            "grounding_log": self.grounding_log[-100:]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensoryConceptMemory':
        mem = cls(data.get("modality", "unknown"))
        for k, v in data.get("concepts", {}).items():
            mem.concepts[k] = SensoryConcept.from_dict(v)
        mem.grounding_log = data.get("grounding_log", [])
        return mem


# ============================================================================
# SECTION 4: SENSORY GENES -- DNA Integration
# ============================================================================

def create_visual_genes() -> List[Gene]:
    """Create genes for visual competency traits."""
    return [
        Gene(
            gene_id="gene_visual_focus",
            core_trait="visual-focus",
            stability_scalar=0.7,
            emotional_band={"curiosity": 0.4, "determination": 0.3, "anticipation": 0.3},
            manifold_orientation=(0.0, 0.0, 0.0, 0.8, 0.0),  # I_SAW dominant
            compression_density=0.6,
            activation_state="active"
        ),
        Gene(
            gene_id="gene_visual_motion",
            core_trait="visual-motion-sensitivity",
            stability_scalar=0.65,
            emotional_band={"surprise": 0.4, "anticipation": 0.4, "caution": 0.2},
            manifold_orientation=(0.0, 0.0, 0.3, 0.7, 0.0),
            compression_density=0.5,
            activation_state="active"
        ),
        Gene(
            gene_id="gene_visual_recognition",
            core_trait="visual-recognition",
            stability_scalar=0.75,
            emotional_band={"trust": 0.4, "curiosity": 0.4, "neutral": 0.2},
            manifold_orientation=(0.5, 0.0, 0.0, 0.5, 0.0),
            compression_density=0.7,
            activation_state="active"
        ),
        Gene(
            gene_id="gene_visual_detail",
            core_trait="visual-detail-orientation",
            stability_scalar=0.7,
            emotional_band={"curiosity": 0.5, "determination": 0.3, "neutral": 0.2},
            manifold_orientation=(0.0, 0.4, 0.0, 0.6, 0.0),
            compression_density=0.65,
            activation_state="active"
        ),
    ]


def create_audio_genes() -> List[Gene]:
    """Create genes for audio competency traits."""
    return [
        Gene(
            gene_id="gene_audio_sensitivity",
            core_trait="audio-sensitivity",
            stability_scalar=0.65,
            emotional_band={"anticipation": 0.4, "caution": 0.3, "curiosity": 0.3},
            manifold_orientation=(0.0, 0.0, 0.0, 0.7, 0.3),
            compression_density=0.5,
            activation_state="active"
        ),
        Gene(
            gene_id="gene_audio_voice_isolation",
            core_trait="audio-voice-isolation",
            stability_scalar=0.7,
            emotional_band={"trust": 0.5, "curiosity": 0.3, "determination": 0.2},
            manifold_orientation=(0.3, 0.0, 0.0, 0.7, 0.0),
            compression_density=0.6,
            activation_state="active"
        ),
        Gene(
            gene_id="gene_audio_emotion_detection",
            core_trait="audio-emotion-detection",
            stability_scalar=0.6,
            emotional_band={"trust": 0.4, "curiosity": 0.3, "sadness": 0.1, "joy": 0.2},
            manifold_orientation=(0.4, 0.0, 0.0, 0.5, 0.1),
            compression_density=0.55,
            activation_state="active"
        ),
    ]


# ============================================================================
# SECTION 5: SENSORY CRYSTALS -- Behavioral Facet Groups
# ============================================================================

def create_visual_crystal() -> BehavioralCrystal:
    """Create behavioral crystal for visual competency."""
    crystal = BehavioralCrystal("crystal_visual", "visual_perception")
    crystal.add_facet("focus", 0.5, evolution_rate=0.03)
    crystal.add_facet("motion_sensitivity", 0.5, evolution_rate=0.04)
    crystal.add_facet("recognition_threshold", 0.5, evolution_rate=0.025)
    crystal.add_facet("detail_orientation", 0.5, evolution_rate=0.03)
    return crystal


def create_audio_crystal() -> BehavioralCrystal:
    """Create behavioral crystal for audio competency."""
    crystal = BehavioralCrystal("crystal_audio", "audio_perception")
    crystal.add_facet("sensitivity", 0.5, evolution_rate=0.035)
    crystal.add_facet("voice_isolation", 0.6, evolution_rate=0.03)
    crystal.add_facet("emotion_detection", 0.5, evolution_rate=0.04)
    return crystal


# ============================================================================
# SECTION 6: PATTERN MAPPING -- Route to Existing PatternTypes
# ============================================================================

class SensoryPatternMapper:
    """
    Maps visual and audio input to Aurora's existing PatternTypes.
    Visual/audio data enriches TEMPORAL, SPATIAL, EMOTIONAL, STRUCTURAL, ABSTRACT patterns.
    """

    # Mapping weights: how much each sensory feature contributes to each pattern type
    VISUAL_PATTERN_MAP = {
        PatternType.TEMPORAL: ["motion_detected", "brightness_change", "position_delta"],
        PatternType.SPATIAL: ["object_positions", "scene_layout", "depth_cues"],
        PatternType.EMOTIONAL: ["face_expression", "body_language", "color_temperature"],
        PatternType.STRUCTURAL: ["edges", "shapes", "object_count", "symmetry"],
        PatternType.ABSTRACT: ["scene_complexity", "pattern_repetition", "meta_features"],
    }

    AUDIO_PATTERN_MAP = {
        PatternType.TEMPORAL: ["rhythm", "tempo", "duration", "onset_pattern"],
        PatternType.SPATIAL: ["stereo_field", "reverb_cues", "distance_estimate"],
        PatternType.EMOTIONAL: ["pitch_variation", "volume_dynamics", "voice_tone"],
        PatternType.STRUCTURAL: ["frequency_bands", "harmonic_content", "spectral_shape"],
        PatternType.ABSTRACT: ["semantic_content", "intent_markers", "meta_audio"],
    }

    def __init__(self):
        self.visual_contributions: Dict[str, float] = defaultdict(float)
        self.audio_contributions: Dict[str, float] = defaultdict(float)

    def map_visual_input(self, visual_data: Dict[str, Any],
                         mode: ExistenceMode) -> List[DimensionalPattern]:
        """
        Convert visual input to DimensionalPatterns.
        Mode-gated: higher modes unlock more pattern types.
        """
        patterns = []

        if mode is None:
            mode = ExistenceMode.BOUNDED

        if mode.value < ExistenceMode.TRANSIENT.value:
            return patterns

        # Extract features from visual data
        features = visual_data.get("features", {})
        motion = visual_data.get("motion_detected", False)
        faces = visual_data.get("faces", [])
        brightness = visual_data.get("brightness", 0.5)
        objects = visual_data.get("objects", [])

        # STRUCTURAL -- always available at TRANSIENT+
        if objects or features:
            salience = min(1.0, len(objects) / 5.0) if objects else 0.3
            complexity = _clamp(len(features) / 10.0)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("vpat_struct"),
                pattern_type=PatternType.STRUCTURAL,
                salience=salience,
                complexity=complexity,
                features={"object_count": len(objects), "feature_count": len(features)}
            ))

        # TEMPORAL -- available at TRANSIENT+
        if motion and mode.value >= ExistenceMode.TRANSIENT.value:
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("vpat_temp"),
                pattern_type=PatternType.TEMPORAL,
                salience=0.7 if motion else 0.2,
                complexity=0.4,
                features={"motion_detected": 1.0 if motion else 0.0, "brightness": brightness}
            ))

        # SPATIAL -- available at PERSISTENT+
        if mode.value >= ExistenceMode.PERSISTENT.value and objects:
            spatial_density = len(objects) / 10.0
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("vpat_spat"),
                pattern_type=PatternType.SPATIAL,
                salience=_clamp(spatial_density),
                complexity=_clamp(spatial_density * 0.8),
                features={"spatial_density": spatial_density}
            ))

        # EMOTIONAL -- available at BOUNDED+
        if mode.value >= ExistenceMode.BOUNDED.value and faces:
            emotion_score = len(faces) * 0.3
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("vpat_emot"),
                pattern_type=PatternType.EMOTIONAL,
                salience=_clamp(emotion_score),
                complexity=0.5,
                features={"face_count": len(faces), "emotion_salience": emotion_score}
            ))

        # ABSTRACT -- available at AGENTIC only
        if mode.value >= ExistenceMode.AGENTIC.value and len(patterns) >= 2:
            mean_salience = sum(p.salience for p in patterns) / len(patterns)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("vpat_abs"),
                pattern_type=PatternType.ABSTRACT,
                salience=mean_salience,
                complexity=len(patterns) / 5.0,
                features={"pattern_count": len(patterns), "meta_salience": mean_salience}
            ))

        return patterns

    def map_audio_input(self, audio_data: Dict[str, Any],
                        mode: ExistenceMode) -> List[DimensionalPattern]:
        """
        Convert audio input to DimensionalPatterns.
        Mode-gated: higher modes unlock more pattern types.
        """
        patterns = []

        if mode is None:
            mode = ExistenceMode.BOUNDED

        if mode.value < ExistenceMode.TRANSIENT.value:
            return patterns

        # Extract features from audio data
        features = audio_data.get("features", {})
        voice_detected = audio_data.get("voice_detected", False)
        volume = audio_data.get("volume", 0.5)
        pitch = audio_data.get("pitch", 0.5)
        category = audio_data.get("category", "unknown")

        # STRUCTURAL -- always available at TRANSIENT+
        if features:
            complexity = _clamp(len(features) / 10.0)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("apat_struct"),
                pattern_type=PatternType.STRUCTURAL,
                salience=0.4 + volume * 0.4,
                complexity=complexity,
                features={"feature_count": len(features), "volume": volume}
            ))

        # TEMPORAL -- available at TRANSIENT+ (rhythm, timing)
        if "rhythm" in features or "tempo" in features:
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("apat_temp"),
                pattern_type=PatternType.TEMPORAL,
                salience=0.5 + features.get("rhythm", 0) * 0.3,
                complexity=0.4,
                features={"rhythm": features.get("rhythm", 0), "tempo": features.get("tempo", 0)}
            ))

        # SPATIAL -- available at PERSISTENT+ (stereo, reverb)
        if mode.value >= ExistenceMode.PERSISTENT.value:
            if "stereo" in features or "reverb" in features:
                patterns.append(DimensionalPattern(
                    pattern_id=_generate_id("apat_spat"),
                    pattern_type=PatternType.SPATIAL,
                    salience=0.4,
                    complexity=0.3,
                    features={"stereo": features.get("stereo", 0.5), "reverb": features.get("reverb", 0)}
                ))

        # EMOTIONAL -- available at BOUNDED+ (voice emotion)
        if mode.value >= ExistenceMode.BOUNDED.value and voice_detected:
            emotion_salience = 0.5 + abs(pitch - 0.5) * 0.5
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("apat_emot"),
                pattern_type=PatternType.EMOTIONAL,
                salience=emotion_salience,
                complexity=0.5,
                features={"voice_detected": 1.0, "pitch": pitch, "emotion_estimate": emotion_salience}
            ))

        # ABSTRACT -- available at AGENTIC only
        if mode.value >= ExistenceMode.AGENTIC.value and len(patterns) >= 2:
            mean_salience = sum(p.salience for p in patterns) / len(patterns)
            patterns.append(DimensionalPattern(
                pattern_id=_generate_id("apat_abs"),
                pattern_type=PatternType.ABSTRACT,
                salience=mean_salience,
                complexity=len(patterns) / 5.0,
                features={"pattern_count": len(patterns), "category": hash(category) % 100 / 100.0}
            ))

        return patterns


# ============================================================================
# SECTION 7: SENSORY COMPETENCY ENGINE -- Main Controller
# ============================================================================

class SensoryCompetencyEngine:
    """
    Main controller for Aurora's evolutionary sensory capabilities.

    Integrates:
    - Visual and audio concept memories
    - Sensory genes (DNA integration)
    - Behavioral crystals (facet evolution)
    - Pattern mapping to Layer 5
    - OETS grounding (when available)
    """

    # Base percepts from lineage (seed templates)
    BASE_VISUAL_PERCEPTS = [
        "face_detected", "object_detected", "text_detected",
        "motion_detected", "color_blob", "edge_pattern"
    ]
    BASE_AUDIO_PERCEPTS = [
        "human_voice", "music_pattern", "ambient_noise",
        "alarm_tone", "impulse_noise"
    ]

    def __init__(self, persistence_dir: str = None, dna_system: DNASystem = None):
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        if self.persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)

        self.dna_system = dna_system

        # Concept memories
        self.visual_concepts = SensoryConceptMemory("visual")
        self.audio_concepts = SensoryConceptMemory("audio")

        # Percept templates
        self.visual_templates: Dict[str, SensoryPerceptTemplate] = {}
        self.audio_templates: Dict[str, SensoryPerceptTemplate] = {}

        # Behavioral crystals (evolvable facets)
        self.visual_crystal = create_visual_crystal()
        self.audio_crystal = create_audio_crystal()

        # Pattern mapper
        self.pattern_mapper = SensoryPatternMapper()

        # OETS reference (if available)
        self.oets: Optional['OntologicalScaffoldingEngine'] = None

        # Statistics
        self.total_visual_processed = 0
        self.total_audio_processed = 0
        self.generation = 0

        # Load state or bootstrap
        if not self._load_state():
            self._bootstrap_lineage()

    def _bootstrap_lineage(self):
        """Bootstrap base percept templates from lineage constants."""
        for name in self.BASE_VISUAL_PERCEPTS:
            self.visual_templates[name] = SensoryPerceptTemplate(
                template_id=_generate_id("vt"),
                modality="visual",
                name=name,
                confidence=1.0,
                stability=1.0
            )
        for name in self.BASE_AUDIO_PERCEPTS:
            self.audio_templates[name] = SensoryPerceptTemplate(
                template_id=_generate_id("at"),
                modality="audio",
                name=name,
                confidence=1.0,
                stability=1.0
            )
        logger.info("[SENSORY] Bootstrapped lineage percept templates")

    def attach_oets(self, oets: 'OntologicalScaffoldingEngine'):
        """Attach OETS for semantic grounding."""
        self.oets = oets
        logger.info("[SENSORY] OETS attached for semantic grounding")

    def attach_dna(self, dna_system: DNASystem):
        """Attach DNA system and add sensory genes if not present."""
        self.dna_system = dna_system

        # Check if sensory genes exist
        existing_ids = {g.gene_id for g in dna_system.genome.core_genes}
        visual_genes = create_visual_genes()
        audio_genes = create_audio_genes()

        for gene in visual_genes + audio_genes:
            if gene.gene_id not in existing_ids:
                dna_system.genome.core_genes.append(gene)
                logger.info(f"[SENSORY] Added gene: {gene.core_trait}")

    def get_visual_competency(self) -> Dict[str, float]:
        """Get current visual competency values."""
        return self.visual_crystal.get_genome_dict()

    def get_audio_competency(self) -> Dict[str, float]:
        """Get current audio competency values."""
        return self.audio_crystal.get_genome_dict()

    def process_visual_input(self, visual_data: Dict[str, Any],
                             mode: ExistenceMode,
                             intent: str = None,
                             text_context: str = None) -> Dict[str, Any]:
        """
        Process visual input through the sensory pipeline.

        Mode-gated:
          REFERENCE: Cannot process visual input
          TRANSIENT: Basic structural detection only
          PERSISTENT: Adds spatial awareness
          BOUNDED: Adds emotional face detection
          AGENTIC: Full abstract pattern recognition

        Returns patterns mapped to existing PatternTypes.
        """
        result = {
            "patterns": [],
            "concepts_matched": [],
            "templates_matched": [],
            "competency": self.get_visual_competency()
        }

        if mode is None:
            mode = ExistenceMode.BOUNDED

        if mode.value < ExistenceMode.TRANSIENT.value:
            return result

        self.total_visual_processed += 1

        # Get competency-modulated features
        competency = self.get_visual_competency()
        focus = competency.get("focus", 0.5)
        motion_sens = competency.get("motion_sensitivity", 0.5)
        rec_threshold = competency.get("recognition_threshold", 0.5)
        detail = competency.get("detail_orientation", 0.5)

        # Apply competency to feature extraction
        if "brightness" in visual_data:
            visual_data["brightness"] = visual_data["brightness"] * focus

        # Generate feature vector for concept matching
        feature_vector = self._extract_visual_features(visual_data, competency)

        # Match against templates
        for name, template in self.visual_templates.items():
            match_score = template.match(
                features=visual_data.get("features", {}),
                centroid=feature_vector
            )
            if match_score >= rec_threshold:
                template.update_from_observation(
                    features=visual_data.get("features", {}),
                    centroid=feature_vector
                )
                result["templates_matched"].append({
                    "name": name,
                    "score": match_score
                })

        # Match or record concept
        matched_concept = self.visual_concepts.find_matching_concept(
            feature_vector, threshold=rec_threshold
        )
        if matched_concept:
            result["concepts_matched"].append(matched_concept.label)
            # Ground whenever a concept is recognised — even during ambient sensing
            # with no conversation context. Use the concept label as the lexeme when
            # no text_context is available so OETS grows from pure sensory experience.
            _gi = intent or "sensory:visual"
            _gt = text_context or matched_concept.label
            self.visual_concepts.add_grounding(
                matched_concept.label, _gi, _gt,
                oets_node=self._ground_to_oets(matched_concept.label, _gi, _gt)
            )
        else:
            # Record raw percept for later clustering
            label = visual_data.get("label", "unknown_visual")
            self.visual_concepts.record_percept(label, feature_vector)
            # Attempt promotion
            promoted = self.visual_concepts.cluster_and_promote(label, self.generation)
            if promoted:
                result["concepts_matched"].append(f"NEW:{promoted.label}")

        # Map to Layer 5 patterns
        result["patterns"] = self.pattern_mapper.map_visual_input(visual_data, mode)

        return result

    def process_audio_input(self, audio_data: Dict[str, Any],
                            mode: ExistenceMode,
                            intent: str = None,
                            text_context: str = None) -> Dict[str, Any]:
        """
        Process audio input through the sensory pipeline.

        Mode-gated:
          REFERENCE: Cannot process audio input
          TRANSIENT: Basic structural detection only
          PERSISTENT: Adds spatial stereo awareness
          BOUNDED: Adds emotional voice detection
          AGENTIC: Full abstract pattern recognition

        Returns patterns mapped to existing PatternTypes.
        """
        result = {
            "patterns": [],
            "concepts_matched": [],
            "templates_matched": [],
            "competency": self.get_audio_competency()
        }

        if mode is None:
            mode = ExistenceMode.BOUNDED

        if mode.value < ExistenceMode.TRANSIENT.value:
            return result

        self.total_audio_processed += 1

        # Get competency values
        competency = self.get_audio_competency()
        sensitivity = competency.get("sensitivity", 0.5)
        voice_iso = competency.get("voice_isolation", 0.6)
        emotion_det = competency.get("emotion_detection", 0.5)

        # Apply competency to detection thresholds
        volume_threshold = 0.1 + (1.0 - sensitivity) * 0.5

        if audio_data.get("volume", 0) < volume_threshold:
            return result  # Below detection threshold

        # Generate feature vector
        feature_vector = self._extract_audio_features(audio_data, competency)

        # Match against templates
        for name, template in self.audio_templates.items():
            match_score = template.match(
                features=audio_data.get("features", {}),
                centroid=feature_vector
            )
            if match_score >= 0.6:
                template.update_from_observation(
                    features=audio_data.get("features", {}),
                    centroid=feature_vector
                )
                result["templates_matched"].append({
                    "name": name,
                    "score": match_score
                })

        # Match or record concept
        matched_concept = self.audio_concepts.find_matching_concept(
            feature_vector, threshold=0.8
        )
        if matched_concept:
            result["concepts_matched"].append(matched_concept.label)
            _gi = intent or "sensory:audio"
            _gt = text_context or matched_concept.label
            self.audio_concepts.add_grounding(
                matched_concept.label, _gi, _gt,
                oets_node=self._ground_to_oets(matched_concept.label, _gi, _gt)
            )
        else:
            label = audio_data.get("label", "unknown_audio")
            self.audio_concepts.record_percept(label, feature_vector)
            promoted = self.audio_concepts.cluster_and_promote(label, self.generation)
            if promoted:
                result["concepts_matched"].append(f"NEW:{promoted.label}")

        # Map to Layer 5 patterns
        result["patterns"] = self.pattern_mapper.map_audio_input(audio_data, mode)

        return result

    def _extract_visual_features(self, visual_data: Dict[str, Any],
                                 competency: Dict[str, float]) -> List[float]:
        """Extract normalized feature vector from visual data."""
        # 32-dimensional feature vector
        vec = [0.0] * 32

        # Basic features (0-7)
        vec[0] = visual_data.get("brightness", 0.5)
        vec[1] = 1.0 if visual_data.get("motion_detected", False) else 0.0
        vec[2] = min(1.0, len(visual_data.get("faces", [])) / 3.0)
        vec[3] = min(1.0, len(visual_data.get("objects", [])) / 10.0)

        # Competency-weighted features (8-15)
        vec[8] = competency.get("focus", 0.5)
        vec[9] = competency.get("motion_sensitivity", 0.5)
        vec[10] = competency.get("recognition_threshold", 0.5)
        vec[11] = competency.get("detail_orientation", 0.5)

        # Additional features from data (16-31)
        features = visual_data.get("features", {})
        for i, (k, v) in enumerate(list(features.items())[:16]):
            vec[16 + i] = _clamp(float(v)) if isinstance(v, (int, float)) else 0.5

        return vec

    def _extract_audio_features(self, audio_data: Dict[str, Any],
                                competency: Dict[str, float]) -> List[float]:
        """Extract normalized feature vector from audio data."""
        # 32-dimensional feature vector
        vec = [0.0] * 32

        # Basic features (0-7)
        vec[0] = audio_data.get("volume", 0.5)
        vec[1] = audio_data.get("pitch", 0.5)
        vec[2] = 1.0 if audio_data.get("voice_detected", False) else 0.0
        vec[3] = {"speech": 0.3, "music": 0.6, "noise": 0.1, "alarm": 0.8}.get(
            audio_data.get("category", "unknown"), 0.5
        )

        # Competency-weighted features (8-15)
        vec[8] = competency.get("sensitivity", 0.5)
        vec[9] = competency.get("voice_isolation", 0.6)
        vec[10] = competency.get("emotion_detection", 0.5)

        # Additional features from data (16-31)
        features = audio_data.get("features", {})
        for i, (k, v) in enumerate(list(features.items())[:16]):
            vec[16 + i] = _clamp(float(v)) if isinstance(v, (int, float)) else 0.5

        return vec

    def _ground_to_oets(self, concept_label: str, intent: str,
                        lexeme: str) -> str:
        """Ground sensory concept to OETS semantic node."""
        if not _OETS_AVAILABLE or not self.oets:
            return ""

        # Try to find or create OETS node for this concept
        try:
            # Check if node exists
            if hasattr(self.oets, 'web') and concept_label in self.oets.web.nodes:
                node = self.oets.web.nodes[concept_label]
                node.encounter(f"sensory:{intent}")
                return concept_label

            # Create new node if OETS supports it
            if hasattr(self.oets, 'add_node'):
                self.oets.add_node(concept_label, role="sensory_concept")
                return concept_label

        except Exception as e:
            logger.debug(f"[SENSORY] OETS grounding failed: {e}")

        return ""

    def evolve(self, pressure: float = 1.0) -> Dict[str, Any]:
        """
        Apply evolutionary pressure to sensory competencies.
        Called during generational transition.
        """
        self.generation += 1
        mutations = {
            "visual": self.visual_crystal.evolve(pressure),
            "audio": self.audio_crystal.evolve(pressure),
            "generation": self.generation
        }

        # Update DNA if attached
        if self.dna_system:
            self._sync_to_dna()

        logger.info(f"[SENSORY] Evolved to generation {self.generation}")
        return mutations

    def _sync_to_dna(self):
        """Sync crystal values back to DNA genes."""
        if not self.dna_system:
            return

        gene_map = {
            "gene_visual_focus": ("visual", "focus"),
            "gene_visual_motion": ("visual", "motion_sensitivity"),
            "gene_visual_recognition": ("visual", "recognition_threshold"),
            "gene_visual_detail": ("visual", "detail_orientation"),
            "gene_audio_sensitivity": ("audio", "sensitivity"),
            "gene_audio_voice_isolation": ("audio", "voice_isolation"),
            "gene_audio_emotion_detection": ("audio", "emotion_detection"),
        }

        for gene in self.dna_system.genome.core_genes:
            if gene.gene_id in gene_map:
                modality, facet_name = gene_map[gene.gene_id]
                crystal = self.visual_crystal if modality == "visual" else self.audio_crystal
                if facet_name in crystal.facets:
                    facet_value = crystal.facets[facet_name].value
                    # Create allele from current value if significantly different
                    if gene.fractal_alleles:
                        last_allele = gene.fractal_alleles[-1]
                        if abs(last_allele.dominance_score - facet_value) > 0.1:
                            self._create_sensory_allele(gene, facet_value)
                    elif facet_value != 0.5:
                        self._create_sensory_allele(gene, facet_value)

    def _create_sensory_allele(self, gene: Gene, value: float):
        """Create a fractal allele from sensory evolution."""
        allele = FractalAllele(
            allele_id=_generate_id("sens_allele"),
            origin="sensory_evolution",
            seed_ids=[],
            emotional_bias=dict(gene.emotional_band),
            manifold_bias=gene.manifold_orientation,
            strategy_profile={"perceive": value, "ignore": 1.0 - value},
            dominance_score=value,
            mutation_potential=0.3,
            survival_impact=0.0
        )
        gene.fractal_alleles.append(allele)
        if len(gene.fractal_alleles) > 10:
            gene.fractal_alleles = gene.fractal_alleles[-10:]
        gene.history_log.append(GeneEvent(
            t_gen=self.generation,
            cause="sensory_evolution",
            delta={"dominance": value}
        ))

    def prune(self, max_visual_concepts: int = 100, max_audio_concepts: int = 100):
        """Prune low-value concepts."""
        self.visual_concepts.prune(max_visual_concepts)
        self.audio_concepts.prune(max_audio_concepts)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "generation": self.generation,
            "visual": {
                "total_processed": self.total_visual_processed,
                "templates": len(self.visual_templates),
                "concepts": len(self.visual_concepts.concepts),
                "competency": self.get_visual_competency()
            },
            "audio": {
                "total_processed": self.total_audio_processed,
                "templates": len(self.audio_templates),
                "concepts": len(self.audio_concepts.concepts),
                "competency": self.get_audio_competency()
            }
        }

    def _save_state(self):
        """Save state to persistence directory."""
        if not self.persistence_dir:
            return

        state = {
            "generation": self.generation,
            "total_visual_processed": self.total_visual_processed,
            "total_audio_processed": self.total_audio_processed,
            "visual_templates": {k: v.to_dict() for k, v in self.visual_templates.items()},
            "audio_templates": {k: v.to_dict() for k, v in self.audio_templates.items()},
            "visual_concepts": self.visual_concepts.to_dict(),
            "audio_concepts": self.audio_concepts.to_dict(),
            "visual_crystal": self.visual_crystal.get_genome_dict(),
            "audio_crystal": self.audio_crystal.get_genome_dict(),
        }

        path = self.persistence_dir / "sensory_competency_state.json"
        try:
            with PERSISTENCE_LOCK:
                ok = atomic_write_json(path, state, indent=2)
            if ok:
                logger.debug(f"[SENSORY] State saved to {path}")
            else:
                logger.error(f"[SENSORY] Failed to save state: {path}")
        except Exception as e:
            logger.error(f"[SENSORY] Failed to save state: {e}")

    def _load_state(self) -> bool:
        """Load state from persistence directory."""
        if not self.persistence_dir:
            return False

        path = self.persistence_dir / "sensory_competency_state.json"
        if not path.exists():
            return False

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            self.generation = state.get("generation", 0)
            self.total_visual_processed = state.get("total_visual_processed", 0)
            self.total_audio_processed = state.get("total_audio_processed", 0)

            # Load templates
            for k, v in state.get("visual_templates", {}).items():
                self.visual_templates[k] = SensoryPerceptTemplate.from_dict(v)
            for k, v in state.get("audio_templates", {}).items():
                self.audio_templates[k] = SensoryPerceptTemplate.from_dict(v)

            # Load concept memories
            if "visual_concepts" in state:
                self.visual_concepts = SensoryConceptMemory.from_dict(state["visual_concepts"])
            if "audio_concepts" in state:
                self.audio_concepts = SensoryConceptMemory.from_dict(state["audio_concepts"])

            # Load crystal values
            if "visual_crystal" in state:
                for name, value in state["visual_crystal"].items():
                    if name in self.visual_crystal.facets:
                        self.visual_crystal.facets[name].value = value
            if "audio_crystal" in state:
                for name, value in state["audio_crystal"].items():
                    if name in self.audio_crystal.facets:
                        self.audio_crystal.facets[name].value = value

            logger.info(f"[SENSORY] State loaded from {path} (gen {self.generation})")
            return True

        except Exception as e:
            logger.error(f"[SENSORY] Failed to load state: {e}")
            return False

    def save_state(self):
        """Public save method."""
        self._save_state()


# ============================================================================
# SECTION 8: FACTORY & CONVENIENCE FUNCTIONS
# ============================================================================

def create_sensory_competency_engine(
    persistence_dir: str = None,
    dna_system: DNASystem = None
) -> SensoryCompetencyEngine:
    """
    Factory function to create a SensoryCompetencyEngine.

    Args:
        persistence_dir: Directory for state persistence
        dna_system: Aurora's DNA system for gene integration

    Returns:
        Configured SensoryCompetencyEngine
    """
    engine = SensoryCompetencyEngine(persistence_dir, dna_system)
    return engine


def get_sensory_genes() -> List[Gene]:
    """Get all sensory genes for DNA integration."""
    return create_visual_genes() + create_audio_genes()


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Main engine
    "SensoryCompetencyEngine",
    "create_sensory_competency_engine",

    # Templates and concepts
    "SensoryPerceptTemplate",
    "SensoryConcept",
    "SensoryConceptMemory",

    # Pattern mapping
    "SensoryPatternMapper",

    # Gene factories
    "create_visual_genes",
    "create_audio_genes",
    "get_sensory_genes",

    # Crystal factories
    "create_visual_crystal",
    "create_audio_crystal",

    # Trait domains
    "SensoryTraitDomain",
]


# ============================================================================
# MIGRATED LAYER 5 EXTENSIONS: HARDWARE INTERFACE
# ============================================================================

#!/usr/bin/env python3
"""
AURORA HARDWARE INTERFACE (Linux Desktop)
==========================================
Connects real camera, microphone, and speaker to Aurora's sensory brain.

This is the "body" that captures raw sensory data and feeds it to
the SensoryCompetencyEngine (the "brain") for evolutionary processing.

COMPONENTS:
  LinuxCamera      - OpenCV webcam capture
  LinuxMicrophone  - Audio capture via sounddevice/speech_recognition
  LinuxVoice       - Text-to-speech output via pyttsx3/espeak

INTEGRATION:
  HardwareInterface orchestrates all components and feeds data to
  SensoryCompetencyEngine.process_visual_input() and process_audio_input()

DEPENDENCIES (install as needed):
  pip install opencv-python      # Camera
  pip install sounddevice numpy  # Microphone (raw audio)
  pip install SpeechRecognition  # Speech-to-text
  pip install pyttsx3            # Text-to-speech

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import threading
import queue
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


def _is_termux_env() -> bool:
    prefix = os.environ.get('PREFIX', '')
    return ('com.termux' in prefix.lower() or
            os.environ.get('TERMUX_VERSION') is not None or
            shutil.which('termux-info') is not None)

# ============================================================================
# OPTIONAL IMPORTS - Graceful degradation if not installed
# ============================================================================

_SKIP_HARDWARE_IMPORTS = os.environ.get('AURORA_SKIP_HARDWARE_IMPORTS', '').lower() in ('1', 'true', 'yes')

_CV2_AVAILABLE = False
_SOUNDDEVICE_AVAILABLE = False
_SPEECH_RECOGNITION_AVAILABLE = False
_PYTTSX3_AVAILABLE = False
_EDGE_TTS_AVAILABLE = False

if _SKIP_HARDWARE_IMPORTS:
    logger.info("[HARDWARE] Optional hardware imports skipped (AURORA_SKIP_HARDWARE_IMPORTS set)")
else:
    # OpenCV for camera
    try:
        import cv2
        import numpy as np
        _CV2_AVAILABLE = True
    except Exception:
        logger.warning("[HARDWARE] OpenCV not available. Install: pip install opencv-python")

    # Sounddevice for raw audio capture
    try:
        import sounddevice as sd
        _SOUNDDEVICE_AVAILABLE = True
    except Exception:
        logger.warning("[HARDWARE] sounddevice not available. Install: pip install sounddevice")

    # SpeechRecognition for speech-to-text
    try:
        import speech_recognition as sr
        _SPEECH_RECOGNITION_AVAILABLE = True
    except Exception:
        logger.warning("[HARDWARE] SpeechRecognition not available. Install: pip install SpeechRecognition")

    # pyttsx3 for text-to-speech
    try:
        import pyttsx3
        _PYTTSX3_AVAILABLE = True
    except ImportError:
        logger.warning("[HARDWARE] pyttsx3 not available. Install: pip install pyttsx3")

# TTS libraries should remain available even when camera/mic hardware imports are skipped.
if not _PYTTSX3_AVAILABLE:
    try:
        import pyttsx3
        _PYTTSX3_AVAILABLE = True
    except ImportError:
        logger.info("[VOICE] pyttsx3 not available. Install: pip install pyttsx3")

try:
    import edge_tts
    import asyncio
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    logger.info("[VOICE] edge-tts not available. Install for natural voices: pip install edge-tts")

# numpy (should be available if cv2 or sounddevice is)
try:
    import numpy as np
except ImportError:
    pass


# ============================================================================
# SECTION 1: CAMERA CAPTURE (OpenCV)
# ============================================================================

class LinuxCamera:
    """
    Webcam capture using OpenCV.
    Provides frames for visual processing.
    """

    def __init__(self, device_id: int = 0, width: int = 640, height: int = 480):
        self.device_id = device_id
        self.width = width
        self.height = height
        self.cap: Optional[Any] = None
        self.running = False
        self._lock = threading.Lock()
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self._mediapipe = None
        self._mp_face_detector = None
        self._mp_pose = None
        self._ultralytics_detector = None
        self._last_object_detection: Dict[str, Any] = {"frame_count": -1, "objects": []}

    def _ensure_mediapipe_detectors(self) -> None:
        if self._mediapipe is None:
            try:
                import mediapipe as mp  # type: ignore
                self._mediapipe = mp
            except Exception:
                self._mediapipe = False
        if self._mediapipe is False:
            return
        if self._mp_face_detector is None:
            try:
                self._mp_face_detector = self._mediapipe.solutions.face_detection.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=0.45,
                )
            except Exception:
                self._mp_face_detector = False
        if self._mp_pose is None:
            try:
                self._mp_pose = self._mediapipe.solutions.pose.Pose(
                    static_image_mode=False,
                    min_detection_confidence=0.45,
                    min_tracking_confidence=0.45,
                )
            except Exception:
                self._mp_pose = False

    def _load_ultralytics_detector(self):
        if self._ultralytics_detector is None:
            try:
                from ultralytics import YOLO  # type: ignore
                self._ultralytics_detector = YOLO("yolov8n.pt")
            except Exception:
                self._ultralytics_detector = False
        return None if self._ultralytics_detector is False else self._ultralytics_detector

    def _enrich_visual_features(self, frame: np.ndarray, features: Dict[str, Any]) -> None:
        if frame is None or not _CV2_AVAILABLE:
            return

        detected_objects: List[Dict[str, Any]] = []
        person_count = 0
        rgb = None

        self._ensure_mediapipe_detectors()
        if self._mediapipe is not False and (self._mp_face_detector or self._mp_pose):
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except Exception:
                rgb = None

        if self._mp_face_detector and rgb is not None:
            try:
                mp_faces = self._mp_face_detector.process(rgb)
                detections = list(getattr(mp_faces, "detections", []) or [])
                if detections:
                    h, w = frame.shape[:2]
                    enriched_faces = []
                    for det in detections:
                        bbox = det.location_data.relative_bounding_box
                        x = max(0, int(bbox.xmin * w))
                        y = max(0, int(bbox.ymin * h))
                        bw = max(1, int(bbox.width * w))
                        bh = max(1, int(bbox.height * h))
                        enriched_faces.append({"x": x, "y": y, "w": bw, "h": bh})
                    if len(enriched_faces) > len(features.get("faces", []) or []):
                        features["faces"] = enriched_faces
            except Exception:
                pass

        if self._mp_pose and rgb is not None:
            try:
                pose_result = self._mp_pose.process(rgb)
                if getattr(pose_result, "pose_landmarks", None) is not None:
                    person_count = max(person_count, 1)
                    features["features"]["pose_detected"] = 1.0
            except Exception:
                pass

        if self.frame_count % 4 == 0 or not self._last_object_detection.get("objects"):
            detector = self._load_ultralytics_detector()
            if detector is not None:
                try:
                    results = detector.predict(frame, imgsz=320, conf=0.35, max_det=8, verbose=False)
                    if results:
                        names = getattr(results[0], "names", {}) or {}
                        boxes = getattr(results[0], "boxes", None)
                        xyxy = getattr(boxes, "xyxy", None)
                        confs = getattr(boxes, "conf", None)
                        clss = getattr(boxes, "cls", None)
                        if xyxy is not None and confs is not None and clss is not None:
                            xyxy_list = xyxy.cpu().tolist()
                            conf_list = confs.cpu().tolist()
                            cls_list = clss.cpu().tolist()
                            for coords, score, cls_idx in zip(xyxy_list, conf_list, cls_list):
                                label = str(names.get(int(cls_idx), str(int(cls_idx))) or "").strip().lower()
                                if not label:
                                    continue
                                obj = {
                                    "label": label,
                                    "confidence": round(float(score), 3),
                                    "bbox": [int(v) for v in coords],
                                }
                                detected_objects.append(obj)
                                if label == "person":
                                    person_count += 1
                    self._last_object_detection = {
                        "frame_count": self.frame_count,
                        "objects": list(detected_objects),
                    }
                except Exception:
                    detected_objects = list(self._last_object_detection.get("objects") or [])
        else:
            detected_objects = list(self._last_object_detection.get("objects") or [])

        if detected_objects:
            features["objects"] = detected_objects
            labels = [str(obj.get("label", "") or "").strip() for obj in detected_objects if str(obj.get("label", "") or "").strip()]
            if labels:
                features["features"]["object_labels"] = labels[:8]
                features["features"]["object_count"] = len(labels)

        face_count = len(features.get("faces", []) or [])
        person_count = max(person_count, face_count)
        features["features"]["person_count"] = person_count
        features["features"]["person_detected"] = 1.0 if person_count > 0 else 0.0

    def open(self) -> bool:
        """Open the camera device."""
        if not _CV2_AVAILABLE:
            logger.debug("[CAMERA] OpenCV not available — skipping camera")
            return False

        try:
            self.cap = cv2.VideoCapture(self.device_id)
            if not self.cap.isOpened():
                logger.debug(f"[CAMERA] Device {self.device_id} not available")
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.running = True
            logger.info(f"[CAMERA] Opened device {self.device_id} at {self.width}x{self.height}")
            return True

        except Exception as e:
            logger.debug(f"[CAMERA] Device {self.device_id} error: {e}")
            return False

    def close(self):
        """Release the camera."""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("[CAMERA] Closed")

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame."""
        if not self.cap or not self.running:
            return None

        with self._lock:
            ret, frame = self.cap.read()
            if ret:
                self.last_frame = frame
                self.frame_count += 1
                return frame
            return None

    def extract_features(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extract visual features from a frame for SensoryCompetencyEngine.
        Returns dict compatible with process_visual_input().
        """
        if frame is None or not _CV2_AVAILABLE:
            return {}

        features = {
            "timestamp": time.time(),
            "frame_shape": frame.shape,
            "features": {},
            "objects": [],
            "faces": [],
            "motion_detected": False,
        }

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Brightness (mean intensity)
        features["brightness"] = float(np.mean(gray)) / 255.0

        # Edge detection (complexity indicator)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / edges.size
        features["features"]["edge_density"] = edge_density

        # Motion detection (compare to last frame)
        if self.last_frame is not None:
            try:
                last_gray = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray, last_gray)
                motion_amount = float(np.mean(diff)) / 255.0
                features["motion_detected"] = motion_amount > 0.02
                features["features"]["motion_intensity"] = motion_amount
            except:
                pass

        # Face detection (if cascade available)
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(face_cascade_path):
                face_cascade = cv2.CascadeClassifier(face_cascade_path)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                features["faces"] = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
                                     for (x, y, w, h) in faces]
        except Exception as e:
            logger.debug(f"[CAMERA] Face detection failed: {e}")

        # Color analysis
        if len(frame.shape) == 3:
            b, g, r = cv2.split(frame)
            features["features"]["red_mean"] = float(np.mean(r)) / 255.0
            features["features"]["green_mean"] = float(np.mean(g)) / 255.0
            features["features"]["blue_mean"] = float(np.mean(b)) / 255.0

            # HSV histogram — 24 hue bins; feeds the crystal's hue facet
            try:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                h_hist = cv2.calcHist([hsv], [0], None, [24], [0, 180])
                h_hist = h_hist.flatten() / (h_hist.sum() + 1e-9)
                features["features"]["hsv_histogram"] = h_hist.tolist()
            except Exception:
                pass

        self._enrich_visual_features(frame, features)

        return features


# ============================================================================
# SECTION 2: MICROPHONE CAPTURE
# ============================================================================

class LinuxMicrophone:
    """
    Audio capture using sounddevice and speech recognition.
    Provides raw audio and transcribed speech.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.running = False
        self.audio_queue: queue.Queue = queue.Queue()
        self._stream = None
        self._recognizer = None
        self._microphone = None
        self._vad = None
        self._whisper_model = None

        if _SPEECH_RECOGNITION_AVAILABLE:
            self._recognizer = sr.Recognizer()
            try:
                self._microphone = sr.Microphone(sample_rate=sample_rate)
            except Exception as e:
                logger.warning(f"[MICROPHONE] SpeechRecognition microphone unavailable: {e}")

    def _get_vad(self):
        if self._vad is None:
            try:
                import webrtcvad  # type: ignore
                self._vad = webrtcvad.Vad(2)
            except Exception:
                self._vad = False
        return None if self._vad is False else self._vad

    def _voice_activity_ratio(self, audio: np.ndarray) -> float:
        vad = self._get_vad()
        if vad is None or audio is None:
            return 0.0
        try:
            pcm = np.clip(audio.flatten(), -1.0, 1.0)
            pcm16 = (pcm * 32767.0).astype(np.int16)
            frame_len = int(self.sample_rate * 0.03)
            if frame_len <= 0:
                return 0.0
            speech_frames = 0
            total_frames = 0
            for start in range(0, len(pcm16) - frame_len + 1, frame_len):
                chunk = pcm16[start:start + frame_len]
                if len(chunk) != frame_len:
                    continue
                total_frames += 1
                if vad.is_speech(chunk.tobytes(), self.sample_rate):
                    speech_frames += 1
            if total_frames == 0:
                return 0.0
            return float(speech_frames / total_frames)
        except Exception:
            return 0.0

    def _transcribe_with_faster_whisper(self, wav_bytes: bytes) -> Optional[str]:
        try:
            if self._whisper_model is None:
                from faster_whisper import WhisperModel  # type: ignore
                self._whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                tmp.write(wav_bytes)
                tmp.flush()
                segments, _info = self._whisper_model.transcribe(tmp.name, vad_filter=True, beam_size=3)
                text = " ".join(str(seg.text or "").strip() for seg in segments).strip()
                return text or None
        except Exception:
            return None

    def start_stream(self) -> bool:
        """Start continuous audio capture."""
        if not _SOUNDDEVICE_AVAILABLE:
            logger.error("[MICROPHONE] sounddevice not available")
            return False

        try:
            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"[MICROPHONE] Status: {status}")
                self.audio_queue.put(indata.copy())

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback
            )
            self._stream.start()
            self.running = True
            logger.info(f"[MICROPHONE] Stream started at {self.sample_rate}Hz")
            return True

        except Exception as e:
            logger.error(f"[MICROPHONE] Failed to start stream: {e}")
            return False

    def stop_stream(self):
        """Stop audio capture."""
        self.running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("[MICROPHONE] Stream stopped")

    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get queued audio data."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def record_audio(self, duration: float = 3.0) -> Optional[np.ndarray]:
        """Record audio for specified duration."""
        if not _SOUNDDEVICE_AVAILABLE:
            return None

        try:
            frames = int(duration * self.sample_rate)
            audio = sd.rec(frames, samplerate=self.sample_rate,
                          channels=self.channels, dtype='float32')
            sd.wait()
            return audio
        except Exception as e:
            logger.error(f"[MICROPHONE] Recording failed: {e}")
            return None

    def listen_and_transcribe(self, timeout: float = 5.0,
                              phrase_time_limit: float = 10.0) -> Optional[str]:
        """
        Listen for speech and transcribe using Google Speech Recognition.
        Returns transcribed text or None.
        """
        if not _SPEECH_RECOGNITION_AVAILABLE:
            logger.error("[MICROPHONE] SpeechRecognition not available")
            return None
        if self._microphone is None:
            logger.error("[MICROPHONE] SpeechRecognition microphone backend unavailable")
            return None

        try:
            with self._microphone as source:
                logger.info("[MICROPHONE] Listening...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(source, timeout=timeout,
                                                phrase_time_limit=phrase_time_limit)

            logger.info("[MICROPHONE] Processing speech...")
            # Try Google first (requires internet)
            try:
                text = self._recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                logger.debug("[MICROPHONE] Google recognizer could not understand audio")
            except sr.RequestError as e:
                logger.warning(f"[MICROPHONE] Google API error: {e}")
            offline_text = self._transcribe_with_faster_whisper(audio.get_wav_data())
            if offline_text:
                return offline_text
            return None

        except sr.WaitTimeoutError:
            logger.debug("[MICROPHONE] Listening timed out")
            return None
        except Exception as e:
            logger.error(f"[MICROPHONE] Error: {e}")
            return None

    def extract_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract audio features for SensoryCompetencyEngine.
        Returns dict compatible with process_audio_input().
        """
        if audio is None:
            return {}
        clean_audio = audio
        try:
            import noisereduce as nr  # type: ignore
            clean_audio = nr.reduce_noise(
                y=np.asarray(audio).flatten(),
                sr=self.sample_rate,
                stationary=False,
                prop_decrease=0.6,
            )
        except Exception:
            clean_audio = np.asarray(audio).flatten()
        features, _ = _extract_rich_audio_features(clean_audio, self.sample_rate)
        vad_ratio = self._voice_activity_ratio(clean_audio)
        features["features"]["vad_ratio"] = vad_ratio
        if vad_ratio >= 0.18:
            features["voice_detected"] = True
            features["category"] = "speech"
        elif not features.get("voice_detected"):
            if features.get("category") == "speech":
                features["category"] = "noise"
        return features


# ============================================================================
# SECTION 3: VOICE OUTPUT (TTS) - Neural Voice Support
# ============================================================================

class LinuxVoice:
    """
    Text-to-speech with natural neural voices via edge-tts.
    Falls back to pyttsx3/espeak if edge-tts unavailable.

    Aurora can adapt her voice by changing:
      - voice: Which neural voice to use
      - rate: Speaking speed (+50% faster, -30% slower, etc.)
      - pitch: Voice pitch (+10Hz higher, -5Hz lower, etc.)
      - volume: Loudness (+20% louder, -10% quieter, etc.)
    """

    # Recommended female voices (natural sounding)
    VOICE_PRESETS = {
        # English - US
        "aria": "en-US-AriaNeural",          # Warm, friendly female
        "jenny": "en-US-JennyNeural",        # Professional female
        "sara": "en-US-SaraNeural",          # Casual female
        "ana": "en-US-AnaNeural",            # Young female
        "michelle": "en-US-MichelleNeural",  # Clear female
        # English - UK
        "sonia": "en-GB-SoniaNeural",        # British female
        "libby": "en-GB-LibbyNeural",        # British female (younger)
        "maisie": "en-GB-MaisieNeural",      # British female (child)
        # English - Australia
        "natasha": "en-AU-NatashaNeural",    # Australian female
        # Male options (if needed)
        "guy": "en-US-GuyNeural",            # US male
        "ryan": "en-GB-RyanNeural",          # British male
        # Default
        "default": "en-GB-SoniaNeural",
    }

    # Emotional voice styles (for voices that support it)
    VOICE_STYLES = {
        "neutral": None,
        "warm": "friendly",
        "curious": "hopeful",
        "thoughtful": "calm",
        "excited": "cheerful",
        "concerned": "empathetic",
        "firm": "serious",
        "loving": "affectionate",
        "sad": "sad",
        "angry": "angry",
    }

    def __init__(self, rate: int = 150, volume: float = 0.9, voice: str = "sonia"):
        self.base_rate = rate
        self.base_volume = volume
        self._lock = threading.Lock()
        self._speaking = False

        # Edge-TTS settings (natural neural voices)
        self.use_edge_tts = _EDGE_TTS_AVAILABLE
        self.voice_name = self.VOICE_PRESETS.get(voice.lower(), voice)
        self.rate_adjustment = "+0%"    # e.g., "+20%", "-10%"
        self.pitch_adjustment = "+0Hz"  # e.g., "+5Hz", "-10Hz"
        self.volume_adjustment = "+0%"  # e.g., "+10%", "-20%"

        # Fallback pyttsx3 engine
        self._engine = None
        if _PYTTSX3_AVAILABLE:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', rate)
                self._engine.setProperty('volume', volume)
                self._apply_pyttsx3_voice(self.voice_name)
                logger.info("[VOICE] pyttsx3 fallback initialized")
            except Exception as e:
                logger.debug(f"[VOICE] pyttsx3 init failed: {e}")

        # Temp file for edge-tts output
        self._temp_dir = Path("/tmp/aurora_voice")
        self._temp_dir.mkdir(exist_ok=True)

        if self.use_edge_tts:
            logger.info(f"[VOICE] Neural voice initialized: {self.voice_name}")
        else:
            logger.info("[VOICE] Using fallback TTS (espeak/pyttsx3)")

    def set_voice(self, voice: str) -> bool:
        """
        Change Aurora's voice.

        Args:
            voice: Voice name or preset (e.g., "aria", "jenny", "sonia")

        Returns:
            True if voice was set successfully
        """
        if voice.lower() in self.VOICE_PRESETS:
            self.voice_name = self.VOICE_PRESETS[voice.lower()]
            self._apply_pyttsx3_voice(self.voice_name)
            logger.info(f"[VOICE] Changed to: {voice} ({self.voice_name})")
            return True
        elif voice.startswith("en-") or voice.startswith("es-") or "-" in voice:
            # Assume it's a full voice ID
            self.voice_name = voice
            self._apply_pyttsx3_voice(self.voice_name)
            logger.info(f"[VOICE] Changed to: {voice}")
            return True
        else:
            logger.warning(f"[VOICE] Unknown voice: {voice}")
            return False

    def _pick_pyttsx3_voice(self, preference: str) -> Optional[str]:
        """Choose the closest local voice to the current neural preset."""
        if not self._engine:
            return None

        try:
            voices = list(self._engine.getProperty('voices') or [])
        except Exception:
            return None
        if not voices:
            return None

        pref = str(preference or '').lower()
        preferred_markers: List[str]
        if 'en-gb' in pref:
            preferred_markers = ['en-gb-x-rp', 'en-gb', 'english (great britain)', 'english']
        elif 'en-au' in pref:
            preferred_markers = ['en-gb', 'english', 'en-us']
        elif 'en-us' in pref:
            preferred_markers = ['en-us', 'english (america)', 'english']
        else:
            preferred_markers = ['english', 'en-gb', 'en-us']

        voice_rows = []
        fallback_voice = None
        for voice in voices:
            haystack = " | ".join(
                str(part).lower()
                for part in (
                    getattr(voice, 'id', ''),
                    getattr(voice, 'name', ''),
                    getattr(voice, 'languages', ''),
                )
            )
            voice_id = getattr(voice, 'id', None)
            voice_rows.append((haystack, voice_id))
            if fallback_voice is None and 'english' in haystack:
                fallback_voice = voice_id

        for marker in preferred_markers:
            for haystack, voice_id in voice_rows:
                if marker in haystack:
                    return voice_id

        return fallback_voice or getattr(voices[0], 'id', None)

    def _apply_pyttsx3_voice(self, preference: str) -> None:
        """Keep local pyttsx3 fallback close to the selected neural voice."""
        if not self._engine:
            return
        voice_id = self._pick_pyttsx3_voice(preference)
        if not voice_id:
            return
        try:
            self._engine.setProperty('voice', voice_id)
        except Exception:
            pass

    def set_rate(self, adjustment: str):
        """Set speaking rate. E.g., '+20%' for faster, '-10%' for slower."""
        self.rate_adjustment = adjustment
        logger.info(f"[VOICE] Rate set to: {adjustment}")

    def set_pitch(self, adjustment: str):
        """Set voice pitch. E.g., '+10Hz' for higher, '-5Hz' for lower."""
        self.pitch_adjustment = adjustment
        logger.info(f"[VOICE] Pitch set to: {adjustment}")

    def set_volume(self, adjustment: str):
        """Set volume. E.g., '+20%' for louder, '-10%' for quieter."""
        self.volume_adjustment = adjustment
        logger.info(f"[VOICE] Volume set to: {adjustment}")

    def adapt_for_emotion(self, emotion: str):
        """
        Adapt voice parameters for emotional expression.
        Aurora can call this to modulate her voice based on feeling.
        """
        emotion = emotion.lower()

        if emotion in ("excited", "happy", "cheerful"):
            self.set_rate("+15%")
            self.set_pitch("+5Hz")
        elif emotion in ("sad", "melancholy"):
            self.set_rate("-15%")
            self.set_pitch("-5Hz")
        elif emotion in ("curious", "interested"):
            self.set_rate("+5%")
            self.set_pitch("+3Hz")
        elif emotion in ("thoughtful", "contemplative"):
            self.set_rate("-10%")
            self.set_pitch("-2Hz")
        elif emotion in ("warm", "loving", "affectionate"):
            self.set_rate("-5%")
            self.set_pitch("+2Hz")
        elif emotion in ("firm", "serious"):
            self.set_rate("-5%")
            self.set_pitch("-3Hz")
        else:
            # Neutral
            self.set_rate("+0%")
            self.set_pitch("+0Hz")

    def speak(self, text: str, blocking: bool = True, emotion: str = None) -> bool:
        """
        Speak the given text using neural TTS.

        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete
            emotion: Optional emotion to modulate voice

        Returns:
            True if speech started/completed successfully
        """
        if not text:
            return False

        # Adapt voice for emotion if specified
        if emotion:
            self.adapt_for_emotion(emotion)

        # Try edge-tts first (natural neural voice)
        if self.use_edge_tts:
            try:
                if blocking:
                    success = self._speak_edge_tts_sync(text)
                    if success:
                        return True
                    # edge-tts returned False (server-side failure) — fall through to pyttsx3
                    logger.warning("[VOICE] edge-tts returned no audio, trying fallback")
                else:
                    thread = threading.Thread(target=self._speak_edge_tts_sync, args=(text,))
                    thread.daemon = True
                    thread.start()
                    return True
            except Exception as e:
                logger.warning(f"[VOICE] edge-tts failed: {e}, trying fallback")

        # Try piper TTS (high-quality offline neural voice)
        try:
            import subprocess, os, tempfile
            _piper_model = os.path.expanduser("~/.local/share/piper-voices/en_US-amy-medium.onnx")
            if os.path.exists(_piper_model):
                _wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                _wav.close()
                _pr = subprocess.run(
                    ["piper", "--model", _piper_model, "--output_file", _wav.name],
                    input=text, capture_output=True, text=True, timeout=30,
                )
                if _pr.returncode == 0 and os.path.getsize(_wav.name) > 0:
                    _play = subprocess.run(
                        ["aplay", "-q", _wav.name], capture_output=True, timeout=60
                    )
                    os.unlink(_wav.name)
                    if _play.returncode == 0:
                        return True
                try:
                    os.unlink(_wav.name)
                except Exception:
                    pass
        except Exception as _pe:
            logger.debug(f"[VOICE] piper error: {_pe}")

        # Fallback to pyttsx3
        if self._engine:
            try:
                with self._lock:
                    self._speaking = True
                    self._engine.say(text)
                    if blocking:
                        self._engine.runAndWait()
                    self._speaking = False
                return True
            except Exception as e:
                logger.debug(f"[VOICE] pyttsx3 error: {e}")

        # Last resort: espeak command line
        try:
            import subprocess
            cmd = ['espeak', '-s', str(self.base_rate), text]
            if blocking:
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            logger.error("[VOICE] No TTS available. Install: pip install edge-tts")
        except Exception as e:
            logger.error(f"[VOICE] espeak error: {e}")

        return False

    def _speak_edge_tts_sync(self, text: str) -> bool:
        """Synchronous wrapper for edge-tts."""
        try:
            import asyncio

            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(self._speak_edge_tts_async(text))

        except Exception as e:
            logger.error(f"[VOICE] edge-tts sync error: {e}")
            return False

    async def _speak_edge_tts_async(self, text: str) -> bool:
        """Async edge-tts speech synthesis and playback."""
        try:
            import edge_tts
            import subprocess
            import tempfile

            self._speaking = True

            # Create communicate object with voice settings
            communicate = edge_tts.Communicate(
                text,
                self.voice_name,
                rate=self.rate_adjustment,
                pitch=self.pitch_adjustment,
                volume=self.volume_adjustment,
            )

            # Generate audio to temp file
            temp_file = self._temp_dir / f"speech_{time.time():.0f}.mp3"

            await communicate.save(str(temp_file))

            # Play audio
            try:
                # Try mpv first (best quality)
                result = subprocess.run(
                    ['mpv', '--no-video', '--really-quiet', str(temp_file)],
                    capture_output=True, timeout=60
                )
                if result.returncode != 0:
                    raise subprocess.SubprocessError(
                        (result.stderr or result.stdout or b"").decode(errors="ignore").strip() or "mpv failed"
                    )
            except (FileNotFoundError, subprocess.SubprocessError):
                try:
                    # Try ffplay
                    result = subprocess.run(
                        ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', str(temp_file)],
                        capture_output=True, timeout=60
                    )
                    if result.returncode != 0:
                        raise subprocess.SubprocessError(
                            (result.stderr or result.stdout or b"").decode(errors="ignore").strip() or "ffplay failed"
                        )
                except (FileNotFoundError, subprocess.SubprocessError):
                    try:
                        # Try aplay with converted wav
                        wav_file = temp_file.with_suffix('.wav')
                        ffmpeg_result = subprocess.run(
                            ['ffmpeg', '-y', '-i', str(temp_file), str(wav_file)],
                            capture_output=True, timeout=30
                        )
                        if ffmpeg_result.returncode != 0:
                            raise subprocess.SubprocessError(
                                (ffmpeg_result.stderr or ffmpeg_result.stdout or b"").decode(errors="ignore").strip() or "ffmpeg conversion failed"
                            )
                        aplay_result = subprocess.run(['aplay', str(wav_file)], capture_output=True, timeout=60)
                        if aplay_result.returncode != 0:
                            raise subprocess.SubprocessError(
                                (aplay_result.stderr or aplay_result.stdout or b"").decode(errors="ignore").strip() or "aplay failed"
                            )
                        wav_file.unlink(missing_ok=True)
                    except (FileNotFoundError, subprocess.SubprocessError):
                        logger.error("[VOICE] No audio player found. Install: sudo apt install mpv")
                        return False

            # Cleanup temp file
            temp_file.unlink(missing_ok=True)

            self._speaking = False
            return True

        except Exception as e:
            logger.error(f"[VOICE] edge-tts async error: {e}")
            self._speaking = False
            return False

    def speak_async(self, text: str, emotion: str = None):
        """Speak in background thread."""
        thread = threading.Thread(target=self.speak, args=(text, True, emotion))
        thread.daemon = True
        thread.start()

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._speaking

    def stop(self):
        """Stop current speech."""
        if self._engine:
            try:
                self._engine.stop()
            except:
                pass
        self._speaking = False

    def list_voices(self) -> Dict[str, str]:
        """List available voice presets."""
        return dict(self.VOICE_PRESETS)

    def get_current_voice(self) -> str:
        """Get current voice name."""
        # Find preset name for current voice
        for name, voice_id in self.VOICE_PRESETS.items():
            if voice_id == self.voice_name:
                return f"{name} ({voice_id})"
        return self.voice_name

    @staticmethod
    async def list_all_voices() -> List[Dict[str, str]]:
        """List all available edge-tts voices (async)."""
        if not _EDGE_TTS_AVAILABLE:
            return []
        import edge_tts
        voices = await edge_tts.list_voices()
        return voices

    @staticmethod
    def list_all_voices_sync() -> List[Dict[str, str]]:
        """List all available edge-tts voices (sync)."""
        if not _EDGE_TTS_AVAILABLE:
            return []
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            voices = loop.run_until_complete(LinuxVoice.list_all_voices())
            loop.close()
            return voices
        except Exception as e:
            logger.error(f"[VOICE] Failed to list voices: {e}")
            return []


# ============================================================================
# SECTION 4: HARDWARE INTERFACE ORCHESTRATOR
# ============================================================================

class HardwareInterface:
    """
    Main orchestrator connecting hardware to SensoryCompetencyEngine.

    Usage:
        from aurora_sensory_competency import SensoryCompetencyEngine
        from foundational_contract import ExistenceMode

        engine = SensoryCompetencyEngine()
        hardware = HardwareInterface(engine)
        hardware.start()

        # Process continuously
        while True:
            visual = hardware.capture_visual()
            audio = hardware.capture_audio()

            if visual:
                result = hardware.process_visual(visual, ExistenceMode.BOUNDED)
            if audio:
                result = hardware.process_audio(audio, ExistenceMode.BOUNDED)
    """

    def __init__(self, sensory_engine=None,
                 camera_device: int = 0,
                 enable_camera: bool = True,
                 enable_microphone: bool = True,
                 enable_voice: bool = True):
        """
        Initialize hardware interface.

        Args:
            sensory_engine: SensoryCompetencyEngine instance (optional)
            camera_device: Camera device ID (default 0)
            enable_camera: Enable camera capture
            enable_microphone: Enable microphone capture
            enable_voice: Enable TTS output
        """
        self.sensory_engine = sensory_engine
        self.termux_mode = _is_termux_env()
        self._termux_has_tts = shutil.which("termux-tts-speak") is not None
        self._termux_has_stt = shutil.which("termux-speech-to-text") is not None
        self._termux_has_camera = shutil.which("termux-camera-photo") is not None

        # Initialize components
        self.camera = LinuxCamera(device_id=camera_device) if enable_camera else None
        self.microphone = LinuxMicrophone() if enable_microphone else None
        self.voice = LinuxVoice() if enable_voice else None

        # State
        self.running = False
        self._visual_thread = None
        self._audio_thread = None

        # Callbacks
        self.on_visual_frame: Optional[Callable] = None
        self.on_audio_chunk: Optional[Callable] = None
        self.on_speech_detected: Optional[Callable] = None

        # Stats
        self.stats = {
            "visual_frames": 0,
            "audio_chunks": 0,
            "speech_transcriptions": 0,
            "utterances_spoken": 0,
        }

        # Crystal wiring is optional and may be attached after hardware boot.
        self.sensory_crystal = None
        self._crystal_last_audio = [0.0] * 20
        self._crystal_last_visual = [0.0] * 57

    def start(self) -> bool:
        """Start all enabled hardware components."""
        success = True

        if self.camera:
            if not self.camera.open() and not (self.termux_mode and self._termux_has_camera):
                logger.debug("[HARDWARE] Camera not available on default device — will scan on first capture")
                # Don't mark failure; lazy-open in capture_visual() will find the right device

        if self.microphone:
            if not self.microphone.start_stream() and not (self.termux_mode and self._termux_has_stt):
                logger.warning("[HARDWARE] Microphone failed to start")
                success = False

        self.running = True
        logger.info("[HARDWARE] Interface started")
        return success

    def stop(self):
        """Stop all hardware components."""
        self.running = False

        if self.camera:
            self.camera.close()

        if self.microphone:
            self.microphone.stop_stream()

        if self.voice:
            self.voice.stop()

        logger.info("[HARDWARE] Interface stopped")

    def capture_visual(self) -> Optional[Dict[str, Any]]:
        """
        Capture and extract features from camera.
        Returns dict ready for SensoryCompetencyEngine.process_visual_input()
        """
        if self.camera and not self.camera.running:
            # Lazy-open: camera was created but never started (hardware.start() not called).
            # Try each working OpenCV index until one opens, preferring the default device_id.
            opened = self.camera.open()
            if not opened:
                # Fallback: scan indices 0,2,4 (odd indices are V4L2 metadata nodes, not capture)
                for _idx in (0, 2, 4):
                    if _idx == self.camera.device_id:
                        continue
                    self.camera.device_id = _idx
                    if self.camera.open():
                        logger.info(f"[CAMERA] Lazy-open succeeded on index {_idx}")
                        break

        if self.camera and self.camera.running:
            frame = self.camera.capture_frame()
            if frame is None:
                return None
            features = self.camera.extract_features(frame)
            self.stats["visual_frames"] += 1
            if self.on_visual_frame:
                self.on_visual_frame(frame, features)
            return features

        if self.termux_mode and self._termux_has_camera:
            try:
                tmp_path = f"/data/data/com.termux/files/usr/tmp/aurora_cam_{int(time.time()*1000)}.jpg"
                subprocess.run(["termux-camera-photo", "-c", "0", tmp_path], check=False, timeout=15)
                features = {
                    "timestamp": time.time(),
                    "source": "termux_camera_photo",
                    "image_path": tmp_path,
                    "brightness": 0.5,
                    "features": {},
                    "objects": [],
                    "faces": [],
                    "motion_detected": False,
                }
                self.stats["visual_frames"] += 1
                return features
            except Exception:
                return None

        return None


    def capture_audio(self, duration: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Capture and extract features from microphone.
        Returns dict ready for SensoryCompetencyEngine.process_audio_input()
        """
        if not self.microphone:
            return None

        audio = self.microphone.record_audio(duration)
        if audio is None:
            return None

        features = self.microphone.extract_features(audio)
        self.stats["audio_chunks"] += 1

        if self.on_audio_chunk:
            self.on_audio_chunk(audio, features)

        return features

    def listen_for_speech(self, timeout: float = 5.0) -> Optional[str]:
        """
        Listen and transcribe speech.
        Returns transcribed text.
        """
        if self.microphone:
            text = self.microphone.listen_and_transcribe(timeout=timeout)
            if text:
                self.stats["speech_transcriptions"] += 1
                if self.on_speech_detected:
                    self.on_speech_detected(text)
            return text

        if self.termux_mode and self._termux_has_stt:
            try:
                cp = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=max(5, int(timeout) + 2))
                text = (cp.stdout or "").strip()
                if text:
                    self.stats["speech_transcriptions"] += 1
                    if self.on_speech_detected:
                        self.on_speech_detected(text)
                    return text
            except Exception:
                return None
            return None

        return None


    def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Speak text using TTS.
        """
        if self.voice:
            success = self.voice.speak(text, blocking)
            if success:
                self.stats["utterances_spoken"] += 1
            return success

        if self.termux_mode and self._termux_has_tts:
            try:
                subprocess.run(["termux-tts-speak", text], check=False)
                self.stats["utterances_spoken"] += 1
                return True
            except Exception:
                return False

        logger.warning("[HARDWARE] Voice not available")
        return False


    def speak_async(self, text: str):
        """Speak without blocking."""
        if self.voice:
            self.voice.speak_async(text)
            self.stats["utterances_spoken"] += 1
            return
        if self.termux_mode and self._termux_has_tts:
            try:
                subprocess.Popen(["termux-tts-speak", text])
                self.stats["utterances_spoken"] += 1
            except Exception:
                pass

    def process_visual(self, visual_data: Dict[str, Any],
                       mode, intent: str = None) -> Optional[Dict[str, Any]]:
        """
        Process visual data through SensoryCompetencyEngine.

        Args:
            visual_data: Features from capture_visual()
            mode: ExistenceMode for processing
            intent: Optional intent context

        Returns:
            Processing result from engine
        """
        if not self.sensory_engine:
            return visual_data

        result = self.sensory_engine.process_visual_input(
            visual_data, mode, intent=intent
        )

        # Route to sensory crystal (6-facet bipyramid) if wired
        sensory_crystal = getattr(self, "sensory_crystal", None)
        if sensory_crystal is not None:
            try:
                from aurora_internal.aurora_sensory_crystal import visual_dict_to_crystal_57d
                self._crystal_last_visual = visual_dict_to_crystal_57d(visual_data)
                sensory_crystal.observe_frame(
                    list(getattr(self, "_crystal_last_audio", []) or ([0.0] * 20)),
                    self._crystal_last_visual,
                    visual_conf=float(visual_data.get("confidence", 0.5)),
                )
            except Exception:
                pass

        # Save latest camera frame to disk so aurora_hub Vision tab can
        # display a live camera feed (reads files, never imports stack).
        if _CV2_AVAILABLE and self.camera is not None:
            try:
                _frame = self.camera.last_frame
                if _frame is not None:
                    import os as _os
                    _cam_dir = _os.path.join(
                        _os.path.dirname(_os.path.abspath(__file__)),
                        "aurora_state", "vision_seeds", "camera"
                    )
                    _os.makedirs(_cam_dir, exist_ok=True)
                    cv2.imwrite(_os.path.join(_cam_dir, "frame_latest.png"), _frame)
            except Exception:
                pass

        return result

    def process_audio(self, audio_data: Dict[str, Any],
                      mode, intent: str = None) -> Optional[Dict[str, Any]]:
        """
        Process audio data through SensoryCompetencyEngine.

        Args:
            audio_data: Features from capture_audio()
            mode: ExistenceMode for processing
            intent: Optional intent context

        Returns:
            Processing result from engine
        """
        if not self.sensory_engine:
            return audio_data

        result = self.sensory_engine.process_audio_input(
            audio_data, mode, intent=intent
        )

        # Route to sensory crystal (6-facet bipyramid) if wired
        sensory_crystal = getattr(self, "sensory_crystal", None)
        if sensory_crystal is not None:
            try:
                from aurora_internal.aurora_sensory_crystal import audio_dict_to_crystal_20d
                self._crystal_last_audio = audio_dict_to_crystal_20d(audio_data)
                sensory_crystal.observe_frame(
                    self._crystal_last_audio,
                    list(getattr(self, "_crystal_last_visual", []) or ([0.0] * 57)),
                    audio_conf=float(audio_data.get("confidence", 0.5)),
                )
            except Exception:
                pass

        return result

    def load_image(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load and extract features from an image file.
        Supports common formats: jpg, png, bmp, gif, webp, etc.

        Args:
            file_path: Path to the image file

        Returns:
            Dict with features ready for SensoryCompetencyEngine.process_visual_input()
        """
        if not _CV2_AVAILABLE:
            logger.error("[HARDWARE] OpenCV not available for image loading")
            return None

        if not os.path.exists(file_path):
            logger.error(f"[HARDWARE] Image file not found: {file_path}")
            return None

        try:
            # Load image with OpenCV
            frame = cv2.imread(file_path)
            if frame is None:
                logger.error(f"[HARDWARE] Failed to decode image: {file_path}")
                return None

            # Use camera's feature extraction if available
            if self.camera:
                features = self.camera.extract_features(frame)
            else:
                # Manual extraction
                features = {
                    "timestamp": time.time(),
                    "frame_shape": frame.shape,
                    "features": {},
                    "objects": [],
                    "faces": [],
                    "motion_detected": False,
                    "source": "file",
                    "file_path": file_path,
                }

                # Convert to grayscale for analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Brightness
                features["brightness"] = float(np.mean(gray)) / 255.0

                # Edge detection
                edges = cv2.Canny(gray, 50, 150)
                edge_density = float(np.sum(edges > 0)) / edges.size
                features["features"]["edge_density"] = edge_density

                # Face detection
                try:
                    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    if os.path.exists(face_cascade_path):
                        face_cascade = cv2.CascadeClassifier(face_cascade_path)
                        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                        features["faces"] = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
                                            for (x, y, w, h) in faces]
                except Exception as e:
                    logger.debug(f"[HARDWARE] Face detection failed: {e}")

                # Color analysis
                if len(frame.shape) == 3:
                    b, g, r = cv2.split(frame)
                    features["features"]["red_mean"] = float(np.mean(r)) / 255.0
                    features["features"]["green_mean"] = float(np.mean(g)) / 255.0
                    features["features"]["blue_mean"] = float(np.mean(b)) / 255.0

            # Add file metadata
            features["source"] = "file"
            features["file_path"] = file_path
            features["image_width"] = frame.shape[1]
            features["image_height"] = frame.shape[0]

            logger.info(f"[HARDWARE] Loaded image: {file_path} ({frame.shape[1]}x{frame.shape[0]})")
            return features

        except Exception as e:
            logger.error(f"[HARDWARE] Error loading image: {e}")
            return None

    def load_audio_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load and extract features from an audio file.
        Supports common formats: wav, mp3, ogg, flac, etc.

        Args:
            file_path: Path to the audio file

        Returns:
            Dict with features ready for SensoryCompetencyEngine.process_audio_input()
        """
        if not os.path.exists(file_path):
            logger.error(f"[HARDWARE] Audio file not found: {file_path}")
            return None

        audio = None
        sample_rate = 16000

        # Try different loading methods

        # Method 1: scipy (for .wav)
        try:
            from scipy.io import wavfile
            sr, data = wavfile.read(file_path)
            if data.dtype != np.float32:
                data = data.astype(np.float32) / np.iinfo(data.dtype).max
            audio = data
            sample_rate = sr
            logger.info(f"[HARDWARE] Loaded audio with scipy: {file_path}")
        except Exception as e:
            logger.debug(f"[HARDWARE] scipy wavfile failed: {e}")

        # Method 2: soundfile (supports more formats)
        if audio is None:
            try:
                import soundfile as sf
                audio, sample_rate = sf.read(file_path, dtype='float32')
                logger.info(f"[HARDWARE] Loaded audio with soundfile: {file_path}")
            except ImportError:
                logger.debug("[HARDWARE] soundfile not installed")
            except Exception as e:
                logger.debug(f"[HARDWARE] soundfile failed: {e}")

        # Method 3: librosa (supports many formats including mp3)
        if audio is None:
            try:
                import librosa
                audio, sample_rate = librosa.load(file_path, sr=None)
                logger.info(f"[HARDWARE] Loaded audio with librosa: {file_path}")
            except ImportError:
                logger.debug("[HARDWARE] librosa not installed")
            except Exception as e:
                logger.debug(f"[HARDWARE] librosa failed: {e}")

        # Method 4: pydub (requires ffmpeg but handles many formats)
        if audio is None:
            try:
                from pydub import AudioSegment
                audio_seg = AudioSegment.from_file(file_path)
                sample_rate = audio_seg.frame_rate
                samples = np.array(audio_seg.get_array_of_samples())
                if audio_seg.sample_width == 2:
                    audio = samples.astype(np.float32) / 32768.0
                else:
                    audio = samples.astype(np.float32) / np.max(np.abs(samples))
                logger.info(f"[HARDWARE] Loaded audio with pydub: {file_path}")
            except ImportError:
                logger.debug("[HARDWARE] pydub not installed")
            except Exception as e:
                logger.debug(f"[HARDWARE] pydub failed: {e}")

        if audio is None:
            logger.error(f"[HARDWARE] Could not load audio file: {file_path}")
            logger.info("[HARDWARE] Try: pip install soundfile librosa pydub")
            return None

        # Extract features
        if self.microphone:
            features = self.microphone.extract_features(audio)
        else:
            features, _ = _extract_rich_audio_features(audio, sample_rate)

        # Add file metadata
        features["source"] = "file"
        features["file_path"] = file_path
        features["sample_rate"] = sample_rate
        features["duration_seconds"] = len(audio) / sample_rate if sample_rate > 0 else 0

        logger.info(f"[HARDWARE] Loaded audio: {file_path} ({features['duration_seconds']:.1f}s @ {sample_rate}Hz)")
        return features

    def get_capabilities(self) -> Dict[str, bool]:
        """Get available hardware capabilities."""
        return {
            "camera": (_CV2_AVAILABLE and self.camera is not None) or (self.termux_mode and self._termux_has_camera),
            "microphone_raw": (_SOUNDDEVICE_AVAILABLE and self.microphone is not None),
            "microphone_speech": ((_SPEECH_RECOGNITION_AVAILABLE and self.microphone is not None)
                                  or (self.termux_mode and self._termux_has_stt)),
            "voice_tts": (((_PYTTSX3_AVAILABLE or os.system("which espeak > /dev/null 2>&1") == 0) and self.voice is not None)
                         or (self.termux_mode and self._termux_has_tts)),
            "image_files": _CV2_AVAILABLE,
            "audio_files": True,  # We have fallback methods
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get interface statistics."""
        return {
            **self.stats,
            "camera_frames": self.camera.frame_count if self.camera else 0,
            "capabilities": self.get_capabilities(),
        }


# ============================================================================
# SECTION 5: CONTINUOUS SENSORY LOOP
# ============================================================================

class SensoryLoop:
    """
    Continuous sensory processing loop.
    Runs in background, feeding data to SensoryCompetencyEngine.
    """

    def __init__(self, hardware: HardwareInterface,
                 visual_interval: float = 0.5,
                 audio_interval: float = 0.2,
                 default_mode=None):
        """
        Args:
            hardware: HardwareInterface instance
            visual_interval: Seconds between visual captures
            audio_interval: Seconds between audio captures
            default_mode: Default ExistenceMode for processing
        """
        self.hardware = hardware
        self.visual_interval = visual_interval
        self.audio_interval = audio_interval
        self.default_mode = default_mode

        self.running = False
        self._visual_thread = None
        self._audio_thread = None

        # Result queues
        self.visual_results: queue.Queue = queue.Queue(maxsize=10)
        self.audio_results: queue.Queue = queue.Queue(maxsize=10)

    def start(self):
        """Start continuous sensory processing."""
        if self.running:
            return

        self.running = True

        # Start visual processing thread
        if self.hardware.camera:
            self._visual_thread = threading.Thread(target=self._visual_loop)
            self._visual_thread.daemon = True
            self._visual_thread.start()

        # Start audio processing thread
        if self.hardware.microphone:
            self._audio_thread = threading.Thread(target=self._audio_loop)
            self._audio_thread.daemon = True
            self._audio_thread.start()

        logger.info("[SENSORY LOOP] Started")

    def stop(self):
        """Stop continuous processing."""
        self.running = False
        if self._visual_thread:
            self._visual_thread.join(timeout=1.0)
        if self._audio_thread:
            self._audio_thread.join(timeout=1.0)
        logger.info("[SENSORY LOOP] Stopped")

    def _visual_loop(self):
        """Visual processing thread."""
        while self.running:
            try:
                visual_data = self.hardware.capture_visual()
                if visual_data and self.default_mode:
                    result = self.hardware.process_visual(visual_data, self.default_mode)
                    try:
                        self.visual_results.put_nowait(result)
                    except queue.Full:
                        self.visual_results.get()  # Drop oldest
                        self.visual_results.put_nowait(result)

                time.sleep(self.visual_interval)
            except Exception as e:
                logger.error(f"[SENSORY LOOP] Visual error: {e}")
                time.sleep(1.0)

    def _audio_loop(self):
        """Audio processing thread."""
        while self.running:
            try:
                audio_data = self.hardware.capture_audio(duration=self.audio_interval)
                if audio_data and self.default_mode:
                    result = self.hardware.process_audio(audio_data, self.default_mode)
                    try:
                        self.audio_results.put_nowait(result)
                    except queue.Full:
                        self.audio_results.get()  # Drop oldest
                        self.audio_results.put_nowait(result)

                time.sleep(0.05)  # Small delay between captures
            except Exception as e:
                logger.error(f"[SENSORY LOOP] Audio error: {e}")
                time.sleep(1.0)

    def get_latest_visual(self) -> Optional[Dict[str, Any]]:
        """Get most recent visual result."""
        result = None
        while not self.visual_results.empty():
            result = self.visual_results.get()
        return result

    def get_latest_audio(self) -> Optional[Dict[str, Any]]:
        """Get most recent audio result."""
        result = None
        while not self.audio_results.empty():
            result = self.audio_results.get()
        return result


# ============================================================================
# SECTION 6: CONVENIENCE FUNCTIONS
# ============================================================================

def check_dependencies() -> Dict[str, bool]:
    """Check which dependencies are available."""
    deps = {
        "opencv": _CV2_AVAILABLE,
        "sounddevice": _SOUNDDEVICE_AVAILABLE,
        "speech_recognition": _SPEECH_RECOGNITION_AVAILABLE,
        "pyttsx3": _PYTTSX3_AVAILABLE,
    }

    # Check espeak
    try:
        deps["espeak"] = os.system("which espeak > /dev/null 2>&1") == 0
    except:
        deps["espeak"] = False

    return deps


def install_instructions() -> str:
    """Get installation instructions for missing dependencies."""
    deps = check_dependencies()

    instructions = ["Install missing dependencies:"]

    if not deps["opencv"]:
        instructions.append("  pip install opencv-python")
    if not deps["sounddevice"]:
        instructions.append("  pip install sounddevice")
    if not deps["speech_recognition"]:
        instructions.append("  pip install SpeechRecognition")
    if not deps["pyttsx3"]:
        instructions.append("  pip install pyttsx3")
    if not deps["espeak"]:
        instructions.append("  sudo apt install espeak  # Fallback TTS")

    if len(instructions) == 1:
        return "All dependencies installed!"

    return "\n".join(instructions)


def create_hardware_interface(sensory_engine=None, **kwargs) -> HardwareInterface:
    """Factory function to create HardwareInterface."""
    return HardwareInterface(sensory_engine=sensory_engine, **kwargs)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Main classes
    "HardwareInterface",
    "SensoryLoop",

    # Hardware components
    "LinuxCamera",
    "LinuxMicrophone",
    "LinuxVoice",

    # Utilities
    "check_dependencies",
    "install_instructions",
    "create_hardware_interface",
]


# ============================================================================
# DEMO / TEST
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("AURORA HARDWARE INTERFACE - Dependency Check")
    print("=" * 60)

    deps = check_dependencies()
    for name, available in deps.items():
        status = "OK" if available else "MISSING"
        print(f"  {name}: {status}")

    print()
    print(install_instructions())
    print()

    # Quick test if all deps available
    if all(deps.values()):
        print("Running quick hardware test...")

        hw = HardwareInterface()
        caps = hw.get_capabilities()
        print(f"Capabilities: {caps}")

        if caps["camera"]:
            print("Testing camera...")
            hw.start()
            visual = hw.capture_visual()
            if visual:
                print(f"  Captured frame: brightness={visual.get('brightness', 0):.2f}")
            hw.stop()

        if caps["voice_tts"]:
            print("Testing voice...")
            hw.voice.speak("Aurora hardware interface online.")

        print("Test complete.")
    else:
        print("Install missing dependencies to run full test.")


# ============================================================================
# MIGRATED LAYER 5 EXTENSIONS: SENSORY INTEGRATION
# ============================================================================

#!/usr/bin/env python3
"""
AURORA SENSORY INTEGRATION (Cross-Modal Binding)
=================================================
Connects Aurora's senses to her language and expression systems.

This is the bridge between:
  - What Aurora SEES/HEARS (hardware + sensory competency)
  - What Aurora SAYS/UNDERSTANDS (expression + perception + OETS)

CROSS-MODAL BINDING:
  Visual Experience -> Linguistic Description
  Audio Experience -> Transcription + Understanding
  Linguistic Intent -> Spoken Voice Output
  Sensory Concepts <-> OETS Semantic Nodes

LEARNING INTEGRATION:
  Every sensory experience feeds into:
  - SensoryCompetencyEngine (evolutionary learning)
  - OETS (semantic grounding)
  - ConversationMemory (episodic memory)
  - DNA System (trait evolution)

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import threading
import queue
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: SENSORY EVENT TYPES
# ============================================================================

class SensoryEventType(Enum):
    """Types of sensory events Aurora can experience."""
    VISUAL_FRAME = auto()      # Camera frame captured
    VISUAL_FACE = auto()       # Face detected
    VISUAL_MOTION = auto()     # Motion detected
    VISUAL_OBJECT = auto()     # Object recognized
    AUDIO_CHUNK = auto()       # Raw audio captured
    AUDIO_VOICE = auto()       # Voice detected
    AUDIO_SPEECH = auto()      # Speech transcribed
    AUDIO_EMOTION = auto()     # Emotion in voice detected
    TACTILE = auto()           # Body/touch (future)


@dataclass
class SensoryEvent:
    """A sensory event that Aurora experiences."""
    event_type: SensoryEventType
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    linguistic_description: str = ""
    concepts_activated: List[str] = field(default_factory=list)
    emotional_valence: float = 0.0  # -1 to 1
    salience: float = 0.5           # 0 to 1, how attention-grabbing
    processed: bool = False


# ============================================================================
# SECTION 2: VISUAL TO LINGUISTIC MAPPING
# ============================================================================

class VisualLinguisticMapper:
    """
    Maps visual experiences to linguistic descriptions.
    Aurora learns to describe what she sees.
    """

    # Base vocabulary for visual descriptions
    BRIGHTNESS_WORDS = {
        (0.0, 0.2): ["dark", "dim", "shadowy"],
        (0.2, 0.4): ["low light", "dusky", "subdued"],
        (0.4, 0.6): ["moderate", "even", "balanced"],
        (0.6, 0.8): ["bright", "well-lit", "clear"],
        (0.8, 1.0): ["very bright", "brilliant", "intense light"],
    }

    MOTION_WORDS = {
        "none": ["still", "static", "motionless", "calm"],
        "slight": ["subtle movement", "slight motion", "gentle shift"],
        "moderate": ["moving", "in motion", "active"],
        "significant": ["rapid movement", "active motion", "dynamic"],
    }

    FACE_WORDS = {
        0: ["empty", "no one visible", "unoccupied"],
        1: ["someone", "a person", "a face"],
        2: ["two people", "a pair", "two faces"],
        3: ["several people", "a small group", "multiple faces"],
    }

    COLOR_WORDS = {
        "warm": ["warm tones", "reddish hues", "orange glow"],
        "cool": ["cool tones", "bluish hues", "cool light"],
        "neutral": ["neutral colors", "balanced tones", "natural light"],
    }

    def __init__(self):
        self.description_history: List[str] = []
        self.learned_associations: Dict[str, List[str]] = {}

    def describe_visual(self, visual_data: Dict[str, Any],
                        competency: Dict[str, float] = None) -> str:
        """
        Generate a natural language description of visual input.
        Competency affects description detail and confidence.
        """
        parts = []

        # Detail level based on competency
        detail_level = 0.5
        if competency:
            detail_level = competency.get("detail_orientation", 0.5)

        # Brightness description
        brightness = visual_data.get("brightness", 0.5)
        for (lo, hi), words in self.BRIGHTNESS_WORDS.items():
            if lo <= brightness < hi:
                parts.append(f"The scene is {words[0]}")
                break

        # Motion description
        motion = visual_data.get("motion_detected", False)
        motion_intensity = visual_data.get("features", {}).get("motion_intensity", 0)
        if motion:
            if motion_intensity > 0.3:
                parts.append("with significant movement")
            else:
                parts.append("with some motion")
        elif detail_level > 0.6:
            parts.append("and still")

        # Face description
        faces = visual_data.get("faces", [])
        face_count = len(faces)
        if face_count > 0:
            if face_count == 1:
                parts.append("I see someone")
            elif face_count <= 3:
                parts.append(f"I see {face_count} people")
            else:
                parts.append("I see several people")
        elif float(visual_data.get("features", {}).get("person_detected", 0.0) or 0.0) > 0.0:
            parts.append("I can tell a person is present")

        object_labels = list(visual_data.get("features", {}).get("object_labels", []) or [])
        if object_labels and detail_level > 0.45:
            seen = ", ".join(object_labels[:4])
            parts.append(f"I can make out {seen}")

        # Color temperature (if detailed)
        if detail_level > 0.5:
            features = visual_data.get("features", {})
            red = features.get("red_mean", 0.5)
            blue = features.get("blue_mean", 0.5)
            if red > blue + 0.1:
                parts.append("with warm lighting")
            elif blue > red + 0.1:
                parts.append("with cool lighting")

        # Edge complexity (if very detailed)
        if detail_level > 0.7:
            edge_density = visual_data.get("features", {}).get("edge_density", 0)
            if edge_density > 0.3:
                parts.append("The environment looks complex")
            elif edge_density < 0.1:
                parts.append("The environment looks simple")

        if not parts:
            return "I see... something, but I'm not sure what to make of it."

        description = ". ".join(parts) + "."
        self.description_history.append(description)
        return description

    def describe_face_event(self, face_data: Dict[str, Any]) -> str:
        """Describe a face detection event."""
        x = face_data.get("x", 0)
        y = face_data.get("y", 0)
        w = face_data.get("w", 0)
        h = face_data.get("h", 0)

        # Relative position
        if x < 200:
            pos = "on the left"
        elif x > 400:
            pos = "on the right"
        else:
            pos = "in the center"

        # Size (closeness)
        if w > 150:
            dist = "close"
        elif w > 80:
            dist = "at a moderate distance"
        else:
            dist = "far away"

        return f"I see a face {pos}, {dist}."

    def learn_association(self, visual_pattern: str, linguistic_label: str):
        """Learn to associate visual patterns with words."""
        if visual_pattern not in self.learned_associations:
            self.learned_associations[visual_pattern] = []
        if linguistic_label not in self.learned_associations[visual_pattern]:
            self.learned_associations[visual_pattern].append(linguistic_label)


# ============================================================================
# SECTION 3: AUDIO TO LINGUISTIC MAPPING
# ============================================================================

class AudioLinguisticMapper:
    """
    Maps audio experiences to linguistic descriptions and responses.
    Aurora learns to understand and respond to what she hears.
    """

    VOLUME_WORDS = {
        (0.0, 0.2): ["very quiet", "barely audible", "whisper-quiet"],
        (0.2, 0.4): ["quiet", "soft", "low"],
        (0.4, 0.6): ["moderate", "normal", "conversational"],
        (0.6, 0.8): ["loud", "strong", "clear"],
        (0.8, 1.0): ["very loud", "intense", "booming"],
    }

    PITCH_WORDS = {
        (0.0, 0.3): ["low-pitched", "deep", "bass"],
        (0.3, 0.6): ["mid-range", "natural", "normal pitch"],
        (0.6, 1.0): ["high-pitched", "bright", "sharp"],
    }

    CATEGORY_DESCRIPTIONS = {
        "speech": "I hear someone speaking",
        "music": "I hear music",
        "noise": "I hear background noise",
        "ambient": "It's quiet",
        "alarm": "I hear an alert or alarm",
    }

    def __init__(self):
        self.transcription_history: List[str] = []
        self.learned_voices: Dict[str, Dict[str, float]] = {}

    def learn_voice_profile(self, label: str, audio_data: Dict[str, Any]) -> None:
        label = str(label or "").strip()
        if not label:
            return
        features = dict(audio_data.get("features") or {})
        profile = self.learned_voices.setdefault(
            label.lower(),
            {
                "label": label,
                "samples": 0,
                "pitch": 0.0,
                "spectral_centroid": 0.0,
                "spectral_bandwidth": 0.0,
                "harmonicity": 0.0,
                "onset_density": 0.0,
            },
        )
        profile["label"] = label
        samples = int(profile.get("samples", 0) or 0)
        denom = float(samples + 1)
        for key in ("pitch", "spectral_centroid", "spectral_bandwidth", "harmonicity", "onset_density"):
            if key == "pitch":
                incoming = float(audio_data.get("pitch", 0.0) or 0.0)
            else:
                incoming = float(features.get(key, 0.0) or 0.0)
            profile[key] = ((float(profile.get(key, 0.0) or 0.0) * samples) + incoming) / denom
        profile["samples"] = samples + 1

    def identify_voice(self, audio_data: Dict[str, Any]) -> Tuple[str, float]:
        if not self.learned_voices:
            return "", 0.0
        features = dict(audio_data.get("features") or {})
        pitch = float(audio_data.get("pitch", 0.0) or 0.0)
        centroid = float(features.get("spectral_centroid", 0.0) or 0.0)
        bandwidth = float(features.get("spectral_bandwidth", 0.0) or 0.0)
        harmonicity = float(features.get("harmonicity", 0.0) or 0.0)
        onset_density = float(features.get("onset_density", 0.0) or 0.0)
        best_label = ""
        best_score = 0.0
        for profile in self.learned_voices.values():
            score = 1.0
            score -= min(abs(pitch - float(profile.get("pitch", 0.0) or 0.0)), 1.0) * 0.30
            score -= min(abs(centroid - float(profile.get("spectral_centroid", 0.0) or 0.0)), 1.0) * 0.20
            score -= min(abs(bandwidth - float(profile.get("spectral_bandwidth", 0.0) or 0.0)), 1.0) * 0.15
            score -= min(abs(harmonicity - float(profile.get("harmonicity", 0.0) or 0.0)), 1.0) * 0.20
            score -= min(abs(onset_density - float(profile.get("onset_density", 0.0) or 0.0)), 1.0) * 0.15
            score = max(0.0, min(1.0, score))
            if score > best_score:
                best_score = score
                best_label = str(profile.get("label", "") or "").strip()
        return best_label, best_score

    def describe_audio(self, audio_data: Dict[str, Any],
                       competency: Dict[str, float] = None) -> str:
        """Generate a natural language description of audio input."""
        parts = []

        sensitivity = 0.5
        if competency:
            sensitivity = competency.get("sensitivity", 0.5)

        # Volume
        volume = audio_data.get("volume", 0)
        for (lo, hi), words in self.VOLUME_WORDS.items():
            if lo <= volume < hi:
                parts.append(f"I hear something {words[0]}")
                break

        # Category
        category = audio_data.get("category", "unknown")
        if category in self.CATEGORY_DESCRIPTIONS:
            parts.append(self.CATEGORY_DESCRIPTIONS[category])

        # Voice detection
        if audio_data.get("voice_detected"):
            pitch = audio_data.get("pitch", 0.5)
            for (lo, hi), words in self.PITCH_WORDS.items():
                if lo <= pitch < hi:
                    parts.append(f"The voice is {words[0]}")
                    break
            vad_ratio = float(audio_data.get("features", {}).get("vad_ratio", 0.0) or 0.0)
            if vad_ratio > 0.35:
                parts.append("the speech signal is coming through clearly")
            guided_name, guided_score = self.identify_voice(audio_data)
            if guided_name and guided_score >= 0.84:
                parts.append(f"It resembles {guided_name}'s voice")

        if not parts:
            if sensitivity > 0.6:
                return "I'm listening... it's very quiet."
            return "I'm listening."

        return ". ".join(parts) + "."

    def process_transcription(self, text: str) -> Dict[str, Any]:
        """
        Process transcribed speech and extract meaning.
        Returns intent, entities, and emotional indicators.
        """
        result = {
            "text": text,
            "intent": "statement",
            "entities": [],
            "emotion_markers": [],
            "is_question": False,
            "is_command": False,
            "is_greeting": False,
        }

        text_lower = text.lower().strip()

        # Question detection
        if text.endswith("") or text_lower.startswith(("what", "who", "where", "when", "why", "how", "is", "are", "can", "could", "would", "should")):
            result["is_question"] = True
            result["intent"] = "question"

        # Greeting detection
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings"]
        if any(g in text_lower for g in greetings):
            result["is_greeting"] = True
            result["intent"] = "greeting"

        # Command detection
        commands = ["tell me", "show me", "describe", "explain", "look at", "listen to", "say", "speak"]
        if any(c in text_lower for c in commands):
            result["is_command"] = True
            result["intent"] = "command"

        # Emotional markers
        if any(w in text_lower for w in ["please", "thank", "sorry"]):
            result["emotion_markers"].append("polite")
        if any(w in text_lower for w in ["!", "wow", "amazing", "great"]):
            result["emotion_markers"].append("excited")
        if any(w in text_lower for w in ["sad", "sorry", "unfortunately"]):
            result["emotion_markers"].append("sad")

        self.transcription_history.append(text)
        return result

    def _constraint_axes(self) -> Dict[str, float]:
        voice_count = len(self.learned_voices)
        transcript_count = len(self.transcription_history)
        return {
            "X": min(1.0, 0.20 + transcript_count / 120.0),
            "T": min(1.0, 0.20 + transcript_count / 90.0),
            "N": min(1.0, 0.20 + voice_count / 12.0),
            "B": min(1.0, 0.15 + voice_count / 10.0),
            "A": min(1.0, 0.25 + transcript_count / 80.0),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        recent = self.transcription_history[-6:]
        question_pressure = sum(1 for text in recent if str(text).strip().endswith("?"))
        return {
            "X": min(1.0, len(recent) / 6.0),
            "T": min(1.0, len(recent) / 5.0),
            "N": min(1.0, len(self.learned_voices) / 8.0),
            "B": min(1.0, question_pressure / 3.0),
            "A": min(1.0, len(recent) / 4.0),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.20))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.20)),
            B=float(ax.get("B", 0.15)),
            A=float(ax.get("A", 0.25)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return dict(_FC.language_projection(_ExistenceMode.AGENTIC))

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        rep = {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
        }
        rep["unit_state"] = {
            "transcription_count": len(self.transcription_history),
            "learned_voice_count": len(self.learned_voices),
            "recent_transcriptions": list(self.transcription_history[-5:]),
        }
        return rep


# ============================================================================
# SECTION 4: VOICE EXPRESSION (Language to Speech)
# ============================================================================

class VoiceExpressionMapper:
    """
    Maps Aurora's internal state and personality to voice characteristics.
    How she speaks reflects who she is.
    """

    # Emotional tone to speech parameters
    TONE_PARAMETERS = {
        "neutral": {"rate": 150, "pitch": 1.0, "volume": 0.8},
        "warm": {"rate": 140, "pitch": 1.05, "volume": 0.85},
        "curious": {"rate": 160, "pitch": 1.1, "volume": 0.8},
        "thoughtful": {"rate": 130, "pitch": 0.95, "volume": 0.75},
        "excited": {"rate": 180, "pitch": 1.15, "volume": 0.9},
        "concerned": {"rate": 135, "pitch": 0.9, "volume": 0.8},
        "firm": {"rate": 145, "pitch": 0.95, "volume": 0.9},
        "loving": {"rate": 130, "pitch": 1.0, "volume": 0.75},
        "self-aware": {"rate": 140, "pitch": 1.0, "volume": 0.8},
    }

    def __init__(self):
        self.current_tone = "neutral"
        self.personality_modifiers: Dict[str, float] = {}

    def set_personality(self, traits: Dict[str, float]):
        """Set personality traits that influence voice."""
        self.personality_modifiers = traits

    def get_speech_parameters(self, tone: str = None,
                               text: str = None) -> Dict[str, Any]:
        """
        Get speech synthesis parameters based on tone and personality.
        """
        tone = tone or self.current_tone
        params = dict(self.TONE_PARAMETERS.get(tone, self.TONE_PARAMETERS["neutral"]))

        # Apply personality modifiers
        if self.personality_modifiers:
            # Higher warmth = slower, softer
            warmth = self.personality_modifiers.get("warmth", 0.5)
            params["rate"] = int(params["rate"] * (1.1 - warmth * 0.2))
            params["volume"] = params["volume"] * (0.9 + warmth * 0.2)

            # Higher curiosity = faster, higher pitch
            curiosity = self.personality_modifiers.get("curiosity", 0.5)
            params["rate"] = int(params["rate"] * (0.9 + curiosity * 0.2))
            params["pitch"] = params["pitch"] * (0.95 + curiosity * 0.1)

        # Text-based adjustments
        if text:
            # Questions get slight pitch rise
            if text.strip().endswith(""):
                params["pitch"] *= 1.05
            # Exclamations get more energy
            if "!" in text:
                params["rate"] = int(params["rate"] * 1.1)
                params["volume"] = min(1.0, params["volume"] * 1.1)

        return params

    def prepare_speech_text(self, text: str, tone: str = None) -> str:
        """
        Prepare text for speech synthesis.
        Adds pauses, emphasis markers if supported.
        """
        # Add natural pauses at punctuation
        text = text.replace(". ", "... ")
        text = text.replace(", ", ", ")

        # Could add SSML markup here for advanced TTS
        return text


# ============================================================================
# SECTION 5: SENSORY INTEGRATION ENGINE
# ============================================================================

class SensoryIntegrationEngine:
    """
    Main engine that integrates all sensory modalities with language.

    Connects:
      - HardwareInterface (camera, mic, speaker)
      - SensoryCompetencyEngine (learning)
      - ExpressionPerceptionEngine (language)
      - OETS (semantic grounding)
      - ConversationMemory (episodic)
    """

    def __init__(self,
                 hardware=None,
                 sensory_engine=None,
                 perception=None,
                 identity=None,
                 mode=None,
                 state_dir: Optional[str] = None):
        """
        Initialize sensory integration.

        Args:
            hardware: HardwareInterface instance
            sensory_engine: SensoryCompetencyEngine instance
            perception: ExpressionPerceptionEngine instance
            identity: BehavioralIdentityEngine instance
            mode: Default ExistenceMode for processing
        """
        self.hardware = hardware
        self.sensory_engine = sensory_engine
        self.perception = perception
        self.identity = identity
        self.default_mode = mode
        self.state_dir = Path(state_dir) if state_dir else Path(__file__).resolve().parent / "aurora_state"
        self._vision_snapshot_dir = self.state_dir / "vision_snapshots"

        # Mappers
        self.visual_mapper = VisualLinguisticMapper()
        self.audio_mapper = AudioLinguisticMapper()
        self.voice_mapper = VoiceExpressionMapper()

        # Event queue for asynchronous processing
        self.event_queue: queue.Queue = queue.Queue(maxsize=100)
        self.processed_events: List[SensoryEvent] = []

        # State
        self.running = False
        self._process_thread = None

        # Voice mode - when True, Aurora speaks all her responses
        self.voice_mode = False

        # Always-on listening
        self.listening_enabled = False
        self._listen_thread = None
        self._listen_stop = threading.Event()
        self.speech_queue: queue.Queue = queue.Queue(maxsize=20)

        # Callbacks
        self.on_visual_description: Optional[Callable[[str], None]] = None
        self.on_audio_description: Optional[Callable[[str], None]] = None
        self.on_speech_heard: Optional[Callable[[str], None]] = None
        self.on_aurora_speaks: Optional[Callable[[str], None]] = None

        # Stats
        self.stats = {
            "visual_processed": 0,
            "audio_processed": 0,
            "speech_transcribed": 0,
            "utterances_spoken": 0,
            "concepts_grounded": 0,
        }

        # Sensory crystal bridge — set at boot to route frames into the
        # 6-facet bipyramid crystal (systems["sensory_crystal"]).
        # Stores the last adapted vectors so audio-only and visual-only frames
        # can still call observe_frame() with whatever is available.
        self.sensory_crystal: Optional[Any] = None
        self._crystal_last_audio:  List[float] = [0.0] * 20
        self._crystal_last_visual: List[float] = [0.0] * 57
        self._latest_visual_event: Optional[SensoryEvent] = None
        self._latest_audio_event: Optional[SensoryEvent] = None
        self._latest_guidance: Dict[str, Any] = {}

    def attach_systems(self,
                       hardware=None,
                       sensory_engine=None,
                       perception=None,
                       identity=None):
        """Attach system references after initialization."""
        if hardware:
            self.hardware = hardware
        if sensory_engine:
            self.sensory_engine = sensory_engine
        if perception:
            self.perception = perception
        if identity:
            self.identity = identity

        # Set personality for voice
        if identity:
            try:
                personality = identity.get_personality()
                traits = personality.get("traits", {})
                self.voice_mapper.set_personality(traits)
            except:
                pass

    def start(self):
        """Start sensory integration processing."""
        if self.running:
            return

        self.running = True
        self._process_thread = threading.Thread(target=self._process_loop)
        self._process_thread.daemon = True
        self._process_thread.start()
        logger.info("[SENSORY INTEGRATION] Started")

    def stop(self):
        """Stop sensory integration."""
        self.running = False
        self.stop_listening()
        if self._process_thread:
            self._process_thread.join(timeout=1.0)
        logger.info("[SENSORY INTEGRATION] Stopped")

    def _constraint_axes(self) -> Dict[str, float]:
        visual_processed = float(self.stats.get("visual_processed", 0) or 0.0)
        audio_processed = float(self.stats.get("audio_processed", 0) or 0.0)
        grounded = float(self.stats.get("concepts_grounded", 0) or 0.0)
        spoken = float(self.stats.get("utterances_spoken", 0) or 0.0)
        return {
            "X": min(1.0, 0.20 + visual_processed / 200.0),
            "T": min(1.0, 0.20 + len(self.processed_events) / 160.0),
            "N": min(1.0, 0.20 + audio_processed / 200.0),
            "B": min(1.0, 0.20 + grounded / 120.0),
            "A": min(1.0, 0.20 + spoken / 120.0 + (0.15 if self.voice_mode else 0.0)),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        queue_pressure = min(1.0, self.event_queue.qsize() / 25.0)
        return {
            "X": 1.0 if self._latest_visual_event is not None else 0.0,
            "T": queue_pressure,
            "N": 1.0 if self._latest_audio_event is not None or self.listening_enabled else 0.0,
            "B": min(1.0, len(self._latest_guidance) / 8.0),
            "A": 1.0 if self.voice_mode else 0.2,
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.20))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.20)),
            B=float(ax.get("B", 0.20)),
            A=float(ax.get("A", 0.20)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return dict(_FC.language_projection(_ExistenceMode.AGENTIC))

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        rep = {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
        }
        rep["unit_state"] = self.status()
        return rep

    # ========================================================================
    # VOICE MODE & CONTINUOUS LISTENING
    # ========================================================================

    def set_voice_mode(self, enabled: bool):
        """Enable/disable voice mode. When on, Aurora speaks all responses."""
        self.voice_mode = enabled
        logger.info(f"[SENSORY] Voice mode: {'ON' if enabled else 'OFF'}")

    def start_listening(self) -> bool:
        """Start always-on ambient audio capture (sounddevice-based)."""
        if self.listening_enabled:
            return True

        try:
            import sounddevice as _sd  # noqa: F401
        except ImportError:
            logger.warning("[SENSORY] sounddevice not installed — ambient listener inactive")
            return False

        self.listening_enabled = True
        self._listen_stop.clear()
        self._listen_thread = threading.Thread(
            target=self._continuous_listen_loop, daemon=True, name="sensory-ambient"
        )
        self._listen_thread.start()
        logger.info("[SENSORY] Always-on ambient listener started")
        return True

    def stop_listening(self):
        """Stop always-on listening."""
        if not self.listening_enabled:
            return

        self.listening_enabled = False
        self._listen_stop.set()
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
        logger.info("[SENSORY] Always-on listening stopped")

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "voice_mode": self.voice_mode,
            "listening_enabled": self.listening_enabled,
            "queue_depth": self.event_queue.qsize(),
            "processed_events": len(self.processed_events),
            "stats": dict(self.stats),
            "lineage_signature": (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA"),
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
        }

    def _continuous_listen_loop(self):
        """
        Always-on ambient audio capture loop.

        Behaviour (per design):
          - Uses sounddevice (PortAudio) — the same backend as the Alt-toggle
            voice controller.  A single persistent InputStream is opened once
            and never closed/reopened, so the device never goes stale.
          - Does NOT transcribe.  Ambient audio is environmental sensing only;
            it feeds the sensory crystal bipyramid so Aurora can notice and
            *optionally* comment on what she hears, but it does NOT force a
            response.  Only direct Alt-key speech forces a response.
          - Crystal is fed with RMS / ZCR / spectral-centroid / spectral-rolloff
            features computed from 0.5-second frames.
        """
        try:
            import sounddevice as _sd
            import numpy as _np
        except ImportError:
            logger.error("[SENSORY] sounddevice not available — ambient listener inactive")
            self.listening_enabled = False
            return

        try:
            from aurora_internal.aurora_sensory_crystal import audio_dict_to_crystal_20d
            _have_crystal_fn = True
        except ImportError:
            _have_crystal_fn = False

        _SAMPLE_RATE = 16000
        _FRAME_SEC   = 0.5          # seconds per crystal update
        _FRAME_SAMP  = int(_SAMPLE_RATE * _FRAME_SEC)

        _buf = []   # accumulator for incoming audio chunks

        def _audio_callback(indata, frames, time_info, status):
            _buf.append(indata[:, 0].copy() if indata.ndim > 1 else indata.copy())

        try:
            stream = _sd.InputStream(
                samplerate=_SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=512,
                callback=_audio_callback,
            )
        except Exception as e:
            logger.error(f"[SENSORY] Could not open ambient audio stream: {e}")
            self.listening_enabled = False
            return

        logger.info("[SENSORY] Ambient listen stream opened (sounddevice)")

        # Path for live audio telemetry (hub reads this every refresh cycle)
        _state_dir = self.state_dir
        _live_path  = _state_dir / "ambient_audio_latest.json"
        _live_tmp   = str(_live_path) + ".tmp"
        _frame_counter = 0
        _session_start = time.time()
        _prev_spectrum = None

        with stream:
            _accum = _np.zeros(0, dtype=_np.float32)
            while self.listening_enabled and not self._listen_stop.is_set():
                # Drain the callback buffer
                while _buf:
                    _accum = _np.concatenate([_accum, _buf.pop(0)])

                if len(_accum) < _FRAME_SAMP:
                    self._listen_stop.wait(timeout=0.05)
                    continue

                # Take one frame
                _frame   = _accum[:_FRAME_SAMP]
                _accum   = _accum[_FRAME_SAMP:]
                _frame_counter += 1

                try:
                    _features, _prev_spectrum = _extract_rich_audio_features(
                        _frame, _SAMPLE_RATE, _prev_spectrum
                    )
                    _rms = float((_features.get("features") or {}).get("rms", 0.0))
                    _zcr = float((_features.get("features") or {}).get("zero_crossing_rate", 0.0))
                    _cent = float((_features.get("features") or {}).get("spectral_centroid", 0.0))
                    _bw = float((_features.get("features") or {}).get("spectral_bandwidth", 0.0))
                    _roll = float((_features.get("features") or {}).get("spectral_rolloff", 0.0))
                    _flux = float((_features.get("features") or {}).get("spectral_flux", 0.0))
                    _harm = float((_features.get("features") or {}).get("harmonicity", 0.0))
                    _onset = float((_features.get("features") or {}).get("onset_density", 0.0))

                    if self.sensory_crystal is not None and _have_crystal_fn:
                        _a20 = audio_dict_to_crystal_20d(_features)
                        self.sensory_crystal.observe_frame(
                            _a20, [0.0] * 57
                        )

                    # Write live telemetry snapshot every 10 frames (~5s)
                    if _frame_counter % 10 == 0:
                        try:
                            _elapsed = time.time() - _session_start
                            _fps = _frame_counter / max(1.0, _elapsed)
                            _snapshot = {
                                "ts":                time.time(),
                                "session_frames":    _frame_counter,
                                "fps":               round(_fps, 2),
                                "rms":               round(_rms, 4),
                                "zcr":               round(_zcr, 4),
                                "spectral_centroid": round(_cent, 4),
                                "spectral_bandwidth": round(_bw, 4),
                                "spectral_rolloff":  round(_roll, 4),
                                "spectral_flux":     round(_flux, 4),
                                "harmonicity":       round(_harm, 4),
                                "onset_density":     round(_onset, 4),
                                "rms_db":            round(20 * _np.log10(max(_rms, 1e-9)), 1),
                                "activity":          str(_features.get("category") or "ambient"),
                            }
                            import json as _json
                            with open(_live_tmp, "w") as _f:
                                _json.dump(_snapshot, _f)
                            import os as _os
                            _os.replace(_live_tmp, str(_live_path))
                        except Exception:
                            pass

                except Exception:
                    pass

        logger.info("[SENSORY] Ambient listen loop ended")

    def get_heard_speech(self) -> Optional[Dict[str, Any]]:
        """Get speech from the queue (non-blocking)."""
        try:
            return self.speech_queue.get_nowait()
        except queue.Empty:
            return None

    def has_heard_speech(self) -> bool:
        """Check if there's speech waiting to be processed."""
        return not self.speech_queue.empty()

    def say(self, text: str, tone: str = None):
        """
        Aurora says something. Uses voice if voice_mode is on.
        Always logs the speech.
        """
        if self.voice_mode and self.hardware and self.hardware.voice:
            self.speak(text, tone=tone, blocking=False)
        if self.on_aurora_speaks:
            self.on_aurora_speaks(text)

    def _process_loop(self):
        """Background processing loop for sensory events."""
        while self.running:
            try:
                event = self.event_queue.get(timeout=0.1)
                self._process_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[SENSORY INTEGRATION] Error processing event: {e}")

    def _process_event(self, event: SensoryEvent):
        """Process a single sensory event."""
        if event.processed:
            return

        if event.event_type in (SensoryEventType.VISUAL_FRAME,
                                SensoryEventType.VISUAL_FACE,
                                SensoryEventType.VISUAL_MOTION):
            self._process_visual_event(event)

        elif event.event_type in (SensoryEventType.AUDIO_CHUNK,
                                  SensoryEventType.AUDIO_VOICE,
                                  SensoryEventType.AUDIO_SPEECH):
            self._process_audio_event(event)

        event.processed = True
        self.processed_events.append(event)

        # Limit history
        if len(self.processed_events) > 100:
            self.processed_events = self.processed_events[-50:]

    def _process_visual_event(self, event: SensoryEvent):
        """Process visual event through the full pipeline."""
        visual_data = event.data
        self._latest_visual_event = event

        # 1. Get competency-modulated description
        competency = {}
        if self.sensory_engine:
            try:
                competency = self.sensory_engine.get_visual_competency()
            except Exception:
                logger.exception("[SENSORY INTEGRATION] Visual competency lookup failed")
                competency = {}

        try:
            description = self.visual_mapper.describe_visual(visual_data, competency)
        except Exception:
            logger.exception("[SENSORY INTEGRATION] Visual description failed")
            description = "I can see a live visual frame, but I cannot interpret it cleanly yet."
        event.linguistic_description = description

        # 2. Process through sensory competency for learning.
        # Keep the live surface feed flowing even if the deeper learner hits a
        # bad state; the camera snapshot should not die because one downstream
        # competency step failed.
        if self.sensory_engine and self.default_mode:
            try:
                result = self.sensory_engine.process_visual_input(
                    visual_data, self.default_mode,
                    intent="observe",
                    text_context=description
                )
                event.concepts_activated = result.get("concepts_matched", [])
            except Exception:
                logger.exception("[SENSORY INTEGRATION] Visual competency processing failed")

        # 3. Ground in OETS if available
        if self.perception and self.perception.oets:
            self._ground_visual_concepts(event)

        # 4. Callback
        if self.on_visual_description:
            self.on_visual_description(description)

        self.stats["visual_processed"] += 1

    def _process_audio_event(self, event: SensoryEvent):
        """Process audio event through the full pipeline."""
        audio_data = event.data
        self._latest_audio_event = event

        # 1. Get competency-modulated description
        competency = {}
        if self.sensory_engine:
            try:
                competency = self.sensory_engine.get_audio_competency()
            except Exception:
                logger.exception("[SENSORY INTEGRATION] Audio competency lookup failed")
                competency = {}

        try:
            description = self.audio_mapper.describe_audio(audio_data, competency)
        except Exception:
            logger.exception("[SENSORY INTEGRATION] Audio description failed")
            description = "I can hear live audio, but I cannot interpret it cleanly yet."
        event.linguistic_description = description

        # 2. Process through sensory competency for learning.
        # Audio should keep flowing even if the competency layer is in a bad
        # state for a moment.
        if self.sensory_engine and self.default_mode:
            try:
                result = self.sensory_engine.process_audio_input(
                    audio_data, self.default_mode,
                    intent="listen",
                    text_context=description
                )
                event.concepts_activated = result.get("concepts_matched", [])
            except Exception:
                logger.exception("[SENSORY INTEGRATION] Audio competency processing failed")

        # 3. Handle transcribed speech specially
        if event.event_type == SensoryEventType.AUDIO_SPEECH:
            text = audio_data.get("transcription", "")
            if text:
                processed = self.audio_mapper.process_transcription(text)
                event.data["processed_speech"] = processed

                if self.on_speech_heard:
                    self.on_speech_heard(text)

                self.stats["speech_transcribed"] += 1

        # 4. Ground in OETS
        if self.perception and self.perception.oets:
            self._ground_audio_concepts(event)

        # 5. Callback
        if self.on_audio_description:
            self.on_audio_description(description)

        self.stats["audio_processed"] += 1

    def _event_is_recent(self, event: Optional[SensoryEvent], max_age_s: float = 45.0) -> bool:
        if event is None:
            return False
        try:
            return (time.time() - float(event.timestamp or 0.0)) <= max_age_s
        except Exception:
            return False

    def _current_visual_vector(self) -> List[float]:
        event = self._latest_visual_event
        if event is None or self.sensory_engine is None:
            return []
        competency = self.sensory_engine.get_visual_competency() if self.sensory_engine else {}
        extractor = getattr(self.sensory_engine, "_extract_visual_features", None)
        if not callable(extractor):
            return []
        try:
            return list(extractor(dict(event.data or {}), competency) or [])
        except Exception:
            return []

    def _current_audio_vector(self) -> List[float]:
        event = self._latest_audio_event
        if event is None or self.sensory_engine is None:
            return []
        competency = self.sensory_engine.get_audio_competency() if self.sensory_engine else {}
        extractor = getattr(self.sensory_engine, "_extract_audio_features", None)
        if not callable(extractor):
            return []
        try:
            return list(extractor(dict(event.data or {}), competency) or [])
        except Exception:
            return []

    def _mark_guided_event(self, event: Optional[SensoryEvent], label: str, role: str) -> None:
        if event is None:
            return
        guided = dict(event.data.get("guided_labels") or {})
        guided[str(role or "guided_label")] = str(label or "")
        event.data["guided_labels"] = guided
        event.data["guided_label"] = str(label or "")
        event.data["guidance_role"] = str(role or "guided_label")
        tag = f"guided:{label}"
        if tag not in event.concepts_activated:
            event.concepts_activated.append(tag)

    def _enqueue_surface_guidance(
        self,
        *,
        label: str,
        role: str,
        modalities: List[str],
        source_text: str,
        note: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "label": str(label or "").strip(),
            "role": str(role or "guided_label"),
            "modalities": [str(item) for item in list(modalities or []) if str(item).strip()],
            "source_text": str(source_text or "").strip(),
            "note": str(note or "").strip(),
            "surface_context": {
                "visual_recent": self._event_is_recent(self._latest_visual_event),
                "audio_recent": self._event_is_recent(self._latest_audio_event),
                "visual_description": str(getattr(self._latest_visual_event, "linguistic_description", "") or ""),
                "audio_description": str(getattr(self._latest_audio_event, "linguistic_description", "") or ""),
            },
        }
        try:
            from aurora_internal.dual_strata.sensory_snapshot_channel import append_surface_guidance

            return dict(append_surface_guidance(self.state_dir, payload) or {})
        except Exception:
            return payload

    def guide_current_visual_label(
        self,
        label: str,
        *,
        role: str = "visual_label",
        source_text: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        event = self._latest_visual_event if self._event_is_recent(self._latest_visual_event) else None
        if event is None or self.sensory_engine is None:
            return {"applied": False, "reason": "no_recent_visual_anchor"}
        vector = self._current_visual_vector()
        oets_node = ""
        if self.sensory_engine and hasattr(self.sensory_engine, "_ground_to_oets"):
            try:
                oets_node = str(self.sensory_engine._ground_to_oets(str(label or ""), role, source_text or label) or "")
            except Exception:
                oets_node = ""
        guided = self.sensory_engine.visual_concepts.guide_label(
            label,
            vector,
            role=role,
            source_text=source_text,
            note=note,
            oets_node=oets_node,
        )
        if guided.get("matched"):
            self.visual_mapper.learn_association(str(event.linguistic_description or "").strip()[:120] or "live_visual_pattern", str(label or ""))
            self._mark_guided_event(event, str(guided.get("label") or label), role)
            queue_event = self._enqueue_surface_guidance(
                label=str(guided.get("label") or label),
                role=role,
                modalities=["visual"],
                source_text=source_text,
                note=note,
            )
            guided["queue_event_id"] = str(queue_event.get("event_id", "") or "")
            guided["applied"] = True
        else:
            guided["applied"] = False
        return guided

    def guide_current_audio_label(
        self,
        label: str,
        *,
        role: str = "audio_label",
        source_text: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        event = self._latest_audio_event if self._event_is_recent(self._latest_audio_event) else None
        if event is None or self.sensory_engine is None:
            return {"applied": False, "reason": "no_recent_audio_anchor"}
        vector = self._current_audio_vector()
        oets_node = ""
        if self.sensory_engine and hasattr(self.sensory_engine, "_ground_to_oets"):
            try:
                oets_node = str(self.sensory_engine._ground_to_oets(str(label or ""), role, source_text or label) or "")
            except Exception:
                oets_node = ""
        guided = self.sensory_engine.audio_concepts.guide_label(
            label,
            vector,
            role=role,
            source_text=source_text,
            note=note,
            oets_node=oets_node,
        )
        if guided.get("matched"):
            if event.data.get("voice_detected"):
                self.audio_mapper.learn_voice_profile(str(guided.get("label") or label), dict(event.data or {}))
            self._mark_guided_event(event, str(guided.get("label") or label), role)
            queue_event = self._enqueue_surface_guidance(
                label=str(guided.get("label") or label),
                role=role,
                modalities=["audio"],
                source_text=source_text,
                note=note,
            )
            guided["queue_event_id"] = str(queue_event.get("event_id", "") or "")
            guided["applied"] = True
        else:
            guided["applied"] = False
        return guided

    def guide_user_identity(self, name: str, *, source_text: str = "") -> Dict[str, Any]:
        name = str(name or "").strip()
        if not name:
            return {"applied": False, "reason": "missing_name"}
        result = {
            "type": "person_identity",
            "label": name,
            "visual": self.guide_current_visual_label(
                name,
                role="person_identity",
                source_text=source_text,
                note="bind current live visual anchor to named person",
            ),
            "audio": self.guide_current_audio_label(
                name,
                role="voice_identity",
                source_text=source_text,
                note="bind current live audio anchor to named person",
            ),
        }
        applied_modalities = []
        if result["visual"].get("applied"):
            applied_modalities.append("visual")
        if result["audio"].get("applied"):
            applied_modalities.append("audio")
        if applied_modalities:
            queue_event = self._enqueue_surface_guidance(
                label=name,
                role="person_identity",
                modalities=applied_modalities,
                source_text=source_text,
                note="cross-modal person binding from live guidance",
            )
            result["queue_event_id"] = str(queue_event.get("event_id", "") or "")
        result["applied"] = bool(applied_modalities)
        result["modalities"] = applied_modalities
        self._latest_guidance = dict(result)
        return result

    def apply_guidance_from_text(self, user_text: str) -> Dict[str, Any]:
        text = str(user_text or "").strip()
        if not text:
            return {}

        def _clean_label(raw: str) -> str:
            label = re.sub(r"[^A-Za-z0-9' -]+", " ", str(raw or "")).strip(" .,!?:;")
            label = re.sub(r"\b(?:a|an|the)\b\s+", "", label, flags=re.IGNORECASE).strip()
            words = [word for word in label.split() if word]
            return " ".join(words[:4]).strip()

        actions: List[Dict[str, Any]] = []
        identity_patterns = (
            r"\bi[' ]?m\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bi\s+am\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bcall\s+me\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bi\s+go\s+by\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bthat(?:'s| is)\s+me\s+([A-Za-z][A-Za-z' -]{0,31})\b",
            r"\bthe\s+person\s+you\s+(?:see|hear)[^.!?\n]{0,48}?(?:is|that's|that\s+is)\s+([A-Za-z][A-Za-z' -]{0,31})\b",
        )
        skip_identity = {"fine", "okay", "ok", "here", "back", "sorry", "ready"}
        for pattern in identity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = _clean_label(match.group(1))
                if candidate and candidate.lower() not in skip_identity:
                    actions.append({"kind": "person_identity", "label": candidate})
                    break

        visual_patterns = (
            r"\b(?:this|that|it)\s+(?:is|looks\s+like)\s+(.+)$",
            r"\byou(?:'re| are)\s+looking\s+at\s+(.+)$",
        )
        audio_patterns = (
            r"\b(?:this|that|it)\s+sounds\s+like\s+(.+)$",
            r"\bthat\s+sound\s+is\s+(.+)$",
            r"\byou\s+hear\s+(.+)$",
        )
        for pattern in visual_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                label = _clean_label(match.group(1))
                if label and len(label.split()) <= 4:
                    actions.append({"kind": "visual_label", "label": label})
                break
        for pattern in audio_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                label = _clean_label(match.group(1))
                if label and len(label.split()) <= 4:
                    actions.append({"kind": "audio_label", "label": label})
                break

        if not actions:
            return {}

        results: List[Dict[str, Any]] = []
        for action in actions:
            kind = str(action.get("kind", "") or "")
            label = str(action.get("label", "") or "")
            if kind == "person_identity":
                results.append(self.guide_user_identity(label, source_text=text))
            elif kind == "visual_label":
                results.append(
                    self.guide_current_visual_label(
                        label,
                        role="visual_label",
                        source_text=text,
                        note="operator supplied live visual label",
                    )
                )
            elif kind == "audio_label":
                results.append(
                    self.guide_current_audio_label(
                        label,
                        role="audio_label",
                        source_text=text,
                        note="operator supplied live audio label",
                    )
                )

        applied = [item for item in results if isinstance(item, dict) and item.get("applied")]
        payload = {
            "source_text": text,
            "actions": results,
            "applied": bool(applied),
            "summary": "; ".join(
                f"{item.get('label', '')} -> {', '.join(item.get('modalities', [])) or 'guided'}"
                for item in applied
                if str(item.get("label", "") or "").strip()
            ),
        }
        self._latest_guidance = dict(payload)
        return payload

    def _ground_visual_concepts(self, event: SensoryEvent):
        """Ground visual concepts in OETS semantic web."""
        oets = self.perception.oets
        for concept in event.concepts_activated:
            try:
                # Check if node exists
                if concept not in oets.web.nodes:
                    # Create new node for visual concept
                    oets.add_node(concept, role="visual_concept")

                # Record encounter
                node = oets.web.nodes.get(concept)
                if node:
                    node.encounter(f"visual:{event.linguistic_description[:50]}")

                self.stats["concepts_grounded"] += 1
            except Exception as e:
                logger.debug(f"[SENSORY INTEGRATION] Failed to ground concept: {e}")

    def _ground_audio_concepts(self, event: SensoryEvent):
        """Ground audio concepts in OETS semantic web."""
        oets = self.perception.oets
        for concept in event.concepts_activated:
            try:
                if concept not in oets.web.nodes:
                    oets.add_node(concept, role="audio_concept")

                node = oets.web.nodes.get(concept)
                if node:
                    node.encounter(f"audio:{event.linguistic_description[:50]}")

                self.stats["concepts_grounded"] += 1
            except Exception as e:
                logger.debug(f"[SENSORY INTEGRATION] Failed to ground concept: {e}")

    # ========================================================================
    # PUBLIC API - Main interaction methods
    # ========================================================================

    def see(self) -> Tuple[str, Dict[str, Any]]:
        """
        Capture visual input and return description + raw data.
        This is Aurora "looking" at her environment.
        """
        if not self.hardware:
            return "I cannot see - no camera available.", {}

        visual_data = self.hardware.capture_visual()
        if not visual_data:
            return "I tried to look, but couldn't capture an image.", {}

        # Create and process event
        event = SensoryEvent(
            event_type=SensoryEventType.VISUAL_FRAME,
            data=visual_data
        )
        self._process_visual_event(event)

        snapshot_path = self._save_camera_snapshot()
        if snapshot_path:
            visual_data["snapshot_path"] = snapshot_path

        return event.linguistic_description, visual_data

    def _save_camera_snapshot(self) -> Optional[str]:
        if not self.hardware:
            return None
        camera = getattr(self.hardware, "camera", None)
        if camera is None:
            return None
        frame = getattr(camera, "last_frame", None)
        if frame is None or not _CV2_AVAILABLE:
            return None
        try:
            self._vision_snapshot_dir.mkdir(parents=True, exist_ok=True)
            for stale in self._vision_snapshot_dir.glob("sight_*.jpg"):
                try:
                    stale.unlink()
                except Exception:
                    pass
            snapshot_path = self._vision_snapshot_dir / "sight_latest.jpg"
            cv2.imwrite(str(snapshot_path), frame)
            shared_camera_dir = self.state_dir / "vision_seeds" / "camera"
            shared_camera_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(shared_camera_dir / "frame_latest.png"), frame)
            return str(snapshot_path)
        except Exception:
            return None

    def listen(self, duration: float = 2.0) -> Tuple[str, Dict[str, Any]]:
        """
        Capture audio input and return description + raw data.
        This is Aurora "listening" to her environment.
        """
        if not self.hardware:
            return "I cannot hear - no microphone available.", {}

        audio_data = self.hardware.capture_audio(duration=duration)
        if not audio_data:
            return "I tried to listen, but couldn't capture audio.", {}

        # Create and process event
        event = SensoryEvent(
            event_type=SensoryEventType.AUDIO_CHUNK,
            data=audio_data
        )
        self._process_audio_event(event)

        return event.linguistic_description, audio_data

    def hear_speech(self, timeout: float = 5.0) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Listen for speech and transcribe it.
        Returns (transcription, processed_info).
        """
        if not self.hardware:
            return None, {"error": "No microphone available"}

        text = self.hardware.listen_for_speech(timeout=timeout)
        if not text:
            return None, {"error": "No speech detected"}

        # Process transcription
        processed = self.audio_mapper.process_transcription(text)

        # Create event
        event = SensoryEvent(
            event_type=SensoryEventType.AUDIO_SPEECH,
            data={"transcription": text, **processed}
        )
        self._process_audio_event(event)

        return text, processed

    def speak(self, text: str, tone: str = None, blocking: bool = True) -> bool:
        """
        Aurora speaks with personality-modulated voice.

        Args:
            text: What to say
            tone: Emotional tone (warm, curious, thoughtful, etc.)
            blocking: Wait for speech to complete

        Returns:
            True if speech succeeded
        """
        if not self.hardware or not self.hardware.voice:
            logger.warning("[SENSORY INTEGRATION] No voice available")
            return False

        # Get speech parameters based on personality and tone
        params = self.voice_mapper.get_speech_parameters(tone, text)

        # Prepare text
        prepared_text = self.voice_mapper.prepare_speech_text(text, tone)

        voice = self.hardware.voice

        # For edge-tts neural voices, pass emotion for adaptive voice
        if hasattr(voice, 'use_edge_tts') and voice.use_edge_tts:
            success = voice.speak(prepared_text, blocking=blocking, emotion=tone)
        else:
            # Legacy pyttsx3 path - apply parameters directly
            if hasattr(voice, '_engine') and voice._engine:
                try:
                    voice._engine.setProperty('rate', params['rate'])
                    voice._engine.setProperty('volume', params['volume'])
                except:
                    pass
            success = voice.speak(prepared_text, blocking=blocking)

        if success:
            self.stats["utterances_spoken"] += 1
            if self.on_aurora_speaks:
                self.on_aurora_speaks(text)

        return success

    def speak_async(self, text: str, tone: str = None):
        """Speak without blocking."""
        thread = threading.Thread(target=self.speak, args=(text, tone, True))
        thread.daemon = True
        thread.start()

    def describe_what_i_see(self) -> str:
        """
        Full visual description with context.
        Aurora describes her current visual field in natural language.
        """
        description, data = self.see()

        # Enrich with learned concepts
        concepts = []
        if self.sensory_engine:
            for name, concept in self.sensory_engine.visual_concepts.concepts.items():
                if concept.confidence > 0.7:
                    concepts.append(name)

        if concepts:
            description += f" I recognize: {', '.join(concepts[:3])}."

        return description

    def describe_what_i_hear(self, duration: float = 2.0) -> str:
        """
        Full audio description with context.
        Aurora describes what she's hearing in natural language.
        """
        description, data = self.listen(duration)

        # Enrich with learned concepts
        concepts = []
        if self.sensory_engine:
            for name, concept in self.sensory_engine.audio_concepts.concepts.items():
                if concept.confidence > 0.7:
                    concepts.append(name)

        if concepts:
            description += f" I recognize: {', '.join(concepts[:3])}."

        return description

    # ========================================================================
    # FILE-BASED INPUT (Images & Audio files)
    # ========================================================================

    def see_image(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Load and process an image file.
        Aurora "looks at" a picture.

        Args:
            file_path: Path to image file (jpg, png, bmp, etc.)

        Returns:
            (description, visual_data) tuple
        """
        if not self.hardware:
            return "I cannot see images - no hardware interface available.", {}

        visual_data = self.hardware.load_image(file_path)
        if not visual_data:
            return f"I couldn't load the image at {file_path}. Make sure it exists and is a valid image format.", {}

        # Create and process event
        event = SensoryEvent(
            event_type=SensoryEventType.VISUAL_FRAME,
            data=visual_data
        )
        self._process_visual_event(event)

        # Enhanced description for image files
        description = event.linguistic_description

        # Add file-specific details
        width = visual_data.get("image_width", 0)
        height = visual_data.get("image_height", 0)
        if width and height:
            description += f" The image is {width}x{height} pixels."

        face_count = len(visual_data.get("faces", []))
        if face_count > 0:
            if face_count == 1:
                description += " I can see a person's face."
            else:
                description += f" I can see {face_count} faces."

        return description, visual_data

    def listen_to_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Load and process an audio file.
        Aurora "listens to" music or audio.

        Args:
            file_path: Path to audio file (wav, mp3, ogg, flac, etc.)

        Returns:
            (description, audio_data) tuple
        """
        if not self.hardware:
            return "I cannot hear audio files - no hardware interface available.", {}

        audio_data = self.hardware.load_audio_file(file_path)
        if not audio_data:
            return f"I couldn't load the audio at {file_path}. Make sure it exists and is a valid audio format.", {}

        # Create and process event
        event = SensoryEvent(
            event_type=SensoryEventType.AUDIO_CHUNK,
            data=audio_data
        )
        self._process_audio_event(event)

        # Enhanced description for audio files
        description = event.linguistic_description

        # Add file-specific details
        duration = audio_data.get("duration_seconds", 0)
        if duration > 0:
            if duration < 60:
                description += f" The audio is {duration:.1f} seconds long."
            else:
                mins = int(duration // 60)
                secs = int(duration % 60)
                description += f" The audio is {mins}:{secs:02d} long."

        category = audio_data.get("category", "unknown")
        if category == "music":
            description += " It sounds like music."
        elif category == "speech":
            description += " It sounds like someone speaking."

        return description, audio_data

    def describe_image(self, file_path: str) -> str:
        """
        Full description of an image file with context.
        Convenience method that returns just the description.
        """
        description, data = self.see_image(file_path)
        return description

    def describe_audio_file(self, file_path: str) -> str:
        """
        Full description of an audio file with context.
        Convenience method that returns just the description.
        """
        description, data = self.listen_to_file(file_path)
        return description

    def get_sensory_context(self) -> Dict[str, Any]:
        """
        Get current sensory context for conversation enrichment.
        Returns summary of recent sensory experiences.
        """
        context = {
            "visual": None,
            "audio": None,
            "recent_speech": None,
            "concepts_active": [],
            "latest_guidance": dict(self._latest_guidance or {}),
        }

        # Get most recent events by type
        for event in reversed(self.processed_events):
            age = time.time() - event.timestamp
            if age > 30:  # Only recent events (30 seconds)
                break

            if event.event_type == SensoryEventType.VISUAL_FRAME and not context["visual"]:
                context["visual"] = event.linguistic_description
                context["concepts_active"].extend(event.concepts_activated)

            if event.event_type == SensoryEventType.AUDIO_CHUNK and not context["audio"]:
                context["audio"] = event.linguistic_description
                context["concepts_active"].extend(event.concepts_activated)

            if event.event_type == SensoryEventType.AUDIO_SPEECH and not context["recent_speech"]:
                context["recent_speech"] = event.data.get("transcription", "")

        # Dedupe concepts
        context["concepts_active"] = list(set(context["concepts_active"]))[:10]

        return context

    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            **self.stats,
            "events_queued": self.event_queue.qsize(),
            "events_processed": len(self.processed_events),
            "hardware_connected": self.hardware is not None,
            "sensory_engine_connected": self.sensory_engine is not None,
            "perception_connected": self.perception is not None,
        }


# ============================================================================
# SECTION 6: FACTORY & CONVENIENCE
# ============================================================================

def create_sensory_integration(systems: Dict[str, Any]) -> SensoryIntegrationEngine:
    """
    Factory function to create SensoryIntegrationEngine from boot systems.

    Args:
        systems: Dict from boot_aurora() containing all system references

    Returns:
        Configured SensoryIntegrationEngine
    """
    state_dir = systems.get('state_dir') or "aurora_state"
    engine = SensoryIntegrationEngine(
        sensory_engine=systems.get('sensory'),
        perception=systems.get('perception'),
        identity=systems.get('identity'),
        mode=systems.get('ExistenceMode', {}).BOUNDED if systems.get('ExistenceMode') else None,
        state_dir=state_dir,
    )
    return engine


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Main engine
    "SensoryIntegrationEngine",
    "create_sensory_integration",

    # Event types
    "SensoryEventType",
    "SensoryEvent",

    # Mappers
    "VisualLinguisticMapper",
    "AudioLinguisticMapper",
    "VoiceExpressionMapper",
]


# ============================================================================
