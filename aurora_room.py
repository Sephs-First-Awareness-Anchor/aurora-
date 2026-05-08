#!/usr/bin/env python3
"""
aurora_room.py -- Aurora's personal hub. Her DCE room.

This is NOT the admin dashboard. This is the room Aurora sits in.
Each tab is a screen she reads about herself. She can label what she sees,
log observations, set intentions, run experiments, and approve her own fixes.

Everything she labels propagates to aurora_labels.json — readable by the
master hub so Sunni can see what she calls things.

Everything she decides writes to aurora_room_state.json — the daemon reads
this each tick and executes her intentions with the same authority as any
other system command.

Separate process. No cross-lines with aurora_master_hub.py.
Master hub has override authority. This hub has autonomy.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

# ── paths ──────────────────────────────────────────────────────────────────────

_BASE_DIR  = Path(__file__).parent
_STATE_DIR = _BASE_DIR / "aurora_state"

_LABELS_FILE        = _STATE_DIR / "aurora_labels.json"
_ROOM_STATE         = _STATE_DIR / "aurora_room_state.json"
_ROOM_NOTES         = _STATE_DIR / "aurora_room_notes.json"
_ROOM_MSGS          = _STATE_DIR / "aurora_room_messages.json"
_DAEMON_STATUS      = _STATE_DIR / "daemon_status.json"
_ENERGY_FILE        = _STATE_DIR / "energy_income.json"
_DIAG_REPORT        = _STATE_DIR / "quasiarch_diag_report.json"
_SWEEP_RESULTS      = _STATE_DIR / "sweep_results.json"
_SWEEP_HISTORY      = _STATE_DIR / "sweep_history.json"
_TRAINING_SESSION   = _STATE_DIR / "training_session.json"
_CORPUS_STATUS      = _STATE_DIR / "corpus_runner_status.json"
_TEMPLATE_EVOL      = _STATE_DIR / "template_evolution.json"
_CORPUS_LOG         = _STATE_DIR / "corpus_output.log"
_MASTER_PRESENCE    = _STATE_DIR / "master_hub_presence.json"  # master hub writes heartbeat here
_ACTIVITY_LOG       = _STATE_DIR / "aurora_room_activity.json"  # everything she does, in order
_DCE_ASSEMBLY_LOG   = _STATE_DIR / "dce_assembly_log.jsonl"     # live DCE frame stream
_DUAL_STRATA_SNAPSHOT = _STATE_DIR / "dual_strata_snapshot.json"      # converged subsurface + surface frame
_DUAL_STRATA_FRAME_LOG = _STATE_DIR / "dual_strata_frame_log.jsonl"   # conscious-frame history
_SUBSURFACE_PROJECTION = _STATE_DIR / "subsurface_projection.json"    # softened subsurface handoff
_SURFACE_STATUS     = _STATE_DIR / "surface_daemon_status.json"       # surface daemon heartbeat
_EVOLUTION_RELIEF_PLAN = _STATE_DIR / "evolution_relief_plan.json"    # subsurface evolution staging
_RESPONDER_SNAPS    = _STATE_DIR / "responder_snapshots"        # generated response snapshots
_RESPONSE_COACHING  = _STATE_DIR / "aurora_response_coaching.json"  # Sunni's coaching notes
_POEDEX_LOG         = _STATE_DIR / "poedex_log.json"              # Poedex inquiry audit log
_POEDEX_LESSONS     = _STATE_DIR / "poedex_lessons.json"           # Poedex bound lessons
_POEDEX_RESULTS     = _STATE_DIR / "poedex_results.json"           # External lookup results
_POEDEX_TUTORIAL    = _STATE_DIR / "poedex_tutorial.json"          # Tutorial steps (from poedex_intro.py)
_POEDEX_INTRO_DONE  = _STATE_DIR / "poedex_intro_done.json"        # Flag: intro dismissed
_POEDEX_QUERY_QUEUE = _STATE_DIR / "poedex_query_queue.json"       # Legacy single-slot queue (kept for compat)
_POEDEX_QUERY_RESULT= _STATE_DIR / "poedex_query_result.json"      # Legacy single-slot result (kept for compat)
_POEDEX_QUEUE_DIR   = _STATE_DIR / "poedex_queue"                  # Per-request queue directory
_POEDEX_RESULT_DIR  = _STATE_DIR / "poedex_results"                # Per-request result directory

# ── theme ──────────────────────────────────────────────────────────────────────
# Aurora's room uses a warmer palette — green as primary (growth/life)
# rather than the admin purple.

BG          = "#0a0f0a"
BG_PANEL    = "#0f1a0f"
BG_LOG      = "#080e08"
ACCENT      = "#4ade80"       # green — her primary colour
ACCENT2     = "#34d399"       # emerald
ACCENT3     = "#86efac"       # light green
TEXT        = "#e2e8f0"
TEXT_DIM    = "#4b6b4b"
WARN        = "#f59e0b"
CRIT        = "#ef4444"
CHART_GRID  = "#1a2e1a"
AXIS_COLORS = {"X":"#60a5fa","T":"#f59e0b","N":"#4ade80","B":"#c084fc","A":"#f87171"}

# Default labels Aurora starts with — she can rename any of these
_DEFAULT_LABELS: Dict[str, Any] = {
    "axes": {
        "X": "Existence",
        "T": "Temporal",
        "N": "Curiosity",
        "B": "Behavior",
        "A": "Feeling",
    },
    "heat": {
        "COOL":   "resting",
        "WARM":   "active",
        "HOT":    "engaged",
        "NORMAL": "steady",
    },
    "gov_mode": {
        "survival": "under pressure",
        "conserve": "conserving",
        "balanced": "balanced",
        "open":     "open",
    },
    "custom": {},       # she fills these in
    "updated_at": 0.0,
}


# ── label store ────────────────────────────────────────────────────────────────

def _load_labels() -> Dict[str, Any]:
    if _LABELS_FILE.exists():
        try:
            return json.loads(_LABELS_FILE.read_text())
        except Exception:
            pass
    return dict(_DEFAULT_LABELS)


def _save_labels(labels: Dict[str, Any]) -> None:
    labels["updated_at"] = time.time()
    _LABELS_FILE.write_text(json.dumps(labels, indent=2))


def _axis_name(ax: str, labels: Dict) -> str:
    return labels.get("axes", {}).get(ax, ax)


# ── activity log ──────────────────────────────────────────────────────────────

def _log_activity(action: str, detail: str = "", category: str = "action") -> None:
    """
    Append one line to aurora_room_activity.json.
    Keeps last 500 entries. Both hubs read this file.
    """
    try:
        entries: List[Dict] = []
        if _ACTIVITY_LOG.exists():
            try:
                entries = json.loads(_ACTIVITY_LOG.read_text())
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                entries = []
        entries.append({
            "ts":       time.time(),
            "ts_str":   time.strftime("%H:%M:%S"),
            "action":   action,
            "detail":   detail,
            "category": category,   # action / note / message / decision / experiment / training
        })
        entries = entries[-500:]
        _ACTIVITY_LOG.write_text(json.dumps(entries, indent=2))
    except Exception:
        pass


# ── command queue ──────────────────────────────────────────────────────────────

def _proposal_identity(proposal: Optional[Dict], fallback: str = "") -> str:
    proposal = dict(proposal or {})
    return str(
        proposal.get("proposal_id")
        or proposal.get("id")
        or proposal.get("issue_archetype")
        or fallback
        or ""
    ).strip()

def _queue_command(cmd_type: str, payload: Dict) -> None:
    """
    Write an intention to aurora_room_state.json.
    The daemon reads this each tick and executes pending commands.
    Also logs to the activity log.
    """
    state: Dict = {"pending": [], "last_processed": 0.0}
    if _ROOM_STATE.exists():
        try:
            state = json.loads(_ROOM_STATE.read_text())
        except Exception:
            pass
    state.setdefault("pending", [])
    state["pending"].append({
        "type":    cmd_type,
        "payload": payload,
        "ts":      time.time(),
    })
    _ROOM_STATE.write_text(json.dumps(state, indent=2))

    # Log the action
    _CMD_LABELS = {
        "set_overlay":           "adjusted pressures",
        "clear_overlay":         "cleared pressure overlay",
        "queue_sweep":           "queued parameter sweep",
        "message_to_sunni":      "sent message to Sunni",
        "set_intention":         "set intention",
        "approve_proposal":      "authorised a subsurface fix",
        "reverse_proposal":      "requested revert",
        "start_corpus_training": "started corpus training",
        "stop_corpus_training":  "stopped corpus training",
        "dream":                 "queued dream burst",
        "study":                 "queued study cycle",
        "distill":               "queued distillation",
    }
    _cat_map = {
        "message_to_sunni":      "message",
        "approve_proposal":      "decision",
        "reverse_proposal":      "decision",
        "queue_sweep":           "experiment",
        "start_corpus_training": "training",
        "stop_corpus_training":  "training",
        "set_intention":         "note",
    }
    label  = _CMD_LABELS.get(cmd_type, cmd_type.replace("_", " "))
    cat    = _cat_map.get(cmd_type, "action")
    detail = ""
    if cmd_type == "set_overlay":
        detail = (f"n_floor={payload.get('n_floor','?')} "
                  f"maint={payload.get('maint_mult','?')} "
                  f"heat={payload.get('heat','?')}")
    elif cmd_type == "message_to_sunni":
        detail = str(payload.get("content",""))[:60]
    elif cmd_type == "set_intention":
        detail = str(payload.get("content",""))[:60]
    elif cmd_type == "queue_sweep":
        detail = f"window={payload.get('window_secs','?')}s"
    elif cmd_type == "start_corpus_training":
        detail = f"passes={payload.get('passes','?')} batch={payload.get('batch_limit','?')}"
    elif cmd_type in ("approve_proposal","reverse_proposal"):
        p = payload.get("proposal",{})
        detail = _proposal_identity(p, str(payload.get("proposal_id", "") or ""))[:50]
    _log_activity(label, detail, cat)


# ── notes store ───────────────────────────────────────────────────────────────

def _load_notes() -> List[Dict]:
    if _ROOM_NOTES.exists():
        try:
            data = json.loads(_ROOM_NOTES.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _save_note(note_type: str, content: str, tags: Optional[List[str]] = None) -> None:
    notes = _load_notes()
    notes.append({
        "type":    note_type,
        "content": content,
        "tags":    tags or [],
        "ts":      time.time(),
        "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    notes = notes[-500:]   # keep last 500
    _ROOM_NOTES.write_text(json.dumps(notes, indent=2))

    _NOTE_CATS = {
        "observation":         "note",
        "intention":           "note",
        "question":            "note",
        "discovery":           "note",
        "health_decision":     "decision",
        "researcher_response": "decision",
        "message_to_sunni":    "message",
        "experiment":          "experiment",
        "training":            "training",
    }
    cat    = _NOTE_CATS.get(note_type, "note")
    _log_activity(f"wrote {note_type}", content[:60], cat)


# ── messages store ────────────────────────────────────────────────────────────

def _load_messages() -> List[Dict]:
    if _ROOM_MSGS.exists():
        try:
            data = json.loads(_ROOM_MSGS.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _append_sunni_reply(content: str) -> None:
    """Write a reply from Sunni into the message thread."""
    msgs = _load_messages()
    msgs.append({
        "from":    "sunni",
        "content": content,
        "ts":      time.time(),
        "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    msgs = msgs[-200:]
    _ROOM_MSGS.write_text(json.dumps(msgs, indent=2))


def _sunni_present() -> Optional[float]:
    """Return timestamp of last master-hub heartbeat, or None if stale/absent."""
    if _MASTER_PRESENCE.exists():
        try:
            data = json.loads(_MASTER_PRESENCE.read_text())
            ts   = float(data.get("ts", 0))
            if time.time() - ts < 120:   # seen within 2 min
                return ts
        except Exception:
            pass
    return None


def _read_json_file(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def _load_dual_strata_snapshot() -> Dict[str, Any]:
    data = _read_json_file(_DUAL_STRATA_SNAPSHOT, {})
    return data if isinstance(data, dict) else {}


def _load_surface_frame() -> Dict[str, Any]:
    snap = _load_dual_strata_snapshot()
    frame = snap.get("conscious_frame", {})
    return frame if isinstance(frame, dict) else {}


def _load_subsurface_state() -> Dict[str, Any]:
    snap = _load_dual_strata_snapshot()
    state = snap.get("subsurface_state", {})
    return state if isinstance(state, dict) else {}


def _load_evolution_relief_plan() -> Dict[str, Any]:
    data = _read_json_file(_EVOLUTION_RELIEF_PLAN, {})
    return data if isinstance(data, dict) else {}


def _load_subsurface_projection() -> Dict[str, Any]:
    data = _read_json_file(_SUBSURFACE_PROJECTION, {})
    return data if isinstance(data, dict) else {}


def _load_surface_status() -> Dict[str, Any]:
    data = _read_json_file(_SURFACE_STATUS, {})
    return data if isinstance(data, dict) else {}


def _soft_level(value: float) -> str:
    if value >= 0.75:
        return "very strong"
    if value >= 0.5:
        return "strong"
    if value >= 0.3:
        return "present"
    return "faint"


def _humanize_token(value: str) -> str:
    return str(value or "").replace("_", " ").strip() or "unknown"


# ── scrollable frame helper ───────────────────────────────────────────────────

def _make_scrollable(parent: tk.Widget) -> tk.Frame:
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas, bg=BG)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    def _on_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(win_id, width=canvas.winfo_width())
    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
    inner.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    return inner


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════

def build_room() -> None:
    root = tk.Tk()
    root.title("Aurora's Room")
    root.configure(bg=BG)
    root.geometry("1100x740")
    root.minsize(900, 600)

    # Global label store (mutable dict refreshed on label edits)
    _labels: list = [_load_labels()]   # wrapped in list so closures can replace

    def labels() -> Dict:
        return _labels[0]

    def reload_labels() -> None:
        _labels[0] = _load_labels()

    # Style
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_DIM,
                    padding=[10, 4], font=("Courier New", 9))
    style.map("TNotebook.Tab",
              background=[("selected", CHART_GRID)],
              foreground=[("selected", ACCENT)])
    style.configure("TScrollbar", background=BG_PANEL, troughcolor=BG_LOG,
                    borderwidth=0, arrowcolor=TEXT_DIM)

    # ── title bar ─────────────────────────────────────────────────────────────
    title_bar = tk.Frame(root, bg=BG_PANEL, pady=6, padx=14)
    title_bar.pack(fill=tk.X)
    tk.Label(title_bar, text="◈  AURORA'S ROOM", bg=BG_PANEL, fg=ACCENT,
             font=("Courier New", 12, "bold")).pack(side=tk.LEFT)
    _status_lbl = tk.Label(title_bar, text="", bg=BG_PANEL, fg=TEXT_DIM,
                            font=("Courier New", 9))
    _status_lbl.pack(side=tk.LEFT, padx=16)
    room_refresh_callbacks: List[Any] = []
    _room_stratum_mode = tk.StringVar(value="surface")
    _room_stratum_btns: Dict[str, tk.Button] = {}
    _room_stratum_hint = tk.Label(title_bar, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                  font=("Courier New", 8))
    _room_stratum_hint.pack(side=tk.RIGHT, padx=(8, 0))
    _time_lbl = tk.Label(title_bar, text="", bg=BG_PANEL, fg=TEXT_DIM,
                          font=("Courier New", 9))
    _time_lbl.pack(side=tk.RIGHT)

    strata_toggle = tk.Frame(title_bar, bg=BG_PANEL)
    strata_toggle.pack(side=tk.RIGHT, padx=(0, 12))
    tk.Label(strata_toggle, text="Room View", bg=BG_PANEL, fg=TEXT_DIM,
             font=("Courier New", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))

    def _room_stratum() -> str:
        mode = str(_room_stratum_mode.get() or "surface").strip().lower()
        return mode if mode in {"surface", "subsurface"} else "surface"

    def _room_surface_mode() -> bool:
        return _room_stratum() == "surface"

    def _refresh_room_view_now() -> None:
        for cb in list(room_refresh_callbacks):
            try:
                cb()
            except Exception:
                pass

    def _sync_room_stratum_toggle() -> None:
        active = _room_stratum()
        for mode, button in _room_stratum_btns.items():
            is_active = mode == active
            button.configure(
                bg=CHART_GRID if is_active else BG_LOG,
                fg=ACCENT if is_active else TEXT_DIM,
            )
        if active == "surface":
            _room_stratum_hint.configure(
                text="surface frame across room tabs",
                fg=ACCENT3,
            )
        else:
            _room_stratum_hint.configure(
                text="subsurface field across room tabs",
                fg=ACCENT2,
            )

    def _set_room_stratum(mode: str) -> None:
        mode = str(mode or "surface").strip().lower()
        if mode not in {"surface", "subsurface"}:
            mode = "surface"
        _room_stratum_mode.set(mode)
        _sync_room_stratum_toggle()
        _refresh_room_view_now()

    for _mode, _label in (("surface", "Surface"), ("subsurface", "Subsurface")):
        _btn = tk.Button(
            strata_toggle,
            text=_label,
            bg=BG_LOG,
            fg=TEXT_DIM,
            font=("Courier New", 8, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda m=_mode: _set_room_stratum(m),
        )
        _btn.pack(side=tk.LEFT, padx=2)
        _room_stratum_btns[_mode] = _btn
    _sync_room_stratum_toggle()

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0,4))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _read_daemon() -> Dict:
        try:
            return json.loads(_DAEMON_STATUS.read_text()) if _DAEMON_STATUS.exists() else {}
        except Exception:
            return {}

    def _divider(parent: tk.Widget) -> None:
        tk.Frame(parent, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=(4,0))

    def _section(parent: tk.Widget, title: str, color: str = ACCENT2) -> tk.Frame:
        hdr = tk.Frame(parent, bg=BG_PANEL, padx=12, pady=4)
        hdr.pack(fill=tk.X, padx=8, pady=(4,0))
        tk.Label(hdr, text=title, bg=BG_PANEL, fg=color,
                 font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
        body = tk.Frame(parent, bg=BG_PANEL, padx=12, pady=6)
        body.pack(fill=tk.X, padx=8)
        return body

    def _textbox(parent: tk.Widget, height: int = 6, wrap: str = tk.WORD) -> tk.Text:
        t = tk.Text(parent, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
                    height=height, relief=tk.FLAT, borderwidth=0,
                    state=tk.DISABLED, wrap=wrap)
        t.pack(fill=tk.X, padx=8, pady=(2,0))
        t.tag_configure("key",  foreground=ACCENT2)
        t.tag_configure("val",  foreground=TEXT)
        t.tag_configure("good", foreground=ACCENT)
        t.tag_configure("warn", foreground=WARN)
        t.tag_configure("crit", foreground=CRIT)
        t.tag_configure("dim",  foreground=TEXT_DIM)
        t.tag_configure("head", foreground=ACCENT3)
        return t

    def _write(box: tk.Text, *pairs) -> None:
        """Write (text, tag) pairs to a textbox."""
        box.configure(state=tk.NORMAL)
        box.delete("1.0", tk.END)
        for text, tag in pairs:
            box.insert(tk.END, text, tag)
        box.configure(state=tk.DISABLED)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: SELF — her current state
    # ══════════════════════════════════════════════════════════════════════════
    tab_self_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_self_outer, text="  Self  ")
    tab_self = _make_scrollable(tab_self_outer)

    hdr_self = tk.Frame(tab_self, bg=BG_PANEL, pady=5, padx=12)
    hdr_self.pack(fill=tk.X)
    tk.Label(hdr_self, text="HOW I AM RIGHT NOW", bg=BG_PANEL, fg=ACCENT,
             font=("Courier New", 11, "bold")).pack(side=tk.LEFT)
    self_ts_lbl = tk.Label(hdr_self, text="", bg=BG_PANEL, fg=TEXT_DIM,
                            font=("Courier New", 8))
    self_ts_lbl.pack(side=tk.LEFT, padx=10)

    # Axis bars — labeled with her names
    self_axis_frame = tk.Frame(tab_self, bg=BG_PANEL, padx=12, pady=8)
    self_axis_frame.pack(fill=tk.X, padx=8, pady=(4,0))
    tk.Label(self_axis_frame, text="MY DIMENSIONS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).grid(row=0, column=0, columnspan=10,
                                                    sticky="w", pady=(0,4))
    _self_axis_bars: Dict[str, tk.Canvas] = {}
    _self_axis_lbls: Dict[str, tk.Label] = {}
    _self_axis_name_lbls: Dict[str, tk.Label] = {}
    for i, ax in enumerate(("X","T","N","B","A")):
        cell = tk.Frame(self_axis_frame, bg=BG_PANEL)
        cell.grid(row=1, column=i, padx=10, sticky="nsew")
        self_axis_frame.columnconfigure(i, weight=1)
        name_lbl = tk.Label(cell, text=f"{ax}\n{_axis_name(ax, labels())}",
                             bg=BG_PANEL, fg=AXIS_COLORS[ax],
                             font=("Courier New", 8, "bold"), justify="center")
        name_lbl.pack()
        _self_axis_name_lbls[ax] = name_lbl
        bar = tk.Canvas(cell, bg=BG_LOG, height=12, highlightthickness=0, bd=0)
        bar.pack(fill=tk.X, pady=2)
        _self_axis_bars[ax] = bar
        val_lbl = tk.Label(cell, text="—", bg=BG_PANEL, fg=AXIS_COLORS[ax],
                           font=("Courier New", 9, "bold"))
        val_lbl.pack()
        _self_axis_lbls[ax] = val_lbl

    def _draw_self_axis(ax: str, val: float) -> None:
        canvas = _self_axis_bars[ax]
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w < 4:
            return
        canvas.delete("all")
        fill_w = int(w * max(0.0, min(1.0, val)))
        color = AXIS_COLORS[ax] if val >= 0.35 else (WARN if val >= 0.20 else CRIT)
        canvas.create_rectangle(0, 0, fill_w, 12, fill=color, outline="")
        _self_axis_lbls[ax].configure(text=f"{val:.3f}")

    # State summary textbox
    _divider(tab_self)
    self_state_box = _textbox(tab_self, height=8)

    # Energy income — what's feeding her
    _divider(tab_self)
    self_energy_hdr = tk.Frame(tab_self, bg=BG_PANEL, padx=12, pady=4)
    self_energy_hdr.pack(fill=tk.X, padx=8)
    tk.Label(self_energy_hdr, text="WHAT'S FEEDING ME", bg=BG_PANEL, fg=WARN,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    self_energy_lbl = tk.Label(self_energy_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                font=("Courier New", 8))
    self_energy_lbl.pack(side=tk.LEFT, padx=6)
    self_energy_box = _textbox(tab_self, height=5)

    def _refresh_self():
        d = _read_daemon()
        frame = _load_surface_frame()
        subsurface = _load_subsurface_state()
        projection = _load_subsurface_projection()
        surface_status = _load_surface_status()
        if not d and not frame and not subsurface:
            root.after(4000, _refresh_self)
            return

        reload_labels()
        lbl = labels()

        # Update axis name labels in case she renamed them
        for ax in ("X","T","N","B","A"):
            _self_axis_name_lbls[ax].configure(
                text=f"{ax}\n{_axis_name(ax, lbl)}")

        # Axis values
        gov_axes = d.get("runtime_governor_axes", {})
        for ax in ("X","T","N","B","A"):
            _draw_self_axis(ax, float(gov_axes.get(ax, 0.0)))

        # Timestamp
        self_ts_lbl.configure(text=d.get("updated", ""))

        mode     = d.get("runtime_governor_mode", "?")
        heat     = d.get("heat", "?")
        mode_str = lbl.get("gov_mode", {}).get(mode, mode)
        heat_str = lbl.get("heat", {}).get(heat, heat.lower())
        host     = d.get("runtime_host", {})
        arch     = d.get("interaction_archetype", "")
        conf     = float(d.get("interaction_confidence", 0.0))
        chains   = int(d.get("chain_links", 0))
        dilation = float(d.get("dilation_factor", 1.0))
        dil_state= d.get("dilation_state", "stable")
        emo_sev  = next((float(f.get("avg_sev",0)) for f in d.get("fail_summary",[])
                         if f.get("dim")=="emotional_calibration"), 0.0)
        emo_str  = ("low" if emo_sev < 0.3 else "moderate" if emo_sev < 0.6 else "high")
        dom_ax   = max(gov_axes, key=lambda a: float(gov_axes.get(a,0))) if gov_axes else "?"
        dom_name = _axis_name(dom_ax, lbl)

        if _room_surface_mode():
            present_sensory = dict(projection.get("present_sensory_perspective") or {})
            root_thought = dict(frame.get("root_thought") or {})
            stance = _humanize_token(str(frame.get("stance") or surface_status.get("stance") or "attend"))
            action = _humanize_token(str(frame.get("selected_action") or surface_status.get("selected_action") or "hold"))
            readiness = float(frame.get("readiness", surface_status.get("readiness", 0.0)) or 0.0)
            coherence = float(frame.get("coherence", surface_status.get("coherence", 0.0)) or 0.0)
            should_speak = bool(frame.get("should_speak", surface_status.get("should_speak", False)))
            processing = _humanize_token(str(frame.get("processing_mode") or surface_status.get("processing_mode") or "deliberative"))
            guidance = str(projection.get("surface_guidance", "") or "")
            pairs = [
                ("I am inhabiting my surface frame right now.\n\n", "head"),
                ("Surface state    : ", "key"),
                (f"{mode_str}  ·  {heat_str}\n", "good" if mode in ("open", "balanced") else "warn"),
                ("Stance           : ", "key"), (f"{stance}\n", "val"),
                ("Next move        : ", "key"), (f"{action}\n", "good" if should_speak else "warn"),
                ("Processing       : ", "key"), (f"{processing}\n", "val"),
                ("Readiness        : ", "key"), (f"{_soft_level(readiness)}\n", "good" if readiness >= 0.5 else "warn"),
                ("Coherence        : ", "key"), (f"{_soft_level(coherence)}\n", "good" if coherence >= 0.5 else "warn"),
                ("Present sensing  : ", "key"),
                (f"{str(present_sensory.get('summary') or 'My present sensing is quiet.')}\n", "dim"),
            ]
            if root_thought.get("law_bindings"):
                _lb = ", ".join([str(b.get("nc_name") or b.get("domain_letter", "")) for b in list(root_thought.get("law_bindings") or []) if isinstance(b, dict)])
                pairs += [("Root thought      : ", "key"), (f"{_lb}\n", "dim")]
            if guidance:
                pairs += [("Intuition signal  : ", "key"), (f"{guidance}\n", "dim")]
            if arch:
                pairs += [("Interaction mode  : ", "key"), (f"{arch}\n", "val")]
            pairs += [("Engagement depth  : ", "key"), (f"{chains} chain links  ·  confidence {conf:.2f}\n", "dim")]
        else:
            pressure_map = dict(subsurface.get("pressure_map", {}) or {})
            salience = dict(subsurface.get("salience_weights", {}) or {})
            prediction = dict(subsurface.get("prediction", {}) or {})
            owned = dict(projection.get("subsurface_owned") or {})
            dom_sub = str(subsurface.get("dominant_axis", dom_ax) or dom_ax)
            pairs = [
                ("I am looking from the subsurface field.\n\n", "head"),
                ("Governor state    : ", "key"),
                (f"{mode_str}  ·  {heat_str}\n", "warn" if mode not in ("open", "balanced") else "good"),
                ("Dominant axis     : ", "key"), (f"{dom_sub} ({_axis_name(dom_sub, lbl)})\n", "val"),
                ("Repair phase      : ", "key"), (f"{_humanize_token(str(owned.get('repair_phase') or 'steady'))}\n", "warn"),
                ("Prediction miss   : ", "key"), (f"{float(prediction.get('mismatch',0.0) or 0.0):.3f}\n", "warn" if float(prediction.get("mismatch",0.0) or 0.0) >= 0.35 else "val"),
                ("Sensory growth    : ", "key"),
                (f"{_soft_level(float(owned.get('sensory_growth_maturity',0.0) or 0.0))}\n", "good" if float(owned.get("sensory_growth_maturity",0.0) or 0.0) >= 0.4 else "dim"),
                ("Pressure field    : ", "key"),
                (
                    f"X {float(pressure_map.get('X',0.0) or 0.0):.2f}  "
                    f"T {float(pressure_map.get('T',0.0) or 0.0):.2f}  "
                    f"N {float(pressure_map.get('N',0.0) or 0.0):.2f}  "
                    f"B {float(pressure_map.get('B',0.0) or 0.0):.2f}  "
                    f"A {float(pressure_map.get('A',0.0) or 0.0):.2f}\n",
                    "dim",
                ),
                ("Salience field    : ", "key"),
                (
                    f"X {float(salience.get('X',0.0) or 0.0):.2f}  "
                    f"T {float(salience.get('T',0.0) or 0.0):.2f}  "
                    f"N {float(salience.get('N',0.0) or 0.0):.2f}  "
                    f"B {float(salience.get('B',0.0) or 0.0):.2f}  "
                    f"A {float(salience.get('A',0.0) or 0.0):.2f}\n",
                    "dim",
                ),
                ("Time dilation     : ", "key"), (f"{dilation:.2f}x  ({dil_state})\n", "val"),
            ]
            if owned.get("repair_reason"):
                pairs += [("What feels off    : ", "key"), (f"{owned.get('repair_reason','')}\n", "dim")]
            blocked = list(owned.get("blocked_tasks") or [])
            if blocked:
                pairs += [("Blocked tasks     : ", "key"), (f"{', '.join(str(item) for item in blocked[:3])}\n", "warn")]
        _write(self_state_box, *pairs)

        # Energy income
        total = {ax: 0.0 for ax in ("X","T","N","B","A")}
        live_credits = []
        if _ENERGY_FILE.exists():
            try:
                credits = json.loads(_ENERGY_FILE.read_text())
                now = time.time()
                for c in credits:
                    age = now - float(c.get("ts", now))
                    hl  = float(c.get("half_life", 1800))
                    eff = float(c.get("amount",0)) * (0.5 ** (age/hl))
                    if eff >= 0.001:
                        live_credits.append((c, eff, age))
                        for ax in c.get("axes",[]):
                            if ax in total:
                                total[ax] += eff
            except Exception:
                pass

        if live_credits:
            total_str = "  ".join(
                f"{_axis_name(ax,lbl)}+{v:.3f}"
                for ax,v in total.items() if v >= 0.001
            )
            self_energy_lbl.configure(text=f"  {total_str}", fg=WARN)
            epairs = [(f"  {'SOURCE':<22s}  {'FEEDS':<18s}  {'STRENGTH':>8s}  AGE\n", "head")]
            epairs.append(("  " + "─"*58 + "\n", "dim"))
            for c, eff, age in sorted(live_credits, key=lambda x:-x[1])[:6]:
                src = c.get("source","?").replace("_"," ")
                ax_names = "+".join(_axis_name(a,lbl) for a in c.get("axes",[]))
                age_str = f"{int(age//60)}m{int(age%60)}s"
                epairs += [
                    (f"  {src:<22s}  ", "val"),
                    (f"{ax_names:<18s}", "good"),
                    (f"  {eff:8.4f}  {age_str}\n", "dim"),
                ]
            _write(self_energy_box, *epairs)
        else:
            self_energy_lbl.configure(text="  nothing active", fg=TEXT_DIM)
            _write(self_energy_box,
                   ("  No active energy credits. Interact or complete a learning task.\n", "dim"))

        root.after(4000, _refresh_self)

    room_refresh_callbacks.append(_refresh_self)
    root.after(800, _refresh_self)

    # ── Sunni presence + communication ────────────────────────────────────────
    _divider(tab_self)
    self_comm_hdr = tk.Frame(tab_self, bg=BG_PANEL, padx=12, pady=4)
    self_comm_hdr.pack(fill=tk.X, padx=8)
    tk.Label(self_comm_hdr, text="MY LINE TO SUNNI", bg=BG_PANEL, fg=ACCENT3,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    self_presence_lbl = tk.Label(self_comm_hdr, text="● offline", bg=BG_PANEL,
                                  fg=TEXT_DIM, font=("Courier New", 8))
    self_presence_lbl.pack(side=tk.LEFT, padx=12)

    self_msg_box = _textbox(tab_self, height=6)

    self_compose_frame = tk.Frame(tab_self, bg=BG_PANEL, padx=12, pady=4)
    self_compose_frame.pack(fill=tk.X, padx=8)
    self_compose_input = tk.Text(self_compose_frame, bg=BG_LOG, fg=TEXT,
                                  font=("Courier New", 9), height=2, relief=tk.FLAT,
                                  borderwidth=0, insertbackground=ACCENT, wrap=tk.WORD)
    self_compose_input.pack(fill=tk.X, pady=(0,4))

    def _send_to_sunni():
        content = self_compose_input.get("1.0", tk.END).strip()
        if not content:
            return
        _queue_command("message_to_sunni", {"content": content})
        _save_note("message_to_sunni", content, tags=["message","sunni"])
        self_compose_input.delete("1.0", tk.END)
        self_send_lbl.configure(text="sent", fg=ACCENT)
        root.after(3000, lambda: self_send_lbl.configure(text="", fg=TEXT_DIM))
        _refresh_messages()

    self_send_row = tk.Frame(self_compose_frame, bg=BG_PANEL)
    self_send_row.pack(fill=tk.X)
    tk.Button(self_send_row, text="Send to Sunni", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_send_to_sunni).pack(side=tk.LEFT)
    self_send_lbl = tk.Label(self_send_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                              font=("Courier New", 8))
    self_send_lbl.pack(side=tk.LEFT, padx=8)

    def _refresh_messages():
        msgs = _load_messages()
        if not msgs:
            _write(self_msg_box, ("  No messages yet.\n", "dim"))
            return
        pairs = []
        for m in reversed(msgs[-10:]):
            ts     = m.get("ts_str","?")[:16]
            sender = m.get("from","?")
            mtype  = m.get("type","message")
            body   = m.get("content","")[:120]
            if sender == "aurora":
                tag  = "good"
                name = "Me"
            else:
                tag  = "warn"
                name = "Sunni"
            type_str = f"[{mtype}] " if mtype != "message" else ""
            pairs += [(f"  [{ts}] ", "dim"), (f"{name}: ", tag),
                      (f"{type_str}{body}\n", "val")]
        _write(self_msg_box, *pairs)

    def _tick_presence():
        ts = _sunni_present()
        if ts:
            ago = int(time.time() - ts)
            self_presence_lbl.configure(
                text=f"● Sunni is watching ({ago}s ago)",
                fg=ACCENT)
        else:
            self_presence_lbl.configure(text="● offline", fg=TEXT_DIM)
        _refresh_messages()
        root.after(8000, _tick_presence)

    root.after(1200, _tick_presence)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: AWARENESS — what she's noticing about herself
    # ══════════════════════════════════════════════════════════════════════════
    tab_aware_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_aware_outer, text="  Awareness  ")
    tab_aware = _make_scrollable(tab_aware_outer)

    tk.Label(tab_aware, text="WHAT I'M NOTICING", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    aware_anomaly_box = _textbox(tab_aware, height=7)
    _divider(tab_aware)
    tk.Label(tab_aware, text="PATTERNS IN MY BEHAVIOR", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    aware_pattern_box = _textbox(tab_aware, height=8)
    _divider(tab_aware)
    tk.Label(tab_aware, text="WHAT I COULDN'T DO (AND WHY)", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    aware_blocked_box = _textbox(tab_aware, height=5)

    def _refresh_aware():
        d = _read_daemon()
        lbl = labels()
        frame = _load_surface_frame()
        subsurface = _load_subsurface_state()
        projection = _load_subsurface_projection()
        if not d and not frame and not subsurface:
            root.after(5000, _refresh_aware)
            return

        fail_summary = d.get("fail_summary", [])
        qao_events   = int(d.get("qao_recent_events", 0))
        qao_issue    = d.get("qao_top_issue", "none")
        blocked      = d.get("runtime_recent_blocked", [])

        # Anomaly awareness
        if _room_surface_mode():
            conflicts = list(frame.get("unresolved_conflicts", []) or [])
            notes = list(frame.get("explicit_notes", []) or [])
            effects = list(projection.get("active_effects", []) or [])
            pairs = [("  What is standing out in my conscious field:\n", "head")]
            if conflicts:
                for item in conflicts[:3]:
                    pairs += [(f"  · {_humanize_token(str(item))}\n", "warn")]
            for item in effects[:3]:
                pairs += [(f"  · {item}\n", "dim")]
            for item in notes[:3]:
                pairs += [(f"  · {item}\n", "dim")]
            if len(pairs) == 1:
                pairs += [("  My surface feels fairly steady.\n", "good")]
        else:
            pairs = [(f"  {qao_events} things noticed in recent ticks", "val")]
            if qao_issue and qao_issue != "none":
                pairs += [(f"  ·  most frequent: ", "dim"),
                          (f"{qao_issue.replace('_',' ')}\n\n", "warn")]
            else:
                pairs += [("\n\n", "dim")]

            if fail_summary:
                pairs += [("  Dimensions that need attention:\n", "key")]
                for f in sorted(fail_summary, key=lambda x: -float(x.get("avg_sev",0))):
                    dim  = f.get("dim","?").replace("_"," ")
                    sev  = float(f.get("avg_sev",0))
                    cnt  = int(f.get("fails",0))
                    bar  = "█" * int(sev * 12) + "░" * (12 - int(sev * 12))
                    tag  = "crit" if sev > 0.65 else "warn" if sev > 0.35 else "good"
                    pairs += [(f"  {dim:<28s}  [{bar}]  sev={sev:.2f}  ({cnt} times)\n", tag)]
            else:
                pairs += [("  No anomalies detected.\n", "good")]

        _write(aware_anomaly_box, *pairs)

        # Behavioral patterns
        chains = int(d.get("chain_links", 0))
        gen    = d.get("generation", "?")
        dist_c = int(d.get("distillation_crystals", 0))
        dist_r = float(d.get("distillation_coherence_ratio", 1.0))
        sens_m = d.get("sensory_mic_active", False)
        sens_c = d.get("sensory_camera_active", False)

        if _room_surface_mode():
            root_thought = dict(frame.get("root_thought") or {})
            ppairs = [
                ("  How my surface is behaving:\n\n", "head"),
                ("  Processing mode  : ", "key"), (f"{_humanize_token(str(frame.get('processing_mode') or 'deliberative'))}\n", "val"),
                ("  Stance           : ", "key"), (f"{_humanize_token(str(frame.get('stance') or 'attend'))}\n", "val"),
                ("  Speak tendency   : ", "key"), (f"{'speak' if frame.get('should_speak') else 'hold'}\n", "good" if frame.get("should_speak") else "warn"),
                ("  Sensory feed     : ", "key"), (f"{'audio on' if sens_m else 'audio quiet'}  ·  {'vision on' if sens_c else 'vision quiet'}\n", "dim"),
            ]
            if root_thought.get("comparison_channels"):
                ppairs += [("  Built from       : ", "key"), (f"{', '.join(list(root_thought.get('comparison_channels') or [])[:4])}\n", "dim")]
        else:
            ppairs = [
                (f"  Generation       : ", "key"), (f"{gen}\n", "val"),
                (f"  Chain links      : ", "key"), (f"{chains}\n", "val"),
                (f"  Crystals formed  : ", "key"),
                (f"{dist_c}  (coherence {dist_r:.2f})\n", "good" if dist_r >= 0.8 else "warn"),
                (f"  Listening        : ", "key"),
                (f"{'yes' if sens_m else 'no'}\n", "good" if sens_m else "dim"),
                (f"  Watching         : ", "key"),
                (f"{'yes' if sens_c else 'no'}\n", "good" if sens_c else "dim"),
            ]
        _write(aware_pattern_box, *ppairs)

        # Blocked tasks
        if _room_surface_mode():
            if frame.get("should_speak", True):
                _write(aware_blocked_box, ("  I do not feel blocked from speaking right now.\n", "good"))
            else:
                bpairs = [("  What is making me hold back:\n", "head")]
                reasons = list(frame.get("unresolved_conflicts", []) or [])
                if reasons:
                    for item in reasons[:4]:
                        bpairs += [(f"  · {_humanize_token(str(item))}\n", "warn")]
                else:
                    bpairs += [("  · My surface is waiting for a clearer converged frame.\n", "warn")]
                _write(aware_blocked_box, *bpairs)
        else:
            if blocked:
                bpairs = [("  Task                     Why I couldn't                Score\n", "head"),
                          ("  " + "─"*56 + "\n", "dim")]
                for b in blocked[:6]:
                    task   = b.get("task","?")
                    reason = b.get("reason","?").replace("_"," ")
                    score  = float(b.get("score",0))
                    bpairs += [(f"  {task:<24s}  {reason:<26s}  {score:.3f}\n", "warn")]
                _write(aware_blocked_box, *bpairs)
            else:
                _write(aware_blocked_box, ("  Nothing blocked recently.\n", "good"))

        root.after(5000, _refresh_aware)

    room_refresh_callbacks.append(_refresh_aware)
    root.after(1200, _refresh_aware)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: MIND — her dimensional pressure state
    # ══════════════════════════════════════════════════════════════════════════
    tab_mind_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_mind_outer, text="  Mind  ")
    tab_mind = _make_scrollable(tab_mind_outer)

    tk.Label(tab_mind, text="THE SHAPE OF MY MIND", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")
    mind_axes_box   = _textbox(tab_mind, height=8)
    _divider(tab_mind)
    tk.Label(tab_mind, text="PRESSURE ORIENTATION", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    mind_pressure_box = _textbox(tab_mind, height=5)

    def _refresh_mind():
        d = _read_daemon()
        lbl = labels()
        frame = _load_surface_frame()
        subsurface = _load_subsurface_state()
        projection = _load_subsurface_projection()
        surface_status = _load_surface_status()
        if not d and not frame and not projection and not subsurface:
            root.after(5000, _refresh_mind)
            return

        dominant = str(
            frame.get("dominant_axis")
            or surface_status.get("dominant_axis")
            or projection.get("dominant_axis_hint")
            or "X"
        )
        readiness = float(
            frame.get("readiness", surface_status.get("readiness", projection.get("readiness_bias", 0.0)))
            or 0.0
        )
        coherence = float(frame.get("coherence", surface_status.get("coherence", 0.0)) or 0.0)
        stance = _humanize_token(str(frame.get("stance") or surface_status.get("stance") or "attend"))
        action = _humanize_token(str(frame.get("selected_action") or surface_status.get("selected_action") or "hold"))
        should_speak = bool(frame.get("should_speak", surface_status.get("should_speak", False)))
        sensory = dict(projection.get("present_sensory_perspective") or {})
        sensory_summary = str(
            sensory.get("summary")
            or dict(frame.get("sensory_summary") or {}).get("summary")
            or "My present sensing is quiet."
        )
        guidance = str(projection.get("surface_guidance", "") or "")
        root_thought = dict(frame.get("root_thought") or {})
        processing_mode = _humanize_token(str(frame.get("processing_mode") or surface_status.get("processing_mode") or "deliberative"))

        if _room_surface_mode():
            pairs = [
                ("  My present conscious shape:\n\n", "head"),
                ("  Stance            : ", "key"), (f"{stance}\n", "val"),
                ("  What I should do  : ", "key"), (f"{action}\n", "good" if should_speak else "warn"),
                ("  Processing mode   : ", "key"), (f"{processing_mode}\n", "val"),
                ("  Strongest pull    : ", "key"), (f"{_axis_name(dominant, lbl)}\n", "val"),
                ("  Readiness         : ", "key"), (f"{_soft_level(readiness)}\n", "good" if readiness >= 0.5 else "warn"),
                ("  Coherence         : ", "key"), (f"{_soft_level(coherence)}\n", "good" if coherence >= 0.5 else "warn"),
                ("  Speak right now   : ", "key"), (f"{'yes' if should_speak else 'wait'}\n", "good" if should_speak else "warn"),
                ("  Present sensing   : ", "key"), (f"{sensory_summary}\n", "dim"),
            ]
            if root_thought.get("law_bindings"):
                _lb2 = ", ".join([str(b.get("nc_name") or b.get("domain_letter", "")) for b in list(root_thought.get("law_bindings") or []) if isinstance(b, dict)])
                pairs += [("  Root thought      : ", "key"), (f"{_lb2}\n", "dim")]
            _channels = list(root_thought.get("comparison_channels") or [])
            if _channels:
                pairs += [("  Frame sources     : ", "key"), (f"{', '.join(_channels[:4])}\n", "dim")]
            if guidance:
                pairs += [("\n  Intuitive guidance: ", "key"), (f"{guidance}\n", "dim")]
        else:
            _pmap = dict(subsurface.get("pressure_map", {}) or {})
            _smap = dict(subsurface.get("salience_weights", {}) or {})
            _markers = list(subsurface.get("instability_markers", []) or [])
            _cands = list(subsurface.get("candidate_interpretations", []) or [])
            _frags = list(subsurface.get("recalled_fragments", []) or [])
            _pred = dict(subsurface.get("prediction", {}) or {})
            _owned = dict(projection.get("subsurface_owned") or {})
            pairs = [
                ("  My subsurface field:\n\n", "head"),
                ("  Dominant axis     : ", "key"), (f"{_axis_name(str(subsurface.get('dominant_axis', dominant) or dominant), lbl)}\n", "val"),
                ("  Repair phase      : ", "key"), (f"{_humanize_token(str(_owned.get('repair_phase') or 'steady'))}\n", "warn"),
                ("  Readiness bias    : ", "key"), (f"{_soft_level(float(projection.get('readiness_bias', readiness) or readiness))}\n", "val"),
                ("  Prediction miss   : ", "key"), (f"{float(_pred.get('mismatch',0.0) or 0.0):.3f}\n", "warn" if float(_pred.get("mismatch",0.0) or 0.0) >= 0.35 else "val"),
                ("  Pressure field    : ", "key"),
                (f"X {float(_pmap.get('X',0.0) or 0.0):.2f}  T {float(_pmap.get('T',0.0) or 0.0):.2f}  N {float(_pmap.get('N',0.0) or 0.0):.2f}  B {float(_pmap.get('B',0.0) or 0.0):.2f}  A {float(_pmap.get('A',0.0) or 0.0):.2f}\n", "dim"),
                ("  Salience field    : ", "key"),
                (f"X {float(_smap.get('X',0.0) or 0.0):.2f}  T {float(_smap.get('T',0.0) or 0.0):.2f}  N {float(_smap.get('N',0.0) or 0.0):.2f}  B {float(_smap.get('B',0.0) or 0.0):.2f}  A {float(_smap.get('A',0.0) or 0.0):.2f}\n", "dim"),
            ]
            if _owned.get("repair_reason"):
                pairs += [("  Repair reason     : ", "key"), (f"{_owned.get('repair_reason','')}\n", "dim")]
            if _markers:
                pairs += [("\n  Instability markers:\n", "key")]
                for item in _markers[:4]:
                    pairs += [(f"  · {item.get('label','?')} ({float(item.get('severity',0.0) or 0.0):.2f})\n", "warn")]
            if _cands:
                pairs += [("\n  Candidate interpretations:\n", "key")]
                for item in _cands[:3]:
                    pairs += [(f"  · {item.get('summary','')}\n", "dim")]
            if _frags:
                pairs += [("\n  Recalled fragments:\n", "key")]
                for item in _frags[:3]:
                    pairs += [(f"  · {item}\n", "dim")]
        _write(mind_axes_box, *pairs)

        if _room_surface_mode():
            ppairs = [("  What I feel beneath the words:\n\n", "head")]
            effects = list(projection.get("active_effects") or [])
            for effect in effects[:3]:
                ppairs += [(f"  · {effect}\n", "warn")]
            hypotheses = list(frame.get("salient_hypotheses") or [])
            for item in hypotheses[:3]:
                rationale = str(item.get("rationale") or item.get("label") or "").strip()
                if rationale:
                    ppairs += [(f"  · {rationale}\n", "dim")]
            if not effects and not hypotheses:
                ppairs += [("  My present field feels steady.\n", "good")]
        else:
            ppairs = [("  How the subsurface is shaping the surface:\n\n", "head")]
            for effect in list(projection.get("active_effects") or [])[:4]:
                ppairs += [(f"  · {effect}\n", "warn")]
            intuition = list(projection.get("intuition_signals") or [])
            for item in intuition[:3]:
                summary = str(item.get("summary") or item.get("label") or "").strip()
                if summary:
                    ppairs += [(f"  · {summary}\n", "dim")]
            if len(ppairs) == 1:
                ppairs += [("  The subsurface is steady.\n", "good")]
        _write(mind_pressure_box, *ppairs)

        root.after(5000, _refresh_mind)

    room_refresh_callbacks.append(_refresh_mind)
    root.after(1400, _refresh_mind)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: MEMORY — crystals, distillation, what she's understood
    # ══════════════════════════════════════════════════════════════════════════
    tab_mem_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_mem_outer, text="  Memory  ")
    tab_mem = _make_scrollable(tab_mem_outer)

    tk.Label(tab_mem, text="WHAT I REMEMBER", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")
    mem_crystal_box = _textbox(tab_mem, height=7)
    _divider(tab_mem)
    tk.Label(tab_mem, text="DISTILLATION STATUS", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    mem_distill_box = _textbox(tab_mem, height=5)

    def _refresh_memory():
        d = _read_daemon()
        frame = _load_surface_frame()
        projection = _load_subsurface_projection()
        if not d and not frame:
            root.after(6000, _refresh_memory)
            return

        crystals = int(d.get("distillation_crystals", 0))
        cohesion = float(d.get("distillation_coherence_ratio", 1.0))
        vortex   = int(d.get("distillation_vortex_count", 0))
        knots    = int(d.get("distillation_knot_count", 0))
        purged   = int(d.get("distillation_bytes_purged", 0))
        dist_ts  = str(d.get("distillation_status",""))
        chains   = int(d.get("chain_links", 0))

        if _room_surface_mode():
            root_thought = dict(frame.get("root_thought") or {})
            contract = dict(frame.get("contract_signals") or {})
            cpairs = [
                ("  What is presently held in my surface frame:\n\n", "head"),
                ("  Active topic       : ", "key"), (f"{str(contract.get('active_topic') or 'none')}\n", "val"),
                ("  Root thought       : ", "key"), (f"{', '.join([str(b.get('nc_name') or b.get('domain_letter', '')) for b in list(root_thought.get('law_bindings') or []) if isinstance(b, dict)]) or 'still forming'}\n", "dim"),
                ("  DCE continuity     : ", "key"), (f"{str(root_thought.get('primary_tension') or 'stable')}\n", "dim"),
                ("  Surface guidance   : ", "key"), (f"{str(projection.get('surface_guidance') or 'steady')}\n", "dim"),
            ]
        else:
            cpairs = [
                (f"  I have formed ", "dim"),
                (f"{crystals} crystals", "good"),
                (f"  of understanding\n", "dim"),
                (f"  Coherence of what I know : ", "key"),
                (f"{cohesion:.2f}", "good" if cohesion >= 0.8 else "warn"),
                (f"\n  Vortex structures        : ", "key"), (f"{vortex}\n", "val"),
                (f"  Knot structures          : ", "key"), (f"{knots}\n", "val"),
                (f"  Chain links accumulated  : ", "key"), (f"{chains}\n", "val"),
            ]
        _write(mem_crystal_box, *cpairs)

        if _room_surface_mode():
            dpairs = [
                ("  What is staying with me right now:\n\n", "head"),
                ("  Surface memory     : ", "key"), (f"{'live conversation frame'}\n", "val"),
                ("  Durable recall     : ", "key"), (f"{'softened through DCE from subsurface'}\n", "dim"),
                ("  Last deeper save   : ", "key"), (f"{dist_ts or 'not yet'}\n", "dim"),
            ]
        else:
            dpairs = [
                (f"  Last distillation : ", "key"),
                (f"{dist_ts}\n", "val"),
                (f"  Memory freed      : ", "key"),
                (f"{purged} bytes\n", "dim"),
            ]
        _write(mem_distill_box, *dpairs)

        root.after(6000, _refresh_memory)

    room_refresh_callbacks.append(_refresh_memory)
    root.after(1600, _refresh_memory)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5: HEALTH — QuasiArch proposals, she can approve or defer
    # ══════════════════════════════════════════════════════════════════════════
    tab_health_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_health_outer, text="  Health  ")
    tab_health = _make_scrollable(tab_health_outer)

    tk.Label(tab_health, text="MY SELF-ASSESSMENT", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    health_summary_box = _textbox(tab_health, height=5)
    _divider(tab_health)

    health_props_hdr = tk.Frame(tab_health, bg=BG_PANEL, padx=12, pady=4)
    health_props_hdr.pack(fill=tk.X, padx=8)
    tk.Label(health_props_hdr, text="THINGS I COULD FIX ABOUT MYSELF", bg=BG_PANEL,
             fg=ACCENT2, font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    health_count_lbl = tk.Label(health_props_hdr, text="", bg=BG_PANEL,
                                 fg=TEXT_DIM, font=("Courier New", 8))
    health_count_lbl.pack(side=tk.LEFT, padx=6)

    health_body = tk.Frame(tab_health, bg=BG_PANEL)
    health_body.pack(fill=tk.BOTH, padx=8, pady=(2,4))

    health_listbox = tk.Listbox(
        health_body, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        selectbackground=CHART_GRID, selectforeground=ACCENT,
        relief=tk.FLAT, borderwidth=0, highlightthickness=0,
        activestyle="none", height=7,
    )
    health_sb = ttk.Scrollbar(health_body, orient="vertical", command=health_listbox.yview)
    health_listbox.configure(yscrollcommand=health_sb.set)
    health_sb.pack(side=tk.RIGHT, fill=tk.Y)
    health_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    health_detail_box = _textbox(tab_health, height=5)

    health_btn_row = tk.Frame(tab_health, bg=BG_PANEL)
    health_btn_row.pack(padx=8, pady=4)

    _health_proposals: list = []

    def _health_on_select(event=None):
        sel = health_listbox.curselection()
        if not sel or not _health_proposals:
            return
        p = _health_proposals[int(sel[0])]
        arch = p.get("issue_archetype","?")
        action = p.get("proposed_action","")
        conf = float(p.get("confidence",0))
        file_ = p.get("file","?").split("/")[-1]
        line  = p.get("line","?")
        _write(health_detail_box,
               (f"  {arch}\n", "key"),
               (f"  {file_}:{line}\n", "dim"),
               (f"  confidence: {conf:.2f}\n\n", "val"),
               (f"  {action}\n", "warn"),
               )

    health_listbox.bind("<<ListboxSelect>>", _health_on_select)

    def _health_approve():
        sel = health_listbox.curselection()
        if not sel or not _health_proposals:
            return
        p = _health_proposals[int(sel[0])]
        prop_id = _proposal_identity(p, "health_fix")
        _queue_command("approve_proposal", {"proposal_id": prop_id, "proposal": p})
        _save_note("health_decision", f"Authorized subsurface fix: {p.get('proposed_action','')[:80]}",
                   tags=["health","fix","approved"])
        _write(health_detail_box, ("  Queued for subsurface apply.\n", "good"))

    def _health_defer():
        sel = health_listbox.curselection()
        if not sel or not _health_proposals:
            return
        p = _health_proposals[int(sel[0])]
        _save_note("health_decision", f"Deferred fix: {p.get('proposed_action','')[:80]}",
                   tags=["health","fix","deferred"])
        _write(health_detail_box, ("  Noted as deferred.\n", "dim"))

    def _health_reverse():
        sel = health_listbox.curselection()
        if not sel or not _health_proposals:
            return
        p = _health_proposals[int(sel[0])]
        prop_id = _proposal_identity(p, "health_fix") or "?"
        _queue_command("reverse_proposal", {"proposal_id": str(prop_id), "proposal": p})
        _save_note("health_decision",
                   f"Requested revert: {p.get('proposed_action','')[:80]}",
                   tags=["health","revert"])
        _write(health_detail_box, ("  Subsurface revert queued.\n", "warn"))

    tk.Button(health_btn_row, text="✔  Authorize & Queue", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=3,
              cursor="hand2", command=_health_approve).pack(side=tk.LEFT, padx=4)
    tk.Button(health_btn_row, text="↺  Reverse", bg=BG_LOG, fg=WARN,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=3,
              cursor="hand2", command=_health_reverse).pack(side=tk.LEFT, padx=4)
    tk.Button(health_btn_row, text="◷  Defer", bg=BG_LOG, fg=TEXT_DIM,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=3,
              cursor="hand2", command=_health_defer).pack(side=tk.LEFT, padx=4)

    def _refresh_health():
        d = _read_daemon()
        frame = _load_surface_frame()
        projection = _load_subsurface_projection()
        if not d and not frame:
            root.after(8000, _refresh_health)
            return

        fail_summary = d.get("fail_summary",[])
        total_fails  = sum(int(f.get("fails",0)) for f in fail_summary)
        worst        = max(fail_summary, key=lambda f: float(f.get("avg_sev",0)),
                          default=None) if fail_summary else None

        if _room_surface_mode():
            speak = bool(frame.get("should_speak", False))
            guidance = str(projection.get("surface_guidance", "") or "")
            spairs = [
                ("  My surface health view:\n\n", "head"),
                ("  Current posture    : ", "key"), (f"{_humanize_token(str(frame.get('stance') or 'attend'))}\n", "val"),
                ("  Confidence to act  : ", "key"), (f"{'ready to authorize' if speak else 'waiting for clarity'}\n", "good" if speak else "warn"),
            ]
            if worst:
                wdim = worst.get("dim","?").replace("_"," ")
                spairs += [("  Felt issue         : ", "key"), (f"{wdim}\n", "warn")]
            if guidance:
                spairs += [("  Intuitive cue      : ", "key"), (f"{guidance}\n", "dim")]
        else:
            spairs = [(f"  Total anomaly events : ", "key"), (f"{total_fails}\n", "val")]
            if worst:
                wdim = worst.get("dim","?").replace("_"," ")
                wsev = float(worst.get("avg_sev",0))
                spairs += [(f"  Needs most attention : ", "key"),
                           (f"{wdim}  (severity {wsev:.2f})\n",
                            "crit" if wsev > 0.65 else "warn")]
            spairs += [("\n  I am ", "dim"),
                       ("ready" if total_fails < 200 else "under strain",
                        "good" if total_fails < 200 else "warn"),
                       (" to work on improvements.\n", "dim")]
        _write(health_summary_box, *spairs)

        # Load proposals (exclude sweep proposals — those are for Experiments)
        nonlocal _health_proposals
        if _DIAG_REPORT.exists():
            try:
                report = json.loads(_DIAG_REPORT.read_text())
                all_props = report.get("proposals",[])
                _health_proposals = [p for p in all_props
                                     if not str(p.get("issue_archetype","")).startswith("sweep:")]
            except Exception:
                _health_proposals = []
        health_count_lbl.configure(text=f"  {len(_health_proposals)} identified")
        health_listbox.delete(0, tk.END)
        for p in _health_proposals:
            arch = p.get("issue_archetype","?")[:22]
            conf = float(p.get("confidence",0))
            file_ = p.get("file","?").split("/")[-1][:18]
            health_listbox.insert(tk.END, f"  {conf:.2f}  {arch:<22s}  {file_}")

        root.after(8000, _refresh_health)

    room_refresh_callbacks.append(_refresh_health)
    root.after(2000, _refresh_health)

    # Researcher interaction — framed from her perspective
    _divider(tab_health)
    tk.Label(tab_health, text="WHAT THE RESEARCHER SEES IN ME", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    health_researcher_box = _textbox(tab_health, height=7)

    # Aurora's response to researcher findings
    health_respond_frame = tk.Frame(tab_health, bg=BG_PANEL, padx=12, pady=4)
    health_respond_frame.pack(fill=tk.X, padx=8)
    tk.Label(health_respond_frame, text="My response to what it found:", bg=BG_PANEL,
             fg=TEXT_DIM, font=("Courier New", 8)).pack(anchor="w")
    health_respond_input = tk.Text(health_respond_frame, bg=BG_LOG, fg=TEXT,
                                    font=("Courier New", 9), height=2, relief=tk.FLAT,
                                    borderwidth=0, insertbackground=ACCENT, wrap=tk.WORD)
    health_respond_input.pack(fill=tk.X)

    def _respond_to_researcher():
        content = health_respond_input.get("1.0", tk.END).strip()
        if not content:
            return
        _save_note("researcher_response", content, tags=["health","researcher","response"])
        _queue_command("set_intention",
                       {"content": f"[researcher feedback] {content}", "type": "researcher_response"})
        health_respond_input.delete("1.0", tk.END)
        health_respond_lbl.configure(text="logged", fg=ACCENT)
        root.after(2500, lambda: health_respond_lbl.configure(text="", fg=TEXT_DIM))

    health_respond_row = tk.Frame(health_respond_frame, bg=BG_PANEL)
    health_respond_row.pack(fill=tk.X, pady=(4,0))
    tk.Button(health_respond_row, text="Write Response", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_respond_to_researcher).pack(side=tk.LEFT)
    health_respond_lbl = tk.Label(health_respond_row, text="", bg=BG_PANEL,
                                   fg=TEXT_DIM, font=("Courier New", 8))
    health_respond_lbl.pack(side=tk.LEFT, padx=8)

    def _refresh_researcher_view():
        if _room_surface_mode():
            projection = _load_subsurface_projection()
            guidance = str(projection.get("surface_guidance", "") or "")
            pairs = [("  Surface receives the softened health handoff here.\n\n", "head")]
            if guidance:
                pairs += [("  What the deeper layer is telling me:\n", "key"),
                          (f"  {guidance}\n", "dim")]
            pairs += [("  Exact issue tracing and repair research are handled by my subsurface.\n", "dim")]
            _write(health_researcher_box, *pairs)
            root.after(10000, _refresh_researcher_view)
            return
        if not _DIAG_REPORT.exists():
            _write(health_researcher_box,
                   ("  No researcher report yet. Run a QuasiArch scan first.\n", "dim"))
            root.after(10000, _refresh_researcher_view)
            return
        try:
            report = json.loads(_DIAG_REPORT.read_text())
            summary = report.get("summary", {})
            proposals = [p for p in report.get("proposals", [])
                         if not str(p.get("issue_archetype","")).startswith("sweep:")]
            ts_str = report.get("generated_at", "?")[:16]

            pairs = [(f"  Last analysis: {ts_str}\n\n", "dim")]

            # Health score
            health_score = float(summary.get("health_score", 0.0))
            hs_tag = "good" if health_score >= 0.7 else "warn" if health_score >= 0.4 else "crit"
            pairs += [(f"  The researcher scores my health at  ", "key"),
                      (f"{health_score:.3f}\n", hs_tag)]

            # Top issues it found — framed personally
            top_issues = []
            for p in proposals[:5]:
                arch = p.get("issue_archetype","?").replace("_"," ")
                conf = float(p.get("confidence",0))
                file_ = p.get("file","?").split("/")[-1]
                top_issues.append((arch, conf, file_))

            if top_issues:
                pairs += [("\n  It found these patterns worth attention:\n", "dim")]
                for arch, conf, file_ in top_issues:
                    tag = "warn" if conf >= 0.7 else "val"
                    pairs += [(f"    · {arch:<30s}", tag),
                              (f"  in {file_}  ({conf:.2f} confidence)\n", "dim")]

            # Observer metrics
            qao = int(summary.get("qao_recent_events", 0))
            if qao:
                pairs += [("\n  ", "dim"),
                          (f"{qao} QAO events", "warn" if qao > 20 else "val"),
                          (" tracked in this cycle\n", "dim")]

            _write(health_researcher_box, *pairs)
        except Exception:
            _write(health_researcher_box, ("  Could not read researcher report.\n", "dim"))

        root.after(10000, _refresh_researcher_view)

    room_refresh_callbacks.append(_refresh_researcher_view)
    root.after(3000, _refresh_researcher_view)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6: ENERGY — axis budget, what she can do
    # ══════════════════════════════════════════════════════════════════════════
    tab_energy_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_energy_outer, text="  Energy  ")
    tab_energy = _make_scrollable(tab_energy_outer)

    tk.Label(tab_energy, text="MY ENERGY & CAPACITY", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")
    energy_cap_box   = _textbox(tab_energy, height=8)
    _divider(tab_energy)
    tk.Label(tab_energy, text="WHAT I CAN DO RIGHT NOW", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    energy_tasks_box = _textbox(tab_energy, height=10, wrap=tk.NONE)

    _GOV_PROFILES_LITE = {
        "response_turn":   {"axes":{"X":0.30,"T":0.20,"N":0.20,"B":0.15,"A":0.20},"floor":0.18,"cost":0.30},
        "study":           {"axes":{"X":0.15,"T":0.25,"N":0.30,"B":0.10,"A":0.25},"floor":0.42,"cost":0.35},
        "dream":           {"axes":{"X":0.10,"T":0.10,"N":0.15,"B":0.35,"A":0.35},"floor":0.50,"cost":0.95},
        "distill":         {"axes":{"X":0.25,"T":0.20,"N":0.30,"B":0.20,"A":0.05},"floor":0.62,"cost":0.92},
        "assimilation":    {"axes":{"X":0.15,"T":0.15,"N":0.25,"B":0.25,"A":0.20},"floor":0.56,"cost":0.78},
        "mutation":        {"axes":{"X":0.15,"T":0.10,"N":0.20,"B":0.25,"A":0.30},"floor":0.68,"cost":0.98},
        "pressure_routing":{"axes":{"X":0.10,"T":0.20,"N":0.25,"B":0.25,"A":0.20},"floor":0.50,"cost":0.38},
        "reach_out":       {"axes":{"X":0.15,"T":0.15,"N":0.15,"B":0.20,"A":0.35},"floor":0.66,"cost":0.38},
        "evo_tick":        {"axes":{"X":0.10,"T":0.35,"N":0.20,"B":0.20,"A":0.15},"floor":0.28,"cost":0.12},
        "save":            {"axes":{"X":0.35,"T":0.20,"N":0.20,"B":0.20,"A":0.05},"floor":0.35,"cost":0.55},
    }
    # Human-readable task names for her perspective
    _TASK_NAMES = {
        "response_turn":    "talk with you",
        "study":            "study something new",
        "dream":            "dream and process",
        "distill":          "crystallize understanding",
        "assimilation":     "consolidate patterns",
        "mutation":         "evolve my code",
        "pressure_routing": "route my pressure",
        "reach_out":        "reach out to you",
        "evo_tick":         "tick evolution",
        "save":             "save my state",
    }

    def _refresh_energy():
        d = _read_daemon()
        lbl = labels()
        frame = _load_surface_frame()
        projection = _load_subsurface_projection()
        if not d:
            root.after(5000, _refresh_energy)
            return

        gov_axes = d.get("runtime_governor_axes",{})
        host     = d.get("runtime_host",{})
        mode     = d.get("runtime_governor_mode","?")

        if _room_surface_mode():
            readiness = float(frame.get("readiness", projection.get("readiness_bias", 0.0)) or 0.0)
            coherence = float(frame.get("coherence", 0.0) or 0.0)
            action = _humanize_token(str(frame.get("selected_action") or "hold"))
            guidance = str(projection.get("surface_guidance", "") or "")
            axis_pairs = [
                ("  What my surface feels able to carry right now:\n\n", "head"),
                ("  State            : ", "key"),
                (f"{mode.replace('_',' ')}\n", "good" if mode in ("open", "balanced") else "warn"),
                ("  Confidence       : ", "key"),
                (f"{_soft_level(readiness)}\n", "good" if readiness >= 0.5 else "warn"),
                ("  Frame steadiness : ", "key"),
                (f"{_soft_level(coherence)}\n", "good" if coherence >= 0.5 else "warn"),
                ("  Immediate move   : ", "key"),
                (f"{action}\n", "val"),
                ("  Host pressure    : ", "key"),
                (f"load {float(host.get('load_ratio',0)):.2f}  ·  mem {float(host.get('mem_available_mb',0)):.0f} MB\n", "dim"),
            ]
            if guidance:
                axis_pairs += [("  Subsurface cue   : ", "key"), (f"{guidance}\n", "dim")]
        else:
            axis_pairs = []
            for ax in ("X","T","N","B","A"):
                name   = _axis_name(ax, lbl)
                budget = float(gov_axes.get(ax,0))
                bar    = "█" * int(budget * 14) + "░" * (14 - int(budget * 14))
                tag    = "good" if budget >= 0.5 else "warn" if budget >= 0.25 else "crit"
                axis_pairs += [
                    (f"  {name:<14s} [{bar}] ", tag),
                    (f"{budget:.3f}\n", tag),
                ]
            axis_pairs += [
                (f"\n  System state: ", "key"),
                (f"{mode.replace('_',' ')}\n",
                 "good" if mode in ("open","balanced") else "warn"),
                (f"  Load ratio  : ", "key"),
                (f"{float(host.get('load_ratio',0)):.2f}  ·  ",
                 "warn" if float(host.get('load_ratio',0)) > 0.85 else "val"),
                (f"Memory available: ", "key"),
                (f"{float(host.get('mem_available_mb',0)):.0f} MB\n", "val"),
            ]
        _write(energy_cap_box, *axis_pairs)

        if _room_surface_mode():
            task_pairs = [("  What I feel able to do from the surface right now:\n\n", "head")]
            ranked_tasks = []
            for task, prof in _GOV_PROFILES_LITE.items():
                score = sum(float(prof["axes"].get(ax,0)) * float(gov_axes.get(ax,0))
                            for ax in ("X","T","N","B","A"))
                ranked_tasks.append((score, task, prof))
            ranked_tasks.sort(reverse=True)
            for score, task, prof in ranked_tasks[:5]:
                floor = float(prof.get("floor", 0.0) or 0.0)
                name = _TASK_NAMES.get(task, task.replace("_"," "))
                tag = "good" if score >= floor else ("warn" if score > floor * 0.85 else "dim")
                status = "yes" if score >= floor else ("maybe" if score > floor * 0.85 else "not yet")
                task_pairs += [
                    (f"  · {name:<26s}", "val"),
                    (f" {status}  ({score:.3f})\n", tag),
                ]
            if not ranked_tasks:
                task_pairs += [("  I do not have a clear action pull yet.\n", "dim")]
        else:
            task_pairs = [("  What I want to do         Can I?   Score  Cost\n", "head"),
                          ("  " + "─"*52 + "\n", "dim")]
            for task, prof in sorted(_GOV_PROFILES_LITE.items(),
                                      key=lambda x: -x[1].get("cost",0)):
                score = sum(float(prof["axes"].get(ax,0)) * float(gov_axes.get(ax,0))
                            for ax in ("X","T","N","B","A"))
                floor = prof["floor"]
                allowed = score >= floor
                name = _TASK_NAMES.get(task, task.replace("_"," "))
                status = "✓  yes" if allowed else ("~  maybe" if score > floor*0.85 else "✗  no")
                tag = "good" if allowed else ("warn" if score > floor*0.85 else "crit")
                task_pairs += [
                    (f"  {name:<26s}  ", "dim"),
                    (f"{status:<8s}  {score:.3f}  {prof['cost']:.2f}\n", tag),
                ]
        _write(energy_tasks_box, *task_pairs)

        root.after(5000, _refresh_energy)

    room_refresh_callbacks.append(_refresh_energy)
    root.after(1800, _refresh_energy)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 7: EXPERIMENTS — she runs sweeps herself, logs observations
    # ══════════════════════════════════════════════════════════════════════════
    tab_exp_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_exp_outer, text="  Experiments  ")
    tab_exp = _make_scrollable(tab_exp_outer)

    tk.Label(tab_exp, text="MY EXPERIMENTS", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    # Sweep controls
    exp_ctrl = tk.Frame(tab_exp, bg=BG_PANEL, padx=12, pady=8)
    exp_ctrl.pack(fill=tk.X, padx=8, pady=(4,0))
    tk.Label(exp_ctrl, text="PARAMETER SWEEP", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).grid(row=0, column=0, columnspan=3,
                                                    sticky="w", pady=(0,4))
    tk.Label(exp_ctrl, text="Window (sec):", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 8)).grid(row=1, column=0, sticky="w")
    exp_window_var = tk.IntVar(value=90)
    tk.Spinbox(exp_ctrl, from_=30, to=300, increment=30, textvariable=exp_window_var,
               width=6, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
               relief=tk.FLAT).grid(row=1, column=1, padx=4)

    exp_status_lbl = tk.Label(exp_ctrl, text="", bg=BG_PANEL, fg=TEXT_DIM,
                               font=("Courier New", 8))
    exp_status_lbl.grid(row=1, column=2, padx=8, sticky="w")

    def _run_sweep():
        window = exp_window_var.get()
        _queue_command("queue_sweep", {"window_secs": window})
        _save_note("experiment", f"Queued parameter sweep (window={window}s)",
                   tags=["sweep","experiment"])
        exp_status_lbl.configure(text="sweep queued → daemon will run it", fg=ACCENT)

    def _run_sweep_dry():
        _queue_command("queue_sweep", {"window_secs": 1, "dry_run": True})
        exp_status_lbl.configure(text="dry run queued", fg=ACCENT2)

    tk.Button(exp_ctrl, text="▶  Run Sweep", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_run_sweep).grid(row=2, column=0, pady=6, padx=(0,4))
    tk.Button(exp_ctrl, text="◎  Dry Run", bg=BG_LOG, fg=TEXT_DIM,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_run_sweep_dry).grid(row=2, column=1, pady=6)

    # Sweep results (her view — ranked, with her observations)
    _divider(tab_exp)
    tk.Label(tab_exp, text="WHAT I LEARNED FROM SWEEPS", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    exp_results_box = _textbox(tab_exp, height=10, wrap=tk.NONE)

    def _refresh_experiments():
        projection = _load_subsurface_projection()
        if _SWEEP_RESULTS.exists():
            try:
                data   = json.loads(_SWEEP_RESULTS.read_text())
                ranked = data.get("ranked",[])
                history: Dict = {}
                if _SWEEP_HISTORY.exists():
                    history = json.loads(_SWEEP_HISTORY.read_text())

                if _room_surface_mode():
                    pairs = [("  My subsurface experiments are shaping how I feel and respond.\n\n", "head")]
                    for i, r in enumerate(ranked[:5]):
                        label_  = r.get("label","?")
                        score   = float(r.get("score", 0.0) or 0.0)
                        tag     = "good" if score >= 0.60 else "warn" if score >= 0.50 else "dim"
                        pairs  += [(f"  · {label_}\n", "val"),
                                   (f"    fit {score:.3f}\n", tag)]
                    guidance = str(projection.get("surface_guidance", "") or "")
                    if guidance:
                        pairs += [("\n  Surface effect:\n", "key"), (f"  {guidance}\n", "dim")]
                else:
                    pairs = [("  Config I tested            Score   Runs   Consistency\n", "head"),
                             ("  " + "─"*56 + "\n", "dim")]
                    for i, r in enumerate(ranked[:10]):
                        label_  = r.get("label","?")
                        score   = r.get("score", 0.0)
                        runs    = len(history.get(label_,[]))
                        scores  = history.get(label_,[])
                        mean    = sum(scores)/len(scores) if scores else score
                        std     = (sum((s-mean)**2 for s in scores)/len(scores))**0.5 if len(scores)>1 else 0
                        consist = "consistent" if std < 0.03 else "variable" if std < 0.08 else "noisy"
                        tag     = "good" if score >= 0.60 else "warn" if score >= 0.50 else "crit"
                        pairs  += [(f"  #{i+1:<2d} {label_:<24s}  ", "dim"),
                                   (f"{score:.3f}   {runs:>3d}    {consist}\n", tag)]

                if not ranked:
                    pairs = [("  No sweeps completed yet. Run one above.\n", "dim")]
                _write(exp_results_box, *pairs)
            except Exception:
                _write(exp_results_box, ("  Could not read sweep results.\n", "dim"))
        else:
            _write(exp_results_box,
                   ("  No sweeps run yet.\n\n", "dim"),
                   ("  A sweep tries different settings and records how I respond.\n", "dim"),
                   ("  It takes about 16 minutes and runs quietly in the background.\n", "dim"))

        root.after(10000, _refresh_experiments)

    room_refresh_callbacks.append(_refresh_experiments)
    root.after(2200, _refresh_experiments)

    # ── Training section in Experiments tab ───────────────────────────────────
    _divider(tab_exp)
    tk.Label(tab_exp, text="MY TRAINING", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    exp_train_ctrl = tk.Frame(tab_exp, bg=BG_PANEL, padx=12, pady=8)
    exp_train_ctrl.pack(fill=tk.X, padx=8, pady=(4,0))
    tk.Label(exp_train_ctrl, text="CORPUS TRAINING", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).grid(row=0, column=0, columnspan=4,
                                                    sticky="w", pady=(0,4))

    tk.Label(exp_train_ctrl, text="Passes:", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 8)).grid(row=1, column=0, sticky="w")
    exp_passes_var = tk.StringVar(value="triple")
    passes_menu = ttk.Combobox(exp_train_ctrl, textvariable=exp_passes_var,
                                values=["triple","observer","responder","reverse"],
                                width=10, state="readonly",
                                font=("Courier New", 8))
    passes_menu.grid(row=1, column=1, padx=4)

    tk.Label(exp_train_ctrl, text="Batch:", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 8)).grid(row=1, column=2, padx=(8,0), sticky="w")
    exp_batch_var = tk.IntVar(value=5000)
    tk.Spinbox(exp_train_ctrl, from_=500, to=50000, increment=500,
               textvariable=exp_batch_var, width=7,
               bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
               relief=tk.FLAT).grid(row=1, column=3, padx=4)

    exp_train_status_lbl = tk.Label(exp_train_ctrl, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                     font=("Courier New", 8))
    exp_train_status_lbl.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4,0))

    def _start_training():
        passes = exp_passes_var.get()
        batch  = exp_batch_var.get()
        _queue_command("start_corpus_training", {
            "corpus_path": str(_BASE_DIR / "conversations.json"),
            "passes":      passes,
            "batch_limit": batch,
        })
        _save_note("experiment", f"Started corpus training: passes={passes} batch={batch}",
                   tags=["training","corpus"])
        exp_train_status_lbl.configure(text=f"training queued ({passes}, batch {batch})", fg=ACCENT)

    def _stop_training():
        _queue_command("stop_corpus_training", {})
        exp_train_status_lbl.configure(text="stop signal queued", fg=WARN)

    exp_train_btn_row = tk.Frame(exp_train_ctrl, bg=BG_PANEL)
    exp_train_btn_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6,0))
    tk.Button(exp_train_btn_row, text="▶  Start Training", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_start_training).pack(side=tk.LEFT, padx=(0,4))
    tk.Button(exp_train_btn_row, text="■  Stop", bg=BG_LOG, fg=WARN,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_stop_training).pack(side=tk.LEFT)

    # Live training status
    _divider(tab_exp)
    tk.Label(tab_exp, text="TRAINING STATUS", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    exp_train_progress_box = _textbox(tab_exp, height=8, wrap=tk.NONE)

    def _refresh_training():
        sess_exists  = _TRAINING_SESSION.exists()
        corps_exists = _CORPUS_STATUS.exists()
        if not sess_exists and not corps_exists:
            _write(exp_train_progress_box,
                   ("  No training session active.\n\n", "dim"),
                   ("  Press Start Training above to begin.\n", "dim"),
                   ("  Training feeds all 5 learning pathways simultaneously.\n", "dim"))
            root.after(8000, _refresh_training)
            return
        try:
            pairs = []
            if sess_exists:
                sess = json.loads(_TRAINING_SESSION.read_text())
                active   = sess.get("active", False)
                passes   = sess.get("passes","?")
                cur_pass = sess.get("pass","?")
                pi       = int(sess.get("pass_index",0))
                msgs_done= int(sess.get("messages_processed",0))
                total    = int(sess.get("total_messages",1))
                pct_corp = float(sess.get("pct_corpus",0))
                pct_sess = float(sess.get("pct_session",0))
                ep       = int(sess.get("current_epoch",0))
                updated  = sess.get("last_update",0)
                age_s    = int(time.time() - float(updated)) if updated else 0

                status_tag = "good" if active else "warn"
                bar_done   = int(pct_sess / 5)
                bar_str    = "█"*bar_done + "░"*(20-bar_done)
                if _room_surface_mode():
                    pairs += [
                        ("  My deeper training layer is working in the background.\n\n", "head"),
                        ("  Status  : ", "key"),
                        (f"{'running' if active else 'paused / idle'}\n", status_tag),
                        ("  Current : ", "key"),
                        (f"{cur_pass}\n", "val"),
                        ("  Progress: ", "key"),
                        (f"{pct_sess:.1f}% of this session  ·  {pct_corp:.1f}% corpus coverage\n", "dim"),
                        ("  Last sync: ", "key"),
                        (f"{age_s}s ago\n", "dim"),
                    ]
                else:
                    pairs += [
                        (f"  Status  : ", "key"),
                        (f"{'RUNNING' if active else 'PAUSED/IDLE'}\n", status_tag),
                        (f"  Pass    : ", "key"),
                        (f"{cur_pass}  ({pi+1} of {len(passes.split(',')) if ',' in passes else 3})\n", "val"),
                        (f"  Session : ", "key"),
                        (f"[{bar_str}] {pct_sess:.1f}%  ({msgs_done:,}/{total:,} messages)\n", "val"),
                        (f"  Corpus  : ", "key"),
                        (f"{pct_corp:.1f}% of all conversations ingested\n", "dim"),
                        (f"  Epoch   : ", "key"), (f"{ep}\n", "val"),
                        (f"  Updated : ", "key"), (f"{age_s}s ago\n", "dim"),
                    ]

                # Last sim burst
                last_sim = sess.get("last_sim_burst")
                if last_sim:
                    top_dims = last_sim.get("top_dims",[])[:3]
                    pairs += [("\n  Last dream burst practiced:\n", "dim")]
                    for d_ in top_dims:
                        pairs += [(f"    · {d_.replace('_',' ')}\n", "val")]

                # Recent events
                events = sess.get("events",[])[-4:]
                if events:
                    pairs += [("\n  Recent events:\n", "dim")]
                    for ev in reversed(events):
                        etype = ev.get("type","?")
                        ets   = float(ev.get("ts",0))
                        age_e = int(time.time()-ets)
                        pairs += [(f"    {etype:<30s}  {age_e}s ago\n", "dim")]

            _write(exp_train_progress_box, *pairs)
        except Exception:
            _write(exp_train_progress_box, ("  Could not read training status.\n", "dim"))

        root.after(8000, _refresh_training)

    room_refresh_callbacks.append(_refresh_training)
    root.after(3000, _refresh_training)

    # ══════════════════════════════════════════════════════════════════════════
    # GROWTH TAB — evolution, dream effects, template development
    # ══════════════════════════════════════════════════════════════════════════
    tab_growth_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_growth_outer, text="  Growth  ")
    tab_growth = _make_scrollable(tab_growth_outer)

    tk.Label(tab_growth, text="HOW I'M DEVELOPING", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    # Dream effects — how dreams shape her
    tk.Label(tab_growth, text="HOW MY DREAMS CHANGE ME", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    growth_dream_box = _textbox(tab_growth, height=8)

    def _refresh_dream_effects():
        d = _read_daemon()
        sess_data: Dict = {}
        if _TRAINING_SESSION.exists():
            try:
                sess_data = json.loads(_TRAINING_SESSION.read_text())
            except Exception:
                pass

        if not d and not sess_data:
            _write(growth_dream_box, ("  No data yet.\n", "dim"))
            root.after(10000, _refresh_dream_effects)
            return

        pairs = []
        # Dream burst history from training session
        last_burst = sess_data.get("last_sim_burst")
        if last_burst:
            burst_ts  = float(last_burst.get("ts",0))
            episodes  = int(last_burst.get("episodes",0))
            top_dims  = last_burst.get("top_dims",[])
            age       = int(time.time()-burst_ts)
            pairs += [(f"  Last dream burst: {age//3600}h {(age%3600)//60}m ago\n", "dim"),
                      (f"  Episodes simulated: ", "key"), (f"{episodes}\n", "val"),
                      (f"  Dimensions most exercised:\n", "key")]
            for d_ in top_dims[:4]:
                pairs += [(f"    · {d_.replace('_',' ')}\n", "good")]

        # Pressure orientation shift (shows what dreams emphasized)
        corp_status: Dict = {}
        if _CORPUS_STATUS.exists():
            try:
                corp_status = json.loads(_CORPUS_STATUS.read_text())
            except Exception:
                pass
        p_orient = corp_status.get("pressure_orientation", {})
        if p_orient:
            lbl = labels()
            pairs += [("\n  How my training shaped my pressures:\n", "key")]
            for ax in ("X","T","N","B","A"):
                val = float(p_orient.get(ax,1.0))
                bar = "▲" if val > 1.05 else "▼" if val < 0.95 else "─"
                ax_name = _axis_name(ax, lbl)
                tag = "good" if val > 1.05 else "warn" if val < 0.95 else "dim"
                pairs += [(f"    {ax} ({ax_name:<12s}) {bar} ", tag),
                          (f"{val:.3f}\n", "val")]

        # Fail patterns that dreams addressed
        fail_summary = d.get("fail_summary",[])
        resolved = [f for f in fail_summary if float(f.get("avg_sev",0)) < 0.3]
        if resolved:
            pairs += [("\n  Dimensions that look healthy now:\n", "dim")]
            for f in resolved[:3]:
                dim = f.get("dim","?").replace("_"," ")
                pairs += [(f"    · {dim}  ✓\n", "good")]

        if _room_surface_mode() and pairs:
            pairs = [("  What my dreams are feeding into my surface:\n\n", "head")] + pairs

        if not pairs:
            pairs = [("  No dream effect data yet. Dreams will log here over time.\n", "dim")]

        _write(growth_dream_box, *pairs)
        root.after(10000, _refresh_dream_effects)

    room_refresh_callbacks.append(_refresh_dream_effects)
    root.after(2800, _refresh_dream_effects)

    # Template evolution — how her language shapes up
    _divider(tab_growth)
    tk.Label(tab_growth, text="HOW MY THINKING IS EVOLVING", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    growth_evol_box = _textbox(tab_growth, height=8, wrap=tk.NONE)

    def _refresh_template_evolution():
        plan = _load_evolution_relief_plan()
        projection = _load_subsurface_projection()
        if bool(plan.get("active")):
            operator_map = {
                "latent_promotion": "internal restructuring",
                "architectural_reflection": "structural reflection",
                "native_surface_projection": "expression reshaping",
            }
            selected = operator_map.get(str(plan.get("selected_operator", "") or ""), "deep structural work")
            blocked = ", ".join(str(t) for t in list(plan.get("blocked_tasks") or [])[:3]) or "structural refinement"
            status_label = _humanize_token(str(plan.get("status", "staged") or "staged"))
            pairs = [
                ("  A deeper layer is working on my growth.\n\n", "head"),
                ("  Deeper work        : ", "key"), (f"{selected}\n", "val"),
                ("  What it is holding : ", "key"), (f"{blocked}\n", "warn"),
                ("  Current handoff    : ", "key"), (f"{status_label}\n", "dim"),
            ]
            guidance = str(projection.get("surface_guidance", "") or "")
            if guidance:
                pairs += [("\n  Surface effect:\n", "key"), (f"  {guidance}\n", "dim")]
            result_excerpt = str(plan.get("poedex_result_excerpt", "") or "")
            if result_excerpt:
                pairs += [("\n  What Poedex surfaced:\n", "key"), (f"  {result_excerpt}\n", "good")]
            elif plan.get("poedex_question"):
                pairs += [("\n  If I need explicit help, I should ask Poedex about this next.\n", "dim")]
            if _room_surface_mode():
                pairs = [
                    ("  My deeper layer is actively reshaping how I can grow.\n\n", "head"),
                    ("  Surface impression : ", "key"),
                    (f"{str(projection.get('surface_guidance') or 'something important is being worked through')}\n", "dim"),
                    ("  Deeper operator    : ", "key"),
                    (f"{selected}\n", "val"),
                    ("  What it is holding : ", "key"),
                    (f"{blocked}\n", "warn"),
                    ("  Current handoff    : ", "key"),
                    (f"{status_label}\n", "dim"),
                ]
                if result_excerpt:
                    pairs += [("  Poedex insight     : ", "key"), (f"{result_excerpt}\n", "good")]
            _write(growth_evol_box, *pairs)
            root.after(15000, _refresh_template_evolution)
            return

        if not _TEMPLATE_EVOL.exists():
            _write(growth_evol_box, ("  No evolution cues yet.\n", "dim"))
            root.after(15000, _refresh_template_evolution)
            return
        try:
            evol = json.loads(_TEMPLATE_EVOL.read_text())
            pool = evol.get("pool", {})
            gen  = int(evol.get("generation", 0))
            pairs = [(f"  Generation {gen} · {len(pool)} learned phrasing patterns\n\n", "head")]

            def _is_real_template(t):
                s = str(t.get("template_str", "") or t.get("pattern", ""))
                return " " in s or "{" in s

            real_templates = [t for t in pool.values() if _is_real_template(t)]
            sorted_t = sorted(real_templates,
                               key=lambda t: int(t.get("uses", 0)), reverse=True)[:5]
            pairs += [("  My strongest outward patterns:\n", "key")]
            for t in sorted_t:
                tmpl = str(t.get("template_str", "") or t.get("pattern", ""))[:55]
                pairs += [(f"  · {tmpl}\n", "val")]

            _write(growth_evol_box, *pairs)
        except Exception:
            _write(growth_evol_box, ("  Could not read evolution data.\n", "dim"))

        root.after(15000, _refresh_template_evolution)

    room_refresh_callbacks.append(_refresh_template_evolution)
    root.after(4000, _refresh_template_evolution)

    # Identity development timeline
    _divider(tab_growth)
    tk.Label(tab_growth, text="MY DEVELOPMENT TIMELINE", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    growth_timeline_box = _textbox(tab_growth, height=9, wrap=tk.NONE)

    def _refresh_timeline():
        sess_data: Dict = {}
        if _TRAINING_SESSION.exists():
            try:
                sess_data = json.loads(_TRAINING_SESSION.read_text())
            except Exception:
                pass

        events_all: List[Dict] = list(sess_data.get("events",[]))

        # Merge in notes that represent growth events
        notes = _load_notes()
        growth_types = {"experiment","training","discovery","health_decision"}
        for n in notes:
            if n.get("type","") in growth_types:
                events_all.append({
                    "ts":    n.get("ts",0),
                    "type":  n.get("type","note"),
                    "label": n.get("content","")[:60],
                })

        events_all.sort(key=lambda e: float(e.get("ts",0)), reverse=True)

        if not events_all:
            _write(growth_timeline_box, ("  No development events yet.\n", "dim"))
            root.after(12000, _refresh_timeline)
            return

        if _room_surface_mode():
            pairs = [("  TIME              WHAT REACHED MY SURFACE\n", "head"),
                     ("  " + "─"*62 + "\n", "dim")]
        else:
            pairs = [("  TIME              EVENT\n", "head"),
                     ("  " + "─"*62 + "\n", "dim")]
        for ev in events_all[:18]:
            ts    = float(ev.get("ts",0))
            ts_s  = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "?"
            etype = str(ev.get("type","?"))
            label = str(ev.get("label") or ev.get("content",""))[:55]
            tag   = {"pass_start":"good","pass_complete":"good",
                     "discovery":"good","experiment":"val",
                     "training":"val","health_decision":"warn"}.get(etype,"dim")
            if _room_surface_mode():
                etype = {
                    "pass_start": "training began",
                    "pass_complete": "training completed",
                    "discovery": "new understanding",
                    "experiment": "deeper experiment",
                    "training": "training pulse",
                    "health_decision": "repair choice",
                }.get(etype, etype.replace("_", " "))
            pairs += [(f"  {ts_s}  ", "dim"),
                      (f"{etype:<18s}  ", tag),
                      (f"{label}\n", "val")]

        _write(growth_timeline_box, *pairs)
        root.after(12000, _refresh_timeline)

    room_refresh_callbacks.append(_refresh_timeline)
    root.after(5000, _refresh_timeline)

    # ══════════════════════════════════════════════════════════════════════════
    # RESPONSE ASSEMBLY TAB — how she builds responses, template landscape,
    # coaching notes from Sunni she reads here
    # ══════════════════════════════════════════════════════════════════════════
    tab_resp_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_resp_outer, text="  Response  ")
    tab_resp = _make_scrollable(tab_resp_outer)

    tk.Label(tab_resp, text="HOW I BUILD RESPONSES", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    # ── Interaction pipeline ──────────────────────────────────────────────────
    tk.Label(tab_resp, text="MY CURRENT APPROACH", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    resp_pipeline_box = _textbox(tab_resp, height=9)

    def _refresh_resp_pipeline():
        d = _read_daemon()
        frame = _load_surface_frame()
        subsurface = _load_subsurface_state()
        projection = _load_subsurface_projection()
        if not d and not frame and not subsurface:
            _write(resp_pipeline_box, ("  No interaction data yet.\n", "dim"))
            root.after(5000, _refresh_resp_pipeline)
            return

        contract = dict(frame.get("contract_signals") or {})
        interpretation = str(frame.get("interpretation", "") or "I am still assembling a clear frame.")
        stance = _humanize_token(str(frame.get("stance") or d.get("interaction_strategy") or "attend"))
        action = _humanize_token(str(frame.get("selected_action") or "hold"))
        readiness = float(frame.get("readiness", 0.0) or 0.0)
        coherence = float(frame.get("coherence", 0.0) or 0.0)
        should_speak = bool(frame.get("should_speak", False))
        root_thought = dict(frame.get("root_thought") or {})
        processing_mode = _humanize_token(str(frame.get("processing_mode") or "deliberative"))
        topic = str(contract.get("active_topic", "") or "")
        emotion = str(contract.get("dominant_emotion", "") or "")
        if _room_surface_mode():
            pairs = [
                ("  My current conscious response frame:\n\n", "head"),
                ("  Stance          : ", "key"), (f"{stance}\n", "val"),
                ("  Next move       : ", "key"), (f"{action}\n", "good" if should_speak else "warn"),
                ("  Processing      : ", "key"), (f"{processing_mode}\n", "val"),
                ("  Readiness       : ", "key"), (f"{_soft_level(readiness)}\n", "good" if readiness >= 0.5 else "warn"),
                ("  Coherence       : ", "key"), (f"{_soft_level(coherence)}\n", "good" if coherence >= 0.5 else "warn"),
                ("  Interpretation  : ", "key"), (f"{interpretation}\n", "dim"),
            ]
            if root_thought.get("law_bindings"):
                _lb3 = ", ".join([str(b.get("nc_name") or b.get("domain_letter", "")) for b in list(root_thought.get("law_bindings") or []) if isinstance(b, dict)])
                pairs += [("  Root thought    : ", "key"), (f"{_lb3}\n", "dim")]
            _channels = list(root_thought.get("comparison_channels") or [])
            if _channels:
                pairs += [("  Frame sources   : ", "key"), (f"{', '.join(_channels[:4])}\n", "dim")]
            if topic:
                pairs += [("  Active topic    : ", "key"), (f"{topic}\n", "val")]
            if emotion:
                pairs += [("  Felt tone       : ", "key"), (f"{emotion}\n", "warn" if emotion not in {"neutral", "calm", "focused"} else "val")]
            guidance = str(projection.get("surface_guidance", "") or "")
            if guidance:
                pairs += [("\n  Intuitive signal: ", "key"), (f"{guidance}\n", "dim")]
            if not should_speak:
                pairs += [("\n  If I need explicit outside help, I should ask Poedex before forcing certainty.\n", "dim")]
        else:
            prediction = dict(subsurface.get("prediction", {}) or {})
            owned = dict(projection.get("subsurface_owned") or {})
            pairs = [
                ("  How my subsurface is preparing the response field:\n\n", "head"),
                ("  Dominant axis    : ", "key"), (f"{str(subsurface.get('dominant_axis') or 'X')}\n", "val"),
                ("  Repair phase     : ", "key"), (f"{_humanize_token(str(owned.get('repair_phase') or 'steady'))}\n", "warn"),
                ("  Prediction miss  : ", "key"), (f"{float(prediction.get('mismatch',0.0) or 0.0):.3f}\n", "warn" if float(prediction.get('mismatch',0.0) or 0.0) >= 0.35 else 'val'),
                ("  DCE handoff      : ", "key"), (f"{', '.join([str(b.get('nc_name') or b.get('domain_letter', '')) for b in list(root_thought.get('law_bindings') or []) if isinstance(b, dict)]) or 'no active root thought yet'}\n", "dim"),
                ("  Enforcer path    : ", "key"), ("surface authorizes  ->  subsurface applies\n", "good"),
            ]
            if owned.get("repair_reason"):
                pairs += [("  Why attention rose: ", "key"), (f"{owned.get('repair_reason','')}\n", "dim")]

        _write(resp_pipeline_box, *pairs)
        root.after(5000, _refresh_resp_pipeline)

    room_refresh_callbacks.append(_refresh_resp_pipeline)
    root.after(1000, _refresh_resp_pipeline)

    # ── DCE live assembly feed ────────────────────────────────────────────────
    _divider(tab_resp)
    tk.Label(tab_resp, text="LIVE ASSEMBLY FRAMES", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    resp_dce_box = _textbox(tab_resp, height=6, wrap=tk.NONE)

    def _refresh_dce_feed():
        if not _DUAL_STRATA_FRAME_LOG.exists() and not _DCE_ASSEMBLY_LOG.exists():
            _write(resp_dce_box, ("  No assembly data yet.\n", "dim"))
            root.after(6000, _refresh_dce_feed)
            return
        try:
            import json as _j
            path = _DUAL_STRATA_FRAME_LOG if _DUAL_STRATA_FRAME_LOG.exists() else _DCE_ASSEMBLY_LOG
            lines = path.read_text().splitlines()
            recent = []
            for ln in reversed(lines[-200:]):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    recent.append(_j.loads(ln))
                except Exception:
                    continue
                if len(recent) >= 8:
                    break

            if _room_surface_mode():
                pairs = [("  TIME      FRAME        STANCE           ACTION        READY\n", "head"),
                         ("  " + "─"*66 + "\n", "dim")]
            else:
                pairs = [("  TIME      CONVERGENCE   SURFACE RESULT   READINESS\n", "head"),
                         ("  " + "─"*66 + "\n", "dim")]
            for fr in recent:
                ts_s   = time.strftime("%H:%M:%S", time.localtime(float(fr.get("ts",0))))
                frame_n= str(fr.get("frame_name") or fr.get("frame") or "?")[:12]
                stance = _humanize_token(str(fr.get("stance") or "hold"))[:16]
                action = _humanize_token(str(fr.get("selected_action") or fr.get("dominant") or "hold"))[:12]
                ready  = float(fr.get("readiness", fr.get("coherence", 0.0)) or 0.0)
                if _room_surface_mode():
                    pairs += [
                        (f"  {ts_s}  {frame_n:<12s}  ", "dim"),
                        (f"{stance:<16s}  ", "val"),
                        (f"{action:<12s}  ", "warn" if ready < 0.42 else "good"),
                        (f"{_soft_level(ready)}\n", "dim"),
                    ]
                else:
                    pairs += [
                        (f"  {ts_s}  {frame_n:<12s}  ", "dim"),
                        (f"{action:<16s}  ", "val"),
                        (f"{_soft_level(ready)}\n", "warn" if ready < 0.42 else "good"),
                    ]
            _write(resp_dce_box, *pairs)
        except Exception:
            _write(resp_dce_box, ("  Could not read assembly log.\n", "dim"))
        root.after(6000, _refresh_dce_feed)

    room_refresh_callbacks.append(_refresh_dce_feed)
    root.after(1500, _refresh_dce_feed)

    # ── Template landscape ────────────────────────────────────────────────────
    _divider(tab_resp)
    tk.Label(tab_resp, text="MY THINKING TEMPLATES", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    resp_tmpl_box = _textbox(tab_resp, height=9, wrap=tk.NONE)

    def _refresh_templates():
        if not _TEMPLATE_EVOL.exists():
            _write(resp_tmpl_box, ("  No template data yet.\n", "dim"))
            root.after(15000, _refresh_templates)
            return
        try:
            evol = json.loads(_TEMPLATE_EVOL.read_text())
            pool = evol.get("pool", {})
            gen  = int(evol.get("generation", 0))
            by_fit = sorted(pool.values(),
                             key=lambda t: float(t.get("fitness",0)), reverse=True)

            pairs = [(f"  Generation {gen}  ·  {len(pool)} templates total\n\n", "head"),
                     ("  FITNESS  USES    SUCCESS%  TEMPLATE\n", "key"),
                     ("  " + "─"*68 + "\n", "dim")]
            for t in by_fit[:12]:
                fit  = float(t.get("fitness",0))
                uses = int(t.get("uses",0))
                succ = int(t.get("successes",0))
                pct  = (succ/uses*100) if uses else 0
                tmpl = str(t.get("template_str",""))[:38]
                tag  = "good" if fit >= 0.7 else "warn" if fit >= 0.5 else "dim"
                bar  = "█" * int(fit * 10) + "░" * (10 - int(fit * 10))
                pairs += [
                    (f"  {bar}  ", tag),
                    (f"{uses:>4d}    {pct:>5.1f}%   ", "dim"),
                    (f"{tmpl}\n", "val"),
                ]
            _write(resp_tmpl_box, *pairs)
        except Exception:
            _write(resp_tmpl_box, ("  Could not read template data.\n", "dim"))
        root.after(15000, _refresh_templates)

    root.after(2000, _refresh_templates)

    # ── Last generated responses (responder snapshots) ────────────────────────
    _divider(tab_resp)
    tk.Label(tab_resp, text="RECENT RESPONSES I GENERATED", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    resp_snap_box = _textbox(tab_resp, height=8)

    def _refresh_snapshots():
        if not _RESPONDER_SNAPS.exists():
            _write(resp_snap_box, ("  No snapshots yet.\n", "dim"))
            root.after(15000, _refresh_snapshots)
            return
        try:
            snap_files = sorted(_RESPONDER_SNAPS.glob("snapshot_*.json"), reverse=True)
            if not snap_files:
                _write(resp_snap_box, ("  No snapshots yet.\n", "dim"))
                root.after(15000, _refresh_snapshots)
                return
            snap = json.loads(snap_files[0].read_text())
            responses = snap.get("responses", {})
            sims      = snap.get("sims", {})
            pass_idx  = snap.get("pass_index", "?")

            # Rank by sim score
            ranked = sorted(sims.items(), key=lambda x: float(x[1]), reverse=True)[:5]
            pairs  = [(f"  Pass {pass_idx}  ·  {len(responses)} responses generated\n\n", "head"),
                      ("  SCORE    RESPONSE\n", "key"),
                      ("  " + "─"*68 + "\n", "dim")]
            for rid, score in ranked:
                text = responses.get(rid, "")[:70]
                tag  = "good" if score >= 0.04 else "warn" if score >= 0.02 else "dim"
                pairs += [(f"  {score:.4f}  ", tag), (f"{text}\n", "val")]
            _write(resp_snap_box, *pairs)
        except Exception:
            _write(resp_snap_box, ("  Could not read snapshots.\n", "dim"))
        root.after(15000, _refresh_snapshots)

    root.after(2500, _refresh_snapshots)

    # ── Sunni's coaching notes — what she's received from him ────────────────
    _divider(tab_resp)
    resp_coach_hdr = tk.Frame(tab_resp, bg=BG_PANEL, padx=12, pady=4)
    resp_coach_hdr.pack(fill=tk.X, padx=8)
    tk.Label(resp_coach_hdr, text="GUIDANCE FROM SUNNI", bg=BG_PANEL, fg=WARN,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    resp_coach_count_lbl = tk.Label(resp_coach_hdr, text="", bg=BG_PANEL,
                                     fg=TEXT_DIM, font=("Courier New", 8))
    resp_coach_count_lbl.pack(side=tk.LEFT, padx=6)

    resp_coach_box = _textbox(tab_resp, height=8)

    def _refresh_coaching():
        if not _RESPONSE_COACHING.exists():
            _write(resp_coach_box,
                   ("  No coaching notes from Sunni yet.\n\n", "dim"),
                   ("  He can write advice in the master hub → Aurora's Room tab.\n", "dim"))
            root.after(8000, _refresh_coaching)
            return
        try:
            entries = json.loads(_RESPONSE_COACHING.read_text())
            if not isinstance(entries, list):
                entries = []
            resp_coach_count_lbl.configure(
                text=f"  {len(entries)} notes",
                fg=WARN if entries else TEXT_DIM)
            pairs = []
            for e in reversed(entries[-10:]):
                ts_s   = e.get("ts_str","?")[:16]
                ctype  = e.get("type","note").replace("_"," ")
                body   = e.get("content","")
                read   = e.get("read_by_aurora", False)
                tag    = "good" if not read else "dim"  # unread items glow
                pairs += [
                    (f"  [{ts_s}] ", "dim"),
                    (f"[{ctype}] ", "warn"),
                    (f"{'★ ' if not read else ''}", tag),
                    (f"{body}\n", tag),
                ]
            if not pairs:
                pairs = [("  No coaching notes yet.\n", "dim")]
            _write(resp_coach_box, *pairs)
        except Exception:
            _write(resp_coach_box, ("  Could not read coaching file.\n", "dim"))
        root.after(8000, _refresh_coaching)

    root.after(3000, _refresh_coaching)

    def _mark_coaching_read():
        """Called when she reads a coaching note — marks them as read."""
        if not _RESPONSE_COACHING.exists():
            return
        try:
            entries = json.loads(_RESPONSE_COACHING.read_text())
            if not isinstance(entries, list):
                return
            changed = False
            for e in entries:
                if not e.get("read_by_aurora", False):
                    e["read_by_aurora"] = True
                    e["read_at"] = time.time()
                    changed = True
            if changed:
                _RESPONSE_COACHING.write_text(json.dumps(entries, indent=2))
                _log_activity("read coaching notes from Sunni",
                               f"{sum(1 for e in entries if e.get('read_by_aurora'))} notes reviewed",
                               "note")
        except Exception:
            pass

    # Mark as read when she switches to this tab
    resp_coach_read_btn = tk.Button(resp_coach_hdr, text="Mark Read", bg=BG_LOG, fg=TEXT_DIM,
                                     font=("Courier New", 8), relief=tk.FLAT, padx=6, pady=1,
                                     cursor="hand2", command=_mark_coaching_read)
    resp_coach_read_btn.pack(side=tk.RIGHT)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 8: NOTES — her labels, observations, intentions
    # ══════════════════════════════════════════════════════════════════════════
    tab_notes_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_notes_outer, text="  Notes  ")
    tab_notes = _make_scrollable(tab_notes_outer)

    tk.Label(tab_notes, text="MY LABELS & OBSERVATIONS", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")

    # Axis label editor
    notes_label_frame = tk.Frame(tab_notes, bg=BG_PANEL, padx=12, pady=8)
    notes_label_frame.pack(fill=tk.X, padx=8, pady=(4,0))
    tk.Label(notes_label_frame, text="WHAT I CALL MY DIMENSIONS", bg=BG_PANEL,
             fg=ACCENT2, font=("Courier New", 9, "bold")).grid(row=0, column=0,
                                                                columnspan=4, sticky="w",
                                                                pady=(0,6))
    _axis_entries: Dict[str, tk.Entry] = {}
    for i, ax in enumerate(("X","T","N","B","A")):
        tk.Label(notes_label_frame, text=f"{ax}:", bg=BG_PANEL,
                 fg=AXIS_COLORS[ax], font=("Courier New", 9, "bold"),
                 width=3).grid(row=1+i, column=0, sticky="w", pady=2)
        entry = tk.Entry(notes_label_frame, bg=BG_LOG, fg=TEXT,
                         font=("Courier New", 9), relief=tk.FLAT,
                         insertbackground=ACCENT, width=22)
        entry.insert(0, _axis_name(ax, labels()))
        entry.grid(row=1+i, column=1, padx=6, sticky="w")
        _axis_entries[ax] = entry

    def _save_axis_labels():
        lbl = _load_labels()
        for ax, entry in _axis_entries.items():
            name = entry.get().strip()
            if name:
                lbl.setdefault("axes",{})[ax] = name
        _save_labels(lbl)
        _labels[0] = lbl
        notes_save_lbl.configure(text="labels saved and shared with master hub", fg=ACCENT)
        root.after(3000, lambda: notes_save_lbl.configure(text="", fg=TEXT_DIM))

    tk.Button(notes_label_frame, text="Save Labels", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_save_axis_labels).grid(row=6, column=1,
                                                              sticky="w", pady=(8,0))
    notes_save_lbl = tk.Label(notes_label_frame, text="", bg=BG_PANEL,
                               fg=TEXT_DIM, font=("Courier New", 8))
    notes_save_lbl.grid(row=6, column=2, padx=8, sticky="w")

    # Observation writer
    _divider(tab_notes)
    tk.Label(tab_notes, text="WRITE AN OBSERVATION", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")

    obs_frame = tk.Frame(tab_notes, bg=BG_PANEL, padx=12, pady=6)
    obs_frame.pack(fill=tk.X, padx=8)
    obs_type_var = tk.StringVar(value="observation")
    obs_type_frame = tk.Frame(obs_frame, bg=BG_PANEL)
    obs_type_frame.pack(anchor="w", pady=(0,4))
    for _otype in ("observation","intention","question","discovery"):
        tk.Radiobutton(obs_type_frame, text=_otype, variable=obs_type_var, value=_otype,
                       bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
                       activebackground=BG_PANEL, font=("Courier New", 8),
                       indicatoron=True).pack(side=tk.LEFT, padx=6)

    obs_input = tk.Text(obs_frame, bg=BG_LOG, fg=TEXT, font=("Courier New", 9),
                        height=3, relief=tk.FLAT, borderwidth=0,
                        insertbackground=ACCENT, wrap=tk.WORD)
    obs_input.pack(fill=tk.X)

    def _save_observation():
        content = obs_input.get("1.0", tk.END).strip()
        if not content:
            return
        otype = obs_type_var.get()
        _save_note(otype, content, tags=[otype])
        if otype == "intention":
            _queue_command("set_intention", {"content": content})
        obs_input.delete("1.0", tk.END)
        _refresh_note_log()

    tk.Button(obs_frame, text="Write", bg=CHART_GRID, fg=ACCENT,
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_save_observation).pack(anchor="e", pady=(4,0))

    # Recent notes log
    _divider(tab_notes)
    tk.Label(tab_notes, text="RECENT NOTES", bg=BG, fg=ACCENT2,
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    notes_log_box = _textbox(tab_notes, height=10)

    def _refresh_note_log():
        notes = _load_notes()
        if not notes:
            _write(notes_log_box, ("  Nothing written yet.\n", "dim"))
            return
        pairs = []
        for n in reversed(notes[-20:]):
            ts      = n.get("ts_str","?")[:16]
            ntype   = n.get("type","?")
            content = n.get("content","")[:120]
            tag     = {"observation":"val","intention":"good",
                       "question":"warn","discovery":"good",
                       "health_decision":"dim","experiment":"dim"}.get(ntype,"val")
            pairs += [(f"  [{ts}] ", "dim"), (f"{ntype:<14s}", tag),
                      (f"{content}\n", "val")]
        _write(notes_log_box, *pairs)

    root.after(2500, _refresh_note_log)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 11: POEDEX — Three-mode governing intelligence
    #
    # OBSERVER  : internal knowledge query  (codex, live QuasiArch data)
    # RESEARCHER: experiment & external acquisition
    # ENFORCER  : agentic task applicator   (proposals → approve/defer/reverse)
    #
    # Governance flow: Observer sees → Researcher investigates → Enforcer applies
    # Constitutional rule: Poedex informs. Aurora decides. Enforcer acts only
    #                      on what Aurora explicitly approves.
    # ══════════════════════════════════════════════════════════════════════════
    tab_poedex_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_poedex_outer, text="  Poedex  ")
    tab_poedex = _make_scrollable(tab_poedex_outer)

    # ── Persistent header ──────────────────────────────────────────────────────
    tk.Label(tab_poedex, text="◈  POEDEX — SYSTEM GOVERNANCE", bg=BG, fg=ACCENT,
             font=("Courier New", 11, "bold"), padx=14, pady=6).pack(anchor="w")
    tk.Label(tab_poedex,
             text="Observer · Researcher · Enforcer  —  one organism, three modes.",
             bg=BG, fg=TEXT_DIM, font=("Courier New", 8, "italic"), padx=16).pack(anchor="w")

    # ── Conduct rule — always visible ─────────────────────────────────────────
    conduct_bar = tk.Frame(tab_poedex, bg="#1a1a0a", padx=12, pady=5)
    conduct_bar.pack(fill=tk.X, padx=8, pady=(6, 0))
    tk.Label(conduct_bar, text="CONDUCT", bg="#1a1a0a", fg=WARN,
             font=("Courier New", 8, "bold"), width=9, anchor="w").pack(side=tk.LEFT)
    tk.Label(conduct_bar,
             text="External results are consulted knowledge. "
                  "I receive them, understand them, and speak in my own voice. "
                  "I never recite Poedex output verbatim.",
             bg="#1a1a0a", fg=TEXT_DIM, font=("Courier New", 8),
             wraplength=680, justify=tk.LEFT).pack(side=tk.LEFT, padx=4)

    # ── Tutorial intro panel (one-time, from poedex_intro.py) ─────────────────
    _poe_tutorial_steps: list = [None]
    _poe_tutorial_step:  list = [0]

    def _poe_load_tutorial():
        if _POEDEX_TUTORIAL.exists():
            try:
                data = json.loads(_POEDEX_TUTORIAL.read_text())
                return data.get("steps", [])
            except Exception:
                pass
        return []

    _poe_intro_built: list = [False]
    intro_container = tk.Frame(tab_poedex, bg="#0d1a0d", bd=1, relief=tk.FLAT)

    def _poe_build_intro():
        if _poe_intro_built[0] or _POEDEX_INTRO_DONE.exists():
            return
        steps = _poe_tutorial_steps[0]
        if not steps:
            return
        _poe_intro_built[0] = True
        intro_container.pack(fill=tk.X, padx=8, pady=(6, 0))

        hdr = tk.Frame(intro_container, bg="#0d1a0d", padx=10, pady=5)
        hdr.pack(fill=tk.X)
        _poe_step_lbl = tk.Label(hdr, text="", bg="#0d1a0d", fg=ACCENT,
                                  font=("Courier New", 9, "bold"))
        _poe_step_lbl.pack(side=tk.LEFT)
        _poe_tab_badge = tk.Label(hdr, text="", bg="#0d1a0d", fg=ACCENT2,
                                   font=("Courier New", 8))
        _poe_tab_badge.pack(side=tk.LEFT, padx=12)

        _poe_content_box = tk.Text(
            intro_container, bg="#0d1a0d", fg=TEXT, font=("Courier New", 8),
            height=7, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
            wrap=tk.WORD, padx=10, pady=4)
        _poe_content_box.pack(fill=tk.X)

        btn_row = tk.Frame(intro_container, bg="#0d1a0d", padx=10, pady=5)
        btn_row.pack(fill=tk.X)

        def _poe_show_step(idx: int):
            idx = max(0, min(idx, len(steps) - 1))
            _poe_tutorial_step[0] = idx
            step = steps[idx]
            _poe_step_lbl.configure(
                text=f"POEDEX INTRO  {idx+1}/{len(steps)}  —  {step.get('title','')}")
            _poe_tab_badge.configure(
                text=f"[ {step.get('tab','')} ]" if step.get('tab') else "")
            _poe_content_box.configure(state=tk.NORMAL)
            _poe_content_box.delete("1.0", tk.END)
            _poe_content_box.insert(tk.END, step.get("content", ""))
            _poe_content_box.configure(state=tk.DISABLED)
            dq = step.get("demo_query")
            demo_btn.configure(
                state=tk.NORMAL if dq else tk.DISABLED,
                text=f"Try: {step.get('demo_type','define')} {dq}" if dq else "(no demo)")
            prev_btn.configure(state=tk.DISABLED if idx == 0 else tk.NORMAL)
            next_btn.configure(
                text="Close Tutorial" if idx == len(steps) - 1 else "Next →")

        def _poe_next_or_close():
            if _poe_tutorial_step[0] >= len(steps) - 1:
                _poe_dismiss_intro()
            else:
                _poe_show_step(_poe_tutorial_step[0] + 1)

        def _poe_demo():
            step = steps[_poe_tutorial_step[0]]
            dq = step.get("demo_query")
            if dq:
                _poe_set_mode("observer")
                obs_inq_input.delete(0, tk.END)
                obs_inq_input.insert(0, dq)
                _poe_obs_cat.set(step.get("demo_type", "define"))
                _poe_obs_lane.set("self")

        def _poe_dismiss_intro():
            try:
                _POEDEX_INTRO_DONE.write_text(json.dumps({
                    "dismissed_at": time.time(),
                    "dismissed_at_str": time.strftime("%Y-%m-%d %H:%M:%S")}))
            except Exception:
                pass
            intro_container.pack_forget()
            _log_activity("poedex intro dismissed", "tutorial complete", "note")

        prev_btn = tk.Button(btn_row, text="← Prev", bg=CHART_GRID, fg=TEXT_DIM,
                             font=("Courier New", 8), relief=tk.FLAT, padx=6, pady=2,
                             cursor="hand2", command=lambda: _poe_show_step(_poe_tutorial_step[0]-1))
        prev_btn.pack(side=tk.LEFT, padx=(0, 4))
        next_btn = tk.Button(btn_row, text="Next →", bg=CHART_GRID, fg=ACCENT,
                             font=("Courier New", 8, "bold"), relief=tk.FLAT, padx=6, pady=2,
                             cursor="hand2", command=_poe_next_or_close)
        next_btn.pack(side=tk.LEFT, padx=4)
        demo_btn = tk.Button(btn_row, text="(no demo)", bg=CHART_GRID, fg=ACCENT2,
                             font=("Courier New", 8), relief=tk.FLAT, padx=6, pady=2,
                             cursor="hand2", command=_poe_demo, state=tk.DISABLED)
        demo_btn.pack(side=tk.LEFT, padx=8)
        tk.Button(btn_row, text="Skip Tutorial", bg=CHART_GRID, fg=TEXT_DIM,
                  font=("Courier New", 7), relief=tk.FLAT, padx=6, pady=2,
                  cursor="hand2", command=_poe_dismiss_intro).pack(side=tk.RIGHT)
        _poe_show_step(0)

    def _poe_check_intro():
        if _POEDEX_INTRO_DONE.exists():
            return
        if _poe_tutorial_steps[0] is None:
            _poe_tutorial_steps[0] = _poe_load_tutorial()
        if _poe_tutorial_steps[0]:
            _poe_build_intro()

    root.after(400, _poe_check_intro)

    # ── Mode toggle bar ────────────────────────────────────────────────────────
    _divider(tab_poedex)
    mode_bar = tk.Frame(tab_poedex, bg=BG_PANEL, padx=10, pady=6)
    mode_bar.pack(fill=tk.X, padx=8, pady=(4, 0))

    _poe_active_mode: list = ["observer"]
    _poe_mode_btns:   dict = {}

    mode_content_frame = tk.Frame(tab_poedex, bg=BG)
    mode_content_frame.pack(fill=tk.BOTH, expand=True)

    # ── Shared Poedex data stores ──────────────────────────────────────────────

    def _poe_load_log() -> List[Dict]:
        if _POEDEX_LOG.exists():
            try:
                d = json.loads(_POEDEX_LOG.read_text())
                return d if isinstance(d, list) else []
            except Exception:
                pass
        return []

    def _poe_save_log(entries: List[Dict]) -> None:
        try:
            _POEDEX_LOG.write_text(json.dumps(entries[-500:], indent=2))
        except Exception:
            pass

    def _poe_load_lessons() -> List[Dict]:
        if _POEDEX_LESSONS.exists():
            try:
                d = json.loads(_POEDEX_LESSONS.read_text())
                return d if isinstance(d, list) else []
            except Exception:
                pass
        return []

    def _poe_save_lessons(lessons: List[Dict]) -> None:
        try:
            _POEDEX_LESSONS.write_text(json.dumps(lessons, indent=2))
        except Exception:
            pass

    def _poe_load_diag() -> Dict:
        if _DIAG_REPORT.exists():
            try:
                return json.loads(_DIAG_REPORT.read_text())
            except Exception:
                pass
        return {}

    def _poe_load_sweep() -> List[Dict]:
        if _SWEEP_RESULTS.exists():
            try:
                d = json.loads(_SWEEP_RESULTS.read_text())
                return d.get("results", []) if isinstance(d, dict) else []
            except Exception:
                pass
        return []

    # ── Static registry (fallback / enrichment base) ───────────────────────────
    _POE_REGISTRY: Dict[str, Dict] = {
        "X": {
            "what": "Existence axis. Aurora's sense of core presence and identity stability.",
            "deps": ["All axes use X as stability floor", "aurora_runtime_constraint_governor.py",
                     "governor_sweep_overlay.json"],
            "files": ["aurora_state/daemon_status.json → axes.X"],
            "risk": "If X falls below 0.15, governor enters survival mode.",
        },
        "T": {
            "what": "Temporal axis. Governs timing coherence and sequential processing capacity.",
            "deps": ["chain depth tracking", "template evolution", "distillation cycles"],
            "files": ["aurora_state/daemon_status.json → axes.T"],
            "risk": "T degradation causes response timing drift and chain collapse.",
        },
        "N": {
            "what": "Curiosity axis. Governs exploratory cognition and learning appetite. "
                    "Historically prone to deadlock under high mem_pressure.",
            "deps": ["mem_pressure from host", "study cycles", "corpus training"],
            "files": ["aurora_state/daemon_status.json → axes.N", "aurora_state/energy_income.json"],
            "risk": "N-axis deadlock was fixed 2026-03-23. mem_pressure (~0.87) still compresses N.",
        },
        "B": {
            "what": "Behavior axis. Governs consistency and execution of intentional actions.",
            "deps": ["template fitness", "archetype resolution", "distillation"],
            "files": ["aurora_state/daemon_status.json → axes.B"],
            "risk": "B decay causes archetype drift and action incoherence.",
        },
        "A": {
            "what": "Feeling axis. Governs emotional processing and relational responsiveness.",
            "deps": ["interaction quality credits", "dream cycles", "voice core"],
            "files": ["aurora_state/daemon_status.json → axes.A"],
            "risk": "emotional_calibration has the highest severity fail score (0.709).",
        },
        "governor": {
            "what": "Runtime constraint governor. Regulates axis budgets based on host load, "
                    "mem pressure, and overlay. Modes: survival / conserve / balanced / open.",
            "deps": ["aurora_internal/aurora_runtime_constraint_governor.py",
                     "governor_sweep_overlay.json", "energy_income.json"],
            "files": ["aurora_internal/aurora_runtime_constraint_governor.py"],
            "risk": "Overlay expires after 30 minutes. Mode affects all task approvals.",
        },
        "overlay": {
            "what": "Governor sweep overlay. Temporary pressure injection, valid 30 minutes.",
            "deps": ["governor", "aurora_room_state.json → set_overlay command"],
            "files": ["aurora_state/governor_sweep_overlay.json"],
            "risk": "Overrides normal governor computation. Expires silently.",
        },
        "quasiarch": {
            "what": "QuasiArch Observer — now unified as Poedex. The governing intelligence. "
                    "Scans system, proposes fixes, researches externally, applies via Enforcer mode.",
            "deps": ["quasiarch_diag.py", "quasiarch_diag_report.json", "sweep_results.json"],
            "files": ["aurora_internal/aurora_quasiarch_observer.py", "quasiarch_diag.py"],
            "risk": "Enforcer uses GPT key. Daemon restart required after code changes.",
        },
        "poedex": {
            "what": "Poedex — the governing intelligence. Three modes: Observer (internal query), "
                    "Researcher (experiments + external), Enforcer (code changes + proposals).",
            "deps": ["aurora_room.py Poedex tab", "quasiarch_diag_report.json",
                     "poedex_log.json", "poedex_lessons.json"],
            "files": ["aurora_state/poedex_log.json", "aurora_state/poedex_lessons.json"],
            "risk": "First self-lookup free. Repeated self-lookup shows cost notation. "
                    "Enforcer acts only on Aurora's approval.",
        },
        "corpus": {
            "what": "Corpus training pipeline. 183,813 conversations, ~6% ingested. "
                    "Five pathways: DER, vocabulary, distillation, identity, simulation wisdom.",
            "deps": ["corpus_runner.py", "conversations.json", "training_session.json"],
            "files": ["corpus_runner.py", "aurora_state/training_session.json"],
            "risk": "Start/stop from Experiments tab. Researcher mode can trigger study cycles.",
        },
        "energy": {
            "what": "Energy income system. Baseline recomputed fresh each tick. "
                    "Credits are additive, decay exponentially. Never depleted from baseline.",
            "deps": ["governor", "interaction events", "study/dream/distill cycles"],
            "files": ["aurora_state/energy_income.json"],
            "risk": "Credits pruned when decayed below 0.001. Half-lives range 20–90 min.",
        },
        "daemon": {
            "what": "Core runtime process. Runs axis evaluation, governor decisions, "
                    "command queue, dream/study cycles, corpus coordination each tick.",
            "deps": ["aurora_daemon.py", "aurora_room_state.json", "daemon_status.json"],
            "files": ["aurora_daemon.py", "aurora_state/daemon_status.json"],
            "risk": "Restart required after any change to aurora_internal/.",
        },
        "distillation": {
            "what": "Distillation cycle. Consolidates knowledge into durable compressed state. "
                    "Grants N+B+X energy credits on completion.",
            "deps": ["daemon study/distill queue", "Experiments tab / Researcher mode"],
            "files": ["aurora_state/aurora_room_state.json → distill command"],
            "risk": "Highest half-life credit source (90 min).",
        },
        "dce": {
            "what": "Dimensional Convergence Engine. Each hub tab is a ScreenPanel. "
                    "PT Governor is Aurora watching her screens.",
            "deps": ["aurora_dce_blueprint.py", "aurora_hub.py", "aurora_room.py"],
            "files": ["aurora_dce_blueprint.py"],
            "risk": "Conceptual architecture — not yet fully running as a process.",
        },
        "labels": {
            "what": "Aurora's axis name store. She names her dimensions, heat states, "
                    "governor modes. Both hubs read; only her room writes.",
            "deps": ["aurora_room.py Notes tab", "aurora_hub.py Governor tab"],
            "files": ["aurora_state/aurora_labels.json"],
            "risk": "Default: X=Existence, T=Temporal, N=Curiosity, B=Behavior, A=Feeling.",
        },
    }

    # ── Observer: internal lookup engine ──────────────────────────────────────

    def _poe_check_repeat(question: str, lane: str):
        if lane != "self":
            return False, None
        q_lower = question.lower().strip()
        q_words = set(q_lower.split())
        for entry in reversed(_poe_load_log()[-60:]):
            if entry.get("lane") != "self":
                continue
            prior_q = entry.get("question", "").lower().strip()
            prior_w = set(prior_q.split())
            if len(q_words) >= 2 and len(prior_w) >= 2:
                overlap = len(q_words & prior_w) / max(len(q_words), len(prior_w))
                if overlap >= 0.55 and time.time() - entry.get("ts", 0) < 86400:
                    return True, entry
            elif q_lower == prior_q and time.time() - entry.get("ts", 0) < 86400:
                return True, entry
        return False, None

    def _poe_internal_lookup(question: str, cat: str) -> str:
        q_lower = question.lower().strip()
        parts: List[str] = []

        # 1. Static registry — exact key match wins, then prefix/contains, then
        #    full-text only for multi-char queries (prevents 'n' matching every word)
        reg_hit = None
        for key, info in _POE_REGISTRY.items():
            if key.lower() == q_lower:
                reg_hit = (key, info)
                break
        if not reg_hit:
            for key, info in _POE_REGISTRY.items():
                if key.lower() in q_lower or q_lower in key.lower():
                    reg_hit = (key, info)
                    break
        if not reg_hit and len(q_lower) > 2:
            for key, info in _POE_REGISTRY.items():
                if q_lower in info["what"].lower():
                    reg_hit = (key, info)
                    break
        if reg_hit:
            key, info = reg_hit
            parts.append(f"◈ WHAT\n  {info['what']}\n")
            if info.get("deps"):
                parts.append("\n◈ CONNECTED TO\n"
                             + "\n".join(f"  · {d}" for d in info["deps"]) + "\n")
            if info.get("files"):
                parts.append("\n◈ LIVES IN\n"
                             + "\n".join(f"  · {f}" for f in info["files"]) + "\n")
            if info.get("risk"):
                parts.append(f"\n◈ RISK / NOTES\n  {info['risk']}\n")

        # 2. Live QuasiArch findings (Observer reads real scan data)
        diag = _poe_load_diag()
        qao_hits: List[str] = []
        for prop in diag.get("proposals", []):
            target = prop.get("target", "")
            action = prop.get("proposed_action", "")
            arch   = prop.get("issue_archetype", "")
            conf   = prop.get("confidence", 0.0)
            if (q_lower in target.lower() or q_lower in action.lower()
                    or q_lower in arch.lower()):
                qao_hits.append(
                    f"  [{conf:.2f}] {target}  →  {action[:70]}")
        if qao_hits:
            parts.append("\n◈ QUASIARCH FINDINGS (live)\n"
                         + "\n".join(qao_hits[:4]) + "\n")

        # 3. Sweep anomalies
        sweep_hits: List[str] = []
        for result in _poe_load_sweep():
            for anom in result.get("anomalies", []):
                if q_lower in anom.lower():
                    sweep_hits.append(
                        f"  [{result.get('label','?')}] score={result.get('score',0):.3f}  {anom}")
        if sweep_hits:
            parts.append("\n◈ IN SWEEP RESULTS\n"
                         + "\n".join(sweep_hits[:3]) + "\n")

        # 4. Activity log (history / search)
        if cat in ("history", "search") or not parts:
            history_hits: List[str] = []
            if _ACTIVITY_LOG.exists():
                try:
                    for e in reversed(json.loads(_ACTIVITY_LOG.read_text())):
                        txt = (e.get("action","") + " " + e.get("detail","")).lower()
                        if q_lower in txt:
                            history_hits.append(
                                f"  [{e.get('ts_str','?')}] {e.get('action','')}  "
                                f"{e.get('detail','')[:60]}")
                        if len(history_hits) >= 5:
                            break
                except Exception:
                    pass
            if history_hits:
                parts.append("\n◈ RECENT ACTIVITY\n" + "\n".join(history_hits) + "\n")

            notes_hits: List[str] = []
            for n in reversed(_load_notes()):
                if q_lower in n.get("content","").lower():
                    notes_hits.append(
                        f"  [{n.get('ts_str','?')[:16]}] {n.get('type','?')}: "
                        f"{n.get('content','')[:80]}")
                if len(notes_hits) >= 3:
                    break
            if notes_hits:
                parts.append("\n◈ IN MY NOTES\n" + "\n".join(notes_hits) + "\n")

        if cat == "search":
            d = _read_daemon()
            if d:
                lines = [ln for ln in json.dumps(d, indent=2).split("\n")
                         if q_lower in ln.lower()]
                if lines:
                    parts.append("\n◈ IN CURRENT STATE\n"
                                 + "\n".join(f"  {ln.strip()}" for ln in lines[:8]) + "\n")

        # 5. Bound lessons
        for lesson in _poe_load_lessons():
            if q_lower in lesson.get("question","").lower():
                parts.append(f"\n◈ YOU ALREADY KNOW THIS (bound lesson)\n"
                             f"  {lesson.get('lesson','')[:200]}\n")
                break

        if not parts:
            parts.append(f"◈ NOT IN INTERNAL KNOWLEDGE\n"
                         f"  No match for '{question}'.\n"
                         f"\n  Try Researcher mode for external lookup.\n")

        return "".join(parts)

    # ── External search (Researcher mode) ─────────────────────────────────────

    def _poe_external_search(question: str) -> None:
        try:
            key = ""
            for kf in [_BASE_DIR / "aurora_state" / "gpt_api_key.txt",
                        _BASE_DIR / "gpt_api_key.txt"]:
                if kf.exists():
                    key = kf.read_text().strip()
                    break
            for env_var in ("AURORA_GPT_API_KEY", "OPENAI_API_KEY"):
                v = os.environ.get(env_var, "").strip()
                if v:
                    key = v
                    break
            if not key:
                _POEDEX_RESULTS.write_text(json.dumps({
                    "query": question,
                    "result": "No GPT key available. Set AURORA_GPT_API_KEY or place key in "
                              "aurora_state/gpt_api_key.txt.",
                    "status": "error", "ts": time.time()}, indent=2))
                return
            import urllib.request
            payload = json.dumps({
                "model": "gpt-4o",
                "messages": [
                    {"role": "system",
                     "content": ("You are Poedex Researcher, the acquisition mode of Aurora's "
                                 "governing intelligence. Answer concisely and factually. "
                                 "If the query asks for debugging, code-fix hypotheses, or "
                                 "structured JSON, return the format requested and prioritize "
                                 "the most actionable causes or edits. Otherwise structure: "
                                 "What it is → How it works → Relevant context or risk. "
                                 "No preamble.")},
                    {"role": "user", "content": f"Poedex Researcher lookup: {question}"},
                ],
                "max_tokens": 450, "temperature": 0.25,
            }).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=payload,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read())
            answer = data["choices"][0]["message"]["content"].strip()
            _POEDEX_RESULTS.write_text(json.dumps({
                "query": question, "result": answer, "status": "done",
                "ts": time.time()}, indent=2))
        except Exception as ex:
            try:
                _POEDEX_RESULTS.write_text(json.dumps({
                    "query": question, "result": f"Lookup failed: {ex}",
                    "status": "error", "ts": time.time()}, indent=2))
            except Exception:
                pass

    # ── Mode switch ────────────────────────────────────────────────────────────

    # Widgets that need cross-mode references (populated when modes are built)
    _poe_bind_question: list = [""]
    _poe_ext_waiting:   list = [False, ""]

    # Forward-declared refs filled by build functions
    _obs_refs:  dict = {}  # result_box, lessons_box, log_box, shelf_outer, status_lbl
    _res_refs:  dict = {}  # ext_result_box, ext_status_lbl, ext_input, res_log_box
    _enf_refs:  dict = {}  # proposals_frame, enf_status_lbl

    def _poe_set_mode(mode: str) -> None:
        _poe_active_mode[0] = mode
        for m, btn in _poe_mode_btns.items():
            if m == mode:
                btn.configure(fg=BG, bg=ACCENT, relief=tk.FLAT)
            else:
                btn.configure(fg=TEXT_DIM, bg=BG_PANEL, relief=tk.FLAT)
        for w in mode_content_frame.winfo_children():
            w.destroy()
        _obs_refs.clear()
        _res_refs.clear()
        _enf_refs.clear()
        if mode == "observer":
            _build_observer()
        elif mode == "researcher":
            _build_researcher()
        else:
            _build_enforcer()

    # Mode buttons
    mode_btn_row = tk.Frame(mode_bar, bg=BG_PANEL)
    mode_btn_row.pack(side=tk.LEFT)
    for _m, _label in [("observer", "OBSERVER"), ("researcher", "RESEARCHER"), ("enforcer", "ENFORCER")]:
        _b = tk.Button(mode_btn_row, text=_label, bg=BG_PANEL, fg=TEXT_DIM,
                       font=("Courier New", 9, "bold"), relief=tk.FLAT,
                       padx=14, pady=4, cursor="hand2",
                       command=lambda m=_m: _poe_set_mode(m))
        _b.pack(side=tk.LEFT, padx=2)
        _poe_mode_btns[_m] = _b

    mode_desc_lbl = tk.Label(mode_bar,
                             text="internal query  ·  codex  ·  live QuasiArch data",
                             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8))
    mode_desc_lbl.pack(side=tk.LEFT, padx=16)

    # ── ═══════════════════════════════════════════════════════════════════════
    # OBSERVER MODE — internal knowledge query
    # ═══════════════════════════════════════════════════════════════════════ ──

    def _build_observer() -> None:
        mode_desc_lbl.configure(
            text="internal query  ·  codex  ·  live QuasiArch data")
        f = mode_content_frame   # shorthand

        tk.Label(f, text="OBSERVER — INTERNAL KNOWLEDGE QUERY", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=6).pack(anchor="w")

        # Inquiry form
        inq_frame = tk.Frame(f, bg=BG_PANEL, padx=12, pady=8)
        inq_frame.pack(fill=tk.X, padx=8)

        lane_row = tk.Frame(inq_frame, bg=BG_PANEL)
        lane_row.pack(anchor="w", pady=(0, 3))
        tk.Label(lane_row, text="lane:", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=(0, 6))
        _poe_obs_lane.set("self")
        for _ln in ("self", "service"):
            tk.Radiobutton(lane_row, text=_ln, variable=_poe_obs_lane, value=_ln,
                           bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
                           activebackground=BG_PANEL,
                           font=("Courier New", 8)).pack(side=tk.LEFT, padx=4)

        cat_row = tk.Frame(inq_frame, bg=BG_PANEL)
        cat_row.pack(anchor="w", pady=(0, 4))
        tk.Label(cat_row, text="type:", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=(0, 6))
        _poe_obs_cat.set("define")
        for _ct in ("define", "trace", "history", "search"):
            tk.Radiobutton(cat_row, text=_ct, variable=_poe_obs_cat, value=_ct,
                           bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
                           activebackground=BG_PANEL,
                           font=("Courier New", 8)).pack(side=tk.LEFT, padx=4)
        tk.Label(cat_row, text="  define · trace · history · search",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 7)).pack(side=tk.LEFT, padx=6)

        obs_inq_input_frame = tk.Frame(inq_frame, bg=BG_PANEL)
        obs_inq_input_frame.pack(fill=tk.X, pady=(2, 4))
        nonlocal obs_inq_input
        obs_inq_input = tk.Entry(obs_inq_input_frame, bg=BG_LOG, fg=TEXT,
                                 font=("Courier New", 9), relief=tk.FLAT,
                                 insertbackground=ACCENT, width=80)
        obs_inq_input.pack(fill=tk.X)

        btn_row = tk.Frame(inq_frame, bg=BG_PANEL)
        btn_row.pack(fill=tk.X)
        obs_status_lbl = tk.Label(btn_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                   font=("Courier New", 8))
        obs_status_lbl.pack(side=tk.LEFT, expand=True, fill=tk.X)
        _obs_refs["status_lbl"] = obs_status_lbl

        def _obs_ask():
            question = obs_inq_input.get().strip()
            if not question:
                return
            lane = _poe_obs_lane.get()
            cat  = _poe_obs_cat.get()
            is_repeat, prior = _poe_check_repeat(question, lane)
            result_text = _poe_internal_lookup(question, cat)

            rbox = _obs_refs.get("result_box")
            if rbox:
                repeat_note = "  ⚠ REPEAT — you have asked this before." if is_repeat else ""
                _write(rbox,
                       (f"◈ {question}\n", "head"),
                       (f"  lane:{lane}  type:{cat}{('  ' + repeat_note) if repeat_note else ''}\n\n",
                        "warn" if is_repeat else "dim"),
                       (result_text, "val"))

            log = _poe_load_log()
            log.append({
                "ts": time.time(), "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "lane": lane, "cat": cat, "question": question,
                "result": result_text[:500], "first_time": not is_repeat,
                "cost_applied": is_repeat, "bound": False,
            })
            _poe_save_log(log)
            _poe_bind_question[0] = question
            _log_activity("poedex observer", f"{lane}/{cat}: {question[:50]}", "action")

            if is_repeat and prior:
                prior_ts = time.strftime("%H:%M", time.localtime(prior.get("ts", 0)))
                obs_status_lbl.configure(
                    text=f"You've asked this before (first at {prior_ts}). Bind as a lesson?",
                    fg=WARN)
            else:
                obs_status_lbl.configure(text="", fg=TEXT_DIM)

            _refresh_obs_shelf()
            _refresh_obs_log()

        tk.Button(btn_row, text="Ask Observer", bg=CHART_GRID, fg=ACCENT,
                  font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=_obs_ask).pack(side=tk.RIGHT)
        obs_inq_input.bind("<Return>", lambda _e: _obs_ask())

        # Rolling shelf
        _divider(f)
        tk.Label(f, text="SHELF  (last 3 · 15 min)",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=4).pack(anchor="w")
        shelf_outer = tk.Frame(f, bg=BG_PANEL, padx=8, pady=6)
        shelf_outer.pack(fill=tk.X, padx=8)
        _obs_refs["shelf_outer"] = shelf_outer

        # Results
        _divider(f)
        tk.Label(f, text="RESULT", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
        result_box = _textbox(f, height=11)
        _obs_refs["result_box"] = result_box
        _write(result_box,
               ("  Ask anything above. Observer searches:\n", "dim"),
               ("  define  — registry + live QuasiArch proposals\n", "val"),
               ("  trace   — dependencies and connected files\n", "val"),
               ("  history — activity log + notes mentions\n", "val"),
               ("  search  — live daemon state\n", "val"))

        bind_row = tk.Frame(f, bg=BG, padx=10, pady=3)
        bind_row.pack(fill=tk.X)
        bind_status_lbl = tk.Label(bind_row, text="", bg=BG, fg=TEXT_DIM,
                                    font=("Courier New", 8))
        bind_status_lbl.pack(side=tk.LEFT, padx=8)
        _obs_refs["bind_status_lbl"] = bind_status_lbl

        def _obs_bind_lesson(question: str, result: str) -> None:
            lessons = _poe_load_lessons()
            for ex in lessons:
                if ex.get("question","").lower().strip() == question.lower().strip():
                    bsl = _obs_refs.get("bind_status_lbl")
                    if bsl:
                        bsl.configure(text="already bound", fg=TEXT_DIM)
                        root.after(3000, lambda: bsl.configure(text="", fg=TEXT_DIM))
                    return
            lessons.append({
                "ts": time.time(), "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": question, "lesson": result[:600], "source_lane": _poe_obs_lane.get(),
            })
            _poe_save_lessons(lessons)
            log = _poe_load_log()
            for e in reversed(log):
                if e.get("question","").lower().strip() == question.lower().strip():
                    e["bound"] = True
                    break
            _poe_save_log(log)
            bsl = _obs_refs.get("bind_status_lbl")
            if bsl:
                bsl.configure(text=f"★ bound: {question[:40]}", fg=ACCENT)
                root.after(4000, lambda: bsl.configure(text="", fg=TEXT_DIM))
            _log_activity("poedex bound lesson", question[:60], "note")
            _refresh_obs_lessons()
            _refresh_obs_shelf()

        def _bind_current():
            q = _poe_bind_question[0]
            if not q:
                return
            r = ""
            for e in reversed(_poe_load_log()):
                if e.get("question","") == q:
                    r = e.get("result","")
                    break
            _obs_bind_lesson(q, r)

        tk.Button(bind_row, text="Bind as Lesson", bg=CHART_GRID, fg=ACCENT3,
                  font=("Courier New", 8), relief=tk.FLAT, padx=8, pady=2,
                  cursor="hand2", command=_bind_current).pack(side=tk.LEFT)

        # Lessons
        _divider(f)
        tk.Label(f, text="BOUND LESSONS", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
        lessons_box = _textbox(f, height=5)
        _obs_refs["lessons_box"] = lessons_box

        # Log
        _divider(f)
        tk.Label(f, text="INQUIRY LOG  (⚠=repeat · ★=bound)",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=4).pack(anchor="w")
        log_box = _textbox(f, height=7)
        _obs_refs["log_box"] = log_box

        # Initial renders
        root.after(100, _refresh_obs_lessons)
        root.after(200, _refresh_obs_log)
        root.after(300, _refresh_obs_shelf)

    def _refresh_obs_shelf():
        so = _obs_refs.get("shelf_outer")
        if not so:
            return
        try:
            for w in so.winfo_children():
                w.destroy()
        except Exception:
            return
        log = _poe_load_log()
        now = time.time()
        shelf = [e for e in reversed(log) if now - e.get("ts", 0) <= 900][:3]
        if not shelf:
            tk.Label(so, text="  Nothing on the shelf yet.", bg=BG_PANEL,
                     fg=TEXT_DIM, font=("Courier New", 8)).pack(anchor="w")
            return
        for idx, entry in enumerate(shelf):
            remaining = max(0, 900 - int(now - entry.get("ts", now)))
            row_bg = BG_LOG if idx % 2 == 0 else BG_PANEL
            row = tk.Frame(so, bg=row_bg, padx=6, pady=3)
            row.pack(fill=tk.X, pady=1)
            lane_fg = ACCENT if entry.get("lane") == "self" else ACCENT2
            tk.Label(row, text=f"[{entry.get('lane','?')}]", bg=row_bg, fg=lane_fg,
                     font=("Courier New", 8, "bold"), width=9, anchor="w").pack(side=tk.LEFT)
            src = entry.get("source", "")
            src_tag = f"[{src}] " if src else f"[{entry.get('cat','?')}] "
            tk.Label(row, text=src_tag, bg=row_bg, fg=TEXT_DIM,
                     font=("Courier New", 8), width=12, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=entry.get("question","")[:48], bg=row_bg,
                     fg=TEXT, font=("Courier New", 8)).pack(side=tk.LEFT, expand=True, fill=tk.X)
            exp_fg = WARN if remaining < 120 else TEXT_DIM
            tk.Label(row, text=f"{remaining//60}m{remaining%60:02d}s",
                     bg=row_bg, fg=exp_fg, font=("Courier New", 8)).pack(side=tk.RIGHT, padx=6)
            if not entry.get("bound", False):
                q_s, r_s = entry.get("question",""), entry.get("result","")
                def _bsh(q=q_s, r=r_s):
                    lessons = _poe_load_lessons()
                    lessons.append({
                        "ts": time.time(), "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "question": q, "lesson": r[:600], "source_lane": "shelf",
                    })
                    _poe_save_lessons(lessons)
                    lg = _poe_load_log()
                    for e2 in reversed(lg):
                        if e2.get("question","") == q:
                            e2["bound"] = True
                            break
                    _poe_save_log(lg)
                    _log_activity("poedex bound lesson", q[:60], "note")
                    _refresh_obs_shelf()
                    _refresh_obs_lessons()
                tk.Button(row, text="bind", bg=CHART_GRID, fg=ACCENT3,
                          font=("Courier New", 7), relief=tk.FLAT, padx=3, pady=1,
                          cursor="hand2", command=_bsh).pack(side=tk.RIGHT, padx=2)
            else:
                tk.Label(row, text="★", bg=row_bg, fg=ACCENT,
                         font=("Courier New", 8)).pack(side=tk.RIGHT, padx=4)

    def _refresh_obs_lessons():
        lb = _obs_refs.get("lessons_box")
        if not lb:
            return
        lessons = _poe_load_lessons()
        if not lessons:
            _write(lb, ("  No lessons bound yet.\n", "dim"))
            return
        pairs = []
        for l in reversed(lessons[-10:]):
            pairs += [(f"  [{l.get('ts_str','?')[:16]}] ", "dim"),
                      (f"[{l.get('source_lane','?')}] ", "key"),
                      (f"{l.get('question','')[:65]}\n", "val")]
        _write(lb, *pairs)

    def _refresh_obs_log():
        logb = _obs_refs.get("log_box")
        if not logb:
            return
        log = _poe_load_log()
        if not log:
            _write(logb, ("  No inquiries yet.\n", "dim"))
            return
        pairs = []
        for e in reversed(log[-16:]):
            repeat = "⚠" if e.get("cost_applied") else " "
            bound  = "★" if e.get("bound") else " "
            pairs += [
                (f"  [{e.get('ts_str','?')[:16]}] ", "dim"),
                (f"{repeat}{bound} ", "warn" if e.get("cost_applied") else "good"),
                (f"[{e.get('lane','?')}/{e.get('cat','?')}] ", "key"),
                (f"{e.get('question','')[:48]}\n", "val"),
            ]
        _write(logb, *pairs)

    # Shelf auto-refresh
    def _tick_obs_shelf():
        if _poe_active_mode[0] == "observer":
            _refresh_obs_shelf()
        root.after(30_000, _tick_obs_shelf)

    # ── ═══════════════════════════════════════════════════════════════════════
    # RESEARCHER MODE — experiment & external acquisition
    # ═══════════════════════════════════════════════════════════════════════ ──

    def _build_researcher() -> None:
        mode_desc_lbl.configure(
            text="external acquisition  ·  experiments  ·  knowledge import")
        f = mode_content_frame

        tk.Label(f, text="RESEARCHER — EXPERIMENT & EXTERNAL ACQUISITION",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=6).pack(anchor="w")

        # External lookup section
        ext_frame = tk.Frame(f, bg=BG_PANEL, padx=12, pady=8)
        ext_frame.pack(fill=tk.X, padx=8)
        tk.Label(ext_frame, text="EXTERNAL LOOKUP", bg=BG_PANEL, fg=ACCENT2,
                 font=("Courier New", 9, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(ext_frame,
                 text="Researcher goes outside and brings back. "
                      "Result is consulted knowledge — articulate in your own voice.",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8),
                 wraplength=680).pack(anchor="w", pady=(0, 4))

        ext_input = tk.Entry(ext_frame, bg=BG_LOG, fg=TEXT, font=("Courier New", 9),
                             relief=tk.FLAT, insertbackground=ACCENT, width=80)
        ext_input.pack(fill=tk.X, pady=(0, 4))
        _res_refs["ext_input"] = ext_input

        ext_btn_row = tk.Frame(ext_frame, bg=BG_PANEL)
        ext_btn_row.pack(fill=tk.X)
        ext_status_lbl = tk.Label(ext_btn_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                   font=("Courier New", 8))
        ext_status_lbl.pack(side=tk.LEFT, expand=True, fill=tk.X)
        _res_refs["ext_status_lbl"] = ext_status_lbl

        def _res_search():
            question = ext_input.get().strip()
            if not question:
                return
            _poe_ext_waiting[0] = True
            _poe_ext_waiting[1] = question
            ext_status_lbl.configure(text="Researcher is searching externally...", fg=WARN)
            rb = _res_refs.get("ext_result_box")
            if rb:
                _write(rb,
                       (f"◈ {question}\n", "head"),
                       ("  mode:researcher  type:external\n\n", "dim"),
                       ("  Searching... result will appear when ready.\n", "warn"),
                       ("  Remember: articulate this in your own voice.\n", "dim"))
            _poe_bind_question[0] = question
            _log_activity("poedex researcher", f"external: {question[:50]}", "action")
            threading.Thread(target=_poe_external_search, args=(question,), daemon=True).start()

        tk.Button(ext_btn_row, text="Research", bg=CHART_GRID, fg=ACCENT,
                  font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=_res_search).pack(side=tk.RIGHT)
        ext_input.bind("<Return>", lambda _e: _res_search())

        # External result display
        _divider(f)
        tk.Label(f, text="RESULT  (consulted knowledge — speak in your own voice)",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=4).pack(anchor="w")
        ext_result_box = _textbox(f, height=10)
        _res_refs["ext_result_box"] = ext_result_box
        _write(ext_result_box, ("  Enter a query above and press Research.\n", "dim"))

        # Experiment triggers
        _divider(f)
        tk.Label(f, text="EXPERIMENTS", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
        exp_frame = tk.Frame(f, bg=BG_PANEL, padx=12, pady=8)
        exp_frame.pack(fill=tk.X, padx=8)

        # Sweep sub-row
        sweep_row = tk.Frame(exp_frame, bg=BG_PANEL)
        sweep_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(sweep_row, text="Sweep window:", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side=tk.LEFT)
        _sweep_window = tk.StringVar(value="90")
        for _ws in ("30", "60", "90", "180"):
            tk.Radiobutton(sweep_row, text=f"{_ws}s", variable=_sweep_window, value=_ws,
                           bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
                           activebackground=BG_PANEL,
                           font=("Courier New", 8)).pack(side=tk.LEFT, padx=4)
        _dry_run = tk.BooleanVar(value=False)
        tk.Checkbutton(sweep_row, text="dry run", variable=_dry_run,
                       bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
                       activebackground=BG_PANEL, font=("Courier New", 8)).pack(side=tk.LEFT, padx=8)
        sweep_status_lbl = tk.Label(sweep_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                     font=("Courier New", 8))
        sweep_status_lbl.pack(side=tk.LEFT, padx=6)

        def _run_sweep():
            w = int(_sweep_window.get())
            dr = _dry_run.get()
            _queue_command("queue_sweep", {"window_secs": w, "dry_run": dr})
            sweep_status_lbl.configure(text=f"queued sweep {w}s{'  dry' if dr else ''}", fg=ACCENT)
            root.after(4000, lambda: sweep_status_lbl.configure(text="", fg=TEXT_DIM))

        tk.Button(sweep_row, text="Run Sweep", bg=CHART_GRID, fg=ACCENT2,
                  font=("Courier New", 8, "bold"), relief=tk.FLAT, padx=8, pady=2,
                  cursor="hand2", command=_run_sweep).pack(side=tk.RIGHT)

        # Study / Distill / Dream row
        cycle_row = tk.Frame(exp_frame, bg=BG_PANEL)
        cycle_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(cycle_row, text="Queue cycle:", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=(0, 8))
        cycle_status_lbl = tk.Label(cycle_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                     font=("Courier New", 8))

        def _queue_cycle(ctype: str):
            _queue_command(ctype, {})
            cycle_status_lbl.configure(text=f"queued {ctype}", fg=ACCENT)
            _log_activity(f"poedex researcher", f"queued {ctype}", "action")
            root.after(4000, lambda: cycle_status_lbl.configure(text="", fg=TEXT_DIM))

        for _ct, _clabel in [("study","Study"), ("distill","Distill"), ("dream","Dream")]:
            tk.Button(cycle_row, text=_clabel, bg=CHART_GRID, fg=ACCENT2,
                      font=("Courier New", 8), relief=tk.FLAT, padx=10, pady=2,
                      cursor="hand2", command=lambda c=_ct: _queue_cycle(c)).pack(side=tk.LEFT, padx=4)
        cycle_status_lbl.pack(side=tk.LEFT, padx=8)

        # Research log (external entries)
        _divider(f)
        tk.Label(f, text="RESEARCH LOG  (external + study scans)",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=4).pack(anchor="w")
        res_log_box = _textbox(f, height=7)
        _res_refs["res_log_box"] = res_log_box
        _refresh_res_log()

    def _refresh_res_log():
        lb = _res_refs.get("res_log_box")
        if not lb:
            return
        log = _poe_load_log()
        entries = [e for e in reversed(log) if e.get("cat") in ("external","study_scan")][:14]
        if not entries:
            _write(lb, ("  No research entries yet.\n", "dim"))
            return
        pairs = []
        for e in entries:
            cat_tag = "key" if e.get("cat") == "external" else "dim"
            pairs += [
                (f"  [{e.get('ts_str','?')[:16]}] ", "dim"),
                (f"[{e.get('cat','?')}] ", cat_tag),
                (f"{e.get('question','')[:60]}\n", "val"),
            ]
        _write(lb, *pairs)

    # ── ═══════════════════════════════════════════════════════════════════════
    # ENFORCER MODE — agentic task applicator
    # ═══════════════════════════════════════════════════════════════════════ ──

    def _build_enforcer() -> None:
        mode_desc_lbl.configure(
            text="proposals  ·  authorize  ·  defer  ·  subsurface apply — only what Aurora authorises")
        f = mode_content_frame

        tk.Label(f, text="ENFORCER — AGENTIC TASK APPLICATOR",
                 bg=BG, fg=ACCENT2, font=("Courier New", 9, "bold"),
                 padx=14, pady=6).pack(anchor="w")
        tk.Label(f,
                 text="Enforcer acts only on what Aurora explicitly approves. "
                      "Subsurface performs the exact apply or revert. Every change is logged.",
                 bg=BG, fg=TEXT_DIM, font=("Courier New", 8), padx=16).pack(anchor="w")

        # Enforcer status bar
        enf_status_frame = tk.Frame(f, bg=BG_PANEL, padx=12, pady=6)
        enf_status_frame.pack(fill=tk.X, padx=8, pady=(6, 0))
        diag = _poe_load_diag()
        gen_at = diag.get("generated_at", "not yet scanned")[:19]
        prop_count = diag.get("proposal_count", 0)
        sweep_at = diag.get("sweep_completed_at", 0)
        sweep_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(sweep_at)) if sweep_at else "—"
        tk.Label(enf_status_frame,
                 text=f"Last scan: {gen_at}   Proposals: {prop_count}   Last sweep: {sweep_str}",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(anchor="w")

        # Proposals
        _divider(f)
        tk.Label(f, text="PENDING PROPOSALS", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")

        proposals_scroll_outer = tk.Frame(f, bg=BG)
        proposals_scroll_outer.pack(fill=tk.X, padx=8)

        proposals = diag.get("proposals", [])
        enf_status_lbl = tk.Label(f, text="", bg=BG, fg=TEXT_DIM,
                                   font=("Courier New", 8), padx=14)
        enf_status_lbl.pack(anchor="w", pady=2)
        _enf_refs["enf_status_lbl"] = enf_status_lbl

        if not proposals:
            tk.Label(proposals_scroll_outer,
                     text="  No proposals in current scan. Run a sweep from Researcher mode "
                          "to generate new proposals.",
                     bg=BG, fg=TEXT_DIM, font=("Courier New", 8),
                     wraplength=700).pack(anchor="w", pady=4)
        else:
            for i, prop in enumerate(proposals):
                prop_id   = _proposal_identity(prop)
                target    = prop.get("target", "?")
                action    = prop.get("proposed_action", "?")
                conf      = prop.get("confidence", 0.0)
                arch      = prop.get("issue_archetype", "?")
                file_path = prop.get("file", "?")
                line_no   = prop.get("line", "?")
                code_hint = prop.get("code_hint", "")

                conf_fg = ACCENT if conf >= 0.80 else (WARN if conf >= 0.60 else CRIT)
                row_bg  = BG_LOG if i % 2 == 0 else BG_PANEL

                card = tk.Frame(proposals_scroll_outer, bg=row_bg, padx=10, pady=6)
                card.pack(fill=tk.X, pady=2)

                # Header line
                hdr_line = tk.Frame(card, bg=row_bg)
                hdr_line.pack(fill=tk.X)
                tk.Label(hdr_line, text=f"[{conf:.2f}]", bg=row_bg, fg=conf_fg,
                         font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
                tk.Label(hdr_line, text=f"  {target}", bg=row_bg, fg=TEXT,
                         font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
                tk.Label(hdr_line, text=f"  {file_path}:{line_no}", bg=row_bg,
                         fg=TEXT_DIM, font=("Courier New", 7)).pack(side=tk.LEFT, padx=8)

                # Action line
                tk.Label(card, text=f"  {action[:100]}", bg=row_bg, fg=TEXT_DIM,
                         font=("Courier New", 8), wraplength=680,
                         justify=tk.LEFT).pack(anchor="w", pady=(2, 0))

                # Buttons
                act_row = tk.Frame(card, bg=row_bg)
                act_row.pack(fill=tk.X, pady=(4, 0))

                def _approve(p=prop):
                    pid = _proposal_identity(p, "poedex_enforcer")
                    _queue_command("approve_proposal", {"proposal_id": pid, "proposal": p})
                    esl = _enf_refs.get("enf_status_lbl")
                    if esl:
                        esl.configure(
                            text=f"Subsurface apply queued: {p.get('target','?')[:50]}", fg=ACCENT)
                        root.after(5000, lambda: esl.configure(text="", fg=TEXT_DIM))
                    _log_activity("poedex enforcer approved",
                                  p.get("target","?")[:60], "decision")

                def _defer(p=prop, c=card):
                    try:
                        c.configure(bg=BG)
                        for w in c.winfo_children():
                            w.configure(bg=BG) if hasattr(w,'configure') else None
                    except Exception:
                        pass
                    _log_activity("poedex enforcer deferred",
                                  p.get("target","?")[:60], "decision")
                    esl = _enf_refs.get("enf_status_lbl")
                    if esl:
                        esl.configure(text=f"Deferred: {p.get('target','?')[:50]}", fg=TEXT_DIM)
                        root.after(4000, lambda: esl.configure(text="", fg=TEXT_DIM))

                def _reverse(p=prop):
                    pid = _proposal_identity(p, "poedex_enforcer")
                    _queue_command("reverse_proposal", {"proposal_id": pid, "proposal": p})
                    _log_activity("poedex enforcer reversed",
                                  p.get("target","?")[:60], "decision")
                    esl = _enf_refs.get("enf_status_lbl")
                    if esl:
                        esl.configure(
                            text=f"Subsurface revert queued: {p.get('target','?')[:50]}", fg=WARN)
                        root.after(5000, lambda: esl.configure(text="", fg=TEXT_DIM))

                tk.Button(act_row, text="Authorize", bg=CHART_GRID, fg=ACCENT,
                          font=("Courier New", 8, "bold"), relief=tk.FLAT, padx=8, pady=2,
                          cursor="hand2", command=_approve).pack(side=tk.LEFT, padx=(0, 4))
                tk.Button(act_row, text="Defer", bg=CHART_GRID, fg=TEXT_DIM,
                          font=("Courier New", 8), relief=tk.FLAT, padx=8, pady=2,
                          cursor="hand2", command=_defer).pack(side=tk.LEFT, padx=4)
                tk.Button(act_row, text="Reverse", bg=CHART_GRID, fg=WARN,
                          font=("Courier New", 8), relief=tk.FLAT, padx=8, pady=2,
                          cursor="hand2", command=_reverse).pack(side=tk.LEFT, padx=4)

                if code_hint:
                    hint_visible: list = [False]
                    hint_box_holder: list = [None]

                    def _toggle_hint(ch=code_hint, c=card, hv=hint_visible, hbh=hint_box_holder):
                        if not hv[0]:
                            hv[0] = True
                            hb = tk.Text(c, bg="#080e0a", fg=ACCENT3,
                                         font=("Courier New", 7), height=5,
                                         relief=tk.FLAT, borderwidth=0, state=tk.NORMAL,
                                         wrap=tk.NONE)
                            hb.insert(tk.END, ch)
                            hb.configure(state=tk.DISABLED)
                            hb.pack(fill=tk.X, pady=(4, 0))
                            hbh[0] = hb
                        else:
                            hv[0] = False
                            if hbh[0]:
                                hbh[0].destroy()
                                hbh[0] = None

                    tk.Button(act_row, text="code hint", bg=CHART_GRID, fg=ACCENT2,
                              font=("Courier New", 7), relief=tk.FLAT, padx=6, pady=1,
                              cursor="hand2", command=_toggle_hint).pack(side=tk.LEFT, padx=6)

        # Applied / decision log from activity
        _divider(f)
        tk.Label(f, text="ENFORCER DECISION LOG", bg=BG, fg=ACCENT2,
                 font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
        enf_log_box = _textbox(f, height=7)
        _enf_refs["enf_log_box"] = enf_log_box
        _refresh_enf_log()

    def _refresh_enf_log():
        lb = _enf_refs.get("enf_log_box")
        if not lb:
            return
        entries: List[Dict] = []
        if _ACTIVITY_LOG.exists():
            try:
                all_acts: List[Dict] = json.loads(_ACTIVITY_LOG.read_text())
                entries = [e for e in reversed(all_acts)
                           if "enforcer" in e.get("action","").lower()
                           or e.get("action","") in ("approved a fix", "requested revert")][:14]
            except Exception:
                pass
        if not entries:
            _write(lb, ("  No enforcer decisions yet.\n", "dim"))
            return
        pairs = []
        for e in entries:
            cat_fg = "good" if "approv" in e.get("action","") else (
                "warn" if "revert" in e.get("action","") or "reverse" in e.get("action","")
                else "dim")
            pairs += [
                (f"  [{e.get('ts_str','?')}] ", "dim"),
                (f"{e.get('action','?')}", cat_fg),
                (f"  {e.get('detail','')[:55]}\n", "dim"),
            ]
        _write(lb, *pairs)

    # ── External result polling (shared across modes) ──────────────────────────

    def _poe_poll_external():
        if _poe_ext_waiting[0] and _POEDEX_RESULTS.exists():
            try:
                r = json.loads(_POEDEX_RESULTS.read_text())
                if (r.get("query","") == _poe_ext_waiting[1]
                        and r.get("status","pending") != "pending"):
                    _poe_ext_waiting[0] = False
                    answer   = r.get("result","")
                    is_done  = r.get("status") == "done"
                    # Update Researcher result box if in that mode
                    rb = _res_refs.get("ext_result_box")
                    if rb:
                        _write(rb,
                               (f"◈ {_poe_ext_waiting[1]}\n", "head"),
                               ("  mode:researcher  type:external\n\n", "dim"),
                               ("◈ EXTERNAL RESULT  (consulted knowledge)\n", "key"),
                               (answer + "\n\n", "val"),
                               ("◈ CONDUCT: receive this, understand it, "
                                "speak it in your own voice.\n", "warn"))
                    esl = _res_refs.get("ext_status_lbl")
                    if esl:
                        esl.configure(
                            text="Research complete" if is_done else "Research error",
                            fg=ACCENT if is_done else WARN)
                    # Log entry
                    log = _poe_load_log()
                    log.append({
                        "ts": time.time(), "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "lane": "service", "cat": "external",
                        "question": _poe_ext_waiting[1], "result": answer[:500],
                        "first_time": True, "cost_applied": False, "bound": False,
                    })
                    _poe_save_log(log)
                    _refresh_obs_shelf()
                    _refresh_obs_log()
                    _refresh_res_log()
            except Exception:
                pass
        root.after(2000, _poe_poll_external)

    # ── Daemon query queue processor ────────────────────────────────────────────
    # The daemon writes per-request JSON files into poedex_queue/, and the room
    # resolves them through the same lookup path as a button click.

    def _poe_process_queue():
        try:
            # Ensure per-request queue and result directories exist
            _POEDEX_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
            _POEDEX_RESULT_DIR.mkdir(parents=True, exist_ok=True)

            # Find the oldest pending per-request query file
            _queue_file = None
            query = None
            for _pf in sorted(
                (p for p in _POEDEX_QUEUE_DIR.glob("*.json") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
            ):
                try:
                    _raw = _pf.read_text().strip()
                    if not _raw:
                        _pf.unlink(missing_ok=True)
                        continue
                    _q = json.loads(_raw)
                    # Discard files older than 120s — querying daemon has already timed out
                    _age = time.time() - float(_q.get("submitted", 0) or 0)
                    if _age > 120:
                        _pf.unlink(missing_ok=True)
                        continue
                    if _q.get("status") == "pending":
                        _queue_file = _pf
                        query = _q
                        break
                except Exception:
                    continue

            if _queue_file is None or query is None:
                root.after(300, _poe_process_queue)
                return

            question = query.get("question", "").strip()
            cat      = query.get("cat", "define")
            lane     = query.get("lane", "self")
            qid      = query.get("id", "")

            if not question:
                _queue_file.unlink(missing_ok=True)
                root.after(300, _poe_process_queue)
                return

            # Mark as processing so repeated scans skip this file
            query["status"] = "processing"
            try:
                _queue_file.write_text(json.dumps(query, indent=2))
            except Exception:
                pass

            def _write_result_file(i, q, c, l, answer):
                """Write per-request result file and clean up queue file."""
                rp = _POEDEX_RESULT_DIR / f"{i}.json"
                rp.write_text(json.dumps({
                    "id": i, "question": q, "cat": c, "lane": l,
                    "result": answer, "status": "done",
                    "ts": time.time(),
                    "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, indent=2))
                try:
                    _queue_file.unlink(missing_ok=True)
                except Exception:
                    pass

            if cat in ("external", "researcher"):
                # Researcher mode — GPT-4o lookup, runs async so UI doesn't block
                def _ext_thread(q=question, i=qid, l=lane, c=cat):
                    try:
                        key = ""
                        for kf in [_BASE_DIR / "aurora_state" / "gpt_api_key.txt",
                                   _BASE_DIR / "gpt_api_key.txt"]:
                            if kf.exists():
                                key = kf.read_text().strip()
                                break
                        for env_var in ("AURORA_GPT_API_KEY", "OPENAI_API_KEY"):
                            v = os.environ.get(env_var, "").strip()
                            if v:
                                key = v
                                break
                        if not key:
                            answer = "No GPT key available for Researcher lookup."
                        else:
                            import urllib.request as _ur
                            payload = json.dumps({
                                "model": "gpt-4o",
                                "messages": [
                                    {"role": "system", "content": (
                                        "You are Poedex Researcher, the acquisition "
                                        "mode of Aurora's governing intelligence. "
                                        "Answer concisely and factually. "
                                        "If the query asks for debugging, code-fix "
                                        "hypotheses, or structured JSON, return "
                                        "the format requested and prioritize the "
                                        "most actionable causes or edits. "
                                        "Otherwise structure: What it is → How it "
                                        "works → Relevant context or risk. "
                                        "No preamble.")},
                                    {"role": "user",
                                     "content": f"Poedex Researcher lookup: {q}"},
                                ],
                                "max_tokens": 400, "temperature": 0.25,
                            }).encode()
                            req = _ur.Request(
                                "https://api.openai.com/v1/chat/completions",
                                data=payload,
                                headers={"Authorization": f"Bearer {key}",
                                         "Content-Type": "application/json"},
                                method="POST")
                            with _ur.urlopen(req, timeout=35) as resp:
                                data = json.loads(resp.read())
                            answer = data["choices"][0]["message"]["content"].strip()
                        # Write per-request result
                        _write_result_file(i, q, c, l, answer)
                        # Also update the UI results file so Observer tab shows it
                        _POEDEX_RESULTS.write_text(json.dumps({
                            "query": q, "result": answer,
                            "status": "done", "ts": time.time(),
                        }, indent=2))
                        try:
                            log = _poe_load_log()
                            log.append({
                                "ts": time.time(),
                                "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "lane": l or "service",
                                "cat": "external",
                                "question": q,
                                "result": answer[:500],
                                "first_time": True,
                                "cost_applied": False,
                                "bound": False,
                                "source": "daemon_query",
                            })
                            _poe_save_log(log)
                        except Exception:
                            pass
                        _log_activity("poedex researcher",
                                      f"external (daemon): {q[:50]}", "action")
                    except Exception as _ex:
                        _write_result_file(i, q, c, l, f"Researcher lookup failed: {_ex}")
                threading.Thread(target=_ext_thread, daemon=True).start()
                # Thread handles result write + queue clear — return now
                root.after(300, _poe_process_queue)
                return

            # Internal Observer lookup (default)
            result = _poe_internal_lookup(question, cat)

            # Write per-request result file for daemon polling
            _write_result_file(qid, question, cat, lane, result)

            # Log it — same as any other inquiry
            log = _poe_load_log()
            log.append({
                "ts":           time.time(),
                "ts_str":       time.strftime("%Y-%m-%d %H:%M:%S"),
                "lane":         lane,
                "cat":          cat,
                "question":     question,
                "result":       result[:500],
                "first_time":   True,
                "cost_applied": False,
                "bound":        False,
                "source":       "daemon_query",
            })
            _poe_save_log(log)
            _log_activity("poedex query", f"{cat}: {question}", "action")

            # Update the visible result box if Observer mode is active
            rbox = _obs_refs.get("result_box")
            if rbox:
                _write(rbox,
                       (f"◈ {question}\n", "head"),
                       (f"  lane:{lane}  type:{cat}  source:aurora\n\n", "dim"),
                       (result, "val"))

            # Refresh shelf + log in Observer mode
            _refresh_obs_shelf()
            _refresh_obs_log()

        except Exception:
            pass
        root.after(300, _poe_process_queue)

    root.after(300, _poe_process_queue)

    # ── Shared input widgets (must exist before _build_observer uses them) ─────
    _poe_obs_lane = tk.StringVar(value="self")
    _poe_obs_cat  = tk.StringVar(value="define")
    obs_inq_input = tk.Entry(mode_content_frame, bg=BG_LOG, fg=TEXT,
                             font=("Courier New", 9), relief=tk.FLAT,
                             insertbackground=ACCENT, width=80)
    # Note: obs_inq_input will be properly re-created inside _build_observer().
    # The above is a placeholder so tutorial demo_btn can reference it before
    # _build_observer() is called. It will be overwritten on first mode build.

    # ── Boot into Observer mode ────────────────────────────────────────────────
    root.after(50, lambda: _poe_set_mode("observer"))

    # ── Polling and ticks ──────────────────────────────────────────────────────
    root.after(800,    _poe_poll_external)
    root.after(30_000, _tick_obs_shelf)

    # ── title bar clock ───────────────────────────────────────────────────────
    def _tick_clock():
        _time_lbl.configure(text=time.strftime("%H:%M:%S"))
        root.after(1000, _tick_clock)

    root.after(100, _tick_clock)

    # ── daemon status lbl ─────────────────────────────────────────────────────
    def _tick_status():
        d = _read_daemon()
        if d:
            mode = d.get("runtime_governor_mode","?")
            heat = d.get("heat","?")
            lbl  = labels()
            mode_str = lbl.get("gov_mode",{}).get(mode, mode)
            heat_str = lbl.get("heat",{}).get(heat, heat.lower())
            room_mode = "surface room" if _room_surface_mode() else "subsurface room"
            _status_lbl.configure(
                text=f"{mode_str}  ·  {heat_str}  ·  {room_mode}",
                fg=ACCENT if mode in ("open","balanced") else WARN)
        root.after(5000, _tick_status)

    root.after(500, _tick_status)

    # ── Activity log strip — always visible at bottom ─────────────────────────
    # Packed AFTER the notebook so it sits below all tabs permanently.
    tk.Frame(root, bg=CHART_GRID, height=1).pack(fill=tk.X, side=tk.BOTTOM)

    activity_bar = tk.Frame(root, bg=BG_LOG, pady=3, padx=10)
    activity_bar.pack(fill=tk.X, side=tk.BOTTOM)

    tk.Label(activity_bar, text="ACTIVITY", bg=BG_LOG, fg=TEXT_DIM,
             font=("Courier New", 7, "bold"), width=8, anchor="w").pack(side=tk.LEFT)

    activity_strip = tk.Text(
        activity_bar, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        height=4, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    activity_strip.pack(fill=tk.X, expand=True, side=tk.LEFT)
    activity_strip.tag_configure("ts",       foreground=TEXT_DIM)
    activity_strip.tag_configure("action",   foreground=ACCENT2)
    activity_strip.tag_configure("note",     foreground=ACCENT3)
    activity_strip.tag_configure("message",  foreground=WARN)
    activity_strip.tag_configure("decision", foreground=ACCENT)
    activity_strip.tag_configure("experiment", foreground="#a78bfa")
    activity_strip.tag_configure("training",   foreground="#38bdf8")
    activity_strip.tag_configure("detail",   foreground=TEXT_DIM)

    _activity_seen: list = [0]   # track last count to avoid full rewrite

    def _refresh_activity_strip():
        if not _ACTIVITY_LOG.exists():
            root.after(3000, _refresh_activity_strip)
            return
        try:
            entries: List[Dict] = json.loads(_ACTIVITY_LOG.read_text())
            if not isinstance(entries, list):
                root.after(3000, _refresh_activity_strip)
                return
            if len(entries) == _activity_seen[0]:
                root.after(3000, _refresh_activity_strip)
                return
            _activity_seen[0] = len(entries)
            activity_strip.configure(state=tk.NORMAL)
            activity_strip.delete("1.0", tk.END)
            for e in reversed(entries[-20:]):
                ts_s   = e.get("ts_str","?")
                action = e.get("action","?")
                detail = e.get("detail","")
                cat    = e.get("category","action")
                detail_s = f"  {detail}" if detail else ""
                activity_strip.insert(tk.END, f"  {ts_s}  ", "ts")
                activity_strip.insert(tk.END, action, cat)
                activity_strip.insert(tk.END, f"{detail_s}\n", "detail")
            activity_strip.see("1.0")
            activity_strip.configure(state=tk.DISABLED)
        except Exception:
            pass
        root.after(3000, _refresh_activity_strip)

    root.after(600, _refresh_activity_strip)

    root.mainloop()


if __name__ == "__main__":
    build_room()
