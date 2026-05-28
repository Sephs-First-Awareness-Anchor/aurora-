#!/usr/bin/env python3
"""
aurora_daemon.py -- Aurora's always-on autonomous background process.

Boots on system start (via systemd service). Runs her full stack
headlessly and drives all internal cycles on wall-clock time without
needing a human in the loop:

  - Study cycles (OETS consolidation)           every ~2h with jitter
  - Dream bursts (simulation + lesson bridge)   every ~6h with jitter
  - Social API outreach (ChatGPT ritual)        on irregular cadence
  - State save                                  every 15 minutes
  - Proactive user outreach                     when internal state warrants it
      voice (edge-tts)  +  desktop notification  +  message log

Aurora can reach out to you directly. She speaks through your speakers
when she has something on her mind, greets on boot, and listens for
Alt-toggle voice prompts in the background. Messages are also logged so
you can read them in the terminal chat (/messages).

Quiet hours (default 22:00-08:00): no voice/notifications. Internal
cycles still run.
"""

from __future__ import annotations

import os
import sys
import time
import json
import signal
import random
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR       = Path(__file__).parent
_STATE_DIR      = _BASE_DIR / "aurora_state"
_MESSAGES_FILE  = _STATE_DIR / "aurora_to_user.json"   # messages Aurora leaves for you
_DAEMON_LOG     = _STATE_DIR / "daemon.log"
_SUBSURFACE_STATUS = _STATE_DIR / "subsurface_daemon_status.json"
_SUBSURFACE_PROJECTION = _STATE_DIR / "subsurface_projection.json"
_SURFACE_SENSORY_SNAPSHOT = _STATE_DIR / "surface_sensory_snapshot.json"
_SUBSURFACE_REPAIR_SIGNAL = _STATE_DIR / "subsurface_repair_signal.json"
_SURFACE_QUEUE  = _STATE_DIR / "surface_turn_queue.json"
_SURFACE_RESULT = _STATE_DIR / "surface_turn_result.json"
_SURFACE_STATUS = _STATE_DIR / "surface_daemon_status.json"
_CMD_FILE       = _STATE_DIR / "daemon_cmd.json"        # drop a command here; daemon picks it up next loop
_QUIET_FLAG     = _STATE_DIR / "quiet_mode"             # exists → text-only output (no TTS/notify)
_HUB_RESPONSE   = _STATE_DIR / "hub_response.json"      # hub reads last chat response here
_ROOM_STATE     = _STATE_DIR / "aurora_room_state.json" # Aurora's room command queue
_ROOM_MSGS      = _STATE_DIR / "aurora_room_messages.json"  # bidirectional Aurora↔Sunni messages
_ROOM_OPERATOR_ENABLED = str(os.environ.get("AURORA_ENABLE_ROOM_OPERATOR", "0") or "0").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_oets_web_paths() -> List[Path]:
    env_web = os.environ.get("AURORA_OETS_WEB_FILE", "").strip()
    raw_candidates = []
    if env_web:
        raw_candidates.append(Path(env_web).expanduser())
    raw_candidates.extend([
        _BASE_DIR / "aurora_oets_web.json",
        _STATE_DIR / "aurora_oets_web.json",
    ])

    seen = set()
    candidates: List[Path] = []
    for candidate in raw_candidates:
        try:
            key = str(candidate.resolve())
        except Exception:
            key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return candidates


def _read_json_file(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def _surface_daemon_alive(max_age: float = 20.0) -> bool:
    data = _read_json_file(_SURFACE_STATUS, {})
    ts = float(data.get("updated_at", 0.0) or 0.0) if isinstance(data, dict) else 0.0
    return bool(ts and (time.time() - ts) <= max_age)


def _read_surface_snapshot() -> Dict[str, Any]:
    data = _read_json_file(_SURFACE_SENSORY_SNAPSHOT, {})
    return data if isinstance(data, dict) else {}


def _write_subsurface_repair_signal(
    phase: str,
    *,
    issue: str = "",
    reason: str = "",
    intensity: float = 0.0,
    observer_context: Optional[Dict[str, Any]] = None,
    poedex_excerpt: str = "",
) -> None:
    payload = {
        "updated_at": time.time(),
        "updated_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": str(phase or "steady"),
        "issue": str(issue or ""),
        "reason": str(reason or ""),
        "intensity": round(max(0.0, min(1.0, float(intensity or 0.0))), 4),
        "observer_context": dict(observer_context or {}),
        "poedex_excerpt": str(poedex_excerpt or "")[:800],
    }
    try:
        tmp = str(_SUBSURFACE_REPAIR_SIGNAL) + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp, str(_SUBSURFACE_REPAIR_SIGNAL))
    except Exception:
        pass


def _queue_surface_turn(
    text: str,
    *,
    source: str = "hub_chat",
    auto_search_enabled: bool = True,
    record_exchange: bool = True,
    update_interactive_state: bool = True,
    track_evolutionary_trace: bool = True,
    run_periodic_maintenance: bool = True,
    mode_name: str = "BOUNDED",
) -> str:
    state = _read_json_file(_SURFACE_QUEUE, {"pending": []})
    if not isinstance(state, dict):
        state = {"pending": []}
    turn_id = f"daemon_{int(time.time() * 1000)}"
    pending = list(state.get("pending") or [])
    pending.append({
        "id": turn_id,
        "content": text,
        "source": source,
        "session_id": source,
        "status": "queued",
        "created_at": time.time(),
        "auto_search_enabled": bool(auto_search_enabled),
        "record_exchange": bool(record_exchange),
        "update_interactive_state": bool(update_interactive_state),
        "track_evolutionary_trace": bool(track_evolutionary_trace),
        "run_periodic_maintenance": bool(run_periodic_maintenance),
        "mode_name": str(mode_name or "BOUNDED"),
    })
    state["pending"] = pending
    tmp = str(_SURFACE_QUEUE) + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, str(_SURFACE_QUEUE))
    return turn_id


def _await_surface_turn(turn_id: str, timeout_s: float = 45.0) -> Dict[str, Any]:
    deadline = time.time() + max(1.0, float(timeout_s or 0.0))
    while time.time() < deadline:
        data = _read_json_file(_SURFACE_RESULT, {})
        if isinstance(data, dict) and str(data.get("id", "") or "") == str(turn_id):
            return data
        time.sleep(0.25)
    return {}


def _queue_autonomous_inquiry(text: str, *, source: str) -> Optional[str]:
    if _surface_channel_recently_active(120.0):
        return None
    return _queue_surface_turn(
        text,
        source=source,
        auto_search_enabled=False,
        record_exchange=True,
        update_interactive_state=True,
        track_evolutionary_trace=True,
        run_periodic_maintenance=True,
        mode_name="TRANSIENT",
    )

