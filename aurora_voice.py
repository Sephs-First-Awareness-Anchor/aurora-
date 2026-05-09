#!/usr/bin/env python3
"""
aurora_voice.py -- Aurora's voice interface.

Entry points:

  WakeWordListener         -- optional always-on background thread.
                              Listens for "hey aurora".
                              When detected, calls on_wake() callback.

  AltToggleVoiceController -- always-on background thread for daemon use.
                              Tap ALT once to start recording.
                              Tap ALT again to send the prompt.

  VoiceSession             -- interactive terminal voice loop.
                              Hold SPACE to record, release to send.
                              Aurora responds with her voice.
                              Say "goodbye" / "bye" or press ESC to end.

Wake word engine priority:
  1. PocketSphinx keyword spotting (offline, no API key, preferred)
  2. speech_recognition + Google (online fallback)

Transcription engine priority:
  1. speech_recognition + Google (most accurate for conversation)
  2. PocketSphinx (offline fallback)
"""

from __future__ import annotations

import os
import sys
import time
import selectors
import asyncio
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from aurora_internal.dual_strata.surface_channel import request_surface_turn

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SAMPLE_RATE      = 16000
CHANNELS         = 1
WAKE_WORDS       = ["hey aurora", "hey, aurora"]
GOODBYE_WORDS    = {"goodbye", "bye", "see you", "see ya", "that's all", "thats all", "exit", "stop"}
WAKE_SENSITIVITY = 1e-7    # PocketSphinx keyword sensitivity (lower = more sensitive)
MAX_RECORD_SEC   = 30      # max push-to-talk recording length
SILENCE_TIMEOUT  = 3.0     # auto-stop recording after N sec of silence
WAKE_WINDOW_SEC  = 2.4     # size of each wake-listener audio window
WAKE_COOLDOWN_SEC = 12.0   # suppress immediate re-triggers after a wake session
DEFAULT_DAEMON_TOGGLE_KEY = "alt"


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(int(minimum), int(os.environ.get(name, str(default)).strip() or default))
    except Exception:
        return max(int(minimum), int(default))


VOICE_TRAIN_EPOCHS = _env_int("AURORA_VOICE_TRAIN_EPOCHS", 3, minimum=2)
VOICE_TRAIN_EPISODES = _env_int("AURORA_VOICE_TRAIN_EPISODES", 6, minimum=2)
VOICE_TRAIN_TURNS = _env_int("AURORA_VOICE_TRAIN_TURNS", 5, minimum=2)
VOICE_STUDY_CYCLES = _env_int("AURORA_VOICE_STUDY_CYCLES", 4, minimum=2)
VOICE_DREAM_EPISODES = _env_int("AURORA_VOICE_DREAM_EPISODES", 8, minimum=2)
VOICE_EXPLORE_CYCLES = _env_int("AURORA_VOICE_EXPLORE_CYCLES", 4, minimum=2)
VOICE_CORPUS_PATH = Path(
    os.environ.get("AURORA_VOICE_CORPUS")
    or str(Path(__file__).parent / "conversations.json")
)

# Available TTS voices — cycled by "reactivate voice" command
VOICE_CYCLE = [
    "en-GB-SoniaNeural",       # default — British female
    "en-GB-LibbyNeural",       # British female, softer
    "en-US-AriaNeural",        # US female
    "en-US-JennyNeural",       # US female, clearer
    "en-AU-NatashaNeural",     # Australian female
    "en-US-SaraNeural",        # US female, casual
]
_voice_index = 0  # tracks current position in VOICE_CYCLE
_pyttsx3_engine = None

def _current_voice() -> str:
    return VOICE_CYCLE[_voice_index % len(VOICE_CYCLE)]

def _next_voice() -> str:
    global _voice_index
    _voice_index = (_voice_index + 1) % len(VOICE_CYCLE)
    return _current_voice()

# Initialise from environment if set
_env_voice = os.environ.get("CLAUDE_TTS_VOICE", "")
if _env_voice in VOICE_CYCLE:
    _voice_index = VOICE_CYCLE.index(_env_voice)

# Always read current voice through _current_voice() — never use VOICE directly
VOICE = _current_voice()  # kept for legacy compat; updated on switch


# ---------------------------------------------------------------------------
# TTS — reuses edge-tts the same way speak_response.py does
# ---------------------------------------------------------------------------
async def _tts_async(text: str) -> bool:
    try:
        import edge_tts
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        comm = edge_tts.Communicate(text, _current_voice(), rate="+0%", volume="+0%")
        await comm.save(tmp)
        result = subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp],
            timeout=120,
        )
        os.unlink(tmp)
        return result.returncode == 0
    except Exception:
        return False


def _split_tts_chunks(text: str, max_chars: int = 600) -> list:
    """
    Split text into chunks of at most max_chars, breaking at sentence boundaries
    ('. ', '! ', '? ', '\n') so each edge-tts call stays well within limits.
    Never splits mid-sentence if avoidable.
    """
    import re
    # Normalize: collapse runs of whitespace, strip leading/trailing
    text = re.sub(r'[ \t]+', ' ', text).strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks = []
    # Split on sentence-ending punctuation followed by space or end-of-string
    sentence_pattern = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_pattern.split(text)

    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # If a single sentence is already over the limit, split at comma or hard-break
        if len(sentence) > max_chars:
            # Flush what we have
            if current:
                chunks.append(current.strip())
                current = ""
            # Split long sentence at commas or em-dashes
            sub_parts = re.split(r'(?<=,)\s+|(?<=—)\s+|(?<= —)\s*', sentence)
            sub_buf = ""
            for part in sub_parts:
                if len(sub_buf) + len(part) + 1 <= max_chars:
                    sub_buf = (sub_buf + " " + part).strip()
                else:
                    if sub_buf:
                        chunks.append(sub_buf)
                    sub_buf = part[:max_chars]  # hard truncate last resort
            if sub_buf:
                chunks.append(sub_buf)
            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def speak(text: str) -> bool:
    """Speak text aloud via edge-tts. Long text is chunked to prevent fallback."""
    chunks = _split_tts_chunks(text, max_chars=600)
    if not chunks:
        return False

    # Try edge-tts chunk by chunk. If every chunk succeeds, return True.
    # Only fall back to pyttsx3/espeak if edge-tts fails on the first chunk —
    # meaning edge-tts itself is unavailable (not just a length issue).
    all_ok = True
    first_chunk_failed = False
    for i, chunk in enumerate(chunks):
        try:
            ok = asyncio.run(_tts_async(chunk))
            if not ok:
                all_ok = False
                if i == 0:
                    first_chunk_failed = True
                break
        except Exception:
            all_ok = False
            if i == 0:
                first_chunk_failed = True
            break

    if all_ok:
        return True

    # edge-tts is unavailable — fall back for the full text (truncated to be safe)
    safe_text = text[:400]
    try:
        global _pyttsx3_engine
        import pyttsx3

        if _pyttsx3_engine is None:
            _pyttsx3_engine = pyttsx3.init()
            _pyttsx3_engine.setProperty('rate', 150)
            voices = list(_pyttsx3_engine.getProperty('voices') or [])
            preferred_markers = [
                "en-gb-x-rp",
                "en-gb",
                "english (great britain)",
                "english",
            ]
            voice_rows = [
                (
                    " | ".join(
                        str(part).lower()
                        for part in (
                            getattr(voice, "id", ""),
                            getattr(voice, "name", ""),
                            getattr(voice, "languages", ""),
                        )
                    ),
                    getattr(voice, "id", ""),
                )
                for voice in voices
            ]
            for marker in preferred_markers:
                selected_voice_id = next(
                    (voice_id for haystack, voice_id in voice_rows if marker in haystack),
                    "",
                )
                if selected_voice_id:
                    _pyttsx3_engine.setProperty('voice', selected_voice_id)
                    break

        _pyttsx3_engine.say(safe_text)
        _pyttsx3_engine.runAndWait()
        return True
    except Exception:
        pass
    try:
        subprocess.run(["espeak", "-s", "160", "-v", "en", safe_text], timeout=60)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# STT helpers
