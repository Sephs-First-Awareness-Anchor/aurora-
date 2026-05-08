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
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set, Deque
from dataclasses import dataclass, field
from collections import defaultdict, deque

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

    def what_have_i_learned(self) -> List[str]:
        """Return what Aurora has learned, in her own words."""
        confident = [s for s in self.shards.values() if s.confidence > 0.5]
        confident.sort(key=lambda s: s.confidence, reverse=True)
        return [s.understanding for s in confident[:10]]

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
        return f"I noticed something when using {concept_name}"

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
        self.difficulty_multiplier = min(2.0, 1.0 + epoch * 0.05)
        self.min_acceptable_fitness = min(0.7, 0.3 + epoch * 0.02)
        self.patience = max(0.2, self.patience - min(0.2, epoch * 0.01))

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
        # Apply difficulty scaling
        scaled_fitness = _clamp(raw_fitness / self.difficulty_multiplier)

        # Update engagement
        if scaled_fitness < self.min_acceptable_fitness:
            self.engagement = max(0.0, self.engagement - 0.15)
        else:
            self.engagement = min(1.0, self.engagement + 0.05)

        self.satisfaction = 0.7 * self.satisfaction + 0.3 * scaled_fitness

        return {
            'scores': scores,
            'raw_fitness': raw_fitness,
            'scaled_fitness': scaled_fitness,
            'engagement': self.engagement,
            'satisfaction': self.satisfaction,
            'still_engaged': self.engagement > 0.2,
            'avatar_personality': self.personality.value,
            'epoch': self.current_epoch
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

    MIN_DILATION = 100.0
    MAX_DILATION = 10_000_000.0
    START_DILATION = 3000.0

    RAMP_UP_RATE = 1.15
    THROTTLE_RATE = 0.7
    EMERGENCY_RATE = 0.4

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
    timestamp: float = field(default_factory=time.time)


class SimulationSession:
    """
    Runs simulation episodes. The bridge between all systems.
    Generates topics → runs conversations → feeds results back to L5/L6.
    """

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

        # Speed-run state
        self._speed_run_active: bool = False
        self._speed_run_axis_amplifiers: Dict[str, float] = {}
        self._speed_run_slot_cursor: int = 0
        self._speed_run_slots: List[str] = []

        # Avatars
        self.avatars: Dict[str, SimulatedAvatar] = {}
        self._create_avatar_pool()

        # Episode tracking
        self.episodes: List[EpisodeResult] = []
        self.current_epoch = 0
        self.total_turns = 0

    def _create_avatar_pool(self):
        """Create one avatar per personality type."""
        for personality in AvatarPersonality:
            aid = f"avatar_{personality.value}"
            self.avatars[aid] = SimulatedAvatar(
                avatar_id=aid, personality=personality)

    def run_episode(self, turns: int = 5,
                    avatar_personality: Optional[AvatarPersonality] = None,
                    mode: ExistenceMode = ExistenceMode.BOUNDED
                    ) -> EpisodeResult:
        """
        Run one simulation episode.
        Topic generated → avatar selected → turns processed → results fed back.
        """
        # Select avatar
        if avatar_personality:
            avatar_id = f"avatar_{avatar_personality.value}"
        else:
            avatar_id = random.choice(list(self.avatars.keys()))
        avatar = self.avatars[avatar_id]
        avatar.reset()
        avatar.set_epoch(self.current_epoch)

        # Generate topic
        topic = TopicGenerator.generate()

        fitness_scores = []
        understanding_texts = []

        for turn in range(turns):
            if not avatar.engagement > 0.2:
                break  # Avatar disengaged

            # Generate response pool
            pool = self.learner.generate_pool(topic)

            # Resolve active NC slot for gradient-biased selection
            active_slot: Optional[str] = None
            if self._speed_run_active and self._speed_run_slots:
                cursor = self._speed_run_slot_cursor % len(self._speed_run_slots)
                active_slot = self._speed_run_slots[cursor]

            # Aurora selects (biased by understanding + pressure gradient)
            selected = self._select_response(pool, topic, active_slot=active_slot)

            # Build expression through L5 if available
            expression_text = self._generate_expression(selected, topic, mode)

            # Avatar reacts
            reaction = avatar.react(expression_text, topic)
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
                                                  topic['category'])
            if shard:
                understanding_texts.append(shard.understanding)

            # Feed to perception pipeline
            if self.perception:
                self.perception.ingest_interaction({
                    'input': topic['prompt'],
                    'tone': topic['expected_tone'],
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
                'theme': topic['category'],
                'stability': avg_fitness,
                'seed_ids': [_generate_id("ep_seed")],
                'emotional_bias': {topic.get('expected_tone', 'neutral'): 0.7},
                'manifold_position': (avg_fitness, 0, 0, 0, 0),
            }]
            self.identity.process_episode(
                episode_summary, relics,
                {topic['category']: avg_fitness},
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
            topic_category=topic['category'],
            turns=len(fitness_scores),
            avg_fitness=avg_fitness,
            final_engagement=avatar.engagement,
            understanding_gained=understanding_texts,
            relics_formed=relics_formed,
        )
        self.episodes.append(result)
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

        # Consolidate L5 if available
        if self.perception:
            self.perception.consolidate(mode)

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

    def _generate_expression(self, selected: ConceptualResponse,
                              context: Dict, mode: ExistenceMode) -> str:
        """Generate expression text. Uses L5 if available, else simple generation."""
        concept_name = selected.primary_concept.value.replace('_', ' ')
        topic = context.get('topic', '')

        if self.perception:
            from aurora_consciousness_engine import AssemblyResult
            mock_assembly = AssemblyResult(
                synthesis=None, frame_applied="balanced",
                adjusted_axes={}, coherence=selected.intensity,
                entropy_state={}, ds_stats={}
            )
            result = self.perception.express(
                mock_assembly, i_state=selected.primary_concept.value, mode="sim")
            return result.get('expression', concept_name)

        # Fallback: simple generated text
        return f"I approach this with {concept_name}. {topic}"

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
                 state_dir: str = "aurora_state"):
        self.contract = contract or FoundationalContract()

        # 625 evolutionary pressure map — boot-load if descriptor path given or map exists
        self.pressure_map: Optional["Aurora625PressureMap"] = None
        if _HAS_PRESSURE_MAP:
            import os
            cached = os.path.join(state_dir, "evo_625_pressure_map.json")
            if descriptors_path or os.path.exists(cached):
                try:
                    self.pressure_map = build_from_descriptors(
                        descriptors_path=descriptors_path or "operation_descriptors.json",
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
        return stats


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
