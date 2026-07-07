# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Aurora Classroom — targeted curriculum runner: Aurora + two InceptionEntity
dream entities, one weak-dimension lesson at a time, with before/after
dev_index measured against the real developmental log.

This is NOT a new learning system. It wires three things that already exist
but have never been run together for this purpose:

    1. SimulationSession's pressure-targeted avatar spec mechanism
       (aurora_simulation_engine.py) — queue_avatar_specs() + run_episode()
       already knows how to build a specialized episode aimed at a named
       weak rubric dimension (_DIMENSION_PERSONALITY_HINTS already maps
       "context_carryover" -> CURIOUS and "coherence_maintenance" -> CRITICAL,
       exactly the two dimensions flagged in the health check).

    2. InceptionEntity (aurora_simulation_engine.py) — spawned via
       SimulationEngine.spawn_entity(), run via
       SimulationEngine.run_entity_experience(), resolved via
       entity.collapse_to_parent(). Two entities given different i_states
       process the SAME lesson content Aurora's episode just generated,
       from different perspectives.

    3. DivergenceTracker (aurora_simulation_engine.py, already instantiated
       as SimulationSession.divergence) — captures whether the two entities'
       resolved perspectives are pulling apart or converging. Reused as-is,
       not reimplemented.

    4. record_developmental_snapshot (aurora_developmental_log.py) — called
       force=True immediately before and after the lesson so the dev_index
       delta measured is attributable to THIS lesson, not just whatever
       throttled snapshot happened to land nearby.

The one piece of genuinely new glue code is _episode_to_entity_experience():
there is no existing adapter from an EpisodeResult to the `experience` dict
InceptionEntity.process_experience() expects, so this module builds one from
the episode's real fitness/engagement/topic data. That function's mapping is
a first-pass heuristic, not a sourced pre-existing rule — treat it as the one
part of this file to look over most critically.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from foundational_contract import ExistenceMode
from aurora_simulation_engine import (
    SimulationEngine,
    EntityDepth,
    EpisodeResult,
)
from aurora_developmental_log import record_developmental_snapshot


@dataclass
class ClassResult:
    """Everything one targeted lesson produced, in one record."""

    lesson_id: str
    target_dimension: str
    turns: int
    episode_avg_fitness: float
    episode_final_engagement: float
    episode_understanding_gained: List[str]
    entity_ids: Tuple[str, str]
    entity_resolutions: Tuple[Dict[str, Any], Dict[str, Any]]
    divergence_score: float
    is_diverging: bool
    dev_index_before: Optional[float]
    dev_index_after: Optional[float]
    dev_delta_from_lesson: Optional[float]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "target_dimension": self.target_dimension,
            "turns": self.turns,
            "episode_avg_fitness": round(self.episode_avg_fitness, 4),
            "episode_final_engagement": round(self.episode_final_engagement, 4),
            "episode_understanding_gained": list(self.episode_understanding_gained),
            "entity_ids": list(self.entity_ids),
            "entity_resolutions": list(self.entity_resolutions),
            "divergence_score": round(self.divergence_score, 4),
            "is_diverging": bool(self.is_diverging),
            "dev_index_before": self.dev_index_before,
            "dev_index_after": self.dev_index_after,
            "dev_delta_from_lesson": self.dev_delta_from_lesson,
            "timestamp": self.timestamp,
        }


def _episode_to_entity_experience(episode: EpisodeResult, target_dimension: str) -> Dict[str, Any]:
    """
    NEW glue code — not a sourced pre-existing adapter. Builds the
    `experience` dict InceptionEntity.process_experience() expects
    (a `channels` dict of {tone: weight}) from the real EpisodeResult
    the targeted episode just produced.

    Heuristic: high fitness + high engagement reads as a "resonant" channel
    weighted toward affirmation; low fitness/engagement reads as "strained".
    This is a first pass — worth reviewing against what actually correlates
    with dev_index movement once real lessons have run.
    """
    fitness = float(episode.avg_fitness or 0.0)
    engagement = float(episode.final_engagement or 0.0)
    resonant = max(0.0, min(1.0, (fitness + engagement) / 2.0))
    strained = max(0.0, 1.0 - resonant)
    return {
        "channels": {
            "resonant": round(resonant, 4),
            "strained": round(strained, 4),
        },
        "tone": "warm" if resonant >= 0.55 else "neutral",
        "target_dimension": target_dimension,
        "topic_category": episode.topic_category,
        "understanding_gained": list(episode.understanding_gained or []),
    }


