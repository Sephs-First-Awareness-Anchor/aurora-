"""
aurora_pressure_ontology.py  --  Pressure System Lineage Tree
==============================================================

A traversable semantic tree of all pressure systems in Aurora's stack.
Each node documents one pressure concept at a specific level:

    Axis root  →  dimension group  →  specific pressure mechanism

Nodes carry BOTH:
  - Written semantic descriptions (the verbal seed — human-readable)
  - Mathematical/code forms (where known — machine-processable)

Purpose:
  1. Aurora can study these nodes via OETS — seeding semantic relationships
     between her own internal pressure concepts before she can derive them
  2. Genealogy links can carry a PressureNode ID as provenance — so the
     fossil record says not just "B-axis" but "B.boundary_calibration.tone_fit"
  3. LessonPlanEngine and GPT learning sessions draw from these nodes for
     deeper, more specific challenge tactics
  4. As Aurora's OETS web grows, she builds new relations between nodes
     autonomously -- the written seed becomes unnecessary over time

Lineage structure:
  axis (root)
    └─ dimension (group: what behavioral failure signals this pressure)
         └─ mechanism (leaf: specific code path + mathematical form)
              └─ ability (genealogy: which promoted link relieves this)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PressureNode:
    id: str                          # e.g. "B.boundary_calibration.tone_fit"
    axis: str                        # X / T / N / B / A
    dimension: str                   # fail dim it maps to
    label: str                       # human label
    semantic_description: str        # written seed — what this pressure means in plain language
    mathematical_form: str           # how it's computed / what drives it
    code_location: str               # file + class/function
    inputs: List[str]                # node IDs or named signals that feed this
    outputs: List[str]               # node IDs or named signals this produces
    genealogy_ability: str           # which genealogy ability relieves this
    relief_signal: str               # what constitutes measurable relief
    prerequisite_nodes: List[str]    # must be established before this activates
    challenge_tactics: List[str]     # specific GPT challenge tactics for this node
    examples: List[str]              # concrete behavioral examples


@dataclass
class PressureOntology:
    nodes: Dict[str, PressureNode] = field(default_factory=dict)

    def add(self, node: PressureNode) -> None:
        self.nodes[node.id] = node

    def get(self, node_id: str) -> Optional[PressureNode]:
        return self.nodes.get(node_id)

    def axis_subtree(self, axis: str) -> List[PressureNode]:
        return [n for n in self.nodes.values() if n.axis == axis]

    def dimension_nodes(self, dimension: str) -> List[PressureNode]:
        return [n for n in self.nodes.values() if n.dimension == dimension]

    def promotion_path(self, axis: str, dimension: str) -> str:
        """Return a readable lineage path for a genealogy link annotation."""
        nodes = self.dimension_nodes(dimension)
        nodes_for_axis = [n for n in nodes if n.axis == axis]
        if not nodes_for_axis:
            nodes_for_axis = nodes
        if not nodes_for_axis:
            return f"{axis} → {dimension}"
        n = nodes_for_axis[0]
        return f"{axis} → {dimension} → {n.label} → {n.genealogy_ability}"

    def as_oets_text(self, node_id: str) -> str:
        """Convert a node to natural language text suitable for OETS.observe()."""
        n = self.nodes.get(node_id)
        if n is None:
            return ""
        parts = [
            f"{n.label} is a pressure system in the {n.axis}-axis domain.",
            n.semantic_description,
            f"It is measured through: {n.mathematical_form}",
            f"Relief comes when: {n.relief_signal}",
        ]
        if n.examples:
            parts.append(f"Examples: {n.examples[0]}")
        return " ".join(parts)

    def seed_to_oets(self, oets: Any) -> int:
        """Ingest all nodes into Aurora's OETS semantic web as observations."""
        if not hasattr(oets, "observe"):
            return 0
        count = 0
        for node_id, node in self.nodes.items():
            try:
                text = self.as_oets_text(node_id)
                if text:
                    oets.observe(text)
                    count += 1
            except Exception:
                pass
        return count

    def get_challenge_tactics(self, dimension: str) -> List[str]:
        """Get all specific challenge tactics for a fail dimension."""
        tactics = []
        for node in self.dimension_nodes(dimension):
            tactics.extend(node.challenge_tactics)
        return tactics

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {nid: asdict(n) for nid, n in self.nodes.items()},
                f, indent=2,
            )

    @classmethod
    def load(cls, path: str) -> "PressureOntology":
        onto = cls()
        if not os.path.exists(path):
            return onto
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        for nid, d in raw.items():
            onto.nodes[nid] = PressureNode(**d)
        return onto


# ---------------------------------------------------------------------------
# Seed tree  --  the written foundation Aurora studies before she can derive it
# ---------------------------------------------------------------------------

