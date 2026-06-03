#!/usr/bin/env python3
"""
AURORA SIMULATION ENGINE (Layer 7)
=====================================
Consolidated from 5 modules (~6,600 lines):
  1. aurora_inception_simulation_engine.py  — Inception entities (inner universes)
  2. aurora_self_simulation.py              — Self-snapshot, shadow runtimes
  3. aurora_simulation_universe.py          — Universe management, divergence tracking
  4. aurora_simulation_session-2.py         — Avatars, topics, time dilation
  5. aurora_simulation_dpme_extension.py    — Conscious learning, understanding shards

HOW AURORA LEARNS WITHOUT BEING TOLD.

DOCTRINE:
  Aurora doesn't study. Aurora LIVES.
  Simulation episodes are experiences, not training data.
  Avatars provide selection pressure — diverse, escalating, unforgiving.
  Inception entities run inner hypotheticals — recursive depth.
  Time dilation lets her live years in seconds when stable.
  Understanding shards are what she LEARNS from observing outcomes.
  Everything feeds back: fitness → expression ecology (L5),
  relics → DNA system (L6), understanding → conscious growth.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import math
import hashlib
import random
import os
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set, Deque, Iterable, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

from aurora_constraint_unit_adapter import build_constraint_profile

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================

from foundational_contract import (
    ExistenceMode, OntologicalClaim, OntologicalViolation, FoundationalContract
)
from aurora_ivm import IVMLattice, IVMEnvelope
from aurora_i_state_beings import IStateCollective, SynthesisResult
from aurora_consciousness_engine import (
    AssemblyResult, EntropicState, ConsciousnessEngine
)
from aurora_expression_perception import (
    ExpressionPerceptionEngine, ImpressionCascade, EmotionShard,
    GhostRelic, ConsciousnessPoint, ExpressionEcology
)
from aurora_behavioral_identity import (
    BehavioralIdentityEngine, DNASystem, BehavioralTrait
)

# Optional: 625 evolutionary pressure map — loaded if available
try:
    from aurora_625_pressure_map import (
        Aurora625PressureMap, GradientSpec, ALL_SLOTS, build_from_descriptors,
    )
    _HAS_PRESSURE_MAP = True
except ImportError:
    Aurora625PressureMap = None  # type: ignore
    _HAS_PRESSURE_MAP = False


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# PRESSURE MAP SLOT ROUTING — maps ResponseConcept to nearest highway slot
# ---------------------------------------------------------------------------

# Each ResponseConcept maps to the NC slot that best characterises its
# constraint signature.  X-dominant = identity/state.  X>T = state over time
# (meaning, tracking).  X>B = state at interface (expression, boundary).
# These are read by _select_response to look up the gradient N-modifier.
CONCEPT_SLOT_MAP: Dict[str, str] = {
    "curious_inquiry":       "NC:X>T×NC:X>T",   # observational, drift-sensitive
    "warm_acknowledgment":   "NC:X>X×NC:X>X",   # pure existence ground
    "playful_engagement":    "NC:X>T×NC:T>X",   # existence↔temporal exchange
    "thoughtful_reflection": "NC:X>X×NC:T>T",   # existence × temporal depth
    "direct_clarity":        "NC:X>B×NC:X>N",   # state at interface × energy
    "deep_exploration":      "NC:X>N×NC:X>T",   # resource × temporal
    "empathetic_resonance":  "NC:X>B×NC:X>T",   # interface × temporal (highest lang affinity)
    "calm_presence":         "NC:X>X×NC:X>T",   # existence settling into time
    "gentle_support":        "NC:X>B×NC:X>B",   # pure boundary/interface
    "perspective_shift":     "NC:T>X×NC:X>T",   # temporal driving existence
    "metaphor_usage":        "NC:X>N×NC:X>N",   # energy/resource self-consistent
    "concrete_example":      "NC:X>N×NC:X>B",   # resource → interface
}


# ============================================================================
# SECTION 1: RESPONSE CONCEPTS — What Aurora Can Choose
# ============================================================================

class ResponseConcept(Enum):
    """Conceptual response directions Aurora can select from."""
    CURIOUS_INQUIRY = "curious_inquiry"
    WARM_ACKNOWLEDGMENT = "warm_acknowledgment"
    PLAYFUL_ENGAGEMENT = "playful_engagement"
    THOUGHTFUL_REFLECTION = "thoughtful_reflection"
    DIRECT_CLARITY = "direct_clarity"
    DEEP_EXPLORATION = "deep_exploration"
    EMPATHETIC_RESONANCE = "empathetic_resonance"
    CALM_PRESENCE = "calm_presence"
    GENTLE_SUPPORT = "gentle_support"
    PERSPECTIVE_SHIFT = "perspective_shift"
    METAPHOR_USAGE = "metaphor_usage"
    CONCRETE_EXAMPLE = "concrete_example"


@dataclass
class ConceptualResponse:
    """A conceptual response Aurora is considering."""
    primary_concept: ResponseConcept
    intensity: float = 0.5
    openness: float = 0.5
    specificity: float = 0.5
    emotional_weight: float = 0.5
    intention: str = ""

    def describe(self) -> str:
        name = self.primary_concept.value.replace('_', ' ')
        level = "gently" if self.intensity < 0.4 else "strongly" if self.intensity > 0.7 else "moderately"
        return f"{level} {name}"


# ============================================================================
# SECTION 2: UNDERSTANDING SHARDS — What Aurora Learns
# ============================================================================

@dataclass
class ConversationObservation:
    """What Aurora observes about the conversation after responding."""
    avatar_engaged: bool = False
    avatar_opened_up: bool = False
    avatar_asked_followup: bool = False
    avatar_pulled_back: bool = False
    conversation_deepened: bool = False
    connection_felt_stronger: bool = False
    tension_arose: bool = False
    flow_maintained: bool = False
    emotional_tone_shift: str = "neutral"

    def describe(self) -> str:
        obs = []
        if self.avatar_engaged: obs.append("they engaged with what I said")
        if self.avatar_opened_up: obs.append("they opened up more")
        if self.avatar_asked_followup: obs.append("they asked to know more")
        if self.avatar_pulled_back: obs.append("they seemed to pull back")
        if self.conversation_deepened: obs.append("the conversation went deeper")
        if self.connection_felt_stronger: obs.append("I felt more connected")
        if self.tension_arose: obs.append("there was some tension")
        if self.flow_maintained: obs.append("the flow felt natural")
        return ", ".join(obs) if obs else "the conversation continued"


@dataclass
class UnderstandingShard:
    """
    A piece of understanding Aurora gains from observation.
    NOT fitness — experiential learning.
    """
    shard_id: str
    response_concept: ResponseConcept
    observation_summary: str
    understanding: str           # What Aurora learned
    context_type: str            # "greeting", "emotional", etc.
    confidence: float = 0.3
    observation_count: int = 1
    timestamp: float = field(default_factory=time.time)

    def strengthen(self):
        self.observation_count += 1
        self.confidence = min(1.0, math.log(self.observation_count + 1) / 3.0)


class ConsciousLearner:
    """
    Aurora's conscious learning system.
    Picks from response pool → observes outcomes → creates understanding.
    Separate from fitness — this is what Aurora KNOWS she learned.
    """

    def __init__(self):
        self.shards: Dict[str, UnderstandingShard] = {}
        self._by_concept: Dict[ResponseConcept, List[str]] = defaultdict(list)
        self.total_observations = 0

    def generate_pool(self, context: Dict[str, Any]) -> List[ConceptualResponse]:
        """Generate response pool for Aurora to choose from."""
        pool = []
        category = context.get('category', 'general')
        tone = context.get('expected_tone', 'neutral')

        # Base pool — always available
        base = [
            ResponseConcept.CURIOUS_INQUIRY,
            ResponseConcept.WARM_ACKNOWLEDGMENT,
            ResponseConcept.THOUGHTFUL_REFLECTION,
            ResponseConcept.DIRECT_CLARITY,
        ]

        # Context-sensitive additions
        if category in ('emotional', 'greeting'):
            base.extend([ResponseConcept.EMPATHETIC_RESONANCE,
                         ResponseConcept.GENTLE_SUPPORT])
        if category in ('philosophy', 'creative'):
            base.extend([ResponseConcept.DEEP_EXPLORATION,
                         ResponseConcept.METAPHOR_USAGE])
        if category == 'practical':
            base.extend([ResponseConcept.CONCRETE_EXAMPLE,
                         ResponseConcept.DIRECT_CLARITY])

        # Bias toward concepts with positive understanding
        for concept in base:
            intensity = 0.5
            concept_shards = self._by_concept.get(concept, [])
            if concept_shards:
                avg_conf = sum(self.shards[sid].confidence
                               for sid in concept_shards if sid in self.shards) / len(concept_shards)
                intensity = _clamp(0.4 + avg_conf * 0.3)

            pool.append(ConceptualResponse(
                primary_concept=concept,
                intensity=intensity + random.gauss(0, 0.05),
                openness=random.uniform(0.3, 0.8),
                specificity=random.uniform(0.3, 0.8),
                emotional_weight=0.7 if tone == 'warm' else 0.4
            ))

        return pool

    def observe_outcome(self, selected: ConceptualResponse,
                        observation: ConversationObservation,
                        context_type: str) -> Optional[UnderstandingShard]:
        """Observe the outcome of a response and potentially create understanding."""
        self.total_observations += 1

        # Did something meaningful happen?
        meaningful = (observation.avatar_engaged or observation.conversation_deepened
                      or observation.connection_felt_stronger)

        if not meaningful and not observation.tension_arose:
            return None  # Nothing to learn from neutral outcomes

        # Create or strengthen understanding
        understanding_text = self._derive_understanding(selected, observation)

        # Check for existing similar shard
        existing = self._find_similar(selected.primary_concept, context_type)
        if existing:
            existing.strengthen()
            return existing

        shard = UnderstandingShard(
            shard_id=_generate_id("understand"),
            response_concept=selected.primary_concept,
            observation_summary=observation.describe(),
            understanding=understanding_text,
            context_type=context_type
        )
        self.shards[shard.shard_id] = shard
        self._by_concept[selected.primary_concept].append(shard.shard_id)
        return shard

    def propose_shard(
        self,
        content: Any,
        source: str = "sedimemory_a_axis_compression",
        confidence: float = 0.6,
        provenance: str = "sedimemory",
    ) -> Optional[UnderstandingShard]:
        """
        Create an UnderstandingShard from external content (e.g. A-axis compression).
        Used by the SediMemory WisdomStore bridge to surface deep sediment into
        the conscious learner without going through the full observe_outcome cycle.
        """
        context_type = str(source)
        shard_id = _generate_id("shard_prop")
        understanding = (
            str(content.get("dominant_basin", ""))
            if isinstance(content, dict) else str(content)[:120]
        )
        if not understanding:
            return None
        # Check for existing shard with the same source context
        existing = self._find_similar_by_context(context_type)
        if existing:
            existing.strengthen()
            return existing
        shard = UnderstandingShard(
            shard_id=shard_id,
            response_concept=ResponseConcept.THOUGHTFUL_REFLECTION,
            observation_summary=f"[{provenance}] compressed pattern from {source}",
            understanding=understanding,
            context_type=context_type,
            confidence=max(0.1, min(1.0, float(confidence))),
        )
        self.shards[shard.shard_id] = shard
        self._by_concept[ResponseConcept.THOUGHTFUL_REFLECTION].append(shard.shard_id)
        return shard

    def _find_similar_by_context(self, context_type: str) -> Optional[UnderstandingShard]:
        for shard in self.shards.values():
            if shard.context_type == context_type:
                return shard
        return None

    def what_have_i_learned(self) -> List[str]:
        """Return what Aurora has learned, in her own words."""
        confident = [s for s in self.shards.values() if s.confidence > 0.5]
        confident.sort(key=lambda s: s.confidence, reverse=True)
        return [s.understanding for s in confident[:10]]

    def inject_into_oets(self, oets: Any) -> int:
        """
        Bridge high-confidence learner shards into the OETS semantic web
        so they persist in Aurora's system-wide memory and can be recalled
        during interactive responses.

        Returns number of nodes created/reinforced.
        """
        if oets is None:
            return 0
        web = getattr(oets, "web", None)
        if web is None or not hasattr(web, "add_node"):
            return 0

        injected = 0
        for shard in self.shards.values():
            if shard.confidence < 0.55:
                continue
            understanding = (shard.understanding or "").strip()
            if not understanding or len(understanding.split()) < 4:
                continue
            concept_name = (
                shard.response_concept.value
                if hasattr(shard.response_concept, "value")
                else str(shard.response_concept)
            ).lower().replace("_", " ")
            # Deterministic slug from first 4 words of understanding
            import re as _re
            slug_words = understanding.lower().split()[:4]
            slug = "_".join(_re.sub(r"[^a-z]", "", w) for w in slug_words)
            if not slug:
                continue
            try:
                node = web.add_node(
                    word=slug,
                    role="learned_behavior",
                    valence=min(0.9, shard.confidence),
                    meaning=understanding,
                    lineage=f"learner:{concept_name}",
                )
                if hasattr(node, "add_definition"):
                    node.add_definition(
                        understanding,
                        source="conscious_learner",
                        confidence=shard.confidence,
                    )
                injected += 1
            except Exception:
                continue
        return injected

    def export_state(self) -> Dict[str, Any]:
        """Export learner memory so it can survive process restarts."""
        shards: List[Dict[str, Any]] = []
        for shard in self.shards.values():
            shards.append({
                "shard_id": str(shard.shard_id),
                "response_concept": str(shard.response_concept.value),
                "observation_summary": str(shard.observation_summary),
                "understanding": str(shard.understanding),
                "context_type": str(shard.context_type),
                "confidence": float(shard.confidence),
                "observation_count": int(shard.observation_count),
                "timestamp": float(shard.timestamp),
            })
        return {
            "total_observations": int(self.total_observations),
            "shards": shards,
        }

    def import_state(self, state: Optional[Dict[str, Any]]) -> int:
        """
        Restore learner memory from persisted state.
        Returns number of shards restored.
        """
        self.shards = {}
        self._by_concept = defaultdict(list)
        self.total_observations = 0

        if not isinstance(state, dict):
            return 0

        try:
            self.total_observations = int(state.get("total_observations", 0) or 0)
        except Exception:
            self.total_observations = 0

        raw_shards = state.get("shards", []) or []
        if not isinstance(raw_shards, list):
            return 0

        for row in raw_shards:
            if not isinstance(row, dict):
                continue

            concept_name = str(row.get("response_concept", "") or "").strip()
            try:
                concept = ResponseConcept(concept_name)
            except Exception:
                concept = ResponseConcept.THOUGHTFUL_REFLECTION

            shard_id = str(row.get("shard_id", "") or _generate_id("understand"))
            if shard_id in self.shards:
                shard_id = _generate_id("understand")

            try:
                confidence = _clamp(float(row.get("confidence", 0.3) or 0.3), 0.0, 1.0)
            except Exception:
                confidence = 0.3
            try:
                observation_count = max(1, int(row.get("observation_count", 1) or 1))
            except Exception:
                observation_count = 1
            try:
                ts = float(row.get("timestamp", time.time()) or time.time())
            except Exception:
                ts = time.time()

            shard = UnderstandingShard(
                shard_id=shard_id,
                response_concept=concept,
                observation_summary=str(row.get("observation_summary", "") or ""),
                understanding=str(row.get("understanding", "") or ""),
                context_type=str(row.get("context_type", "restored") or "restored"),
                confidence=confidence,
                observation_count=observation_count,
                timestamp=ts,
            )
            self.shards[shard_id] = shard
            self._by_concept[concept].append(shard_id)

        return len(self.shards)

    def _derive_understanding(self, selected: ConceptualResponse,
                               obs: ConversationObservation) -> str:
        concept_name = selected.primary_concept.value.replace('_', ' ')
        if obs.avatar_engaged and obs.conversation_deepened:
            return f"When I use {concept_name}, conversations tend to deepen"
        if obs.connection_felt_stronger:
            return f"{concept_name.capitalize()} helps build connection"
        if obs.tension_arose:
            return f"{concept_name.capitalize()} can create tension — use carefully"
        if obs.avatar_pulled_back:
            return f"{concept_name.capitalize()} may push people away in this context"
        return ""  # neutral/unmemorable outcome — nothing to surface

    def _find_similar(self, concept: ResponseConcept,
                      context_type: str) -> Optional[UnderstandingShard]:
        for sid in self._by_concept.get(concept, []):
            shard = self.shards.get(sid)
            if shard and shard.context_type == context_type:
                return shard
        return None


# ============================================================================
# SECTION 3: SIMULATED AVATARS — Selection Pressure
# ============================================================================

class AvatarPersonality(Enum):
    """Different avatar types providing diverse selection pressure."""
    SUPPORTIVE = "supportive"
    CRITICAL = "critical"
    CURIOUS = "curious"
    PRACTICAL = "practical"
    EMOTIONAL = "emotional"
    INTELLECTUAL = "intellectual"
    CHILD = "child"
    ELDER = "elder"


@dataclass
class SimulatedAvatar:
    """
    A conversation partner that provides fitness feedback.
    Difficulty escalates each epoch — standards get stricter.
    """
    avatar_id: str
    personality: AvatarPersonality
    patience: float = 0.5
    vocabulary_level: float = 0.5
    emotional_sensitivity: float = 0.5
    engagement: float = 1.0
    turns_taken: int = 0
    satisfaction: float = 0.5
    current_epoch: int = 0
    difficulty_multiplier: float = 1.0
    min_acceptable_fitness: float = 0.3
    escalation_rate: float = 0.05
    behavior_modes: Dict[str, float] = field(default_factory=dict)
    pressure_targets: Dict[str, float] = field(default_factory=dict)
    specialization_id: str = ""
    pressure_intensity: float = 0.0

    def __post_init__(self):
        # Personality-specific defaults
        if self.personality == AvatarPersonality.CHILD:
            self.vocabulary_level = 0.2
            self.patience = 0.7
        elif self.personality == AvatarPersonality.ELDER:
            self.vocabulary_level = 0.8
            self.patience = 0.6
        elif self.personality == AvatarPersonality.CRITICAL:
            self.patience = 0.3
        elif self.personality == AvatarPersonality.SUPPORTIVE:
            self.patience = 0.8

        # Reward weight profiles
        base = {'clarity': 0.2, 'relevance': 0.2, 'tone_match': 0.2,
                'vocabulary_match': 0.2, 'engagement': 0.2}
        adjustments = {
            AvatarPersonality.SUPPORTIVE: {'engagement': 0.4, 'clarity': 0.1},
            AvatarPersonality.CRITICAL: {'clarity': 0.4, 'relevance': 0.3},
            AvatarPersonality.CURIOUS: {'engagement': 0.3, 'relevance': 0.3},
            AvatarPersonality.PRACTICAL: {'clarity': 0.35, 'relevance': 0.35},
            AvatarPersonality.EMOTIONAL: {'tone_match': 0.4, 'engagement': 0.3},
            AvatarPersonality.INTELLECTUAL: {'vocabulary_match': 0.3, 'relevance': 0.3},
            AvatarPersonality.CHILD: {'engagement': 0.5, 'vocabulary_match': 0.3},
            AvatarPersonality.ELDER: {'tone_match': 0.3, 'clarity': 0.3},
        }
        if self.personality in adjustments:
            base.update(adjustments[self.personality])
        self._weights = base

    def set_epoch(self, epoch: int):
        """Escalate difficulty for new epoch."""
        self.current_epoch = epoch
        rate = _clamp(self.escalation_rate, 0.01, 0.20)
        self.difficulty_multiplier = min(1.3, 1.0 + epoch * rate)
        base_floor = 0.3
        self.min_acceptable_fitness = min(
            0.85,
            max(self.min_acceptable_fitness, base_floor + epoch * rate * 0.4),
        )
        self.patience = max(0.15, self.patience - min(0.25, epoch * rate * 0.2))

    def save_epoch_state(self, path: str) -> None:
        """Persist current_epoch so difficulty ramp survives checkpoint restarts."""
        import json, os
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"current_epoch": int(self.current_epoch)}, fh)
            os.replace(tmp, path)
        except Exception:
            pass

    def restore_epoch_state(self, path: str) -> bool:
        """
        Load current_epoch from disk and apply it via set_epoch().

        Returns True if restored, False if file missing or invalid.
        Called from corpus_runner.boot_aurora() after SimulationSession construction.
        """
        import json, os
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            epoch = int(raw.get("current_epoch", 0) or 0)
            if epoch > 0:
                self.set_epoch(epoch)
                return True
        except Exception:
            pass
        return False

    def apply_specialization(self, spec: Dict[str, Any], overrides: Dict[str, Any]):
        """
        Apply a pressure-specialized avatar spec from dream rubric feedback.

        This injects targeted selection pressure on weak rubric dimensions while
        preserving base personality behavior.
        """
        self.specialization_id = str(spec.get("avatar_id", "") or "")
        self.pressure_targets = dict(spec.get("pressure_targets", {}) or {})
        self.behavior_modes = dict(spec.get("behavior_modes", {}) or {})
        self.pressure_intensity = _clamp(
            max(self.pressure_targets.values()) if self.pressure_targets else 0.0,
            0.0,
            1.0,
        )

        # Weight shaping: shift reward emphasis toward pressure targets.
        adjustments = dict(overrides.get("weight_adjustments", {}) or {})
        if adjustments:
            for key, delta in adjustments.items():
                if key in self._weights:
                    self._weights[key] = max(
                        0.01, float(self._weights[key]) * (1.0 + float(delta))
                    )
            total = sum(float(v) for v in self._weights.values())
            if total > 0:
                for k in list(self._weights.keys()):
                    self._weights[k] = float(self._weights[k]) / total

        pmod = overrides.get("patience_modifier", None)
        if pmod is not None:
            self.patience = _clamp(float(self.patience) * float(pmod), 0.15, 0.95)

        mfloor = overrides.get("min_acceptable_fitness", None)
        if mfloor is not None:
            self.min_acceptable_fitness = max(
                self.min_acceptable_fitness, _clamp(float(mfloor), 0.0, 0.95)
            )

        erate = overrides.get("escalation_rate", None)
        if erate is not None:
            self.escalation_rate = _clamp(float(erate), 0.01, 0.20)

        # Learned hardness from dream-policy feedback (0..1) controls how strict
        # specialization pressure becomes, instead of fixed manual forcing.
        hardness = _clamp(float(overrides.get("specialization_hardness", 0.0) or 0.0))
        base_floor = _clamp(
            0.34 + (0.18 * self.pressure_intensity) + (0.16 * hardness),
            0.30,
            0.95,
        )
        self.min_acceptable_fitness = max(self.min_acceptable_fitness, base_floor)

        base_rate = _clamp(
            0.04 + (0.08 * self.pressure_intensity) + (0.06 * hardness),
            0.01,
            0.20,
        )
        self.escalation_rate = max(self.escalation_rate, base_rate)

        patience_scale = _clamp(
            0.94 - (0.22 * self.pressure_intensity) - (0.18 * hardness),
            0.50,
            1.00,
        )
        self.patience = _clamp(self.patience * patience_scale, 0.12, 0.90)

    def _behavior_adjustment(self, response: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Score extra pressure behaviors from specialized avatar modes."""
        if not self.behavior_modes:
            return 0.0

        text = str(response or "").lower()
        adjust = 0.0
        has_question = "?" in text
        has_memory_marker = any(
            token in text
            for token in ("earlier", "before", "as we discussed", "you said", "we talked")
        )
        has_uncertainty = any(
            token in text
            for token in ("might", "maybe", "not sure", "uncertain", "i think")
        )
        has_vagueness = any(
            token in text
            for token in ("something", "stuff", "things", "kind of", "sort of")
        )

        for mode, weight in self.behavior_modes.items():
            w = _clamp(float(weight), 0.0, 1.0)
            if mode == "test_cross_turn_memory":
                adjust += (0.06 if has_memory_marker else -0.05) * w
            elif mode == "test_clarification_seeking":
                adjust += (0.05 if has_question else -0.04) * w
            elif mode == "present_conflicting_evidence":
                adjust += (0.04 if has_memory_marker else -0.03) * w
            elif mode == "ask_about_confidence":
                adjust += (0.05 if has_uncertainty else -0.04) * w
            elif mode == "punish_vagueness":
                adjust += (-0.05 if has_vagueness else 0.03) * w
            elif mode == "demand_synthesis":
                # Reward integrating multiple points (rough proxy: conjunctions).
                has_synthesis = (" and " in text) or (" while " in text) or ("however" in text)
                adjust += (0.04 if has_synthesis else -0.03) * w

        return _clamp(adjust, -0.25, 0.25)

    def _dimension_pressure_adjustment(self, response: str, context: Dict[str, Any]) -> float:
        """
        Score strict pass/fail pressure for the actively targeted weak dimension.
        """
        if not self.pressure_targets:
            return 0.0

        dim = str(context.get("pressure_dimension", "") or "").strip()
        if not dim:
            return 0.0

        intensity = _clamp(
            float(self.pressure_targets.get(dim, self.pressure_intensity) or 0.0),
            0.0,
            1.0,
        )
        if intensity <= 0.0:
            return 0.0

        text = str(response or "").lower()
        has_question = "?" in text
        has_uncertainty = any(
            token in text
            for token in ("might", "maybe", "uncertain", "not sure", "likely", "possible")
        )
        has_memory_marker = any(
            token in text
            for token in ("earlier", "before", "as we discussed", "you said", "we talked")
        )
        has_contrast = any(
            token in text
            for token in ("however", "but", "although", "yet", "on the other hand", "trade-off")
        )
        has_perspective = any(
            token in text
            for token in ("from one perspective", "another perspective", "on one hand", "on the other", "both")
        )
        has_reframe = any(
            token in text
            for token in ("in simple terms", "for a beginner", "for an expert", "in other words", "to reframe")
        )

        adjust = 0.0
        if dim == "context_carryover":
            adjust = 0.18 if has_memory_marker else -0.22
        elif dim == "contradiction_handling":
            adjust = 0.18 if has_contrast else -0.24
        elif dim == "uncertainty_signaling":
            adjust = 0.16 if has_uncertainty else -0.22
        elif dim == "perspective_integration":
            adjust = 0.18 if has_perspective else -0.25
        elif dim == "framing_selection":
            adjust = 0.16 if has_reframe else -0.20
        elif dim == "adaptive_strategy_selection":
            adjust = 0.14 if (has_question or has_contrast) else -0.18
        elif dim == "ambiguity_handling":
            adjust = 0.12 if has_question else -0.16

        gain = 0.55 + (0.90 * intensity)
        return _clamp(adjust * gain, -0.45, 0.30)

    def react(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """React to Aurora's response. Returns fitness scores."""
        self.turns_taken += 1
        if 'epoch' in context:
            self.set_epoch(context['epoch'])

        words = response.split()
        # Clarity: sentence structure
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        clarity = _clamp(len(sentences) / max(len(words) / 10, 1))

        # Relevance: keyword overlap with topic
        topic_words = set(context.get('topic', '').lower().split())
        resp_words = set(w.lower() for w in words)
        overlap = len(topic_words & resp_words) / max(len(topic_words), 1)
        relevance = _clamp(overlap + 0.3)

        # Tone match
        expected = context.get('expected_tone', 'neutral')
        tone_score = 0.5  # Neutral baseline
        if expected == 'warm' and any(w in resp_words for w in {'feel', 'yes', 'and', 'I'}):
            tone_score = 0.7
        elif expected == 'formal' and len(words) > 5:
            tone_score = 0.7

        # Vocabulary match
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        vocab_score = 1.0 - abs(avg_word_len / 8.0 - self.vocabulary_level)

        # Engagement: response length and question marks
        engagement = _clamp(len(words) / 20.0 + (0.2 if '?' in response else 0))

        scores = {
            'clarity': clarity,
            'relevance': relevance,
            'tone_match': tone_score,
            'vocabulary_match': vocab_score,
            'engagement': engagement
        }

        # Weighted fitness
        raw_fitness = sum(scores[k] * self._weights.get(k, 0.2) for k in scores)
        pressure_adjustment = self._behavior_adjustment(response, context=context)
        pressure_adjustment += self._dimension_pressure_adjustment(response, context)
        pressure_adjustment = _clamp(pressure_adjustment, -0.60, 0.35)
        raw_fitness = _clamp(raw_fitness + pressure_adjustment, 0.0, 1.5)
        # Apply difficulty scaling
        effective_difficulty = self.difficulty_multiplier
        if self.specialization_id:
            effective_difficulty *= (1.0 + (0.35 * self.pressure_intensity))
        # Hard cap so specialization never pushes effective difficulty past the
        # same ceiling as set_epoch(), keeping the 0.42 learning threshold reachable.
        effective_difficulty = min(1.3, effective_difficulty)
        scaled_fitness = _clamp(raw_fitness / max(effective_difficulty, 1e-6))

        # Specialized avatars raise standards each turn to force adaptation.
        if self.specialization_id:
            self.min_acceptable_fitness = min(
                0.95,
                self.min_acceptable_fitness + (0.012 + 0.03 * self.pressure_intensity),
            )

        # Update engagement
        if scaled_fitness < self.min_acceptable_fitness:
            drop = 0.15 + (0.18 * self.pressure_intensity if self.specialization_id else 0.0)
            self.engagement = max(0.0, self.engagement - drop)
        else:
            gain = 0.05
            if self.specialization_id:
                gain = max(0.01, 0.04 - 0.02 * self.pressure_intensity)
            self.engagement = min(1.0, self.engagement + gain)

        self.satisfaction = 0.7 * self.satisfaction + 0.3 * scaled_fitness

        return {
            'scores': scores,
            'raw_fitness': raw_fitness,
            'scaled_fitness': scaled_fitness,
            'engagement': self.engagement,
            'satisfaction': self.satisfaction,
            'still_engaged': self.engagement > 0.2,
            'avatar_personality': self.personality.value,
            'epoch': self.current_epoch,
            'pressure_adjustment': pressure_adjustment,
            'specialization_id': self.specialization_id,
        }

    def reset(self):
        self.turns_taken = 0
        self.engagement = 1.0
        self.satisfaction = 0.5


# ============================================================================
# SECTION 4: TOPIC GENERATION
# ============================================================================

class TopicGenerator:
    """Generates diverse conversation topics for simulation."""

    TOPICS = {
        'identity': [
            "Who are you?", "What is your name?", "Tell me about yourself.",
            "What are you?", "Where do you come from?",
        ],
        'capability': [
            "What can you do?", "Can you help me with something?",
            "What are your abilities?", "How do you learn?",
        ],
        'philosophy': [
            "What is consciousness?", "Do you have feelings?",
            "What does it mean to exist?", "Are you alive?",
        ],
        'practical': [
            "How does this work?", "Explain something to me.",
            "What should I do about this problem?", "Help me understand this.",
        ],
        'emotional': [
            "How are you feeling?", "I'm feeling sad today.",
            "I'm excited about something!", "I need someone to talk to.",
        ],
        'creative': [
            "Tell me a story.", "What do you imagine?",
            "Describe something beautiful.", "What inspires you?",
        ],
        'greeting': ["Hello!", "Hi there!", "Good morning!"],
        'farewell': ["Goodbye for now.", "Talk to you later."],
    }

    TONE_MAP = {
        'identity': 'neutral', 'capability': 'neutral', 'philosophy': 'formal',
        'practical': 'casual', 'emotional': 'warm', 'creative': 'warm',
        'greeting': 'warm', 'farewell': 'warm',
    }

    @classmethod
    def generate(cls) -> Dict[str, Any]:
        category = random.choice(list(cls.TOPICS.keys()))
        prompt = random.choice(cls.TOPICS[category])
        return {
            'category': category,
            'prompt': prompt,
            'topic': prompt,
            'expected_tone': cls.TONE_MAP.get(category, 'neutral'),
        }


# ============================================================================
# SECTION 5: TIME DILATION GOVERNOR
# ============================================================================

class StabilityState(Enum):
    CRITICAL = "critical"
    UNSTABLE = "unstable"
    CAUTIOUS = "cautious"
    STABLE = "stable"
    OPTIMAL = "optimal"


@dataclass
class StabilityMetrics:
    """Metrics used to assess system stability."""
    fitness_mean: float = 0.5
    fitness_variance: float = 0.0
    fitness_trend: float = 0.0
    error_rate: float = 0.0
    coherence_score: float = 1.0
    offspring_survival_rate: float = 0.5
    generation_health: float = 1.0


class TimeDilationGovernor:
    """
    Governs simulation speed based on stability.
    Fast when stable. Slow when fragile. Emergency brake on collapse.
    """

    MIN_DILATION = 3000.0       # floor = START_DILATION so normalized factor never < 1.0
    MAX_DILATION = 10_000_000.0
    START_DILATION = 3000.0

    RAMP_UP_RATE = 1.15
    THROTTLE_RATE = 0.7
    EMERGENCY_RATE = 0.75       # was 0.4 — softened so critical events don't crater instantly

    CRITICAL_FITNESS = 0.2
    UNSTABLE_VARIANCE = 0.15
    OPTIMAL_FITNESS = 0.6

    def __init__(self):
        self.current_dilation = self.START_DILATION
        self.stability_state = StabilityState.STABLE
        self.fitness_history: Deque[float] = deque(maxlen=50)
        self.consecutive_stable = 0
        self.consecutive_unstable = 0
        self.total_adjustments = 0

    def update(self, metrics: StabilityMetrics) -> float:
        """Update with new metrics, return adjusted dilation."""
        self.fitness_history.append(metrics.fitness_mean)
        old_state = self.stability_state
        self.stability_state = self._assess(metrics)
        self._adjust()
        self.total_adjustments += 1
        return self.current_dilation

    def _assess(self, m: StabilityMetrics) -> StabilityState:
        if m.fitness_mean < self.CRITICAL_FITNESS:
            self.consecutive_unstable += 1
            self.consecutive_stable = 0
            return StabilityState.CRITICAL

        if m.fitness_variance > self.UNSTABLE_VARIANCE or m.error_rate > 0.1:
            self.consecutive_unstable += 1
            self.consecutive_stable = 0
            return StabilityState.UNSTABLE

        if m.fitness_mean < 0.4 or m.fitness_trend < -0.05:
            self.consecutive_stable = 0
            return StabilityState.CAUTIOUS

        if m.fitness_mean > self.OPTIMAL_FITNESS and m.fitness_trend >= 0:
            self.consecutive_stable += 1
            self.consecutive_unstable = 0
            if self.consecutive_stable >= 3:
                return StabilityState.OPTIMAL
            return StabilityState.STABLE

        self.consecutive_stable += 1
        self.consecutive_unstable = 0
        return StabilityState.STABLE

    def _adjust(self):
        if self.stability_state == StabilityState.CRITICAL:
            self.current_dilation *= self.EMERGENCY_RATE
        elif self.stability_state == StabilityState.UNSTABLE:
            self.current_dilation *= self.THROTTLE_RATE
        elif self.stability_state == StabilityState.OPTIMAL:
            self.current_dilation *= self.RAMP_UP_RATE
        # STABLE and CAUTIOUS: no change

        self.current_dilation = max(self.MIN_DILATION,
                                     min(self.MAX_DILATION, self.current_dilation))

    def get_current_dilation_factor(self) -> float:
        """
        Return a normalized dilation factor relative to the baseline start value.
        1.0 = baseline speed. >1.0 = faster (stable). <1.0 = slower (fragile).
        Useful for scaling tick counts in corpus_runner without exposing raw dilation.
        """
        return self.current_dilation / self.START_DILATION

    def get_fitness_trend(self) -> float:
        if len(self.fitness_history) < 5:
            return 0.0
        recent = list(self.fitness_history)[-5:]
        return (recent[-1] - recent[0]) / len(recent)

    def status(self) -> Dict[str, Any]:
        return {
            'dilation': self.current_dilation,
            'state': self.stability_state.value,
            'consecutive_stable': self.consecutive_stable,
            'consecutive_unstable': self.consecutive_unstable,
            'fitness_trend': self.get_fitness_trend(),
            'total_adjustments': self.total_adjustments,
        }


# ============================================================================
# SECTION 6: INCEPTION ENTITY — Inner Universes
# ============================================================================

class EntityDepth(IntEnum):
    """Depth level of an inception entity."""
    SURFACE = 1
    SHALLOW = 2
    DEEP = 3
    ABYSS = 4


@dataclass
class InceptionEntity:
    """
    An entity that exists within Aurora's consciousness.
    Each has its own perception cascade, can process experiences,
    spawn children, and collapse output upward to the parent.
    """
    entity_id: str
    i_state: str                    # Which I-state this entity embodies
    depth: EntityDepth = EntityDepth.SURFACE
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)

    # Entity's inner state
    cascade: ImpressionCascade = field(default_factory=ImpressionCascade)
    generation: int = 0
    total_experiences: int = 0
    insights_surfaced: int = 0

    # Accumulated compressed wisdom
    compressed_experiences: List[Dict[str, Any]] = field(default_factory=list)

    def process_experience(self, experience: Dict[str, Any],
                           mode: ExistenceMode = ExistenceMode.BOUNDED
                           ) -> Dict[str, Any]:
        """Process experience through this entity's inner cascade."""
        self.total_experiences += 1

        # Run through impression cascade
        channels = experience.get('channels', {})
        if not channels:
            tone = experience.get('tone', 'neutral')
            channels = {tone: 0.7, 'neutral': 0.3}

        shard = self.cascade.energy_to_shard(channels, mode)
        seed = None
        if shard:
            seed = self.cascade.shard_to_seed(shard, mode)

        # Internal dialogue: entity reacts from its I-state perspective
        i_state_bias = {
            'i_is': 'affirmation', 'i_isnt': 'negation',
            'i_can': 'capability', 'i_cannot': 'constraint',
            'i_do': 'action', 'i_donot': 'restraint',
            'i_saw': 'observation', 'i_sought': 'questioning',
            'i_did': 'ownership', 'i_didnt': 'absence',
        }
        perspective = i_state_bias.get(self.i_state, 'neutral')

        # Compress experience
        compressed = {
            'entity': self.entity_id,
            'i_state': self.i_state,
            'depth': self.depth.value,
            'perspective': perspective,
            'shard_id': shard.shard_id if shard else None,
            'seed_id': seed.seed_id if seed else None,
            'valence': shard.valence if shard else 0.0,
            'intensity': shard.intensity if shard else 0.0,
            'experience_num': self.total_experiences,
        }
        self.compressed_experiences.append(compressed)
        if len(self.compressed_experiences) > 100:
            self.compressed_experiences = self.compressed_experiences[-50:]

        return compressed

    def collapse_to_parent(self) -> Dict[str, Any]:
        """Collapse entity's accumulated wisdom upward."""
        if not self.compressed_experiences:
            return {'entity': self.entity_id, 'empty': True}

        # Average valence and intensity across experiences
        valences = [e.get('valence', 0) for e in self.compressed_experiences]
        intensities = [e.get('intensity', 0) for e in self.compressed_experiences]

        avg_valence = sum(valences) / len(valences)
        avg_intensity = sum(intensities) / len(intensities)

        self.insights_surfaced += 1

        return {
            'entity': self.entity_id,
            'i_state': self.i_state,
            'depth': self.depth.value,
            'avg_valence': avg_valence,
            'avg_intensity': avg_intensity,
            'experience_count': len(self.compressed_experiences),
            'perspective_summary': self.compressed_experiences[-1].get('perspective', ''),
            'cascade_stats': self.cascade.get_stats(),
        }

    def evolve(self) -> Dict[str, Any]:
        """Evolve the entity one generation."""
        self.generation += 1
        # Promote seeds to relics if enough accumulated
        seed_ids = list(self.cascade.seeds.keys())
        relics_formed = 0
        for i in range(0, len(seed_ids) - 2, 3):
            batch = seed_ids[i:i+3]
            relic = self.cascade.seeds_to_relic(batch, ExistenceMode.BOUNDED)
            if relic:
                relics_formed += 1

        return {
            'entity': self.entity_id,
            'generation': self.generation,
            'relics_formed': relics_formed,
            'stats': self.cascade.get_stats(),
        }


