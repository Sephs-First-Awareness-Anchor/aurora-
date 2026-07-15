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
import os
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
from aurora_internal.aurora_directed_training_corpus import (
    get_directed_training_corpus_bridge,
)
from aurora_internal.aurora_specialized_avatar_synthesizer import (
    behavior_modes_for_dimension,
)

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

# R1.3 of the Semantic Plateau Remediation Directive (2026-07-15): before
# this map, every lesson used the SAME frozen i_state pair set at
# ClassroomSession construction ("i_can", "i_saw" by default) for its
# entire lifetime -- one of the compounding causes of the 452/452 identity
# failure the directive documents. Each dimension now gets a pair chosen
# to oppose or texture that dimension's own nature (contradiction lessons
# get an affirmation/negation pair, uncertainty lessons get a
# capability/questioning pair, etc.), rotating across all ten canonical
# poles (aurora_simulation_engine.py's InceptionEntity i_state_bias) over
# the curriculum so every pole sees use, not just the original default two.
_DIMENSION_I_STATE_PAIRS: Dict[str, Tuple[str, str]] = {
    "coherence_maintenance": ("i_is", "i_saw"),
    "context_carryover": ("i_did", "i_didnt"),
    "ambiguity_handling": ("i_sought", "i_saw"),
    "contradiction_handling": ("i_is", "i_isnt"),
    "implied_intent_inference": ("i_can", "i_do"),
    "misunderstanding_repair": ("i_isnt", "i_did"),
    "uncertainty_signaling": ("i_can", "i_sought"),
    "boundary_calibration": ("i_do", "i_donot"),
    "framing_selection": ("i_saw", "i_did"),
    "emotional_calibration": ("i_is", "i_cannot"),
    "semantic_precision": ("i_did", "i_do"),
    "adaptive_strategy_selection": ("i_can", "i_donot"),
    "compression_elaboration_fit": ("i_do", "i_saw"),
    "perspective_integration": ("i_can", "i_saw"),
    "multi_turn_stability": ("i_did", "i_sought"),
}
_DEFAULT_I_STATE_PAIR: Tuple[str, str] = ("i_can", "i_saw")

# FIX-A019 (flat-divergence watchdog): halt the classroom rather than keep
# burning lessons once the entity-perspective signal is provably dead.
# Derived from the PERSISTED classroom_log.jsonl tail (not in-memory state)
# so the watchdog trips correctly across separate scheduled runs, not just
# within one long-lived process.
_FLAT_DIVERGENCE_HALT_THRESHOLD = 20
_ZERO_DIVERGENCE_EPS = 1e-9


class ClassroomHaltedError(RuntimeError):
    """Raised by ClassroomSession.run_lesson() when the flat-divergence
    watchdog trips (FIX-A019). Dead signal = stop, not continue."""


def _consecutive_zero_divergence_tail(state_dir: Path) -> int:
    """Count consecutive divergence_score==0.0 lessons at the END of
    classroom_log.jsonl, walking backward from the most recent entry.
    Degrades to 0 (never blocks the classroom) on any read/parse failure --
    the same failure-isolation discipline as every other guard in this
    codebase; a broken watchdog must never be the thing that halts real
    lessons."""
    log_path = state_dir / "classroom_log.jsonl"
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0
    count = 0
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            score = float(entry.get("divergence_score"))
        except Exception:
            break
        if abs(score) < _ZERO_DIVERGENCE_EPS:
            count += 1
        else:
            break
    return count


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


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