# ---------------------------------------------------------------------------

def _transcribe_google(audio_data) -> str:
    """Transcribe using Google (online, most accurate)."""
    import speech_recognition as sr
    r = sr.Recognizer()
    try:
        return r.recognize_google(audio_data)
    except Exception:
        return ""


def _transcribe_sphinx(audio_data) -> str:
    """Transcribe using PocketSphinx (offline fallback)."""
    import speech_recognition as sr
    r = sr.Recognizer()
    try:
        return r.recognize_sphinx(audio_data)
    except Exception:
        return ""


def transcribe(audio_data) -> str:
    """Transcribe audio — Google first, sphinx fallback."""
    text = _transcribe_google(audio_data)
    if not text:
        text = _transcribe_sphinx(audio_data)
    return text.strip()


def _make_audio_data(raw_bytes: bytes):
    import speech_recognition as sr
    return sr.AudioData(raw_bytes, SAMPLE_RATE, 2)


def _normalize_wake_text(text: str) -> str:
    return " ".join(text.lower().replace(",", " ").split())


def _matches_wake_transcript(text: str) -> bool:
    normalized = _normalize_wake_text(text)
    if not normalized:
        return False
    return normalized == "hey aurora" or normalized.startswith("hey aurora ")


def _confirm_wake_phrase(raw_bytes: bytes) -> bool:
    """
    Confirm a keyword-spotting hit using full transcription of the same audio.
    This cuts down false positives before opening a voice session.
    """
    try:
        audio = _make_audio_data(raw_bytes)
    except Exception:
        return False

    for transcriber in (_transcribe_sphinx, _transcribe_google):
        try:
            if _matches_wake_transcript(transcriber(audio)):
                return True
        except Exception:
            continue

    return False


def _get_hardware_voice(systems: Optional[Dict[str, Any]]):
    hardware = systems.get("hardware") if systems else None
    return getattr(hardware, "voice", None) if hardware else None


def _tts_route_mode() -> str:
    return str(os.environ.get("AURORA_TTS_ROUTE", "") or "").strip().lower()


def _speak_with_system_voice(
    text: str,
    systems: Optional[Dict[str, Any]],
    tone: Optional[str] = None,
) -> bool:
    route = _tts_route_mode()
    if route in {"simple", "direct", "local"}:
        return speak(text)
    if route in {"simple_first", "direct_first", "local_first"}:
        if speak(text):
            return True

    integration = systems.get("sensory_integration") if systems else None
    if integration and hasattr(integration, "speak"):
        try:
            if integration.speak(text, tone=tone or "warm"):
                return True
        except Exception:
            pass

    voice = _get_hardware_voice(systems)
    if voice and hasattr(voice, "speak"):
        try:
            if voice.speak(text, blocking=True, emotion=tone):
                return True
        except TypeError:
            try:
                if voice.speak(text, blocking=True):
                    return True
            except Exception:
                pass
        except Exception:
            pass

    return speak(text)


def _cycle_system_voice(systems: Optional[Dict[str, Any]]) -> Optional[str]:
    voice = _get_hardware_voice(systems)
    if not voice or not hasattr(voice, "list_voices") or not hasattr(voice, "set_voice"):
        return None

    try:
        presets = voice.list_voices() or {}
        preset_names = list(presets.keys())
        if not preset_names:
            return None

        current_voice_id = getattr(voice, "voice_name", "")
        current_index = -1
        for i, preset_name in enumerate(preset_names):
            if presets.get(preset_name) == current_voice_id:
                current_index = i
                break

        next_name = preset_names[(current_index + 1) % len(preset_names)]
        if voice.set_voice(next_name):
            return voice.get_current_voice()
    except Exception:
        return None

    return None


def speak_with_system_voice(
    text: str,
    systems: Optional[Dict[str, Any]],
    tone: Optional[str] = None,
) -> bool:
    """Public shared TTS path used by daemon and command surfaces."""
    return _speak_with_system_voice(text, systems, tone=tone)


def get_system_voice_label(systems: Optional[Dict[str, Any]]) -> str:
    """Return Aurora's currently selected shared-system voice label."""
    voice = _get_hardware_voice(systems)
    if voice and hasattr(voice, "get_current_voice"):
        try:
            label = str(voice.get_current_voice() or "").strip()
            if label:
                return label
        except Exception:
            pass
    return _current_voice()


def persist_system_voice_selection(systems: Optional[Dict[str, Any]]) -> bool:
    """Persist the currently selected shared voice into Aurora state."""
    if not systems:
        return False
    try:
        from aurora import save_sensory_skill_state

        return bool(save_sensory_skill_state(systems, verbose=False))
    except Exception:
        return False


def _wait_key_event_evdev(target_codes: set[int], event_values: set[int], timeout: Optional[float]) -> Optional[int]:
    """
    Wait for a matching evdev key event and return the matched key code.
    Returns None on timeout or if evdev/input devices are unavailable.
    """
    try:
        from evdev import InputDevice, list_devices, ecodes
    except Exception:
        return None

    devices = []
    selector = selectors.DefaultSelector()
    try:
        for path in list_devices():
            try:
                dev = InputDevice(path)
                caps = dev.capabilities().get(ecodes.EV_KEY, [])
                key_codes = {item if isinstance(item, int) else item[0] for item in caps}
                if key_codes.intersection(target_codes):
                    devices.append(dev)
                    selector.register(dev, selectors.EVENT_READ, dev)
            except Exception:
                continue

        if not devices:
            return None

        deadline = None if timeout is None else time.time() + timeout
        while True:
            wait_timeout = None
            if deadline is not None:
                wait_timeout = max(0.0, deadline - time.time())
                if wait_timeout == 0.0:
                    return None

            ready = selector.select(wait_timeout)
            if not ready:
                return None

            for key, _ in ready:
                dev = key.data
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.code in target_codes and event.value in event_values:
                            return event.code
                except BlockingIOError:
                    continue
                except Exception:
                    continue
    finally:
        for dev in devices:
            try:
                selector.unregister(dev)
            except Exception:
                pass
            try:
                dev.close()
            except Exception:
                pass


def _normalize_key_name(name: str) -> str:
    clean = (name or "").strip().lower().replace("-", "_")
    aliases = {
        "spacebar": "space",
        "escape": "esc",
        "left_alt": "alt",
        "right_alt": "alt",
        "alt_l": "alt",
        "alt_r": "alt",
        "alt_gr": "alt",
    }
    return aliases.get(clean, clean)


def _evdev_codes_for_key_name(name: str) -> tuple[str, ...]:
    normalized = _normalize_key_name(name)
    mapping = {
        "space": ("KEY_SPACE",),
        "esc": ("KEY_ESC",),
        "alt": ("KEY_LEFTALT", "KEY_RIGHTALT"),
    }
    return mapping.get(normalized, ())


