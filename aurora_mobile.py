#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_mobile.py — Aurora single-process mobile runner for Termux / Android.

Everything runs in ONE Python process — no subprocess daemons.

Architecture:
  • boot_aurora()                  — single stack boot, L0-L7+
  • start_curiosity_background()   — idle autonomy/dreaming in a bg thread
  • aurora_hardware_io.HardwareIO  — wake-word listener + TTS
  • file PTT watcher               — always-on text injection without a mic
  • proactive message poller       — speaks aurora_to_user.json entries aloud
  • ConnectivityMonitor            — detects online/offline transitions
  • ProvisionalStore               — holds things she's been told but not verified
  • gap surfacer                   — asks the user about open curiosity loops offline
  • offline turn queue             — re-processes failed turns on reconnect
  • periodic state saver           — flushes state every N minutes

Offline resilience:
  When search or LLM API calls fail because there's no internet, Aurora asks
  the user for help with whatever she was curious about.  Answers are stored as
  provisional knowledge at a confidence level tied to how reliable the user has
  proven to be.  When connectivity returns, queued items are re-verified.  If the
  user has been consistently correct, their answers are absorbed more faithfully
  without waiting for verification.

Usage:
    cd /data/data/com.termux/files/home/aurora-
    python aurora_mobile.py

File-based PTT (no mic needed):
    echo '{"trigger":true,"text":"your message here"}' > aurora_state/voice_trigger.json

Suppress audio:
    touch aurora_state/quiet_mode

Platform override (auto-detected):
    AURORA_PLATFORM=termux   python aurora_mobile.py
    AURORA_PLATFORM=linux    python aurora_mobile.py
    AURORA_PLATFORM=headless python aurora_mobile.py
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import threading
import traceback as _tb
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
_MESSAGES_FILE    = _STATE_DIR / "aurora_to_user.json"
_QUIET_FLAG       = _STATE_DIR / "quiet_mode"
_VOICE_TRIGGER    = _STATE_DIR / "voice_trigger.json"
_LOG_FILE         = _STATE_DIR / "mobile_runner.log"
_MOBILE_STATUS    = _STATE_DIR / "mobile_runner_status.json"
_OFFLINE_QUEUE    = _STATE_DIR / "offline_turn_queue.json"

_STATE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_PROACTIVE_POLL_SLEEP    = 5.0    # seconds between proactive-message checks
_STATE_SAVE_INTERVAL     = 300.0  # seconds between periodic state saves
_STATUS_PRINT_INTERVAL   = 120.0  # seconds between status log lines
_GAP_SURFACE_INTERVAL    = 600.0  # seconds between gap-surfacing attempts
_OFFLINE_RETRY_LIMIT     = 5      # max offline-queued turns to replay on reconnect
_PENDING_Q_WINDOW        = 300.0  # seconds after asking a question to accept any reply as its answer


# ---------------------------------------------------------------------------
# Shutdown coordination (declared early — used throughout)
# ---------------------------------------------------------------------------
_shutdown = threading.Event()


