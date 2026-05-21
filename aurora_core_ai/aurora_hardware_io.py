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
    except ImportError:
        pass
    try:
        import speech_recognition  # noqa: F401
        return "linux"
    except ImportError:
        pass
    return "headless"


PLATFORM = detect_platform()

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
        fn = subprocess.run if block else subprocess.Popen
        try:
            fn(["termux-tts-speak", text],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print(f"[AURORA] {text}")
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


def _listen_termux(timeout: float) -> Optional[str]:
    """Use termux-speech-to-text (blocks until done, respects timeout)."""
    if not _termux_cmd("termux-speech-to-text"):
        return None
    # Give a generous timeout beyond the caller's window.
    # termux-speech-to-text opens Android STT UI; if we kill the client
    # subprocess too early its socket closes and Termux:API's ResultReturner
    # gets "Connection refused" — a Java-side crash we can prevent by never
    # timing out prematurely.  45 s is the Android STT hard limit.
    _proc_timeout = max(45.0, timeout + 15.0)
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True, text=True,
            timeout=_proc_timeout,
        )
        raw = result.stdout.strip()
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list) and data:
                    return str(data[0]).strip()
                if isinstance(data, dict):
                    return str(data.get("utterances", [""])[0] or "").strip()
            except json.JSONDecodeError:
                return raw
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
                    # Record 2-second clip
                    subprocess.run(
                        ["termux-microphone-record",
                         "-e", "wav", "-r", str(self._sample_rate),
                         "-c", "1", "-l", "2", "-f", tmp],
                        timeout=6,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    if Path(tmp).exists():
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
            if self._paused.is_set():
                time.sleep(0.5)
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
        result["ambient_mic"] = _termux_cmd("termux-microphone-record")
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