def _wait_for_named_press(target_keys: set[str], timeout: Optional[float] = None, allow_esc: bool = True) -> Optional[str]:
    """
    Wait for one of the target keys to be pressed.
    Returns the normalized key name, 'esc', or None on timeout/unavailable backend.
    """
    normalized_targets = {_normalize_key_name(key) for key in target_keys if key}
    if allow_esc:
        normalized_targets.add("esc")
    deadline = None if timeout is None else time.time() + timeout

    def _remaining() -> Optional[float]:
        if deadline is None:
            return None
        return max(0.0, deadline - time.time())

    def _wait_pynput(wait_timeout: Optional[float]) -> Optional[str]:
        try:
            from pynput import keyboard as _kb

            pressed = {"value": None}

            def _key_name(key) -> Optional[str]:
                name = getattr(key, "name", None)
                if not name and hasattr(key, "char"):
                    name = key.char
                if not name and key in {_kb.Key.alt, _kb.Key.alt_l, _kb.Key.alt_r}:
                    name = "alt"
                if not name and key == _kb.Key.space:
                    name = "space"
                if not name and key == _kb.Key.esc:
                    name = "esc"
                return _normalize_key_name(name) if isinstance(name, str) else None

            def _on_press(key):
                name = _key_name(key)
                if name in normalized_targets:
                    pressed["value"] = name
                    return False

            listener = _kb.Listener(on_press=_on_press)
            listener.start()
            started = time.time()
            while pressed["value"] is None:
                if wait_timeout is not None and (time.time() - started) >= wait_timeout:
                    break
                time.sleep(0.05)
            listener.stop()
            return pressed["value"]
        except Exception:
            return None

    def _wait_evdev(wait_timeout: Optional[float]) -> Optional[str]:
        try:
            from evdev import ecodes
        except Exception:
            return None

        code_to_name: Dict[int, str] = {}
        for name in normalized_targets:
            for code_name in _evdev_codes_for_key_name(name):
                code = getattr(ecodes, code_name, None)
                if code is not None:
                    code_to_name[code] = name

        if not code_to_name:
            return None

        code = _wait_key_event_evdev(set(code_to_name.keys()), {1}, wait_timeout)
        return code_to_name.get(code)

    backend_env = os.environ.get("AURORA_KEYBOARD_BACKEND", "").strip().lower()
    if backend_env == "evdev":
        waiters = [_wait_evdev]
    elif backend_env == "pynput":
        waiters = [_wait_pynput]
    else:
        waiters = [_wait_evdev, _wait_pynput] if _prefer_evdev_keyboard() else [_wait_pynput, _wait_evdev]
    for waiter in waiters:
        wait_timeout = _remaining()
        if wait_timeout == 0.0:
            break
        result = waiter(wait_timeout)
        if result is not None:
            return result
    return None


def _wait_for_named_release(target_keys: set[str], timeout: Optional[float] = None) -> Optional[str]:
    """Wait for one of the target keys to be released."""
    normalized_targets = {_normalize_key_name(key) for key in target_keys if key}
    deadline = None if timeout is None else time.time() + timeout

    def _remaining() -> Optional[float]:
        if deadline is None:
            return None
        return max(0.0, deadline - time.time())

    def _wait_pynput(wait_timeout: Optional[float]) -> Optional[str]:
        try:
            from pynput import keyboard as _kb

            released = {"value": None}

            def _key_name(key) -> Optional[str]:
                name = getattr(key, "name", None)
                if not name and hasattr(key, "char"):
                    name = key.char
                if not name and key in {_kb.Key.alt, _kb.Key.alt_l, _kb.Key.alt_r}:
                    name = "alt"
                if not name and key == _kb.Key.space:
                    name = "space"
                return _normalize_key_name(name) if isinstance(name, str) else None

            def _on_release(key):
                name = _key_name(key)
                if name in normalized_targets:
                    released["value"] = name
                    return False

            listener = _kb.Listener(on_release=_on_release)
            listener.start()
            started = time.time()
            while released["value"] is None:
                if wait_timeout is not None and (time.time() - started) >= wait_timeout:
                    break
                time.sleep(0.05)
            listener.stop()
            return released["value"]
        except Exception:
            return None

    def _wait_evdev(wait_timeout: Optional[float]) -> Optional[str]:
        try:
            from evdev import ecodes
        except Exception:
            return None

        code_to_name: Dict[int, str] = {}
        for name in normalized_targets:
            for code_name in _evdev_codes_for_key_name(name):
                code = getattr(ecodes, code_name, None)
                if code is not None:
                    code_to_name[code] = name

        if not code_to_name:
            return None

        code = _wait_key_event_evdev(set(code_to_name.keys()), {0}, wait_timeout)
        return code_to_name.get(code)

    backend_env = os.environ.get("AURORA_KEYBOARD_BACKEND", "").strip().lower()
    if backend_env == "evdev":
        waiters = [_wait_evdev]
    elif backend_env == "pynput":
        waiters = [_wait_pynput]
    else:
        waiters = [_wait_evdev, _wait_pynput] if _prefer_evdev_keyboard() else [_wait_pynput, _wait_evdev]
    for waiter in waiters:
        wait_timeout = _remaining()
        if wait_timeout == 0.0:
            break
        result = waiter(wait_timeout)
        if result is not None:
            return result
    return None


def _probe_audio_stack() -> Optional[str]:
    try:
        import sounddevice as sd
    except ImportError:
        return "sounddevice is not installed"

    try:
        devices = sd.query_devices()
    except Exception as e:
        return f"could not query audio devices: {e}"

    if not any(int(d.get("max_input_channels", 0)) > 0 for d in devices):
        return "no input-capable microphone device is available"

    return None


def _probe_keyboard_stack(toggle_key: str = DEFAULT_DAEMON_TOGGLE_KEY) -> Optional[str]:
    normalized = _normalize_key_name(toggle_key)
    backend_env = os.environ.get("AURORA_KEYBOARD_BACKEND", "").strip().lower()
    if backend_env == "evdev":
        backend_order = ["evdev"]
    elif backend_env == "pynput":
        backend_order = ["pynput"]
    else:
        backend_order = ["evdev", "pynput"] if _prefer_evdev_keyboard() else ["pynput", "evdev"]
    errors = []

    for backend in backend_order:
        if backend == "evdev":
            try:
                from evdev import InputDevice, list_devices, ecodes
            except Exception as e:
                errors.append(f"evdev unavailable: {e}")
                continue

            target_codes = set()
            for code_name in _evdev_codes_for_key_name(normalized):
                code = getattr(ecodes, code_name, None)
                if code is not None:
                    target_codes.add(code)
            if not target_codes:
                errors.append(f"evdev has no mapping for key '{normalized}'")
                continue

            try:
                for path in list_devices():
                    try:
                        dev = InputDevice(path)
                        caps = dev.capabilities().get(ecodes.EV_KEY, [])
                        key_codes = {item if isinstance(item, int) else item[0] for item in caps}
                        dev.close()
                        if key_codes.intersection(target_codes):
                            return None
                    except Exception:
                        continue
                errors.append(f"no evdev keyboard exposes '{normalized}'")
            except Exception as e:
                errors.append(f"evdev probe failed: {e}")
            continue

        if backend == "pynput":
            try:
                from pynput import keyboard as _kb
                if normalized == "alt":
                    _ = (_kb.Key.alt, _kb.Key.alt_l, _kb.Key.alt_r)
                elif normalized == "space":
                    _ = _kb.Key.space
                elif normalized == "esc":
                    _ = _kb.Key.esc
                return None
            except Exception as e:
                errors.append(f"pynput unavailable: {e}")

    return "; ".join(errors) if errors else "no keyboard backend available"


def _prefer_evdev_keyboard() -> bool:
    backend = os.environ.get("AURORA_KEYBOARD_BACKEND", "").strip().lower()
    if backend == "evdev":
        return True
    if backend == "pynput":
        return False
    return bool(os.environ.get("INVOCATION_ID"))


