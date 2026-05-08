"""
aurora_pressure_classifier.py
─────────────────────────────────────────────────────────────────────────────
Converts raw axis pressure into semantically typed pressure signals.

Raw pressure tells you WHERE the system is straining.
Typed pressure tells you WHAT KIND of deficiency is present.
Different deficiency types need different responses.

Six pressure types and what they mean:

  knowledge_gap     — Aurora lacks the conceptual content to resolve the
                      tension; the answer exists outside current internal
                      knowledge.  Signal: retrieval, study, ontology expansion.

  reasoning_gap     — Aurora has relevant knowledge but the causal/temporal
                      chain connecting it is weak.  Signal: synthesis,
                      structural reinforcement, multi-step drill.

  articulation_gap  — Aurora can think the thought but cannot express it
                      precisely or consistently.  Signal: vocabulary anchoring,
                      revision pressure, semantic precision drill.

  stability_gap     — Behavioral output varies unpredictably under equivalent
                      inputs.  Signal: strategy consolidation, identity
                      reinforcement, consistency drill.

  tool_gap          — Aurora cannot effectively use available resources or
                      calibrate interactions at the boundary.
                      Signal: tool-use training, boundary calibration,
                      interface drill.

  code_gap          — The code structures themselves are the bottleneck.
                      Signal: code evolution budget increase, architectural
                      reflection operators.

Sources used (in priority order):
  1. aurora_state/adapter_hints.json     (axis-level surface pressure + relief)
  2. aurora_state/fail_points.json       (dimension-level cumulative fails)
  3. aurora_state/surface_pressure_log.jsonl  (recent per-tick snapshots)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

_AXES = ("X", "T", "N", "B", "A")

_ADAPTER_HINTS_REL   = "aurora_state/adapter_hints.json"
_FAIL_POINTS_REL     = "aurora_state/fail_points.json"
_PRESSURE_LOG_REL    = "aurora_state/surface_pressure_log.jsonl"
_PRESSURE_MAP_REL    = "aurora_state/evo_625_pressure_map.json"

# Each cognitive dimension maps to one of the 6 pressure types.
# Derived from DIMENSION_AXIS in aurora_dream_trainer.py and semantic meaning.
_DIM_TO_TYPE: Dict[str, str] = {
    # knowledge_gap — X axis: grounding, limits, perspective
    "uncertainty_signaling":        "knowledge_gap",
    "contradiction_handling":       "knowledge_gap",
    "perspective_integration":      "knowledge_gap",
    # reasoning_gap — T axis: temporal coherence, causal chains
    "coherence_maintenance":        "reasoning_gap",
    "context_carryover":            "reasoning_gap",
    "misunderstanding_repair":      "reasoning_gap",
    "multi_turn_stability":         "reasoning_gap",
    # articulation_gap — N axis: word choice, semantic precision, concision
    "semantic_precision":           "articulation_gap",
    "compression_elaboration_fit":  "articulation_gap",
    "implied_intent_inference":     "articulation_gap",
    # tool_gap — B axis: boundary calibration, interface, emotional register
    "boundary_calibration":         "tool_gap",
    "ambiguity_handling":           "tool_gap",
    "emotional_calibration":        "tool_gap",
    # stability_gap — A axis: strategy selection, framing
    "framing_selection":            "stability_gap",
    "adaptive_strategy_selection":  "stability_gap",
}

# Axis letter → which pressure type it primarily indicates
_AXIS_TO_TYPE: Dict[str, str] = {
    "X": "knowledge_gap",
    "T": "reasoning_gap",
    "N": "articulation_gap",
    "B": "tool_gap",
    "A": "stability_gap",
}

# All 6 types
PRESSURE_TYPES = (
    "knowledge_gap",
    "reasoning_gap",
    "articulation_gap",
    "stability_gap",
    "tool_gap",
    "code_gap",
)


class TypedPressureSignal:
    """
    Holds a typed pressure classification result.

    Attributes:
        scores      {type: 0..1}  normalized pressure per type
        dominant    most pressured type name
        ranked      list of (type, score) sorted descending
        axis_sources  {axis: mean_pressure} from recent observations
        dim_sources   {dim: severity} top contributing fail dimensions
        timestamp   when this classification was computed
    """

    __slots__ = (
        "scores", "dominant", "ranked",
        "axis_sources", "dim_sources", "timestamp",
    )

    def __init__(
        self,
        scores: Dict[str, float],
        axis_sources: Dict[str, float],
        dim_sources: Dict[str, float],
    ):
        self.scores      = scores
        self.axis_sources = axis_sources
        self.dim_sources  = dim_sources
        self.timestamp   = time.time()

        self.ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        self.dominant = self.ranked[0][0] if self.ranked else "knowledge_gap"

    def above(self, threshold: float = 0.30) -> List[Tuple[str, float]]:
        """Return types with score above threshold, sorted desc."""
        return [(t, s) for t, s in self.ranked if s >= threshold]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores":       {k: round(v, 4) for k, v in self.scores.items()},
            "dominant":     self.dominant,
            "ranked":       [(t, round(s, 4)) for t, s in self.ranked],
            "axis_sources": {k: round(v, 4) for k, v in self.axis_sources.items()},
            "dim_sources":  {k: round(v, 4) for k, v in self.dim_sources.items()},
            "timestamp":    round(self.timestamp, 2),
        }


class PressureClassifier:
    """
    Classifies raw axis/dimension pressure into typed pressure signals.

    Usage:
        clf = PressureClassifier(repo_root)
        signal = clf.classify()
        print(signal.dominant)           # e.g. "reasoning_gap"
        print(signal.above(0.30))        # types above 30% pressure
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    # ── public ────────────────────────────────────────────────────────────────

    def classify(self) -> TypedPressureSignal:
        """
        Full classification pipeline.  Safe to call repeatedly.
        Returns a TypedPressureSignal with all 6 type scores.
        """
        axis_pressure  = self._axis_pressure_from_hints()
        dim_fails      = self._dim_fails_from_ledger()
        code_pressure  = self._code_pressure_from_hints()

        scores: Dict[str, float] = {t: 0.0 for t in PRESSURE_TYPES}

        # ── axis-driven component (weight 0.6) ────────────────────────────────
        for ax, pressure in axis_pressure.items():
            ptype = _AXIS_TO_TYPE.get(ax)
            if ptype:
                scores[ptype] = max(scores[ptype], pressure * 0.6)

        # ── dimension-driven component (weight 0.4 additive) ─────────────────
        dim_contribution: Dict[str, float] = defaultdict(float)
        dim_count:        Dict[str, int]   = defaultdict(int)
        for dim, severity in dim_fails.items():
            ptype = _DIM_TO_TYPE.get(dim)
            if ptype:
                dim_contribution[ptype] += severity
                dim_count[ptype]        += 1

        for ptype, total_sev in dim_contribution.items():
            count   = max(1, dim_count[ptype])
            avg_sev = min(1.0, total_sev / count)
            scores[ptype] = min(1.0, scores[ptype] + avg_sev * 0.4)

        # ── code_gap: from evolver bias composite ─────────────────────────────
        scores["code_gap"] = code_pressure

        # ── normalise all scores to [0, 1] ────────────────────────────────────
        for ptype in PRESSURE_TYPES:
            scores[ptype] = round(min(1.0, max(0.0, scores[ptype])), 4)

        # ── top contributing fail dimensions for reporting ────────────────────
        top_dims = dict(
            sorted(dim_fails.items(), key=lambda kv: -kv[1])[:8]
        )

        return TypedPressureSignal(
            scores=scores,
            axis_sources=axis_pressure,
            dim_sources=top_dims,
        )

    def status(self) -> Dict[str, Any]:
        signal = self.classify()
        return {
            "classified_at":  round(signal.timestamp, 2),
            "dominant_type":  signal.dominant,
            "scores":         signal.scores,
            "axis_sources":   signal.axis_sources,
            "top_dim_sources": signal.dim_sources,
        }

    # ── data loaders ──────────────────────────────────────────────────────────

    def _axis_pressure_from_hints(self) -> Dict[str, float]:
        """
        Read adapter_hints.json → axis_stats → mean_pressure_pre per axis.
        Falls back to surface_pressure_log mean when hints are missing or stale-zero.
        """
        hints = self._load_json(_ADAPTER_HINTS_REL)
        axis_stats = hints.get("axis_stats", {})
        result: Dict[str, float] = {}

        for ax in _AXES:
            st = axis_stats.get(ax, {})
            if st:
                result[ax] = float(st.get("mean_pressure_pre", 0.0) or 0.0)

        log_result = self._axis_pressure_from_log()
        if not result:
            return log_result

        for ax, value in log_result.items():
            if abs(float(result.get(ax, 0.0) or 0.0)) < 1e-6:
                result[ax] = value

        if not any(abs(float(v or 0.0)) > 1e-6 for v in result.values()):
            return log_result
        return result

    def _axis_pressure_from_log(self) -> Dict[str, float]:
        """Compute mean per-axis pressure from the most recent entries in
        surface_pressure_log.jsonl.  Tail-scans from the end of the file so
        it stays fast regardless of log size (which can exceed 50 MB)."""
        path = self._path(_PRESSURE_LOG_REL)
        if not os.path.exists(path):
            return {}
        _SCAN_ENTRIES = 500   # number of recent entries to average
        _CHUNK        = 65536
        sums:   Dict[str, float] = defaultdict(float)
        counts: Dict[str, int]   = defaultdict(int)
        try:
            buf   = b""
            lines = []
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                pos = fh.tell()
                while len(lines) < _SCAN_ENTRIES and pos > 0:
                    read_sz = min(_CHUNK, pos)
                    pos    -= read_sz
                    fh.seek(pos)
                    buf     = fh.read(read_sz) + buf
                    parts   = buf.split(b"\n")
                    buf     = parts[0]
                    for part in reversed(parts[1:]):
                        part = part.strip()
                        if part:
                            lines.append(part)
                        if len(lines) >= _SCAN_ENTRIES:
                            break
            for raw in lines[:_SCAN_ENTRIES]:
                try:
                    entry = json.loads(raw)
                    snap = entry.get("axis_pressure") or entry.get("intent_pressure")
                    if isinstance(snap, dict):
                        for ax in _AXES:
                            v = float(snap.get(ax, 0.0) or 0.0)
                            sums[ax]   += v
                            counts[ax] += 1
                except Exception:
                    pass
        except Exception:
            pass
        return {ax: round(sums[ax] / max(1, counts[ax]), 4) for ax in _AXES if counts[ax] > 0}

    def _dim_fails_from_ledger(self) -> Dict[str, float]:
        """
        Read fail_points.json → per-dimension average severity.
        Returns empty dict if ledger not found.
        """
        data = self._load_json(os.path.join(_STATE_ROOT, _FAIL_POINTS_REL.split("/")[-1]))
        if not data:
            # try relative path directly
            data = self._load_json(_FAIL_POINTS_REL)
        records = data.get("records", {})
        result: Dict[str, float] = {}
        for dim, rec in records.items():
            if isinstance(rec, dict):
                fail_count = int(rec.get("fail_count", 0) or 0)
                if fail_count == 0:
                    continue
                severity_sum = float(rec.get("severity_sum", 0.0) or 0.0)
                avg_sev = severity_sum / fail_count
                # weight by fail count (more fails = more reliable signal)
                weight = min(1.0, fail_count / 10.0)
                result[dim] = round(avg_sev * weight, 4)
        return result

    def _code_pressure_from_hints(self) -> float:
        """
        Estimate code_gap pressure from structural adaptation signals.

        Raw evolver bias alone is not enough, because leverage-relief may write
        strong compensatory hints that are meant to rebalance the stack rather
        than signal a permanent code bottleneck. Blend multiple surfaces:
          - axis_stats spread / baseline pressure
          - threshold and cooldown adaptation churn
          - residual evolver bias, damped when relief mode is active
        """
        hints = self._load_json(_ADAPTER_HINTS_REL)
        if not hints:
            return 0.0

        axis_stats = dict(hints.get("axis_stats") or {})
        threshold_deltas = dict(hints.get("threshold_deltas") or {})
        cooldown_mults = dict(hints.get("surface_cooldown_multipliers") or {})
        bias = dict(hints.get("evolver_bias_hints") or {})
        relief_active = bool(hints.get("leverage_redirect_active") or (hints.get("genealogy_gate_relief") or {}).get("active"))

        axis_pressure = 0.0
        pre_vals = [
            float((axis_stats.get(ax) or {}).get("mean_pressure_pre", 0.0) or 0.0)
            for ax in _AXES
            if isinstance(axis_stats.get(ax), dict)
        ]
        if pre_vals:
            span = max(pre_vals) - min(pre_vals)
            mean_pre = sum(pre_vals) / max(1, len(pre_vals))
            axis_pressure = min(1.0, span * 0.7 + mean_pre * 0.25)

        bias_pressure = 0.0
        if bias:
            values = [abs(float(v)) for v in bias.values() if v is not None]
            if values:
                bias_pressure = min(1.0, sum(values) / len(values) / 0.2)
                if relief_active:
                    bias_pressure *= 0.35

        delta_pressure = min(1.0, sum(abs(float(v)) for v in threshold_deltas.values()) / 0.08) if threshold_deltas else 0.0
        cooldown_pressure = min(1.0, len(cooldown_mults) / 8.0) if cooldown_mults else 0.0

        blended = max(axis_pressure, bias_pressure * 0.6)
        blended += delta_pressure * 0.25
        blended += cooldown_pressure * 0.15
        if relief_active and axis_pressure <= 0.0:
            blended = min(blended, 0.35)
        return round(min(1.0, max(0.0, blended)), 4)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_json(self, rel_path: str) -> Dict[str, Any]:
        # accept both absolute and relative
        path = rel_path if os.path.isabs(rel_path) else os.path.join(self.repo_root, rel_path)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _path(self, rel: str) -> str:
        return os.path.join(self.repo_root, rel)
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
