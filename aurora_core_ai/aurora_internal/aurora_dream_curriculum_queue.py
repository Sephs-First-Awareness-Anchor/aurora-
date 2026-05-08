#!/usr/bin/env python3
"""
AURORA DREAM CURRICULUM QUEUE
=================================
Manages the queue of dream episode packs and selects the next pack
for dream execution based on developmental need.

Integrates with:
  - AutonomyEngine._build_dream_seed  (seed source)
  - AutonomyEngine._check_dreams      (dream trigger)
  - SimulationEngine.run_episode       (execution)

Selection logic:
  1. Weakness-targeted packs get priority when repeated failures exist
  2. Packs are consumed in difficulty-ascending order
  3. Successfully completed packs can be re-queued with higher difficulty
  4. Balanced packs fill gaps between targeted rounds

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_constraint_unit_adapter import build_constraint_profile
from aurora_internal.aurora_conversation_episode_compiler import (
    ConversationEpisodeCompiler,
    DreamEpisodePack,
)


# ============================================================================
# COMPLETION RECORD
# ============================================================================

@dataclass
class PackCompletionRecord:
    """Record of a completed dream episode pack run."""
    episode_id: str
    completed_at: float
    mean_fitness: float
    weakness_dimensions: List[str] = field(default_factory=list)
    improvement_detected: bool = False
    requeue_recommended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "completed_at": self.completed_at,
            "mean_fitness": self.mean_fitness,
            "weakness_dimensions": self.weakness_dimensions,
            "improvement_detected": self.improvement_detected,
            "requeue_recommended": self.requeue_recommended,
        }


# ============================================================================
# CURRICULUM QUEUE
# ============================================================================

class DreamCurriculumQueue:
    """
    Selects the next dream episode pack based on developmental priority.

    Queue ordering:
      1. Weakness-targeted packs (sorted by difficulty ascending)
      2. Stress test packs (high difficulty, for resilience)
      3. Balanced packs (fill gaps)

    Completed packs are tracked. Packs with poor outcomes can be re-queued.
    """

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "dream_episodes")):
        self.storage_dir = storage_dir
        self.compiler = ConversationEpisodeCompiler(storage_dir=storage_dir)
        self._queue: List[str] = []  # episode_ids in priority order
        self._completed: Dict[str, PackCompletionRecord] = {}
        self._current_pack_id: Optional[str] = None
        self._history_path = os.path.join(storage_dir, "queue_history.json")
        self._load_history()

    def _load_history(self):
        """Load completion history from disk."""
        if os.path.exists(self._history_path):
            try:
                with open(self._history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for rec in data.get("completed", []):
                    self._completed[rec["episode_id"]] = PackCompletionRecord(
                        episode_id=rec["episode_id"],
                        completed_at=rec["completed_at"],
                        mean_fitness=rec["mean_fitness"],
                        weakness_dimensions=rec.get("weakness_dimensions", []),
                        improvement_detected=rec.get("improvement_detected", False),
                        requeue_recommended=rec.get("requeue_recommended", False),
                    )
            except Exception:
                pass

    def _save_history(self):
        """Persist completion history."""
        os.makedirs(self.storage_dir, exist_ok=True)
        data = {
            "completed": [r.to_dict() for r in self._completed.values()],
            "queue": self._queue,
            "current_pack_id": self._current_pack_id,
        }
        with open(self._history_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def build_queue(self, force_rebuild: bool = False):
        """
        Build the dream curriculum queue from available packs.
        Sorts by: weakness_targeted first, then by difficulty ascending.
        """
        available = self.compiler.list_available_packs()
        if not available and not force_rebuild:
            return

        # Filter out already-completed packs (unless requeue recommended)
        eligible = []
        for info in available:
            eid = info["episode_id"]
            if eid in self._completed:
                rec = self._completed[eid]
                if rec.requeue_recommended:
                    eligible.append(info)
            else:
                eligible.append(info)

        # Sort: weakness_targeted first, then stress_test, then balanced
        # Within each group: sort by difficulty ascending
        mode_priority = {"weakness_targeted": 0, "stress_test": 1, "balanced": 2}

        def _priority(info: Dict[str, Any]) -> tuple:
            pack = self.compiler.load_pack(str(info.get("episode_id", "") or ""))
            if pack is None:
                return (
                    mode_priority.get(info.get("design_mode", "balanced"), 9),
                    1.0,
                    1.0,
                    info.get("difficulty_estimate", 0.5),
                )
            weakest = min((float(v) for v in (pack.rubric_profile or {}).values()), default=0.5)
            regime = dict(pack.runtime_regime or {})
            regime_signature = str(regime.get("tier3_regime_signature", "XTNBA") or "XTNBA")
            dominant_axis = str((regime.get("weighted_form") or {}).get("dominant_axis", "X") or "X")
            dominant_weight = float(self._pack_axis_weights(pack).get(dominant_axis, 0.0) or 0.0)
            return (
                mode_priority.get(pack.design_mode or "balanced", 9),
                0 if regime_signature != "XTNBA" else 1,
                weakest,
                -dominant_weight,
                pack.difficulty_estimate,
            )

        eligible.sort(key=_priority)

        self._queue = [info["episode_id"] for info in eligible]
        self._save_history()

    def next_pack(self) -> Optional[DreamEpisodePack]:
        """
        Select and return the next dream episode pack.

        Returns None if queue is empty or no packs available.
        """
        if not self._queue:
            self.build_queue()

        if not self._queue:
            return None

        episode_id = self._queue.pop(0)
        pack = self.compiler.load_pack(episode_id)
        if pack:
            self._current_pack_id = episode_id
            self._save_history()
        return pack

    def record_completion(
        self,
        episode_id: str,
        mean_fitness: float,
        weakness_dimensions: Optional[List[str]] = None,
        improvement_detected: bool = False,
    ):
        """Record the outcome of a completed dream episode pack."""
        # Determine if requeue is recommended
        requeue = mean_fitness < 0.4 and not improvement_detected

        record = PackCompletionRecord(
            episode_id=episode_id,
            completed_at=time.time(),
            mean_fitness=mean_fitness,
            weakness_dimensions=weakness_dimensions or [],
            improvement_detected=improvement_detected,
            requeue_recommended=requeue,
        )
        self._completed[episode_id] = record
        self._current_pack_id = None
        self._save_history()

    def compile_from_corpus(
        self,
        json_path: str,
        max_conversations: int = 500,
    ) -> int:
        """
        Compile conversation JSON into episode packs and build queue.
        Returns number of packs compiled.
        """
        packs = self.compiler.compile_from_json(json_path, max_conversations)
        if packs:
            self.build_queue(force_rebuild=True)
        return len(packs)

    def get_seed_from_pack(self, pack: DreamEpisodePack) -> str:
        """
        Build a dream seed string from a pack's rubric profile.
        This replaces the generic seed with pack-aware context.
        """
        parts = [f"mode:{pack.design_mode}"]
        parts.append(f"signature:{pack.constraint_signature}")
        parts.append(
            f"regime:{str((pack.runtime_regime or {}).get('tier3_regime_signature', 'XTNBA') or 'XTNBA')}"
        )
        parts.append(
            f"language:{str((pack.language_projection or {}).get('dominant_channel', 'selection') or 'selection')}"
        )

        # Add weakness targets
        weakest = sorted(pack.rubric_profile.items(), key=lambda kv: kv[1])[:3]
        for dim, score in weakest:
            parts.append(f"weakness:{dim}({score:.2f})")

        parts.append(f"difficulty:{pack.difficulty_estimate:.2f}")

        return " | ".join(parts)

    def extract_episode_messages(
        self,
        pack: DreamEpisodePack,
        conversation_index: int = 0,
    ) -> List[Dict[str, str]]:
        """
        Extract messages from a specific conversation within a pack.
        Returns list of {"role": ..., "text": ...} dicts.
        """
        if not pack.payloads or conversation_index >= len(pack.payloads):
            return []

        payload = pack.payloads[conversation_index]
        return payload.get("messages", [])

    @property
    def queue_length(self) -> int:
        return len(self._queue)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def current_pack_id(self) -> Optional[str]:
        return self._current_pack_id

    def _pack_axis_weights(self, pack: DreamEpisodePack) -> Dict[str, float]:
        rubric = dict(pack.rubric_profile or {})
        mapping = {
            "X": (
                "perspective_integration",
                "uncertainty_signaling",
                "contradiction_handling",
                "coherence_maintenance",
            ),
            "T": (
                "context_carryover",
                "multi_turn_stability",
            ),
            "N": (
                "semantic_precision",
                "compression_elaboration_fit",
                "implied_intent_inference",
            ),
            "B": (
                "emotional_calibration",
                "boundary_calibration",
                "ambiguity_handling",
            ),
            "A": (
                "framing_selection",
                "adaptive_strategy_selection",
            ),
        }
        weights: Dict[str, float] = {}
        for axis, dims in mapping.items():
            values = [float(rubric.get(dim, 0.0) or 0.0) for dim in dims]
            weights[axis] = round(sum(values) / max(len(values), 1), 4)
        return weights

    def constraint_profile(self):
        queue_pressure = {
            "X": min(1.0, self.completed_count / 25.0),
            "T": min(1.0, self.queue_length / 25.0),
            "N": 1.0 if self.current_pack_id else 0.2,
            "B": min(1.0, sum(1 for rec in self._completed.values() if rec.requeue_recommended) / 10.0),
            "A": min(1.0, sum(1 for rec in self._completed.values() if rec.improvement_detected) / 10.0),
        }
        queue_weights = {
            "X": 0.18,
            "T": 0.28,
            "N": 0.16,
            "B": 0.18,
            "A": 0.20,
        }
        return build_constraint_profile(
            unit_id="dream_curriculum_queue",
            unit_kind="curriculum_queue",
            operational_role="dream_curriculum_orchestration",
            genealogy="XTNBAA",
            axis_weights=queue_weights,
            pressure_axes=queue_pressure,
        )

    def runtime_regime(self) -> Dict[str, Any]:
        return self.constraint_profile().runtime_regime()

    def language_projection(self) -> Dict[str, Any]:
        return self.constraint_profile().language_projection()

    def universal_representation(self) -> Dict[str, Any]:
        profile = self.constraint_profile()
        rep = profile.universal_representation()
        rep["unit_state"] = {
            "queue_length": self.queue_length,
            "completed_count": self.completed_count,
            "current_pack_id": self.current_pack_id,
            "queued_episode_ids": list(self._queue[:12]),
        }
        return rep
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