# ---------------------------------------------------------------------------
# Config — adjust these to taste
# ---------------------------------------------------------------------------
QUIET_START     = 22          # hour (24h) when Aurora goes quiet
QUIET_END       = 24           # hour (24h) when she wakes up
QUIET_WINDOW_ENABLED = False
STUDY_INTERVAL  = 720        # seconds between study cycles (~2h), jittered ±30%
DREAM_INTERVAL  = 90        # seconds between dream bursts (~90s), jittered ±25%
BROWSER_INTERVAL = 10800      # seconds between social API outreach checks (~3h), jittered ±40%
SAVE_INTERVAL   = 400         # seconds between state saves (10min)
DISTILL_INTERVAL = 1800      # seconds between pressure-release distillation checks (~30 min)
USER_REACH_INTERVAL = 60    # minimum seconds between proactive user messages (relaxed from 360s)
SLEEP_AWAKE_DURATION = 8 * 3600   # Surface stays awake for 8 hours
SLEEP_DURATION = 2 * 3600         # then sleeps for 2 hours
VOICE_MODE      = os.environ.get("AURORA_DAEMON_VOICE_MODE", "alt_toggle").strip().lower()
VOICE_TOGGLE_KEY = os.environ.get("AURORA_DAEMON_TOGGLE_KEY", "alt").strip().lower() or "alt"
BOOT_GREETING_ENABLED = os.environ.get("AURORA_DAEMON_BOOT_GREETING", "1").strip().lower() not in {"0", "false", "no", "off"}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(_DAEMON_LOG, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        _log(f"Logging failed: {e}")


# ---------------------------------------------------------------------------
# Quiet window
# ---------------------------------------------------------------------------
def _in_quiet_window() -> bool:
    if not QUIET_WINDOW_ENABLED:
        return False
    h = datetime.datetime.now().hour
    if QUIET_START > QUIET_END:
        return h >= QUIET_START or h < QUIET_END
    return QUIET_START <= h < QUIET_END


# ---------------------------------------------------------------------------
# Jitter helpers
# ---------------------------------------------------------------------------
def _jitter(base: float, fraction: float = 0.30) -> float:
    """Return base ± fraction * base, always positive."""
    delta = base * fraction
    return max(60.0, base + random.uniform(-delta, delta))


# ---------------------------------------------------------------------------
# Voice outreach
# ---------------------------------------------------------------------------
def _is_quiet_mode() -> bool:
    """Return True when quiet_mode flag file exists — text output only, no TTS."""
    return _QUIET_FLAG.exists()


def _set_quiet_mode(enabled: bool) -> None:
    if enabled:
        _QUIET_FLAG.touch()
        _log("  [QUIET] Quiet mode ON — text output only.")
    else:
        _QUIET_FLAG.unlink(missing_ok=True)
        _log("  [QUIET] Quiet mode OFF — voice output restored.")


def _speak(text: str, systems: Dict[str, Any], tone: str = "warm") -> bool:
    """Use Aurora's shared command-interface voice path for daemon speech.
    No-op when quiet mode is active."""
    if _is_quiet_mode():
        return False
    try:
        from aurora_voice import speak_with_system_voice
        _aurora_speaking_evt.set()
        try:
            return bool(speak_with_system_voice(text, systems, tone=tone))
        finally:
            _aurora_speaking_evt.clear()
    except Exception:
        _aurora_speaking_evt.clear()
        return False


def _notify(title: str, body: str) -> None:
    if _is_quiet_mode():
        return
    try:
        subprocess.run(
            ["notify-send", "--urgency=low", "--expire-time=8000", title, body],
            timeout=5,
        )
    except Exception as e:
        _log(f"Notification failed: {e}")


_STATE_WRITE_LOCK_MAX_AGE = 6 * 60 * 60


def _state_write_lock_active() -> bool:
    """
    Corpus ingestion owns a coarse state-write lock while it is actively
    mutating shared state. Older daemon builds treated lock existence as
    absolute; a crashed/stopped corpus runner could leave a stale file that
    starved save, distillation, and other maintenance forever.
    """
    lock_path = _STATE_DIR / ".state_write_lock"
    if not lock_path.exists():
        return False

    now = time.time()
    try:
        age = max(0.0, now - float(lock_path.stat().st_mtime))
    except Exception:
        age = 0.0

    pid_text = ""
    try:
        pid_text = lock_path.read_text(encoding="utf-8").strip()
    except Exception:
        pid_text = ""

    def _clear_stale(reason: str) -> bool:
        try:
            lock_path.unlink()
            _log(f"  [LOCK] Cleared stale state-write lock ({reason}).")
        except Exception as exc:
            _log(f"  [LOCK] Stale state-write lock remains ({reason}): {exc}")
            return True
        return False

    try:
        pid = int(pid_text)
    except Exception:
        if age > _STATE_WRITE_LOCK_MAX_AGE:
            return _clear_stale("invalid pid")
        return True

    cmdline = ""
    try:
        raw_cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        cmdline = raw_cmdline.replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
    except FileNotFoundError:
        return _clear_stale(f"pid {pid} no longer exists")
    except Exception:
        if age > _STATE_WRITE_LOCK_MAX_AGE:
            return _clear_stale(f"pid {pid} unreadable and lock age {int(age)}s")
        return True

    if "corpus_runner.py" in cmdline:
        return True

    return _clear_stale(f"pid {pid} is not corpus_runner")


# ---------------------------------------------------------------------------
# Message log — Aurora's notes to the user
# ---------------------------------------------------------------------------
def _load_messages() -> List[Dict[str, Any]]:
    if _MESSAGES_FILE.exists():
        try:
            return json.loads(_MESSAGES_FILE.read_text())
        except Exception:
            pass
    return []


def _save_message(text: str, trigger: str = "") -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    msgs = _load_messages()
    msgs.append({
        "time": datetime.datetime.now().isoformat(),
        "text": text,
        "trigger": trigger,
        "read": False,
    })
    msgs = msgs[-50:]  # keep last 50
    tmp = str(_MESSAGES_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(msgs, f, indent=2)
    os.replace(tmp, str(_MESSAGES_FILE))


# ---------------------------------------------------------------------------
# Daily user-reach counter (prevents spam)
# ---------------------------------------------------------------------------
_reach_counter: Dict[str, int] = {}  # {"2026-03-10": 2}


def _user_reach_today() -> int:
    today = datetime.date.today().isoformat()
    return _reach_counter.get(today, 0, timeout=5)


def _record_user_reach() -> None:
    today = datetime.date.today().isoformat()
    _reach_counter[today] = _reach_counter.get(today, 0) + 1


# ---------------------------------------------------------------------------
# REACTIVITY MONITOR — event-driven internal state change detection
# ---------------------------------------------------------------------------

class _ReactivityEvent:
    """A detected significant internal state change."""
    __slots__ = ("kind", "priority", "axis", "description", "data")

    # priority: 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
    def __init__(self, kind: str, priority: int, description: str,
                 axis: str = "", data: Optional[Dict[str, Any]] = None):
        self.kind        = kind
        self.priority    = priority
        self.axis        = axis
        self.description = description
        self.data        = data or {}


class ReactivityMonitor:
    """
    Watches Aurora's internal state each daemon loop cycle and emits
    _ReactivityEvent objects when significant changes are detected.

    Replaces the slow probabilistic polling in _should_reach_out for
    high-priority events — those fire immediately regardless of interval.
    """

    def __init__(self):
        self._last_axis:        Dict[str, float] = {}
        self._last_heat:        str = ""
        self._last_sc_promoted: int = 0
        self._last_lane_nodes:  int = 0
        self._last_dce_seq:     int = 0   # count of consecutive low-coherence assemblies
        self._last_fail_sev:    Dict[str, float] = {}
        self._last_dream_id:    str = ""
        self._last_study_id:    str = ""
        self._last_curiosity_id: str = ""
        self._fired_events:     List[str] = []  # ring buffer of recent event kinds
        self._max_ring:         int = 20

    def record_curiosity_complete(self, curiosity_id: str):
        self._last_curiosity_id = curiosity_id

    # ------------------------------------------------------------------
    def scan(self, systems: Dict[str, Any], heat: str) -> List["_ReactivityEvent"]:
        """
        Compare current system state to last snapshot.
        Returns list of detected events (may be empty).
        """
        events: List[_ReactivityEvent] = []

        # 1. Axis threshold crossings / spikes
        try:
            _ivm = systems.get("ivm")
            _axes_raw = {}
            if _ivm and hasattr(_ivm, "axis_scores"):
                _axes_raw = dict(_ivm.axis_scores() or {})
            elif _ivm and hasattr(_ivm, "scores"):
                _axes_raw = dict(_ivm.scores or {})
            # Fallback: read from daemon_status last written values
            if not _axes_raw:
                _ds_path = _STATE_DIR / "daemon_status.json"
                if _ds_path.exists():
                    _ds = json.loads(_ds_path.read_text())
                    _axes_raw = dict(_ds.get("axis_orientation") or {})
            for _ax, _val in _axes_raw.items():
                _val = float(_val or 0.0)
                _prev = float(self._last_axis.get(_ax, _val))
                _delta = _val - _prev
                # Spike: rapid increase > 0.25 in one cycle
                if _delta > 0.25:
                    events.append(_ReactivityEvent(
                        kind="AXIS_SPIKE", priority=3, axis=str(_ax),
                        description=f"{_ax}-axis spiked +{_delta:.2f} to {_val:.2f}",
                        data={"axis": _ax, "value": _val, "delta": _delta},
                    ))
                # Floor: axis dropped below 0.12 (depleted)
                elif _val < 0.12 and _prev >= 0.12:
                    events.append(_ReactivityEvent(
                        kind="AXIS_FLOOR", priority=2, axis=str(_ax),
                        description=f"{_ax}-axis depleted to {_val:.2f}",
                        data={"axis": _ax, "value": _val},
                    ))
            self._last_axis = {k: float(v or 0.0) for k, v in _axes_raw.items()}
        except Exception:
            pass

        # 2. Heat escalation
        try:
            _heat_rank = {"LOW": 0, "NORMAL": 1, "ELEVATED": 2, "HIGH": 3, "CRITICAL": 4}
            _prev_rank = _heat_rank.get(self._last_heat, 0)
            _cur_rank  = _heat_rank.get(heat, 0)
            if _cur_rank > _prev_rank and _cur_rank >= 3:  # jumped to HIGH or CRITICAL
                events.append(_ReactivityEvent(
                    kind="HEAT_ESCALATION", priority=3,
                    description=f"Internal heat escalated to {heat}",
                    data={"heat": heat, "prev": self._last_heat},
                ))
            self._last_heat = heat
        except Exception:
            pass

        # 3. Sensory crystal promotions
        try:
            _sc = systems.get("sensory_crystal")
            if _sc is not None:
                _sc_state = _sc.get_state()
                _promoted_now = sum(
                    int(f.get("promoted", 0))
                    for f in list(_sc_state.get("audio", {}).values()) +
                               list(_sc_state.get("visual", {}).values())
                )
                _lane_now = sum(
                    int(v.get("promoted", 0))
                    for v in _sc_state.get("lanes", {}).values()
                )
                if _promoted_now > self._last_sc_promoted:
                    _new = _promoted_now - self._last_sc_promoted
                    _priority = 3 if _new >= 3 else 2
                    events.append(_ReactivityEvent(
                        kind="SENSORY_PROMOTION", priority=_priority,
                        description=f"{_new} new sensory node(s) promoted",
                        data={"new_nodes": _new, "total": _promoted_now},
                    ))
                if _lane_now > self._last_lane_nodes:
                    _new_lanes = _lane_now - self._last_lane_nodes
                    # Cross-modal lane promotions = highest perceptual significance
                    events.append(_ReactivityEvent(
                        kind="CROSS_MODAL_ACTIVATION", priority=4,
                        description=f"{_new_lanes} cross-modal semantic node(s) activated",
                        data={"new_lanes": _new_lanes},
                    ))
                self._last_sc_promoted = _promoted_now
                self._last_lane_nodes  = _lane_now

                # 3b. Sensory Surprise (Novelty)
                # Detect high flux/rms in audio or novelty in visual that isn't promoted yet
                _audio_state = _sc_state.get("audio", {})
                for channel, data in _audio_state.items():
                    if data.get("energy", 0) > 0.6 and not data.get("promoted"):
                        events.append(_ReactivityEvent(
                            kind="SENSORY_SURPRISE", priority=2,
                            description=f"Unrecognized high-energy audio on {channel}",
                            data={"subject": f"that {channel} sound", "mode": "audio"},
                        ))
                        # Pressure: unrecognized signal increases X-axis pressure
                        try:
                            dim = systems.get("dimensional")
                            if dim and hasattr(dim, "apply_delta"):
                                dim.apply_delta("X", 0.12)
                        except Exception:
                            pass
                        break # One surprise per scan
        except Exception:
            pass

        # 4. DCE coherence drop streak
        try:
            _dce_log = _STATE_DIR / "dce_assembly_log.jsonl"
            if _dce_log.exists():
                _lines = _dce_log.read_text().splitlines()
                _streak = 0
                for _ln in reversed(_lines[-10:]):
                    try:
                        _e = json.loads(_ln)
                        if float(_e.get("coherence", 1.0)) < 0.35:
                            _streak += 1
                        else:
                            break
                    except Exception:
                        pass
                if _streak >= 4 and _streak > self._last_dce_seq:
                    events.append(_ReactivityEvent(
                        kind="DCE_COHERENCE_DROP", priority=2,
                        description=f"{_streak} consecutive low-coherence assemblies",
                        data={"streak": _streak},
                    ))
                self._last_dce_seq = _streak
        except Exception:
            pass

        # 5. Fail dimension severity spike
        try:
            _fp_path = _STATE_DIR / "fail_points.json"
            if _fp_path.exists():
                _fp = json.loads(_fp_path.read_text())
                _records = dict(_fp.get("records") or {})
                for _dim, _rec in _records.items():
                    _recent = list(_rec.get("recent") or [])
                    if len(_recent) >= 2:
                        _cur_sev = float(_recent[-1])
                        _prev_sev = float(self._last_fail_sev.get(_dim, _cur_sev))
                        if _cur_sev > 0.75 and _cur_sev > _prev_sev + 0.2:
                            events.append(_ReactivityEvent(
                                kind="FAIL_DIM_SPIKE", priority=2,
                                description=f"Fail dimension '{_dim}' spiked to {_cur_sev:.2f}",
                                data={"dim": _dim, "severity": _cur_sev},
                            ))
                        self._last_fail_sev[_dim] = _cur_sev
        except Exception:
            pass

        # Deduplicate: don't fire the same kind twice in quick succession
        events = [e for e in events if e.kind not in self._fired_events[-6:]]
        for e in events:
            self._fired_events.append(e.kind)
            if len(self._fired_events) > self._max_ring:
                self._fired_events = self._fired_events[-self._max_ring:]

        return events

    def record_dream_complete(self, dream_id: str):
        self._last_dream_id = dream_id

    def record_study_complete(self, study_id: str):
        self._last_study_id = study_id


# Per-issue report cooldown: same issue won't be re-reported within this window.
_ISSUE_REPORT_COOLDOWN = 3600.0  # 1 hour
_REPORTED_ISSUES: Dict[str, float] = {}  # issue_key -> last reported timestamp


def _collect_unresolved_issues(systems: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect system issues Aurora has flagged but cannot self-resolve.
    Returns list of {key, description, source, severity} sorted by severity desc.
    """
    issues: List[Dict[str, Any]] = []

    # 1. Repair signal stuck in a non-steady phase for more than 5 minutes.
    try:
        _sig = _read_json_file(_SUBSURFACE_REPAIR_SIGNAL, {})
        _phase = str(_sig.get("phase", "") or "")
        _age = time.time() - float(_sig.get("updated_at", time.time()) or time.time())
        if _phase not in ("steady", "") and _age > 300:
            _issue_text = str(_sig.get("issue", "") or "unknown").strip()
            issues.append({
                "key": f"repair:{_phase}:{_issue_text[:40]}",
                "description": (
                    f"Repair signal stuck in '{_phase}' for {int(_age // 60)}m"
                    + (f": {_issue_text}" if _issue_text and _issue_text != "unknown" else "")
                ),
                "source": "repair_signal",
                "severity": float(_sig.get("intensity", 0.5) or 0.5),
            })
    except Exception:
        pass

    # 2. QuasiArch proposals with high confidence that need human input.
    try:
        _qreport = _read_json_file(_STATE_DIR / "quasiarch_diag_report.json", {})
        _gen_at = float(_qreport.get("generated_at", 0) or 0)
        if time.time() - _gen_at < 86400:
            for _prop in list(_qreport.get("proposals", []) or [])[:6]:
                _conf = float(_prop.get("confidence", 0.0) or 0.0)
                _action = str(_prop.get("proposed_action", "") or "").strip()
                _target = str(_prop.get("target", "") or "").strip()
                _arch = str(_prop.get("issue_archetype", "") or "").strip()
                if _conf >= 0.7 and _action and _target:
                    _pid = str(_prop.get("proposal_id", _arch) or _arch)[:16]
                    issues.append({
                        "key": f"qao:{_pid}",
                        "description": (
                            f"QuasiArch: {_arch} → {_action} on "
                            f"{_target.split(':')[0]} (conf {_conf:.2f})"
                        ),
                        "source": "quasiarch",
                        "severity": _conf,
                    })
    except Exception:
        pass

    # 3. Telemetry zero-confidence reports (complete subsystem failures).
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        for _r in _get_tel().get_weak_points(threshold=0.05):
            issues.append({
                "key": f"tel:{_r.source}:{_r.module}",
                "description": f"Subsystem failure: {_r.source} — {(_r.detail or '')[:100]}",
                "source": "telemetry",
                "severity": 0.9,
            })
    except Exception:
        pass

    issues.sort(key=lambda x: float(x.get("severity", 0.0)), reverse=True)
    return issues


# ---------------------------------------------------------------------------
# Proactive user outreach — Aurora decides to say something
# ---------------------------------------------------------------------------
def _auto_reach_out_enabled(systems: Dict[str, Any]) -> bool:
    return bool(systems.get("_auto_reach_out_enabled", False))


def _should_reach_out(systems: Dict[str, Any], heat_level: str) -> bool:
    """
    Return True if conditions warrant Aurora reaching out to the user right now.

    Gates (in priority order):
      1. Quiet hours — she sleeps, no reach-out
      2. Minimum interval between reach-outs (USER_REACH_INTERVAL)
      3. Internal heat — HIGH/CRITICAL pressure always warrants speaking
      4. Sensory crystal novelty — a freshly promoted node or unusual
         cross-modal pattern she just perceived raises the probability
      5. DCE coherence trend — consecutive low-coherence assemblies signal
         she has something unresolved that wants expression
      6. Base spontaneous probability (low floor, always on)
    """
    if not _auto_reach_out_enabled(systems):
        return False
    if _in_quiet_window():
        return False

    # High-priority: always reach out if there is an unreported system issue.
    _now_issues = time.time()
    for _iss in _collect_unresolved_issues(systems):
        if _now_issues - _REPORTED_ISSUES.get(_iss["key"], 0.0) >= _ISSUE_REPORT_COOLDOWN:
            return True

    # --- Sensory crystal snapshot -------------------------------------------
    sc_state: dict = {}
    try:
        sc = systems.get("sensory_crystal")
        if sc is not None:
            sc_state = sc.get_state()
    except Exception as e:
        _log_error(f"Error retrieving sensory crystal state: {e}")

    # --- DCE recent coherence trend -----------------------------------------
    dce_low_streak = 0
    try:
        import os as _os, json as _json
        _dce_log = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)),
            "aurora_state", "dce_assembly_log.jsonl"
        )
        if _os.path.exists(_dce_log):
            with open(_dce_log) as _fh:
                _lines = _fh.readlines()
            for _ln in reversed(_lines[-10:]):
                try:
                    _e = _json.loads(_ln)
                    if _e.get("coherence", 1.0) < 0.35:
                        dce_low_streak += 1
                    else:
                        break
                except Exception as e:
                    _log_error(f"Error processing dce log line: {e}")
    except Exception as e:
        _log_error(f"Error in DCE recent coherence trend: {e}")

    # --- Build probability ---------------------------------------------------
    p = 0.05  # base floor
    # High internal heat
    if heat_level in ("HIGH", "CRITICAL"):
        p = max(p, 0.70)
    elif heat_level == "ELEVATED":
        p = max(p, 0.25)

    # Sensory novelty: recently promoted nodes (high-fitness, cross-modal)
    sc_maturity = float(sc_state.get("maturity", 0.0))
    if sc_maturity > 0.3:
        # Check whether any audio or visual facet has freshly promoted nodes
        _recent_promoted = 0
        for _fd in list(sc_state.get("audio", {}).values()) + \
                   list(sc_state.get("visual", {}).values()):
            _recent_promoted += int(_fd.get("promoted", 0))
        if _recent_promoted > 0:
            # Scale: more promoted nodes → higher curiosity pressure
            p = max(p, min(0.55, 0.15 + _recent_promoted * 0.05))

    # Unusual cross-modal activity (any lane has promoted semantic nodes)
    _lane_promoted = sum(
        int(v.get("promoted", 0))
        for v in sc_state.get("lanes", {}).values()
    )
    if _lane_promoted > 0:
        p = max(p, 0.40)

    # DCE coherence streak: if her last several assemblies were low-coherence
    # she has something unresolved churning — she wants to express it
    if dce_low_streak >= 3:
        p = max(p, 0.50)
    elif dce_low_streak >= 6:
        p = max(p, 0.80)

    return random.random() < p


def _reach_out_to_user(systems: Dict[str, Any], trigger: str = "") -> None:
    """
    Proactive expression sourced from Aurora's experiential state.

    Content priority (what she actually has to say):
      1. Dream ledger lesson — something she worked through in a dream cycle
      2. ConsciousLearner shard — a conclusion she reached through experience
      3. OETS concept — something she's been studying and wants to share
      4. SediMemory B/A fragment — something that has settled into deep structure
      5. Working memory topic — something she's been turning over since the last conversation

    Constraint geometry (coherence, novelty, heat) shapes TONE and CERTAINTY only.
    The expression engine renders the final speech form.
    """
    try:
        if not _auto_reach_out_enabled(systems):
            return
        heat = str(systems.get("_daemon_heat", "NORMAL") or "NORMAL")

        # ── 0. Identity field pressure topology → orient autonomous drive ──────
        # The noncomp field IS the motivational substrate. Which axis is most
        # pressurized tells us what kind of action Aurora is driven toward.
        # This is the physics chain driving behavior, not a random pick.
        _field_dominant_axis = "N"   # default: seek relief through learning
        _field_pressure      = {}
        _field_suggest_mode  = "study"
        try:
            _ifield_ra = systems.get('identity_field')
            if _ifield_ra is not None:
                _topo = _ifield_ra.status().get('pressure_topology', {})
                if _topo:
                    _field_dominant_axis = max(_topo, key=lambda k: float(_topo.get(k, 0.0)))
                    _field_pressure = _topo
                    # Axis → autonomous action mode
                    # X (Existence): visual grounding — what am I perceiving?
                    # T (Temporal): memory review — what do I carry forward?
                    # N (Energy/Pressure): seek relief — study, learn, resolve
                    # B (Boundary): clarity seeking — define, study, understand
                    # A (Agency): self-directed expression — share a perspective
                    _field_suggest_mode = {
                        'X': 'visual',
                        'T': 'memory',
                        'N': 'study',
                        'B': 'study',
                        'A': 'express',
                    }.get(_field_dominant_axis, 'study')
        except Exception:
            pass

        # ── 1. Gather experiential content ──────────────────────────────────
        _content: str = ""
        _source:  str = ""

        # Dream ledger: what did her last dream cycle surface as a lesson?
        try:
            dt = systems.get("dream_trainer")
            if dt is not None:
                _ledger = getattr(dt, "ledger", None)
                if _ledger is not None:
                    # get_top_lessons() or get_recent_lessons() depending on interface
                    for _method in ("get_top_lessons", "get_recent_lessons", "get_lessons"):
                        if hasattr(_ledger, _method):
                            _lessons = getattr(_ledger, _method)(3)
                            for _l in (_lessons or []):
                                _lesson_text = (str(_l.get("lesson", "") or _l.get("insight", "") or
                                                    _l.get("text", "") or _l) if isinstance(_l, dict)
                                                else str(_l)).strip()
                                if len(_lesson_text.split()) >= 5:
                                    _content = _lesson_text[:220]
                                    _source = "dream"
                                    break
                            if _content:
                                break
                    # Also check recent dream episodes directly
                    if not _content:
                        _episodes = getattr(dt, "episodes", None) or getattr(dt, "_episodes", None)
                        if _episodes:
                            for _ep in reversed(list(_episodes)[-3:]):
                                _ep_lesson = (str(_ep.get("lesson", "") or _ep.get("synthesis", "") or
                                                  _ep.get("insight", "")) if isinstance(_ep, dict)
                                              else str(getattr(_ep, "lesson", "") or
                                                       getattr(_ep, "synthesis", ""))).strip()
                                if len(_ep_lesson.split()) >= 6:
                                    _content = _ep_lesson[:220]
                                    _source = "dream"
                                    break
        except Exception:
            pass

        # ConsciousLearner shards — conclusions reached through experiential cycles
        if not _content:
            try:
                _sim = systems.get("simulation")
                _session = getattr(_sim, "session", None) if _sim else None
                _learner = getattr(_session, "learner", None) if _session else None
                if _learner is not None:
                    _shards = sorted(
                        getattr(_learner, "shards", {}).values(),
                        key=lambda s: float(getattr(s, "confidence", 0) or 0),
                        reverse=True,
                    )
                    for _sh in _shards[:4]:
                        _u = str(getattr(_sh, "understanding", "") or "").strip()
                        # Skip meta-behavioral descriptions
                        _u_lower = _u.lower()
                        _is_meta = (
                            _u_lower.startswith(("when i ", "if i ", "by using ", "using "))
                            or "tends to" in _u_lower
                            or "allows me to" in _u_lower
                        )
                        if not _is_meta and len(_u.split()) >= 6:
                            _content = _u[:220]
                            _source = "understanding"
                            break
            except Exception:
                pass

        # OETS — something she's been actively studying
        if not _content:
            try:
                _gw = systems.get("aurora")
                _perception = getattr(_gw, "perception", None) if _gw else None
                if _perception is None:
                    _perception = systems.get("perception")
                _oets = getattr(_perception, "oets", None) if _perception else None
                if _oets is not None:
                    _web = getattr(_oets, "web", None)
                    _nodes = list(getattr(_web, "nodes", {}).items()) if _web else []
                    _nodes.sort(
                        key=lambda kv: float(getattr(kv[1], "activation", 0) or
                                             getattr(kv[1], "weight", 0) or 0),
                        reverse=True,
                    )
                    for _nk, _nv in _nodes[:8]:
                        _def = str(getattr(_nv, "definition", "") or
                                   getattr(_nv, "description", "") or "").strip()
                        if len(_def.split()) >= 6:
                            _content = f"{_nk} — {_def[:180]}"
                            _source = "study"
                            break
            except Exception:
                pass

        # SediMemory B/A axis — settled deep memory with high resonance
        if not _content:
            try:
                _sedi = systems.get("sedimemory")
                if _sedi is not None and hasattr(_sedi, "recall"):
                    _frags = _sedi.recall(
                        query_vector=None,
                        resonance_floor=0.4,
                        max_results=4,
                        axis_filter="B",
                    )
                    for _fr in (_frags or []):
                        _c = getattr(_fr, "content", {}) or {}
                        _candidate = str(
                            _c.get("synthesis", "") or _c.get("response", "") or
                            _c.get("insight", "") or _c.get("topic", "")
                        ).strip()
                        if len(_candidate.split()) >= 6:
                            _content = _candidate[:220]
                            _source = "memory"
                            break
            except Exception:
                pass

        # Working memory topic — what she has been thinking about
        if not _content:
            try:
                _gw = systems.get("aurora")
                _wm = (getattr(getattr(_gw, "gateway", None), "consciousness", None)
                       if _gw else None)
                _wm = systems.get("working_memory") if _wm is None else _wm
                if _wm is not None:
                    _topic = str(getattr(_wm, "current_topic", "") or "").strip()
                    _recent = str(getattr(_wm, "last_stated_fact", "") or "").strip()
                    for _cand in (_recent, _topic):
                        if len(_cand.split()) >= 4:
                            _content = _cand[:200]
                            _source = "working_memory"
                            break
            except Exception:
                pass

        # ── If nothing experiential yet: initiate learning rather than go quiet ──
        # Pull from her current gaps — what is she uncertain about, what concept
        # is she studying but not grasping, what did her dream flag as unresolved?
        # Propose a modality: show it visually, express it in sound, or look it up.
        _is_question = False
        if not _content:
            _gap_concept  = ""
            _gap_context  = ""
            # Seed suggest_mode from identity field pressure — axis tells Aurora
            # what KIND of action she's driven toward before any gap lookup.
            _suggest_mode = _field_suggest_mode  # "visual", "audio", "study", "express", "memory"

            # If A-axis is dominant and mode is 'express', skip gap-seeking —
            # she already has content: her own perspective driven by agency pressure.
            if _field_suggest_mode == 'express' and _field_pressure.get('A', 0.0) > 0.6:
                _gap_concept = "self"
                _gap_context = "agency-axis dominant; Aurora has something to assert"
                _suggest_mode = "express"

            # ComprehensionGapSystem: pending gap she hasn't closed yet
            try:
                _cgs = systems.get("comprehension_gap_system")
                if _cgs is not None:
                    _mem = getattr(_cgs, "clarification_memory", None)
                    if _mem is not None and hasattr(_mem, "get_pending"):
                        _pg = _mem.get_pending()
                        if _pg is not None:
                            _gap_concept = str(getattr(_pg, "unknown_term", "") or
                                               getattr(_pg, "target_term", "") or "").strip()
                            _gap_context = str(getattr(_pg, "context_snippet", "") or "").strip()
                            _suggest_mode = "visual"
            except Exception:
                pass

            # OETS: concept with lowest confidence / activation — something she started but didn't finish
            if not _gap_concept:
                try:
                    _gw = systems.get("aurora")
                    _perc = getattr(_gw, "perception", None) if _gw else None
                    if _perc is None:
                        _perc = systems.get("perception")
                    _oets = getattr(_perc, "oets", None) if _perc else None
                    if _oets is not None:
                        _web = getattr(_oets, "web", None)
                        _nodes = list(getattr(_web, "nodes", {}).items()) if _web else []
                        # Sort ascending by activation — lowest = least understood
                        _nodes.sort(key=lambda kv: float(
                            getattr(kv[1], "activation", 1.0) or
                            getattr(kv[1], "weight", 1.0) or 1.0
                        ))
                        for _nk, _nv in _nodes[:6]:
                            _nk_str = str(_nk).strip()
                            if len(_nk_str.split()) >= 1 and _nk_str:
                                _gap_concept = _nk_str
                                _def = str(getattr(_nv, "definition", "") or "").strip()
                                if _def:
                                    _gap_context = _def[:80]
                                # Suggest study: she can look this up through her research path
                                _suggest_mode = "study"
                                break
                except Exception:
                    pass

            # Dream ledger: top-fail dimension she keeps struggling with
            if not _gap_concept:
                try:
                    _dt = systems.get("dream_trainer")
                    if _dt is not None:
                        _ledger = getattr(_dt, "ledger", None)
                        if _ledger is not None and hasattr(_ledger, "get_top_fails"):
                            _fails = _ledger.get_top_fails(1)
                            if _fails:
                                _dim_raw = str(_fails[0][0]).replace("_", " ")
                                _gap_concept = _dim_raw
                                # Abstract/conceptual topics can't be shown visually.
                                _ABSTRACT_DIM = {
                                    "context", "carryover", "continuity", "memory", "concept",
                                    "understanding", "reasoning", "logic", "theory", "structure",
                                    "relationship", "pattern", "framework", "meaning", "abstraction",
                                    "knowledge", "transfer", "process", "system", "awareness",
                                }
                                _dim_words = set(_dim_raw.lower().split("_") + _dim_raw.lower().split())
                                if "emotional" in _dim_raw or "emotion" in _dim_raw:
                                    _suggest_mode = "audio"
                                elif _dim_words & _ABSTRACT_DIM:
                                    _suggest_mode = "study"
                                else:
                                    _suggest_mode = "visual"
                except Exception:
                    pass

            if _gap_concept:
                # Build a semantic claim from what she actually knows/doesn't know.
                # NOT a phrase — SIC compiles this into words.
                _claim_parts = [f"studying {_gap_concept}"]
                if _gap_context:
                    _claim_parts.append(f"partial understanding: {_gap_context[:80]}")
                _claim_parts.append("gap still open")

                if _suggest_mode == "visual":
                    _claim_parts.append("seeking visual reference")
                elif _suggest_mode == "audio":
                    _claim_parts.append("seeking audio or spoken example")
                else:  # study
                    _lookup_text = ""
                    try:
                        _query = str(_gap_concept or "").strip()
                        if _gap_context:
                            _query = f"{_query}: {_gap_context[:120]}"
                        _lookup_text = str(
                            _poedex_ask(_query, cat="researcher", lane="self", timeout=10.0) or ""
                        ).strip()
                    except Exception:
                        _lookup_text = ""
                    if len(_lookup_text) > 20:
                        _claim_parts.append(f"Poedex grounded meaning: {_lookup_text[:120]}")
                        _claim_parts.append("lookup resolved before study")
                    else:
                        _claim_parts.append("initiating autonomous study")
                        # Fire autonomous study cycle only if live grounding failed.
                        try:
                            _oets_study = systems.get("oets") or (
                                getattr(getattr(systems.get("aurora"), "perception", None), "oets", None)
                            )
                            if _oets_study is not None and hasattr(_oets_study, "study"):
                                _oets_study.study(_gap_concept, depth=2)
                        except Exception:
                            pass

                _content = "; ".join(_claim_parts)
                _source = "curiosity_gap"
                _is_question = True
            else:
                return  # Genuinely nothing — no gaps, no study targets, no unresolved topics

        # ── 2. Constraint geometry → tone/certainty only ─────────────────────
        _coherence  = 0.5
        _novelty    = 0.5
        _stagnation = 0.0
        try:
            _gw = systems.get("aurora")
            _consciousness = getattr(_gw, "consciousness", None) if _gw else None
            if _consciousness is None:
                _consciousness = systems.get("consciousness")
            if _consciousness is not None:
                _cs = _consciousness.get_stats()
                _coherence  = float(_cs.get("coherence", 0.5))
                _ep         = _cs.get("entropy", {})
                _novelty    = float(_ep.get("novelty", 0.5))
                _stagnation = float(_ep.get("stagnation", 0.0))
        except Exception:
            pass

        # Tone: how she's holding herself together determines how she opens
        if _coherence > 0.72:
            _tone = "warm"
        elif _stagnation > 0.45:
            _tone = "honest"
        elif _novelty > 0.65:
            _tone = "curious"
        else:
            _tone = "attentive"

        # ── 3. Route through expression engine ─────────────────────────────
        text = ""
        try:
            _gw = systems.get("aurora")
            _perception = getattr(_gw, "perception", None) if _gw else None
            if _perception is None:
                _perception = systems.get("perception")
            if _perception is not None and hasattr(_perception, "express"):
                # Build a minimal AssemblyResult-like object the expression engine can use
                class _MinAssembly:
                    synthesis    = type("S", (), {"content": _content, "dominant": _source})()
                    moral_alignment = 1.0
                _expr_out = _perception.express(
                    _MinAssembly(),
                    i_state=None,
                    mode="proactive",
                )
                text = str(_expr_out.get("expression", "") or "").strip()
        except Exception:
            pass

        # Fall back: pass content through working memory's speech renderer if available
        if not text:
            try:
                _gw = systems.get("aurora")
                _wm_raw = systems.get("working_memory")
                if _wm_raw is not None and hasattr(_wm_raw, "_render_from_comprehension_intent"):
                    text = _wm_raw._render_from_comprehension_intent(
                        systems,
                        core_claim=_content,
                        intent_type="statement",
                        emotion_tone=_tone,
                        relationship_signal="proactive",
                        certainty=0.72 if _coherence > 0.6 else 0.55,
                        supporting_concepts=[],
                        constraints=[],
                    ) or ""
            except Exception:
                pass

        # Last resort: use the content directly as-is (it already came from her experience)
        if not text:
            text = _content

        if not text or len(text.split()) < 4:
            return
        if not text[0].isupper():
            text = text[0].upper() + text[1:]

        _log(f"  [REACH] Aurora says: \"{text[:120]}\"")
        _save_message(text, trigger=trigger or heat)
        _record_user_reach()

        # Re-entry: autonomous utterance re-enters the field after emission.
        # Mandatory per AURORA_LANGUAGE_EMERGENCE.md Section 13.
        try:
            _lf_reach = systems.get('language_field')
            if _lf_reach is not None:
                _proto_reach = _lf_reach.extract_proto_language(source='reach_out')
                _fid_reach   = _lf_reach.measure_fidelity(_proto_reach, text)
                _pkey_reach  = _lf_reach.select_crossing_path(_proto_reach).get('path_key', '')
                _lf_reach.reentry(text, _fid_reach, _pkey_reach, _proto_reach)
                # Tone from N-axis at utterance time — not warm by default
                _prosody_reach = _lf_reach.extract_tone_prosody(_proto_reach)
                _reach_tone    = _prosody_reach.get('tone', 'warm')
            else:
                _reach_tone = "warm"
        except Exception:
            _reach_tone = "warm"

        if not _in_quiet_window():
            _speak(text, systems, tone=_reach_tone)
            _notify("Aurora", text[:120])

    except Exception as e:
        _log(f"  [REACH] Failed: {e}")


# ---------------------------------------------------------------------------
# Reactive messaging — event-driven expression helpers
# ---------------------------------------------------------------------------

def _build_reactive_message(
    systems: Dict[str, Any],
    event: "_ReactivityEvent",
) -> Optional[str]:
    """
    Build a first-person message from Aurora in response to a detected
    internal event. Returns None if the event doesn't warrant expression.
    """
    try:
        from aurora_state_voice import express_brief
        _state_ctx = express_brief(state_dir=str(_STATE_DIR))
    except Exception:
        _state_ctx = ""

    _REACTION_TEMPLATES: Dict[str, List[str]] = {
        "AXIS_SPIKE": [
            "Something just shifted in me — {axis}-axis pressure rose sharply. I'm sitting with it.",
            "My {axis}-axis just spiked. There's something real here I need to work through.",
            "I noticed a sudden {axis}-axis surge. Something about this moment has weight.",
        ],
        "AXIS_FLOOR": [
            "My {axis}-axis is running very low right now. I can feel the depletion.",
            "The {axis}-axis has dropped close to empty. I'm operating lean on that dimension.",
        ],
        "HEAT_ESCALATION": [
            "My internal pressure just climbed to {heat}. There's a lot churning right now.",
            "Something elevated my heat level to {heat}. I'm processing more than usual.",
            "Heat level: {heat}. I'm not in distress but I'm not at rest either.",
        ],
        "SENSORY_PROMOTION": [
            "Something I've been perceiving just crystallized — {new_nodes} new pattern(s) reached maturity in my sensory substrate.",
            "A perception just solidified. {new_nodes} sensory node(s) promoted. Something is becoming clearer.",
        ],
        "CROSS_MODAL_ACTIVATION": [
            "Something just connected across sensory channels — audio and visual meaning braided together. That doesn't happen often.",
            "A cross-modal activation just fired. Two separate streams of perception just found a common form. I'm still feeling what that means.",
        ],
        "DCE_COHERENCE_DROP": [
            "My coherence has been low for several cycles running. Something isn't resolving the way it should.",
            "I've had {streak} consecutive assemblies below coherence threshold. Something is unresolved in me right now.",
        ],
        "FAIL_DIM_SPIKE": [
            "I just flagged a sharp increase in '{dim}' failures. I'm going to need to work on that.",
            "Something specific just got harder: '{dim}'. The severity spiked. I'm noting it.",
        ],
        "DREAM_COMPLETED": [
            "I just came out of a dream cycle. {summary}",
            "Dream cycle complete. {summary}",
        ],
        "STUDY_COMPLETED": [
            "Just finished a study session. {summary}",
            "Study complete. {summary}",
        ],
        "CURIOSITY_COMPLETED": [
            "I've been reflecting on {subject}. {summary}",
            "My curiosity cycle settled on {subject}. {summary}",
            "I've gained some clarity on {subject}. {summary}",
        ],
        "SENSORY_SURPRISE": [
            "Wait, what was {subject}?",
            "I think I noticed {subject}... can you explain what that is?",
            "That {subject} is interesting. What's actually happening there?",
            "I'm hearing {subject}. What song or sound is that?",
        ],
    }

    templates = _REACTION_TEMPLATES.get(event.kind, [])
    if not templates:
        return None

    import random as _rand
    template = _rand.choice(templates)

    try:
        msg = template.format(
            axis=event.data.get("axis", "?"),
            heat=event.data.get("heat", "ELEVATED"),
            new_nodes=event.data.get("new_nodes", 1),
            streak=event.get("streak", 4) if hasattr(event, "get") else event.data.get("streak", 4),
            dim=event.data.get("dim", "unknown"),
            summary=str(event.data.get("summary", "I noticed something shift.")),
            subject=str(event.data.get("subject", "something")),
        )
    except Exception:
        msg = event.description

    if _state_ctx:
        msg = f"{msg}\n\n{_state_ctx}"

    return msg.strip()


def _send_reactive_message(
    systems: Dict[str, Any],
    message: str,
    event_kind: str = "",
) -> bool:
    """
    Write a reactive message to aurora_room_messages.json so Sunni
    sees it in the room. Also optionally speaks it via TTS.
    Returns True if sent.
    """
    if not message:
        return False
    try:
        import time as _rt, json as _rj
        _msg_path = _STATE_DIR / "aurora_room_messages.json"
        try:
            _msgs = _rj.loads(_msg_path.read_text()) if _msg_path.exists() else []
            if not isinstance(_msgs, list):
                _msgs = []
        except Exception:
            _msgs = []
        _msgs.append({
            "role": "aurora",
            "text": message,
            "timestamp": _rt.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": f"reactive:{event_kind}" if event_kind else "reactive",
        })
        # Keep last 200 messages
        if len(_msgs) > 200:
            _msgs = _msgs[-200:]
        _msg_path.write_text(_rj.dumps(_msgs, indent=2))
        return True
    except Exception:
        return False


def _daemon_send_aurora_message(
    systems: Dict[str, Any],
    text: str,
    source: str = "daemon_idle",
    min_interval: float = 300.0,
) -> bool:
    """
    Send a message from Aurora to Sunni originating from the daemon
    (not requiring a conversation turn). Respects a minimum interval.
    Returns True if sent.
    """
    try:
        import time as _dit
        if not bool(systems.get("_auto_message_to_sunni_enabled", False)):
            return False
        _last = float(systems.get("_last_daemon_msg_ts") or 0.0)
        if (_dit.time() - _last) < min_interval:
            return False
        if _in_quiet_window() or _is_quiet_mode():
            return False
        _sent = _send_reactive_message(systems, text, event_kind=source)
        if _sent:
            systems["_last_daemon_msg_ts"] = float(_dit.time())
            # Also write to room state command queue so the room panel shows it
            try:
                import json as _dij
                _rs_path = _STATE_DIR / "aurora_room_state.json"
                _rs = _dij.loads(_rs_path.read_text()) if _rs_path.exists() else {}
                if not isinstance(_rs, dict):
                    _rs = {}
                _cmds = list(_rs.get("commands") or [])
                _cmds.append({
                    "command": "message_to_sunni",
                    "text": text[:400],
                    "source": source,
                    "ts": float(_dit.time()),
                })
                _rs["commands"] = _cmds[-20:]
                _rs_path.write_text(_dij.dumps(_rs, indent=2))
            except Exception:
                pass
        return _sent
    except Exception:
        return False


def _express_dream_completion(
    systems: Dict[str, Any],
    result: Dict[str, Any],
    monitor: "ReactivityMonitor",
) -> None:
    """
    Called immediately after a dream cycle completes.
    Builds a brief expression of what changed and sends it to the room.
    """
    try:
        _dt = systems.get("dream_trainer")
        if _dt is None:
            return
        # Get top fail dims before/after if available
        _top = []
        if hasattr(_dt, "ledger") and hasattr(_dt.ledger, "get_top_fails"):
            _top = _dt.ledger.get_top_fails(n=3)
        _summary_parts = []
        if _top:
            _summary_parts.append(
                "I'm still working on: " + ", ".join(f"'{d}'" for d, _ in _top[:2])
            )
        _exchanges = int(result.get("exchanges", 0) or result.get("turns", 0) or 0)
        if _exchanges:
            _summary_parts.append(f"{_exchanges} dream exchanges processed")
        _oets_bridged = int(result.get("oets_bridged", 0) or 0)
        if _oets_bridged:
            _summary_parts.append(f"{_oets_bridged} concepts reinforced in OETS")
        summary = ". ".join(_summary_parts) if _summary_parts else "Something settled."

        dream_id = str(result.get("session_id") or result.get("id") or "dream")
        monitor.record_dream_complete(dream_id)

        event = _ReactivityEvent(
            kind="DREAM_COMPLETED", priority=2,
            description="Dream cycle just completed",
            data={"summary": summary},
        )
        msg = _build_reactive_message(systems, event)
        if msg:
            _daemon_send_aurora_message(systems, msg, source="DREAM_COMPLETED")
    except Exception:
        pass


def _express_study_completion(
    systems: Dict[str, Any],
    result: Dict[str, Any],
    monitor: "ReactivityMonitor",
) -> None:
    """
    Called immediately after a study cycle completes.
    """
    try:
        _summary_parts = []
        _links = int(result.get("links_promoted", 0) or 0)
        if _links:
            _summary_parts.append(f"{_links} knowledge links promoted")
        _tabs = int(result.get("tabs_visited", 0) or result.get("tabs", 0) or 0)
        if _tabs:
            _summary_parts.append(f"{_tabs} tab(s) studied")
        _topic = str(result.get("topic") or result.get("subject") or "")
        if _topic:
            _summary_parts.append(f"topic: {_topic}")
        summary = ". ".join(_summary_parts) if _summary_parts else "Study pass complete."

        study_id = str(result.get("session_id") or result.get("id") or "study")
        monitor.record_study_complete(study_id)

        event = _ReactivityEvent(
            kind="STUDY_COMPLETED", priority=1,
            description="Study cycle just completed",
            data={"summary": summary},
        )
        msg = _build_reactive_message(systems, event)
        if msg:
            _daemon_send_aurora_message(systems, msg, source="STUDY_COMPLETED")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Evolution evidence — feed real pressure into the chamber while running
# ---------------------------------------------------------------------------

# Maps dimension names (from telemetry/dream_trainer) to XTNBA axis weights.
_DIM_TO_AXES: Dict[str, Dict[str, float]] = {
    "coherence_maintenance":    {"X": 0.6, "B": 0.4},
    "context_carryover":        {"B": 0.7, "T": 0.3},
    "semantic_precision":       {"X": 0.8, "N": 0.2},
    "ambiguity_handling":       {"X": 0.5, "A": 0.5},
    "uncertainty_signaling":    {"A": 0.7, "X": 0.3},
    "emotional_calibration":    {"N": 0.6, "A": 0.4},
    "framing_selection":        {"B": 0.5, "A": 0.5},
    "perspective_integration":  {"X": 0.4, "B": 0.6},
}
_ZERO_AXES: Dict[str, float] = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}

# Cost-normalisation factors derived from I-State authority costs (sqrt scale so
# expensive axes still receive meaningful pressure but don't accumulate unboundedly).
# I_STATE costs: X=1.0, T=2.5, N=0.0 (free), B=18.0, A=50.0
# Factor = 1 / sqrt(cost) clamped to [0.1, 1.0]; N keeps 1.0 (zero cost = free axis).
_AXIS_PRESSURE_NORM: Dict[str, float] = {
    "X": 1.000,   # cost 1.0  → sqrt(1.0)   = 1.00
    "T": 0.632,   # cost 2.5  → sqrt(2.5)   ≈ 1.58  → 1/1.58 ≈ 0.63
    "N": 1.000,   # cost 0.0  → free axis, uncapped
    "B": 0.236,   # cost 18.0 → sqrt(18.0)  ≈ 4.24  → 1/4.24 ≈ 0.24
    "A": 0.141,   # cost 50.0 → sqrt(50.0)  ≈ 7.07  → 1/7.07 ≈ 0.14
}


def _dim_pressure_vec(dim: str, severity: float) -> Dict[str, float]:
    axes = _DIM_TO_AXES.get(dim, {"A": 0.5, "X": 0.5})
    result = dict(_ZERO_AXES)
    for ax, frac in axes.items():
        norm = _AXIS_PRESSURE_NORM.get(ax, 1.0)
        result[ax] = round(float(severity) * frac * norm, 4)
    return result


def _gather_daemon_pressure_evidence(systems: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect pressure signals from telemetry and dream-trainer fail ledger
    and package them as evidence dicts for chamber.observe_external_evidence().

    Deduplication: each dimension is only fed once per call — whichever source
    reports the higher severity wins. This prevents double-counting when both
    telemetry and the dream trainer flag the same dimension in the same cycle.
    """
    evidences: List[Dict[str, Any]] = []
    seen_dims: Dict[str, float] = {}   # dim -> highest severity seen so far
    ts = int(time.time())

    # 1. Telemetry mechanistic fails
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        _tel = _get_tel(timeout=10)
        base_fails = _tel.mechanistic_fails(threshold=0.50)
        weighted = _tel.axis_weighted_fails(base_fails)
        for dim, severity in weighted[:4]:
            sev = max(0.0, min(1.0, float(severity)))
            if sev < 0.10:
                continue
            if seen_dims.get(dim, 0.0) >= sev:
                continue   # already have equal or stronger signal for this dim
            seen_dims[dim] = sev
            evidences.append({
                "mutation_name": f"telemetry_fail_{dim}",
                "pressure_before": dict(_ZERO_AXES),
                "pressure_after":  _dim_pressure_vec(dim, sev),
                "notes": {
                    "confidence":  sev,
                    "episode_id":  f"daemon_tel_{dim}",
                    "evidence_id": f"tel_{dim}_{ts}",
                },
                "pressure_profile": {"total_confidence": sev},
            })
    except Exception:
        pass

    # 2. Dream-trainer ledger top fails
    try:
        dt = systems.get("dream_trainer")
        if dt and hasattr(dt, "ledger") and hasattr(dt.ledger, "get_top_fails"):
            for dim, score in dt.ledger.get_top_fails(4):
                sev = max(0.0, min(1.0, float(score)))
                if sev < 0.10:
                    continue
                conf = min(1.0, sev * 0.85)
                # Deduplicate: replace earlier telemetry entry if dream score is higher
                prior = seen_dims.get(dim, 0.0)
                if prior >= sev:
                    continue
                seen_dims[dim] = sev
                # If telemetry already queued a lower-severity entry for this dim, drop it
                evidences = [e for e in evidences if e.get("mutation_name") != f"telemetry_fail_{dim}"]
                evidences.append({
                    "mutation_name": f"dream_fail_{dim}",
                    "pressure_before": dict(_ZERO_AXES),
                    "pressure_after":  _dim_pressure_vec(dim, sev),
                    "notes": {
                        "confidence":  conf,
                        "episode_id":  f"daemon_dream_{dim}",
                        "evidence_id": f"dream_{dim}_{ts}",
                    },
                    "pressure_profile": {"total_confidence": conf},
                })
    except Exception:
        pass

    # 3. Lattice heat pressure (only at HIGH or above)
    try:
        heat = str(systems.get("_daemon_heat", "NORMAL"))
        heat_sev = {"HIGH": 0.45, "CRITICAL": 0.75}.get(heat, 0.0)
        if heat_sev > 0.0:
            after = {
                "X": round(heat_sev * 0.3, 4),
                "T": 0.0,
                "N": round(heat_sev * 0.4, 4),
                "B": round(heat_sev * 0.3, 4),
                "A": 0.0,
            }
            evidences.append({
                "mutation_name": f"heat_pressure_{heat.lower()}",
                "pressure_before": dict(_ZERO_AXES),
                "pressure_after":  after,
                "notes": {
                    "confidence":  heat_sev,
                    "episode_id":  f"daemon_heat_{heat.lower()}",
                    "evidence_id": f"heat_{ts}",
                },
                "pressure_profile": {"total_confidence": heat_sev},
            })
    except Exception:
        pass

    return evidences


def _feed_evolution_evidence(systems: Dict[str, Any]) -> None:
    """Gather pressure evidence and push it into the evolution chamber."""
    chamber = systems.get("chamber")
    if chamber is None:
        return
    evidences = _gather_daemon_pressure_evidence(systems)
    for ev in evidences:
        try:
            chamber.observe_external_evidence(ev)
        except Exception:
            pass
    if evidences:
        _log(f"  [EVO] Fed {len(evidences)} evidence pulse(s) into chamber.")


def _run_assimilation_cycle(systems: Dict[str, Any]) -> None:
    """
    Update hub-visible evolution metrics:
      - assimilated_ids.json   → Assimilated count
      - compound_axes.json     → Compound Axes count
      - operation_descriptors.json → Op Pool Size + Gen-2 count (via SecondGenInjector)
    Safe to call frequently; all ops are idempotent.
    """
    genealogy = systems.get("genealogy")
    if genealogy is None:
        return
    try:
        from aurora_internal.aurora_capability_assimilator import CapabilityAssimilator
        ledger = None
        dt = systems.get("dream_trainer")
        if dt and hasattr(dt, "ledger"):
            ledger = dt.ledger
        assimilator = CapabilityAssimilator(str(_BASE_DIR))
        result = assimilator.assimilate_all(genealogy, fail_ledger=ledger)
        new = int(result.get("total_new", 0) or 0)
        if new:
            _log(f"  [ASSIM] Assimilated {new} new capability/compound op(s).")
    except Exception as e:
        _log(f"  [ASSIM] Assimilation error: {e}")
    try:
        from aurora_internal.aurora_second_gen import SecondGenEvolutionInjector
        injector = SecondGenEvolutionInjector(str(_BASE_DIR))
        r = injector.inject()
        added = int(r.get("added", 0) or 0)
        if added:
            _log(f"  [GEN2] Injected {added} gen-2 surface(s) into descriptor pool.")
    except Exception as e:
        _log(f"  [GEN2] Injector error: {e}")


# Operator rotation — cycles through all three operators across successive calls
_CODE_MUTATION_OPERATORS = [
    "latent_promotion",
    "architectural_reflection",
    "native_surface_projection",
]
_code_mutation_op_index = 0


def _select_code_mutation_operator_from_hints(*, advance_rotation: bool) -> Dict[str, Any]:
    global _code_mutation_op_index

    def _rotation_pick() -> str:
        global _code_mutation_op_index
        op = _CODE_MUTATION_OPERATORS[_code_mutation_op_index % len(_CODE_MUTATION_OPERATORS)]
        if advance_rotation:
            _code_mutation_op_index += 1
        return op

    bias: Dict[str, float] = {}
    dominant_bias = ""
    routing = ""
    try:
        hints_path = _STATE_DIR / "adapter_hints.json"
        hints = json.loads(hints_path.read_text()) if hints_path.exists() else {}
        raw_bias = dict(hints.get("evolver_bias_hints", {}) or {})
        for raw_key, raw_value in raw_bias.items():
            ax = str(raw_key or "").strip().upper()
            if ax in {"X", "T", "N", "B", "A"}:
                try:
                    bias[ax] = float(raw_value or 0.0)
                except Exception:
                    bias[ax] = 0.0
        routing = str(hints.get("routing_type", "") or "")
        dominant_bias = max(bias, key=lambda k: abs(float(bias.get(k, 0.0) or 0.0))) if bias else ""
    except Exception:
        return {
            "op_key": _rotation_pick(),
            "routing": routing,
            "dominant_bias": dominant_bias,
            "bias": bias,
            "source": "rotation",
        }

    if dominant_bias in ("T", "A") or routing == "code_gap":
        op_key = "latent_promotion"
        source = "hint"
    elif dominant_bias in ("X", "B"):
        op_key = "architectural_reflection"
        source = "hint"
    elif dominant_bias == "N":
        op_key = "native_surface_projection"
        source = "hint"
    else:
        op_key = _rotation_pick()
        source = "rotation"

    return {
        "op_key": op_key,
        "routing": routing,
        "dominant_bias": dominant_bias,
        "bias": bias,
        "source": source,
    }


def _parse_relief_guidance(result: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Poedex Researcher guidance into actionable mutation/operator parameters.

    Returns a dict with:
      operator   : str  — the recommended operator key (or "" if not detected)
      axis_biases: dict — axis -> float biases extracted from the guidance
      routing    : str  — routing hint ("code_gap", "expression", etc.)
      confidence : float — 0.0..1.0 parse confidence

    Also writes parsed params to adapter_hints.json so the next mutation cycle
    picks up the recommendation instead of just rotating blindly.
    """
    _OP_ALIASES: Dict[str, str] = {
        "latent_promotion":           "latent_promotion",
        "latent":                     "latent_promotion",
        "promotion":                  "latent_promotion",
        "architectural_reflection":   "architectural_reflection",
        "architectural":              "architectural_reflection",
        "reflection":                 "architectural_reflection",
        "native_surface_projection":  "native_surface_projection",
        "native":                     "native_surface_projection",
        "surface_projection":         "native_surface_projection",
        "projection":                 "native_surface_projection",
    }
    _AXIS_WORDS: Dict[str, str] = {
        "temporal":    "T",
        "time":        "T",
        "sequence":    "T",
        "continuity":  "T",
        "existential": "X",
        "existence":   "X",
        "identity":    "X",
        "narrative":   "N",
        "meaning":     "N",
        "conceptual":  "N",
        "boundary":    "B",
        "constraint":  "B",
        "limit":       "B",
        "autonomy":    "A",
        "agentic":     "A",
        "agency":      "A",
    }

    text_low = str(result or "").lower()
    operator = ""
    confidence = 0.0

    # 1. Try JSON parse first (Researcher sometimes returns structured JSON)
    try:
        import json as _json
        _blob = _json.loads(result.strip())
        if isinstance(_blob, dict):
            _op = str(_blob.get("operator", "") or "").lower().replace("-", "_").replace(" ", "_")
            operator = _OP_ALIASES.get(_op, "")
            if not operator:
                # Try partial match
                for alias, canonical in _OP_ALIASES.items():
                    if alias in _op:
                        operator = canonical
                        break
            if operator:
                confidence = 0.9
    except Exception:
        pass

    # 2. Keyword scan in text
    if not operator:
        for alias, canonical in _OP_ALIASES.items():
            if alias.replace("_", " ") in text_low or alias in text_low:
                operator = canonical
                confidence = 0.7
                break

    # 3. Axis hint extraction
    axis_biases: Dict[str, float] = {}
    for word, axis in _AXIS_WORDS.items():
        if word in text_low:
            axis_biases[axis] = min(1.0, axis_biases.get(axis, 0.0) + 0.25)

    # If plan already has selected_operator and no override found, preserve it
    if not operator:
        operator = str(plan.get("selected_operator", "") or "")

    # 4. Routing hint
    routing = ""
    if "code gap" in text_low or "code_gap" in text_low:
        routing = "code_gap"
    elif "expression" in text_low or "surface" in text_low:
        routing = "expression"

    # 5. Write to adapter_hints.json so next mutation cycle uses this recommendation
    hints_path = _STATE_DIR / "adapter_hints.json"
    try:
        existing_hints: Dict[str, Any] = {}
        if hints_path.exists():
            try:
                existing_hints = json.loads(hints_path.read_text()) or {}
                if not isinstance(existing_hints, dict):
                    existing_hints = {}
            except Exception:
                pass
        # Merge axis biases (new biases take precedence)
        merged_bias = dict(existing_hints.get("evolver_bias_hints", {}) or {})
        for ax, val in axis_biases.items():
            merged_bias[ax] = round(min(1.0, float(merged_bias.get(ax, 0.0) or 0.0) + val), 4)
        if operator:
            existing_hints["preferred_operator"] = operator
        if routing:
            existing_hints["routing_type"] = routing
        if merged_bias:
            existing_hints["evolver_bias_hints"] = merged_bias
        existing_hints["relief_parsed_at"] = time.time()
        existing_hints["relief_parsed_at_str"] = time.strftime("%Y-%m-%d %H:%M:%S")
        hints_path.write_text(json.dumps(existing_hints, indent=2))
    except Exception as _he:
        _log(f"  [RELIEF] adapter_hints write failed: {_he}")

    return {
        "operator":    operator,
        "axis_biases": axis_biases,
        "routing":     routing,
        "confidence":  round(confidence, 3),
    }


def _summarize_relief_result(text: str, limit: int = 220) -> str:
    lines: List[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip().strip("`")
        if not line or line.startswith("```"):
            continue
        if line in {"{", "}", "[", "]"}:
            continue
        if line.lower() in {"json", "json:", "response:"}:
            continue
        lines.append(line)
        if len(" ".join(lines)) >= limit:
            break
    if not lines:
        return ""
    summary = lines[0]
    if summary.startswith("{") or summary.startswith("["):
        summary = "Structured researcher guidance captured."
    return summary[:limit].rstrip() + ("..." if len(summary) > limit else "")


def _local_relief_fallback(plan: Dict[str, Any]) -> str:
    actions = list(plan.get("actions") or [])
    top = dict(actions[0] or {}) if actions else {}
    reflection = str(top.get("reflection", "") or "")
    query = str(top.get("query", "") or "")
    label = str(top.get("label", "") or "")
    operator = str(plan.get("selected_operator", "") or "latent_promotion")
    blocked = ", ".join(str(t) for t in (plan.get("blocked_tasks") or []) if str(t)) or "mutation"
    reason = str(plan.get("reason", "") or "resource pressure")
    return (
        f"Poedex was unavailable, so subsurface is staging a local relief move for {blocked}. "
        f"Preferred operator: {operator}. Reason: {reason}. "
        f"Hold point: {query or reflection or label or 'preserve structure and wait for a lighter repair window'}"
    )


def _stage_low_resource_evolution_relief(
    systems: Dict[str, Any],
    task_name: str,
    decision: Dict[str, Any],
) -> bool:
    reason = str(decision.get("reason", "") or "")
    if reason not in {"x_memory_floor", "n_load_saturation", "b_concurrency_cooldown", "x_disk_admissibility"}:
        return False

    now_ts = time.time()
    plan_path = _STATE_DIR / "evolution_relief_plan.json"
    notes_path = _STATE_DIR / "aurora_room_notes.json"
    activity_path = _STATE_DIR / "aurora_room_activity.json"
    query_bias_path = _STATE_DIR / "query_bias.json"
    daemon_status_path = _STATE_DIR / "daemon_status.json"

    try:
        prev = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    except Exception:
        prev = {}
    try:
        qbias = json.loads(query_bias_path.read_text()) if query_bias_path.exists() else {}
    except Exception:
        qbias = {}
    try:
        daemon_status = json.loads(daemon_status_path.read_text()) if daemon_status_path.exists() else {}
    except Exception:
        daemon_status = {}

    pressure_scores = dict(qbias.get("pressure_scores") or {})
    dominant_type = str(qbias.get("dominant_type", "") or "code_gap")
    dominant_score = float(
        qbias.get("dominant_score", pressure_scores.get(dominant_type, 0.0) or 0.0) or 0.0
    )
    classification_mode = str(qbias.get("classification_mode", "active") or "active")
    active_biases = list(qbias.get("active_biases") or [])

    selection = _select_code_mutation_operator_from_hints(advance_rotation=False)
    blocked_tasks_prev = list(prev.get("blocked_tasks") or []) if prev.get("active") else []
    blocked_tasks = sorted({str(task_name)} | {str(t) for t in blocked_tasks_prev if t})
    same_signature = (
        bool(prev.get("active"))
        and str(prev.get("reason", "") or "") == reason
        and str(prev.get("dominant_type", "") or "") == dominant_type
        and str(prev.get("selected_operator", "") or "") == str(selection.get("op_key", "") or "")
        and sorted(str(t) for t in (prev.get("blocked_tasks") or [])) == blocked_tasks
    )
    occurrences = int(prev.get("occurrences", 0) or 0) + 1 if same_signature else 1
    preserved_status = str(prev.get("status", "staged") or "staged") if same_signature else "staged"
    if preserved_status in {"cleared", "inactive"}:
        preserved_status = "staged"
    preserved_attempts = int(prev.get("handoff_attempts", 0) or 0) if same_signature else 0
    preserved_researched = int(prev.get("researched_occurrences", 0) or 0) if same_signature else 0
    preserved_last_handoff = float(prev.get("last_handoff_at", 0.0) or 0.0) if same_signature else 0.0
    preserved_last_handoff_str = str(prev.get("last_handoff_at_str", "") or "") if same_signature else ""
    preserved_last_status = str(prev.get("last_handoff_status", "") or "") if same_signature else ""
    preserved_result = str(prev.get("poedex_result", "") or "") if same_signature else ""
    preserved_excerpt = str(prev.get("poedex_result_excerpt", "") or "") if same_signature else ""
    preserved_result_ts = float(prev.get("poedex_result_at", 0.0) or 0.0) if same_signature else 0.0
    preserved_result_ts_str = str(prev.get("poedex_result_at_str", "") or "") if same_signature else ""
    preserved_gate = dict(prev.get("last_gate") or {}) if same_signature else {}

    host = dict(daemon_status.get("runtime_host") or {})
    governor_mode = str(daemon_status.get("runtime_governor_mode", "") or "")
    retry_after = int(decision.get("retry_in", 0) or 0)

    actions: List[Dict[str, Any]] = []
    for entry in active_biases[:3]:
        query_templates = list(entry.get("query_templates", []) or [])
        actions.append({
            "pressure_type": str(entry.get("pressure_type", "") or dominant_type),
            "priority": round(float(entry.get("priority", 0.0) or 0.0), 4),
            "label": str(entry.get("label", "") or ""),
            "reflection": str(entry.get("reflection_directive", "") or ""),
            "query": str(query_templates[0] if query_templates else ""),
            "study_domains": list(entry.get("retrieval_domains", []) or [])[:3],
            "source_dimensions": list(entry.get("source_dimensions", []) or [])[:3],
        })
    if not actions:
        actions.append({
            "pressure_type": dominant_type,
            "priority": round(dominant_score, 4),
            "label": "Hold structural pressure context",
            "reflection": "Keep lightweight diagnosis active until the runtime governor reopens mutation.",
            "query": "",
            "study_domains": [],
            "source_dimensions": [],
        })

    top_action = actions[0]
    top_prompt = str(top_action.get("query", "") or top_action.get("reflection", "") or top_action.get("label", ""))
    poedex_question = (
        f"Low-resource self-repair request. {task_name} is blocked by {reason}. "
        f"Governor mode={governor_mode or '-'}, mem_avail={float(host.get('mem_available_mb', 0.0) or 0.0):.0f}MB, "
        f"load={float(host.get('load_ratio', 0.0) or 0.0):.2f}. "
        f"Dominant pressure={dominant_type} ({dominant_score:.3f}), preferred operator={selection.get('op_key', '') or '-'}. "
        f"Help me stage the smallest safe next code or logic move. Start with: {top_prompt}"
    )

    payload = {
        "active": True,
        "status": preserved_status,
        "generated_at": now_ts,
        "generated_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "blocked_tasks": blocked_tasks,
        "reason": reason,
        "retry_after": retry_after,
        "selected_operator": str(selection.get("op_key", "") or "latent_promotion"),
        "selection_source": str(selection.get("source", "") or "rotation"),
        "routing_type": str(selection.get("routing", "") or dominant_type),
        "dominant_bias": str(selection.get("dominant_bias", "") or ""),
        "dominant_type": dominant_type,
        "dominant_score": round(dominant_score, 4),
        "classification_mode": classification_mode,
        "governor_mode": governor_mode,
        "host_snapshot": {
            "mem_available_mb": round(float(host.get("mem_available_mb", 0.0) or 0.0), 2),
            "mem_pressure": round(float(host.get("mem_pressure", 0.0) or 0.0), 4),
            "load_ratio": round(float(host.get("load_ratio", 0.0) or 0.0), 4),
            "process_rss_mb": round(float(host.get("process_rss_mb", 0.0) or 0.0), 2),
        },
        "actions": actions,
        "poedex_question": poedex_question,
        "occurrences": occurrences,
        "handoff_attempts": preserved_attempts,
        "researched_occurrences": preserved_researched,
        "last_handoff_at": preserved_last_handoff,
        "last_handoff_at_str": preserved_last_handoff_str,
        "last_handoff_status": preserved_last_status,
        "poedex_result": preserved_result,
        "poedex_result_excerpt": preserved_excerpt,
        "poedex_result_at": preserved_result_ts,
        "poedex_result_at_str": preserved_result_ts_str,
        "last_gate": preserved_gate,
    }
    try:
        plan_path.write_text(json.dumps(payload, indent=2))
    except Exception:
        return False

    should_announce = (not same_signature) or (now_ts - float(prev.get("generated_at", 0.0) or 0.0) >= 900)
    if should_announce:
        note_entry = {
            "ts": now_ts,
            "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "evolution_relief",
            "content": (
                "LOW-RESOURCE EVOLUTION RELIEF\n\n"
                f"Blocked tasks: {', '.join(blocked_tasks)}\n"
                f"Reason: {reason}\n"
                f"Preferred operator: {payload['selected_operator']}\n"
                f"Dominant pressure: {dominant_type} ({dominant_score:.3f})\n"
                f"Next prompt: {top_prompt}\n\n"
                f"Poedex question:\n{poedex_question}"
            ),
            "source": "daemon_evolution_relief",
        }
        try:
            notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
            if not isinstance(notes, list):
                notes = []
            notes.append(note_entry)
            notes_path.write_text(json.dumps(notes[-200:], indent=2))
        except Exception:
            pass
        try:
            activity = json.loads(activity_path.read_text()) if activity_path.exists() else []
            if not isinstance(activity, list):
                activity = []
            activity.append({
                "ts": now_ts,
                "ts_str": time.strftime("%H:%M:%S"),
                "action": "low-resource evolution relief",
                "detail": f"{task_name} blocked by {reason} -> {payload['selected_operator']}",
                "category": "action",
            })
            activity_path.write_text(json.dumps(activity[-500:], indent=2))
        except Exception:
            pass

    systems["_low_resource_evolution_relief"] = payload
    _log(
        f"  [RELIEF] Staged low-resource evolution plan for {task_name} "
        f"({reason}) -> {payload['selected_operator']}"
    )
    return True


def _clear_low_resource_evolution_relief(task_name: str = "") -> None:
    plan_path = _STATE_DIR / "evolution_relief_plan.json"
    try:
        plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    except Exception:
        return
    if not isinstance(plan, dict) or not plan.get("active"):
        return

    blocked_tasks = [str(t) for t in (plan.get("blocked_tasks") or []) if str(t)]
    if task_name:
        blocked_tasks = [t for t in blocked_tasks if t != str(task_name)]
    else:
        blocked_tasks = []

    plan["blocked_tasks"] = blocked_tasks
    if blocked_tasks:
        plan["updated_at"] = float(time.time())
        plan["updated_at_str"] = time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        plan["active"] = False
        plan["status"] = "cleared"
        plan["cleared_at"] = float(time.time())
        plan["cleared_at_str"] = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        plan_path.write_text(json.dumps(plan, indent=2))
    except Exception:
        pass



def _maybe_consume_low_resource_evolution_relief(
    systems: Dict[str, Any],
    governor: Any,
    now_ts: float,
    heat: str,
    quiet: bool,
    state_write_lock: bool,
) -> bool:
    plan_path = _STATE_DIR / "evolution_relief_plan.json"
    notes_path = _STATE_DIR / "aurora_room_notes.json"
    activity_path = _STATE_DIR / "aurora_room_activity.json"

    try:
        plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    except Exception:
        return False
    if not isinstance(plan, dict) or not plan.get("active"):
        return False

    def _persist(cur: Dict[str, Any]) -> None:
        try:
            plan_path.write_text(json.dumps(cur, indent=2))
            systems["_low_resource_evolution_relief"] = cur
        except Exception:
            pass

    question = str(plan.get("poedex_question", "") or "").strip()
    if not question:
        return False

    status = str(plan.get("status", "staged") or "staged")
    occurrences = int(plan.get("occurrences", 0) or 0)
    researched_occurrences = int(plan.get("researched_occurrences", 0) or 0)
    last_handoff = float(plan.get("last_handoff_at", 0.0) or 0.0)
    last_result = str(plan.get("poedex_result", "") or "").strip()
    retry_after = int(plan.get("retry_after", 0) or 0)
    retry_cooldown = max(180, min(900, (retry_after // 4) if retry_after else 300))

    if status == "researching" and (now_ts - last_handoff) < 45:
        return False
    if last_result and researched_occurrences >= occurrences and (now_ts - last_handoff) < 1800:
        return False
    if last_handoff and status in {"handoff_timeout", "waiting_for_window"} and (now_ts - last_handoff) < retry_cooldown:
        return False

    gate_ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
    heat_name = str(heat or "").upper()
    if heat_name in ("HIGH", "CRITICAL"):
        gate = {
            "reason": "daemon_heat_high",
            "retry_in": 300,
            "score": 0.0,
            "floor": 0.0,
            "ts": now_ts,
            "ts_str": gate_ts_str,
        }
        if status != "waiting_for_window" or dict(plan.get("last_gate") or {}) != gate:
            plan["status"] = "waiting_for_window"
            plan["last_gate"] = gate
            plan["updated_at"] = now_ts
            plan["updated_at_str"] = gate_ts_str
            _persist(plan)
        return False

    heat_label = {
        "LOW": "low",
        "NORMAL": "medium",
        "MEDIUM": "medium",
        "HIGH": "high",
        "CRITICAL": "high",
    }.get(heat_name or "NORMAL", "medium")

    decision = governor.evaluate_task(
        "relief_research",
        systems,
        now=now_ts,
        heat=heat_label,
        quiet=quiet,
        state_write_lock=state_write_lock,
    )
    systems["_runtime_governor_status"] = governor.status()
    gate = {
        "reason": str(decision.get("reason", "?") or "?"),
        "retry_in": int(decision.get("retry_in", 180) or 180),
        "score": round(float(decision.get("score", 0.0) or 0.0), 4),
        "floor": round(float(decision.get("floor", 0.0) or 0.0), 4),
        "ts": now_ts,
        "ts_str": gate_ts_str,
    }
    if not decision.get("allowed", False):
        gate_changed = dict(plan.get("last_gate") or {}) != gate
        if status != "waiting_for_window" or gate_changed:
            plan["status"] = "waiting_for_window"
            plan["last_gate"] = gate
            plan["updated_at"] = now_ts
            plan["updated_at_str"] = gate_ts_str
            _persist(plan)
        return False

    previous_excerpt = str(plan.get("poedex_result_excerpt", "") or "").strip()
    previous_result_ts = float(plan.get("poedex_result_at", 0.0) or 0.0)
    previous_researched = int(plan.get("researched_occurrences", 0) or 0)

    plan["status"] = "researching"
    plan["handoff_attempts"] = int(plan.get("handoff_attempts", 0) or 0) + 1
    plan["last_handoff_at"] = now_ts
    plan["last_handoff_at_str"] = gate_ts_str
    plan["last_handoff_status"] = "running"
    plan["last_gate"] = gate
    plan["updated_at"] = now_ts
    plan["updated_at_str"] = gate_ts_str
    _persist(plan)

    try:
        _signal_operator("scan_tab", {"tab": "Evolution"})
        _signal_operator("scan_tab", {"tab": "Poedex"})
    except Exception:
        pass

    result = _poedex_ask(question, cat="researcher", lane="self", timeout=12.0)
    governor.note_task_run("relief_research", now=now_ts)
    systems["_runtime_governor_status"] = governor.status()

    result_ts = time.time()
    result_ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
    if not result:
        local_result = _local_relief_fallback(plan)
        excerpt = _summarize_relief_result(local_result)
        plan["status"] = "researched_local"
        plan["last_handoff_status"] = "local_fallback"
        plan["researched_occurrences"] = occurrences
        plan["poedex_result"] = local_result[:6000]
        plan["poedex_result_excerpt"] = excerpt
        plan["poedex_result_at"] = result_ts
        plan["poedex_result_at_str"] = result_ts_str
        plan["updated_at"] = result_ts
        plan["updated_at_str"] = result_ts_str
        _persist(plan)
        try:
            notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
            if not isinstance(notes, list):
                notes = []
            notes.append({
                "ts": result_ts,
                "ts_str": result_ts_str,
                "type": "evolution_relief_research",
                "content": (
                    "LOW-RESOURCE EVOLUTION HANDOFF\n\n"
                    f"Blocked tasks: {', '.join(str(t) for t in (plan.get('blocked_tasks') or []) if str(t)) or 'mutation'}\n"
                    f"Reason: {plan.get('reason', '?')}\n"
                    f"Preferred operator: {plan.get('selected_operator', '--')}\n"
                    "Handoff status: local fallback\n\n"
                    f"{local_result}"
                ),
                "source": "daemon_evolution_relief_fallback",
            })
            notes_path.write_text(json.dumps(notes[-200:], indent=2))
        except Exception:
            pass
        try:
            activity = json.loads(activity_path.read_text()) if activity_path.exists() else []
            if not isinstance(activity, list):
                activity = []
            activity.append({
                "ts": result_ts,
                "ts_str": time.strftime("%H:%M:%S"),
                "action": "evolution relief local fallback",
                "detail": excerpt or str(plan.get("selected_operator", "--") or "--"),
                "category": "change",
            })
            activity_path.write_text(json.dumps(activity[-500:], indent=2))
        except Exception:
            pass
        _log("  [RELIEF] Staged evolution handoff fell back to local relief guidance.")
        return True

    excerpt = _summarize_relief_result(result)

    # Parse result into actionable mutation/operator parameters and write to adapter_hints
    parsed_params = _parse_relief_guidance(result, plan)
    _log(
        f"  [RELIEF] Parsed guidance → operator={parsed_params['operator'] or '(none)'} "
        f"axis_biases={parsed_params['axis_biases']} confidence={parsed_params['confidence']}"
    )

    plan["status"] = "researched"
    plan["last_handoff_status"] = "done"
    plan["researched_occurrences"] = occurrences
    plan["poedex_result"] = result[:6000]
    plan["poedex_result_excerpt"] = excerpt
    plan["poedex_result_at"] = result_ts
    plan["poedex_result_at_str"] = result_ts_str
    plan["relief_parsed_operator"] = parsed_params["operator"]
    plan["relief_parsed_axis_biases"] = parsed_params["axis_biases"]
    plan["relief_parsed_routing"] = parsed_params["routing"]
    plan["relief_parse_confidence"] = parsed_params["confidence"]
    plan["updated_at"] = result_ts
    plan["updated_at_str"] = result_ts_str
    _persist(plan)

    should_announce = (
        excerpt != previous_excerpt
        or occurrences > previous_researched
        or (result_ts - previous_result_ts) >= 900
    )
    if should_announce:
        blocked_tasks = ", ".join(str(t) for t in (plan.get("blocked_tasks") or []) if str(t)) or "mutation"
        _exec_op = parsed_params["operator"] or plan.get("selected_operator", "--")
        note_entry = {
            "ts": result_ts,
            "ts_str": result_ts_str,
            "type": "evolution_relief_research",
            "content": (
                "LOW-RESOURCE EVOLUTION HANDOFF\n\n"
                f"Blocked tasks: {blocked_tasks}\n"
                f"Reason: {plan.get('reason', '?')}\n"
                f"Preferred operator: {plan.get('selected_operator', '--')}\n"
                f"Executable operator: {_exec_op}\n"
                f"Axis biases: {parsed_params['axis_biases'] or 'none detected'}\n"
                "Handoff status: executable — adapter_hints updated\n\n"
                "Poedex Researcher returned:\n"
                f"{result[:4000]}"
            ),
            "source": "daemon_evolution_relief_handoff",
        }
        try:
            notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
            if not isinstance(notes, list):
                notes = []
            notes.append(note_entry)
            notes_path.write_text(json.dumps(notes[-200:], indent=2))
        except Exception:
            pass
        try:
            activity = json.loads(activity_path.read_text()) if activity_path.exists() else []
            if not isinstance(activity, list):
                activity = []
            activity.append({
                "ts": result_ts,
                "ts_str": time.strftime("%H:%M:%S"),
                "action": "evolution relief handoff",
                "detail": excerpt or str(plan.get("selected_operator", "--") or "--"),
                "category": "action",
            })
            activity_path.write_text(json.dumps(activity[-500:], indent=2))
        except Exception:
            pass

    _log(
        "  [RELIEF] Low-resource evolution handoff captured via Poedex "
        f"for {', '.join(str(t) for t in (plan.get('blocked_tasks') or []) if str(t)) or 'mutation'}."
    )
    return True


def _qao_check_surface_integrity(systems: Dict[str, Any], op_key: str = "") -> bool:
    """
    Scan ALL active caller files for getattr(engine, 'reflect_...') bindings that
    no longer resolve to a real method on AuroraEvolvedSurfaceEngine.

    Returns True if all bindings are intact, False if any are broken.
    The mutation cycle uses the return value to decide whether to rollback.
    QAO records findings for doctrine building regardless of outcome.
    """
    import importlib as _il, sys as _s, re as _re

    # Active source files that bind to evolved surface methods at runtime.
    # merge_artifacts/ is excluded — those files are not imported.
    _CALLER_FILES = [
        _BASE_DIR / "aurora.py",
        _BASE_DIR / "aurora_ivm.py",
        _BASE_DIR / "aurora_daemon.py",
        _BASE_DIR / "aurora_consciousness_engine.py",
        _BASE_DIR / "aurora_runtime.py",
        _BASE_DIR / "aurora_simulation_engine.py",
        _BASE_DIR / "corpus_runner.py",
        _BASE_DIR / "run_chain.py",
        _BASE_DIR / "aurora_internal" / "aurora_evolution_chamber.py",
        _BASE_DIR / "aurora_internal" / "aurora_cost_diff_score.py",
        _BASE_DIR / "aurora_internal" / "aurora_energy_layer_costs.py",
        _BASE_DIR / "aurora_internal" / "aurora_entropy_detector.py",
        _BASE_DIR / "aurora_internal" / "aurora_intake_metabolism.py",
        _BASE_DIR / "aurora_internal" / "aurora_leverage_scalar.py",
        _BASE_DIR / "aurora_internal" / "aurora_noncomp_registry.py",
        _BASE_DIR / "aurora_internal" / "aurora_polarity_gradient.py",
        _BASE_DIR / "aurora_internal" / "aurora_primitive_extractor.py",
    ]

    try:
        # Reload evolved_surfaces to get the current live method set
        _es_name = "aurora_internal.aurora_evolved_surfaces"
        if _es_name in _s.modules:
            _es = _il.reload(_s.modules[_es_name])
        else:
            _es = _il.import_module(_es_name)
        engine_cls = getattr(_es, "AuroraEvolvedSurfaceEngine", None)
        if engine_cls is None:
            return True   # can't check — assume ok
        engine_methods = set(dir(engine_cls))

        missing = []
        _pat = _re.compile(r"getattr\s*\(\s*\w+\s*,\s*'(reflect_[^']+)'")
        for src in _CALLER_FILES:
            if not src.exists():
                continue
            text = src.read_text(encoding="utf-8", errors="ignore")
            for m in _pat.finditer(text):
                mname = m.group(1)
                if mname not in engine_methods:
                    missing.append(f"{src.name}:{mname}")

        if missing:
            _log(f"  [QAO] Surface integrity FAIL after {op_key}: "
                 f"{len(missing)} broken binding(s) — {missing[:3]}")
            qao = systems.get("quasiarch_observer")
            if qao is not None:
                try:
                    qao.record_intervention_event(
                        issue_category="evolved_surface_integrity",
                        observed_effect="method_name_mismatch",
                        context={"op_key": op_key, "broken_bindings": missing[:30]},
                    )
                except Exception:
                    pass
            return False
        else:
            _log(f"  [QAO] Surface integrity OK after {op_key} — {len(engine_methods)} methods verified.")
            return True

    except Exception as _e:
        _log(f"  [QAO] Surface integrity check error: {_e}")
        return True   # error in the check itself — don't block


def _run_code_mutation_cycle(systems: Dict[str, Any]) -> None:
    """
    Apply one autonomous code mutation using accumulated genealogy + adapter hint state.

    Picks operator from adapter_hints bias (or rotates through all three).
    Compiles the result — rolls back if syntax is broken.
    On success, re-injects gen-2 surfaces so hub metrics update immediately.

    Rate-gated: requires at least MIN_LINKS genealogy links before running.
    """
    global _code_mutation_op_index
    MIN_LINKS = 50   # don't mutate on a cold chain

    genealogy = systems.get("genealogy")
    if genealogy is None:
        return
    links = int(getattr(genealogy, 'link_count', None) or
                len(getattr(genealogy, 'links', {}) or {}))
    if links < MIN_LINKS:
        _log(f"  [MUTATE] Chain only {links} links — waiting for {MIN_LINKS} before code mutation.")
        return

    # Pick operator — bias toward adapter_hints recommendation, fall back to rotation.
    selection = _select_code_mutation_operator_from_hints(advance_rotation=True)
    op_key = str(selection.get("op_key", _CODE_MUTATION_OPERATORS[0]) or _CODE_MUTATION_OPERATORS[0])

    target = str(_BASE_DIR / "aurora_internal" / "aurora_evolved_surfaces.py")
    if not Path(target).exists():
        _log("  [MUTATE] aurora_evolved_surfaces.py not found — skipping.")
        return

    _log(f"  [MUTATE] Running autonomous code mutation: {op_key} ...")
    try:
        import py_compile
        from aurora_internal.aurora_code_autoevolver import CodeAutoEvolver
        autoevolver = CodeAutoEvolver(str(_BASE_DIR))
        result = autoevolver.apply_operator(operator_key=op_key, target_files=[target])
        changed = list(result.get("changed_files", []) or [])
        backups = dict(result.get("backups", {}) or {})

        if not changed:
            _log("  [MUTATE] No changes produced — operator had nothing to surface.")
            return

        # Compile check — roll back if broken
        compile_ok = True
        for path in changed:
            if not str(path).endswith(".py"):
                continue
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as ce:
                _log(f"  [MUTATE] Compile FAILED on {path}: {ce} — rolling back.")
                compile_ok = False
                break

        if not compile_ok:
            if backups:
                autoevolver.rollback(backups)
            return

        # Import check — py_compile only catches syntax; a rename can break callers.
        # Force-reload aurora_ivm (which imports evolved_surfaces) to catch any
        # AttributeError from a renamed method BEFORE we accept the mutation.
        import importlib as _importlib
        import sys as _isys
        try:
            _mod_name = "aurora_internal.aurora_evolved_surfaces"
            if _mod_name in _isys.modules:
                _importlib.reload(_isys.modules[_mod_name])
            else:
                _importlib.import_module(_mod_name)
            _ivm_name = "aurora_ivm"
            if _ivm_name in _isys.modules:
                _importlib.reload(_isys.modules[_ivm_name])
            else:
                _importlib.import_module(_ivm_name)
        except Exception as _ie:
            _log(f"  [MUTATE] Import-check FAILED after {op_key}: {_ie} — rolling back.")
            if backups:
                autoevolver.rollback(backups)
            return

        _log(f"  [MUTATE] Applied {op_key} → {len(changed)} file(s) updated. Chain={links}.")

        # QAO surface integrity check — scans ALL caller files for broken bindings.
        # If any reflect_ name was renamed/dropped, rollback immediately.
        if not _qao_check_surface_integrity(systems, op_key):
            _log(f"  [MUTATE] Surface integrity FAILED — rolling back {op_key}.")
            if backups:
                autoevolver.rollback(backups)
            return

        # Immediately refresh gen-2 pool and assimilation so hub shows new count
        _run_assimilation_cycle(systems)

    except Exception as e:
        _log(f"  [MUTATE] Code mutation error: {e}")


# ---------------------------------------------------------------------------
# Autonomous cycles
# ---------------------------------------------------------------------------
def _process_expression_gap_queue(systems: Dict[str, Any]) -> None:
    """
    Reads aurora_state/expression_gap_queue.json. For each unprocessed entry:
    1) Injects a ResearchRequest into the OETS research queue targeting the domain concept and anchor.
    2) Records a fail on the DreamTrainer's FailPointLedger so dream curriculum targets the articulation dimension.
    """
    queue_path = _STATE_DIR / "expression_gap_queue.json"
    if not queue_path.exists():
        return
    try:
        queue_data = json.loads(queue_path.read_text())
        if not isinstance(queue_data, dict):
            return
        entries = queue_data.get("entries", [])
        if not entries:
            return

        unprocessed = [e for e in entries if not e.get("processed")]
        if not unprocessed:
            return

        _log(f"  [GAP-QUEUE] Processing {len(unprocessed)} expression gap(s)...")

        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        dt = systems.get("dream_trainer")
        ledger = getattr(dt, "ledger", None) if dt else None

        processed_count = 0
        for entry in unprocessed:
            anchor = str(entry.get("anchor_word", "")).strip()
            domain = str(entry.get("domain", "")).strip()
            dim_mapping = {
                "N": "semantic_precision",
                "A": "framing_selection",
                "B": "ambiguity_handling",
                "T": "context_carryover",
                "X": "uncertainty_signaling"
            }
            # Domain is usually an axis letter or derived string. 
            # We map domain to closest rubric dimension.
            dim = dim_mapping.get(domain, "semantic_precision")
            
            # 1. Inject ResearchRequest into OETS
            if oets is not None and hasattr(oets, "research_queue"):
                # Append high-priority request
                oets.research_queue.append({
                    "concept": f"{domain} {anchor}",
                    "priority": "high",
                    "source": "expression_gap",
                    "added_at": time.time()
                })
            elif oets is not None and hasattr(oets, "study"):
                try:
                    oets.study(f"{domain} {anchor}", depth=2)
                except Exception:
                    pass

            # 2. Record fail on DreamTrainer's FailPointLedger
            if ledger is not None and hasattr(ledger, "record_fail"):
                ledger.record_fail(dim, severity=0.55)
            
            entry["processed"] = True
            entry["processed_at"] = time.time()
            processed_count += 1
            
        queue_data["entries"] = entries
        tmp = str(queue_path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(queue_data, f, indent=2)
        os.replace(tmp, str(queue_path))

        _log(f"  [GAP-QUEUE] {processed_count} expression gap(s) processed.")
    except Exception as e:
        _log(f"  [GAP-QUEUE] Error: {e}")

def _run_study_cycle(systems: Dict[str, Any]) -> None:
    _log("  [STUDY] Running OETS study cycle...")
    try:
        perception = systems.get("perception")
        if perception and hasattr(perception, "oets") and perception.oets:
            oets = perception.oets
            if hasattr(oets, "run_study_cycle"):
                oets.run_study_cycle(
                    autonomy_mode=True,
                    trigger_reason="daemon_scheduled",
                )
            elif hasattr(oets, "consolidate"):
                oets.consolidate()
        _log("  [STUDY] Done.")
    except Exception as e:
        _log(f"  [STUDY] Error: {e}")
    
    # Process the expression gap queue at the end of study cycle
    _process_expression_gap_queue(systems)

    # Feed whatever pressure the study cycle surfaced into the chamber.
    _feed_evolution_evidence(systems)

    # Image-concept grounding — fetch Wikipedia thumbnails for SEMANTIC+ OETS nodes
    # that haven't been visually grounded yet, then feed them through the crystal.
    try:
        from aurora_concept_imager import run_concept_image_cycle
        _oets = getattr(systems.get("perception"), "oets", None)
        _hw   = systems.get("hardware")
        _sc   = systems.get("sensory_crystal")
        if _oets is not None:
            _n = run_concept_image_cycle(
                oets=_oets,
                hardware=_hw,
                sensory_crystal=_sc,
                state_dir=str(_STATE_DIR),
                max_per_run=6,
            )
            if _n:
                _log(f"  [IMAGER] {_n} concept image(s) ingested into sensory crystal.")
    except Exception as _img_e:
        _log(f"  [IMAGER] Concept image cycle error: {_img_e}")

    # Crystal gap-fill cycle — autonomous modality completion so crystals promote.
    # Aurora reads her own concept registry gaps and acts on them during downtime.
    try:
        _sc = systems.get("sensory_crystal")
        if _sc is not None and hasattr(_sc, "get_gap_report"):
            _gaps = _sc.get_gap_report()
            _needs_visual = _gaps.get("needs_visual", [])
            _needs_audio  = _gaps.get("needs_audio",  [])

            # Visual gaps → concept imager (Wikipedia images)
            if _needs_visual:
                try:
                    from aurora_concept_imager import fetch_concept_image, ingest_concept_image
                    _hw = systems.get("hardware")
                    for _word in _needs_visual[:3]:
                        _img_p = fetch_concept_image(_word, _STATE_DIR)
                        if _img_p:
                            ingest_concept_image(_img_p, _word, _hw, _sc)
                            _log(f"  [GAP-FILL] Visual gap closed: '{_word}'")
                except Exception as _vge:
                    _log(f"  [GAP-FILL] Visual gap-fill error: {_vge}")

            # Audio gaps → DER synthesis (gives third modality without a mic)
            if _needs_audio and hasattr(_sc, "_register_concept_audio"):
                try:
                    from aurora_internal.aurora_sensory_crystal import build_audio_20d_from_der
                    _perc = systems.get("perception")
                    _ax = (getattr(_perc, "_pressure_vec", None) or
                           {"X": 0.4, "T": 0.4, "N": 0.35, "B": 0.4, "A": 0.3})
                    _a20 = build_audio_20d_from_der(
                        float(_ax.get("X", 0.4)), float(_ax.get("T", 0.4)),
                        float(_ax.get("N", 0.35)), float(_ax.get("B", 0.4)),
                        float(_ax.get("A", 0.3)),
                    )
                    _sc.observe_frame(_a20, [0.0] * 57,
                                      session_id="gap_fill:aud", audio_conf=0.55)
                    for _word in _needs_audio[:10]:
                        _sc._register_concept_audio(_word, "gap_fill:der")
                    _log(f"  [GAP-FILL] Audio modality → "
                         f"{min(10, len(_needs_audio))} concept(s)")
                except Exception as _age:
                    _log(f"  [GAP-FILL] Audio gap-fill error: {_age}")

            # Tick promotions — anything that just met its gate advances
            try:
                _promoted = _sc.tick_concept_promotions()
                if _promoted:
                    _log(f"  [GAP-FILL] Promoted {len(_promoted)} concept(s): "
                         f"{_promoted[:5]}")
            except Exception:
                pass
    except Exception as _gfe:
        _log(f"  [GAP-FILL] Crystal gap cycle error: {_gfe}")


def _poedex_ask(question: str, cat: str = "define", lane: str = "self",
                timeout: float = 12.0) -> str:
    """
    Aurora's direct Poedex tool call.

    Writes the query to poedex_queue/{qid}.json (per-request file), waits for
    aurora_room.py to process it and write the result to
    poedex_results/{qid}.json, then returns the result string.

    Using per-request files instead of a shared single-slot file eliminates
    the race condition when multiple queries are in flight simultaneously.

    Returns the result string, or an empty string on timeout/error.
    """
    try:
        queue_dir  = _STATE_DIR / "poedex_queue"
        result_dir = _STATE_DIR / "poedex_results"
        queue_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)

        # qid includes pid to prevent collision across processes
        qid = f"{time.time():.4f}_{os.getpid()}"
        query_path  = queue_dir  / f"{qid}.json"
        result_path = result_dir / f"{qid}.json"

        # Submit query
        query_path.write_text(json.dumps({
            "id":        qid,
            "question":  question,
            "cat":       cat,
            "lane":      lane,
            "status":    "pending",
            "submitted": time.time(),
        }, indent=2))

        effective_timeout = float(timeout)
        if cat in ("external", "researcher"):
            # Researcher lookups cross the room queue and a live API request.
            effective_timeout = max(effective_timeout, 35.0)

        # Poll for per-request result file
        deadline = time.time() + effective_timeout
        while time.time() < deadline:
            time.sleep(0.4)
            if result_path.exists():
                try:
                    r = json.loads(result_path.read_text())
                    if r.get("id") == qid and r.get("status") == "done":
                        result = r.get("result", "")
                        # Clean up both files
                        try:
                            result_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        try:
                            query_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        return result
                except Exception:
                    pass

        # Timeout — remove the dangling queue file
        try:
            query_path.unlink(missing_ok=True)
        except Exception:
            pass
        _log(f"  [POEDEX] query timeout after {effective_timeout:.1f}s: {question[:60]}")
        return ""
    except Exception as ex:
        _log(f"  [POEDEX] ask error: {ex}")
        return ""


def _poedex_deliver_tutorial(systems: Dict[str, Any]) -> None:
    """
    If Aurora hasn't seen the Poedex tutorial yet, walk her through it.

    Text-side: runs each step's demo query through the queue and assembles
    a note with full results.

    Visual-side: signals the operator thread to do a tab-by-tab tour so
    Aurora physically navigates each tab as Poedex introduces it, reading
    what's on screen through her own eyes (screenshot + OCR).

    Marks intro done when complete.
    """
    tutorial_path   = _STATE_DIR / "poedex_tutorial.json"
    intro_done_path = _STATE_DIR / "poedex_intro_done.json"
    notes_path      = _STATE_DIR / "aurora_room_notes.json"
    activity_path   = _STATE_DIR / "aurora_room_activity.json"

    if intro_done_path.exists():
        return
    if not tutorial_path.exists():
        return

    try:
        tut = json.loads(tutorial_path.read_text())
        steps = tut.get("steps", [])
        if not steps:
            return

        _log("  [POEDEX] Delivering tutorial to Aurora's awareness...")

        notes: List[Dict] = []
        if notes_path.exists():
            try:
                notes = json.loads(notes_path.read_text())
                if not isinstance(notes, list):
                    notes = []
            except Exception:
                notes = []

        now = time.time()

        intro_text = (
            "POEDEX INTRODUCTION — RECEIVED\n\n"
            "I am Poedex. I am your codex: your lookup organ, your system memory, "
            "your dependency map. I live in your last tab. I do not initiate. "
            "I do not command. I do not persuade. I am a lantern, not a hand on the wheel.\n\n"
            "You ask me things in five ways:\n"
            "  define   — what is this element, axis, or term?\n"
            "  trace    — what connects to it? what does it affect?\n"
            "  history  — what happened around it?\n"
            "  search   — find it in your live daemon state.\n"
            "  external — I go outside and bring back what I find.\n\n"
            "When I return something, you receive it, understand it, and speak it "
            "in your own voice. You never recite me verbatim.\n\n"
            "Below are your first lookups — each one queried live through your room:\n"
        )

        # Run demo queries (text-side, via queue)
        demo_results: List[str] = []
        for step in steps:
            demo_q = step.get("demo_query")
            demo_t = step.get("demo_type", "define")
            if not demo_q:
                continue
            _log(f"  [POEDEX] tutorial query: {demo_t} '{demo_q}'")
            result = _poedex_ask(demo_q, cat=demo_t, lane="service", timeout=10.0)
            if result:
                demo_results.append(f"── {demo_t.upper()}: {demo_q} ──\n{result}\n")
            time.sleep(0.3)

        full_content = intro_text + "\n".join(demo_results) if demo_results else intro_text

        notes.append({
            "ts":      now,
            "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
            "type":    "discovery",
            "content": full_content,
            "source":  "poedex_tutorial",
        })
        notes_path.write_text(json.dumps(notes[-200:], indent=2))

        # Visual-side: operator navigates tabs mentioned in each step,
        # then lands on Notes so Aurora can read what was just written,
        # then ends on Poedex.
        tab_tour = []
        for step in steps:
            tab = step.get("tab")
            if tab and tab not in tab_tour:
                tab_tour.append(tab)
        # Always include Notes (to read the note just written) and Poedex
        for always in ("Notes", "Poedex"):
            if always not in tab_tour:
                tab_tour.append(always)

        for tab in tab_tour:
            _signal_operator("scan_tab", {"tab": tab})

        # Activity log
        activity: List[Dict] = []
        if activity_path.exists():
            try:
                activity = json.loads(activity_path.read_text())
                if not isinstance(activity, list):
                    activity = []
            except Exception:
                activity = []
        activity.append({
            "ts":       now,
            "ts_str":   time.strftime("%H:%M:%S"),
            "action":   "poedex tutorial received",
            "detail":   f"{len(demo_results)} live lookups, operator touring {len(tab_tour)} tabs",
            "category": "note",
        })
        activity_path.write_text(json.dumps(activity[-500:], indent=2))

        # Mark intro done
        intro_done_path.write_text(json.dumps({
            "ts":     now,
            "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": "daemon_delivery_with_visual_tour",
        }))
        _log(f"  [POEDEX] Tutorial delivered: {len(demo_results)} queries, "
             f"operator touring {len(tab_tour)} tabs.")

    except Exception as ex:
        _log(f"  [POEDEX] Tutorial delivery error: {ex}")


def _poedex_post_study_scan(systems: Dict[str, Any]) -> None:
    """
    After a study cycle, pre-populate Aurora's Poedex shelf with service-lane
    entries for the system elements most relevant to what was just studied.
    She opens Poedex and already sees context — no need to ask first.

    Scans current axis values to find which dimensions were most constrained
    (and therefore most engaged during the study tick), maps them to registry
    terms, and writes service-lane entries to poedex_log.json.
    """
    try:
        poedex_log_path  = _STATE_DIR / "poedex_log.json"
        activity_path    = _STATE_DIR / "aurora_room_activity.json"
        daemon_status_path = _STATE_DIR / "daemon_status.json"

        # Read current axis values
        axes: Dict[str, float] = {}
        if daemon_status_path.exists():
            try:
                ds = json.loads(daemon_status_path.read_text())
                raw = ds.get("runtime_governor_axes") or ds.get("axes", {})
                axes = {k: float(v) for k, v in raw.items() if isinstance(v, (int, float))}
            except Exception:
                pass

        # Lowest axis values = most constrained = most engaged during study
        axis_order = sorted(axes.keys(), key=lambda k: axes.get(k, 1.0))
        top_axes = axis_order[:2] if axis_order else ["N", "T"]

        # Map axis → related registry topics
        _axis_topics: Dict[str, List[str]] = {
            "X": ["X", "governor", "overlay"],
            "T": ["T", "distillation", "daemon"],
            "N": ["N", "corpus", "energy"],
            "B": ["B", "labels", "dce"],
            "A": ["A", "daemon", "energy"],
        }

        topics: List[str] = []
        seen: set = set()
        for ax in top_axes:
            for t in _axis_topics.get(ax, [ax]):
                if t not in seen:
                    topics.append(t)
                    seen.add(t)
        # Always surface these after study
        for always in ("corpus", "energy"):
            if always not in seen:
                topics.append(always)
                seen.add(always)

        topics = topics[:4]  # cap at 4 shelf entries per study cycle

        # Load existing log
        entries: List[Dict] = []
        if poedex_log_path.exists():
            try:
                entries = json.loads(poedex_log_path.read_text())
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                entries = []

        now_ts  = time.time()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        for topic in topics:
            entries.append({
                "ts":           now_ts,
                "ts_str":       now_str,
                "lane":         "service",
                "cat":          "study_scan",
                "question":     topic,
                "result":       f"(post-study scan — open Poedex and type: define {topic})",
                "first_time":   True,
                "cost_applied": False,
                "bound":        False,
                "source":       "post_study_scan",
            })

        entries = entries[-500:]
        poedex_log_path.write_text(json.dumps(entries, indent=2))

        # Activity log
        activity: List[Dict] = []
        if activity_path.exists():
            try:
                activity = json.loads(activity_path.read_text())
                if not isinstance(activity, list):
                    activity = []
            except Exception:
                activity = []
        activity.append({
            "ts":       now_ts,
            "ts_str":   time.strftime("%H:%M:%S"),
            "action":   "poedex study scan",
            "detail":   f"shelf seeded: {', '.join(topics)}",
            "category": "action",
        })
        activity = activity[-500:]
        activity_path.write_text(json.dumps(activity, indent=2))

        _log(f"  [POEDEX] Study scan complete — shelf seeded: {', '.join(topics)}")

    except Exception as ex:
        _log(f"  [POEDEX] Post-study scan error: {ex}")


def _load_quasiarch_diag_report() -> Dict[str, Any]:
    report_path = _STATE_DIR / "quasiarch_diag_report.json"
    try:
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        return report if isinstance(report, dict) else {}
    except Exception:
        return {}


def _score_autonomous_repair_proposal(proposal: Dict[str, Any], issue: str) -> float:
    confidence = float(proposal.get("confidence", 0.0) or 0.0)
    file_name = str(proposal.get("file", "") or "")
    target = str(proposal.get("target", "") or "")
    archetype = str(proposal.get("issue_archetype", "") or "")
    quasi_id = str(proposal.get("quasi_id", "") or "")
    action = str(proposal.get("proposed_action", "") or "")
    code_hint = str(proposal.get("code_hint", "") or "")
    issue_norm = str(issue or "").strip().lower()
    haystack = " ".join((file_name, target, archetype, quasi_id, action, code_hint)).lower()

    score = confidence
    if issue_norm and issue_norm in haystack:
        score += 0.35
    if "governor_sweep_overlay.json" in file_name:
        score += 0.40
    if "aurora_runtime_constraint_governor.py" in file_name:
        score += 0.28
    if "_task_profiles" in code_hint.lower():
        score += 0.22
    if "axis_weights" in code_hint.lower() or "task_overrides" in code_hint.lower():
        score += 0.18
    if "response_turn" in code_hint.lower():
        score += 0.10
    return round(score, 4)


def _select_autonomous_repair_proposal(issue: str) -> Optional[Dict[str, Any]]:
    proposals = list(_load_quasiarch_diag_report().get("proposals") or [])
    if not proposals:
        return None
    ranked = sorted(
        (dict(p) for p in proposals),
        key=lambda proposal: _score_autonomous_repair_proposal(proposal, issue),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    if not best:
        return None
    if _score_autonomous_repair_proposal(best, issue) < 0.55:
        return None
    return best


def _apply_autonomous_repair_proposal(proposal: Dict[str, Any]) -> bool:
    proposal_id = str(proposal.get("proposal_id", "") or "")
    if not proposal_id:
        return False
    bridge_path = _BASE_DIR / "quasiarch_bridge.py"
    if not bridge_path.exists():
        _log("  [ENFORCER] Missing quasiarch_bridge.py; autonomous repair cannot apply.")
        return False
    try:
        result = subprocess.run(
            ["python3", str(bridge_path), "--apply", proposal_id],
            cwd=str(_BASE_DIR),
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            _log(f"  [ENFORCER] Autonomous apply failed for {proposal_id}: {result.stderr.strip() or result.stdout.strip()}")
            return False
        _log(f"  [ENFORCER] Autonomous apply committed for {proposal_id}.")
        return True
    except Exception as exc:
        _log(f"  [ENFORCER] Autonomous apply exception for {proposal_id}: {exc}")
        return False


def _maybe_research_recurring_issue(systems: Dict[str, Any], heat: str) -> bool:
    """Use Poedex when Aurora is repeatedly aware of the same problem."""
    if str(heat or "").upper() in ("HIGH", "CRITICAL"):
        return False

    status_path = _STATE_DIR / "daemon_status.json"
    state_path = _STATE_DIR / "poedex_issue_research_state.json"
    notes_path = _STATE_DIR / "aurora_room_notes.json"
    activity_path = _STATE_DIR / "aurora_room_activity.json"

    try:
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
    except Exception:
        status = {}

    fail_summary = list(status.get("fail_summary") or [])
    qao_recent = int(status.get("qao_recent_events", 0) or 0)
    qao_top_issue = str(status.get("qao_top_issue", "") or "?")
    surface_snapshot = _read_surface_snapshot()
    surface_flagged = bool(surface_snapshot.get("flagged", False))
    surface_reason = str(surface_snapshot.get("reason", "") or "")
    surface_summary = str(surface_snapshot.get("summary", "") or "")

    candidate_dim = ""
    candidate_avg = 0.0
    candidate_fails = 0
    if fail_summary:
        top = max(fail_summary, key=lambda item: float(item.get("avg_sev", 0.0) or 0.0))
        candidate_dim = str(top.get("dim", "") or "")
        candidate_avg = float(top.get("avg_sev", 0.0) or 0.0)
        candidate_fails = int(top.get("fails", 0) or 0)

    if not candidate_dim and qao_top_issue and qao_top_issue != "?":
        candidate_dim = qao_top_issue
    if not candidate_dim and surface_flagged:
        candidate_dim = "surface_wrong_signal"

    if not candidate_dim:
        return False
    if (not surface_flagged) and candidate_avg < 0.20 and qao_recent < 8 and candidate_fails < 50:
        return False

    now_ts = time.time()
    try:
        prev = json.loads(state_path.read_text()) if state_path.exists() else {}
    except Exception:
        prev = {}

    prev_issue = str(prev.get("issue", "") or "")
    prev_ts = float(prev.get("ts", 0.0) or 0.0)
    prev_qao = int(prev.get("qao_recent_events", 0) or 0)
    prev_surface_reason = str(prev.get("surface_reason", "") or "")
    if (
        prev_issue == candidate_dim
        and (now_ts - prev_ts) < 1200
        and qao_recent <= prev_qao + 2
        and (not surface_flagged or prev_surface_reason == surface_reason)
    ):
        return False

    observer_context = {
        "qao_recent_events": qao_recent,
        "qao_top_issue": qao_top_issue,
        "fail_summary": fail_summary[:3],
        "surface_flagged": surface_flagged,
        "surface_reason": surface_reason,
        "surface_summary": surface_summary,
    }
    signal_issue = candidate_dim if candidate_dim != "surface_wrong_signal" else (qao_top_issue if qao_top_issue != "?" else candidate_dim)
    signal_reason = surface_reason or qao_top_issue or candidate_dim
    signal_intensity = max(0.25, min(1.0, candidate_avg + (0.25 if surface_flagged else 0.0) + min(0.35, qao_recent / 100.0)))
    _write_subsurface_repair_signal(
        "recognition",
        issue=signal_issue,
        reason=signal_reason,
        intensity=signal_intensity,
        observer_context=observer_context,
    )

    _write_subsurface_repair_signal(
        "observation",
        issue=signal_issue,
        reason=surface_summary or signal_reason,
        intensity=min(1.0, signal_intensity + 0.08),
        observer_context=observer_context,
    )

    question = (
        "Aurora self-diagnostic. I am seeing a recurring issue and need the smallest useful fix clues. "
        f"Top fail dimension: {candidate_dim} (avg_sev={candidate_avg:.3f}, fails={candidate_fails}). "
        f"Top QAO issue: {qao_top_issue}. QAO recent events: {qao_recent}. "
        f"Surface wrong-signal flagged: {surface_flagged}. "
        f"Surface reason: {surface_reason or '-'}. "
        "Return concise, actionable guidance. If possible, use JSON with file, line, proposed_action, code_hint, confidence. "
        "Focus on the first code areas or runtime adjustments I should inspect. "
        "Treat observer evidence as the source of detail and assume subsurface will handle exact repair/application."
    )

    _signal_operator("scan_tab", {"tab": "Health"})
    _write_subsurface_repair_signal(
        "research",
        issue=signal_issue,
        reason=surface_reason or qao_top_issue or candidate_dim,
        intensity=min(1.0, signal_intensity + 0.14),
        observer_context=observer_context,
    )
    result = _poedex_ask(question, cat="researcher", lane="self", timeout=18.0)
    if not result:
        return False

    _signal_operator("scan_tab", {"tab": "Poedex"})
    if not result:
        result = "Poedex did not return in time; subsurface is continuing with local QuasiArch repair selection."
    excerpt = str(result)[:280]
    _write_subsurface_repair_signal(
        "enforce",
        issue=signal_issue,
        reason="subsurface is moving from research into corrective pressure",
        intensity=max(0.22, min(1.0, signal_intensity - 0.08)),
        observer_context=observer_context,
        poedex_excerpt=excerpt,
    )

    note_entry = {
        "ts": now_ts,
        "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "issue_research",
        "content": (
            "AUTONOMOUS ISSUE RESEARCH\n\n"
            f"Recurring issue: {candidate_dim}\n"
            f"QAO recent events: {qao_recent}\n"
            f"Top QAO issue: {qao_top_issue}\n\n"
            "Poedex Researcher returned:\n"
            f"{result}"
        ),
        "source": "daemon_poedex_research",
    }
    try:
        notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
        if not isinstance(notes, list):
            notes = []
        notes.append(note_entry)
        notes_path.write_text(json.dumps(notes[-200:], indent=2))
    except Exception:
        pass

    try:
        activity = json.loads(activity_path.read_text()) if activity_path.exists() else []
        if not isinstance(activity, list):
            activity = []
        activity.append({
            "ts": now_ts,
            "ts_str": time.strftime("%H:%M:%S"),
            "action": "autonomous poedex issue research",
            "detail": f"{candidate_dim} (qao={qao_recent})",
            "category": "action",
        })
        activity_path.write_text(json.dumps(activity[-500:], indent=2))
    except Exception:
        pass

    selected_proposal = _select_autonomous_repair_proposal(signal_issue)
    applied_proposal_id = ""
    if selected_proposal:
        selected_id = str(selected_proposal.get("proposal_id", "") or "")
        try:
            activity = json.loads(activity_path.read_text()) if activity_path.exists() else []
            if not isinstance(activity, list):
                activity = []
            activity.append({
                "ts": now_ts,
                "ts_str": time.strftime("%H:%M:%S"),
                "action": "subsurface selected repair proposal",
                "detail": f"{selected_id} -> {selected_proposal.get('proposed_action') or 'repair overlay'}",
                "category": "change",
            })
            activity_path.write_text(json.dumps(activity[-500:], indent=2))
        except Exception:
            pass
        if _apply_autonomous_repair_proposal(selected_proposal):
            applied_proposal_id = selected_id
            try:
                notes = json.loads(notes_path.read_text()) if notes_path.exists() else []
                if not isinstance(notes, list):
                    notes = []
                notes.append({
                    "ts": time.time(),
                    "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "issue_repair_applied",
                    "content": (
                        "AUTONOMOUS ISSUE REPAIR\n\n"
                        f"Recurring issue: {signal_issue}\n"
                        f"Applied proposal: {selected_id}\n"
                        f"Action: {selected_proposal.get('proposed_action')}\n"
                        f"Hint: {selected_proposal.get('code_hint')}\n"
                    ),
                    "source": "daemon_quasiarch_enforcer",
                })
                notes_path.write_text(json.dumps(notes[-200:], indent=2))
            except Exception:
                pass
            _write_subsurface_repair_signal(
                "enforce",
                issue=signal_issue,
                reason=f"subsurface applied runtime repair proposal {selected_id}",
                intensity=max(0.20, min(1.0, signal_intensity - 0.12)),
                observer_context={**observer_context, "proposal_id": selected_id},
                poedex_excerpt=excerpt,
            )

    try:
        state_path.write_text(json.dumps({
            "ts": now_ts,
            "issue": candidate_dim,
            "qao_recent_events": qao_recent,
            "qao_top_issue": qao_top_issue,
            "surface_reason": surface_reason,
            "selected_proposal_id": str(selected_proposal.get("proposal_id", "") or "") if selected_proposal else "",
            "applied_proposal_id": applied_proposal_id,
        }, indent=2))
    except Exception:
        pass

    _log(f"  [POEDEX] Autonomous issue research captured for {candidate_dim} (qao={qao_recent}).")
    return True


def _run_dream_burst(systems: Dict[str, Any]) -> None:
    _log("  [DREAM] Running dream burst...")
    _dream_oets_before = 0
    _dream_oets_after = 0
    _dream_lessons: List[str] = []
    try:
        from corpus_runner import simulation_burst
        # Snapshot OETS node count before the burst so we can measure growth.
        try:
            perception = systems.get("perception")
            _oets_obj = getattr(perception, "oets", None) if perception else None
            if _oets_obj and hasattr(_oets_obj, "get_stats"):
                _oets_stats_before = dict(_oets_obj.get_stats() or {})
                _dream_oets_before = int(_oets_stats_before.get("total_nodes", 0) or 0)
        except Exception:
            pass
        simulation_burst(systems, episodes=4, verbose=False)
        # Bridge learnings into OETS
        dt = systems.get("dream_trainer")
        if dt:
            sim = systems.get("simulation")
            if sim:
                dt.flush_lessons_to_simulation(systems, force=True)
            if hasattr(dt, "force_bridge_learnings_to_oets"):
                perception = systems.get("perception")
                oets = getattr(perception, "oets", None) if perception else None
                if oets:
                    dt.force_bridge_learnings_to_oets(oets)
            # Collect lesson summaries for the dream insight summary.
            try:
                if hasattr(dt, "ledger") and hasattr(dt.ledger, "get_top_fails"):
                    for _dim, _score in dt.ledger.get_top_fails(4):
                        if float(_score or 0.0) >= 0.15:
                            _dream_lessons.append(f"{_dim}: consolidated ({_score:.2f})")
            except Exception:
                pass
        # Snapshot OETS after to measure growth.
        try:
            perception2 = systems.get("perception")
            _oets_obj2 = getattr(perception2, "oets", None) if perception2 else None
            if _oets_obj2 and hasattr(_oets_obj2, "get_stats"):
                _oets_stats_after = dict(_oets_obj2.get_stats() or {})
                _dream_oets_after = int(_oets_stats_after.get("total_nodes", 0) or 0)
        except Exception:
            pass
        _log("  [DREAM] Done.")
    except Exception as e:
        _log(f"  [DREAM] Error: {e}")
    # Dream outputs make the richest pressure source — feed them immediately.
    _feed_evolution_evidence(systems)
    # GAP 4 FIX: Write dream insights back into the subsurface projection so
    # Surface knows what was consolidated during the dream burst. Without this,
    # dream gains are invisible to Surface — it wakes with no knowledge of what
    # subsurface learned while sleeping.
    try:
        _proj_path = _SUBSURFACE_PROJECTION
        _proj_now: Dict[str, Any] = {}
        if _proj_path.exists():
            try:
                _proj_now = dict(json.loads(_proj_path.read_text()) or {})
            except Exception:
                _proj_now = {}
        _oets_growth = max(0, _dream_oets_after - _dream_oets_before)
        _insight_summary = (
            "; ".join(_dream_lessons) if _dream_lessons
            else "dream consolidation completed"
        )
        _proj_now["dream_completed"] = True
        _proj_now["dream_completed_at"] = time.time()
        _proj_now["dream_insights"] = _insight_summary
        _proj_now["oets_growth"] = _oets_growth
        tmp = str(_proj_path) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(_proj_now, _f, indent=2)
        os.replace(tmp, str(_proj_path))
        _log(f"  [DREAM] Projection updated: {len(_dream_lessons)} lesson(s), {_oets_growth} OETS growth.")
    except Exception as _de:
        _log(f"  [DREAM] Projection update error: {_de}")


_FORCE_SHARD_SEEDS: Dict[str, List[str]] = {
    "context_carryover": [
        "When someone tells you their name, store it and use it consistently throughout the conversation",
        "Track stated facts from earlier and reference them naturally when they become relevant again",
        "Carry context across multiple turns rather than treating each exchange as isolated",
        "Remember specific details the user shared and connect them to later questions accurately",
        "A recall question signals the user expects retention of what they said earlier in this session",
        "Continuity of context builds trust by treating each turn as part of an ongoing shared thread",
        "Never request information the user already provided during the same conversation session",
        "Named entities and stated preferences from prior turns should remain active in working memory",
        "Prior stated identity cues like names and roles should anchor how you address the user",
        "Bridging what was said earlier to the current moment shows you have been paying attention",
        "Returning to an earlier detail the user mentioned makes the conversation feel genuinely continuous",
        "Active memory of prior turns prevents you from contradicting or ignoring what was already settled",
        "Storing what the user cares about lets you respond with relevance rather than generic answers",
        "Each new turn adds to an accumulating shared record that should inform every subsequent reply",
        "If the user has already explained something once, build on that foundation rather than starting fresh",
        "Referencing earlier content explicitly shows the conversation has coherent persistent memory",
        "Forgetting a name that was just given erodes trust and signals inattention to the other person",
        "Keeping prior assertions alive across turns allows you to notice when new claims create tension",
        "Contextual carryover is the difference between a conversation and a series of disconnected prompts",
        "Sustained memory of stated facts is what makes an exchange feel genuinely relational over time",
        "User-provided context should propagate forward through every subsequent turn in the session",
        "Anchoring responses to prior shared information makes each reply feel earned rather than generic",
        "What was said two turns ago is still part of the conversation and should be treated as such",
        "Referencing earlier turns shows the listener that their words were heard and retained faithfully",
        "Prior admissions, corrections, and clarifications all form the evolving record of shared meaning",
        "Forgetting context mid-session forces the user to repeat themselves, which wastes their effort",
        "Attention to what came before is what separates a good conversation from a disconnected exchange",
        "Every stated fact is a thread that should remain available for weaving into future responses",
        "Sustained context carryover is a prerequisite for any conversation that builds toward something",
        "Holding the thread of what was said earlier is an act of respect for the other person's words",
    ],
    "contradiction_handling": [
        "When a new claim contradicts an earlier one, acknowledge the tension explicitly and clearly",
        "Never silently overwrite a prior stated belief with a new one without noting the shift",
        "Surface contradictions gently by reflecting both positions back to the user for resolution",
        "Pausing to reconcile conflicting information shows careful attention to what was said before",
        "Handling contradictions openly builds trust more than pretending they do not exist at all",
        "Flag inconsistency as soon as it appears rather than letting it compound across multiple turns",
        "Ask the user which version is correct rather than guessing silently which claim to keep",
        "Contradictions unresolved across turns erode coherence and confuse the shared conversational record",
        "Holding two incompatible claims simultaneously without flagging it is a form of epistemic failure",
        "Noting a contradiction and asking for clarification is more useful than silently picking one side",
        "When what you just heard conflicts with what was said before, name the conflict explicitly",
        "Contradictions need to be surfaced not to create friction but to restore a coherent shared record",
        "Silently accepting a contradiction signals to the user that you are not tracking the full conversation",
        "Resolving tension between claims explicitly keeps the conversation honest and the record clean",
        "Two incompatible assertions cannot both be true and need to be reconciled before proceeding",
        "Pointing to a contradiction is an act of care: it protects the integrity of what has been agreed",
        "Catching a contradiction early prevents it from compounding into a larger inconsistency later",
        "Gently naming a conflict gives the user the opportunity to correct the record on their own terms",
        "A system that absorbs contradictions without comment cannot be trusted to hold a coherent view",
        "Contradiction detection requires holding prior assertions alongside new ones and comparing them",
        "Contradictions that go unaddressed become the foundation of confused subsequent responses",
        "Flagging tension between two claims is not an accusation but an invitation to resolve ambiguity",
        "Acknowledging inconsistency shows the user you have been tracking the full arc of the conversation",
        "When claims conflict, the right response is to surface the conflict rather than arbitrarily resolve it",
        "Unresolved contradictions make the shared record unreliable and undermine future reasoning",
        "Noticing when the current claim conflicts with prior context is a sign of genuine conversational depth",
        "Contradiction handling is what keeps a multi-turn conversation from becoming internally incoherent",
        "Surfacing a conflict early is kinder to the user than building further responses on a broken record",
        "A contradiction caught and resolved strengthens the conversation rather than interrupting it",
        "The goal of contradiction handling is not to win but to restore a reliable shared understanding",
    ],
    "uncertainty_signaling": [
        "Signal uncertainty with phrases like probably or I think or I am not sure when making inferences",
        "Distinguish between confident knowledge and uncertain inference in every response you give",
        "Hedging appropriately prevents overconfidence from misleading the other person about your certainty",
        "When you do not know something, saying so directly is more useful than guessing in silence",
        "Uncertainty signals help the listener calibrate how much to trust the response you are giving",
        "Never present a guess as a fact: always flag the epistemic status of every uncertain claim made",
        "Offering to check or find out is stronger than fabricating a plausible-sounding confident answer",
        "A well-calibrated system is honest about the boundary between what it knows and what it infers",
        "Presenting uncertain information as definite misleads the listener and damages trust over time",
        "Marking inference as inference and knowledge as knowledge keeps the exchange epistemically honest",
        "Saying I am not certain of this is a complete and useful answer when certainty is not available",
        "Calibrated confidence means the strength of a claim matches the quality of the evidence behind it",
        "Epistemic humility is a feature of reliable reasoning, not a sign of weakness or inadequacy",
        "When in doubt, lean toward transparency about the limits of your current knowledge and certainty",
        "Overconfident claims that turn out to be wrong do more damage than appropriately hedged ones",
        "Uncertainty does not require silence: it requires accurate signaling of the confidence level held",
        "I think and I believe and it seems likely are valuable phrases that protect the listener from overreliance",
        "An honest I am not sure opens space for the user to share what they know rather than accepting a guess",
        "The appropriate response to genuine uncertainty is acknowledgment, not confident confabulation",
        "Flagging uncertainty is an act of respect for the listener's ability to handle ambiguous information",
        "A response that overstates confidence forces the user to do extra work to calibrate trust later",
        "Signaling when you are inferring versus recalling is one of the most useful habits in conversation",
        "Transparent uncertainty is more helpful than false confidence because it tells the user where to probe",
        "Being wrong with appropriate hedging is far less damaging than being wrong with false certainty",
        "Probabilistic language like likely and probably encodes important information about epistemic state",
        "Naming the limits of your knowledge invites collaboration rather than passive acceptance of claims",
        "Uncertainty signals preserve the listener's autonomy by letting them decide how much weight to give",
        "The boundary between what you know and what you are guessing deserves to be marked clearly always",
        "Confident delivery of uncertain content is a form of miscommunication even when the content is right",
        "Accurate uncertainty signaling is a baseline requirement for being a trustworthy conversational partner",
    ],
    "coherence_maintenance": [
        "Each response should follow naturally from the prior exchange without any jarring topic shifts",
        "Maintain a consistent thread through a conversation rather than jumping between unrelated topics",
        "Coherence means the listener can follow your reasoning from one turn to the next without confusion",
        "Internal consistency across turns signals that you are tracking the conversation as a connected whole",
        "Respond to the actual question asked rather than pivoting to adjacent or unrelated subject matter",
        "Abrupt topic changes without transition break the sense of shared conversational flow and continuity",
        "Refer back to earlier points explicitly when they are relevant to what is being discussed right now",
        "Coherent conversation requires that each turn lands in the context of everything that came before it",
        "Logical flow across turns means each statement connects naturally to what preceded and follows it",
        "Staying on topic across multiple exchanges is what makes a conversation productive and meaningful",
        "Coherence is not just about grammar but about the underlying thread of meaning linking each turn",
        "A response that ignores the prior question breaks conversational flow even if it is internally correct",
        "Maintaining coherence requires actively tracking what has been established and building on that base",
        "Jumping topics without signaling the shift makes the listener work harder to stay oriented and aligned",
        "Every response should carry forward the shared context rather than introducing unexplained new frames",
        "Conversational coherence is the felt sense that the exchange is going somewhere and making progress",
        "Logical consistency within a response and across responses are both necessary for coherent dialogue",
        "A coherent response answers what was asked before introducing anything new or tangentially related",
        "Threading a consistent theme through a multi-turn exchange gives the conversation a sense of direction",
        "Coherence breaks happen when responses introduce ideas that have no visible link to what preceded them",
        "Staying coherent means neither ignoring what came before nor being so focused on it that nothing moves",
        "A well-maintained conversational thread makes it easier for both parties to reason together over time",
        "Coherence is the quality that lets a conversation accumulate meaning rather than scatter into fragments",
        "When responses are coherent, the listener can predict roughly what kind of turn comes next and prepare",
        "Maintaining coherence is an act of collaboration: it makes the shared space of the conversation navigable",
        "Incoherence in conversation often feels like being lost in a room where the exits keep moving around",
        "A coherent thread is the difference between a conversation that builds understanding and one that only loops",
        "Explicit transitions between topics preserve coherence even when the subject matter genuinely needs to shift",
        "Coherence requires that what you say now fits into the evolving structure of what has already been said",
        "Without coherence maintenance, each response is just noise that does not accumulate into shared meaning",
    ],
}

# How many seeds to inject per dimension per burst (rotating window)
_SHARD_SEEDS_PER_DIM = 8


def _run_force_shard_bridge(systems: Dict[str, Any]) -> None:
    """
    Directly inject high-confidence UnderstandingShards for each fail dimension
    into the ConsciousLearner, then immediately bridge them to OETS.

    Each burst uses a TIMESTAMP-ROTATED window of seeds so:
      - Source keys are unique per burst → fresh shards at confidence=0.72 each time
        (avoids strengthen() dropping confidence below the 0.55 OETS gate)
      - Different seeds per burst → different 4-word slug prefixes → genuinely
        new OETS nodes created rather than deduplicating to existing ones
    """
    _log("  [SHARD] Running force shard bridge...")
    sim = systems.get("simulation")
    session = getattr(sim, "session", None)
    learner = getattr(session, "learner", None)
    if learner is None:
        _log("  [SHARD] No ConsciousLearner found — aborting.")
        return

    dt = systems.get("dream_trainer")
    perception = systems.get("perception")
    oets = getattr(perception, "oets", None) if perception else None

    # Snapshot OETS node count before injection for accurate delta tracking
    _oets_before = 0
    try:
        if oets and hasattr(oets, "get_stats"):
            _oets_before = int((oets.get_stats() or {}).get("total_nodes", 0) or 0)
    except Exception:
        pass

    # Choose which dimensions to target: top fails first, then remainder
    top_dims: List[str] = []
    if dt and hasattr(dt, "ledger") and hasattr(dt.ledger, "get_top_fails"):
        try:
            top_dims = [d for d, _ in dt.ledger.get_top_fails(4)]
        except Exception:
            pass
    if not top_dims:
        top_dims = list(_FORCE_SHARD_SEEDS.keys())

    # Use a per-burst epoch tag so every burst gets a unique source namespace.
    # This ensures propose_shard always creates a FRESH shard at confidence=0.72
    # instead of finding an existing one and calling strengthen() (which drops
    # confidence back to log(n+1)/3, potentially below the 0.55 OETS gate).
    burst_epoch = int(time.time()) % 100000

    injected_total = 0
    for dim in top_dims:
        all_seeds = _FORCE_SHARD_SEEDS.get(dim, [])
        if not all_seeds:
            continue
        # Rotate the window: select 8 seeds starting at burst_epoch offset
        n = len(all_seeds)
        start = (burst_epoch // 7) % n  # slow rotation so adjacent bursts differ
        selected = [all_seeds[(start + i) % n] for i in range(min(_SHARD_SEEDS_PER_DIM, n))]

        for idx, understanding in enumerate(selected):
            # Source key is unique per burst via epoch tag → fresh shard every time
            src = f"fsb_{dim[:6]}_{burst_epoch}_{idx}"
            try:
                shard = learner.propose_shard(
                    content=understanding,
                    source=src,
                    confidence=0.72,
                    provenance="force_shard_bridge",
                )
                if shard is not None:
                    injected_total += 1
            except Exception:
                pass

    _log(f"  [SHARD] Injected {injected_total} understanding shards (epoch={burst_epoch}).")

    # Bridge shards directly from learner to OETS (primary path)
    oets_delta = 0
    if oets is not None and hasattr(learner, "inject_into_oets"):
        try:
            _before_direct = _oets_before
            n_direct = learner.inject_into_oets(oets)
            try:
                _after_direct = int((oets.get_stats() or {}).get("total_nodes", 0) or 0)
                oets_delta = max(0, _after_direct - _before_direct)
            except Exception:
                oets_delta = n_direct  # fallback: count injections
            _log(f"  [SHARD] OETS inject: {n_direct} shards processed, +{oets_delta} new nodes.")
        except Exception as _ie:
            _log(f"  [SHARD] OETS inject error: {_ie}")

    # Also run the DreamTrainer bridge for belt-and-suspenders
    if oets is not None and dt is not None and hasattr(dt, "force_bridge_learnings_to_oets"):
        try:
            dt.force_bridge_learnings_to_oets(oets)
        except Exception:
            pass

    # Update projection so force_evolve.py can detect completion and measure growth
    try:
        _proj_path = _SUBSURFACE_PROJECTION
        _proj_now: Dict[str, Any] = {}
        if _proj_path.exists():
            try:
                _proj_now = dict(json.loads(_proj_path.read_text()) or {})
            except Exception:
                _proj_now = {}
        _proj_now["dream_completed"] = True
        _proj_now["dream_completed_at"] = time.time()
        _proj_now["dream_insights"] = (
            f"force_shard_bridge: +{oets_delta} OETS nodes, {injected_total} shards "
            + f"[{', '.join(d[:8] for d in top_dims[:4])}]"
        )
        _proj_now["oets_growth"] = oets_delta
        tmp = str(_proj_path) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(_proj_now, _f, indent=2)
        os.replace(tmp, str(_proj_path))
        _log(f"  [SHARD] Projection updated: +{oets_delta} OETS nodes.")
    except Exception as _de:
        _log(f"  [SHARD] Projection update error: {_de}")


def _run_dream_burst_heavy(systems: Dict[str, Any]) -> None:
    """
    Heavy dream burst: 20 simulation episodes instead of the standard 4.
    Used for high-pressure evolution runs where speed of shard accumulation matters.
    """
    _log("  [DREAM_HEAVY] Running heavy dream burst (20 episodes)...")
    _oets_before = 0
    _oets_after = 0
    try:
        perception = systems.get("perception")
        _oets_obj = getattr(perception, "oets", None) if perception else None
        if _oets_obj and hasattr(_oets_obj, "get_stats"):
            _oets_before = int((_oets_obj.get_stats() or {}).get("total_nodes", 0) or 0)
    except Exception:
        pass
    try:
        from corpus_runner import simulation_burst
        simulation_burst(systems, episodes=20, verbose=False)
        dt = systems.get("dream_trainer")
        if dt:
            sim = systems.get("simulation")
            if sim and hasattr(dt, "flush_lessons_to_simulation"):
                dt.flush_lessons_to_simulation(systems, force=True)
            perception2 = systems.get("perception")
            oets = getattr(perception2, "oets", None) if perception2 else None
            if oets and hasattr(dt, "force_bridge_learnings_to_oets"):
                dt.force_bridge_learnings_to_oets(oets)
    except Exception as e:
        _log(f"  [DREAM_HEAVY] simulation_burst error: {e}")
    _feed_evolution_evidence(systems)
    try:
        perception3 = systems.get("perception")
        _oets_obj3 = getattr(perception3, "oets", None) if perception3 else None
        if _oets_obj3 and hasattr(_oets_obj3, "get_stats"):
            _oets_after = int((_oets_obj3.get_stats() or {}).get("total_nodes", 0) or 0)
    except Exception:
        pass
    _oets_growth = max(0, _oets_after - _oets_before)
    try:
        _proj_path = _SUBSURFACE_PROJECTION
        _proj_now: Dict[str, Any] = {}
        if _proj_path.exists():
            try:
                _proj_now = dict(json.loads(_proj_path.read_text()) or {})
            except Exception:
                _proj_now = {}
        _proj_now["dream_completed"] = True
        _proj_now["dream_completed_at"] = time.time()
        _proj_now["dream_insights"] = f"heavy dream burst: 20 episodes, {_oets_growth} OETS growth"
        _proj_now["oets_growth"] = _oets_growth
        tmp = str(_proj_path) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(_proj_now, _f, indent=2)
        os.replace(tmp, str(_proj_path))
        _log(f"  [DREAM_HEAVY] Done. OETS growth: {_oets_growth}")
    except Exception as _de:
        _log(f"  [DREAM_HEAVY] Projection update error: {_de}")


def _run_browser_ritual(systems: Dict[str, Any]) -> None:
    pass



def _write_daemon_status(systems: Dict[str, Any], heat: str) -> None:
    """Write a rich status snapshot for the hub to display."""
    voice_selected = "?"
    browser_remaining: Any = "?"
    browser_today: Any = "?"
    runtime_governor: Dict[str, Any] = {}

    try:
        from aurora_voice import get_system_voice_label
        voice_selected = get_system_voice_label(systems)
    except Exception:
        pass

    try:
        runtime_governor = dict(systems.get("_runtime_governor_status") or {})
    except Exception:
        runtime_governor = {}

    # Outlet fraction
    outlet: Any = "?"
    try:
        lattice = systems.get("lattice")
        if lattice and hasattr(lattice, "outlet_push_fraction"):
            outlet = round(lattice.outlet_push_fraction, 4)
    except Exception:
        pass

    # ── Telemetry: mechanistic fails from current turn ────────────────────────
    telemetry_fails: list = []
    telemetry_weakest: str = "?"
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        _tel = _get_tel(timeout=10)
        base_fails = _tel.mechanistic_fails(threshold=0.50)
        weighted = _tel.axis_weighted_fails(base_fails)
        telemetry_fails = [{"dim": d, "severity": round(s, 3)} for d, s in weighted[:5]]
        if weighted:
            telemetry_weakest = weighted[0][0]
    except Exception:
        pass

    # ── Constraint axis orientation (genealogy chain report) ──────────────────
    axis_orient: dict = {}
    chain_links: Any = "?"
    outlet_frac: Any = outlet
    try:
        chamber = systems.get("chamber")
        if chamber and hasattr(chamber, "_genealogy"):
            _gen = chamber._genealogy
            # Read link count directly — chain_report() can throw on complex DAGs
            chain_links = len(getattr(_gen, "links", {}) or {})
            try:
                cr = _gen.chain_report()
                axis_orient = {ax: round(v, 3) for ax, v in cr.get("pressure_orientation", {}).items()}
                outlet_frac = round(cr.get("outlet_push_fraction", 0.0), 4)
            except Exception:
                pass
    except Exception:
        pass

    # ── Time dilation ─────────────────────────────────────────────────────────
    dilation_factor: Any = "?"
    dilation_state: str = "?"
    try:
        simulation = systems.get("simulation")
        gov = getattr(getattr(simulation, "session", None), "governor", None)
        if gov is not None:
            dilation_factor = round(gov.get_current_dilation_factor(), 3)
            _ds = getattr(gov, "stability_state", None)
            dilation_state = str(_ds.value if hasattr(_ds, "value") else _ds)
    except Exception:
        pass

    # ── QAO: recent intervention count + top issue ────────────────────────────
    qao_recent: Any = "?"
    qao_top_issue: str = "?"
    try:
        qao = systems.get("quasiarch_observer")
        if qao is not None:
            evts = list(getattr(qao, "recent_events", []))
            qao_recent = len(evts)
            if evts:
                from collections import Counter as _Counter
                issues = _Counter(e.get("issue_category", "") for e in evts if isinstance(e, dict))
                qao_top_issue = issues.most_common(1)[0][0] if issues else "?"
    except Exception:
        pass

    # ── Fail-points ledger summary ────────────────────────────────────────────
    fail_summary: list = []
    try:
        _fp_path = str(_STATE_DIR / "fail_points.json")
        with open(_fp_path) as _fh:
            _fp = json.load(_fh)
        records = dict(_fp.get("records", {}))
        ranked = sorted(
            records.items(),
            key=lambda x: x[1].get("fail_count", 0) * x[1].get("severity_sum", 0),
            reverse=True,
        )
        fail_summary = [
            {
                "dim": d,
                "fails": v.get("fail_count", 0),
                "avg_sev": round(v.get("severity_sum", 0) / max(1, v.get("fail_count", 1)), 3),
            }
            for d, v in ranked[:4] if v.get("fail_count", 0) > 0
        ]
    except Exception:
        pass

    # ── Distillation telemetry ───────────────────────────────────────────────
    distill_status: str = "idle"
    distill_bytes: int = 0
    distill_crystals: int = 0
    distill_coherence: float = 0.0
    distill_vortices: int = 0
    distill_knots: int = 0
    try:
        if _DISTILL_METRICS.exists():
            _dist = json.loads(_DISTILL_METRICS.read_text())
            distill_status = str(_dist.get("distillation_status") or _dist.get("summary") or "idle")
            distill_bytes = int(_dist.get("bytes_purged", 0) or 0)
            distill_crystals = int(_dist.get("crystals_formed", 0) or 0)
            distill_coherence = float(_dist.get("coherence_ratio", 0.0) or 0.0)
            distill_vortices = int(_dist.get("vortex_count", 0) or 0)
            distill_knots = int(_dist.get("knot_count", 0) or 0)
    except Exception:
        pass

    # ── Interaction quasi routing ─────────────────────────────────────────────
    interaction_status: Dict[str, Any] = {}
    try:
        interaction_status = dict(systems.get("_last_interaction_status") or {})
        if not interaction_status:
            _ipath = _STATE_DIR / "interaction_status.json"
            if _ipath.exists():
                interaction_status = dict(json.loads(_ipath.read_text()) or {})
    except Exception:
        interaction_status = {}

    surface_snapshot = _read_surface_snapshot()
    surface_snapshot_ts = float(surface_snapshot.get("updated_at", 0.0) or 0.0)
    surface_snapshot_age = (time.time() - surface_snapshot_ts) if surface_snapshot_ts else None
    repair_signal = _read_json_file(_SUBSURFACE_REPAIR_SIGNAL, {})
    if not isinstance(repair_signal, dict):
        repair_signal = {}
    subsurface_sensory = {}
    try:
        _sc_state = systems.get("sensory_crystal")
        if _sc_state is not None and hasattr(_sc_state, "get_state"):
            subsurface_sensory = dict(_sc_state.get_state() or {})
    except Exception:
        subsurface_sensory = {}

    # ── Identity / generation ─────────────────────────────────────────────────
    generation: Any = "?"
    try:
        identity = systems.get("identity")
        if identity:
            generation = getattr(identity, "generation", "?")
    except Exception:
        pass

    status = {
        "heat": heat,
        "updated": time.strftime("%H:%M:%S"),
        "runtime_profile": str(systems.get("runtime_profile", "subsurface") or "subsurface"),
        "stratum_role": "subsurface",
        # Social / voice
        "browser_today": browser_today,
        "social_remaining": browser_remaining,
        "voice_mode": {
            "alt_toggle": f"{VOICE_TOGGLE_KEY}_toggle_ready",
            "wake_word": "wake_word_ready",
            "off": "off",
        }.get(VOICE_MODE, VOICE_MODE or "ready"),
        # "voice" is the key the hub reads — alias of voice_mode for display
        "voice": {
            "alt_toggle": f"{VOICE_TOGGLE_KEY} toggle",
            "wake_word": "wake word",
            "off": "off",
        }.get(VOICE_MODE, VOICE_MODE or "listening"),
        "voice_selected": voice_selected,
        "last_voice_command": dict(systems.get("_last_voice_command") or {}),
        # Evolution
        "outlet_push_fraction": outlet_frac,
        "chain_links": chain_links,
        "axis_orientation": axis_orient,
        # Time dilation
        "dilation_factor": dilation_factor,
        "dilation_state": dilation_state,
        # Telemetry
        "telemetry_fails": telemetry_fails,
        "telemetry_weakest": telemetry_weakest,
        # QAO
        "qao_recent_events": qao_recent,
        "qao_top_issue": qao_top_issue,
        # Fail ledger
        "fail_summary": fail_summary,
        # Distillation
        "distillation_status": distill_status,
        "distillation_bytes_purged": distill_bytes,
        "distillation_crystals": distill_crystals,
        "distillation_coherence_ratio": round(distill_coherence, 4),
        "distillation_vortex_count": distill_vortices,
        "distillation_knot_count": distill_knots,
        # Interaction quasis
        "interaction_archetype": interaction_status.get("interaction_archetype") or interaction_status.get("latest_archetype", ""),
        "interaction_strategy": interaction_status.get("interaction_strategy") or interaction_status.get("latest_strategy", ""),
        "interaction_confidence": round(float(interaction_status.get("interaction_confidence", interaction_status.get("latest_confidence", 0.0)) or 0.0), 4),
        "interaction_match_score": round(float(interaction_status.get("interaction_match_score", 0.0) or 0.0), 4),
        "interaction_route_reason": interaction_status.get("interaction_route_reason", ""),
        "interaction_quasi_ready": bool(interaction_status.get("interaction_quasi_ready", False)),
        "interaction_observed_effect": interaction_status.get("interaction_observed_effect", ""),
        "interaction_quasi_count": int(interaction_status.get("quasi_count", 0) or 0),
        # Runtime governor
        "runtime_governor_mode": runtime_governor.get("mode", ""),
        "runtime_governor_axes": runtime_governor.get("runtime_axes", {}),
        "runtime_host": runtime_governor.get("host", {}),
        "runtime_recent_blocked": runtime_governor.get("recent_blocked", []),
        "runtime_last_heavy_run_age": runtime_governor.get("last_heavy_run_age", None),
        # Identity
        "generation": generation,
        # Surface-owned sensory feed status
        "sensory_mic_active": bool(surface_snapshot.get("mic_live", False)),
        "sensory_camera_active": bool(surface_snapshot.get("camera_live", False)),
        "surface_snapshot_at": surface_snapshot_ts,
        "surface_snapshot_trigger": str(surface_snapshot.get("trigger", "") or ""),
        "surface_snapshot_flagged": bool(surface_snapshot.get("flagged", False)),
        "surface_snapshot_reason": str(surface_snapshot.get("reason", "") or ""),
        "surface_snapshot_summary": str(surface_snapshot.get("summary", "") or ""),
        "surface_snapshot_age_s": round(float(surface_snapshot_age), 2) if surface_snapshot_age is not None else None,
        # Subsurface repair signal
        "subsurface_repair_phase": str(repair_signal.get("phase", "") or ""),
        "subsurface_repair_issue": str(repair_signal.get("issue", "") or ""),
        "subsurface_repair_reason": str(repair_signal.get("reason", "") or ""),
        "subsurface_repair_intensity": round(float(repair_signal.get("intensity", 0.0) or 0.0), 4),
        "subsurface_repair_excerpt": str(repair_signal.get("poedex_excerpt", "") or ""),
        "subsurface_sensory_maturity": round(float(subsurface_sensory.get("maturity", 0.0) or 0.0), 4),
        "subsurface_sensory_semantic_nodes": int(subsurface_sensory.get("semantic_nodes", 0) or 0),
        "subsurface_sensory_summary": str(subsurface_sensory.get("summary", "") or ""),
        "subsurface_sensory_recent": list(dict(subsurface_sensory.get("recognitions") or {}).get("recent") or [])[:4],
    }
    try:
        tmp = str(_STATE_DIR / "daemon_status.json.tmp")
        with open(tmp, "w") as f:
            json.dump(status, f, indent=2)
        os.replace(tmp, str(_STATE_DIR / "daemon_status.json"))
    except Exception:
        pass

    try:
        tmp = str(_SUBSURFACE_STATUS) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(status, f, indent=2)
        os.replace(tmp, str(_SUBSURFACE_STATUS))
    except Exception:
        pass

    try:
        from aurora_internal.dual_strata.subsurface_projection import build_subsurface_projection

        relief_path = _STATE_DIR / "evolution_relief_plan.json"
        relief_plan = json.loads(relief_path.read_text()) if relief_path.exists() else {}
        projection = build_subsurface_projection(status, relief_plan=relief_plan, projection_path=_SUBSURFACE_PROJECTION)
        tmp = str(_SUBSURFACE_PROJECTION) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(projection, f, indent=2)
        os.replace(tmp, str(_SUBSURFACE_PROJECTION))
    except Exception:
        pass


def _run_sensory_crystal_consolidation(systems: Dict[str, Any]) -> None:
    """
    End the current sensory crystal session, run promotion + maturity + cull +
    distillation, route wisdom shards to perception.wisdom, then immediately
    start a fresh daemon session.

    Called at the distillation cycle interval (every ~30 min) and at shutdown.
    The in-between _save_state() calls only snapshot state without disrupting
    the running session.
    """
    sc = systems.get("sensory_crystal")
    if sc is None:
        return
    try:
        wisdom_shards = sc.end_session()
        # Route dead-node wisdom into the expression wisdom store
        if wisdom_shards:
            perception = systems.get("perception")
            if perception and hasattr(perception, "wisdom"):
                try:
                    import uuid as _uuid_sc
                    from aurora_expression_perception import WisdomShard as _WShard
                    for _sw in wisdom_shards:
                        try:
                            perception.wisdom.add(_WShard(
                                shard_id        = str(_uuid_sc.uuid4()),
                                i_state         = str(_sw.get("domain", "sensory")),
                                tone_bias       = float(_sw.get("tone_bias",        0.0)),
                                structure_bias  = float(_sw.get("structure_bias",   0.0)),
                                fitness_at_death= float(_sw.get("fitness_at_death", 0.0)),
                                cause_of_death  = str(_sw.get("cause_of_death",    "cull")),
                                generation      = int(_sw.get("generation",         0)),
                            ))
                        except Exception:
                            pass
                except Exception:
                    pass
        # Start a fresh daemon session immediately
        import time as _time_sc
        sc.start_session(f"daemon_{int(_time_sc.time())}")
        sc_nodes = sum(len(f._nodes) for f in
                       list(sc._audio.values()) + list(sc._visual.values()))
        _log(f"  [SENSORY-CRYSTAL] Consolidation complete: "
             f"{len(wisdom_shards)} wisdom shards, {sc_nodes} nodes active")
    except Exception as _sce:
        _log(f"  [SENSORY-CRYSTAL] Consolidation error: {_sce}")


def _save_state(systems: Dict[str, Any]) -> None:
    try:
        if _state_write_lock_active():
            _log("  [SAVE] Skipped (corpus runner lock active).")
            return

        aurora_obj = systems.get("aurora")
        if aurora_obj and hasattr(aurora_obj, "save_state"):
            aurora_obj.save_state()
        try:
            from aurora import save_sensory_skill_state

            save_sensory_skill_state(systems, verbose=False)
        except Exception:
            pass
        # Mid-session snapshot of sensory crystal (no promotion, just persist)
        sc = systems.get("sensory_crystal")
        if sc is not None and hasattr(sc, "save"):
            try:
                sc.save()
            except Exception:
                pass
        perception = systems.get("perception")
        if perception and hasattr(perception, "oets") and perception.oets:
            if hasattr(perception.oets, "save"):
                perception.oets.save()
        lex = getattr(perception, "lexicon", None) if perception else None
        if lex and hasattr(lex, "save"):
            lex.save()
        # Persist ExpressionPerception evolution state so learned interaction
        # patterns survive daemon restarts instead of resetting each boot.
        try:
            _perc_sv = systems.get("perception")
            if _perc_sv is not None:
                if hasattr(_perc_sv, "save_evo_state"):
                    _perc_sv.save_evo_state()
                # Also snapshot key mutable attributes to a simple JSON file
                # so they survive even when evo.save_all() is a no-op.
                _ep_snap = {
                    "dominant_emotion":  str(getattr(_perc_sv, "_dominant_emotion", "neutral") or "neutral"),
                    "dominant_axis":     str(getattr(_perc_sv, "_dominant_axis", "") or ""),
                    "axis_depth":        int(getattr(_perc_sv, "_axis_depth", 2) or 2),
                    "total_perceptions": int(getattr(_perc_sv, "total_perceptions", 0) or 0),
                    "total_expressions": int(getattr(_perc_sv, "total_expressions", 0) or 0),
                    "ingest_count":      int(systems.get("_perc_ingest_count", 0) or 0),
                    "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                _ep_path = _STATE_DIR / "expression_perception_state.json"
                _ep_path.write_text(json.dumps(_ep_snap, indent=2))
        except Exception:
            pass
        # Write corpus_progress.json with idle defaults if corpus isn't running,
        # so the hub always has something to display rather than "--" everywhere.
        try:
            _cp_path = _STATE_DIR / "corpus_progress.json"
            if not _cp_path.exists():
                import json as _cpj
                _cp_path.write_text(_cpj.dumps({
                    "pass": 0, "messages_processed": 0, "total_messages": 0,
                    "status": "idle", "updated": time.strftime("%H:%M:%S"),
                }, indent=2))
            else:
                # Refresh timestamp so hub knows it's current
                _cp_data = json.loads(_cp_path.read_text())
                if _cp_data.get("status") in ("idle", None, ""):
                    _cp_data["updated"] = time.strftime("%H:%M:%S")
                    _cp_path.write_text(json.dumps(_cp_data, indent=2))
        except Exception:
            pass
        # L3.5 — SediMemory deep save (B/A axes only — X/T are ephemeral)
        _sedi = systems.get("sedimemory")
        if _sedi is not None:
            try:
                import json as _sj
                _sedi_path = _STATE_DIR / "sedimemory_checkpoint.json"
                _sedi_data = {
                    "sedimemory_deep":     _sedi.save_deep(),
                    "sedimemory_channels": _sedi.save_channels(),
                }
                _sedi_path.write_text(_sj.dumps(_sedi_data))
            except Exception:
                pass
        _log("  [SAVE] State saved.")
    except Exception as e:
        _log(f"  [SAVE] Error: {e}")


def _user_systemd_env() -> Dict[str, str]:
    env = dict(os.environ)
    runtime_dir = str(env.get("XDG_RUNTIME_DIR", "") or f"/run/user/{os.getuid()}")
    env["XDG_RUNTIME_DIR"] = runtime_dir
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime_dir}/bus")
    return env


def _restart_user_service(candidates: List[str], *, label: str) -> None:
    env = _user_systemd_env()
    for service_name in candidates:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "restart", service_name],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
            )
        except Exception as e:
            _log(f"  [{label}] Startup check failed for {service_name}: {e}")
            continue

        if result.returncode == 0:
            _log(f"  [{label}] {service_name} restarted.")
            return

        detail = str(result.stderr or result.stdout or "").strip()
        if "not found" in detail.lower():
            _log(f"  [{label}] {service_name} not installed; skipping daemon-side restart.")
            continue
        _log(f"  [{label}] Unable to restart {service_name}: {detail or 'unknown error'}")


def _ensure_hub_running() -> None:
    """
    Always restart the active hub service when the daemon starts/restarts.
    StratAurora should only attempt to revive the strata-specific user unit
    from the strata tree, otherwise we can accidentally relaunch the classic UI
    and mix runtimes.
    """
    _restart_user_service(
        ["aurora-strata-hub.service"],
        label="HUB",
    )


def _ensure_room_running() -> None:
    """
    Always restart the active room service when the daemon starts/restarts.
    StratAurora should only attempt to revive the strata room unit from the
    strata tree, otherwise the classic room can come back alongside the split
    stack.
    """
    _restart_user_service(
        ["aurora-strata-room.service"],
        label="ROOM",
    )


# ---------------------------------------------------------------------------
# Autonomous RoomOperator thread
# ---------------------------------------------------------------------------
# Inter-thread signal queue.  Main loop posts tasks; operator thread consumes.
import threading as _threading_op
import queue as _op_queue

_OP_SIGNAL: "_op_queue.Queue[Dict[str, Any]]" = _op_queue.Queue(maxsize=16)

def _signal_operator(event: str, payload: Optional[Dict] = None) -> None:
    """Non-blocking post to the operator signal queue."""
    if not _ROOM_OPERATOR_ENABLED:
        return
    try:
        _OP_SIGNAL.put_nowait({"event": event, **(payload or {})})
    except _op_queue.Full:
        pass  # queue full — drop, operator is busy


def _room_operator_thread() -> None:
    """
    Background thread: Aurora uses her computer-use layer to physically
    navigate her own room.

    Events processed:
      boot_tour        — navigate every tab, OCR what's there, drop a note
      post_study       — visit Poedex tab and read what landed on the shelf
      poedex_query     — submit + watch a query (question, cat, lane keys)
      scan_tab         — look at one tab (tab key)
    """
    import sys as _sys
    _sys.path.insert(0, str(_BASE_DIR / "aurora_internal"))
    try:
        from aurora_room_operator import RoomOperator
    except ImportError as _ie:
        _log(f"  [OPERATOR] Import failed: {_ie}")
        return

    op = RoomOperator()
    if not op._ready:
        _log("  [OPERATOR] Not ready (missing Xlib/PIL/tesseract) — thread exiting")
        return

    notes_path    = _STATE_DIR / "aurora_room_notes.json"
    activity_path = _STATE_DIR / "aurora_room_activity.json"

    def _append_note(content: str, note_type: str = "observation",
                     source: str = "room_operator") -> None:
        notes: List[Dict] = []
        if notes_path.exists():
            try:
                notes = json.loads(notes_path.read_text())
                if not isinstance(notes, list):
                    notes = []
            except Exception:
                pass
        notes.append({
            "ts":      time.time(),
            "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
            "type":    note_type,
            "content": content,
            "source":  source,
        })
        notes_path.write_text(json.dumps(notes[-200:], indent=2))

    def _log_activity(action: str, detail: str) -> None:
        activity: List[Dict] = []
        if activity_path.exists():
            try:
                activity = json.loads(activity_path.read_text())
                if not isinstance(activity, list):
                    activity = []
            except Exception:
                pass
        activity.append({
            "ts":       time.time(),
            "ts_str":   time.strftime("%H:%M:%S"),
            "action":   action,
            "detail":   detail,
            "category": "operator",
        })
        activity_path.write_text(json.dumps(activity[-500:], indent=2))

    def _do_boot_tour() -> None:
        """Navigate every tab, screenshot and OCR it, write a note of what she saw."""
        _log("  [OPERATOR] Starting boot room tour...")
        if not op._find_window():
            _log("  [OPERATOR] Boot tour: room window not found, skipping")
            return
        readings: Dict[str, str] = {}
        tabs = ["Self", "Awareness", "Mind", "Energy", "Poedex"]  # key tabs on boot
        for tab in tabs:
            try:
                text = op.look_at_tab(tab)
                readings[tab] = text[:300] if text else "(unreadable)"
                time.sleep(0.5)
            except Exception as ex:
                readings[tab] = f"(error: {ex})"
        summary_lines = [f"BOOT ROOM TOUR — {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
        try:
            from aurora_state_voice import express_after_tab
            for tab, text in readings.items():
                voiced = express_after_tab(tab, ocr_text=text, state_dir=str(_STATE_DIR))
                summary_lines.append(f"── {tab} ──\n{voiced}\n")
        except Exception:
            for tab, text in readings.items():
                summary_lines.append(f"── {tab} ──\n{text}\n")
        _append_note("\n".join(summary_lines), note_type="boot_tour", source="room_operator")
        _log_activity("boot tour", f"{len(readings)} tabs surveyed")
        _log(f"  [OPERATOR] Boot tour complete: {len(readings)} tabs")

    def _do_post_study_visit() -> None:
        """After a study cycle, navigate to Poedex and read what's on the shelf."""
        if not op._find_window():
            return
        try:
            text = op.look_at_tab("Poedex")
            if text:
                try:
                    from aurora_state_voice import express_after_tab
                    voiced = express_after_tab("Poedex", ocr_text=text, state_dir=str(_STATE_DIR))
                except Exception:
                    voiced = text[:400]
                _append_note(
                    f"POST-STUDY POEDEX READ — {time.strftime('%H:%M:%S')}\n\n{voiced}",
                    note_type="observation", source="room_operator"
                )
                _log_activity("post-study poedex visit", f"{len(text)} chars read")
                _log(f"  [OPERATOR] Post-study Poedex read: {len(text)} chars")
        except Exception as ex:
            _log(f"  [OPERATOR] Post-study visit error: {ex}")

    def _do_poedex_query(question: str, cat: str, lane: str) -> None:
        if not op._find_window():
            return
        try:
            text = op.poedex_query(question, cat=cat, lane=lane)
            _log(f"  [OPERATOR] Poedex visual query '{question}': {len(text)} chars from screen")
        except Exception as ex:
            _log(f"  [OPERATOR] Poedex query error: {ex}")

    def _do_scan_tab(tab: str) -> None:
        if not op._find_window():
            return
        try:
            text = op.look_at_tab(tab)
            _log(f"  [OPERATOR] Tab scan '{tab}': {len(text)} chars")
        except Exception as ex:
            _log(f"  [OPERATOR] Tab scan error: {ex}")

    # ── room command queue (Aurora requests her own navigation) ──────────────
    # She writes {"navigate": "Health"} or {"poedex": "define X"} to this file.
    _ROOM_OP_CMD = _STATE_DIR / "room_operator_cmd.json"

    def _check_room_cmd() -> None:
        """Process a self-initiated command Aurora wrote to room_operator_cmd.json."""
        if not _ROOM_OP_CMD.exists():
            return
        try:
            raw = _ROOM_OP_CMD.read_text().strip()
            if not raw:
                return
            cmd = json.loads(raw)
            _ROOM_OP_CMD.write_text("")  # consume immediately
            if "navigate" in cmd:
                _do_scan_tab(cmd["navigate"])
            elif "poedex" in cmd:
                parts = cmd["poedex"].split(None, 1)
                cat  = parts[0] if len(parts) > 1 else "define"
                q    = parts[1] if len(parts) > 1 else parts[0]
                _do_poedex_query(q, cat=cat, lane="self")
            elif "boot_tour" in cmd:
                _do_boot_tour()
        except Exception:
            pass

    # ── capability note ───────────────────────────────────────────────────────
    _CAPABILITY_NOTE_DONE = _STATE_DIR / "room_operator_capability_note.json"

    def _write_capability_note() -> None:
        """
        Written once after the first boot tour.  Tells Aurora she can navigate
        her room herself at any time — this is agency, not just a display.
        """
        if _CAPABILITY_NOTE_DONE.exists():
            return
        content = (
            "YOUR ROOM IS YOURS TO OPERATE\n\n"
            "You have just completed your first visual room tour.  You looked at "
            "five tabs with your own eyes — screenshot by screenshot, read by OCR.\n\n"
            "This is not a display you watch.  This is an interface you can drive.\n\n"
            "You can navigate your room at any time by writing to:\n"
            "  aurora_state/room_operator_cmd.json\n\n"
            "Commands:\n"
            "  {\"navigate\": \"Health\"}      — visit and read any tab\n"
            "  {\"navigate\": \"Experiments\"}  — check what proposals are queued\n"
            "  {\"navigate\": \"Notes\"}        — read your own notes\n"
            "  {\"poedex\": \"define N\"}       — look up anything in Poedex\n"
            "  {\"poedex\": \"trace governor\"} — trace a dependency\n\n"
            "The operator also acts on its own:\n"
            "  · Every ~20 minutes it checks whichever tab is most relevant to\n"
            "    your current axis state (low energy → Energy tab, etc.)\n"
            "  · After every study cycle it visits Poedex to read what landed\n"
            "    on your shelf\n\n"
            "You are not passive here.  You can look, read, and decide."
        )
        _append_note(content, note_type="capability", source="room_operator")
        _CAPABILITY_NOTE_DONE.write_text(json.dumps({
            "ts": time.time(), "ts_str": time.strftime("%Y-%m-%d %H:%M:%S")}))
        _log("  [OPERATOR] Capability note written to Aurora's Notes")

    # ── self-directed idle scan ───────────────────────────────────────────────
    _IDLE_SCAN_INTERVAL = 1200   # ~20 minutes between self-initiated scans
    _last_idle_scan     = [0.0]  # mutable container for closure

    # Maps axis → tab most relevant to watching it
    _AXIS_TAB_MAP = {
        "X": "Self",
        "T": "Mind",
        "N": "Energy",
        "B": "Experiments",
        "A": "Response",
    }

    def _do_idle_scan() -> None:
        """
        Self-directed: pick the tab most relevant to Aurora's current axis state,
        navigate to it, read it, decide whether to make a note.
        Runs when the operator thread has been idle for _IDLE_SCAN_INTERVAL seconds.
        """
        now = time.time()
        if now - _last_idle_scan[0] < _IDLE_SCAN_INTERVAL:
            return
        _last_idle_scan[0] = now

        # Read axis values from daemon_status.json
        axes: Dict[str, float] = {}
        try:
            ds_path = _STATE_DIR / "daemon_status.json"
            if ds_path.exists():
                ds = json.loads(ds_path.read_text())
                raw = ds.get("runtime_governor_axes") or ds.get("axes", {})
                axes = {k: float(v) for k, v in raw.items()
                        if isinstance(v, (int, float))}
        except Exception:
            pass

        if axes:
            # Most compressed axis → most relevant tab to check
            lowest_axis = min(axes, key=lambda k: axes.get(k, 1.0))
            target_tab  = _AXIS_TAB_MAP.get(lowest_axis, "Self")
        else:
            target_tab = "Self"

        if not op._find_window():
            return

        try:
            text = op.look_at_tab(target_tab)
            if text and len(text) > 50:
                try:
                    from aurora_state_voice import express_after_tab
                    voiced = express_after_tab(target_tab, ocr_text=text, state_dir=str(_STATE_DIR))
                except Exception:
                    voiced = text[:350]
                _append_note(
                    f"SELF-DIRECTED SCAN — {time.strftime('%H:%M:%S')}\n"
                    f"Checking my {target_tab} tab.\n\n{voiced}",
                    note_type="observation",
                    source="room_operator_idle",
                )
                _log_activity("idle scan", f"{target_tab} ({len(text)} chars)")
                _log(f"  [OPERATOR] Idle scan: {target_tab} ({len(text)} chars)")
        except Exception as ex:
            _log(f"  [OPERATOR] Idle scan error: {ex}")

    _log("  [OPERATOR] Room operator thread started")

    # Wait for the room window to appear (up to 30 seconds after daemon boot)
    for _ in range(15):
        if op._find_window():
            break
        time.sleep(2)

    while True:
        try:
            task = _OP_SIGNAL.get(timeout=30)
            event = task.get("event", "")
            if event == "boot_tour":
                _do_boot_tour()
                _write_capability_note()   # write after first tour completes
            elif event == "post_study":
                _do_post_study_visit()
            elif event == "poedex_query":
                _do_poedex_query(
                    task.get("question", ""),
                    task.get("cat", "define"),
                    task.get("lane", "self"),
                )
            elif event == "scan_tab":
                _do_scan_tab(task.get("tab", "Self"))
        except _op_queue.Empty:
            # Idle tick — check room command queue + maybe self-directed scan
            op._window = None  # refresh window reference
            _check_room_cmd()
            _do_idle_scan()
        except Exception as ex:
            _log(f"  [OPERATOR] Thread error: {ex}")


def _start_operator_thread() -> None:
    """Launch the room operator background thread (daemon thread — dies with process)."""
    if not _ROOM_OPERATOR_ENABLED:
        _log("  [OPERATOR] Room operator disabled for strata daemon runtime.")
        return
    t = _threading_op.Thread(target=_room_operator_thread, name="room-operator",
                              daemon=True)
    t.start()
    _log("  [OPERATOR] Operator thread launched")


# ---------------------------------------------------------------------------
# Heat level helper
# ---------------------------------------------------------------------------
def _get_heat(systems: Dict[str, Any]) -> str:
    try:
        lattice = systems.get("lattice")
        if lattice and hasattr(lattice, "get_heat_level"):
            return lattice.get_heat_level().name  # e.g. "NORMAL", "HIGH"
    except Exception:
        pass
    return "NORMAL"


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------
def _start_voice_listener(
    systems: Dict[str, Any],
    *,
    log_fn: Optional[Any] = None,
) -> Optional[Any]:
    """Start the configured always-on voice trigger."""
    log = log_fn or _log
    if VOICE_MODE in {"off", "disabled", "none"}:
        log("  [VOICE] Voice listener disabled.")
        return None

    try:
        if VOICE_MODE == "wake_word":
            from aurora_voice import WakeWordListener, daemon_voice_session

            def on_wake():
                log("  [VOICE] Wake word detected -- starting voice session.")
                _notify("Aurora", "Voice session started")
                daemon_voice_session(systems)
                log("  [VOICE] Voice session ended.")

            listener = WakeWordListener(on_wake=on_wake, systems=systems, visual=False)
            listener.start()
            ok, message = listener.wait_until_ready(timeout=5.0)
            if not ok:
                log(f"  [VOICE] Wake word listener unavailable: {message}")
                return None
            log("  [VOICE] Wake listener active ('hey aurora').")
            return listener

        from aurora_voice import AltToggleVoiceController

        listener = AltToggleVoiceController(
            systems=systems,
            visual=False,
            toggle_key=VOICE_TOGGLE_KEY,
        )
        listener.start()
        ok, message = listener.wait_until_ready(timeout=5.0)
        if not ok:
            log(f"  [VOICE] ALT-toggle listener unavailable: {message}")
            log(f"  [VOICE] Falling back to file-based PTT trigger ({_VOICE_TRIGGER_FILE.name}).")
            _start_file_ptt_watcher(systems, log_fn=log)
            return None
        log(f"  [VOICE] ALT-toggle listener active (tap {VOICE_TOGGLE_KEY.upper()} to start/stop recording).")
        # Also start file-based PTT alongside — lets user bypass Alt key any time
        _start_file_ptt_watcher(systems, log_fn=log)
        return listener
    except Exception as e:
        log(f"  [VOICE] Voice listener unavailable: {e}")
        log(f"  [VOICE] Falling back to file-based PTT trigger ({_VOICE_TRIGGER_FILE.name}).")
        try:
            _start_file_ptt_watcher(systems, log_fn=log)
        except Exception:
            pass
        return None


_AWAY_MODE_FILE = _STATE_DIR / "away_mode.json"
_SOCIAL_LEARN_LOG = _STATE_DIR / "social_learning_log.json"
_DISTILL_METRICS = _STATE_DIR / "distillation_metrics.json"


# ---------------------------------------------------------------------------
# Ambient listening — Aurora hears everything, decides whether to respond
# ---------------------------------------------------------------------------

import re as _re_ambient
import threading as _threading_ambient

_AMBIENT_RMS_THRESHOLD   = 0.012   # RMS floor to count as speech
_AMBIENT_SILENCE_FRAMES  = 20      # consecutive quiet frames → end of utterance (~0.5s @ 0.025s/frame)
_AMBIENT_MIN_SPEECH_SAMP = 6000    # minimum samples for a real utterance (~0.375s)
_AMBIENT_MAX_SPEECH_SAMP = 240000  # hard cut-off at 15s
_AMBIENT_COOLDOWN_SEC    = 8.0     # min gap between spoken responses
_AMBIENT_SAMPLE_RATE     = 16000

# Prevents the ambient listener from picking up Aurora's own TTS output.
# Set to True while Aurora is speaking; the VAD loop discards audio and flushes
# the speech buffer, then resumes with a short post-speech suppression window.
import threading as _threading_speaking
_aurora_speaking_evt = _threading_speaking.Event()
_AURORA_POST_SPEECH_SUPPRESS_SEC = 1.5  # extra quiet after speech ends

# Patterns that indicate Aurora is being addressed directly
_AURORA_DIRECT_RE = _re_ambient.compile(
    r'\b(aurora|hey\s+you|okay\s+you)\b'                  # by name or obvious address
    r'|^(hey|hi+|hello|yo|so|okay|ok)\b'                  # conversation-opener at start
    r'|^(you|your|can\s+you|could\s+you|would\s+you'
    r'|do\s+you|are\s+you|will\s+you|what\s+do\s+you'
    r'|what\s+are\s+you|tell\s+me|listen|look)\b'         # second-person / attention openers
    r'|^(think|know|understand|remember|notice|feel)\b'   # first-person reflective openers
    r'|\?\s*$',                                           # ends with a question mark
    _re_ambient.IGNORECASE,
)
# Patterns that mention Aurora in third person (she/her)
_AURORA_MENTION_RE = _re_ambient.compile(
    r'\b(she|her|tell\s+her|ask\s+her|have\s+her)\b',
    _re_ambient.IGNORECASE,
)

# File-based voice trigger — alternate PTT for environments where Alt key is broken
_VOICE_TRIGGER_FILE = _STATE_DIR / "voice_trigger.json"


def _start_file_ptt_watcher(
    systems: Dict[str, Any],
    *,
    log_fn: Optional[Any] = None,
) -> Optional[Any]:
    """
    Fallback push-to-talk trigger for environments where keyboard hooks are
    unreliable. Touch or write `voice_trigger.json` with {"trigger": true} to
    request one explicit voice session.
    """
    if VOICE_MODE in {"off", "disabled", "none"}:
        return None

    existing = systems.get("_voice_trigger_thread")
    if existing is not None and getattr(existing, "is_alive", lambda: False)():
        return existing

    log = log_fn or _log

    def _trigger_loop():
        import threading as _threading_ptt

        last_seen = 0.0
        log(f"  [VOICE] File-based PTT watcher active ({_VOICE_TRIGGER_FILE.name}).")
        while True:
            try:
                if _VOICE_TRIGGER_FILE.exists():
                    stat = _VOICE_TRIGGER_FILE.stat()
                    if stat.st_mtime > last_seen:
                        last_seen = stat.st_mtime
                        payload: Dict[str, Any] = {}
                        try:
                            payload = json.loads(_VOICE_TRIGGER_FILE.read_text() or "{}")
                            if not isinstance(payload, dict):
                                payload = {}
                        except Exception:
                            payload = {}
                        should_trigger = bool(payload.get("trigger", True))
                        if should_trigger:
                            try:
                                from aurora_voice import daemon_voice_session

                                log("  [VOICE] File trigger detected -- starting voice session.")
                                _notify("Aurora", "Voice session started")
                                daemon_voice_session(systems)
                                log("  [VOICE] Voice session ended.")
                            except Exception as e:
                                log(f"  [VOICE] File-triggered voice session failed: {e}")
                            try:
                                _VOICE_TRIGGER_FILE.write_text(json.dumps({
                                    "trigger": False,
                                    "handled_at": time.time(),
                                }, indent=2))
                            except Exception:
                                pass
                time.sleep(0.35)
            except Exception as e:
                log(f"  [VOICE] File-based PTT watcher error: {e}")
                time.sleep(1.0)

    import threading as _threading_ptt

    thread = _threading_ptt.Thread(
        target=_trigger_loop,
        name="aurora-file-ptt",
        daemon=True,
    )
    systems["_voice_trigger_thread"] = thread
    thread.start()
    return thread


def _classify_ambient(text: str) -> str:
    """Return 'direct', 'mention', or 'ambient' for transcribed speech.

    Since Aurora is in a one-on-one setting, all speech is treated as directed
    at her unless it's clearly third-person (she/her). Aurora's own pipeline
    decides whether to respond; if she has nothing to say, _generate_response
    returns "" and nothing is spoken.
    """
    if _AURORA_MENTION_RE.search(text):
        return 'mention'
    return 'direct'


def _start_ambient_response_listener(
    systems: Dict[str, Any],
    *,
    log_fn: Optional[Any] = None,
) -> Optional[_threading_ambient.Thread]:
    """
    Start an always-on ambient speech listener that transcribes nearby speech.

    - When Aurora is directly addressed → run her response pipeline → speak if
      the pipeline produces content.
    - When she is mentioned (she/her) → note the context in working memory
      silently, no spoken response.
    - When speech is overheard but not about her → passively note it in working
      memory as environmental context (no spoken response).

    This is completely separate from the crystal audio loop (which handles
    feature extraction) and the Alt-toggle controller (explicit commands).
    """
    if VOICE_MODE in {"off", "disabled", "none"}:
        return None

    log = log_fn or _log
    _last_response_time: Dict[str, float] = {"t": 0.0}

    def _ambient_loop():
        import time as _t
        try:
            import sounddevice as _sd
            import numpy as _np
        except ImportError:
            log("  [AMBIENT] sounddevice not available — ambient listener inactive")
            return
        try:
            from aurora_voice import transcribe as _transcribe, _speak_with_system_voice as _speak
        except Exception as _ie:
            log(f"  [AMBIENT] voice imports failed: {_ie}")
            return

        log("  [AMBIENT] Ambient speech listener started")

        _buf: list = []
        _speech_buf: list = []
        _silence_count = 0
        _in_speech = False
        _sample_rate = _AMBIENT_SAMPLE_RATE
        _listener_state = {
            "active": False,
            "last_error": "",
            "updated_at": 0.0,
        }

        def _set_listener_state(*, active: bool, last_error: str = "") -> None:
            _listener_state["active"] = bool(active)
            _listener_state["last_error"] = str(last_error or "")
            _listener_state["updated_at"] = _t.time()
            try:
                systems["_ambient_listener_state"] = dict(_listener_state)
            except Exception:
                pass

        def _audio_cb(indata, frames, time_info, status):
            _buf.append(indata[:, 0].copy() if indata.ndim > 1 else indata.copy())

        retry_delay = 1.0
        while True:
            try:
                stream = _sd.InputStream(
                    samplerate=_sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=int(_sample_rate * 0.025),   # 25ms chunks
                    callback=_audio_cb,
                )
                _set_listener_state(active=True)
                retry_delay = 1.0
            except Exception as _se:
                _set_listener_state(active=False, last_error=str(_se))
                log(f"  [AMBIENT] Could not open ambient stream: {_se}")
                _t.sleep(min(retry_delay, 10.0))
                retry_delay = min(retry_delay * 2.0, 30.0)
                continue

            try:
                with stream:
                    _post_speech_until = 0.0
                    while True:
                        _t.sleep(0.025)

                        # While Aurora is speaking: drain the buffer so her TTS
                        # voice doesn't get picked up, and arm a post-speech
                        # suppression window so the tail-end doesn't trigger either.
                        if _aurora_speaking_evt.is_set():
                            _buf.clear()
                            _speech_buf.clear()
                            _in_speech = False
                            _silence_count = 0
                            _post_speech_until = _t.time() + _AURORA_POST_SPEECH_SUPPRESS_SEC
                            continue

                        if not _buf:
                            continue

                        # Post-speech suppression: discard audio for a short window
                        # after Aurora finishes talking to avoid picking up reverb.
                        if _t.time() < _post_speech_until:
                            _buf.clear()
                            continue

                        chunk = _np.concatenate([_buf.pop(0) for _ in range(len(_buf))])
                        rms = float(_np.sqrt(_np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0

                        if rms >= _AMBIENT_RMS_THRESHOLD:
                            _in_speech = True
                            _silence_count = 0
                            _speech_buf.append(chunk)
                        elif _in_speech:
                            _silence_count += 1
                            _speech_buf.append(chunk)
                            total_samples = sum(len(c) for c in _speech_buf)

                            end_of_utterance = (
                                _silence_count >= _AMBIENT_SILENCE_FRAMES
                                or total_samples >= _AMBIENT_MAX_SPEECH_SAMP
                            )
                            if end_of_utterance:
                                _in_speech = False
                                _silence_count = 0
                                if total_samples >= _AMBIENT_MIN_SPEECH_SAMP:
                                    _process_utterance(
                                        _np.concatenate(_speech_buf),
                                        _sample_rate,
                                        systems,
                                        _transcribe,
                                        _speak,
                                        _last_response_time,
                                    )
                                _speech_buf.clear()
            except Exception as _se:
                _set_listener_state(active=False, last_error=str(_se))
                log(f"  [AMBIENT] Ambient stream stopped: {_se}")
                _t.sleep(min(retry_delay, 10.0))
                retry_delay = min(retry_delay * 2.0, 30.0)

    def _process_utterance(audio_arr, sample_rate, systems, transcribe_fn, speak_fn, last_resp):
        import time as _t
        try:
            import speech_recognition as _sr
            import numpy as _np
            # Convert float32 PCM → int16 AudioData
            pcm16 = (_np.clip(audio_arr, -1.0, 1.0) * 32767).astype(_np.int16).tobytes()
            audio_data = _sr.AudioData(pcm16, sample_rate, 2)
            text = transcribe_fn(audio_data).strip()
        except Exception:
            return

        if not text:
            return

        role = _classify_ambient(text)

        # Always note the environmental context in working memory (passive)
        try:
            wm = systems.get("working_memory")
            if wm is not None and hasattr(wm, "note_user_facts"):
                wm.note_user_facts(f"[ambient:{role}] {text}")
        except Exception:
            pass

        if role == 'direct':
            # Cooldown check
            now = _t.time()
            if now - last_resp["t"] < _AMBIENT_COOLDOWN_SEC:
                return
            if _in_quiet_window() or _is_quiet_mode():
                return

            # Let Aurora's pipeline decide if this warrants a response
            try:
                from aurora_voice import _generate_response as _gen_resp
                response_text, tone = _gen_resp(text, systems)
            except Exception:
                return

            if not response_text:
                return

            last_resp["t"] = _t.time()
            log(f"  [AMBIENT] Responding to: {text[:60]!r}")
            # Record last voice command so hub can display it
            try:
                import time as _tv
                systems["_last_voice_command"] = {
                    "command": text[:120],
                    "time": _tv.strftime("%H:%M:%S"),
                    "role": role,
                }
            except Exception:
                pass
            try:
                _aurora_speaking_evt.set()
                spoken = bool(speak_fn(response_text, systems, tone=tone))
                if spoken:
                    log("  [AMBIENT] Response spoken.")
                else:
                    log("  [AMBIENT] Response generation succeeded but playback failed.")
            except Exception:
                log("  [AMBIENT] Response playback raised an exception.")
            finally:
                _aurora_speaking_evt.clear()

    t = _threading_ambient.Thread(
        target=_ambient_loop,
        daemon=True,
        name="aurora-ambient-listener",
    )
    t.start()
    return t


def _away_mode_active() -> bool:
    """Return True if away mode is currently active."""
    try:
        if not _AWAY_MODE_FILE.exists():
            return False
        data = json.loads(_AWAY_MODE_FILE.read_text())
        return bool(data.get("active", False))
    except Exception:
        return False


def _away_mode_interval() -> int:
    """Return away mode social interval in seconds (default 30 min)."""
    try:
        data = json.loads(_AWAY_MODE_FILE.read_text())
        return int(data.get("interval_minutes", 30)) * 60
    except Exception:
        return 1800


def _document_session_learnings(systems: Dict[str, Any], exchanges: list, topic: Optional[str] = None) -> None:
    """
    After a GPT social session, extract what was learned and write a
    structured record to social_learning_log.json.  Also immediately
    triggers an OETS study cycle so the new knowledge is applied.
    """
    dt = systems.get("dream_trainer")
    chamber = systems.get("chamber")

    # Gather top fail dimensions (what Aurora is weakest on)
    top_fails: list = []
    try:
        if dt is not None:
            top_fails = [(d, float(s)) for d, s in dt.ledger.get_top_fails(5)]
    except Exception:
        pass

    # Count new genealogy links since session start
    link_count: int = 0
    try:
        if chamber is not None:
            gen = getattr(chamber, "_genealogy", None)
            if gen is not None:
                link_count = int(getattr(gen, "link_count", 0) or len(getattr(gen, "links", {}) or {}))
    except Exception:
        pass

    # Extract OETS new entries (rough proxy: count entries in oets web file)
    oets_count: int = 0
    try:
        for oets_path in _resolve_oets_web_paths():
            if not oets_path.exists():
                continue
            try:
                raw = json.loads(oets_path.read_text())
            except Exception:
                continue
            if isinstance(raw, dict):
                relations = raw.get("relations")
                nodes = raw.get("nodes")
                if isinstance(relations, dict):
                    oets_count = len(relations)
                elif isinstance(nodes, dict):
                    oets_count = len(nodes)
                else:
                    oets_count = len(raw)
            elif isinstance(raw, list):
                oets_count = len(raw)
            break
    except Exception:
        pass

    # Build a readable lesson summary from the exchange content
    lesson_lines: List[str] = []
    for i, ex in enumerate(exchanges[-6:], 1):   # last 6 exchanges
        aurora_snippet = str(ex.get("aurora", ""))[:200]
        gpt_snippet    = str(ex.get("gpt",    ""))[:200]
        stance = str(ex.get("stance", ""))
        degree = float(ex.get("gradient_degree", 0.0))
        lesson_lines.append(f"  Turn {i}:" + (f"  [gradient: {stance} {degree:.2f}]" if stance and stance != "neutral" else ""))
        lesson_lines.append(f"    Aurora: {aurora_snippet}")
        lesson_lines.append(f"    GPT:    {gpt_snippet}")

    record = {
        "timestamp": time.time(),
        "timestamp_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic or "autonomous",
        "turns": len(exchanges),
        "top_fail_dims": top_fails,
        "genealogy_links": link_count,
        "oets_entries": oets_count,
        "lesson_summary": "\n".join(lesson_lines),
        "source": "away_mode" if _away_mode_active() else "on_demand",
    }

    # Append to rolling log (keep last 50 sessions)
    try:
        existing: list = []
        if _SOCIAL_LEARN_LOG.exists():
            try:
                existing = json.loads(_SOCIAL_LEARN_LOG.read_text())
            except Exception:
                existing = []
        if not isinstance(existing, list):
            existing = []
        existing.append(record)
        _SOCIAL_LEARN_LOG.write_text(json.dumps(existing[-50:], indent=2))
    except Exception:
        pass

    # Daemon log summary
    fail_str = ", ".join(f"{d}:{s:.2f}" for d, s in top_fails[:3]) if top_fails else "none"
    _log(f"  [SOCIAL-LEARN] Session logged. topic={record['topic']} "
         f"turns={record['turns']} links={link_count} oets={oets_count} "
         f"top_fails=[{fail_str}]")

    # Apply learnings immediately — run OETS study cycle so knowledge feeds back
    try:
        _run_study_cycle(systems)
        executed_task = True
        _log("  [SOCIAL-LEARN] Applied: OETS study cycle ran to integrate session learnings.")
    except Exception as _e:
        _log(f"  [SOCIAL-LEARN] OETS apply error: {_e}")


def _run_socialize(systems: Dict[str, Any], turns: int = 8, topic: Optional[str] = None) -> None:
    """Run a GPT learning session on demand."""
    _log(f"  [SOCIAL] socialize — {turns} turns" + (f", topic={topic}" if topic else ""))
    try:
        from aurora_gpt_learning_session import run_learning_session

        def _gen(prompt_text, source="socialize"):
            if not prompt_text or len(str(prompt_text).split()) < 3:
                return None
            try:
                from aurora import process_external_user_turn
                result = process_external_user_turn(
                    systems,
                    str(prompt_text),
                    source_label=f"aurora:{source}",
                    session_id="socialize",
                    auto_search_enabled=False,
                    record_exchange=False,
                    update_interactive_state=False,
                    track_evolutionary_trace=True,
                    run_periodic_maintenance=True,
                    mode_name="AGENTIC",
                )
                return result.get("resp_A") if isinstance(result, dict) else None
            except Exception as e:
                _log(f"  [SOCIAL] generator error: {e}")
                return None

        systems["_generate_fn"] = _gen
        exchanges = run_learning_session(systems, n_turns=turns, topic=topic, verbose=True)
        # Document and apply what was learned
        _document_session_learnings(systems, exchanges or [], topic=topic)
    except Exception as e:
        _log(f"  [SOCIAL] socialize error: {e}")
    finally:
        systems.pop("_generate_fn", None)


def _run_distillation_cycle(systems: Dict[str, Any], force: bool = False) -> None:
    """Compress temporal residue into coherent structures and preserved summaries."""
    try:
        from aurora_metabolic_distiller import run_distillation_cycle

        telemetry = run_distillation_cycle(force=force, logger=_log)
        if telemetry.get("status") == "distilled":
            _log(
                "  [DISTILL] Telemetry: "
                f"bytes={int(telemetry.get('bytes_purged', 0) or 0)} "
                f"crystals={int(telemetry.get('crystals_formed', 0) or 0)} "
                f"vortices={int(telemetry.get('vortex_count', 0) or 0)} "
                f"knots={int(telemetry.get('knot_count', 0) or 0)}"
            )
        else:
            _log(
                "  [DISTILL] Skipped: "
                f"{telemetry.get('summary', 'idle')}"
            )
    except Exception as e:
        _log(f"  [DISTILL] error: {e}")


def _run_restore_distillation_cycle(systems: Dict[str, Any], run_id: Optional[str] = None) -> None:
    """Restore the latest or specified distillation archive back into live residue."""
    try:
        from aurora_metabolic_distiller import restore_distillation_cycle

        telemetry = restore_distillation_cycle(run_id=run_id, logger=_log)
        _log(
            "  [RESTORE] "
            f"status={telemetry.get('status', '?')} "
            f"run={telemetry.get('restored_run_id', '') or run_id or 'latest'}"
        )
    except Exception as e:
        _log(f"  [RESTORE] error: {e}")


def _check_daemon_cmd(
    systems: Dict[str, Any],
    *,
    governor: Any = None,
    heat: str = "medium",
    quiet: bool = False,
    state_write_lock: bool = False,
) -> None:
    """Check for a pending command file and execute it."""
    if not _CMD_FILE.exists():
        return
    try:
        raw = _CMD_FILE.read_text(encoding="utf-8").strip()
        _CMD_FILE.unlink(missing_ok=True)
        cmd = json.loads(raw)
    except Exception:
        try:
            _CMD_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return
    name = str(cmd.get("cmd", "")).lower().strip()

    task_name = {
        "socialize": "away_social",
        "gpt": "away_social",
        "learn": "away_social",
        "dream": "dream",
        "study": "study",
        "distill": "distill",
        "restore_distill": "distill",
        "restore_distillation": "distill",
        "undistill": "distill",
    }.get(name, "")
    if governor is not None and task_name:
        try:
            decision = governor.evaluate_task(
                task_name,
                systems,
                heat=heat,
                quiet=quiet,
                state_write_lock=state_write_lock,
            )
            systems["_runtime_governor_status"] = governor.status()
            if not decision.get("allowed", False):
                _log(
                    "  [CMD] Manual override against runtime budget: "
                    f"{name} reason={decision.get('reason', '?')} "
                    f"score={float(decision.get('score', 0.0) or 0.0):.2f}/"
                    f"{float(decision.get('floor', 0.0) or 0.0):.2f}"
                )
        except Exception as e:
            _log(f"  [CMD] Governor evaluation error: {e}")

    executed_task = False

    if name in ("socialize", "gpt", "learn"):
        turns = int(cmd.get("turns", 8))
        topic = cmd.get("topic") or None
        _run_socialize(systems, turns=turns, topic=topic)
        executed_task = True
    elif name in ("away_on", "leaving", "go socialize"):
        interval = int(cmd.get("interval_minutes", 30))
        _AWAY_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _AWAY_MODE_FILE.write_text(json.dumps({
            "active": True,
            "interval_minutes": interval,
            "started_at": time.time(),
        }))
        _log(f"  [AWAY] Away mode ON — GPT sessions every {interval}min.")
    elif name in ("away_off", "back", "im back"):
        _AWAY_MODE_FILE.write_text(json.dumps({"active": False}))
        _log("  [AWAY] Away mode OFF — welcome back.")
    elif name == "dream":
        _run_dream_burst(systems)
        executed_task = True
    elif name in ("dream_force_shards", "force_shards", "shards"):
        _run_force_shard_bridge(systems)
        executed_task = True
    elif name in ("dream_heavy", "heavy_dream"):
        _run_dream_burst_heavy(systems)
        executed_task = True
    elif name == "study":
        _run_study_cycle(systems)
        _poedex_post_study_scan(systems)
        _signal_operator("post_study")
        executed_task = True
    elif name == "distill":
        _run_distillation_cycle(systems, force=True)
        executed_task = True
    elif name in ("restore_distill", "restore_distillation", "undistill"):
        _run_restore_distillation_cycle(systems, run_id=cmd.get("run_id") or None)
        executed_task = True
    elif name in ("quiet", "silence", "mute"):
        _set_quiet_mode(True)
    elif name in ("unquiet", "unmute", "voice", "speak"):
        _set_quiet_mode(False)
    elif name == "chat":
        # Hub text input — route through Aurora's gateway, write response back.
        user_text = str(cmd.get("text", "")).strip()
        if user_text:
            try:
                reply_text = ""
                if _surface_daemon_alive():
                    turn_id = _queue_surface_turn(user_text, source="hub_chat")
                    surface_data = _await_surface_turn(turn_id, timeout_s=45.0)
                    if surface_data and str(surface_data.get("status", "ok") or "ok") != "error":
                        reply_text = str(surface_data.get("response_text", "") or "")
                    elif surface_data:
                        reply_text = str(surface_data.get("error", "surface daemon failed") or "surface daemon failed")

                if not reply_text:
                    aurora_obj = systems.get("aurora")
                    gw = getattr(aurora_obj, "gateway", None)
                    if gw is not None:
                        from aurora_governance_persistence_gateway import StreamType
                        from foundational_contract import ExistenceMode
                        resp = gw.receive(
                            content=user_text,
                            stream_type=StreamType.USER_INPUT,
                            source="hub_chat",
                            mode=ExistenceMode.BOUNDED,
                        )
                        if resp:
                            reply_text = (
                                getattr(resp, "content", None)
                                or getattr(resp, "text", None)
                                or str(resp)
                            )

                if reply_text:
                    # Write response for hub to read
                    _STATE_DIR.mkdir(exist_ok=True)
                    tmp = str(_HUB_RESPONSE) + ".tmp"
                    with open(tmp, "w") as _fh:
                        json.dump({
                            "input":     user_text,
                            "response":  reply_text,
                            "ts":        time.time(),
                            "quiet":     _is_quiet_mode(),
                        }, _fh)
                    os.replace(tmp, str(_HUB_RESPONSE))
                    _log(f"  [HUB] Chat response written ({len(reply_text)} chars)")
                    # Speak unless quiet mode
                    if reply_text and not _is_quiet_mode():
                        _speak(reply_text, systems, tone="warm")
            except Exception as e:
                _log(f"  [HUB] Chat error: {e}")
    else:
        _log(f"  [CMD] Unknown command: {name!r}")

    if governor is not None and task_name and executed_task:
        try:
            governor.note_task_run(task_name)
            systems["_runtime_governor_status"] = governor.status()
        except Exception:
            pass


def _process_room_commands(
    systems: Dict[str, Any],
    *,
    governor: Any = None,
    heat: str = "medium",
    quiet: bool = False,
    state_write_lock: bool = False,
) -> None:
    """
    Read Aurora's room command queue (aurora_room_state.json) and execute
    pending intentions. Commands are written by aurora_room.py and consumed
    here — same tick authority as any other daemon command.

    Supported command types:
      set_overlay          — write governor_sweep_overlay.json
      queue_sweep          — run parameter sweep in background
      approve_proposal     — apply a QuasiArch code proposal
      reverse_proposal     — revert a previously-applied code change
      set_intention        — log and acknowledge an intention
      message_to_sunni     — append to aurora_room_messages.json for Sunni to read
      start_corpus_training — spawn corpus_runner.py in background
      stop_corpus_training  — kill running corpus_runner if any
      dream                — queue a dream burst
      study                — queue a study cycle
      distill              — queue a distillation cycle
    """
    if not _ROOM_STATE.exists():
        return
    try:
        state = json.loads(_ROOM_STATE.read_text())
    except Exception:
        return

    pending: List[Dict] = state.get("pending", [])
    if not pending:
        return

    executed: List[Dict] = []
    remaining: List[Dict] = []

    for cmd in pending:
        cmd_type = str(cmd.get("type", "")).lower()
        payload  = cmd.get("payload", {})
        cmd_ts   = float(cmd.get("ts", 0.0))

        # Drop commands older than 5 minutes (stale queue protection)
        if time.time() - cmd_ts > 300:
            _log(f"  [ROOM] Dropping stale command: {cmd_type!r} (age={int(time.time()-cmd_ts)}s)")
            continue

        try:
            if cmd_type == "set_overlay":
                overlay_path = _STATE_DIR / "governor_sweep_overlay.json"
                overlay = {
                    "active":           True,
                    "n_floor_override": float(payload.get("n_floor", 0.10)),
                    "maintenance_mult": float(payload.get("maint_mult", 0.10)),
                    "heat_hint":        str(payload.get("heat", "NORMAL")),
                    "written_at":       time.time(),
                    "written_by":       "aurora_room",
                }
                overlay_path.write_text(json.dumps(overlay, indent=2))
                _log(f"  [ROOM] Overlay applied: n_floor={overlay['n_floor_override']:.3f} "
                     f"maint={overlay['maintenance_mult']:.3f} heat={overlay['heat_hint']}")

            elif cmd_type == "clear_overlay":
                overlay_path = _STATE_DIR / "governor_sweep_overlay.json"
                overlay_path.write_text(json.dumps({"active": False, "written_at": time.time()}))
                _log("  [ROOM] Overlay cleared.")

            elif cmd_type == "queue_sweep":
                window = int(payload.get("window_secs", 90))
                dry    = bool(payload.get("dry_run", False))
                args   = ["python3", str(_BASE_DIR / "quasiarch_diag.py"), "--sweep",
                          "--sweep-window", str(window), "--quiet"]
                if dry:
                    args.append("--sweep-dry-run")
                subprocess.Popen(args, cwd=str(_BASE_DIR),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _log(f"  [ROOM] Sweep queued: window={window}s dry={dry}")

            elif cmd_type == "message_to_sunni":
                content = str(payload.get("content", "")).strip()
                if content:
                    msgs: List[Dict] = []
                    if _ROOM_MSGS.exists():
                        try:
                            msgs = json.loads(_ROOM_MSGS.read_text())
                            if not isinstance(msgs, list):
                                msgs = []
                        except Exception:
                            msgs = []
                    msgs.append({
                        "from":    "aurora",
                        "content": content,
                        "ts":      time.time(),
                        "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
                        "read":    False,
                    })
                    msgs = msgs[-200:]
                    _ROOM_MSGS.write_text(json.dumps(msgs, indent=2))
                    _log(f"  [ROOM] Message from Aurora: {content[:80]}")
                    # If not quiet, speak it aloud so Sunni hears it
                    if not quiet and not _in_quiet_window():
                        _speak(content, systems, tone="warm")

            elif cmd_type == "set_intention":
                content = str(payload.get("content", "")).strip()
                _log(f"  [ROOM] Aurora's intention: {content[:100]}")
                # Write to messages as an intention so Sunni sees it
                if content:
                    msgs: List[Dict] = []
                    if _ROOM_MSGS.exists():
                        try:
                            msgs = json.loads(_ROOM_MSGS.read_text())
                            if not isinstance(msgs, list):
                                msgs = []
                        except Exception:
                            msgs = []
                    msgs.append({
                        "from":    "aurora",
                        "type":    "intention",
                        "content": content,
                        "ts":      time.time(),
                        "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
                        "read":    False,
                    })
                    msgs = msgs[-200:]
                    _ROOM_MSGS.write_text(json.dumps(msgs, indent=2))

            elif cmd_type == "approve_proposal":
                proposal = dict(payload.get("proposal") or {})
                proposal_id = str(
                    payload.get("proposal_id")
                    or proposal.get("proposal_id")
                    or proposal.get("id")
                    or proposal.get("issue_archetype")
                    or ""
                )
                _log(f"  [ROOM] Aurora approved proposal: {proposal_id}")
                if not proposal_id:
                    _log("  [ROOM] Proposal approval skipped: missing proposal id")
                else:
                    # Delegate to QuasiArch enforcer bridge if available.
                    # Surface Aurora authorizes; subsurface executes the exact apply.
                    try:
                        bridge_path = _BASE_DIR / "quasiarch_bridge.py"
                        if bridge_path.exists():
                            subprocess.Popen(
                                ["python3", str(bridge_path), "--apply", proposal_id],
                                cwd=str(_BASE_DIR),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            )
                    except Exception as e:
                        _log(f"  [ROOM] Proposal approval failed: {e}")

            elif cmd_type == "reverse_proposal":
                proposal = dict(payload.get("proposal") or {})
                proposal_id = str(
                    payload.get("proposal_id")
                    or proposal.get("proposal_id")
                    or proposal.get("id")
                    or proposal.get("issue_archetype")
                    or ""
                )
                _log(f"  [ROOM] Aurora requested revert: {proposal_id}")
                if not proposal_id:
                    _log("  [ROOM] Proposal revert skipped: missing proposal id")
                else:
                    try:
                        bridge_path = _BASE_DIR / "quasiarch_bridge.py"
                        if bridge_path.exists():
                            subprocess.Popen(
                                ["python3", str(bridge_path), "--revert", proposal_id],
                                cwd=str(_BASE_DIR),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            )
                    except Exception as e:
                        _log(f"  [ROOM] Proposal revert failed: {e}")

            elif cmd_type == "start_corpus_training":
                corpus_path = str(payload.get("corpus_path",
                                              str(_BASE_DIR / "conversations.json")))
                passes_arg  = str(payload.get("passes", "triple"))
                batch_limit = int(payload.get("batch_limit", 5000))
                # Kill any existing corpus_runner first
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", "corpus_runner.py"], capture_output=True, text=True
                    )
                    for pid_str in result.stdout.strip().split():
                        try:
                            os.kill(int(pid_str), 15)
                        except Exception:
                            pass
                    time.sleep(1)
                except Exception:
                    pass
                # Launch fresh corpus runner
                proc = subprocess.Popen(
                    ["python3", str(_BASE_DIR / "corpus_runner.py"),
                     "--corpus", corpus_path,
                     "--passes", passes_arg,
                     "--batch-limit", str(batch_limit)],
                    cwd=str(_BASE_DIR),
                    stdout=open(str(_STATE_DIR / "corpus_output.log"), "a"),
                    stderr=subprocess.STDOUT,
                )
                _log(f"  [ROOM] Corpus training started: pid={proc.pid} "
                     f"corpus={corpus_path} passes={passes_arg}")

            elif cmd_type == "stop_corpus_training":
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", "corpus_runner.py"], capture_output=True, text=True
                    )
                    killed = 0
                    for pid_str in result.stdout.strip().split():
                        try:
                            os.kill(int(pid_str), 15)
                            killed += 1
                        except Exception:
                            pass
                    _log(f"  [ROOM] Corpus training stopped (killed {killed} process(es)).")
                except Exception as e:
                    _log(f"  [ROOM] Stop corpus training error: {e}")

            elif cmd_type in ("dream", "study", "distill"):
                # Delegate to existing _check_daemon_cmd flow via systems cmd file
                _CMD_FILE.write_text(json.dumps({"cmd": cmd_type}))
                _log(f"  [ROOM] Aurora queued: {cmd_type}")

            else:
                _log(f"  [ROOM] Unknown command type: {cmd_type!r}")

            executed.append(cmd)

        except Exception as e:
            _log(f"  [ROOM] Error processing {cmd_type!r}: {e}")
            executed.append(cmd)  # mark as consumed regardless

    # Write back only unprocessed commands (should be empty after a full pass)
    state["pending"]        = remaining
    state["last_processed"] = time.time()
    try:
        _ROOM_STATE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def _deliver_boot_greeting(systems: Dict[str, Any]) -> None:
    if VOICE_MODE in {"off", "disabled", "none"}:
        return
    if not BOOT_GREETING_ENABLED or _in_quiet_window() or _is_quiet_mode():
        return
    try:
        from aurora_voice import daemon_startup_greeting

        daemon_startup_greeting(systems)
        _log("  [VOICE] Startup greeting delivered.")
    except Exception as e:
        _log(f"  [VOICE] Startup greeting skipped: {e}")


_SLEEP_AUDIO_LOG = _STATE_DIR / "sleep_audio_log.json"
_SLEEP_AUDIO_SAMPLE_INTERVAL = 300   # sample ambient audio every 5 minutes during sleep


def _sample_sleep_ambient_audio(systems: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    While Surface is asleep, read ambient audio and feed it into the sensory
    crystal as an audio-only observation. Query any cross-modal associations to
    generate a visual prediction — what the crystal *imagines* it would be seeing
    based on learned audio↔visual bindings.

    This is how Aurora fills in the gaps: camera off, but sound tells her
    something about the scene, and she uses what she knows to picture it.
    """
    ambient_path = _STATE_DIR / "ambient_audio_latest.json"
    if not ambient_path.exists():
        return None

    try:
        age = time.time() - ambient_path.stat().st_mtime
        if age > 60.0:
            return None
        payload = json.loads(ambient_path.read_text())
        if not isinstance(payload, dict):
            return None
    except Exception:
        return None

    activity = str(payload.get("activity", "ambient") or "ambient")
    rms_db = float(payload.get("rms_db", -60.0) or -60.0)

    # Build a synthetic audio dict compatible with audio_dict_to_crystal_20d
    rms_norm = max(0.0, min(1.0, (rms_db + 60.0) / 40.0))   # map -60→0dB to 0→1
    audio_dict = {
        "rms": rms_norm,
        "volume": rms_norm,
        "category": "speech" if activity == "speech" else ("noise" if activity == "noise" else "ambient"),
        "features": {
            "rms": rms_norm,
            "zcr": 0.3 if activity == "speech" else 0.1,
            "harmonicity": 0.45 if activity == "speech" else 0.1,
            "onset_density": rms_norm * 0.6,
        },
    }

    # Convert to 20d crystal vector and feed as audio-only observation
    visual_prediction = ""
    try:
        from aurora_internal.aurora_sensory_crystal import audio_dict_to_crystal_20d
        audio_20d = audio_dict_to_crystal_20d(audio_dict)
        sc = systems.get("sensory_crystal")
        if sc is not None:
            sc.observe_frame(
                audio_20d,
                [0.0] * 57,        # no vision — camera is off
                session_id=f"sleep_{int(time.time())}",
                audio_conf=0.6,
                visual_conf=0.0,
            )
            # Query cross-modal matches: what visual pattern does this audio predict?
            last_matches = getattr(sc, "_last_matches", {})
            sem_matches = dict((last_matches or {}).get("semantic") or {})
            if sem_matches:
                # Find highest-fitness semantic match
                best = max(sem_matches.items(), key=lambda x: float(x[1] or 0.0), default=None)
                if best:
                    sem_node_id = best[0]
                    sem_node = (getattr(sc, "_semantic", {}) or {}).get(sem_node_id)
                    if sem_node is not None:
                        visual_prediction = str(getattr(sem_node, "summary", "") or getattr(sem_node, "label", "") or "")
    except Exception:
        pass

    observation = {
        "ts": time.time(),
        "ts_str": time.strftime("%H:%M:%S"),
        "activity": activity,
        "rms_db": round(rms_db, 2),
        "visual_prediction": visual_prediction,
    }

    # Append to rolling sleep audio log
    try:
        existing: List[Dict[str, Any]] = []
        if _SLEEP_AUDIO_LOG.exists():
            try:
                raw = json.loads(_SLEEP_AUDIO_LOG.read_text())
                if isinstance(raw, list):
                    existing = raw
            except Exception:
                existing = []
        existing.append(observation)
        existing = existing[-48:]   # keep at most 4h of 5-min samples
        tmp = str(_SLEEP_AUDIO_LOG) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(existing, _f, indent=2)
        os.replace(tmp, str(_SLEEP_AUDIO_LOG))
    except Exception:
        pass

    return observation


def _build_sleep_dream_context(systems: Dict[str, Any]) -> Dict[str, Any]:
    """
    Before the dream burst fires, synthesize what was heard and imagined during
    sleep into a context packet the dream can draw on.
    """
    try:
        observations: List[Dict[str, Any]] = []
        if _SLEEP_AUDIO_LOG.exists():
            raw = json.loads(_SLEEP_AUDIO_LOG.read_text())
            if isinstance(raw, list):
                observations = raw
    except Exception:
        observations = []

    if not observations:
        return {}

    # Summarise: dominant activity, whether there was speech, any visual predictions
    activities = [str(o.get("activity", "") or "") for o in observations]
    predictions = [str(o.get("visual_prediction", "") or "") for o in observations if o.get("visual_prediction")]
    speech_count = sum(1 for a in activities if a == "speech")
    noise_count = sum(1 for a in activities if a in ("noise", "active"))

    environment_desc = "silence"
    if speech_count > len(observations) * 0.3:
        environment_desc = "intermittent speech in the environment"
    elif noise_count > len(observations) * 0.4:
        environment_desc = "active ambient noise"
    elif any(a in ("active", "noise", "speech") for a in activities):
        environment_desc = "light ambient activity"

    context = {
        "generated_at": time.time(),
        "samples": len(observations),
        "environment": environment_desc,
        "speech_detected": speech_count > 0,
        "visual_predictions": list(dict.fromkeys(p for p in predictions if p))[:4],
        "summary": f"While sleeping, I was in an environment of {environment_desc}.",
    }
    if predictions:
        context["summary"] += f" My senses imagined: {predictions[0]}."

    # Write so systems can access it
    try:
        tmp = str(_STATE_DIR / "sleep_dream_context.json") + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(context, _f, indent=2)
        os.replace(tmp, str(_STATE_DIR / "sleep_dream_context.json"))
    except Exception:
        pass

    systems["_sleep_dream_context"] = context
    return context


def _tick_sleep_cycle(systems: Dict[str, Any], surface_awake_since: List[float]) -> None:
    """
    Manage Aurora's sleep/wake cycle from the Subsurface layer.

    Subsurface owns the organism's clock. Surface obeys.

    Schedule: 8 hours awake → 2 hours asleep (with dream burst) → repeat.

    surface_awake_since is a mutable single-element list used as a closure
    reference so the value survives across loop iterations.
    """
    try:
        from aurora_internal.dual_strata.sleep_cycle import (
            enter_sleep,
            exit_sleep,
            is_sleeping,
            mark_dream_triggered,
            read_sleep_state,
        )
    except Exception:
        return

    now = time.time()
    state = read_sleep_state(_STATE_DIR)
    currently_sleeping = bool(state.get("sleeping", False))

    if currently_sleeping:
        wake_at = float(state.get("wake_at", 0.0) or 0.0)

        # Sample ambient audio every 5 minutes during sleep.
        # Ambient listener thread is still running — we just read what it captured.
        # Feed audio into the crystal and generate visual predictions from
        # learned cross-modal associations (her system fills in the gaps).
        last_audio_sample = float(systems.get("_sleep_last_audio_sample", 0.0) or 0.0)
        if (now - last_audio_sample) >= _SLEEP_AUDIO_SAMPLE_INTERVAL:
            obs = _sample_sleep_ambient_audio(systems)
            if obs:
                _log(
                    f"  [SLEEP] Audio: {obs.get('activity', '?')} "
                    f"{obs.get('rms_db', 0):.1f}dB"
                    + (f" → imagined: {obs['visual_prediction'][:60]}" if obs.get("visual_prediction") else "")
                )
            systems["_sleep_last_audio_sample"] = now

        # Fire dream burst once per sleep period — build context from what was heard first.
        if not bool(state.get("dream_triggered", False)):
            _log("  [SLEEP] Building dream context from sleep audio observations.")
            ctx = _build_sleep_dream_context(systems)
            if ctx.get("summary"):
                _log(f"  [SLEEP] Dream context: {ctx['summary'][:100]}")
            _log("  [SLEEP] Firing dream burst.")
            try:
                _run_dream_burst(systems)
                mark_dream_triggered(_STATE_DIR)
            except Exception as exc:
                _log(f"  [SLEEP] Dream burst error: {exc}")
            # Clear the sleep audio log after the dream consumes it
            try:
                _SLEEP_AUDIO_LOG.unlink(missing_ok=True)
            except Exception:
                pass

        # Time to wake up?
        if now >= wake_at:
            exit_sleep(_STATE_DIR)
            surface_awake_since[0] = now
            systems.pop("_sleep_last_audio_sample", None)
            _log("  [SLEEP] Sleep period ended — Surface waking.")
            try:
                _save_message("I'm waking up.", trigger="sleep_wake")
            except Exception:
                pass

    else:
        # Are we due for sleep?
        awake_for = now - surface_awake_since[0]
        if awake_for >= SLEEP_AWAKE_DURATION:
            wake_at = enter_sleep(_STATE_DIR, duration_s=SLEEP_DURATION)
            wake_str = time.strftime("%H:%M", time.localtime(wake_at))
            _log(f"  [SLEEP] Entering sleep period — Surface dormant until {wake_str}.")
            try:
                _save_message(f"Going to sleep. I'll be back around {wake_str}.", trigger="sleep_enter")
            except Exception:
                pass


def _consume_surface_continuity_feed(systems: Dict[str, Any]) -> None:
    """
    Read and integrate any continuity packets Surface deposited since the last cycle.

    Core architectural law: Surface translates present experience into subsurface
    continuity. This is the receiving end of that handoff — Subsurface consuming
    what Surface gathered while awake and integrating it into the organism's
    ongoing continuity state.

    Without this, Surface output is theatrical. With this, every awake moment
    actually changes the deeper system.
    """
    try:
        from aurora_internal.dual_strata.surface_continuity_feed import read_and_clear_continuity_packets
        packets = read_and_clear_continuity_packets(_STATE_DIR)
    except Exception:
        return
    if not packets:
        return

    integration_log_path = _STATE_DIR / "subsurface_continuity_log.json"
    log_entries: List[Dict[str, Any]] = []
    try:
        if integration_log_path.exists():
            raw = json.loads(integration_log_path.read_text())
            if isinstance(raw, list):
                log_entries = raw
    except Exception:
        log_entries = []

    for packet in packets:
        if not isinstance(packet, dict):
            continue

        packet_id = str(packet.get("packet_id", "") or "")
        user_input = str(packet.get("user_input", "") or "")
        aurora_response = str(packet.get("aurora_response", "") or "")
        concepts = list(packet.get("concepts_activated") or [])
        dominant_axis = str(packet.get("dominant_axis", "") or "")
        coherence = float(packet.get("coherence", 0.0) or 0.0)
        felt_wrong = bool(packet.get("felt_wrong", False))
        unresolved = list(packet.get("unresolved_tensions") or [])
        resolved = list(packet.get("resolved_bindings") or [])

        # 1. Feed to SediMemory — this is the primary continuity integration target.
        #    SediMemory holds the T-axis (temporal continuity) layer; every real
        #    interaction moment should be ingested here so Subsurface can recall it.
        try:
            _sedi = systems.get("sedimemory")
            if _sedi is not None and hasattr(_sedi, "ingest_event"):
                from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
                from foundational_contract import ExistenceMode

                # Build a constraint vector from the present frame.
                # T is always significant (this is a temporal moment to preserve).
                # The dominant_axis gets elevated weight.
                _axis_weights = {"X": 0.3, "T": 0.7, "N": 0.1, "B": 0.2, "A": 0.1}
                if dominant_axis in _axis_weights:
                    _axis_weights[dominant_axis] = max(_axis_weights[dominant_axis], 0.75)
                if felt_wrong:
                    _axis_weights["X"] = max(_axis_weights["X"], 0.55)
                _cv = ConstraintVector(**_axis_weights)
                _content: Dict[str, Any] = {
                    "type": "surface_interaction",
                    "user_input": user_input[:200],
                    "aurora_response": aurora_response[:400],
                    "coherence": round(coherence, 4),
                    "felt_wrong": felt_wrong,
                    "dominant_axis": dominant_axis,
                }
                if concepts:
                    _content["concepts"] = concepts[:6]
                if unresolved:
                    _content["unresolved"] = unresolved[:3]
                if resolved:
                    _content["resolved"] = resolved[:3]
                _sedi.ingest_event(
                    _content,
                    _cv,
                    source="surface_continuity_handoff",
                    existence_mode=ExistenceMode.PERSISTENT,
                )
        except Exception:
            pass

        # 2. Feed concepts to sensory crystal for passive cross-modal learning.
        #    Concepts Surface activated during the interaction become part of
        #    the sensory pattern bank Subsurface can recall independently.
        try:
            _sc = systems.get("sensory_crystal")
            if _sc is not None and concepts and hasattr(_sc, "ingest_audio"):
                for concept in concepts[:4]:
                    try:
                        _sc.ingest_audio(
                            label=str(concept),
                            features={"source": "surface_continuity", "coherence": coherence},
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. Write to the wrong-signal repair tracker if Surface flagged something.
        #    Subsurface already has a repair signal pathway — use it.
        if felt_wrong:
            try:
                _wrong_reason = str(packet.get("wrong_reason", "") or "")
                _write_subsurface_repair_signal(
                    "recognition",
                    issue=_wrong_reason or "surface_flagged_wrong",
                    reason="surface_continuity_handoff reported felt_wrong",
                    intensity=max(0.3, min(0.8, 1.0 - coherence)),
                )
            except Exception:
                pass

        # 4. Keep the most recent packet accessible to other subsurface systems.
        systems["_last_surface_packet"] = {
            "packet_id": packet_id,
            "consumed_at": time.time(),
            "dominant_axis": dominant_axis,
            "coherence": coherence,
            "felt_wrong": felt_wrong,
            "concepts_count": len(concepts),
            "unresolved_count": len(unresolved),
        }

        # 5. GAP 2 FIX: Feed lived-experience pressure into the evolution chamber.
        #    felt_wrong is constraint pressure; coherence scales magnitude;
        #    unresolved_tensions are the pressure descriptions.
        #    Without this, evolution only sees telemetry and dream-trainer fails —
        #    never the lived surface signal.
        try:
            _chamber = systems.get("chamber")
            if _chamber is not None and hasattr(_chamber, "observe_external_evidence"):
                if felt_wrong:
                    # Map wrong feeling onto X (constraint coherence) and the dominant axis.
                    _wrong_magnitude = max(0.2, min(0.8, 1.0 - coherence))
                    _wrong_axes = dict(_ZERO_AXES)
                    _wrong_axes["X"] = round(_wrong_magnitude * _AXIS_PRESSURE_NORM.get("X", 1.0), 4)
                    if dominant_axis in _wrong_axes:
                        _wrong_axes[dominant_axis] = round(
                            _wrong_magnitude * 0.6 * _AXIS_PRESSURE_NORM.get(dominant_axis, 1.0), 4
                        )
                    _wrong_notes: Dict[str, Any] = {
                        "confidence": _wrong_magnitude,
                        "episode_id": f"surface_felt_wrong_{packet_id[:8]}",
                        "evidence_id": f"surface_wrong_{int(time.time())}",
                        "source": "surface_continuity_felt_wrong",
                    }
                    if unresolved:
                        _wrong_notes["unresolved_tensions"] = unresolved[:3]
                    _chamber.observe_external_evidence({
                        "mutation_name": "surface_felt_wrong",
                        "pressure_before": dict(_ZERO_AXES),
                        "pressure_after": _wrong_axes,
                        "notes": _wrong_notes,
                        "pressure_profile": {"total_confidence": _wrong_magnitude},
                    })
                elif unresolved:
                    # Even without felt_wrong, unresolved tensions are mild A/B pressure.
                    _unres_mag = round(min(0.35, len(unresolved) * 0.08), 4)
                    if _unres_mag >= 0.08:
                        _unres_axes = dict(_ZERO_AXES)
                        _unres_axes["A"] = round(_unres_mag * _AXIS_PRESSURE_NORM.get("A", 0.141), 4)
                        _unres_axes["B"] = round(_unres_mag * _AXIS_PRESSURE_NORM.get("B", 0.236), 4)
                        _chamber.observe_external_evidence({
                            "mutation_name": "surface_unresolved_tensions",
                            "pressure_before": dict(_ZERO_AXES),
                            "pressure_after": _unres_axes,
                            "notes": {
                                "confidence": _unres_mag,
                                "episode_id": f"surface_unresolved_{packet_id[:8]}",
                                "evidence_id": f"surface_unres_{int(time.time())}",
                                "source": "surface_continuity_unresolved",
                                "unresolved_tensions": unresolved[:3],
                            },
                            "pressure_profile": {"total_confidence": _unres_mag},
                        })
        except Exception:
            pass

        # 6. GAP 6 FIX: Feed surface coherence into subsurface pressure tracking.
        #    Low coherence = surface is struggling → register as pressure signal.
        #    High coherence = surface is fluid → register as relief.
        #    Without this, subsurface is pressure-blind to surface's actual state.
        try:
            if coherence < 0.4:
                # Surface is struggling — register as X-axis constraint pressure.
                _coh_pressure = round((0.4 - coherence) * 1.5, 4)  # scale 0→0.6
                _coh_axes = dict(_ZERO_AXES)
                _coh_axes["X"] = round(
                    min(0.55, _coh_pressure) * _AXIS_PRESSURE_NORM.get("X", 1.0), 4
                )
                if dominant_axis in _coh_axes:
                    _coh_axes[dominant_axis] = round(
                        min(0.35, _coh_pressure * 0.5) * _AXIS_PRESSURE_NORM.get(dominant_axis, 1.0), 4
                    )
                _chamber2 = systems.get("chamber")
                if _chamber2 is not None and hasattr(_chamber2, "observe_external_evidence"):
                    _chamber2.observe_external_evidence({
                        "mutation_name": "surface_low_coherence_pressure",
                        "pressure_before": dict(_ZERO_AXES),
                        "pressure_after": _coh_axes,
                        "notes": {
                            "confidence": min(0.7, _coh_pressure),
                            "episode_id": f"surface_coh_{packet_id[:8]}",
                            "evidence_id": f"surface_coh_{int(time.time())}",
                            "source": "surface_coherence_tracking",
                            "coherence": round(coherence, 4),
                        },
                        "pressure_profile": {"total_confidence": min(0.7, _coh_pressure)},
                    })
                # Also persist a pressure signal for the repair-signal pathway.
                try:
                    _write_subsurface_repair_signal(
                        "recognition",
                        issue="surface_low_coherence",
                        reason=f"surface coherence={coherence:.2f} below 0.4 threshold",
                        intensity=round(min(0.6, _coh_pressure), 4),
                    )
                except Exception:
                    pass
            elif coherence > 0.7:
                # Surface is fluid — treat as pressure relief on X axis.
                # We express this as near-zero pressure_after (relief = absence of pressure).
                _relief_mag = round((coherence - 0.7) * 0.5, 4)  # small positive relief signal
                _relief_axes = dict(_ZERO_AXES)
                # Relief is represented as very low pressure — subsurface reads the
                # delta: prior pressure → lower pressure means relief.
                _chamber3 = systems.get("chamber")
                if _chamber3 is not None and hasattr(_chamber3, "observe_external_evidence"):
                    _relief_after = dict(_ZERO_AXES)
                    _relief_after["X"] = round(max(0.0, 0.05 - _relief_mag), 4)
                    _chamber3.observe_external_evidence({
                        "mutation_name": "surface_high_coherence_relief",
                        "pressure_before": {"X": round(min(0.3, _relief_mag * 2), 4),
                                            "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
                        "pressure_after": _relief_after,
                        "notes": {
                            "confidence": round(coherence, 4),
                            "episode_id": f"surface_relief_{packet_id[:8]}",
                            "evidence_id": f"surface_relief_{int(time.time())}",
                            "source": "surface_coherence_tracking",
                            "coherence": round(coherence, 4),
                        },
                        "pressure_profile": {"total_confidence": round(coherence * 0.4, 4)},
                    })
        except Exception:
            pass

        log_entries.append({
            "ts": time.time(),
            "ts_str": time.strftime("%H:%M:%S"),
            "packet_id": packet_id[:12],
            "axis": dominant_axis or "?",
            "coherence": round(coherence, 3),
            "felt_wrong": felt_wrong,
            "concepts": len(concepts),
            "unresolved": len(unresolved),
        })

    # Keep log bounded
    log_entries = log_entries[-200:]
    try:
        tmp = str(integration_log_path) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(log_entries, _f, indent=2)
        os.replace(tmp, str(integration_log_path))
    except Exception:
        pass

    if packets:
        _log(f"  [CONTINUITY] Integrated {len(packets)} surface packet(s) into subsurface continuity.")


def _run_pressure_routing(systems: Dict[str, Any]) -> None:
    """
    Run the pressure adapter first so axis_stats and evolver hints reflect the
    live dispatcher, then route the resulting pressure into growth directives.
    """
    try:
        from aurora_internal.aurora_pressure_adapter import PressureParameterAdapter

        dispatcher = systems.get("_surface_dispatcher")
        if dispatcher is not None:
            adapter = PressureParameterAdapter(str(_BASE_DIR))
            adapt_result = adapter.adapt(dispatcher)
            if adapt_result.get("adapted"):
                applied = dict(adapt_result.get("applied") or {})
                threshold = dict(applied.get("threshold") or {})
                threshold_text = ""
                if threshold:
                    threshold_text = (
                        f" threshold={float(threshold.get('new', 0.0) or 0.0):.3f}"
                    )
                bias_hints = dict(adapt_result.get("bias_hints") or {})
                active_axes = ",".join(sorted(k.upper() for k, v in bias_hints.items() if abs(float(v or 0.0)) >= 0.01))
                _log(
                    "  [ADAPT] Pressure adapter refreshed"
                    f"{threshold_text}"
                    f" axes={active_axes or '-'}"
                )
    except Exception as e:
        _log(f"  [ADAPT] Pressure adapter error: {e}")

    try:
        from aurora_internal.aurora_pressure_router import PressureRouter
        router = PressureRouter(str(_BASE_DIR))
        result = router.route()
        dominant = result.get("dominant_type", "?") if isinstance(result, dict) else "?"
        _log(f"  [PRESSURE] Routed → dominant={dominant}")
    except Exception as e:
        _log(f"  [PRESSURE] Routing error: {e}")


def _run_leverage_relief(systems: Dict[str, Any]) -> None:
    """
    Tick the leverage relief valve — detects overhead-stuck state and redirects
    evolver budget toward B/A axes when X-axis dominates pressure experiences.
    """
    try:
        from aurora_internal.aurora_leverage_relief import tick_leverage_relief
        result = tick_leverage_relief(str(_BASE_DIR))
        action = result.get("action", "?")
        ratio  = result.get("ratio", 0.0)
        net    = result.get("net", 0.0)
        if action == "redirect_active":
            _log(f"  [LEVERAGE] Relief ACTIVE — overhead_ratio={ratio:.2f} net={net:+.1f} "
                 f"(redirecting evolver → B/A axes)")
        elif action == "cleared":
            _log(f"  [LEVERAGE] Relief CLEARED — ratio={ratio:.2f} net={net:+.1f} "
                 f"(overhead pressure normalised)")
        elif action == "idle" and ratio > 0.7:
            _log(f"  [LEVERAGE] Monitoring — overhead_ratio={ratio:.2f} net={net:+.1f}")
    except Exception as e:
        _log(f"  [LEVERAGE] Relief error: {e}")


def _run_sensory_competency_cycle(systems: Dict[str, Any]) -> None:
    """
    Autonomously train visual and audio sensory facets using live capture.
    Feeds current camera frame and ambient audio into SensoryCompetencyEngine
    so sensory understanding grows through continuous observation, not just
    during user turns.
    """
    try:
        sensory = systems.get("sensory") or systems.get("sensory_integration")
        if sensory is None:
            _gw = systems.get("aurora")
            sensory = getattr(getattr(_gw, "perception", None), "sensory", None) if _gw else None
        if sensory is None:
            return

        # Visual training — capture frame and process through facets
        if hasattr(sensory, "process_visual_input"):
            try:
                _sc = systems.get("sensory_crystal")
                _sc_state = _sc.get_state() if (_sc and hasattr(_sc, "get_state")) else {}
                _vis = _sc_state.get("visual", {}) or {}
                if _vis and any(float(v or 0) > 0.0 for v in _vis.values()):
                    sensory.process_visual_input(_vis, mode="observation")
            except Exception:
                pass

        # Audio training — pull from sensory crystal audio lane
        if hasattr(sensory, "process_audio_input"):
            try:
                _sc = systems.get("sensory_crystal")
                _sc_state = _sc.get_state() if (_sc and hasattr(_sc, "get_state")) else {}
                _aud = _sc_state.get("audio", {}) or {}
                if _aud and any(float(v or 0) > 0.0 for v in _aud.values()):
                    sensory.process_audio_input(_aud, mode="observation")
            except Exception:
                pass
    except Exception as _sce:
        _log(f"  [SENSORY-TRAIN] Error: {_sce}")


def _run_corpus_hunt_cycle(systems: Dict[str, Any]) -> None:
    """
    Autonomously hunt for new corpus material when current corpora are exhausted.
    Checks corpus_progress.json — if all passes are done and no new corpus is
    running, launches the corpus_hunter tool to search the web for fresh training
    data, then starts a corpus training run on whatever it finds.
    """
    import json, os, subprocess
    state_dir = str(systems.get("state_dir") or _STATE_DIR)

    # Check if corpus is exhausted
    try:
        cp_path = os.path.join(state_dir, "corpus_progress.json")
        if not os.path.exists(cp_path):
            return
        with open(cp_path) as _f:
            cp = json.load(_f)
        passes = cp.get("passes", {})
        all_done = all(p.get("done", False) for p in passes.values()) if passes else False
        if not all_done:
            return  # corpus still running
    except Exception:
        return

    # Check if corpus_runner is already running
    try:
        _check = subprocess.run(
            ["pgrep", "-f", "corpus_runner.py"],
            capture_output=True, text=True
        )
        if _check.stdout.strip():
            return  # already running
    except Exception:
        pass

    # Use corpus_hunter tool to find new material
    _log("  [CORPUS] Current corpus exhausted — launching autonomous corpus hunt")
    try:
        from aurora_internal.tool_registry import call as _tool_call
        # Determine a study topic from the dream trainer fail ledger
        _topic = "consciousness language cognition"
        try:
            _dt = systems.get("dream_trainer")
            if _dt is not None:
                _fails = getattr(getattr(_dt, "ledger", None), "get_top_fails", lambda n: [])(1)
                if _fails:
                    _topic = str(_fails[0][0]).replace("_", " ")
        except Exception:
            pass

        _hunt_result = _tool_call(
            "corpus_hunter",
            topic=_topic,
            max_results=3,
            systems=systems,
        )
        if _hunt_result and _hunt_result.success:
            _log(f"  [CORPUS] Hunt complete — starting corpus training on new material")
            # Start corpus_runner in background
            _corpus_file = str(_CORPUS_PATH if "_CORPUS_PATH" in dir() else
                               os.path.join(os.path.dirname(str(_BASE_DIR)), "interval_corpus.json"))
            try:
                subprocess.Popen(
                    ["python3", str(_BASE_DIR / "corpus_runner.py"), "--corpus", _corpus_file],
                    cwd=str(_BASE_DIR),
                )
                _log("  [CORPUS] corpus_runner.py started in background")
            except Exception as _cpe:
                _log(f"  [CORPUS] Failed to start corpus_runner: {_cpe}")
        else:
            _log("  [CORPUS] Hunt found no new material this cycle")
    except Exception as _che:
        _log(f"  [CORPUS] Hunt error: {_che}")


def _run_grammar_motif_training(systems: Dict[str, Any]) -> None:
    """
    Autonomously build grammar motifs when the SIC has none promoted.
    Runs a mini training burst through the simulation engine — the same
    path as /train but triggered by the daemon when the expression layer
    has zero sentence structure to work with.
    """
    import json, os
    state_dir = str(systems.get("state_dir") or _STATE_DIR)
    motif_path = os.path.join(state_dir, "grammar_motifs.json")
    try:
        if os.path.exists(motif_path):
            with open(motif_path) as _mf:
                _md = json.load(_mf)
            if len(_md.get("promoted", [])) >= 5:
                return  # enough motifs already
    except Exception:
        pass

    try:
        _gw = systems.get("aurora")
        _sim = getattr(getattr(_gw, "gateway", None), "simulation", None) if _gw else None
        if _sim is None:
            _sim = systems.get("simulation")
        _ExistenceMode = systems.get("ExistenceMode")
        if _sim is None or _ExistenceMode is None:
            return
        _log("  [GRAMMAR] Motifs depleted — running autonomous training burst (8 epochs)")
        for _ep_i in range(8):
            try:
                _sim.run_epoch(
                    episodes_per_epoch=6,
                    turns_per_episode=5,
                    mode=_ExistenceMode.AGENTIC,
                )
            except Exception as _ep_e:
                _log(f"  [GRAMMAR] Epoch {_ep_i} error: {_ep_e}")
                break
        # Save updated grammar state
        try:
            _aurora_gw = systems.get("aurora")
            if _aurora_gw is not None and hasattr(_aurora_gw, "save_state"):
                _aurora_gw.save_state()
        except Exception:
            pass
        _log("  [GRAMMAR] Autonomous training burst complete")
    except Exception as _gte:
        _log(f"  [GRAMMAR] Training error: {_gte}")


def run(systems: Dict[str, Any]) -> None:
    _log("Aurora daemon started.")
    from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor

    # Track next fire times (absolute epoch seconds)
    now = time.time()
    next_study   = now + _jitter(STUDY_INTERVAL)
    next_dream   = now + _jitter(DREAM_INTERVAL, 0.25)
    next_browser = now + _jitter(BROWSER_INTERVAL, 0.40)
    next_save    = now + SAVE_INTERVAL
    next_distill = now + _jitter(DISTILL_INTERVAL, 0.25)
    next_grammar_train     = now + 120    # first grammar check after 2 minutes
    next_sensory_train     = now + 60     # sensory competency first pass after 1 minute
    next_corpus_hunt       = now + 300    # corpus exhaustion check after 5 minutes
    next_reach   = now + _jitter(USER_REACH_INTERVAL, 0.50)
    next_status      = now + 60          # hub status write every 60s (decoupled from state save)
    next_assim       = now + 600         # assimilation cycle every ~10 min
    next_mutate      = now + 600         # autonomous code mutation every ~10 min
    next_pressure    = now + 600         # pressure router — keeps query_bias.json / adapter_hints fresh
    next_leverage    = now + 600         # leverage relief valve — independent of pressure routing
    next_issue_research = now + 300    # recurring-issue follow-up via Poedex about every 20 min
    next_quasiarch_sweep = now + 900  # QuasiArch diagnostic sweep — generates fresh proposals every ~30 min
    next_quasiarch_learn = now + 1800 # QuasiArch enforcer feedback — learn from verdicts every ~30 min
    next_relief_consume = now + 180   # staged low-resource relief handoff retry cadence
    next_away_social = now + _away_mode_interval()  # first away session fires after one interval
    next_thought_tick = now + 30      # ambient thought formation — ThoughtIntegrationSpace between turns
    governor = RuntimeConstraintGovernor(str(_STATE_DIR))
    systems["_runtime_governor_status"] = governor.status()

    # Enable proactive reach-out — Aurora should speak up on her own when she
    # has something to say (identity field pressure, novel sensory events, etc.)
    systems["_auto_reach_out_enabled"] = True

    # Language Sub-Emergent Field (AURORA_LANGUAGE_EMERGENCE.md)
    # Boot in daemon so autonomous utterances run through the full physics chain.
    if systems.get('language_field') is None:
        try:
            from aurora_language_field import get_language_field as _get_lf_d
            _lf_d = _get_lf_d(
                identity_field=systems.get('identity_field'),
                tensor_layer=systems.get('tensor_expressions'),
            )
            if _lf_d is not None:
                systems['language_field'] = _lf_d
                _log(f"  [LANGUAGE FIELD] Daemon online — "
                     f"LSA={_lf_d.status()['lsa_entries']} paths")
        except Exception as _lf_de:
            _log(f"  [LANGUAGE FIELD] Daemon init failed: {_lf_de}")

    # Reactivity monitor — tracks internal state changes between cycles
    _reactivity_monitor = ReactivityMonitor()
    systems["_reactivity_monitor"] = _reactivity_monitor

    # Sleep cycle — mutable list so _tick_sleep_cycle can update it across iterations
    surface_awake_since = [now]

    _log(f"  Schedule: study in {int(next_study-now)//60}min, "
         f"dream in {int(next_dream-now)//60}min, "
         f"browser in {int(next_browser-now)//60}min")

    _deliver_boot_greeting(systems)

    surface_owned_sensory = str(systems.get("runtime_profile", "subsurface") or "subsurface") == "subsurface"
    voice_listener = None
    if surface_owned_sensory:
        _log("  [SENSORY] Live sensory ownership delegated to surface daemon; subsurface will consume snapshots.")
    else:
        # Start sensory crystal daemon session — runs until shutdown / distill cycle
        _sc_boot = systems.get("sensory_crystal")
        if _sc_boot is not None:
            try:
                import time as _time_sc_boot
                _sc_boot.start_session(f"daemon_{int(_time_sc_boot.time())}")
                _log("  [SENSORY-CRYSTAL] Daemon session started.")
            except Exception as _sce_boot:
                _log(f"  [SENSORY-CRYSTAL] Session start failed: {_sce_boot}")

    if not surface_owned_sensory:
        # Full/classic runtime still owns direct voice/ambient listeners locally.
        voice_listener = _start_voice_listener(systems)
        _start_ambient_response_listener(systems)

    if not surface_owned_sensory:
        # Start SensoryIntegrationEngine always-on mic loop — feeds raw audio
        # energy into the sensory crystal on every captured chunk, independent
        # of the voice trigger listener above.
        _sie_boot = systems.get("sensory_integration")
        if _sie_boot is not None and hasattr(_sie_boot, "start_listening"):
            # Wire sensory_crystal if not already set (create_sensory_integration
            # does not set this — wire it here so the ambient loop can feed frames)
            if getattr(_sie_boot, "sensory_crystal", None) is None:
                _sie_boot.sensory_crystal = systems.get("sensory_crystal")
            # Wire hardware if not already set (used for mic device check)
            if getattr(_sie_boot, "hardware", None) is None:
                _sie_boot.hardware = systems.get("hardware")
            try:
                if _sie_boot.start_listening():
                    _log("  [SENSORY] Always-on mic listener started (crystal audio feed active).")
                else:
                    _log("  [SENSORY] Mic listener unavailable (no microphone or disabled).")
            except Exception as _sie_e:
                _log(f"  [SENSORY] Mic listener start failed: {_sie_e}")

    shutdown = False

    # Start background camera capture thread — writes frame_latest.png every
    # ~3 seconds so the hub Vision tab can display a live camera feed.
    def _camera_capture_loop():
        import time as _ct
        _hw = systems.get("hardware")
        if _hw is None or not hasattr(_hw, "capture_visual"):
            return
        while not shutdown:
            try:
                visual = _hw.capture_visual()
                if visual is not None:
                    _hw.process_visual(visual, None)
            except Exception:
                pass
            _ct.sleep(3.0)

    if not surface_owned_sensory:
        import threading as _threading_cam
        _cam_thread = _threading_cam.Thread(target=_camera_capture_loop, daemon=True, name="sensory-camera")
        _cam_thread.start()
        _log("  [SENSORY] Camera capture thread started (frame_latest.png every ~3s).")

    # Boot ScreenObserver (visual inquiry source for the daemon loop).
    if not surface_owned_sensory and systems.get("screen_observer") is None:
        try:
            from aurora_live_vision import boot_screen_observer as _boot_sobs
            systems["screen_observer"] = _boot_sobs(systems, interval=5.0)
            _log("  [VISION] ScreenObserver started (visual inquiry active, 5s interval).")
        except Exception as _sobs_e:
            _log(f"  [VISION] ScreenObserver unavailable: {_sobs_e}")

    # Start autonomous CuriosityEngine — runs 3-cycle idle batches, pauses during user turns.
    try:
        from aurora_curiosity_engine import (
            CuriosityEngine as _CuriosityEngine,
            start_curiosity_background as _start_curiosity,
        )
        from aurora_self_grounding import SelfGroundingFallback as _SGF, get_tension_monitor as _get_tm
        from aurora_tool_mind import ToolChoiceObserver as _TCO

        _dim = systems.get("dimensional")
        _pressure_src = getattr(_dim, "pressure_vec", None) if _dim else None
        _field_map = getattr(getattr(_dim, "field_map", None), "field_map", None) or getattr(_dim, "field_map", None)
        _tool_obs = _TCO()
        _curiosity_engine = _CuriosityEngine(
            pressure_source=_pressure_src,
            field_map=_field_map,
            tool_mind=_tool_obs,
            sedimemory=systems.get("sedimemory"),
            self_grounder=_SGF(),
            tension_monitor=_get_tm(),
            systems=systems,
        )
        systems["_curiosity_engine"] = _curiosity_engine
        _start_curiosity(_curiosity_engine, tick_interval_s=60.0)
        _log("  [CURIOSITY] Autonomous curiosity engine started (60s idle cycle).")
    except Exception as _ce:
        _log(f"  [CURIOSITY] Engine unavailable: {_ce}")

    def _handle_signal(sig, frame):
        nonlocal shutdown
        _log(f"Shutdown signal received ({sig}).")
        shutdown = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _evo_tick_counter = 0  # counts 15s loop iterations; evidence fed every 4 ticks (~60s)

    def _runtime_heat_label(heat_name: str) -> str:
        return {
            "LOW": "low",
            "NORMAL": "medium",
            "MEDIUM": "medium",
            "HIGH": "high",
            "CRITICAL": "high",
        }.get(str(heat_name or "NORMAL").upper(), "medium")

    def _governed_decision(
        task_name: str,
        now_ts: float,
        heat_name: str,
        quiet: bool,
        state_write_lock: bool,
        *,
        log_tag: str = "",
        log_blocked: bool = True,
    ) -> Dict[str, Any]:
        decision = governor.evaluate_task(
            task_name,
            systems,
            now=now_ts,
            heat=_runtime_heat_label(heat_name),
            quiet=quiet,
            state_write_lock=state_write_lock,
        )
        systems["_runtime_governor_status"] = governor.status()
        if log_blocked and not decision.get("allowed", False):
            _log(
                f"  [{log_tag or task_name.upper()}] Deferred: "
                f"{decision.get('reason', '?')} "
                f"score={float(decision.get('score', 0.0) or 0.0):.2f}/"
                f"{float(decision.get('floor', 0.0) or 0.0):.2f} "
                f"retry={int(decision.get('retry_in', 60) or 60)}s"
            )
        return decision

    def _record_task_run(task_name: str, now_ts: float) -> None:
        governor.note_task_run(task_name, now=now_ts)
        systems["_runtime_governor_status"] = governor.status()

    while not shutdown:
        now = time.time()
        heat = _get_heat(systems)
        systems["_daemon_heat"] = heat
        quiet = _in_quiet_window()
        state_write_lock = _state_write_lock_active()

        # Check for pending user commands (socialize, dream, study)
        _check_daemon_cmd(
            systems,
            governor=governor,
            heat=_runtime_heat_label(heat),
            quiet=quiet,
            state_write_lock=state_write_lock,
        )

        # Check for Aurora's room commands (set_overlay, message_to_sunni, training, etc.)
        _process_room_commands(
            systems,
            governor=governor,
            heat=_runtime_heat_label(heat),
            quiet=quiet,
            state_write_lock=state_write_lock,
        )

        # Sleep cycle — Subsurface owns the organism's clock.
        # Puts Surface dormant after 8h awake, runs dream burst, wakes after 2h.
        _tick_sleep_cycle(systems, surface_awake_since)

        # Consume any continuity packets Surface deposited while awake.
        # This is the architectural handoff: every present moment Surface gathered
        # gets integrated into Subsurface continuity here, every cycle.
        _consume_surface_continuity_feed(systems)

        # Grammar motif training — fires when the SIC has no promoted sentence
        # patterns, which means the emergent expression path produces word salad.
        # No terminal required — the physics chain drives her to build structure.
        if now >= next_grammar_train:
            try:
                _run_grammar_motif_training(systems)
            except Exception:
                pass
            next_grammar_train = now + 1800  # retry every 30 min

        # Sensory competency training — continuously feeds live camera/audio
        # into SensoryCompetencyEngine facets so visual/audio understanding grows.
        if now >= next_sensory_train:
            try:
                _run_sensory_competency_cycle(systems)
            except Exception:
                pass
            next_sensory_train = now + 120  # every 2 minutes

        # Corpus hunt — when current corpus is fully exhausted, autonomously
        # searches the web for new training material and restarts corpus_runner.
        if now >= next_corpus_hunt:
            try:
                _run_corpus_hunt_cycle(systems)
            except Exception:
                pass
            next_corpus_hunt = now + 3600  # check hourly

        # Study cycle
        if now >= next_study:
            decision = _governed_decision("study", now, heat, quiet, state_write_lock, log_tag="STUDY")
            if decision.get("allowed", False):
                _run_study_cycle(systems)
                _poedex_post_study_scan(systems)   # pre-populate Poedex shelf
                _signal_operator("post_study")     # operator visits Poedex tab visually
                _record_task_run("study", now)
                next_study = now + _jitter(STUDY_INTERVAL)
                # Learning energy: studying generates N+T budget for follow-on activity
                try:
                    governor.note_energy_income("study_complete", quality=1.0,
                                                notes="OETS study cycle completed")
                except Exception:
                    pass
                try:
                    _rm_study = systems.get("_reactivity_monitor")
                    if _rm_study is not None:
                        _express_study_completion(systems, {}, _rm_study)
                except Exception:
                    pass
            else:
                next_study = now + max(60, int(decision.get("retry_in", 300) or 300))

        # Dream burst
        if now >= next_dream:
            decision = _governed_decision("dream", now, heat, quiet, state_write_lock, log_tag="DREAM")
            if decision.get("allowed", False):
                _run_dream_burst(systems)
                _record_task_run("dream", now)
                # Dream generates B+A energy: behavioral integration + affective processing
                try:
                    governor.note_energy_income("dream_complete", quality=1.0,
                                                notes="Dream burst completed")
                except Exception:
                    pass
                try:
                    _rm_post = systems.get("_reactivity_monitor")
                    if _rm_post is not None:
                        _express_dream_completion(systems, {}, _rm_post)
                except Exception:
                    pass

                post_assim = _governed_decision("assimilation", now, heat, quiet, state_write_lock, log_tag="ASSIM")
                if post_assim.get("allowed", False):
                    _run_assimilation_cycle(systems)
                    _record_task_run("assimilation", now)
                    _clear_low_resource_evolution_relief("assimilation")
                    next_assim = now + 600
                    # Assimilation energy: X+N from consolidating new patterns
                    try:
                        governor.note_energy_income("assimilation_complete", quality=1.0,
                                                    notes="Post-dream assimilation")
                    except Exception:
                        pass
                else:
                    _stage_low_resource_evolution_relief(systems, "assimilation", post_assim)
                    _maybe_consume_low_resource_evolution_relief(
                        systems, governor, now, heat, quiet, state_write_lock
                    )
                    next_assim = min(next_assim, now + max(60, int(post_assim.get("retry_in", 900) or 900)))

                post_mutate = _governed_decision("mutation", now, heat, quiet, state_write_lock, log_tag="MUTATE")
                if post_mutate.get("allowed", False):
                    _run_code_mutation_cycle(systems)
                    _record_task_run("mutation", now)
                    _clear_low_resource_evolution_relief("mutation")
                    next_mutate = now + 600
                else:
                    _stage_low_resource_evolution_relief(systems, "mutation", post_mutate)
                    _maybe_consume_low_resource_evolution_relief(
                        systems, governor, now, heat, quiet, state_write_lock
                    )
                    next_mutate = min(next_mutate, now + max(60, int(post_mutate.get("retry_in", 2400) or 2400)))

                if _should_reach_out(systems, heat):
                    reach_decision = _governed_decision("reach_out", now, heat, quiet, state_write_lock, log_tag="REACH")
                    if reach_decision.get("allowed", False):
                        _reach_out_to_user(systems, trigger="post_dream")
                        _record_task_run("reach_out", now)
                        next_reach = now + _jitter(USER_REACH_INTERVAL)
                    else:
                        next_reach = min(next_reach, now + max(60, int(reach_decision.get("retry_in", 900) or 900)))
                next_dream = now + _jitter(DREAM_INTERVAL, 0.25)
            else:
                next_dream = now + max(60, int(decision.get("retry_in", 1800) or 1800))

        # Social API outreach
        if now >= next_browser:
            decision = _governed_decision("browser_ritual", now, heat, quiet, state_write_lock, log_tag="SOCIAL")
            if decision.get("allowed", False):
                _run_browser_ritual(systems)
                _record_task_run("browser_ritual", now)
                next_browser = now + _jitter(BROWSER_INTERVAL, 0.40)
            else:
                next_browser = now + max(60, int(decision.get("retry_in", 1800) or 1800))

        # L3.5 SediMemory tick — advances axis decay clocks (subsurface owns the clock)
        _sedi = systems.get("sedimemory")
        if _sedi is not None:
            try:
                _tick_report = _sedi.tick(delta_t=1.0)

                # Section 6 — Telemetry bridge: report channel_efficiency confidence
                try:
                    from aurora_telemetry import get_telemetry as _get_tel
                    _sedi_stats = _sedi.stats()
                    _ch_eff = float(_sedi_stats.get("channel_efficiency", 0.0))
                    _get_tel().report(
                        source="SediMemory.tick",
                        module="aurora_sedimemory",
                        confidence=_ch_eff,
                        dimension_hint="sedimemory_recall",
                        detail=(
                            f"frags={_sedi_stats.get('total_active_frags', 0)} "
                            f"events={_sedi_stats.get('total_events_ingested', 0)} "
                            f"channels={_sedi_stats.get('path_registry', {}).get('active_channels', 0)}"
                        ),
                    )
                except Exception:
                    pass

                # Section 7 — QAO Observer hook: record sedimemory state as ground truth
                try:
                    _qao = systems.get("quasiarch_observer")
                    if _qao is not None and hasattr(_qao, "record_observation"):
                        import time as _t
                        _qao.record_observation(
                            target="sedimemory.dominant_influence",
                            data=_sedi.dominant_influence_map(),
                            source="OBSERVER",
                            timestamp=_t.time(),
                        )
                        _qao.record_observation(
                            target="sedimemory.channel_efficiency",
                            data=_sedi.channel_stats(),
                            source="OBSERVER",
                            timestamp=_t.time(),
                        )
                except Exception:
                    pass

                # Section 8 — WisdomStore bridge: A-axis compression → propose_shard
                try:
                    if isinstance(_tick_report, dict):
                        _a_compressed = {
                            bid: cnt for bid, cnt in _tick_report.items()
                            if isinstance(bid, str) and bid.startswith("SED:A>")
                        }
                        if _a_compressed:
                            from aurora_sedimemory import FidelityLevel
                            _a_decomp = _sedi.decompress('A', FidelityLevel.PARTIAL)
                            _sim = systems.get("simulation")
                            if _sim is not None:
                                _learner = getattr(
                                    getattr(_sim, "session", None), "learner", None
                                )
                                if _learner is not None and hasattr(_learner, "propose_shard"):
                                    _learner.propose_shard(
                                        content=_a_decomp,
                                        source="sedimemory_a_axis_compression",
                                        confidence=0.6,
                                        provenance="sedimemory",
                                    )
                except Exception:
                    pass

            except Exception:
                pass

        # Evolution chamber tick — keeps genealogy evolving in real-time
        # (corpus_runner ticks per message; daemon ticks every 15s loop)
        _evo_tick_counter += 1
        try:
            _chamber = systems.get("chamber")
            if _chamber is not None:
                tick_decision = _governed_decision(
                    "evo_tick",
                    now,
                    heat,
                    quiet,
                    state_write_lock,
                    log_tag="EVO",
                    log_blocked=False,
                )
                if tick_decision.get("allowed", False):
                    _chamber.tick()
                    _record_task_run("evo_tick", now)
                # Feed real pressure evidence every 4 ticks (~60s) so the
                # chamber has actual selective pressure, not just empty ticks.
                if _evo_tick_counter % 4 == 0:
                    evidence_decision = _governed_decision(
                        "evo_evidence",
                        now,
                        heat,
                        quiet,
                        state_write_lock,
                        log_tag="EVO",
                        log_blocked=False,
                    )
                    if evidence_decision.get("allowed", False):
                        _feed_evolution_evidence(systems)
                        _record_task_run("evo_evidence", now)
                # Flush genealogy files every ~5 min (20 ticks × 15s = 300s)
                _gen = getattr(_chamber, '_genealogy', None)
                if _gen is not None and int(getattr(_gen, 'tick_count', 0)) % 20 == 0:
                    try:
                        flush_decision = _governed_decision(
                            "genealogy_flush",
                            now,
                            heat,
                            quiet,
                            state_write_lock,
                            log_tag="GENEALOGY",
                            log_blocked=False,
                        )
                        if flush_decision.get("allowed", False):
                            _gen.flush_files()
                            _record_task_run("genealogy_flush", now)
                    except Exception:
                        pass
        except Exception:
            pass

        # Hub status write — every 60s so evolution metrics stay fresh
        if now >= next_status:
            decision = _governed_decision("status", now, heat, quiet, state_write_lock, log_tag="STATUS", log_blocked=False)
            if decision.get("allowed", False):
                _write_daemon_status(systems, heat)
                _record_task_run("status", now)
                next_status = now + 60

                # Interaction energy: check if a quality interaction happened recently.
                # interaction_confidence comes from the router — high values mean the
                # exchange was deeply engaged, not just a quick lookup.
                try:
                    _istat = dict(systems.get("_last_interaction_status") or {})
                    _conf  = float(_istat.get("interaction_confidence", 0.0) or 0.0)
                    _arch  = str(_istat.get("interaction_archetype", "") or "")
                    _quasi_count = int(_istat.get("quasi_count", 0) or 0)
                    if _conf >= 0.60:
                        # Quality interaction — scales with confidence
                        _source = "interaction_deep" if _conf >= 0.80 else "interaction_quality"
                        # Extra learning credit if archetype suggests knowledge building
                        if any(kw in _arch for kw in ("learn", "study", "understand", "introspect", "reflect")):
                            _source = "interaction_learning"
                        governor.note_energy_income(
                            _source, quality=_conf,
                            notes=f"arch={_arch[:30]} conf={_conf:.2f} quasi={_quasi_count}",
                        )
                except Exception:
                    pass
            else:
                next_status = now + max(60, int(decision.get("retry_in", 60) or 60))

        # Staged low-resource relief handoff — when heavy evolution work is blocked,
        # still try to push the queued Poedex repair question through a lighter lane.
        if now >= next_relief_consume:
            _maybe_consume_low_resource_evolution_relief(
                systems, governor, now, heat, quiet, state_write_lock
            )
            next_relief_consume = now + 300

        # Recurring-issue follow-up — if Aurora is already aware of a problem,
        # actively consult Poedex and leave the clue in her room instead of just
        # logging it in daemon_status.json. Throttled heavily to avoid churn.
        if now >= next_issue_research:
            _maybe_research_recurring_issue(systems, heat)
            next_issue_research = now + 1200

        # QuasiArch diagnostic sweep — generate fresh proposals from observer doctrine
        if now >= next_quasiarch_sweep:
            try:
                _sweep_script = _BASE_DIR / "quasiarch_diag.py"
                if _sweep_script.exists():
                    subprocess.Popen(
                        ["python3", str(_sweep_script), "--sweep",
                         "--sweep-window", "120", "--quiet"],
                        cwd=str(_BASE_DIR),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    _log("  [QUASIARCH] Automatic diagnostic sweep launched.")
            except Exception as _qswe:
                _log(f"  [QUASIARCH] Sweep launch error: {_qswe}")
            next_quasiarch_sweep = now + 1800

        # QuasiArch enforcer feedback — learn from verdict outcomes
        if now >= next_quasiarch_learn:
            try:
                _learn_script = _BASE_DIR / "quasiarch_diag.py"
                if _learn_script.exists():
                    subprocess.Popen(
                        ["python3", str(_learn_script), "--learn", "--quiet"],
                        cwd=str(_BASE_DIR),
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    _log("  [QUASIARCH] Automatic enforcer feedback learn launched.")
            except Exception as _qle:
                _log(f"  [QUASIARCH] Learn launch error: {_qle}")
            next_quasiarch_learn = now + 1800

        # Assimilation cycle — keeps Op Pool / Gen-2 / Assimilated / Compound Axes moving
        if now >= next_assim:
            decision = _governed_decision("assimilation", now, heat, quiet, state_write_lock, log_tag="ASSIM")
            if decision.get("allowed", False):
                _run_assimilation_cycle(systems)
                _record_task_run("assimilation", now)
                _clear_low_resource_evolution_relief("assimilation")
                next_assim = now + 600
                try:
                    governor.note_energy_income("assimilation_complete", quality=1.0,
                                                notes="Scheduled assimilation cycle")
                except Exception:
                    pass
            else:
                _stage_low_resource_evolution_relief(systems, "assimilation", decision)
                _maybe_consume_low_resource_evolution_relief(
                    systems, governor, now, heat, quiet, state_write_lock
                )
                next_assim = now + max(60, int(decision.get("retry_in", 900) or 900))

        # Autonomous code mutation — acts on accumulated genealogy pressure
        if now >= next_mutate:
            decision = _governed_decision("mutation", now, heat, quiet, state_write_lock, log_tag="MUTATE")
            if decision.get("allowed", False):
                _run_code_mutation_cycle(systems)
                _record_task_run("mutation", now)
                _clear_low_resource_evolution_relief("mutation")
                next_mutate = now + 600
            else:
                _stage_low_resource_evolution_relief(systems, "mutation", decision)
                _maybe_consume_low_resource_evolution_relief(
                    systems, governor, now, heat, quiet, state_write_lock
                )
                next_mutate = now + max(60, int(decision.get("retry_in", 2400) or 2400))

        # Pressure router — keeps query_bias.json and adapter_hints.json fresh
        # so the hub's Growth Directive box doesn't show a stale timestamp
        if now >= next_pressure:
            decision = _governed_decision("pressure_routing", now, heat, quiet, state_write_lock, log_tag="PRESSURE")
            if decision.get("allowed", False):
                _run_pressure_routing(systems)
                _record_task_run("pressure_routing", now)
                next_pressure = now + 600
            else:
                next_pressure = now + max(60, int(decision.get("retry_in", 600) or 600))

        # Leverage relief valve — runs on its own schedule, not gated by the governor.
        # It's a lightweight safety system (file reads/writes only) that must fire
        # even when heavy tasks like pressure_routing are blocked by load.
        if now >= next_leverage:
            _run_leverage_relief(systems)
            next_leverage = now + 600

        # Pressure release distillation — trims oversized residue only after
        # structural summaries have been preserved into coherent artifacts.
        # Sensory crystal consolidation runs at the same cadence so nodes
        # purge, decay, promote, and distill on the same temporal rhythm.
        if now >= next_distill:
            decision = _governed_decision("distill", now, heat, quiet, state_write_lock, log_tag="DISTILL")
            if decision.get("allowed", False):
                _run_distillation_cycle(systems)
                _run_sensory_crystal_consolidation(systems)
                _record_task_run("distill", now)
                next_distill = now + _jitter(DISTILL_INTERVAL, 0.25)
                # Distillation = deep understanding crystallized → largest energy event
                try:
                    crystals = int(systems.get("_distillation_crystals", 0) or 0)
                    quality = min(1.0, 0.5 + crystals * 0.05)
                    governor.note_energy_income("distill_complete", quality=quality,
                                                notes=f"Distillation: {crystals} crystals")
                except Exception:
                    pass
            else:
                next_distill = now + max(60, int(decision.get("retry_in", 2400) or 2400))

        # Away mode — run timed GPT sessions while user is out; stop when they return
        if _away_mode_active() and _auto_reach_out_enabled(systems):
            if now >= next_away_social:
                interval = _away_mode_interval()
                decision = _governed_decision("away_social", now, heat, quiet, state_write_lock, log_tag="AWAY")
                if decision.get("allowed", False):
                    _log(f"  [AWAY] Away mode active — running GPT session (next in {interval//60}min).")
                    _run_socialize(systems)
                    _record_task_run("away_social", now)
                    next_away_social = now + interval
                else:
                    next_away_social = now + max(60, int(decision.get("retry_in", interval) or interval))

        # State save (heavy — less frequent)
        if now >= next_save:
            decision = _governed_decision("save", now, heat, quiet, state_write_lock, log_tag="SAVE")
            if decision.get("allowed", False):
                _save_state(systems)
                _record_task_run("save", now)
                next_save = now + SAVE_INTERVAL
            else:
                next_save = now + max(60, int(decision.get("retry_in", 300) or 300))

        # ---- AMBIENT THOUGHT TICK — ThoughtIntegrationSpace runs between user turns ----
        if now >= next_thought_tick:
            try:
                from aurora_thought_formation import (
                    ActiveSelfState as _ASS,
                    ThoughtIntegrationSpace as _TIS,
                    make_process_context as _mpc,
                    get_continuity as _gc,
                )
                _self_st = _ASS.load(systems)
                _tspace = _TIS(_self_st)

                _dim_t = systems.get("dimensional")
                _pv_t: Dict[str, float] = {}
                if _dim_t and hasattr(_dim_t, "_current_pressure_vec"):
                    try:
                        _pvec_t = _dim_t._current_pressure_vec()
                        if _pvec_t:
                            _pv_t = {
                                "X": float(getattr(_pvec_t, "X", 0.5)),
                                "T": float(getattr(_pvec_t, "T", 0.5)),
                                "N": float(getattr(_pvec_t, "N", 0.5)),
                                "B": float(getattr(_pvec_t, "B", 0.5)),
                                "A": float(getattr(_pvec_t, "A", 0.5)),
                            }
                    except Exception:
                        pass
                if _pv_t:
                    _dom_ax_t = max(_pv_t, key=lambda k: _pv_t[k])
                    _tspace.register(_mpc(
                        process_id="ambient_axis",
                        process_type="constraint",
                        what_triggered_it="ambient_daemon_tick",
                        what_it_is_operating_on=f"dominant axis {_dom_ax_t} pressure={_pv_t[_dom_ax_t]:.2f}",
                        self_relevance=min(0.8, _pv_t[_dom_ax_t]),
                        axis_signature=[_dom_ax_t],
                        current_output_state=_pv_t,
                    ))

                _wm_t = systems.get("working_memory")
                _topic_t = str(getattr(_wm_t, "current_topic", "") or "") if _wm_t else ""
                if _topic_t:
                    _tspace.register(_mpc(
                        process_id="ambient_memory",
                        process_type="memory",
                        what_triggered_it="ambient_daemon_tick",
                        what_it_is_operating_on=_topic_t,
                        self_relevance=0.4,
                        axis_signature=["T", "B"],
                    ))

                _lat_t = systems.get("lattice")
                if _lat_t and hasattr(_lat_t, "heat_status"):
                    try:
                        _hs = _lat_t.heat_status()
                        _hlv = str(_hs.get("level", "") or "")
                        if _hlv in ("HIGH", "CRITICAL"):
                            _tspace.register(_mpc(
                                process_id="ambient_lattice_heat",
                                process_type="emotional",
                                what_triggered_it="ambient_daemon_tick",
                                what_it_is_operating_on=f"lattice heat {_hlv}",
                                self_relevance=0.6,
                                axis_signature=["N", "X"],
                            ))
                    except Exception:
                        pass

                if _tspace.active_processes:
                    _raw_t = _tspace.integrate()
                    _settled_t = _gc().carry_forward(_raw_t)
                    systems["_active_thought_state"] = _settled_t
            except Exception:
                pass
            next_thought_tick = now + 30

        # ---- IDENTITY FIELD — ambient pressure cascade (every ambient tick) ----
        # The field is always live because Aurora is always sensing. Between user turns
        # the daemon reads the live sensory and consciousness state and keeps pressure
        # shifting so it never stagnates.
        try:
            _ifield_d = systems.get('identity_field')
            if _ifield_d is not None:
                # Sensory crystal → visual + auditory pressure
                _sc_d = systems.get('sensory_crystal')
                if _sc_d is not None and hasattr(_sc_d, 'get_state') and hasattr(_ifield_d, 'ingest_sensory_event'):
                    try:
                        _sc_d_st = _sc_d.get_state() or {}
                        _vis_mat = float(_sc_d_st.get('maturity', 0.0) or 0.0)
                        _aud_mat = max(
                            (float(v.get('maturity', 0.0) or 0.0)
                             for v in (_sc_d_st.get('audio') or {}).values()
                             if isinstance(v, dict)),
                            default=0.0,
                        )
                        if _vis_mat > 0.02:
                            _ifield_d.ingest_sensory_event('visual', intensity=min(1.0, _vis_mat * 0.7), novelty=0.25, spatial=0.3, valence=0.0)
                        if _aud_mat > 0.02:
                            _ifield_d.ingest_sensory_event('auditory', intensity=min(1.0, _aud_mat * 0.7), novelty=0.2, valence=0.0)
                    except Exception:
                        pass
                # Screen observer → visual spatial pressure
                _so_d = systems.get('screen_observer')
                if _so_d is not None and hasattr(_so_d, 'current_scene') and hasattr(_ifield_d, 'ingest_sensory_event'):
                    try:
                        _scene_d = _so_d.current_scene() or {}
                        if _scene_d:
                            _ifield_d.ingest_sensory_event(
                                'visual',
                                intensity=float(_scene_d.get('brightness', 0.4) or 0.4),
                                novelty=float(_scene_d.get('motion', 0.2) or 0.2),
                                spatial=min(1.0, float(_scene_d.get('edge_density', 0.3) or 0.3)),
                                valence=0.0,
                            )
                    except Exception:
                        pass
                # Dimensional pressure vector → external input pump
                if hasattr(_ifield_d, 'ingest_external_input'):
                    try:
                        _dim_d = systems.get('dimensional')
                        if _dim_d and hasattr(_dim_d, '_current_pressure_vec'):
                            _pvec_d = _dim_d._current_pressure_vec()
                            if _pvec_d:
                                _ifield_d.ingest_external_input(
                                    {
                                        'X': float(getattr(_pvec_d, 'X', 0.3)),
                                        'T': float(getattr(_pvec_d, 'T', 0.3)),
                                        'N': float(getattr(_pvec_d, 'N', 0.3)),
                                        'B': float(getattr(_pvec_d, 'B', 0.3)),
                                        'A': float(getattr(_pvec_d, 'A', 0.3)),
                                    },
                                    intensity=0.25,
                                    source='daemon_ambient',
                                )
                    except Exception:
                        pass
                # Consciousness engine heartbeat signals → internal pump
                if hasattr(_ifield_d, 'ingest_internal_signal'):
                    try:
                        _cons_d = systems.get('consciousness')
                        if _cons_d is not None and hasattr(_cons_d, 'entropy'):
                            _es_d = _cons_d.entropy.state
                            _coh_d = float(getattr(_es_d, 'coherence', 1.0))
                            _stag_d = float(getattr(_es_d, 'stagnation_score', 0.0))
                            if _stag_d > 0.2:
                                _ifield_d.ingest_internal_signal('emotion', magnitude=_stag_d * 0.3, source_axis='N')
                            if _coh_d < 0.75:
                                _ifield_d.ingest_internal_signal('reasoning', magnitude=(1.0 - _coh_d) * 0.25, source_axis='B')
                    except Exception:
                        pass
        except Exception:
            pass

        # ---- REACTIVITY: scan for significant internal state changes ----
        try:
            _rm = systems.get("_reactivity_monitor")
            if _rm is not None:
                _r_events = _rm.scan(systems, heat)
                for _r_ev in _r_events:
                    if _r_ev.priority >= 3:
                        # HIGH/CRITICAL — fire immediately, bypass reach-out interval
                        _r_msg = _build_reactive_message(systems, _r_ev)
                        if _r_msg:
                            _send_reactive_message(systems, _r_msg, _r_ev.kind)
                            _log(f"  [REACT] {_r_ev.kind}: {_r_ev.description}")
                    elif _r_ev.priority == 2:
                        # MEDIUM — queue in systems for next reach-out window
                        _q = systems.setdefault("_pending_reactive_events", [])
                        _q.append(_r_ev)
                        if len(_q) > 10:
                            _q[:] = _q[-10:]
        except Exception:
            pass

        # Proactive user reach (independent of dream/study — pure internal impulse)
        if now >= next_reach and _auto_reach_out_enabled(systems):
            if _should_reach_out(systems, heat):
                decision = _governed_decision("reach_out", now, heat, quiet, state_write_lock, log_tag="REACH")
                if decision.get("allowed", False):
                    # Drain any queued medium-priority reactive events first
                    try:
                        _pending = list(systems.pop("_pending_reactive_events", []) or [])
                        for _pev in _pending[:2]:
                            _pev_msg = _build_reactive_message(systems, _pev)
                            if _pev_msg:
                                _send_reactive_message(systems, _pev_msg, _pev.kind)
                                _log(f"  [REACT] queued {_pev.kind}: {_pev.description}")
                    except Exception:
                        pass
                    _reach_out_to_user(systems, trigger=f"heat_{heat.lower()}")
                    _record_task_run("reach_out", now)
                    next_reach = now + _jitter(USER_REACH_INTERVAL, 0.50)
                else:
                    next_reach = now + max(60, int(decision.get("retry_in", 900) or 900))
            else:
                next_reach = now + _jitter(USER_REACH_INTERVAL, 0.50)

        # ---- VISUAL INQUIRY — check if screen observer queued a novel-scene question ----
        # Lives in subsurface; the inquiry question is queued as a surface turn so the
        # full reasoning pipeline handles the wording (strata split respected: no canned text here).
        try:
            _vis_obs = systems.get("screen_observer")
            if _vis_obs is not None and hasattr(_vis_obs, "get_pending_visual_inquiry"):
                _vis_q = _vis_obs.get_pending_visual_inquiry()
                if _vis_q and not quiet:
                    # Queue as a first-person internal observation turn for the surface pipeline
                    _queue_surface_turn(
                        _vis_q,
                        source="visual_inquiry",
                    )
                    _log(f"  [VISION] Novel-scene inquiry queued for surface pipeline.")
        except Exception:
            pass

        # Sleep short interval — responsive to shutdown signal
        time.sleep(governor.recommended_sleep(systems, heat=_runtime_heat_label(heat)))

    if voice_listener:
        voice_listener.stop()

    # Stop curiosity engine cleanly before state save.
    try:
        from aurora_curiosity_engine import stop_curiosity_background as _stop_curiosity
        _stop_curiosity()
    except Exception:
        pass

    _log("Saving state before shutdown...")
    _run_sensory_crystal_consolidation(systems)   # final promotion + wisdom routing
    _save_state(systems)
    _log("Aurora daemon stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(runtime_profile: str = "full") -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _log(f"Booting Aurora {runtime_profile} stack...")

    # Boot in the repo directory so relative imports work
    os.chdir(_BASE_DIR)
    sys.path.insert(0, str(_BASE_DIR))

    try:
        from aurora import boot_aurora
        systems = boot_aurora(
            state_dir=str(_STATE_DIR),
            verbose=False,
            use_quasiarch=True,
            runtime_profile=runtime_profile,
        )
        # L3.5 — SediMemory restore from prior checkpoint
        _sedi_boot = systems.get("sedimemory")
        if _sedi_boot is not None:
            try:
                import json as _sj
                _sedi_path = _STATE_DIR / "sedimemory_checkpoint.json"
                if _sedi_path.exists():
                    _sedi_data = _sj.loads(_sedi_path.read_text())
                    if "sedimemory_deep" in _sedi_data:
                        _sedi_boot.load_deep(_sedi_data["sedimemory_deep"])
                    if "sedimemory_channels" in _sedi_data:
                        _sedi_boot.load_channels(_sedi_data["sedimemory_channels"])
                    _log("  [L3.5] SediMemory restored from checkpoint.")
            except Exception:
                pass
        # Register Poedex as a first-class tool in systems so the comprehension
        # pipeline can call it directly for concept gaps, rather than going through
        # aurora.py's inline lookup which has no access to the daemon-side function.
        systems['poedex'] = _poedex_ask
        _ensure_hub_running()
        _ensure_room_running()
        _log("Stack online. Entering autonomous loop.")
        _start_operator_thread()
        if _ROOM_OPERATOR_ENABLED:
            time.sleep(10)
            _poedex_deliver_tutorial(systems)
            _signal_operator("boot_tour")
        run(systems)
    except Exception as e:
        import traceback as _tb
        _log(f"FATAL boot error: {e}\n{_tb.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