# R1.2 of the Semantic Plateau Remediation Directive (2026-07-15): maps each
# rubric dimension onto ImpressionCascade.EMOTION_VALENCE's own vocabulary
# (aurora_expression_perception.py), giving every lesson a distinct baseline
# "texture" instead of the same resonant/strained split for every dimension.
# Covers every dimension in _DEFAULT_CANDIDATE_DIMENSIONS above.
_DIMENSION_CHANNEL_TEXTURE: Dict[str, Dict[str, float]] = {
    "coherence_maintenance": {"trust": 0.6, "confusion": 0.4},
    "context_carryover": {"trust": 0.5, "anticipation": 0.5},
    "ambiguity_handling": {"curiosity": 0.6, "confusion": 0.4},
    "contradiction_handling": {"confusion": 0.5, "anger": 0.3, "surprise": 0.2},
    "implied_intent_inference": {"curiosity": 0.5, "determination": 0.5},
    "misunderstanding_repair": {"sadness": 0.3, "trust": 0.4, "determination": 0.3},
    "uncertainty_signaling": {"curiosity": 0.4, "confusion": 0.4, "anticipation": 0.2},
    "boundary_calibration": {"trust": 0.5, "fear": 0.3, "neutral": 0.2},
    "framing_selection": {"determination": 0.5, "curiosity": 0.5},
    "emotional_calibration": {"joy": 0.3, "sadness": 0.3, "trust": 0.4},
    "semantic_precision": {"determination": 0.6, "confusion": 0.4},
    "adaptive_strategy_selection": {"curiosity": 0.5, "determination": 0.5},
    "compression_elaboration_fit": {"neutral": 0.5, "determination": 0.5},
    "perspective_integration": {"trust": 0.5, "curiosity": 0.5},
    "multi_turn_stability": {"trust": 0.6, "anticipation": 0.4},
}


