"""
Aurora-side integration wrapper for the QuasiArch Observer lattice.

This keeps the copied QuasiArch subsystem inside Aurora's stack as a
diagnostic observer first. It records interventions, builds doctrine, and
can be queried for hypotheses. Active steering is opt-in.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.quasiarch_observer import DoctrineObject, IntegratedMemoryPipeline


_QAO_MAX_BOOT_FILES = 50_000   # skip load_all() if state is larger than this


def _fast_file_count(directory: str, limit: int) -> int:
    """
    Count files in a directory, stopping once `limit` is reached.

    Uses os.scandir so it reads only enough directory entries to answer
    the question — safe to call on million-file directories without hanging.
    Returns the count (capped at `limit`), so the caller can do:
        if _fast_file_count(dir, 50_001) > 50_000: skip_load()
    """
    try:
        with os.scandir(directory) as it:
            return sum(1 for _ in itertools.islice(it, limit))
    except (OSError, FileNotFoundError):
        return 0


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _pressure_band(score: float) -> str:
    score = _clamp(score)
    if score >= 0.72:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def build_quasiarch_pressure_vector(
    systems: Optional[Dict[str, Any]],
    *,
    source: str = "",
    phase: str = "",
) -> Dict[str, Any]:
    systems = systems or {}

    autonomy = systems.get("autonomy")
    quotas = getattr(autonomy, "quotas", None)
    interactive_state = dict(systems.get("_interactive_state", {}) or {})
    consciousness = systems.get("consciousness")
    search_adapter = systems.get("search_adapter")
    checkpoint = systems.get("checkpoint")
    aurora = systems.get("aurora")
    gateway = getattr(aurora, "gateway", None) if aurora is not None else None

    dreams_used = float(getattr(quotas, "dreams_used", 0) or 0)
    study_used = float(getattr(quotas, "study_cycles_used", 0) or 0)
    observations_used = float(getattr(quotas, "observations_used", 0) or 0)
    pending_spontaneous = float(interactive_state.get("pending_spontaneous", 0) or 0)
    autonomy_running = 1.0 if bool(getattr(autonomy, "running", False)) else 0.0

    checkpoint_thread = getattr(checkpoint, "_thread", None)
    autosave_active = 1.0 if checkpoint_thread is not None and checkpoint_thread.is_alive() else 0.0

    exploration_depth = 0.0
    quarantine_depth = 0.0
    if gateway is not None:
        try:
            exploration_depth = min(1.0, len(getattr(gateway, "_exploration_queue", []) or []) / 6.0)
        except Exception:
            exploration_depth = 0.0
        try:
            quarantine_depth = min(1.0, len(getattr(gateway, "quarantine", {}) or {}) / 4.0)
        except Exception:
            quarantine_depth = 0.0

    search_attempts = float(getattr(search_adapter, "_search_attempts", 0) or 0)
    search_successes = float(getattr(search_adapter, "_search_successes", 0) or 0)
    search_failure_bias = 0.0
    if search_attempts > 0:
        search_failure_bias = _clamp((search_attempts - search_successes) / max(1.0, search_attempts))

    coherence = 1.0
    stagnation = 0.0
    if consciousness is not None and hasattr(consciousness, "entropy"):
        try:
            es = consciousness.entropy.state
            coherence = float(getattr(es, "coherence", 1.0) or 1.0)
            stagnation = float(getattr(es, "stagnation_score", 0.0) or 0.0)
        except Exception:
            pass

    coherence_deficit = _clamp(1.0 - coherence)
    background_density_score = _clamp(
        0.12 * autonomy_running
        + 0.20 * min(1.0, dreams_used / 4.0)
        + 0.18 * min(1.0, study_used / 6.0)
        + 0.10 * min(1.0, observations_used / 6.0)
        + 0.20 * min(1.0, pending_spontaneous / 4.0)
        + 0.20 * exploration_depth
    )
    io_pressure_score = _clamp(
        0.36 * autosave_active
        + 0.24 * search_failure_bias
        + 0.20 * quarantine_depth
        + 0.20 * exploration_depth
    )
    system_load_score = _clamp(
        0.34 * background_density_score
        + 0.28 * io_pressure_score
        + 0.18 * coherence_deficit
        + 0.20 * _clamp(stagnation)
    )

    return {
        "source": str(source or ""),
        "phase": str(phase or ""),
        "system_load": _pressure_band(system_load_score),
        "system_load_score": round(system_load_score, 4),
        "io_pressure": _pressure_band(io_pressure_score),
        "io_pressure_score": round(io_pressure_score, 4),
        "background_cycle_density": _pressure_band(background_density_score),
        "background_cycle_density_score": round(background_density_score, 4),
        "cognitive_coherence": round(_clamp(coherence), 4),
        "cognitive_stagnation": round(_clamp(stagnation), 4),
        "factors": {
            "autonomy_running": autonomy_running,
            "autosave_active": autosave_active,
            "dreams_used": round(dreams_used, 4),
            "study_cycles_used": round(study_used, 4),
            "observations_used": round(observations_used, 4),
            "pending_spontaneous": round(pending_spontaneous, 4),
            "exploration_depth": round(exploration_depth, 4),
            "quarantine_depth": round(quarantine_depth, 4),
            "search_failure_bias": round(search_failure_bias, 4),
            "coherence_deficit": round(coherence_deficit, 4),
        },
    }


def build_quasiarch_constraint_context(
    issue: str,
    intervention: str,
    logic_tier: str,
    systems: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    systems = systems or {}
    text = " ".join(
        part.strip().lower()
        for part in (str(issue or ""), str(intervention or ""), str(logic_tier or ""))
        if str(part or "").strip()
    )
    scores: Dict[str, float] = {axis: 0.12 for axis in ("X", "T", "N", "B", "A")}
    keywords = {
        "X": ("ground", "lookup", "fact", "knowledge", "truth", "ontology", "study", "search", "evidence"),
        "T": ("context", "carryover", "thread", "followup", "recall", "memory", "topic", "afterthought", "dream"),
        "N": ("pressure", "load", "stagnation", "entropy", "uncertain", "cost", "quota", "density", "slow"),
        "B": ("contradict", "conflict", "referent", "clarif", "ambigu", "boundary", "branch", "gap", "distinguish"),
        "A": ("repair", "intervention", "strategy", "hypothesis", "commit", "revise", "apply", "resolve", "offer"),
    }
    for axis, axis_keywords in keywords.items():
        matches = sum(1 for token in axis_keywords if token in text)
        if matches > 0:
            scores[axis] += min(0.45, matches * 0.12)

    genealogy_orientation = {}
    genealogy = systems.get("genealogy")
    if genealogy is not None and hasattr(genealogy, "pressure_orientation"):
        try:
            genealogy_orientation = {
                axis: float(value)
                for axis, value in dict(genealogy.pressure_orientation() or {}).items()
                if str(axis or "").upper() in {"X", "T", "N", "B", "A"}
            }
        except Exception:
            genealogy_orientation = {}
    for axis in ("X", "T", "N", "B", "A"):
        scores[axis] += 0.18 * _clamp(float(genealogy_orientation.get(axis, 0.0) or 0.0))

    total = sum(scores.values()) or 1.0
    normalized = {axis: round(scores[axis] / total, 4) for axis in ("X", "T", "N", "B", "A")}
    dominant_axis = max(normalized, key=normalized.get)
    purpose_lane = {
        "X": "admissibility_grounding",
        "T": "continuity_memory",
        "N": "load_uncertainty",
        "B": "distinction_branching",
        "A": "repair_commitment",
    }.get(dominant_axis, "admissibility_grounding")
    axis_signature = [
        axis for axis, weight in sorted(normalized.items(), key=lambda item: item[1], reverse=True)
        if weight >= 0.18
    ][:3]
    if not axis_signature:
        axis_signature = [dominant_axis]

    return {
        "constraint_axes": dict(normalized),
        "dominant_axis": dominant_axis,
        "axis_signature": axis_signature,
        "purpose_lane": purpose_lane,
        "genealogy_pressure_orientation": {
            axis: round(float(genealogy_orientation.get(axis, 0.0) or 0.0), 4)
            for axis in ("X", "T", "N", "B", "A")
        },
    }


TRAINING_STRATEGY_PATCHES: Dict[str, Dict[str, Any]] = {
    "context_thread_stabilization": {
        "pressure_targets": {
            "context_carryover": 0.90,
            "multi_turn_stability": 0.82,
            "coherence_maintenance": 0.74,
        },
        "behavior_modes": {"test_cross_turn_memory": 0.86},
        "constraint_axes": {"T": 0.90, "B": 0.42},
        "study_topics": ["context carryover", "multi turn stability"],
        "episodes_bonus": 1,
        "turns_bonus": 1,
        "queue_repeats": 2,
    },
    "clarification_grounding_loop": {
        "pressure_targets": {
            "ambiguity_handling": 0.86,
            "semantic_precision": 0.78,
            "boundary_calibration": 0.72,
        },
        "behavior_modes": {"ask_about_confidence": 0.72},
        "constraint_axes": {"X": 0.78, "B": 0.70, "A": 0.58},
        "study_topics": ["ambiguity handling", "semantic precision"],
        "episodes_bonus": 1,
        "turns_bonus": 0,
        "queue_repeats": 2,
    },
    "lookup_bridge_activation": {
        "pressure_targets": {
            "uncertainty_signaling": 0.82,
            "semantic_precision": 0.72,
            "boundary_calibration": 0.66,
        },
        "behavior_modes": {"ask_about_confidence": 0.70},
        "constraint_axes": {"N": 0.82, "X": 0.72, "A": 0.46},
        "study_topics": ["uncertainty signaling", "semantic precision"],
        "episodes_bonus": 0,
        "turns_bonus": 0,
        "queue_repeats": 1,
    },
    "uncertainty_signal_repair": {
        "pressure_targets": {
            "uncertainty_signaling": 0.92,
            "semantic_precision": 0.70,
        },
        "behavior_modes": {"ask_about_confidence": 0.80},
        "constraint_axes": {"N": 0.92, "X": 0.54},
        "study_topics": ["uncertainty signaling"],
        "episodes_bonus": 0,
        "turns_bonus": 0,
        "queue_repeats": 1,
    },
    "repair_path_stabilization": {
        "pressure_targets": {
            "misunderstanding_repair": 0.90,
            "contradiction_handling": 0.84,
            "boundary_calibration": 0.66,
        },
        "behavior_modes": {
            "present_conflicting_evidence": 0.78,
            "ask_about_confidence": 0.58,
        },
        "constraint_axes": {"A": 0.90, "B": 0.84},
        "study_topics": ["misunderstanding repair", "contradiction handling"],
        "episodes_bonus": 1,
        "turns_bonus": 1,
        "queue_repeats": 2,
    },
    "evidence_alignment_repair": {
        "pressure_targets": {
            "semantic_precision": 0.82,
            "coherence_maintenance": 0.72,
            "framing_selection": 0.68,
        },
        "behavior_modes": {"present_conflicting_evidence": 0.64},
        "constraint_axes": {"X": 0.82, "T": 0.72, "A": 0.50},
        "study_topics": ["semantic precision", "coherence maintenance"],
        "episodes_bonus": 1,
        "turns_bonus": 0,
        "queue_repeats": 2,
    },
    "response_pressure_rebalancing": {
        "pressure_targets": {
            "framing_selection": 0.72,
            "adaptive_strategy_selection": 0.70,
            "compression_elaboration_fit": 0.66,
        },
        "behavior_modes": {"use_vague_phrasing": 0.42},
        "constraint_axes": {"A": 0.72, "N": 0.66},
        "study_topics": ["framing selection", "adaptive strategy selection"],
        "episodes_bonus": 0,
        "turns_bonus": 0,
        "queue_repeats": 1,
    },
}


@dataclass
class QuasiArchGateDecision:
    mode: str
    phase: str
    issue_category: str
    doctrine_id: str = ""
    doctrine_strategy: str = ""
    doctrine_confidence: float = 0.0
    doctrine_version: int = 0
    applied: bool = False
    rationale: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "phase": self.phase,
            "issue_category": self.issue_category,
            "doctrine_id": self.doctrine_id,
            "doctrine_strategy": self.doctrine_strategy,
            "doctrine_confidence": self.doctrine_confidence,
            "doctrine_version": self.doctrine_version,
            "applied": self.applied,
            "rationale": list(self.rationale),
        }


class AuroraQuasiArchObserver:
    """
    Aurora runtime adapter for QuasiArch diagnostics.

    Modes:
      - shadow:   record only
      - advisory: record + attach recommendations
      - gated:    advisory + allow doctrine to modify training plans if
                  confidence and applicability thresholds are met
    """

    def __init__(
        self,
        state_dir: str = _STATE_ROOT,
        mode: Optional[str] = None,
        gate_confidence: float = 0.82,
        advisory_confidence: float = 0.62,
    ) -> None:
        self.state_dir = state_dir
        self.storage_dir = os.path.join(state_dir, "quasiarch_observer")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.pipeline = IntegratedMemoryPipeline(storage_dir=self.storage_dir)
        # Guard: if the state directory has grown beyond _QAO_MAX_BOOT_FILES files
        # (glob("*.json") on millions of files hangs the process for minutes), skip
        # load_all() and start cold.  The observer still runs — it just won't have
        # historical memory from prior sessions until the state is pruned.
        _edges_dir = os.path.join(self.storage_dir, "edges")
        _state_file_count = _fast_file_count(_edges_dir, _QAO_MAX_BOOT_FILES + 1)
        if _state_file_count > _QAO_MAX_BOOT_FILES:
            print(
                f"  [QAO] State too large ({_state_file_count}+ files in edges/) — "
                f"skipping load_all() to prevent boot stall.  "
                f"Run scripts/reset_quasiarch_observer_state.sh to prune."
            )
        else:
            try:
                self.pipeline.memory.load_all()
            except Exception:
                pass
        self._mode_requested = mode
        self.mode = str(mode or os.environ.get("AURORA_QUASIARCH_MODE", "advisory")).strip().lower()
        if self.mode not in {"shadow", "advisory", "gated"}:
            self.mode = "advisory"
        self.gate_confidence = float(gate_confidence)
        self.advisory_confidence = float(advisory_confidence)
        self.issue_counts: Dict[str, int] = {}
        self.consultation_counts: Dict[str, int] = {}
        self.consultation_debt: float = 0.0
        self.issue_consultation_debt: Dict[str, float] = {}
        self.hypothesis_credit: float = 0.0
        self.possibility_pressure: float = 0.0
        self.issue_possibility_pressure: Dict[str, float] = {}
        self.recent_events: Deque[Dict[str, Any]] = deque(maxlen=96)
        self.consultation_history: Deque[Dict[str, Any]] = deque(maxlen=96)
        self.gate_history: Deque[Dict[str, Any]] = deque(maxlen=96)
        self._state_path = os.path.join(self.storage_dir, "runtime_state.json")
        self.systems: Dict[str, Any] = {}
        self._load_state()

    def attach_systems(self, systems: Optional[Dict[str, Any]]) -> None:
        self.systems = dict(systems or {})

    def _normalize_genealogy_refs(self, refs: Any) -> List[Dict[str, Any]]:
        if isinstance(refs, dict):
            candidates = [refs]
        elif isinstance(refs, list):
            candidates = list(refs)
        else:
            candidates = []

        normalized: List[Dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            target_files = [
                str(path).strip()
                for path in (item.get("target_files", []) or [])
                if str(path).strip()
            ]
            constraints = [
                str(value).strip()
                for value in (item.get("constraints", []) or [])
                if str(value).strip()
            ]
            ref = {
                "source": str(item.get("source", "") or "").strip(),
                "source_episode_id": str(item.get("source_episode_id", "") or "").strip(),
                "seed_lineage_id": str(item.get("seed_lineage_id", "") or "").strip(),
                "evidence_id": str(item.get("evidence_id", "") or "").strip(),
                "mutation_name": str(item.get("mutation_name", "") or "").strip(),
                "mutation_id": str(item.get("mutation_id", "") or "").strip(),
                "operator_key": str(item.get("operator_key", "") or "").strip(),
                "ability_id": str(item.get("ability_id", "") or "").strip(),
                "operation_lineage_id": str(item.get("operation_lineage_id", "") or "").strip(),
                "registered": bool(item.get("registered", False)),
                "accepted": bool(item.get("accepted", False)),
                "constraints": constraints,
                "target_files": target_files,
            }
            if any(
                ref[key]
                for key in (
                    "source_episode_id",
                    "seed_lineage_id",
                    "evidence_id",
                    "mutation_id",
                    "ability_id",
                    "operation_lineage_id",
                )
            ):
                normalized.append(ref)
        return normalized

    def _extract_genealogy_refs(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        refs = self._normalize_genealogy_refs(payload.get("genealogy_refs"))
        if refs:
            return refs
        refs = self._normalize_genealogy_refs(payload.get("code_evolution_refs"))
        if refs:
            return refs
        dream_apply = payload.get("dream_apply")
        if isinstance(dream_apply, dict):
            refs = self._normalize_genealogy_refs(dream_apply.get("code_evolution_refs"))
            if refs:
                return refs
        return []

    def _load_state(self) -> None:
        if not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return
        loaded_mode = str(data.get("mode", self.mode) or self.mode).lower()
        if loaded_mode not in {"shadow", "advisory", "gated"}:
            loaded_mode = self.mode
        if self._mode_requested is None and not os.environ.get("AURORA_QUASIARCH_MODE", "").strip():
            if loaded_mode == "gated":
                loaded_mode = "advisory"
        self.mode = loaded_mode
        self.issue_counts = {
            str(key): int(value)
            for key, value in dict(data.get("issue_counts", {}) or {}).items()
        }
        self.consultation_counts = {
            str(key): int(value)
            for key, value in dict(data.get("consultation_counts", {}) or {}).items()
        }
        self.consultation_debt = float(data.get("consultation_debt", 0.0) or 0.0)
        self.issue_consultation_debt = {
            str(key): float(value)
            for key, value in dict(data.get("issue_consultation_debt", {}) or {}).items()
        }
        self.hypothesis_credit = float(data.get("hypothesis_credit", 0.0) or 0.0)
        self.possibility_pressure = float(data.get("possibility_pressure", 0.0) or 0.0)
        self.issue_possibility_pressure = {
            str(key): float(value)
            for key, value in dict(data.get("issue_possibility_pressure", {}) or {}).items()
        }
        self.recent_events.clear()
        for item in list(data.get("recent_events", []) or [])[-self.recent_events.maxlen:]:
            if isinstance(item, dict):
                self.recent_events.append(dict(item))
        self.consultation_history.clear()
        for item in list(data.get("consultation_history", []) or [])[-self.consultation_history.maxlen:]:
            if isinstance(item, dict):
                self.consultation_history.append(dict(item))
        self.gate_history.clear()
        for item in list(data.get("gate_history", []) or [])[-self.gate_history.maxlen:]:
            if isinstance(item, dict):
                self.gate_history.append(dict(item))

    def _write_runtime_state(self) -> bool:
        try:
            payload = {
                "mode": self.mode,
                "gate_confidence": self.gate_confidence,
                "advisory_confidence": self.advisory_confidence,
                "issue_counts": dict(self.issue_counts),
                "consultation_counts": dict(self.consultation_counts),
                "consultation_debt": float(self.consultation_debt),
                "issue_consultation_debt": dict(self.issue_consultation_debt),
                "hypothesis_credit": float(self.hypothesis_credit),
                "possibility_pressure": float(self.possibility_pressure),
                "issue_possibility_pressure": dict(self.issue_possibility_pressure),
                "recent_events": list(self.recent_events),
                "consultation_history": list(self.consultation_history),
                "gate_history": list(self.gate_history),
                "saved_at": time.time(),
            }
            with open(self._state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            return True
        except Exception:
            return False

    def save(self) -> bool:
        try:
            self.pipeline.memory.live_save()
            try:
                self.pipeline.ghost_relics.save()
            except Exception:
                pass
            return self._write_runtime_state()
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        stats = {}
        try:
            stats = self.pipeline.memory.stats()
        except Exception:
            stats = {}
        relic_stats = {}
        try:
            relic_stats = self.pipeline.get_ghost_relic_stats()
        except Exception:
            relic_stats = {}
        return {
            "mode": self.mode,
            "gate_confidence": self.gate_confidence,
            "advisory_confidence": self.advisory_confidence,
            "issue_families_tracked": len(stats.get("issue_families", []) or []),
            "quasi_archetypes": list(stats.get("quasi_archetypes", []) or []),
            "recent_event_count": len(self.recent_events),
            "consultation_event_count": len(self.consultation_history),
            "recent_gate_count": len(self.gate_history),
            "ghost_relics": int(relic_stats.get("total_relics", 0) or 0),
            "reformations": int(relic_stats.get("total_reformations", 0) or 0),
            "consultation_debt": round(float(self.consultation_debt), 4),
            "hypothesis_credit": round(float(self.hypothesis_credit), 4),
            "possibility_pressure": round(float(self.possibility_pressure), 4),
            "issue_consultation_debt": {
                key: round(float(value), 4)
                for key, value in sorted(
                    self.issue_consultation_debt.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
            },
            "issue_possibility_pressure": {
                key: round(float(value), 4)
                for key, value in sorted(
                    self.issue_possibility_pressure.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
            },
        }

    def get_doctrine_candidates(
        self,
        issue_category: str,
        logic_tier: str = "runtime_orchestration",
        distribution_context: str = "multi_module__same_tier",
        min_confidence: Optional[float] = None,
        limit: int = 3,
        phase: str = "runtime_exact",
        charge_cost: bool = True,
    ) -> List[Dict[str, Any]]:
        confidence_floor = (
            float(self.advisory_confidence)
            if min_confidence is None
            else float(min_confidence)
        )
        try:
            candidates = self.pipeline.get_doctrine_candidates_for_event(
                {
                    "issue": str(issue_category or ""),
                    "logic_tier": str(logic_tier or "runtime_orchestration"),
                    "distribution_context": str(distribution_context or "multi_module__same_tier"),
                },
                min_confidence=confidence_floor,
            )
        except Exception:
            candidates = []
        result: List[Dict[str, Any]] = []
        for candidate in candidates[: max(0, int(limit))]:
            entry = candidate.to_dict()
            if charge_cost:
                entry["consultation_cost"] = self._record_consultation(
                    issue_category=issue_category,
                    doctrine=candidate,
                    phase=phase,
                    rotation_count=0,
                    consumer="runtime",
                    resolution_mode="exact",
                )
            result.append(entry)
        return result

    def reason_about_event(
        self,
        issue_category: str,
        logic_tier: str = "runtime_orchestration",
        distribution_context: str = "multi_module__same_tier",
        min_confidence: Optional[float] = None,
        limit: int = 2,
        rotate: bool = True,
        charge_cost: bool = True,
        phase: str = "runtime_reasoning",
        consumer: str = "runtime",
    ) -> Dict[str, Any]:
        confidence_floor = (
            float(self.advisory_confidence)
            if min_confidence is None
            else float(min_confidence)
        )
        event = {
            "issue": str(issue_category or ""),
            "logic_tier": str(logic_tier or "runtime_orchestration"),
            "distribution_context": str(distribution_context or "multi_module__same_tier"),
        }
        try:
            candidates = self.pipeline.get_doctrine_candidates_for_event(
                event,
                min_confidence=confidence_floor,
            )
        except Exception:
            candidates = []

        analyses: List[Dict[str, Any]] = []
        for doctrine in candidates[: max(0, int(limit))]:
            entry: Dict[str, Any] = {
                "doctrine": doctrine.to_dict(),
                "hypotheses": [],
            }
            if rotate:
                for rotation_name in list(doctrine.available_rotations or []):
                    try:
                        rotation = self.pipeline.rotate_and_record(doctrine.quasi_id, rotation_name)
                    except Exception:
                        rotation = None
                    if rotation is None:
                        continue
                    entry["hypotheses"].append(
                        {
                            "rotation": rotation.rotation_name,
                            "pivot_point_scores": dict(rotation.pivot_point_scores),
                            "hypotheses": list(rotation.hypotheses),
                        }
                    )
            analyses.append(entry)

        hypothesis_credit = None
        if charge_cost:
            total_hypotheses = sum(
                len(rotation.get("hypotheses", []) or [])
                for analysis in analyses
                for rotation in list(analysis.get("hypotheses", []) or [])
            )
            ambiguity_span = max(0, len(analyses) - 1) + total_hypotheses
            quality = self._score_hypothesis_quality(
                issue_category=issue_category,
                analyses=analyses,
            )
            hypothesis_credit = self._record_hypothesis_hold(
                issue_category=issue_category,
                phase=phase,
                consumer=consumer,
                hypothesis_count=max(total_hypotheses, len(analyses)),
                ambiguity_span=ambiguity_span,
                quality=quality,
            )
            for analysis in analyses:
                analysis["hypothesis_credit"] = dict(hypothesis_credit)

        return {
            "event": event,
            "mode": self.mode,
            "candidate_count": len(candidates),
            "analyses": analyses,
            "hypothesis_credit": hypothesis_credit,
        }

    def _score_hypothesis_quality(
        self,
        issue_category: str,
        analyses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        issue_key = str(issue_category or "unknown_issue").strip() or "unknown_issue"
        hypothesis_records: List[Dict[str, Any]] = []
        signatures: List[str] = []

        for analysis in list(analyses or []):
            for rotation in list(analysis.get("hypotheses", []) or []):
                rotation_name = str(rotation.get("rotation", "") or "")
                for hypothesis in list(rotation.get("hypotheses", []) or []):
                    if not isinstance(hypothesis, dict):
                        continue
                    informative_keys = [
                        str(key)
                        for key, value in hypothesis.items()
                        if key not in {"hypothesis_type", "recommendation"}
                        and value not in ("", None, [], {}, "unknown", "none")
                    ]
                    recommendation = str(hypothesis.get("recommendation", "") or "").strip()
                    informative = bool(informative_keys or recommendation)
                    signature_parts = [rotation_name]
                    for key in sorted(informative_keys)[:4]:
                        signature_parts.append(f"{key}:{hypothesis.get(key)}")
                    if recommendation:
                        signature_parts.append(f"rec:{recommendation}")
                    if len(signature_parts) == 1:
                        signature_parts.append("uninformative")
                    signature = " | ".join(signature_parts)
                    signatures.append(signature)
                    hypothesis_records.append(
                        {
                            "rotation": rotation_name,
                            "informative": informative,
                            "recommendation": bool(recommendation),
                            "signature": signature,
                        }
                    )

        total = len(hypothesis_records)
        if total <= 0:
            return {
                "qualified": False,
                "coherence": 0.0,
                "novelty": 0.0,
                "stagnation": 1.0,
                "quality": 0.0,
                "signatures": [],
            }

        informative_ratio = sum(1 for rec in hypothesis_records if rec["informative"]) / float(total)
        recommendation_ratio = sum(1 for rec in hypothesis_records if rec["recommendation"]) / float(total)
        unique_signatures = list(dict.fromkeys(signatures))
        diversity_ratio = len(unique_signatures) / float(total)

        recent_signature_sets: List[set] = []
        for item in reversed(self.consultation_history):
            if item.get("resolution_mode") != "hypothesis":
                continue
            if str(item.get("issue_category", "") or "") != issue_key:
                continue
            prior = set(str(sig) for sig in list(item.get("signatures", []) or []) if sig)
            if prior:
                recent_signature_sets.append(prior)
            if len(recent_signature_sets) >= 4:
                break

        current_set = set(unique_signatures)
        stagnation_scores: List[float] = []
        for prior in recent_signature_sets:
            union = len(current_set | prior)
            if union <= 0:
                continue
            stagnation_scores.append(len(current_set & prior) / float(union))
        stagnation = sum(stagnation_scores) / float(len(stagnation_scores)) if stagnation_scores else 0.0

        coherence = min(1.0, 0.58 * informative_ratio + 0.42 * recommendation_ratio)
        novelty = max(0.0, min(1.0, diversity_ratio - (0.55 * stagnation)))
        quality = max(0.0, min(1.0, 0.62 * coherence + 0.38 * novelty))
        qualified = bool(
            total >= 2
            and coherence >= 0.52
            and quality >= 0.48
            and stagnation <= 0.72
        )
        return {
            "qualified": qualified,
            "coherence": round(coherence, 4),
            "novelty": round(novelty, 4),
            "stagnation": round(stagnation, 4),
            "quality": round(quality, 4),
            "signatures": unique_signatures[:8],
        }

    def _record_consultation(
        self,
        issue_category: str,
        doctrine: DoctrineObject,
        phase: str,
        rotation_count: int,
        consumer: str,
        resolution_mode: str = "exact",
    ) -> Dict[str, Any]:
        issue_key = str(issue_category or "unknown_issue").strip() or "unknown_issue"
        issue_count = int(self.consultation_counts.get(issue_key, 0) or 0)
        phase_low = str(phase or "").lower()
        training_phase = any(token in phase_low for token in ("train", "epoch", "burst", "corpus"))
        confidence = float(getattr(doctrine, "confidence", 0.0) or 0.0)
        coherence = float(getattr(doctrine, "coherence_index", 0.0) or 0.0)
        novelty = float(getattr(doctrine, "novelty_index", 0.0) or 0.0)
        exact_mode = str(resolution_mode or "exact").lower() == "exact"
        base_cost = 0.10 if training_phase and exact_mode else 0.06 if exact_mode else 0.03
        familiarity_cost = min(0.24, issue_count * 0.03)
        maturity_cost = max(0.0, min(0.18, confidence * 0.10 + coherence * 0.08 - novelty * 0.06))
        rotation_cost = min(0.06, max(0, int(rotation_count)) * 0.01)
        total_cost = round(base_cost + familiarity_cost + maturity_cost + rotation_cost, 4)

        self.consultation_counts[issue_key] = issue_count + 1
        current_issue_debt = float(self.issue_consultation_debt.get(issue_key, 0.0) or 0.0)
        updated_issue_debt = round(min(3.0, current_issue_debt + total_cost), 4)
        self.issue_consultation_debt[issue_key] = updated_issue_debt
        self.consultation_debt = round(min(6.0, float(self.consultation_debt) + total_cost), 4)

        record = {
            "timestamp": time.time(),
            "issue_category": issue_key,
            "phase": str(phase or ""),
            "consumer": str(consumer or "runtime"),
            "resolution_mode": "exact" if exact_mode else "advisory",
            "doctrine_id": str(getattr(doctrine, "quasi_id", "") or ""),
            "strategy": str(getattr(doctrine, "primary_strategy", "") or ""),
            "cost": total_cost,
            "global_debt": float(self.consultation_debt),
            "issue_debt": updated_issue_debt,
            "rotation_count": int(rotation_count or 0),
        }
        self.consultation_history.append(record)
        return {
            "cost": total_cost,
            "global_debt": float(self.consultation_debt),
            "issue_debt": updated_issue_debt,
            "issue_consults": int(self.consultation_counts.get(issue_key, 0) or 0),
        }

    def _record_hypothesis_hold(
        self,
        issue_category: str,
        phase: str,
        consumer: str,
        hypothesis_count: int,
        ambiguity_span: int,
        quality: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        issue_key = str(issue_category or "unknown_issue").strip() or "unknown_issue"
        hypotheses = max(1, int(hypothesis_count or 0))
        span = max(0, int(ambiguity_span or 0))
        quality = dict(quality or {})
        coherence_raw = quality.get("coherence", 0.0)
        novelty_raw = quality.get("novelty", 0.0)
        stagnation_raw = quality.get("stagnation", 1.0)
        quality_raw = quality.get("quality", 0.0)
        coherence = float(0.0 if coherence_raw is None else coherence_raw)
        novelty = float(0.0 if novelty_raw is None else novelty_raw)
        stagnation = float(1.0 if stagnation_raw is None else stagnation_raw)
        quality_score = float(0.0 if quality_raw is None else quality_raw)
        coherent = coherence >= 0.52 and quality_score >= 0.48
        non_stagnant = stagnation <= 0.72 and novelty >= 0.18
        qualified = bool(quality.get("qualified", False) and coherent and non_stagnant)
        if qualified:
            reward = round(
                min(
                    0.26,
                    (0.03 + hypotheses * 0.022 + min(0.05, span * 0.008))
                    * max(0.45, quality_score),
                ),
                4,
            )
            pressure_gain = round(
                min(
                    0.34,
                    (0.04 + hypotheses * 0.02 + min(0.08, span * 0.01))
                    * max(0.45, (0.55 * coherence + 0.45 * novelty)),
                ),
                4,
            )
        else:
            reward = 0.0
            pressure_gain = 0.0

        self.hypothesis_credit = round(min(6.0, float(self.hypothesis_credit) + reward), 4)
        self.possibility_pressure = round(min(6.0, float(self.possibility_pressure) + pressure_gain), 4)
        current_issue_pressure = float(self.issue_possibility_pressure.get(issue_key, 0.0) or 0.0)
        self.issue_possibility_pressure[issue_key] = round(min(3.0, current_issue_pressure + pressure_gain), 4)
        if qualified:
            self.consultation_debt = round(max(0.0, float(self.consultation_debt) - min(0.08, reward * 0.5)), 4)
            current_issue_debt = float(self.issue_consultation_debt.get(issue_key, 0.0) or 0.0)
            self.issue_consultation_debt[issue_key] = round(max(0.0, current_issue_debt - min(0.06, reward * 0.4)), 4)
        record = {
            "timestamp": time.time(),
            "issue_category": issue_key,
            "phase": str(phase or ""),
            "consumer": str(consumer or "runtime"),
            "resolution_mode": "hypothesis",
            "hypothesis_count": hypotheses,
            "ambiguity_span": span,
            "qualified": qualified,
            "coherent": coherent,
            "non_stagnant": non_stagnant,
            "coherence": round(coherence, 4),
            "novelty": round(novelty, 4),
            "stagnation": round(stagnation, 4),
            "quality": round(quality_score, 4),
            "signatures": list(quality.get("signatures", []) or []),
            "reward": reward,
            "possibility_pressure": pressure_gain,
            "global_hypothesis_credit": float(self.hypothesis_credit),
            "global_possibility_pressure": float(self.possibility_pressure),
        }
        self.consultation_history.append(record)
        return {
            "reward": reward,
            "possibility_pressure": pressure_gain,
            "qualified": qualified,
            "coherent": coherent,
            "non_stagnant": non_stagnant,
            "coherence": round(coherence, 4),
            "novelty": round(novelty, 4),
            "stagnation": round(stagnation, 4),
            "quality": round(quality_score, 4),
            "global_hypothesis_credit": float(self.hypothesis_credit),
            "global_possibility_pressure": float(self.possibility_pressure),
            "global_consultation_debt": float(self.consultation_debt),
        }

    def _apply_learning_credit(
        self,
        issue_category: str,
        observed_effect: str,
    ) -> Dict[str, float]:
        issue_key = str(issue_category or "unknown_issue").strip() or "unknown_issue"
        effect_key = str(observed_effect or "").strip().lower()
        credit_map = {
            "resolved_fully": 0.20,
            "resolved_partially": 0.10,
            "pending_verification": 0.04,
            "no_change_observed": 0.0,
            "regression_introduced": -0.06,
        }
        credit = float(credit_map.get(effect_key, 0.0))
        issue_debt = float(self.issue_consultation_debt.get(issue_key, 0.0) or 0.0)
        if credit >= 0.0:
            issue_debt = max(0.0, issue_debt - credit)
            self.consultation_debt = max(0.0, float(self.consultation_debt) - credit)
            self.possibility_pressure = max(0.0, float(self.possibility_pressure) - min(0.08, credit * 0.5))
        else:
            issue_debt = min(3.0, issue_debt + abs(credit))
            self.consultation_debt = min(6.0, float(self.consultation_debt) + abs(credit))
            self.possibility_pressure = min(6.0, float(self.possibility_pressure) + abs(credit))
        self.issue_consultation_debt[issue_key] = round(issue_debt, 4)
        self.consultation_debt = round(float(self.consultation_debt), 4)
        return {
            "credit": round(credit, 4),
            "global_debt": float(self.consultation_debt),
            "issue_debt": float(self.issue_consultation_debt.get(issue_key, 0.0) or 0.0),
        }

    def record_observation(
        self,
        target: str,
        data: Any,
        source: str = "OBSERVER",
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Record a passive ground-truth observation with OBSERVER provenance.
        Used by SediMemory and other subsystems for telemetry without
        triggering the full intervention pipeline.
        """
        import time as _t
        import inspect as _qao_inspect
        ts = float(timestamp if timestamp is not None else _t.time())
        
        # Locate the exact code call
        try:
            caller_frame = _qao_inspect.stack()[1]
            code_call = f"{os.path.basename(caller_frame.filename)}:{caller_frame.lineno} ({caller_frame.function})"
        except Exception:
            code_call = "unknown"

        event = {
            "target": str(target),
            "data": data,
            "source": str(source),
            "ts": ts,
            "provenance": "OBSERVER",
            "code_call": code_call,
        }
        self.recent_events.append(event)

    def record_intervention_event(
        self,
        target: str,
        issue: str,
        logic_tier: str,
        intervention: str,
        intended_effect: str,
        observed_effect: str,
        tags: Optional[List[str]] = None,
        auto_advance: Optional[bool] = None,
        rotate_doctrine: bool = False,
        system_pressure: Optional[Dict[str, Any]] = None,
        genealogy_refs: Optional[Any] = None,
        code_call: Optional[str] = None,
    ) -> Dict[str, Any]:
        issue_key = str(issue or "unknown_issue").strip() or "unknown_issue"
        self.issue_counts[issue_key] = int(self.issue_counts.get(issue_key, 0) or 0) + 1
        count = self.issue_counts[issue_key]
        if auto_advance is None:
            auto_advance = self._should_auto_advance(issue_key, observed_effect, count)
        constraint_context = build_quasiarch_constraint_context(
            issue=issue_key,
            intervention=str(intervention or ""),
            logic_tier=str(logic_tier or ""),
            systems=self.systems,
        )
        pressure_vector = build_quasiarch_pressure_vector(
            self.systems,
            source=str(target or issue_key),
            phase=str((tags or ["runtime"])[:1][0] if tags else "runtime"),
        )
        if isinstance(system_pressure, dict) and system_pressure:
            merged_pressure = dict(pressure_vector)
            merged_pressure.update(system_pressure)
            pressure_vector = merged_pressure
        normalized_genealogy_refs = self._normalize_genealogy_refs(genealogy_refs)
        
        event_payload = {
            "target": str(target or "aurora.unknown_target"),
            "issue": issue_key,
            "logic_tier": str(logic_tier or "runtime_orchestration"),
            "intervention": str(intervention or "unknown_intervention"),
            "intended_effect": str(intended_effect or "stabilize_behavior"),
            "observed_effect": str(observed_effect or "pending_verification"),
            "constraint_context": dict(constraint_context),
            "system_pressure": dict(pressure_vector),
            "genealogy_refs": list(normalized_genealogy_refs),
        }
        if code_call:
            event_payload["code_call"] = str(code_call)

        result = self.pipeline.observe_intervention_event(
            event=event_payload,
            tags=list(tags or []),
            auto_advance=bool(auto_advance),
            rotate_doctrine=bool(rotate_doctrine and auto_advance),
        )
        doctrine = None
        advance_summary = result.get("advance_summary") if isinstance(result, dict) else None
        if isinstance(advance_summary, dict):
            doctrine = advance_summary.get("doctrine")
        event_summary = {
            "timestamp": time.time(),
            "target": str(target),
            "issue_category": issue_key,
            "logic_tier": logic_tier,
            "intervention": intervention,
            "observed_effect": observed_effect,
            "code_call": code_call,
            "count": count,
            "auto_advance": bool(auto_advance),
            "doctrine_strategy": getattr(doctrine, "primary_strategy", ""),
            "doctrine_confidence": float(getattr(doctrine, "confidence", 0.0) or 0.0),
            "constraint_context": dict(constraint_context),
            "system_pressure": dict(pressure_vector),
            "genealogy_refs": list(normalized_genealogy_refs),
        }
        event_summary["learning_credit"] = self._apply_learning_credit(
            issue_key,
            observed_effect,
        )
        self.recent_events.append(event_summary)
        self._write_runtime_state()
        return {
            "event": event_summary,
            "base_node": result.get("base_node") if isinstance(result, dict) else None,
            "advance_summary": advance_summary,
        }

    # ── Observer loop: flush QAO events → chamber evidence ───────────────────
    _QAO_AXIS_MAP: Dict[str, str] = {
        "existence": "X", "temporal": "T", "energy": "N",
        "boundary": "B", "agency": "A",
    }

    def get_recent_evidence_dicts(self, max_events: int = 8) -> List[Dict[str, Any]]:
        """
        Convert the N most-recent intervention events into evidence dicts
        compatible with EvolutionaryChamber.observe_external_evidence().

        Called every 5 turns by aurora.py to close the observer loop:
        QAO records an intervention → next tick that signal enters chamber
        pressure instead of only deferred to the next session's fail ledger.
        """
        out: List[Dict[str, Any]] = []
        for ev in list(self.recent_events)[-max_events:]:
            if not isinstance(ev, dict):
                continue
            sp = dict(ev.get("system_pressure") or {})
            # Build per-axis relief/cost from system_pressure values
            relief: Dict[str, float] = {}
            cost: Dict[str, float] = {}
            max_relief_axis = "X"
            max_relief_val = 0.0
            for long_name, short in self._QAO_AXIS_MAP.items():
                raw = float(sp.get(long_name, sp.get(short, 0.0)) or 0.0)
                relief[short] = round(min(0.05, raw * 0.10), 6)
                cost[short] = round(min(0.01, raw * 0.02), 6)
                if relief[short] > max_relief_val:
                    max_relief_val = relief[short]
                    max_relief_axis = short
            # Derive confidence from learning credit, scaled by inverse axis
            # participation rate.  Rare axes (A=0.0001) carry more signal per
            # observation than high-frequency axes (X=1.0), so their events
            # deserve proportionally higher confidence weight.
            _AXIS_PARTICIPATION = {"X": 1.0, "T": 0.1, "N": 0.01, "B": 0.001, "A": 0.0001}
            lc = ev.get("learning_credit") or {}
            if isinstance(lc, dict):
                raw_credit = float(lc.get("credit", 0.0) or 0.0)
            else:
                raw_credit = 0.0
            _participation = _AXIS_PARTICIPATION.get(max_relief_axis, 1.0)
            # Inverse participation: A-axis events (rare) get up to 4x boost,
            # X-axis events (frequent) get no boost. Cap multiplier at 4.
            _inv_participation = min(4.0, 1.0 / max(0.25, _participation))
            confidence = round(min(1.0, (abs(raw_credit) * 0.5 + 0.25) * _inv_participation * 0.5), 4)
            issue = str(ev.get("issue_category", "qao_event") or "qao_event")
            intervention = str(ev.get("intervention", "") or "")
            out.append({
                "source":          "quasiarch_observer",
                "op_id":           f"qao:{issue}",
                "kind":            "reflection",
                "outcome":         "intervention",
                "axis":            max_relief_axis,
                "relief":          relief,
                "cost":            cost,
                "pressure_before": {},
                "pressure_after":  {},
                "mutation_name":   f"qao_{issue[:40]}",
                "action_label":    f"qao:{intervention[:16]}",
                "notes": {
                    "confidence":       confidence,
                    "issue_category":   issue,
                    "logic_tier":       str(ev.get("logic_tier", "") or ""),
                    "doctrine_strategy": str(ev.get("doctrine_strategy", "") or ""),
                    "observed_effect":  str(ev.get("observed_effect", "") or ""),
                },
            })
        return out

    def record_training_epoch(
        self,
        plan: Dict[str, Any],
        result: Dict[str, Any],
        phase: str,
    ) -> Dict[str, Any]:
        issue, intervention, intended_effect = self._derive_training_event(plan)
        fitness = float((result or {}).get("avg_fitness", 0.0) or 0.0)
        shards = int((result or {}).get("learner_shards", 0) or 0)
        observed_effect = self._observed_effect_from_training(fitness, shards, plan)
        tags = ["aurora", "train", str(phase or "train")]
        dominant_targets = list(dict(plan.get("pressure_targets", {}) or {}).keys())[:3]
        tags.extend(f"dim:{dim}" for dim in dominant_targets)
        genealogy_refs = self._extract_genealogy_refs(result)
        return self.record_intervention_event(
            target="aurora.gateway.simulation.run_epoch",
            issue=issue,
            logic_tier="evolutionary_pipeline",
            intervention=intervention,
            intended_effect=intended_effect,
            observed_effect=observed_effect,
            tags=tags,
            auto_advance=True,
            rotate_doctrine=False,
            genealogy_refs=genealogy_refs,
        )

    def record_corpus_response(
        self,
        prompt_text: str,
        aurora_text: str,
        truth_text: str,
        phase: str,
        kind: str,
        signal: float,
        threshold: float,
        counter_pressure: float,
        prompt_grounding: float,
        truth_alignment: float,
    ) -> Dict[str, Any]:
        issue, intervention, intended_effect = self._derive_corpus_event(
            prompt_text=prompt_text,
            kind=kind,
            truth_alignment=truth_alignment,
            prompt_grounding=prompt_grounding,
        )
        observed_effect = self._observed_effect_from_corpus(
            signal=signal,
            threshold=threshold,
            counter_pressure=counter_pressure,
            truth_alignment=truth_alignment,
            prompt_grounding=prompt_grounding,
        )
        tags = ["aurora", "corpus", str(phase or "corpus"), f"kind:{kind}"]
        return self.record_intervention_event(
            target="aurora.corpus.response_generation",
            issue=issue,
            logic_tier="expression_ecology",
            intervention=intervention,
            intended_effect=intended_effect,
            observed_effect=observed_effect,
            tags=tags,
            auto_advance=None,
            rotate_doctrine=False,
        )

    def advise_training_plan(
        self,
        plan: Dict[str, Any],
        phase: str = "train",
    ) -> Dict[str, Any]:
        patched = dict(plan or {})
        patched.setdefault("pressure_targets", {})
        patched.setdefault("behavior_modes", {})
        patched.setdefault("constraint_axes", {})
        patched.setdefault("avatar_overrides", {})
        patched.setdefault("study_topics", [])
        patched.setdefault("rationale", [])
        patched.setdefault("guide_sources", [])

        issue, _, _ = self._derive_training_event(patched)
        doctrine = self._select_doctrine(issue_category=issue, logic_tier="evolutionary_pipeline")
        decision = QuasiArchGateDecision(
            mode=self.mode,
            phase=str(phase or "train"),
            issue_category=issue,
        )
        if doctrine is None:
            decision.rationale.append("no_matching_doctrine")
            self.gate_history.append(decision.to_dict())
            patched["quasiarch_gate"] = decision.to_dict()
            return patched

        exact_cost = self._record_consultation(
            issue_category=issue,
            doctrine=doctrine,
            phase=str(phase or "train"),
            rotation_count=0,
            consumer="training",
            resolution_mode="exact",
        )
        decision.doctrine_id = doctrine.quasi_id
        decision.doctrine_strategy = doctrine.primary_strategy
        decision.doctrine_confidence = float(doctrine.confidence)
        decision.doctrine_version = int(doctrine.lineage_version)
        decision.rationale.append(
            f"matched:{doctrine.primary_strategy}@v{doctrine.lineage_version}"
        )
        patched["quasiarch_consult"] = dict(exact_cost)
        patched["avatar_overrides"]["quasiarch_exact_cost"] = float(exact_cost.get("cost", 0.0) or 0.0)
        patched["avatar_overrides"]["quasiarch_dependency_debt"] = float(exact_cost.get("issue_debt", 0.0) or 0.0)
        patched["rationale"].append(
            f"quasiarch_exact_cost:{float(exact_cost.get('cost', 0.0) or 0.0):.3f}"
        )

        reasoning = self.reason_about_event(
            issue_category=issue,
            logic_tier="evolutionary_pipeline",
            distribution_context="multi_module__same_tier",
            limit=1,
            rotate=True,
            charge_cost=True,
            phase=str(phase or "train"),
            consumer="training",
        )
        hypothesis_credit = dict(reasoning.get("hypothesis_credit", {}) or {})
        top_analysis = (reasoning.get("analyses", []) or [])[:1]
        rotation_summaries: List[Dict[str, Any]] = []
        total_hypotheses = 0
        for analysis in top_analysis:
            for rotation in list(analysis.get("hypotheses", []) or []):
                hypothesis_count = len(rotation.get("hypotheses", []) or [])
                total_hypotheses += hypothesis_count
                rotation_summaries.append(
                    {
                        "rotation": rotation.get("rotation"),
                        "hypothesis_count": hypothesis_count,
                    }
                )
        patched["quasiarch_reasoning"] = {
            "candidate_count": int(reasoning.get("candidate_count", 0) or 0),
            "hypothesis_credit": hypothesis_credit,
            "rotations": rotation_summaries,
        }
        patched["avatar_overrides"]["quasiarch_hypothesis_credit"] = float(
            hypothesis_credit.get("global_hypothesis_credit", 0.0) or 0.0
        )
        patched["avatar_overrides"]["quasiarch_possibility_pressure"] = float(
            hypothesis_credit.get("global_possibility_pressure", 0.0) or 0.0
        )
        patched["avatar_overrides"]["quasiarch_net_dependency"] = round(
            float(exact_cost.get("issue_debt", 0.0) or 0.0)
            - float(hypothesis_credit.get("reward", 0.0) or 0.0),
            4,
        )
        if total_hypotheses > 0:
            for topic in ("hypothesis discrimination", "ambiguity holding"):
                if topic not in patched["study_topics"]:
                    patched["study_topics"].append(topic)
            patched["rationale"].append(
                f"quasiarch_hypothesis_credit:{float(hypothesis_credit.get('reward', 0.0) or 0.0):.3f}"
            )
            patched["rationale"].append(
                f"quasiarch_possibility_pressure:{float(hypothesis_credit.get('possibility_pressure', 0.0) or 0.0):.3f}"
            )

        patched["episodes_bonus"] = int(patched.get("episodes_bonus", 0) or 0) + int(
            float(exact_cost.get("cost", 0.0) or 0.0) >= 0.18
        ) + int(
            float(hypothesis_credit.get("possibility_pressure", 0.0) or 0.0) >= 0.10
        )
        patched["turns_bonus"] = int(patched.get("turns_bonus", 0) or 0) + int(
            float(exact_cost.get("issue_debt", 0.0) or 0.0) >= 0.75
        ) + int(total_hypotheses >= 3)

        patch = TRAINING_STRATEGY_PATCHES.get(doctrine.primary_strategy, {})
        can_apply = (
            self.mode == "gated"
            and doctrine.is_active_version
            and float(doctrine.confidence) >= float(self.gate_confidence)
            and bool(patch)
        )
        if self.mode in {"advisory", "gated"}:
            patched["quasiarch_advice"] = {
                "issue_category": issue,
                "strategy": doctrine.primary_strategy,
                "confidence": float(doctrine.confidence),
                "version": int(doctrine.lineage_version),
                "applicability_boundary": doctrine.applicability_boundary,
                "failure_indicators": list(doctrine.failure_indicators),
            }
        if can_apply:
            self._merge_training_patch(patched, patch)
            patched["guide_sources"] = list(dict.fromkeys(
                list(patched.get("guide_sources", []) or []) + ["quasiarch"]
            ))
            patched["rationale"].append(
                f"quasiarch_gated:{doctrine.primary_strategy} "
                f"conf={float(doctrine.confidence):.2f} v={int(doctrine.lineage_version)}"
            )
            decision.applied = True
        elif self.mode == "advisory":
            patched["rationale"].append(
                f"quasiarch_advisory:{doctrine.primary_strategy} "
                f"conf={float(doctrine.confidence):.2f}"
            )
        else:
            decision.rationale.append("shadow_mode_no_apply")

        self.gate_history.append(decision.to_dict())
        patched["quasiarch_gate"] = decision.to_dict()
        return patched

    def _select_doctrine(self, issue_category: str, logic_tier: str) -> Optional[DoctrineObject]:
        try:
            candidates = self.pipeline.get_doctrine_candidates_for_event(
                {
                    "issue": issue_category,
                    "logic_tier": logic_tier,
                    "distribution_context": "multi_module__same_tier",
                },
                min_confidence=self.advisory_confidence,
            )
        except Exception:
            candidates = []
        if candidates:
            return candidates[0]
        return None

    def _merge_training_patch(self, plan: Dict[str, Any], patch: Dict[str, Any]) -> None:
        for key in ("pressure_targets", "behavior_modes", "constraint_axes"):
            current = dict(plan.get(key, {}) or {})
            incoming = dict(patch.get(key, {}) or {})
            for sub_key, sub_val in incoming.items():
                current[sub_key] = max(float(current.get(sub_key, 0.0) or 0.0), float(sub_val))
            plan[key] = current
        study_topics = list(plan.get("study_topics", []) or [])
        for topic in list(patch.get("study_topics", []) or []):
            if topic not in study_topics:
                study_topics.append(topic)
        plan["study_topics"] = study_topics[:4]
        for scalar_key in ("episodes_bonus", "turns_bonus", "queue_repeats"):
            plan[scalar_key] = max(
                int(plan.get(scalar_key, 0) or 0),
                int(patch.get(scalar_key, 0) or 0),
            )

    def _should_auto_advance(self, issue_category: str, observed_effect: str, count: int) -> bool:
        if count < 4:
            return False
        if observed_effect in {"no_change_observed", "regression_introduced"}:
            return True
        return count % 4 == 0

    def _derive_training_event(self, plan: Dict[str, Any]) -> Tuple[str, str, str]:
        targets = dict(plan.get("pressure_targets", {}) or {})
        if not targets:
            return (
                "response_pressure_instability",
                "response_pressure_rebalancing",
                "stabilize response behavior under mixed counter-pressure",
            )
        dominant_dim = max(targets, key=lambda key: float(targets.get(key, 0.0) or 0.0))
        if dominant_dim in {"context_carryover", "multi_turn_stability", "coherence_maintenance"}:
            return (
                "context_carryover_instability",
                "context_thread_reinforcement",
                "carry context, referents, and claims across turns",
            )
        if dominant_dim in {"ambiguity_handling", "semantic_precision", "boundary_calibration"}:
            return (
                "grounding_lookup_instability",
                "clarify_grounding_loop",
                "tighten grounding before committing to an answer",
            )
        if dominant_dim in {"uncertainty_signaling"}:
            return (
                "uncertainty_signaling_gap",
                "uncertainty_signal_repair",
                "mark uncertainty directly without losing relevance",
            )
        if dominant_dim in {"misunderstanding_repair", "contradiction_handling"}:
            return (
                "repair_resolution_instability",
                "repair_path_stabilization",
                "repair contradictions and misunderstandings before drift compounds",
            )
        if dominant_dim in {"framing_selection", "adaptive_strategy_selection", "compression_elaboration_fit"}:
            return (
                "response_grounding_drift",
                "response_pressure_rebalancing",
                "select a framing strategy that preserves meaning and control",
            )
        return (
            "response_pressure_instability",
            "response_pressure_rebalancing",
            "stabilize response behavior under mixed counter-pressure",
        )

    def _derive_corpus_event(
        self,
        prompt_text: str,
        kind: str,
        truth_alignment: float,
        prompt_grounding: float,
    ) -> Tuple[str, str, str]:
        prompt_low = str(prompt_text or "").lower()
        if "look up" in prompt_low or "what do you mean" in prompt_low or "meaning" in prompt_low:
            return (
                "grounding_lookup_instability",
                "lookup_bridge_activation",
                "bridge unresolved questions into lookup or meaning anchoring",
            )
        if kind == "followup":
            return (
                "context_carryover_instability",
                "context_thread_reinforcement",
                "preserve referent and claim continuity on callbacks",
            )
        if kind == "repair":
            return (
                "repair_resolution_instability",
                "repair_path_stabilization",
                "repair contradictions and misunderstanding without drift",
            )
        if kind == "uncertainty":
            return (
                "uncertainty_signaling_gap",
                "uncertainty_signal_repair",
                "signal uncertainty clearly while keeping the answer useful",
            )
        if truth_alignment < 0.28 or prompt_grounding < 0.24:
            return (
                "response_grounding_drift",
                "evidence_alignment_repair",
                "align reply structure to evidence and prompt grounding",
            )
        return (
            "response_pressure_instability",
            "response_pressure_rebalancing",
            "stabilize response quality under corpus pressure",
        )

    def _observed_effect_from_training(
        self,
        fitness: float,
        shards: int,
        plan: Dict[str, Any],
    ) -> str:
        min_fit = float(
            dict(plan.get("avatar_overrides", {}) or {}).get("min_acceptable_fitness", 0.46) or 0.46
        )
        if fitness >= max(0.68, min_fit + 0.12):
            return "resolved_fully"
        if fitness >= max(0.46, min_fit - 0.02) or shards > 0:
            return "resolved_partially"
        if fitness < 0.28 and shards == 0:
            return "regression_introduced"
        return "no_change_observed"

    def _observed_effect_from_corpus(
        self,
        signal: float,
        threshold: float,
        counter_pressure: float,
        truth_alignment: float,
        prompt_grounding: float,
    ) -> str:
        signal = float(signal)
        threshold = float(threshold)
        if truth_alignment >= 0.56 and prompt_grounding >= 0.30 and signal >= threshold - 0.02:
            return "resolved_fully"
        if truth_alignment >= 0.28 or signal >= threshold - 0.06:
            return "resolved_partially"
        if truth_alignment < 0.12 and prompt_grounding < 0.12 and counter_pressure >= 0.20:
            return "regression_introduced"
        return "no_change_observed"
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