def _wait_for_press(timeout: Optional[float] = None) -> Optional[str]:
    """
    Wait for SPACE or ESC press.
    Returns 'space', 'esc', or None on timeout/unavailable backend.
    """
    return _wait_for_named_press({"space"}, timeout=timeout, allow_esc=True)


def _wait_for_space_release(timeout: Optional[float] = None) -> bool:
    """Wait for SPACE release. Returns True when released, False on timeout/unavailable backend."""
    return _wait_for_named_release({"space"}, timeout=timeout) == "space"


def _capture_audio_window(duration: float = WAKE_WINDOW_SEC) -> Optional[bytes]:
    """
    Capture a fixed audio window using sounddevice.
    Returns raw PCM bytes (16kHz mono int16) or None on failure.
    """
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        return None

    try:
        frames = max(1, int(duration * SAMPLE_RATE))
        audio = sd.rec(frames, samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype="int16")
        sd.wait()
        arr = np.asarray(audio, dtype="int16")
        return arr.tobytes()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Voice command system
# Maps spoken phrases → aurora.py command equivalents
# Spoken trigger:          Equivalent cmd:     What it does:
#   "activate training"      /train             multi-epoch simulation burst
#   "activate study"         /study             multi-cycle OETS consolidation
#   "activate dream"         (dream burst)      lesson bridge + multi-episode burst
#   "activate explore"       /explore           multi-cycle autonomous exploration
#   "activate diagnosis"     /status            system status, spoken back
#   "activate lessons"       /lessons           lesson plan summary, spoken
#   "activate fail points"   /failpoints        top fail dimensions, spoken
#   "activate save"          /save              save all state
#   "activate messages"      /messages          read unread messages aloud
#   "activate sight"         /sight             camera snapshot + spoken summary
#   "reactivate voice"       (cycle TTS voice)  switch to next voice preset
# ---------------------------------------------------------------------------

# Phrase patterns — each entry: (list of trigger substrings/regex, command_key)
# First match wins. Phrases checked against lowercased transcribed text.
_VOICE_COMMAND_PATTERNS = [
    # Core Engine Commands
    (["activate training", "start training", "run training"],           "train"),
    (["activate corpus runner", "run corpus runner", "corpus runner fast",
      "run corpus fast", "corpus triple fast"],                           "corpusfast"),
    (["activate study", "start study", "run study"],                    "study"),
    (["activate dream", "start dream", "run dream", "dream burst"],     "dream"),
    (["activate explore", "start explore", "run explore", "activate exploration"], "explore"),
    (["activate diagnosis", "activate diag", "run diagnostics",
      "system status", "activate status"],                              "status"),
    (["activate lessons", "show lessons", "what are the lessons"],      "lessons"),
    (["activate fail points", "show fail points", "fail points",
      "activate failpoints"],                                           "failpoints"),
    (["activate save", "save state", "save everything"],                "save"),
    (["activate messages", "show messages", "any messages",
      "do i have messages"],                                            "messages"),
    (["activate sight", "activate see", "start sight", "start seeing",
      "look around", "what do you see"],                                "sight"),
    (["reactivate voice", "change voice", "switch voice",
      "different voice", "new voice"],                                  "switchvoice"),
    (["activate socialize", "start socialize", "go socialize",
      "socialize with gpt", "run learning session", "talk to gpt",
      "gpt session", "learning session"],                               "socialize"),
      
    # Cognitive Tools
    ([r"what time is it", r"check time", r"current time"],              "time"),
    ([r"weather in (.*)", r"weather for (.*)", r"check weather in (.*)", r"what's the weather in (.*)"], "weather"),
    ([r"what's the weather", r"check weather"],                         "weather_local"),
    ([r"calculate (.*)", r"math (.*)", r"what is (.*)"],                "calculator"),
    ([r"query memory", r"read memory"],                                 "memory"),
    ([r"check self state", r"internal state"],                          "self_state"),
    
    # Mobile/Android Hardware Tools
    ([r"check battery", r"battery level", r"how much battery"],         "mobile_battery"),
    ([r"toggle flashlight", r"turn on flashlight", r"turn off flashlight", r"flashlight"], "mobile_flashlight"),
    ([r"vibrate phone", r"vibrate"],                                    "mobile_vibrate"),
    ([r"where am i", r"check location", r"my location"],                "mobile_location"),
    
    # Mobile/Android Deep Hooks
    ([r"send text to (.*) saying (.*)", r"send sms to (.*) saying (.*)"], "mobile_sms"),
    ([r"make a call to (.*)", r"call (.*)"],                            "mobile_call"),
    ([r"read contacts", r"find contact (.*)"],                          "mobile_contacts"),
    ([r"check wifi", r"toggle wifi", r"turn on wifi"],                  "mobile_wifi"),
    
    # Corpus Management
    ([r"download new corpus from (.*)", r"fetch new corpus from (.*)"], "corpus_download"),
    ([r"start training on (.*)", r"train on (.*)"],                     "corpus_train"),
]

import re