class ClassroomSession:
    """
    Aurora + two InceptionEntity dream entities, run through one targeted
    lesson at a time. Wraps an EXISTING SimulationEngine instance — does not
    construct one, since SimulationEngine.__init__ does real boot work
    (pressure map load, FoundationalContract, etc.) that belongs to whatever
    already builds Aurora's `systems` dict.
    """

    def __init__(
        self,
        engine: SimulationEngine,
        systems: Dict[str, Any],
        entity_i_states: Tuple[str, str] = ("i_can", "i_saw"),
        state_dir: Optional[str] = None,
    ) -> None:
        self.engine = engine
        self.systems = systems
        self.state_dir = Path(state_dir) if state_dir else (
            Path(systems.get("state_dir") or "aurora_state")
        )
        self._lesson_count = 0

        # Spawn the two dream-entity classmates once, at SURFACE depth
        # (BOUNDED mode is sufficient — see spawn_entity's depth gating,
        # DEEP+ would require AGENTIC mode and isn't needed for this).
        entity_a = engine.spawn_entity(
            i_state=entity_i_states[0], depth=EntityDepth.SURFACE, mode=ExistenceMode.BOUNDED
        )
        entity_b = engine.spawn_entity(
            i_state=entity_i_states[1], depth=EntityDepth.SURFACE, mode=ExistenceMode.BOUNDED
        )
        if entity_a is None or entity_b is None:
            raise RuntimeError(
                "ClassroomSession requires BOUNDED+ mode to spawn entities — "
                "spawn_entity() returned None. Check ExistenceMode passed in."
            )
        self.entity_ids: Tuple[str, str] = (entity_a.entity_id, entity_b.entity_id)

    def run_lesson(
        self,
        target_dimension: str,
        turns: int = 6,
        seed_prompt: str = "",
    ) -> ClassResult:
        """
        One targeted lesson:
          1. Snapshot dev_index (force=True, so it's not throttled away).
          2. Queue a pressure-specialized avatar spec aimed at
             target_dimension and run the real episode through it.
          3. Feed both entities the episode's actual content.
          4. Capture divergence between the two entities' resolved
             perspectives via the existing DivergenceTracker.
          5. Snapshot dev_index again (force=True) and compute the delta
             attributable to this lesson.
        """
        self._lesson_count += 1
        lesson_id = f"class_{target_dimension}_{self._lesson_count}_{int(time.time())}"

        dev_before_snap = record_developmental_snapshot(self.systems, force=True)
        dev_before = dev_before_snap.get("dev_index") if dev_before_snap else None

        queued = self.engine.session.queue_avatar_specs([
            {
                "avatar_id": lesson_id,
                "pressure_targets": {target_dimension: 1.0},
            }
        ])
        if queued < 1:
            raise RuntimeError(
                f"queue_avatar_specs() failed to queue a spec for '{target_dimension}' — "
                "check that the dimension name is a valid pressure_target key."
            )

        episode: EpisodeResult = self.engine.run_episode(turns=turns, seed_prompt=seed_prompt)

        experience = _episode_to_entity_experience(episode, target_dimension)
        entity_resolutions: List[Dict[str, Any]] = []
        for entity_id in self.entity_ids:
            self.engine.run_entity_experience(entity_id, experience, mode=ExistenceMode.BOUNDED)
            resolution = self.engine.entities[entity_id].collapse_to_parent()
            entity_resolutions.append(resolution)

        # Reuse the existing DivergenceTracker exactly as SimulationSession
        # already uses it — feed it the two entities' resolved numeric state.
        divergence_stats: Dict[str, float] = {}
        for idx, resolution in enumerate(entity_resolutions):
            divergence_stats[f"entity_{idx}_valence"] = float(resolution.get("avg_valence", 0.0) or 0.0)
            divergence_stats[f"entity_{idx}_intensity"] = float(resolution.get("avg_intensity", 0.0) or 0.0)
        self.engine.session.divergence.capture(divergence_stats)
        divergence_score = self.engine.session.divergence.current_divergence
        is_diverging = self.engine.session.divergence.is_diverging()

        dev_after_snap = record_developmental_snapshot(self.systems, force=True)
        dev_after = dev_after_snap.get("dev_index") if dev_after_snap else None
        dev_delta = (
            round(dev_after - dev_before, 4)
            if dev_after is not None and dev_before is not None
            else None
        )

        result = ClassResult(
            lesson_id=lesson_id,
            target_dimension=target_dimension,
            turns=turns,
            episode_avg_fitness=float(episode.avg_fitness or 0.0),
            episode_final_engagement=float(episode.final_engagement or 0.0),
            episode_understanding_gained=list(episode.understanding_gained or []),
            entity_ids=self.entity_ids,
            entity_resolutions=(entity_resolutions[0], entity_resolutions[1]),
            divergence_score=divergence_score,
            is_diverging=is_diverging,
            dev_index_before=dev_before,
            dev_index_after=dev_after,
            dev_delta_from_lesson=dev_delta,
        )
        self._persist(result)
        return result

    def run_curriculum(
        self,
        target_dimensions: List[str],
        turns_per_lesson: int = 6,
    ) -> List[ClassResult]:
        """Run one lesson per requested dimension, in order. E.g.
        run_curriculum(["context_carryover", "coherence_maintenance"])."""
        return [
            self.run_lesson(dimension, turns=turns_per_lesson)
            for dimension in target_dimensions
        ]

    def _persist(self, result: ClassResult) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.state_dir / "classroom_log.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True) + "\n")