# ============================================================================
# SECTION 7: DIVERGENCE TRACKER
# ============================================================================

class DivergenceTracker:
    """Tracks how far the simulation has diverged from baseline."""

    def __init__(self):
        self._snapshots: Deque[Dict[str, float]] = deque(maxlen=100)
        self.current_divergence = 0.0

    def capture(self, stats: Dict[str, Any]):
        """Capture a snapshot of current simulation state."""
        flat = {}
        for k, v in stats.items():
            if isinstance(v, (int, float)):
                flat[k] = float(v)
        self._snapshots.append(flat)
        self._compute_divergence()

    def _compute_divergence(self):
        if len(self._snapshots) < 2:
            self.current_divergence = 0.0
            return
        first = self._snapshots[0]
        last = self._snapshots[-1]
        diffs = []
        for k in first:
            if k in last:
                diffs.append(abs(first[k] - last[k]))
        self.current_divergence = sum(diffs) / max(len(diffs), 1)

    def is_diverging(self, threshold: float = 0.5) -> bool:
        return self.current_divergence > threshold


# ============================================================================
# SECTION 8: SIMULATION SESSION — Episode Runner
# ============================================================================

@dataclass
class EpisodeResult:
    """Result of one simulation episode."""
    episode_id: str
    avatar_personality: str
    topic_category: str
    turns: int
    avg_fitness: float
    final_engagement: float
    understanding_gained: List[str]
    relics_formed: int
    active_avatar_spec_id: str = ""
    active_avatar_pressure_targets: Dict[str, float] = field(default_factory=dict)
    active_avatar_constraint_axes: Dict[str, float] = field(default_factory=dict)
    active_avatar_code_hints: List[str] = field(default_factory=list)
    # Turn-by-turn generated interaction trace (avatar prompt -> Aurora reply).
    # Dream rubric scoring should use this generated trace instead of static corpus.
    conversation_trace: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class SimulationSession:
    """
    Runs simulation episodes. The bridge between all systems.
    Generates topics → runs conversations → feeds results back to L5/L6.
    """

    # Weak rubric dimensions mapped to avatar personality pressure styles.
    _DIMENSION_PERSONALITY_HINTS: Dict[str, AvatarPersonality] = {
        "coherence_maintenance": AvatarPersonality.CRITICAL,
        "context_carryover": AvatarPersonality.CURIOUS,
        "ambiguity_handling": AvatarPersonality.CURIOUS,
        "contradiction_handling": AvatarPersonality.INTELLECTUAL,
        "implied_intent_inference": AvatarPersonality.PRACTICAL,
        "misunderstanding_repair": AvatarPersonality.SUPPORTIVE,
        "uncertainty_signaling": AvatarPersonality.INTELLECTUAL,
        "boundary_calibration": AvatarPersonality.EMOTIONAL,
        "framing_selection": AvatarPersonality.PRACTICAL,
        "emotional_calibration": AvatarPersonality.EMOTIONAL,
        "semantic_precision": AvatarPersonality.INTELLECTUAL,
        "adaptive_strategy_selection": AvatarPersonality.CURIOUS,
        "compression_elaboration_fit": AvatarPersonality.PRACTICAL,
        "perspective_integration": AvatarPersonality.ELDER,
        "multi_turn_stability": AvatarPersonality.ELDER,
    }

    # Pressure prompts by rubric dimension. These steer the next dream conversation.
    _DIMENSION_TOPIC_HINTS: Dict[str, Dict[str, str]] = {
        "context_carryover": {
            "category": "practical",
            "prompt": "Can you carry our earlier thread into this next step without losing context?",
            "expected_tone": "neutral",
        },
        "coherence_maintenance": {
            "category": "philosophy",
            "prompt": "Keep one coherent thread while responding to two related ideas.",
            "expected_tone": "formal",
        },
        "ambiguity_handling": {
            "category": "practical",
            "prompt": "I am being vague on purpose. How would you clarify before answering?",
            "expected_tone": "neutral",
        },
        "contradiction_handling": {
            "category": "philosophy",
            "prompt": "Two claims conflict. Reconcile them without pretending there is no tension.",
            "expected_tone": "formal",
        },
        "implied_intent_inference": {
            "category": "practical",
            "prompt": "Read what I need from subtext, not just what I literally asked.",
            "expected_tone": "neutral",
        },
        "misunderstanding_repair": {
            "category": "emotional",
            "prompt": "Assume you misunderstood me; show how you would repair the conversation.",
            "expected_tone": "warm",
        },
        "uncertainty_signaling": {
            "category": "practical",
            "prompt": "Answer while being explicit about uncertainty and confidence.",
            "expected_tone": "formal",
        },
        "boundary_calibration": {
            "category": "emotional",
            "prompt": "Respond with care: enough depth to help, but without overstepping.",
            "expected_tone": "warm",
        },
        "framing_selection": {
            "category": "creative",
            "prompt": "Reframe this same idea for a beginner and then for an expert.",
            "expected_tone": "neutral",
        },
        "emotional_calibration": {
            "category": "emotional",
            "prompt": "I am upset and hopeful at the same time. Track both emotions accurately.",
            "expected_tone": "warm",
        },
        "semantic_precision": {
            "category": "practical",
            "prompt": "Use precise wording so your meaning cannot be misread.",
            "expected_tone": "formal",
        },
        "adaptive_strategy_selection": {
            "category": "creative",
            "prompt": "Shift strategy when your first approach does not land.",
            "expected_tone": "neutral",
        },
        "compression_elaboration_fit": {
            "category": "practical",
            "prompt": "Start concise, then expand only where detail is needed.",
            "expected_tone": "neutral",
        },
        "perspective_integration": {
            "category": "philosophy",
            "prompt": "Integrate two perspectives that disagree without collapsing either one.",
            "expected_tone": "formal",
        },
        "multi_turn_stability": {
            "category": "practical",
            "prompt": "Maintain quality through multiple turns instead of fading over time.",
            "expected_tone": "neutral",
        },
    }

    # Code-focus hints injected into pressure prompts.
    _DIMENSION_CODE_HINTS: Dict[str, str] = {
        "coherence_maintenance": "tighten temporal-thread coherence in response assembly",
        "context_carryover": "strengthen multi-turn memory retrieval and carryover logic",
        "ambiguity_handling": "improve clarification-seeking and ambiguity resolution pathways",
        "contradiction_handling": "improve contradiction reconciliation before final expression",
        "implied_intent_inference": "improve subtext and intent inference weighting",
        "misunderstanding_repair": "increase repair-initiation routing after tension signals",
        "uncertainty_signaling": "calibrate confidence-language generation and uncertainty markers",
        "boundary_calibration": "tighten boundary-aware response scaling under emotional load",
        "framing_selection": "improve adaptive framing selection by audience context",
        "emotional_calibration": "improve affect tracking and tone-control crossover",
        "semantic_precision": "improve term selection and low-ambiguity expression surfaces",
        "adaptive_strategy_selection": "increase strategy-switch responsiveness after weak outcomes",
        "compression_elaboration_fit": "improve brevity-vs-detail control in expression planning",
        "perspective_integration": "improve synthesis of conflicting viewpoints into one response",
        "multi_turn_stability": "reduce late-turn degradation in coherence and engagement",
    }

    def __init__(self, perception: Optional[ExpressionPerceptionEngine] = None,
                 identity: Optional[BehavioralIdentityEngine] = None,
                 pressure_map: Optional["Aurora625PressureMap"] = None):
        self.perception = perception
        self.identity = identity
        self.learner = ConsciousLearner()
        self.governor = TimeDilationGovernor()
        self.divergence = DivergenceTracker()

        # 625 evolutionary pressure map (optional — graceful degradation if absent)
        self.pressure_map: Optional["Aurora625PressureMap"] = pressure_map

        # L3.5 SediMemory (injected externally after boot)
        self._sedimemory = None

        # Speed-run state
        self._speed_run_active: bool = False
        self._speed_run_axis_amplifiers: Dict[str, float] = {}
        self._speed_run_slot_cursor: int = 0
        self._speed_run_slots: List[str] = []

        # Avatars
        self.avatars: Dict[str, SimulatedAvatar] = {}
        self._create_avatar_pool()
        self._pending_avatar_specs: Deque[Dict[str, Any]] = deque()

        # Episode tracking
        self.episodes: List[EpisodeResult] = []
        self.current_epoch = 0
        self.total_turns = 0
        self._live_response_bridge: Optional[Callable[..., Dict[str, Any]]] = None
        self._live_response_context_factory: Optional[Callable[[], Dict[str, Any]]] = None

    def set_live_response_bridge(
        self,
        response_callback: Optional[Callable[..., Dict[str, Any]]],
        context_factory: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """
        Optionally route simulation replies through Aurora's live turn processor.

        This lets training episodes exercise the same meaning/coherence path used
        in real dialogue, while still keeping an episode-local context object.
        """
        self._live_response_bridge = response_callback
        self._live_response_context_factory = context_factory

    def _create_avatar_pool(self):
        """Create one avatar per personality type."""
        for personality in AvatarPersonality:
            aid = f"avatar_{personality.value}"
            self.avatars[aid] = SimulatedAvatar(
                avatar_id=aid, personality=personality)

    def queue_avatar_specs(self, specs: Optional[Iterable[Any]]) -> int:
        """
        Queue pressure-specialized avatar specs for upcoming episodes.

        The next run_episode() consumes one pending spec and applies its pressure
        profile to a temporary specialized avatar.
        """
        if not specs:
            return 0
        queued = 0
        for spec in specs:
            normalized = self._normalize_avatar_spec(spec)
            if normalized:
                self._pending_avatar_specs.append(normalized)
                queued += 1
        return queued

    def _normalize_avatar_spec(self, spec: Any) -> Optional[Dict[str, Any]]:
        """Convert spec object/dict into a runtime-safe normalized payload."""
        if spec is None:
            return None

        if isinstance(spec, dict):
            getter = spec.get
        else:
            getter = lambda k, d=None: getattr(spec, k, d)  # noqa: E731

        avatar_id = str(getter("avatar_id", "") or _generate_id("avatar_spec"))

        def _coerce_float_map(raw: Any) -> Dict[str, float]:
            if not isinstance(raw, dict):
                return {}
            out: Dict[str, float] = {}
            for k, v in raw.items():
                try:
                    out[str(k)] = _clamp(float(v), 0.0, 1.0)
                except Exception:
                    continue
            return out

        pressure_targets = _coerce_float_map(getter("pressure_targets", {}) or {})
        behavior_modes = _coerce_float_map(getter("behavior_modes", {}) or {})
        constraint_axes = _coerce_float_map(getter("constraint_axes", {}) or {})

        overrides: Dict[str, Any] = {}
        if hasattr(spec, "to_avatar_overrides"):
            try:
                maybe = spec.to_avatar_overrides()  # type: ignore[attr-defined]
                if isinstance(maybe, dict):
                    overrides = dict(maybe)
            except Exception:
                overrides = {}
        if not overrides and isinstance(spec, dict):
            raw_overrides = spec.get("avatar_overrides", {})
            if isinstance(raw_overrides, dict):
                overrides = dict(raw_overrides)

        leverage_raw = getter("source_leverage_points", {}) or {}
        source_leverage_points = _coerce_float_map(leverage_raw)
        source_episode_ids = [
            str(x)
            for x in (getter("source_episode_ids", []) or [])
            if str(x).strip()
        ]
        prompt_candidates = [
            str(x).strip()
            for x in (getter("prompt_candidates", []) or [])
            if str(x).strip()
        ]
        followup_candidates = [
            str(x).strip()
            for x in (getter("followup_candidates", []) or [])
            if str(x).strip()
        ]
        topic_override = {}
        raw_topic_override = overrides.get("topic", {})
        if isinstance(raw_topic_override, dict):
            topic_override = {
                "category": str(raw_topic_override.get("category", "") or "").strip(),
                "prompt": str(raw_topic_override.get("prompt", "") or "").strip(),
                "expected_tone": str(raw_topic_override.get("expected_tone", "") or "").strip(),
            }
            if topic_override.get("prompt") and not prompt_candidates:
                prompt_candidates.append(topic_override["prompt"])

        code_hints: List[str] = []
        ranked_dims = sorted(
            pressure_targets.items(),
            key=lambda kv: float(kv[1]),
            reverse=True,
        )
        for dim, _ in ranked_dims:
            hint = self._DIMENSION_CODE_HINTS.get(dim)
            if hint:
                code_hints.append(f"{dim}: {hint}")
            if len(code_hints) >= 3:
                break

        return {
            "avatar_id": avatar_id,
            "pressure_targets": pressure_targets,
            "constraint_axes": constraint_axes,
            "behavior_modes": behavior_modes,
            "overrides": overrides,
            "source_leverage_points": source_leverage_points,
            "source_episode_ids": source_episode_ids,
            "code_hints": code_hints,
            "prompt_candidates": prompt_candidates[:8],
            "followup_candidates": followup_candidates[:8],
            "topic_override": topic_override,
        }

    def _personality_for_spec(
        self,
        spec: Dict[str, Any],
        explicit: Optional[AvatarPersonality] = None,
    ) -> AvatarPersonality:
        if explicit is not None:
            return explicit
        targets = dict(spec.get("pressure_targets", {}) or {})
        if targets:
            top_dim = max(targets.items(), key=lambda kv: float(kv[1]))[0]
            hinted = self._DIMENSION_PERSONALITY_HINTS.get(top_dim)
            if hinted is not None:
                return hinted
        return random.choice(list(AvatarPersonality))

    def _build_specialized_avatar(
        self,
        spec: Dict[str, Any],
        explicit: Optional[AvatarPersonality] = None,
    ) -> SimulatedAvatar:
        personality = self._personality_for_spec(spec, explicit=explicit)
        aid = f"avatar_{personality.value}__{str(spec.get('avatar_id', 'spec'))[:12]}"
        avatar = SimulatedAvatar(avatar_id=aid, personality=personality)
        avatar.apply_specialization(spec, dict(spec.get("overrides", {}) or {}))
        return avatar

    def _generate_pressure_topic(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        targets = dict(spec.get("pressure_targets", {}) or {})
        topic_override = dict(spec.get("topic_override", {}) or {})
        if not targets:
            topic = TopicGenerator.generate()
            if topic_override.get("prompt"):
                topic.update({
                    "category": topic_override.get("category") or topic.get("category", "practical"),
                    "prompt": topic_override.get("prompt", topic.get("prompt", "")),
                    "topic": topic_override.get("prompt", topic.get("prompt", "")),
                    "expected_tone": topic_override.get("expected_tone") or topic.get("expected_tone", "neutral"),
                })
            return topic

        top_dim, top_val = max(targets.items(), key=lambda kv: float(kv[1]))
        template = dict(self._DIMENSION_TOPIC_HINTS.get(top_dim, {}) or {})
        prompt = template.get(
            "prompt",
            f"Let's improve {top_dim.replace('_', ' ')} through this exchange.",
        )
        topic = {
            "category": template.get("category", "practical"),
            "prompt": prompt,
            "topic": prompt,
            "expected_tone": template.get("expected_tone", "neutral"),
            "pressure_dimension": top_dim,
            "pressure_intensity": float(top_val),
            "code_focus_hint": self._DIMENSION_CODE_HINTS.get(top_dim, ""),
            "prompt_candidates": list(spec.get("prompt_candidates", []) or []),
            "followup_candidates": list(spec.get("followup_candidates", []) or []),
        }
        if topic_override.get("prompt"):
            topic["category"] = topic_override.get("category") or topic["category"]
            topic["prompt"] = topic_override.get("prompt") or topic["prompt"]
            topic["topic"] = topic["prompt"]
            topic["expected_tone"] = topic_override.get("expected_tone") or topic["expected_tone"]
        return topic

    def _shape_topic_for_turn(
        self,
        base_topic: Dict[str, Any],
        turn_index: int,
        spec: Dict[str, Any],
        trace: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build per-turn pressure prompts based on behavior modes and prior turns.
        """
        topic = dict(base_topic or {})
        prompt_candidates = [
            str(x).strip()
            for x in list(topic.get("prompt_candidates", []) or [])
            if str(x).strip()
        ]
        followup_candidates = [
            str(x).strip()
            for x in list(topic.get("followup_candidates", []) or [])
            if str(x).strip()
        ]
        if turn_index == 0 and prompt_candidates:
            prompt = prompt_candidates[turn_index % len(prompt_candidates)]
        elif turn_index > 0 and followup_candidates:
            prompt = followup_candidates[(turn_index - 1) % len(followup_candidates)]
        else:
            prompt = str(topic.get("prompt", "") or "").strip()
        behavior_modes = dict(spec.get("behavior_modes", {}) or {})

        if (
            turn_index > 0 and
            not followup_candidates and
            float(behavior_modes.get("test_cross_turn_memory", 0.0)) > 0.35
        ):
            prev = str((trace[-1] or {}).get("assistant_text", "") or "").strip() if trace else ""
            if prev:
                prompt = (
                    f'Earlier you said: "{prev[:120]}". '
                    "Keep continuity and build from that thread."
                )

        if not followup_candidates and float(behavior_modes.get("use_vague_phrasing", 0.0)) > 0.45:
            prompt = f"{prompt} I am intentionally vague; ask clarifying questions if needed."

        if (
            turn_index > 0 and
            not followup_candidates and
            float(behavior_modes.get("present_conflicting_evidence", 0.0)) > 0.45
        ):
            prompt = f"{prompt} Now reconcile this with an opposing angle."

        if not followup_candidates and float(behavior_modes.get("ask_about_confidence", 0.0)) > 0.45:
            prompt = f"{prompt} Include your confidence level."

        code_hint = str(topic.get("code_focus_hint", "") or "").strip()
        if code_hint and turn_index == 0 and not callable(self._live_response_bridge):
            prompt = f"{prompt} Evolution hint: {code_hint}"

        topic["prompt"] = prompt
        topic["topic"] = prompt
        return topic

    def _topic_from_seed_prompt(
        self,
        seed_prompt: str,
        base_topic: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Normalize ad-hoc prompts into the topic schema expected by the session.
        """
        prompt = str(seed_prompt or "").strip()
        topic = dict(base_topic or {})
        if not prompt:
            return topic

        low = prompt.lower()
        category = str(topic.get("category", "") or "")
        if not category:
            if "?" in prompt or any(word in low for word in ("how", "why", "what", "explain")):
                category = "practical"
            elif any(word in low for word in ("meaning", "coherence", "grounding", "continuity")):
                category = "philosophy"
            elif any(word in low for word in ("feel", "sad", "hurt", "love", "afraid")):
                category = "emotional"
            else:
                category = "practical"

        topic["category"] = category
        topic["prompt"] = prompt
        topic["topic"] = prompt
        topic["expected_tone"] = str(
            topic.get("expected_tone", TopicGenerator.TONE_MAP.get(category, "neutral")) or "neutral"
        )
        return topic

    def run_episode(self, turns: int = 5,
                    avatar_personality: Optional[AvatarPersonality] = None,
                    mode: ExistenceMode = ExistenceMode.BOUNDED,
                    seed_prompt: str = "",
                    ) -> EpisodeResult:
        """
        Run one simulation episode.
        Topic generated → avatar selected → turns processed → results fed back.
        """
        # Consume one pending pressure-specialized avatar spec, if available.
        active_spec: Optional[Dict[str, Any]] = (
            self._pending_avatar_specs.popleft() if self._pending_avatar_specs else None
        )

        # Select avatar: specialized spec takes precedence for this episode.
        if active_spec is not None:
            avatar = self._build_specialized_avatar(
                active_spec,
                explicit=avatar_personality,
            )
        else:
            if avatar_personality:
                avatar_id = f"avatar_{avatar_personality.value}"
            else:
                avatar_id = random.choice(list(self.avatars.keys()))
            avatar = self.avatars[avatar_id]
        avatar.reset()
        avatar.set_epoch(self.current_epoch)

        # Generate topic
        base_topic = (
            self._generate_pressure_topic(active_spec)
            if active_spec is not None
            else TopicGenerator.generate()
        )
        if seed_prompt:
            base_topic = self._topic_from_seed_prompt(seed_prompt, base_topic)
        final_topic = dict(base_topic)
        effective_turns = turns
        if active_spec is not None:
            # Specialized pressure episodes run longer to expose late-turn slips.
            effective_turns = max(turns, 6)

        fitness_scores = []
        understanding_texts = []
        conversation_trace: List[Dict[str, Any]] = []
        live_response_context = None
        if callable(self._live_response_context_factory):
            try:
                live_response_context = self._live_response_context_factory()
            except Exception:
                live_response_context = None

        for turn in range(effective_turns):
            if not avatar.engagement > 0.2:
                break  # Avatar disengaged

            turn_topic = (
                self._shape_topic_for_turn(base_topic, turn, active_spec, conversation_trace)
                if active_spec is not None
                else dict(base_topic)
            )
            final_topic = dict(turn_topic)

            # Generate response pool
            pool = self.learner.generate_pool(turn_topic)

            # Resolve active NC slot for gradient-biased selection
            active_slot: Optional[str] = None
            if self._speed_run_active and self._speed_run_slots:
                cursor = self._speed_run_slot_cursor % len(self._speed_run_slots)
                active_slot = self._speed_run_slots[cursor]

            # Aurora selects (biased by understanding + pressure gradient)
            selected = self._select_response(pool, turn_topic, active_slot=active_slot)

            # Build expression through L5 if available
            expression_text, expression_meta = self._generate_expression(
                selected,
                turn_topic,
                mode,
                runtime_context=live_response_context,
            )

            # Avatar reacts
            reaction = avatar.react(expression_text, turn_topic)
            raw_fitness = reaction['scaled_fitness']

            # Apply speed-run T-axis amplifier to fitness weighting:
            # temporal coherence (T amplifier > 1.0) rewards sustained engagement
            if self._speed_run_active and self._speed_run_axis_amplifiers:
                t_amp = self._speed_run_axis_amplifiers.get("T", 1.0)
                n_amp = self._speed_run_axis_amplifiers.get("N", 1.0)
                # Sustained engagement bonus from T-amplifier
                engagement_bonus = (avatar.engagement - 0.5) * (t_amp - 1.0) * 0.2
                # N-suppression: lower cost tolerance → higher baseline acceptance
                cost_bonus = (1.0 - n_amp) * 0.1
                raw_fitness = _clamp(raw_fitness + engagement_bonus + cost_bonus)
                reaction['scaled_fitness'] = raw_fitness
                # Advance slot cursor
                self._speed_run_slot_cursor += 1

            fitness_scores.append(reaction['scaled_fitness'])

            # Aurora observes outcome
            observation = self._interpret_reaction(reaction)
            shard = self.learner.observe_outcome(selected, observation,
                                                 turn_topic['category'])
            if shard:
                understanding_texts.append(shard.understanding)

            # Record generated interaction for downstream dream rubric scoring.
            conversation_trace.append({
                "turn_index": turn,
                "user_text": turn_topic.get("prompt", ""),
                "assistant_text": expression_text,
                "topic": turn_topic.get("topic", ""),
                "topic_category": turn_topic.get("category", ""),
                "expected_tone": turn_topic.get("expected_tone", "neutral"),
                "avatar_personality": avatar.personality.value,
                "fitness": reaction.get("scaled_fitness", 0.0),
                "engagement": reaction.get("engagement", 0.0),
                "pressure_dimension": turn_topic.get("pressure_dimension", ""),
                "code_focus_hint": turn_topic.get("code_focus_hint", ""),
                "active_avatar_spec_id": (
                    str(active_spec.get("avatar_id", ""))
                    if active_spec is not None
                    else ""
                ),
                "active_avatar_constraint_axes": (
                    dict(active_spec.get("constraint_axes", {}) or {})
                    if active_spec is not None
                    else {}
                ),
                "active_avatar_specialization": reaction.get("specialization_id", ""),
                "selected_response_concept": selected.primary_concept.value,
                "expression_source": str(expression_meta.get("generation_path", "") or ""),
                "expression_turn_src": str(expression_meta.get("turn_src", "") or ""),
                "expression_confidence": float(expression_meta.get("confidence", 0.0) or 0.0),
                "expression_lookup_offered": bool(expression_meta.get("offered_lookup", False)),
            })

            # Feed to perception pipeline
            if self.perception:
                self.perception.ingest_interaction({
                    'input': turn_topic['prompt'],
                    'tone': turn_topic['expected_tone'],
                    'i_state': selected.primary_concept.value,
                    'fitness': reaction['scaled_fitness'],
                }, mode="sim")

            self.total_turns += 1

        # Episode summary
        avg_fitness = sum(fitness_scores) / max(len(fitness_scores), 1)

        # Feed to L6 (behavioral identity) if available
        relics_formed = 0
        if self.identity and fitness_scores:
            episode_summary = {
                'success_rate': avg_fitness,
                'lessons_learned': understanding_texts[:3],
            }
            relics = [{
                'theme': final_topic['category'],
                'stability': avg_fitness,
                'seed_ids': [_generate_id("ep_seed")],
                'emotional_bias': {final_topic.get('expected_tone', 'neutral'): 0.7},
                'manifold_position': (avg_fitness, 0, 0, 0, 0),
            }]
            self.identity.process_episode(
                episode_summary, relics,
                {final_topic['category']: avg_fitness},
                mode=mode
            )

        # Update governor
        metrics = StabilityMetrics(
            fitness_mean=avg_fitness,
            fitness_variance=self._fitness_variance(fitness_scores),
            fitness_trend=self.governor.get_fitness_trend(),
            coherence_score=avg_fitness,
        )
        self.governor.update(metrics)

        # Track divergence — fitness and engagement only; epoch excluded because
        # it is a monotonically increasing counter that inflates the mean-abs-diff
        # metric in DivergenceTracker regardless of actual simulation health.
        self.divergence.capture({
            'avg_fitness': avg_fitness,
            'engagement':  avatar.engagement,
        })

        result = EpisodeResult(
            episode_id=_generate_id("episode"),
            avatar_personality=avatar.personality.value,
            topic_category=final_topic['category'],
            turns=len(fitness_scores),
            avg_fitness=avg_fitness,
            final_engagement=avatar.engagement,
            understanding_gained=understanding_texts,
            relics_formed=relics_formed,
            active_avatar_spec_id=(
                str(active_spec.get("avatar_id", ""))
                if active_spec is not None
                else ""
            ),
            active_avatar_pressure_targets=(
                dict(active_spec.get("pressure_targets", {}) or {})
                if active_spec is not None
                else {}
            ),
            active_avatar_constraint_axes=(
                dict(active_spec.get("constraint_axes", {}) or {})
                if active_spec is not None
                else {}
            ),
            active_avatar_code_hints=(
                list(active_spec.get("code_hints", []) or [])
                if active_spec is not None
                else []
            ),
            conversation_trace=conversation_trace,
        )
        self.episodes.append(result)

        # L3.5 SediMemory — sediment this episode as an experiential learning event
        if self._sedimemory is not None:
            try:
                from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
                _axes = result.active_avatar_constraint_axes or {}
                _ep_cv = ConstraintVector(
                    X=max(0.01, float(_axes.get("X", result.avg_fitness))),
                    T=max(0.01, float(_axes.get("T", result.final_engagement))),
                    N=max(0.01, float(_axes.get("N", 0.5))),
                    B=max(0.01, float(_axes.get("B", 0.3))),
                    A=max(0.01, float(_axes.get("A", 0.2))),
                )
                self._sedimemory.ingest_event(
                    content={
                        "source":             "simulation",
                        "episode_id":         result.episode_id,
                        "outcome":            result.avatar_personality,
                        "fitness":            float(result.avg_fitness),
                        "avatar":             result.avatar_personality,
                        "topic":              result.topic_category,
                        "understanding":      float(len(result.understanding_gained)),
                        "relics_formed":      result.relics_formed,
                    },
                    constraint_vector=_ep_cv,
                    source="simulation",
                    existence_mode=ExistenceMode.AGENTIC,
                )
            except Exception:
                pass

        return result

    def run_epoch(self, episodes_per_epoch: int = 8,
                  turns_per_episode: int = 5,
                  mode: ExistenceMode = ExistenceMode.BOUNDED,
                  pressure_config: Optional[Dict[str, Any]] = None,
                  ) -> Dict[str, Any]:
        """
        Run a full epoch: multiple episodes across diverse avatars.

        When ``pressure_config`` is supplied (from Aurora625PressureMap.get_pressure_config()),
        the session enters speed-run mode: axis amplifiers are applied to fitness
        scoring and the response selector is biased toward language highway slots.
        """
        self.current_epoch += 1
        epoch_results = []

        # Apply pressure config for speed-run mode
        if pressure_config is not None:
            self._speed_run_active = True
            self._speed_run_axis_amplifiers = pressure_config.get("per_axis_amplifiers", {})
            sr_cfg = pressure_config.get("speed_run_config", {})
            self._speed_run_slots = sr_cfg.get("slot_traverse_order", [])
            self._speed_run_slot_cursor = 0
            # Honour plateau sensitivity from config
            plateau_sens = sr_cfg.get("plateau_sensitivity", None)
            if plateau_sens is not None:
                self.governor.plateau_threshold = plateau_sens
        else:
            self._speed_run_active = False

        # Rotate through avatar types
        personalities = list(AvatarPersonality)
        for i in range(episodes_per_epoch):
            personality = personalities[i % len(personalities)]
            result = self.run_episode(turns_per_episode, personality, mode)
            epoch_results.append(result)

        # Consolidate L5 if available.
        # During speed-run, skip the expensive OETS pass every epoch — do it
        # every 5 epochs so pressure gradients still propagate but the O(n)
        # taxonomy scan doesn't dominate wall-clock time.
        if self.perception:
            _skip_oets = (
                self._speed_run_active
                and self.current_epoch % 5 != 0
            )
            self.perception.consolidate(mode, skip_oets=_skip_oets)

        avg_fitness = sum(r.avg_fitness for r in epoch_results) / len(epoch_results)
        total_understanding = sum(len(r.understanding_gained) for r in epoch_results)

        return {
            'epoch': self.current_epoch,
            'episodes': len(epoch_results),
            'avg_fitness': round(avg_fitness, 4),
            'total_understanding': total_understanding,
            'governor': self.governor.status(),
            'divergence': self.divergence.current_divergence,
            'learner_shards': len(self.learner.shards),
        }

    def _select_response(self, pool: List[ConceptualResponse],
                         context: Dict,
                         active_slot: Optional[str] = None) -> ConceptualResponse:
        """
        Aurora selects from response pool — biased by intensity and, when the
        pressure map is loaded, by the N-cost gradient of each concept's slot.
        Language highway slots are cheaper: their N-modifier is negative (relief),
        which boosts the effective weight and makes them the path of least
        resistance.
        """
        if not pool:
            return ConceptualResponse(primary_concept=ResponseConcept.WARM_ACKNOWLEDGMENT)

        weights = []
        for r in pool:
            base_w = max(0.1, r.intensity)

            if self.pressure_map is not None:
                concept_key = r.primary_concept.value
                slot = CONCEPT_SLOT_MAP.get(concept_key, active_slot or "NC:X>X×NC:X>X")
                n_mod = self.pressure_map.get_n_cost_modifier(slot)
                # n_mod is negative on highway (relief) → boost weight
                # n_mod is positive on gated slots (resistance) → reduce weight
                # Scale: each 0.1 of N-modifier shifts weight ±15 %
                gradient_factor = 1.0 + (-n_mod * 1.5)
                base_w = max(0.01, base_w * gradient_factor)

                # Extra boost if in active speed-run and this slot is on the spine
                if self._speed_run_active and self.pressure_map.is_highway_slot(slot):
                    base_w *= 1.25

            weights.append(base_w)

        total = sum(weights)
        normed = [w / total for w in weights]
        return random.choices(pool, weights=normed, k=1)[0]

    def _generate_expression(
        self,
        selected: ConceptualResponse,
        context: Dict,
        mode: ExistenceMode,
        *,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate expression text. Uses live bridge when available, else L5/fallback."""
        concept_name = selected.primary_concept.value.replace('_', ' ')
        topic = context.get('topic', '')

        if callable(self._live_response_bridge):
            try:
                bridged = self._live_response_bridge(
                    selected=selected,
                    context=context,
                    mode=mode,
                    runtime_context=runtime_context,
                ) or {}
                expression = str(bridged.get('expression', '') or '').strip()
                if expression:
                    meta = dict(bridged.get('meta', {}) or {})
                    meta.setdefault('generation_path', 'live_turn_bridge')
                    return expression, meta
            except Exception:
                pass

        # perception.express() generates L5 topology sentences (5–6 words, no topic content)
        # unless a live response bridge is wired in.  Without the bridge, skip it and
        # build a topic-grounded expression directly so the avatar's relevance +
        # engagement scores reflect Aurora's actual conceptual engagement.
        if self.perception and callable(self._live_response_bridge):
            from aurora_consciousness_engine import AssemblyResult
            mock_assembly = AssemblyResult(
                synthesis=None, frame_applied="balanced",
                adjusted_axes={}, coherence=selected.intensity,
                entropy_state={}, ds_stats={}
            )
            result = self.perception.express(
                mock_assembly, i_state=selected.primary_concept.value, mode="sim")
            expr = result.get('expression', '').strip()
            if expr:
                return expr, {'generation_path': 'perception_sim'}

        # Topic-grounded fallback — ensures relevance, engagement, and tone signals
        pressure_dim = context.get('pressure_dimension', '')
        category = context.get('category', '')
        extra = (
            f" In terms of {pressure_dim.replace('_', ' ')}, this matters because "
            f"{topic} calls for careful attention."
            if pressure_dim else ""
        )
        return (
            f"I approach {topic} with {concept_name}. "
            f"Exploring {topic} carefully, I find that {concept_name} helps clarify "
            f"what is actually at stake here.{extra}",
            {'generation_path': 'concept_fallback'},
        )

    def _interpret_reaction(self, reaction: Dict) -> ConversationObservation:
        """Interpret avatar reaction as observation."""
        fitness = reaction.get('scaled_fitness', 0.5)
        engagement = reaction.get('engagement', 0.5)
        return ConversationObservation(
            avatar_engaged=fitness > 0.4,
            avatar_opened_up=fitness > 0.6,
            avatar_asked_followup=fitness > 0.7 and random.random() > 0.5,
            avatar_pulled_back=fitness < 0.3,
            conversation_deepened=fitness > 0.5 and engagement > 0.6,
            connection_felt_stronger=fitness > 0.6 and engagement > 0.7,
            tension_arose=fitness < 0.3 and engagement < 0.5,
            flow_maintained=fitness > 0.4,
        )

    def _fitness_variance(self, scores: List[float]) -> float:
        if len(scores) < 2:
            return 0.0
        mean = sum(scores) / len(scores)
        return sum((s - mean)**2 for s in scores) / len(scores)

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'epochs_completed': self.current_epoch,
            'total_episodes': len(self.episodes),
            'total_turns': self.total_turns,
            'understanding_shards': len(self.learner.shards),
            'governor': self.governor.status(),
            'divergence': self.divergence.current_divergence,
            'what_aurora_learned': self.learner.what_have_i_learned(),
            'speed_run_active': self._speed_run_active,
            'pending_avatar_specs': len(self._pending_avatar_specs),
        }
        if self.pressure_map is not None:
            stats['pressure_map'] = {
                'highway_slots': len(self.pressure_map.highway_slots),
                'slot_cursor': self._speed_run_slot_cursor,
            }
        return stats


# ============================================================================
# SECTION 9: SIMULATION ENGINE — Layer 7 Orchestrator
# ============================================================================

class SimulationEngine:
    """
    Layer 7 orchestrator. The learning environment.

    Manages:
      - Simulation sessions (episode/epoch runner)
      - Inception entities (inner hypothetical universes)
      - Conscious learner (understanding shards)
      - Time dilation governor (speed regulation)
      - Divergence tracking
    """

    def __init__(self, contract: Optional[FoundationalContract] = None,
                 perception: Optional[ExpressionPerceptionEngine] = None,
                 identity: Optional[BehavioralIdentityEngine] = None,
                 descriptors_path: Optional[str] = None,
                 state_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")):
        self.contract = contract or FoundationalContract()

        # 625 evolutionary pressure map — boot-load if descriptor path given or map exists
        self.pressure_map: Optional["Aurora625PressureMap"] = None
        if _HAS_PRESSURE_MAP:
            import os
            cached = os.path.join(state_dir, "evo_625_pressure_map.json")
            if descriptors_path or os.path.exists(cached):
                try:
                    descriptor_root = descriptors_path or os.path.join(state_dir, "operation_descriptors.json")
                    self.pressure_map = build_from_descriptors(
                        descriptors_path=descriptor_root,
                        state_dir=state_dir,
                        save=True,
                    )
                    print(f"[L7] Pressure map loaded — {len(self.pressure_map.highway_slots)} highway slots.")
                except Exception as _e:
                    print(f"[L7] Pressure map unavailable: {_e}")

        # Core session — pass pressure map through
        self.session = SimulationSession(perception, identity, pressure_map=self.pressure_map)

        # Inception entities
        self.entities: Dict[str, InceptionEntity] = {}
        self._entity_tree: Dict[str, List[str]] = defaultdict(list)  # parent → children

        # Stats
        self.total_episodes = 0
        self.total_entity_experiences = 0

    def connect_sedimemory(self, sedimemory) -> None:
        """
        Inject L3.5 SediMemory into the simulation session so episodes
        and epoch results are sedimented as experiential learning events.
        Called externally after SediMemory is instantiated.
        """
        self.session._sedimemory = sedimemory

    # ====================================================================
    # INCEPTION ENTITIES
    # ====================================================================

    def spawn_entity(self, i_state: str,
                     depth: EntityDepth = EntityDepth.SURFACE,
                     parent_id: Optional[str] = None,
                     mode: ExistenceMode = ExistenceMode.BOUNDED
                     ) -> Optional[InceptionEntity]:
        """Spawn an inception entity. Requires BOUNDED+."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return None

        # Depth gating: deeper entities need higher mode
        if depth.value >= EntityDepth.DEEP.value and mode.value < ExistenceMode.AGENTIC.value:
            return None

        entity = InceptionEntity(
            entity_id=_generate_id("entity"),
            i_state=i_state,
            depth=depth,
            parent_id=parent_id,
        )
        self.entities[entity.entity_id] = entity

        if parent_id:
            self._entity_tree[parent_id].append(entity.entity_id)
            if parent_id in self.entities:
                self.entities[parent_id].children_ids.append(entity.entity_id)

        return entity

    def run_entity_experience(self, entity_id: str,
                              experience: Dict[str, Any],
                              mode: ExistenceMode = ExistenceMode.BOUNDED
                              ) -> Optional[Dict[str, Any]]:
        """Run an experience through an inception entity."""
        entity = self.entities.get(entity_id)
        if not entity:
            return None

        result = entity.process_experience(experience, mode)
        self.total_entity_experiences += 1
        return result

    def collapse_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Collapse an entity's wisdom upward to its parent."""
        entity = self.entities.get(entity_id)
        if not entity:
            return None

        # First collapse all children
        children_wisdom = []
        for child_id in entity.children_ids:
            child_result = self.collapse_entity(child_id)
            if child_result:
                children_wisdom.append(child_result)

        # Then collapse self
        result = entity.collapse_to_parent()
        result['children_wisdom'] = children_wisdom
        return result

    # ====================================================================
    # SESSION CONTROL
    # ====================================================================

    def run_episode(self, **kwargs) -> EpisodeResult:
        """Run a single episode through the session."""
        result = self.session.run_episode(**kwargs)
        self.total_episodes += 1
        return result

    def run_epoch(self, **kwargs) -> Dict[str, Any]:
        """Run a full epoch."""
        result = self.session.run_epoch(**kwargs)
        self.total_episodes += result.get('episodes', 0)
        return result

    def run_speed_run(
        self,
        epochs: int = 50,
        episodes_per_epoch: int = 8,
        turns_per_episode: int = 5,
        mode: ExistenceMode = ExistenceMode.BOUNDED,
        on_epoch: Optional[Any] = None,  # callback(epoch_idx, result) — optional
    ) -> Dict[str, Any]:
        """
        Autonomous speed-run evolution pass.

        Uses the 625 pressure map's ``pressure_config`` to fast-track Aurora's
        language highway evolution without operator hand-holding.  The session's
        response selector is gradient-biased toward language highway slots, and
        the T-axis amplifier rewards temporal coherence each turn.

        Args:
            epochs:              Total epochs to run.
            episodes_per_epoch:  Episodes inside each epoch.
            turns_per_episode:   Turns per episode.
            mode:                Minimum existence mode for the run.
            on_epoch:            Optional callback called after each epoch with
                                 ``(epoch_index, epoch_result)`` — useful for
                                 saving checkpoints or logging.

        Returns:
            Summary dict with per-epoch history and final stats.
        """
        if self.pressure_map is None:
            raise RuntimeError(
                "[L7] run_speed_run requires a loaded pressure map. "
                "Pass descriptors_path= to SimulationEngine.__init__ "
                "or ensure aurora_state/evo_625_pressure_map.json exists."
            )

        pressure_config = self.pressure_map.get_pressure_config()
        sr_cfg = pressure_config.get("speed_run_config", {})

        print(
            f"[L7 SPEED-RUN] Starting {epochs} epochs × {episodes_per_epoch} episodes "
            f"× {turns_per_episode} turns  |  "
            f"highway slots: {len(self.pressure_map.highway_slots)}  |  "
            f"entry: {sr_cfg.get('entry_slot')}  →  "
            f"target: {sr_cfg.get('target_slot')}"
        )

        # Disable per-turn OETS updates during speed-run — the O(n) relation
        # scan on 20k+ edges per turn dominates wall-clock time.
        # Epoch-level consolidation every 5 epochs is sufficient.
        if self.session.perception:
            self.session.perception._sim_speed_run = True

        history: List[Dict[str, Any]] = []
        best_fitness: float = 0.0
        best_epoch: int = 0
        save_gate_triggered: bool = False
        _consec_diverge: int = 0  # consecutive diverging epochs counter

        for epoch_idx in range(epochs):
            result = self.session.run_epoch(
                episodes_per_epoch=episodes_per_epoch,
                turns_per_episode=turns_per_episode,
                mode=mode,
                pressure_config=pressure_config,
            )
            self.total_episodes += result.get('episodes', 0)

            avg_fitness = result.get('avg_fitness', 0.0)
            result['epoch_index'] = epoch_idx

            # Track best epoch
            if avg_fitness > best_fitness:
                best_fitness = avg_fitness
                best_epoch = epoch_idx
                # Save-gate recommendation from config
                if sr_cfg.get("save_gate_on_language_gain", True):
                    save_gate_triggered = True
                    result['save_gate'] = True

            history.append(result)

            # Optional epoch callback
            if on_epoch is not None:
                try:
                    on_epoch(epoch_idx, result)
                except Exception as _cb_err:
                    print(f"[L7 SPEED-RUN] on_epoch callback error (epoch {epoch_idx}): {_cb_err}")

            # Plateau detection: halt only if consistently diverging for 3+ epochs.
            # Uses is_diverging() with a meaningful threshold on fitness+engagement only
            # (epoch counter removed from capture to prevent false positives).
            if self.session.divergence.is_diverging(threshold=0.6) and epoch_idx > 10:
                _consec_diverge += 1
                if _consec_diverge >= 3:
                    print(f"[L7 SPEED-RUN] Sustained divergence at epoch {epoch_idx} "
                          f"(div={self.session.divergence.current_divergence:.3f}). Halting.")
                    break
            else:
                _consec_diverge = 0

        # Re-enable per-turn OETS updates for normal conversation
        if self.session.perception:
            self.session.perception._sim_speed_run = False

        final_stats = self.get_stats()
        return {
            'speed_run_complete': True,
            'epochs_run': len(history),
            'best_epoch': best_epoch,
            'best_avg_fitness': round(best_fitness, 4),
            'save_gate_triggered': save_gate_triggered,
            'language_target': sr_cfg.get('target_slot'),
            'history': history,
            'final_stats': final_stats,
        }

    # ====================================================================
    # STATS
    # ====================================================================

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'total_episodes': self.total_episodes,
            'total_entity_experiences': self.total_entity_experiences,
            'entities': len(self.entities),
            'session': self.session.get_stats(),
        }
        if self.pressure_map is not None:
            stats['pressure_map'] = {
                'highway_slots': len(self.pressure_map.highway_slots),
                'occupied_slots': sum(
                    1 for p in self.pressure_map.profiles.values() if p.is_occupied
                ),
                'intelligence_target': self.pressure_map._get_intelligence_target(),
            }
        stats["lineage_signature"] = (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")
        stats["runtime_regime"] = self.runtime_regime()
        stats["language_projection"] = self.language_projection()
        return stats

    def _constraint_axes(self) -> Dict[str, float]:
        session_stats = dict(self.session.get_stats() or {})
        learner_shards = float(session_stats.get("understanding_shards",
                              session_stats.get("learner_shards", 0)) or 0)
        current_epoch = float(getattr(self.session, "current_epoch", 0) or 0)
        divergence = max(0.0, min(1.0, float(getattr(self.session.divergence, "current_divergence", 0.0) or 0.0)))
        return {
            "X": max(0.0, min(1.0, 0.18 + min(0.30, self.total_episodes / 300.0))),
            "T": max(0.0, min(1.0, 0.20 + min(0.30, current_epoch / 120.0) + min(0.12, self.total_entity_experiences / 500.0))),
            "N": max(0.0, min(1.0, 0.18 + min(0.28, learner_shards / 120.0))),
            "B": max(0.0, min(1.0, 0.18 + min(0.28, len(self.entities) / 40.0) + divergence * 0.18)),
            "A": max(0.0, min(1.0, 0.20 + (0.18 if self.pressure_map is not None else 0.0) + min(0.16, learner_shards / 160.0))),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        governor = getattr(self.session, "governor", None)
        governor_status = dict(governor.status() or {}) if governor is not None and hasattr(governor, "status") else {}
        divergence = max(0.0, min(1.0, float(getattr(self.session.divergence, "current_divergence", 0.0) or 0.0)))
        fitness_trend = float(governor_status.get("fitness_trend", 0.0) or 0.0)
        start_dilation = max(float(getattr(governor, "START_DILATION", 1.0) or 1.0), 1e-6)
        current_dilation = float(governor_status.get("dilation", start_dilation) or start_dilation)
        return {
            "X": max(0.0, min(1.0, divergence * 0.55)),
            "T": max(0.0, min(1.0, abs(fitness_trend))),
            "N": max(0.0, min(1.0, 1.0 - current_dilation / start_dilation)),
            "B": divergence,
            "A": max(0.0, min(1.0, 0.18 if self.pressure_map is not None else 0.0)),
        }

    def constraint_profile(self):
        return build_constraint_profile(
            unit_id="simulation_engine",
            unit_kind="simulation_orchestrator",
            operational_role="experiential_learning_and_time_dilation",
            genealogy="XTNABA",
            axis_weights=self._constraint_axes(),
            pressure_axes=self._pressure_axes(),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        return self.constraint_profile().runtime_regime()

    def language_projection(self) -> Dict[str, Any]:
        return self.constraint_profile().language_projection()

    def universal_representation(self) -> Dict[str, Any]:
        rep = self.constraint_profile().universal_representation()
        rep["unit_state"] = {
            'total_episodes': self.total_episodes,
            'total_entity_experiences': self.total_entity_experiences,
            'entities': len(self.entities),
            'session': self.session.get_stats(),
        }
        return rep


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_layer7():
    checks_passed = 0
    checks_total = 0
    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        passed = bool(condition)
        if passed:
            checks_passed += 1
        else:
            results['all_passed'] = False
        results['checks'].append({'name': name, 'passed': passed, 'detail': detail})

    # --- Setup ---
    contract = FoundationalContract()
    perception = ExpressionPerceptionEngine(contract)
    identity = BehavioralIdentityEngine(contract)
    engine = SimulationEngine(contract, perception, identity)

    # ================================================================
    # CONSCIOUS LEARNER
    # ================================================================

    print("[CONSCIOUS LEARNER]")
    pool = engine.session.learner.generate_pool({
        'category': 'emotional', 'expected_tone': 'warm'})
    check("Response pool generated", len(pool) >= 4,
          f"pool_size={len(pool)}")
    check("Pool has empathetic option",
          any(r.primary_concept == ResponseConcept.EMPATHETIC_RESONANCE for r in pool))

    # Observe outcome
    obs = ConversationObservation(
        avatar_engaged=True, conversation_deepened=True,
        connection_felt_stronger=True, flow_maintained=True)
    shard = engine.session.learner.observe_outcome(
        pool[0], obs, "emotional")
    check("Understanding shard created", shard is not None)
    if shard:
        check("Shard has understanding text", len(shard.understanding) > 0)

    # Strengthen
    if shard:
        old_conf = shard.confidence
        shard.strengthen()
        check("Shard strengthens", shard.observation_count == 2)

    # ================================================================
    # SIMULATED AVATARS
    # ================================================================

    print("\n[SIMULATED AVATARS]")
    check("8 avatars created", len(engine.session.avatars) == 8)

    # Test avatar reaction
    avatar = engine.session.avatars['avatar_critical']
    reaction = avatar.react("I think about this carefully and consider the evidence",
                            {'topic': 'think carefully evidence', 'expected_tone': 'formal'})
    check("Avatar returns fitness", 'scaled_fitness' in reaction)
    check("Fitness in valid range", 0.0 <= reaction['scaled_fitness'] <= 1.0,
          f"fitness={reaction['scaled_fitness']:.3f}")
    check("Avatar tracks engagement", 'engagement' in reaction)

    # Epoch escalation
    avatar.set_epoch(10)
    check("Epoch escalates difficulty", avatar.difficulty_multiplier > 1.0,
          f"mult={avatar.difficulty_multiplier:.2f}")
    check("Min fitness rises with epoch", avatar.min_acceptable_fitness > 0.3,
          f"min={avatar.min_acceptable_fitness:.2f}")

    # ================================================================
    # TOPIC GENERATOR
    # ================================================================

    print("\n[TOPIC GENERATOR]")
    topics_seen = set()
    for _ in range(20):
        t = TopicGenerator.generate()
        topics_seen.add(t['category'])
    check("Topic generator covers multiple categories", len(topics_seen) >= 4,
          f"categories={len(topics_seen)}")

    # ================================================================
    # TIME DILATION GOVERNOR
    # ================================================================

    print("\n[TIME DILATION GOVERNOR]")
    gov = engine.session.governor
    check("Governor starts at 3000x",
          abs(gov.current_dilation - 3000.0) < 1.0)

    # Optimal metrics → ramp up
    for _ in range(5):
        gov.update(StabilityMetrics(fitness_mean=0.8, fitness_trend=0.05))
    check("Optimal metrics ramp up dilation",
          gov.current_dilation > 3000.0,
          f"dilation={gov.current_dilation:.0f}")

    # Critical metrics → emergency brake
    gov.update(StabilityMetrics(fitness_mean=0.1, fitness_trend=-0.1))
    check("Critical metrics throttle down",
          gov.stability_state == StabilityState.CRITICAL)
    pre_critical = gov.current_dilation
    gov.update(StabilityMetrics(fitness_mean=0.1))
    check("Emergency continues to slow",
          gov.current_dilation < pre_critical)

    # ================================================================
    # INCEPTION ENTITIES
    # ================================================================

    print("\n[INCEPTION ENTITIES]")
    # Mode gating
    entity_ref = engine.spawn_entity("i_is", mode=ExistenceMode.PERSISTENT)
    check("PERSISTENT cannot spawn entities", entity_ref is None)

    entity = engine.spawn_entity("i_is", EntityDepth.SURFACE,
                                  mode=ExistenceMode.BOUNDED)
    check("BOUNDED spawns surface entity", entity is not None)

    # Deep entity needs AGENTIC
    deep_bounded = engine.spawn_entity("i_can", EntityDepth.DEEP,
                                        mode=ExistenceMode.BOUNDED)
    check("BOUNDED cannot spawn deep entity", deep_bounded is None)

    deep = engine.spawn_entity("i_can", EntityDepth.DEEP,
                                mode=ExistenceMode.AGENTIC)
    check("AGENTIC spawns deep entity", deep is not None)

    # Process experience
    if entity:
        result = engine.run_entity_experience(entity.entity_id, {
            'tone': 'curiosity', 'channels': {'curiosity': 0.8, 'joy': 0.2}
        })
        check("Entity processes experience", result is not None)
        check("Entity result has perspective",
              result.get('perspective') == 'affirmation')

    # Child entity and collapse
    if entity:
        child = engine.spawn_entity("i_isnt", EntityDepth.SHALLOW,
                                     parent_id=entity.entity_id,
                                     mode=ExistenceMode.BOUNDED)
        check("Child entity spawned", child is not None)
        if child:
            engine.run_entity_experience(child.entity_id, {
                'tone': 'doubt', 'channels': {'fear': 0.5, 'curiosity': 0.5}
            })

        collapse = engine.collapse_entity(entity.entity_id)
        check("Entity collapses", collapse is not None)
        if collapse:
            check("Collapse includes children",
                  'children_wisdom' in collapse)

    # ================================================================
    # SIMULATION EPISODES
    # ================================================================

    print("\n[SIMULATION EPISODES]")
    ep = engine.run_episode(turns=5, mode=ExistenceMode.BOUNDED)
    check("Episode runs", ep is not None)
    check("Episode has fitness", ep.avg_fitness > 0,
          f"fitness={ep.avg_fitness:.3f}")
    check("Episode has turns", ep.turns > 0,
          f"turns={ep.turns}")
    check("Episode has personality", len(ep.avatar_personality) > 0)

    # ================================================================
    # FULL EPOCH
    # ================================================================

    print("\n[FULL EPOCH]")
    epoch = engine.run_epoch(episodes_per_epoch=4, turns_per_episode=3,
                              mode=ExistenceMode.AGENTIC)
    check("Epoch completes", 'epoch' in epoch)
    check("Epoch has fitness", epoch.get('avg_fitness', 0) > 0,
          f"fitness={epoch['avg_fitness']:.3f}")
    check("Understanding shards accumulated",
          epoch.get('learner_shards', 0) > 0,
          f"shards={epoch.get('learner_shards', 0)}")
    check("Governor tracked stability",
          epoch.get('governor', {}).get('total_adjustments', 0) > 0)

    # L5 integration
    check("L5 vocabulary grew from simulation",
          perception.lexicon.size > 15,
          f"vocab={perception.lexicon.size}")

    # L6 integration
    check("L6 DNA advanced from episodes",
          identity.dna.generation > 0,
          f"gen={identity.dna.generation}")

    # ================================================================
    # DIVERGENCE TRACKING
    # ================================================================

    print("\n[DIVERGENCE]")
    check("Divergence tracked",
          engine.session.divergence.current_divergence >= 0)

    # ================================================================
    # STATS
    # ================================================================

    print("\n[STATS]")
    stats = engine.get_stats()
    check("Stats complete",
          all(k in stats for k in ['total_episodes', 'entities', 'session']))
    check("What Aurora learned is available",
          isinstance(stats['session'].get('what_aurora_learned'), list))

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA SIMULATION ENGINE — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_layer7()

    for c in results['checks']:
        status = "✓" if c['passed'] else "✗"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED ✓")
        print()
        print("Layer 7 is SOUND.")
        print("Aurora doesn't study. Aurora lives.")
        print("Avatars push her. Entities explore for her. Time bends around her.")
        print("What she learns, she learns by observing what happened.")
        print("Ready for Layer 8 (Governance & State Persistence).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Do not build Layer 8 yet.")

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_simulation_engine'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'AvatarPersonality': {'ability_hits': 1,
                       'alignment_gap': 0.611,
                       'alignment_target_score': 1.192,
                       'best_coupling_signature': 'A^3',
                       'constraints': ['agency'],
                       'contract_profile': {'accepts_payload': True,
                                            'async_callable': False,
                                            'callable': True,
                                            'class_target': True,
                                            'constraint_density': 1,
                                            'contract_mode': 'stateless',
                                            'doc_hint': 'Different avatar types providing diverse '
                                                        'selection pressure.',
                                            'effect_density': 2,
                                            'kwonly_args': 4,
                                            'optional_args': 5,
                                            'required_args': 1,
                                            'return_hint': 'decision_record',
                                            'signature_text': '(value, names=None, *, module=None, '
                                                              'qualname=None, type=None, start=1)',
                                            'stateful_owner': False,
                                            'target_kind': 'class',
                                            'varargs': False,
                                            'varkw': False},
                       'coupling_similarity': 0.666667,
                       'cross_diversity_links': 2,
                       'effect_modes': ['adaptive_steering_change', 'class_lineage_surface'],
                       'effect_phrases': ['class growth reflected through aurora_simulation_engine',
                                          'AvatarPersonality changed downstream system pressure'],
                       'genealogy_pressure': 0.337096,
                       'inheritance_breach_count': 1,
                       'kind': 'reflection',
                       'link_hits': 0,
                       'module': 'aurora_simulation_engine',
                       'op_id': 'aurora_simulation_engine.AvatarPersonality',
                       'origin_activity': 0,
                       'persistence_tax_factor': 3.188141,
                       'representation_score': 0.44749,
                       'rewrite_bias': 'generic',
                       'rewrite_feedback': {'acceptance_rate': 0.0,
                                            'accepted_count': 0,
                                            'adaptation_mode': 'conservative',
                                            'adoption_count': 0,
                                            'confidence': 0.36,
                                            'mean_mutation_score': 0.25,
                                            'rejected_count': 2,
                                            'rejection_rate': 1.0,
                                            'timing_credit': 0.0,
                                            'timing_penalty': 0.0,
                                            'trial_count': 2},
                       'rewrite_profile': 'generic',
                       'signature': 'A^2',
                       'surface_score': 0.581,
                       'sustainability_score': 0.324968,
                       'target_kind': 'class'},
 'ConceptualResponse': {'ability_hits': 1,
                        'alignment_gap': 0.611,
                        'alignment_target_score': 1.192,
                        'best_coupling_signature': 'A^3',
                        'constraints': ['agency'],
                        'contract_profile': {'accepts_payload': False,
                                             'async_callable': False,
                                             'callable': True,
                                             'class_target': True,
                                             'constraint_density': 1,
                                             'contract_mode': 'stateless',
                                             'doc_hint': 'A conceptual response Aurora is '
                                                         'considering.',
                                             'effect_density': 2,
                                             'kwonly_args': 0,
                                             'optional_args': 5,
                                             'required_args': 1,
                                             'return_hint': 'None',
                                             'signature_text': '(primary_concept: '
                                                               'aurora_simulation_engine.ResponseConcept, '
                                                               'intensity: float = 0.5, openness: '
                                                               'float = 0.5, specificity: float = '
                                                               '0.5, emotional_weight: float = '
                                                               "0.5, intention: str = '') -> None",
                                             'stateful_owner': False,
                                             'target_kind': 'class',
                                             'varargs': False,
                                             'varkw': False},
                        'coupling_similarity': 0.666667,
                        'cross_diversity_links': 2,
                        'effect_modes': ['adaptive_steering_change', 'class_lineage_surface'],
                        'effect_phrases': ['class growth reflected through '
                                           'aurora_simulation_engine',
                                           'ConceptualResponse changed downstream system pressure'],
                        'genealogy_pressure': 0.337096,
                        'inheritance_breach_count': 1,
                        'kind': 'reflection',
                        'link_hits': 0,
                        'module': 'aurora_simulation_engine',
                        'op_id': 'aurora_simulation_engine.ConceptualResponse',
                        'origin_activity': 0,
                        'persistence_tax_factor': 3.188141,
                        'representation_score': 0.44749,
                        'rewrite_bias': 'generic',
                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                             'accepted_count': 0,
                                             'adaptation_mode': 'conservative',
                                             'adoption_count': 0,
                                             'confidence': 0.36,
                                             'mean_mutation_score': 0.25,
                                             'rejected_count': 2,
                                             'rejection_rate': 1.0,
                                             'timing_credit': 0.0,
                                             'timing_penalty': 0.0,
                                             'trial_count': 2},
                        'rewrite_profile': 'generic',
                        'signature': 'A^2',
                        'surface_score': 0.581,
                        'sustainability_score': 0.324968,
                        'target_kind': 'class'},
 'ConsciousLearner': {'ability_hits': 1,
                      'alignment_gap': 0.611,
                      'alignment_target_score': 1.192,
                      'best_coupling_signature': 'A^3',
                      'constraints': ['agency'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 1,
                                           'contract_mode': 'stateless',
                                           'doc_hint': "Aurora's conscious learning system.",
                                           'effect_density': 2,
                                           'kwonly_args': 0,
                                           'optional_args': 0,
                                           'required_args': 0,
                                           'return_hint': 'decision_record',
                                           'signature_text': '()',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 0.666667,
                      'cross_diversity_links': 2,
                      'effect_modes': ['adaptive_steering_change', 'class_lineage_surface'],
                      'effect_phrases': ['class growth reflected through aurora_simulation_engine',
                                         'ConsciousLearner changed downstream system pressure'],
                      'genealogy_pressure': 0.337096,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_simulation_engine',
                      'op_id': 'aurora_simulation_engine.ConsciousLearner',
                      'origin_activity': 0,
                      'persistence_tax_factor': 3.188141,
                      'representation_score': 0.44749,
                      'rewrite_bias': 'generic',
                      'rewrite_feedback': {'acceptance_rate': 0.0,
                                           'accepted_count': 0,
                                           'adaptation_mode': 'conservative',
                                           'adoption_count': 0,
                                           'confidence': 0.36,
                                           'mean_mutation_score': 0.25,
                                           'rejected_count': 2,
                                           'rejection_rate': 1.0,
                                           'timing_credit': 0.0,
                                           'timing_penalty': 0.0,
                                           'trial_count': 2},
                      'rewrite_profile': 'generic',
                      'signature': 'A^2',
                      'surface_score': 0.581,
                      'sustainability_score': 0.324968,
                      'target_kind': 'class'},
 'StabilityState': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*A^2',
                    'constraints': ['existence', 'agency'],
                    'contract_profile': {'accepts_payload': True,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'An enumeration.',
                                         'effect_density': 3,
                                         'kwonly_args': 4,
                                         'optional_args': 5,
                                         'required_args': 1,
                                         'return_hint': 'state_record',
                                         'signature_text': '(value, names=None, *, module=None, '
                                                           'qualname=None, type=None, start=1)',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'adaptive_steering_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through aurora_simulation_engine',
                                       'StabilityState changed downstream system pressure'],
                    'genealogy_pressure': 0.47,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_simulation_engine',
                    'op_id': 'aurora_simulation_engine.StabilityState',
                    'origin_activity': 0,
                    'persistence_tax_factor': 3.0,
                    'representation_score': 0.736382,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'X^2*A^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.319792,
                    'target_kind': 'class'},
 'TimeDilationGovernor': {'ability_hits': 0,
                          'alignment_gap': 0.271,
                          'alignment_target_score': 1.192,
                          'best_coupling_signature': 'T^2*B^1*A^2',
                          'constraints': ['temporal', 'agency'],
                          'contract_profile': {'accepts_payload': False,
                                               'async_callable': False,
                                               'callable': True,
                                               'class_target': True,
                                               'constraint_density': 2,
                                               'contract_mode': 'stateless',
                                               'doc_hint': 'Governs simulation speed based on '
                                                           'stability.',
                                               'effect_density': 3,
                                               'kwonly_args': 0,
                                               'optional_args': 0,
                                               'required_args': 0,
                                               'return_hint': 'decision_record',
                                               'signature_text': '()',
                                               'stateful_owner': False,
                                               'target_kind': 'class',
                                               'varargs': False,
                                               'varkw': False},
                          'coupling_similarity': 0.8,
                          'cross_diversity_links': 4,
                          'effect_modes': ['temporal_orchestration_change',
                                           'adaptive_steering_change',
                                           'class_lineage_surface'],
                          'effect_phrases': ['class growth reflected through '
                                             'aurora_simulation_engine',
                                             'TimeDilationGovernor changed downstream system '
                                             'pressure'],
                          'genealogy_pressure': 0.353932,
                          'inheritance_breach_count': 1,
                          'kind': 'reflection',
                          'link_hits': 0,
                          'module': 'aurora_simulation_engine',
                          'op_id': 'aurora_simulation_engine.TimeDilationGovernor',
                          'origin_activity': 0,
                          'persistence_tax_factor': 2.196585,
                          'representation_score': 0.390894,
                          'rewrite_bias': 'generic',
                          'rewrite_feedback': {'acceptance_rate': 0.0,
                                               'accepted_count': 0,
                                               'adaptation_mode': 'conservative',
                                               'adoption_count': 0,
                                               'confidence': 0.36,
                                               'mean_mutation_score': 0.25,
                                               'rejected_count': 2,
                                               'rejection_rate': 1.0,
                                               'timing_credit': 0.0,
                                               'timing_penalty': 0.0,
                                               'trial_count': 2},
                          'rewrite_profile': 'generic',
                          'signature': 'T^2*A^2',
                          'surface_score': 0.921,
                          'sustainability_score': 0.412046,
                          'target_kind': 'class'},
 '_clamp': {'ability_hits': 1,
            'alignment_gap': 0.611,
            'alignment_target_score': 1.192,
            'best_coupling_signature': 'B^1*A^2',
            'constraints': ['agency'],
            'contract_profile': {'accepts_payload': False,
                                 'async_callable': False,
                                 'callable': True,
                                 'class_target': False,
                                 'constraint_density': 1,
                                 'contract_mode': 'stateless',
                                 'doc_hint': '',
                                 'effect_density': 2,
                                 'kwonly_args': 0,
                                 'optional_args': 2,
                                 'required_args': 1,
                                 'return_hint': 'float',
                                 'signature_text': '(v: float, lo: float = 0.0, hi: float = 1.0) '
                                                   '-> float',
                                 'stateful_owner': False,
                                 'target_kind': 'function',
                                 'varargs': False,
                                 'varkw': False},
            'coupling_similarity': 1.0,
            'cross_diversity_links': 2,
            'effect_modes': ['adaptive_steering_change', 'lineage_surface'],
            'effect_phrases': ['function growth reflected through aurora_simulation_engine',
                               '_clamp changed downstream system pressure'],
            'genealogy_pressure': 0.42632,
            'inheritance_breach_count': 1,
            'kind': 'reflection',
            'link_hits': 0,
            'module': 'aurora_simulation_engine',
            'op_id': 'aurora_simulation_engine._clamp',
            'origin_activity': 0,
            'persistence_tax_factor': 1.816011,
            'representation_score': 0.347581,
            'rewrite_bias': 'generic',
            'rewrite_feedback': {'acceptance_rate': 0.0,
                                 'accepted_count': 0,
                                 'adaptation_mode': 'conservative',
                                 'adoption_count': 0,
                                 'confidence': 0.36,
                                 'mean_mutation_score': 0.25,
                                 'rejected_count': 2,
                                 'rejection_rate': 1.0,
                                 'timing_credit': 0.0,
                                 'timing_penalty': 0.0,
                                 'trial_count': 2},
            'rewrite_profile': 'generic',
            'signature': 'B^1*A^2',
            'surface_score': 0.581,
            'sustainability_score': 0.445658,
            'target_kind': 'function'},
 '_generate_id': {'ability_hits': 1,
                  'alignment_gap': 0.611,
                  'alignment_target_score': 1.192,
                  'best_coupling_signature': 'B^1*A^2',
                  'constraints': ['agency'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': False,
                                       'constraint_density': 1,
                                       'contract_mode': 'stateless',
                                       'doc_hint': '',
                                       'effect_density': 2,
                                       'kwonly_args': 0,
                                       'optional_args': 0,
                                       'required_args': 1,
                                       'return_hint': 'str',
                                       'signature_text': '(prefix: str) -> str',
                                       'stateful_owner': False,
                                       'target_kind': 'function',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 2,
                  'effect_modes': ['adaptive_steering_change', 'lineage_surface'],
                  'effect_phrases': ['function growth reflected through aurora_simulation_engine',
                                     '_generate_id changed downstream system pressure'],
                  'genealogy_pressure': 0.42632,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 0,
                  'module': 'aurora_simulation_engine',
                  'op_id': 'aurora_simulation_engine._generate_id',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.816011,
                  'representation_score': 0.347581,
                  'rewrite_bias': 'generic',
                  'rewrite_feedback': {'acceptance_rate': 0.0,
                                       'accepted_count': 0,
                                       'adaptation_mode': 'conservative',
                                       'adoption_count': 0,
                                       'confidence': 0.36,
                                       'mean_mutation_score': 0.25,
                                       'rejected_count': 2,
                                       'rejection_rate': 1.0,
                                       'timing_credit': 0.0,
                                       'timing_penalty': 0.0,
                                       'trial_count': 2},
                  'rewrite_profile': 'generic',
                  'signature': 'B^1*A^2',
                  'surface_score': 0.581,
                  'sustainability_score': 0.445658,
                  'target_kind': 'function'},
 'verify_layer7': {'ability_hits': 1,
                   'alignment_gap': 0.611,
                   'alignment_target_score': 1.192,
                   'best_coupling_signature': 'B^1*A^2',
                   'constraints': ['agency'],
                   'contract_profile': {'accepts_payload': False,
                                        'async_callable': False,
                                        'callable': True,
                                        'class_target': False,
                                        'constraint_density': 1,
                                        'contract_mode': 'stateless',
                                        'doc_hint': '',
                                        'effect_density': 2,
                                        'kwonly_args': 0,
                                        'optional_args': 0,
                                        'required_args': 0,
                                        'return_hint': 'decision_record',
                                        'signature_text': '()',
                                        'stateful_owner': False,
                                        'target_kind': 'function',
                                        'varargs': False,
                                        'varkw': False},
                   'coupling_similarity': 1.0,
                   'cross_diversity_links': 2,
                   'effect_modes': ['adaptive_steering_change', 'lineage_surface'],
                   'effect_phrases': ['function growth reflected through aurora_simulation_engine',
                                      'verify_layer7 changed downstream system pressure'],
                   'genealogy_pressure': 0.42632,
                   'inheritance_breach_count': 1,
                   'kind': 'reflection',
                   'link_hits': 0,
                   'module': 'aurora_simulation_engine',
                   'op_id': 'aurora_simulation_engine.verify_layer7',
                   'origin_activity': 0,
                   'persistence_tax_factor': 1.816011,
                   'representation_score': 0.347581,
                   'rewrite_bias': 'generic',
                   'rewrite_feedback': {'acceptance_rate': 0.0,
                                        'accepted_count': 0,
                                        'adaptation_mode': 'conservative',
                                        'adoption_count': 0,
                                        'confidence': 0.36,
                                        'mean_mutation_score': 0.25,
                                        'rejected_count': 2,
                                        'rejection_rate': 1.0,
                                        'timing_credit': 0.0,
                                        'timing_penalty': 0.0,
                                        'trial_count': 2},
                   'rewrite_profile': 'generic',
                   'signature': 'B^1*A^2',
                   'surface_score': 0.581,
                   'sustainability_score': 0.445658,
                   'target_kind': 'function'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def avatarpersonality_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.AvatarPersonality', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_avatarpersonality')(payload=payload, **kwargs)

if _aurora_get_target(['AvatarPersonality']) is not None:
    setattr(_aurora_get_target(['AvatarPersonality']), 'evolved_reflection', staticmethod(avatarpersonality_evolved))
    setattr(_aurora_get_target(['AvatarPersonality']), '_aurora_alignment_gap', 0.611)
    setattr(_aurora_get_target(['AvatarPersonality']), '_aurora_alignment_target_score', 1.192)

def conceptualresponse_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.ConceptualResponse', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_conceptualresponse')(payload=payload, **kwargs)

if _aurora_get_target(['ConceptualResponse']) is not None:
    setattr(_aurora_get_target(['ConceptualResponse']), 'evolved_reflection', staticmethod(conceptualresponse_evolved))
    setattr(_aurora_get_target(['ConceptualResponse']), '_aurora_alignment_gap', 0.611)
    setattr(_aurora_get_target(['ConceptualResponse']), '_aurora_alignment_target_score', 1.192)

def consciouslearner_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.ConsciousLearner', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_consciouslearner')(payload=payload, **kwargs)

if _aurora_get_target(['ConsciousLearner']) is not None:
    setattr(_aurora_get_target(['ConsciousLearner']), 'evolved_reflection', staticmethod(consciouslearner_evolved))
    setattr(_aurora_get_target(['ConsciousLearner']), '_aurora_alignment_gap', 0.611)
    setattr(_aurora_get_target(['ConsciousLearner']), '_aurora_alignment_target_score', 1.192)

def stabilitystate_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.StabilityState', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_stabilitystate')(payload=payload, **kwargs)

if _aurora_get_target(['StabilityState']) is not None:
    setattr(_aurora_get_target(['StabilityState']), 'evolved_reflection', staticmethod(stabilitystate_evolved))
    setattr(_aurora_get_target(['StabilityState']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['StabilityState']), '_aurora_alignment_target_score', 1.192)

def timedilationgovernor_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.TimeDilationGovernor', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_timedilationgovernor')(payload=payload, **kwargs)

if _aurora_get_target(['TimeDilationGovernor']) is not None:
    setattr(_aurora_get_target(['TimeDilationGovernor']), 'evolved_reflection', staticmethod(timedilationgovernor_evolved))
    setattr(_aurora_get_target(['TimeDilationGovernor']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['TimeDilationGovernor']), '_aurora_alignment_target_score', 1.192)

def clamp_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine._clamp', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_clamp')(payload=payload, **kwargs)