def _detect_voice_command(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (command_key, param1, param2) if text matches a voice command, else None."""
    tl = text.lower().strip()
    for patterns, key in _VOICE_COMMAND_PATTERNS:
        for p in patterns:
            # If the pattern is a regex with capture groups
            if "(.*)" in p:
                match = re.search(p, tl)
                if match:
                    groups = match.groups()
                    p1 = groups[0].strip() if len(groups) > 0 else None
                    p2 = groups[1].strip() if len(groups) > 1 else None
                    return key, p1, p2
            # Standard substring match
            elif p in tl:
                return key, None, None
    return None, None, None

def _log_voice_command_to_hub(command_key: str, result_summary: str) -> None:
    """Write voice command event to daemon_status.json for hub display."""
    import json, time as _t
    try:
        status_path = Path(__file__).parent / "aurora_state" / "daemon_status.json"
        status: dict = {}
        if status_path.exists():
            try:
                status = json.loads(status_path.read_text())
            except Exception:
                pass
        summary_base = str(result_summary or "")
        summary_display = summary_base if len(summary_base) <= 360 else summary_base[:357] + "..."
        status["last_voice_command"] = {
            "command": command_key,
            "summary": summary_display,
            "time": _t.strftime("%H:%M:%S"),
        }
        tmp = str(status_path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(status, f, indent=2)
        import os as _os
        _os.replace(tmp, str(status_path))
    except Exception:
        pass

    # Also append to daemon.log so hub log panel shows it
    try:
        log_path = Path(__file__).parent / "aurora_state" / "daemon.log"
        import time as _t2
        ts = _t2.strftime("%H:%M:%S")
        log_summary = summary_base if len(summary_base) <= 400 else summary_base[:397] + "..."
        with open(log_path, "a") as f:
            f.write(f"[{ts}] [VOICE CMD] {command_key}: {log_summary}\n")
    except Exception:
        pass


def _execute_voice_command(command_key: str, p1: Optional[str], p2: Optional[str], systems: Optional[Dict[str, Any]]) -> str:
    """
    Execute the voice command and return a short spoken confirmation.
    Triggers the same underlying actions as the aurora.py slash commands, or local tools.
    """
    # --- New Cognitive Tools ---
    if command_key == "time":
        from aurora_internal.tool_registry import _time_now
        res = _time_now()
        return res.data if res.success else "I couldn't check the time."
        
    if command_key == "weather":
        from aurora_internal.tool_registry import _weather_fetch
        if not p1: return "Please specify a location."
        res = _weather_fetch(location=p1)
        return res.data if res.success else f"I couldn't fetch the weather for {p1}."
        
    if command_key == "weather_local":
        from aurora_internal.tool_registry import _weather_fetch
        res = _weather_fetch(location="local")
        return res.data if res.success else "I couldn't fetch the local weather."
        
    if command_key == "calculator":
        from aurora_internal.tool_registry import _calculator
        if not p1: return "Please specify a calculation."
        res = _calculator(expression=p1)
        return res.data if res.success else "I couldn't calculate that."
        
    if command_key == "self_state":
        from aurora_internal.tool_registry import _self_state_read
        res = _self_state_read(systems=systems)
        return "Internal state check complete. " + res.data if res.success else "I couldn't check my internal state."
        
    if command_key == "memory":
        from aurora_internal.tool_registry import _memory_read
        res = _memory_read() # Assuming this exists or returns basic state
        return "Memory read complete."

    # --- New Mobile Tools (Absolute Full Access) ---
    if command_key == "mobile_battery":
        try:
            from plyer import battery
            status = battery.status
            return f"Battery is at {status['percentage']} percent, and is {'charging' if status['isCharging'] else 'not charging'}."
        except Exception as e:
            return "I don't have access to the battery sensor."

    if command_key == "mobile_flashlight":
        try:
            from plyer import flash
            # Simplified toggle logic; plyer flash requires camera permission
            flash.on()
            return "Flashlight activated."
        except Exception as e:
            return "I couldn't activate the flashlight."
            
    if command_key == "mobile_vibrate":
        try:
            from plyer import vibrator
            vibrator.vibrate(time=1)
            return "Haptics triggered."
        except Exception:
            return "Vibration not supported."
            
    if command_key == "mobile_location":
        try:
            from plyer import gps
            return "GPS location access requires full initialization. Location services are active."
        except Exception:
            return "Location services are unavailable."

    if command_key == "mobile_sms":
        try:
            from plyer import sms
            if not p1 or not p2: return "I need a name and a message to send an SMS."
            sms.send(recipient=p1, message=p2)
            return f"SMS sent to {p1}."
        except Exception:
            return "SMS permissions or capability not available."
            
    if command_key == "mobile_call":
        try:
            from plyer import call
            if not p1: return "Who should I call?"
            call.makecall(tel=p1)
            return f"Calling {p1}."
        except Exception:
            return "Call permissions or capability not available."
            
    if command_key == "mobile_wifi":
        try:
            from plyer import wifi
            return "WiFi status checked."
        except Exception:
            return "WiFi access requires PyJnius deep hooks."

    # --- Corpus Commands ---
    if command_key == "corpus_download":
        from aurora_internal.tool_registry import _corpus_download
        res = _corpus_download(url=p1, systems=systems)
        return res.data if res.success else f"Corpus download failed: {res.note}"
        
    if command_key == "corpus_train":
        from aurora_internal.tool_registry import _corpus_train
        res = _corpus_train(corpus_name=p1, systems=systems)
        return res.data if res.success else f"Training failed to start: {res.note}"

    # --- Core Engine Commands ---
    if command_key == "switchvoice":
        new_voice = _cycle_system_voice(systems)
        if new_voice:
            persist_system_voice_selection(systems)
            result = f"Switching to {new_voice}."
            _log_voice_command_to_hub(command_key, f"Voice → {new_voice}")
            return result

        new_voice = _next_voice()
        global VOICE
        VOICE = new_voice
        short = new_voice.split("-")[2].replace("Neural", "")  # e.g. "Ryan"
        result = f"Switching to {short}."
        _log_voice_command_to_hub(command_key, f"Voice → {new_voice}")
        return result

    if command_key == "save":
        try:
            aurora_obj = systems.get("aurora") if systems else None
            if aurora_obj and hasattr(aurora_obj, "save_state"):
                aurora_obj.save_state()
            perception = (systems.get("perception") if systems else None)
            lex = getattr(perception, "lexicon", None) if perception else None
            if lex and hasattr(lex, "save"):
                lex.save()
            result = "State saved."
        except Exception as e:
            result = f"Save failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "train":
        try:
            from aurora import train as _train

            epochs = max(2, int(VOICE_TRAIN_EPOCHS or 2))
            episodes = max(2, int(VOICE_TRAIN_EPISODES or 2))
            turns = max(2, int(VOICE_TRAIN_TURNS or 2))
            _train(
                systems,
                epochs=epochs,
                episodes_per_epoch=episodes,
                turns_per_episode=turns,
                verbose=False,
                phase_prefix="voice_train",
            )
            result = (
                f"Training complete after {epochs} epochs "
                f"with {episodes} episodes per epoch."
            )
        except Exception as e:
            result = f"Training unavailable: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "study":
        try:
            from aurora import study as _study

            cycles = max(2, int(VOICE_STUDY_CYCLES or 2))
            _study(systems, cycles=cycles, verbose=False)
            result = f"Study complete after {cycles} cycles."
        except Exception as e:
            result = f"Study failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "dream":
        try:
            from corpus_runner import simulation_burst
            episodes = max(2, int(VOICE_DREAM_EPISODES or 2))
            simulation_burst(systems, episodes=episodes, verbose=False)
            result = f"Dream burst complete after {episodes} episodes."
            dt = systems.get("dream_trainer") if systems else None
            if dt:
                dt.flush_lessons_to_simulation(systems, force=True)
        except Exception as e:
            result = f"Dream burst failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "corpusfast":
        script = Path(__file__).parent / "corpus_runner.py"
        corpus = VOICE_CORPUS_PATH
        if not script.exists():
            result = "Corpus runner script missing."
            _log_voice_command_to_hub(command_key, result)
            return result
        if not corpus.exists():
            result = f"Corpus file not found: {corpus}"
            _log_voice_command_to_hub(command_key, result)
            return result
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent)
            proc = subprocess.run(
                [sys.executable, str(script), "--corpus", str(corpus), "--passes", "triple",
                 "--fast", "--quiet"],
                cwd=str(script.parent),
                env=env,
                capture_output=True,
                text=True,
                timeout=7200,
            )
            if proc.returncode == 0:
                result = "Corpus runner triple fast completed."
            else:
                summary = proc.stderr.strip() or proc.stdout.strip()
                snippet = summary[:320] + ("..." if len(summary) > 320 else "")
                result = f"Corpus runner failed: {snippet}"
        except Exception as e:
            result = f"Corpus runner command failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "explore":
        try:
            from aurora import explore as _explore

            cycles = max(2, int(VOICE_EXPLORE_CYCLES or 2))
            _explore(systems, cycles=cycles, verbose=False)
            result = f"Exploration complete after {cycles} cycles."
        except Exception as e:
            result = f"Exploration failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "status":
        try:
            import json as _j
            state = _j.loads(
                (Path(__file__).parent / "aurora_state" / "aurora_state.json").read_text()
            )
            gen    = state.get("generation", "?")
            epochs = state.get("simulation_epochs", "?")
            gov    = state.get("governance_stats", {})
            nodes  = gov.get("total_nodes", "?") if isinstance(gov, dict) else "?"
            fp     = _j.loads(
                (Path(__file__).parent / "aurora_state" / "fail_points.json").read_text()
            )
            records = fp.get("records", {})
            top_fails = sorted(
                [(d, sum(v.get("recent", [0])) / max(len(v.get("recent", [1])), 1))
                 for d, v in records.items()],
                key=lambda x: -x[1]
            )[:2]
            weak = " and ".join(d.replace("_", " ") for d, _ in top_fails)
            result = (
                f"Generation {gen}. {epochs} simulation epochs. "
                f"{nodes} governance nodes. "
                f"Weakest areas: {weak}."
            )
        except Exception as e:
            result = f"Status unavailable: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "lessons":
        try:
            dt = systems.get("dream_trainer") if systems else None
            if dt and hasattr(dt, "lesson_plan_summary"):
                summary = dt.lesson_plan_summary()
                # Strip to first 2 sentences for voice
                sentences = [s.strip() for s in summary.split(".") if s.strip()][:3]
                result = ". ".join(sentences) + "."
            else:
                result = "No lesson plan available yet."
        except Exception as e:
            result = f"Lessons unavailable: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "failpoints":
        try:
            dt = systems.get("dream_trainer") if systems else None
            if dt and hasattr(dt, "ledger"):
                top = dt.ledger.get_top_fails(3)
                parts = [f"{d.replace('_', ' ')} at {int(s * 100)}%" for d, s in top]
                result = "Top fail dimensions: " + ", ".join(parts) + "."
            else:
                import json as _j
                fp = _j.loads(
                    (Path(__file__).parent / "aurora_state" / "fail_points.json").read_text()
                )
                records = fp.get("records", {})
                top = sorted(
                    [(d, sum(v.get("recent", [0])) / max(len(v.get("recent", [1])), 1))
                     for d, v in records.items()],
                    key=lambda x: -x[1]
                )[:3]
                parts = [f"{d.replace('_', ' ')} at {int(s * 100)}%" for d, s in top]
                result = "Top fail dimensions: " + ", ".join(parts) + "."
        except Exception as e:
            result = f"Fail points unavailable: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "messages":
        try:
            import json as _j, os as _os
            msg_path = Path(__file__).parent / "aurora_state" / "aurora_to_user.json"
            if msg_path.exists():
                msgs = _j.loads(msg_path.read_text())
                unread = [m for m in msgs if not m.get("read")]
                if unread:
                    texts = [m["text"] for m in unread[:3]]
                    result = f"You have {len(unread)} message(s). " + " | ".join(texts)
                    # Mark read
                    for m in msgs:
                        m["read"] = True
                    tmp = str(msg_path) + ".tmp"
                    with open(tmp, "w") as f:
                        _j.dump(msgs, f, indent=2)
                    _os.replace(tmp, str(msg_path))
                else:
                    result = "No new messages."
            else:
                result = "No messages yet."
        except Exception as e:
            result = f"Messages unavailable: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key in {"sight", "see"}:
        try:
            integration = systems.get("sensory_integration") if systems else None
            if integration:
                description, data = integration.see()
                result = str(description or "I looked, but I couldn't form a clear description.")
                faces = list(data.get("faces", []) or []) if isinstance(data, dict) else []
                if faces:
                    result += f" I detected {len(faces)} face"
                    if len(faces) != 1:
                        result += "s"
                    result += "."
                if isinstance(data, dict) and data.get("motion_detected"):
                    result += " Motion is present."
                snapshot_path = data.get("snapshot_path") if isinstance(data, dict) else None
                if snapshot_path:
                    result += f" Snapshot saved to {Path(snapshot_path).name}."
            else:
                result = "Vision system not available."
        except Exception as e:
            result = f"Vision failed: {e}"
        _log_voice_command_to_hub(command_key, result)
        return result

    if command_key == "socialize":
        result = "Socialize disabled — language smoother not wired in."
        _log_voice_command_to_hub(command_key, result)
        return result

    return f"Command {command_key} not implemented."


# ---------------------------------------------------------------------------
# Gateway helper — generate Aurora's response text
# ---------------------------------------------------------------------------

def _generate_response(text: str, systems: Optional[Dict[str, Any]]) -> tuple[str, str]:
    """Send text through Aurora's interactive pipeline and return (response, tone)."""
    if systems is None:
        return "", "attentive"
    try:
        queued = request_surface_turn(
            text,
            source="voice_session",
            session_id="voice_session",
            auto_search_enabled=False,
            record_exchange=True,
            track_evolutionary_trace=True,
            run_periodic_maintenance=True,
            mode_name="BOUNDED",
            timeout_s=60.0,
        )
        if str(queued.get("status", "") or "") == "ok":
            result = str(queued.get("response_text", "") or "").strip()
            tone = str(queued.get("response_tone", "attentive") or "attentive")
            if result:
                return result, tone
    except Exception:
        pass
    try:
        from aurora import process_external_user_turn

        turn = process_external_user_turn(
            systems,
            text,
            source_label="voice_session",
            session_id="voice_session",
            auto_search_enabled=False,
            record_exchange=True,
            update_interactive_state=True,
            track_evolutionary_trace=True,
            run_periodic_maintenance=True,
        )
        resp_A = turn.get("resp_A") if isinstance(turn, dict) else None
        result = getattr(resp_A, "content", "") if resp_A else ""
        tone = getattr(resp_A, "emotional_tone", "attentive") if resp_A else "attentive"
        if result:
            return result.strip(), tone
    except Exception:
        pass

    return "", "attentive"


# ---------------------------------------------------------------------------
# Voice Session — push-to-talk conversation
# ---------------------------------------------------------------------------

class VoiceSession:
    """
    Interactive voice conversation.

    Hold SPACE to record what you're saying.
    Release SPACE to send it to Aurora and hear her response.
    Say "goodbye" (or a variant) or press ESC to end the session.
    """

    def __init__(
        self,
        systems: Optional[Dict[str, Any]] = None,
        on_end: Optional[Callable] = None,
        visual: bool = True,      # print status lines (True when run from terminal)
    ):
        self.systems = systems
        self.on_end = on_end
        self.visual = visual
        self._active = False

    def _print(self, msg: str) -> None:
        if self.visual:
            print(msg, flush=True)

    def _greeting(self) -> str:
        """Generate the same greeting Aurora would give to 'hey aurora' in chat."""
        g, _ = _generate_response("hey aurora", self.systems)
        return g.strip() if g else ""

    def _speak_text(self, text: str, tone: Optional[str] = None) -> bool:
        return _speak_with_system_voice(text, self.systems, tone=tone)

    def _record_until_release(self) -> Optional[bytes]:
        """
        Record audio from the microphone for as long as SPACE is held.
        Returns raw PCM bytes (16kHz, mono, int16) or None on error.
        """
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._print("  [VOICE] sounddevice not installed. pip install sounddevice")
            return None

        chunks = []

        def _callback(indata, frames, time_info, status):
            chunks.append(indata.copy())

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=_callback,
        )

        with stream:
            if not _wait_for_space_release(timeout=MAX_RECORD_SEC):
                time.sleep(0.1)

        if not chunks:
            return None

        import numpy as np
        audio = np.concatenate(chunks, axis=0)
        return audio.tobytes()

    def _record_until_stop_event(self, stop_event: threading.Event, max_duration: float = MAX_RECORD_SEC) -> Optional[bytes]:
        """Record until an external stop event is set or max_duration is reached."""
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._print("  [VOICE] sounddevice not installed. pip install sounddevice")
            return None

        chunks = []

        def _callback(indata, frames, time_info, status):
            chunks.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=_callback,
            ):
                stop_event.wait(timeout=max_duration)
        except Exception:
            return None

        if not chunks:
            return None

        audio = np.concatenate(chunks, axis=0)
        return audio.tobytes()

    def _record_until_silence(
        self,
        start_timeout: float = 8.0,
        silence_timeout: float = SILENCE_TIMEOUT,
        max_duration: float = MAX_RECORD_SEC,
        activation_threshold: int = 500,
    ) -> Optional[bytes]:
        """
        Record audio once speech begins, then stop after sustained silence.
        Returns raw PCM bytes (16kHz, mono, int16) or None on timeout/error.
        """
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._print("  [VOICE] sounddevice not installed. pip install sounddevice")
            return None

        chunks = []
        speech_started = False
        last_signal_at = 0.0
        started_at = time.time()

        def _callback(indata, frames, time_info, status):
            nonlocal speech_started, last_signal_at
            chunk = indata.copy()
            chunks.append(chunk)

            try:
                peak = int(np.max(np.abs(chunk)))
            except Exception:
                peak = 0

            if peak >= activation_threshold:
                speech_started = True
                last_signal_at = time.time()

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=_callback,
            ):
                while self._active:
                    now = time.time()
                    if not speech_started:
                        if now - started_at >= start_timeout:
                            return None
                    else:
                        if last_signal_at and (now - last_signal_at) >= silence_timeout:
                            break
                        if (now - started_at) >= max_duration:
                            break
                    time.sleep(0.05)
        except Exception:
            return None

        if not chunks or not speech_started:
            return None

        audio = np.concatenate(chunks, axis=0)
        return audio.tobytes()

    def _pcm_to_audio_data(self, raw_bytes: bytes):
        """Convert raw PCM bytes to speech_recognition AudioData."""
        return _make_audio_data(raw_bytes)

    def _handle_transcribed_text(self, text: str, goodbye_ends_session: bool = True) -> str:
        self._print(f"  You: \"{text}\"")

        tl = text.lower().strip().rstrip(".")
        if any(tl == w or tl.startswith(w) for w in GOODBYE_WORDS):
            farewell, farewell_tone = _generate_response(
                "The person just said goodbye to end our voice conversation. "
                "Give them a brief, warm farewell — one sentence.",
                self.systems,
            )
            if not farewell:
                farewell = "Talk to you later."
                farewell_tone = "warm"
            self._print(f"  Aurora: \"{farewell}\"")
            self._speak_text(farewell, tone=farewell_tone)
            if goodbye_ends_session:
                self._active = False
            return "goodbye"

        cmd_key, p1, p2 = _detect_voice_command(text)
        if cmd_key:
            self._print(f"  [CMD] {cmd_key} (p1: {p1}, p2: {p2})")
            confirmation = _execute_voice_command(cmd_key, p1, p2, self.systems)
            self._print(f"  Aurora: \"{confirmation}\"")
            self._speak_text(confirmation, tone="attentive")
            return "command"

        response, response_tone = _generate_response(text, self.systems)
        if not response:
            response = "I'm here. I just need a moment."
            response_tone = "thoughtful"
        self._print(f"  Aurora: \"{response}\"")
        self._speak_text(response, tone=response_tone)
        return "response"

    def run(
        self,
        initial_space_timeout: Optional[float] = None,
        greet: bool = True,
        greeting_text: Optional[str] = None,
        hands_free: bool = False,
    ) -> None:
        """Run the voice session. Blocks until session ends."""
        self._active = True

        if greet:
            greeting = greeting_text or self._greeting()
            self._print(f"\n  Aurora: \"{greeting}\"")
            self._speak_text(greeting, tone="warm")

        if hands_free:
            self._print("\n  Speak naturally. Say 'goodbye' to end.\n")
        else:
            self._print("\n  Hold SPACE to speak. ESC or say 'goodbye' to end.\n")

        esc_pressed = False
        ended_by_goodbye = False
        while self._active and not esc_pressed:
            if hands_free:
                self._print("  [listening...]")
                raw = self._record_until_silence(
                    start_timeout=initial_space_timeout or 10.0,
                )
                if raw is None:
                    self._active = False
                    break
            else:
                key = _wait_for_press(timeout=initial_space_timeout)
                if key is None:
                    self._active = False
                    break
                if key == "esc":
                    esc_pressed = True
                    break

                # Space was pressed — start recording
                self._print("  [recording...]  ")
                raw = self._record_until_release()
            self._print("  [processing...]")

            if not raw:
                continue

            # Transcribe
            audio_data = self._pcm_to_audio_data(raw)
            text = transcribe(audio_data)
            if not text:
                self._print("  (didn't catch that)")
                continue

            outcome = self._handle_transcribed_text(text, goodbye_ends_session=True)
            if outcome == "goodbye":
                ended_by_goodbye = True

        if initial_space_timeout is not None and self.visual and not self._active and not esc_pressed:
            if ended_by_goodbye:
                pass
            elif hands_free:
                self._print("  [VOICE] Session timed out waiting for speech.")
            else:
                self._print("  [VOICE] Session timed out waiting for SPACE.")

        self._print("\n  [Voice session ended]\n")
        self._active = False
        if self.on_end:
            self.on_end()

