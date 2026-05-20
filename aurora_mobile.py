#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_mobile.py — Full Aurora stack launcher for Termux / Android.

Boots the subsurface daemon (dreaming, studying, curiosity cycles) and the
surface daemon (conversation pipeline) as background subprocesses, then drives
an always-on wake-word + voice I/O loop on the main process via
aurora_hardware_io so you can talk to Aurora hands-free on your phone.

Say "aurora <anything>" and she responds. When idle she runs her own curiosity
and autonomy cycles in the background. Proactive messages from the subsurface
daemon are spoken aloud when they arrive.

Usage:
    cd /data/data/com.termux/files/home/aurora-   # or wherever the repo lives
    python aurora_mobile.py

Termux one-time setup:
    pkg install python termux-api
    pip install SpeechRecognition     # optional — improves transcription quality

File-based PTT (no mic or termux-api needed — works everywhere):
    echo '{"trigger":true,"text":"your message here"}' \\
        > aurora_state/voice_trigger.json

Suppress all audio output:
    touch aurora_state/quiet_mode

Platform override (auto-detected — override if needed):
    AURORA_PLATFORM=termux python aurora_mobile.py
    AURORA_PLATFORM=linux  python aurora_mobile.py
    AURORA_PLATFORM=headless python aurora_mobile.py
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Bootstrap: make sure aurora_core_ai is importable for HardwareIO etc.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE / "aurora_core_ai"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_STATE_DIR        = _HERE / "aurora_state"
_SURFACE_QUEUE    = _STATE_DIR / "surface_turn_queue.json"
_SURFACE_RESULT   = _STATE_DIR / "surface_turn_result.json"
_SURFACE_STATUS   = _STATE_DIR / "surface_daemon_status.json"
_SUBSURFACE_STATUS = _STATE_DIR / "subsurface_daemon_status.json"
_MESSAGES_FILE    = _STATE_DIR / "aurora_to_user.json"
_QUIET_FLAG       = _STATE_DIR / "quiet_mode"
_VOICE_TRIGGER    = _STATE_DIR / "voice_trigger.json"
_LOG_FILE         = _STATE_DIR / "mobile_runner.log"

_STATE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_SURFACE_BOOT_TIMEOUT  = 120.0   # max seconds to wait for surface to reach idle
_RESPONSE_POLL_TIMEOUT = 60.0    # max seconds to wait for a turn result
_RESPONSE_POLL_SLEEP   = 0.2
_PROACTIVE_POLL_SLEEP  = 5.0     # how often to check for proactive messages
_CURIOSITY_INTERRUPT   = True    # interrupt curiosity cycles on each user turn


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _log(msg: str) -> None:
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _is_quiet() -> bool:
    return _QUIET_FLAG.exists()


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any) -> None:
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Surface turn queue — queue a voice utterance for the surface daemon
# ---------------------------------------------------------------------------
def _queue_turn(
    text: str,
    *,
    source: str = "mobile_voice",
) -> str:
    state = _read_json(_SURFACE_QUEUE, {"pending": []})
    if not isinstance(state, dict):
        state = {"pending": []}
    turn_id = f"mobile_{int(time.time() * 1000)}"
    pending = list(state.get("pending") or [])
    pending.append({
        "id": turn_id,
        "content": text,
        "source": source,
        "session_id": "mobile",
        "status": "queued",
        "created_at": time.time(),
        "auto_search_enabled": True,
        "record_exchange": True,
        "update_interactive_state": True,
        "track_evolutionary_trace": True,
        "run_periodic_maintenance": True,
        "mode_name": "BOUNDED",
    })
    state["pending"] = pending
    _write_json(_SURFACE_QUEUE, state)
    return turn_id


