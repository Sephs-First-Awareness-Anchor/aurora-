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

# Fallback candidate pool when fail_points.json is missing/empty (fresh
# environment) -- the full dimension set _DIMENSION_PERSONALITY_HINTS already
# knows how to specialize an avatar for (aurora_simulation_engine.py).
_DEFAULT_CANDIDATE_DIMENSIONS: Tuple[str, ...] = (
    "coherence_maintenance", "context_carryover", "ambiguity_handling",
    "contradiction_handling", "implied_intent_inference", "misunderstanding_repair",
    "uncertainty_signaling", "boundary_calibration", "framing_selection",
    "emotional_calibration", "semantic_precision", "adaptive_strategy_selection",
    "compression_elaboration_fit", "perspective_integration", "multi_turn_stability",
)

# How many of a dimension's most recent classroom lessons to look at before
# calling it "not improving." Below this, there isn't enough history to judge
# staleness one way or the other, so it's treated as fresh/not stale.
STALE_LESSON_LOOKBACK = 3
# A lesson's dev_delta at or below this counts as "didn't move the needle."
STALE_DELTA_THRESHOLD = 0.05


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
    content_source: str = "generic"
    seed_prompt: str = ""
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
            "content_source": self.content_source,
            "seed_prompt": self.seed_prompt,
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


def _load_fail_points(state_dir: Path) -> Dict[str, Any]:
    """Real per-dimension fail data from the health-check pipeline
    (aurora_diag.py writes this). Returns {} on any miss -- a fresh
    environment with no fail history yet is not an error."""
    try:
        with open(state_dir / "fail_points.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _dimension_trend(recent: List[float]) -> str:
    """Same IMPROVING/WORSENING/stable classification aurora_diag.py's health
    check already uses (identical thresholds) -- reused by rebuilding it here
    rather than importing a diagnostic script into production glue code, but
    kept numerically identical on purpose so 'stale' means the same thing in
    both places."""
    if not recent or len(recent) < 5:
        return "n/a"
    earlier = sum(recent[:5]) / 5
    latest = sum(recent[-5:]) / 5
    if latest < earlier * 0.9:
        return "IMPROVING"
    if latest > earlier * 1.1:
        return "WORSENING"
    return "stable"


def _read_classroom_log(state_dir: Path) -> List[Dict[str, Any]]:
    path = state_dir / "classroom_log.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _is_stale(
    lessons_for_dim: List[Dict[str, Any]],
    lookback: int = STALE_LESSON_LOOKBACK,
    threshold: float = STALE_DELTA_THRESHOLD,
) -> bool:
    """A dimension is stale when its last `lookback` classroom lessons all
    failed to move dev_index by more than `threshold`. Fewer lessons than
    `lookback` means there isn't enough history to call it stale yet --
    a dimension is innocent (fresh) until it's actually shown to be stuck."""
    if len(lessons_for_dim) < lookback:
        return False
    recent = lessons_for_dim[-lookback:]
    deltas = [l.get("dev_delta_from_lesson") for l in recent]
    if any(d is None for d in deltas):
        return False
    return all(float(d) <= threshold for d in deltas)


def _real_example_seed(
    fail_records: Dict[str, Any],
    dimension: str,
    already_used: set,
) -> Tuple[str, str]:
    """
    Pull one real failing conversation excerpt for `dimension` out of
    fail_points.json's own `examples` (populated by the health-check
    pipeline from actual corpus/live-turn failures) and turn it into a
    seed_prompt. Rotates past any conversation_id already used earlier in
    this same curriculum run so repeated stale dimensions don't just get fed
    the identical example every time.

    Returns (seed_prompt, content_source). content_source is
    "generic" (nothing usable found -- caller falls back to no seed) or
    "real_failure_example:<conversation_id>" when a real excerpt was used.
    """
    examples = (fail_records.get(dimension, {}) or {}).get("examples", []) or []
    for example in examples:
        conv_id = str(example.get("conversation_id", "") or "")
        if conv_id and conv_id in already_used:
            continue
        user_turns = [str(t) for t in (example.get("user_turns") or []) if str(t).strip()]
        if not user_turns:
            continue
        # The last user turn is usually the most specific/pointed one in
        # these multi-turn excerpts (see fail_points.json's own examples).
        seed = user_turns[-1].strip()
        if conv_id:
            already_used.add(conv_id)
        return seed, f"real_failure_example:{conv_id or 'unknown'}"
    return "", "generic"


def select_curriculum(
    systems: Dict[str, Any],
    n: int = 4,
    state_dir: Optional[str] = None,
    stale_lookback: int = STALE_LESSON_LOOKBACK,
    stale_delta_threshold: float = STALE_DELTA_THRESHOLD,
) -> List[Tuple[str, str, str]]:
    """
    Build a curriculum plan of `n` (target_dimension, seed_prompt,
    content_source) triples, ranked by real fail_points.json severity
    (fail_count, highest first -- same ranking aurora_diag.py's health check
    already uses).

    When a dimension's recent classroom lessons show it isn't improving
    (see _is_stale) or fail_points.json's own recent-score trend reads
    WORSENING, a real failing conversation excerpt for that dimension is
    fed as seed_prompt instead of leaving the lesson generic -- grounding
    the next attempt in concrete content instead of repeating whatever
    generic lesson already isn't moving the needle. Falls back to the full
    known dimension pool if fail_points.json has no data yet (fresh
    environment) -- there's no fail history to rank, but the lessons still
    need to happen.
    """
    sd = Path(state_dir) if state_dir else Path(str(systems.get("state_dir") or "aurora_state"))
    fp = _load_fail_points(sd)
    records: Dict[str, Any] = fp.get("records", {}) or {}

    if records:
        ranked = [dim for dim, _ in sorted(records.items(), key=lambda kv: -kv[1].get("fail_count", 0))]
    else:
        ranked = list(_DEFAULT_CANDIDATE_DIMENSIONS)

    log_entries = _read_classroom_log(sd)
    by_dim: Dict[str, List[Dict[str, Any]]] = {}
    for entry in log_entries:
        by_dim.setdefault(entry.get("target_dimension", ""), []).append(entry)

    used_example_ids: set = set()
    plan: List[Tuple[str, str, str]] = []
    for dim in ranked:
        if len(plan) >= n:
            break
        stale = _is_stale(by_dim.get(dim, []), lookback=stale_lookback, threshold=stale_delta_threshold)
        trend = _dimension_trend((records.get(dim, {}) or {}).get("recent", []))
        seed_prompt, content_source = "", "generic"
        if stale or trend == "WORSENING":
            seed_prompt, content_source = _real_example_seed(records, dim, used_example_ids)
        plan.append((dim, seed_prompt, content_source))

    return plan[:n]


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
        content_source: str = "generic",
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
            content_source=content_source,
            seed_prompt=seed_prompt,
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

    def run_targeted_curriculum(
        self,
        n: int = 4,
        turns_per_lesson: int = 6,
    ) -> List[ClassResult]:
        """
        Auto-select `n` lessons via select_curriculum() (ranked by real
        fail_points.json severity, real failing content fed in for any
        dimension that's gone stale or is trending WORSENING) and run them
        in order. This is the entry point the scheduled workflow runs --
        run_curriculum() above stays available for an explicit dimension
        list.
        """
        plan = select_curriculum(self.systems, n=n, state_dir=str(self.state_dir))
        return [
            self.run_lesson(dimension, turns=turns_per_lesson, seed_prompt=seed_prompt, content_source=content_source)
            for dimension, seed_prompt, content_source in plan
        ]

    def _persist(self, result: ClassResult) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.state_dir / "classroom_log.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True) + "\n")
