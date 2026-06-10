"""
aurora_turn_chain.py -- TurnUnderstandingState dataclass.

The bidirectional reasoning pipeline traverses the developmental chain in both
directions for every turn:

  UPWARD  (self -- comprehension):
      Information(X) -> Belief(T) -> Purpose(N) -> Meaning(B) -> Understanding(A)

  APEX:   TurnUnderstandingState holds the full model at this turn.

  DOWNWARD (self -- expression):
      Understanding(A) -> Meaning(B) -> Purpose(N) -> Belief(T) -> Information(X)
      -> Communication out

The five stages map 1:1 to the five NC axes:

  Information   (X axis) -- existence: either it IS information or it isn't. The gate.
  Belief        (T axis) -- time: recurrence and prediction over time shape belief.
  Purpose       (N axis) -- cost: energy/value pressure moves belief to directed purpose.
  Meaning       (B axis) -- boundary: what falls within the boundary of significance.
  Understanding (A axis) -- agency: cross-domain integration pressure, direction.

OBSERVATION (two-chain perception):
  One chain going UP is Aurora's own -- she builds comprehension inward.
  One chain going DOWN on ANOTHER's output is observation of that other --
  she infers their Understanding -> Meaning -> Purpose -> Belief -> Information
  by running the downward chain on what they produced.

  perspective="self"  => upward builds comprehension, downward builds expression
  perspective="other" => downward chain deconstructs an external agent's output,
                         filling other_model with the inferred reasoning

Each stage reads from state, enriches it, and passes it to the next.
The stage functions themselves live in aurora.py.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TurnUnderstandingState:
    # ----------------------------------------------------------------
    # Stage 1 -- Information (X axis)
    # Existence: either it IS information or it isn't. The operator gate.
    # ----------------------------------------------------------------
    raw_text: str = ""
    parsed: Dict[str, Any] = field(default_factory=dict)        # UtteranceParser output
    oets_concepts: List[Dict[str, Any]] = field(default_factory=list)
    pipeline_state: Dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # Stage 2 -- Belief (T axis)
    # Time: recurrence and prediction over time shape belief.
    # Working memory IS the T-axis mechanism.
    # ----------------------------------------------------------------
    referent_map: Dict[str, Any] = field(default_factory=dict)
    claim_resolution: Dict[str, Any] = field(default_factory=dict)
    working_memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    session_continuity: float = 0.0
    belief_tension: float = 0.0

    # ----------------------------------------------------------------
    # Stage 3 -- Purpose (N axis)
    # Cost/energy: value pressure moves belief to directed purpose.
    # ----------------------------------------------------------------
    emotional_state: Dict[str, Any] = field(default_factory=dict)
    surface_reactive_emotion: Dict[str, Any] = field(default_factory=dict)
    deep_emotional_state: Dict[str, Any] = field(default_factory=dict)
    polarity_gradient: Dict[str, Any] = field(default_factory=dict)
    goal_stack: List[str] = field(default_factory=list)
    intent: str = "general"
    axis_activation: Dict[str, float] = field(default_factory=dict)
    dominant_axis: str = "X"

    # ----------------------------------------------------------------
    # Stage 4 -- Meaning (B axis)
    # Boundary: conflict between goals determines what falls within
    # the boundary of significance -- what carries weight.
    # ----------------------------------------------------------------
    meaning_forms: List[Dict[str, Any]] = field(default_factory=list)
    dominant_meaning_form: Dict[str, Any] = field(default_factory=dict)
    salient_concepts: List[str] = field(default_factory=list)
    semantic_pressure: float = 0.0
    a_dominant: bool = False           # True when A-axis > 0.65 -- full-agency field response

    # ----------------------------------------------------------------
    # Stage 5 -- Understanding (A axis) -- THE APEX
    # Agency: integration pressure across domains -> cross-domain
    # consistency -> direction.
    # ----------------------------------------------------------------
    understanding_observation: Dict[str, Any] = field(default_factory=dict)
    developmental_stage: Dict[str, Any] = field(default_factory=dict)
    learned_hints: List[str] = field(default_factory=list)
    noncomp_input_state: Dict[str, Any] = field(default_factory=dict)
    noncomp_output_state: Dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # Downward pass / Communication output (filled by stages 5 -> 1)
    # These fields are what AURORA produces (perspective="self").
    # ----------------------------------------------------------------
    response_content: str = ""
    response_tone: str = "neutral"
    response_confidence: float = 0.5
    response_src: str = "chain"

    # Flags propagated to resp_A
    skip_exchange_record: bool = False
    skip_cross_learning: bool = False
    defer_save: bool = False

    # Quasiarch events accumulated during the pass
    quasiarch_events: List[Dict[str, Any]] = field(default_factory=list)

    # ----------------------------------------------------------------
    # Two-chain perception
    # perspective="self"  => normal self-pipeline
    # perspective="other" => downward chain deconstructs another's output;
    #                        other_model holds the inferred reasoning chain
    # ----------------------------------------------------------------
    perspective: str = "self"
    other_model: Dict[str, Any] = field(default_factory=dict)
    # other_model is populated by _run_observation_pipeline:
    # {
    #   "inferred_understanding": str   -- what A-axis intent drove their output
    #   "inferred_meaning":       list  -- what they considered salient (B-axis)
    #   "inferred_purpose":       str   -- what goal/cost drove them (N-axis)
    #   "inferred_belief":        dict  -- what temporal patterns they relied on (T-axis)
    #   "inferred_information":   list  -- what they selected to actually say (X-axis)
    #   "divergence_map":         dict  -- per-axis delta between their model and Aurora's
    # }