def _await_turn_result(turn_id: str, timeout: float = _RESPONSE_POLL_TIMEOUT) -> Optional[str]:
    """Poll surface_turn_result.json until our turn_id appears. Returns response_text or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = _read_json(_SURFACE_RESULT, {})
        if isinstance(data, dict) and str(data.get("id", "") or "") == turn_id:
            return str(data.get("response_text", "") or "").strip()
        time.sleep(_RESPONSE_POLL_SLEEP)
    return None


# ---------------------------------------------------------------------------
# Daemon subprocess management
# ---------------------------------------------------------------------------

_PROCS: List[subprocess.Popen] = []


def _start_daemon(script_name: str, label: str) -> Optional[subprocess.Popen]:
    script = _HERE / script_name
    if not script.exists():
        _log(f"  [{label}] Script not found: {script_name} — skipping.")
        return None
    try:
        env = dict(os.environ)
        # Ensure repo root is in PYTHONPATH for both daemons
        existing_pp = env.get("PYTHONPATH", "")
        paths = [str(_HERE), str(_HERE / "aurora_core_ai")]
        env["PYTHONPATH"] = os.pathsep.join(paths + ([existing_pp] if existing_pp else []))
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(_HERE),
            env=env,
        )
        _PROCS.append(proc)
        _log(f"  [{label}] Started (pid={proc.pid}).")
        return proc
    except Exception as e:
        _log(f"  [{label}] Failed to start: {e}")
        return None


def _wait_for_surface(timeout: float = _SURFACE_BOOT_TIMEOUT) -> bool:
    """Block until surface daemon reports 'idle' or timeout."""
    _log("  [BOOT] Waiting for surface daemon to reach idle state...")
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        data = _read_json(_SURFACE_STATUS, {})
        state_name = str(data.get("state", "") or data.get("state_name", "") or "")
        if state_name in ("idle", "processing"):
            _log(f"  [BOOT] Surface daemon ready (state={state_name}).")
            return True
        time.sleep(1.0)
        dots += 1
        if dots % 5 == 0:
            elapsed = int(time.time() - (deadline - timeout))
            _log(f"  [BOOT] Still booting... ({elapsed}s)")
    return False


def _stop_all() -> None:
    _log("Shutting down daemon subprocesses...")
    for proc in _PROCS:
        try:
            proc.terminate()
        except Exception:
            pass
    # Give them a moment to flush state, then kill if needed
    deadline = time.time() + 8.0
    for proc in _PROCS:
        try:
            remaining = max(0.1, deadline - time.time())
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
        except Exception:
            pass
    _log("Daemon subprocesses stopped.")


# ---------------------------------------------------------------------------
# Curiosity cycle interrupt (if aurora_curiosity_engine is importable)
# ---------------------------------------------------------------------------

def _interrupt_curiosity() -> None:
    try:
        from aurora_curiosity_engine import interrupt_curiosity_cycles
        interrupt_curiosity_cycles()
    except Exception:
        pass


def _reset_curiosity() -> None:
    try:
        from aurora_curiosity_engine import reset_curiosity_interrupt
        reset_curiosity_interrupt()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Proactive message watcher — speak messages Aurora queued for you
# ---------------------------------------------------------------------------

_LAST_PROACTIVE_READ: int = 0


def _poll_proactive_messages(speak_fn) -> None:
    """Check aurora_to_user.json for unread proactive messages and speak them."""
    global _LAST_PROACTIVE_READ
    try:
        msgs = _read_json(_MESSAGES_FILE, [])
        if not isinstance(msgs, list):
            return
        unread = [m for m in msgs if isinstance(m, dict) and not m.get("read", False)]
        for msg in unread:
            text = str(msg.get("text", "") or "").strip()
            if not text:
                continue
            trigger = str(msg.get("trigger", "") or "")
            _log(f"  [AURORA] {text[:120]}")
            if not _is_quiet():
                speak_fn(text)
            msg["read"] = True
        if unread:
            _write_json(_MESSAGES_FILE, msgs)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# On-utterance callback — called by NameListener when aurora hears her name
# ---------------------------------------------------------------------------

def _make_on_utterance(speak_fn) -> Any:
    _in_flight = threading.Event()

    def _on_utterance(text: str) -> None:
        if _in_flight.is_set():
            return  # already processing a turn — drop duplicate
        _in_flight.set()
        try:
            text = text.strip()
            if not text:
                return
            _log(f"  [YOU] {text}")
            _interrupt_curiosity()

            turn_id = _queue_turn(text, source="mobile_voice")
            _log("  [AURORA] Thinking...")

            response = _await_turn_result(turn_id)
            if response:
                _log(f"  [AURORA] {response[:300]}")
                if not _is_quiet():
                    speak_fn(response)
            else:
                _log("  [AURORA] (no response within timeout)")

            _reset_curiosity()
        finally:
            _in_flight.clear()

    return _on_utterance


# ---------------------------------------------------------------------------
# HardwareIO setup
# ---------------------------------------------------------------------------

def _boot_hardware_io(speak_fn, on_utterance) -> Optional[Any]:
    """Import and start HardwareIO. Returns the HardwareIO instance or None."""
    try:
        # aurora_hardware_io.py lives in aurora_core_ai/ — already in sys.path
        from aurora_hardware_io import HardwareIO, PLATFORM, probe

        caps = probe()
        _log(f"  [HW] Platform: {PLATFORM.upper()}")
        _log(f"  [HW] Capabilities: tts={caps['tts']} stt={caps['stt']} "
             f"camera={caps['camera']} ambient_mic={caps['ambient_mic']} "
             f"file_ptt={caps['file_ptt']}")

        systems: Dict[str, Any] = {}  # minimal systems dict for HardwareIO
        hw = HardwareIO(systems=systems)

        hw.start(
            on_utterance=on_utterance,
            enable_ambient=caps.get("ambient_mic", False),
        )
        return hw
    except ImportError as e:
        _log(f"  [HW] aurora_hardware_io unavailable ({e}) — falling back to file PTT only.")
        return None
    except Exception as e:
        _log(f"  [HW] HardwareIO start failed: {e} — falling back to file PTT only.")
        return None


# ---------------------------------------------------------------------------
# File PTT fallback watcher (always active — no hardware needed)
# ---------------------------------------------------------------------------

def _start_file_ptt_watcher(on_utterance) -> threading.Thread:
    """
    Poll voice_trigger.json for manual text injection.
    Write {"trigger":true,"text":"..."} to send a turn without a microphone.
    """
    def _loop():
        last_mtime = 0.0
        while not _shutdown.is_set():
            try:
                if _VOICE_TRIGGER.exists():
                    mtime = _VOICE_TRIGGER.stat().st_mtime
                    if mtime > last_mtime:
                        last_mtime = mtime
                        raw = _VOICE_TRIGGER.read_text(encoding="utf-8")
                        data = json.loads(raw)
                        if data.get("trigger"):
                            _VOICE_TRIGGER.write_text(
                                json.dumps({"trigger": False}), encoding="utf-8"
                            )
                            text = str(data.get("text", "") or "").strip()
                            if text:
                                threading.Thread(
                                    target=on_utterance,
                                    args=(text,),
                                    daemon=True,
                                    name="mobile-ptt-dispatch",
                                ).start()
            except Exception:
                pass
            _shutdown.wait(0.5)

    t = threading.Thread(target=_loop, daemon=True, name="mobile-file-ptt")
    t.start()
    return t


# ---------------------------------------------------------------------------
# Proactive message poller
# ---------------------------------------------------------------------------

def _start_proactive_poller(speak_fn) -> threading.Thread:
    def _loop():
        while not _shutdown.is_set():
            _poll_proactive_messages(speak_fn)
            _shutdown.wait(_PROACTIVE_POLL_SLEEP)

    t = threading.Thread(target=_loop, daemon=True, name="mobile-proactive-poll")
    t.start()
    return t


# ---------------------------------------------------------------------------
# TTS fallback (if HardwareIO can't be imported)
# ---------------------------------------------------------------------------

def _make_speak_fn() -> Any:
    """Return a speak function using aurora_hardware_io if available, else print."""
    try:
        from aurora_hardware_io import speak as _hw_speak
        def _speak(text: str) -> None:
            try:
                _hw_speak(text, block=True)
            except Exception:
                pass
        return _speak
    except Exception:
        def _speak(text: str) -> None:
            print(f"[AURORA] {text}", flush=True)
        return _speak


# ---------------------------------------------------------------------------
# Shutdown coordination
# ---------------------------------------------------------------------------

_shutdown = threading.Event()


def _handle_signal(sig, _frame) -> None:
    _log(f"Signal {sig} received — shutting down.")
    _shutdown.set()


# ---------------------------------------------------------------------------
# Boot greeting
# ---------------------------------------------------------------------------

def _boot_greeting(speak_fn) -> None:
    greeting = (
        "Aurora mobile stack online. "
        "Say my name followed by anything on your mind, "
        "or write to voice_trigger.json to send a message without your mic."
    )
    _log(f"  [AURORA] {greeting}")
    if not _is_quiet():
        speak_fn(greeting)


# ---------------------------------------------------------------------------
# Status display (printed periodically to terminal)
# ---------------------------------------------------------------------------

def _print_status() -> None:
    surf = _read_json(_SURFACE_STATUS, {})
    sub  = _read_json(_SUBSURFACE_STATUS, {})
    surf_state = str(surf.get("state", surf.get("state_name", "?")) or "?")
    sub_state  = str(sub.get("phase", sub.get("state", "?")) or "?")
    _log(
        f"  [STATUS] surface={surf_state}  subsurface={sub_state}  "
        f"quiet={'on' if _is_quiet() else 'off'}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _log("=" * 56)
    _log("  A U R O R A  —  Mobile Runner")
    _log("  Authors: Sunni (Sir) Morningstar & Cael Devo")
    _log("=" * 56)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    # ── 1. Boot TTS first so greeting works ────────────────────────────────
    speak_fn = _make_speak_fn()

    # ── 2. Start subsurface daemon (dreaming, curiosity, autonomy) ─────────
    _log("[BOOT] Starting subsurface daemon...")
    sub_proc = _start_daemon("aurora_subsurface_daemon.py", "SUBSURFACE")

    # ── 3. Start surface daemon (conversation pipeline) ────────────────────
    _log("[BOOT] Starting surface daemon...")
    surf_proc = _start_daemon("aurora_surface_daemon.py", "SURFACE")

    # ── 4. Wait for surface daemon to reach idle ───────────────────────────
    ready = _wait_for_surface(_SURFACE_BOOT_TIMEOUT)
    if not ready:
        _log("[WARN] Surface daemon did not reach idle within timeout — continuing anyway.")

    # ── 5. Boot HardwareIO (wake-word + ambient mic + TTS) ─────────────────
    _log("[BOOT] Starting hardware I/O...")
    on_utterance = _make_on_utterance(speak_fn)
    hw = _boot_hardware_io(speak_fn, on_utterance)

    # ── 6. File PTT watcher — always-on regardless of HardwareIO ──────────
    _log("[BOOT] File PTT watcher active.")
    _log(f"  → To send text without mic: echo '{{\"trigger\":true,\"text\":\"hello\"}}' > {_VOICE_TRIGGER}")
    _start_file_ptt_watcher(on_utterance)

    # ── 7. Proactive message poller ────────────────────────────────────────
    _start_proactive_poller(speak_fn)

    # ── 8. Boot greeting ───────────────────────────────────────────────────
    _boot_greeting(speak_fn)

    # ── 9. Main loop — just keep threads alive, print periodic status ──────
    _log("[BOOT] Aurora mobile stack online. Press Ctrl-C to stop.")
    next_status = time.time() + 60.0

    while not _shutdown.is_set():
        # Check if daemon subprocesses are still alive
        for proc, label in [(sub_proc, "SUBSURFACE"), (surf_proc, "SURFACE")]:
            if proc is not None and proc.poll() is not None:
                _log(f"  [{label}] Daemon exited unexpectedly (code={proc.returncode}) — check logs.")

        if time.time() >= next_status:
            _print_status()
            next_status = time.time() + 60.0

        _shutdown.wait(1.0)

    # ── 10. Shutdown ──────────────────────────────────────────────────────
    if hw is not None:
        try:
            hw.stop()
        except Exception:
            pass

    _stop_all()
    _log("Aurora mobile runner stopped.")


if __name__ == "__main__":
    main()