def _episode_to_entity_experience(episode: EpisodeResult, target_dimension: str) -> Dict[str, Any]:
    """
    Structured channel adapter (R1.2). Replaces the two-scalar
    resonant/strained compression this function used to produce -- that
    compression was worse than just lossy: "resonant" and "strained" are
    not entries in ImpressionCascade.EMOTION_VALENCE
    (aurora_expression_perception.py), so InceptionEntity.process_
    experience()'s valence computation was mathematically forced to 0.0
    on every lesson regardless of channel weights, and because
    strained == 1 - resonant, the channel magnitudes always summed to
    exactly 1.0, forcing intensity to a fixed 1/3 every time. That is the
    literal arithmetic behind the observed (0.3333, 0.0) constant tuple
    across all 904 real entity resolutions.

    Every channel name below is drawn from EMOTION_VALENCE's real
    vocabulary, built from four structured signals the EpisodeResult
    already carries (no new subsystem, richer use of existing data):

      - momentum: per-turn fitness deltas within THIS episode
        (conversation_trace), not just the episode average -- a lesson
        that trended up feels different from one that started well and
        collapsed, even at the same avg_fitness.
      - grounded: whether real understanding_gained entries exist for
        this episode (previously captured but routed nowhere).
      - target-dimension texture: _DIMENSION_CHANNEL_TEXTURE above, so a
        contradiction_handling lesson doesn't feel like a
        boundary_calibration one.
      - pull: engagement trajectory, final vs mean across the episode's
        own turns, not just the terminal engagement value in isolation.

    Dict contract is unchanged: {channels, tone, target_dimension,
    topic_category, understanding_gained} -- richer channels, same
    interface, no downstream breakage.
    """
    fitness = float(episode.avg_fitness or 0.0)
    engagement = float(episode.final_engagement or 0.0)
    trace = list(episode.conversation_trace or [])
    understanding = list(episode.understanding_gained or [])

    fitness_series = [float(t.get("fitness", 0.0) or 0.0) for t in trace]
    momentum = 0.0
    if len(fitness_series) >= 2:
        deltas = [fitness_series[i + 1] - fitness_series[i] for i in range(len(fitness_series) - 1)]
        momentum = sum(deltas) / len(deltas)

    grounded = _clamp01(len(understanding) / 3.0) if understanding else 0.0

    engagement_series = [float(t.get("engagement", 0.0) or 0.0) for t in trace]
    mean_engagement = (sum(engagement_series) / len(engagement_series)) if engagement_series else engagement
    pull = engagement - mean_engagement

    channels: Dict[str, float] = {}

    def _add(name: str, weight: float) -> None:
        if weight <= 0:
            return
        channels[name] = channels.get(name, 0.0) + weight

    # Base fitness/engagement composite -- successor to the old
    # resonant/strained split, mapped onto real EMOTION_VALENCE channels.
    resonance = _clamp01((fitness + engagement) / 2.0)
    _add("joy", resonance * 0.6)
    _add("trust", resonance * 0.4)
    _add("sadness", (1.0 - resonance) * 0.5)
    _add("confusion", (1.0 - resonance) * 0.3)

    # momentum channel
    if momentum > 0.01:
        _add("determination", min(1.0, momentum * 4.0))
    elif momentum < -0.01:
        _add("sadness", min(1.0, abs(momentum) * 4.0))
        _add("confusion", min(1.0, abs(momentum) * 2.0))

    # grounded channel
    if grounded > 0:
        _add("trust", grounded * 0.5)
        _add("curiosity", grounded * 0.3)
    else:
        _add("confusion", 0.2)

    # pull channel
    if pull > 0.02:
        _add("anticipation", min(1.0, pull * 3.0))
    elif pull < -0.02:
        _add("neutral", min(1.0, abs(pull) * 2.0))

    # target-dimension texture
    for name, weight in _DIMENSION_CHANNEL_TEXTURE.get(target_dimension, {"neutral": 1.0}).items():
        _add(name, weight)

    if not channels:
        channels = {"neutral": 1.0}

    return {
        "channels": {k: round(v, 4) for k, v in channels.items()},
        "tone": "warm" if resonance >= 0.55 else "neutral",
        "target_dimension": target_dimension,
        "topic_category": episode.topic_category,
        "understanding_gained": understanding,
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


_ROTATION_FILE = "classroom_corpus_rotation.json"


def _load_rotation_state(state_dir: Path) -> Dict[str, List[str]]:
    """Per-dimension record of which seed ids have already been fed to a
    lesson, persisted across scheduled runs. Without this, every curriculum
    run re-scans from the front of each dimension's example pool and finds
    the same first usable entry every time -- the pool never grows on its
    own (fail_points.json's live-diagnostic writer isn't part of the
    scheduled path, and the directed corpus is static text), so without
    persisted rotation the same handful of conversation ids just keep
    getting recycled forever."""
    try:
        with open(state_dir / _ROTATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(dim): [str(i) for i in (ids or [])] for dim, ids in data.items()}
    except Exception:
        pass
    return {}


def _save_rotation_state(state_dir: Path, state: Dict[str, List[str]]) -> None:
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        tmp = state_dir / (_ROTATION_FILE + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, state_dir / _ROTATION_FILE)
    except Exception:
        pass


def _real_example_seed(
    fail_records: Dict[str, Any],
    dimension: str,
    already_used: set,
    rotation_state: Optional[Dict[str, List[str]]] = None,
) -> Tuple[str, str]:
    """
    Pull one real seed for `dimension`, preferring an actually-observed
    failing conversation excerpt from fail_points.json's own `examples`
    (populated by the health-check pipeline from real corpus/live-turn
    failures), then falling back to a real conversational snippet pulled
    from the directed training corpus (aurora_internal/train.txt via
    DirectedTrainingCorpusBridge -- a genuinely different, much larger real
    text pool tagged to this same rubric dimension).

    Rotation is two-layered: `already_used` skips ids already picked earlier
    in *this* curriculum run (so one run's several lessons don't collide),
    and the persisted `rotation_state[dimension]` skips ids already fed in
    *previous* scheduled runs, so the pool actually advances over time
    instead of the same front-of-list entry recurring every run. Once every
    id in the combined pool has been used, rotation wraps back to the start
    for that dimension -- she goes through the whole known set again rather
    than freezing on nothing.

    Returns (seed_prompt, content_source). content_source is
    "generic" (nothing usable found anywhere), "real_failure_example:<id>",
    or "directed_corpus:<dimension>:<index>".
    """
    rotation_state = rotation_state if rotation_state is not None else {}
    persisted_used = set(rotation_state.get(dimension, []) or [])

    candidates: List[Tuple[str, str, str]] = []  # (id, seed_text, content_source)

    examples = (fail_records.get(dimension, {}) or {}).get("examples", []) or []
    for i, example in enumerate(examples):
        conv_id = str(example.get("conversation_id", "") or "") or f"unindexed_{i}"
        user_turns = [str(t) for t in (example.get("user_turns") or []) if str(t).strip()]
        if not user_turns:
            continue
        # The last user turn is usually the most specific/pointed one in
        # these multi-turn excerpts (see fail_points.json's own examples).
        seed = user_turns[-1].strip()
        candidates.append((f"fail_point:{conv_id}", seed, f"real_failure_example:{conv_id}"))

    try:
        bridge = get_directed_training_corpus_bridge()
        corpus_samples = bridge.samples_for_dimensions([dimension], limit=64).get(dimension, [])
    except Exception:
        corpus_samples = []
    for i, snippet in enumerate(corpus_samples):
        seed = str(snippet or "").strip()
        if not seed:
            continue
        candidates.append((f"corpus:{dimension}:{i}", seed, f"directed_corpus:{dimension}:{i}"))

    if not candidates:
        return "", "generic"

    # Held-out semantic probe battery exclusion (Semantic Plateau Remediation
    # Directive, Phase R0): a probe that ever became lesson-seed content would
    # stop being held-out, so any candidate whose text matches a probe turn
    # is dropped before rotation ever sees it. Degrades to a no-op (never
    # blocks the classroom) if the battery module is unavailable.
    try:
        from aurora_internal.aurora_semantic_probe_battery import is_seed_excluded
        candidates = [c for c in candidates if not is_seed_excluded(c[1])]
    except Exception:
        pass

    if not candidates:
        return "", "generic"

    for cand_id, seed, content_source in candidates:
        if cand_id in already_used or cand_id in persisted_used:
            continue
        already_used.add(cand_id)
        used_list = rotation_state.setdefault(dimension, [])
        used_list.append(cand_id)
        return seed, content_source

    # Whole combined pool exhausted across past runs -- wrap around and
    # start feeding the same real set again rather than going generic.
    rotation_state[dimension] = []
    cand_id, seed, content_source = candidates[0]
    already_used.add(cand_id)
    rotation_state[dimension].append(cand_id)
    return seed, content_source


def select_curriculum(
    systems: Dict[str, Any],
    n: int = 4,
    state_dir: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """
    Build a curriculum plan of `n` (target_dimension, seed_prompt,
    content_source) triples, ranked by real fail_points.json severity
    (fail_count, highest first -- same ranking aurora_diag.py's health check
    already uses).

    Every lesson that has a real failing-conversation excerpt available in
    fail_points.json gets it as seed_prompt -- not just stale/WORSENING
    dimensions. Confirmed empirically (see crystal-stagnation investigation,
    2026-07-09): with no seed_prompt, run_episode()'s synthetic dialogue
    only exercises a tiny, repetitive vocabulary (the dimension name plus a
    handful of connector words like "now"/"feels"/"likely"), all of which
    Aurora already has crystals for -- so "generic" lessons never introduce
    a genuinely new concept for the crystal-creation pipeline to catch,
    which is why her crystal count sat completely flat for weeks despite
    constant scheduled lesson activity. Real excerpts are actual varied
    conversation text, so they're what actually lets new vocabulary/concepts
    reach the crystal registry. Falls back to "generic" only when
    fail_points.json truly has no example for that dimension yet. Falls
    back to the full known dimension pool if fail_points.json has no data
    at all yet (fresh environment) -- there's no fail history to rank, but
    the lessons still need to happen.
    """
    sd = Path(state_dir) if state_dir else Path(str(systems.get("state_dir") or "aurora_state"))
    fp = _load_fail_points(sd)
    records: Dict[str, Any] = fp.get("records", {}) or {}

    if records:
        ranked = [dim for dim, _ in sorted(records.items(), key=lambda kv: -kv[1].get("fail_count", 0))]
    else:
        ranked = list(_DEFAULT_CANDIDATE_DIMENSIONS)

    rotation_state = _load_rotation_state(sd)
    used_example_ids: set = set()
    plan: List[Tuple[str, str, str]] = []
    for dim in ranked:
        if len(plan) >= n:
            break
        seed_prompt, content_source = _real_example_seed(
            records, dim, used_example_ids, rotation_state=rotation_state
        )
        plan.append((dim, seed_prompt, content_source))
    _save_rotation_state(sd, rotation_state)

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
        consecutive_zero = _consecutive_zero_divergence_tail(self.state_dir)
        if consecutive_zero >= _FLAT_DIVERGENCE_HALT_THRESHOLD:
            raise ClassroomHaltedError(
                f"Flat-divergence watchdog tripped: {consecutive_zero} consecutive "
                "classroom lessons with divergence_score == 0.0 (FIX-A019). Dead "
                "signal = stop, not continue -- see the Semantic Plateau "
                "Remediation Directive R1.3. Fix the classroom differential "
                "before running more lessons."
            )

        self._lesson_count += 1
        lesson_id = f"class_{target_dimension}_{self._lesson_count}_{int(time.time())}"

        # R1.3: rotate the perspective pair per dimension instead of the
        # frozen pair fixed at ClassroomSession construction. The entity
        # objects themselves persist across lessons (their cascades keep
        # accumulating shards/seeds/relics) -- only the i_state lens each
        # one currently views experience through changes per lesson.
        i_state_pair = _DIMENSION_I_STATE_PAIRS.get(target_dimension, _DEFAULT_I_STATE_PAIR)
        for entity_id, i_state in zip(self.entity_ids, i_state_pair):
            entity = self.engine.entities.get(entity_id)
            if entity is not None:
                entity.i_state = i_state

        dev_before_snap = record_developmental_snapshot(self.systems, force=True)
        dev_before = dev_before_snap.get("dev_index") if dev_before_snap else None

        # behavior_modes (2026-07-14 fix): without this, _shape_topic_for_turn()
        # never activates the dimension-specific pressure behavior (e.g.
        # context_carryover's test_cross_turn_memory, the "Earlier you
        # said..." callback prompt) -- every turn silently fell through to
        # the same static one-line prompt (the dimension name itself), so
        # a lesson could never actually exercise the targeted competency.
        # This is the same _DIMENSION_TO_BEHAVIOR mapping
        # synthesize_from_summary() already uses for dream-triggered
        # specialized episodes; classroom lessons were the one path that
        # bypassed it.
        queued = self.engine.session.queue_avatar_specs([
            {
                "avatar_id": lesson_id,
                "pressure_targets": {target_dimension: 1.0},
                "behavior_modes": behavior_modes_for_dimension(target_dimension),
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

        # MTSL perturbation probe (live-wired 2026-07-14): see
        # _run_mtsl_perturbation_probe's own docstring. Isolated so a
        # probe failure can never take out a lesson result that already
        # persisted fine.
        try:
            self._run_mtsl_perturbation_probe()
        except Exception:
            pass

        return result

    def _run_mtsl_perturbation_probe(self) -> None:
        """A real what-if experiment against the MTSL coordinator's own
        buffered topology history, recorded as classroom evidence
        (FIX-A012: source-tagged, lower authority than lived evidence,
        never alone promotes a variant) on whatever semantic variant is
        currently live at that coordinate. No-op (never fakes anything)
        when no coordinator has observed anything yet this session."""
        dimensional = self.systems.get("dimensional")
        coordinator = getattr(dimensional, "_mtsl_coordinator", None)
        if coordinator is None:
            return
        coordinator.run_perturbation_probe(getattr(dimensional, "dps", None), source="classroom")

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
        fail_points.json severity, real failing conversation content fed in
        for every dimension that has an example on record) and run them in
        order. This is the entry point the scheduled workflow runs --
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
