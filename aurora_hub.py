#!/usr/bin/env python3
"""
aurora_hub.py -- Aurora's visual dashboard (tabbed layout).

Tabs:
  1. Overview  -- radar charts, vitals, mid-row panels, daemon log.
  2. QAO Observer -- full QuasiArch Observer dashboard.
  3. Vision    -- live screen feed / vision index dashboard.
  4. Audio    -- sensory crystal audio facets / microphone graph.

Reads only from aurora_state/ JSON files -- no Aurora stack import needed.
Auto-refreshes every 5 s (Overview), 3 s (QAO), 2 s (Vision).

Launch:
    python3 aurora_hub.py
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import itertools
import threading
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from aurora_internal.dual_strata.sensory_control_channel import (
    camera_enabled as sensory_camera_enabled,
    set_camera_enabled,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR   = Path(__file__).parent
_STATE_DIR  = _BASE_DIR / "aurora_state"

_ROOM_MSGS          = _STATE_DIR / "aurora_room_messages.json"
_ROOM_NOTES         = _STATE_DIR / "aurora_room_notes.json"
_ROOM_ACTIVITY      = _STATE_DIR / "aurora_room_activity.json"
_RESPONSE_COACHING  = _STATE_DIR / "aurora_response_coaching.json"
_LABELS_FILE        = _STATE_DIR / "aurora_labels.json"
_MASTER_PRESENCE    = _STATE_DIR / "master_hub_presence.json"
_TRAINING_SESSION   = _STATE_DIR / "training_session.json"
_TEMPLATE_EVOL      = _STATE_DIR / "template_evolution.json"
_DUAL_STRATA_SNAPSHOT = _STATE_DIR / "dual_strata_snapshot.json"
_SUBSURFACE_PROJECTION = _STATE_DIR / "subsurface_projection.json"
_SURFACE_QUEUE      = _STATE_DIR / "surface_turn_queue.json"
_SURFACE_RESULT     = _STATE_DIR / "surface_turn_result.json"
_SURFACE_STATUS     = _STATE_DIR / "surface_daemon_status.json"

REFRESH_MS        = 5000   # Overview refresh
REFRESH_QAO_MS    = 3000   # QAO tab refresh
REFRESH_VISION_MS = 2000   # Vision tab refresh
REFRESH_AUDIO_MS  = 2000   # Audio tab refresh

# ---------------------------------------------------------------------------
# Colour palette (dark theme)
# ---------------------------------------------------------------------------
BG          = "#0d0d1a"
BG_PANEL    = "#13132b"
BG_LOG      = "#0a0a14"
ACCENT      = "#8b5cf6"       # purple
ACCENT2     = "#06b6d4"       # cyan
TEXT        = "#e2e8f0"
TEXT_DIM    = "#64748b"
HEAT_COLORS = {
    "NORMAL":   "#22c55e",
    "ELEVATED": "#f59e0b",
    "HIGH":     "#f97316",
    "CRITICAL": "#ef4444",
}
CHART_FG    = "#c4b5fd"
CHART_GRID  = "#1e1b4b"
RADAR_FILL  = "#7c3aed"
RADAR_LINE  = "#a78bfa"

# ---------------------------------------------------------------------------
# Dimension -> Core Axis mapping
# ---------------------------------------------------------------------------
AXIS_DIMS: Dict[str, List[str]] = {
    "Intelligence":   [
        "coherence_maintenance",
        "semantic_precision",
        "adaptive_strategy_selection",
        "compression_elaboration_fit",
    ],
    "Communication":  [
        "context_carryover",
        "multi_turn_stability",
        "misunderstanding_repair",
        "boundary_calibration",
    ],
    "Coherence":      [
        "coherence_maintenance",
        "contradiction_handling",
        "multi_turn_stability",
        "framing_selection",
    ],
    "Meaning":        [
        "semantic_precision",
        "implied_intent_inference",
        "compression_elaboration_fit",
        "perspective_integration",
    ],
    "Understanding":  [
        "perspective_integration",
        "ambiguity_handling",
        "implied_intent_inference",
        "misunderstanding_repair",
    ],
}

TRAIT_LABELS = [
    "curiosity", "caution", "emotional_expressiveness",
    "verbosity", "introspection", "pattern_sensitivity",
    "social_engagement", "energy_conservation",
]
TRAIT_SHORT = [
    "Curiosity", "Caution", "Emotional", "Verbosity",
    "Introspection", "Pattern", "Social", "Energy",
]

# ---------------------------------------------------------------------------
# QAO axis mapping + colours
# ---------------------------------------------------------------------------
QAO_AXIS_MAP: Dict[str, str] = {
    "factual_grounding_gap":              "X",
    "grounding_lookup_instability":       "X",
    "comprehension_gap_vocabulary":       "X",
    "comprehension_gap_structural":       "X",
    "comprehension_gap_slang":            "X",
    "response_grounding_gap":             "X",
    "comprehension_gap_ellipsis":         "N",
    "compression_elaboration_fit":        "N",
    "articulation_meaning_drift":         "N",
    "context_carryover_instability":      "T",
    "question_followup_stability":        "T",
    "meaning_tension":                    "T",
    "meaning_momentum":                   "T",
    "meaning_persistence":                "T",
    "perspective_integration":            "B",
    "meaning_complexity":                 "B",
    "response_pressure_instability":      "B",
    "coherence_maintenance":              "A",
    "uncertainty_signaling_gap":          "A",
    "understanding_contract_self_audit":  "A",
    "contradiction_resolution":           "A",
    "unspecific_echo_response":           "A",
}

AXIS_COLORS: Dict[str, str] = {
    "X": "#facc15",
    "T": "#06b6d4",
    "N": "#f97316",
    "B": "#a78bfa",
    "A": "#f87171",
}

REFRESH_EVO_MS = 6000  # Evolution tab refresh


def _augment_import_paths() -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path.home() / ".local" / "lib" / f"python{version}" / "site-packages",
        Path("/usr/local/lib") / f"python{version}" / "dist-packages",
        Path("/usr/lib/python3/dist-packages"),
    ]
    for candidate in candidates:
        try:
            resolved = str(candidate.resolve())
        except Exception:
            resolved = str(candidate)
        if candidate.is_dir() and resolved not in sys.path:
            sys.path.append(resolved)


def _auto_install(package: str, import_name: str = "") -> bool:
    """Try to pip-install a package if it's missing. Returns True on success."""
    import_name = import_name or package
    try:
        __import__(import_name)
        return True
    except ImportError:
        pass
    print(f"[Hub] Auto-installing {package} ...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", package],
        capture_output=True,
    )
    if result.returncode == 0:
        print(f"[Hub] {package} installed OK.")
        return True
    print(f"[Hub] Failed to install {package}: {result.stderr.decode()[:200]}")
    return False


def _ensure_matplotlib_available() -> None:
    try:
        import matplotlib  # noqa: F401
        return
    except Exception:
        _augment_import_paths()
    try:
        import matplotlib  # noqa: F401
        return
    except Exception:
        pass
    if _auto_install("matplotlib"):
        try:
            import matplotlib  # noqa: F401
            return
        except Exception:
            pass
    print("[Hub] Could not load matplotlib. Run: pip install matplotlib numpy")
    sys.exit(1)


def _ensure_numpy_available() -> None:
    try:
        import numpy  # noqa: F401
        return
    except Exception:
        pass
    if _auto_install("numpy"):
        try:
            import numpy  # noqa: F401
            return
        except Exception:
            pass
    print("[Hub] Could not load numpy. Run: pip install numpy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# StateReader -- reads JSON state files
# ---------------------------------------------------------------------------

class StateReader:

    def read_all(self) -> Dict[str, Any]:
        return {
            "fail_points":          self._read("fail_points.json"),
            "aurora_state":         self._read("aurora_state.json"),
            "daemon_status":        self._read("daemon_status.json"),
            "surface_status":       self._read_path(_SURFACE_STATUS),
            "surface_snapshot":     self._read("surface_sensory_snapshot.json"),
            "subsurface_projection": self._read_path(_SUBSURFACE_PROJECTION),
            "subsurface_status":    self._read("subsurface_daemon_status.json"),
            "lexicon_size":         self._lex_size(),
            "log_lines":            self._read_log(60),
            "surface_log_lines":    self._read_surface_log(40),
            "messages_unread":      self._unread_messages(),
            "qao_runtime":          self._read_path(_STATE_DIR / "quasiarch_observer" / "runtime_state.json"),
            "corpus_progress":      self._read("corpus_progress.json"),
            "stall_events":         self._read("stall_events.json"),
            "exploration_log":      self._read("exploration_log.json"),
            "language_state":       self._read("language_state.json"),
            "responder_snaps":      self._responder_trend(),
            "fail_trends":          self._fail_trends(self._read("fail_points.json")),
            # New additions
            "qao_journal_recent":   self._read_qao_journal_issues(30),
            "qao_node_count":       self._count_dir(_STATE_DIR / "quasiarch_observer" / "nodes"),
            "qao_edge_count":       self._count_dir(_STATE_DIR / "quasiarch_observer" / "edges"),
            "screen_frames":        self._screen_frames(),
            # Live corpus-runner training status (updated every ~100 messages)
            "corpus_runner_status": self._read("corpus_runner_status.json"),
            "distillation_metrics": self._read("distillation_metrics.json"),
            "interaction_status": self._read("interaction_status.json"),
        }

    def _read(self, name: str) -> Dict[str, Any]:
        p = _STATE_DIR / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return {}

    def _read_path(self, p: Path) -> Dict[str, Any]:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return {}

    def _responder_trend(self) -> List[float]:
        snap_dir = _STATE_DIR / "responder_snapshots"
        if not snap_dir.exists():
            return []
        try:
            files = sorted(snap_dir.glob("*.json"))[-6:]
            avgs = []
            for f in files:
                d = json.loads(f.read_text())
                scores = d.get("scores", d.get("sample_scores", []))
                if scores:
                    avgs.append(round(sum(scores) / len(scores), 4))
            return avgs
        except Exception:
            return []

    def _fail_trends(self, fp: Dict) -> Dict[str, str]:
        records = fp.get("records", {})
        trends: Dict[str, str] = {}
        for dim, rec in records.items():
            recent = rec.get("recent", [])
            if len(recent) >= 6:
                earlier = sum(recent[:3]) / 3
                latest  = sum(recent[-3:]) / 3
                if latest < earlier * 0.88:
                    trends[dim] = "↑"
                elif latest > earlier * 1.12:
                    trends[dim] = "↓"
                else:
                    trends[dim] = "→"
            else:
                trends[dim] = "?"
        return trends

    def _lex_size(self) -> int:
        p = _STATE_DIR / "lexicon.json"
        if p.exists():
            try:
                d = json.loads(p.read_text())
                return len(d.get("entries", {}))
            except Exception:
                pass
        return 0

    def _read_log(self, n: int) -> List[str]:
        p = _STATE_DIR / "daemon.log"
        if not p.exists():
            return ["daemon not running"]
        try:
            lines = p.read_text().splitlines()
            return lines[-n:] if len(lines) > n else lines
        except Exception:
            return []

    def _read_surface_log(self, n: int) -> List[str]:
        p = _STATE_DIR / "surface_daemon.log"
        if not p.exists():
            return []
        try:
            lines = p.read_text().splitlines()
            return lines[-n:] if len(lines) > n else lines
        except Exception:
            return []

    def _unread_messages(self) -> int:
        p = _STATE_DIR / "aurora_to_user.json"
        if not p.exists():
            return 0
        try:
            msgs = json.loads(p.read_text())
            return sum(1 for m in msgs if not m.get("read"))
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # New state-reader methods
    # ------------------------------------------------------------------

    def _read_qao_journal_issues(self, n: int) -> List[str]:
        """
        Read last N issue-flagging lines from journal.jsonl without loading
        the full 3.3M-line file.  Uses seek-from-end strategy.
        """
        journal = _STATE_DIR / "quasiarch_observer" / "journal.jsonl"
        if not journal.exists():
            return []
        results: List[str] = []
        try:
            file_size = journal.stat().st_size
            if file_size == 0:
                return []
            # Read last 256 KB -- enough for 30+ entries even with large payloads
            chunk_size = min(262144, file_size)
            with open(journal, "rb") as fh:
                fh.seek(max(0, file_size - chunk_size))
                tail = fh.read().decode("utf-8", errors="replace")
            lines = tail.splitlines()
            # Keep only lines that mention issues (non-empty list)
            for line in reversed(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                # Filter: must contain "issues=[" and must NOT be empty-list "issues=[]"
                if '"issues": [' in stripped or "'issues': [" in stripped:
                    try:
                        obj = json.loads(stripped)
                        issues_val = obj.get("issues", [])
                        if isinstance(issues_val, list) and len(issues_val) > 0:
                            results.append(stripped)
                    except Exception:
                        # Not valid JSON on its own -- include raw if it looks right
                        if '"issues": []' not in stripped and "'issues': []" not in stripped:
                            results.append(stripped)
                if len(results) >= n:
                    break
            results.reverse()
        except Exception:
            pass
        return results

    def _count_dir(self, p: Path) -> int:
        """Fast directory entry count (capped at 50001)."""
        if not p.exists():
            return 0
        try:
            count = sum(1 for _ in itertools.islice(os.scandir(p), 50001))
            return count
        except Exception:
            return 0

    def _screen_frames(self) -> List[Dict[str, Any]]:
        """List last 5 screen frame PNGs sorted by mtime."""
        screen_dir = _STATE_DIR / "vision_seeds" / "screen"
        if not screen_dir.exists():
            return []
        try:
            entries = [
                e for e in os.scandir(screen_dir)
                if e.name.endswith(".png") and e.is_file()
            ]
            entries.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            result = []
            for e in entries[:5]:
                st = e.stat()
                result.append({
                    "path":  e.path,
                    "mtime": st.st_mtime,
                    "size":  st.st_size,
                })
            return result
        except Exception:
            return []

    def read_training(self) -> Dict[str, Any]:
        """Read live training session state."""
        return {
            "session":              self._read("training_session.json"),
            "fail_points":          self._read("fail_points.json"),
            "corpus_runner_status": self._read("corpus_runner_status.json"),
            "distillation_metrics": self._read("distillation_metrics.json"),
            "interaction_status": self._read("interaction_status.json"),
        }

    def read_evolution(self) -> Dict[str, Any]:
        """Read all evolution-layer state files."""
        return {
            "adapter_hints":        self._read("adapter_hints.json"),
            "compound_axes":        self._read("compound_axes.json"),
            "query_bias":           self._read("query_bias.json"),
            "assimilated_ids":      self._read_assimilated_count(),
            "pool_size":            self._read_pool_size(),
            "evolved_count":        self._read_evolved_count(),
            "fail_points":          self._read("fail_points.json"),
            # Live constraint genealogy stats from corpus training
            "corpus_runner_status": self._read("corpus_runner_status.json"),
            "distillation_metrics": self._read("distillation_metrics.json"),
            # Daemon-mode genealogy fallback (written every turn when daemon is active)
            "daemon_status":        self._read("daemon_status.json"),
            "relief_plan":          self._read("evolution_relief_plan.json"),
            "pressure_log":         self.read_pressure_log(500),
            "layer_pressure":       self.read_all_layer_pressure(),
        }

    def read_all_layer_pressure(self) -> Dict[str, Any]:
        """Read pressure data from every layer and return a unified dict."""
        import re as _re_p
        # Axis depth scale constants (from aurora_noncomp_registry.py)
        # X=surface/cheapest → A=deep/most-expensive
        _AXIS_BUDGET    = {"X": 1.0,  "T": 5.0,  "N": 6.0,  "B": 18.0,  "A": 50.0}
        _AXIS_SHIFT_COST= {"X": 1.0,  "T": 7.0,  "N": 10.0, "B": 40.0,  "A": 150.0}
        _AXIS_FLIP_THR  = {"X": 0.35, "T": 0.42, "N": 0.50, "B": 0.65,  "A": 0.82}
        _OVERHEAD_SUM   = _AXIS_BUDGET["X"] + _AXIS_BUDGET["T"]   # 6.0
        _LEVERAGE_SUM   = _AXIS_BUDGET["B"] + _AXIS_BUDGET["A"]   # 68.0
        _BAND_LOW       = -(_OVERHEAD_SUM  * 0.30)                 # ≈ -1.8
        _BAND_HIGH      =  (_LEVERAGE_SUM  * 0.05)                 # ≈ +3.4

        result: Dict[str, Any] = {
            "L4_genealogy":  {"total": 0, "axis": {}, "gate": {}, "avg_tension": 0.0, "recent": []},
            "L4_turn_chain": {"total": 0, "avg_tension": 0.0, "recent": []},
            "L5_template":   {"pool_size": 0, "generation": 0},
            "L6_behavioral": {"governance": {}, "crystal_pressure": {}},
            "L7_surface":    {"axis_cooc": {}, "recent": []},
            "L7_625map":     {"occupied": 0, "total": 625, "highway": 0, "axis_weight": {}},
            "leverage": {
                "axis_budget":   _AXIS_BUDGET,
                "axis_shift":    _AXIS_SHIFT_COST,
                "axis_flip":     _AXIS_FLIP_THR,
                "band_low":      _BAND_LOW,
                "band_high":     _BAND_HIGH,
                "overhead_sum":  _OVERHEAD_SUM,
                "leverage_sum":  _LEVERAGE_SUM,
                # computed after experiences are parsed:
                "overhead_score": 0.0,
                "leverage_score": 0.0,
                "net":            0.0,
                "band_position":  "unknown",
                "axis_normalized": {},
            },
        }
        # ── L4/cross-layer: pressure_experiences.jsonl (tail 300) ────────────
        try:
            entries = self.read_pressure_log(300, fname="pressure_experiences.jsonl")
            for e in entries:
                src = e.get("source", "")
                cons = e.get("consequence", {})
                tension = abs(float(cons.get("tension", cons.get("net", 0)) or 0))
                pursuing = e.get("pursuing", "")
                causal = e.get("causal_action", "")
                outcome = e.get("outcome", {})
                tone = outcome.get("tone", "")
                ts = e.get("timestamp", 0)
                ts_s = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "--"
                gate_m = _re_p.search(r"Gate(\d+)", causal)

                if src == "genealogy":
                    d = result["L4_genealogy"]
                    d["total"] += 1
                    # axis
                    for ax in ("X", "T", "N", "B", "A"):
                        if f"_{ax}_axis" in pursuing or f"promote_{ax}" in pursuing:
                            d["axis"][ax] = d["axis"].get(ax, 0) + 1
                    # gate
                    if gate_m:
                        gk = f"G{gate_m.group(1)}"
                        d["gate"][gk] = d["gate"].get(gk, 0) + 1
                    d["avg_tension"] = (d["avg_tension"] * (d["total"] - 1) + tension) / d["total"]
                    if len(d["recent"]) < 12:
                        short_causal = causal[:45]
                        d["recent"].append(f"[{ts_s}] {tone:<10} T={tension:.4f}  {short_causal}")

                elif src == "turn_chain":
                    d = result["L4_turn_chain"]
                    d["total"] += 1
                    d["avg_tension"] = (d["avg_tension"] * (d["total"] - 1) + tension) / d["total"]
                    if len(d["recent"]) < 6:
                        d["recent"].append(f"[{ts_s}] {tone:<10} {e.get('meaning','')[:40]}")

                elif src == "dream_trainer":
                    # merge into a general "dream" bucket under L4
                    if "dream_trainer" not in result:
                        result["L4_dream"] = {"total": 0, "avg_tension": 0.0, "recent": []}
                    d = result["L4_dream"]
                    d["total"] += 1
                    d["avg_tension"] = (d["avg_tension"] * (d["total"] - 1) + tension) / d["total"]
                    if len(d["recent"]) < 4:
                        d["recent"].append(f"[{ts_s}] {tone}  T={tension:.4f}")
        except Exception:
            pass

        # ── Leverage scalar computation ───────────────────────────────────────
        try:
            ax = result["L4_genealogy"]["axis"]
            lv = result["leverage"]
            # Cost-weighted axis pressure: raw_count × budget (deeper axes cost more → need more relief)
            overhead_score = (ax.get("X", 0) * lv["axis_budget"]["X"] +
                              ax.get("T", 0) * lv["axis_budget"]["T"])
            leverage_score = (ax.get("B", 0) * lv["axis_budget"]["B"] +
                              ax.get("A", 0) * lv["axis_budget"]["A"])
            net = leverage_score - overhead_score
            if net < lv["band_low"]:
                band_pos = "LOW"    # overhead dominant — surface pressure rising
            elif net > lv["band_high"]:
                band_pos = "HIGH"   # leverage dominant — structural rigidity increasing
            else:
                band_pos = "INSIDE"
            lv["overhead_score"] = overhead_score
            lv["leverage_score"] = leverage_score
            lv["net"]            = net
            lv["band_position"]  = band_pos
            # Normalized pressure per axis: raw_count / budget (how hard each layer is working relative to its cost)
            max_norm = max(
                (ax.get(a, 0) / lv["axis_budget"][a] for a in ("X","T","N","B","A")),
                default=1.0
            ) or 1.0
            lv["axis_normalized"] = {
                a: (ax.get(a, 0) / lv["axis_budget"][a]) / max_norm
                for a in ("X", "T", "N", "B", "A")
            }
        except Exception:
            pass

        # ── L5: template_evolution.json ───────────────────────────────────────
        try:
            te = self._read("template_evolution.json")
            if isinstance(te, dict):
                pool = te.get("pool", {})
                result["L5_template"]["pool_size"] = len(pool)
                result["L5_template"]["generation"] = te.get("generation", 0)
        except Exception:
            pass

        # ── L6: aurora_state.json governance + crystal_genomes ────────────────
        try:
            st = self._read("aurora_state.json")
            if isinstance(st, dict):
                result["L6_behavioral"]["governance"] = st.get("governance_stats", {})
                cg = st.get("crystal_genomes", {})
                # flatten crystal scores into pressure proxy (1 - score = gap)
                flat = {}
                for genome, dims in cg.items():
                    if isinstance(dims, dict):
                        for dim, val in dims.items():
                            gap = round(1.0 - float(val), 4)
                            if gap > 0.3:
                                flat[f"{genome}.{dim}"] = gap
                result["L6_behavioral"]["crystal_pressure"] = flat
        except Exception:
            pass

        # ── L7: evo_625_pressure_map.json ─────────────────────────────────────
        try:
            p625 = _STATE_DIR / "evo_625_pressure_map.json"
            if p625.exists() and p625.stat().st_size < 5_000_000:
                pm = json.loads(p625.read_text())
                slots = pm.get("slots", {})
                occupied = sum(1 for s in slots.values()
                               if s.get("profile", {}).get("is_occupied"))
                highway_cnt = pm.get("highway_slot_count", 0)
                axis_w: Dict[str, float] = {}
                for slot_key, slot_data in slots.items():
                    w = slot_data.get("profile", {}).get("total_weight", 0)
                    for part in slot_key.split("×"):
                        if ":" in part and ">" in part:
                            src_ax = part.split(":")[1].split(">")[0]
                            axis_w[src_ax] = axis_w.get(src_ax, 0.0) + w
                result["L7_625map"].update({
                    "occupied": occupied,
                    "highway":  highway_cnt,
                    "axis_weight": axis_w,
                })
        except Exception:
            pass

        # ── L7: surface_pressure_log.jsonl (last 100) ────────────────────────
        try:
            surface_entries = self.read_pressure_log(100)
            cooc: Dict[str, int] = {}
            for e in surface_entries:
                axes = e.get("expected_axes", [])
                ts = e.get("timestamp", 0)
                sc = float(e.get("surface_score", 0))
                gp = float(e.get("genealogy_pressure", 0))
                ts_s = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "--"
                ax_s = "+".join(axes) if axes else "?"
                if len(result["L7_surface"]["recent"]) < 15:
                    result["L7_surface"]["recent"].append(
                        {"ts": ts_s, "axes": axes, "score": sc, "gp": gp})
                from itertools import combinations as _comb
                if len(axes) >= 2:
                    for a1, a2 in _comb(sorted(set(axes)), 2):
                        key = f"{a1}{a2}"
                        cooc[key] = cooc.get(key, 0) + 1
            result["L7_surface"]["axis_cooc"] = cooc
        except Exception:
            pass

        return result

    def read_pressure_log(self, n: int = 500, fname: str = "surface_pressure_log.jsonl") -> List[Dict]:
        """Tail last N entries from a .jsonl pressure log using seek-from-end."""
        p = _STATE_DIR / fname
        if not p.exists():
            return []
        try:
            chunk = 65536
            entries: List[Dict] = []
            with open(p, "rb") as f:
                f.seek(0, 2)
                fsize = f.tell()
                pos = fsize
                buf = b""
                while len(entries) < n and pos > 0:
                    read_size = min(chunk, pos)
                    pos -= read_size
                    f.seek(pos)
                    buf = f.read(read_size) + buf
                    lines = buf.split(b"\n")
                    # Keep all but the first (may be partial)
                    buf = lines[0]
                    for line in reversed(lines[1:]):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            pass
                        if len(entries) >= n:
                            break
            return list(reversed(entries[:n]))
        except Exception:
            return []

    def _read_assimilated_count(self) -> int:
        p = _STATE_DIR / "assimilated_ids.json"
        if not p.exists():
            return 0
        try:
            data = json.loads(p.read_text())
            return len(data) if isinstance(data, list) else 0
        except Exception:
            return 0

    def _read_pool_size(self) -> int:
        p = _STATE_DIR / "operation_descriptors.json"
        if not p.exists():
            return 0
        try:
            # Count without loading entire 8.7 MB file — scan for top-level array entries
            size = p.stat().st_size
            if size > 30_000_000:
                return -1   # too large, skip
            data = json.loads(p.read_text())
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                return len(data.get("operations", data.get("ops", [])))
            return 0
        except Exception:
            return 0

    def _read_evolved_count(self) -> Dict[str, int]:
        """Return gen1, gen2, and frontier counts.

        Gen-1: evolved surfaces in _SURFACE_REGISTRY (aurora_evolved_surfaces.py)
        Gen-2: descriptor pool entries tagged _generation==2 (SecondGenInjector output)
        Frontier: descriptor pool entries tagged _frontier==True (4-class frontier ops)
        """
        p = _STATE_DIR / "operation_descriptors.json"
        gen1 = 0
        gen2 = 0
        frontier = 0

        # Gen-1: count from _SURFACE_REGISTRY — force reload so mutations are reflected
        try:
            import importlib, sys as _sys
            _repo = str(p.parent.parent)
            if _repo not in _sys.path:
                _sys.path.insert(0, _repo)
            _mod_name = "aurora_internal.aurora_evolved_surfaces"
            if _mod_name in _sys.modules:
                aes = importlib.reload(_sys.modules[_mod_name])
            else:
                aes = importlib.import_module(_mod_name)
            reg = getattr(aes, "_SURFACE_REGISTRY", {})
            gen1 = len(reg) if isinstance(reg, dict) else 0
        except Exception:
            gen1 = 0

        if not p.exists():
            return {"gen1": gen1, "gen2": 0, "frontier": 0}
        try:
            size = p.stat().st_size
            if size > 30_000_000:
                return {"gen1": gen1, "gen2": 0, "frontier": 0}
            data = json.loads(p.read_text())
            ops = data if isinstance(data, list) else data.get("operations", [])
            # Gen-2: SecondGenInjector tags with _generation=2
            gen2 = sum(1 for o in ops if isinstance(o, dict)
                       and o.get("_generation") == 2)
            # Frontier: aurora_frontier_ops.py tags with _frontier=True
            frontier = sum(1 for o in ops if isinstance(o, dict)
                           and o.get("_frontier"))
            return {"gen1": gen1, "gen2": gen2, "frontier": frontier}
        except Exception:
            return {"gen1": gen1, "gen2": 0, "frontier": 0}

    def read_lineage(self) -> Dict[str, Any]:
        """Read constraint genealogy state for the Lineage tab."""
        gen_dir = _STATE_DIR / "genealogy"
        links: Dict = {}
        abilities: Dict = {}
        tick_state: Dict = {}
        events: List[Dict] = []

        try:
            p = gen_dir / "links.json"
            if p.exists():
                links = json.loads(p.read_text())
        except Exception:
            pass
        try:
            p = gen_dir / "abilities.json"
            if p.exists():
                abilities = json.loads(p.read_text())
        except Exception:
            pass
        try:
            p = gen_dir / "tick_state.json"
            if p.exists():
                tick_state = json.loads(p.read_text())
        except Exception:
            pass
        try:
            p = gen_dir / "events.jsonl"
            if p.exists():
                file_size = p.stat().st_size
                chunk = min(65536, file_size)
                with open(p, "rb") as fh:
                    fh.seek(max(0, file_size - chunk))
                    tail = fh.read().decode("utf-8", errors="replace")
                for line in reversed(tail.splitlines()):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        events.append(obj)
                        if len(events) >= 20:
                            break
                    except Exception:
                        pass
                events.reverse()
        except Exception:
            pass

        # Depth distribution
        from collections import Counter as _Counter
        depth_dist = dict(sorted(_Counter(
            v.get("depth", 0) for v in links.values()
        ).items())) if links else {}

        # Ability axis distribution
        ax_dist = dict(sorted(_Counter(
            v.get("axis", "?") for v in abilities.values()
        ).items())) if abilities else {}
        # Filter to known axes only
        ax_dist = {k: v for k, v in ax_dist.items() if k in ("X", "T", "N", "B", "A")}

        return {
            "total_links": len(links),
            "total_abilities": len(abilities),
            "tick_state": tick_state,
            "depth_dist": depth_dist,
            "ax_dist": ax_dist,
            "recent_events": events,
        }

    def read_sensory_crystal(self) -> Dict[str, Any]:
        """Read sensory crystal hub state snapshot."""
        p = _STATE_DIR / "sensory_crystal_state.json"
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text()) or {}
        except Exception:
            return {}

    def read_dce_log(self, n: int = 200) -> List[Dict]:
        """Read last N entries from dce_assembly_log.jsonl."""
        p = _STATE_DIR / "dce_assembly_log.jsonl"
        if not p.exists():
            return []
        try:
            lines = p.read_text().splitlines()
            out = []
            for ln in lines[-n:]:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
            return out
        except Exception:
            return []

    def read_sensory_telemetry(self, n: int = 200) -> List[Dict]:
        """Read last N entries from sensory_telemetry.jsonl."""
        p = _STATE_DIR / "sensory_telemetry.jsonl"
        if not p.exists():
            return []
        try:
            lines = p.read_text().splitlines()
            out = []
            for ln in lines[-n:]:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
            return out
        except Exception:
            return []

    def read_manifold(self) -> Dict[str, Any]:
        """Read manifold / identity / constraint state for the Manifold tab."""
        daemon_status = self._read("daemon_status.json")
        aurora_state = self._read("aurora_state.json")
        gen_dir = _STATE_DIR / "genealogy"

        # Abilities per axis from genealogy
        ax_abilities: Dict[str, int] = {}
        try:
            p = gen_dir / "abilities.json"
            if p.exists():
                from collections import Counter as _Counter
                data = json.loads(p.read_text())
                cnt = _Counter(v.get("axis", "?") for v in data.values())
                ax_abilities = {k: cnt[k] for k in ("X", "T", "N", "B", "A")}
        except Exception:
            pass

        # Couplings (axis transition counts)
        couplings: Dict = {}
        try:
            p = gen_dir / "couplings.json"
            if p.exists():
                couplings = json.loads(p.read_text())
        except Exception:
            pass

        return {
            "axis_orientation": daemon_status.get("axis_orientation", {}),
            "dilation_factor": daemon_status.get("dilation_factor", 1.0),
            "dilation_state": daemon_status.get("dilation_state", "normal"),
            "traits": aurora_state.get("traits", {}),
            "identity_anchors": aurora_state.get("identity_anchors", []),
            "time_dilation": aurora_state.get("time_dilation", {}),
            "stability_state": aurora_state.get("stability_state", {}),
            "generation": aurora_state.get("generation", 0),
            "simulation_epochs": aurora_state.get("simulation_epochs", 0),
            "understanding_shards": aurora_state.get("understanding_shards", 0),
            "ax_abilities": ax_abilities,
            "couplings": couplings,
            "chain_links": daemon_status.get("chain_links", 0),
            "outlet_push_fraction": daemon_status.get("outlet_push_fraction", 0.0),
        }

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------

    def axis_scores(self, fail_points: Dict) -> Dict[str, float]:
        records = fail_points.get("records", {})
        scores: Dict[str, float] = {}
        for axis, dims in AXIS_DIMS.items():
            masteries = []
            for dim in dims:
                rec = records.get(dim, {})
                recent = rec.get("recent", [])
                if recent:
                    avg_fail = sum(recent) / len(recent)
                    masteries.append(max(0.0, 1.0 - avg_fail))
                else:
                    masteries.append(0.5)  # no data = unknown, not 100%
            scores[axis] = round(sum(masteries) / len(masteries), 3)
        return scores

    def trait_scores(self, aurora_state: Dict) -> Dict[str, float]:
        traits = aurora_state.get("traits", {})
        if not isinstance(traits, dict):
            return {t: 0.0 for t in TRAIT_LABELS}
        return {t: min(1.0, max(0.0, float(traits.get(t, 0.0)))) for t in TRAIT_LABELS}

    def heat_label(self, daemon_status: Dict) -> Tuple[str, str]:
        label = daemon_status.get("heat", "NORMAL")
        color = HEAT_COLORS.get(label, HEAT_COLORS["NORMAL"])
        return label, color


# ---------------------------------------------------------------------------
# Radar chart drawing (matplotlib)
# ---------------------------------------------------------------------------

def _radar_chart(fig, ax, labels: List[str], values: List[float],
                 fill_color: str, line_color: str, title: str):
    import numpy as np
    N = len(labels)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    vals = list(values) + [values[0]]

    ax.set_facecolor(BG_PANEL)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20", "40", "60", "80", "100"],
                       color=TEXT_DIM, fontsize=6)
    ax.yaxis.grid(True, color=CHART_GRID, linewidth=0.5)
    ax.xaxis.grid(True, color=CHART_GRID, linewidth=0.5)
    ax.spines["polar"].set_color(CHART_GRID)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXT, fontsize=8, fontweight="bold")

    ax.plot(angles, vals, color=line_color, linewidth=2, linestyle="solid")
    ax.fill(angles, vals, color=fill_color, alpha=0.25)
    ax.scatter(angles[:-1], values, color=line_color, s=30, zorder=5)
    ax.set_title(title, color=TEXT, fontsize=9, pad=14, fontweight="bold")


# ---------------------------------------------------------------------------
# Main hub window
# ---------------------------------------------------------------------------

def _make_scrollable_inner(outer: "tk.Frame") -> "tk.Frame":
    """Wrap a tab's outer frame in a Canvas+Scrollbar so content can scroll.
    Returns the inner Frame — pack all tab content into it instead of outer."""
    import tkinter as tk
    from tkinter import ttk
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=BG)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_configure)

    def _on_canvas_configure(event):
        canvas.itemconfig(win_id, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def _on_enter(_e):
        def _scroll(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)
    def _on_leave(_e):
        canvas.unbind_all("<MouseWheel>")
    inner.bind("<Enter>", _on_enter)
    inner.bind("<Leave>", _on_leave)
    return inner


def _build_ui():
    import tkinter as tk
    from tkinter import scrolledtext, ttk, font as tkfont
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np

    reader = StateReader()

    # ── Root window ─────────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("Aurora Hub")
    root.configure(bg=BG)
    root.geometry("1280x900")
    root.minsize(1000, 720)

    # ── Zoom state ───────────────────────────────────────────────────────────
    # We walk the full widget tree and rescale each font tuple in-place.
    # This is the only reliable way to zoom all text in Tkinter when fonts
    # are specified as ("Family", size) tuples rather than named Font objects.
    _zoom = {"level": 1.0}   # current multiplier (1.0 = as-built size)

    def _apply_zoom(delta: float):
        import re as _re
        new_level = round(max(0.4, min(3.0, _zoom["level"] + delta)), 2)
        if new_level == _zoom["level"]:
            return
        ratio = new_level / max(_zoom["level"], 0.01)
        _zoom["level"] = new_level

        def _rescale(widget):
            try:
                f = widget.cget("font")
                if f:
                    if isinstance(f, tuple) and len(f) >= 2:
                        new_size = max(5, int(round(int(f[1]) * ratio)))
                        widget.config(font=(f[0], new_size) + f[2:])
                    elif isinstance(f, str) and f:
                        m = _re.match(r'(.*?)\s+(\d+)(.*)?$', f.strip())
                        if m:
                            new_size = max(5, int(round(int(m.group(2)) * ratio)))
                            widget.config(font=f"{m.group(1)} {new_size}{m.group(3) or ''}")
            except Exception:
                pass
            try:
                for child in widget.winfo_children():
                    _rescale(child)
            except Exception:
                pass

        _rescale(root)
        # Also rescale ttk notebook tab font via style
        try:
            import tkinter.ttk as _ttk
            st = _ttk.Style()
            cur = st.lookup("TNotebook.Tab", "font") or "Courier New 9 bold"
            m = _re.match(r'(.*?)\s+(\d+)(.*)?$', str(cur).strip())
            if m:
                new_size = max(5, int(round(int(m.group(2)) * ratio)))
                st.configure("TNotebook.Tab", font=f"{m.group(1)} {new_size}{m.group(3) or ''}")
        except Exception:
            pass

        pct = int(round(_zoom["level"] * 100))
        try:
            lbl_zoom.config(text=f"  {pct}%")
        except Exception:
            pass

    # ── Title bar (always visible above tabs) ────────────────────────────────
    title_frame = tk.Frame(root, bg=BG, pady=8, padx=16)
    title_frame.pack(fill=tk.X)

    lbl_name = tk.Label(title_frame, text="● AURORA", bg=BG,
                        fg=ACCENT, font=("Courier New", 18, "bold"))
    lbl_name.pack(side=tk.LEFT)

    lbl_gen = tk.Label(title_frame, text="gen:--", bg=BG,
                       fg=TEXT_DIM, font=("Courier New", 11))
    lbl_gen.pack(side=tk.LEFT, padx=(18, 0))

    lbl_heat = tk.Label(title_frame, text="● NORMAL", bg=BG,
                        fg=HEAT_COLORS["NORMAL"], font=("Courier New", 11, "bold"))
    lbl_heat.pack(side=tk.LEFT, padx=(14, 0))

    lbl_msgs = tk.Label(title_frame, text="", bg=BG,
                        fg=ACCENT2, font=("Courier New", 10))
    lbl_msgs.pack(side=tk.RIGHT, padx=8)

    lbl_refresh = tk.Label(title_frame, text="", bg=BG,
                           fg=TEXT_DIM, font=("Courier New", 8))
    lbl_refresh.pack(side=tk.RIGHT, padx=4)

    # Zoom controls (right side, before refresh label)
    lbl_zoom = tk.Label(title_frame, text="  100%", bg=BG,
                        fg=TEXT_DIM, font=("Courier New", 8))
    lbl_zoom.pack(side=tk.RIGHT, padx=2)

    btn_zoom_out = tk.Button(title_frame, text="−", bg=BG_PANEL, fg=TEXT,
                             font=("Courier New", 10, "bold"), bd=0, padx=6,
                             activebackground=CHART_GRID, activeforeground=ACCENT,
                             command=lambda: _apply_zoom(-0.1))
    btn_zoom_out.pack(side=tk.RIGHT)

    btn_zoom_in = tk.Button(title_frame, text="+", bg=BG_PANEL, fg=TEXT,
                            font=("Courier New", 10, "bold"), bd=0, padx=6,
                            activebackground=CHART_GRID, activeforeground=ACCENT,
                            command=lambda: _apply_zoom(+0.1))
    btn_zoom_in.pack(side=tk.RIGHT)

    btn_zoom_reset = tk.Button(title_frame, text="⊙", bg=BG_PANEL, fg=TEXT_DIM,
                               font=("Courier New", 9), bd=0, padx=4,
                               activebackground=CHART_GRID, activeforeground=ACCENT2,
                               command=lambda: _apply_zoom(1.2 - _zoom["level"]))
    btn_zoom_reset.pack(side=tk.RIGHT, padx=(0, 4))

    # Quiet mode toggle (title bar, right side)
    _quiet_mode_state = {"on": (_STATE_DIR / "quiet_mode").exists()}

    def _write_cmd(payload: dict) -> None:
        try:
            tmp = str(_STATE_DIR / "daemon_cmd.json") + ".tmp"
            with open(tmp, "w") as _f:
                json.dump(payload, _f)
            os.replace(tmp, str(_STATE_DIR / "daemon_cmd.json"))
        except Exception:
            pass

    def _read_state_file(path: Path, default: Any) -> Any:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default

    def _surface_daemon_alive(max_age: float = 20.0) -> bool:
        data = _read_state_file(_SURFACE_STATUS, {})
        ts = float(data.get("updated_at", 0.0) or 0.0) if isinstance(data, dict) else 0.0
        return bool(ts and (time.time() - ts) <= max_age)

    def _queue_surface_turn(text: str) -> str:
        state = _read_state_file(_SURFACE_QUEUE, {"pending": []})
        if not isinstance(state, dict):
            state = {"pending": []}
        turn_id = f"hub_{int(time.time() * 1000)}"
        pending = list(state.get("pending") or [])
        pending.append({
            "id": turn_id,
            "content": text,
            "source": "hub_overview",
            "session_id": "hub_overview",
            "status": "queued",
            "created_at": time.time(),
            "auto_search_enabled": True,
            "record_exchange": True,
            "track_evolutionary_trace": True,
            "run_periodic_maintenance": True,
            "mode_name": "BOUNDED",
        })
        state["pending"] = pending
        tmp = str(_SURFACE_QUEUE) + ".tmp"
        with open(tmp, "w") as _f:
            json.dump(state, _f, indent=2)
        os.replace(tmp, str(_SURFACE_QUEUE))
        return turn_id

    vis_camera_btn = None

    def _update_quiet_btn():
        on = (_STATE_DIR / "quiet_mode").exists()
        _quiet_mode_state["on"] = on
        if on:
            quiet_btn.config(text="🔇 QUIET", fg="#f97316")
        else:
            quiet_btn.config(text="🔊 VOICE", fg="#4ade80")

    def _toggle_quiet():
        on = (_STATE_DIR / "quiet_mode").exists()
        if on:
            _write_cmd({"cmd": "unquiet"})
            _QUIET_FLAG_PATH = _STATE_DIR / "quiet_mode"
            try:
                _QUIET_FLAG_PATH.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            _write_cmd({"cmd": "quiet"})
            try:
                (_STATE_DIR / "quiet_mode").touch()
            except Exception:
                pass
        root.after(300, _update_quiet_btn)

    def _update_camera_btn():
        if vis_camera_btn is None:
            return
        if sensory_camera_enabled(_STATE_DIR):
            vis_camera_btn.config(text="CAM ON", fg="#4ade80")
        else:
            vis_camera_btn.config(text="CAM OFF", fg="#f97316")

    def _toggle_camera_capture():
        next_enabled = not sensory_camera_enabled(_STATE_DIR)
        set_camera_enabled(_STATE_DIR, next_enabled, source="aurora_hub")
        root.after(150, _update_camera_btn)

    quiet_btn = tk.Button(
        title_frame,
        text="🔊 VOICE",
        command=_toggle_quiet,
        bg=BG_PANEL, fg="#4ade80",
        font=("Courier New", 9, "bold"),
        relief=tk.FLAT, padx=8, pady=2,
        activebackground=CHART_GRID, activeforeground=TEXT,
        cursor="hand2",
    )
    quiet_btn.pack(side=tk.RIGHT, padx=8)
    _update_quiet_btn()  # sync to actual state at launch

    # Keyboard zoom bindings
    root.bind_all("<Control-equal>",   lambda e: _apply_zoom(+0.1))
    root.bind_all("<Control-plus>",    lambda e: _apply_zoom(+0.1))
    root.bind_all("<Control-minus>",   lambda e: _apply_zoom(-0.1))
    root.bind_all("<Control-0>",       lambda e: _apply_zoom(1.2 - _zoom["level"]))

    tk.Frame(root, bg=CHART_GRID, height=1).pack(fill=tk.X)

    # ── Notebook (tabs) ──────────────────────────────────────────────────────
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=BG_PANEL, foreground=TEXT_DIM,
                    padding=[12, 4], font=("Courier New", 9, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", CHART_GRID)],
              foreground=[("selected", ACCENT), ("active", TEXT)])

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    # ========================================================================
    # TAB 1: OVERVIEW
    # ========================================================================
    tab_overview_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_overview_outer, text="  Overview  ")
    tab_overview = _make_scrollable_inner(tab_overview_outer)

    # ── Charts row ───────────────────────────────────────────────────────────
    charts_frame = tk.Frame(tab_overview, bg=BG)
    charts_frame.pack(fill=tk.X, padx=8, pady=8)

    fig_left, ax_left = plt.subplots(figsize=(3.8, 3.8),
                                     subplot_kw={"polar": True},
                                     facecolor=BG_PANEL)
    canvas_left = FigureCanvasTkAgg(fig_left, master=charts_frame)
    canvas_left.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
    canvas_left.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    fig_right, ax_right = plt.subplots(figsize=(3.8, 3.8),
                                       subplot_kw={"polar": True},
                                       facecolor=BG_PANEL)
    canvas_right = FigureCanvasTkAgg(fig_right, master=charts_frame)
    canvas_right.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
    canvas_right.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    # ── Vitals bar ───────────────────────────────────────────────────────────
    tk.Frame(tab_overview, bg=CHART_GRID, height=1).pack(fill=tk.X)

    vitals_frame = tk.Frame(tab_overview, bg=BG_PANEL, pady=6, padx=16)
    vitals_frame.pack(fill=tk.X)

    vital_font = ("Courier New", 10)
    vital_labels: Dict[str, tk.Label] = {}

    vitals_defs = [
        ("vocab",    "Vocab",    "--"),
        ("oets",     "OETS",     "--"),
        ("outlet",   "Outlet",   "--"),
        ("epochs",   "Epochs",   "--"),
        ("browser",  "Social",   "--"),
        ("distill",  "Distill",  "--"),
        ("evolve",   "Evolve",   "--"),
        ("persist",  "Persist",  "--"),
        ("interact", "Interact", "--"),
        ("voice",    "Voice",    "--"),
        ("lastcmd",  "Last Cmd", "--"),
    ]
    for key, display, default in vitals_defs:
        cell = tk.Frame(vitals_frame, bg=BG_PANEL, padx=14)
        cell.pack(side=tk.LEFT)
        tk.Label(cell, text=display, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        lbl = tk.Label(cell, text=default, bg=BG_PANEL,
                       fg=ACCENT2, font=vital_font)
        lbl.pack()
        vital_labels[key] = lbl

    # ── Mid row ──────────────────────────────────────────────────────────────
    tk.Frame(tab_overview, bg=CHART_GRID, height=1).pack(fill=tk.X)
    mid_frame = tk.Frame(tab_overview, bg=BG, pady=4, padx=8)
    mid_frame.pack(fill=tk.X)

    def _make_panel(parent, title, width=None):
        frame = tk.Frame(parent, bg=BG_PANEL, padx=8, pady=4,
                         relief=tk.FLAT, bd=0)
        if width:
            frame.config(width=width)
        tk.Label(frame, text=title, bg=BG_PANEL,
                 fg=ACCENT, font=("Courier New", 7, "bold")).pack(anchor=tk.W)
        sep = tk.Frame(frame, bg=CHART_GRID, height=1)
        sep.pack(fill=tk.X, pady=(1, 3))
        return frame

    # QAO mini-panel
    qao_panel = _make_panel(mid_frame, "QUASIARCH OBSERVER")
    qao_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    qao_issue_labels: Dict[str, tk.Label] = {}
    QAO_SHOW_ISSUES = [
        ("coherence_maintenance",        "Coherence"),
        ("context_carryover_instability","Context Carry"),
        ("articulation_meaning_drift",   "Meaning Drift"),
        ("factual_grounding_gap",        "Grounding"),
        ("question_followup_stability",  "Followup"),
        ("grounding_lookup_instability", "Lookup Stab"),
        ("uncertainty_signaling_gap",    "Uncertainty"),
        ("response_pressure_instability","Resp Pressure"),
    ]
    for key, label in QAO_SHOW_ISSUES:
        row = tk.Frame(qao_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{label:<16}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=16, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 7), anchor=tk.W)
        lbl.pack(side=tk.LEFT)
        qao_issue_labels[key] = lbl

    qao_conf_lbl = tk.Label(qao_panel, text="gate:--  adv:--", bg=BG_PANEL,
                            fg=TEXT_DIM, font=("Courier New", 7))
    qao_conf_lbl.pack(anchor=tk.W, pady=(3, 0))

    # 5-Axis health panel
    axis_panel = _make_panel(mid_frame, "5-AXIS HEALTH  (mastery %)")
    axis_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    AXIS_HEALTH_DIMS: Dict[str, List[str]] = {
        "X  surface":  ["uncertainty_signaling", "contradiction_handling", "semantic_precision"],
        "T  temporal": ["coherence_maintenance", "context_carryover", "multi_turn_stability"],
        "N  compress": ["compression_elaboration_fit", "semantic_precision", "implied_intent_inference"],
        "B  deep":     ["perspective_integration", "boundary_calibration", "ambiguity_handling"],
        "A  core":     ["framing_selection", "adaptive_strategy_selection", "emotional_calibration"],
    }
    axis_health_labels: Dict[str, Tuple[tk.Label, tk.Label]] = {}
    for ax_key in AXIS_HEALTH_DIMS:
        row = tk.Frame(axis_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{ax_key:<12}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=12, anchor=tk.W).pack(side=tk.LEFT)
        bar_lbl = tk.Label(row, text="----------", bg=BG_PANEL,
                           fg=ACCENT2, font=("Courier New", 7), anchor=tk.W)
        bar_lbl.pack(side=tk.LEFT)
        pct_lbl = tk.Label(row, text="--%", bg=BG_PANEL,
                           fg=TEXT, font=("Courier New", 7))
        pct_lbl.pack(side=tk.LEFT, padx=(4, 0))
        axis_health_labels[ax_key] = (bar_lbl, pct_lbl)

    # Fail trends panel
    trend_panel = _make_panel(mid_frame, "FAIL TRENDS  (up improving  down worse)")
    trend_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    TREND_DIMS = [
        "coherence_maintenance", "context_carryover", "semantic_precision",
        "compression_elaboration_fit", "perspective_integration",
        "uncertainty_signaling", "boundary_calibration", "framing_selection",
    ]
    trend_labels: Dict[str, tk.Label] = {}
    for dim in TREND_DIMS:
        short = dim.replace("_", " ")[:22]
        row = tk.Frame(trend_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{short:<24}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=24, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="?", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 8, "bold"))
        lbl.pack(side=tk.LEFT)
        trend_labels[dim] = lbl

    # Corpus panel
    corpus_panel = _make_panel(mid_frame, "CORPUS / SENSOR")
    corpus_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    corpus_info_labels: Dict[str, tk.Label] = {}
    CORPUS_ROWS = [
        ("pass",      "Pass"),
        ("msg",       "Messages"),
        ("score",     "Score trend"),
        ("stall",     "Last stall"),
        ("stall_dim", "Stuck dims"),
        ("sensor_ts", "Sensor ran"),
        ("sensor_top","Top signal"),
        ("diag_ax",   "Noisy axis"),
    ]
    for key, label in CORPUS_ROWS:
        row = tk.Frame(corpus_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{label:<14}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=14, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 7), anchor=tk.W)
        lbl.pack(side=tk.LEFT)
        corpus_info_labels[key] = lbl

    # ── Log panel ─────────────────────────────────────────────────────────────
    tk.Frame(tab_overview, bg=CHART_GRID, height=1).pack(fill=tk.X)
    log_header = tk.Frame(tab_overview, bg=BG, pady=4, padx=16)
    log_header.pack(fill=tk.X)
    tk.Label(log_header, text="DAEMON LOG", bg=BG,
             fg=TEXT_DIM, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    log_box = scrolledtext.ScrolledText(
        tab_overview, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=8,
        insertbackground=TEXT,
    )
    log_box.pack(fill=tk.X, padx=8, pady=(0, 8))

    log_box.tag_config("study",   foreground=ACCENT2)
    log_box.tag_config("dream",   foreground=ACCENT)
    log_box.tag_config("browser", foreground="#fb923c")
    log_box.tag_config("wake",    foreground="#4ade80")
    log_box.tag_config("save",    foreground=TEXT_DIM)
    log_box.tag_config("reach",   foreground="#f472b6")
    log_box.tag_config("distill", foreground="#34d399")
    log_box.tag_config("restore", foreground="#fbbf24")
    log_box.tag_config("error",   foreground="#f87171")
    log_box.tag_config("default", foreground=TEXT_DIM)

    def _tag_for_line(line: str) -> str:
        lo = line.lower()
        if "[study]"   in lo: return "study"
        if "[dream]"   in lo: return "dream"
        if "[browser]" in lo: return "browser"
        if "[wake]"    in lo: return "wake"
        if "[save]"    in lo: return "save"
        if "[reach]"   in lo: return "reach"
        if "[distill]" in lo: return "distill"
        if "[restore]" in lo: return "restore"
        if "error" in lo or "fatal" in lo: return "error"
        return "default"

    def _update_log(lines: List[str]) -> None:
        log_box.configure(state=tk.NORMAL)
        log_box.delete("1.0", tk.END)
        for line in lines:
            tag = _tag_for_line(line)
            log_box.insert(tk.END, line + "\n", tag)
        log_box.see(tk.END)
        log_box.configure(state=tk.DISABLED)

    # ── Surface daemon log panel ───────────────────────────────────────────────
    tk.Frame(tab_overview, bg=CHART_GRID, height=1).pack(fill=tk.X)
    surface_log_header = tk.Frame(tab_overview, bg=BG, pady=4, padx=16)
    surface_log_header.pack(fill=tk.X)
    tk.Label(surface_log_header, text="SURFACE LOG", bg=BG,
             fg="#38bdf8", font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    tk.Label(surface_log_header, text="  (what Aurora says & surface events)", bg=BG,
             fg=TEXT_DIM, font=("Courier New", 7)).pack(side=tk.LEFT)

    surface_log_box = scrolledtext.ScrolledText(
        tab_overview, bg=BG_LOG, fg="#38bdf8",
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6,
        insertbackground=TEXT,
    )
    surface_log_box.pack(fill=tk.X, padx=8, pady=(0, 8))

    surface_log_box.tag_config("speak",   foreground="#22c55e")
    surface_log_box.tag_config("hear",    foreground="#fb923c")
    surface_log_box.tag_config("surface", foreground="#38bdf8")
    surface_log_box.tag_config("error",   foreground="#f87171")
    surface_log_box.tag_config("default", foreground=TEXT_DIM)

    def _tag_for_surface_line(line: str) -> str:
        lo = line.lower()
        if "spoken" in lo or "speaking" in lo or "aurora says" in lo or "[speak]" in lo: return "speak"
        if "heard" in lo or "speech" in lo or "[hear]" in lo or "[input]" in lo: return "hear"
        if "error" in lo or "fatal" in lo: return "error"
        return "surface"

    def _update_surface_log(lines: list) -> None:
        surface_log_box.configure(state=tk.NORMAL)
        surface_log_box.delete("1.0", tk.END)
        if not lines:
            surface_log_box.insert(tk.END, "surface daemon not running\n", "default")
        else:
            for line in lines:
                tag = _tag_for_surface_line(line)
                surface_log_box.insert(tk.END, line + "\n", tag)
        surface_log_box.see(tk.END)
        surface_log_box.configure(state=tk.DISABLED)

    # ── Hub chat input ────────────────────────────────────────────────────────
    tk.Frame(tab_overview, bg=CHART_GRID, height=1).pack(fill=tk.X)
    chat_hdr = tk.Frame(tab_overview, bg=BG, padx=10, pady=2)
    chat_hdr.pack(fill=tk.X, padx=6)
    tk.Label(chat_hdr, text="SEND MESSAGE TO AURORA", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    chat_quiet_lbl = tk.Label(chat_hdr, text="", bg=BG,
                               fg=TEXT_DIM, font=("Courier New", 7))
    chat_quiet_lbl.pack(side=tk.RIGHT, padx=6)

    chat_input_frame = tk.Frame(tab_overview, bg=BG_PANEL, padx=8, pady=6)
    chat_input_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

    chat_entry = tk.Entry(
        chat_input_frame,
        bg=BG_LOG, fg=TEXT,
        font=("Courier New", 10),
        relief=tk.FLAT, bd=2,
        insertbackground=TEXT,
    )
    chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

    _pending_chat = {"mode": "", "id": ""}

    def _send_chat(event=None):
        text = chat_entry.get().strip()
        if not text:
            return
        if _surface_daemon_alive():
            try:
                _pending_chat["mode"] = "surface"
                _pending_chat["id"] = _queue_surface_turn(text)
                chat_quiet_lbl.config(text="[surface daemon]", fg=ACCENT2)
            except Exception:
                _pending_chat["mode"] = "daemon"
                _pending_chat["id"] = ""
                _write_cmd({"cmd": "chat", "text": text})
        else:
            _pending_chat["mode"] = "daemon"
            _pending_chat["id"] = ""
            _write_cmd({"cmd": "chat", "text": text})
        chat_entry.delete(0, tk.END)
        chat_response_box.configure(state=tk.NORMAL)
        chat_response_box.insert(tk.END, f"You: {text}\n", "you")
        chat_response_box.see(tk.END)
        chat_response_box.configure(state=tk.DISABLED)
        # Poll for response
        root.after(800, _poll_chat_response)

    chat_entry.bind("<Return>", _send_chat)

    send_btn = tk.Button(
        chat_input_frame,
        text="Send",
        command=_send_chat,
        bg=ACCENT, fg=TEXT,
        font=("Courier New", 9, "bold"),
        relief=tk.FLAT, padx=10, pady=2,
        activebackground=RADAR_LINE,
        cursor="hand2",
    )
    send_btn.pack(side=tk.LEFT)

    # Response display
    chat_response_box = scrolledtext.ScrolledText(
        tab_overview,
        bg=BG_LOG, fg=TEXT,
        font=("Courier New", 9),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6,
        insertbackground=TEXT, wrap=tk.WORD,
    )
    chat_response_box.pack(fill=tk.BOTH, padx=6, pady=(0, 6))
    chat_response_box.tag_config("you",    foreground=ACCENT2)
    chat_response_box.tag_config("aurora", foreground="#a78bfa")
    chat_response_box.tag_config("dim",    foreground=TEXT_DIM)

    _last_response_ts = {"ts": 0.0}

    def _poll_chat_response():
        try:
            if _pending_chat.get("mode") == "surface" and _SURFACE_RESULT.exists():
                data = _read_state_file(_SURFACE_RESULT, {})
                ts = float(data.get("processed_at", 0.0) or 0.0)
                if str(data.get("id", "") or "") == str(_pending_chat.get("id", "") or "") and ts > _last_response_ts["ts"]:
                    _last_response_ts["ts"] = ts
                    if str(data.get("status", "ok") or "ok") == "error":
                        reply = str(data.get("error", "surface daemon failed") or "surface daemon failed")
                        mode_tag = " [surface error]"
                    else:
                        reply = str(data.get("response_text", "") or "")
                        mode_tag = " [surface]"
                    chat_response_box.configure(state=tk.NORMAL)
                    chat_response_box.insert(tk.END, f"Aurora{mode_tag}: {reply}\n\n", "aurora")
                    chat_response_box.see(tk.END)
                    chat_response_box.configure(state=tk.DISABLED)
                    chat_quiet_lbl.config(text="[surface daemon]", fg=ACCENT2)
                    _pending_chat["mode"] = ""
                    _pending_chat["id"] = ""
                    return

            resp_file = _STATE_DIR / "hub_response.json"
            if not resp_file.exists():
                root.after(600, _poll_chat_response)
                return
            data = json.loads(resp_file.read_text())
            ts = float(data.get("ts", 0.0))
            if ts > _last_response_ts["ts"]:
                _last_response_ts["ts"] = ts
                reply = data.get("response", "")
                quiet = data.get("quiet", False)
                mode_tag = " [text only]" if quiet else ""
                chat_response_box.configure(state=tk.NORMAL)
                chat_response_box.insert(
                    tk.END, f"Aurora{mode_tag}: {reply}\n\n", "aurora"
                )
                chat_response_box.see(tk.END)
                chat_response_box.configure(state=tk.DISABLED)
                chat_quiet_lbl.config(
                    text="[quiet mode]" if quiet else "",
                    fg="#f97316",
                )
            root.after(600, _poll_chat_response)
        except Exception:
            root.after(600, _poll_chat_response)

    def _draw_radar(fig, ax, labels, values, fill_color, line_color, title):
        ax.clear()
        _radar_chart(fig, ax, labels, values, fill_color, line_color, title)
        fig.tight_layout()

    # ========================================================================
    # TAB 2: QAO OBSERVER
    # ========================================================================
    tab_qao_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_qao_outer, text="  QAO Observer  ")
    tab_qao = _make_scrollable_inner(tab_qao_outer)

    # ── Header row: gauge gauges + counts ────────────────────────────────────
    qao_hdr = tk.Frame(tab_qao, bg=BG_PANEL, pady=6, padx=10)
    qao_hdr.pack(fill=tk.X, padx=6, pady=(6, 2))

    def _qao_gauge(parent, label, key):
        cell = tk.Frame(parent, bg=BG_PANEL, padx=12)
        cell.pack(side=tk.LEFT)
        tk.Label(cell, text=label, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        lbl = tk.Label(cell, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 14, "bold"))
        lbl.pack()
        return lbl

    qao_gate_lbl    = _qao_gauge(qao_hdr, "Gate Confidence", "gate")
    qao_adv_lbl     = _qao_gauge(qao_hdr, "Advisory Conf.", "adv")
    qao_issues_lbl  = _qao_gauge(qao_hdr, "Total Issues", "total")
    qao_journal_lbl = _qao_gauge(qao_hdr, "Journal Entries", "journal")
    qao_nodes_lbl   = _qao_gauge(qao_hdr, "QAO Nodes", "nodes")
    qao_edges_lbl   = _qao_gauge(qao_hdr, "QAO Edges", "edges")

    # ── Issue heatmap ─────────────────────────────────────────────────────────
    tk.Frame(tab_qao, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)

    heatmap_hdr = tk.Frame(tab_qao, bg=BG, padx=10, pady=2)
    heatmap_hdr.pack(fill=tk.X, padx=6)
    tk.Label(heatmap_hdr, text="ISSUE HEATMAP", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    # Axis pie label (text-based)
    axis_pie_lbl = tk.Label(heatmap_hdr, text="", bg=BG,
                            fg=TEXT_DIM, font=("Courier New", 8))
    axis_pie_lbl.pack(side=tk.RIGHT, padx=10)

    heatmap_frame = tk.Frame(tab_qao, bg=BG_PANEL, padx=8, pady=4)
    heatmap_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

    # Two-column layout for heatmap rows
    hm_left  = tk.Frame(heatmap_frame, bg=BG_PANEL)
    hm_right = tk.Frame(heatmap_frame, bg=BG_PANEL)
    hm_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
    hm_right.pack(side=tk.LEFT, fill=tk.X, expand=True)

    _QAO_ALL_ISSUES = list(QAO_AXIS_MAP.keys())
    heatmap_rows: Dict[str, Dict[str, tk.Label]] = {}

    for idx, issue_key in enumerate(_QAO_ALL_ISSUES):
        parent = hm_left if idx < len(_QAO_ALL_ISSUES) // 2 + 1 else hm_right
        axis   = QAO_AXIS_MAP.get(issue_key, "X")
        color  = AXIS_COLORS.get(axis, ACCENT2)

        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)

        short_name = issue_key.replace("_", " ")[:26]
        tk.Label(row, text=f"{short_name:<26}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=26, anchor=tk.W).pack(side=tk.LEFT)
        ax_lbl = tk.Label(row, text=axis, bg=BG_PANEL,
                          fg=color, font=("Courier New", 7, "bold"), width=2)
        ax_lbl.pack(side=tk.LEFT)

        bar_lbl = tk.Label(row, text="          ", bg=BG_PANEL,
                           fg=color, font=("Courier New", 7), width=10, anchor=tk.W)
        bar_lbl.pack(side=tk.LEFT)

        cnt_lbl = tk.Label(row, text="0", bg=BG_PANEL,
                           fg=TEXT, font=("Courier New", 7), width=6, anchor=tk.E)
        cnt_lbl.pack(side=tk.LEFT)

        arr_lbl = tk.Label(row, text="->", bg=BG_PANEL,
                           fg=TEXT_DIM, font=("Courier New", 7))
        arr_lbl.pack(side=tk.LEFT, padx=(2, 0))

        heatmap_rows[issue_key] = {
            "bar": bar_lbl,
            "cnt": cnt_lbl,
            "arr": arr_lbl,
            "color": color,
        }

    # ── Live journal feed ─────────────────────────────────────────────────────
    tk.Frame(tab_qao, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    jf_hdr = tk.Frame(tab_qao, bg=BG, padx=10, pady=2)
    jf_hdr.pack(fill=tk.X, padx=6)
    tk.Label(jf_hdr, text="LIVE JOURNAL FEED  (last 30 issue entries)", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    journal_feed = scrolledtext.ScrolledText(
        tab_qao, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=9,
        insertbackground=TEXT,
    )
    journal_feed.pack(fill=tk.BOTH, padx=6, pady=(0, 4), expand=False)

    # Color tags per axis
    for ax, col in AXIS_COLORS.items():
        journal_feed.tag_config(f"ax_{ax}", foreground=col)
    journal_feed.tag_config("default_j", foreground=TEXT_DIM)

    # ── QAO stats footer ──────────────────────────────────────────────────────
    tk.Frame(tab_qao, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    qao_stats_frame = tk.Frame(tab_qao, bg=BG_PANEL, pady=4, padx=10)
    qao_stats_frame.pack(fill=tk.X, padx=6, pady=(2, 4))
    qao_stats_lbl = tk.Label(qao_stats_frame, text="nodes:--  edges:--  relics:--  journal entries:--",
                             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8))
    qao_stats_lbl.pack(anchor=tk.W)

    # ── Saved issue counts for trend comparison ───────────────────────────────
    _qao_prev_counts: Dict[str, int] = {}

    def _journal_axis_tag(line: str) -> str:
        """Determine which axis colour to apply to a journal entry."""
        for issue_key, axis in QAO_AXIS_MAP.items():
            if issue_key in line:
                return f"ax_{axis}"
        return "default_j"

    def _update_journal_feed(entries: List[str]) -> None:
        journal_feed.configure(state=tk.NORMAL)
        journal_feed.delete("1.0", tk.END)
        for raw in entries:
            # Try to pretty-display: show timestamp + first issue name + count
            try:
                obj = json.loads(raw)
                ts_val = obj.get("timestamp", obj.get("ts", "?"))
                issues = obj.get("issues", [])
                preview = ", ".join(str(i) for i in issues[:3])
                display = f"[{ts_val}] {preview}\n"
            except Exception:
                display = raw[:120] + "\n"
            tag = _journal_axis_tag(display)
            journal_feed.insert(tk.END, display, tag)
        journal_feed.see(tk.END)
        journal_feed.configure(state=tk.DISABLED)

    # ========================================================================
    # TAB 3: VISION
    # ========================================================================
    tab_vision_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_vision_outer, text="  Vision  ")
    tab_vision = _make_scrollable_inner(tab_vision_outer)

    # ── Status bar ────────────────────────────────────────────────────────────
    vis_status_frame = tk.Frame(tab_vision, bg=BG_PANEL, pady=5, padx=10)
    vis_status_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

    vis_run_lbl = tk.Label(vis_status_frame, text="Observer: --", bg=BG_PANEL,
                           fg=ACCENT2, font=("Courier New", 10, "bold"))
    vis_run_lbl.pack(side=tk.LEFT)

    vis_interval_lbl = tk.Label(vis_status_frame, text="interval:--s", bg=BG_PANEL,
                                fg=TEXT_DIM, font=("Courier New", 9))
    vis_interval_lbl.pack(side=tk.LEFT, padx=12)

    vis_frames_lbl = tk.Label(vis_status_frame, text="frames:--", bg=BG_PANEL,
                              fg=TEXT_DIM, font=("Courier New", 9))
    vis_frames_lbl.pack(side=tk.LEFT, padx=4)

    vis_lastcap_lbl = tk.Label(vis_status_frame, text="last:--", bg=BG_PANEL,
                               fg=TEXT_DIM, font=("Courier New", 9))
    vis_lastcap_lbl.pack(side=tk.LEFT, padx=12)

    # ── WHAT I SEE — Aurora's description of current visual perception ────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    _vis_desc_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    _vis_desc_hdr.pack(fill=tk.X, padx=6)
    tk.Label(_vis_desc_hdr, text="WHAT I SEE", bg=BG,
             fg="#f472b6", font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    _vis_desc_frame = tk.Frame(tab_vision, bg=BG_PANEL, padx=10, pady=6)
    _vis_desc_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    vis_perception_lbl = tk.Label(
        _vis_desc_frame, text="Waiting for visual data...",
        bg=BG_PANEL, fg=TEXT, font=("Courier New", 10),
        wraplength=700, justify=tk.LEFT, anchor="w",
    )
    vis_perception_lbl.pack(fill=tk.X)

    # ── Live frame display ────────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    vis_live_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    vis_live_hdr.pack(fill=tk.X, padx=6)
    tk.Label(vis_live_hdr, text="LIVE FEED  (latest capture)", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    vis_camera_btn = tk.Button(
        vis_live_hdr,
        text="CAM ON",
        command=_toggle_camera_capture,
        bg=BG_PANEL,
        fg="#4ade80",
        font=("Courier New", 8, "bold"),
        relief=tk.FLAT,
        padx=8,
        pady=2,
        activebackground=CHART_GRID,
        activeforeground=TEXT,
        cursor="hand2",
    )
    vis_camera_btn.pack(side=tk.RIGHT, padx=(0, 6))
    vis_frame_ts_lbl = tk.Label(vis_live_hdr, text="", bg=BG,
                                fg=TEXT_DIM, font=("Courier New", 7))
    vis_frame_ts_lbl.pack(side=tk.RIGHT, padx=6)
    _update_camera_btn()

    vis_live_frame = tk.Frame(tab_vision, bg=BG_PANEL)
    vis_live_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    _vis_img_ref = {"photo": None}   # keep PIL PhotoImage alive (avoid GC)
    vis_img_lbl = tk.Label(vis_live_frame, bg=BG_PANEL, text="No frame yet",
                           fg=TEXT_DIM, font=("Courier New", 8))
    vis_img_lbl.pack(side=tk.LEFT, padx=4, pady=4)

    # ── Current scene info ────────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    scene_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    scene_hdr.pack(fill=tk.X, padx=6)
    tk.Label(scene_hdr, text="CURRENT SCENE", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    scene_info_frame = tk.Frame(tab_vision, bg=BG_PANEL, padx=10, pady=4)
    scene_info_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

    scene_info_labels: Dict[str, tk.Label] = {}
    _SCENE_ROWS = [
        ("scene_type",    "Scene type"),
        ("brightness",    "Brightness"),
        ("edge_density",  "Edge density"),
        ("motion",        "Motion"),
        ("concepts",      "Concepts matched"),
    ]
    for key, label in _SCENE_ROWS:
        row = tk.Frame(scene_info_frame, bg=BG_PANEL)
        row.pack(side=tk.LEFT, padx=14)
        tk.Label(row, text=label, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        lbl = tk.Label(row, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 10, "bold"))
        lbl.pack()
        scene_info_labels[key] = lbl

    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    vis_crystal_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    vis_crystal_hdr.pack(fill=tk.X, padx=6)
    tk.Label(vis_crystal_hdr, text="VISION CRYSTAL  (growth · promotions · semantic load)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    vis_crystal_frame = tk.Frame(tab_vision, bg=BG_PANEL, padx=10, pady=4)
    vis_crystal_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    vis_crystal_labels: Dict[str, tk.Label] = {}
    for _lbl, _key in [
        ("hue", "hue"),
        ("shape", "shape"),
        ("motion", "motion"),
        ("semantic", "semantic"),
        ("frames", "frames"),
    ]:
        _row = tk.Frame(vis_crystal_frame, bg=BG_PANEL)
        _row.pack(side=tk.LEFT, padx=14)
        tk.Label(_row, text=_lbl, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        _val = tk.Label(_row, text="--", bg=BG_PANEL,
                        fg=ACCENT2, font=("Courier New", 10, "bold"), justify=tk.CENTER)
        _val.pack()
        vis_crystal_labels[_key] = _val

    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    vis_rec_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    vis_rec_hdr.pack(fill=tk.X, padx=6)
    tk.Label(vis_rec_hdr, text="LIVE RECOGNITIONS  (recent matches · bindings · semantic cues)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    vis_rec_box = scrolledtext.ScrolledText(
        tab_vision, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=5,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    vis_rec_box.pack(fill=tk.BOTH, padx=6, pady=(0, 4), expand=False)
    vis_rec_box.tag_config("visual", foreground="#f472b6")
    vis_rec_box.tag_config("audio", foreground="#4ade80")
    vis_rec_box.tag_config("semantic", foreground=ACCENT2)
    vis_rec_box.tag_config("dim", foreground=TEXT_DIM)

    # ── Scene log ─────────────────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    slog_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    slog_hdr.pack(fill=tk.X, padx=6)
    tk.Label(slog_hdr, text="SCENE LOG  (last 15 observations)", bg=BG,
             fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    scene_log_box = scrolledtext.ScrolledText(
        tab_vision, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=10,
        insertbackground=TEXT,
    )
    scene_log_box.pack(fill=tk.BOTH, padx=6, pady=(0, 4))

    scene_log_box.tag_config("text_heavy",  foreground=ACCENT2)
    scene_log_box.tag_config("image_rich",  foreground="#f472b6")
    scene_log_box.tag_config("terminal",    foreground="#4ade80")
    scene_log_box.tag_config("idle",        foreground=TEXT_DIM)
    scene_log_box.tag_config("active",      foreground="#fb923c")
    scene_log_box.tag_config("default_sl",  foreground=TEXT_DIM)

    # ── Controls ──────────────────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    ctrl_frame = tk.Frame(tab_vision, bg=BG_PANEL, pady=5, padx=10)
    ctrl_frame.pack(fill=tk.X, padx=6, pady=(2, 2))

    tk.Label(ctrl_frame, text="Interval (s):", bg=BG_PANEL,
             fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT)
    vis_interval_var = tk.DoubleVar(value=5.0)
    vis_slider = tk.Scale(
        ctrl_frame, from_=2, to=30, orient=tk.HORIZONTAL,
        variable=vis_interval_var, bg=BG_PANEL, fg=TEXT,
        highlightthickness=0, troughcolor=CHART_GRID,
        activebackground=ACCENT, font=("Courier New", 7),
        length=180,
    )
    vis_slider.pack(side=tk.LEFT, padx=8)

    vis_startstop_lbl = tk.Label(ctrl_frame, text="[Start/Stop: use /screen in daemon]",
                                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 7))
    vis_startstop_lbl.pack(side=tk.LEFT, padx=8)

    # ── Vision index stats ────────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    vis_idx_frame = tk.Frame(tab_vision, bg=BG_PANEL, pady=4, padx=10)
    vis_idx_frame.pack(fill=tk.X, padx=6, pady=(2, 2))
    vis_idx_lbl = tk.Label(vis_idx_frame,
                           text="clusters:--  vectors:--  oets_bound:--  screen_dir file count:--",
                           bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8))
    vis_idx_lbl.pack(anchor=tk.W)

    # ── Observer telemetry log ────────────────────────────────────────────────
    tk.Frame(tab_vision, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    vis_telem_hdr = tk.Frame(tab_vision, bg=BG, padx=10, pady=2)
    vis_telem_hdr.pack(fill=tk.X, padx=6)
    tk.Label(vis_telem_hdr, text="OBSERVER TELEMETRY  (daemon log · vision events)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    vis_telem_box = scrolledtext.ScrolledText(
        tab_vision, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    vis_telem_box.pack(fill=tk.BOTH, padx=6, pady=(0, 6), expand=True)
    vis_telem_box.tag_config("vision",  foreground=ACCENT2)
    vis_telem_box.tag_config("screen",  foreground="#4ade80")
    vis_telem_box.tag_config("active",  foreground="#fb923c")
    vis_telem_box.tag_config("dim",     foreground=TEXT_DIM)

    # ========================================================================
    # TAB 4: AUDIO  (Sensory Crystal microphone facets)
    # ========================================================================
    tab_audio_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_audio_outer, text="  Audio  ")
    tab_audio = _make_scrollable_inner(tab_audio_outer)

    # ── Status bar ────────────────────────────────────────────────────────────
    aud_status_frame = tk.Frame(tab_audio, bg=BG_PANEL, pady=5, padx=10)
    aud_status_frame.pack(fill=tk.X, padx=6, pady=(6, 2))
    aud_status_lbl = tk.Label(aud_status_frame, text="Sensory Crystal: --",
                               bg=BG_PANEL, fg=ACCENT2, font=("Courier New", 10, "bold"))
    aud_status_lbl.pack(side=tk.LEFT)
    aud_frames_lbl = tk.Label(aud_status_frame, text="frames:--", bg=BG_PANEL,
                               fg=TEXT_DIM, font=("Courier New", 9))
    aud_frames_lbl.pack(side=tk.LEFT, padx=14)
    aud_maturity_lbl = tk.Label(aud_status_frame, text="crystal maturity:--",
                                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 9))
    aud_maturity_lbl.pack(side=tk.LEFT, padx=8)
    aud_mic_lbl = tk.Label(aud_status_frame, text="● MIC OFF", bg=BG_PANEL,
                            fg=TEXT_DIM, font=("Courier New", 9, "bold"))
    aud_mic_lbl.pack(side=tk.RIGHT, padx=10)

    # ── WHAT I HEAR — Aurora's description of current audio perception ────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    _aud_desc_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    _aud_desc_hdr.pack(fill=tk.X, padx=6)
    tk.Label(_aud_desc_hdr, text="WHAT I HEAR", bg=BG,
             fg="#4ade80", font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    _aud_desc_frame = tk.Frame(tab_audio, bg=BG_PANEL, padx=10, pady=6)
    _aud_desc_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    aud_perception_lbl = tk.Label(
        _aud_desc_frame, text="Waiting for audio data...",
        bg=BG_PANEL, fg=TEXT, font=("Courier New", 10),
        wraplength=700, justify=tk.LEFT, anchor="w",
    )
    aud_perception_lbl.pack(fill=tk.X)

    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    aud_detail_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    aud_detail_hdr.pack(fill=tk.X, padx=6)
    tk.Label(aud_detail_hdr, text="AUDIO CRYSTAL DETAIL  (growth · promotions · semantic load)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    aud_detail_frame = tk.Frame(tab_audio, bg=BG_PANEL, pady=4, padx=10)
    aud_detail_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    aud_detail_labels: Dict[str, tk.Label] = {}
    for _lbl, _key in [
        ("tone", "tone"),
        ("timbre", "timbre"),
        ("rhythm", "rhythm"),
        ("semantic", "semantic"),
        ("lanes", "lanes"),
    ]:
        _row = tk.Frame(aud_detail_frame, bg=BG_PANEL)
        _row.pack(side=tk.LEFT, padx=14)
        tk.Label(_row, text=_lbl, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        _val = tk.Label(_row, text="--", bg=BG_PANEL,
                        fg=ACCENT2, font=("Courier New", 10, "bold"), justify=tk.CENTER)
        _val.pack()
        aud_detail_labels[_key] = _val

    # ── Live ambient audio feed ────────────────────────────────────────────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    _live_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    _live_hdr.pack(fill=tk.X, padx=6)
    tk.Label(_live_hdr, text="LIVE AMBIENT AUDIO  (soundscape features · 0.5s frames)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    _live_ts_lbl = tk.Label(_live_hdr, text="", bg=BG, fg=TEXT_DIM,
                             font=("Courier New", 7))
    _live_ts_lbl.pack(side=tk.RIGHT, padx=6)

    _live_frame = tk.Frame(tab_audio, bg=BG_PANEL, pady=6, padx=10)
    _live_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

    # Row 1: RMS level bar + dB
    _rms_row = tk.Frame(_live_frame, bg=BG_PANEL)
    _rms_row.pack(fill=tk.X, pady=1)
    tk.Label(_rms_row, text="RMS level", width=14, anchor="w",
             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT)
    _rms_bar_canvas = tk.Canvas(_rms_row, bg=BG_LOG, height=14, width=320,
                                 highlightthickness=0)
    _rms_bar_canvas.pack(side=tk.LEFT, padx=4)
    _rms_val_lbl = tk.Label(_rms_row, text="--dB", width=8, anchor="w",
                             bg=BG_PANEL, fg="#4ade80", font=("Courier New", 8, "bold"))
    _rms_val_lbl.pack(side=tk.LEFT, padx=4)
    _act_lbl = tk.Label(_rms_row, text="--", bg=BG_PANEL, fg=ACCENT2,
                         font=("Courier New", 8, "bold"))
    _act_lbl.pack(side=tk.LEFT, padx=8)

    # Row 2: spectral features
    _spec_row = tk.Frame(_live_frame, bg=BG_PANEL)
    _spec_row.pack(fill=tk.X, pady=1)
    _spec_fields: Dict[str, tk.Label] = {}
    for _sf_lbl, _sf_key in [
        ("centroid", "spectral_centroid"),
        ("rolloff",  "spectral_rolloff"),
        ("ZCR",      "zcr"),
        ("fps",      "fps"),
    ]:
        tk.Label(_spec_row, text=f"{_sf_lbl}:", width=9, anchor="w",
                 bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT)
        _v = tk.Label(_spec_row, text="--", width=7, anchor="w",
                      bg=BG_PANEL, fg=TEXT, font=("Courier New", 8, "bold"))
        _v.pack(side=tk.LEFT)
        _spec_fields[_sf_key] = _v

    # ── Facet maturity & promotion progress ───────────────────────────────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    aud_chart_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    aud_chart_hdr.pack(fill=tk.X, padx=6)
    tk.Label(aud_chart_hdr, text="AUDIO FACETS  (tone · timbre · rhythm  —  maturity & node counts)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    _aud_fig_frame = tk.Frame(tab_audio, bg=BG_PANEL)
    _aud_fig_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    _aud_fig_ref = {"fig": None, "canvas": None}

    # ── Cross-modal lanes ─────────────────────────────────────────────────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    aud_lanes_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    aud_lanes_hdr.pack(fill=tk.X, padx=6)
    tk.Label(aud_lanes_hdr, text="CROSS-MODAL LANES  (audio ↔ visual semantic links)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    aud_lanes_frame = tk.Frame(tab_audio, bg=BG_PANEL, padx=10, pady=4)
    aud_lanes_frame.pack(fill=tk.X, padx=6, pady=(0, 2))
    aud_lane_labels: Dict[str, tk.Label] = {}
    for _ln in ("tone↔hue", "timbre↔shape", "rhythm↔motion"):
        _row = tk.Frame(aud_lanes_frame, bg=BG_PANEL)
        _row.pack(side=tk.LEFT, padx=16)
        tk.Label(_row, text=_ln, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        _lbl = tk.Label(_row, text="--", bg=BG_PANEL,
                        fg=ACCENT2, font=("Courier New", 12, "bold"))
        _lbl.pack()
        aud_lane_labels[_ln] = _lbl

    # ── Promotion telemetry log ───────────────────────────────────────────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    aud_telem_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    aud_telem_hdr.pack(fill=tk.X, padx=6)
    tk.Label(aud_telem_hdr, text="SENSORY TELEMETRY  (node promotions · cross-modal links)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    aud_telem_box = scrolledtext.ScrolledText(
        tab_audio, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=8,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    aud_telem_box.pack(fill=tk.BOTH, padx=6, pady=(0, 2))
    aud_telem_box.tag_config("promoted", foreground=ACCENT2)
    aud_telem_box.tag_config("audio",    foreground="#4ade80")
    aud_telem_box.tag_config("visual",   foreground="#f472b6")
    aud_telem_box.tag_config("dim",      foreground=TEXT_DIM)

    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    aud_rec_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    aud_rec_hdr.pack(fill=tk.X, padx=6)
    tk.Label(aud_rec_hdr, text="RECOGNITION FEED  (live audio/visual/semantic matches)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    aud_rec_box = scrolledtext.ScrolledText(
        tab_audio, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=5,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    aud_rec_box.pack(fill=tk.BOTH, padx=6, pady=(0, 2), expand=False)
    aud_rec_box.tag_config("audio", foreground="#4ade80")
    aud_rec_box.tag_config("visual", foreground="#f472b6")
    aud_rec_box.tag_config("semantic", foreground=ACCENT2)
    aud_rec_box.tag_config("dim", foreground=TEXT_DIM)

    # ── DCE reasoning log ─────────────────────────────────────────────────────
    tk.Frame(tab_audio, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    dce_hdr = tk.Frame(tab_audio, bg=BG, padx=10, pady=2)
    dce_hdr.pack(fill=tk.X, padx=6)
    tk.Label(dce_hdr, text="DCE ASSEMBLY  (reasoning · meaning · coherence)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)
    dce_log_box = scrolledtext.ScrolledText(
        tab_audio, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    dce_log_box.pack(fill=tk.X, padx=6, pady=(0, 6))
    dce_log_box.tag_config("high",   foreground="#4ade80")
    dce_log_box.tag_config("mid",    foreground=ACCENT2)
    dce_log_box.tag_config("low",    foreground="#f97316")
    dce_log_box.tag_config("dim",    foreground=TEXT_DIM)

    # ========================================================================
    # TAB 5: EVOLUTION
    # ========================================================================
    tab_evo_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_evo_outer, text="  Evolution  ")
    tab_evo = _make_scrollable_inner(tab_evo_outer)

    # ── Status gauges row ─────────────────────────────────────────────────────
    evo_hdr = tk.Frame(tab_evo, bg=BG_PANEL, pady=6, padx=10)
    evo_hdr.pack(fill=tk.X, padx=6, pady=(6, 2))

    def _evo_gauge(parent, label, key):
        cell = tk.Frame(parent, bg=BG_PANEL, padx=12)
        cell.pack(side=tk.LEFT)
        tk.Label(cell, text=label, bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7)).pack()
        lbl = tk.Label(cell, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 14, "bold"))
        lbl.pack()
        return lbl

    evo_pool_lbl       = _evo_gauge(evo_hdr, "Op Pool Size",     "pool")
    evo_gen1_lbl       = _evo_gauge(evo_hdr, "Gen-1 Surfaces",   "gen1")
    evo_gen2_lbl       = _evo_gauge(evo_hdr, "Gen-2 Injected",   "gen2")
    evo_frontier_lbl   = _evo_gauge(evo_hdr, "Frontier Ops",     "frontier")
    evo_assimilated_lbl= _evo_gauge(evo_hdr, "Assimilated",      "assim")
    evo_compounds_lbl  = _evo_gauge(evo_hdr, "Compound Axes",    "cmpd")

    # ── Two-panel middle row ──────────────────────────────────────────────────
    tk.Frame(tab_evo, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    evo_mid = tk.Frame(tab_evo, bg=BG, pady=4, padx=8)
    evo_mid.pack(fill=tk.X)

    # LEFT: Typed pressure classification
    evo_pressure_panel = _make_panel(evo_mid, "TYPED PRESSURE  (what kind of gap)")
    evo_pressure_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    _PRESSURE_TYPES_DISPLAY = [
        ("knowledge_gap",   "Knowledge gap",    "missing content → retrieval"),
        ("reasoning_gap",   "Reasoning gap",    "chain breaks  → synthesis"),
        ("articulation_gap","Articulation gap", "can't express → precision drill"),
        ("stability_gap",   "Stability gap",    "inconsistent  → consolidate"),
        ("tool_gap",        "Tool gap",         "boundary fail → calibrate"),
        ("code_gap",        "Code gap",         "struct limit  → evo budget"),
    ]
    evo_pressure_rows: Dict[str, Dict[str, tk.Label]] = {}
    for ptype, label, hint in _PRESSURE_TYPES_DISPLAY:
        row = tk.Frame(evo_pressure_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{label:<18}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=18, anchor=tk.W).pack(side=tk.LEFT)
        bar_l = tk.Label(row, text="----------", bg=BG_PANEL,
                         fg=ACCENT2, font=("Courier New", 7), width=12, anchor=tk.W)
        bar_l.pack(side=tk.LEFT)
        pct_l = tk.Label(row, text="0%", bg=BG_PANEL,
                         fg=TEXT, font=("Courier New", 7), width=5)
        pct_l.pack(side=tk.LEFT)
        hint_l = tk.Label(row, text=hint, bg=BG_PANEL,
                          fg=TEXT_DIM, font=("Courier New", 7))
        hint_l.pack(side=tk.LEFT, padx=(4, 0))
        evo_pressure_rows[ptype] = {"bar": bar_l, "pct": pct_l, "hint": hint_l}

    evo_dominant_lbl = tk.Label(evo_pressure_panel, text="dominant: --", bg=BG_PANEL,
                                fg=ACCENT, font=("Courier New", 8, "bold"))
    evo_dominant_lbl.pack(anchor=tk.W, pady=(4, 0))

    # RIGHT: Axis pressure + evolver bias
    evo_axis_panel = _make_panel(evo_mid, "AXIS PRESSURE + EVOLVER BIAS")
    evo_axis_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    _AXIS_DISPLAY = [
        ("X", "Existence", "vitality"),
        ("T", "Temporal",  "processing"),
        ("N", "Energy",    "processing"),
        ("B", "Boundary",  "memory"),
        ("A", "Agency",    "creative"),
    ]
    evo_axis_rows: Dict[str, Dict[str, tk.Label]] = {}
    for ax, name, der_ch in _AXIS_DISPLAY:
        row = tk.Frame(evo_axis_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        color = AXIS_COLORS.get(ax, ACCENT2)
        tk.Label(row, text=f"{ax}  {name:<10}", bg=BG_PANEL,
                 fg=color, font=("Courier New", 7, "bold"), width=13, anchor=tk.W).pack(side=tk.LEFT)
        pressure_l = tk.Label(row, text="press:--", bg=BG_PANEL,
                              fg=ACCENT2, font=("Courier New", 7), width=10)
        pressure_l.pack(side=tk.LEFT)
        bias_l = tk.Label(row, text="bias:--", bg=BG_PANEL,
                          fg=TEXT_DIM, font=("Courier New", 7), width=10)
        bias_l.pack(side=tk.LEFT)
        der_l = tk.Label(row, text=f"→ {der_ch}", bg=BG_PANEL,
                         fg=TEXT_DIM, font=("Courier New", 7))
        der_l.pack(side=tk.LEFT, padx=(4, 0))
        evo_axis_rows[ax] = {"pressure": pressure_l, "bias": bias_l}

    evo_routing_lbl = tk.Label(evo_axis_panel, text="routing: --", bg=BG_PANEL,
                               fg=ACCENT, font=("Courier New", 8, "bold"))
    evo_routing_lbl.pack(anchor=tk.W, pady=(4, 0))

    # ── Second mid row ────────────────────────────────────────────────────────
    tk.Frame(tab_evo, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    evo_mid2 = tk.Frame(tab_evo, bg=BG, pady=4, padx=8)
    evo_mid2.pack(fill=tk.X)

    # LEFT: What evolves next
    evo_next_panel = _make_panel(evo_mid2, "WHAT EVOLVES NEXT")
    evo_next_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    _NEXT_ROWS = [
        ("top_axis",     "Highest bias axis"),
        ("top_bias_val", "Bias magnitude"),
        ("compound_st",  "Compound axes"),
        ("slots_avail",  "Virtual slots open"),
        ("frontier_st",  "Frontier ops"),
        ("gen2_st",      "Gen-2 candidates"),
    ]
    evo_next_labels: Dict[str, tk.Label] = {}
    for key, label in _NEXT_ROWS:
        row = tk.Frame(evo_next_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{label:<22}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=22, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL,
                       fg=ACCENT2, font=("Courier New", 7), anchor=tk.W)
        lbl.pack(side=tk.LEFT)
        evo_next_labels[key] = lbl

    # RIGHT: Training priorities (top fail dims with pressure type)
    evo_train_panel = _make_panel(evo_mid2, "TRAINING PRIORITIES  (fault-line learning)")
    evo_train_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    # dimension → pressure type
    _DIM_TYPE_MAP = {
        "coherence_maintenance":   "reasoning",
        "context_carryover":       "reasoning",
        "semantic_precision":      "articulation",
        "compression_elaboration_fit": "articulation",
        "perspective_integration": "knowledge",
        "uncertainty_signaling":   "knowledge",
        "boundary_calibration":    "tool",
        "ambiguity_handling":      "tool",
        "adaptive_strategy_selection": "stability",
        "framing_selection":       "stability",
        "misunderstanding_repair": "reasoning",
        "emotional_calibration":   "tool",
        "implied_intent_inference":"articulation",
    }
    _TRAIN_SHOW = [
        "coherence_maintenance", "semantic_precision",
        "context_carryover", "perspective_integration",
        "boundary_calibration", "adaptive_strategy_selection",
    ]
    evo_train_labels: Dict[str, Dict[str, tk.Label]] = {}
    for dim in _TRAIN_SHOW:
        ptype = _DIM_TYPE_MAP.get(dim, "")
        short = dim.replace("_", " ")[:20]
        row = tk.Frame(evo_train_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{short:<20}", bg=BG_PANEL,
                 fg=TEXT_DIM, font=("Courier New", 7), width=20, anchor=tk.W).pack(side=tk.LEFT)
        sev_l = tk.Label(row, text="--", bg=BG_PANEL,
                         fg=ACCENT2, font=("Courier New", 7), width=5)
        sev_l.pack(side=tk.LEFT)
        type_l = tk.Label(row, text=f"[{ptype}]" if ptype else "", bg=BG_PANEL,
                          fg=TEXT_DIM, font=("Courier New", 7))
        type_l.pack(side=tk.LEFT, padx=(3, 0))
        evo_train_labels[dim] = {"sev": sev_l, "type": type_l}

    # ── Multi-layer Pressure Monitor ──────────────────────────────────────────
    tk.Frame(tab_evo, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    evo_plog_hdr = tk.Frame(tab_evo, bg=BG, padx=10, pady=2)
    evo_plog_hdr.pack(fill=tk.X, padx=6)
    tk.Label(evo_plog_hdr,
             text="LAYER PRESSURE MONITOR  (genealogy · turn-chain · template · behavioral · 625-surface)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    # Top row: four layer mini-panels side by side
    evo_plog_top = tk.Frame(tab_evo, bg=BG, pady=2, padx=8)
    evo_plog_top.pack(fill=tk.X, padx=6)

    def _layer_panel(parent, title):
        p = _make_panel(parent, title)
        p.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        return p

    # L4 Genealogy panel — leverage-scale aware
    p_l4g = _layer_panel(evo_plog_top, "L4 GENEALOGY  (leverage-normalized)")
    evo_l4g_labels: Dict[str, tk.Label] = {}
    # Gate/tension stats
    for key, label in [("total","Experiences"), ("gate_G4","Gate-4 rej"),
                       ("gate_G5","Gate-5 rej"), ("tension","Avg tension")]:
        row = tk.Frame(p_l4g, bg=BG_PANEL)
        row.pack(fill=tk.X)
        tk.Label(row, text=f"{label:<11}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 7), width=11, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=ACCENT2,
                       font=("Courier New", 7))
        lbl.pack(side=tk.LEFT)
        evo_l4g_labels[key] = lbl
    # Leverage scale bars: X→T→N→B→A with budget labels
    tk.Frame(p_l4g, bg=CHART_GRID, height=1).pack(fill=tk.X, pady=2)
    _AXIS_COSTS_DISPLAY = [
        ("X", "b=1",  0.35, "surface"),
        ("T", "b=5",  0.42, "temporal"),
        ("N", "b=6",  0.50, "zero-pt"),
        ("B", "b=18", 0.65, "boundary"),
        ("A", "b=50", 0.82, "agency"),
    ]
    evo_l4g_bars: Dict[str, Dict] = {}
    for ax, cost_lbl, flip_thr, role in _AXIS_COSTS_DISPLAY:
        row = tk.Frame(p_l4g, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        color = AXIS_COLORS.get(ax, ACCENT2)
        tk.Label(row, text=ax, bg=BG_PANEL, fg=color,
                 font=("Courier New", 7, "bold"), width=2).pack(side=tk.LEFT)
        tk.Label(row, text=f"{cost_lbl:<5}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 6), width=5).pack(side=tk.LEFT)
        bar_lbl = tk.Label(row, text="░░░░░░░░░░", bg=BG_PANEL, fg=color,
                           font=("Courier New", 7), width=10, anchor=tk.W)
        bar_lbl.pack(side=tk.LEFT)
        pct_lbl = tk.Label(row, text="0%", bg=BG_PANEL, fg=TEXT_DIM,
                           font=("Courier New", 6), width=4)
        pct_lbl.pack(side=tk.LEFT)
        evo_l4g_bars[ax] = {"bar": bar_lbl, "pct": pct_lbl, "color": color}
    # Leverage band indicator
    tk.Frame(p_l4g, bg=CHART_GRID, height=1).pack(fill=tk.X, pady=2)
    evo_band_lbl = tk.Label(p_l4g, text="band: --", bg=BG_PANEL,
                            fg=ACCENT2, font=("Courier New", 7, "bold"))
    evo_band_lbl.pack(anchor=tk.W)
    evo_net_lbl = tk.Label(p_l4g, text="net leverage: --", bg=BG_PANEL,
                           fg=TEXT_DIM, font=("Courier New", 7))
    evo_net_lbl.pack(anchor=tk.W)
    evo_l4g_labels["band"] = evo_band_lbl
    evo_l4g_labels["net"]  = evo_net_lbl

    # L4 Turn-chain + Dream panel
    p_l4t = _layer_panel(evo_plog_top, "L4 TURN-CHAIN / DREAM")
    evo_l4t_labels: Dict[str, tk.Label] = {}
    for key, label in [("tc_total","TC events"), ("tc_tension","TC tension"),
                       ("dm_total","Dream events"), ("dm_tension","Dream tension")]:
        row = tk.Frame(p_l4t, bg=BG_PANEL)
        row.pack(fill=tk.X)
        tk.Label(row, text=f"{label:<14}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 7), width=14, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=ACCENT2,
                       font=("Courier New", 7))
        lbl.pack(side=tk.LEFT)
        evo_l4t_labels[key] = lbl

    # L5/L6 panel
    p_l56 = _layer_panel(evo_plog_top, "L5 TEMPLATE / L6 BEHAVIORAL")
    evo_l56_labels: Dict[str, tk.Label] = {}
    for key, label in [("pool","L5 pool"), ("gen","L5 gen"),
                       ("gov_nodes","L6 nodes"), ("gov_energy","L6 energy"),
                       ("crystal_gaps","L6 crystal gaps")]:
        row = tk.Frame(p_l56, bg=BG_PANEL)
        row.pack(fill=tk.X)
        tk.Label(row, text=f"{label:<16}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 7), width=16, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=ACCENT2,
                       font=("Courier New", 7))
        lbl.pack(side=tk.LEFT)
        evo_l56_labels[key] = lbl

    # L7 625-map + surface panel
    p_l7 = _layer_panel(evo_plog_top, "L7 625-MAP / SURFACE")
    evo_l7_labels: Dict[str, tk.Label] = {}
    for key, label in [("occupied","Occupied slots"), ("highway","Highway slots"),
                       ("wX","X weight"), ("wT","T weight"), ("wN","N weight"),
                       ("wB","B weight"), ("wA","A weight")]:
        row = tk.Frame(p_l7, bg=BG_PANEL)
        row.pack(fill=tk.X)
        tk.Label(row, text=f"{label:<14}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 7), width=14, anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=ACCENT2,
                       font=("Courier New", 7))
        lbl.pack(side=tk.LEFT)
        evo_l7_labels[key] = lbl

    # Bottom row: experience feed (left) + surface co-occurrence (right)
    evo_plog_mid = tk.Frame(tab_evo, bg=BG, pady=2, padx=8)
    evo_plog_mid.pack(fill=tk.BOTH, padx=6, pady=(0, 2))

    # Left: multi-source experience feed
    evo_plog_feed = scrolledtext.ScrolledText(
        evo_plog_mid, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 7),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6, width=60,
        insertbackground=TEXT, wrap=tk.NONE,
    )
    evo_plog_feed.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
    for _ax in ("X", "T", "N", "B", "A"):
        evo_plog_feed.tag_config(f"ax_{_ax}", foreground=AXIS_COLORS.get(_ax, ACCENT2))
    evo_plog_feed.tag_config("hi",       foreground="#ef4444")
    evo_plog_feed.tag_config("genealogy",foreground="#f59e0b")
    evo_plog_feed.tag_config("turn",     foreground=ACCENT2)
    evo_plog_feed.tag_config("dream",    foreground="#818cf8")
    evo_plog_feed.tag_config("surface",  foreground="#4ade80")
    evo_plog_feed.tag_config("dim",      foreground=TEXT_DIM)

    # Right: axis co-occurrence matrix
    evo_cooc_panel = _make_panel(evo_plog_mid, "SURFACE CO-OCCURRENCE")
    evo_cooc_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
    _AXIS_PAIRS = [
        ("N","B"), ("N","T"), ("N","A"), ("N","X"),
        ("B","T"), ("B","A"), ("B","X"), ("T","A"), ("T","X"), ("A","X"),
    ]
    evo_cooc_labels: Dict[str, tk.Label] = {}
    for a1, a2 in _AXIS_PAIRS:
        row = tk.Frame(evo_cooc_panel, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        key = f"{a1}{a2}"
        c1 = AXIS_COLORS.get(a1, ACCENT2)
        c2 = AXIS_COLORS.get(a2, ACCENT2)
        lf = tk.Frame(row, bg=BG_PANEL, width=40)
        lf.pack(side=tk.LEFT)
        tk.Label(lf, text=a1, bg=BG_PANEL, fg=c1,
                 font=("Courier New", 7, "bold"), width=2).pack(side=tk.LEFT)
        tk.Label(lf, text="+", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 7), width=1).pack(side=tk.LEFT)
        tk.Label(lf, text=a2, bg=BG_PANEL, fg=c2,
                 font=("Courier New", 7, "bold"), width=2).pack(side=tk.LEFT)
        cnt_l = tk.Label(row, text="--", bg=BG_PANEL, fg=ACCENT2,
                         font=("Courier New", 7), width=5)
        cnt_l.pack(side=tk.LEFT)
        bar_l = tk.Label(row, text="", bg=BG_PANEL, fg="#22c55e",
                         font=("Courier New", 7))
        bar_l.pack(side=tk.LEFT, padx=(2, 0))
        evo_cooc_labels[key] = {"cnt": cnt_l, "bar": bar_l}

    # ── Growth directive (full width) ─────────────────────────────────────────
    tk.Frame(tab_evo, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    evo_directive_hdr = tk.Frame(tab_evo, bg=BG, padx=10, pady=2)
    evo_directive_hdr.pack(fill=tk.X, padx=6)
    tk.Label(evo_directive_hdr, text="GROWTH DIRECTIVE  (what Aurora should study next)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    evo_directive_box = scrolledtext.ScrolledText(
        tab_evo, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=8,
        insertbackground=TEXT,
        wrap=tk.WORD,
    )
    evo_directive_box.pack(fill=tk.X, padx=6, pady=(0, 4))
    evo_directive_box.tag_config("heading",    foreground=ACCENT,  font=("Courier New", 8, "bold"))
    evo_directive_box.tag_config("directive",  foreground=ACCENT2)
    evo_directive_box.tag_config("hypothesis", foreground="#f472b6")
    evo_directive_box.tag_config("domain",     foreground="#4ade80")
    evo_directive_box.tag_config("dim",        foreground=TEXT_DIM)

    # ── Daemon activity log (MUTATE / ASSIM / EVO / DREAM / PRESSURE lines) ──
    tk.Frame(tab_evo, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6)
    evo_act_hdr = tk.Frame(tab_evo, bg=BG, padx=10, pady=2)
    evo_act_hdr.pack(fill=tk.X, padx=6)
    tk.Label(evo_act_hdr, text="DAEMON ACTIVITY LOG  (mutation · assimilation · evolution events)",
             bg=BG, fg=ACCENT, font=("Courier New", 8, "bold")).pack(side=tk.LEFT)

    evo_activity_box = scrolledtext.ScrolledText(
        tab_evo, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=14,
        insertbackground=TEXT,
        wrap=tk.NONE,
    )
    evo_activity_box.pack(fill=tk.BOTH, padx=6, pady=(0, 8), expand=True)
    evo_activity_box.tag_config("mutate",   foreground="#f472b6")
    evo_activity_box.tag_config("dream",    foreground="#818cf8")
    evo_activity_box.tag_config("assim",    foreground="#4ade80")
    evo_activity_box.tag_config("evo",      foreground=ACCENT2)
    evo_activity_box.tag_config("pressure", foreground="#fbbf24")
    evo_activity_box.tag_config("study",    foreground="#38bdf8")
    evo_activity_box.tag_config("gen2",     foreground="#f472b6")
    evo_activity_box.tag_config("sensory",    foreground="#818cf8")
    evo_activity_box.tag_config("dim",      foreground=TEXT_DIM)

    # ========================================================================
    # TAB 5: TRAINING  (live corpus training session monitor)
    # ========================================================================
    REFRESH_TRAINING_MS = 2000

    tab_training_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_training_outer, text="  Training  ")
    tab_training = _make_scrollable_inner(tab_training_outer)

    # ── Status bar ────────────────────────────────────────────────────────────
    trn_status_bar = tk.Frame(tab_training, bg=BG_PANEL, pady=6, padx=10)
    trn_status_bar.pack(fill=tk.X, padx=6, pady=(6, 2))

    trn_active_lbl = tk.Label(trn_status_bar, text="● IDLE", bg=BG_PANEL,
                               fg=TEXT_DIM, font=("Courier New", 11, "bold"))
    trn_active_lbl.pack(side=tk.LEFT, padx=(0, 16))

    trn_pass_lbl = tk.Label(trn_status_bar, text="pass: --", bg=BG_PANEL,
                             fg=ACCENT2, font=("Courier New", 10))
    trn_pass_lbl.pack(side=tk.LEFT, padx=8)

    trn_sim_lbl = tk.Label(trn_status_bar, text="sim: --", bg=BG_PANEL,
                            fg=TEXT, font=("Courier New", 10))
    trn_sim_lbl.pack(side=tk.LEFT, padx=8)

    trn_updated_lbl = tk.Label(trn_status_bar, text="", bg=BG_PANEL,
                                fg=TEXT_DIM, font=("Courier New", 8))
    trn_updated_lbl.pack(side=tk.RIGHT)

    # ── Progress bars row ─────────────────────────────────────────────────────
    tk.Frame(tab_training, bg=CHART_GRID, height=1).pack(fill=tk.X)
    trn_prog_frame = tk.Frame(tab_training, bg=BG_PANEL, pady=6, padx=12)
    trn_prog_frame.pack(fill=tk.X, padx=6, pady=2)

    def _trn_progress_row(parent, label):
        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=label, bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8), width=14, anchor="w").pack(side=tk.LEFT)
        bar = tk.Label(row, text=chr(0x2591)*20, bg=BG_PANEL,
                       fg=ACCENT, font=("Courier New", 9))
        bar.pack(side=tk.LEFT, padx=4)
        pct = tk.Label(row, text="0%", bg=BG_PANEL, fg=TEXT,
                       font=("Courier New", 9))
        pct.pack(side=tk.LEFT)
        detail = tk.Label(row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                          font=("Courier New", 8))
        detail.pack(side=tk.LEFT, padx=8)
        return bar, pct, detail

    trn_corpus_bar, trn_corpus_pct, trn_corpus_detail = _trn_progress_row(trn_prog_frame, "Corpus total")
    trn_session_bar, trn_session_pct, trn_session_detail = _trn_progress_row(trn_prog_frame, "This session")

    # ── Mid row: fail dims + sim burst ────────────────────────────────────────
    tk.Frame(tab_training, bg=CHART_GRID, height=1).pack(fill=tk.X)
    trn_mid = tk.Frame(tab_training, bg=BG, pady=4, padx=8)
    trn_mid.pack(fill=tk.X)

    # LEFT: top fail dims being trained
    trn_fail_panel = _make_panel(trn_mid, "FAIL DIMS  (by severity)")
    trn_fail_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    _TRN_DIMS = [
        "emotional_calibration", "framing_selection", "coherence_maintenance",
        "perspective_integration", "context_carryover", "boundary_calibration",
        "uncertainty_signaling",  "semantic_precision",
    ]
    trn_fail_rows: Dict[str, Any] = {}
    for _dim in _TRN_DIMS:
        _row = tk.Frame(trn_fail_panel, bg=BG_PANEL)
        _row.pack(fill=tk.X, pady=1, padx=4)
        _short = _dim.replace("_", " ")[:22]
        tk.Label(_row, text=_short, bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8), width=22, anchor="w").pack(side=tk.LEFT)
        _bar = tk.Label(_row, text=chr(0x2591)*10, bg=BG_PANEL,
                        fg=ACCENT2, font=("Courier New", 8))
        _bar.pack(side=tk.LEFT, padx=2)
        _sev = tk.Label(_row, text="--", bg=BG_PANEL, fg=TEXT,
                        font=("Courier New", 8))
        _sev.pack(side=tk.LEFT, padx=2)
        trn_fail_rows[_dim] = {"bar": _bar, "sev": _sev}

    # RIGHT: sim burst status + lesson plan
    trn_burst_panel = _make_panel(trn_mid, "LAST SIM BURST  /  LESSON PLAN")
    trn_burst_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    trn_burst_ts_lbl  = tk.Label(trn_burst_panel, text="Last burst: --", bg=BG_PANEL,
                                  fg=TEXT_DIM, font=("Courier New", 8))
    trn_burst_ts_lbl.pack(anchor="w", padx=6, pady=(2, 0))

    trn_burst_eps_lbl = tk.Label(trn_burst_panel, text="Episodes: --", bg=BG_PANEL,
                                  fg=ACCENT2, font=("Courier New", 9))
    trn_burst_eps_lbl.pack(anchor="w", padx=6)

    trn_burst_dims_lbl = tk.Label(trn_burst_panel, text="Targeting: --", bg=BG_PANEL,
                                   fg=TEXT, font=("Courier New", 8), wraplength=220,
                                   justify="left")
    trn_burst_dims_lbl.pack(anchor="w", padx=6, pady=(0, 4))

    tk.Frame(trn_burst_panel, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=4)

    trn_plan_ts_lbl  = tk.Label(trn_burst_panel, text="Lesson plan: --", bg=BG_PANEL,
                                 fg=TEXT_DIM, font=("Courier New", 8))
    trn_plan_ts_lbl.pack(anchor="w", padx=6, pady=(4, 0))

    trn_plan_dims_lbl = tk.Label(trn_burst_panel, text="--", bg=BG_PANEL,
                                  fg=ACCENT, font=("Courier New", 8), wraplength=220,
                                  justify="left")
    trn_plan_dims_lbl.pack(anchor="w", padx=6, pady=(0, 4))

    # ── Events log ────────────────────────────────────────────────────────────
    tk.Frame(tab_training, bg=CHART_GRID, height=1).pack(fill=tk.X)
    trn_log_frame = tk.Frame(tab_training, bg=BG_LOG)
    trn_log_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 6))

    trn_log_box = tk.Text(trn_log_frame, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
                           state=tk.DISABLED, wrap=tk.WORD, height=10,
                           relief=tk.FLAT, borderwidth=0)
    trn_log_box.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
    trn_log_box.tag_config("sim",       foreground=ACCENT)
    trn_log_box.tag_config("check",     foreground=ACCENT2)
    trn_log_box.tag_config("pass",      foreground="#4ade80")
    trn_log_box.tag_config("batch",     foreground="#f59e0b")
    trn_log_box.tag_config("complete",  foreground="#22c55e")
    trn_log_box.tag_config("dim",       foreground=TEXT_DIM)

    # ========================================================================
    # REFRESH FUNCTIONS (each tab refreshes independently)
    # ========================================================================

    def refresh_overview():
        try:
            data = reader.read_all()

            fail_points   = data["fail_points"]
            aurora_state  = data["aurora_state"]
            daemon_status = data["daemon_status"]
            lex_size      = data["lexicon_size"]
            log_lines     = data["log_lines"]
            unread        = data["messages_unread"]

            # Title bar
            gen    = aurora_state.get("generation", "--")
            epochs = aurora_state.get("simulation_epochs", "--")
            lbl_gen.config(text=f"gen:{gen}  sim:{epochs}")

            heat_label_str, heat_color = reader.heat_label(daemon_status)
            lbl_heat.config(text=f"● {heat_label_str}", fg=heat_color)

            ts = time.strftime("%H:%M:%S")
            lbl_refresh.config(text=f"refresh {ts}")

            if unread:
                lbl_msgs.config(text=f"unread:{unread}")
            else:
                lbl_msgs.config(text="")

            # Core axes radar
            axis_scores = reader.axis_scores(fail_points)
            ax_labels   = list(AXIS_DIMS.keys())
            ax_values   = [axis_scores.get(k, 0.5) for k in ax_labels]
            _draw_radar(fig_left, ax_left, ax_labels, ax_values,
                        RADAR_FILL, RADAR_LINE, "Core Development Axes")
            canvas_left.draw()

            # Traits radar
            trait_scores_d = reader.trait_scores(aurora_state)
            tr_values = [trait_scores_d.get(t, 0.0) for t in TRAIT_LABELS]
            peak = max(tr_values) if max(tr_values) > 0 else 1.0
            tr_norm = [v / peak for v in tr_values]
            _draw_radar(fig_right, ax_right, TRAIT_SHORT, tr_norm,
                        "#0e7490", ACCENT2, "Character Traits (relative)")
            canvas_right.draw()

            # Vitals
            gov        = aurora_state.get("governance_stats", {})
            oets_nodes = gov.get("total_nodes", "--") if isinstance(gov, dict) else "--"
            browser_today = daemon_status.get("browser_today", "--")
            distill_status = daemon_status.get("distillation_status") or data.get("distillation_metrics", {}).get("distillation_status", "--")
            interaction_status = data.get("interaction_status", {}) or {}
            interaction_strategy = daemon_status.get("interaction_strategy") or interaction_status.get("interaction_strategy") or interaction_status.get("latest_strategy") or "--"
            interaction_conf = daemon_status.get("interaction_confidence")
            if interaction_conf is None:
                interaction_conf = interaction_status.get("interaction_confidence")
            if interaction_conf is None:
                interaction_conf = interaction_status.get("latest_confidence")
            interaction_ready = daemon_status.get("interaction_quasi_ready")
            if interaction_ready is None:
                interaction_ready = interaction_status.get("interaction_quasi_ready")
            voice_status  = daemon_status.get("voice", "listening")
            layer8_status = daemon_status.get("layer8", {}) or {}
            drive_sync_status = daemon_status.get("drive_sync", {}) or {}
            checkpoint_status = daemon_status.get("checkpoint", {}) or {}
            manual_lineage_status = daemon_status.get("manual_code_lineage", {}) or {}
            dream_trainer_status = daemon_status.get("dream_trainer", {}) or {}
            code_evolution_status = daemon_status.get("code_evolution_chamber", {}) or {}

            # Prefer live corpus_runner_status over stale daemon_status for
            # genealogy metrics (outlet, epoch, oets) — daemon_status is only
            # written by aurora_daemon.py, never by corpus_runner.
            cr_status  = data.get("corpus_runner_status", {})
            outlet_raw = (cr_status.get("outlet_push_fraction")
                          if cr_status.get("outlet_push_fraction") is not None
                          else daemon_status.get("outlet_push_fraction", "--"))
            outlet = f"{outlet_raw:.4f}" if isinstance(outlet_raw, float) else str(outlet_raw)
            if cr_status.get("oets_nodes") is not None:
                oets_nodes = str(cr_status["oets_nodes"])
            if cr_status.get("current_epoch") is not None:
                epochs = cr_status["current_epoch"]

            vital_labels["vocab"].config(text=str(lex_size) if lex_size else "--")
            vital_labels["oets"].config(text=str(oets_nodes))
            vital_labels["outlet"].config(text=str(outlet))
            vital_labels["epochs"].config(text=str(epochs))
            vital_labels["browser"].config(text=str(browser_today))
            vital_labels["distill"].config(text=str(distill_status)[:18])
            evolve_bits = []
            if code_evolution_status:
                if code_evolution_status.get("repo_root"):
                    evolve_bits.append("ce")
                if code_evolution_status.get("accepted_count", 0):
                    evolve_bits.append(f"a{int(code_evolution_status.get('accepted_count', 0))}")
                else:
                    evolve_bits.append("idle")
            vital_labels["evolve"].config(text="/".join(evolve_bits)[:18] if evolve_bits else "--")
            persist_bits = []
            persist_bits.append("sync" if drive_sync_status.get("rclone_available") else "local")
            persist_bits.append("ckpt" if checkpoint_status else "--")
            if manual_lineage_status.get("initialized"):
                persist_bits.append("lineage")
            if dream_trainer_status.get("top_fails"):
                persist_bits.append("learn")
            vital_labels["persist"].config(text="/".join(persist_bits)[:18])
            _int_label = str(interaction_strategy or "--")
            if isinstance(interaction_conf, (int, float)) and interaction_conf > 0:
                _int_label = f"{_int_label}:{float(interaction_conf):.2f}"[:18]
            vital_labels["interact"].config(
                text=_int_label[:18],
                fg=("#34d399" if interaction_ready else ACCENT2),
            )
            vital_labels["voice"].config(text=voice_status)

            last_cmd = daemon_status.get("last_voice_command", {})
            if last_cmd:
                cmd_display = f"{last_cmd.get('command','?')} {last_cmd.get('time','')}"
                vital_labels["lastcmd"].config(text=cmd_display, fg="#f472b6")
            else:
                vital_labels["lastcmd"].config(text="--", fg=ACCENT2)

            # QAO mini-panel
            qao_rt  = data.get("qao_runtime", {})
            qao_ics = qao_rt.get("issue_counts", {})
            for key, lbl in qao_issue_labels.items():
                cnt   = qao_ics.get(key, 0)
                color = "#ef4444" if cnt > 300 else ("#f59e0b" if cnt > 100 else ACCENT2)
                lbl.config(text=str(cnt), fg=color)
            gc   = qao_rt.get("gate_confidence", "?")
            ac   = qao_rt.get("advisory_confidence", "?")
            gc_s = f"{gc:.2f}" if isinstance(gc, float) else str(gc)
            ac_s = f"{ac:.2f}" if isinstance(ac, float) else str(ac)
            qao_conf_lbl.config(text=f"gate:{gc_s}  adv:{ac_s}")

            # 5-Axis health
            fp_recs = fail_points.get("records", {})
            for ax_key, dims in AXIS_HEALTH_DIMS.items():
                masteries = []
                for dim in dims:
                    rec    = fp_recs.get(dim, {})
                    recent = rec.get("recent", [])
                    if recent:
                        masteries.append(max(0.0, 1.0 - sum(recent) / len(recent)))
                    else:
                        masteries.append(0.5)  # no data = unknown, not 100%
                pct = sum(masteries) / len(masteries) if masteries else 0.5
                filled  = int(pct * 10)
                bar_str = chr(0x2588) * filled + chr(0x2591) * (10 - filled)
                color   = "#22c55e" if pct >= 0.7 else ("#f59e0b" if pct >= 0.45 else "#ef4444")
                bar_lbl, pct_lbl = axis_health_labels[ax_key]
                bar_lbl.config(text=bar_str, fg=color)
                pct_lbl.config(text=f"{pct*100:.0f}%", fg=color)

            # Fail trends
            fail_tr = data.get("fail_trends", {})
            for dim, lbl in trend_labels.items():
                arrow = fail_tr.get(dim, "?")
                color = "#22c55e" if arrow == "up" else ("#ef4444" if arrow == "down" else TEXT_DIM)
                # Use actual arrows when available
                if arrow == chr(0x2191):
                    color = "#22c55e"
                elif arrow == chr(0x2193):
                    color = "#ef4444"
                lbl.config(text=arrow, fg=color)

            # Corpus + Sensor
            cp = data.get("corpus_progress", {})
            corpus_info_labels["pass"].config(text=str(cp.get("pass", "--")))
            corpus_info_labels["msg"].config(
                text=f"{cp.get('messages_processed', '--')} / {cp.get('total_messages', '--')}")

            snaps = data.get("responder_snaps", [])
            if len(snaps) >= 2:
                delta  = snaps[-1] - snaps[0]
                arr    = chr(0x2191) if delta > 0.005 else (chr(0x2193) if delta < -0.005 else "->")
                color  = "#22c55e" if delta > 0 else ("#ef4444" if delta < -0.005 else TEXT_DIM)
                snap_s = f"{snaps[-1]:.4f} ({arr}{abs(delta):.4f})"
                corpus_info_labels["score"].config(text=snap_s, fg=color)
            elif snaps:
                corpus_info_labels["score"].config(text=f"{snaps[-1]:.4f}")

            stall_ev = data.get("stall_events", [])
            if isinstance(stall_ev, dict):
                stall_ev = stall_ev.get("events", [])
            if stall_ev:
                last    = stall_ev[-1]
                ts_val  = str(last.get("timestamp", "?"))[:16]
                dims    = last.get("stuck_dims", last.get("dims", "?"))
                corpus_info_labels["stall"].config(text=ts_val)
                corpus_info_labels["stall_dim"].config(text=str(dims)[:28])
            else:
                corpus_info_labels["stall"].config(text="none")
                corpus_info_labels["stall_dim"].config(text="--")

            exp = data.get("exploration_log", {})
            if exp:
                exp_ts = str(exp.get("timestamp", "?"))[:16]
                corpus_info_labels["sensor_ts"].config(text=exp_ts)
                # top_dims_fired / axis_summary may be pre-computed OR need
                # deriving from per-exchange session_log
                top_dims = exp.get("top_dims_fired", [])
                ax_sum   = exp.get("axis_summary", {})
                if not top_dims or not ax_sum:
                    try:
                        from collections import Counter as _Counter
                        _sl = exp.get("session_log") or []
                        _dim_counts: _Counter = _Counter()
                        _ax_counts:  _Counter = _Counter()
                        for _ex in _sl:
                            for _d in (_ex.get("dims_fired") or []):
                                _dim_counts[str(_d)] += 1
                            for _ax, _cnt in (_ex.get("qao_spread") or {}).items():
                                _ax_counts[str(_ax)] += int(_cnt or 0)
                        if not top_dims:
                            top_dims = _dim_counts.most_common(5)
                        if not ax_sum:
                            ax_sum = {k: [(k, v)] for k, v in _ax_counts.items()}
                    except Exception:
                        pass
                top_dim = top_dims[0][0] if top_dims else "--"
                corpus_info_labels["sensor_top"].config(text=top_dim[:24])
                noisy = max(ax_sum.items(),
                            key=lambda kv: sum(c for _, c in kv[1]),
                            default=("--", []))[0] if ax_sum else "--"
                corpus_info_labels["diag_ax"].config(text=noisy)
            else:
                corpus_info_labels["sensor_ts"].config(text="no run yet")
                corpus_info_labels["sensor_top"].config(text="--")
                corpus_info_labels["diag_ax"].config(text="--")

            # Log
            _update_log(log_lines)
            _update_surface_log(data.get("surface_log_lines", []))

        except Exception as e:
            _update_log([f"[hub error] {e}"])

        root.after(REFRESH_MS, refresh_overview)

    def refresh_qao():
        try:
            data = reader.read_all()
            qao_rt  = data.get("qao_runtime", {})
            qao_ics = qao_rt.get("issue_counts", {})

            # Header gauges
            gc  = qao_rt.get("gate_confidence", "--")
            ac  = qao_rt.get("advisory_confidence", "--")
            qao_gate_lbl.config(
                text=f"{gc:.3f}" if isinstance(gc, float) else str(gc),
                fg=ACCENT2 if isinstance(gc, float) else "#f59e0b")
            qao_adv_lbl.config(
                text=f"{ac:.3f}" if isinstance(ac, float) else str(ac),
                fg=ACCENT2 if isinstance(ac, float) else "#f59e0b")

            total_issues = sum(qao_ics.values()) if qao_ics else 0
            qao_issues_lbl.config(
                text=str(total_issues) if total_issues else "RESET",
                fg=ACCENT2 if total_issues else "#f59e0b")

            journal_path = _STATE_DIR / "quasiarch_observer" / "journal.jsonl"
            if journal_path.exists():
                # Approximate entry count from file size / avg line length
                fsize = journal_path.stat().st_size
                approx = fsize // 120   # rough avg bytes per JSON line
                qao_journal_lbl.config(text=f"~{approx:,}")
            else:
                qao_journal_lbl.config(text="--")

            qao_nodes_lbl.config(text=str(data.get("qao_node_count", "--")))
            qao_edges_lbl.config(text=str(data.get("qao_edge_count", "--")))

            # Issue heatmap
            max_count = max(qao_ics.values(), default=1) or 1
            axis_tallies: Dict[str, int] = {ax: 0 for ax in AXIS_COLORS}

            for issue_key, row_widgets in heatmap_rows.items():
                cnt   = qao_ics.get(issue_key, 0)
                color = row_widgets["color"]
                axis  = QAO_AXIS_MAP.get(issue_key, "X")
                axis_tallies[axis] = axis_tallies.get(axis, 0) + cnt

                # Bar (max 10 chars)
                filled  = int(round(cnt / max_count * 10))
                bar_str = chr(0x2588) * filled + " " * (10 - filled)
                row_widgets["bar"].config(text=bar_str, fg=color)
                row_widgets["cnt"].config(text=str(cnt))

                # Trend arrow vs previous
                prev = _qao_prev_counts.get(issue_key, cnt)
                if cnt > prev + 2:
                    arr, arr_col = chr(0x2191), "#ef4444"
                elif cnt < prev - 2:
                    arr, arr_col = chr(0x2193), "#22c55e"
                else:
                    arr, arr_col = "->", TEXT_DIM
                row_widgets["arr"].config(text=arr, fg=arr_col)
                _qao_prev_counts[issue_key] = cnt

            # Axis pie (text)
            pie_parts = []
            for ax in ["X", "T", "N", "B", "A"]:
                pie_parts.append(f"{ax}:{axis_tallies.get(ax, 0)}")
            axis_pie_lbl.config(text="  ".join(pie_parts))

            # Journal feed
            entries = data.get("qao_journal_recent", [])
            if not entries and not qao_rt:
                # QAO was reset — show reset marker info
                reset_marker = _STATE_DIR / "quasiarch_observer" / ".reset_marker"
                journal_feed.configure(state=tk.NORMAL)
                journal_feed.delete("1.0", tk.END)
                if reset_marker.exists():
                    try:
                        info = reset_marker.read_text().strip()
                        journal_feed.insert(tk.END,
                            "QAO was reset — rebuilding from fresh state.\n\n"
                            f"{info}\n\n"
                            "The QAO re-populates automatically as Aurora processes\n"
                            "new interactions. Issue counts will appear here once\n"
                            "the observer writes its first journal entries.\n",
                            "default_j")
                    except Exception:
                        journal_feed.insert(tk.END,
                            "QAO observer directory is empty.\n"
                            "Will populate on next aurora daemon cycle.\n",
                            "default_j")
                else:
                    journal_feed.insert(tk.END,
                        "QAO not yet initialized.\n"
                        "Start the daemon to boot the observer.\n",
                        "default_j")
                journal_feed.configure(state=tk.DISABLED)
            else:
                _update_journal_feed(entries)

            # Stats footer
            nc = data.get("qao_node_count", "--")
            ec = data.get("qao_edge_count", "--")
            relics_path = _STATE_DIR / "quasiarch_observer" / "relics"
            rc = reader._count_dir(relics_path)
            qao_stats_lbl.config(
                text=f"nodes:{nc}  edges:{ec}  relics:{rc}  "
                     f"journal entries:~{approx:,}" if journal_path.exists()
                     else f"nodes:{nc}  edges:{ec}  relics:{rc}"
            )

        except Exception:
            pass

        root.after(REFRESH_QAO_MS, refresh_qao)

    def refresh_vision():
        try:
            data = reader.read_all()
            frames = data.get("screen_frames", [])
            surface_status = data.get("surface_status", {}) or {}
            surface_snapshot = data.get("surface_snapshot", {}) or {}
            subsurface_projection = data.get("subsurface_projection", {}) or {}
            subsurface_status = data.get("subsurface_status", {}) or {}
            camera_allowed = sensory_camera_enabled(_STATE_DIR)
            _update_camera_btn()
            present_sensory = dict(surface_status.get("present_sensory_perspective") or {})
            recognitions = dict(present_sensory.get("recognitions") or {})
            live_recognitions = [
                str(item).strip()
                for item in list(recognitions.get("recent") or [])
                if str(item).strip()
            ]
            if not live_recognitions:
                last_matches = dict(recognitions.get("last_matches") or {})
                for lane_name in ("audio", "visual", "semantic"):
                    lane = dict(last_matches.get(lane_name) or {})
                    for key, value in lane.items():
                        if value:
                            live_recognitions.append(f"{lane_name}:{key}")
                for item in list(subsurface_status.get("subsurface_sensory_recent") or []):
                    item_s = str(item).strip()
                    if item_s and item_s not in live_recognitions:
                        live_recognitions.append(item_s)
            live_recognitions = live_recognitions[:4]
            live_visual_description = str(present_sensory.get("visual_description", "") or "").strip()
            live_visual_question = str(present_sensory.get("pending_visual_question", "") or "").strip()
            live_guidance_summary = str(
                present_sensory.get("guidance_summary", "")
                or dict(present_sensory.get("latest_guidance") or {}).get("summary", "")
                or ""
            ).strip()
            sc = reader.read_sensory_crystal() or {}
            vis_state = dict(sc.get("visual", {}) or {})
            semantic_nodes = int(sc.get("semantic_nodes", 0) or 0)
            total_frames = int(sc.get("total_frames", 0) or 0)

            # Status bar
            screen_dir = _STATE_DIR / "vision_seeds" / "screen"
            frame_count = len(list(screen_dir.glob("*.png"))) if screen_dir.exists() else 0
            cam_frame = _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png"
            sight_frame = _STATE_DIR / "vision_snapshots" / "sight_latest.jpg"
            live_frame = None
            if camera_allowed:
                live_frame = cam_frame if cam_frame.exists() else sight_frame if sight_frame.exists() else None

            if frames:
                last_mtime = frames[0]["mtime"]
                last_ts_str = time.strftime("%H:%M:%S", time.localtime(last_mtime))
            else:
                last_ts_str = "--"

            if not camera_allowed:
                vis_run_lbl.config(
                    text="Surface feed: camera off",
                    fg="#f97316",
                )
                vis_frames_lbl.config(text=f"frames:{frame_count}  crystal:{total_frames}")
                vis_lastcap_lbl.config(text=f"last:{last_ts_str}")
            elif live_frame is not None:
                frame_age = max(0.0, time.time() - live_frame.stat().st_mtime)
                vis_run_lbl.config(
                    text="Surface feed: live" if frame_age < 10.0 else f"Surface feed: stale {int(frame_age)}s",
                    fg=ACCENT2 if frame_age < 10.0 else "#f59e0b",
                )
                vis_frames_lbl.config(text=f"frames:{frame_count}  crystal:{total_frames}")
                vis_lastcap_lbl.config(text=f"last:{time.strftime('%H:%M:%S', time.localtime(live_frame.stat().st_mtime))}")
            else:
                vis_run_lbl.config(
                    text="Surface feed: no frames",
                    fg=TEXT_DIM,
                )
                vis_frames_lbl.config(text=f"frames:{frame_count}  crystal:{total_frames}")
                vis_lastcap_lbl.config(text=f"last:{last_ts_str}")

            # ── "WHAT I SEE" — display Aurora's own module output ──
            try:
                _vis_lines = []
                if live_visual_description:
                    _vis_lines.append(live_visual_description)
                if live_visual_question:
                    _vis_lines.append(f"Question: {live_visual_question}")
                _vis_recs = [r for r in live_recognitions if "saw" in r.lower() or "visual" in r.lower() or "cross-modal" in r.lower()]
                if _vis_recs:
                    _vis_lines.extend(_vis_recs)
                _sub_proj = subsurface_projection
                _sensory_sum = str(_sub_proj.get("sensory_summary", "") or "").strip()
                if _sensory_sum:
                    _vis_lines.append(_sensory_sum)
                _snap_sum = str(surface_snapshot.get("summary", "") or "").strip()
                if _snap_sum:
                    _vis_lines.append(_snap_sum)
                if live_guidance_summary:
                    _vis_lines.append(live_guidance_summary)
                _deduped = []
                for _line in _vis_lines:
                    _line_s = str(_line).strip()
                    if _line_s and _line_s not in _deduped:
                        _deduped.append(_line_s)
                vis_perception_lbl.config(text="\n".join(_deduped) if _deduped else "No visual perception yet.")
            except Exception:
                pass

            # Live frame image — camera first, screen fallback
            try:
                from PIL import Image as _PILImage, ImageTk as _PILImageTk
                latest_png = None
                _cam_source = "SCREEN"

                # 1. Prefer camera frame only if it is recent (< 30 s)
                if camera_allowed and cam_frame.exists():
                    cam_age = time.time() - cam_frame.stat().st_mtime
                    if cam_age < 30.0:
                        latest_png = cam_frame
                        _cam_source = "CAMERA" if cam_age < 10.0 else f"CAMERA (stale {int(cam_age)}s)"
                if latest_png is None and camera_allowed and sight_frame.exists():
                    snap_age = time.time() - sight_frame.stat().st_mtime
                    if snap_age < 30.0:
                        latest_png = sight_frame
                        _cam_source = "SURFACE SNAP" if snap_age < 10.0 else f"SURFACE SNAP ({int(snap_age)}s)"

                # 2. Fall back to screen capture frames (ScreenObserver output)
                if latest_png is None:
                    screen_dir_path = _STATE_DIR / "vision_seeds" / "screen"
                    pngs = sorted(screen_dir_path.glob("*.png"),
                                  key=lambda p: p.stat().st_mtime, reverse=True)
                    if pngs:
                        latest_png = pngs[0]
                        _cam_source = "SCREEN"

                # 3. Last resort: show the camera file even if stale, so there's
                #    something on screen rather than a blank placeholder.
                if latest_png is None and camera_allowed:
                    for _stale_cand in (cam_frame, sight_frame):
                        if _stale_cand.exists():
                            _stale_age = time.time() - _stale_cand.stat().st_mtime
                            latest_png = _stale_cand
                            _cam_source = f"STALE ({int(_stale_age//60)}m old)"
                            break

                if latest_png is not None:
                    img = _PILImage.open(latest_png)
                    # Fit to 480×270 while preserving aspect ratio
                    img.thumbnail((480, 270), _PILImage.LANCZOS)
                    photo = _PILImageTk.PhotoImage(img)
                    _vis_img_ref["photo"] = photo   # keep reference
                    vis_img_lbl.config(image=photo, text="", bg=BG_PANEL)
                    mtime = latest_png.stat().st_mtime
                    ts_s = time.strftime("%H:%M:%S", time.localtime(mtime))
                    vis_frame_ts_lbl.config(text=f"[{_cam_source}]  {latest_png.name}  captured {ts_s}")
                else:
                    vis_img_lbl.config(image="", text="Camera disabled" if not camera_allowed else "No frames captured yet",
                                       fg=TEXT_DIM, font=("Courier New", 8))
                    vis_frame_ts_lbl.config(text="CAMERA OFF" if not camera_allowed else "NO SIGNAL")
            except Exception:
                pass

            # Scene log from frame mtimes (derive scene info from filenames + size)
            scene_log_box.configure(state=tk.NORMAL)
            scene_log_box.delete("1.0", tk.END)

            # Try to read scene log from screen_observer state file if present
            obs_state = _STATE_DIR / "screen_observer_log.json"
            scene_entries: List[Dict] = []
            if obs_state.exists():
                try:
                    raw = obs_state.read_text()
                    scene_entries = json.loads(raw)
                    if not isinstance(scene_entries, list):
                        scene_entries = []
                except Exception:
                    # File may be truncated mid-write — recover valid entries
                    # Strategy 1: find complete {...} blobs handling nested [] arrays
                    try:
                        import re as _re2
                        scene_entries = []
                        # Match outermost { } accounting for nested arrays/objects
                        depth = 0
                        start = None
                        for i, ch in enumerate(raw):
                            if ch == '{':
                                if depth == 0:
                                    start = i
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0 and start is not None:
                                    try:
                                        scene_entries.append(json.loads(raw[start:i+1]))
                                    except Exception:
                                        pass
                                    start = None
                    except Exception:
                        pass
                    # Strategy 2: if still empty, regex-extract key fields from partial text
                    if not scene_entries and obs_state.exists():
                        try:
                            import re as _re3
                            partial: Dict[str, Any] = {}
                            for _fld, _pat in [
                                ("timestamp",       r'"timestamp":\s*([\d.]+)'),
                                ("brightness",      r'"brightness":\s*([\d.]+)'),
                                ("edge_density",    r'"edge_density":\s*([\d.]+)'),
                                ("saturation",      r'"saturation":\s*([\d.]+)'),
                                ("motion",          r'"motion(?:_magnitude)?":\s*([\d.]+)'),
                                ("scene_type",      r'"scene_type":\s*"([^"]+)"'),
                            ]:
                                m = _re3.search(_pat, raw)
                                if m:
                                    v = m.group(1)
                                    partial[_fld] = float(v) if _fld != "scene_type" else v
                            if "brightness" in partial:
                                scene_entries = [partial]
                        except Exception:
                            scene_entries = []

            if not scene_entries:
                cam_candidates = [
                    _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png",
                    _STATE_DIR / "vision_snapshots" / "sight_latest.jpg",
                ]
                latest_cam = next((path for path in cam_candidates if path.exists()), None)
                if latest_cam is not None:
                    try:
                        mtime = latest_cam.stat().st_mtime
                        age = max(0.0, time.time() - mtime)
                        scene_entries = [{
                            "timestamp": mtime,
                            "scene_type": "camera_live" if age < 10.0 else "camera_snapshot",
                            "brightness": 0.0,
                            "edge_density": 0.0,
                            "motion": 0.0,
                            "concepts": list(live_recognitions or []),
                            "source": latest_cam.name,
                            "camera_live": age < 10.0,
                        }]
                    except Exception:
                        scene_entries = []

            if not scene_entries:
                try:
                    present = dict(surface_status.get("present_sensory_perspective") or {})
                    snap_recognitions = dict(present.get("recognitions") or {})
                    recent = [
                        str(item).strip()
                        for item in list(snap_recognitions.get("recent") or [])
                        if str(item).strip()
                    ]
                    snap_ts = float(surface_snapshot.get("updated_at", 0.0) or 0.0)
                    if snap_ts > 0.0:
                        scene_entries = [{
                            "timestamp": snap_ts,
                            "scene_type": "surface_live" if present.get("camera_live") else "surface_audio_only",
                            "brightness": 0.0,
                            "edge_density": 0.0,
                            "motion": 0.0,
                            "concepts_matched": recent,
                            "concepts": recent,
                            "summary": str(surface_snapshot.get("summary", "") or present.get("summary", "") or ""),
                            "camera_live": bool(present.get("camera_live", False)),
                            "mic_live": bool(present.get("mic_live", False)),
                            "trigger": str(surface_snapshot.get("trigger", "") or ""),
                        }]
                except Exception:
                    scene_entries = []

            if scene_entries:
                for obs in scene_entries[-15:]:
                    ts_val   = obs.get("timestamp", 0)
                    ts_str   = time.strftime("%H:%M:%S", time.localtime(ts_val)) if ts_val else "--"
                    stype    = obs.get("scene_type", "unknown")
                    bright   = obs.get("brightness", 0.0)
                    edge     = obs.get("edge_density", 0.0)
                    motion   = obs.get("motion", obs.get("motion_magnitude", 0.0))
                    concepts = obs.get("concepts_matched", [])
                    if concepts:
                        c_str = f"concepts:{concepts[:2]}"
                    elif live_recognitions:
                        c_str = f"recognitions:{live_recognitions[:2]}"
                    else:
                        c_str = ""
                    summary = str(obs.get("summary", "") or "").strip()
                    line = (f"[{ts_str}] scene={stype:<11}  "
                            f"bright={bright:.2f}  edge={edge:.2f}  "
                            f"motion={motion:.2f}  {c_str}\n")
                    tag = stype if stype in ("text_heavy", "image_rich", "terminal", "idle", "active") else "default_sl"
                    scene_log_box.insert(tk.END, line, tag)
                    if summary:
                        scene_log_box.insert(tk.END, f"           {summary[:140]}\n", "dim")
            else:
                # Fall back: list files with timestamps
                for frm in reversed(frames[:15]):
                    ts_str = time.strftime("%H:%M:%S", time.localtime(frm["mtime"]))
                    size_kb = frm["size"] // 1024
                    fname   = os.path.basename(frm["path"])
                    line    = f"[{ts_str}] {fname}  ({size_kb} KB)\n"
                    scene_log_box.insert(tk.END, line, "default_sl")

                if not frames:
                    scene_log_box.insert(tk.END,
                        "No screen frames found.\n"
                        "Start observer with: systems['screen_observer'] = boot_screen_observer(systems)\n",
                        "idle")

            scene_log_box.see(tk.END)
            scene_log_box.configure(state=tk.DISABLED)

            # Current scene info -- from latest frame entry
            if scene_entries:
                latest = scene_entries[-1]
                scene_info_labels["scene_type"].config(text=latest.get("scene_type", "--"))
                scene_info_labels["brightness"].config(text=f"{latest.get('brightness', 0):.3f}")
                scene_info_labels["edge_density"].config(text=f"{latest.get('edge_density', 0):.3f}")
                m_val = latest.get("motion", latest.get("motion_magnitude", 0))
                scene_info_labels["motion"].config(text=f"{m_val:.3f}")
                concepts = latest.get("concepts_matched", [])
                scene_info_labels["concepts"].config(
                    text=str(concepts[:2]) if concepts else (", ".join(live_recognitions[:2]) if live_recognitions else "none")
                )
            elif frames:
                scene_info_labels["scene_type"].config(text="unknown")
                scene_info_labels["brightness"].config(text="--")
                scene_info_labels["edge_density"].config(text="--")
                scene_info_labels["motion"].config(text="--")
                scene_info_labels["concepts"].config(text=", ".join(live_recognitions[:2]) if live_recognitions else "--")

            def _facet_text(name: str) -> str:
                fd = dict(vis_state.get(name, {}) or {})
                return f"{fd.get('nodes', 0)} ({fd.get('promoted', 0)}↑)\nm={float(fd.get('maturity', 0.0) or 0.0):.2f}"

            vis_crystal_labels["hue"].config(text=_facet_text("hue"))
            vis_crystal_labels["shape"].config(text=_facet_text("shape"))
            vis_crystal_labels["motion"].config(text=_facet_text("motion"))
            vis_crystal_labels["semantic"].config(text=str(semantic_nodes))
            vis_crystal_labels["frames"].config(text=str(total_frames))

            vis_rec_box.configure(state=tk.NORMAL)
            vis_rec_box.delete("1.0", tk.END)
            _rec_lines: List[tuple[str, str]] = []
            for item in live_recognitions:
                item_s = str(item).strip()
                if not item_s:
                    continue
                tag = "semantic"
                low = item_s.lower()
                if low.startswith("visual:"):
                    tag = "visual"
                elif low.startswith("audio:"):
                    tag = "audio"
                _rec_lines.append((f"{item_s}\n", tag))
            for lane_name, lane in dict(recognitions.get("last_matches") or {}).items():
                lane_d = dict(lane or {})
                for key, value in lane_d.items():
                    if not value:
                        continue
                    tag = "visual" if lane_name == "visual" else "audio" if lane_name == "audio" else "semantic"
                    _rec_lines.append((f"{lane_name}:{key} -> {value}\n", tag))
            if not _rec_lines:
                _rec_lines.append(("No live recognitions yet.\n", "dim"))
            for line, tag in _rec_lines[:12]:
                vis_rec_box.insert(tk.END, line, tag)
            vis_rec_box.configure(state=tk.DISABLED)

            # Vision index stats
            vi_path = _STATE_DIR / "vision_index.json"
            clusters_n = "--"
            vectors_n  = "--"
            oets_bound = "--"
            _vi_clusters: Dict = {}
            if vi_path.exists():
                try:
                    vi = json.loads(vi_path.read_text())
                    _vi_clusters = vi.get("clusters", {})
                    clusters_n = len(_vi_clusters)
                    vectors_n  = vi.get("vector_count", len(vi.get("vectors", vi.get("feature_vectors", {}))))
                    oets_bound = sum(1 for c in _vi_clusters.values() if c.get("oets_bound"))
                except Exception:
                    pass

            # Sensory crystal visual facets
            _sc_hue_n = _sc_shape_n = _sc_motion_n = "--"
            _sc_hue_m = _sc_shape_m = _sc_motion_m = "--"
            _sc_total = "--"
            _sc_path = _STATE_DIR / "sensory_crystal_state.json"
            if _sc_path.exists():
                try:
                    _sc = json.loads(_sc_path.read_text())
                    _vis = _sc.get("visual", {})
                    _sc_hue_n    = _vis.get("hue",    {}).get("nodes", "--")
                    _sc_hue_m    = _vis.get("hue",    {}).get("maturity", 0)
                    _sc_shape_n  = _vis.get("shape",  {}).get("nodes", "--")
                    _sc_shape_m  = _vis.get("shape",  {}).get("maturity", 0)
                    _sc_motion_n = _vis.get("motion", {}).get("nodes", "--")
                    _sc_motion_m = _vis.get("motion", {}).get("maturity", 0)
                    _sc_total    = _sc.get("total_frames", "--")
                except Exception:
                    pass

            screen_count = frame_count
            vis_idx_lbl.config(
                text=(f"clusters:{clusters_n}  vectors:{vectors_n}  oets_bound:{oets_bound}"
                      f"  screen_dir files:{screen_count}  crystal_frames:{_sc_total}"
                      f"  hue:{_sc_hue_n}(m={_sc_hue_m:.2f})  shape:{_sc_shape_n}(m={_sc_shape_m:.2f})"
                      f"  motion:{_sc_motion_n}(m={_sc_motion_m:.2f})"
                      if isinstance(_sc_hue_m, float) else
                      f"clusters:{clusters_n}  vectors:{vectors_n}  oets_bound:{oets_bound}"
                      f"  screen_dir files:{screen_count}")
            )

            # Observer telemetry — pull vision/screen/observer/imager lines from daemon log
            _VIS_TAGS = ("[VISION]", "[SCREEN]", "[OBSERVER]", "[QAO]", "[SAVE]", "[IMAGER]")
            _VIS_STYLES = {
                "[VISION]":   "vision",
                "[SCREEN]":   "screen",
                "[OBSERVER]": "screen",
                "[QAO]":      "active",
                "[IMAGER]":   "active",
                "[SAVE]":     "dim",
            }
            try:
                vis_telem_box.configure(state=tk.NORMAL)
                vis_telem_box.delete("1.0", tk.END)
                if live_visual_description:
                    vis_telem_box.insert(tk.END, f"[live-camera] {live_visual_description}\n", "vision")
                if live_visual_question:
                    vis_telem_box.insert(tk.END, f"[clarify] {live_visual_question}\n", "active")
                if live_guidance_summary:
                    vis_telem_box.insert(tk.END, f"[guidance] {live_guidance_summary}\n", "dim")
                log_lines = reader._read_surface_log(500)
                telem_lines = [
                    l for l in log_lines
                    if any(t in l for t in _VIS_TAGS) or "Surface camera" in l or "Surface hardware" in l or "Surface sensory" in l
                ]
                if telem_lines:
                    for line in telem_lines[-40:]:
                        style = "dim"
                        for tag, s in _VIS_STYLES.items():
                            if tag in line:
                                style = s
                                break
                        if "Surface camera" in line or "Surface hardware" in line or "Surface sensory" in line:
                            style = "vision"
                        vis_telem_box.insert(tk.END, line.rstrip() + "\n", style)
                    vis_telem_box.see(tk.END)
                else:
                    # No daemon log vision lines — show what we know from state files
                    if scene_entries:
                        latest = scene_entries[-1]
                        ts_v = float(latest.get("timestamp", 0))
                        ts_s = time.strftime("%H:%M:%S", time.localtime(ts_v)) if ts_v else "--"
                        vis_telem_box.insert(tk.END,
                            f"[{ts_s}] Last observation: "
                            f"scene={latest.get('scene_type','?')}  "
                            f"brightness={latest.get('brightness',0):.3f}  "
                            f"edge={latest.get('edge_density',0):.3f}\n", "screen")
                    # Show vision_index cluster labels
                    if _vi_clusters:
                        vis_telem_box.insert(tk.END, "── Vision Index Clusters ──\n", "dim")
                        for cid, cdata in list(_vi_clusters.items())[:12]:
                            label   = cdata.get("concept_label", cid)
                            members = len(cdata.get("members", []))
                            conf    = cdata.get("confidence", 0)
                            bound   = "✓" if cdata.get("oets_bound") else " "
                            vis_telem_box.insert(tk.END,
                                f"  [{bound}] {label:<40}  members:{members}  conf:{conf:.2f}\n",
                                "vision")
                    # Sensory crystal visual summary
                    if isinstance(_sc_hue_m, float):
                        vis_telem_box.insert(tk.END,
                            f"\n── Sensory Crystal Visual Facets ──\n"
                            f"  hue   : {_sc_hue_n} nodes  maturity={_sc_hue_m:.3f}\n"
                            f"  shape : {_sc_shape_n} nodes  maturity={_sc_shape_m:.3f}\n"
                            f"  motion: {_sc_motion_n} nodes  maturity={_sc_motion_m:.3f}\n"
                            f"  total frames ingested: {_sc_total}\n",
                            "screen")
                    vis_telem_box.insert(tk.END,
                        f"\nScreen frames captured: {frame_count}  "
                        f"Daemon log vision tags appear here when active.\n",
                        "dim")
                vis_telem_box.configure(state=tk.DISABLED)
            except Exception:
                pass

        except Exception:
            pass

        root.after(REFRESH_VISION_MS, refresh_vision)

    def refresh_audio():
        try:
            data = reader.read_all()
            surface_status = data.get("surface_status", {}) or {}
            surface_snapshot = data.get("surface_snapshot", {}) or {}
            subsurface_projection = data.get("subsurface_projection", {}) or {}
            present_sensory = dict(surface_status.get("present_sensory_perspective") or {})
            recognitions = dict(present_sensory.get("recognitions") or {})
            live_recognitions = [
                str(item).strip()
                for item in list(recognitions.get("recent") or [])
                if str(item).strip()
            ][:8]
            live_audio_description = str(present_sensory.get("audio_description", "") or "").strip()
            live_recent_speech = str(present_sensory.get("recent_speech", "") or "").strip()
            live_guidance_summary = str(
                present_sensory.get("guidance_summary", "")
                or dict(present_sensory.get("latest_guidance") or {}).get("summary", "")
                or ""
            ).strip()
            # ── Mic always-on listener status ────────────────────────────────
            try:
                _sf = _STATE_DIR / "daemon_status.json"
                _sf_age = (time.time() - _sf.stat().st_mtime) if _sf.exists() else 9999
                # Daemon writes status every 60s — if file is >70s old, daemon is down
                _daemon_alive = _sf.exists() and _sf_age < 70
                if not _daemon_alive:
                    aud_mic_lbl.config(text="● DAEMON DOWN", fg=TEXT_DIM)
                else:
                    _ds = reader.read_all().get("daemon_status") or {}
                    _mic_on = _ds.get("sensory_mic_active", False)
                    if _mic_on:
                        aud_mic_lbl.config(text="● MIC LIVE", fg="#4ade80")
                    else:
                        aud_mic_lbl.config(text="● MIC OFF", fg="#f97316")
            except Exception:
                pass

            # ── "WHAT I HEAR" — display Aurora's own module output ──
            try:
                _aud_lines = []
                if live_audio_description:
                    _aud_lines.append(live_audio_description)
                if live_recent_speech:
                    _aud_lines.append(f"Speech: {live_recent_speech}")
                _aud_recs = [r for r in live_recognitions if "heard" in r.lower() or "audio" in r.lower() or "cross-modal" in r.lower()]
                if _aud_recs:
                    _aud_lines.extend(_aud_recs)
                _sub_proj_a = subsurface_projection
                _sensory_sum_a = str(_sub_proj_a.get("sensory_summary", "") or "").strip()
                if _sensory_sum_a:
                    _aud_lines.append(_sensory_sum_a)
                _psp = surface_snapshot.get("present_sensory_perspective", {}) or present_sensory
                _psp_sum = str(_psp.get("summary", "") or "").strip()
                if _psp_sum:
                    _aud_lines.append(_psp_sum)
                _surf_guide = str(surface_status.get("surface_guidance", "") or live_guidance_summary or "").strip()
                if _surf_guide:
                    _aud_lines.append(_surf_guide)
                _deduped = []
                for _line in _aud_lines:
                    _line_s = str(_line).strip()
                    if _line_s and _line_s not in _deduped:
                        _deduped.append(_line_s)
                aud_perception_lbl.config(text="\n".join(_deduped) if _deduped else "No audio perception yet.")
            except Exception:
                pass

            # ── Live ambient audio ────────────────────────────────────────
            try:
                _lap = _STATE_DIR / "ambient_audio_latest.json"
                if _lap.exists():
                    _la_age = time.time() - _lap.stat().st_mtime
                    _la = json.loads(_lap.read_text())
                    _ts_s = time.strftime("%H:%M:%S", time.localtime(_la.get("ts", 0)))
                    _age_s = f"  {int(_la_age)}s ago" if _la_age > 5 else ""
                    _live_ts_lbl.config(text=f"updated {_ts_s}{_age_s}")

                    # RMS bar (0…-60 dB mapped to 0…320px)
                    _rms_db = float(_la.get("rms_db", -60))
                    _bar_w  = max(2, int((_rms_db + 60) / 60 * 320))
                    _bar_col = ("#4ade80" if _rms_db > -20 else
                                "#facc15" if _rms_db > -40 else "#475569")
                    _rms_bar_canvas.delete("all")
                    _rms_bar_canvas.create_rectangle(0, 0, _bar_w, 14,
                                                     fill=_bar_col, outline="")
                    _rms_val_lbl.config(text=f"{_rms_db:.1f}dB", fg=_bar_col)

                    _act = _la.get("activity", "--")
                    _act_col = ("#4ade80" if _act == "speech" else
                                "#facc15" if _act == "active" else TEXT_DIM)
                    _act_lbl.config(text=_act.upper(), fg=_act_col)

                    for _fk, _flbl in _spec_fields.items():
                        _v = _la.get(_fk)
                        if _v is not None:
                            _flbl.config(text=f"{_v:.3f}" if _fk != "fps" else f"{_v:.1f}/s")
                else:
                    _live_ts_lbl.config(text="no data yet")
            except Exception:
                pass

            sc = reader.read_sensory_crystal()
            if sc:
                mat = sc.get("maturity", 0.0)
                frm = sc.get("total_frames", 0)
                aud_status_lbl.config(text=f"Sensory Crystal: active")
                aud_frames_lbl.config(text=f"frames:{frm}")
                aud_maturity_lbl.config(text=f"crystal maturity:{mat:.3f}")

                # ── Bar chart: audio facets ───────────────────────────────
                try:
                    _ensure_matplotlib_available()
                    import matplotlib
                    matplotlib.use("TkAgg")
                    import matplotlib.pyplot as _plt
                    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                    audio_data = sc.get("audio", {})
                    facet_names = list(audio_data.keys())
                    maturities  = [audio_data[f].get("maturity", 0.0) for f in facet_names]
                    nodes       = [audio_data[f].get("nodes", 0) for f in facet_names]
                    promoted    = [audio_data[f].get("promoted", 0) for f in facet_names]

                    if _aud_fig_ref["canvas"] is not None:
                        try:
                            _aud_fig_ref["canvas"].get_tk_widget().destroy()
                        except Exception:
                            pass
                    if _aud_fig_ref["fig"] is not None:
                        try:
                            _plt.close(_aud_fig_ref["fig"])
                        except Exception:
                            pass

                    fig, axes = _plt.subplots(1, 2, figsize=(8, 2.2), facecolor=BG_PANEL)
                    x = range(len(facet_names))

                    # Left: maturity per facet
                    axes[0].bar(x, maturities, color=CHART_FG, width=0.5)
                    axes[0].set_xticks(list(x))
                    axes[0].set_xticklabels(facet_names, color=TEXT, fontsize=7)
                    axes[0].set_ylim(0, 1.0)
                    axes[0].set_title("Facet Maturity", color=ACCENT, fontsize=8)
                    axes[0].set_facecolor(BG_PANEL)
                    axes[0].tick_params(colors=TEXT_DIM)
                    for spine in axes[0].spines.values():
                        spine.set_edgecolor(CHART_GRID)

                    # Right: node count (total / promoted split)
                    axes[1].bar(x, nodes,    color=CHART_FG, width=0.5, label="nodes")
                    axes[1].bar(x, promoted, color=ACCENT,   width=0.5, label="promoted")
                    axes[1].set_xticks(list(x))
                    axes[1].set_xticklabels(facet_names, color=TEXT, fontsize=7)
                    axes[1].set_title("Nodes / Promoted", color=ACCENT, fontsize=8)
                    axes[1].set_facecolor(BG_PANEL)
                    axes[1].tick_params(colors=TEXT_DIM)
                    for spine in axes[1].spines.values():
                        spine.set_edgecolor(CHART_GRID)
                    axes[1].legend(fontsize=6, labelcolor=TEXT, facecolor=BG_PANEL,
                                   edgecolor=CHART_GRID)

                    fig.tight_layout(pad=0.5)
                    canvas = FigureCanvasTkAgg(fig, master=_aud_fig_frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.X)
                    _aud_fig_ref["fig"]    = fig
                    _aud_fig_ref["canvas"] = canvas
                except Exception:
                    pass

                # ── Cross-modal lanes ─────────────────────────────────────
                lanes = sc.get("lanes", {})
                _lane_map = {
                    "tone↔hue":      "tone-hue",
                    "timbre↔shape":  "timbre-shape",
                    "rhythm↔motion": "rhythm-motion",
                }
                for display, key in _lane_map.items():
                    ld = lanes.get(key, {})
                    n_nodes    = ld.get("nodes", 0)
                    n_promoted = ld.get("promoted", 0)
                    if display in aud_lane_labels:
                        aud_lane_labels[display].config(
                            text=f"{n_nodes} ({n_promoted}↑)",
                            fg=ACCENT2 if n_promoted else TEXT_DIM,
                        )
                aud_detail_labels["tone"].config(
                    text=f"{audio_data.get('tone', {}).get('nodes', 0)} ({audio_data.get('tone', {}).get('promoted', 0)}↑)\nm={float(audio_data.get('tone', {}).get('maturity', 0.0) or 0.0):.2f}"
                )
                aud_detail_labels["timbre"].config(
                    text=f"{audio_data.get('timbre', {}).get('nodes', 0)} ({audio_data.get('timbre', {}).get('promoted', 0)}↑)\nm={float(audio_data.get('timbre', {}).get('maturity', 0.0) or 0.0):.2f}"
                )
                aud_detail_labels["rhythm"].config(
                    text=f"{audio_data.get('rhythm', {}).get('nodes', 0)} ({audio_data.get('rhythm', {}).get('promoted', 0)}↑)\nm={float(audio_data.get('rhythm', {}).get('maturity', 0.0) or 0.0):.2f}"
                )
                aud_detail_labels["semantic"].config(text=str(sc.get("semantic_nodes", 0)))
                aud_detail_labels["lanes"].config(
                    text=str(sum(int(dict(v or {}).get("promoted", 0) or 0) for v in lanes.values()))
                )
            else:
                aud_status_lbl.config(text="Sensory Crystal: no state file yet")
                for _k in aud_detail_labels:
                    aud_detail_labels[_k].config(text="--")

            # ── Sensory telemetry log ─────────────────────────────────────
            telem = reader.read_sensory_telemetry(100)
            aud_telem_box.configure(state=tk.NORMAL)
            aud_telem_box.delete("1.0", tk.END)
            if live_audio_description:
                aud_telem_box.insert(tk.END, f"[live-audio] {live_audio_description}\n", "audio")
            if live_recent_speech:
                aud_telem_box.insert(tk.END, f"[speech] {live_recent_speech}\n", "semantic")
            if live_guidance_summary:
                aud_telem_box.insert(tk.END, f"[guidance] {live_guidance_summary}\n", "dim")
            for entry in telem[-40:]:
                ts_s = time.strftime("%H:%M:%S", time.localtime(entry.get("ts", 0)))
                ev   = entry.get("event", "?")
                dom  = entry.get("domain", "")
                fac  = entry.get("facet", "")
                fit  = entry.get("fitness", 0)
                use  = entry.get("usage", 0)
                lnk  = entry.get("links", 0)
                line = (f"[{ts_s}] {ev:<16} {dom}/{fac:<10}  "
                        f"fit={fit:.2f}  use={use}  links={lnk}\n")
                tag  = "audio" if dom == "audio" else "visual" if dom == "visual" else "dim"
                if ev == "node_promoted":
                    tag = "promoted"
                aud_telem_box.insert(tk.END, line, tag)
            if not telem:
                # Show real progress toward first promotion instead of static message
                try:
                    _sc2 = reader.read_sensory_crystal()
                    _frm2 = _sc2.get("total_frames", 0)
                    aud_telem_box.insert(tk.END,
                        f"── Crystal bootstrap in progress ──\n"
                        f"  Total frames ingested: {_frm2}\n",
                        "dim")
                    for _dom, _dfacets in [
                        ("audio",  _sc2.get("audio",  {})),
                        ("visual", _sc2.get("visual", {})),
                    ]:
                        for _fac, _fd in _dfacets.items():
                            _n   = _fd.get("nodes", 0)
                            _m   = _fd.get("maturity", 0.0)
                            _p   = _fd.get("promoted", 0)
                            _bar = int(_m * 20)
                            _bar_s = "█" * _bar + "░" * (20 - _bar)
                            _tag2 = "audio" if _dom == "audio" else "visual"
                            aud_telem_box.insert(tk.END,
                                f"  {_dom}/{_fac:<8}  [{_bar_s}] {_m:.3f}  "
                                f"nodes:{_n}  promoted:{_p}\n",
                                _tag2)
                    aud_telem_box.insert(tk.END,
                        "\n  First promotions appear here once facets mature.\n", "dim")
                except Exception:
                    aud_telem_box.insert(tk.END, "Crystal initializing...\n", "dim")
            aud_telem_box.see(tk.END)
            aud_telem_box.configure(state=tk.DISABLED)

            aud_rec_box.configure(state=tk.NORMAL)
            aud_rec_box.delete("1.0", tk.END)
            _audio_rec_lines: List[tuple[str, str]] = []
            for item in live_recognitions:
                item_s = str(item).strip()
                if not item_s:
                    continue
                tag = "semantic"
                low = item_s.lower()
                if low.startswith("audio:"):
                    tag = "audio"
                elif low.startswith("visual:"):
                    tag = "visual"
                _audio_rec_lines.append((f"{item_s}\n", tag))
            for lane_name, lane in dict(recognitions.get("last_matches") or {}).items():
                lane_d = dict(lane or {})
                for key, value in lane_d.items():
                    if not value:
                        continue
                    tag = "audio" if lane_name == "audio" else "visual" if lane_name == "visual" else "semantic"
                    _audio_rec_lines.append((f"{lane_name}:{key} -> {value}\n", tag))
            if not _audio_rec_lines:
                _audio_rec_lines.append(("No active recognition bindings yet.\n", "dim"))
            for line, tag in _audio_rec_lines[:12]:
                aud_rec_box.insert(tk.END, line, tag)
            aud_rec_box.configure(state=tk.DISABLED)

            # ── DCE assembly log ──────────────────────────────────────────
            dce_entries = reader.read_dce_log(100)
            dce_log_box.configure(state=tk.NORMAL)
            dce_log_box.delete("1.0", tk.END)
            for entry in dce_entries[-30:]:
                ts_s = time.strftime("%H:%M:%S", time.localtime(entry.get("ts", 0)))
                frm  = entry.get("frame", "?")
                coh  = entry.get("coherence", 0.0)
                dom  = entry.get("dominant", "?")
                qua  = entry.get("quality", 0.0)
                smat = entry.get("sensory_mat", 0.0)
                warp = "⚡WARP" if entry.get("warp") else ""
                line = (f"[{ts_s}] {frm:<12} coh={coh:.2f}  "
                        f"dom={dom}  q={qua:.2f}  s_mat={smat:.2f}  {warp}\n")
                tag  = "high" if coh >= 0.7 else "mid" if coh >= 0.4 else "low"
                dce_log_box.insert(tk.END, line, tag)
            if not dce_entries:
                dce_log_box.insert(tk.END,
                    "No DCE assembly log yet — starts after first interaction.\n",
                    "dim")
            dce_log_box.see(tk.END)
            dce_log_box.configure(state=tk.DISABLED)

        except Exception:
            pass
        root.after(REFRESH_AUDIO_MS, refresh_audio)

    def refresh_evolution():
        try:
            data = reader.read_evolution()

            hints     = data.get("adapter_hints", {})
            compounds = data.get("compound_axes", {})
            qbias      = data.get("query_bias", {})
            relief_plan = data.get("relief_plan", {})
            assim_cnt  = data.get("assimilated_ids", 0)
            pool_size = data.get("pool_size", 0)
            evo_cnt   = data.get("evolved_count", {})
            fail_pts  = data.get("fail_points", {})

            # ── Gauges ────────────────────────────────────────────────────────
            evo_pool_lbl.config(text=str(pool_size) if pool_size > 0 else "--")
            evo_gen1_lbl.config(text=str(evo_cnt.get("gen1", "--")))
            evo_gen2_lbl.config(text=str(evo_cnt.get("gen2", "--")))
            evo_frontier_lbl.config(
                text=str(evo_cnt.get("frontier", "--")),
                fg="#22c55e" if evo_cnt.get("frontier", 0) >= 4 else "#f59e0b",
            )
            evo_assimilated_lbl.config(text=str(assim_cnt) if assim_cnt else "--")
            evo_compounds_lbl.config(
                text=str(len(compounds)),
                fg=ACCENT if len(compounds) > 0 else TEXT_DIM,
            )

            # ── Typed pressure (from query_bias scores) ───────────────────────
            pressure_scores = qbias.get("pressure_scores", {})
            dominant_type   = qbias.get("dominant_type", "--")

            for ptype, widgets in evo_pressure_rows.items():
                score  = float(pressure_scores.get(ptype, 0.0))
                filled = int(score * 12)
                bar_s  = chr(0x2588) * filled + chr(0x2591) * (12 - filled)
                color  = "#ef4444" if score > 0.6 else ("#f59e0b" if score > 0.35 else ACCENT2)
                is_dom = (ptype == dominant_type)
                widgets["bar"].config(text=bar_s, fg=color)
                widgets["pct"].config(text=f"{score*100:.0f}%",
                                      fg=ACCENT if is_dom else TEXT)

            evo_dominant_lbl.config(
                text=f"dominant: {dominant_type}",
                fg=ACCENT if dominant_type != "--" else TEXT_DIM,
            )

            # ── Axis pressure + bias ──────────────────────────────────────────
            axis_stats = hints.get("axis_stats", {})
            bias_hints = hints.get("evolver_bias_hints", {})
            routing_type = hints.get("routing_type", "--")

            _axis_constraint_names = {"X": "existence", "T": "temporal",
                                      "N": "energy", "B": "boundary", "A": "agency"}
            for ax, widgets in evo_axis_rows.items():
                st      = axis_stats.get(ax, {})
                press   = float(st.get("mean_pressure_pre", 0.0))
                cname   = _axis_constraint_names.get(ax, ax.lower())
                bias_v  = float(bias_hints.get(cname, bias_hints.get(ax.lower(), 0.0)))
                press_color = ("#ef4444" if press > 0.5 else
                               ("#f59e0b" if press > 0.3 else ACCENT2))
                bias_color  = ("#ef4444" if bias_v > 0.08 else
                               ("#4ade80" if bias_v < -0.02 else TEXT_DIM))
                widgets["pressure"].config(
                    text=f"press:{press:.3f}", fg=press_color)
                widgets["bias"].config(
                    text=f"bias:{bias_v:+.3f}", fg=bias_color)

            evo_routing_lbl.config(
                text=f"routing: {routing_type}",
                fg=ACCENT if routing_type != "--" else TEXT_DIM,
            )

            # ── What evolves next ─────────────────────────────────────────────
            # Top bias axis
            if bias_hints:
                top_axis_name = max(bias_hints, key=lambda k: abs(float(bias_hints[k])))
                top_val = float(bias_hints[top_axis_name])
                evo_next_labels["top_axis"].config(
                    text=f"{top_axis_name}",
                    fg="#ef4444" if abs(top_val) > 0.1 else ACCENT2)
                evo_next_labels["top_bias_val"].config(
                    text=f"{top_val:+.4f}",
                    fg="#ef4444" if abs(top_val) > 0.1 else ACCENT2)
            else:
                evo_next_labels["top_axis"].config(text="no data yet", fg=TEXT_DIM)
                evo_next_labels["top_bias_val"].config(text="--", fg=TEXT_DIM)

            # Compound axes
            n_compounds = len(compounds)
            n_vslots = sum(
                len(v.get("virtual_slots", [])) for v in compounds.values()
            ) if isinstance(compounds, dict) else 0
            if n_compounds > 0:
                top_comp = max(compounds.items(),
                               key=lambda kv: kv[1].get("co_occurrence", 0),
                               default=("--", {}))[0]
                evo_next_labels["compound_st"].config(
                    text=f"{n_compounds} registered  (top: {top_comp})",
                    fg="#22c55e")
                evo_next_labels["slots_avail"].config(
                    text=f"{n_vslots} virtual slots",
                    fg=ACCENT2)
            else:
                evo_next_labels["compound_st"].config(
                    text="none yet — need runtime pressure log",
                    fg=TEXT_DIM)
                evo_next_labels["slots_avail"].config(text="0", fg=TEXT_DIM)

            # Frontier + gen2
            nf = evo_cnt.get("frontier", 0)
            evo_next_labels["frontier_st"].config(
                text=f"{nf}/4 ops in pool" if nf else "not yet injected",
                fg="#22c55e" if nf >= 4 else "#f59e0b")
            ng2 = evo_cnt.get("gen2", 0)
            evo_next_labels["gen2_st"].config(
                text=f"{ng2} gen-2 ops in pool",
                fg=ACCENT2 if ng2 > 0 else TEXT_DIM)

            # ── Training priorities ───────────────────────────────────────────
            fp_recs = fail_pts.get("records", {})
            for dim, widgets in evo_train_labels.items():
                rec = fp_recs.get(dim, {})
                if not isinstance(rec, dict):
                    continue
                fc  = int(rec.get("fail_count", 0))
                sev = float(rec.get("severity_sum", 0.0)) / max(1, fc)
                color = ("#ef4444" if sev > 0.6 else
                         ("#f59e0b" if sev > 0.35 else ACCENT2))
                txt = f"{sev:.2f} ({fc})" if fc > 0 else "--"
                widgets["sev"].config(text=txt, fg=color)

            # ── Multi-layer pressure panels ───────────────────────────────────
            lp = data.get("layer_pressure", {})

            # L4 Genealogy — leverage-normalized
            l4g = lp.get("L4_genealogy", {})
            lv  = lp.get("leverage", {})
            evo_l4g_labels["total"].config(text=str(l4g.get("total", 0)))
            gate_d = l4g.get("gate", {})
            evo_l4g_labels["gate_G4"].config(
                text=str(gate_d.get("G4", 0)),
                fg="#f59e0b" if gate_d.get("G4", 0) > 50 else ACCENT2)
            evo_l4g_labels["gate_G5"].config(
                text=str(gate_d.get("G5", 0)),
                fg="#ef4444" if gate_d.get("G5", 0) > 200 else ACCENT2)
            evo_l4g_labels["tension"].config(
                text=f"{l4g.get('avg_tension', 0):.4f}",
                fg="#ef4444" if l4g.get("avg_tension", 0) > 0.5 else ACCENT2)
            # Leverage scale bars — cost-normalized
            ax_norm = lv.get("axis_normalized", {})
            for ax, widgets in evo_l4g_bars.items():
                norm = ax_norm.get(ax, 0.0)
                filled = int(norm * 10)
                bar = chr(0x2588) * filled + chr(0x2591) * (10 - filled)
                color = widgets["color"] if norm > 0.01 else TEXT_DIM
                widgets["bar"].config(text=bar, fg=color)
                widgets["pct"].config(text=f"{norm*100:.0f}%", fg=color)
            # Band position + relief valve status
            band_pos = lv.get("band_position", "unknown")
            net      = lv.get("net", 0.0)
            band_color = {"LOW": "#ef4444", "INSIDE": "#22c55e",
                          "HIGH": "#f59e0b", "unknown": TEXT_DIM}.get(band_pos, TEXT_DIM)
            band_text  = {"LOW": "LOW — overhead dominant (X/T heavy)",
                          "INSIDE": "INSIDE viable band",
                          "HIGH": "HIGH — leverage dominant (B/A heavy)",
                          "unknown": "unknown"}.get(band_pos, band_pos)
            # Check if relief valve is active
            try:
                hints = json.loads((_STATE_DIR / "adapter_hints.json").read_text())
                relief_active = hints.get("leverage_redirect_active", False)
                if relief_active:
                    band_text += "  ⟶ RELIEF ACTIVE"
                    band_color = "#f59e0b"
            except Exception:
                pass
            evo_l4g_labels["band"].config(text=f"band: {band_text}", fg=band_color)
            evo_l4g_labels["net"].config(
                text=f"net: {net:+.1f}  (viable: {lv.get('band_low',0):.1f}→{lv.get('band_high',0):.1f})",
                fg=band_color)

            # L4 Turn-chain + Dream
            l4t = lp.get("L4_turn_chain", {})
            l4d = lp.get("L4_dream", {})
            evo_l4t_labels["tc_total"].config(text=str(l4t.get("total", 0)))
            evo_l4t_labels["tc_tension"].config(text=f"{l4t.get('avg_tension', 0):.4f}")
            evo_l4t_labels["dm_total"].config(text=str(l4d.get("total", 0)))
            evo_l4t_labels["dm_tension"].config(
                text=f"{l4d.get('avg_tension', 0):.4f}",
                fg="#ef4444" if l4d.get("avg_tension", 0) > 0.5 else ACCENT2)

            # L5/L6
            l5 = lp.get("L5_template", {})
            l6 = lp.get("L6_behavioral", {})
            evo_l56_labels["pool"].config(text=str(l5.get("pool_size", "--")))
            evo_l56_labels["gen"].config(text=str(l5.get("generation", "--")))
            gov = l6.get("governance", {})
            evo_l56_labels["gov_nodes"].config(text=str(gov.get("total_nodes", "--")))
            energy_nodes = gov.get("layers", {}).get("ENERGY", "--")
            evo_l56_labels["gov_energy"].config(text=str(energy_nodes))
            cp = l6.get("crystal_pressure", {})
            if cp:
                top_gap = max(cp.items(), key=lambda kv: kv[1], default=("--", 0))
                evo_l56_labels["crystal_gaps"].config(
                    text=f"{len(cp)} gaps (top:{top_gap[1]:.2f})",
                    fg="#f59e0b" if len(cp) > 3 else ACCENT2)
            else:
                evo_l56_labels["crystal_gaps"].config(text="none", fg="#22c55e")

            # L7 625-map
            l7m = lp.get("L7_625map", {})
            occ = l7m.get("occupied", 0)
            tot = l7m.get("total", 625)
            evo_l7_labels["occupied"].config(
                text=f"{occ}/{tot}",
                fg="#22c55e" if occ > 150 else "#f59e0b")
            evo_l7_labels["highway"].config(text=str(l7m.get("highway", "--")))
            aw = l7m.get("axis_weight", {})
            max_w = max(aw.values(), default=1)
            for ax in ("X","T","N","B","A"):
                w = aw.get(ax, 0)
                color = AXIS_COLORS.get(ax, ACCENT2) if w > 0 else TEXT_DIM
                evo_l7_labels[f"w{ax}"].config(text=f"{w:.1f}", fg=color)

            # Experience feed: show recent events from all layers
            evo_plog_feed.configure(state=tk.NORMAL)
            evo_plog_feed.delete("1.0", tk.END)
            shown = 0
            for src_key, tag, prefix in [
                ("L4_genealogy",  "genealogy", "GENE"),
                ("L4_turn_chain", "turn",      "TURN"),
                ("L4_dream",      "dream",     "DREM"),
            ]:
                src_d = lp.get(src_key, {})
                for line in src_d.get("recent", []):
                    evo_plog_feed.insert(tk.END, f"[{prefix}] ", tag)
                    evo_plog_feed.insert(tk.END, line + "\n", "dim")
                    shown += 1
            # Surface entries
            l7s = lp.get("L7_surface", {})
            for entry in l7s.get("recent", [])[:8]:
                axes = entry.get("axes", [])
                evo_plog_feed.insert(tk.END, "[SURF] ", "surface")
                evo_plog_feed.insert(tk.END,
                    f"[{entry['ts']}] ", "dim")
                for i, ax in enumerate(axes):
                    evo_plog_feed.insert(tk.END, ax, f"ax_{ax}")
                    if i < len(axes) - 1:
                        evo_plog_feed.insert(tk.END, "+", "dim")
                sc = entry.get("score", 0)
                evo_plog_feed.insert(tk.END,
                    f"  sc={sc:.3f}  gp={entry.get('gp',0):.3f}\n",
                    "hi" if sc > 0.7 else "dim")
            if shown == 0 and not l7s.get("recent"):
                evo_plog_feed.insert(tk.END,
                    "No pressure experiences yet.\n"
                    "Experiences accumulate from genealogy, turn-chain, dream, and surface layers.\n",
                    "dim")
            evo_plog_feed.see(tk.END)
            evo_plog_feed.configure(state=tk.DISABLED)

            # Surface co-occurrence matrix
            cooc_counts = l7s.get("axis_cooc", {})
            max_cooc = max(cooc_counts.values(), default=1)
            for key, widgets in evo_cooc_labels.items():
                cnt = cooc_counts.get(key, 0)
                filled = int((cnt / max(max_cooc, 1)) * 8)
                bar = chr(0x2588) * filled + chr(0x2591) * (8 - filled)
                color = "#22c55e" if cnt > 5 else ("#f59e0b" if cnt > 0 else TEXT_DIM)
                widgets["cnt"].config(text=str(cnt) if cnt else "--", fg=color)
                widgets["bar"].config(text=bar, fg=color)

            # ── Growth directive (from query_bias) ────────────────────────────
            evo_directive_box.configure(state=tk.NORMAL)
            evo_directive_box.delete("1.0", tk.END)

            active_biases = qbias.get("active_biases", [])
            classification_mode = str(qbias.get("classification_mode", "active") or "active")
            dominant_score = float(
                qbias.get("dominant_score", pressure_scores.get(dominant_type, 0.0) or 0.0) or 0.0
            )
            daemon_st = data.get("daemon_status", {}) or {}
            gov_mode = str(daemon_st.get("runtime_governor_mode", "") or "")
            blocked_tasks = list(daemon_st.get("runtime_recent_blocked", []) or [])

            if gov_mode in ("survival", "conserve", "minimal") or blocked_tasks:
                host = daemon_st.get("runtime_host", {}) or {}
                mem_avail = float(host.get("mem_available_mb", 0.0) or 0.0)
                load_ratio = float(host.get("load_ratio", 0.0) or 0.0)
                evo_directive_box.insert(
                    tk.END,
                    f"Runtime guard active: mode={gov_mode or '--'}  load={load_ratio:.2f}  mem_avail={mem_avail:.0f}MB\n",
                    "hypothesis",
                )
                for blocked_entry in blocked_tasks[:3]:
                    task = blocked_entry.get("task", "?")
                    reason = blocked_entry.get("reason", "?")
                    score = blocked_entry.get("score")
                    score_txt = ""
                    if isinstance(score, (int, float)):
                        score_txt = f" score={float(score):.3f}"
                    evo_directive_box.insert(
                        tk.END,
                        f"  {task} deferred by {reason}{score_txt}\n",
                        "dim",
                    )
                evo_directive_box.insert(tk.END, "\n")

            if relief_plan.get("active"):
                staged_tasks = ", ".join(list(relief_plan.get("blocked_tasks", []) or [])[:3]) or "mutation"
                staged_reason = str(relief_plan.get("reason", "?") or "?")
                staged_operator = str(relief_plan.get("selected_operator", "--") or "--")
                staged_when = str(relief_plan.get("generated_at_str", "--") or "--")
                staged_retry = int(relief_plan.get("retry_after", 0) or 0)
                staged_status = str(relief_plan.get("status", "staged") or "staged").replace("_", " ")
                handoff_attempts = int(relief_plan.get("handoff_attempts", 0) or 0)
                evo_directive_box.insert(
                    tk.END,
                    f"Survival relief staged: {staged_tasks} blocked by {staged_reason}  ->  {staged_operator}  ({staged_when})\n",
                    "heading",
                )
                evo_directive_box.insert(
                    tk.END,
                    f"  Handoff status: {staged_status}  attempts={handoff_attempts}\n",
                    "directive",
                )
                if staged_retry > 0:
                    evo_directive_box.insert(
                        tk.END,
                        f"  Retry window: {staged_retry}s\n",
                        "directive",
                    )
                last_gate = dict(relief_plan.get("last_gate") or {})
                if last_gate:
                    gate_reason = str(last_gate.get("reason", "") or "")
                    gate_score = last_gate.get("score")
                    gate_floor = last_gate.get("floor")
                    gate_retry = int(last_gate.get("retry_in", 0) or 0)
                    gate_bits = [f"Safe-window gate: {gate_reason or 'allowed'}"]
                    if isinstance(gate_score, (int, float)) and isinstance(gate_floor, (int, float)):
                        gate_bits.append(f"score={float(gate_score):.3f}/{float(gate_floor):.3f}")
                    if gate_retry > 0 and gate_reason and gate_reason != "allowed":
                        gate_bits.append(f"retry={gate_retry}s")
                    evo_directive_box.insert(
                        tk.END,
                        "  " + "  ".join(gate_bits) + "\n",
                        "dim" if gate_reason and gate_reason != "allowed" else "domain",
                    )
                last_handoff = str(relief_plan.get("last_handoff_at_str", "") or "")
                if last_handoff:
                    handoff_status = str(relief_plan.get("last_handoff_status", "") or "")
                    status_suffix = f" ({handoff_status})" if handoff_status else ""
                    evo_directive_box.insert(
                        tk.END,
                        f"  Last handoff: {last_handoff}{status_suffix}\n",
                        "dim",
                    )
                result_excerpt = str(relief_plan.get("poedex_result_excerpt", "") or "").strip()
                if result_excerpt:
                    evo_directive_box.insert(
                        tk.END,
                        f"  Poedex returned: {result_excerpt}\n",
                        "domain",
                    )
                for staged_action in list(relief_plan.get("actions", []) or [])[:2]:
                    pressure_type = str(staged_action.get("pressure_type", "") or "?")
                    label = str(staged_action.get("label", "") or "")
                    prompt = str(staged_action.get("query", "") or staged_action.get("reflection", "") or label)
                    evo_directive_box.insert(
                        tk.END,
                        f"  Queue [{pressure_type}]: {prompt}\n",
                        "dim",
                    )
                    domains = list(staged_action.get("study_domains", []) or [])[:3]
                    if domains:
                        evo_directive_box.insert(
                            tk.END,
                            f"  Study:  {', '.join(domains)}\n",
                            "domain",
                        )
                poedex_q = str(relief_plan.get("poedex_question", "") or "").strip()
                if poedex_q:
                    evo_directive_box.insert(
                        tk.END,
                        f"  Poedex queue: {poedex_q[:220]}{'...' if len(poedex_q) > 220 else ''}\n",
                        "hypothesis",
                    )
                evo_directive_box.insert(tk.END, "\n")

            if not active_biases:
                if dominant_type not in ("--",) and dominant_score > 0.0:
                    floor = float(qbias.get("min_score", 0.20) or 0.20)
                    evo_directive_box.insert(
                        tk.END,
                        f"Pressure signal present but below the strong-routing floor ({dominant_score:.3f} < {floor:.2f}).\n"
                        "Aurora will keep the dominant growth direction warm until stronger pressure accumulates.\n\n",
                        "dim",
                    )
                elif not hints and not qbias:
                    evo_directive_box.insert(
                        tk.END,
                        "No pressure data yet.\n\n"
                        "Run 50+ ticks to populate surface_pressure_log.jsonl,\n"
                        "then the pressure router will write the growth directive here.\n",
                        "dim",
                    )
                else:
                    evo_directive_box.insert(
                        tk.END,
                        "Pressure detected but not yet classified.\n"
                        "Run 'adapt' from the aurora> CLI to trigger routing.\n",
                        "dim",
                    )
            else:
                ts = qbias.get("last_updated", 0)
                ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) if ts else "--"
                evo_directive_box.insert(
                    tk.END,
                    f"Updated {ts_str}  ·  dominant: {dominant_type}\n",
                    "dim",
                )
                if classification_mode != "active":
                    evo_directive_box.insert(
                        tk.END,
                        "Weak-signal routing: keeping the dominant growth direction warm while pressure builds.\n\n",
                        "dim",
                    )
                else:
                    evo_directive_box.insert(tk.END, "\n")

                for entry in active_biases[:3]:
                    ptype = entry.get("pressure_type", "")
                    pri   = entry.get("priority", 0.0)
                    label = entry.get("label", "")
                    axis  = entry.get("axis", "")
                    evo_directive_box.insert(
                        tk.END,
                        f"▶ [{ptype}]  priority={pri:.3f}  —  {label}  ({axis})\n",
                        "heading",
                    )

                    refl = entry.get("reflection_directive", "")
                    if refl:
                        evo_directive_box.insert(tk.END, f"  Reflection: {refl}\n", "directive")

                    hyp = entry.get("hypothesis_seed", "")
                    if hyp:
                        evo_directive_box.insert(tk.END, f"  Hypothesis: {hyp}\n", "hypothesis")

                    domains = entry.get("retrieval_domains", [])
                    if domains:
                        evo_directive_box.insert(
                            tk.END,
                            f"  Study:  {', '.join(domains[:4])}\n",
                            "domain",
                        )

                    templates = entry.get("query_templates", [])
                    if templates:
                        evo_directive_box.insert(tk.END, f"  Query:  {templates[0]}\n", "dim")

                    evo_directive_box.insert(tk.END, "\n")
            evo_directive_box.see("1.0")
            evo_directive_box.configure(state=tk.DISABLED)

            # ── Live constraint genealogy ─────────────────────────────────────
            # Primary: corpus_runner_status.json (written during training runs)
            # Fallback: daemon_status.json (written every turn during daemon mode)
            cr_st = data.get("corpus_runner_status", {})
            cr_ts = float(cr_st.get("timestamp", 0) or 0)
            cr_age = time.time() - cr_ts if cr_ts else 9999
            daemon_st = data.get("daemon_status", {})

            # Use corpus_runner_status if fresh (< 5 min old), else daemon
            if cr_st and cr_age < 300:
                links   = cr_st.get("links_promoted", "--")
                outlet  = cr_st.get("outlet_push_fraction")
                ticks   = cr_st.get("tick_count", "--")
                epoch   = cr_st.get("current_epoch", "--")
                pass_n  = cr_st.get("pass_name", "--")
                msgs    = cr_st.get("message_count", "--")
                orient  = cr_st.get("pressure_orientation", {})
                age_s   = int(cr_age)
                age_str = f"{age_s}s ago" if age_s < 300 else f"{age_s//60}m ago"
                source  = "corpus"
            elif daemon_st:
                links   = daemon_st.get("chain_links", "--")
                outlet  = daemon_st.get("outlet_push_fraction")
                ticks   = "--"
                epoch   = "--"
                pass_n  = "daemon"
                msgs    = "--"
                orient  = daemon_st.get("axis_orientation", {})
                upd     = daemon_st.get("updated", "")
                age_str = f"daemon {upd}" if upd else "daemon"
                source  = "daemon"
            else:
                links = outlet = ticks = epoch = pass_n = msgs = orient = None
                age_str = source = ""

            if links is not None or outlet is not None:
                orient_str = "  ".join(f"{ax}:{v:.2f}" for ax, v in sorted((orient or {}).items())) if orient else "--"
                outlet_str = f"{outlet:.4f}" if isinstance(outlet, float) else "--"
                try:
                    evo_directive_box.configure(state=tk.NORMAL)
                    evo_directive_box.insert("1.0",
                        f"─── Constraint Genealogy [{source}] ({age_str}) ───\n"
                        f"  pass={pass_n}  msgs={msgs}  epoch={epoch}\n"
                        f"  links={links}  outlet={outlet_str}  ticks={ticks}\n"
                        f"  orient: {orient_str}\n\n",
                        "directive",
                    )
                    evo_directive_box.configure(state=tk.DISABLED)
                except Exception:
                    pass

            # ── Daemon activity log ───────────────────────────────────────────
            # Pull the last ~200 lines from daemon.log and show only the ones
            # tagged with evo-relevant prefixes so the user can see what's
            # happening in the system after each autonomous cycle.
            _EVO_TAGS = ("[MUTATE]", "[ASSIM]", "[GEN2]", "[EVO]", "[DREAM]",
                         "[PRESSURE]", "[STUDY]", "[FRONTIER]", "[CHAMBER]")
            _TAG_STYLE = {
                "[MUTATE]":   "mutate",
                "[DREAM]":    "dream",
                "[ASSIM]":    "assim",
                "[GEN2]":     "gen2",
                "[EVO]":      "evo",
                "[PRESSURE]": "pressure",
                "[STUDY]":    "study",
                "[FRONTIER]": "evo",
                "[CHAMBER]":  "evo",
            }
            try:
                log_lines = reader._read_log(300)
                evo_lines = [l for l in log_lines if any(t in l for t in _EVO_TAGS)]
                evo_activity_box.configure(state=tk.NORMAL)
                evo_activity_box.delete("1.0", tk.END)
                if not evo_lines:
                    evo_activity_box.insert(tk.END,
                        "No evolution activity yet.\n"
                        "Mutation and assimilation cycles fire every ~10 min.\n",
                        "dim")
                else:
                    for line in evo_lines[-120:]:   # show last 120 evo events
                        style = "dim"
                        for tag, s in _TAG_STYLE.items():
                            if tag in line:
                                style = s
                                break
                        evo_activity_box.insert(tk.END, line.rstrip() + "\n", style)
                # Sensory promotions feed the evolution picture
                _stelem = reader.read_sensory_telemetry(30)
                for _se in _stelem[-10:]:
                    _sts = time.strftime("%H:%M:%S", time.localtime(_se.get("ts", 0)))
                    _sdom = _se.get("domain", "")
                    _sfac = _se.get("facet", "")
                    _sfit = _se.get("fitness", 0)
                    _sline = (f"[{_sts}] [SENSORY] {_sdom}/{_sfac} promoted "
                              f"fitness={_sfit:.2f}\n")
                    evo_activity_box.insert(tk.END, _sline, "sensory")
                    evo_activity_box.see(tk.END)
                evo_activity_box.configure(state=tk.DISABLED)
            except Exception:
                pass

        except Exception as e:
            try:
                evo_directive_box.configure(state=tk.NORMAL)
                evo_directive_box.delete("1.0", tk.END)
                evo_directive_box.insert(tk.END, f"[refresh error] {e}\n", "dim")
                evo_directive_box.configure(state=tk.DISABLED)
            except Exception:
                pass

        root.after(REFRESH_EVO_MS, refresh_evolution)

    def refresh_training():
        try:
            data      = reader.read_training()
            sess      = data.get("session", {})
            fail_pts  = data.get("fail_points", {})
            fp_recs   = fail_pts.get("records", {})
            cr_st     = data.get("corpus_runner_status", {})

            # corpus_runner_status is written every ~100 msgs; use it as the
            # primary liveness signal since training_session.json only saves
            # at checkpoints (every 500 msgs).
            cr_ts     = float(cr_st.get("timestamp", 0) or 0)
            cr_age    = time.time() - cr_ts if cr_ts else 9999
            is_active = cr_age < 300  # active if status updated within 5 min

            # Status bar
            if is_active:
                trn_active_lbl.config(text="● ACTIVE", fg="#22c55e")
            else:
                trn_active_lbl.config(text="● IDLE", fg=TEXT_DIM)

            # Prefer corpus_runner_status pass name (live) over session pass
            pass_name = cr_st.get("pass_name") or sess.get("pass", "--")
            pass_idx  = sess.get("pass_index", 0)
            msgs_live = cr_st.get("message_count", "")
            trn_pass_lbl.config(
                text=f"pass: {pass_name}  [{pass_idx+1}/3]"
                     + (f"  msg:{msgs_live}" if msgs_live else ""),
                fg=ACCENT2 if is_active else TEXT_DIM,
            )

            last_sim = cr_st.get("last_sim") or sess.get("last_sim")
            if last_sim is not None:
                sim_color = ("#22c55e" if last_sim > 0.35 else
                             ("#f59e0b" if last_sim > 0.18 else "#ef4444"))
                trn_sim_lbl.config(text=f"sim: {last_sim:.3f}", fg=sim_color)
            else:
                trn_sim_lbl.config(text="sim: --", fg=TEXT_DIM)

            # Freshness: use corpus_runner_status timestamp for tighter age display
            lu_ts = cr_ts or sess.get("last_update")
            if lu_ts:
                age = time.time() - float(lu_ts)
                trn_updated_lbl.config(
                    text=f"updated {int(age)}s ago",
                    fg=ACCENT2 if age < 120 else TEXT_DIM,
                )

            # Progress bars
            def _draw_bar(bar_lbl, pct_lbl, detail_lbl, pct_val, processed, total):
                filled = int(min(pct_val, 100) / 100 * 20)
                bar_lbl.config(text=chr(0x2588)*filled + chr(0x2591)*(20-filled))
                pct_lbl.config(text=f"{pct_val:.1f}%")
                if total:
                    detail_lbl.config(text=f"{processed:,} / {total:,}")

            _draw_bar(trn_corpus_bar, trn_corpus_pct, trn_corpus_detail,
                      sess.get("pct_corpus", 0.0),
                      sess.get("messages_processed", 0),
                      sess.get("total_messages", 0))

            batch_limit = sess.get("batch_limit", 0)
            _draw_bar(trn_session_bar, trn_session_pct, trn_session_detail,
                      sess.get("pct_session", 0.0),
                      sess.get("session_messages", 0),
                      batch_limit if batch_limit > 0 else sess.get("total_messages", 0))

            # Fail dims with live severity bars
            for dim, widgets in trn_fail_rows.items():
                rec = fp_recs.get(dim, {})
                fc  = int(rec.get("fail_count", 0))
                sev = (float(rec.get("severity_sum", 0.0)) / max(1, fc)) if fc > 0 else 0.0
                filled = int(min(sev, 1.0) * 10)
                bar_str = chr(0x2588)*filled + chr(0x2591)*(10-filled)
                color = ("#ef4444" if sev > 0.6 else
                         ("#f59e0b" if sev > 0.35 else ACCENT2))
                widgets["bar"].config(text=bar_str, fg=color)
                widgets["sev"].config(
                    text=f"{sev:.2f} ({fc})" if fc > 0 else "--",
                    fg=color if fc > 0 else TEXT_DIM,
                )

            # Sim burst panel
            burst = sess.get("last_sim_burst")
            if burst:
                bts  = float(burst.get("ts", 0))
                beps = burst.get("episodes", "--")
                bdims = ", ".join(burst.get("top_dims", [])[:3]) or "--"
                btime = time.strftime("%H:%M:%S", time.localtime(bts)) if bts else "--"
                trn_burst_ts_lbl.config(text=f"Last burst: {btime}")
                trn_burst_eps_lbl.config(text=f"Episodes: {beps}")
                trn_burst_dims_lbl.config(text=f"Targeting: {bdims}", fg=ACCENT)
            else:
                trn_burst_ts_lbl.config(text="Last burst: none yet")
                trn_burst_eps_lbl.config(text="Episodes: --")
                trn_burst_dims_lbl.config(text="Targeting: --", fg=TEXT_DIM)

            # Lesson plan panel
            plan = sess.get("lesson_plan")
            if plan:
                pts   = float(plan.get("ts", 0))
                pdims = ", ".join(plan.get("top_dims", [])[:4]) or "--"
                ptime = time.strftime("%H:%M:%S", time.localtime(pts)) if pts else "--"
                trn_plan_ts_lbl.config(text=f"Lesson plan: {ptime}")
                trn_plan_dims_lbl.config(text=pdims, fg=ACCENT2)
            else:
                trn_plan_ts_lbl.config(text="Lesson plan: none yet")
                trn_plan_dims_lbl.config(text="--", fg=TEXT_DIM)

            # Events log
            events = sess.get("events", [])
            if events:
                trn_log_box.configure(state=tk.NORMAL)
                trn_log_box.delete("1.0", tk.END)
                _ETYPE_TAG = {
                    "sim_burst":   "sim",
                    "checkpoint":  "check",
                    "pass_start":  "pass",
                    "lesson_plan": "pass",
                    "batch_stop":  "batch",
                    "complete":    "complete",
                }
                for ev in reversed(events[-20:]):
                    ets  = float(ev.get("ts", 0))
                    etype = ev.get("type", "")
                    emsg = ev.get("msg", "")
                    estr = time.strftime("%H:%M:%S", time.localtime(ets))
                    tag  = _ETYPE_TAG.get(etype, "dim")
                    trn_log_box.insert(tk.END, f"{estr}  {emsg}\n", tag)
                trn_log_box.see("1.0")
                trn_log_box.configure(state=tk.DISABLED)

        except Exception as e:
            try:
                trn_log_box.configure(state=tk.NORMAL)
                trn_log_box.delete("1.0", tk.END)
                trn_log_box.insert(tk.END, f"[refresh error] {e}\n", "dim")
                trn_log_box.configure(state=tk.DISABLED)
            except Exception:
                pass

        root.after(REFRESH_TRAINING_MS, refresh_training)

    # ========================================================================
    # TAB 6: SOCIAL  (GPT learning sessions + away mode)
    # ========================================================================
    REFRESH_SOCIAL_MS = 8000

    tab_social_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_social_outer, text="  Social  ")
    tab_social = _make_scrollable_inner(tab_social_outer)

    # ── Away mode status bar ──────────────────────────────────────────────────
    soc_away_bar = tk.Frame(tab_social, bg=BG_PANEL, pady=6, padx=10)
    soc_away_bar.pack(fill=tk.X, padx=6, pady=(6, 2))

    soc_away_dot = tk.Label(soc_away_bar, text="●", bg=BG_PANEL,
                             fg=TEXT_DIM, font=("Courier New", 11, "bold"))
    soc_away_dot.pack(side=tk.LEFT, padx=(0, 6))

    soc_away_lbl = tk.Label(soc_away_bar, text="AWAY MODE: OFF",
                              bg=BG_PANEL, fg=TEXT_DIM,
                              font=("Courier New", 10, "bold"))
    soc_away_lbl.pack(side=tk.LEFT)

    soc_interval_lbl = tk.Label(soc_away_bar, text="",
                                 bg=BG_PANEL, fg=TEXT_DIM,
                                 font=("Courier New", 9))
    soc_interval_lbl.pack(side=tk.LEFT, padx=(16, 0))

    soc_session_count_lbl = tk.Label(soc_away_bar, text="",
                                      bg=BG_PANEL, fg=ACCENT2,
                                      font=("Courier New", 9))
    soc_session_count_lbl.pack(side=tk.RIGHT, padx=(0, 6))

    # ── Session list + transcript split ──────────────────────────────────────
    soc_split = tk.Frame(tab_social, bg=BG)
    soc_split.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

    # Left: session list
    soc_left = tk.Frame(soc_split, bg=BG, width=220)
    soc_left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
    soc_left.pack_propagate(False)

    tk.Label(soc_left, text="SESSIONS", bg=BG, fg=ACCENT,
             font=("Courier New", 8, "bold")).pack(anchor=tk.W, pady=(2, 2))

    soc_list_box = tk.Listbox(
        soc_left, bg=BG_LOG, fg=TEXT, selectbackground=ACCENT2,
        selectforeground=BG, font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0, activestyle="none",
    )
    soc_list_box.pack(fill=tk.BOTH, expand=True)

    # Right: transcript + learning summary
    soc_right = tk.Frame(soc_split, bg=BG)
    soc_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(soc_right, text="TRANSCRIPT", bg=BG, fg=ACCENT,
             font=("Courier New", 8, "bold")).pack(anchor=tk.W, pady=(2, 2))

    soc_transcript_box = scrolledtext.ScrolledText(
        soc_right, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=18,
        insertbackground=TEXT, wrap=tk.WORD,
    )
    soc_transcript_box.pack(fill=tk.BOTH, expand=True)
    soc_transcript_box.tag_config("aurora",  foreground=ACCENT2,  font=("Courier New", 8, "bold"))
    soc_transcript_box.tag_config("gpt",     foreground="#94a3b8", font=("Courier New", 8, "bold"))
    soc_transcript_box.tag_config("heading", foreground=ACCENT,   font=("Courier New", 8, "bold"))
    soc_transcript_box.tag_config("learn",   foreground="#4ade80")
    soc_transcript_box.tag_config("dim",     foreground=TEXT_DIM)

    # ── Learning summary strip ────────────────────────────────────────────────
    tk.Frame(tab_social, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=6, pady=(4, 0))
    soc_learn_box = scrolledtext.ScrolledText(
        tab_social, bg=BG_LOG, fg=TEXT_DIM,
        font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0,
        state=tk.DISABLED, height=6,
        insertbackground=TEXT, wrap=tk.WORD,
    )
    soc_learn_box.pack(fill=tk.X, padx=6, pady=(0, 6))
    soc_learn_box.tag_config("heading", foreground=ACCENT,  font=("Courier New", 8, "bold"))
    soc_learn_box.tag_config("fact",    foreground="#4ade80")
    soc_learn_box.tag_config("dim",     foreground=TEXT_DIM)

    # Internal state — which session index is selected
    _soc_state = {"sessions": [], "selected": -1, "signature": None}

    def _soc_load_transcript(idx: int) -> None:
        sessions = _soc_state["sessions"]
        if idx < 0 or idx >= len(sessions):
            return
        sess = sessions[idx]
        soc_transcript_box.configure(state=tk.NORMAL)
        soc_transcript_box.delete("1.0", tk.END)
        import datetime as _dt
        ts = float(sess.get("timestamp", 0) or 0)
        ts_str = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "--"
        topic = sess.get("topic") or "autonomous"
        turns = sess.get("turns", 0)
        source = str(sess.get("source", "learning_session") or "learning_session")
        source_lbl = "entity_journal" if source == "entity_journal" else "learning_session"
        soc_transcript_box.insert(tk.END,
            f"Session  {ts_str}  ·  topic: {topic}  ·  {turns} turn(s)  ·  {source_lbl}\n"
            + "─" * 60 + "\n\n", "heading")
        for ex in (sess.get("exchanges") or []):
            aurora_txt = str(ex.get("aurora", "")).strip()
            gpt_txt    = str(ex.get("gpt", "")).strip()
            if gpt_txt:
                soc_transcript_box.insert(tk.END, "GPT:    ", "gpt")
                soc_transcript_box.insert(tk.END, gpt_txt + "\n\n", "dim")
            if aurora_txt:
                soc_transcript_box.insert(tk.END, "Aurora: ", "aurora")
                soc_transcript_box.insert(tk.END, aurora_txt + "\n\n", "dim")
        soc_transcript_box.see("1.0")
        soc_transcript_box.configure(state=tk.DISABLED)

    def _on_soc_select(evt) -> None:
        sel = soc_list_box.curselection()
        if not sel:
            return
        # List shows newest first; map back to sessions list index
        list_idx = sel[0]
        sessions = _soc_state["sessions"]
        real_idx = len(sessions) - 1 - list_idx
        _soc_state["selected"] = real_idx
        _soc_load_transcript(real_idx)

    soc_list_box.bind("<<ListboxSelect>>", _on_soc_select)

    def refresh_social() -> None:
        try:
            import datetime as _dt, json as _jl
            _transcripts_path  = _STATE_DIR / "gpt_learning_transcripts.json"
            _learn_log_path    = _STATE_DIR / "social_learning_log.json"
            _away_path         = _STATE_DIR / "away_mode.json"

            # ── Away mode status ──────────────────────────────────────────────
            away_active   = False
            away_interval = 30
            away_started  = 0.0
            try:
                awd = _jl.loads(_away_path.read_text()) if _away_path.exists() else {}
                away_active   = bool(awd.get("active", False))
                away_interval = int(awd.get("interval_minutes", 30) or 30)
                away_started  = float(awd.get("started_at", 0.0) or 0.0)
            except Exception:
                pass

            if away_active:
                soc_away_dot.config(fg="#4ade80")
                soc_away_lbl.config(text="AWAY MODE: ACTIVE", fg="#4ade80")
                soc_interval_lbl.config(
                    text=f"sessions every {away_interval} min",
                    fg=TEXT_DIM)
            else:
                soc_away_dot.config(fg=TEXT_DIM)
                soc_away_lbl.config(text="AWAY MODE: OFF", fg=TEXT_DIM)
                soc_interval_lbl.config(text="", fg=TEXT_DIM)

            # ── Load transcript sessions ──────────────────────────────────────
            sessions: list = []
            try:
                if _transcripts_path.exists():
                    sessions = _jl.loads(_transcripts_path.read_text())
                    if not isinstance(sessions, list):
                        sessions = []
            except Exception:
                sessions = []

            sessions = [
                dict(sess) for sess in sessions
                if isinstance(sess, dict) and list(sess.get("exchanges") or [])
            ]

            try:
                _entity_journal_path = _STATE_DIR / "entity_journal.json"
                if _entity_journal_path.exists():
                    journal = _jl.loads(_entity_journal_path.read_text())
                    raw_exchanges = list(journal.get("exchanges") or [])
                    if raw_exchanges:
                        session_exchanges = []
                        last_ts = 0.0
                        for ex in raw_exchanges:
                            if not isinstance(ex, dict):
                                continue
                            ex_time = str(ex.get("time", "") or "").strip()
                            if ex_time:
                                try:
                                    last_ts = max(last_ts, _dt.datetime.fromisoformat(ex_time).timestamp())
                                except Exception:
                                    pass
                            aurora_txt = str(ex.get("aurora", ex.get("aurora_said", "")) or "").strip()
                            gpt_txt = str(ex.get("gpt", ex.get("they_said", "")) or "").strip()
                            if aurora_txt or gpt_txt:
                                session_exchanges.append({
                                    "aurora": aurora_txt,
                                    "gpt": gpt_txt,
                                })
                        if session_exchanges:
                            sessions.append({
                                "timestamp": last_ts,
                                "topic": str(
                                    journal.get("conversation_id")
                                    or journal.get("conversation_url")
                                    or journal.get("entity_name")
                                    or "chatgpt_thread"
                                ),
                                "turns": len(session_exchanges),
                                "exchanges": session_exchanges,
                                "source": "entity_journal",
                            })
            except Exception:
                pass

            sessions.sort(key=lambda sess: float(sess.get("timestamp", 0) or 0))
            _soc_state["sessions"] = sessions
            total = len(sessions)
            soc_session_count_lbl.config(text=f"{total} session(s) total")

            signature = [
                (
                    int(float(sess.get("timestamp", 0) or 0)),
                    int(sess.get("turns", 0) or 0),
                    len(list(sess.get("exchanges") or [])),
                    str(sess.get("topic") or ""),
                    str(sess.get("source", "") or ""),
                )
                for sess in sessions
            ]

            if signature != _soc_state.get("signature"):
                _soc_state["signature"] = signature
                soc_list_box.delete(0, tk.END)
                for sess in reversed(sessions):   # newest first
                    ts   = float(sess.get("timestamp", 0) or 0)
                    ts_s = _dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else "--"
                    trns = int(sess.get("turns", 0) or 0)
                    tpc  = str(sess.get("topic") or "")[:14] or "auto"
                    src  = "J" if str(sess.get("source", "") or "") == "entity_journal" else "S"
                    soc_list_box.insert(tk.END, f"  {ts_s}  {trns}t  {src}:{tpc}")
                if total > 0:
                    selected = _soc_state.get("selected", -1)
                    if selected < 0 or selected >= total:
                        selected = total - 1
                    _soc_state["selected"] = selected
                    list_idx = total - 1 - selected
                    if 0 <= list_idx < total:
                        soc_list_box.selection_clear(0, tk.END)
                        soc_list_box.selection_set(list_idx)
                        _soc_load_transcript(selected)
            elif 0 <= _soc_state.get("selected", -1) < total:
                _soc_load_transcript(_soc_state["selected"])

            # ── Learning summary (from social_learning_log) ───────────────────
            learn_records: list = []
            try:
                if _learn_log_path.exists():
                    learn_records = _jl.loads(_learn_log_path.read_text())
                    if not isinstance(learn_records, list):
                        learn_records = []
            except Exception:
                learn_records = []

            # Sessions run since away mode started (or last 5 if not away)
            cutoff = away_started if away_active else 0.0
            recent_learns = [r for r in learn_records
                             if float(r.get("timestamp", 0) or 0) >= cutoff]
            if not recent_learns:
                recent_learns = learn_records[-5:]

            soc_learn_box.configure(state=tk.NORMAL)
            soc_learn_box.delete("1.0", tk.END)
            if not recent_learns:
                soc_learn_box.insert(tk.END,
                    "No learning records yet. Sessions are documented after each GPT exchange.\n",
                    "dim")
            else:
                label = "SINCE AWAY START" if (away_active and cutoff) else "RECENT SESSIONS"
                soc_learn_box.insert(tk.END, f"── {label} ──\n", "heading")
                for rec in recent_learns[-8:]:
                    ts  = float(rec.get("timestamp", 0) or 0)
                    ts_s = _dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else "--"
                    trns = int(rec.get("turns", 0) or 0)
                    links = int(rec.get("genealogy_links", 0) or 0)
                    oets  = int(rec.get("oets_entries", 0) or 0)
                    fails = rec.get("top_fail_dims") or []
                    fail_str = ", ".join(f"{d}:{s:.2f}" for d, s in fails[:3]) if fails else "—"
                    soc_learn_box.insert(tk.END,
                        f"  {ts_s}  turns={trns}  links={links}  oets={oets}  "
                        f"top_fails=[{fail_str}]\n", "fact")
            soc_learn_box.configure(state=tk.DISABLED)

        except Exception as _e:
            try:
                soc_learn_box.configure(state=tk.NORMAL)
                soc_learn_box.delete("1.0", tk.END)
                soc_learn_box.insert(tk.END, f"[refresh error] {_e}\n", "dim")
                soc_learn_box.configure(state=tk.DISABLED)
            except Exception:
                pass

        root.after(REFRESH_SOCIAL_MS, refresh_social)

    # ========================================================================
    # TAB 7: MANIFOLD  --  axis pressure · ability landscape · identity
    # ========================================================================
    REFRESH_MANIFOLD_MS = 4000

    tab_manifold_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_manifold_outer, text="  Manifold  ")
    tab_manifold = _make_scrollable_inner(tab_manifold_outer)

    # ── Header ───────────────────────────────────────────────────────────────
    mf_hdr = tk.Frame(tab_manifold, bg=BG_PANEL, pady=5, padx=12)
    mf_hdr.pack(fill=tk.X)
    tk.Label(mf_hdr, text="MANIFOLD  &  CONSTRAINT STATE", bg=BG_PANEL,
             fg=ACCENT, font=("Courier New", 11, "bold")).pack(side=tk.LEFT)
    mf_ticks_lbl = tk.Label(mf_hdr, text="ticks:--  links:--  abilities:--",
                             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 9))
    mf_ticks_lbl.pack(side=tk.RIGHT)

    # ── Main split ───────────────────────────────────────────────────────────
    mf_body = tk.Frame(tab_manifold, bg=BG)
    mf_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # Left: axis pressure radar
    mf_left = tk.Frame(mf_body, bg=BG_PANEL, bd=0)
    mf_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    fig_mf, ax_mf = plt.subplots(figsize=(3.6, 3.6), subplot_kw={"polar": True},
                                  facecolor=BG_PANEL)
    canvas_mf = FigureCanvasTkAgg(fig_mf, master=mf_left)
    canvas_mf.get_tk_widget().configure(bg=BG_PANEL, highlightthickness=0)
    canvas_mf.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Middle: ability distribution
    mf_mid = tk.Frame(mf_body, bg=BG_PANEL, bd=0)
    mf_mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    tk.Label(mf_mid, text="ABILITY LANDSCAPE", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(pady=(6, 2))

    mf_ab_frame = tk.Frame(mf_mid, bg=BG_PANEL)
    mf_ab_frame.pack(fill=tk.X, padx=8)

    _AXIS_COLORS_MF = {"X": "#06b6d4", "T": "#a78bfa", "N": "#34d399",
                       "B": "#f59e0b", "A": "#ef4444"}
    _AXIS_NAMES_MF  = {"X": "X surface", "T": "T temporal", "N": "N compress",
                       "B": "B deep",    "A": "A core"}

    mf_ab_rows: Dict[str, Dict] = {}
    for ax in ("A", "B", "N", "T", "X"):
        row = tk.Frame(mf_ab_frame, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{ax}", bg=BG_PANEL,
                 fg=_AXIS_COLORS_MF[ax], font=("Courier New", 9, "bold"),
                 width=3, anchor="w").pack(side=tk.LEFT)
        bar_lbl = tk.Label(row, text="░" * 20, bg=BG_PANEL,
                           fg=_AXIS_COLORS_MF[ax], font=("Courier New", 8))
        bar_lbl.pack(side=tk.LEFT, padx=(2, 4))
        cnt_lbl = tk.Label(row, text="--", bg=BG_PANEL,
                           fg=TEXT, font=("Courier New", 9))
        cnt_lbl.pack(side=tk.LEFT)
        mf_ab_rows[ax] = {"bar": bar_lbl, "cnt": cnt_lbl}

    tk.Frame(mf_mid, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=6)

    # Constraint state gauges
    tk.Label(mf_mid, text="CONSTRAINT STATE", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(pady=(0, 4))

    mf_state_frame = tk.Frame(mf_mid, bg=BG_PANEL)
    mf_state_frame.pack(fill=tk.X, padx=8)

    mf_state_rows: Dict[str, tk.Label] = {}
    for key, label in [("dilation", "Time dilation"), ("outlet", "Outlet push"),
                       ("links", "Chain links"),  ("epochs", "Sim epochs"),
                       ("shards", "Understanding")]:
        row = tk.Frame(mf_state_frame, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{label:<16}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=TEXT,
                           font=("Courier New", 9, "bold"))
        val_lbl.pack(side=tk.LEFT)
        mf_state_rows[key] = val_lbl

    # Right: identity panel
    mf_right = tk.Frame(mf_body, bg=BG_PANEL, bd=0)
    mf_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    tk.Label(mf_right, text="IDENTITY ANCHORS", bg=BG_PANEL, fg=ACCENT,
             font=("Courier New", 9, "bold")).pack(pady=(6, 2))

    mf_anchors = tk.Text(mf_right, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
                         wrap=tk.WORD, bd=0, height=8, state=tk.DISABLED)
    mf_anchors.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
    mf_anchors.tag_configure("anchor", foreground=ACCENT2)
    mf_anchors.tag_configure("dim", foreground=TEXT_DIM)

    def refresh_manifold():
        try:
            data = reader.read_manifold()
            ax_orient = data.get("axis_orientation", {})
            ax_abilities = data.get("ax_abilities", {})

            # ── Update header ────────────────────────────────────────────
            ticks = data.get("chain_links", "--")
            gen_dir = _STATE_DIR / "genealogy"
            try:
                ts = json.loads((gen_dir / "tick_state.json").read_text())
                tick_count = ts.get("tick_count", "--")
                last_promo = ts.get("last_promotion_tick", "--")
                mf_ticks_lbl.config(text=(
                    f"ticks:{tick_count:,}  "
                    f"last_promo:{last_promo:,}  "
                    f"links:{ticks}"
                ) if isinstance(tick_count, int) else f"links:{ticks}")
            except Exception:
                mf_ticks_lbl.config(text=f"links:{ticks}")

            # ── Axis pressure radar ──────────────────────────────────────
            ax_mf.clear()
            axes_5 = ["X", "T", "N", "B", "A"]
            vals_5 = [float(ax_orient.get(a, 0.0)) for a in axes_5]
            max_v  = max(vals_5) if vals_5 else 1.0
            norm_v = [v / max(max_v, 0.001) for v in vals_5]
            _radar_chart(fig_mf, ax_mf, axes_5, norm_v,
                         fill_color="#7c3aed", line_color="#a78bfa",
                         title="Constraint Axis Pressure")
            # Overlay raw values on the radar points
            angles_5 = [n / 5.0 * 2 * math.pi for n in range(5)]
            for i, (ang, rv) in enumerate(zip(angles_5, vals_5)):
                ax_mf.annotate(f"{rv:.2f}", xy=(ang, norm_v[i]),
                               xytext=(ang, min(1.05, norm_v[i] + 0.12)),
                               fontsize=7, color=ACCENT2, ha="center")
            canvas_mf.draw()

            # ── Ability distribution bars ────────────────────────────────
            max_ab = max(ax_abilities.values()) if ax_abilities else 1
            for ax, widgets in mf_ab_rows.items():
                cnt = ax_abilities.get(ax, 0)
                filled = int(cnt / max(max_ab, 1) * 20)
                bar_s = chr(0x2588) * filled + chr(0x2591) * (20 - filled)
                widgets["bar"].config(text=bar_s)
                widgets["cnt"].config(text=f"{cnt:,}")

            # ── Constraint state gauges ──────────────────────────────────
            dil = float(data.get("dilation_factor", 1.0))
            dil_state = data.get("dilation_state", "normal")
            dil_color = "#ef4444" if dil_state == "critical" else (
                        "#f59e0b" if dil > 1.5 else TEXT)
            mf_state_rows["dilation"].config(
                text=f"{dil:.3f}x  ({dil_state})", fg=dil_color)

            outlet = float(data.get("outlet_push_fraction", 0.0))
            mf_state_rows["outlet"].config(
                text=f"{outlet:.3f}",
                fg="#f59e0b" if outlet > 0.5 else TEXT)

            mf_state_rows["links"].config(
                text=str(data.get("chain_links", "--")),
                fg=ACCENT2)
            mf_state_rows["epochs"].config(
                text=f"{data.get('simulation_epochs', 0):,}")
            mf_state_rows["shards"].config(
                text=f"{data.get('understanding_shards', 0):,}")

            # ── Identity anchors ─────────────────────────────────────────
            anchors = data.get("identity_anchors", [])
            mf_anchors.configure(state=tk.NORMAL)
            mf_anchors.delete("1.0", tk.END)
            if anchors:
                for i, a in enumerate(anchors[:6], 1):
                    mf_anchors.insert(tk.END, f"[{i}] ", "dim")
                    mf_anchors.insert(tk.END, str(a)[:120] + "\n\n", "anchor")
            else:
                mf_anchors.insert(tk.END, "no identity anchors loaded", "dim")
            mf_anchors.configure(state=tk.DISABLED)

        except Exception as _e:
            try:
                mf_anchors.configure(state=tk.NORMAL)
                mf_anchors.delete("1.0", tk.END)
                mf_anchors.insert(tk.END, f"[error] {_e}", "dim")
                mf_anchors.configure(state=tk.DISABLED)
            except Exception:
                pass
        root.after(REFRESH_MANIFOLD_MS, refresh_manifold)

    # ========================================================================
    # TAB 8: LINEAGE  --  chain depth · events · ability topology
    # ========================================================================
    REFRESH_LINEAGE_MS = 5000

    tab_lineage_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_lineage_outer, text="  Lineage  ")
    tab_lineage = _make_scrollable_inner(tab_lineage_outer)

    # ── Header stats row ─────────────────────────────────────────────────────
    ln_hdr = tk.Frame(tab_lineage, bg=BG_PANEL, pady=5, padx=12)
    ln_hdr.pack(fill=tk.X)
    tk.Label(ln_hdr, text="CONSTRAINT GENEALOGY & LINEAGE", bg=BG_PANEL,
             fg=ACCENT, font=("Courier New", 11, "bold")).pack(side=tk.LEFT)

    ln_stats_frame = tk.Frame(ln_hdr, bg=BG_PANEL)
    ln_stats_frame.pack(side=tk.RIGHT)

    ln_stat_lbls: Dict[str, tk.Label] = {}
    for key, label in [("links", "Links"), ("abilities", "Abilities"),
                       ("ticks", "Ticks"), ("last_promo", "Last Promo")]:
        tk.Label(ln_stats_frame, text=f"  {label}:", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        lbl = tk.Label(ln_stats_frame, text="--", bg=BG_PANEL, fg=ACCENT2,
                       font=("Courier New", 9, "bold"))
        lbl.pack(side=tk.LEFT, padx=(0, 8))
        ln_stat_lbls[key] = lbl

    # ── Main body ────────────────────────────────────────────────────────────
    ln_body = tk.Frame(tab_lineage, bg=BG)
    ln_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # Left: depth distribution chart + ability axis bars
    ln_left = tk.Frame(ln_body, bg=BG_PANEL)
    ln_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    tk.Label(ln_left, text="LINK DEPTH DISTRIBUTION", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(pady=(6, 4))

    ln_depth_frame = tk.Frame(ln_left, bg=BG_PANEL)
    ln_depth_frame.pack(fill=tk.X, padx=10)

    ln_depth_rows: Dict[int, Dict] = {}
    for d in range(1, 8):
        row = tk.Frame(ln_depth_frame, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"D{d}", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Courier New", 9), width=3, anchor="e").pack(side=tk.LEFT)
        bar_lbl = tk.Label(row, text="░" * 25, bg=BG_PANEL,
                           fg="#7c3aed", font=("Courier New", 8))
        bar_lbl.pack(side=tk.LEFT, padx=(3, 4))
        cnt_lbl = tk.Label(row, text="0", bg=BG_PANEL,
                           fg=TEXT, font=("Courier New", 9))
        cnt_lbl.pack(side=tk.LEFT)
        ln_depth_rows[d] = {"bar": bar_lbl, "cnt": cnt_lbl}

    tk.Frame(ln_left, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=10, pady=6)

    tk.Label(ln_left, text="ABILITY AXIS TOPOLOGY", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(pady=(0, 4))

    ln_ax_frame = tk.Frame(ln_left, bg=BG_PANEL)
    ln_ax_frame.pack(fill=tk.X, padx=10)

    ln_ax_rows: Dict[str, Dict] = {}
    for ax, col in [("A", "#ef4444"), ("B", "#f59e0b"), ("N", "#34d399"),
                    ("T", "#a78bfa"), ("X", "#06b6d4")]:
        row = tk.Frame(ln_ax_frame, bg=BG_PANEL)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=f"{ax}", bg=BG_PANEL, fg=col,
                 font=("Courier New", 9, "bold"), width=3, anchor="w").pack(side=tk.LEFT)
        bar_lbl = tk.Label(row, text="░" * 25, bg=BG_PANEL,
                           fg=col, font=("Courier New", 8))
        bar_lbl.pack(side=tk.LEFT, padx=(2, 4))
        cnt_lbl = tk.Label(row, text="--", bg=BG_PANEL, fg=TEXT,
                           font=("Courier New", 9))
        cnt_lbl.pack(side=tk.LEFT)
        ln_ax_rows[ax] = {"bar": bar_lbl, "cnt": cnt_lbl}

    # Right: recent events feed
    ln_right = tk.Frame(ln_body, bg=BG_PANEL)
    ln_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    tk.Label(ln_right, text="RECENT CHAIN EVENTS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(pady=(6, 4))

    ln_events_box = tk.Text(ln_right, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
                            wrap=tk.NONE, bd=0, state=tk.DISABLED)
    ln_events_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
    ln_events_box.tag_configure("tick",    foreground=TEXT_DIM)
    ln_events_box.tag_configure("axis_A",  foreground="#ef4444")
    ln_events_box.tag_configure("axis_B",  foreground="#f59e0b")
    ln_events_box.tag_configure("axis_N",  foreground="#34d399")
    ln_events_box.tag_configure("axis_T",  foreground="#a78bfa")
    ln_events_box.tag_configure("axis_X",  foreground="#06b6d4")
    ln_events_box.tag_configure("relief",  foreground="#22c55e")
    ln_events_box.tag_configure("cost",    foreground="#f97316")

    def refresh_lineage():
        try:
            data = reader.read_lineage()
            ts = data.get("tick_state", {})

            # ── Stats header ─────────────────────────────────────────────
            ln_stat_lbls["links"].config(text=f"{data['total_links']:,}")
            ln_stat_lbls["abilities"].config(text=f"{data['total_abilities']:,}")
            tick_count = ts.get("tick_count", 0)
            last_promo = ts.get("last_promotion_tick", 0)
            ln_stat_lbls["ticks"].config(text=f"{tick_count:,}")
            since_promo = tick_count - last_promo if isinstance(tick_count, int) else 0
            ln_stat_lbls["last_promo"].config(
                text=f"t{last_promo:,}  (+{since_promo:,})",
                fg="#f59e0b" if since_promo > 5000 else ACCENT2)

            # ── Depth bars ───────────────────────────────────────────────
            depth_dist = data.get("depth_dist", {})
            max_depth_cnt = max(depth_dist.values()) if depth_dist else 1
            for d, widgets in ln_depth_rows.items():
                cnt = depth_dist.get(d, 0)
                filled = int(cnt / max(max_depth_cnt, 1) * 25)
                widgets["bar"].config(text=chr(0x2588) * filled + chr(0x2591) * (25 - filled))
                widgets["cnt"].config(text=str(cnt) if cnt else "0",
                                      fg=ACCENT2 if cnt > 0 else TEXT_DIM)

            # ── Axis topology bars ────────────────────────────────────────
            ax_dist = data.get("ax_dist", {})
            max_ax = max(ax_dist.values()) if ax_dist else 1
            for ax, widgets in ln_ax_rows.items():
                cnt = ax_dist.get(ax, 0)
                filled = int(cnt / max(max_ax, 1) * 25)
                widgets["bar"].config(text=chr(0x2588) * filled + chr(0x2591) * (25 - filled))
                widgets["cnt"].config(text=f"{cnt:,}" if cnt else "--")

            # ── Events feed ──────────────────────────────────────────────
            events = data.get("recent_events", [])
            ln_events_box.configure(state=tk.NORMAL)
            ln_events_box.delete("1.0", tk.END)
            if events:
                for ev in reversed(events[-15:]):
                    try:
                        tick   = ev.get("tick", "?")
                        dom_ax = str(ev.get("dominant_relief_axis", "?") or "?")
                        p_bef  = ev.get("pressure_before", {})
                        p_aft  = ev.get("pressure_after",  {})
                        relief = ev.get("relief", {})
                        notes  = str(ev.get("notes", "") or "")[:40]

                        # Safe float extraction — some event types store dicts or None
                        def _safe_f(val, default=0.0):
                            try:
                                return float(val)
                            except Exception:
                                return default

                        cost_raw = ev.get("trace_cost_total", 0.0)
                        if isinstance(cost_raw, dict):
                            cost = sum(_safe_f(v) for v in cost_raw.values())
                        else:
                            cost = _safe_f(cost_raw)

                        # Pressure delta on dominant axis
                        ax_bef_raw = p_bef.get(dom_ax, 0.0) if isinstance(p_bef, dict) else 0.0
                        ax_aft_raw = p_aft.get(dom_ax, 0.0) if isinstance(p_aft, dict) else 0.0
                        ax_bef = _safe_f(ax_bef_raw)
                        ax_aft = _safe_f(ax_aft_raw)

                        # Total relief (sum of scalar values only)
                        rel_v = 0.0
                        if isinstance(relief, dict):
                            for rv in relief.values():
                                rel_v += _safe_f(rv)
                        rel_v = round(rel_v, 4)

                        tick_str = f"{tick:>7}" if isinstance(tick, int) else f"{str(tick):>7}"
                        ln_events_box.insert(tk.END, f"t{tick_str}  ", "tick")
                        ax_tag = f"axis_{dom_ax}" if dom_ax in ("X", "T", "N", "B", "A") else "tick"
                        ln_events_box.insert(tk.END, f"[{dom_ax}]", ax_tag)
                        ln_events_box.insert(tk.END,
                            f"  {ax_bef:.3f}→{ax_aft:.3f}  ", "tick")
                        ln_events_box.insert(tk.END, f"relief:{rel_v:+.4f}", "relief")
                        ln_events_box.insert(tk.END, f"  cost:{cost:.3f}", "cost")
                        if notes:
                            ln_events_box.insert(tk.END, f"  {notes}", "tick")
                        ln_events_box.insert(tk.END, "\n")
                    except Exception:
                        ln_events_box.insert(tk.END, f"[event parse error]\n", "tick")
            else:
                ln_events_box.insert(tk.END, "no lineage events yet\n", "tick")
            ln_events_box.configure(state=tk.DISABLED)

        except Exception as _e:
            try:
                ln_events_box.configure(state=tk.NORMAL)
                ln_events_box.delete("1.0", tk.END)
                ln_events_box.insert(tk.END, f"[error] {_e}\n", "tick")
                ln_events_box.configure(state=tk.DISABLED)
            except Exception:
                pass
        root.after(REFRESH_LINEAGE_MS, refresh_lineage)

    # ── Diagnostics tab ───────────────────────────────────────────────────────
    # Two sections:
    #   TOP — Live Runtime Tracker: reads aurora_state/ JSON files every 4s,
    #          flags anomalies (overhead stuck, gate rejects, deferrals, etc.)
    #          with WARN/CRIT severity.  Zero cost to Aurora — pure file reads.
    #   BTM — Code Analysis: on-demand QuasiArch scan of active scripts;
    #          proposals can be approved → Enforcer deployed.

    DIAG_REPORT  = _STATE_DIR / "quasiarch_diag_report.json"
    DIAG_SCRIPT  = _BASE_DIR  / "quasiarch_diag.py"
    REFRESH_DIAG_MS = 4000

    tab_diag_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_diag_outer, text="  Diagnostics  ")
    tab_diag = _make_scrollable_inner(tab_diag_outer)

    # ── header ───────────────────────────────────────────────────────────────
    dg_hdr = tk.Frame(tab_diag, bg=BG_PANEL, pady=5, padx=12)
    dg_hdr.pack(fill=tk.X)
    tk.Label(dg_hdr, text="SYSTEM DIAGNOSTICS", bg=BG_PANEL,
             fg=ACCENT, font=("Courier New", 11, "bold")).pack(side=tk.LEFT)
    dg_ts_lbl = tk.Label(dg_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                          font=("Courier New", 8))
    dg_ts_lbl.pack(side=tk.LEFT, padx=10)
    tk.Label(dg_hdr, text="operator health checks  ·  separate from Aurora room state",
             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT, padx=4)

    # ── TOP: live runtime check panel ────────────────────────────────────────
    dg_live_frame = tk.Frame(tab_diag, bg=BG_PANEL)
    dg_live_frame.pack(fill=tk.X, padx=8, pady=(4, 2))
    tk.Label(dg_live_frame, text="LIVE CHECKS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 2))

    dg_checks_box = tk.Text(
        dg_live_frame, bg=BG_LOG, fg=TEXT, font=("Courier New", 9),
        height=12, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    dg_checks_box.pack(fill=tk.X, padx=6, pady=(0, 6))
    dg_checks_box.tag_configure("ok",   foreground="#22c55e")
    dg_checks_box.tag_configure("warn", foreground="#f59e0b")
    dg_checks_box.tag_configure("crit", foreground="#ef4444")
    dg_checks_box.tag_configure("dim",  foreground=TEXT_DIM)
    dg_checks_box.tag_configure("head", foreground=ACCENT2)

    # ── MIDDLE: code-scan body ────────────────────────────────────────────────
    dg_scan_hdr = tk.Frame(tab_diag, bg=BG_PANEL, pady=4, padx=12)
    dg_scan_hdr.pack(fill=tk.X, padx=8, pady=(2, 0))
    tk.Label(dg_scan_hdr, text="CODE ANALYSIS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    dg_scan_status = tk.Label(dg_scan_hdr, text="  no scan yet", bg=BG_PANEL,
                               fg=TEXT_DIM, font=("Courier New", 8))
    dg_scan_status.pack(side=tk.LEFT, padx=6)
    dg_scan_btn = tk.Button(dg_scan_hdr, text="▶  Run Scan", bg="#1e1b4b", fg=ACCENT2,
                            font=("Courier New", 9, "bold"),
                            relief=tk.FLAT, padx=8, pady=2, cursor="hand2")
    dg_scan_btn.pack(side=tk.RIGHT, padx=4)
    dg_sweep_btn = tk.Button(dg_scan_hdr, text="⚙  Sweep", bg="#1a2e1a", fg="#4ade80",
                             font=("Courier New", 9, "bold"),
                             relief=tk.FLAT, padx=8, pady=2, cursor="hand2")
    dg_sweep_btn.pack(side=tk.RIGHT, padx=4)

    dg_body = tk.Frame(tab_diag, bg=BG)
    dg_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)

    # Left: proposals list
    dg_left = tk.Frame(dg_body, bg=BG_PANEL)
    dg_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
    dg_list_frame = tk.Frame(dg_left, bg=BG_PANEL)
    dg_list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
    dg_listbox = tk.Listbox(
        dg_list_frame, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        selectbackground=ACCENT, selectforeground=BG, relief=tk.FLAT,
        borderwidth=0, highlightthickness=0, activestyle="none",
    )
    dg_list_sb = ttk.Scrollbar(dg_list_frame, orient="vertical",
                                command=dg_listbox.yview)
    dg_listbox.configure(yscrollcommand=dg_list_sb.set)
    dg_list_sb.pack(side=tk.RIGHT, fill=tk.Y)
    dg_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _dg_on_listbox_select(event=None):
        sel = dg_listbox.curselection()
        if sel:
            idx = int(sel[0])
            _dg_proposal_idx[0] = idx
            _dg_show_detail(idx)

    dg_listbox.bind("<<ListboxSelect>>", _dg_on_listbox_select)

    # Right: detail + deploy
    dg_right = tk.Frame(dg_body, bg=BG_PANEL, width=400)
    dg_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
    dg_right.pack_propagate(False)
    tk.Label(dg_right, text="PROPOSAL DETAIL", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 8, "bold")).pack(pady=(4, 1))
    dg_detail_box = tk.Text(
        dg_right, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.WORD,
    )
    # Pack buttons BEFORE the expanding text box so they anchor to the bottom
    dg_btn_row = tk.Frame(dg_right, bg=BG_PANEL)
    dg_btn_row.pack(side=tk.BOTTOM, pady=6)
    dg_deploy_btn = tk.Button(
        dg_btn_row, text="✔  Deploy & Commit",
        bg="#1e1b4b", fg="#ef4444", font=("Courier New", 9, "bold"),
        relief=tk.FLAT, padx=8, pady=4, cursor="hand2", state=tk.DISABLED,
    )
    dg_deploy_btn.pack(side=tk.LEFT, padx=(0, 4))
    dg_reverse_btn = tk.Button(
        dg_btn_row, text="↩  Reverse & Try Next",
        bg="#1e1b4b", fg="#f59e0b", font=("Courier New", 9, "bold"),
        relief=tk.FLAT, padx=8, pady=4, cursor="hand2", state=tk.DISABLED,
    )
    dg_reverse_btn.pack(side=tk.LEFT)
    dg_detail_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 3))
    dg_detail_box.tag_configure("key",  foreground=ACCENT2)
    dg_detail_box.tag_configure("val",  foreground=TEXT)
    dg_detail_box.tag_configure("hint", foreground="#34d399")
    dg_detail_box.tag_configure("warn", foreground="#f59e0b")

    # Bottom log
    dg_log_frame = tk.Frame(tab_diag, bg=BG_PANEL)
    dg_log_frame.pack(fill=tk.X, padx=8, pady=(0, 4))
    tk.Label(dg_log_frame, text="ENFORCER OUTPUT", bg=BG_PANEL, fg=TEXT_DIM,
             font=("Courier New", 8, "bold")).pack(anchor="w", padx=6, pady=(3, 0))
    dg_log_box = tk.Text(
        dg_log_frame, bg=BG_LOG, fg=TEXT_DIM, font=("Courier New", 8),
        height=5, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
    )
    dg_log_box.pack(fill=tk.X, padx=6, pady=(2, 4))

    # ── shared state ─────────────────────────────────────────────────────────
    _dg_proposals:      list  = []
    _dg_proposal_idx:   list  = [0]     # mutable so closures can update it
    _dg_scan_proc:      list  = [None]
    _dg_last_enforced:  list  = [None]  # dict: {file, backup, commit_sha, proposal}

    _ENFORCER_LEDGER = Path.home() / ".quasiarch" / "enforcer_state" / "enforcer_ledger.json"

    def _dg_log(msg: str) -> None:
        try:
            dg_log_box.configure(state=tk.NORMAL)
            dg_log_box.insert(tk.END, msg + "\n")
            dg_log_box.see(tk.END)
            dg_log_box.configure(state=tk.DISABLED)
        except Exception:
            pass

    def _dg_clear_log() -> None:
        try:
            dg_log_box.configure(state=tk.NORMAL)
            dg_log_box.delete("1.0", tk.END)
            dg_log_box.configure(state=tk.DISABLED)
        except Exception:
            pass

    # ── live runtime checks ───────────────────────────────────────────────────

    def _run_live_checks() -> list:
        """
        Pure file reads against aurora_state/ — returns list of
        (severity, label, detail) tuples.  severity: 'ok'|'warn'|'crit'.
        """
        checks = []

        def _read_json(name):
            try:
                with open(_STATE_DIR / name, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

        def _check(label, ok, warn_msg="", crit=False):
            sev = "ok" if ok else ("crit" if crit else "warn")
            checks.append((sev, label, warn_msg if not ok else ""))

        # ── daemon_status.json ────────────────────────────────────────────────
        ds = _read_json("daemon_status.json")
        gov_mode = ds.get("runtime_governor_mode", "?")
        _check("Governor mode",
               gov_mode not in ("survival", "minimal"),
               f"mode={gov_mode} — tasks may be deferred", crit=(gov_mode == "minimal"))

        axes = ds.get("runtime_governor_axes", {})
        n_ax = axes.get("N", 1.0)
        _check("N-axis budget",
               n_ax > 0.30,
               f"N={n_ax:.3f} — corpus/study tasks likely blocked", crit=(n_ax < 0.15))

        blocked = ds.get("runtime_recent_blocked", [])
        _check("No blocked tasks", len(blocked) == 0,
               f"{len(blocked)} task(s) blocked: " +
               ", ".join(b.get("task","?") for b in blocked[:3]))

        heat = ds.get("heat", "?")
        _check("Heat OK", heat in ("COOL", "NORMAL", "warm"),
               f"heat={heat}", crit=(heat == "CRITICAL"))

        host = ds.get("runtime_host", {})
        mem_p = host.get("mem_pressure", 0.0)
        _check("Memory OK", mem_p < 0.80,
               f"mem_pressure={mem_p:.2f} — x_memory_floor may block tasks",
               crit=(mem_p > 0.90))

        load_r = host.get("load_ratio", 0.0)
        _check("CPU load OK", load_r < 1.5,
               f"load_ratio={load_r:.2f} — governor may throttle", crit=(load_r > 2.0))

        disk = host.get("disk_free_ratio", 1.0)
        _check("Disk space", disk > 0.10,
               f"disk_free={disk:.1%}", crit=(disk < 0.05))

        for fd in ds.get("telemetry_fails", []):
            dim = fd.get("dim","?"); sev_f = fd.get("severity",0.0)
            _check(f"QAO {dim}", sev_f < 0.70,
                   f"severity={sev_f:.3f}", crit=(sev_f > 0.85))

        # ── adapter_hints.json ────────────────────────────────────────────────
        hints = _read_json("adapter_hints.json")
        gr = hints.get("genealogy_gate_relief", {})
        _check("Gate-5 relief active",
               not gr.get("active", False),
               f"Gate-5 relief ACTIVE (factor={gr.get('relief_factor',1.0):.2f}) — overhead stuck")

        lr_active = hints.get("leverage_redirect_active", False)
        _check("Leverage redirect active",
               not lr_active,
               "leverage redirect ON — evolver biased toward B/A axes")

        # ── surface_pressure_log (tail 300 lines) — overhead ratio ────────────
        try:
            surf_path = _STATE_DIR / "surface_pressure_log.jsonl"
            if surf_path.exists():
                counts = {"X": 0, "T": 0, "N": 0, "B": 0, "A": 0}
                chunk = 32768; buf = b""; lines_found = []
                with open(surf_path, "rb") as f:
                    f.seek(0, 2); pos = f.tell()
                    while len(lines_found) < 300 and pos > 0:
                        read_sz = min(chunk, pos); pos -= read_sz
                        f.seek(pos); buf = f.read(read_sz) + buf
                        parts = buf.split(b"\n"); buf = parts[0]
                        for p in reversed(parts[1:]):
                            p = p.strip()
                            if p: lines_found.append(p)
                            if len(lines_found) >= 300: break
                for raw in lines_found[:300]:
                    try:
                        obj = json.loads(raw)
                        for ax in (obj.get("expected_axes") or []):
                            if ax in counts: counts[ax] += 1
                    except Exception:
                        pass
                total = sum(counts.values())
                if total > 0:
                    overhead = (counts.get("X", 0) + counts.get("T", 0)) / total
                    _check("Overhead ratio",
                           overhead < 0.80,
                           f"X+T = {overhead:.1%} of last {total} surfaces — LeverageReliefValve may activate",
                           crit=(overhead > 0.95))
                    lev = (counts.get("B", 0) + counts.get("A", 0)) / max(1, total)
                    checks.append(("dim", "Surface axis split",
                                   f"X:{counts['X']} T:{counts['T']} "
                                   f"N:{counts['N']} B:{counts['B']} A:{counts['A']}"))
        except Exception:
            pass

        # ── pressure_experiences Gate counts ──────────────────────────────────
        try:
            exp_path = _STATE_DIR / "pressure_experiences.jsonl"
            if exp_path.exists():
                gate4 = gate5 = 0
                chunk = 65536; buf = b""; lines_found = []
                with open(exp_path, "rb") as f:
                    f.seek(0, 2); pos = f.tell()
                    while len(lines_found) < 500 and pos > 0:
                        read_sz = min(chunk, pos); pos -= read_sz
                        f.seek(pos); buf = f.read(read_sz) + buf
                        parts = buf.split(b"\n"); buf = parts[0]
                        for p in reversed(parts[1:]):
                            p = p.strip()
                            if p: lines_found.append(p)
                            if len(lines_found) >= 500: break
                for raw in lines_found[:500]:
                    try:
                        obj = json.loads(raw)
                        g = (obj.get("consequence") or {}).get("gate", 0)
                        if g == 4: gate4 += 1
                        elif g == 5: gate5 += 1
                    except Exception:
                        pass
                total = gate4 + gate5
                if total > 0:
                    g5_ratio = gate5 / total
                    _check("Gate-5 reject ratio",
                           g5_ratio < 0.90,
                           f"Gate-5 = {g5_ratio:.1%} of last {total} genealogy events",
                           crit=(g5_ratio > 0.97))
                    checks.append(("dim", "Gate rejects (last 500)",
                                   f"Gate4={gate4}  Gate5={gate5}"))
        except Exception:
            pass

        # ── links.json ────────────────────────────────────────────────────────
        try:
            lp = _BASE_DIR / "aurora_runtime_output" / "links.json"
            if not lp.exists():
                lp = _BASE_DIR / "links.json"
            if lp.exists():
                with open(lp, encoding="utf-8") as f:
                    ldata = json.load(f)
                checks.append(("dim", "Chain links on disk",
                                f"{len(ldata)} links in links.json"))
        except Exception:
            pass

        return checks

    def _refresh_diag_live() -> None:
        try:
            checks = _run_live_checks()
            dg_ts_lbl.configure(text=time.strftime("updated %H:%M:%S"))
            dg_checks_box.configure(state=tk.NORMAL)
            dg_checks_box.delete("1.0", tk.END)
            ok_n = warn_n = crit_n = 0
            for sev, label, detail in checks:
                if sev == "ok":
                    icon = "✓"; ok_n += 1
                elif sev == "crit":
                    icon = "✗"; crit_n += 1
                elif sev == "warn":
                    icon = "⚠"; warn_n += 1
                else:
                    icon = "·"
                dg_checks_box.insert(tk.END, f"  {icon}  ", sev)
                dg_checks_box.insert(tk.END, f"{label:<30}", sev if sev != "dim" else "dim")
                if detail:
                    dg_checks_box.insert(tk.END, f"  {detail}", "dim")
                dg_checks_box.insert(tk.END, "\n")
            summary_sev = "crit" if crit_n else ("warn" if warn_n else "ok")
            dg_checks_box.insert(tk.END,
                f"\n  Summary: {ok_n} OK  {warn_n} WARN  {crit_n} CRIT\n",
                summary_sev)
            dg_checks_box.configure(state=tk.DISABLED)
        except Exception:
            pass
        root.after(REFRESH_DIAG_MS, _refresh_diag_live)

    # ── code-scan (on-demand) ─────────────────────────────────────────────────

    def _dg_load_report() -> None:
        nonlocal _dg_proposals
        if not DIAG_REPORT.exists():
            return
        try:
            with open(DIAG_REPORT, encoding="utf-8") as f:
                report = json.load(f)
        except Exception:
            return
        # Exclude sweep proposals — those live on the Governor tab only
        all_props = report.get("proposals", [])
        _dg_proposals = [
            p for p in all_props
            if not str(p.get("issue_archetype", "")).startswith("sweep:")
        ]
        generated = report.get("generated_at", "")[:16]
        dg_scan_status.configure(
            text=f"  {generated}  |  {len(_dg_proposals)} proposals",
            fg=TEXT_DIM if _dg_proposals else "#22c55e",
        )
        dg_listbox.delete(0, tk.END)
        _dg_proposal_idx[0] = 0
        for p in _dg_proposals:
            arch = p.get("issue_archetype", "?")[:20]
            tgt  = p.get("target", "?").split(":")[-1][:26]
            conf = p.get("confidence", 0.0)
            dg_listbox.insert(tk.END, f"  {conf:.2f}  [{arch}]  {tgt}")
        if _dg_proposals:
            _dg_select_proposal(0)

    def _dg_show_detail(idx: int) -> None:
        if idx < 0 or idx >= len(_dg_proposals):
            return
        p = _dg_proposals[idx]
        dg_detail_box.configure(state=tk.NORMAL)
        dg_detail_box.delete("1.0", tk.END)

        def _row(k, v, tag="val"):
            dg_detail_box.insert(tk.END, f"{k:<16}", "key")
            dg_detail_box.insert(tk.END, f"{v}\n", tag)

        _row("archetype", p.get("issue_archetype", "?"))
        _row("strategy", p.get("primary_strategy", "?"))
        _row("target", p.get("target", "?"))
        _row("file:line", f"{p.get('file','?')}:{p.get('line','?')}")
        _row("why flagged", p.get("match_reason", "?"))
        _row("confidence", f"{p.get('confidence', 0.0):.3f}")
        dg_detail_box.insert(tk.END, "\n")
        _row("action", p.get("proposed_action", ""), "warn")
        hint = p.get("code_hint", "")
        if hint:
            dg_detail_box.insert(tk.END, "\ncode hint:\n", "key")
            dg_detail_box.insert(tk.END, f"{hint}\n", "hint")
        dg_detail_box.configure(state=tk.DISABLED)
        dg_deploy_btn.configure(state=tk.NORMAL)

    def _dg_on_select(event=None) -> None:
        sel = dg_listbox.curselection()
        if sel:
            _dg_show_detail(sel[0])

    dg_listbox.bind("<<ListboxSelect>>", _dg_on_select)

    def _dg_run_scan() -> None:
        if _dg_scan_proc[0] is not None and _dg_scan_proc[0].poll() is None:
            _dg_log("[scan already running]")
            return
        _dg_clear_log()
        dg_scan_status.configure(text="  scanning…", fg="#f59e0b")
        dg_scan_btn.configure(state=tk.DISABLED, text="⏳ Scanning…")
        _dg_log(f"[{time.strftime('%H:%M:%S')}]  Starting QuasiArch code scan…")

        def _run():
            import subprocess, sys as _sys
            try:
                proc = subprocess.Popen(
                    [_sys.executable, str(DIAG_SCRIPT), "--quiet"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, cwd=str(_BASE_DIR),
                )
                _dg_scan_proc[0] = proc
                for line in proc.stdout:
                    root.after(0, lambda l=line: _dg_log(l.rstrip()))
                proc.wait()
                root.after(0, _dg_scan_done, proc.returncode)
            except Exception as exc:
                root.after(0, lambda: _dg_log(f"[scan error] {exc}"))
                root.after(0, _dg_scan_done, -1)

        threading.Thread(target=_run, daemon=True, name="diag-scan").start()

    def _dg_scan_done(rc: int) -> None:
        dg_scan_btn.configure(state=tk.NORMAL, text="▶  Run Scan")
        if rc == 0:
            _dg_log("[scan complete]"); _dg_load_report()
        else:
            dg_scan_status.configure(text="  scan failed", fg="#ef4444")
            _dg_log(f"[scan exited {rc}]")

    def _dg_select_proposal(idx: int) -> None:
        """Select proposal at index, update detail panel."""
        if 0 <= idx < len(_dg_proposals):
            dg_listbox.selection_clear(0, tk.END)
            dg_listbox.selection_set(idx)
            dg_listbox.see(idx)
            _dg_proposal_idx[0] = idx
            _dg_show_detail(idx)

    def _dg_read_last_ledger_record() -> Optional[dict]:
        """Read the most recent enforcement record from the ledger."""
        try:
            if _ENFORCER_LEDGER.exists():
                with open(_ENFORCER_LEDGER, encoding="utf-8") as f:
                    records = json.load(f)
                if records:
                    return records[-1]
        except Exception:
            pass
        return None

    def _dg_deploy(proposal_idx: Optional[int] = None) -> None:
        """Deploy enforcer for proposal at proposal_idx (or current selection)."""
        idx = proposal_idx if proposal_idx is not None else _dg_proposal_idx[0]
        if idx < 0 or idx >= len(_dg_proposals):
            _dg_log("[no proposal selected]")
            return
        p = _dg_proposals[idx]
        _dg_proposal_idx[0] = idx
        _dg_select_proposal(idx)
        _dg_log(f"\n[{time.strftime('%H:%M:%S')}]  Enforcer → {p.get('target','')}  "
                f"(proposal {idx+1}/{len(_dg_proposals)})")
        _dg_log(f"  {p.get('proposed_action','')[:80]}")
        _dg_log("  bridge.feedback() DISABLED — Aurora chamber untouched.")
        dg_deploy_btn.configure(state=tk.DISABLED, text="⏳ Enforcing…")
        dg_reverse_btn.configure(state=tk.DISABLED)

        def _run():
            import subprocess, json as _json, tempfile, os
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as tf:
                    _json.dump(p, tf, indent=2); tmp_path = tf.name
                env = dict(os.environ)
                env["QUASIARCH_HOME"] = str(Path.home() / ".quasiarch")
                # auto_commit=True (no --no-commit): enforcer commits if apply+verify passes
                proc = subprocess.Popen(
                    ["qae", "enforce", tmp_path, "--show-diff"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, cwd=str(_BASE_DIR), env=env,
                )
                for line in proc.stdout:
                    root.after(0, lambda l=line: _dg_log(l.rstrip()))
                proc.wait(); os.unlink(tmp_path)
                root.after(0, lambda rc=proc.returncode: _dg_deploy_done(rc, p))
            except FileNotFoundError:
                root.after(0, lambda: _dg_log(
                    "[warn] 'qae' not on PATH — run: cd ~/quasiarch/enforcer && pip install ."))
                root.after(0, lambda: dg_deploy_btn.configure(
                    state=tk.NORMAL, text="✔  Deploy & Commit"))
            except Exception as exc:
                root.after(0, lambda: _dg_log(f"[enforcer error] {exc}"))
                root.after(0, lambda: _dg_deploy_done(-1, p))

        threading.Thread(target=_run, daemon=True, name="diag-deploy").start()

    def _dg_deploy_done(rc: int, proposal: dict) -> None:
        """Called after enforcer subprocess exits. Captures ledger state."""
        dg_deploy_btn.configure(state=tk.NORMAL, text="✔  Deploy & Commit")
        if rc == 0:
            # Read the ledger to get enforcement details (backup path, commit_sha)
            rec = _dg_read_last_ledger_record()
            target_file = proposal.get("file", "")
            backup = str(_BASE_DIR / target_file) + ".qae_backup" if target_file else ""
            _dg_last_enforced[0] = {
                "file":       str(_BASE_DIR / target_file) if target_file else "",
                "backup":     backup,
                "commit_sha": (rec or {}).get("commit_sha", ""),
                "status":     (rec or {}).get("status", "applied"),
                "proposal":   proposal,
                "idx":        _dg_proposal_idx[0],
            }
            status = (rec or {}).get("status", "applied")
            _dg_log(f"[enforcer: {status}]" +
                    (f" sha={_dg_last_enforced[0]['commit_sha'][:8]}"
                     if _dg_last_enforced[0]["commit_sha"] else ""))
            dg_reverse_btn.configure(state=tk.NORMAL)
            # Remove proposal from list once applied or committed
            if status in ("committed", "applied"):
                rm_idx = _dg_proposal_idx[0]
                if 0 <= rm_idx < len(_dg_proposals):
                    _dg_proposals.pop(rm_idx)
                    dg_listbox.delete(rm_idx)
                    # Select next proposal (or previous if at end)
                    next_idx = min(rm_idx, len(_dg_proposals) - 1)
                    if next_idx >= 0:
                        _dg_proposal_idx[0] = next_idx
                        dg_listbox.selection_set(next_idx)
                        dg_listbox.see(next_idx)
                        _dg_show_detail(next_idx)
                    else:
                        _dg_proposal_idx[0] = 0
                        dg_deploy_btn.configure(state=tk.DISABLED)
            # Feed verdict to Researcher → ClaudeTrainer learns from each fix
            def _run_learn():
                try:
                    subprocess.run(
                        [sys.executable, str(_BASE_DIR / "quasiarch_diag.py"), "--learn", "--quiet"],
                        cwd=str(_BASE_DIR), capture_output=True,
                    )
                except Exception:
                    pass
            threading.Thread(target=_run_learn, daemon=True, name="diag-learn").start()
        else:
            # Check ledger: if the fix was already in place, remove it silently
            rec = _dg_read_last_ledger_record()
            err = (rec or {}).get("error", "")
            already_applied = "unchanged content" in err.lower() or "already" in err.lower()
            if already_applied:
                _dg_log("[enforcer: already fixed — removing from list]")
                rm_idx = _dg_proposal_idx[0]
                if 0 <= rm_idx < len(_dg_proposals):
                    _dg_proposals.pop(rm_idx)
                    dg_listbox.delete(rm_idx)
                    next_idx = min(rm_idx, len(_dg_proposals) - 1)
                    if next_idx >= 0:
                        _dg_proposal_idx[0] = next_idx
                        dg_listbox.selection_set(next_idx)
                        dg_listbox.see(next_idx)
                        _dg_show_detail(next_idx)
                    else:
                        _dg_proposal_idx[0] = 0
                        dg_deploy_btn.configure(state=tk.DISABLED)
            else:
                _dg_log(f"[enforcer: exited {rc} — fix not applied]")
            # Still allow reverse if there's a previous enforcement to undo
            if _dg_last_enforced[0]:
                dg_reverse_btn.configure(state=tk.NORMAL)

    def _dg_reverse() -> None:
        """
        Reverse the last applied fix and try the next proposal.
        Strategy:
          1. If .qae_backup exists → restore it, git add+commit "revert: ..."
          2. Else if commit_sha known → git revert <sha> --no-edit
          3. Advance proposal index, auto-select next, enable deploy.
        """
        info = _dg_last_enforced[0]
        if not info:
            _dg_log("[reverse] no prior enforcement to reverse")
            return

        _dg_log(f"\n[{time.strftime('%H:%M:%S')}]  Reversing last fix…")
        dg_reverse_btn.configure(state=tk.DISABLED, text="⏳ Reversing…")
        dg_deploy_btn.configure(state=tk.DISABLED)

        def _run():
            import subprocess, os, shutil
            reversed_ok = False
            file_path   = info.get("file", "")
            backup      = info.get("backup", "")
            commit_sha  = info.get("commit_sha", "")

            # Attempt 1: restore backup
            if backup and os.path.exists(backup):
                try:
                    shutil.copy2(backup, file_path)
                    os.remove(backup)
                    # git add + revert commit
                    rel = os.path.relpath(file_path, str(_BASE_DIR))
                    msg = (f"revert: undo enforcer fix for "
                           f"{info['proposal'].get('target','?')}\n\n"
                           f"Reverting enforcer fix applied by QuasiArch — "
                           f"trying next proposal in loop.")
                    subprocess.run(["git", "add", rel], cwd=str(_BASE_DIR),
                                   capture_output=True)
                    subprocess.run(["git", "commit", "-m", msg], cwd=str(_BASE_DIR),
                                   capture_output=True)
                    root.after(0, lambda: _dg_log("[reverse] backup restored + revert committed"))
                    reversed_ok = True
                except Exception as exc:
                    root.after(0, lambda: _dg_log(f"[reverse] backup restore failed: {exc}"))

            # Attempt 2: git revert if backup gone but commit known
            if not reversed_ok and commit_sha:
                try:
                    res = subprocess.run(
                        ["git", "revert", commit_sha, "--no-edit"],
                        cwd=str(_BASE_DIR), capture_output=True, text=True,
                    )
                    if res.returncode == 0:
                        root.after(0, lambda: _dg_log(f"[reverse] git revert {commit_sha[:8]} OK"))
                        reversed_ok = True
                    else:
                        root.after(0, lambda: _dg_log(
                            f"[reverse] git revert failed: {res.stderr.strip()[:120]}"))
                except Exception as exc:
                    root.after(0, lambda: _dg_log(f"[reverse] git revert error: {exc}"))

            if not reversed_ok:
                root.after(0, lambda: _dg_log(
                    "[reverse] could not reverse — no backup and no commit SHA. "
                    "Check file manually."))

            root.after(0, _dg_after_reverse)

        threading.Thread(target=_run, daemon=True, name="diag-reverse").start()

    def _dg_after_reverse() -> None:
        """Advance to next proposal and prepare for next deploy attempt."""
        dg_reverse_btn.configure(state=tk.DISABLED, text="↩  Reverse & Try Next")
        _dg_last_enforced[0] = None

        next_idx = _dg_proposal_idx[0] + 1
        if next_idx < len(_dg_proposals):
            _dg_log(f"[loop] advancing to proposal {next_idx+1}/{len(_dg_proposals)}")
            _dg_select_proposal(next_idx)
            dg_deploy_btn.configure(state=tk.NORMAL, text="✔  Deploy & Commit")
        else:
            _dg_log("[loop] all proposals exhausted — triggering re-scan…")
            dg_deploy_btn.configure(state=tk.DISABLED)
            _dg_run_scan()

    dg_scan_btn.configure(command=_dg_run_scan)
    dg_deploy_btn.configure(command=_dg_deploy)
    dg_reverse_btn.configure(command=_dg_reverse)

    def _dg_run_sweep() -> None:
        """Launch a parameter sweep in a background thread."""
        _dg_clear_log()
        dg_scan_status.configure(text="  sweeping…", fg="#4ade80")
        dg_sweep_btn.configure(state=tk.DISABLED, text="⏳ Sweeping…")
        _dg_log(f"[{time.strftime('%H:%M:%S')}]  Starting parameter sweep…")
        _dg_log("  11 configs × 90s each ≈ 16 minutes.  Governor overlay active.")

        def _run():
            import subprocess, sys as _sys
            try:
                proc = subprocess.Popen(
                    [_sys.executable, str(DIAG_SCRIPT), "--sweep", "--quiet"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, cwd=str(_BASE_DIR),
                )
                for line in proc.stdout:
                    root.after(0, lambda l=line: _dg_log(l.rstrip()))
                proc.wait()
                root.after(0, lambda rc=proc.returncode: _dg_sweep_done(rc))
            except Exception as exc:
                root.after(0, lambda: _dg_log(f"[sweep error] {exc}"))
                root.after(0, lambda: _dg_sweep_done(-1))

        def _dg_sweep_done(rc: int) -> None:
            dg_sweep_btn.configure(state=tk.NORMAL, text="⚙  Sweep")
            if rc == 0:
                dg_scan_status.configure(text="  sweep complete", fg="#4ade80")
                _dg_log("[sweep] Done — loading proposals…")
                _dg_load_report()
            else:
                dg_scan_status.configure(text="  sweep failed", fg="#ef4444")
                _dg_log(f"[sweep] exited with code {rc}")

        threading.Thread(target=_run, daemon=True, name="diag-sweep").start()

    dg_sweep_btn.configure(command=_dg_run_sweep)

    # Kick off live check loop and load any existing report
    root.after(900, _refresh_diag_live)
    _dg_load_report()

    # ══════════════════════════════════════════════════════════════════════════
    # ── Governor Switchboard tab ──────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    _GOV_OVERLAY   = _STATE_DIR / "governor_sweep_overlay.json"
    _SWEEP_RESULTS = _STATE_DIR / "sweep_results.json"
    _SWEEP_HISTORY = _STATE_DIR / "sweep_history.json"
    REFRESH_GOV_MS = 3000

    # Governor task profiles (mirrors aurora_runtime_constraint_governor.py)
    _GOV_PROFILES = {
        "response_turn":   {"axes": {"X":0.30,"T":0.20,"N":0.20,"B":0.15,"A":0.20}, "floor":0.18, "cost":0.30, "critical":True},
        "status":          {"axes": {"X":0.25,"T":0.30,"N":0.20,"B":0.15,"A":0.10}, "floor":0.12, "cost":0.08, "critical":True},
        "evo_tick":        {"axes": {"X":0.10,"T":0.35,"N":0.20,"B":0.20,"A":0.15}, "floor":0.28, "cost":0.12},
        "evo_evidence":    {"axes": {"X":0.15,"T":0.15,"N":0.15,"B":0.35,"A":0.20}, "floor":0.38, "cost":0.42},
        "study":           {"axes": {"X":0.15,"T":0.25,"N":0.30,"B":0.10,"A":0.25}, "floor":0.42, "cost":0.35},
        "save":            {"axes": {"X":0.35,"T":0.20,"N":0.20,"B":0.20,"A":0.05}, "floor":0.35, "cost":0.55, "critical":True},
        "pressure_routing":{"axes": {"X":0.10,"T":0.20,"N":0.25,"B":0.25,"A":0.20}, "floor":0.50, "cost":0.38},
        "assimilation":    {"axes": {"X":0.15,"T":0.15,"N":0.25,"B":0.25,"A":0.20}, "floor":0.56, "cost":0.78},
        "genealogy_flush": {"axes": {"X":0.25,"T":0.15,"N":0.20,"B":0.30,"A":0.10}, "floor":0.55, "cost":0.50},
        "dream":           {"axes": {"X":0.10,"T":0.10,"N":0.15,"B":0.35,"A":0.35}, "floor":0.50, "cost":0.95},
        "distill":         {"axes": {"X":0.25,"T":0.20,"N":0.30,"B":0.20,"A":0.05}, "floor":0.62, "cost":0.92},
        "mutation":        {"axes": {"X":0.15,"T":0.10,"N":0.20,"B":0.25,"A":0.30}, "floor":0.68, "cost":0.98},
        "away_social":     {"axes": {"X":0.15,"T":0.15,"N":0.25,"B":0.15,"A":0.30}, "floor":0.70, "cost":0.90},
        "browser_ritual":  {"axes": {"X":0.20,"T":0.10,"N":0.25,"B":0.15,"A":0.30}, "floor":0.60, "cost":0.82},
        "reach_out":       {"axes": {"X":0.15,"T":0.15,"N":0.15,"B":0.20,"A":0.35}, "floor":0.66, "cost":0.38},
    }

    tab_gov_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_gov_outer, text="  Governor  ")
    tab_gov = _make_scrollable_inner(tab_gov_outer)

    # ── header ────────────────────────────────────────────────────────────────
    gov_hdr = tk.Frame(tab_gov, bg=BG_PANEL, pady=5, padx=12)
    gov_hdr.pack(fill=tk.X)
    tk.Label(gov_hdr, text="GOVERNOR SWITCHBOARD", bg=BG_PANEL,
             fg="#4ade80", font=("Courier New", 11, "bold")).pack(side=tk.LEFT)
    gov_mode_lbl = tk.Label(gov_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                             font=("Courier New", 9))
    gov_mode_lbl.pack(side=tk.LEFT, padx=12)
    gov_overlay_lbl = tk.Label(gov_hdr, text="overlay: INACTIVE", bg=BG_PANEL,
                                fg=TEXT_DIM, font=("Courier New", 9, "bold"))
    gov_overlay_lbl.pack(side=tk.RIGHT, padx=8)

    # ── levers panel ─────────────────────────────────────────────────────────
    gov_levers = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=8)
    gov_levers.pack(fill=tk.X, padx=8, pady=(4, 0))
    tk.Label(gov_levers, text="LEVERS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0,4))

    # N-floor slider
    tk.Label(gov_levers, text="N floor:", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 9)).grid(row=1, column=0, sticky="w")
    gov_n_floor_var = tk.DoubleVar(value=0.10)
    gov_n_floor_lbl = tk.Label(gov_levers, text="0.10", bg=BG_PANEL, fg="#4ade80",
                                font=("Courier New", 9, "bold"), width=5)
    gov_n_floor_lbl.grid(row=1, column=2, padx=4)
    gov_n_floor = tk.Scale(gov_levers, from_=0.02, to=0.50, resolution=0.01,
                            orient=tk.HORIZONTAL, variable=gov_n_floor_var,
                            bg=BG_PANEL, fg=TEXT, troughcolor=BG_LOG,
                            highlightthickness=0, bd=0, showvalue=False, length=180,
                            command=lambda v: gov_n_floor_lbl.configure(text=f"{float(v):.2f}"))
    gov_n_floor.grid(row=1, column=1, padx=4)

    # Maintenance multiplier slider
    tk.Label(gov_levers, text="Maint mult:", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 9)).grid(row=1, column=3, sticky="w", padx=(16,0))
    gov_maint_var = tk.DoubleVar(value=0.10)
    gov_maint_lbl = tk.Label(gov_levers, text="0.10", bg=BG_PANEL, fg="#4ade80",
                              font=("Courier New", 9, "bold"), width=5)
    gov_maint_lbl.grid(row=1, column=5, padx=4)
    gov_maint = tk.Scale(gov_levers, from_=0.01, to=1.00, resolution=0.01,
                          orient=tk.HORIZONTAL, variable=gov_maint_var,
                          bg=BG_PANEL, fg=TEXT, troughcolor=BG_LOG,
                          highlightthickness=0, bd=0, showvalue=False, length=180,
                          command=lambda v: gov_maint_lbl.configure(text=f"{float(v):.2f}"))
    gov_maint.grid(row=1, column=4, padx=4)

    # Heat selector
    tk.Label(gov_levers, text="Heat:", bg=BG_PANEL, fg=TEXT,
             font=("Courier New", 9)).grid(row=2, column=0, sticky="w", pady=(8,0))
    gov_heat_var = tk.StringVar(value="medium")
    gov_heat_frame = tk.Frame(gov_levers, bg=BG_PANEL)
    gov_heat_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=(8,0))
    for _heat_val, _heat_color in [("low","#22c55e"), ("medium","#f59e0b"), ("high","#ef4444")]:
        tk.Radiobutton(gov_heat_frame, text=_heat_val.upper(), variable=gov_heat_var,
                       value=_heat_val, bg=BG_PANEL, fg=_heat_color, selectcolor=BG_LOG,
                       activebackground=BG_PANEL, font=("Courier New", 9, "bold"),
                       indicatoron=True).pack(side=tk.LEFT, padx=6)

    # Apply / Clear buttons
    gov_btn_frame = tk.Frame(gov_levers, bg=BG_PANEL)
    gov_btn_frame.grid(row=2, column=3, columnspan=3, sticky="e", pady=(8,0))

    def _gov_apply_overlay():
        overlay = {
            "active":           True,
            "n_floor_override": round(gov_n_floor_var.get(), 2),
            "maintenance_mult": round(gov_maint_var.get(), 2),
            "heat_hint":        gov_heat_var.get(),
            "sweep_label":      "manual",
            "written_at":       time.time(),
        }
        _GOV_OVERLAY.write_text(json.dumps(overlay, indent=2))
        gov_overlay_lbl.configure(text="overlay: ACTIVE", fg="#4ade80")

    def _gov_clear_overlay():
        if _GOV_OVERLAY.exists():
            _GOV_OVERLAY.unlink()
        gov_overlay_lbl.configure(text="overlay: INACTIVE", fg=TEXT_DIM)

    tk.Button(gov_btn_frame, text="▶  Apply Overlay", bg="#1a2e1a", fg="#4ade80",
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_gov_apply_overlay).pack(side=tk.LEFT, padx=4)
    tk.Button(gov_btn_frame, text="✖  Clear", bg="#2d1a1a", fg="#ef4444",
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_gov_clear_overlay).pack(side=tk.LEFT, padx=4)

    # ── live axis budget bars ─────────────────────────────────────────────────
    tk.Frame(tab_gov, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=(6,0))
    gov_axis_hdr = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=4)
    gov_axis_hdr.pack(fill=tk.X, padx=8)
    tk.Label(gov_axis_hdr, text="LIVE AXIS BUDGET", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    gov_host_lbl = tk.Label(gov_axis_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                             font=("Courier New", 8))
    gov_host_lbl.pack(side=tk.LEFT, padx=10)

    gov_axis_frame = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=6)
    gov_axis_frame.pack(fill=tk.X, padx=8)
    _gov_axis_bars: Dict[str, tk.Canvas] = {}
    _gov_axis_lbls: Dict[str, tk.Label]  = {}
    _gov_axis_name_lbls: Dict[str, tk.Label] = {}
    _AXES_ORDER = ("X", "T", "N", "B", "A")
    _AXIS_COLORS = {"X":"#60a5fa","T":"#f59e0b","N":"#4ade80","B":"#c084fc","A":"#f87171"}
    _AXIS_NAMES_DEFAULT = {"X":"Existence","T":"Temporal","N":"Curiosity","B":"Behavior","A":"Feeling"}

    def _gov_load_aurora_labels() -> dict:
        """Read aurora_labels.json for her custom axis names."""
        if _LABELS_FILE.exists():
            try:
                d_ = json.loads(_LABELS_FILE.read_text())
                return {ax: d_.get("axes",{}).get(ax, _AXIS_NAMES_DEFAULT.get(ax,ax))
                        for ax in _AXES_ORDER}
            except Exception:
                pass
        return dict(_AXIS_NAMES_DEFAULT)

    for col_i, ax in enumerate(_AXES_ORDER):
        cell = tk.Frame(gov_axis_frame, bg=BG_PANEL)
        cell.grid(row=0, column=col_i, padx=8, sticky="nsew")
        gov_axis_frame.columnconfigure(col_i, weight=1)
        _nm = _AXIS_NAMES_DEFAULT.get(ax, ax)
        _nm_lbl = tk.Label(cell, text=f"{ax}\n{_nm}", bg=BG_PANEL,
                            fg=_AXIS_COLORS[ax], font=("Courier New", 8, "bold"),
                            justify="center")
        _nm_lbl.pack()
        _gov_axis_name_lbls[ax] = _nm_lbl
        bar_bg = tk.Canvas(cell, bg=BG_LOG, height=10, highlightthickness=0, bd=0)
        bar_bg.pack(fill=tk.X, pady=2)
        _gov_axis_bars[ax] = bar_bg
        lbl = tk.Label(cell, text="—", bg=BG_PANEL, fg=_AXIS_COLORS[ax],
                       font=("Courier New", 9, "bold"))
        lbl.pack()
        _gov_axis_lbls[ax] = lbl

    def _gov_draw_axis_bar(ax: str, val: float) -> None:
        canvas = _gov_axis_bars[ax]
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w < 4:
            return
        canvas.delete("all")
        fill_w = int(w * max(0.0, min(1.0, val)))
        color = _AXIS_COLORS[ax]
        # Red tint when critically low
        if val < 0.20:
            color = "#ef4444"
        elif val < 0.35:
            color = "#f59e0b"
        canvas.create_rectangle(0, 0, fill_w, 10, fill=color, outline="")
        _gov_axis_lbls[ax].configure(text=f"{val:.3f}")

    # ── energy income panel ───────────────────────────────────────────────────
    tk.Frame(tab_gov, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=(6,0))
    gov_energy_hdr = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=4)
    gov_energy_hdr.pack(fill=tk.X, padx=8)
    tk.Label(gov_energy_hdr, text="ENERGY INCOME", bg=BG_PANEL, fg="#f59e0b",
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    gov_energy_total_lbl = tk.Label(gov_energy_hdr, text="  no income yet", bg=BG_PANEL,
                                     fg=TEXT_DIM, font=("Courier New", 8))
    gov_energy_total_lbl.pack(side=tk.LEFT, padx=6)

    gov_energy_box = tk.Text(
        tab_gov, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        height=5, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    gov_energy_box.pack(fill=tk.X, padx=8, pady=(2, 0))
    gov_energy_box.tag_configure("src",  foreground="#f59e0b")
    gov_energy_box.tag_configure("axes", foreground="#4ade80")
    gov_energy_box.tag_configure("dim",  foreground=TEXT_DIM)
    gov_energy_box.tag_configure("head", foreground=ACCENT2)

    # ── task schedule table ───────────────────────────────────────────────────
    tk.Frame(tab_gov, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=(6,0))
    gov_task_hdr = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=4)
    gov_task_hdr.pack(fill=tk.X, padx=8)
    tk.Label(gov_task_hdr, text="TASK SCHEDULE  (simulated against current axes)",
             bg=BG_PANEL, fg=ACCENT2, font=("Courier New", 9, "bold")).pack(side=tk.LEFT)

    gov_task_box = tk.Text(
        tab_gov, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        height=10, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    gov_task_box.pack(fill=tk.X, padx=8, pady=(2, 0))
    gov_task_box.tag_configure("ok",    foreground="#22c55e")
    gov_task_box.tag_configure("block", foreground="#ef4444")
    gov_task_box.tag_configure("warn",  foreground="#f59e0b")
    gov_task_box.tag_configure("dim",   foreground=TEXT_DIM)
    gov_task_box.tag_configure("head",  foreground=ACCENT2)

    # ── sweep results panel ───────────────────────────────────────────────────
    tk.Frame(tab_gov, bg=CHART_GRID, height=1).pack(fill=tk.X, padx=8, pady=(6,0))
    gov_sweep_hdr = tk.Frame(tab_gov, bg=BG_PANEL, padx=12, pady=4)
    gov_sweep_hdr.pack(fill=tk.X, padx=8)
    tk.Label(gov_sweep_hdr, text="SWEEP RESULTS", bg=BG_PANEL, fg=ACCENT2,
             font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    gov_sweep_info_lbl = tk.Label(gov_sweep_hdr, text="  no results yet", bg=BG_PANEL,
                                   fg=TEXT_DIM, font=("Courier New", 8))
    gov_sweep_info_lbl.pack(side=tk.LEFT, padx=6)

    gov_sweep_body = tk.Frame(tab_gov, bg=BG_PANEL)
    gov_sweep_body.pack(fill=tk.BOTH, padx=8, pady=(2, 4))

    gov_sweep_list = tk.Listbox(
        gov_sweep_body, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        selectbackground="#1a2e1a", selectforeground="#4ade80",
        relief=tk.FLAT, borderwidth=0, highlightthickness=0,
        activestyle="none", height=8,
    )
    gov_sweep_sb = ttk.Scrollbar(gov_sweep_body, orient="vertical", command=gov_sweep_list.yview)
    gov_sweep_list.configure(yscrollcommand=gov_sweep_sb.set)
    gov_sweep_sb.pack(side=tk.RIGHT, fill=tk.Y)
    gov_sweep_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    gov_sweep_detail = tk.Text(
        tab_gov, bg=BG_LOG, fg=TEXT, font=("Courier New", 8),
        height=6, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.WORD,
    )
    gov_sweep_detail.pack(fill=tk.X, padx=8, pady=(0, 4))
    gov_sweep_detail.tag_configure("key",  foreground=ACCENT2)
    gov_sweep_detail.tag_configure("good", foreground="#22c55e")
    gov_sweep_detail.tag_configure("bad",  foreground="#ef4444")
    gov_sweep_detail.tag_configure("dim",  foreground=TEXT_DIM)

    _gov_sweep_data: list = []   # list of result dicts from last run

    def _gov_load_sweep_results() -> None:
        nonlocal _gov_sweep_data
        if not _SWEEP_RESULTS.exists():
            return
        try:
            data = json.loads(_SWEEP_RESULTS.read_text())
        except Exception:
            return
        ranked = data.get("ranked", [])
        results_by_label = {r["label"]: r for r in data.get("results", [])}
        _gov_sweep_data = [results_by_label.get(r["label"], r) for r in ranked]

        # Load confidence history
        history: Dict = {}
        if _SWEEP_HISTORY.exists():
            try:
                history = json.loads(_SWEEP_HISTORY.read_text())
            except Exception:
                pass

        completed_at = data.get("completed_at", 0)
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(completed_at)) if completed_at else "?"
        gov_sweep_info_lbl.configure(
            text=f"  {len(ranked)} configs  ·  last run {ts}",
            fg=TEXT_DIM
        )

        gov_sweep_list.delete(0, tk.END)
        for i, r in enumerate(_gov_sweep_data):
            label = r.get("label", "?")
            score = r.get("score", 0.0)
            runs  = len(history.get(label, []))
            conf  = ""
            if runs > 1:
                hist_scores = history.get(label, [])
                mean = sum(hist_scores) / len(hist_scores)
                conf = f"  ×{runs} runs μ={mean:.3f}"
            rank_str = f"  #{i+1:2d}  {label:<22s}  score={score:.3f}{conf}"
            gov_sweep_list.insert(tk.END, rank_str)
            # Color code by score
            if score >= 0.60:
                gov_sweep_list.itemconfig(i, fg="#22c55e")
            elif score >= 0.50:
                gov_sweep_list.itemconfig(i, fg=TEXT)
            else:
                gov_sweep_list.itemconfig(i, fg="#ef4444")

    def _gov_on_sweep_select(event=None):
        sel = gov_sweep_list.curselection()
        if not sel or not _gov_sweep_data:
            return
        idx = int(sel[0])
        if idx >= len(_gov_sweep_data):
            return
        r = _gov_sweep_data[idx]
        cfg    = r.get("config", {})
        snap   = r.get("snapshot") or {}
        props  = r.get("proposals", [])
        anomalies = r.get("anomalies", [])
        gov_sweep_detail.configure(state=tk.NORMAL)
        gov_sweep_detail.delete("1.0", tk.END)
        gov_sweep_detail.insert(tk.END, f"{r.get('label','?')}\n", "key")
        gov_sweep_detail.insert(tk.END, f"  score       : ", "dim")
        gov_sweep_detail.insert(tk.END, f"{r.get('score',0):.4f}\n", "good" if r.get('score',0) >= 0.55 else "bad")
        gov_sweep_detail.insert(tk.END, f"  n_floor     : {cfg.get('n_floor_override','?')}   ", "dim")
        gov_sweep_detail.insert(tk.END, f"  maint_mult  : {cfg.get('maintenance_mult','?')}   ", "dim")
        gov_sweep_detail.insert(tk.END, f"  heat        : {cfg.get('heat','?')}\n", "dim")
        gov_axes = snap.get("governor_axes", {})
        if gov_axes:
            axes_str = "  ".join(f"{ax}={float(gov_axes.get(ax,0)):.3f}" for ax in ("X","T","N","B","A"))
            gov_sweep_detail.insert(tk.END, f"  axes        : {axes_str}\n", "dim")
        if anomalies:
            gov_sweep_detail.insert(tk.END, f"  anomalies   : {', '.join(anomalies)}\n", "bad")
        if props:
            gov_sweep_detail.insert(tk.END, f"  proposals   : {len(props)}\n", "dim")
            gov_sweep_detail.insert(tk.END, f"  └ {props[0].get('proposed_action','')[:80]}\n", "dim")
        # "Apply this config" button hint
        gov_sweep_detail.insert(tk.END, f"\n  → Click ", "dim")
        gov_sweep_detail.insert(tk.END, "Apply Config", "good")
        gov_sweep_detail.insert(tk.END, " to load these levers into the switchboard\n", "dim")
        gov_sweep_detail.configure(state=tk.DISABLED)

        # Auto-load into sliders
        n_fl = float(cfg.get("n_floor_override", gov_n_floor_var.get()))
        maint = float(cfg.get("maintenance_mult", gov_maint_var.get()))
        heat  = str(cfg.get("heat", gov_heat_var.get()))
        gov_n_floor_var.set(n_fl)
        gov_n_floor_lbl.configure(text=f"{n_fl:.2f}")
        gov_maint_var.set(maint)
        gov_maint_lbl.configure(text=f"{maint:.2f}")
        gov_heat_var.set(heat)

    gov_sweep_list.bind("<<ListboxSelect>>", _gov_on_sweep_select)

    # ── refresh loop ──────────────────────────────────────────────────────────

    def _gov_compute_task_scores(axes: Dict[str, float]) -> List[tuple]:
        """Simulate evaluate_task() against given axes for all profiles."""
        rows = []
        for task, prof in sorted(_GOV_PROFILES.items(), key=lambda x: -x[1].get("cost",0)):
            score = sum(float(prof["axes"].get(ax,0)) * float(axes.get(ax,0)) for ax in _AXES_ORDER)
            floor = float(prof.get("floor", 0.5))
            allowed = score >= floor
            rows.append((task, score, floor, allowed, prof.get("cost", 0), prof.get("critical", False)))
        return rows

    def _gov_refresh():
        try:
            if not _DAEMON_STATUS.exists():
                return
            raw = json.loads(_DAEMON_STATUS.read_text())
            gov_axes = {ax: float(raw.get("runtime_governor_axes", {}).get(ax, 0.0)) for ax in _AXES_ORDER}
            host = raw.get("runtime_host", {})
            mode = raw.get("runtime_governor_mode", "?")
            heat = raw.get("heat", "?")

            # Mode label
            mode_color = {"survival":"#ef4444","conserve":"#f59e0b","balanced":TEXT,"open":"#22c55e"}.get(mode, TEXT_DIM)
            gov_mode_lbl.configure(
                text=f"mode:{mode}  heat:{heat}  load:{float(host.get('load_1m',0)):.2f}  "
                     f"mem:{float(host.get('mem_pressure',0))*100:.0f}%  "
                     f"disk:{float(host.get('disk_free_ratio',0))*100:.0f}%",
                fg=mode_color,
            )

            # Axis bars (with her labels)
            _aurora_axis_names = _gov_load_aurora_labels()
            for ax in _AXES_ORDER:
                _gov_draw_axis_bar(ax, gov_axes.get(ax, 0.0))
                _gov_axis_name_lbls[ax].configure(
                    text=f"{ax}\n{_aurora_axis_names.get(ax, ax)}"
                )

            # Host label
            gov_host_lbl.configure(
                text=f"load:{float(host.get('load_ratio',0)):.3f}  "
                     f"mem_avail:{float(host.get('mem_available_mb',0)):.0f}MB  "
                     f"rss:{float(host.get('process_rss_mb',0)):.0f}MB"
            )

            # Overlay status
            if _GOV_OVERLAY.exists():
                try:
                    ov = json.loads(_GOV_OVERLAY.read_text())
                    if ov.get("active"):
                        age = time.time() - float(ov.get("written_at", 0))
                        label = ov.get("sweep_label", "manual")
                        gov_overlay_lbl.configure(
                            text=f"overlay: {label.upper()}  ({int(age)}s ago)",
                            fg="#4ade80"
                        )
                    else:
                        gov_overlay_lbl.configure(text="overlay: INACTIVE", fg=TEXT_DIM)
                except Exception:
                    pass
            else:
                gov_overlay_lbl.configure(text="overlay: INACTIVE", fg=TEXT_DIM)

            # Task schedule simulation
            rows = _gov_compute_task_scores(gov_axes)
            gov_task_box.configure(state=tk.NORMAL)
            gov_task_box.delete("1.0", tk.END)
            gov_task_box.insert(tk.END,
                f"  {'TASK':<20s}  {'SCORE':>6s}  {'FLOOR':>6s}  {'COST':>5s}  STATUS\n", "head")
            gov_task_box.insert(tk.END, "  " + "─"*62 + "\n", "dim")
            for task, score, floor, allowed, cost, critical in rows:
                crit_tag = "★" if critical else " "
                if allowed:
                    status = "✓  allowed"
                    tag = "ok"
                else:
                    status = "✗  blocked"
                    tag = "block"
                if not allowed and score > floor * 0.85:
                    status = "~  marginal"
                    tag = "warn"
                gov_task_box.insert(tk.END,
                    f"  {crit_tag}{task:<19s}  {score:6.3f}  {floor:6.3f}  {cost:5.2f}  ", tag)
                gov_task_box.insert(tk.END, f"{status}\n", tag)
            gov_task_box.configure(state=tk.DISABLED)

            # Energy income display
            _energy_file = _STATE_DIR / "energy_income.json"
            if _energy_file.exists():
                try:
                    _credits = json.loads(_energy_file.read_text())
                    _now = time.time()
                    _live = []
                    _totals = {ax: 0.0 for ax in ("X","T","N","B","A")}
                    for c in _credits:
                        _age = _now - float(c.get("ts", _now))
                        _hl  = float(c.get("half_life", 1800))
                        _eff = float(c.get("amount", 0)) * (0.5 ** (_age / _hl))
                        if _eff >= 0.001:
                            _live.append((c, _eff, _age))
                            for _ax in c.get("axes", []):
                                if _ax in _totals:
                                    _totals[_ax] += _eff

                    total_str = "  ".join(
                        f"{ax}+{v:.3f}" for ax, v in _totals.items() if v >= 0.001
                    )
                    gov_energy_total_lbl.configure(
                        text=f"  {len(_live)} active credits  [{total_str}]",
                        fg="#f59e0b" if _live else TEXT_DIM,
                    )

                    gov_energy_box.configure(state=tk.NORMAL)
                    gov_energy_box.delete("1.0", tk.END)
                    gov_energy_box.insert(tk.END,
                        f"  {'SOURCE':<24s}  {'AXES':<12s}  {'EFFECTIVE':>9s}  {'AGE':>7s}  NOTES\n", "head")
                    gov_energy_box.insert(tk.END, "  " + "─"*70 + "\n", "dim")
                    for c, eff, age in sorted(_live, key=lambda x: -x[1])[:8]:
                        axes_str = "+".join(c.get("axes", []))
                        age_str = f"{int(age//60)}m{int(age%60)}s"
                        gov_energy_box.insert(tk.END,
                            f"  {c.get('source','?'):<24s}  ", "src")
                        gov_energy_box.insert(tk.END,
                            f"{axes_str:<12s}", "axes")
                        gov_energy_box.insert(tk.END,
                            f"  {eff:9.4f}  {age_str:>7s}  {c.get('notes','')[:28]}\n", "dim")
                    if not _live:
                        gov_energy_box.insert(tk.END, "  no active income — interact or complete a learning task\n", "dim")
                    gov_energy_box.configure(state=tk.DISABLED)
                except Exception:
                    pass

        except Exception:
            pass

        root.after(REFRESH_GOV_MS, _gov_refresh)

    root.after(1200, _gov_refresh)
    root.after(1500, _gov_load_sweep_results)

    # ══════════════════════════════════════════════════════════════════════════
    # AURORA ROOM OBSERVER TAB — read-only view of her room, messages to/from
    # ══════════════════════════════════════════════════════════════════════════
    tab_room_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_room_outer, text="  Aurora's Room  ")
    tab_room = _make_scrollable_inner(tab_room_outer)

    # ══════════════════════════════════════════════════════════════════════════
    # VOICE COMMANDS TAB
    # ══════════════════════════════════════════════════════════════════════════
    tab_voice_cmds_outer = tk.Frame(notebook, bg=BG)
    notebook.add(tab_voice_cmds_outer, text="  Voice Commands  ")
    
    voice_txt = tk.Text(tab_voice_cmds_outer, bg=BG_LOG, fg=TEXT, font=("Courier New", 10), wrap=tk.WORD, borderwidth=0, padx=20, pady=20)
    voice_scroll = tk.Scrollbar(tab_voice_cmds_outer, command=voice_txt.yview, bg=BG_PANEL, troughcolor=BG)
    voice_txt.configure(yscrollcommand=voice_scroll.set)
    voice_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    voice_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    try:
        cmd_path = _BASE_DIR / "VOICE_COMMANDS.md"
        if cmd_path.exists():
            voice_txt.insert(tk.END, cmd_path.read_text())
        else:
            voice_txt.insert(tk.END, "VOICE_COMMANDS.md not found.")
    except Exception as e:
        voice_txt.insert(tk.END, f"Error loading voice commands: {e}")
    voice_txt.config(state=tk.DISABLED)

    room_hdr = tk.Frame(tab_room, bg=BG_PANEL, pady=5, padx=12)
    room_hdr.pack(fill=tk.X)
    tk.Label(room_hdr, text="◈  AURORA'S ROOM  —  observer view", bg=BG_PANEL,
             fg="#4ade80", font=("Courier New", 11, "bold")).pack(side=tk.LEFT)
    room_aurora_online_lbl = tk.Label(room_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                       font=("Courier New", 9))
    room_aurora_online_lbl.pack(side=tk.LEFT, padx=12)
    room_view_mode = tk.StringVar(value="surface")
    room_view_btns: Dict[str, tk.Button] = {}
    room_view_hint = tk.Label(room_hdr, text="", bg=BG_PANEL, fg=TEXT_DIM,
                              font=("Courier New", 8))
    room_view_hint.pack(side=tk.RIGHT, padx=(8, 0))
    room_toggle = tk.Frame(room_hdr, bg=BG_PANEL)
    room_toggle.pack(side=tk.RIGHT, padx=(0, 8))
    tk.Label(room_toggle, text="View", bg=BG_PANEL, fg=TEXT_DIM,
             font=("Courier New", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))

    def _room_view() -> str:
        mode = str(room_view_mode.get() or "surface").strip().lower()
        return mode if mode in {"surface", "subsurface"} else "surface"

    def _sync_room_view_toggle() -> None:
        active = _room_view()
        for mode, button in room_view_btns.items():
            is_active = mode == active
            button.configure(
                bg=CHART_GRID if is_active else BG_LOG,
                fg="#4ade80" if is_active else TEXT_DIM,
            )
        if active == "surface":
            room_view_hint.configure(text="surface-conscious room view", fg="#a7f3d0")
        else:
            room_view_hint.configure(text="subsurface operator view", fg="#67e8f9")

    def _set_room_view(mode: str) -> None:
        room_view_mode.set(mode if mode in {"surface", "subsurface"} else "surface")
        _sync_room_view_toggle()
        try:
            _refresh_room()
        except Exception:
            pass

    for _mode, _label in (("surface", "Surface"), ("subsurface", "Subsurface")):
        _btn = tk.Button(
            room_toggle,
            text=_label,
            bg=BG_LOG,
            fg=TEXT_DIM,
            font=("Courier New", 8, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda m=_mode: _set_room_view(m),
        )
        _btn.pack(side=tk.LEFT, padx=2)
        room_view_btns[_mode] = _btn
    _sync_room_view_toggle()

    # ── Her axis state (read from daemon, labeled with her names) ────────────
    room_axis_frame = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=8)
    room_axis_frame.pack(fill=tk.X, padx=8, pady=(4,0))
    tk.Label(room_axis_frame, text="HER DIMENSIONS (her labels)", bg=BG_PANEL,
             fg="#86efac", font=("Courier New", 9, "bold")).grid(
             row=0, column=0, columnspan=10, sticky="w", pady=(0,4))
    _room_axis_bars: dict = {}
    _room_axis_lbls: dict = {}
    _ROOM_AXIS_COLORS = {"X":"#60a5fa","T":"#f59e0b","N":"#4ade80","B":"#c084fc","A":"#f87171"}
    for _i, _ax in enumerate(("X","T","N","B","A")):
        _cell = tk.Frame(room_axis_frame, bg=BG_PANEL)
        _cell.grid(row=1, column=_i, padx=10, sticky="nsew")
        room_axis_frame.columnconfigure(_i, weight=1)
        _room_axis_lbls[_ax] = tk.Label(_cell, text=f"{_ax}\n—",
                                         bg=BG_PANEL, fg=_ROOM_AXIS_COLORS[_ax],
                                         font=("Courier New", 8, "bold"), justify="center")
        _room_axis_lbls[_ax].pack()
        _bar = tk.Canvas(_cell, bg="#080e08", height=12, highlightthickness=0, bd=0)
        _bar.pack(fill=tk.X, pady=2)
        _room_axis_bars[_ax] = _bar
        tk.Label(_cell, textvariable=(_bv := tk.StringVar(value="—")),
                 bg=BG_PANEL, fg=_ROOM_AXIS_COLORS[_ax],
                 font=("Courier New", 9, "bold")).pack()
        _room_axis_bars[f"{_ax}_var"] = _bv

    def _draw_room_axis(ax_: str, val_: float) -> None:
        can_ = _room_axis_bars[ax_]
        can_.update_idletasks()
        w_ = can_.winfo_width()
        if w_ < 4:
            return
        can_.delete("all")
        fw_ = int(w_ * max(0.0, min(1.0, val_)))
        c_  = _ROOM_AXIS_COLORS[ax_] if val_ >= 0.35 else ("#f59e0b" if val_ >= 0.20 else "#ef4444")
        can_.create_rectangle(0, 0, fw_, 12, fill=c_, outline="")
        _room_axis_bars[f"{ax_}_var"].set(f"{val_:.3f}")

    # ── Her state summary ─────────────────────────────────────────────────────
    room_state_box = tk.Text(tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
                              height=5, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                              wrap=tk.WORD)
    room_state_box.pack(fill=tk.X, padx=8, pady=(4,0))

    # ── DCE strip + selected room stratum view ───────────────────────────────
    room_div_strata = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div_strata.pack(fill=tk.X, padx=8, pady=(6,0))
    tk.Label(tab_room, text="DCE ROOT THOUGHT  —  shared convergence", bg=BG,
             fg="#facc15", font=("Courier New", 9, "bold"),
             padx=14, pady=4).pack(anchor="w")
    room_dce_box = tk.Text(tab_room, bg="#120f04", fg=TEXT, font=("Courier New", 8),
                            height=5, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                            wrap=tk.WORD)
    room_dce_box.pack(fill=tk.X, padx=8, pady=(2,0))
    tk.Label(tab_room, text="AURORA ROOM VIEW  —  selected stratum", bg=BG,
             fg="#86efac", font=("Courier New", 9, "bold"),
             padx=14, pady=4).pack(anchor="w")
    room_strata_box = tk.Text(tab_room, bg="#081108", fg=TEXT, font=("Courier New", 8),
                               height=9, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                               wrap=tk.WORD)
    room_strata_box.pack(fill=tk.X, padx=8, pady=(2,0))

    # ── Her notes (what she's observing/thinking) ─────────────────────────────
    room_div1 = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div1.pack(fill=tk.X, padx=8, pady=(6,0))
    tk.Label(tab_room, text="HER OBSERVATIONS & INTENTIONS", bg=BG,
             fg="#86efac", font=("Courier New", 9, "bold"),
             padx=14, pady=4).pack(anchor="w")
    room_notes_box = tk.Text(tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
                              height=7, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                              wrap=tk.WORD)
    room_notes_box.pack(fill=tk.X, padx=8, pady=(2,0))
    room_notes_box.tag_configure("key",  foreground="#34d399")
    room_notes_box.tag_configure("val",  foreground=TEXT)
    room_notes_box.tag_configure("good", foreground="#4ade80")
    room_notes_box.tag_configure("warn", foreground="#f59e0b")
    room_notes_box.tag_configure("dim",  foreground="#4b6b4b")

    # ── Message thread (Aurora ↔ Sunni) ───────────────────────────────────────
    room_div2 = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div2.pack(fill=tk.X, padx=8, pady=(6,0))
    tk.Label(tab_room, text="MESSAGES", bg=BG, fg="#86efac",
             font=("Courier New", 9, "bold"), padx=14, pady=4).pack(anchor="w")
    room_msg_box = tk.Text(tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
                            height=8, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                            wrap=tk.WORD)
    room_msg_box.pack(fill=tk.X, padx=8, pady=(2,0))
    room_msg_box.tag_configure("aurora", foreground="#4ade80")
    room_msg_box.tag_configure("sunni",  foreground="#f59e0b")
    room_msg_box.tag_configure("dim",    foreground="#4b6b4b")
    room_msg_box.tag_configure("intent", foreground="#86efac")

    room_div_change = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div_change.pack(fill=tk.X, padx=8, pady=(6,0))
    room_change_hdr = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=4)
    room_change_hdr.pack(fill=tk.X, padx=8)
    tk.Label(room_change_hdr, text="RECENT CHANGES", bg=BG_PANEL,
             fg="#38bdf8", font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    tk.Label(room_change_hdr,
             text="  actual change flow, separate from diagnostics proposals",
             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT)
    room_change_count_lbl = tk.Label(room_change_hdr, text="", bg=BG_PANEL,
                                     fg=TEXT_DIM, font=("Courier New", 8))
    room_change_count_lbl.pack(side=tk.LEFT, padx=8)
    room_change_box = tk.Text(tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
                              height=7, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED,
                              wrap=tk.WORD)
    room_change_box.pack(fill=tk.X, padx=8, pady=(2,0))
    room_change_box.tag_configure("ts", foreground="#4b6b4b")
    room_change_box.tag_configure("change", foreground="#38bdf8")
    room_change_box.tag_configure("good", foreground="#4ade80")
    room_change_box.tag_configure("warn", foreground="#f59e0b")
    room_change_box.tag_configure("dim", foreground=TEXT_DIM)

    # Reply input
    room_reply_frame = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=6)
    room_reply_frame.pack(fill=tk.X, padx=8, pady=(4,0))
    room_reply_input = tk.Text(room_reply_frame, bg="#080e08", fg=TEXT,
                                font=("Courier New", 9), height=2, relief=tk.FLAT,
                                borderwidth=0, insertbackground=ACCENT, wrap=tk.WORD)
    room_reply_input.pack(fill=tk.X)

    def _send_room_reply():
        content = room_reply_input.get("1.0", tk.END).strip()
        if not content:
            return
        msgs_: list = []
        if _ROOM_MSGS.exists():
            try:
                msgs_ = json.loads(_ROOM_MSGS.read_text())
                if not isinstance(msgs_, list):
                    msgs_ = []
            except Exception:
                msgs_ = []
        msgs_.append({
            "from":    "sunni",
            "content": content,
            "ts":      time.time(),
            "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        msgs_ = msgs_[-200:]
        _ROOM_MSGS.write_text(json.dumps(msgs_, indent=2))
        room_reply_input.delete("1.0", tk.END)
        room_reply_lbl.configure(text="sent to Aurora", fg=ACCENT)
        root.after(2500, lambda: room_reply_lbl.configure(text="", fg=TEXT_DIM))

    room_reply_row = tk.Frame(room_reply_frame, bg=BG_PANEL)
    room_reply_row.pack(fill=tk.X, pady=(4,0))
    tk.Button(room_reply_row, text="Reply to Aurora", bg="#1a2e1a", fg="#4ade80",
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_send_room_reply).pack(side=tk.LEFT)
    room_reply_lbl = tk.Label(room_reply_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                               font=("Courier New", 8))
    room_reply_lbl.pack(side=tk.LEFT, padx=8)

    # ── Response coaching panel ───────────────────────────────────────────────
    room_div_coach = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div_coach.pack(fill=tk.X, padx=8, pady=(6,0))
    room_coach_hdr = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=4)
    room_coach_hdr.pack(fill=tk.X, padx=8)
    tk.Label(room_coach_hdr, text="RESPONSE COACHING", bg=BG_PANEL,
             fg="#f59e0b", font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    tk.Label(room_coach_hdr,
             text="  Aurora reads this in her Response tab",
             bg=BG_PANEL, fg=TEXT_DIM, font=("Courier New", 8)).pack(side=tk.LEFT)

    room_coach_type_var = tk.StringVar(value="style_note")
    room_coach_type_frame = tk.Frame(tab_room, bg=BG_PANEL, padx=12)
    room_coach_type_frame.pack(fill=tk.X, padx=8, pady=(2,0))
    _COACH_TYPES = [
        ("style_note",          "General style"),
        ("strengthen_template", "Strengthen a pattern"),
        ("avoid_pattern",       "Avoid a pattern"),
        ("focus_axis",          "Focus an axis"),
        ("response_depth",      "Response depth"),
    ]
    for _cv, _cl in _COACH_TYPES:
        tk.Radiobutton(
            room_coach_type_frame, text=_cl, variable=room_coach_type_var, value=_cv,
            bg=BG_PANEL, fg=TEXT_DIM, selectcolor=BG_LOG,
            activebackground=BG_PANEL, font=("Courier New", 8),
        ).pack(side=tk.LEFT, padx=4)

    room_coach_frame = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=4)
    room_coach_frame.pack(fill=tk.X, padx=8)
    room_coach_input = tk.Text(room_coach_frame, bg="#080e08", fg=TEXT,
                                font=("Courier New", 9), height=3, relief=tk.FLAT,
                                borderwidth=0, insertbackground=ACCENT, wrap=tk.WORD)
    room_coach_input.pack(fill=tk.X)

    # Coaching history
    room_coach_hist_box = tk.Text(
        tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
        height=5, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.WORD,
    )
    room_coach_hist_box.pack(fill=tk.X, padx=8, pady=(2,0))
    room_coach_hist_box.tag_configure("type", foreground="#f59e0b")
    room_coach_hist_box.tag_configure("read", foreground="#4ade80")
    room_coach_hist_box.tag_configure("unread", foreground="#f59e0b")
    room_coach_hist_box.tag_configure("dim",  foreground=TEXT_DIM)

    def _send_coaching():
        content = room_coach_input.get("1.0", tk.END).strip()
        if not content:
            return
        ctype = room_coach_type_var.get()
        entries: list = []
        if _RESPONSE_COACHING.exists():
            try:
                entries = json.loads(_RESPONSE_COACHING.read_text())
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                pass
        entries.append({
            "type":            ctype,
            "content":         content,
            "ts":              time.time(),
            "ts_str":          time.strftime("%Y-%m-%d %H:%M:%S"),
            "from":            "sunni",
            "read_by_aurora":  False,
        })
        entries = entries[-100:]
        _RESPONSE_COACHING.write_text(json.dumps(entries, indent=2))
        room_coach_input.delete("1.0", tk.END)
        room_coach_sent_lbl.configure(text="sent — Aurora will see it in her Response tab", fg=ACCENT)
        root.after(3000, lambda: room_coach_sent_lbl.configure(text="", fg=TEXT_DIM))
        _load_coach_history()

    def _load_coach_history():
        entries: list = []
        if _RESPONSE_COACHING.exists():
            try:
                entries = json.loads(_RESPONSE_COACHING.read_text())
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                pass
        room_coach_hist_box.configure(state=tk.NORMAL)
        room_coach_hist_box.delete("1.0", tk.END)
        if entries:
            for e in reversed(entries[-6:]):
                ts_s   = e.get("ts_str","?")[:16]
                ctype  = e.get("type","?").replace("_"," ")
                body   = e.get("content","")[:80]
                read   = e.get("read_by_aurora", False)
                rtag   = "read" if read else "unread"
                room_coach_hist_box.insert(tk.END, f"  [{ts_s}] ", "dim")
                room_coach_hist_box.insert(tk.END, f"[{ctype}] ", "type")
                room_coach_hist_box.insert(tk.END, f"{'✓ ' if read else '★ '}{body}\n", rtag)
        else:
            room_coach_hist_box.insert(tk.END, "  No coaching notes sent yet.\n", "dim")
        room_coach_hist_box.configure(state=tk.DISABLED)

    room_coach_row = tk.Frame(room_coach_frame, bg=BG_PANEL)
    room_coach_row.pack(fill=tk.X, pady=(4,0))
    tk.Button(room_coach_row, text="Send Coaching Note", bg="#1a2e1a", fg="#f59e0b",
              font=("Courier New", 9, "bold"), relief=tk.FLAT, padx=8, pady=2,
              cursor="hand2", command=_send_coaching).pack(side=tk.LEFT)
    room_coach_sent_lbl = tk.Label(room_coach_row, text="", bg=BG_PANEL, fg=TEXT_DIM,
                                    font=("Courier New", 8))
    room_coach_sent_lbl.pack(side=tk.LEFT, padx=8)

    root.after(1000, _load_coach_history)

    # ── Activity log ─────────────────────────────────────────────────────────
    room_div3 = tk.Frame(tab_room, bg="#1a2e1a", height=1)
    room_div3.pack(fill=tk.X, padx=8, pady=(6,0))
    room_act_hdr = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=4)
    room_act_hdr.pack(fill=tk.X, padx=8)
    tk.Label(room_act_hdr, text="WHAT SHE'S DOING", bg=BG_PANEL,
             fg="#86efac", font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    room_act_count_lbl = tk.Label(room_act_hdr, text="", bg=BG_PANEL,
                                   fg=TEXT_DIM, font=("Courier New", 8))
    room_act_count_lbl.pack(side=tk.LEFT, padx=8)

    room_act_box = tk.Text(
        tab_room, bg="#080e08", fg=TEXT, font=("Courier New", 8),
        height=14, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    room_act_box.pack(fill=tk.X, padx=8, pady=(2, 0))
    room_act_box.tag_configure("ts",         foreground="#4b6b4b")
    room_act_box.tag_configure("action",     foreground="#34d399")
    room_act_box.tag_configure("note",       foreground="#86efac")
    room_act_box.tag_configure("message",    foreground="#f59e0b")
    room_act_box.tag_configure("decision",   foreground="#4ade80")
    room_act_box.tag_configure("experiment", foreground="#a78bfa")
    room_act_box.tag_configure("training",   foreground="#38bdf8")
    room_act_box.tag_configure("detail",     foreground="#4b6b4b")

    # ── Poedex interaction log ─────────────────────────────────────────────────
    tk.Frame(tab_room, bg="#1a2e1a", height=1).pack(fill=tk.X, padx=8, pady=(10, 0))
    poe_log_hdr = tk.Frame(tab_room, bg=BG_PANEL, padx=12, pady=4)
    poe_log_hdr.pack(fill=tk.X, padx=8)
    tk.Label(poe_log_hdr, text="POEDEX INTERACTION LOG", bg=BG_PANEL,
             fg=ACCENT, font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
    poe_log_count_lbl = tk.Label(poe_log_hdr, text="", bg=BG_PANEL,
                                 fg=TEXT_DIM, font=("Courier New", 8))
    poe_log_count_lbl.pack(side=tk.LEFT, padx=8)

    poe_log_box = tk.Text(
        tab_room, bg="#080810", fg=TEXT, font=("Courier New", 8),
        height=16, relief=tk.FLAT, borderwidth=0, state=tk.DISABLED, wrap=tk.NONE,
    )
    poe_log_box.pack(fill=tk.X, padx=8, pady=(2, 0))
    poe_log_box.tag_configure("ts",       foreground="#3a3a5a")
    poe_log_box.tag_configure("lane",     foreground="#818cf8")
    poe_log_box.tag_configure("cat",      foreground="#a78bfa")
    poe_log_box.tag_configure("question", foreground="#e2e8f0")
    poe_log_box.tag_configure("result",   foreground="#94a3b8")
    poe_log_box.tag_configure("bound",    foreground="#4ade80")
    poe_log_box.tag_configure("cost",     foreground="#f59e0b")
    poe_log_box.tag_configure("scan",     foreground="#38bdf8")
    poe_log_box.tag_configure("dim",      foreground=TEXT_DIM)

    # ── Refresh function ──────────────────────────────────────────────────────
    def _refresh_room():
        import json as _json
        # Write presence heartbeat — Aurora's room reads this to know Sunni is watching
        try:
            _MASTER_PRESENCE.write_text(_json.dumps({
                "ts":      time.time(),
                "ts_str":  time.strftime("%Y-%m-%d %H:%M:%S"),
            }))
        except Exception:
            pass

        # Read her labels
        _rlabels: dict = {}
        if _LABELS_FILE.exists():
            try:
                _rlabels = _json.loads(_LABELS_FILE.read_text())
            except Exception:
                pass
        _axis_names_ = _rlabels.get("axes", {})

        # Update axis name labels (her names)
        for _ax in ("X","T","N","B","A"):
            _name_ = _axis_names_.get(_ax, _ax)
            _room_axis_lbls[_ax].configure(text=f"{_ax}\n{_name_}")

        # Read daemon status for axis values + state
        _ds: dict = {}
        _ds_path = _STATE_DIR / "daemon_status.json"
        if _ds_path.exists():
            try:
                _ds = _json.loads(_ds_path.read_text())
            except Exception:
                pass

        if _ds:
            _gov_axes = _ds.get("runtime_governor_axes", {})
            for _ax in ("X","T","N","B","A"):
                _draw_room_axis(_ax, float(_gov_axes.get(_ax, 0.0)))

            _mode = _ds.get("runtime_governor_mode", "?")
            _heat = _ds.get("heat", "?")
            _gov_labels = _rlabels.get("gov_mode", {})
            _heat_labels = _rlabels.get("heat", {})
            _mode_str = _gov_labels.get(_mode, _mode)
            _heat_str = _heat_labels.get(_heat, _heat.lower())
            _arch = _ds.get("interaction_archetype","")
            _chains = int(_ds.get("chain_links", 0))
            _upd = _ds.get("updated","?")
            room_aurora_online_lbl.configure(
                text=f"{_mode_str}  ·  {_heat_str}  ·  {_chains} chain links  ·  {_upd}",
                fg="#4ade80" if _mode in ("open","balanced") else "#f59e0b")

            room_state_box.configure(state=tk.NORMAL)
            room_state_box.delete("1.0", tk.END)
            _dom = max(_gov_axes, key=lambda a_: float(_gov_axes.get(a_,0))) if _gov_axes else "?"
            _dom_name = _axis_names_.get(_dom, _dom)
            room_state_box.insert(tk.END,
                f"  State: {_mode_str}  ·  Heat: {_heat_str}\n"
                f"  Strongest: {_dom} ({_dom_name})\n"
                f"  Chain links: {_chains}  ·  Archetype: {_arch or 'none'}\n",
                "")
            room_state_box.configure(state=tk.DISABLED)

        _dual_snapshot = {}
        if _DUAL_STRATA_SNAPSHOT.exists():
            try:
                _dual_snapshot = _json.loads(_DUAL_STRATA_SNAPSHOT.read_text())
            except Exception:
                _dual_snapshot = {}
        _projection = {}
        if _SUBSURFACE_PROJECTION.exists():
            try:
                _projection = _json.loads(_SUBSURFACE_PROJECTION.read_text())
            except Exception:
                _projection = {}
        _sub = dict(_dual_snapshot.get("subsurface_state", {}) or {})
        _surface = dict(_dual_snapshot.get("conscious_frame", {}) or {})
        _root = dict(_surface.get("root_thought") or {})
        room_dce_box.configure(state=tk.NORMAL)
        room_dce_box.delete("1.0", tk.END)
        if _root:
            room_dce_box.insert(
                tk.END,
                (
                    f"  Root thought: {_root.get('summary','still forming')}\n"
                    f"  Primary tension: {_root.get('primary_tension','steady')}\n"
                    f"  Frame sources: {', '.join(list(_root.get('comparison_channels') or [])[:5]) or 'none yet'}\n"
                ),
                "",
            )
            _guidance = str(_projection.get("surface_guidance", "") or "")
            if _guidance:
                room_dce_box.insert(tk.END, f"  Surface cue: {_guidance}\n")
        else:
            room_dce_box.insert(tk.END, "  No converged DCE frame yet.\n", "")
        room_dce_box.configure(state=tk.DISABLED)

        room_strata_box.configure(state=tk.NORMAL)
        room_strata_box.delete("1.0", tk.END)
        if _room_view() == "surface":
            if _surface:
                _notes = list(_surface.get("explicit_notes", []) or [])
                _hyp = list(_surface.get("salient_hypotheses", []) or [])
                _conflicts = list(_surface.get("unresolved_conflicts", []) or [])
                _mode = str(_surface.get("processing_mode", "") or "deliberative")
                room_strata_box.insert(
                    tk.END,
                    (
                        f"  Surface stance: {_surface.get('stance','?')}  ·  Action: {_surface.get('selected_action','?')}  ·  Speak: {'yes' if _surface.get('should_speak') else 'not yet'}\n"
                        f"  Processing: {_mode}\n"
                        f"  Interpretation: {_surface.get('interpretation','')}\n"
                        f"  Coherence: {float(_surface.get('coherence',0.0) or 0.0):.3f}  ·  Readiness: {float(_surface.get('readiness',0.0) or 0.0):.3f}\n"
                    ),
                    "",
                )
                _present = dict(_projection.get("present_sensory_perspective") or {})
                if _present.get("summary"):
                    room_strata_box.insert(tk.END, f"  Present sensing: {_present.get('summary','')}\n")
                if _notes:
                    room_strata_box.insert(tk.END, "  Intuition notes:\n")
                    for _n in _notes[:3]:
                        room_strata_box.insert(tk.END, f"    - {_n}\n")
                if _hyp:
                    room_strata_box.insert(tk.END, "  Surface-usable intuitions:\n")
                    for _h in _hyp[:3]:
                        room_strata_box.insert(tk.END, f"    - {_h.get('label','?')} ({float(_h.get('confidence',0.0) or 0.0):.2f})\n")
                if _conflicts:
                    room_strata_box.insert(tk.END, "  Still unresolved:\n")
                    for _c in _conflicts[:3]:
                        room_strata_box.insert(tk.END, f"    - {_c}\n")
            else:
                room_strata_box.insert(tk.END, "  No surface-conscious frame yet.\n", "")
        else:
            if _sub:
                _pmap = dict(_sub.get("pressure_map", {}) or {})
                _smap = dict(_sub.get("salience_weights", {}) or {})
                _markers = list(_sub.get("instability_markers", []) or [])
                _cands = list(_sub.get("candidate_interpretations", []) or [])
                _frags = list(_sub.get("recalled_fragments", []) or [])
                _pred = dict(_sub.get("prediction", {}) or {})
                _owned = dict(_projection.get("subsurface_owned") or {})
                room_strata_box.insert(
                    tk.END,
                    (
                        f"  Dominant axis: {_sub.get('dominant_axis','?')}  ·  Readiness: {float(_sub.get('readiness',0.0) or 0.0):.3f}\n"
                        f"  Repair phase: {_owned.get('repair_phase','steady')}  ·  Enforcer: surface authorizes -> subsurface applies\n"
                        f"  Pressure:   X {float(_pmap.get('X',0.0) or 0.0):.2f}  T {float(_pmap.get('T',0.0) or 0.0):.2f}  N {float(_pmap.get('N',0.0) or 0.0):.2f}  B {float(_pmap.get('B',0.0) or 0.0):.2f}  A {float(_pmap.get('A',0.0) or 0.0):.2f}\n"
                        f"  Salience:   X {float(_smap.get('X',0.0) or 0.0):.2f}  T {float(_smap.get('T',0.0) or 0.0):.2f}  N {float(_smap.get('N',0.0) or 0.0):.2f}  B {float(_smap.get('B',0.0) or 0.0):.2f}  A {float(_smap.get('A',0.0) or 0.0):.2f}\n"
                        f"  Prediction mismatch: {float(_pred.get('mismatch',0.0) or 0.0):.3f}  ·  Source: {_pred.get('source','-')}\n"
                    ),
                    "",
                )
                if _markers:
                    room_strata_box.insert(tk.END, "  Instability markers:\n")
                    for _m in _markers[:4]:
                        room_strata_box.insert(tk.END, f"    - {_m.get('label','?')} ({float(_m.get('severity',0.0) or 0.0):.2f})\n")
                if _cands:
                    room_strata_box.insert(tk.END, "  Candidate interpretations:\n")
                    for _c in _cands[:3]:
                        room_strata_box.insert(tk.END, f"    - {_c.get('summary','')}\n")
                if _frags:
                    room_strata_box.insert(tk.END, "  Recalled fragments:\n")
                    for _f in _frags[:3]:
                        room_strata_box.insert(tk.END, f"    - {_f}\n")
            else:
                room_strata_box.insert(tk.END, "  No subsurface snapshot yet.\n", "")
        room_strata_box.configure(state=tk.DISABLED)

        # Her notes
        _notes: list = []
        if _ROOM_NOTES.exists():
            try:
                _notes = _json.loads(_ROOM_NOTES.read_text())
                if not isinstance(_notes, list):
                    _notes = []
            except Exception:
                pass
        room_notes_box.configure(state=tk.NORMAL)
        room_notes_box.delete("1.0", tk.END)
        if _notes:
            for _n in reversed(_notes[-12:]):
                _ts  = _n.get("ts_str","?")[:16]
                _nt  = _n.get("type","?")
                _body= _n.get("content","")[:100]
                _tag = {"observation":"val","intention":"good",
                        "question":"warn","discovery":"good",
                        "message_to_sunni":"key"}.get(_nt,"dim")
                room_notes_box.insert(tk.END, f"  [{_ts}] {_nt:<14s}", "dim")
                room_notes_box.insert(tk.END, f"{_body}\n", _tag)
        else:
            room_notes_box.insert(tk.END, "  Nothing written yet.\n", "dim")
        room_notes_box.configure(state=tk.DISABLED)

        # Message thread
        _msgs: list = []
        if _ROOM_MSGS.exists():
            try:
                _msgs = _json.loads(_ROOM_MSGS.read_text())
                if not isinstance(_msgs, list):
                    _msgs = []
            except Exception:
                pass
        room_msg_box.configure(state=tk.NORMAL)
        room_msg_box.delete("1.0", tk.END)
        if _msgs:
            for _m in _msgs[-15:]:
                _ts   = _m.get("ts_str","?")[:16]
                _from = _m.get("from","?")
                _mtyp = _m.get("type","message")
                _body = _m.get("content","")[:120]
                _tag  = "aurora" if _from == "aurora" else "sunni"
                _name = "Aurora" if _from == "aurora" else "You"
                _typ_s = f"[{_mtyp}] " if _mtyp not in ("message",) else ""
                room_msg_box.insert(tk.END, f"  [{_ts}] ", "dim")
                room_msg_box.insert(tk.END, f"{_name}: ", _tag)
                room_msg_box.insert(tk.END, f"{_typ_s}{_body}\n", "")
        else:
            room_msg_box.insert(tk.END, "  No messages yet.\n", "dim")
        room_msg_box.configure(state=tk.DISABLED)

        # Activity log
        _acts: list = []
        if _ROOM_ACTIVITY.exists():
            try:
                _acts = _json.loads(_ROOM_ACTIVITY.read_text())
                if not isinstance(_acts, list):
                    _acts = []
            except Exception:
                pass
        _change_entries: list = []
        for _e in _acts:
            _act_l = str(_e.get("action", "") or "").lower()
            _cat_l = str(_e.get("category", "") or "").lower()
            if _cat_l in {"decision", "experiment", "training"}:
                _change_entries.append(_e)
                continue
            if any(_tok in _act_l for _tok in (
                "approved", "authorize", "revert", "reverse", "mutation",
                "study", "dream", "distill", "assimilation", "training"
            )):
                _change_entries.append(_e)
        room_change_count_lbl.configure(
            text=f"  {len(_change_entries)} recorded" if _change_entries else "  no changes logged yet",
            fg="#38bdf8" if _change_entries else TEXT_DIM,
        )
        room_change_box.configure(state=tk.NORMAL)
        room_change_box.delete("1.0", tk.END)
        if _change_entries:
            for _e in reversed(_change_entries[-12:]):
                _ts_s  = _e.get("ts_str","?")
                _act   = _e.get("action","?")
                _det   = _e.get("detail","")
                _cat   = str(_e.get("category","action") or "action").lower()
                _tag   = "good" if _cat in {"decision", "training"} else ("change" if _cat == "experiment" else "warn")
                room_change_box.insert(tk.END, f"  {_ts_s}  ", "ts")
                room_change_box.insert(tk.END, f"{_act}\n", _tag)
                if _det:
                    room_change_box.insert(tk.END, f"    {_det[:120]}\n", "dim")
        else:
            room_change_box.insert(tk.END, "  Aurora has not logged any changes yet.\n", "dim")
        room_change_box.configure(state=tk.DISABLED)

        room_act_count_lbl.configure(
            text=f"  {len(_acts)} total events" if _acts else "  no activity yet",
            fg="#4ade80" if _acts else TEXT_DIM,
        )
        room_act_box.configure(state=tk.NORMAL)
        room_act_box.delete("1.0", tk.END)
        if _acts:
            for _e in reversed(_acts[-30:]):
                _ts_s  = _e.get("ts_str","?")
                _act   = _e.get("action","?")
                _det   = _e.get("detail","")
                _cat   = _e.get("category","action")
                _det_s = f"  {_det}" if _det else ""
                room_act_box.insert(tk.END, f"  {_ts_s}  ", "ts")
                room_act_box.insert(tk.END, _act, _cat)
                room_act_box.insert(tk.END, f"{_det_s}\n", "detail")
        else:
            room_act_box.insert(tk.END, "  Aurora hasn't taken any actions yet.\n", "dim")
        room_act_box.configure(state=tk.DISABLED)

        # Poedex interaction log
        _poe_log_path = _STATE_DIR / "poedex_log.json"
        _poe_entries: list = []
        if _poe_log_path.exists():
            try:
                _poe_entries = _json.loads(_poe_log_path.read_text())
                if not isinstance(_poe_entries, list):
                    _poe_entries = []
            except Exception:
                pass
        poe_log_count_lbl.configure(
            text=f"  {len(_poe_entries)} total inquiries" if _poe_entries else "  no inquiries yet",
            fg="#818cf8" if _poe_entries else TEXT_DIM,
        )
        poe_log_box.configure(state=tk.NORMAL)
        poe_log_box.delete("1.0", tk.END)
        if _poe_entries:
            for _pe in reversed(_poe_entries[-40:]):
                _p_ts    = _pe.get("ts_str", "?")
                _p_lane  = _pe.get("lane", "?")
                _p_cat   = _pe.get("cat", "?")
                _p_q     = _pe.get("question", "?")
                _p_res   = _pe.get("result", "")
                _p_bound = _pe.get("bound", False)
                _p_cost  = _pe.get("cost_applied", False)
                _p_src   = _pe.get("source", "")
                # timestamp
                poe_log_box.insert(tk.END, f"  {_p_ts}  ", "ts")
                # lane / category badge
                _lane_tag = "scan" if _p_src == "post_study_scan" else "lane"
                poe_log_box.insert(tk.END, f"[{_p_lane}/{_p_cat}]  ", _lane_tag)
                # question
                poe_log_box.insert(tk.END, _p_q, "question")
                # bound / cost flags
                if _p_bound:
                    poe_log_box.insert(tk.END, "  ★BOUND", "bound")
                if _p_cost:
                    poe_log_box.insert(tk.END, "  ⚠COST", "cost")
                poe_log_box.insert(tk.END, "\n")
                # result (truncated to 120 chars)
                if _p_res and _p_src != "post_study_scan":
                    _res_preview = _p_res[:120].replace("\n", " ")
                    if len(_p_res) > 120:
                        _res_preview += "…"
                    poe_log_box.insert(tk.END, f"    → {_res_preview}\n", "result")
        else:
            poe_log_box.insert(tk.END, "  Aurora hasn't consulted Poedex yet.\n", "dim")
        poe_log_box.configure(state=tk.DISABLED)

        root.after(6000, _refresh_room)

    root.after(900, _refresh_room)

    # ── Hub-side camera capture thread ────────────────────────────────────────
    # The surface daemon owns the camera device and writes frame_latest.png.
    # The hub reads that file — it must NOT open the camera device directly
    # or it will block the daemon from capturing frames.
    _hub_cam_stop = threading.Event()

    import os as _os

    def _on_hub_close():
        _hub_cam_stop.set()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", _on_hub_close)

    # ── Kick off all refresh loops ─────────────────────────────────────────────
    root.after(100, refresh_overview)
    root.after(200, refresh_qao)
    root.after(300, refresh_vision)
    root.after(400, refresh_evolution)
    root.after(500, refresh_training)
    root.after(600, refresh_audio)
    root.after(600, refresh_social)
    root.after(700, refresh_manifold)
    root.after(800, refresh_lineage)

    root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    try:
        _ensure_numpy_available()
        _ensure_matplotlib_available()
        _build_ui()
    except ImportError as e:
        print(f"[Hub] Missing dependency: {e}")
        print("Install with: pip install matplotlib numpy")
        sys.exit(1)
    except Exception as e:
        print(f"[Hub] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