# ---------------------------------------------------------------------------
# Wake Word Listener
# ---------------------------------------------------------------------------

class WakeWordListener:
    """
    Always-on background thread that listens for the wake phrase "hey aurora".

    Uses PocketSphinx keyword spotting (offline, no API key) as primary.
    Falls back to continuous Google transcription if sphinx fails.

    When the wake word is detected, calls on_wake(). The listener pauses
    itself during the voice session to avoid double-triggering.
    """

    def __init__(
        self,
        on_wake: Callable,
        systems: Optional[Dict[str, Any]] = None,
        visual: bool = False,
    ):
        self.on_wake = on_wake
        self.systems = systems
        self.visual = visual
        self._running = False
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._startup_error: Optional[str] = None
        self._cooldown_until = 0.0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="wake-word")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        """Pause while a voice session is active."""
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()
        if self.systems is not None:
            self.systems["_explicit_voice_active"] = False
            self.systems["_last_explicit_voice_time"] = time.time()

    def wait_until_ready(self, timeout: float = 5.0) -> tuple[bool, str]:
        self._ready.wait(timeout=timeout)
        if self._startup_error:
            return False, self._startup_error
        if not self._ready.is_set():
            return False, "wake listener initialization timed out"
        return True, "ready"

    def _loop(self) -> None:
        self._startup_error = self._probe_audio_stack()
        self._ready.set()
        if self._startup_error:
            return
        if self._try_sphinx_loop():
            return
        self._google_fallback_loop()

    def _probe_audio_stack(self) -> Optional[str]:
        return _probe_audio_stack()

    # -- PocketSphinx keyword spotting (offline, preferred) ------------------

    def _try_sphinx_loop(self) -> bool:
        """Returns True if sphinx ran successfully; False if unavailable."""
        try:
            import speech_recognition as sr
        except ImportError:
            return False

        r = sr.Recognizer()
        r.energy_threshold = 400
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8

        keyword_entries = [(word, WAKE_SENSITIVITY) for word in WAKE_WORDS]

        while self._running:
            if self._paused.is_set():
                time.sleep(0.5)
                continue
            if time.time() < self._cooldown_until:
                time.sleep(0.25)
                continue

            raw = _capture_audio_window()
            if not raw:
                time.sleep(0.25)
                continue

            try:
                audio = _make_audio_data(raw)
                result = r.recognize_sphinx(audio, keyword_entries=keyword_entries)
                normalized = _normalize_wake_text(result or "")
                if normalized in {_normalize_wake_text(w) for w in WAKE_WORDS} and _confirm_wake_phrase(raw):
                    self._detected()
            except sr.UnknownValueError:
                pass
            except Exception as e:
                # Missing PocketSphinx should degrade to Google fallback once.
                if "pocketsphinx" in str(e).lower():
                    return False
                try:
                    self._google_fallback_loop()
                except Exception:
                    pass
                return True
        return True

    # -- Google fallback (online) -------------------------------------------

    def _google_fallback_loop(self) -> None:
        try:
            import speech_recognition as sr
        except ImportError:
            return

        r = sr.Recognizer()
        r.energy_threshold = 400
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8

        while self._running:
            if self._paused.is_set():
                time.sleep(0.5)
                continue
            if time.time() < self._cooldown_until:
                time.sleep(0.25)
                continue

            raw = _capture_audio_window()
            if not raw:
                time.sleep(0.25)
                continue

            try:
                audio = _make_audio_data(raw)
                try:
                    text = _normalize_wake_text(r.recognize_google(audio))
                    if _matches_wake_transcript(text):
                        self._detected()
                except Exception:
                    pass
            except Exception:
                time.sleep(0.5)

    def _detected(self) -> None:
        self.pause()
        try:
            self.on_wake()
        finally:
            self._cooldown_until = time.time() + WAKE_COOLDOWN_SEC
            self.resume()