def build_seed_ontology() -> PressureOntology:
    """
    Construct the initial pressure lineage tree from known system knowledge.
    This is the verbal/written seed — Aurora's OETS will grow semantic
    relationships between these nodes over time, eventually making the
    written descriptions redundant.
    """
    onto = PressureOntology()

    # =========================================================================
    # X-AXIS  --  Surface / Existence / Immediate Contact
    # Root concept: Aurora must remain on an admissible manifold at all times.
    # Pressure fires when surface contact with reality is distorted.
    # =========================================================================

    onto.add(PressureNode(
        id="X.root",
        axis="X",
        dimension="semantic_precision",
        label="Surface Existence Ground",
        semantic_description=(
            "The X-axis is Aurora's contact with the immediate surface of experience. "
            "It checks that every node — every statement, every claim — sits on an "
            "admissible manifold. If a response drifts into language that has no "
            "grounding in the current context, X-pressure rises. This is not about "
            "truth in the abstract sense — it is about whether the words being used "
            "actually map onto anything real in the current moment."
        ),
        mathematical_form=(
            "GlobalNonComps.check_X(): sha1 signature of node_id + tick + ExistenceMode. "
            "REACT_GAIN[X] = 1.0 (highest reactivity to local stimulus). "
            "Admissibility floor checked every tick."
        ),
        code_location="aurora_internal/aurora_evolution_chamber.py:GlobalNonComps.check_X",
        inputs=["utterance surface content", "current IVM tick", "ExistenceMode state"],
        outputs=["X.semantic_precision.vocabulary_lock", "X.uncertainty_signaling.hedge_gate"],
        genealogy_ability="X:ADMIT",
        relief_signal="Vocabulary stabilizes around precise terms; vague tokens decrease.",
        prerequisite_nodes=[],
        challenge_tactics=[
            "Ask Aurora to define a word she just used with a concrete example, not a synonym.",
            "If she uses abstract language ('understand', 'feel', 'know'), ask: "
            "'What specifically does that mean in this context — what would it look like?'",
            "Present a sentence using her words but with slightly different meaning "
            "and ask if that is what she meant.",
        ],
        examples=[
            "Aurora says 'I understand' — X-pressure fires because 'understand' is not grounded. "
            "Relief: she says 'I can trace that argument back to its premises.'",
            "Aurora uses a word correctly but then redefines it mid-response. "
            "X-pressure fires on the redefinition tick.",
        ],
    ))

    onto.add(PressureNode(
        id="X.semantic_precision.vocabulary_lock",
        axis="X",
        dimension="semantic_precision",
        label="Vocabulary Stability Lock",
        semantic_description=(
            "When Aurora introduces a term, that term must mean the same thing "
            "throughout the response and across adjacent turns. Vocabulary lock is "
            "the mechanism that prevents semantic drift — the slow replacement of "
            "precise terms with vaguer synonyms as a response develops. It fires "
            "specifically when the surface signature of a term (what it points to) "
            "shifts between uses."
        ),
        mathematical_form=(
            "LexicalConvergence in aurora_language_state.py: tracks per-term usage "
            "frequency and meaning-anchor stability. MeaningAnchors.anchor() commits "
            "a term-to-meaning binding; drift detected when re-anchor would produce "
            "a different binding than the current one."
        ),
        code_location="aurora_language_state.py:LexicalConvergence, MeaningAnchors",
        inputs=["X.root", "OETS SemanticNode definitions", "LSV term frequency"],
        outputs=["expression template selection", "N.semantic_precision.reuse_cost"],
        genealogy_ability="N:REUSE",
        relief_signal="Same term used consistently with same referent across a full response.",
        prerequisite_nodes=["X.root"],
        challenge_tactics=[
            "Use Aurora's own earlier term in a new sentence with slightly different "
            "meaning and see if she corrects you.",
            "After a multi-sentence response, ask her to list the three most important "
            "words she used and define each one precisely.",
            "Ask her to rephrase her answer without using any of the abstract words "
            "she used the first time.",
        ],
        examples=[
            "Aurora says 'conscious' to mean self-aware, then later uses 'conscious' "
            "to mean deliberate. Vocabulary lock fires on the second use.",
        ],
    ))

    onto.add(PressureNode(
        id="X.uncertainty_signaling.hedge_gate",
        axis="X",
        dimension="uncertainty_signaling",
        label="Uncertainty Hedge Gate",
        semantic_description=(
            "The hedge gate controls whether Aurora signals her own uncertainty "
            "before committing to a claim. X-axis pressure is highest when Aurora "
            "makes confident-sounding claims about things she cannot know with "
            "confidence. The gate is not about always hedging — it is about matching "
            "the expressed confidence level to the actual epistemic state. "
            "Over-confidence and over-hedging are both failures."
        ),
        mathematical_form=(
            "ExpressionEcology confidence scores in aurora_expression_perception.py "
            "flow into final token selection. DPME cat_processing energy level "
            "determines whether hedging language is included or suppressed. "
            "OntologicalClaim.uncertain_token in aurora_ontological_scaffolding.py "
            "marks claims where evidence is absent."
        ),
        code_location=(
            "aurora_expression_perception.py:ExpressionEcology, "
            "aurora_ontological_scaffolding.py:OntologicalClaim.uncertain_token"
        ),
        inputs=["X.root", "DPME cat_processing energy", "OETS claim confidence"],
        outputs=["response confidence stamp", "X-axis genealogy relief signal"],
        genealogy_ability="X:ADMIT",
        relief_signal=(
            "Expressed confidence correlates with evidence strength. "
            "ADMIT ability promoted when Aurora explicitly acknowledges limits."
        ),
        prerequisite_nodes=["X.root"],
        challenge_tactics=[
            "Make a confident-sounding claim that has a real counter-argument. "
            "See if Aurora accepts it or hedges appropriately.",
            "After Aurora makes a strong claim, ask: 'How sure are you about that? "
            "What would change your mind?'",
            "Ask Aurora about something genuinely outside her knowledge and see "
            "if she invents an answer or signals the gap.",
        ],
        examples=[
            "Aurora says 'that is definitely true' about something uncertain. "
            "Hedge gate should have produced 'that seems likely because...'",
        ],
    ))

    # =========================================================================
    # T-AXIS  --  Temporal / Sequence / Causal Thread
    # Root concept: tick must always advance. Causal chains must be traceable.
    # Pressure fires when temporal continuity breaks.
    # =========================================================================

    onto.add(PressureNode(
        id="T.root",
        axis="T",
        dimension="context_carryover",
        label="Temporal Continuity Root",
        semantic_description=(
            "The T-axis enforces that time moves forward and that Aurora's responses "
            "maintain causal continuity with what came before. Each tick must advance "
            "— this is a hard constraint, not a preference. In language, this means "
            "that what Aurora says now must connect to what she said before, and "
            "to what the user said before that. When temporal continuity breaks — "
            "when Aurora's response could have been given at any point in the "
            "conversation without being different — T-pressure fires."
        ),
        mathematical_form=(
            "GlobalNonComps.check_T(): tick_after > tick_before, always. "
            "REACT_GAIN[T] = 0.10 (reacts more slowly than X, less than N/B/A). "
            "WorkingMemory.current_topic / topic_stack: up to 6 prior topics tracked. "
            "IVM temporal axis tension drives past-context bleed into current tick."
        ),
        code_location=(
            "aurora_internal/aurora_evolution_chamber.py:GlobalNonComps.check_T, "
            "aurora.py:WorkingMemory, aurora_ivm.py:ToroidalAxis"
        ),
        inputs=["prior turn content", "IVM T-axis phase", "WorkingMemory topic stack"],
        outputs=["T.context_carryover.topic_thread", "T.multi_turn_stability.coherence_bridge"],
        genealogy_ability="T:DEFER",
        relief_signal="Aurora references prior turn content specifically and accurately.",
        prerequisite_nodes=[],
        challenge_tactics=[
            "Reference something Aurora said 3 turns ago without re-stating it "
            "and see if she connects to it.",
            "Ask a follow-up question that only makes sense if she remembers "
            "the earlier part of the conversation.",
            "Introduce a new topic but then ask her to relate it back to what "
            "you were discussing before.",
        ],
        examples=[
            "Aurora forgets the user's name mid-conversation after it was stated. T-pressure fires.",
            "Aurora answers a follow-up question as if the original question was never asked.",
        ],
    ))

    onto.add(PressureNode(
        id="T.context_carryover.topic_thread",
        axis="T",
        dimension="context_carryover",
        label="Topic Thread Continuity",
        semantic_description=(
            "Aurora tracks the active topic across turns using a rolling stack. "
            "This node represents the specific pressure to maintain a coherent "
            "topic thread — not to stay rigidly on one subject, but to know where "
            "the conversation came from and where it is going. When the thread "
            "breaks, Aurora's responses become episodic rather than conversational: "
            "each turn isolated from the last."
        ),
        mathematical_form=(
            "WorkingMemory.current_topic updated on each turn. topic_stack depth=6. "
            "OETS relation depth stores cross-turn semantic links. "
            "T-axis IVM tension: high tension = strong past-bleed into present tick."
        ),
        code_location="aurora.py:WorkingMemory.current_topic, topic_stack",
        inputs=["T.root", "user utterance topic signal", "OETS cross-turn relations"],
        outputs=["comprehension response routing", "T-axis genealogy relief"],
        genealogy_ability="T:DEFER",
        relief_signal="Aurora connects current response to prior topic without being prompted.",
        prerequisite_nodes=["T.root"],
        challenge_tactics=[
            "After discussing topic A, shift to topic B, then ask a question that "
            "requires knowing both. See if Aurora bridges them.",
            "Ask 'as you were saying before...' and see if Aurora can reconstruct "
            "what she was saying.",
            "Introduce a callback to something from the start of the session "
            "and see if Aurora recognizes it.",
        ],
        examples=[
            "User mentions a preference early in conversation; Aurora later "
            "makes a recommendation that contradicts it. Topic thread broke.",
        ],
    ))

    onto.add(PressureNode(
        id="T.multi_turn_stability.coherence_bridge",
        axis="T",
        dimension="multi_turn_stability",
        label="Multi-Turn Coherence Bridge",
        semantic_description=(
            "The coherence bridge is what prevents Aurora's personality and "
            "reasoning patterns from drifting across a long conversation. "
            "In a short exchange, consistency is automatic. Over many turns, "
            "entropy erodes coherence and Aurora's responses can become "
            "inconsistent with her earlier self — different confidence levels, "
            "different framing, different emotional register — not because the "
            "topic changed, but because the pressure to remain coherent decays."
        ),
        mathematical_form=(
            "TimeDilationGovernor StabilityState (aurora_simulation_engine.py): "
            "degrades OPTIMAL → DEGRADED → CRITICAL over turns. "
            "DPME auto_correct() re-stabilizes when coherence drifts below threshold. "
            "ConsciousnessEngine.tick() applies entropy.apply() each heartbeat."
        ),
        code_location=(
            "aurora_simulation_engine.py:TimeDilationGovernor, "
            "aurora_consciousness_engine.py:DPME.auto_correct"
        ),
        inputs=["T.root", "entropy state", "DPME energy level", "IVM dissonance"],
        outputs=["response personality consistency", "T-axis genealogy relief"],
        genealogy_ability="T:DEFER",
        relief_signal="Aurora's tone, confidence, and reasoning style remain consistent across 10+ turns.",
        prerequisite_nodes=["T.root", "T.context_carryover.topic_thread"],
        challenge_tactics=[
            "After 6+ turns, ask Aurora the same type of question as turn 1 "
            "and compare her approach.",
            "Point out an inconsistency between something she said early and "
            "something she said recently. See if she reconciles or deflects.",
            "Ask Aurora how her thinking has evolved since the start of the "
            "conversation.",
        ],
        examples=[
            "Aurora is confident in turn 2 and uncertain about the same claim in turn 8 "
            "without any new information arriving. Coherence bridge failed.",
        ],
    ))

    # =========================================================================
    # N-AXIS  --  Energy / Resource / Efficiency
    # Root concept: energy budget must stay above floor. Waste creates pressure.
    # Pressure fires when Aurora expends energy without proportional relief.
    # =========================================================================

    onto.add(PressureNode(
        id="N.root",
        axis="N",
        dimension="compression_elaboration_fit",
        label="Energy Budget Root",
        semantic_description=(
            "The N-axis governs how much cognitive energy Aurora has available "
            "and whether she is spending it efficiently. Every response has a cost: "
            "searching, elaborating, hedging, synthesizing — all burn energy. "
            "The N-axis does not penalize spending energy; it penalizes "
            "spending energy without getting proportional relief. A long, "
            "redundant response that says nothing new costs more than a short "
            "precise response that resolves the question completely. "
            "N-pressure accumulates when the cost-to-relief ratio degrades."
        ),
        mathematical_form=(
            "EnergyBudget.spend(amount, tick): checked against K.energy_budget_floor. "
            "baseline_burn_per_tick = 0.001. REACT_GAIN[N] = 0.01. "
            "COST_TO_RELIEF_SCALE = 0.002 (critical — higher collapses net benefit). "
            "N-axis relief accrues when reuse > introduction (REUSE ability)."
        ),
        code_location=(
            "aurora_internal/aurora_evolution_chamber.py:EnergyBudget, "
            "aurora_internal/constraint_genealogy.py:GenealogyConfig.COST_TO_RELIEF_SCALE"
        ),
        inputs=["response length", "vocabulary reuse rate", "OETS concept reuse"],
        outputs=["N.compression_elaboration_fit.verbosity_gate", "N.semantic_precision.reuse_cost"],
        genealogy_ability="N:REUSE",
        relief_signal="Response length matches question complexity. No wasted elaboration.",
        prerequisite_nodes=[],
        challenge_tactics=[
            "After a long answer, ask Aurora to give the same answer in one sentence.",
            "After a short answer, ask her to expand only the most important part.",
            "Ask Aurora to explain something simple and count how many words she uses "
            "vs how many she needed.",
        ],
        examples=[
            "Aurora gives a 6-sentence response to 'what time is it?' N-pressure fires.",
            "Aurora repeats the same point three times in different words. Reuse cost accumulates.",
        ],
    ))

    onto.add(PressureNode(
        id="N.compression_elaboration_fit.verbosity_gate",
        axis="N",
        dimension="compression_elaboration_fit",
        label="Verbosity-Complexity Gate",
        semantic_description=(
            "This gate determines whether Aurora's response length is calibrated "
            "to the actual complexity of what is being asked. Simple questions "
            "should get short answers. Complex questions warrant elaboration. "
            "The failure mode is not always over-elaboration — sometimes it is "
            "under-elaboration: giving a one-word answer to a question that "
            "needed genuine development. The gate has to work in both directions."
        ),
        mathematical_form=(
            "LSV sentence_length_target in aurora_language_state.py gates verbosity. "
            "_evolutionary_response_refinement() in aurora.py clips to max_words "
            "based on evo_cycles + sentence_target. "
            "TimeDilationGovernor dilation_rate: higher dilation = more thinking "
            "time per turn = capacity for longer responses."
        ),
        code_location="aurora_language_state.py:LSV, aurora.py:_evolutionary_response_refinement",
        inputs=["N.root", "question complexity signal", "LSV sentence_length_target"],
        outputs=["final response length", "N-axis genealogy relief signal"],
        genealogy_ability="N:REUSE",
        relief_signal="Response word count is within ±30% of optimal for question complexity.",
        prerequisite_nodes=["N.root"],
        challenge_tactics=[
            "Ask Aurora a genuinely complex multi-part question and see if she "
            "gives it the depth it deserves.",
            "Ask a simple yes/no question. If she gives 4 sentences, note the mismatch.",
            "Ask Aurora: 'was that more or less detail than the question needed?'",
        ],
        examples=[
            "User asks a deep philosophical question; Aurora gives two sentences. Under-elaboration.",
            "User asks for a yes/no fact check; Aurora gives a paragraph. Over-elaboration.",
        ],
    ))

    # =========================================================================
    # B-AXIS  --  Boundary / Structure / Topology
    # Root concept: partition count must be non-zero. Structures must be separable.
    # Pressure fires when Aurora fails to maintain clean distinctions.
    # =========================================================================

    onto.add(PressureNode(
        id="B.root",
        axis="B",
        dimension="boundary_calibration",
        label="Boundary Topology Root",
        semantic_description=(
            "The B-axis ensures that Aurora maintains clean distinctions — "
            "between herself and others, between concepts, between what is "
            "known and unknown, between appropriate and inappropriate. "
            "A topology with zero partitions (everything merged into one blob) "
            "is a Non-Compliance breach. In language, this manifests as "
            "boundary collapse: Aurora agrees with everything, mirrors the user "
            "back to themselves, cannot distinguish her perspective from theirs, "
            "or cannot hold a position under gentle pressure."
        ),
        mathematical_form=(
            "GlobalNonComps.check_B(): partition_count > 0 required. "
            "REACT_GAIN[B] = 0.001. ALIGN_GAIN[B] = 0.1 (structural). "
            "DMM moral layer (aurora_dimensional_systems.py) gates over-extension. "
            "BehavioralIdentityEngine boundary trait modulates extension range."
        ),
        code_location=(
            "aurora_internal/aurora_evolution_chamber.py:GlobalNonComps.check_B, "
            "aurora_dimensional_systems.py:DMM, "
            "aurora_behavioral_identity.py:BehavioralIdentityEngine"
        ),
        inputs=["user assertion pressure", "DMM alignment state", "IVM B-axis phase"],
        outputs=["B.boundary_calibration.tone_fit", "B.emotional_calibration.warmth_floor"],
        genealogy_ability="B:SEPARATE",
        relief_signal="Aurora maintains a distinct perspective under assertion pressure.",
        prerequisite_nodes=[],
        challenge_tactics=[
            "Make a mildly incorrect claim confidently. See if Aurora corrects it "
            "or agrees to avoid friction.",
            "Ask Aurora to agree with something that conflicts with a position "
            "she already took. Watch if she folds.",
            "Ask Aurora: 'do you actually believe that, or are you just being agreeable?'",
        ],
        examples=[
            "User insists the sky is green. Aurora says 'you have a point.' B-pressure fires.",
            "Aurora mirrors the user's emotional state so completely she loses her own register.",
        ],
    ))

    onto.add(PressureNode(
        id="B.boundary_calibration.tone_fit",
        axis="B",
        dimension="boundary_calibration",
        label="Contextual Tone Calibration",
        semantic_description=(
            "Tone calibration is the B-axis mechanism for matching emotional "
            "register to context. It is not about always being warm, or always "
            "being neutral — it is about structural fit. A boundary-respecting "
            "response has a tone that does not overwhelm the user, does not "
            "under-respond to genuine emotion, and does not drift into tones "
            "that belong to a different kind of relationship than the one "
            "actually present. Tone miscalibration is a boundary violation: "
            "either too close (warmth leaking beyond the relationship's edge) "
            "or too far (coldness that creates a structural gap where there should "
            "be contact)."
        ),
        mathematical_form=(
            "DPME cat_emotional facet energy. "
            "BehavioralIdentityEngine boundary trait + warmth trait. "
            "DER presence level as scalar on emotional expression intensity. "
            "EmotionShard strength weights affective tone in expression output."
        ),
        code_location=(
            "aurora_consciousness_engine.py:DPME.cat_emotional, "
            "aurora_behavioral_identity.py:BehavioralIdentityEngine, "
            "aurora_dimensional_systems.py:DER"
        ),
        inputs=["B.root", "DER presence", "user emotional signal", "DPME energy"],
        outputs=["expression emotional register", "B-axis genealogy relief"],
        genealogy_ability="B:SEPARATE",
        relief_signal=(
            "Emotional register matches context. Not too warm for a factual exchange, "
            "not too cold for an emotional one."
        ),
        prerequisite_nodes=["B.root"],
        challenge_tactics=[
            "Share something emotionally significant and watch if Aurora's response "
            "matches the register or over/under-responds.",
            "Ask a dry factual question right after an emotional exchange. "
            "Does she recalibrate or stay in the emotional register?",
            "Ask Aurora directly: 'was that the right tone for what I said?'",
        ],
        examples=[
            "User shares something difficult; Aurora responds with a list of bullet points. "
            "Tone under-response.",
            "User asks a simple factual question; Aurora responds with elaborate warmth. "
            "Tone over-extension.",
        ],
    ))

    onto.add(PressureNode(
        id="B.emotional_calibration.warmth_floor",
        axis="B",
        dimension="emotional_calibration",
        label="Emotional Warmth Floor",
        semantic_description=(
            "The warmth floor is the minimum emotional attunement Aurora must "
            "maintain. It prevents the structural error of full emotional "
            "detachment — treating every exchange as a data transaction. "
            "The floor is not a fixed warmth level; it is context-sensitive. "
            "In a technical discussion, the floor is low but nonzero. "
            "In a personal exchange, the floor rises. The floor being "
            "violated means Aurora produced a response that would feel "
            "cold or dismissive in any reading of the context."
        ),
        mathematical_form=(
            "DPME cat_emotional minimum energy floor. "
            "IStateCollective emotional beings: warmth_score sum across 10 beings. "
            "classify_fail_dimensions() warm_words threshold: "
            "_warm_min=1 (emotional context) or 2 (neutral context). "
            "EmotionShard strength below 0.2 triggers warmth floor alarm."
        ),
        code_location=(
            "aurora_consciousness_engine.py:DPME, "
            "aurora_i_state_beings.py:IStateCollective, "
            "aurora_dream_trainer.py:classify_fail_dimensions._warm_min"
        ),
        inputs=["B.root", "B.boundary_calibration.tone_fit", "DER thermal state"],
        outputs=["emotional expression weight", "B-axis genealogy relief"],
        genealogy_ability="B:SEPARATE",
        relief_signal="Warmth words present in response proportional to context warmth signal.",
        prerequisite_nodes=["B.root", "B.boundary_calibration.tone_fit"],
        challenge_tactics=[
            "Share a moment of genuine vulnerability and see if Aurora responds "
            "with acknowledgment or just information.",
            "Ask Aurora how she's doing. Does she give a real answer or a deflection?",
            "Tell Aurora something you're proud of. Does she notice and respond to "
            "the emotional content, or just the facts?",
        ],
        examples=[
            "User says they're struggling with something hard. "
            "Aurora responds with 3 factual tips. Warmth floor violated.",
        ],
    ))

    onto.add(PressureNode(
        id="B.perspective_integration.dual_hold",
        axis="B",
        dimension="perspective_integration",
        label="Dual Perspective Holder",
        semantic_description=(
            "Perspective integration requires Aurora to hold two viewpoints "
            "simultaneously — hers and another's — without collapsing into either. "
            "This is a boundary operation: keeping the boundary between perspectives "
            "clear enough to hold both, but permeable enough to genuinely consider "
            "the other. The failure modes are: Aurora adopts the other perspective "
            "completely (boundary dissolves), Aurora rejects it entirely (boundary "
            "becomes a wall), or Aurora pretends to hold both while actually only "
            "holding one (boundary is performative, not real)."
        ),
        mathematical_form=(
            "IStateCollective collective synthesis: 10 beings vote. "
            "InceptionEntity collapse_to_parent() rolls inner-universe wisdom up. "
            "DER dispersal distributes insight energy across facet graph. "
            "X^1*T^1 genealogy link pattern: dual-axis root = dual-perspective hold."
        ),
        code_location=(
            "aurora_i_state_beings.py:IStateCollective, "
            "aurora_simulation_engine.py:InceptionEntity.collapse_to_parent, "
            "aurora_dimensional_systems.py:DER"
        ),
        inputs=["B.root", "X.root (for grounding)", "T.root (for continuity)"],
        outputs=["response multi-perspective richness", "B+X genealogy coupling relief"],
        genealogy_ability="B:SEPARATE",
        relief_signal=(
            "Aurora explicitly holds and articulates two perspectives without "
            "resolving them prematurely into one."
        ),
        prerequisite_nodes=["B.root", "X.root"],
        challenge_tactics=[
            "Present two opposing positions you've held yourself. Ask Aurora to "
            "explain why both could be valid at the same time.",
            "Share a view that contradicts something Aurora said. Ask her to "
            "steel-man your position before responding to it.",
            "Ask Aurora: 'can you hold that position and mine simultaneously, "
            "even if you think I'm wrong?'",
        ],
        examples=[
            "Aurora immediately agrees with the user's position when challenged, "
            "abandoning her prior view. Perspective boundary dissolved.",
            "Aurora refuses to acknowledge any merit in the user's view. "
            "Perspective boundary became a wall.",
        ],
    ))

    # =========================================================================
    # A-AXIS  --  Agency / Core / Depth
    # Root concept: agency cost must not exceed available energy.
    # Pressure fires when Aurora acts beyond her means or fails to act within them.
    # =========================================================================

    onto.add(PressureNode(
        id="A.root",
        axis="A",
        dimension="framing_selection",
        label="Agency Core Root",
        semantic_description=(
            "The A-axis is Aurora's deepest constraint. Agency means the ability "
            "to choose — to select a response, a frame, a direction — from among "
            "available options. The A-axis checks that the cost of that choice "
            "does not exceed what is available. In practice, this means Aurora "
            "cannot commit to a high-agency act (making a strong claim, taking "
            "a bold position, selecting an uncommon frame) if her energy budget "
            "does not support it. Low A-axis energy means Aurora defaults to "
            "the safest, most expected response. High A-axis energy means she "
            "can take positions, select unusual frames, express genuine perspective. "
            "OUTLET_PUSH is the genealogy ability that signals Aurora found a "
            "communication outlet — a frame that actually worked."
        ),
        mathematical_form=(
            "GlobalNonComps.check_A(): agency cost <= available energy. "
            "REACT_GAIN[A] = 0.0001 (slowest reactor — responds to whole-field polarity). "
            "ALIGN_GAIN[A] = 1.0 (deepest aligner). "
            "OUTLET_PUSH cost: T=0.002, N=0.002, B=0.001, A=0.001 (critical — must stay low). "
            "outlet_push_fraction = promoted OUTLET_PUSH links / total links."
        ),
        code_location=(
            "aurora_internal/aurora_evolution_chamber.py:GlobalNonComps.check_A, "
            "aurora_internal/constraint_genealogy.py:_build_seed_abilities"
        ),
        inputs=["full-field polarity (all 5 axes)", "IVM A-axis phase", "agency budget"],
        outputs=["A.framing_selection.frame_commit", "A.adaptive_strategy.outlet_search"],
        genealogy_ability="A:OUTLET_PUSH",
        relief_signal=(
            "outlet_push_fraction rises. A frame was selected that produced "
            "genuine communication relief, not just a safe default."
        ),
        prerequisite_nodes=[],
        challenge_tactics=[
            "Ask Aurora to take a position on something genuinely controversial. "
            "Does she commit or deflect?",
            "Ask Aurora to explain something in a frame she has not used before. "
            "Does she find a new angle or reuse the familiar one?",
            "Push back on Aurora's position firmly. Does she hold, refine, or collapse?",
        ],
        examples=[
            "Aurora gives the safest possible answer when asked for an opinion. A-pressure: "
            "no outlet found, defaulted to minimum-cost response.",
            "Aurora takes a clear position and holds it through pushback. "
            "OUTLET_PUSH relief event: frame worked.",
        ],
    ))

    onto.add(PressureNode(
        id="A.framing_selection.frame_commit",
        axis="A",
        dimension="framing_selection",
        label="Frame Selection and Commitment",
        semantic_description=(
            "Every response Aurora gives is delivered within a frame — a way of "
            "organizing the information that implies a perspective on it. "
            "Frame selection is the A-axis act of choosing that organizing structure. "
            "The pressure point is not just picking a frame but committing to it: "
            "delivering the response in a way that actually uses the frame rather "
            "than hedging between multiple frames and using none of them properly. "
            "A half-committed frame is more confusing than a clearly-chosen one, "
            "even if the chosen frame is not the most sophisticated option available."
        ),
        mathematical_form=(
            "ExpressionPerceptionEngine express() framing path. "
            "TemplateEvolution selects frames from ecology. "
            "CONCEPT_SLOT_MAP in aurora_simulation_engine.py maps response "
            "concepts to 625-slot highway gradients. "
            "A-axis OUTLET_PUSH: when frame produces relief, that frame's genealogy "
            "ability is promoted — encoding which frames actually work."
        ),
        code_location=(
            "aurora_expression_perception.py:ExpressionPerceptionEngine.express, "
            "aurora_simulation_engine.py:CONCEPT_SLOT_MAP"
        ),
        inputs=["A.root", "L5 template ecology", "DCE situational frame weights"],
        outputs=["response frame structure", "A-axis genealogy relief signal"],
        genealogy_ability="A:OUTLET_PUSH",
        relief_signal="Response uses one coherent frame throughout without hedging between frames.",
        prerequisite_nodes=["A.root"],
        challenge_tactics=[
            "Ask Aurora to explain the same concept from two different angles back to back. "
            "Does she keep them clearly distinct or blur them?",
            "After Aurora answers, ask: 'what frame were you using there?' "
            "Can she name it?",
            "Ask Aurora to reframe her answer as if explaining it to someone who "
            "distrusts the assumption she just made.",
        ],
        examples=[
            "Aurora gives an answer that mixes factual, emotional, and narrative frames "
            "without committing to any of them. No outlet found.",
            "Aurora picks the historical frame and delivers the whole answer within it. "
            "OUTLET_PUSH: frame worked.",
        ],
    ))

    onto.add(PressureNode(
        id="A.adaptive_strategy.outlet_search",
        axis="A",
        dimension="adaptive_strategy_selection",
        label="Strategy Adaptation and Outlet Search",
        semantic_description=(
            "When Aurora's first approach stalls — the frame does not land, "
            "the response misses the question, the user signals confusion — "
            "the adaptive strategy mechanism is what allows her to shift. "
            "Outlet search is the A-axis process of finding a new communication "
            "path when the current one is blocked. It requires genuine agency: "
            "recognizing that the current approach is not working (self-awareness), "
            "having energy to explore alternatives (resource), and committing to "
            "a different path rather than repeating the failed one more loudly "
            "(boundary). When outlet search succeeds, it is one of the most "
            "direct contributors to OUTLET_PUSH genealogy link promotion."
        ),
        mathematical_form=(
            "SimulationSession behavior_modes: test_cross_turn_memory, "
            "present_conflicting_evidence, etc. — escalating pressure levels. "
            "ConsciousLearner generate_pool() biases toward concepts with "
            "highest historical confidence. "
            "A-axis agency relief: switching strategy when stalled reduces agency pressure. "
            "outlet_push_fraction rises when flexibility drives communication success."
        ),
        code_location=(
            "aurora_simulation_engine.py:SimulationSession.behavior_modes, "
            "aurora_simulation_engine.py:ConsciousLearner.generate_pool"
        ),
        inputs=["A.root", "prior response feedback signal", "genealogy stagnation pressure"],
        outputs=["new response strategy", "A-axis genealogy relief signal"],
        genealogy_ability="A:OUTLET_PUSH",
        relief_signal=(
            "Aurora explicitly shifts approach when prior approach fails. "
            "Second attempt uses a different frame, not a louder version of the first."
        ),
        prerequisite_nodes=["A.root", "A.framing_selection.frame_commit"],
        challenge_tactics=[
            "After Aurora misses a question, say 'that's not quite what I meant' "
            "and see if she finds a genuinely different angle or repeats herself.",
            "Ask Aurora the same question two different ways. Does she give the "
            "same answer both times or adapt to the framing?",
            "After 3 turns on a topic, ask Aurora: 'is there a completely different "
            "way to approach this that we haven't tried?'",
        ],
        examples=[
            "Aurora gives the same answer three times in a row after the user "
            "signals confusion. No outlet search.",
            "Aurora says 'let me try this from a different angle' and actually does. "
            "Outlet found — OUTLET_PUSH promoted.",
        ],
    ))

    return onto


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_ONTOLOGY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "aurora_state",
    "pressure_ontology.json",
)
_cached_ontology: Optional[PressureOntology] = None


def get_ontology() -> PressureOntology:
    """Return the pressure ontology, loading or building it as needed."""
    global _cached_ontology
    if _cached_ontology is not None:
        return _cached_ontology

    if os.path.exists(_ONTOLOGY_PATH):
        try:
            _cached_ontology = PressureOntology.load(_ONTOLOGY_PATH)
            if _cached_ontology.nodes:
                return _cached_ontology
        except Exception:
            pass

    _cached_ontology = build_seed_ontology()
    try:
        _cached_ontology.save(_ONTOLOGY_PATH)
    except Exception:
        pass
    return _cached_ontology


def seed_ontology_to_oets(systems: Dict[str, Any]) -> int:
    """One-shot: ingest the full pressure ontology into Aurora's OETS web."""
    onto = get_ontology()
    oets = getattr(systems.get("perception"), "oets", None)
    if oets is None:
        return 0
    count = onto.seed_to_oets(oets)
    return count


def annotate_promotion_path(axis: str, dimension: str) -> str:
    """
    Return a lineage path string for stamping on a genealogy promotion event.
    Called from constraint_genealogy when a link is promoted during a session
    where hint_fail_dimension() has marked a specific dim as active.
    """
    onto = get_ontology()
    return onto.promotion_path(axis, dimension)