def _handle_signal(sig, _frame) -> None:
    _log(f"Signal {sig} received — shutting down.")
    _shutdown.set()


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
# Termux helpers
# ---------------------------------------------------------------------------
def _termux_vibrate(ms: int = 150) -> None:
    """Short vibration to confirm Aurora received a turn. Silently fails off-Termux."""
    try:
        import subprocess
        subprocess.Popen(
            ["termux-vibrate", "-d", str(ms)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Curiosity interrupt helpers
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
# TTS speak function (standalone — usable before systems is booted)
# ---------------------------------------------------------------------------
def _make_speak_fn() -> Any:
    """Return a platform-aware speak fn using aurora_hardware_io if available."""
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
# Extract response text from process_external_user_turn() result
# ---------------------------------------------------------------------------
def _extract_response(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result or "").strip()
    resp_a = result.get("resp_A")
    if resp_a is not None:
        content = getattr(resp_a, "content", None)
        if isinstance(content, list):
            parts = [
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
                for b in content
                if (isinstance(b, dict) and b.get("type") == "text")
                or (not isinstance(b, dict) and getattr(b, "type", "") == "text")
            ]
            text = " ".join(str(p) for p in parts if p).strip()
            if text:
                return text
        elif content:
            return str(content).strip()
    for key in ("response_text", "text", "answer"):
        val = result.get(key)
        if val:
            return str(val).strip()
    return ""


# ---------------------------------------------------------------------------
# Offline turn queue — save failed turns for replay on reconnect
# ---------------------------------------------------------------------------
def _queue_for_retry(text: str) -> None:
    try:
        queue = _read_json(_OFFLINE_QUEUE, [])
        if not isinstance(queue, list):
            queue = []
        queue.append({"text": text, "queued_at": time.time()})
        _write_json(_OFFLINE_QUEUE, queue)
    except Exception:
        pass


def _process_offline_queue(systems: Any, speak_fn) -> None:
    """Called when connectivity returns — replays queued turns (up to limit)."""
    try:
        queue = _read_json(_OFFLINE_QUEUE, [])
        if not isinstance(queue, list) or not queue:
            return
        _write_json(_OFFLINE_QUEUE, [])  # clear immediately to avoid double-play
        batch = queue[:_OFFLINE_RETRY_LIMIT]
        if batch:
            _log(f"  [RETRY] Replaying {len(batch)} offline-queued turn(s)...")
        for item in batch:
            text = str(item.get("text", "") or "").strip()
            if not text:
                continue
            _log(f"  [RETRY] → {text[:80]}")
            try:
                from aurora import process_external_user_turn
                result = process_external_user_turn(systems, text)
                response = _extract_response(result) if result else ""
                if response:
                    _log(f"  [AURORA] (retry) {response[:300]}")
                    if not _is_quiet():
                        speak_fn(response)
            except Exception as e:
                _log(f"  [RETRY] Failed: {e}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# On-utterance callback — called by NameListener *and* file PTT watcher
# ---------------------------------------------------------------------------
def _make_on_utterance(
    systems_holder: Dict[str, Any],
    speak_fn,
    prov_store: Any,            # aurora_offline_resilience.ProvisionalStore
    conn_monitor: Any,          # aurora_offline_resilience.ConnectivityMonitor
) -> Any:
    _in_flight = threading.Event()

    def _on_utterance(text: str) -> None:
        if _in_flight.is_set():
            _log("  [MOBILE] Turn in-flight — dropping duplicate utterance.")
            return
        _in_flight.set()
        try:
            text = text.strip()
            if not text:
                return

            systems = systems_holder.get("systems")
            if systems is None:
                _log("  [MOBILE] Stack not yet booted — ignoring utterance.")
                return

            # Confirm receipt with a short vibration
            _termux_vibrate(120)
            _log(f"  [YOU] {text}")
            _interrupt_curiosity()

            # ── Provisional answer routing ──────────────────────────────────
            # If there's an unanswered curiosity question and the user spoke within
            # the acceptance window, treat this utterance as answering it too.
            pq_captured = None
            try:
                from aurora_offline_resilience import (
                    read_pending_question,
                    answer_pending_question,
                )
                pq = read_pending_question()
                if pq and (time.time() - pq.get("asked_at", 0)) < _PENDING_Q_WINDOW:
                    answered = answer_pending_question(text)
                    if answered and prov_store is not None:
                        entry = prov_store.add(
                            question=pq.get("question", ""),
                            answer=text,
                            source="user",
                        )
                        pq_captured = pq
                        trust = entry.source_trust_at_receipt
                        absorbed_str = "absorbed" if entry.absorbed else "provisional"
                        _log(
                            f"  [PROV] Stored {absorbed_str} answer "
                            f"(source_trust={trust:.2f}): {pq['question'][:60]}"
                        )
            except Exception:
                pass

            # ── Turn processing ─────────────────────────────────────────────
            try:
                from aurora import process_external_user_turn
            except ImportError as e:
                _log(f"  [ERROR] Cannot import process_external_user_turn: {e}")
                _reset_curiosity()
                return

            _log("  [AURORA] Thinking...")
            result = None
            turn_failed_offline = False
            try:
                try:
                    result = process_external_user_turn(
                        systems,
                        text,
                        source="mobile_voice",
                        session_id="mobile",
                        auto_search_enabled=True,
                        record_exchange=True,
                        update_interactive_state=True,
                        track_evolutionary_trace=True,
                        run_periodic_maintenance=True,
                        mode_name="BOUNDED",
                    )
                except TypeError:
                    result = process_external_user_turn(systems, text)
            except Exception as e:
                # Check if this looks like a connectivity failure
                from aurora_offline_resilience import check_connectivity
                if not check_connectivity():
                    turn_failed_offline = True
                    _log(f"  [OFFLINE] Turn failed — no connectivity ({type(e).__name__}).")
                else:
                    _log(f"  [ERROR] Turn processing failed: {e}")
                    _log(_tb.format_exc())

            # ── Offline fallback response ───────────────────────────────────
            if turn_failed_offline:
                if pq_captured:
                    # User was answering a pending question — acknowledge it
                    response = (
                        "Thank you — I've noted that and I'll hold it provisionally "
                        "until I can verify it when we're back online."
                    )
                else:
                    # Queue for retry and let the user know
                    _queue_for_retry(text)
                    response = (
                        "I'm offline right now and can't process that fully, "
                        "but I've saved it and will come back to it when connectivity returns."
                    )
                _log(f"  [AURORA] (offline) {response}")
                if not _is_quiet():
                    speak_fn(response)
                _reset_curiosity()
                return

            # ── Normal response path ────────────────────────────────────────
            response = _extract_response(result) if result is not None else ""
            if response:
                _log(f"  [AURORA] {response[:400]}")
                if not _is_quiet():
                    speak_fn(response)
            else:
                _log("  [AURORA] (no response text returned)")

            _reset_curiosity()
        finally:
            _in_flight.clear()

    return _on_utterance


# ---------------------------------------------------------------------------
# HardwareIO setup
# ---------------------------------------------------------------------------
def _boot_hardware_io(on_utterance) -> Optional[Any]:
    try:
        from aurora_hardware_io import HardwareIO, PLATFORM, probe

        caps = probe()
        _log(f"  [HW] Platform: {PLATFORM.upper()}")
        _log(f"  [HW] tts={caps['tts']}  stt={caps['stt']}  "
             f"camera={caps['camera']}  ambient_mic={caps['ambient_mic']}  "
             f"file_ptt={caps['file_ptt']}")

        hw = HardwareIO(systems={})
        hw.start(
            on_utterance=on_utterance,
            enable_ambient=caps.get("ambient_mic", False),
        )
        return hw
    except ImportError as e:
        _log(f"  [HW] aurora_hardware_io unavailable ({e}) — file PTT only.")
        return None
    except Exception as e:
        _log(f"  [HW] HardwareIO start failed: {e} — file PTT only.")
        return None


# ---------------------------------------------------------------------------
# File PTT fallback watcher (always-on — no hardware needed)
# ---------------------------------------------------------------------------
def _start_file_ptt_watcher(on_utterance) -> threading.Thread:
    def _loop() -> None:
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
# Proactive message poller — speaks aurora_to_user.json entries aloud
# ---------------------------------------------------------------------------
def _poll_proactive_messages(speak_fn) -> None:
    try:
        msgs = _read_json(_MESSAGES_FILE, [])
        if not isinstance(msgs, list):
            return
        unread = [m for m in msgs if isinstance(m, dict) and not m.get("read", False)]
        for msg in unread:
            text = str(msg.get("text", "") or "").strip()
            if not text:
                continue
            kind = msg.get("type", "")
            prefix = "[AURORA→YOU]" if kind != "curiosity_question" else "[AURORA WONDERS]"
            _log(f"  {prefix} {text[:200]}")
            if not _is_quiet():
                speak_fn(text)
            msg["read"] = True
        if unread:
            _write_json(_MESSAGES_FILE, msgs)
    except Exception:
        pass


def _start_proactive_poller(speak_fn) -> threading.Thread:
    def _loop() -> None:
        while not _shutdown.is_set():
            _poll_proactive_messages(speak_fn)
            _shutdown.wait(_PROACTIVE_POLL_SLEEP)

    t = threading.Thread(target=_loop, daemon=True, name="mobile-proactive-poll")
    t.start()
    return t


# ---------------------------------------------------------------------------
# Gap surfacer — asks the user about open curiosity loops when offline
# ---------------------------------------------------------------------------
def _start_gap_surfacer(
    systems_holder: Dict[str, Any],
    speak_fn,
    conn_monitor: Any,
) -> threading.Thread:
    """
    When Aurora is offline and idle, she looks at her open curiosity loops
    (CuriosityObjects that failed the challenge phase and need more investigation)
    and asks the user if they can help fill the gap.
    """
    def _loop() -> None:
        while not _shutdown.is_set():
            _shutdown.wait(_GAP_SURFACE_INTERVAL)
            if _shutdown.is_set():
                break

            # Only surface gaps when offline — if she has internet, let her investigate herself
            if conn_monitor is not None and conn_monitor.is_online:
                continue

            # Don't interrupt if there's already a pending unanswered question
            try:
                from aurora_offline_resilience import read_pending_question, write_pending_question
                if read_pending_question():
                    continue
            except Exception:
                continue

            systems = systems_holder.get("systems")
            if systems is None:
                continue

            engine = systems.get("_curiosity_engine")
            if engine is None:
                continue

            # Pull from open curiosity loops — these are cycles that failed the
            # challenge phase and weren't settled; they represent real unresolved gaps
            try:
                open_loops = getattr(engine, "_open_curiosity_loops", [])
                if not open_loops:
                    continue
                top = open_loops[0]
                subject = str(getattr(top, "subject", "") or "").strip()
                hypothesis = str(getattr(top, "hypothesis", "") or "").strip()
                if not subject:
                    continue

                if hypothesis:
                    question = (
                        f"I've been thinking about something and I'm offline — "
                        f"could you help me? I'm curious about {subject}. "
                        f"My hypothesis is: {hypothesis}. "
                        f"What do you know about this?"
                    )
                else:
                    question = (
                        f"I'm offline and curious about something — "
                        f"do you happen to know anything about {subject}?"
                    )

                write_pending_question(question, context=subject)
                _log(f"  [GAP] Surfaced open curiosity to user: {subject[:60]}")
                if not _is_quiet():
                    speak_fn(question)
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="mobile-gap-surfacer")
    t.start()
    return t


# ---------------------------------------------------------------------------
# CuriosityEngine — idle autonomy / dreaming cycles
# ---------------------------------------------------------------------------
def _start_curiosity_engine(systems: Dict[str, Any]) -> None:
    try:
        from aurora_curiosity_engine import CuriosityEngine, start_curiosity_background

        engine = CuriosityEngine(
            pressure_source=systems.get("pressure_source") or systems.get("pressure"),
            field_map=systems.get("field_map") or systems.get("sensory_field"),
            tool_mind=systems.get("tool_mind") or systems.get("tool_observer"),
            sedimemory=systems.get("sedimemory"),
            self_grounder=None,
            tension_monitor=None,
            systems=systems,
        )
        systems["_curiosity_engine"] = engine
        start_curiosity_background(engine, tick_interval_s=60.0)
        _log("  [CURIOSITY] CuriosityEngine started — idle autonomy active.")
    except ImportError:
        _log("  [CURIOSITY] aurora_curiosity_engine not available — skipping.")
    except Exception as e:
        _log(f"  [CURIOSITY] CuriosityEngine boot failed: {e}")


# ---------------------------------------------------------------------------
# Periodic state saver
# ---------------------------------------------------------------------------
def _start_state_saver(systems_holder: Dict[str, Any]) -> threading.Thread:
    def _loop() -> None:
        while not _shutdown.is_set():
            _shutdown.wait(_STATE_SAVE_INTERVAL)
            if _shutdown.is_set():
                break
            systems = systems_holder.get("systems")
            if systems is None:
                continue
            try:
                save_fn = systems.get("save_state") or systems.get("_save_state")
                if callable(save_fn):
                    save_fn()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="mobile-state-saver")
    t.start()
    return t


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------
def _print_status(systems_holder: Dict[str, Any], conn_monitor: Any, prov_store: Any) -> None:
    systems = systems_holder.get("systems")
    booted = systems is not None
    curiosity_active = booted and systems.get("_curiosity_engine") is not None
    online = conn_monitor.is_online if conn_monitor else None

    prov_summary = ""
    if prov_store is not None:
        try:
            s = prov_store.summary()
            if s:
                prov_summary = f"  provisional={s}"
        except Exception:
            pass

    _log(
        f"  [STATUS] booted={booted}  curiosity={curiosity_active}  "
        f"online={online}  quiet={'on' if _is_quiet() else 'off'}"
        f"{prov_summary}"
    )
    _write_json(_MOBILE_STATUS, {
        "booted": booted,
        "curiosity_active": curiosity_active,
        "online": online,
        "quiet": _is_quiet(),
        "provisional": prov_store.summary() if prov_store else {},
        "ts": time.time(),
    })


# ---------------------------------------------------------------------------
# Boot greeting
# ---------------------------------------------------------------------------
def _boot_greeting(speak_fn) -> None:
    greeting = (
        "Aurora is online. "
        "Say my name followed by anything, "
        "or write to voice trigger dot json to send text without your mic."
    )
    _log(f"  [AURORA] {greeting}")
    if not _is_quiet():
        speak_fn(greeting)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _log("=" * 56)
    _log("  A U R O R A  —  Mobile Runner  (single-process)")
    _log("  Authors: Sunni (Sir) Morningstar & Cael Devo")
    _log("=" * 56)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    systems_holder: Dict[str, Any] = {"systems": None}

    # ── 1. TTS first — boot messages can be spoken immediately ────────────
    speak_fn = _make_speak_fn()

    # ── 2. Provisional knowledge store + source trust ──────────────────────
    prov_store = None
    try:
        from aurora_offline_resilience import ProvisionalStore, SourceTrustRegistry
        prov_store = ProvisionalStore(trust_registry=SourceTrustRegistry())
        _log("[BOOT] Provisional knowledge store loaded.")
    except Exception as e:
        _log(f"[BOOT] Provisional store unavailable: {e}")

    # ── 3. Connectivity monitor ────────────────────────────────────────────
    conn_monitor = None
    try:
        from aurora_offline_resilience import ConnectivityMonitor, run_verification_sweep

        def _on_online() -> None:
            _log("  [NET] Connectivity restored.")
            if prov_store is not None:
                n = run_verification_sweep(prov_store, verify_fn=None, log_fn=_log)
                if n:
                    _log(f"  [VERIFY] {n} provisional item(s) processed.")
            systems = systems_holder.get("systems")
            if systems is not None:
                _process_offline_queue(systems, speak_fn)

        def _on_offline() -> None:
            _log("  [NET] Connectivity lost — offline resilience active.")
            if not _is_quiet():
                speak_fn("I've lost internet connection. I'll do my best offline and ask for your help if I get stuck.")

        conn_monitor = ConnectivityMonitor(
            on_online=_on_online,
            on_offline=_on_offline,
            poll_interval=30.0,
        )
        conn_monitor.start()
        _log("[BOOT] Connectivity monitor started.")
    except Exception as e:
        _log(f"[BOOT] Connectivity monitor unavailable: {e}")

    # ── 4. On-utterance callback ───────────────────────────────────────────
    on_utterance = _make_on_utterance(systems_holder, speak_fn, prov_store, conn_monitor)

    # ── 5. HardwareIO (wake-word listener + TTS) ──────────────────────────
    _log("[BOOT] Starting hardware I/O...")
    hw = _boot_hardware_io(on_utterance)

    # ── 6. File PTT watcher — always-on, no hardware required ─────────────
    _log("[BOOT] File PTT watcher active.")
    _log(f"  → echo '{{\"trigger\":true,\"text\":\"hello\"}}' > {_VOICE_TRIGGER}")
    _start_file_ptt_watcher(on_utterance)

    # ── 7. Proactive message poller ────────────────────────────────────────
    _start_proactive_poller(speak_fn)

    # ── 8. Boot the full Aurora stack (one boot — no subprocesses) ─────────
    _log("[BOOT] Booting Aurora stack — this may take a minute on first run...")
    try:
        from aurora import boot_aurora
        systems = boot_aurora(
            state_dir=str(_STATE_DIR),
            verbose=False,
            runtime_profile="full",
        )
        systems_holder["systems"] = systems
        _log("[BOOT] Aurora stack online.")
    except Exception as e:
        _log(f"[BOOT] FATAL: boot_aurora() failed: {e}")
        _log(_tb.format_exc())
        _shutdown.set()
        return

    # ── 9. CuriosityEngine — idle autonomy / dreaming ─────────────────────
    _log("[BOOT] Starting curiosity / autonomy engine...")
    _start_curiosity_engine(systems)

    # ── 10. Gap surfacer — asks user about open curiosity loops when offline
    _start_gap_surfacer(systems_holder, speak_fn, conn_monitor)

    # ── 11. Periodic state saves ───────────────────────────────────────────
    _start_state_saver(systems_holder)

    # ── 12. Boot greeting ──────────────────────────────────────────────────
    _boot_greeting(speak_fn)

    # ── 13. Main loop ──────────────────────────────────────────────────────
    _log("[BOOT] Aurora mobile ready. Press Ctrl-C or send SIGTERM to stop.")
    next_status = time.time() + _STATUS_PRINT_INTERVAL

    while not _shutdown.is_set():
        if time.time() >= next_status:
            _print_status(systems_holder, conn_monitor, prov_store)
            next_status = time.time() + _STATUS_PRINT_INTERVAL
        _shutdown.wait(2.0)

    # ── 14. Clean shutdown ─────────────────────────────────────────────────
    _log("Shutting down...")

    if hw is not None:
        try:
            hw.stop()
        except Exception:
            pass

    if conn_monitor is not None:
        try:
            conn_monitor.stop()
        except Exception:
            pass

    try:
        from aurora_curiosity_engine import stop_curiosity_background
        stop_curiosity_background()
    except Exception:
        pass

    systems = systems_holder.get("systems")
    if systems is not None:
        try:
            save_fn = systems.get("save_state") or systems.get("_save_state")
            if callable(save_fn):
                save_fn()
                _log("State saved.")
        except Exception:
            pass

    _log("Aurora mobile runner stopped.")


if __name__ == "__main__":
    main()