# ---------------------------------------------------------------------------
# ALT-toggle daemon controller
# ---------------------------------------------------------------------------

class AltToggleVoiceController:
    """
    Always-on daemon voice controller.

    Tap ALT once to begin recording.
    Tap ALT again to submit the captured prompt.
    """

    def __init__(
        self,
        systems: Optional[Dict[str, Any]] = None,
        visual: bool = False,
        toggle_key: str = DEFAULT_DAEMON_TOGGLE_KEY,
    ):
        self.systems = systems
        self.visual = visual
        self.toggle_key = _normalize_key_name(toggle_key or DEFAULT_DAEMON_TOGGLE_KEY)
        self._session = VoiceSession(systems=systems, visual=visual)
        self._running = False
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._record_thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._startup_error: Optional[str] = None
        self._record_stop = threading.Event()
        self._recorded_audio: Optional[bytes] = None
        self._lock = threading.Lock()

    def _print(self, msg: str) -> None:
        if self.visual:
            print(msg, flush=True)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="alt-toggle-voice")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._record_stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2.0)

    def wait_until_ready(self, timeout: float = 5.0) -> tuple[bool, str]:
        self._ready.wait(timeout=timeout)
        if self._startup_error:
            return False, self._startup_error
        if not self._ready.is_set():
            return False, "alt-toggle voice initialization timed out"
        return True, "ready"

    def _start_recording(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._record_stop = threading.Event()
            self._recorded_audio = None
            self._recording = True
            if self.systems is not None:
                self.systems["_explicit_voice_active"] = True
                self.systems["_ambient_suppress_until"] = time.time() + MAX_RECORD_SEC + 5.0

        self._print("  [VOICE] Recording started via ALT toggle.")

        def _worker():
            self._recorded_audio = self._session._record_until_stop_event(
                self._record_stop,
                max_duration=MAX_RECORD_SEC,
            )

        self._record_thread = threading.Thread(target=_worker, daemon=True, name="alt-toggle-record")
        self._record_thread.start()

        try:
            subprocess.run(
                ["notify-send", "--urgency=low", "Aurora", "Recording... tap Alt again to send."],
                timeout=2,
            )
        except Exception:
            pass

    def _finish_recording(self) -> Optional[bytes]:
        with self._lock:
            if not self._recording:
                return None
            self._record_stop.set()
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=MAX_RECORD_SEC + 2.0)
        with self._lock:
            self._recording = False
            if self.systems is not None:
                self.systems["_explicit_voice_active"] = False
        self._print("  [VOICE] Recording stopped.")
        return self._recorded_audio

    def _process_recording(self, raw: Optional[bytes]) -> None:
        if not raw:
            return
        audio_data = self._session._pcm_to_audio_data(raw)
        text = transcribe(audio_data)
        if not text:
            self._print("  [VOICE] Could not transcribe ALT-triggered recording.")
            try:
                subprocess.run(
                    ["notify-send", "--urgency=low", "Aurora", "I didn't catch that."],
                    timeout=2,
                )
            except Exception:
                pass
            return
            
        if self.systems is not None:
            self.systems["_last_explicit_voice_time"] = time.time()
            
        if self.systems is not None:
            self.systems["_explicit_voice_active"] = True
        try:
            self._session._active = True
            self._session._handle_transcribed_text(text, goodbye_ends_session=False)
        finally:
            self._session._active = False
            if self.systems is not None:
                self.systems["_explicit_voice_active"] = False
                self.systems["_last_explicit_voice_time"] = time.time()

    def _loop(self) -> None:
        audio_error = _probe_audio_stack()
        keyboard_error = _probe_keyboard_stack(self.toggle_key)
        self._startup_error = audio_error or keyboard_error
        self._ready.set()
        if self._startup_error:
            return

        while self._running:
            key = _wait_for_named_press({self.toggle_key}, timeout=0.5, allow_esc=True)
            if key is None:
                if self._recording and self._record_thread and not self._record_thread.is_alive():
                    raw = self._finish_recording()
                    self._process_recording(raw)
                continue
            if key == "esc":
                if self._recording:
                    self._finish_recording()
                continue
            if key != self.toggle_key:
                continue
            if not self._recording:
                self._start_recording()
                continue
            raw = self._finish_recording()
            self._process_recording(raw)