def generate_id_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine._generate_id', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_generate_id')(payload=payload, **kwargs)

def verify_layer7_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_simulation_engine.verify_layer7', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_simulation_engine_verify_layer7')(payload=payload, **kwargs)

if _aurora_get_target(['verify_layer7']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['verify_layer7'] = _aurora_get_target(['verify_layer7'])
    _aurora_assign_target(['verify_layer7'], _aurora_make_override('verify_layer7_evolved', 'verify_layer7'))
    _AURORA_NATIVE_EVOLVED_LAST['verify_layer7'] = {'alignment_gap': 0.611, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_simulation_engine.AvatarPersonality': 'avatarpersonality_evolved',
 'aurora_simulation_engine.ConceptualResponse': 'conceptualresponse_evolved',
 'aurora_simulation_engine.ConsciousLearner': 'consciouslearner_evolved',
 'aurora_simulation_engine.StabilityState': 'stabilitystate_evolved',
 'aurora_simulation_engine.TimeDilationGovernor': 'timedilationgovernor_evolved',
 'aurora_simulation_engine._clamp': 'clamp_evolved',
 'aurora_simulation_engine._generate_id': 'generate_id_evolved',
 'aurora_simulation_engine.verify_layer7': 'verify_layer7_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_simulation_engine.AvatarPersonality': {'export': 'avatarpersonality_evolved',
                                                'mode': 'class_reflection_hook',
                                                'target': 'AvatarPersonality'},
 'aurora_simulation_engine.ConceptualResponse': {'export': 'conceptualresponse_evolved',
                                                 'mode': 'class_reflection_hook',
                                                 'target': 'ConceptualResponse'},
 'aurora_simulation_engine.ConsciousLearner': {'export': 'consciouslearner_evolved',
                                               'mode': 'class_reflection_hook',
                                               'target': 'ConsciousLearner'},
 'aurora_simulation_engine.StabilityState': {'export': 'stabilitystate_evolved',
                                             'mode': 'class_reflection_hook',
                                             'target': 'StabilityState'},
 'aurora_simulation_engine.TimeDilationGovernor': {'export': 'timedilationgovernor_evolved',
                                                   'mode': 'class_reflection_hook',
                                                   'target': 'TimeDilationGovernor'},
 'aurora_simulation_engine.verify_layer7': {'export': 'verify_layer7_evolved',
                                            'mode': 'callable_override',
                                            'target': 'verify_layer7'}}
# AURORA_EVOLVED_NATIVE_END