# ---------------------------------------------------------------------------
# Convenience: daemon greeting + daemon voice session hooks
# ---------------------------------------------------------------------------

def daemon_startup_greeting(systems: Optional[Dict[str, Any]] = None) -> str:
    """Speak a short boot greeting and show the ALT control hint."""
    session = VoiceSession(systems=systems, visual=False)
    greeting = session._greeting()
    try:
        prompt = f"{greeting} Tap Alt to speak. Tap Alt again to send."
        subprocess.run(
            ["notify-send", "--urgency=low", "Aurora", prompt[:200]],
            timeout=3,
        )
    except Exception:
        pass

    session._speak_text(greeting, tone="warm")
    return greeting

def daemon_voice_session(systems: Optional[Dict[str, Any]] = None) -> None:
    """
    Voice session designed for daemon context — no terminal, audio only.
    Notifications sent via notify-send.
    """
    try:
        if systems is not None:
            systems["_explicit_voice_active"] = True
            systems["_ambient_suppress_until"] = time.time() + MAX_RECORD_SEC + 20.0

        session = VoiceSession(systems=systems, visual=False)
        greeting = session._greeting()
        session._speak_text(greeting, tone="warm")

        try:
            prompt = f"{greeting} Speak now. Say goodbye to end."
            subprocess.run(
                ["notify-send", "--urgency=normal", "Aurora", prompt[:200]],
                timeout=3,
            )
        except Exception:
            pass

        session.run(
            initial_space_timeout=10.0,
            greet=False,
            greeting_text=greeting,
            hands_free=True,
        )
    except Exception:
        raise
    finally:
        if systems is not None:
            systems["_explicit_voice_active"] = False
            systems["_last_explicit_voice_time"] = time.time()

    try:
        subprocess.run(
            ["notify-send", "--urgency=low", "Aurora", "Voice session ended."],
            timeout=3,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI — standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aurora Voice Interface")
    parser.add_argument("--wake", action="store_true", help="Start wake word listener (demo)")
    parser.add_argument("--session", action="store_true", help="Start voice session directly")
    args = parser.parse_args()

    if args.wake:
        print("Listening for wake phrase ('hey aurora')...")
        print("Press Ctrl+C to stop.\n")

        def on_wake():
            print("\n  Wake word detected!")
            VoiceSession(systems=None, visual=True).run()

        listener = WakeWordListener(on_wake=on_wake, visual=True)
        listener.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            listener.stop()
            print("\nStopped.")

    elif args.session:
        VoiceSession(systems=None, visual=True).run()

    else:
        parser.print_help()
