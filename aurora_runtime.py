#!/usr/bin/env python3
"""
AURORA UNIFIED RUNTIME & SIMULATION ORCHESTRATOR
=================================================
Module: aurora_runtime.py
Layer: Runtime Shell (wraps L-1 through L8 + Evolutionary Chain)

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026

PURPOSE
-------
This is the single entry point for running Aurora's living, interactive
universe — combining the full L-1 through L8 behavioral stack with the
evolutionary constraint chain (EvolutionaryChamber + ConstraintGenealogyLogger)
into one governed runtime.

DOCTRINE
--------
  • No cheating. No layer skipping.
  • Every steering action goes through constraint physics before it touches
    the simulation. The chamber decides what relief is real.
  • Promoted Links feed the simulation as lawful behavioral stimuli,
    not raw results injected from outside.
  • Simulation episode fitness feeds back as real pressure events
    into the chain — the universe is one system.
  • Operator pressure gradients (NC[C][OPERATOR]) are the canonical source
    of cross-dimensional pressure. The REGISTRY owns that physics.

ARCHITECTURE
------------
  L-1 aurora_constraint_manifold_patched  Constraint, ConstraintVector, RecursionLevel
  L-0.5 aurora_noncomp_registry           REGISTRY, NonCompRegistry, SystemConstraintStates
  L0  foundational_contract               FoundationalContract, ExistenceMode
                                          OntologicalClaim, OntologicalViolation
  L1  aurora_ivm                          IVMLattice, ToroidalVertexSystem,
                                          RecursionLevel, ALIGNMENT_VOTE_WEIGHT,
                                          AXIS_ORDER, IVMNode, IVMEnvelope
  L1.5 aurora_polarity_gradient           PolarityGradientSensor, GradientChainMiner
                                          PolarityGradientReport
  L1.6 aurora_difference_buffer           DifferenceHistoryBuffer, DifferenceSnapshot
                                          make_difference_buffer
  L1.7 aurora_cost_diff_score             OP_PRESSURE_WEIGHTS, cross_dim_amplifier,
                                          per_operator_pressure, score_from_cost,
                                          CostDiffScore, MAX_AMPLIFIER
  L2  aurora_dimensional_systems          DimensionalSystems
  L5  aurora_expression_perception        ExpressionPerceptionEngine
  L6  aurora_behavioral_identity          BehavioralIdentityEngine, DNASystem
  L7  aurora_simulation_engine            SimulationEngine, TimeDilationGovernor,
                                          StabilityMetrics, StabilityState,
                                          EpisodeResult, ConsciousLearner
  EVO aurora_evolution_chamber            EvolutionaryChamber, ActionTrace, WorldConstants
  GEN constraint_genealogy                ConstraintGenealogyLogger, GenealogyConfig,
                                          ChainSummaryPrinter, AbilityProfile,
                                          TraceItem, PressureVec
  CKP aurora_checkpoint                   CheckpointManager

CLASSES
-------
  StackSystems       — typed container for all booted layer objects
  ChainSimBridge     — translates promoted Links → simulation stimuli
                       through contract validation (no shortcuts)
  UniverseSteerer    — user-facing steering interface
  AuroraRuntime      — master orchestrator (boot, tick, save, status)
  RuntimeCLI         — interactive terminal loop

USAGE
-----
  python3 aurora_runtime.py
  python3 aurora_runtime.py --mode watch
  python3 aurora_runtime.py --mode burn  --chain-ticks 5000 --sim-epochs 2
  python3 aurora_runtime.py --mode steer                  # interactive
  python3 aurora_runtime.py --mode test                   # self-checks
  python3 aurora_runtime.py --out my_run --state my_state
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import py_compile
import re
import signal
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, FrozenSet, Iterable, List, Optional, Tuple

try:
    from aurora_internal.lineage_canonical import constraints_for_operation as _canonical_constraints_for_operation
except Exception:
    def _canonical_constraints_for_operation(op_name: str, axis: Optional[str] = None,
                                             requires: Optional[Iterable[str]] = None,
                                             effect_tags: Optional[Iterable[str]] = None) -> Tuple[str, ...]:
        return tuple()

try:
    from aurora_internal.aurora_recommendation_hub import enqueue_recommendation as _enqueue_recommendation
except Exception:
    _enqueue_recommendation = None

# =============================================================================
# PATH SETUP
# =============================================================================

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in [_HERE, os.path.join(_HERE, "aurora")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# =============================================================================
# LAYER IMPORTS  (fail loudly with clear diagnostics)
# =============================================================================

def _require(module: str, names: List[str]) -> Dict[str, Any]:
    """Import names from module; raise ImportError with a clear message."""
    try:
        import importlib
        mod = importlib.import_module(module)
        return {n: getattr(mod, n) for n in names}
    except (ImportError, AttributeError) as exc:
        print(f"\n[FATAL] Cannot import {names} from '{module}': {exc}")
        print(f"        Make sure aurora_runtime.py is in the project directory.\n")
        raise


def _soft(module: str, names: List[str]) -> Dict[str, Any]:
    """Import softly — returns empty dict on failure (non-fatal)."""
    try:
        import importlib
        mod = importlib.import_module(module)
        return {n: getattr(mod, n) for n in names}
    except Exception:
        return {}


# — L-1: Constraint Manifold --------------------------------------------------
_LM1 = _soft("aurora_internal.aurora_constraint_manifold_patched", [
    "Constraint", "ConstraintVector", "ManifoldViolation",
    "RecursionLevel", "CompositionalSpace", "State",
])
Constraint           = _LM1.get("Constraint")
ConstraintVector     = _LM1.get("ConstraintVector")
ManifoldViolation    = _LM1.get("ManifoldViolation")

# — L-0.5: Non-Comp Registry --------------------------------------------------
_LNCR = _soft("aurora_internal.aurora_noncomp_registry", [
    "REGISTRY", "NonCompRegistry", "NonCompDimension",
    "SystemConstraintStates", "ConstraintState",
    "LAYER_COST", "OPERATOR_PARAMS", "POLARITY_PARAMS",
    "DIFFERENCE_PARAMS",
])
REGISTRY               = _LNCR.get("REGISTRY")
NonCompRegistry        = _LNCR.get("NonCompRegistry")
SystemConstraintStates = _LNCR.get("SystemConstraintStates")
ConstraintState        = _LNCR.get("ConstraintState")

# — L0: Foundational Contract -------------------------------------------------
_L0 = _require("foundational_contract", [
    "FoundationalContract", "ExistenceMode",
    "OntologicalClaim", "OntologicalViolation",
    "ExistenceProfile", "ExistencePredicate",
])
FoundationalContract = _L0["FoundationalContract"]
ExistenceMode        = _L0["ExistenceMode"]
OntologicalClaim     = _L0["OntologicalClaim"]
OntologicalViolation = _L0["OntologicalViolation"]
ExistenceProfile     = _L0["ExistenceProfile"]
ExistencePredicate   = _L0["ExistencePredicate"]

# — L1: IVM Lattice -----------------------------------------------------------
_L1 = _require("aurora_ivm", [
    "IVMLattice", "IVMNode", "IVMEnvelope", "IVMCoordinate",
    "RecursionLevel", "ToroidalVertexSystem", "ToroidalAxis",
    "ALIGNMENT_VOTE_WEIGHT", "AXIS_ORDER", "LEVEL_TO_AXIS",
    "REACT_GAIN", "ALIGN_GAIN",
])
IVMLattice            = _L1["IVMLattice"]
IVMNode               = _L1["IVMNode"]
IVMEnvelope           = _L1["IVMEnvelope"]
IVMCoordinate         = _L1["IVMCoordinate"]
RecursionLevel        = _L1["RecursionLevel"]
ToroidalVertexSystem  = _L1["ToroidalVertexSystem"]
ToroidalAxis          = _L1["ToroidalAxis"]
ALIGNMENT_VOTE_WEIGHT = _L1["ALIGNMENT_VOTE_WEIGHT"]
AXIS_ORDER            = _L1["AXIS_ORDER"]
LEVEL_TO_AXIS         = _L1["LEVEL_TO_AXIS"]
REACT_GAIN            = _L1["REACT_GAIN"]
ALIGN_GAIN            = _L1["ALIGN_GAIN"]

# — L1.5: Polarity Gradient ---------------------------------------------------
_L1P = _soft("aurora_internal.aurora_polarity_gradient", [
    "PolarityGradientSensor", "GradientChainMiner", "PolarityGradientReport",
    "PolarityGradientSensor", "SCALE_SEQUENCE", "AUTHORITY_DIFFERENTIAL",
])
PolarityGradientSensor  = _L1P.get("PolarityGradientSensor")
GradientChainMiner      = _L1P.get("GradientChainMiner")
PolarityGradientReport  = _L1P.get("PolarityGradientReport")

# — L1.6/L1.7: Constraint Stack (combined facade) ----------------------------
_L1S = _soft("aurora_constraint_stack", [
    "DifferenceHistoryBuffer", "DifferenceSnapshot", "make_difference_buffer",
    "OP_PRESSURE_WEIGHTS", "cross_dim_amplifier", "per_operator_pressure", "pressure_mutation_state",
    "score_from_cost", "CostDiffScore", "MAX_AMPLIFIER",
    "dominant_pressure_axis", "pressure_description", "OPERATOR_PRESSURE_NAMES",
])
if not _L1S:
    # Backward-compatible fallback
    _L1D = _soft("aurora_difference_buffer", [
        "DifferenceHistoryBuffer", "DifferenceSnapshot", "make_difference_buffer",
    ])
    _L1C = _soft("aurora_cost_diff_score", [
        "OP_PRESSURE_WEIGHTS", "cross_dim_amplifier", "per_operator_pressure", "pressure_mutation_state",
        "score_from_cost", "CostDiffScore", "MAX_AMPLIFIER",
        "dominant_pressure_axis", "pressure_description", "OPERATOR_PRESSURE_NAMES",
    ])
    _L1S = dict(_L1D)
    _L1S.update(_L1C)

DifferenceHistoryBuffer = _L1S.get("DifferenceHistoryBuffer")
DifferenceSnapshot      = _L1S.get("DifferenceSnapshot")
make_difference_buffer  = _L1S.get("make_difference_buffer")
OP_PRESSURE_WEIGHTS     = _L1S.get("OP_PRESSURE_WEIGHTS")
cross_dim_amplifier     = _L1S.get("cross_dim_amplifier")
per_operator_pressure   = _L1S.get("per_operator_pressure")
pressure_mutation_state = _L1S.get("pressure_mutation_state")
score_from_cost         = _L1S.get("score_from_cost")
CostDiffScore           = _L1S.get("CostDiffScore")
MAX_AMPLIFIER           = _L1S.get("MAX_AMPLIFIER")
dominant_pressure_axis  = _L1S.get("dominant_pressure_axis")

# — L2: Dimensional Systems ---------------------------------------------------
_L2 = _soft("aurora_dimensional_systems", [
    "DimensionalSystems", "EnergyRegulatorSystem",
    "CrystalProcessingSystem", "MemoryConstantSystem",
    "MoralityMortalitySystem", "EvolutionTracker",
])
DimensionalSystems       = _L2.get("DimensionalSystems")
EnergyRegulatorSystem    = _L2.get("EnergyRegulatorSystem")

# — L5: Expression / Perception -----------------------------------------------
_L5 = _soft("aurora_expression_perception", [
    "ExpressionPerceptionEngine", "ImpressionCascade", "ExpressionEcology",
    "LexicalMemory", "WisdomStore",
])
ExpressionPerceptionEngine = _L5.get("ExpressionPerceptionEngine")
ImpressionCascade          = _L5.get("ImpressionCascade")
ExpressionEcology          = _L5.get("ExpressionEcology")

# — L6: Behavioral Identity ---------------------------------------------------
_L6 = _soft("aurora_behavioral_identity", [
    "BehavioralIdentityEngine", "DNASystem", "BehavioralTrait",
    "BehavioralFacet", "AuroraGenome",
])
BehavioralIdentityEngine = _L6.get("BehavioralIdentityEngine")
DNASystem                = _L6.get("DNASystem")
BehavioralTrait          = _L6.get("BehavioralTrait")

# — L7: Simulation Engine -----------------------------------------------------
_L7 = _soft("aurora_simulation_engine", [
    "SimulationEngine", "TimeDilationGovernor", "StabilityMetrics",
    "StabilityState", "EpisodeResult", "ConsciousLearner",
    "SimulationSession", "UnderstandingShard", "InceptionEntity",
    "EntityDepth",
])
SimulationEngine      = _L7.get("SimulationEngine")
TimeDilationGovernor  = _L7.get("TimeDilationGovernor")
StabilityMetrics      = _L7.get("StabilityMetrics")
StabilityState        = _L7.get("StabilityState")
EpisodeResult         = _L7.get("EpisodeResult")
ConsciousLearner      = _L7.get("ConsciousLearner")
SimulationSession     = _L7.get("SimulationSession")
InceptionEntity       = _L7.get("InceptionEntity")
EntityDepth           = _L7.get("EntityDepth")

# — L4: Consciousness / DPME bridge ------------------------------------------
_L4 = _soft("aurora_consciousness_engine", ["set_external_pressure_guidance"])
set_external_pressure_guidance = _L4.get("set_external_pressure_guidance")

# — Evolutionary Chain --------------------------------------------------------
_EVOC = _require("aurora_internal.aurora_evolution_chamber", [
    "EvolutionaryChamber", "ActionTrace", "WorldConstants",
    "EvolutionChamberV3", "NonCompViolation", "ViolationRecord",
    "EnergyBudget",
])
EvolutionaryChamber = _EVOC["EvolutionaryChamber"]
EvolutionChamberV3  = _EVOC["EvolutionChamberV3"]
ActionTrace         = _EVOC["ActionTrace"]
WorldConstants      = _EVOC["WorldConstants"]
NonCompViolation    = _EVOC["NonCompViolation"]
EnergyBudget        = _EVOC["EnergyBudget"]

_GEN = _require("aurora_evolution_stack", [
    "ConstraintGenealogyLogger", "GenealogyConfig", "ChainSummaryPrinter",
    "AbilityProfile", "TraceItem", "PressureVec", "ReliefRecord",
    "ConstraintLink", "PairStats", "GenealogyDilationGovernor",
])
ConstraintGenealogyLogger = _GEN["ConstraintGenealogyLogger"]
GenealogyConfig           = _GEN["GenealogyConfig"]
ChainSummaryPrinter       = _GEN["ChainSummaryPrinter"]
AbilityProfile            = _GEN["AbilityProfile"]
TraceItem                 = _GEN["TraceItem"]
PressureVec               = _GEN["PressureVec"]
ReliefRecord              = _GEN["ReliefRecord"]
ConstraintLink            = _GEN["ConstraintLink"]

# — Code Evolution -------------------------------------------------------------
_CEVO = _soft("aurora_code_evolution_stack", [
    "CodeConstraintEvaluator", "CodeEvolutionChamber", "CodeEvolutionConfig",
    "CodeMutationTrace", "CodePressureSnapshot", "CodePressureVec",
])
CodeEvolutionChamber = _CEVO.get("CodeEvolutionChamber")
CodeMutationTrace    = _CEVO.get("CodeMutationTrace")

_CMOP = _soft("aurora_internal.aurora_code_mutation_operators", [
    "CodeMutationOperator", "list_operator_specs", "get_operator",
])
list_operator_specs = _CMOP.get("list_operator_specs")
get_operator        = _CMOP.get("get_operator")

_CAEV = _soft("aurora_internal.aurora_code_autoevolver", ["CodeAutoEvolver"])
CodeAutoEvolver = _CAEV.get("CodeAutoEvolver")

# — Checkpoint ----------------------------------------------------------------
_CKP = _soft("aurora_checkpoint", ["CheckpointManager"])
CheckpointManager = _CKP.get("CheckpointManager")


# =============================================================================
# CONSTANTS
# =============================================================================

# The five lawful constraint axis labels — IVM-style lowercase full strings.
# These are the keys used in ActionTrace.constraints_used frozensets,
# IVM stimulus labels, and the bridge axis mapping.
AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_IVM_AXIS_LABELS: Tuple[str, ...] = ("existence", "temporal", "energy", "boundary", "agency")
_AXIS_TO_IVM: Dict[str, str] = dict(zip(AXES, _IVM_AXIS_LABELS))
_IVM_TO_AXIS: Dict[str, str] = dict(zip(_IVM_AXIS_LABELS, AXES))

_CONSTRAINT_TO_DER_CHANNEL = {
    "X": "vitality",
    "T": "processing",
    "N": "memory",
    "B": "emotional",
    "A": "creative",
}

_VERSION = "2.0.0"

CONFLICT_LANES: Tuple[str, ...] = ("intelligence", "communication", "meaning")
CONFLICT_LANE_CONSTRAINTS: Dict[str, FrozenSet[str]] = {
    "intelligence": frozenset({"existence", "temporal", "agency"}),
    "communication": frozenset({"agency", "boundary", "temporal"}),
    "meaning": frozenset({"existence", "agency", "boundary"}),
}
PATH_TARGET_WEIGHTS: Dict[str, float] = {
    "intelligence": 1.0,
    "communication": 1.0,
    "meaning": 1.0,
}

AXIS_SEMANTIC_CORE: Dict[str, str] = {
    "X": "world-model grounding and admissibility",
    "T": "sequencing, timing, and conversational coherence",
    "N": "energy efficiency and cognitive load regulation",
    "B": "boundary clarity and interface precision",
    "A": "agency, intent shaping, and directed action",
}

AXIS_TO_PATH_IMPACT: Dict[str, Dict[str, float]] = {
    "X": {"intelligence": 0.85, "communication": 0.35, "meaning": 0.70},
    "T": {"intelligence": 0.75, "communication": 0.80, "meaning": 0.45},
    "N": {"intelligence": 0.65, "communication": 0.30, "meaning": 0.55},
    "B": {"intelligence": 0.40, "communication": 0.85, "meaning": 0.75},
    "A": {"intelligence": 0.70, "communication": 0.70, "meaning": 0.85},
}

PLATEAU_METRIC_CONSTRAINTS: Dict[str, FrozenSet[str]] = {
    "relief": frozenset({"energy", "boundary"}),
    "bridge": frozenset({"boundary", "temporal", "agency"}),
    "fitness": frozenset({"existence", "temporal", "agency"}),
    "links_total": frozenset({"boundary", "temporal", "agency"}),
    "abilities_total": frozenset({"existence", "temporal", "agency"}),
}

LINKS_STAGNATION_TICKS: int = 500
ABILITIES_STAGNATION_TICKS: int = 500
BRIDGE_STAGNATION_EPOCHS: int = 4
OPERATOR_GRADIENTS_FILE: str = "operator_gradients.json"

# Base five-constraint ancestry set (IVM labels)
_BASE_CONSTRAINT_ANCESTRY: FrozenSet[str] = frozenset(_IVM_AXIS_LABELS)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return bool(default)
    return raw in {"1", "true", "yes", "on", "strict"}


def _env_float(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _normalize_ancestry_constraints(constraints: Optional[Iterable[str]]) -> FrozenSet[str]:
    """Normalize + validate ancestry labels against the base five constraints."""
    if not constraints:
        return frozenset()
    out = []
    valid = set(_IVM_AXIS_LABELS)
    for c in constraints:
        label = str(c).strip().lower()
        if label in valid:
            out.append(label)
    return frozenset(sorted(set(out)))


_LINEAGE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "existence": ("exist", "admit", "state", "being", "presence", "identity"),
    "temporal": ("time", "tempo", "tick", "phase", "sequence", "order", "defer", "batch"),
    "energy": ("energy", "cost", "budget", "effort", "load", "compute", "memory"),
    "boundary": ("boundary", "limit", "partition", "interface", "separate", "seal", "scope"),
    "agency": ("agency", "intent", "choice", "act", "commit", "direct", "control"),
}


def _synthesize_lineage(constraints: Optional[Iterable[str]], hint_text: str = "") -> FrozenSet[str]:
    """Infer base-constraint lineage when labels are undefined."""
    normalized = _normalize_ancestry_constraints(constraints)
    if normalized:
        return normalized

    source_parts: List[str] = [str(c) for c in (constraints or [])]
    if hint_text:
        source_parts.append(str(hint_text))
    text = " ".join(source_parts).lower()

    inferred: List[str] = []
    for axis, keywords in _LINEAGE_KEYWORDS.items():
        if any(k in text for k in keywords):
            inferred.append(axis)

    if inferred:
        return frozenset(sorted(set(inferred)))

    # Hard floor: if we cannot infer, keep lineage attached to the base manifold.
    return _BASE_CONSTRAINT_ANCESTRY


def _constraint_effect_descriptor_label(label: str) -> str:
    """Canonical per-constraint effect descriptor token for combo identifiers."""
    axis = _IVM_TO_AXIS.get(str(label).strip().lower(), "")
    semantic = AXIS_SEMANTIC_CORE.get(axis, str(label).strip().lower())
    token = "".join(ch if (ch.isalnum() or ch == " ") else " " for ch in semantic.lower())
    token = "_".join(part for part in token.split() if part)
    return token or "unspecified"


def _semantic_constraint_combo_id(constraints: FrozenSet[str]) -> str:
    """Deterministic semantic combo id: constraint(effect_descriptor)+..."""
    ordered = sorted(_normalize_ancestry_constraints(constraints))
    if not ordered:
        return "none"
    parts = []
    for lbl in ordered:
        parts.append(f"{lbl}({_constraint_effect_descriptor_label(lbl)})")
    return "+".join(parts)


def _stamp_ancestry_meta(
    meta: Optional[Dict[str, Any]],
    constraints: FrozenSet[str],
    source_fn: str,
    parent_links: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Attach explicit constraint ancestry metadata to an operation trace."""
    m = dict(meta or {})
    ancestry = _normalize_ancestry_constraints(constraints)
    ancestry_sorted = sorted(ancestry)
    parent_ids = [str(x) for x in (parent_links or []) if x]

    # Canonical semantic combination identifier for this operation.
    combo_text = _semantic_constraint_combo_id(ancestry)
    lineage_raw = f"{source_fn}|{combo_text}|{'|'.join(parent_ids)}"
    lineage_id = "OP:" + hashlib.sha1(lineage_raw.encode()).hexdigest()[:12]

    m["constraint_ancestry"] = ancestry_sorted
    m["constraint_combo_id"] = combo_text
    m["operation_lineage_id"] = lineage_id
    m["ancestry_source_fn"] = source_fn
    if parent_ids:
        m["ancestry_parent_links"] = parent_ids
    return m

# =============================================================================
# DEFAULT ACTION CYCLE
# =============================================================================

# Covers all 5 constraint axes in varied pairings — 16 actions cycling ensures
# all pair combinations accumulate at different rates so the genealogy promoter
# has signal to work with. These are lawful stimuli only. The chamber decides
# what happens. You cannot fake relief.

DEFAULT_ACTION_CYCLE: List[ActionTrace] = [
    # A+B pairings (communication / outlet axis)
    ActionTrace("communicate",    frozenset({"agency", "boundary", "temporal"}),
                meta={"episode": "communication"}),
    ActionTrace("release_outlet", frozenset({"agency", "boundary"}),
                meta={"pulse": True, "episode": "outlet"}),
    # X+A pairings (admission / commit axis)
    ActionTrace("admit_state",    frozenset({"existence", "agency"}),
                meta={"episode": "admission"}),
    ActionTrace("commit_choice",  frozenset({"agency", "existence", "temporal"}),
                meta={"episode": "commit"}),
    # T+N pairings (temporal / energy axis)
    ActionTrace("defer_work",     frozenset({"temporal", "energy"}),
                meta={"episode": "deferral"}),
    ActionTrace("batch_process",  frozenset({"temporal", "energy", "boundary"}),
                meta={"episode": "batch"}),
    # B+X pairings (boundary / existence axis)
    ActionTrace("seal_boundary",  frozenset({"boundary", "existence"}),
                meta={"episode": "sealing"}),
    ActionTrace("separate",       frozenset({"boundary", "existence", "temporal"}),
                meta={"episode": "separation"}),
    # N+B pairings (energy / boundary axis)
    ActionTrace("reuse_cache",    frozenset({"energy", "boundary"}),
                meta={"episode": "reuse"}),
    ActionTrace("spend_energy",   frozenset({"energy", "agency"}),
                meta={"episode": "spend"}),
    # X+T pairings (admissibility / time axis)
    ActionTrace("reorder",        frozenset({"existence", "temporal"}),
                meta={"episode": "reorder"}),
    ActionTrace("resolve",        frozenset({"existence", "temporal", "boundary"}),
                meta={"episode": "resolve"}),
    # All-axis stimulation (full pressure sweep)
    ActionTrace("full_assert",    frozenset({"existence", "temporal", "energy", "boundary", "agency"}),
                meta={"pulse": True, "episode": "assert"}),
    ActionTrace("full_commit",    frozenset({"existence", "temporal", "energy", "boundary", "agency"}),
                meta={"episode": "full_commit"}),
    # Single-axis probes (isolate individual constraint dynamics)
    ActionTrace("pure_agency",    frozenset({"agency"}),
                meta={"episode": "agency_probe"}),
    ActionTrace("pure_boundary",  frozenset({"boundary"}),
                meta={"episode": "boundary_probe"}),
]


# =============================================================================
# STACK SYSTEMS — typed container
# =============================================================================

@dataclass
class StackSystems:
    """
    Container for every booted layer object.
    Presence of a field does not guarantee non-None — soft imports may fail.
    Always check `systems.has(name)` before use.
    """
    run_id: str = ""

    # Hard (required) layers
    contract:      Optional[FoundationalContract]      = None   # L0
    lattice:       Optional[IVMLattice]                = None   # L1

    # Soft layers
    dimensional:   Optional[Any] = None   # L2  DimensionalSystems
    perception:    Optional[Any] = None   # L5  ExpressionPerceptionEngine
    identity:      Optional[Any] = None   # L6  BehavioralIdentityEngine
    simulation:    Optional[Any] = None   # L7  SimulationEngine
    evolved_surfaces: Optional[Any] = None

    # Experiential intake pipeline (Steps 9-14)
    accountant:        Optional[Any] = None
    bias_engine:       Optional[Any] = None
    metabolizer:       Optional[Any] = None
    worth_eval:        Optional[Any] = None
    solidification:    Optional[Any] = None
    variant_promoter:  Optional[Any] = None
    strand_lib:        Optional[Any] = None
    strand_builder:    Optional[Any] = None

    # Auxiliary cognition modules
    entropy_detector:         Optional[Any] = None
    primitive_extractor:      Optional[Any] = None
    comprehension_gap_system: Optional[Any] = None
    attention_engine:         Optional[Any] = None
    braided_substrate:        Optional[Any] = None
    language_orchestra:       Optional[Any] = None

    # Evolutionary chain (required)
    chamber:       Optional[EvolutionaryChamber]          = None
    genealogy:     Optional[ConstraintGenealogyLogger]    = None
    printer:       Optional[ChainSummaryPrinter]          = None

    # Checkpoint (optional)
    checkpoint:    Optional[Any] = None

    def has(self, name: str) -> bool:
        return getattr(self, name, None) is not None

    def layer_status(self) -> Dict[str, str]:
        mapping = {
            "L-0.5  NonCompRegistry":       "registry_active",   # checked via REGISTRY global
            "L0     FoundationalContract":  "contract",
            "L1     IVMLattice":            "lattice",
            "L2     DimensionalSystems":    "dimensional",
            "L5     ExpressionPerception":  "perception",
            "L6     BehavioralIdentity":    "identity",
            "L7     SimulationEngine":      "simulation",
            "EVO-CODE Evolved Surfaces":    "evolved_surfaces",
            "STEP9-14 Intake Pipeline":     "metabolizer",
            "AUX    Cognition Modules":     "entropy_detector",
            "EVO    EvolutionaryChamber":   "chamber",
            "GEN    ConstraintGenealogy":   "genealogy",
        }
        status = {}
        for label, attr in mapping.items():
            if attr == "registry_active":
                status[label] = "✓ ACTIVE" if REGISTRY is not None else "✗ MISSING"
            else:
                status[label] = "✓ ACTIVE" if self.has(attr) else "✗ MISSING"
        return status

    def pressure_snapshot(self) -> Optional[Any]:
        """
        Return the most recent DifferenceSnapshot from the chamber's buffer
        if available. Used for live cost-diff scoring across the whole stack.
        """
        if not self.has("chamber"):
            return None
        buf: Optional[DifferenceHistoryBuffer] = getattr(self.chamber, "_diff_buffer", None)
        if buf is None or not buf.is_warm():
            return None
        return buf.snapshot()


# =============================================================================
# BOOT STACK
# =============================================================================

def _restore_genealogy_state(
    logger: ConstraintGenealogyLogger,
    output_dir: str,
    verbose: bool = False,
) -> Dict[str, int]:
    """Restore persisted genealogy state (abilities + links + counters) if present."""
    restored = {"abilities": 0, "links": 0, "events": 0}

    # abilities.json
    abilities_path = os.path.join(output_dir, getattr(logger.cfg, "ABILITIES_FILE", "abilities.json"))
    if os.path.exists(abilities_path):
        try:
            with open(abilities_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            loaded: Dict[str, AbilityProfile] = {}
            for aid, rec in (raw or {}).items():
                if not isinstance(rec, dict):
                    continue
                loaded[str(aid)] = AbilityProfile(
                    id=str(rec.get("id", aid)),
                    axis=str(rec.get("axis", "X")),
                    requires=tuple(rec.get("requires", [])),
                    cost={a: float((rec.get("cost", {}) or {}).get(a, 0.0)) for a in AXES},
                    risk={a: float((rec.get("risk", {}) or {}).get(a, 0.0)) for a in AXES},
                    effect_tags=tuple(rec.get("effect_tags", [])),
                    notes=str(rec.get("notes", "")),
                )
            if loaded:
                logger.abilities = loaded
                normalize = getattr(logger, "normalize_ability_origins", None)
                if callable(normalize):
                    try:
                        normalize()
                    except Exception:
                        pass
            restored["abilities"] = len(getattr(logger, "abilities", {}))
        except Exception:
            pass

    # links.json
    links_path = os.path.join(output_dir, getattr(logger.cfg, "LINKS_FILE", "links.json"))
    if os.path.exists(links_path):
        try:
            with open(links_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            links_loaded: Dict[str, ConstraintLink] = {}
            links_by_parents: Dict[Tuple[str, str], str] = {}
            max_created = 0
            for lid, rec in (raw or {}).items():
                if not isinstance(rec, dict):
                    continue
                stats = rec.get("stats", {}) or {}
                link = ConstraintLink(
                    id=str(rec.get("id", lid)),
                    parents=[str(x) for x in (rec.get("parents", []) or [])],
                    depth=int(rec.get("depth", 1) or 1),
                    created_at_tick=int(rec.get("created_at_tick", 0) or 0),
                    count=int(stats.get("count", 0) or 0),
                    mean_relief={a: float((stats.get("mean_relief", {}) or {}).get(a, 0.0)) for a in AXES},
                    mean_cost={a: float((stats.get("mean_cost", {}) or {}).get(a, 0.0)) for a in AXES},
                    mean_x_risk=float(stats.get("mean_x_risk", 0.0) or 0.0),
                    stdev_relief={a: float((stats.get("stdev_relief", {}) or {}).get(a, 0.0)) for a in AXES},
                    dominant_relief_axis=(str(rec.get("dominant_relief_axis")) if rec.get("dominant_relief_axis") is not None else None),
                    tags=[str(x) for x in (rec.get("tags", []) or [])],
                )
                links_loaded[link.id] = link
                if len(link.parents) == 2:
                    links_by_parents[(link.parents[0], link.parents[1])] = link.id
                if link.created_at_tick > max_created:
                    max_created = link.created_at_tick

            if links_loaded:
                logger.links = links_loaded
                logger._links_by_parents = links_by_parents
                logger.links_promoted = len(links_loaded)
                logger._last_promotion_tick = int(max_created)

                # Ensure every promoted link is also represented as a derived ability
                # when the genealogy implementation supports that mapping.
                reg_link_ability = getattr(logger, "_register_link_ability", None)
                if callable(reg_link_ability):
                    for lnk in links_loaded.values():
                        try:
                            reg_link_ability(lnk)
                        except Exception:
                            continue

            restored["links"] = len(getattr(logger, "links", {}))
            restored["abilities"] = len(getattr(logger, "abilities", {}))
        except Exception:
            pass

    # couplings.json (canonical coupling roots + persistent pressure root state)
    couplings_path = os.path.join(output_dir, getattr(logger.cfg, "COUPLINGS_FILE", "couplings.json"))
    if os.path.exists(couplings_path):
        try:
            with open(couplings_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh) or {}
            roots = raw.get("roots", {}) if isinstance(raw, dict) else {}
            origin_counts = raw.get("origin_counts", {}) if isinstance(raw, dict) else {}
            if isinstance(roots, dict):
                logger._coupling_roots = {str(k): dict(v) for k, v in roots.items() if isinstance(v, dict)}
            if isinstance(origin_counts, dict):
                logger._coupling_origin_counts = defaultdict(int, {str(k): int(v or 0) for k, v in origin_counts.items()})
            logger._coupling_events = int(raw.get("coupling_events", 0) or 0)
            logger._persistent_pressure_root_ema = float(raw.get("persistent_pressure_root_ema", 0.0) or 0.0)
            experiments = raw.get("experiments", {}) if isinstance(raw, dict) else {}
            if isinstance(experiments, dict):
                trials = experiments.get("trials", [])
                adoptions = experiments.get("adoptions", [])
                if isinstance(trials, list):
                    logger._experiment_trials = [dict(t) for t in trials if isinstance(t, dict)]
                if isinstance(adoptions, list):
                    logger._experiment_adoptions = [dict(a) for a in adoptions if isinstance(a, dict)]
        except Exception:
            pass

    # events counter from JSONL line count (for continuity in reports)
    events_path = os.path.join(output_dir, getattr(logger.cfg, "EVENTS_FILE", "events.jsonl"))
    if os.path.exists(events_path):
        try:
            with open(events_path, "r", encoding="utf-8") as fh:
                lines = sum(1 for _ in fh)
            logger.relief_event_count = int(lines)
            logger.tick_count = max(int(getattr(logger, "tick_count", 0)), int(lines))
            restored["events"] = int(lines)
        except Exception:
            pass

    if verbose:
        print(f"  [RESTORE] Genealogy: abilities={restored['abilities']} links={restored['links']} events={restored['events']}")

    # Restore pair stats — K_MIN accumulation across runs.
    # Must happen after links are restored so already-promoted pairs are excluded.
    if hasattr(logger, "restore_pair_stats"):
        try:
            n_pairs = logger.restore_pair_stats()
            restored["pair_stats"] = n_pairs
            if verbose and n_pairs > 0:
                print(f"  [RESTORE] Pair stats: {n_pairs} pairs resumed")
        except Exception:
            pass

    return restored


def _restore_operator_gradients(
    output_dir: str,
    verbose: bool = False,
) -> Dict[str, float]:
    """Restore persisted NC[C][OPERATOR].pressure_gradient values if present."""
    restored: Dict[str, float] = {ax: 0.0 for ax in AXES}
    if REGISTRY is None or Constraint is None:
        return restored

    path = os.path.join(output_dir, OPERATOR_GRADIENTS_FILE)
    if not os.path.exists(path):
        return restored

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh) or {}
        grads = raw.get("gradients", {}) if isinstance(raw, dict) else {}
        ordered = [Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A]
        for c in ordered:
            ax = c.name
            val = float(grads.get(ax, 0.0))
            REGISTRY.operator(c).pressure_gradient = val
            restored[ax] = val
        if verbose:
            print("  [RESTORE] Operator gradients: " + ", ".join([f"{ax}={restored[ax]:.11f}" for ax in AXES]))
    except Exception:
        pass

    return restored


def _persist_operator_gradients(
    output_dir: str,
    verbose: bool = False,
) -> bool:
    """Persist NC[C][OPERATOR].pressure_gradient values for next boot."""
    if REGISTRY is None or Constraint is None:
        return False

    ordered = [Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A]
    payload = {
        "version": _VERSION,
        "saved_at": time.time(),
        "gradients": {c.name: float(REGISTRY.operator(c).pressure_gradient) for c in ordered},
    }
    path = os.path.join(output_dir, OPERATOR_GRADIENTS_FILE)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=True, indent=2, sort_keys=True)
        if verbose:
            print("[RUNTIME] Operator gradients persisted.")
        return True
    except Exception as e:
        if verbose:
            print(f"[RUNTIME] Operator gradient save failed: {e}")
        return False


def boot_stack(state_dir:  str = "aurora_state",
               output_dir: str = "aurora_runtime_output",
               run_id:     Optional[str] = None,
               verbose:    bool = True) -> StackSystems:
    """
    Boot all layers in canonical order (L-1 → L0 → L1 → L2 → L5 → L6 → L7 → EVO → GEN).

    Hard layers (L0, L1, EVO, GEN) are required and abort boot on failure.
    Soft layers are attempted; failures are reported but do not abort the boot.
    The evolutionary chain always boots because it only requires L0 + L1.

    Returns a fully populated StackSystems container.
    """
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(state_dir,  exist_ok=True)

    systems = StackSystems(run_id=run_id)
    _restored_operator = _restore_operator_gradients(output_dir=output_dir, verbose=verbose)
    systems._boot_metrics = {"restored_operator_gradients": dict(_restored_operator), "restored_genealogy": {"abilities": 0, "links": 0, "events": 0}, "checkpoint_restored": False}

    if verbose:
        print("=" * 70)
        print(f"  AURORA UNIFIED RUNTIME  v{_VERSION}")
        print(f"  Authors: Sunni (Sir) Morningstar and Cael Devo")
        print(f"  Run ID: {run_id}")
        print(f"  Constraints: X (existence) / T (time) / N (energy) / B (boundary) / A (agency)")
        print("=" * 70)
        print()

    def _log(label: str, ok: bool, detail: str = "") -> None:
        if verbose:
            mark   = "✓" if ok else "✗"
            suffix = f"  ({detail})" if detail else ""
            print(f"  [{mark}] {label}{suffix}")

    # — L-0.5: Non-Comp Registry (module-level singleton — no construction) —
    _log("L-0.5  NonCompRegistry (REGISTRY)", REGISTRY is not None,
         (
             "pressure gradients: "
             f"X={REGISTRY.operator(Constraint.X).pressure_gradient:.11f} "
             f"T={REGISTRY.operator(Constraint.T).pressure_gradient:.11f} "
             f"N={REGISTRY.operator(Constraint.N).pressure_gradient:.11f} "
             f"B={REGISTRY.operator(Constraint.B).pressure_gradient:.11f} "
             f"A={REGISTRY.operator(Constraint.A).pressure_gradient:.11f}"
         )
         if REGISTRY is not None and Constraint is not None else "unavailable")

    # — L0: Foundational Contract —
    try:
        systems.contract = FoundationalContract()
        _log("L0     FoundationalContract", True)
    except Exception as e:
        _log("L0     FoundationalContract", False, str(e))
        raise RuntimeError("L0 boot failed — cannot continue") from e

    # — L1: IVM Lattice —
    try:
        systems.lattice = IVMLattice(systems.contract)
        node_count = len(getattr(systems.lattice, "nodes", {}))
        _log("L1     IVMLattice", True, f"nodes={node_count}")
    except Exception as e:
        _log("L1     IVMLattice", False, str(e))
        raise RuntimeError("L1 boot failed — cannot continue") from e

    # Seed the lattice with nodes across all five ExistenceMode levels
    _seed_spec = [
        (ExistenceMode.REFERENCE,   "seed_ref",        8),
        (ExistenceMode.TRANSIENT,   "seed_transient",  10),
        (ExistenceMode.PERSISTENT,  "seed_persistent", 14),
        (ExistenceMode.BOUNDED,     "seed_bounded",    10),
        (ExistenceMode.AGENTIC,     "seed_agentic",    8),
    ]
    _n_seeded = 0
    for _mode, _ptype, _count in _seed_spec:
        for _i in range(_count):
            try:
                systems.lattice.admit_at_mode(
                    payload=f"{_ptype}_{_i}",
                    payload_type=_ptype,
                    mode=_mode,
                    scale=_i % 5,
                )
                _n_seeded += 1
            except Exception:
                pass
    if verbose:
        print(f"  [SEED] Lattice seeded with {_n_seeded} nodes across all 5 ExistenceModes")

    # — L2: Dimensional Systems —
    if DimensionalSystems is not None:
        try:
            systems.dimensional = DimensionalSystems(systems.lattice)
            _log("L2     DimensionalSystems", True,
                 "DPS / DMC / DER / DMM active")
        except Exception as e:
            _log("L2     DimensionalSystems", False, str(e))
    else:
        _log("L2     DimensionalSystems", False, "module not available")

    # — Steps 9-14: Intake Metabolism / Worth / Solidification / Variant / DNA —
    try:
        from aurora_internal.aurora_energy_layer_costs import make_accountant
        from aurora_internal.aurora_leverage_scalar import LeverageBiasEngine
        from aurora_internal.aurora_intake_metabolism import make_metabolizer
        from aurora_internal.aurora_worth_evaluator import make_worth_evaluator
        from aurora_internal.aurora_solidification import make_solidification_pipeline
        from aurora_internal.aurora_variant_promotion import VariantPromoter
        from aurora_internal.aurora_dna_strand_schema import StrandLibrary, StrandBuilder

        systems.accountant = make_accountant(initial_pool=500000.0)
        systems.accountant.tick()
        systems.bias_engine = LeverageBiasEngine()
        systems.metabolizer = make_metabolizer(systems.accountant, systems.bias_engine)
        systems.worth_eval = make_worth_evaluator()
        systems.solidification = make_solidification_pipeline()
        systems.variant_promoter = VariantPromoter()
        systems.strand_lib = StrandLibrary()
        systems.strand_builder = StrandBuilder()
        _log("STEP9-14 Intake Pipeline", True, "metabolize->worth->solidify->variant->DNA")
    except Exception as e:
        _log("STEP9-14 Intake Pipeline", False, str(e))

    # — Auxiliary cognition modules (entropy/awareness/language substrate) —
    try:
        from aurora_internal.aurora_entropy_detector import make_entropy_detector
        from aurora_internal.aurora_comprehension_gap import ComprehensionGapSystem
        from aurora_internal.aurora_attention_engine import AttentionEngine
        from aurora_internal.aurora_braided_substrate import BraidedSubstrateLayer
        from aurora_internal.aurora_language_state import ExpressionEvolutionOrchestra

        systems.entropy_detector = make_entropy_detector()
        systems.comprehension_gap_system = ComprehensionGapSystem()
        systems.attention_engine = AttentionEngine()
        systems.braided_substrate = BraidedSubstrateLayer()
        systems.language_orchestra = ExpressionEvolutionOrchestra()
        _log("AUX    Cognition Modules", True, "entropy+gap+attention+substrate+language online")
    except Exception as e:
        _log("AUX    Cognition Modules", False, str(e))

    # — L5: Expression / Perception —
    if ExpressionPerceptionEngine is not None:
        try:
            systems.perception = ExpressionPerceptionEngine(systems.contract)
            _log("L5     ExpressionPerceptionEngine", True)
        except Exception as e:
            _log("L5     ExpressionPerceptionEngine", False, str(e))
    else:
        _log("L5     ExpressionPerceptionEngine", False, "module not available")

    # — L6: Behavioral Identity —
    if BehavioralIdentityEngine is not None:
        try:
            systems.identity = BehavioralIdentityEngine(systems.contract)
            _log("L6     BehavioralIdentityEngine", True)
        except Exception as e:
            _log("L6     BehavioralIdentityEngine", False, str(e))
    else:
        _log("L6     BehavioralIdentityEngine", False, "module not available")

    # — L7: Simulation Engine —
    if SimulationEngine is not None:
        try:
            systems.simulation = SimulationEngine(
                contract   = systems.contract,
                perception = systems.perception,   # Optional[ExpressionPerceptionEngine]
                identity   = systems.identity,     # Optional[BehavioralIdentityEngine]
            )
            _log("L7     SimulationEngine", True)
        except Exception as e:
            _log("L7     SimulationEngine", False, str(e))
    else:
        _log("L7     SimulationEngine", False, "module not available")

    # — Evolutionary Chain: Genealogy Logger —
    try:
        gen_config    = GenealogyConfig()
        systems.genealogy = ConstraintGenealogyLogger(
            run_id     = run_id,
            config     = gen_config,
            abilities  = {},
            output_dir = output_dir,
        )
        _restored_genealogy = _restore_genealogy_state(systems.genealogy, output_dir=output_dir, verbose=verbose)
        try:
            systems._boot_metrics["restored_genealogy"] = dict(_restored_genealogy)
        except Exception:
            pass
        try:
            if systems.dimensional is not None and hasattr(systems.dimensional, "set_genealogy"):
                systems.dimensional.set_genealogy(systems.genealogy)
        except Exception:
            pass
        systems.printer = ChainSummaryPrinter(systems.genealogy)
        _log("GEN    ConstraintGenealogyLogger", True,
             f"K_MIN={gen_config.K_MIN}  RELIEF_EPS={gen_config.RELIEF_EPS}")
    except Exception as e:
        _log("GEN    ConstraintGenealogyLogger", False, str(e))

    # — Evolutionary Chain: Chamber —
    try:
        systems.chamber = EvolutionaryChamber(
            lattice    = systems.lattice,
            genealogy  = systems.genealogy,
            run_id     = run_id,
            output_dir = output_dir,
        )
        _log("EVO    EvolutionaryChamber", True,
             f"alive={systems.chamber.alive}")
    except Exception as e:
        _log("EVO    EvolutionaryChamber", False, str(e))
        raise RuntimeError("EVO boot failed — chamber is required") from e

    # Primitive extractor depends on live genealogy.
    try:
        from aurora_internal.aurora_primitive_extractor import PrimitiveExtractor
        if systems.genealogy is not None:
            systems.primitive_extractor = PrimitiveExtractor(systems.genealogy)
            _log("AUX    PrimitiveExtractor", True, "genealogy lens active")
        else:
            _log("AUX    PrimitiveExtractor", False, "no genealogy")
    except Exception as e:
        _log("AUX    PrimitiveExtractor", False, str(e))

    # — Checkpoint Manager —
    if CheckpointManager is not None:
        try:
            ckpt_path = os.path.join(state_dir, "runtime_checkpoint.json")
            systems.checkpoint = CheckpointManager(
                checkpoint_path    = ckpt_path,
                save_every_n       = 500,
                save_every_t       = 300.0,
            )
            restored = systems.checkpoint.restore()
            try:
                systems._boot_metrics["checkpoint_restored"] = bool(restored)
            except Exception:
                pass
            if verbose and restored:
                cursor = systems.checkpoint.cursor
                print(f"  [CHECKPOINT] Restored — "
                      f"pass: {getattr(cursor,'pass_name','?')}  "
                      f"items: {getattr(cursor,'total_items_processed','?')}")
            systems.checkpoint.start_auto_save(300.0)
            _log("CKP    CheckpointManager", True)
        except Exception as e:
            _log("CKP    CheckpointManager", False, str(e))

    if verbose:
        print()
        layers_active = sum(
            1 for v in systems.layer_status().values() if "ACTIVE" in v
        )
        total_layers = len(systems.layer_status())
        print(f"  Boot complete: {layers_active}/{total_layers} systems active.")

        # Report operator pressure gradients from NC[C][OPERATOR]
        if REGISTRY is not None and Constraint is not None:
            print()
            print("  OPERATOR PRESSURE GRADIENTS (NC[C][OPERATOR]) — canonical source:")
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
                op   = REGISTRY.operator(c)
                cost = REGISTRY.cost(c)
                print(f"    {c.name}  k={cost.shift_cost_coeff:5.1f}  "
                      f"pressure_gradient={op.pressure_gradient:.11f}  "
                      f"scope={op.scope}  conserved={op.is_conserved}")
        print()

    return systems


# =============================================================================
# CHAIN ↔ SIM BRIDGE
# =============================================================================

class ChainSimBridge:
    """
    Translates promoted Links from the genealogy fossil record into
    lawful stimuli for the SimulationEngine.

    DOCTRINE: No shortcuts. Every promoted Link becomes an ActionTrace that
    re-enters the chamber for one tick before its fitness signal reaches L7.
    The chamber physics — not us — decide if there is real relief to report.
    If there is no simulation engine active, bridge ops are no-ops.

    PRESSURE FEEDBACK:
    When a simulation episode completes, its fitness feeds back into the
    chain as a real ActionTrace pressure event (not injected results).
    The operator pressure gradient snapshot at that moment amplifies
    the moral weight of any variant that was active — exactly as the
    cost-diff score physics specify.
    """

    def __init__(self, systems: StackSystems):
        self._systems                  = systems
        self._injected_link_ids: set   = set()
        self._bridge_events: Deque[Dict[str, Any]] = deque(maxlen=200)
        self.total_link_injections     = 0
        self.total_fitness_feedbacks   = 0
        # Tracks which UnderstandingShard ids have already been forwarded to
        # ExpressionEcology.wisdom — prevents duplicate WisdomShard injection
        # across successive inject_promoted_links() calls.
        self._transferred_shard_ids: Set[str] = set()

    def _trace_with_ancestry(self,
                             trace: ActionTrace,
                             source_fn: str,
                             parent_links: Optional[List[str]] = None) -> ActionTrace:
        ancestry = _normalize_ancestry_constraints(trace.constraints_used)
        meta = _stamp_ancestry_meta(trace.meta, ancestry, source_fn, parent_links)
        return ActionTrace(name=trace.name, constraints_used=trace.constraints_used, meta=meta)

    def _link_tag_value(self, link: ConstraintLink, prefix: str, cast=str, default=None):
        tags = list(getattr(link, "tags", []) or [])
        for t in tags:
            s = str(t)
            if s.startswith(prefix):
                raw = s[len(prefix):]
                try:
                    return cast(raw)
                except Exception:
                    return default
        return default

    def _lineage_operation_priority(self, link: ConstraintLink) -> float:
        """Higher means inject earlier. Earlier and seeded lineages are explicitly favored."""
        overall = float(self._link_tag_value(link, "overall_grade:", cast=float, default=0.5) or 0.5)
        opg = float(self._link_tag_value(link, "operator_grade:", cast=float, default=0.5) or 0.5)
        psg = float(self._link_tag_value(link, "purpose_grade:", cast=float, default=0.5) or 0.5)
        generation = int(self._link_tag_value(link, "generation:", cast=int, default=max(1, int(getattr(link, 'depth', 1) or 1))) or 1)
        depth = max(1, int(getattr(link, "depth", 1) or 1))
        seed_influence = float(
            self._link_tag_value(link, "artificial_seed_influence:", cast=float,
                                 default=self._link_tag_value(link, "seed_influence:", cast=float, default=0.0))
            or 0.0
        )

        # Earlier lineage leverage: lower generation gets higher priority.
        early_factor = 1.0 / (1.0 + (0.18 * max(0, generation - 1)))
        depth_factor = 1.0 / (1.0 + (0.10 * max(0, depth - 1)))
        seed_factor = 1.0 + (0.35 * max(0.0, min(1.0, seed_influence)))
        quality = max(0.0, min(1.0, 0.45 * overall + 0.35 * opg + 0.20 * psg))
        return float(((0.65 * early_factor + 0.35 * depth_factor) * (0.5 + quality)) * seed_factor)

    def _lineage_constraints(self, link: ConstraintLink, base_constraints: FrozenSet[str]) -> FrozenSet[str]:
        """Use lineage operator/purpose/generation tags to shape operation constraints."""
        purpose = str(self._link_tag_value(link, "purpose_lane:", cast=str, default="meaning") or "meaning").strip().lower()
        op_action = str(self._link_tag_value(link, "operator_action:", cast=str, default="cross_constraint_operation") or "cross_constraint_operation").strip().lower()
        generation = int(self._link_tag_value(link, "generation:", cast=int, default=max(1, int(getattr(link, 'depth', 1) or 1))) or 1)

        add = set(base_constraints)

        purpose_map = {
            "intelligence": {"existence", "temporal", "energy"},
            "communication": {"boundary", "agency", "temporal"},
            "meaning": {"existence", "agency", "boundary"},
        }
        add |= purpose_map.get(purpose, set())

        if "admissibility" in op_action:
            add |= {"existence", "boundary"}
        elif "temporal" in op_action:
            add |= {"temporal", "energy"}
        elif "energy" in op_action:
            add |= {"energy", "temporal"}
        elif "boundary" in op_action:
            add |= {"boundary", "agency"}
        elif "agency" in op_action:
            add |= {"agency", "existence"}

        # Earlier lineage should continue steering operation base.
        if generation <= 2:
            add |= {"existence", "temporal"}

        return frozenset(sorted(add))

    # ------------------------------------------------------------------
    # PUBLIC: inject promoted links into the sim
    # ------------------------------------------------------------------

    def inject_promoted_links(self) -> List[Dict[str, Any]]:
        """
        Read newly promoted Links from the genealogy fossil record.
        Each new Link becomes one ActionTrace tick through the chamber,
        then the tick result is forwarded to the simulation as a stimulus.

        Returns list of bridge event records for this call.
        """
        if not self._systems.has("chamber") or not self._systems.has("genealogy"):
            return []

        genealogy: ConstraintGenealogyLogger = self._systems.genealogy
        chamber:   EvolutionaryChamber       = self._systems.chamber
        sim:       Optional[Any]             = self._systems.simulation

        events: List[Dict[str, Any]] = []

        # links is Dict[str, ConstraintLink]
        links: Dict[str, ConstraintLink] = getattr(genealogy, "links", {})
        # Iterate over a stable snapshot: chamber ticks can promote links mid-loop.
        pending: List[Tuple[str, ConstraintLink]] = [
            (lid, lnk) for lid, lnk in list(links.items()) if lid not in self._injected_link_ids
        ]
        # Earlier-lineage high-grade operations go first.
        pending.sort(key=lambda kv: self._lineage_operation_priority(kv[1]), reverse=True)

        for link_id, link in pending:

            # Build an ActionTrace from the link's dominant_relief_axis + parent abilities
            dominant: str = getattr(link, "dominant_relief_axis", "B")
            constraint_label: str = _AXIS_TO_IVM.get(dominant, "boundary")
            parents: FrozenSet[str] = getattr(link, "parents", frozenset())

            # Compose a richer constraint set from parent ability IDs
            constraint_set: FrozenSet[str] = frozenset({constraint_label})
            for parent_id in parents:
                # Parent IDs look like "X:ADMIT", "A:DIRECTED_MANIPULATION" etc.
                if ":" in str(parent_id):
                    ax_letter = str(parent_id).split(":")[0].strip().upper()
                    ivm_label = _AXIS_TO_IVM.get(ax_letter)
                    if ivm_label:
                        constraint_set = constraint_set | {ivm_label}

            lineage_constraint_set = self._lineage_constraints(link, constraint_set)
            trace = ActionTrace(
                name             = f"link:{link_id[:16]}",
                constraints_used = lineage_constraint_set,
                meta             = {
                    "link_id":  link_id,
                    "depth":    getattr(link, "depth", 1),
                    "dominant": dominant,
                    "bridge":   True,
                    "purpose_lane": self._link_tag_value(link, "purpose_lane:", cast=str, default="meaning"),
                    "operator_action": self._link_tag_value(link, "operator_action:", cast=str, default="cross_constraint_operation"),
                    "lineage_generation": self._link_tag_value(link, "generation:", cast=int, default=max(1, int(getattr(link, 'depth', 1) or 1))),
                    "seed_influence": self._link_tag_value(link, "seed_influence:", cast=float, default=0.0),
                    "lineage_priority": self._lineage_operation_priority(link),
                },
            )
            trace = self._trace_with_ancestry(
                trace,
                source_fn="bridge.inject_promoted_links",
                parent_links=[link_id],
            )

            # One lawful tick through the chamber — physics apply
            tick_result = chamber.tick(trace)

            # If tick produced relief, forward its fitness signal to simulation
            if tick_result is not None and sim is not None:
                fitness_signal = self._relief_to_fitness(tick_result, link)
                self._forward_to_sim(fitness_signal, sim)
                self.total_fitness_feedbacks += 1

            event = {
                "type":        "link_injection",
                "link_id":     link_id,
                "dominant":    dominant,
                "constraints": sorted(lineage_constraint_set),
                "tick_result": bool(tick_result),
                "lineage_priority": self._lineage_operation_priority(link),
                "seed_influence": self._link_tag_value(link, "seed_influence:", cast=float, default=0.0),
                "timestamp":   time.time(),
            }
            events.append(event)
            self._bridge_events.append(event)
            self._injected_link_ids.add(link_id)
            self.total_link_injections += 1

        return events

    # ------------------------------------------------------------------
    # PUBLIC: feedback sim episode fitness → chain pressure
    # ------------------------------------------------------------------

    def feedback_episode_fitness(self, episode_result: Any) -> Optional[ActionTrace]:
        """
        Translate a simulation EpisodeResult back into a pressure event
        that enters the chamber as a real ActionTrace. High fitness = more
        agency/existence pressure. Low fitness = more boundary/energy pressure.

        The chamber still decides whether this produces relief — no shortcuts.
        Operator pressure gradients (NC[C][OPERATOR]) modulate amplification.
        """
        if not self._systems.has("chamber"):
            return None

        # EpisodeResult fields: avg_fitness, final_engagement, episode_id, turns
        avg_fitness: float = getattr(episode_result, "avg_fitness",      0.5)
        engagement:  float = getattr(episode_result, "final_engagement", 0.5)
        episode_id:  str   = getattr(episode_result, "episode_id",       "?")

        # Map fitness to the constraint axis that fitness corresponds to
        if avg_fitness > 0.65:
            # Growth signal — agency + existence driving forward
            constraints  = frozenset({"agency", "existence", "temporal"})
            episode_name = "fitness_growth"
        elif avg_fitness < 0.35:
            # Stress signal — boundary + energy redistribution needed
            constraints  = frozenset({"boundary", "energy"})
            episode_name = "fitness_stress"
        else:
            # Process signal — temporal + energy + agency balanced
            constraints  = frozenset({"temporal", "energy", "agency"})
            episode_name = "fitness_process"

        # High engagement pulls agency pressure up
        if engagement > 0.7:
            constraints = constraints | frozenset({"agency"})

        trace = ActionTrace(
            name             = f"sim_feedback:{episode_name}",
            constraints_used = constraints,
            meta             = {
                "avg_fitness":   avg_fitness,
                "engagement":    engagement,
                "episode_id":    episode_id,
                "bridge":        True,
                "feedback":      True,
            },
        )
        trace = self._trace_with_ancestry(
            trace,
            source_fn="bridge.feedback_episode_fitness",
        )

        # Lawful tick through chamber — operator pressure physics apply
        self._systems.chamber.tick(trace)
        self.total_fitness_feedbacks += 1
        return trace

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _relief_to_fitness(self, tick_result: Any, link: ConstraintLink) -> Dict[str, Any]:
        """Convert a chamber tick result + link record into a fitness signal dict."""
        # mean_relief is Dict[str, float] keyed by axis name
        mean_relief: Dict[str, float] = getattr(link, "mean_relief", {})
        total_relief = sum(mean_relief.values()) if mean_relief else 0.1
        return {
            "link_fitness":   min(1.0, total_relief / max(len(AXES), 1)),
            "dominant_axis":  getattr(link, "dominant_relief_axis", "B"),
            "link_depth":     getattr(link, "depth", 1),
            "link_count":     getattr(link, "count", 1),
        }

    def _forward_to_sim(self, fitness_signal: Dict[str, Any], sim: Any) -> None:
        """
        Transfer high-confidence understanding shards from ConsciousLearner
        into ExpressionEcology.wisdom (WisdomStore) so that what Aurora learns
        during simulation shapes her actual expressive voice in interactive turns.

        CONSTRAINT ANCESTRY: existence + agency + boundary
          - existence  (X): the shard IS a persisted state of understanding
          - agency     (A): it was formed through active selection pressure
          - boundary   (B): it crosses the sim↔expression interface, reshaping
                            the expressive surface without injecting content

        Each shard is translated to a WisdomShard keyed by the ResponseConcept
        i-state value — the same key ExpressionEcology.spawn() indexes on, and
        the same key the sim sends to ingest_interaction(). The transfer is
        one-directional and non-duplicating (tracked by shard_id).

        OPERATION LINEAGE: bridge.forward_shard_to_ecology
          Registered in UniverseSteerer._register_function_ancestry() under
          constraints {existence, agency, boundary}.  Every shard crossing
          stamps _stamp_ancestry_meta so the genealogy can trace it.
        """
        # Context-type → constraint axis → _AXIS_TO_TONE (from L5)
        # Mirrors the axis-tone mapping in aurora_expression_perception._AXIS_TO_TONE
        _CONTEXT_TO_AXIS_TONE: Dict[str, Tuple[str, float]] = {
            # context_type    axis_label    tone_bias (+warm/-cold)
            "emotional":   ("existence",  +0.10),   # X: warm, grounded
            "greeting":    ("existence",  +0.08),   # X: warm
            "philosophy":  ("temporal",   +0.04),   # T: reflective
            "creative":    ("agency",     +0.06),   # A: curious
            "practical":   ("boundary",   -0.06),   # B: precise (structured)
            "general":     ("temporal",   +0.02),   # T: mild reflective
            "constraint_evolution": ("energy", +0.0), # N: determined, neutral bias
        }

        try:
            session = getattr(sim, "session", None)
            if session is None:
                return
            learner = getattr(session, "learner", None)
            if learner is None:
                return
            perception = getattr(session, "perception", None)
            if perception is None:
                return
            ecology = getattr(getattr(perception, "ecology", None), None, None)
            # ExpressionEcology lives at perception.ecology (ExpressionPerceptionEngine)
            if ecology is None:
                ecology = getattr(perception, "ecology", None)
            if ecology is None:
                return
            wisdom_store = getattr(ecology, "wisdom", None)
            if wisdom_store is None:
                return

            # Determine which shards haven't been transferred yet
            already_transferred: Set[str] = getattr(
                self, "_transferred_shard_ids", set()
            )
            if not hasattr(self, "_transferred_shard_ids"):
                self._transferred_shard_ids: Set[str] = set()

            link_fitness = float(fitness_signal.get("link_fitness", 0.5))
            transferred = 0

            for shard_id, u_shard in list(learner.shards.items()):
                # Only transfer confident shards not yet in the wisdom store
                if shard_id in self._transferred_shard_ids:
                    continue
                confidence = float(getattr(u_shard, "confidence", 0.0))
                if confidence < 0.35:
                    continue  # not mature enough

                # ── Derive WisdomShard fields from UnderstandingShard ─────────
                concept     = getattr(u_shard, "response_concept", None)
                i_state     = concept.value if concept is not None else "i_is"
                ctx_type    = str(getattr(u_shard, "context_type", "general"))
                obs_count   = int(getattr(u_shard, "observation_count", 1))

                _, raw_tone_bias = _CONTEXT_TO_AXIS_TONE.get(
                    ctx_type, ("temporal", 0.0)
                )
                # Positive confidence lifts tone_bias toward warmth/openness,
                # scaled by how much we trust this shard
                tone_bias     = float(raw_tone_bias * confidence)
                # structure_bias: high-confidence shards favour moderate structure;
                # link fitness modulates — stronger chain link → slightly more structure
                structure_bias = float(_clamp(
                    (confidence - 0.5) * 0.4 + (link_fitness - 0.5) * 0.2
                ) - 0.1)

                # ── Stamp constraint ancestry ────────────────────────────────
                # Operation: bridge.forward_shard_to_ecology
                # Constraints: existence + agency + boundary  (X + A + B)
                ancestry_constraints: FrozenSet[str] = frozenset(
                    {"existence", "agency", "boundary"}
                )
                ancestry_meta = _stamp_ancestry_meta(
                    meta={
                        "shard_id":      shard_id,
                        "i_state":       i_state,
                        "context_type":  ctx_type,
                        "confidence":    round(confidence, 4),
                        "obs_count":     obs_count,
                        "link_fitness":  round(link_fitness, 4),
                        "transfer":      True,
                    },
                    constraints=ancestry_constraints,
                    source_fn="bridge.forward_shard_to_ecology",
                    parent_links=[shard_id],
                )

                # ── Build WisdomShard and add to store ───────────────────────
                from aurora_expression_perception import WisdomShard
                wisdom_shard = WisdomShard(
                    shard_id    = f"ws_{shard_id}",
                    i_state     = i_state,
                    tone_bias   = float(_clamp(tone_bias, -1.0, 1.0)),
                    structure_bias = float(_clamp(structure_bias, -1.0, 1.0)),
                    fitness_at_death = float(_clamp(confidence + link_fitness * 0.1)),
                    cause_of_death   = "sim_transfer",
                    generation       = min(obs_count, 20),
                )
                wisdom_store.add(wisdom_shard)
                self._transferred_shard_ids.add(shard_id)
                transferred += 1

            if transferred > 0:
                # Advance learner observation count to reflect the crossing
                learner.total_observations += transferred

        except Exception:
            pass  # simulation + expression are optional — never block on it

    def stats(self) -> Dict[str, Any]:
        return {
            "total_link_injections":   self.total_link_injections,
            "total_fitness_feedbacks": self.total_fitness_feedbacks,
            "injected_link_count":     len(self._injected_link_ids),
            "recent_events":           len(self._bridge_events),
        }


# =============================================================================
# UNIVERSE STEERER
# =============================================================================

class UniverseSteerer:
    """
    The lawful interface for steering Aurora's interactive universe.

    You CANNOT inject results. You CAN inject stimuli — ActionTraces
    and pressure events — and the constraint physics determine what happens.

    OPERATIONS
    ----------
    tick(n)              — advance the chamber n ticks (default action cycle)
    inject(action)       — inject a specific ActionTrace by name or object
    inject_custom(...)   — inject a custom constraint combination
    chain_burst(n)       — run n ticks with full genealogy promotion pass
    sim_episode(**kw)    — run one simulation episode (requires L7)
    sim_epoch(**kw)      — run a full simulation epoch (requires L7)
    sync_bridge()        — inject any newly promoted links into simulation
    pressure_report()    — print live operator pressure gradient snapshot
    status()             — print universe state summary
    links()              — print promoted link report
    what_learned()       — print conscious learner's current understanding
    available_actions()  — list the named actions you can inject
    register_action(...) — add a custom named action to the registry
    """

    def __init__(self, systems: StackSystems, bridge: ChainSimBridge):
        self._s = systems
        self._b = bridge
        self._code_pressure_guidance_fn: Optional[Any] = None
        self._strict_lineage: bool = _env_flag("AURORA_STRICT_LINEAGE", default=True)
        self._lineage_rejections: int = 0
        self._lineage_synthesized_events: int = 0
        self._lineage_default_floor_events: int = 0
        self._function_ancestry: Dict[str, FrozenSet[str]] = {}
        self._function_perf: Dict[str, Dict[str, float]] = {}
        self._function_offspring: Dict[str, Dict[str, Any]] = {}
        self._function_history: Deque[Dict[str, Any]] = deque(maxlen=4096)
        self._function_history_seq: int = 0
        self._surface_lineage: Dict[str, Dict[str, Any]] = {}
        self._surface_history: Deque[Dict[str, Any]] = deque(maxlen=4096)
        self._surface_history_seq: int = 0
        self._action_map: Dict[str, ActionTrace] = {
            a.name: self._with_trace_ancestry(a, source_fn="steerer.default_action")
            for a in DEFAULT_ACTION_CYCLE
        }
        self._tick_cursor:  int = 0
        self._epoch_cursor: int = 0
        self._last_episode: Optional[Any] = None
        self._pressure_history_decay: float = 0.92
        self._pressure_history: Dict[Any, float] = {}
        if Constraint is not None:
            self._pressure_history = {
                c: 0.0 for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
            }

        # Plateau detection + conflict curriculum telemetry
        self._recent_relief_rates: Deque[float] = deque(maxlen=6)
        self._recent_bridge_rates: Deque[float] = deque(maxlen=6)
        self._recent_fitness: Deque[float] = deque(maxlen=6)
        self._recent_total_links: Deque[int] = deque(maxlen=400)
        self._recent_total_abilities: Deque[int] = deque(maxlen=400)
        self._recent_link_growth_rates: Deque[float] = deque(maxlen=6)
        self._last_links_count: int = 0
        self._last_link_change_tick: int = 0
        self._last_abilities_count: int = 0
        self._last_ability_change_tick: int = 0
        self._conflict_cursor: int = 0
        self._conflict_cooldown_ticks: int = 250
        self._last_conflict_tick: int = -10_000
        self._session_relief_events: int = 0
        self._session_chain_ticks: int = 0
        self._session_epochs: int = 0
        self._session_bridge_events: int = 0
        self._session_conflicts_injected: int = 0
        self._session_conflicts_resolved: int = 0
        self._session_conflicts_resolved_execution: int = 0
        self._session_conflicts_resolved_pressure: int = 0
        self._conflict_pressure_resolve_eps: float = 1e-6
        self._session_plateau_pressure_events: int = 0
        self._user_turn_count: int = 0
        self._last_entropy_signal: Optional[Dict[str, Any]] = None
        self._last_gap_event: Optional[Dict[str, Any]] = None
        self._last_braid_snapshot: Optional[Dict[str, Any]] = None
        self._last_language_status: Optional[Dict[str, Any]] = None
        self._last_primitive_vocab: Optional[Dict[str, Any]] = None
        self._last_attention_frame: Optional[Any] = None
        self._last_leverage_band: Optional[str] = None
        self._base_flip_thresholds: Dict[Any, float] = {}
        self._effective_flip_thresholds: Dict[str, float] = {}
        self._last_entropy_regulation_tick: int = -10_000
        self._entropy_regulation_cooldown: int = 8
        self._last_primitive_regulation_tick: int = -10_000
        self._primitive_regulation_cooldown: int = 25
        if REGISTRY is not None and Constraint is not None:
            try:
                for ax in ("X", "T", "N", "B", "A"):
                    c = getattr(Constraint, ax)
                    self._base_flip_thresholds[c] = float(REGISTRY.polarity(c).flip_threshold)
                    self._effective_flip_thresholds[ax] = float(REGISTRY.polarity(c).flip_threshold)
            except Exception:
                self._base_flip_thresholds = {}
                self._effective_flip_thresholds = {}
        self._plateau_metric_counts: Dict[str, int] = {"relief": 0, "bridge": 0, "fitness": 0, "links_total": 0, "abilities_total": 0}
        self._lane_totals: Dict[str, int] = {k: 0 for k in CONFLICT_LANES}
        self._lane_resolved: Dict[str, int] = {k: 0 for k in CONFLICT_LANES}
        self._conflict_log: Deque[Dict[str, Any]] = deque(maxlen=64)

        # Register core operational functions against base-constraint ancestry.
        self._register_function_ancestry("tick", {"temporal", "energy"})
        self._register_function_ancestry("inject", {"agency", "temporal", "boundary"})
        self._register_function_ancestry("inject_custom", {"agency", "temporal", "boundary"})
        self._register_function_ancestry("chain_burst", {"temporal", "energy", "boundary", "agency"})
        self._register_function_ancestry("sim_episode",   {"existence", "temporal", "agency"})
        self._register_function_ancestry("sim_epoch",     {"existence", "temporal", "energy", "agency"})
        self._register_function_ancestry("sim_speed_run", {"existence", "temporal", "energy", "agency"})
        self._register_function_ancestry("bridge.inject_promoted_links",
                                         {"boundary", "agency", "temporal", "energy"})
        self._register_function_ancestry("bridge.feedback_episode_fitness",
                                         {"existence", "temporal", "energy", "agency"})
        # Shard crossing: sim ConsciousLearner -> L5 ExpressionEcology.wisdom
        # existence (X): persisted understanding state crossing into expressive layer
        # agency    (A): formed under active evolutionary selection pressure
        # boundary  (B): crosses the sim<->expression interface surface
        self._register_function_ancestry("bridge.forward_shard_to_ecology",
                                         {"existence", "agency", "boundary"})
        self._register_function_ancestry("pressure_report", {"temporal", "energy"})
        self._register_function_ancestry("status", set(_IVM_AXIS_LABELS))
        self._register_function_ancestry("links", {"boundary", "agency", "temporal"})
        self._register_function_ancestry("what_learned", {"existence", "temporal", "agency"})
        self._register_function_ancestry("available_actions", {"existence", "temporal"})
        self._register_function_ancestry("register_action", {"agency", "existence", "temporal"})
        self._register_function_ancestry("review_before_save", {"existence", "temporal", "boundary"})
        # gateway._integrate: assembly result → identity relic
        # existence (X): turn becomes persisted identity state
        # temporal  (T): time-ordered memory in L6
        # boundary  (B): relic shapes the interaction episode boundary
        self._register_function_ancestry("gateway._integrate",
                                         {"existence", "temporal", "boundary"})
        self._register_function_ancestry("save", {"existence", "boundary", "energy"})
        self._register_function_ancestry("shutdown", {"temporal", "boundary", "agency"})
        self._register_function_ancestry("aux.observe_input", {"existence", "temporal", "agency"})
        self._register_function_ancestry("aux.tick_modules", {"temporal", "energy", "boundary", "agency"})

        for name, tr in self._action_map.items():
            self._register_function_ancestry(f"action:{name}", set(tr.constraints_used))

        # Auto-map broad runtime surface so lineage tracking is not limited
        # to CLI lifecycle calls.
        self._register_stack_surface_lineage()

    # ------------------------------------------------------------------
    # CHAIN STEERING
    # ------------------------------------------------------------------

    def _refresh_operator_gradients(self, alpha: float = 0.08) -> None:
        """Bridge live C:D pressure into operator gradients and DPME guidance."""
        try:
            snap = self._s.pressure_snapshot()
            if snap is None or Constraint is None or REGISTRY is None or per_operator_pressure is None:
                return
            op_pressures = per_operator_pressure(snap)

            decay = self._pressure_history_decay
            for c, contrib in op_pressures.items():
                cval = float(contrib)
                op = REGISTRY.operator(c)
                op.pressure_gradient = (1.0 - alpha) * op.pressure_gradient + (alpha * cval)
                prev = self._pressure_history.get(c, 0.0)
                self._pressure_history[c] = (decay * prev) + ((1.0 - decay) * abs(cval))

            if set_external_pressure_guidance is not None and self._pressure_history:
                ranked = sorted(self._pressure_history.items(), key=lambda kv: kv[1], reverse=True)
                primary_c, primary_v = ranked[0]
                secondary_c, secondary_v = ranked[1] if len(ranked) > 1 else (None, 0.0)
                total = sum(max(0.0, float(v)) for v in self._pressure_history.values())
                score = (float(primary_v) / total) if total > 0.0 else 0.0
                primary_key = getattr(primary_c, 'name', str(primary_c))
                secondary_key = getattr(secondary_c, 'name', str(secondary_c)) if secondary_c is not None else None
                code_guidance = None
                if callable(self._code_pressure_guidance_fn):
                    try:
                        code_guidance = self._code_pressure_guidance_fn() or {}
                    except Exception:
                        code_guidance = None
                if isinstance(code_guidance, dict) and code_guidance:
                    # Blend cross-scale signal so code substrate pressure influences steering.
                    code_score = float(code_guidance.get("score", 0.0) or 0.0)
                    code_compare = float(code_guidance.get("compare_value", 0.0) or 0.0)
                    blend = 0.25
                    score = ((1.0 - blend) * float(score)) + (blend * code_score)
                    primary_v = ((1.0 - blend) * float(primary_v)) + (blend * code_compare)
                    ax_to_lbl = {"X": "existence", "T": "temporal", "N": "energy", "B": "boundary", "A": "agency"}
                    code_primary_axis = str(code_guidance.get("primary_axis", "") or "").upper()
                    code_secondary_axis = str(code_guidance.get("secondary_axis", "") or "").upper()
                    if code_primary_axis in ax_to_lbl:
                        primary_key = code_primary_axis
                        secondary_key = code_secondary_axis if code_secondary_axis in ax_to_lbl else secondary_key
                set_external_pressure_guidance({
                    'score': score,
                    'compare_value': float(primary_v),
                    'primary_channel': _CONSTRAINT_TO_DER_CHANNEL.get(primary_key),
                    'secondary_channel': _CONSTRAINT_TO_DER_CHANNEL.get(secondary_key),
                })
        except Exception:
            return

    def _auto_seed_directive(self,
                             name: str,
                             constraints: FrozenSet[str],
                             meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Auto-map introduced operations into seeded steering directives."""
        payload = dict(meta or {})

        # Allow explicit opt-out if ever needed.
        if bool(payload.get("natural_introduction", False)):
            payload.setdefault("artificial_seed", False)
            return payload

        # Introduced operations default to artificial seed steering.
        if "artificial_seed" not in payload:
            payload["artificial_seed"] = True
        if "bypass_natural" not in payload:
            payload["bypass_natural"] = bool(payload.get("artificial_seed", True))

        cset = {str(c).strip().lower() for c in (constraints or frozenset())}

        # Stable lineage id for this introduced seed op.
        if not payload.get("seed_lineage_id"):
            raw = f"{name}|{','.join(sorted(cset))}"
            payload["seed_lineage_id"] = "seed:" + hashlib.sha1(raw.encode()).hexdigest()[:10]

        # Infer purpose lane from constraint profile.
        lane_sets = {
            "intelligence": {"existence", "temporal", "energy"},
            "communication": {"boundary", "agency", "temporal"},
            "meaning": {"existence", "agency", "boundary"},
        }
        if not payload.get("target_purpose_lane"):
            scores = {k: len(cset & v) for k, v in lane_sets.items()}
            payload["target_purpose_lane"] = max(scores.items(), key=lambda kv: kv[1])[0]

        # Infer operator action from dominant introduced constraint.
        if not payload.get("target_operator_action"):
            pr = ["agency", "boundary", "energy", "temporal", "existence"]
            dom = next((x for x in pr if x in cset), "existence")
            op_map = {
                "existence": "admissibility_gating",
                "temporal": "temporal_orchestration",
                "energy": "energy_economics",
                "boundary": "boundary_shaping",
                "agency": "agency_direction",
            }
            payload["target_operator_action"] = op_map.get(dom, "cross_constraint_operation")

        # Infer target generation from introduced complexity.
        if not payload.get("target_generation"):
            payload["target_generation"] = max(2, 1 + min(6, len(cset)))

        if "artificial_seed_weight" not in payload:
            payload["artificial_seed_weight"] = 0.85

        payload["auto_seed_mapped"] = True
        return payload

    def _intake_log_depth_beads(
        self,
        intake_id: str,
        current_mode: Any,
        accountant: Any,
        tick: int,
        event_log: Dict[str, List[Tuple[Any, Any, float, float, int, Any]]],
        depth_seen: Dict[str, set],
    ) -> None:
        """Append depth-promotion beads for newly reached modes."""
        try:
            from aurora_internal.aurora_dna_strand_schema import NonCompChannel
            from aurora_internal.aurora_constraint_manifold_patched import Constraint
            from foundational_contract import ExistenceMode
        except Exception:
            return

        _mode_to_constraint = {
            ExistenceMode.PERSISTENT: Constraint.N,
            ExistenceMode.BOUNDED: Constraint.B,
            ExistenceMode.AGENTIC: Constraint.A,
        }
        _mode_order = [ExistenceMode.TRANSIENT, ExistenceMode.PERSISTENT, ExistenceMode.BOUNDED, ExistenceMode.AGENTIC]

        seen = depth_seen.setdefault(intake_id, {ExistenceMode.TRANSIENT})
        if intake_id not in event_log:
            event_log[intake_id] = []

        def _pol(c: Any) -> float:
            try:
                return max(-1.0, min(1.0, float(accountant.slot(c).polarity)))
            except Exception:
                return 0.0

        try:
            target_idx = _mode_order.index(current_mode)
        except Exception:
            target_idx = 0

        for mode in _mode_order[1:target_idx + 1]:
            if mode in seen:
                continue
            c = _mode_to_constraint.get(mode)
            if c is None:
                continue
            params = REGISTRY.cost(c) if REGISTRY is not None else None
            delta = float(getattr(params, "time_constant", 0.0) or 0.0)
            event_log[intake_id].append((c, NonCompChannel.M, delta, _pol(c), tick, mode))
            seen.add(mode)

    def _advance_intake_pipeline(self, stimulus_text: str, tick: int) -> None:
        """
        Advance one experiential intake tick (Step 9-14) using the current action
        as the intake stimulus. This keeps the learning loop alive in runtime.
        """
        metabolizer = self._s.metabolizer
        worth_eval = self._s.worth_eval
        solidification = self._s.solidification
        variant_promoter = self._s.variant_promoter
        strand_lib = self._s.strand_lib
        strand_builder = self._s.strand_builder
        accountant = self._s.accountant
        bias_engine = self._s.bias_engine
        if metabolizer is None or accountant is None:
            return

        try:
            from aurora_internal.aurora_dna_strand_schema import NonCompChannel
            from aurora_internal.aurora_constraint_manifold_patched import Constraint
            from foundational_contract import ExistenceMode
        except Exception:
            return

        def _pol(c: Any) -> float:
            try:
                return max(-1.0, min(1.0, float(accountant.slot(c).polarity)))
            except Exception:
                return 0.0

        # Persistent per-intake state.
        event_log = getattr(self, "_intake_event_log", {})
        depth_seen = getattr(self, "_intake_depth_seen", {})
        pending_hz = getattr(self, "_pending_horizons", {})
        self._intake_event_log = event_log
        self._intake_depth_seen = depth_seen
        self._pending_horizons = pending_hz

        accountant.tick()
        if bias_engine is not None and hasattr(bias_engine, "compute_nudges"):
            try:
                bias_engine.compute_nudges(accountant)
            except Exception:
                pass

        # Stage 1: intake receive.
        text = str(stimulus_text or "").strip()
        payload = max(10.0, min(200.0, len(text) * 0.8))
        new_record = metabolizer.receive("runtime_action", tick=tick, energy_payload=payload)
        if new_record is not None:
            iid = new_record.intake_id
            event_log[iid] = [
                (Constraint.X, NonCompChannel.M, float(new_record.entry_toll), _pol(Constraint.X), tick, ExistenceMode.TRANSIENT),
                (Constraint.T, NonCompChannel.O, 0.0, _pol(Constraint.T), tick, ExistenceMode.TRANSIENT),
            ]
            depth_seen[iid] = {ExistenceMode.TRANSIENT}

        modes_before = {iid: rec.current_mode for iid, rec in getattr(metabolizer, "_live", {}).items()}

        # Stage 2: metabolism tick.
        result = metabolizer.advance(tick=tick)

        for record in getattr(result, "promoted", []):
            iid = record.intake_id
            event_log.setdefault(iid, []).append((Constraint.N, NonCompChannel.O, 0.0, _pol(Constraint.N), tick, ExistenceMode.TRANSIENT))

        for iid, rec in list(getattr(metabolizer, "_live", {}).items()):
            prior = modes_before.get(iid)
            if prior is not None and prior != rec.current_mode:
                self._intake_log_depth_beads(iid, rec.current_mode, accountant, tick, event_log, depth_seen)
        for record in getattr(result, "promoted", []):
            self._intake_log_depth_beads(record.intake_id, record.current_mode, accountant, tick, event_log, depth_seen)

        # Stage 3: worth/horizon.
        worth_reports: Dict[str, Any] = {}
        if worth_eval is not None:
            for iid, rec in list(getattr(metabolizer, "_live", {}).items()):
                if str(getattr(rec, "status", "")).upper().endswith("PROMOTED"):
                    try:
                        _, report = worth_eval.evaluate(
                            intake_id=iid,
                            current_mode=rec.current_mode,
                            accountant=accountant,
                            current_tick=tick,
                        )
                    except Exception:
                        continue
                    worth_reports[iid] = (rec, report)
                    if getattr(report, "horizon", None) is not None and iid not in pending_hz:
                        pending_hz[iid] = report.horizon

        # Stage 4/5: solidification.
        if solidification is not None:
            for iid, horizon in list(pending_hz.items()):
                try:
                    eligible = bool(horizon.eligible_at(tick))
                except Exception:
                    eligible = False
                if not eligible:
                    continue
                pair = worth_reports.get(iid)
                if pair is None:
                    pending_hz.pop(iid, None)
                    continue
                _, report = pair
                try:
                    solidification.submit_eligible(
                        horizon=horizon,
                        tick=tick,
                        accountant=accountant,
                        polarity_coherent=bool(getattr(report, "polarity_coherent", False)),
                    )
                except Exception:
                    pass
                pending_hz.pop(iid, None)

            for iid, (rec, report) in list(worth_reports.items()):
                try:
                    solidification.observe_recurrence(
                        intake_id=iid,
                        tick=tick,
                        accountant=accountant,
                        polarity_coherent=bool(getattr(report, "polarity_coherent", False)),
                        energy_spent=float(getattr(rec, "entry_toll", 0.0) or 0.0),
                    )
                except Exception:
                    pass
                event_log.setdefault(iid, []).append(
                    (Constraint.B, NonCompChannel.DIFF, 0.0, 1.0 if bool(getattr(report, "polarity_coherent", False)) else -1.0, tick, rec.current_mode)
                )

        # Stage 6/7: variant + DNA.
        if solidification is not None and variant_promoter is not None:
            try:
                solidified = list(solidification.drain_solidified() or [])
            except Exception:
                solidified = []
            if solidified:
                try:
                    variants = list(variant_promoter.process_solidified(solidified, current_tick=tick) or [])
                except Exception:
                    variants = []
                if strand_lib is not None and strand_builder is not None and variants:
                    for variant in variants:
                        iid = str(getattr(variant, "intake_id", ""))
                        events = list(event_log.get(iid, []))
                        try:
                            events.append((variant.deepest_constraint, NonCompChannel.O, 0.0, 0.0, tick, variant.depth_reached))
                        except Exception:
                            pass
                        if events:
                            try:
                                strand = strand_builder.build(variant, events)
                                strand_lib.register(strand, current_tick=tick)
                            except Exception:
                                pass
                        event_log.pop(iid, None)
                        depth_seen.pop(iid, None)
                        pending_hz.pop(iid, None)

        for rec in getattr(result, "decayed", []):
            iid = rec.intake_id
            event_log.pop(iid, None)
            depth_seen.pop(iid, None)
            pending_hz.pop(iid, None)

    def observe_input_text(self, text: str) -> None:
        """Feed raw operator/user text into awareness modules."""
        self._user_turn_count += 1
        payload = str(text or "").strip()
        if not payload:
            return

        # Comprehension-gap handling
        gap_sys = getattr(self._s, "comprehension_gap_system", None)
        if gap_sys is not None:
            try:
                systems_view = {
                    "perception": getattr(self._s, "perception", None),
                    "working_memory": None,
                }
                self._last_gap_event = gap_sys.process(payload, systems_view, turn_count=self._user_turn_count)
            except Exception:
                self._last_gap_event = None

        # Braided substrate update
        bsl = getattr(self._s, "braided_substrate", None)
        if bsl is not None:
            try:
                from aurora_internal.aurora_braided_substrate import SubstrateEvent
                low = payload.lower()
                intent = "clarify" if "?" in payload else ("execute" if any(k in low for k in ("do ", "run ", "fix ", "update ", "make ")) else "explore")
                context = "uncertain" if ("?" in payload or "maybe" in low) else "task"
                style = "concise" if len(payload.split()) < 14 else "literal"
                evt = SubstrateEvent(
                    intent_signal=intent,
                    context_signal=context,
                    style_signal=style,
                    confidence=0.8 if "?" not in payload else 0.6,
                    evidence_level=0.7,
                    contradiction_flag=bool(any(k in low for k in ("not ", "never ", "but "))),
                    source="interaction",
                )
                bsl.update(evt)
                self._last_braid_snapshot = bsl.snapshot()
                # Project braid state into constraint axes — closes the 8D→5D gap.
                # heat (contradiction accumulation) → B-axis tension;
                # stability (recurrence coherence) → T-axis + X-axis grounding.
                _bsnap = self._last_braid_snapshot or {}
                _b_heat = float(_bsnap.get("heat", 0.0) or 0.0)
                _b_stab = float(_bsnap.get("stability", 0.5) or 0.5)
                _ifield_braid = getattr(self._s, "identity_field", None)
                if _ifield_braid is not None and hasattr(_ifield_braid, "ingest_external_input"):
                    _braid_axes: Dict[str, float] = {
                        "B": 0.35 + _b_heat * 0.40,        # contradiction → B-axis tension
                        "T": 0.30 + _b_stab * 0.35,        # stability → T-axis continuity
                        "X": 0.28 + _b_stab * 0.25,        # stability → X-axis existence
                    }
                    _ifield_braid.ingest_external_input(_braid_axes, intensity=0.18, source="braided_substrate")
            except Exception:
                self._last_braid_snapshot = None

        # Language evolution observe
        lang = getattr(self._s, "language_orchestra", None)
        if lang is not None:
            try:
                lang.observe_user(payload)
                self._last_language_status = lang.status()
            except Exception:
                self._last_language_status = None

        self._record_function_outcome("aux.observe_input", 1.0, evidence=1.0)

    def has_pending_gap(self) -> bool:
        gap_sys = getattr(self._s, "comprehension_gap_system", None)
        if gap_sys is None:
            return False
        try:
            mem = getattr(gap_sys, "memory", None)
            if mem is not None and hasattr(mem, "has_pending"):
                return bool(mem.has_pending())
        except Exception:
            return False
        return False

    def pending_gap_prompt(self) -> Optional[str]:
        if not self.has_pending_gap():
            return None
        ev = getattr(self, "_last_gap_event", None)
        if isinstance(ev, dict) and str(ev.get("action", "")) == "ask":
            return str(ev.get("content", "") or "").strip() or None
        return "Aurora has a pending clarification question."

    def _advance_auxiliary_modules(self, stimulus_text: str, tick: int) -> None:
        """Advance entropy/primitive/language modules each runtime tick."""
        accountant = getattr(self._s, "accountant", None)
        bias_engine = getattr(self._s, "bias_engine", None)
        entropy_detector = getattr(self._s, "entropy_detector", None)
        primitive_extractor = getattr(self._s, "primitive_extractor", None)
        attention_engine = getattr(self._s, "attention_engine", None)
        lang = getattr(self._s, "language_orchestra", None)

        # Unified Attention Engine (Dual-Tier Meaning Formation)
        if attention_engine is not None:
            try:
                # 1. Subsurface Tension: Get introspective drift from chamber
                internal_drift = self._s.pressure_snapshot()
                
                # 2. Surface Salience: Get external intensity from perception
                external_stimuli = {"intensity": 0.0, "tags": []}
                if self._s.has("perception"):
                    external_stimuli = self._s.perception.get_surface_salience()
                
                # 3. Resolve focus if a stimulus was provided in the tick() call
                if stimulus_text and stimulus_text != "tick":
                    external_stimuli["intensity"] = max(external_stimuli.get("intensity", 0.0), 0.7)
                    if "aurora" in stimulus_text.lower():
                        external_stimuli["addressed"] = True
                    external_stimuli["tags"] = external_stimuli.get("tags", []) + ["stimulus"]

                # 4. Tick the engine
                if internal_drift is not None:
                    frame = attention_engine.tick(tick, external_stimuli, internal_drift)
                    self._last_attention_frame = frame

                    # 5. WillIntent dispatch — attention → intention → axis pressure
                    # generate_will() produces an uncommitted intention; route it through
                    # the identity field as the axis most activated by that intent class.
                    will = attention_engine.generate_will()
                    if will is not None:
                        _ifield_attn = getattr(self._s, "identity_field", None)
                        if _ifield_attn is not None and hasattr(_ifield_attn, "ingest_external_input"):
                            _WILL_AXIS: dict = {
                                "curiosity":    {"T": 0.55, "N": 0.48, "A": 0.40},
                                "agency":       {"A": 0.65, "N": 0.50, "T": 0.38},
                                "grounding":    {"X": 0.62, "B": 0.45, "T": 0.35},
                                "self_check":   {"N": 0.58, "X": 0.45, "B": 0.38},
                                "environmental":{"B": 0.60, "X": 0.48, "N": 0.40},
                            }
                            _waxes = _WILL_AXIS.get(will.class_name, {"A": 0.45, "T": 0.40})
                            try:
                                _ifield_attn.ingest_external_input(
                                    _waxes,
                                    intensity=min(0.35, 0.15 + will.resonance * 0.30),
                                    source=f"will_intent:{will.class_name}",
                                )
                            except Exception:
                                pass

                    # 6. Meaning Formation Trigger
                    nucleus = attention_engine.get_meaning_nucleus()
                    if nucleus:
                        res = nucleus["resonance"]
                        axes = nucleus["axes"]

                        # --- Feedback: Emotional (L3 DER) ---
                        if self._s.has("dimensional"):
                            self._s.dimensional.der.register_attention_pulse(res, axes)

                        # --- Feedback: Reasoning (DPME) ---
                        if self._s.has("dpme"):
                            self._s.dpme.apply_attentional_guidance(res, axes)
                            # Pass 2: Semantic Reasoning
                            if self._s.has("perception") and self._s.perception.oets:
                                self._s.dpme.resolve_semantic_tension(self._s.perception.oets)

                        # --- Feedback: Identity (L6) ---
                        if self._s.has("identity"):
                            self._s.identity.reinforce_identity(res, axes)

                        # --- Feedback: Expression (L5) ---
                        if self._s.has("perception"):
                            self._s.perception.set_attentional_focus(nucleus)

                        # OETS relational anchor creation — when state == FORMING and
                        # anchors are present, teach each anchor concept into the
                        # ontological web so high-resonance meanings crystallize there.
                        if self._s.has("perception") and self._s.perception.oets:
                            try:
                                self._s.perception.oets.consolidate()
                                for _anchor in (nucleus.get("anchors") or []):
                                    if _anchor and isinstance(_anchor, str):
                                        # teach() creates/reinforces the node; description
                                        # encodes the resonance context so it's not blank
                                        self._s.perception.oets.teach(
                                            _anchor,
                                            f"attention anchor at resonance {res:.3f}",
                                        )
                            except Exception:
                                pass
            except Exception:
                self._last_attention_frame = None

        # Always-on leverage scalar path: consume leverage each tick and apply
        # ephemeral flip-threshold nudges across constraints.
        if bias_engine is not None and accountant is not None and REGISTRY is not None and Constraint is not None:
            try:
                from aurora_internal.aurora_leverage_scalar import apply_nudges_to_thresholds
                nudges = bias_engine.compute_nudges(accountant)
                effective = apply_nudges_to_thresholds(
                    nudges,
                    base_thresholds=(self._base_flip_thresholds or None),
                )
                for c, th in effective.items():
                    try:
                        REGISTRY.polarity(c).flip_threshold = float(th)
                        self._effective_flip_thresholds[str(getattr(c, "name", c))] = float(th)
                    except Exception:
                        continue
                self._last_leverage_band = str(getattr(bias_engine, "band_position", "inside"))
            except Exception:
                pass

        # Entropy saturation signal
        if entropy_detector is not None and accountant is not None:
            try:
                sig = entropy_detector.measure(accountant, current_tick=int(tick))
                self._last_entropy_signal = {
                    "level": str(getattr(getattr(sig, "level", None), "name", "")),
                    "tick": int(getattr(sig, "tick", tick)),
                    "pressure_rising": bool(getattr(sig, "pressure_rising", False)),
                    "projected_critical_tick": getattr(sig, "projected_critical_tick", None),
                    "shallow_headroom_available": bool(getattr(sig, "shallow_headroom_available", False)),
                }
                # Make entropy detector causally active: translate actionable
                # saturation into pressure-gradient nudges that influence next
                # chamber decisions and promotions.
                if (
                    bool(getattr(sig, "is_actionable", lambda: False)())
                    and REGISTRY is not None
                    and Constraint is not None
                    and (int(tick) - int(self._last_entropy_regulation_tick)) >= int(self._entropy_regulation_cooldown)
                ):
                    level_name = str(getattr(getattr(sig, "level", None), "name", "WATCH")).upper()
                    gain_map = {"CAUTION": 0.0008, "CRITICAL": 0.0018, "EMERGENCY": 0.0030}
                    gain = float(gain_map.get(level_name, 0.0005))
                    fastest = getattr(sig, "fastest_rising_constraint", None)
                    target = fastest if fastest is not None else Constraint.N
                    try:
                        op = REGISTRY.operator(target)
                        op.pressure_gradient = float(op.pressure_gradient) + gain
                    except Exception:
                        pass
                    self._last_entropy_regulation_tick = int(tick)
                    if _enqueue_recommendation is not None:
                        try:
                            _enqueue_recommendation(
                                output_dir=os.path.abspath("aurora_runtime_output"),
                                source="aurora_runtime.UniverseSteerer._advance_auxiliary_modules",
                                run_type="entropy_regulation",
                                title=f"Entropy {level_name} on {getattr(target, 'name', 'N')}",
                                body=(
                                    f"Applied gradient gain={gain:.6f} from entropy detector. "
                                    f"projected_critical_tick={getattr(sig, 'projected_critical_tick', None)}"
                                ),
                                priority=0.62 if level_name in {"CRITICAL", "EMERGENCY"} else 0.42,
                                context={"tick": int(tick), "level": level_name, "target": str(getattr(target, "name", "N"))},
                            )
                        except Exception:
                            pass
            except Exception:
                self._last_entropy_signal = None

        # Primitive extractor read lens (periodic).
        if primitive_extractor is not None and (int(tick) % 25 == 0):
            try:
                vocab = primitive_extractor.vocabulary(print_results=False)
                self._last_primitive_vocab = vocab.to_dict() if hasattr(vocab, "to_dict") else dict(vocab)
                # Primitive lens becomes active by counter-biasing dominant-axis
                # lock-in and nudging weak axes upward in operator gradients.
                if (
                    REGISTRY is not None
                    and Constraint is not None
                    and (int(tick) - int(self._last_primitive_regulation_tick)) >= int(self._primitive_regulation_cooldown)
                ):
                    center = dict(self._last_primitive_vocab.get("axis_center", {}) or {})
                    if center:
                        dominant_ax = max(("X", "T", "N", "B", "A"), key=lambda a: float(center.get(a, 0.0)))
                        weakest_ax = min(("X", "T", "N", "B", "A"), key=lambda a: float(center.get(a, 0.0)))
                        if dominant_ax != weakest_ax:
                            c_dom = getattr(Constraint, dominant_ax, None)
                            c_weak = getattr(Constraint, weakest_ax, None)
                            if c_dom is not None:
                                try:
                                    op_d = REGISTRY.operator(c_dom)
                                    op_d.pressure_gradient = max(0.0, float(op_d.pressure_gradient) - 0.0004)
                                except Exception:
                                    pass
                            if c_weak is not None:
                                try:
                                    op_w = REGISTRY.operator(c_weak)
                                    op_w.pressure_gradient = float(op_w.pressure_gradient) + 0.0009
                                except Exception:
                                    pass
                            self._last_primitive_regulation_tick = int(tick)
                            if _enqueue_recommendation is not None:
                                try:
                                    _enqueue_recommendation(
                                        output_dir=os.path.abspath("aurora_runtime_output"),
                                        source="aurora_runtime.UniverseSteerer._advance_auxiliary_modules",
                                        run_type="primitive_rebalance",
                                        title=f"Rebalance {weakest_ax} against {dominant_ax}",
                                        body=(
                                            f"Primitive center dominant={dominant_ax} weak={weakest_ax}; "
                                            f"applied gradient rebalance."
                                        ),
                                        priority=0.36,
                                        context={"tick": int(tick), "dominant": dominant_ax, "weak": weakest_ax},
                                    )
                                except Exception:
                                    pass
            except Exception:
                self._last_primitive_vocab = None

        # Language LSV metrics update
        if lang is not None:
            try:
                from aurora_internal.aurora_language_state import LSVMetrics
                g = getattr(self._s, "genealogy", None)
                links = len(getattr(g, "links", {}) or {}) if g is not None else 0
                abilities = len(getattr(g, "abilities", {}) or {}) if g is not None else 0
                max_depth = 0
                if g is not None:
                    try:
                        max_depth = max([int(getattr(v, "depth", 0) or 0) for v in getattr(g, "links", {}).values()] or [0])
                    except Exception:
                        max_depth = 0
                contradictions = int(getattr(self, "_session_conflicts_injected", 0))
                chain_ticks = max(1, int(getattr(self, "_session_chain_ticks", 0)))
                contradictions_rate = float(contradictions) / float(chain_ticks)
                coherence = float(getattr(self, "_session_relief_events", 0)) / float(chain_ticks)
                ivm_heat = 0.0
                dim = getattr(self._s, "dimensional", None)
                if dim is not None and getattr(dim, "der", None) is not None:
                    ivm_heat = float(getattr(dim.der, "thermal_load", 0.0) or 0.0)
                rel_density = float(links) / float(max(1, abilities))
                metrics = LSVMetrics(
                    ontology_size=int(abilities + links),
                    relation_density=min(10.0, rel_density),
                    cluster_depth=min(1.0, float(max_depth) / 10.0),
                    coherence=max(0.0, min(1.0, coherence)),
                    contradiction_rate=max(0.0, min(1.0, contradictions_rate)),
                    ivm_heat=max(0.0, min(1.0, ivm_heat)),
                    topic_tracking=0.6 if len(str(stimulus_text or "").split()) > 2 else 0.3,
                )
                lang.update_lsv(metrics)
                self._last_language_status = lang.status()
            except Exception:
                pass

        self._record_function_outcome("aux.tick_modules", 1.0, evidence=1.0)

    def _infer_constraints_from_operation(self, op_name: str) -> FrozenSet[str]:
        canon = tuple(_canonical_constraints_for_operation(op_name))
        if canon:
            return frozenset(canon)

        name = str(op_name or "").strip().lower()
        axes: set[str] = set()

        if any(k in name for k in ("tick", "epoch", "time", "watch", "chain", "phase", "advance", "burst")):
            axes.add("temporal")
        if any(k in name for k in ("cost", "budget", "pressure", "relief", "energy", "diff", "amplifier", "tax", "sustain", "tolerance", "decay")):
            axes.add("energy")
        if any(k in name for k in ("bridge", "link", "inject", "promote", "partition", "interface", "coupling", "constraint", "boundary")):
            axes.add("boundary")
        if any(k in name for k in ("action", "sim", "episode", "behavior", "align", "mutation", "steer", "feedback", "learn", "agency")):
            axes.add("agency")
        if any(k in name for k in ("boot", "restore", "save", "load", "checkpoint", "identity", "state", "register", "validate", "status", "report", "root", "lineage", "ancestry", "exist")):
            axes.add("existence")

        if not axes:
            axes = {"existence", "temporal"}
        return frozenset(sorted(axes))

    def _register_object_operations(self, obj: Any, prefix: str) -> int:
        if obj is None:
            return 0
        owner_constraints = self._infer_constraints_from_operation(prefix)
        owner_module = str(getattr(type(obj), "__module__", "") or getattr(obj, "__module__", "") or "")
        owner_class = str(getattr(type(obj), "__name__", "") or "")
        owner_kind = "class" if isinstance(obj, type) else "object"
        self._register_surface_node(
            prefix,
            owner_kind,
            owner_constraints,
            module=owner_module,
            owner="",
            class_name=owner_class,
        )
        if owner_class:
            class_surface = f"class:{owner_module}.{owner_class}" if owner_module else f"class:{owner_class}"
            self._register_surface_node(
                class_surface,
                "class",
                owner_constraints,
                module=owner_module,
                owner="",
                class_name=owner_class,
            )
            self._record_surface_ripple(class_surface, prefix, "instantiates_surface", {
                "module": owner_module,
                "class_name": owner_class,
            })
        mapped = 0
        for name in dir(obj):
            if not name or name.startswith("_"):
                continue
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            if not callable(attr):
                continue
            op_name = f"{prefix}.{name}"
            if op_name in self._function_ancestry:
                continue
            inferred = self._infer_constraints_from_operation(op_name)
            self._register_function_ancestry(op_name, inferred)
            self._record_surface_ripple(prefix, op_name, "surface_expresses_method", {
                "module": owner_module,
                "class_name": owner_class,
                "method": str(name),
            })
            mapped += 1
        return mapped

    def _register_stack_surface_lineage(self) -> None:
        # Core steerer/system/bridge surfaces.
        self._register_object_operations(self, "steerer")
        self._register_object_operations(self._b, "bridge")
        self._register_object_operations(self._s, "systems")

        # Layer objects reachable from StackSystems.
        for attr in ("contract", "lattice", "dimensional", "perception", "identity", "simulation", "chamber", "genealogy", "checkpoint"):
            obj = getattr(self._s, attr, None)
            self._register_object_operations(obj, attr)

    def _function_group(self, fn_name: str) -> str:
        fn = str(fn_name or "")
        return "action" if fn.startswith("action:") else "system"

    def _function_similarity(self, a: str, b: str) -> float:
        sa = set(self._function_ancestry.get(str(a), frozenset()))
        sb = set(self._function_ancestry.get(str(b), frozenset()))
        if not sa and not sb:
            return 0.0
        inter = len(sa & sb)
        union = len(sa | sb) or 1
        return float(inter) / float(union)

    def _append_function_history(self, fn_name: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._function_history_seq += 1
        rec = {
            "seq": int(self._function_history_seq),
            "function": str(fn_name),
            "event": str(event_type),
            "constraints": sorted(self._function_ancestry.get(str(fn_name), frozenset())),
        }
        if payload:
            rec.update(dict(payload))
        self._function_history.append(rec)

    def _append_surface_history(self, surface_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._surface_history_seq += 1
        node = dict(self._surface_lineage.get(str(surface_id), {}) or {})
        rec = {
            "seq": int(self._surface_history_seq),
            "surface": str(surface_id),
            "event": str(event_type),
            "surface_kind": str(node.get("surface_kind", "") or ""),
            "constraints": sorted(node.get("constraints", []) or []),
        }
        if payload:
            rec.update(dict(payload))
        self._surface_history.append(rec)

    def _surface_parent_key(self, surface_id: str) -> str:
        sid = str(surface_id or "").strip()
        if sid.startswith("action:"):
            return "action_registry"
        if "." in sid:
            return sid.rsplit(".", 1)[0]
        if ":" in sid:
            return sid.split(":", 1)[0]
        return ""

    def _register_surface_node(
        self,
        surface_id: str,
        surface_kind: str,
        constraints: Iterable[str],
        module: str = "",
        owner: str = "",
        class_name: str = "",
    ) -> None:
        key = str(surface_id or "").strip()
        if not key:
            return
        normalized = sorted(_normalize_ancestry_constraints(constraints or []))
        is_new = key not in self._surface_lineage
        rec = dict(self._surface_lineage.get(key, {}) or {})
        rec["surface_id"] = key
        rec["surface_kind"] = str(surface_kind or rec.get("surface_kind", "operation") or "operation")
        rec["constraints"] = list(normalized)
        rec["module"] = str(module or rec.get("module", "") or "")
        rec["owner"] = str(owner or rec.get("owner", "") or "")
        rec["class_name"] = str(class_name or rec.get("class_name", "") or "")
        rec["growth_generation"] = int(rec.get("growth_generation", 1) or 1)
        growth = dict(rec.get("growth_reflection", {}) or {})
        growth["registered"] = True
        growth["constraints"] = list(normalized)
        growth["owner"] = rec["owner"]
        growth["module"] = rec["module"]
        growth["class_name"] = rec["class_name"]
        growth.setdefault("development_required", True)
        growth.setdefault("system_reflection_required", True)
        growth.setdefault("method_count", 0)
        growth.setdefault("ripple_events", 0)
        growth.setdefault("descendant_surfaces", 0)
        parent = self._surface_parent_key(key)
        if parent and parent != key:
            growth["parent_surface"] = parent
        rec["growth_reflection"] = growth
        ripple = dict(rec.get("ripple_effects", {}) or {})
        ripple.setdefault("outbound", {})
        ripple.setdefault("inbound", {})
        ripple.setdefault("ripple_kinds", {})
        ripple.setdefault("propagated_modules", sorted(x for x in {rec["module"]} if x))
        ripple.setdefault("propagated_surface_kinds", sorted(x for x in {rec["surface_kind"]} if x))
        ripple["descendant_count"] = int(len(ripple.get("outbound", {}) or {}))
        ripple["ancestor_count"] = int(len(ripple.get("inbound", {}) or {}))
        rec["ripple_effects"] = ripple
        self._surface_lineage[key] = rec
        if is_new:
            self._append_surface_history(key, "registered", {
                "registration_index": int(len(self._surface_lineage)),
            })

    def _record_surface_ripple(
        self,
        source_id: str,
        target_id: str,
        ripple_kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        source = str(source_id or "").strip()
        target = str(target_id or "").strip()
        if not source or not target or source == target:
            return
        self._register_surface_node(source, "surface", self._function_ancestry.get(source, frozenset()))
        self._register_surface_node(target, "surface", self._function_ancestry.get(target, frozenset()))
        src = dict(self._surface_lineage.get(source, {}) or {})
        dst = dict(self._surface_lineage.get(target, {}) or {})
        src_ripple = dict(src.get("ripple_effects", {}) or {})
        dst_ripple = dict(dst.get("ripple_effects", {}) or {})
        src_out = dict(src_ripple.get("outbound", {}) or {})
        dst_in = dict(dst_ripple.get("inbound", {}) or {})
        ripple_payload = dict(payload or {})
        ripple_payload["kind"] = str(ripple_kind or "growth_ripple")
        src_out[target] = ripple_payload
        dst_in[source] = ripple_payload
        src_ripple["outbound"] = src_out
        dst_ripple["inbound"] = dst_in
        src_ripple["descendant_count"] = int(len(src_out))
        dst_ripple["ancestor_count"] = int(len(dst_in))
        src_kinds = dict(src_ripple.get("ripple_kinds", {}) or {})
        src_kinds[str(ripple_kind or "growth_ripple")] = int(src_kinds.get(str(ripple_kind or "growth_ripple"), 0) or 0) + 1
        src_ripple["ripple_kinds"] = src_kinds
        for rec, ripple in ((src, src_ripple), (dst, dst_ripple)):
            growth = dict(rec.get("growth_reflection", {}) or {})
            growth["ripple_events"] = int(growth.get("ripple_events", 0) or 0) + 1
            growth["descendant_surfaces"] = int(ripple.get("descendant_count", 0) or 0)
            propagated_modules = set(ripple.get("propagated_modules", []) or [])
            if payload and str(payload.get("module", "") or "").strip():
                propagated_modules.add(str(payload.get("module")))
            if rec.get("module"):
                propagated_modules.add(str(rec.get("module")))
            ripple["propagated_modules"] = sorted(x for x in propagated_modules if x)
            propagated_kinds = set(ripple.get("propagated_surface_kinds", []) or [])
            if rec.get("surface_kind"):
                propagated_kinds.add(str(rec.get("surface_kind")))
            ripple["propagated_surface_kinds"] = sorted(x for x in propagated_kinds if x)
            rec["growth_reflection"] = growth
            rec["ripple_effects"] = ripple
        self._surface_lineage[source] = src
        self._surface_lineage[target] = dst
        self._append_surface_history(source, "ripple_outbound", {
            "target_surface": target,
            "ripple_kind": str(ripple_kind or "growth_ripple"),
        })
        self._append_surface_history(target, "ripple_inbound", {
            "source_surface": source,
            "ripple_kind": str(ripple_kind or "growth_ripple"),
        })

    def _record_function_outcome(self, fn_name: str, score: float, evidence: float = 1.0) -> None:
        fn = str(fn_name)
        if fn not in self._function_ancestry:
            if self._strict_lineage:
                self._lineage_reject(
                    "cannot record outcome for unregistered function in strict mode",
                    f"fn={fn}",
                )
            inferred = self._infer_constraints_from_operation(fn)
            self._register_function_ancestry(fn, inferred)
        s = max(0.0, min(1.0, float(score)))
        ev = max(1.0, float(evidence))
        rec = dict(self._function_perf.get(fn, {}) or {})
        alpha = 0.12
        prev = float(rec.get("ema", 0.0) or 0.0)
        calls_before = float(rec.get("calls", 0.0) or 0.0)
        rec["ema"] = ((1.0 - alpha) * prev) + (alpha * s)
        rec["best"] = max(float(rec.get("best", 0.0) or 0.0), s)
        rec["calls"] = float(rec.get("calls", 0.0) or 0.0) + ev
        self._function_perf[fn] = rec
        self._append_function_history(fn, "outcome", {
            "score": round(float(s), 6),
            "evidence": round(float(ev), 6),
            "ema_before": round(float(prev), 6),
            "ema_after": round(float(rec.get("ema", 0.0) or 0.0), 6),
            "ema_delta": round(float(rec.get("ema", 0.0) or 0.0) - float(prev), 6),
            "calls_before": round(float(calls_before), 6),
            "calls_after": round(float(rec.get("calls", 0.0) or 0.0), 6),
        })
        self._try_promote_function_offspring(fn)

    def _try_promote_function_offspring(self, child_fn: str) -> None:
        child = str(child_fn)
        child_rec = dict(self._function_perf.get(child, {}) or {})
        child_calls = float(child_rec.get("calls", 0.0) or 0.0)
        child_ema = float(child_rec.get("ema", 0.0) or 0.0)
        if child_calls < 6.0:
            return

        child_group = self._function_group(child)
        child_anc = set(self._function_ancestry.get(child, frozenset()))
        if not child_anc:
            return

        best_parent = None
        best_weighted_margin = 0.0
        best_sim = 0.0

        for parent, prec in self._function_perf.items():
            if parent == child:
                continue
            if self._function_group(parent) != child_group:
                continue
            p_calls = float((prec or {}).get("calls", 0.0) or 0.0)
            if p_calls < 6.0:
                continue
            sim = self._function_similarity(child, parent)
            if sim < 0.50:
                continue
            margin = child_ema - float((prec or {}).get("ema", 0.0) or 0.0)
            weighted = margin * sim
            if weighted > best_weighted_margin and margin > 0.03:
                best_weighted_margin = weighted
                best_parent = str(parent)
                best_sim = sim

        if not best_parent:
            return

        parent_gen = int((self._function_offspring.get(best_parent, {}) or {}).get("generation", 1) or 1)
        child_gen = max(2, parent_gen + 1)
        parent_anc = set(self._function_ancestry.get(best_parent, frozenset()))
        bias_constraints = sorted(child_anc - parent_anc)
        if not bias_constraints:
            bias_constraints = sorted(child_anc)

        self._function_offspring[child] = {
            "parent": best_parent,
            "generation": int(child_gen),
            "similarity": float(best_sim),
            "performance_margin": float(max(0.0, child_ema - float(self._function_perf.get(best_parent, {}).get("ema", 0.0) or 0.0))),
            "bias_constraints": list(bias_constraints),
        }
        payload = {
            "child": child,
            "parent": best_parent,
            "generation": int(child_gen),
            "similarity": round(float(best_sim), 6),
            "performance_margin": round(float(max(0.0, child_ema - float(self._function_perf.get(best_parent, {}).get("ema", 0.0) or 0.0))), 6),
            "bias_constraints": list(bias_constraints),
        }
        self._append_function_history(child, "offspring_promoted", payload)
        self._append_function_history(best_parent, "ripple_to_offspring", payload)
        self._record_surface_ripple(best_parent, child, "offspring_promoted", payload)

    def _function_bias_constraints(self, source_fn: str) -> FrozenSet[str]:
        rel = dict(self._function_offspring.get(str(source_fn), {}) or {})
        bias = [str(c).strip().lower() for c in (rel.get("bias_constraints", []) or [])]
        return frozenset(x for x in bias if x in set(_IVM_AXIS_LABELS))

    def _lineage_reject(self, reason: str, detail: str = "") -> None:
        self._lineage_rejections += 1
        msg = f"[LINEAGE] Rejected: {reason}"
        if detail:
            msg += f" ({detail})"
        raise ValueError(msg)

    def _resolve_constraints_explicit(
        self,
        requested: Iterable[str],
        hint_text: str,
        source_fn: str,
    ) -> Tuple[FrozenSet[str], List[str], bool]:
        requested_set = frozenset(str(c).strip().lower() for c in (requested or frozenset()))
        normalized = _normalize_ancestry_constraints(requested_set)
        bad = sorted(x for x in requested_set if x not in set(_IVM_AXIS_LABELS))
        synthesized = (not normalized) or bool(bad)

        if not normalized:
            if self._strict_lineage:
                self._lineage_default_floor_events += 1
                self._lineage_reject(
                    "strict lineage requires explicit base constraints",
                    f"source={source_fn}, hint={hint_text}",
                )
            normalized = _synthesize_lineage(requested_set, hint_text=hint_text)
            self._lineage_default_floor_events += 1

        if bad:
            if self._strict_lineage:
                self._lineage_reject(
                    "unknown constraint labels in strict mode",
                    f"source={source_fn}, labels={bad}",
                )
            print(f"[STEERER] Undefined labels {bad}; synthesized lineage={sorted(normalized)}")

        if synthesized:
            self._lineage_synthesized_events += 1
        return normalized, bad, synthesized

    def _register_function_ancestry(self, fn_name: str, constraints: Iterable[str]) -> None:
        requested = [str(c).strip().lower() for c in (constraints or [])]
        ancestry = _normalize_ancestry_constraints(requested)
        if not ancestry:
            if self._strict_lineage:
                self._lineage_reject(
                    "function ancestry missing explicit constraints",
                    f"fn={fn_name}",
                )
            ancestry = _synthesize_lineage(requested, hint_text=str(fn_name))
            self._lineage_synthesized_events += 1
            self._lineage_default_floor_events += 1
        key = str(fn_name)
        is_new = key not in self._function_ancestry
        self._function_ancestry[key] = ancestry
        # Seed a perf slot at registration time so no mapped operation
        # can remain outside reporting coverage.
        if key not in self._function_perf:
            self._function_perf[key] = {"ema": 0.0, "best": 0.0, "calls": 0.0}
        parent_surface = self._surface_parent_key(key)
        self._register_surface_node(
            key,
            "operation" if "." not in key else "method",
            ancestry,
            owner=parent_surface,
            class_name=parent_surface.rsplit(".", 1)[-1] if "." in parent_surface else "",
        )
        if is_new:
            self._append_function_history(key, "registered", {
                "registration_index": int(len(self._function_ancestry)),
            })
            if parent_surface:
                self._register_surface_node(parent_surface, "container", ancestry)
                self._record_surface_ripple(parent_surface, key, "container_expresses_operation", {
                    "operation": key,
                })

    def _with_trace_ancestry(self, trace: ActionTrace, source_fn: str) -> ActionTrace:
        raw_constraints = [str(c).strip().lower() for c in (trace.constraints_used or frozenset())]
        ancestry = _normalize_ancestry_constraints(raw_constraints)
        synthesized = False
        if not ancestry:
            hint_meta = trace.meta if isinstance(trace.meta, dict) else {}
            hint = f"{trace.name} {json.dumps(hint_meta, sort_keys=True)}"
            if self._strict_lineage:
                self._lineage_default_floor_events += 1
                self._lineage_reject(
                    "trace missing explicit constraints",
                    f"source={source_fn}, trace={trace.name}",
                )
            ancestry = _synthesize_lineage(raw_constraints, hint_text=hint)
            synthesized = True

        bias_constraints = self._function_bias_constraints(source_fn)
        if bias_constraints:
            ancestry = frozenset(sorted(set(ancestry) | set(bias_constraints)))

        meta = _stamp_ancestry_meta(trace.meta, ancestry, source_fn)
        if synthesized:
            self._lineage_synthesized_events += 1
            self._lineage_default_floor_events += 1
            meta["ancestry_synthesized"] = True
            meta["ancestry_original_constraints"] = sorted(set(raw_constraints))
        if bias_constraints:
            meta["function_bias_constraints"] = sorted(set(bias_constraints))
            rel = dict(self._function_offspring.get(str(source_fn), {}) or {})
            if rel:
                meta["function_offspring_parent"] = rel.get("parent")
                meta["function_offspring_generation"] = int(rel.get("generation", 1) or 1)
                meta["function_offspring_similarity"] = float(rel.get("similarity", 0.0) or 0.0)

        # Ensure chamber-facing constraints are always lawful base labels.
        return ActionTrace(name=trace.name, constraints_used=frozenset(ancestry), meta=meta)

    def ancestry_report(self) -> Dict[str, Any]:
        mapped = len(self._function_ancestry)
        coverage = sorted({c for vals in self._function_ancestry.values() for c in vals})
        missing_base = sorted(set(_IVM_AXIS_LABELS) - set(coverage))

        perf_tracked = int(len(self._function_perf))
        perf_keys = set(self._function_perf.keys())
        mapped_keys = set(self._function_ancestry.keys())
        unmapped_perf = sorted(perf_keys - mapped_keys)
        mapped_untracked = sorted(mapped_keys - perf_keys)

        prefix_counts: Dict[str, int] = {}
        for fn in mapped_keys:
            if "." in fn:
                prefix = fn.split(".", 1)[0]
            elif ":" in fn:
                prefix = fn.split(":", 1)[0]
            else:
                prefix = "core"
            prefix_counts[prefix] = int(prefix_counts.get(prefix, 0)) + 1

        hot = sorted(
            self._function_perf.items(),
            key=lambda kv: float((kv[1] or {}).get("calls", 0.0) or 0.0),
            reverse=True,
        )[:10]
        hot_ops = [
            {
                "name": str(name),
                "calls": float((rec or {}).get("calls", 0.0) or 0.0),
                "ema": float((rec or {}).get("ema", 0.0) or 0.0),
            }
            for name, rec in hot
        ]

        ripple_sources = sorted(
            (
                {
                    "name": str(name),
                    "children": int(sum(1 for rel in self._function_offspring.values() if str(rel.get("parent", "")) == str(name))),
                    "calls": float((self._function_perf.get(name, {}) or {}).get("calls", 0.0) or 0.0),
                    "ema": float((self._function_perf.get(name, {}) or {}).get("ema", 0.0) or 0.0),
                }
                for name in mapped_keys
            ),
            key=lambda rec: (int(rec.get("children", 0) or 0), float(rec.get("ema", 0.0) or 0.0)),
            reverse=True,
        )[:10]

        surface_nodes = int(len(self._surface_lineage))
        surface_ripple_roots = sorted(
            (
                {
                    "name": str(name),
                    "surface_kind": str((rec or {}).get("surface_kind", "") or ""),
                    "descendants": int(((rec or {}).get("ripple_effects", {}) or {}).get("descendant_count", 0) or 0),
                    "module": str((rec or {}).get("module", "") or ""),
                }
                for name, rec in self._surface_lineage.items()
            ),
            key=lambda rec: (int(rec.get("descendants", 0) or 0), str(rec.get("surface_kind", ""))),
            reverse=True,
        )[:10]
        recent_history = list(self._function_history)[-20:]
        recent_surface_history = list(self._surface_history)[-20:]

        return {
            "mapped_functions": mapped,
            "surface_nodes": surface_nodes,
            "performance_tracked": perf_tracked,
            "performance_coverage_rate": (float(perf_tracked) / float(max(1, mapped))),
            "strict_lineage_enabled": bool(self._strict_lineage),
            "lineage_rejections": int(self._lineage_rejections),
            "lineage_synthesized_events": int(self._lineage_synthesized_events),
            "lineage_default_floor_events": int(self._lineage_default_floor_events),
            "coverage": coverage,
            "missing_base_constraints": missing_base,
            "offspring_relations": int(len(self._function_offspring)),
            "history_events": int(len(self._function_history)),
            "prefix_counts": dict(sorted(prefix_counts.items(), key=lambda kv: kv[0])),
            "unmapped_perf_count": int(len(unmapped_perf)),
            "unmapped_perf_sample": unmapped_perf[:12],
            "mapped_untracked_count": int(len(mapped_untracked)),
            "mapped_untracked_sample": mapped_untracked[:12],
            "hot_operations": hot_ops,
            "top_ripple_sources": ripple_sources,
            "surface_history_events": int(len(self._surface_history)),
            "top_surface_ripple_roots": surface_ripple_roots,
            "recent_history": recent_history,
            "recent_surface_history": recent_surface_history,
        }

    def validate_ancestry(self) -> bool:
        rep = self.ancestry_report()
        ok = len(rep["missing_base_constraints"]) == 0 and rep["mapped_functions"] > 0
        if not ok:
            return False
        if bool(rep.get("strict_lineage_enabled", False)):
            if int(rep.get("lineage_default_floor_events", 0) or 0) > 0:
                return False
            if int(rep.get("lineage_synthesized_events", 0) or 0) > 0:
                return False
        return True

    def tick(self, n: int = 1,
             action: Optional[str] = None) -> List[Optional[Any]]:
        """
        Advance the chamber n ticks.

        Parameters
        ----------
        n      : number of ticks
        action : optional name of a specific action to inject each tick
                 (must be in available_actions()). If None, cycles the
                 default action schedule.

        Returns list of tick results (None = no relief, non-None = relief event).
        """
        if not self._s.has("chamber"):
            print("[STEERER] No chamber active.")
            return []

        fixed_trace: Optional[ActionTrace] = None
        if action:
            fixed_trace = self._action_map.get(action)
            if fixed_trace is None:
                print(f"[STEERER] Unknown action '{action}'. "
                      f"Use available_actions() to see valid names.")
                return []

        results: List[Optional[Any]] = []
        cycle = DEFAULT_ACTION_CYCLE
        for i in range(n):
            t = fixed_trace if fixed_trace else cycle[self._tick_cursor % len(cycle)]
            t = self._with_trace_ancestry(t, source_fn="steerer.tick")
            r = self._s.chamber.tick(t)
            try:
                self._advance_intake_pipeline(stimulus_text=str(getattr(t, "name", "tick")), tick=self._tick_cursor + 1)
            except Exception:
                pass
            try:
                self._advance_auxiliary_modules(stimulus_text=str(getattr(t, "name", "tick")), tick=self._tick_cursor + 1)
            except Exception:
                pass
            results.append(r)
            self._tick_cursor += 1

            # Keep link-growth stagnation signals live in tick() path too (watch/manual modes).
            genealogy = self._s.genealogy
            n_links_tick = len(getattr(genealogy, "links", {})) if genealogy is not None else 0
            n_abilities_tick = len(getattr(genealogy, "abilities", {})) if genealogy is not None else 0
            self._recent_total_links.append(int(n_links_tick))
            self._recent_total_abilities.append(int(n_abilities_tick))
            if int(n_links_tick) != int(self._last_links_count):
                self._last_links_count = int(n_links_tick)
                self._last_link_change_tick = int(self._tick_cursor)
            if int(n_abilities_tick) != int(self._last_abilities_count):
                self._last_abilities_count = int(n_abilities_tick)
                self._last_ability_change_tick = int(self._tick_cursor)

        relief_hits = sum(1 for r in results if r is not None)
        self._session_relief_events += relief_hits
        self._session_chain_ticks += len(results)
        self._refresh_operator_gradients()
        tick_score = (float(relief_hits) / float(max(1, len(results))))
        self._record_function_outcome("tick", tick_score, evidence=float(max(1, len(results))))
        if fixed_trace is not None:
            self._record_function_outcome(f"action:{fixed_trace.name}", tick_score, evidence=float(max(1, len(results))))
        return results

    def inject(self, action: str) -> Optional[Any]:
        """
        Inject exactly one tick of a named action.
        The chamber physics decide whether relief occurs.
        """
        results = self.tick(n=1, action=action)
        out = results[0] if results else None
        self._record_function_outcome("inject", 1.0 if out is not None else 0.0, evidence=1.0)
        return out

    def inject_custom(self,
                      name:        str,
                      constraints: FrozenSet[str],
                      meta:        Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Inject a custom ActionTrace by specifying name and constraint axes.
        Undefined labels are lineage-synthesized instead of rejected.
        The trace enters the chamber lawfully — no result guaranteed.
        """
        inferred_constraints, bad, synthesized = self._resolve_constraints_explicit(
            requested=constraints,
            hint_text=name,
            source_fn="steerer.inject_custom",
        )

        meta_payload = {"custom": True, "lineage_synthesized": bool(synthesized)}
        if bad:
            meta_payload["lineage_bad_labels"] = list(bad)
        if isinstance(meta, dict):
            meta_payload.update(meta)
        meta_payload = self._auto_seed_directive(name=name, constraints=inferred_constraints, meta=meta_payload)

        trace = ActionTrace(
            name             = name,
            constraints_used = inferred_constraints,
            meta             = meta_payload,
        )
        trace = self._with_trace_ancestry(trace, source_fn="steerer.inject_custom")
        if not self._s.has("chamber"):
            print("[STEERER] No chamber active.")
            return None

            result = self._s.chamber.tick(trace)
            try:
                self._advance_intake_pipeline(stimulus_text=str(name), tick=self._tick_cursor + 1)
            except Exception:
                pass
            try:
                self._advance_auxiliary_modules(stimulus_text=str(name), tick=self._tick_cursor + 1)
            except Exception:
                pass
            self._tick_cursor += 1
        self._session_chain_ticks += 1
        if result is not None:
            self._session_relief_events += 1
        score = 1.0 if result is not None else 0.0
        self._record_function_outcome("inject_custom", score, evidence=1.0)
        self._record_function_outcome(f"action:{name}", score, evidence=1.0)
        return result
    def chain_burst(self,
                    n:          int  = 1000,
                    epoch_size: int  = 200,
                    verbose:    bool = True) -> Dict[str, Any]:
        """
        Run n ticks of the evolutionary chain, logging a summary every
        epoch_size ticks. Then sync newly promoted links to the simulation.

        This is the primary way to grow the evolutionary genealogy lawfully —
        no teleology, no result injection.
        """
        if not self._s.has("chamber"):
            print("[STEERER] No chamber active.")
            return {}

        t_start      = time.time()
        relief_events = 0
        epoch_relief_events = 0
        cycle         = DEFAULT_ACTION_CYCLE
        genealogy = self._s.genealogy
        prev_link_count = len(getattr(genealogy, "links", {})) if genealogy is not None else 0
        conflict_injected_total = 0
        conflict_resolved_total = 0
        action_counts: Dict[str, int] = {}
        action_relief_hits: Dict[str, int] = {}

        for i in range(n):
            action = cycle[self._tick_cursor % len(cycle)]
            action_trace = action
            action_name = None
            if isinstance(action, ActionTrace):
                action_trace = self._with_trace_ancestry(action, source_fn="steerer.chain_burst")
                action_name = str(action_trace.name)
                action_counts[action_name] = int(action_counts.get(action_name, 0)) + 1
            result = self._s.chamber.tick(action_trace)
            try:
                _stim = str(action_name or getattr(action_trace, "name", "chain_burst"))
                self._advance_intake_pipeline(stimulus_text=_stim, tick=self._tick_cursor + 1)
            except Exception:
                pass
            try:
                _stim = str(action_name or getattr(action_trace, "name", "chain_burst"))
                self._advance_auxiliary_modules(stimulus_text=_stim, tick=self._tick_cursor + 1)
            except Exception:
                pass
            if result is not None:
                relief_events += 1
                epoch_relief_events += 1
                if action_name is not None:
                    action_relief_hits[action_name] = int(action_relief_hits.get(action_name, 0)) + 1
            self._tick_cursor += 1
            n_links_tick = len(getattr(genealogy, "links", {})) if genealogy is not None else 0
            n_abilities_tick = len(getattr(genealogy, "abilities", {})) if genealogy is not None else 0
            self._recent_total_links.append(int(n_links_tick))
            self._recent_total_abilities.append(int(n_abilities_tick))
            if int(n_links_tick) != int(self._last_links_count):
                self._last_links_count = int(n_links_tick)
                self._last_link_change_tick = int(self._tick_cursor)
            if int(n_abilities_tick) != int(self._last_abilities_count):
                self._last_abilities_count = int(n_abilities_tick)
                self._last_ability_change_tick = int(self._tick_cursor)

            if (i + 1) % epoch_size == 0:
                n_links = len(getattr(genealogy, "links", {})) if genealogy is not None else 0
                promoted_delta = max(0, n_links - prev_link_count)
                prev_link_count = n_links
                epoch_relief_rate = epoch_relief_events / float(max(1, epoch_size))
                epoch_bridge_rate = promoted_delta / float(max(1, epoch_size))
                self._recent_relief_rates.append(epoch_relief_rate)
                self._recent_bridge_rates.append(epoch_bridge_rate)
                self._recent_link_growth_rates.append(epoch_bridge_rate)
                epoch_relief_events = 0

                plateau_flags = self._plateau_flags()
                plateau = any(plateau_flags.values())
                plateau_pressure = self._apply_plateau_pressure(plateau_flags, verbose=verbose) if plateau else {"applied": 0, "metrics": []}
                if plateau and (self._tick_cursor - self._last_conflict_tick) >= self._conflict_cooldown_ticks:
                    _conf = self._inject_conflict_curriculum(rounds=2, verbose=verbose)
                    conflict_injected_total += int(_conf.get("injected", 0) or 0)
                    conflict_resolved_total += int(_conf.get("resolved", 0) or 0)

                if verbose and self._s.has("printer"):
                    print(f"  [CHAIN] tick {self._tick_cursor:>7,}  "
                          f"relief={relief_events}  links={n_links}  "
                          f"elapsed={time.time()-t_start:.1f}s")

                # Update operator pressure gradients during chain runs regardless
                # of verbose mode; otherwise quiet watch appears pressure-static.
                self._refresh_operator_gradients()

        # Sync bridge: inject promoted links → simulation
        bridge_events = self._b.inject_promoted_links()
        bridge_score = float(len(bridge_events)) / float(max(1, n))
        self._record_function_outcome("bridge.inject_promoted_links", max(0.0, min(1.0, bridge_score)), evidence=float(max(1, len(bridge_events))))

        # Flush genealogy fossil record to disk
        if self._s.has("genealogy"):
            try:
                self._s.genealogy.flush_files()
            except Exception:
                pass

        self._session_chain_ticks += n
        self._session_relief_events += relief_events
        self._session_bridge_events += len(bridge_events)

        relief_rate = (relief_events / float(max(1, n)))
        bridge_rate = (len(bridge_events) / float(max(1, n)))
        self._recent_relief_rates.append(relief_rate)
        self._recent_bridge_rates.append(bridge_rate)

        conflict_summary = {"injected": 0, "resolved": 0, "events": []}
        plateau_flags = self._plateau_flags()
        plateau = any(plateau_flags.values())
        plateau_pressure = self._apply_plateau_pressure(plateau_flags, verbose=verbose) if plateau else {"applied": 0, "metrics": []}
        if plateau and (self._tick_cursor - self._last_conflict_tick) >= self._conflict_cooldown_ticks:
            conflict_summary = self._inject_conflict_curriculum(rounds=3, verbose=verbose)
            conflict_injected_total += int(conflict_summary.get("injected", 0) or 0)
            conflict_resolved_total += int(conflict_summary.get("resolved", 0) or 0)

        conflict_rate = float(conflict_resolved_total) / float(max(1, conflict_injected_total))
        chain_score = max(0.0, min(1.0, (0.60 * relief_rate) + (0.30 * bridge_rate) + (0.10 * conflict_rate)))
        self._record_function_outcome("chain_burst", chain_score, evidence=float(max(1, n)))
        for action_name, count in action_counts.items():
            hits = int(action_relief_hits.get(action_name, 0))
            action_score = float(hits) / float(max(1, count))
            self._record_function_outcome(f"action:{action_name}", action_score, evidence=float(max(1, count)))

        elapsed = time.time() - t_start
        summary = {
            "ticks_run":     n,
            "total_ticks":   self._tick_cursor,
            "relief_events": relief_events,
            "bridge_events": len(bridge_events),
            "elapsed_s":     round(elapsed, 2),
            "ticks_per_sec": round(n / max(elapsed, 1e-6), 0),
            "plateau_detected": plateau,
            "plateau_flags": plateau_flags,
            "plateau_pressure_applied": plateau_pressure["applied"],
            "conflict_injected": int(conflict_injected_total),
            "conflict_resolved": int(conflict_resolved_total),
        }

        if verbose:
            print(f"\n  [CHAIN BURST COMPLETE]")
            print(f"    Ticks        : {n:,}")
            print(f"    Relief events: {relief_events}")
            print(f"    Bridge events: {len(bridge_events)}")
            if plateau:
                active_metrics = [k for k, v in plateau_flags.items() if v]
                print(f"    Plateau      : metrics={active_metrics} pressure_build={plateau_pressure['applied']} conflict_injected={int(conflict_injected_total)} resolved={int(conflict_resolved_total)}")
            else:
                print("    Plateau      : not detected")
            print(f"    Elapsed      : {elapsed:.2f}s  "
                  f"({summary['ticks_per_sec']:,.0f} ticks/s)")
            print()

        # Hidden post-run recommendation for Aurora. User is not shown by default.
        try:
            if _enqueue_recommendation is not None:
                out_dir = os.path.abspath("aurora_runtime_output")
                run_output_dir = out_dir
                try:
                    if self._s is not None and self._s.has("genealogy"):
                        run_output_dir = str(getattr(self._s.genealogy, "output_dir", out_dir) or out_dir)
                except Exception:
                    pass

                priority = 0.25
                if plateau:
                    priority += 0.35
                if relief_rate < 0.02:
                    priority += 0.25
                if bridge_rate < 0.005:
                    priority += 0.15
                priority = max(0.0, min(1.0, priority))

                body = (
                    f"Chain run finished ({n} ticks). "
                    f"relief_rate={relief_rate:.4f}, bridge_rate={bridge_rate:.4f}, "
                    f"plateau={bool(plateau)}. "
                    f"Consider adapting action-cycle emphasis toward the strongest improving lane, "
                    f"or discuss if plateau persists."
                )
                _enqueue_recommendation(
                    output_dir=out_dir,
                    source="aurora_runtime.UniverseSteerer.chain_burst",
                    run_type="chain_burst",
                    title="Post-run evolution recommendation",
                    body=body,
                    priority=float(priority),
                    context={
                        "summary": summary,
                        "relief_rate": float(relief_rate),
                        "bridge_rate": float(bridge_rate),
                        "plateau": bool(plateau),
                        "run_output_dir": os.path.abspath(run_output_dir),
                    },
                )
        except Exception:
            pass

        return summary

    def _pressure_contrib_snapshot(self) -> Dict[str, float]:
        out = {k: 0.0 for k in AXES}
        if per_operator_pressure is None or Constraint is None:
            return out
        try:
            snap = self._s.pressure_snapshot()
            if snap is None:
                return out
            pc = per_operator_pressure(snap)
            ordered = [Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A]
            for c in ordered:
                out[c.name] = float(pc.get(c, 0.0))
        except Exception:
            pass
        return out

    def _lane_pressure_delta(self, lane: str, before: Dict[str, float], after: Dict[str, float]) -> float:
        constraints = CONFLICT_LANE_CONSTRAINTS.get(lane, frozenset())
        axis_labels = []
        for lbl in constraints:
            ax = _IVM_TO_AXIS.get(str(lbl).strip().lower())
            if ax in AXES:
                axis_labels.append(ax)
        if not axis_labels:
            axis_labels = list(AXES)
        return sum(abs(float(after.get(ax, 0.0)) - float(before.get(ax, 0.0))) for ax in axis_labels)

    def _metric_slope(self, vals: Iterable[float]) -> float:
        seq = [float(v) for v in vals]
        if len(seq) < 2:
            return 0.0
        return (seq[-1] - seq[0]) / float(len(seq) - 1)

    def _plateau_flags(self) -> Dict[str, bool]:
        flags = {"relief": False, "bridge": False, "fitness": False, "links_total": False, "abilities_total": False}

        if len(self._recent_relief_rates) >= self._recent_relief_rates.maxlen:
            relief_slope = abs(self._metric_slope(self._recent_relief_rates))
            relief_var = statistics.pstdev(self._recent_relief_rates) if len(self._recent_relief_rates) >= 2 else 0.0
            flags["relief"] = (relief_slope <= 0.0015 and relief_var <= 0.03)

        if len(self._recent_bridge_rates) >= self._recent_bridge_rates.maxlen:
            bridge_slope = abs(self._metric_slope(self._recent_bridge_rates))
            bridge_var = statistics.pstdev(self._recent_bridge_rates) if len(self._recent_bridge_rates) >= 2 else 0.0
            near_zero_bridge = all(float(v) <= 1e-6 for v in list(self._recent_bridge_rates)[-BRIDGE_STAGNATION_EPOCHS:])
            flags["bridge"] = (bridge_slope <= 0.0010 and bridge_var <= 0.02) or near_zero_bridge

        if len(self._recent_fitness) >= 4:
            fitness_slope = abs(self._metric_slope(self._recent_fitness))
            fitness_var = statistics.pstdev(self._recent_fitness) if len(self._recent_fitness) >= 2 else 0.0
            flags["fitness"] = (fitness_slope <= 0.015 and fitness_var <= 0.03)

        if len(self._recent_total_links) >= self._recent_total_links.maxlen:
            link_span = max(self._recent_total_links) - min(self._recent_total_links)
            growth_slope = abs(self._metric_slope(self._recent_total_links))
            flags["links_total"] = (link_span <= 1 and growth_slope <= 0.01)

        if len(self._recent_total_abilities) >= self._recent_total_abilities.maxlen:
            ability_span = max(self._recent_total_abilities) - min(self._recent_total_abilities)
            ability_slope = abs(self._metric_slope(self._recent_total_abilities))
            flags["abilities_total"] = (ability_span <= 1 and ability_slope <= 0.01)

        # Hard stagnation triggers: no count change for a long tick interval.
        no_link_change_ticks = int(self._tick_cursor - self._last_link_change_tick)
        if no_link_change_ticks >= LINKS_STAGNATION_TICKS:
            flags["links_total"] = True

        no_ability_change_ticks = int(self._tick_cursor - self._last_ability_change_tick)
        if no_ability_change_ticks >= ABILITIES_STAGNATION_TICKS:
            flags["abilities_total"] = True

        return flags

    def _plateau_detected(self) -> bool:
        flags = self._plateau_flags()
        return any(bool(v) for v in flags.values())

    def _apply_plateau_pressure(self, flags: Dict[str, bool], verbose: bool = False) -> Dict[str, Any]:
        if not self._s.has("chamber"):
            return {"applied": 0, "metrics": []}

        applied = 0
        metric_names: List[str] = []
        for metric, is_plateau in flags.items():
            if not is_plateau:
                continue
            constraints = PLATEAU_METRIC_CONSTRAINTS.get(metric, frozenset({"temporal", "agency"}))
            trace = ActionTrace(
                name=f"plateau_pressure:{metric}",
                constraints_used=constraints,
                meta={"plateau_metric": metric, "pressure_build": True, "pulse": True},
            )
            trace = self._with_trace_ancestry(trace, source_fn="steerer.plateau_pressure")
            result = self._s.chamber.tick(trace)
            self._tick_cursor += 1
            self._session_chain_ticks += 1
            if result is not None:
                self._session_relief_events += 1
            self._session_plateau_pressure_events += 1
            self._plateau_metric_counts[metric] = self._plateau_metric_counts.get(metric, 0) + 1
            applied += 1
            metric_names.append(metric)

        if applied > 0:
            self._refresh_operator_gradients()
            if verbose:
                print(f"  [PLATEAU PRESSURE] applied={applied} metrics={metric_names}")

        return {"applied": applied, "metrics": metric_names}

    def _next_conflict_lane(self) -> str:
        def lane_score(name: str) -> float:
            attempts = max(1, self._lane_totals.get(name, 0))
            resolved = self._lane_resolved.get(name, 0)
            return resolved / float(attempts)

        scores = {lane: lane_score(lane) for lane in CONFLICT_LANES}
        min_score = min(scores.values()) if scores else 0.0
        weakest = [lane for lane in CONFLICT_LANES if abs(scores.get(lane, 0.0) - min_score) <= 1e-12]
        weakest = sorted(weakest, key=lambda lane: (self._lane_totals.get(lane, 0), lane))
        if not weakest:
            weakest = list(CONFLICT_LANES)
        lane = weakest[self._conflict_cursor % len(weakest)]
        self._conflict_cursor += 1
        return lane

    def _inject_conflict_curriculum(self, rounds: int = 3, verbose: bool = True) -> Dict[str, Any]:
        if not self._s.has("chamber"):
            return {"injected": 0, "resolved": 0, "events": []}

        events: List[Dict[str, Any]] = []
        resolved = 0

        for _ in range(max(1, rounds)):
            lane = self._next_conflict_lane()
            constraints = CONFLICT_LANE_CONSTRAINTS.get(lane, frozenset({"temporal", "agency"}))
            before = self._pressure_contrib_snapshot()
            trace = ActionTrace(
                name=f"conflict:{lane}",
                constraints_used=constraints,
                meta={
                    "curriculum": True,
                    "conflict_lane": lane,
                    "target_path": "intelligence_communication_meaning",
                    "pulse": True,
                    "conflict_strength": "high",
                },
            )
            trace = self._with_trace_ancestry(trace, source_fn="steerer.conflict_curriculum")
            result = self._s.chamber.tick(trace)
            self._tick_cursor += 1
            self._refresh_operator_gradients()
            after = self._pressure_contrib_snapshot()
            lane_delta = self._lane_pressure_delta(lane, before, after)
            execution_ok = (result is not None)
            pressure_ok = lane_delta >= float(self._conflict_pressure_resolve_eps)
            # Conflict curriculum success is pressure-gradient response.
            # Execution relief is tracked separately for diagnostics.
            ok = pressure_ok
            if ok:
                resolved += 1
            self._session_conflicts_injected += 1
            self._session_conflicts_resolved += 1 if ok else 0
            self._session_conflicts_resolved_execution += 1 if execution_ok else 0
            self._session_conflicts_resolved_pressure += 1 if pressure_ok else 0
            self._lane_totals[lane] = self._lane_totals.get(lane, 0) + 1
            self._lane_resolved[lane] = self._lane_resolved.get(lane, 0) + (1 if ok else 0)

            event = {
                "tick": self._tick_cursor,
                "lane": lane,
                "constraints": sorted(constraints),
                "resolved": ok,
                "execution_ok": execution_ok,
                "pressure_ok": pressure_ok,
                "pressure_effective": pressure_ok,
                "failed_gate": ("execution" if (not execution_ok) else ("pressure" if (not pressure_ok) else "none")),
                "lane_pressure_delta": lane_delta,
                "pressure_before": before,
                "pressure_after": after,
                "timestamp": time.time(),
            }
            events.append(event)
            self._conflict_log.append(event)

        self._last_conflict_tick = self._tick_cursor
        self._refresh_operator_gradients()

        if verbose:
            print("  [CURRICULUM] conflict burst injected")
            print(f"    Injected : {len(events)}")
            print(f"    Resolved : {resolved}")

        return {
            "injected": len(events),
            "resolved": resolved,
            "resolved_execution": sum(1 for e in events if bool(e.get("execution_ok", False))),
            "resolved_pressure": sum(1 for e in events if bool(e.get("pressure_ok", False))),
            "events": events,
        }

    def _axis_from_item_id(self, item_id: str, seen: Optional[set] = None) -> List[str]:
        tid = str(item_id or "")
        seen_links = seen or set()

        if tid.startswith("NC:") and ">" in tid:
            pair = tid[3:]
            left, right = pair.split(">", 1)
            axes = []
            for ax in (left.strip().upper(), right.strip().upper()):
                if ax in AXES:
                    axes.append(ax)
            return axes

        if tid.startswith("L:"):
            if tid in seen_links:
                return []
            seen_links.add(tid)
            if not self._s.has("genealogy"):
                return []
            link = self._s.genealogy.get_link(tid) if hasattr(self._s.genealogy, "get_link") else None
            if link is None:
                return []
            axes = []
            dom = str(getattr(link, "dominant_relief_axis", "") or "").upper()
            if dom in AXES:
                axes.append(dom)
            for parent in list(getattr(link, "parents", []) or []):
                axes.extend(self._axis_from_item_id(str(parent), seen=seen_links))
            return axes

        if ":" in tid:
            ax = tid.split(":", 1)[0].strip().upper()
            return [ax] if ax in AXES else []

        return []

    def _trait_semantic_card(self, link: Any) -> Dict[str, Any]:
        link_id = str(getattr(link, "id", "?"))
        dominant = str(getattr(link, "dominant_relief_axis", "X") or "X").upper()
        parents = list(getattr(link, "parents", []) or [])

        parent_axes: List[str] = []
        for p in parents:
            parent_axes.extend(self._axis_from_item_id(str(p), seen=set()))
        if not parent_axes and dominant in AXES:
            parent_axes = [dominant]

        counts: Dict[str, int] = {ax: 0 for ax in AXES}
        for ax in parent_axes:
            if ax in counts:
                counts[ax] += 1
        total = sum(counts.values()) or 1
        axis_mix = {ax: counts[ax] / float(total) for ax in AXES if counts[ax] > 0}

        lane_scores: Dict[str, float] = {k: 0.0 for k in CONFLICT_LANES}
        for ax, frac in axis_mix.items():
            impacts = AXIS_TO_PATH_IMPACT.get(ax, {})
            for lane in CONFLICT_LANES:
                lane_scores[lane] += frac * float(impacts.get(lane, 0.0))

        weighted = []
        for lane in CONFLICT_LANES:
            weighted.append(lane_scores[lane] * PATH_TARGET_WEIGHTS.get(lane, 1.0))
        align = (sum(weighted) / float(len(weighted))) if weighted else 0.0

        count = int(getattr(link, "count", 0) or 0)
        depth = int(getattr(link, "depth", 1) or 1)
        confidence = min(1.0, 0.55 + (0.003 * count) + (0.04 * max(0, depth - 1)))

        effect = AXIS_SEMANTIC_CORE.get(dominant, "mixed adaptation effect")
        meaning = f"{link_id} tends to reinforce {effect}."

        return {
            "link_id": link_id,
            "dominant_axis": dominant,
            "dominant_semantic": AXIS_SEMANTIC_CORE.get(dominant, "mixed"),
            "meaning": meaning,
            "parent_axes": parent_axes,
            "axis_mix": axis_mix,
            "lane_scores": lane_scores,
            "alignment_score": align,
            "confidence": confidence,
            "evidence_count": count,
            "depth": depth,
            "recommended": align >= 0.60 and confidence >= 0.65,
        }

    def emergent_trait_cards(self, top_n: int = 12) -> List[Dict[str, Any]]:
        if not self._s.has("genealogy"):
            return []
        links = list(getattr(self._s.genealogy, "links", {}).values())
        if not links:
            return []
        links_sorted = sorted(
            links,
            key=lambda l: (
                int(getattr(l, "count", 0) or 0),
                float(sum(getattr(l, "mean_relief", {}).values())) if hasattr(l, "mean_relief") else 0.0,
            ),
            reverse=True,
        )[:max(1, top_n)]
        cards = [self._trait_semantic_card(lnk) for lnk in links_sorted]
        cards.sort(key=lambda c: (float(c.get("alignment_score", 0.0)), float(c.get("confidence", 0.0))), reverse=True)
        return cards

    def stance_snapshot(self) -> Dict[str, Any]:
        gradients = {k: 0.0 for k in AXES}
        if REGISTRY is not None and Constraint is not None:
            ordered = [Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A]
            for c in ordered:
                gradients[c.name] = float(REGISTRY.operator(c).pressure_gradient)

        links_count = 0
        abilities_count = 0
        if self._s.has("genealogy"):
            links_count = len(getattr(self._s.genealogy, "links", {}))
            abilities_count = len(getattr(self._s.genealogy, "abilities", {}))

        budget = None
        if self._s.has("chamber") and getattr(self._s.chamber, "_budget", None) is not None:
            budget = float(self._s.chamber._budget.available)

        return {
            "ticks": int(self._tick_cursor),
            "relief_events": int(self._session_relief_events),
            "bridge_events": int(self._session_bridge_events),
            "epochs": int(self._session_epochs),
            "conflicts_injected": int(self._session_conflicts_injected),
            "conflicts_resolved": int(self._session_conflicts_resolved),
            "conflicts_resolved_execution": int(self._session_conflicts_resolved_execution),
            "conflicts_resolved_pressure": int(self._session_conflicts_resolved_pressure),
            "plateau_pressure_events": int(self._session_plateau_pressure_events),
            "links": int(links_count),
            "abilities": int(abilities_count),
            "links_total_current": int(links_count),
            "abilities_total_current": int(abilities_count),
            "budget": budget,
            "gradients": gradients,
        }

    def evolution_report(self) -> Dict[str, Any]:
        relief_rate = (self._session_relief_events / float(self._session_chain_ticks)) if self._session_chain_ticks else 0.0
        bridge_rate = (self._session_bridge_events / float(self._session_chain_ticks)) if self._session_chain_ticks else 0.0
        fitness_samples = len(self._recent_fitness)
        first_fitness = float(self._recent_fitness[0]) if fitness_samples else None
        last_fitness = float(self._recent_fitness[-1]) if fitness_samples else None
        fitness_delta = (float(last_fitness) - float(first_fitness)) if fitness_samples >= 2 else None
        lane_scores = {}
        for lane in CONFLICT_LANES:
            attempts = self._lane_totals.get(lane, 0)
            resolved = self._lane_resolved.get(lane, 0)
            lane_scores[lane] = {
                "attempts": attempts,
                "resolved": resolved,
                "resolution_rate": (resolved / float(attempts)) if attempts else 0.0,
                "weight": PATH_TARGET_WEIGHTS.get(lane, 1.0),
            }

        weighted = []
        for lane, rec in lane_scores.items():
            weighted.append(rec["resolution_rate"] * rec["weight"])
        raw_path_score = (sum(weighted) / float(len(weighted))) if weighted else 0.0

        if self._session_conflicts_injected > 0:
            path_score = raw_path_score
            path_aligned = path_score >= 0.55
            path_reason = "conflict curriculum resolution"
        else:
            # No conflict curriculum yet: use directional learning as provisional fit.
            path_score = 0.5 if self._session_chain_ticks > 0 else 0.0
            if fitness_samples >= 2 and first_fitness is not None and last_fitness is not None:
                fitness_non_regression = float(last_fitness) >= float(first_fitness)
            else:
                fitness_non_regression = True
            path_aligned = fitness_non_regression and (relief_rate >= 0.2)
            path_reason = "provisional (no conflict curriculum injected)"

        persistent_root_signature = "A^1*N^1*T^1"
        persistent_root_canonical = "A^1*N^1*T^1"
        persistent_root_expected_gen = 2
        persistent_root_observed_gen = None
        if self._s.has("genealogy") and hasattr(self._s.genealogy, "_persistent_root_lookup"):
            raw_sig, canonical_sig, _rec, observed_gen, expected_gen, _ok = self._s.genealogy._persistent_root_lookup()
            persistent_root_signature = str(raw_sig)
            persistent_root_canonical = str(canonical_sig)
            persistent_root_expected_gen = int(expected_gen)
            persistent_root_observed_gen = observed_gen

        top_coupling_effects = []
        validation_complete_count = 0
        validation_incomplete_count = 0
        validation_considered_count = 0
        validation_pending_count = 0
        validation_evidence_min = 0
        validation_completeness_rate = 0.0
        inheritance_breach_events = 0
        inheritance_breach_events_total = 0
        inheritance_breach_active_count = 0
        experiment_trials = 0
        experiment_adoptions = 0
        experiment_trials_issue = 0
        experiment_trials_exploratory = 0
        latest_experiment_trial = None
        latest_experiment_adoption = None
        promotion_stats = {}
        if self._s.has("genealogy") and hasattr(self._s.genealogy, "chain_report"):
            try:
                cr = self._s.genealogy.chain_report() or {}
                top_coupling_effects = list(cr.get("top_couplings", []) or [])[:6]
                validation_complete_count = int(cr.get("validation_complete_count", 0) or 0)
                validation_incomplete_count = int(cr.get("validation_incomplete_count", 0) or 0)
                validation_considered_count = int(cr.get("validation_considered_count", 0) or 0)
                validation_pending_count = int(cr.get("validation_pending_count", 0) or 0)
                validation_evidence_min = int(cr.get("validation_evidence_min", 0) or 0)
                validation_completeness_rate = float(cr.get("validation_completeness_rate", 0.0) or 0.0)
                inheritance_breach_events = int(cr.get("inheritance_breach_events", 0) or 0)
                inheritance_breach_events_total = int(cr.get("inheritance_breach_events_total", inheritance_breach_events) or inheritance_breach_events)
                inheritance_breach_active_count = int(cr.get("inheritance_breach_active_count", 0) or 0)
                experiment_trials = int(cr.get("experiment_trials", 0) or 0)
                experiment_adoptions = int(cr.get("experiment_adoptions", 0) or 0)
                experiment_trials_issue = int(cr.get("experiment_trials_issue", 0) or 0)
                experiment_trials_exploratory = int(cr.get("experiment_trials_exploratory", 0) or 0)
                latest_experiment_trial = cr.get("latest_experiment_trial")
                latest_experiment_adoption = cr.get("latest_experiment_adoption")
                promotion_stats = dict(cr.get("promotion_stats", {}) or {})
            except Exception:
                top_coupling_effects = []

        return {
            "ticks": self._session_chain_ticks,
            "relief_events": self._session_relief_events,
            "relief_rate": relief_rate,
            "bridge_events": self._session_bridge_events,
            "bridge_rate": bridge_rate,
            "epochs": self._session_epochs,
            "fitness_samples": fitness_samples,
            "fitness_start": first_fitness,
            "fitness_end": last_fitness,
            "fitness_delta": fitness_delta,
            "conflicts_injected": self._session_conflicts_injected,
            "conflicts_resolved": self._session_conflicts_resolved,
            "conflicts_resolved_execution": self._session_conflicts_resolved_execution,
            "conflicts_resolved_pressure": self._session_conflicts_resolved_pressure,
            "plateau_pressure_events": self._session_plateau_pressure_events,
            "plateau_metric_counts": dict(self._plateau_metric_counts),
            "links_plateau_window_span": (
                (max(self._recent_total_links) - min(self._recent_total_links))
                if len(self._recent_total_links) > 0 else 0
            ),
            "links_recent": list(self._recent_total_links)[-10:],
            "no_link_change_ticks": int(self._tick_cursor - self._last_link_change_tick),
            "no_ability_change_ticks": int(self._tick_cursor - self._last_ability_change_tick),
            "tolerance_events_applied": int(getattr(self._s.genealogy, "_tolerance_events_applied", 0) or 0) if self._s.has("genealogy") else 0,
            "tolerance_factor_ema": float(getattr(self._s.genealogy, "_tolerance_factor_ema", 1.0) or 1.0) if self._s.has("genealogy") else 1.0,
            "coupling_root_count": int(len(getattr(self._s.genealogy, "_coupling_roots", {}) or {})) if self._s.has("genealogy") else 0,
            "coupling_events": int(getattr(self._s.genealogy, "_coupling_events", 0) or 0) if self._s.has("genealogy") else 0,
            "persistent_root_ema": float(getattr(self._s.genealogy, "_persistent_pressure_root_ema", 0.0) or 0.0) if self._s.has("genealogy") else 0.0,
            "persistent_root_signature": persistent_root_signature,
            "persistent_root_signature_canonical": persistent_root_canonical,
            "persistent_root_expected_gen": persistent_root_expected_gen,
            "persistent_root_observed_gen": persistent_root_observed_gen,
            "top_coupling_effects": top_coupling_effects,
            "validation_complete_count": validation_complete_count,
            "validation_incomplete_count": validation_incomplete_count,
            "validation_considered_count": validation_considered_count,
            "validation_pending_count": validation_pending_count,
            "validation_evidence_min": validation_evidence_min,
            "validation_completeness_rate": validation_completeness_rate,
            "inheritance_breach_events": inheritance_breach_events,
            "inheritance_breach_events_total": inheritance_breach_events_total,
            "inheritance_breach_active_count": inheritance_breach_active_count,
            "experiment_trials": experiment_trials,
            "experiment_adoptions": experiment_adoptions,
            "experiment_trials_issue": experiment_trials_issue,
            "experiment_trials_exploratory": experiment_trials_exploratory,
            "latest_experiment_trial": latest_experiment_trial,
            "latest_experiment_adoption": latest_experiment_adoption,
            "promotion_stats": promotion_stats,
            "lanes": lane_scores,
            "path_alignment_score": path_score,
            "path_alignment_reason": path_reason,
            "path_aligned": path_aligned,
            "recent_conflicts": list(self._conflict_log)[-10:],
            "conflict_pressure_mean_delta": (
                sum(float(e.get("lane_pressure_delta", 0.0)) for e in list(self._conflict_log))
                / float(max(1, len(self._conflict_log)))
            ),
            "emergent_traits": self.emergent_trait_cards(top_n=12),
            "lineage_coverage": self.ancestry_report(),
        }

    def inject_conflict_rounds(self, rounds: int = 3, verbose: bool = False) -> Dict[str, Any]:
        """Public wrapper for targeted conflict curriculum injection."""
        return self._inject_conflict_curriculum(rounds=rounds, verbose=verbose)

    def print_evolution_report(self) -> None:
        rep = self.evolution_report()
        print("\n  SESSION EVOLUTION REVIEW")
        print("  " + "-" * 58)
        print(f"  Ticks              : {rep['ticks']:,}")
        print(f"  Relief events      : {rep['relief_events']}  (rate={rep['relief_rate']:.4f})")
        print(f"  Bridge events      : {rep['bridge_events']}  (rate={rep['bridge_rate']:.4f})")
        print(f"  Epochs             : {rep['epochs']}")
        fit_samples = int(rep.get("fitness_samples", 0) or 0)
        fit_start = rep.get("fitness_start")
        fit_end = rep.get("fitness_end")
        fit_delta = rep.get("fitness_delta")
        if fit_samples >= 2 and fit_start is not None and fit_end is not None and fit_delta is not None:
            print(f"  Fitness delta      : {float(fit_start):.3f} -> {float(fit_end):.3f}  (delta={float(fit_delta):+.3f})")
        elif fit_samples == 1 and fit_end is not None:
            print(f"  Fitness sample     : {float(fit_end):.3f}  (delta requires >=2 epochs)")
        else:
            print("  Fitness sample     : n/a  (run sim epochs to score fitness)")
        print(
            f"  Conflict curriculum: injected={rep['conflicts_injected']} "
            f"resolved={rep['conflicts_resolved']} "
            f"(execution_ok={int(rep.get('conflicts_resolved_execution',0))} "
            f"pressure_ok={int(rep.get('conflicts_resolved_pressure',0))})"
        )
        print(f"  Conflict pressure Δ : mean={float(rep.get('conflict_pressure_mean_delta',0.0)):.6f}")
        print(f"  Plateau pressure   : events={int(rep.get('plateau_pressure_events',0))} by_metric={rep.get('plateau_metric_counts', {})}")
        print(f"  Tolerance model    : events={int(rep.get('tolerance_events_applied',0))} ema_factor={float(rep.get('tolerance_factor_ema',1.0)):.3f}")
        print(f"  Coupling roots     : count={int(rep.get('coupling_root_count',0))} events={int(rep.get('coupling_events',0))}")
        print(
            f"  Coupling validation: complete={int(rep.get('validation_complete_count',0))} "
            f"incomplete={int(rep.get('validation_incomplete_count',0))} "
            f"considered={int(rep.get('validation_considered_count',0))} "
            f"pending={int(rep.get('validation_pending_count',0))} "
            f"min_events={int(rep.get('validation_evidence_min',0))} "
            f"completeness_rate={float(rep.get('validation_completeness_rate',0.0)):.3f} "
            f"inheritance_breaches={int(rep.get('inheritance_breach_events',0))} "
            f"active={int(rep.get('inheritance_breach_active_count',0))} "
            f"total={int(rep.get('inheritance_breach_events_total',rep.get('inheritance_breach_events',0)))}"
        )
        print(
            f"  Representation experiments: trials={int(rep.get('experiment_trials',0))} "
            f"(issue={int(rep.get('experiment_trials_issue',0))} exploratory={int(rep.get('experiment_trials_exploratory',0))}) "
            f"adoptions={int(rep.get('experiment_adoptions',0))}"
        )
        pstats = dict(rep.get('promotion_stats', {}) or {})
        if pstats:
            print(f"  Promotion diagnostics: {pstats}")
        latest_trial = rep.get('latest_experiment_trial')
        if isinstance(latest_trial, dict):
            print(
                f"    latest trial @tick={latest_trial.get('tick')} mode={latest_trial.get('trigger_mode')} "
                f"shape={latest_trial.get('shape')} Δ={float(latest_trial.get('improvement',0.0)):+.6f} "
                f"adopted={bool(latest_trial.get('adopted',False))}"
            )
        latest_exp = rep.get('latest_experiment_adoption')
        if isinstance(latest_exp, dict):
            print(
                f"    latest adoption @tick={latest_exp.get('tick')} shape={latest_exp.get('shape')} "
                f"from={latest_exp.get('from')} to={latest_exp.get('to')} score={latest_exp.get('score')}"
            )
        print(f"  Persistent root    : {rep.get('persistent_root_signature','A^1*N^1*T^1')} ema={float(rep.get('persistent_root_ema',0.0)):.11f} gen={rep.get('persistent_root_observed_gen')} expected={rep.get('persistent_root_expected_gen',2)}")
        top_couplings = list(rep.get("top_coupling_effects", []) or [])
        if top_couplings:
            print("  Coupling effects (top):")
            for c in top_couplings[:3]:
                print(
                    f"    {str(c.get('signature','?')):<18} gen={c.get('min_generation')}->{c.get('max_generation')} "
                    f"role={c.get('generation_role','?')} score={float(c.get('breeding_score_ema',0.0)):+.3f} "
                    f"effect={float(c.get('effect_ema',0.0)):.6f}"
                )
                print(f"      meaning: {c.get('effect_descriptor','')}")
                sem_txt = str(c.get('semantic_translation','') or '')
                if sem_txt:
                    print(
                        f"      semantic(v{int(c.get('semantic_version',0) or 0)} "
                        f"conf={float(c.get('semantic_confidence',0.0)):.3f}): {sem_txt}"
                    )
                reg = dict(c.get("regulation", {}) or {})
                if reg:
                    print(
                        f"      validation: complete={bool(reg.get('validation_complete',False))} "
                        f"inherit={float(reg.get('inheritance_score',0.0)):.3f} "
                        f"influence={float(reg.get('inheritance_influence_factor',1.0)):.3f} "
                        f"relation={float(reg.get('relation_score',0.0)):.3f} "
                        f"effect={float(reg.get('effect_score',0.0)):.3f} "
                        f"raw_effect={float(reg.get('effect_score_raw',0.0)):.3f} "
                        f"breed={float(reg.get('breeding_score',0.0)):.3f} "
                        f"representation={float(reg.get('representation_score',0.0)):.3f} "
                        f"sustain={float(reg.get('sustainability_score',0.0)):.3f} "
                        f"tax_factor={float(reg.get('persistence_tax_factor',1.0)):.3f} "
                        f"tax_tick={float(reg.get('persistence_tax_per_tick',0.0)):.3f} "
                        f"be_ticks={float(reg.get('break_even_ticks',0.0)):.2f} "
                        f"coverage={float(reg.get('requirement_coverage',0.0)):.3f} "
                        f"strictness={float(reg.get('strictness_index',0.0)):.3f} "
                        f"scale_depth={float(reg.get('scale_depth_index',0.0)):.3f} "
                        f"issues={reg.get('issues',[])}"
                    )
        lcov = dict(rep.get("lineage_coverage", {}) or {})
        if lcov:
            print(
                f"  Lineage coverage   : mapped={int(lcov.get('mapped_functions',0))} "
                f"perf={int(lcov.get('performance_tracked',0))} "
                f"coverage_rate={float(lcov.get('performance_coverage_rate',0.0)):.3f} "
                f"offspring={int(lcov.get('offspring_relations',0))}"
            )
            print(
                f"  Lineage gaps       : unmapped_perf={int(lcov.get('unmapped_perf_count',0))} "
                f"mapped_untracked={int(lcov.get('mapped_untracked_count',0))}"
            )
        print(f"  No-link-change     : ticks={int(rep.get('no_link_change_ticks',0))}")
        print(f"  No-ability-change  : ticks={int(rep.get('no_ability_change_ticks',0))}")
        print("  Lane resolution:")
        for lane in CONFLICT_LANES:
            lane_rec = rep["lanes"][lane]
            print(f"    {lane:<14} attempts={lane_rec['attempts']:<4} resolved={lane_rec['resolved']:<4} rate={lane_rec['resolution_rate']:.3f}")
        print(f"  Path alignment     : score={rep['path_alignment_score']:.3f}  aligned={rep['path_aligned']}")
        print(f"  Alignment basis    : {rep.get('path_alignment_reason', 'n/a')}")

        traits = rep.get("emergent_traits", []) or []
        if traits:
            print("  Emergent traits (top):")
            for t in traits[:6]:
                keep = "keep" if t.get("recommended") else "review"
                print(
                    f"    {t.get('link_id','?'):<14} axis={t.get('dominant_axis','?')} "
                    f"align={float(t.get('alignment_score',0.0)):.3f} "
                    f"conf={float(t.get('confidence',0.0)):.3f} "
                    f"action={keep}"
                )
                print(f"      meaning: {t.get('meaning','')}")

    # ------------------------------------------------------------------
    # SIMULATION STEERING
    # ------------------------------------------------------------------

    def sim_episode(self, **kwargs) -> Optional[EpisodeResult]:
        """
        Run one simulation episode through L7.

        Keyword args are forwarded to SimulationEngine.run_episode().
        Common kwargs: turns (int), avatar_personality (AvatarPersonality)

        After the episode, its fitness feeds back into the chain as real
        pressure — the universe stays connected.
        """
        if not self._s.has("simulation"):
            print("[STEERER] SimulationEngine not active (L7 missing).")
            return None

        # SimulationEngine.run_episode(**kwargs) → EpisodeResult
        result: EpisodeResult = self._s.simulation.run_episode(**kwargs)
        self._last_episode = result
        self._epoch_cursor += 1

        # Feed fitness back into chain (lawful — goes through chamber.tick)
        feedback_trace = self._b.feedback_episode_fitness(result)
        self._record_function_outcome("bridge.feedback_episode_fitness", 1.0 if feedback_trace is not None else 0.0, evidence=1.0)
        if feedback_trace and kwargs.get("verbose", False):
            print(f"  [BRIDGE] Fitness {getattr(result,'avg_fitness',0):.3f} "
                  f"→ chain via '{feedback_trace.name}'")

        score = max(0.0, min(1.0, float(getattr(result, 'avg_fitness', 0.0) or 0.0)))
        self._record_function_outcome("sim_episode", score, evidence=1.0)
        return result

    def sim_epoch(self,
                  episodes: int = 4,
                  turns:    int = 5,
                  **kwargs) -> Optional[Dict[str, Any]]:
        """
        Run a full simulation epoch through L7.

        After the epoch completes, all new promoted links are synced to
        the simulation. Epoch fitness feeds back to the chain.
        """
        if not self._s.has("simulation"):
            print("[STEERER] SimulationEngine not active (L7 missing).")
            return None

        # SimulationEngine.run_epoch(**kwargs) → Dict[str, Any]
        result: Dict[str, Any] = self._s.simulation.run_epoch(
            episodes_per_epoch = episodes,
            turns_per_episode  = turns,
            **kwargs
        )

        # Sync bridge
        epoch_bridge_events = self._b.inject_promoted_links()
        epoch_bridge_score = float(len(epoch_bridge_events or [])) / float(max(1, episodes * turns))
        self._record_function_outcome("bridge.inject_promoted_links", max(0.0, min(1.0, epoch_bridge_score)), evidence=float(max(1, len(epoch_bridge_events or []))))

        # Feedback epoch fitness into the chain
        avg_fitness = result.get("avg_fitness", 0.5) if isinstance(result, dict) else 0.5
        if self._s.has("chamber"):
            class _FakeEpisode:
                pass
            ep            = _FakeEpisode()
            ep.avg_fitness      = avg_fitness
            ep.final_engagement = avg_fitness
            ep.episode_id       = f"epoch_{self._epoch_cursor}"
            fb_trace = self._b.feedback_episode_fitness(ep)
            self._record_function_outcome("bridge.feedback_episode_fitness", 1.0 if fb_trace is not None else 0.0, evidence=1.0)

        avg = float(result.get("avg_fitness", 0.0)) if isinstance(result, dict) else 0.0
        self._recent_fitness.append(avg)
        self._session_epochs += 1

        plateau_flags = self._plateau_flags()
        plateau = any(plateau_flags.values())
        if plateau:
            self._apply_plateau_pressure(plateau_flags, verbose=False)
        if plateau and (self._tick_cursor - self._last_conflict_tick) >= self._conflict_cooldown_ticks:
            self._inject_conflict_curriculum(rounds=2, verbose=False)

        self._epoch_cursor += 1
        score = max(0.0, min(1.0, float(avg)))
        self._record_function_outcome("sim_epoch", score, evidence=float(max(1, episodes)))
        return result

    def sim_speed_run(self,
                      epochs:              int = 50,
                      episodes_per_epoch:  int = 8,
                      turns_per_episode:   int = 5,
                      descriptors_path:    Optional[str] = None,
                      chain_warmup:        int = 2_000,
                      chain_per_epoch:     int = 500,
                      verbose:             bool = True) -> Optional[Dict[str, Any]]:
        """
        Autonomous 625-gradient language speed-run through L7.

        Loads (or builds) the evolutionary pressure map, then drives
        SimulationEngine.run_speed_run() for ``epochs`` full epochs.

        Chain ticks are interleaved so the evolutionary chamber generates
        real relief events the bridge can inject into the sim each epoch.
        Without chain activity the sim runs in isolation with no promoted
        links and no momentum — chain_warmup primes the chamber before the
        run starts, and chain_per_epoch keeps pressure flowing each epoch.

        Args:
            epochs:             Total epochs for the speed-run.
            episodes_per_epoch: Episodes per epoch.
            turns_per_episode:  Turns per episode.
            descriptors_path:   Path to operation_descriptors.json.
            chain_warmup:       Chain ticks to run before speed-run starts
                                (primes relief events). Default 2000.
            chain_per_epoch:    Chain ticks to interleave each epoch.
                                Default 500.
            verbose:            Print progress.
        """
        if not self._s.has("simulation"):
            print("[STEERER] SimulationEngine not active (L7 missing).")
            return None

        sim = self._s.simulation

        # Inject the pressure map into the sim engine if not already loaded
        if getattr(sim, "pressure_map", None) is None:
            try:
                from aurora_625_pressure_map import build_from_descriptors
                import os
                desc = descriptors_path or "operation_descriptors.json"
                state_dir = getattr(self._s, "_state_dir", "aurora_state")
                sim.pressure_map = build_from_descriptors(
                    descriptors_path=desc,
                    state_dir=state_dir,
                    save=True,
                )
                # Propagate to session
                sim.session.pressure_map = sim.pressure_map
                if verbose:
                    print(f"[STEERER] Pressure map loaded — "
                          f"{len(sim.pressure_map.highway_slots)} highway slots.")
            except Exception as _e:
                print(f"[STEERER] Could not load pressure map: {_e}")
                return None

        # ── CHAIN WARM-UP ──────────────────────────────────────────────
        # Prime the chamber with real ticks so the bridge has promoted
        # links to inject when the sim starts.
        if chain_warmup > 0 and self._s.has("chamber"):
            if verbose:
                print(f"[STEERER] Chain warm-up: {chain_warmup:,} ticks...")
            self.chain_burst(chain_warmup, epoch_size=max(100, chain_warmup // 10),
                             verbose=False)
            self._b.inject_promoted_links()
            if verbose:
                gen_links = len(getattr(self._s.genealogy, "links", {}))
                print(f"[STEERER] Warm-up complete — {gen_links} links in DAG.")

        def _on_epoch(epoch_idx: int, result: Dict[str, Any]) -> None:
            """Per-epoch callback: chain ticks → bridge sync → fitness feedback."""

            # ── Per-epoch chain ticks ───────────────────────────────────
            # Keep the chamber generating new relief events every epoch so
            # the bridge always has fresh links to inject into the sim.
            if chain_per_epoch > 0 and self._s.has("chamber"):
                self.chain_burst(chain_per_epoch,
                                 epoch_size=max(50, chain_per_epoch // 5),
                                 verbose=False)

            # Sync promoted links
            bridge_events = self._b.inject_promoted_links()
            self._record_function_outcome(
                "bridge.inject_promoted_links",
                max(0.0, min(1.0, float(len(bridge_events or [])) / max(1, episodes_per_epoch))),
                evidence=float(max(1, len(bridge_events or []))),
            )

            # Feed epoch fitness into chain
            avg_fitness = float(result.get("avg_fitness", 0.5))
            if self._s.has("chamber"):
                class _FakeEpisode:
                    pass
                ep = _FakeEpisode()
                ep.avg_fitness      = avg_fitness
                ep.final_engagement = avg_fitness
                ep.episode_id       = f"speedrun_epoch_{epoch_idx}"
                self._b.feedback_episode_fitness(ep)

            self._recent_fitness.append(avg_fitness)
            self._session_epochs += 1
            self._epoch_cursor   += 1

            # Plateau check — apply pressure if stalling
            plateau_flags = self._plateau_flags()
            if any(plateau_flags.values()):
                self._apply_plateau_pressure(plateau_flags, verbose=False)
                if (self._tick_cursor - self._last_conflict_tick) >= self._conflict_cooldown_ticks:
                    self._inject_conflict_curriculum(rounds=2, verbose=False)

            self._record_function_outcome("sim_epoch", max(0.0, min(1.0, avg_fitness)),
                                          evidence=float(max(1, episodes_per_epoch)))

            if verbose:
                gen_links = len(getattr(self._s.genealogy, "links", {}))
                save_marker = " ◆ SAVE GATE" if result.get("save_gate") else ""
                print(f"  [SPEEDRUN epoch {epoch_idx+1:>3}] "
                      f"fitness={avg_fitness:.3f}  "
                      f"shards={result.get('total_understanding', '?')}  "
                      f"div={result.get('divergence', 0):.3f}  "
                      f"links={gen_links}"
                      f"{save_marker}")

        result = sim.run_speed_run(
            epochs             = epochs,
            episodes_per_epoch = episodes_per_epoch,
            turns_per_episode  = turns_per_episode,
            on_epoch           = _on_epoch,
        )

        if result and verbose:
            print(f"\n[STEERER] Speed-run complete — "
                  f"best epoch: {result['best_epoch']}  "
                  f"best fitness: {result['best_avg_fitness']:.3f}  "
                  f"save gate: {'YES' if result['save_gate_triggered'] else 'no'}")

        self._record_function_outcome("sim_speed_run",
                                      float(result.get("best_avg_fitness", 0.0)) if result else 0.0,
                                      evidence=float(epochs))
        return result

    # ------------------------------------------------------------------
    # PRESSURE REPORT
    # ------------------------------------------------------------------

    def pressure_report(self) -> None:
        """
        Print the live operator pressure gradient snapshot.

        - Live signal comes from the chamber DifferenceHistoryBuffer snapshot (C:D).
        - Canonical gradient storage lives in NC[C][OPERATOR].pressure_gradient.
        """
        self._record_function_outcome("pressure_report", 1.0, evidence=1.0)
        print()

        if OP_PRESSURE_WEIGHTS is None:
            print("  OPERATOR PRESSURE GRADIENTS (NC[C][OPERATOR])")
            print("  " + "-" * 54)
            print("  [aurora_cost_diff_score not loaded]")
            return

        # Pull latest live snapshot first so gradients reflect the live state *before* printing.
        snap = None
        try:
            snap = self._s.pressure_snapshot()
        except Exception:
            snap = None

        op_pressures = None
        if snap:
            try:
                op_pressures = per_operator_pressure(snap)
            except Exception:
                op_pressures = None

        # Bridge: write live contributions into canonical OperatorParams.pressure_gradient (EMA-smoothed)
        if op_pressures and Constraint is not None and REGISTRY is not None:
            alpha = 0.08  # smoothing factor; smaller = steadier gradients
            for c, contrib in op_pressures.items():
                try:
                    op = REGISTRY.operator(c)
                    op.pressure_gradient = (1.0 - alpha) * op.pressure_gradient + (alpha * float(contrib))
                except Exception:
                    # keep reporting alive even if one operator can't be updated
                    pass

        # Now print the canonical gradients (should reflect the update above)
        print("  OPERATOR PRESSURE GRADIENTS (NC[C][OPERATOR])")
        print("  " + "-" * 54)
        if Constraint is not None and REGISTRY is not None:
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
                op = REGISTRY.operator(c)
                print(f"  {c.name}  pressure_gradient={op.pressure_gradient:.11f}  "
                      f"scope={op.scope:6s}  conserved={op.is_conserved}")
        else:
            print("  [registry/constraint not available]")
            return

        print()
        print("  LIVE C:D SNAPSHOT (per-operator pressure contribution)")
        print("  " + "-" * 54)

        if not snap or not op_pressures:
            print("  [no snapshot available]")
            return

        # Raw C:D values (DifferenceSnapshot.values) + per-op contributions
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            d = float(snap.value(c)) if hasattr(snap, "value") else float(getattr(snap, "values", {}).get(c, 0.0))
            contrib = float(op_pressures.get(c, 0.0))
            print(f"  {c.name}:D={d:+.11f}  op_pressure_contrib={contrib:.11f}")

        total_contrib = sum(float(v) for v in op_pressures.values())
        amplifier = cross_dim_amplifier(snap)

        print()
        print(f"  Amplifier        : {amplifier:.11f}  (max={MAX_AMPLIFIER:.6f})")
        if pressure_mutation_state is not None:
            try:
                ms = pressure_mutation_state() or {}
                if isinstance(ms, dict) and ms and isinstance(next(iter(ms.values())), dict):
                    active_axes = [ax for ax, st in ms.items() if bool(st.get("active", False))]
                    event_count = sum(int(st.get("event_count", 0) or 0) for st in ms.values())
                    print(f"  Mutation state   : active_axes={active_axes or ['none']} events={event_count}")
                    for ax in ("X", "T", "N", "B", "A"):
                        st = ms.get(ax, {}) if isinstance(ms, dict) else {}
                        if not isinstance(st, dict):
                            continue
                        print(
                            f"    {ax} mut_active={bool(st.get('active', False))} "
                            f"polarity={float(st.get('polarity', 1.0) or 1.0):+0.0f} "
                            f"last={str(st.get('last_event', 'none'))} "
                            f"count={int(st.get('event_count', 0) or 0)}"
                        )
                else:
                    print(f"  Mutation state   : {ms}")
            except Exception:
                pass
        print(f"  Total contrib    : {total_contrib:.11f}")
        dominant = dominant_pressure_axis(snap)
        dom_label = dominant.name if hasattr(dominant, "name") else (dominant or "none")
        print(f"  Dominant operator: {dom_label}")
        print(f"  Snapshot tick    : {getattr(snap, 'tick', '?')}")


    def status(self) -> None:
        """Print a full universe status snapshot."""
        print()
        print("=" * 60)
        print("  AURORA UNIVERSE STATUS")
        print("=" * 60)

        # Layer status
        print("\n  LAYERS")
        for label, state in self._s.layer_status().items():
            print(f"    {label:<40} {state}")

        # Chamber state
        print("\n  EVOLUTIONARY CHAIN")
        chamber = self._s.chamber
        if chamber:
            # tick_count is a plain int attribute on EvolutionaryChamber
            tc    = getattr(chamber, "tick_count", self._tick_cursor)
            # chamber.alive is a @property on EvolutionaryChamber
            alive = chamber.alive
            # chamber._budget is EnergyBudget; .available is a @property
            budget_obj = getattr(chamber, "_budget", None)
            energy = budget_obj.available if budget_obj is not None else "?"
            relev  = getattr(chamber, "total_relief_events",    "?")
            viols  = getattr(chamber, "total_violation_events", "?")
            print(f"    Tick count         : {tc:,}")
            print(f"    Chamber alive      : {alive}")
            print(f"    Energy budget      : {energy}")
            print(f"    Relief events      : {relev}")
            print(f"    Violation events   : {viols}")
        else:
            print("    (not active)")

        # Genealogy
        print("\n  GENEALOGY")
        genealogy = self._s.genealogy
        if genealogy:
            # links is Dict[str, ConstraintLink] — public attribute
            links     = getattr(genealogy, "links", {})
            # abilities is Dict[str, AbilityProfile] — public attribute
            abilities = getattr(genealogy, "abilities", {})
            # relief_event_count is a public int counter on ConstraintGenealogyLogger
            relcount  = getattr(genealogy, "relief_event_count", "?")
            promoted  = getattr(genealogy, "links_promoted",     "?")
            tol_events = int(getattr(genealogy, "_tolerance_events_applied", 0) or 0)
            tol_ema = float(getattr(genealogy, "_tolerance_factor_ema", 1.0) or 1.0)
            coupling_roots = int(len(getattr(genealogy, "_coupling_roots", {}) or {}))
            coupling_events = int(getattr(genealogy, "_coupling_events", 0) or 0)
            coupling_ema = float(getattr(genealogy, "_persistent_pressure_root_ema", 0.0) or 0.0)
            print(f"    Promoted links     : {len(links)}")
            print(f"    Registered abil.   : {len(abilities)}")
            print(f"    Relief events      : {relcount}")
            print(f"    Links promoted     : {promoted}")
            print(f"    Tolerance events   : {tol_events}")
            print(f"    Tolerance factor   : ema={tol_ema:.3f}")
            print(f"    Coupling roots     : {coupling_roots}  events={coupling_events}")
            print(f"    Persistent root EMA: {coupling_ema:.11f}")
        else:
            print("    (not active)")

        # Bridge
        print("\n  CHAIN↔SIM BRIDGE")
        bs = self._b.stats()
        print(f"    Link injections    : {bs['total_link_injections']}")
        print(f"    Fitness feedbacks  : {bs['total_fitness_feedbacks']}")
        print(f"    Injected link count: {bs['injected_link_count']}")

        # Simulation (L7)
        print("\n  SIMULATION  (L7)")
        sim = self._s.simulation
        if sim:
            # SimulationEngine.get_stats() returns:
            # {'total_episodes', 'total_entity_experiences', 'entities', 'session'}
            # session sub-dict from SimulationSession.get_stats():
            # {'epochs_completed', 'total_episodes', 'total_turns',
            #  'understanding_shards', 'governor', 'divergence', 'what_aurora_learned'}
            stats = sim.get_stats()
            sess  = stats.get("session", {})
            print(f"    Episodes run       : {stats.get('total_episodes', 0)}")
            print(f"    Entity count       : {stats.get('entities', 0)}")
            print(f"    Epochs completed   : {sess.get('epochs_completed', self._epoch_cursor)}")
            print(f"    Total turns        : {sess.get('total_turns', '?')}")
            print(f"    Understanding shards: {sess.get('understanding_shards', '?')}")
            learned = sess.get("what_aurora_learned", [])
            if learned:
                print(f"    Learned ({len(learned)} items):")
                for item in learned[:3]:
                    print(f"      • {item}")
                if len(learned) > 3:
                    print(f"      ... (+{len(learned)-3} more)")
        else:
            print("    (not active)")

        # Lineage coverage
        print("\n  LINEAGE COVERAGE")
        lcov = self.ancestry_report()
        print(f"    Mapped operations : {int(lcov.get('mapped_functions', 0))}")
        print(f"    Perf tracked      : {int(lcov.get('performance_tracked', 0))}  (rate={float(lcov.get('performance_coverage_rate', 0.0)):.3f})")
        print(f"    Offspring links   : {int(lcov.get('offspring_relations', 0))}")
        print(f"    Unmapped perf ops : {int(lcov.get('unmapped_perf_count', 0))}")
        print(f"    Mapped untracked  : {int(lcov.get('mapped_untracked_count', 0))}")

        # Auxiliary cognition
        if self._last_attention_frame:
            print("\n  ATTENTION FOCUS")
            f = self._last_attention_frame
            axes_str = ", ".join([str(getattr(c, "name", c)) for c in f.focus_axes])
            print(f"    State              : {f.state.value}")
            print(f"    Resonance          : {f.resonance:.4f}")
            print(f"    Surface Salience   : {f.surface_salience:.4f}")
            print(f"    Subsurface Tension : {f.subsurface_tension:.4f}")
            print(f"    Focus Axes         : [{axes_str}]")
            if f.anchors:
                print(f"    Active Anchors     : {', '.join(f.anchors)}")

        # Live pressure snapshot
        self.pressure_report()

        print("=" * 60)
        print()
        self._record_function_outcome("status", 1.0, evidence=1.0)

    def links(self, top_n: int = 10) -> None:
        """Print the top promoted evolutionary links by total mean relief."""
        genealogy = self._s.genealogy
        if not genealogy:
            print("[STEERER] Genealogy not active.")
            return

        links: Dict[str, ConstraintLink] = getattr(genealogy, "links", {})
        if not links:
            print("[STEERER] No promoted links yet — run chain_burst() first.")
            return

        sorted_links = sorted(
            links.values(),
            # ConstraintLink.mean_relief is a @property returning Dict[str, float]
            key=lambda lnk: sum(getattr(lnk, "mean_relief", {}).values()),
            reverse=True,
        )[:top_n]

        print(f"\n  TOP {len(sorted_links)} PROMOTED LINKS")
        print("  " + "-" * 60)
        for lnk in sorted_links:
            # ConstraintLink attributes: id, parents, depth, count,
            # dominant_relief_axis, mean_relief (property)
            relief_total = sum(getattr(lnk, "mean_relief", {}).values())
            print(
                f"  {getattr(lnk,'id','?')[:24]:<24}  "
                f"axis={getattr(lnk,'dominant_relief_axis','?')}  "
                f"depth={getattr(lnk,'depth','?')}  "
                f"count={getattr(lnk,'count','?')}  "
                f"relief={relief_total:.4f}"
            )
        print()
        self._record_function_outcome("links", 1.0, evidence=float(max(1, len(sorted_links))))

    def what_learned(self) -> None:
        """Print what the conscious learner has understood so far."""
        sim = self._s.simulation
        if not sim:
            print("[STEERER] SimulationEngine not active.")
            return

        # session is SimulationSession; learner is ConsciousLearner
        session = getattr(sim, "session", None)
        learner = getattr(session, "learner", None) if session else None
        if not learner:
            print("[STEERER] Conscious learner not found.")
            return

        # ConsciousLearner.what_have_i_learned() → List[str]
        learnings: List[str] = learner.what_have_i_learned()
        if not learnings:
            print("[STEERER] Nothing confidently understood yet — run sim_epoch() first.")
            return

        print(f"\n  AURORA HAS LEARNED ({len(learnings)} items):")
        for i, item in enumerate(learnings, 1):
            print(f"    {i:>2}. {item}")
        print()

        self._record_function_outcome("what_learned", 1.0, evidence=float(max(1, len(learnings))))
    def available_actions(self) -> List[str]:
        """List named actions currently executable by energy budget (binary gate)."""
        names = sorted(self._action_map.keys())
        executable_names: List[str] = []

        chamber = self._s.chamber if self._s.has("chamber") else None
        budget_available = None
        agency_cost_coeff = None
        agency_max_magnitude = None
        energy_floor = None
        if chamber is not None:
            try:
                budget_available = float(getattr(chamber._budget, "available", 0.0))
                agency_cost_coeff = float(getattr(chamber.K, "agency_cost_coefficient", 0.0))
                agency_max_magnitude = float(getattr(chamber.K, "agency_max_magnitude", 0.0))
                energy_floor = float(getattr(chamber.K, "energy_budget_floor", 0.0))
            except Exception:
                budget_available = None

        print("\n  AVAILABLE NAMED ACTIONS:")
        for name in names:
            a = self._action_map[name]
            anc = (a.meta or {}).get("constraint_ancestry", sorted(a.constraints_used))
            status = "unknown"
            if budget_available is not None and agency_cost_coeff is not None and agency_max_magnitude is not None and energy_floor is not None:
                requested_axes = len(set(a.constraints_used or frozenset()))
                magnitude = requested_axes * 0.1
                base_cost = agency_cost_coeff * (magnitude ** 2)
                represented = "existence"
                if requested_axes > 0:
                    pr = {"agency": 5, "boundary": 4, "energy": 3, "temporal": 2, "existence": 1}
                    represented = sorted(
                        set(a.constraints_used or frozenset()),
                        key=lambda lbl: (-pr.get(str(lbl).lower(), 0), str(lbl))
                    )[0]
                carry_pool = getattr(chamber, "_carryover_credit_current", {}) if chamber is not None else {}
                carry_credit = float(carry_pool.get(str(represented).lower(), 0.0)) if isinstance(carry_pool, dict) else 0.0
                required_cost = max(0.0, base_cost - carry_credit)
                available_energy = max(0.0, budget_available - energy_floor)
                executable = (requested_axes > 0 and magnitude <= agency_max_magnitude and required_cost <= available_energy)
                status = "executable" if executable else "ineligible"
                if executable:
                    executable_names.append(name)
                print(
                    f"    {name:<24}  status={status:<10}  cost={required_cost:.6f}  credit={carry_credit:.6f}  "
                    f"constraints={sorted(a.constraints_used)}  ancestry={anc}"
                )
            else:
                executable_names.append(name)
                print(f"    {name:<24}  status={status:<10}  constraints={sorted(a.constraints_used)}  ancestry={anc}")
        print()
        self._record_function_outcome("available_actions", 1.0, evidence=float(max(1, len(names))))
        return executable_names

    def register_action(self,
                        name:        str,
                        constraints: FrozenSet[str],
                        meta:        Optional[Dict[str, Any]] = None) -> None:
        """
        Register a custom named action you can inject by name later.
        Undefined labels are lineage-synthesized instead of rejected.
        """
        inferred_constraints, bad, synthesized = self._resolve_constraints_explicit(
            requested=constraints,
            hint_text=name,
            source_fn="steerer.register_action",
        )

        meta_payload = {
            "custom": True,
            "registered_by": "steerer",
            "lineage_synthesized": bool(synthesized),
        }
        if bad:
            meta_payload["lineage_bad_labels"] = list(bad)
        if isinstance(meta, dict):
            meta_payload.update(meta)
        meta_payload = self._auto_seed_directive(name=name, constraints=inferred_constraints, meta=meta_payload)

        trace = ActionTrace(
            name             = name,
            constraints_used = inferred_constraints,
            meta             = meta_payload,
        )
        trace = self._with_trace_ancestry(trace, source_fn="steerer.register_action")
        self._action_map[name] = trace
        self._register_function_ancestry(f"action:{name}", set(inferred_constraints))
        print(f"[STEERER] Action '{name}' registered. "
              f"Constraints: {sorted(inferred_constraints)}")


# =============================================================================
# AURORA RUNTIME — Master Orchestrator
# =============================================================================
class AuroraRuntime:
    """
    Master orchestrator. Boot once, steer forever.

    Usage
    -----
        runtime = AuroraRuntime()
        runtime.boot()
        runtime.steerer.chain_burst(5000)
        runtime.steerer.sim_epoch(episodes=4)
        runtime.steerer.status()
        runtime.save()
    """

    def __init__(self,
                 state_dir:  str = "aurora_state",
                 output_dir: str = "aurora_runtime_output",
                 run_id:     Optional[str] = None):
        self.state_dir  = state_dir
        self.output_dir = output_dir
        self.run_id     = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.systems:  Optional[StackSystems]    = None
        self.bridge:   Optional[ChainSimBridge]  = None
        self.steerer:  Optional[UniverseSteerer] = None
        self._boot_time: Optional[float] = None
        self._running = False
        self.require_save_gate: bool = True
        self._start_stance: Dict[str, Any] = {}
        self.code_chamber: Optional[Any] = None
        self._code_enabled: bool = _env_flag("AURORA_CODE_EVOLUTION", default=True)
        self._code_require_sim_gate: bool = _env_flag("AURORA_CODE_REQUIRE_SIM_GATE", default=True)
        self._code_pending: Dict[str, Dict[str, Any]] = {}
        self._code_history: Deque[Dict[str, Any]] = deque(maxlen=64)
        self._code_latest: Optional[Dict[str, Any]] = None
        self._code_autoevolver: Optional[Any] = None
        self._code_timing_feedback: Dict[str, Any] = {
            "samples": 0,
            "agency_ema": 0.0,
            "temporal_ema": 0.0,
            "last": {},
        }
        self._code_operator_feedback_cache: Dict[str, Any] = {
            "path": "",
            "mtime_ns": 0,
            "size": 0,
            "summary": {},
        }
        self._developmental_sync_enabled: bool = _env_flag("AURORA_DEVELOPMENTAL_SYNC", default=True)
        self._developmental_sync_interval_s: float = float(max(900.0, _env_float("AURORA_DEVELOPMENTAL_SYNC_INTERVAL_S", 21600.0)))
        self._developmental_live_sync_enabled: bool = _env_flag("AURORA_DEVELOPMENTAL_LIVE_SYNC", default=True)
        self._developmental_live_poll_s: float = float(max(120.0, _env_float("AURORA_DEVELOPMENTAL_LIVE_POLL_S", 1800.0)))
        self._developmental_sync_state: Dict[str, Any] = {}
        self._developmental_sync_lock = threading.Lock()
        self._developmental_scheduler_stop: Optional[threading.Event] = None
        self._developmental_scheduler_thread: Optional[threading.Thread] = None

    def boot(self, verbose: bool = True) -> "AuroraRuntime":
        """Boot the full stack and initialise steerer."""
        self._boot_time = time.time()
        self._load_developmental_sync_state()
        self.systems  = boot_stack(
            state_dir  = self.state_dir,
            output_dir = self.output_dir,
            run_id     = self.run_id,
            verbose    = verbose,
        )
        self.bridge  = ChainSimBridge(self.systems)
        self.steerer = UniverseSteerer(self.systems, self.bridge)
        if not self.steerer.validate_ancestry():
            rep = self.steerer.ancestry_report()
            raise RuntimeError(
                f"Constraint ancestry validation failed: missing={rep.get('missing_base_constraints')}"
            )
        self._start_stance = self.steerer.stance_snapshot()
        try:
            self.steerer._register_function_ancestry("runtime.boot", {"existence", "temporal", "boundary"})
            self.steerer._record_function_outcome("runtime.boot", 1.0, evidence=1.0)
            bm = getattr(self.systems, "_boot_metrics", {}) or {}
            ro = dict((bm.get("restored_operator_gradients", {}) or {}))
            rg = dict((bm.get("restored_genealogy", {}) or {}))
            op_mag = sum(abs(float(v or 0.0)) for v in ro.values())
            op_score = max(0.0, min(1.0, op_mag * 1000.0))
            self.steerer._register_function_ancestry("runtime.restore_operator_gradients", {"existence", "energy", "temporal"})
            self.steerer._record_function_outcome("runtime.restore_operator_gradients", op_score, evidence=float(max(1, len(ro))))
            restored_items = int(rg.get("abilities", 0) or 0) + int(rg.get("links", 0) or 0)
            rg_score = max(0.0, min(1.0, float(restored_items) / 200.0))
            self.steerer._register_function_ancestry("runtime.restore_genealogy_state", {"existence", "boundary", "temporal"})
            self.steerer._record_function_outcome("runtime.restore_genealogy_state", rg_score, evidence=float(max(1, restored_items)))
            ck = bool(bm.get("checkpoint_restored", False))
            self.steerer._register_function_ancestry("runtime.restore_checkpoint", {"existence", "temporal", "boundary"})
            self.steerer._record_function_outcome("runtime.restore_checkpoint", 1.0 if ck else 0.25, evidence=1.0)
        except Exception:
            pass
        if self._code_enabled and CodeEvolutionChamber is not None:
            try:
                self.code_chamber = CodeEvolutionChamber(
                    repo_root=_HERE,
                    output_dir=os.path.join(self.output_dir, "code_evolution"),
                )
                if CodeAutoEvolver is not None:
                    self._code_autoevolver = CodeAutoEvolver(repo_root=_HERE)
                if self.steerer is not None:
                    self.steerer._code_pressure_guidance_fn = self._code_pressure_guidance
                if verbose:
                    print("[RUNTIME] Code evolution chamber active.")
            except Exception as e:
                self.code_chamber = None
                if verbose:
                    print(f"[RUNTIME] Code evolution chamber disabled: {e}")
        try:
            self._reload_evolved_surfaces(verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"[RUNTIME] Evolved surfaces unavailable: {e}")
        try:
            self.maybe_sync_developmental_surfaces(
                force=False,
                reason="boot",
                chain_ticks=40,
                episodes=0,
                turns=1,
                dry_run=False,
                verbose=verbose,
            )
        except Exception as e:
            if verbose:
                print(f"[RUNTIME] Developmental sync skipped: {e}")
        self._running = True
        try:
            self._start_developmental_sync_scheduler(verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"[RUNTIME] Developmental sync scheduler skipped: {e}")
        return self

    def _code_pressure_guidance(self) -> Dict[str, Any]:
        base: Dict[str, Any] = {}
        if self.code_chamber is not None and hasattr(self.code_chamber, "guidance_payload"):
            try:
                base = dict(self.code_chamber.guidance_payload() or {})
            except Exception:
                base = {}
        timing = dict(self._code_timing_feedback or {})
        agency = float(timing.get("agency_ema", 0.0) or 0.0)
        temporal = float(timing.get("temporal_ema", 0.0) or 0.0)
        if agency <= 0.0 and temporal <= 0.0:
            return base
        primary_axis = "A" if agency >= temporal else "T"
        secondary_axis = "T" if primary_axis == "A" else "A"
        timing_score = max(agency, temporal)
        compare_value = timing_score if primary_axis == "A" else -timing_score
        if not base:
            return {
                "score": float(timing_score),
                "compare_value": float(compare_value),
                "primary_axis": primary_axis,
                "secondary_axis": secondary_axis,
                "timing_feedback": timing,
            }
        blend = 0.22
        base["score"] = ((1.0 - blend) * float(base.get("score", 0.0) or 0.0)) + (blend * float(timing_score))
        if primary_axis == "A":
            base["compare_value"] = float(base.get("compare_value", 0.0) or 0.0) + (blend * float(agency))
            base["secondary_axis"] = str(base.get("secondary_axis", secondary_axis) or secondary_axis)
            if float(agency) > max(float(temporal), float(base.get("score", 0.0) or 0.0)):
                base["primary_axis"] = "A"
        else:
            base["compare_value"] = float(base.get("compare_value", 0.0) or 0.0) - (blend * float(temporal))
            if float(temporal) > max(float(agency), float(base.get("score", 0.0) or 0.0)):
                base["primary_axis"] = "T"
        base["timing_feedback"] = timing
        return base

    def _code_timing_feedback_from_apply(self, apply_result: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(apply_result or {})
        duration = max(0.0, float(rec.get("duration_s", 0.0) or 0.0))
        file_timings = [dict(x) for x in (rec.get("file_timings", []) or []) if isinstance(x, dict)]
        strategic = [
            row for row in file_timings
            if str(row.get("timing_role", "") or "") in {"strategic_source", "native_source"}
            or "agency" in list(row.get("timing_axes", []) or [])
            or "temporal" in list(row.get("timing_axes", []) or [])
        ]
        descriptor = [row for row in file_timings if str(row.get("timing_role", "") or "") in {"descriptor_state", "generated_surface"}]
        strategic_count = int(len(strategic))
        descriptor_count = int(len(descriptor))
        strategic_time = float(sum(max(0.0, float(row.get("write_duration_s", 0.0) or 0.0)) for row in strategic))
        descriptor_time = float(sum(max(0.0, float(row.get("write_duration_s", 0.0) or 0.0)) for row in descriptor))
        strategic_bytes = float(sum(max(0, int(row.get("bytes_after", 0) or 0)) for row in strategic))
        descriptor_bytes = float(sum(max(0, int(row.get("bytes_after", 0) or 0)) for row in descriptor))
        other_bytes = float(sum(
            max(0, int(row.get("bytes_after", 0) or 0))
            for row in file_timings
            if row not in strategic and row not in descriptor
        ))
        expected_strategic = (0.012 * strategic_count) + (strategic_bytes / 2_800_000.0)
        expected_descriptor = (0.040 * descriptor_count) + (descriptor_bytes / 1_050_000.0)
        expected_other = (0.008 * max(0, int(len(file_timings) - strategic_count - descriptor_count))) + (other_bytes / 2_000_000.0)
        expected = max(0.020, expected_strategic + expected_descriptor + expected_other)
        strategic_observed = max(0.001, strategic_time if strategic_time > 0.0 else duration)
        strategic_ratio = expected_strategic / strategic_observed if strategic_count > 0 else 0.0
        agency_credit = max(0.0, min(1.0, (strategic_ratio - 0.45) / 0.95)) if strategic_count > 0 else 0.0
        descriptor_overhead = max(0.0, descriptor_time - expected_descriptor)
        total_overhead = max(0.0, duration - expected)
        temporal_penalty = 0.0
        if expected > 0.0:
            temporal_penalty = max(0.0, min(1.0, ((descriptor_overhead * 1.8) + total_overhead) / max(0.05, expected * 2.4)))
        if strategic_count > 0 and duration > 0.0:
            strategic_share = min(1.0, strategic_time / duration)
            agency_credit = max(agency_credit, strategic_share * 0.75)
            temporal_penalty = max(0.0, temporal_penalty - (0.18 * strategic_share))
        applied_time_difference = float(total_overhead)
        return {
            "apply_duration_s": float(round(duration, 6)),
            "expected_duration_s": float(round(expected, 6)),
            "applied_time_difference_s": float(round(applied_time_difference, 6)),
            "agency_time_credit": float(round(agency_credit, 6)),
            "temporal_overhead_penalty": float(round(temporal_penalty, 6)),
            "strategic_file_count": strategic_count,
            "strategic_write_time_s": float(round(strategic_time, 6)),
            "descriptor_file_count": descriptor_count,
            "descriptor_write_time_s": float(round(descriptor_time, 6)),
            "descriptor_overhead_s": float(round(descriptor_overhead, 6)),
        }

    def _integrate_code_timing_feedback(self, timing_feedback: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(timing_feedback or {})
        alpha = 0.18
        prev_agency = float(self._code_timing_feedback.get("agency_ema", 0.0) or 0.0)
        prev_temporal = float(self._code_timing_feedback.get("temporal_ema", 0.0) or 0.0)
        agency = float(rec.get("agency_time_credit", 0.0) or 0.0)
        temporal = float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)
        self._code_timing_feedback["agency_ema"] = ((1.0 - alpha) * prev_agency) + (alpha * agency)
        self._code_timing_feedback["temporal_ema"] = ((1.0 - alpha) * prev_temporal) + (alpha * temporal)
        self._code_timing_feedback["samples"] = int(self._code_timing_feedback.get("samples", 0) or 0) + 1
        self._code_timing_feedback["last"] = dict(rec)
        return dict(self._code_timing_feedback)

    def _code_evolution_feedback_path(self) -> str:
        return os.path.join(self.output_dir, "abilities.json")

    def _parse_code_evolution_feedback_record(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(rec, dict):
            return None
        tags = [str(x).strip() for x in (rec.get("effect_tags", []) or []) if str(x).strip()]
        notes = str(rec.get("notes", "") or "")
        if ("code_evolution" not in tags) and ("Code evolution outcome" not in notes):
            return None
        operator_key = ""
        status = ""
        agency_credit = 0.0
        temporal_penalty = 0.0
        mutation_score = 0.0
        for tag in tags:
            if tag.startswith("mutation_operator:"):
                operator_key = str(tag.split(":", 1)[1]).strip().lower()
            elif tag.startswith("mutation_status:"):
                status = str(tag.split(":", 1)[1]).strip().lower()
            elif tag.startswith("agency_time_credit:"):
                try:
                    agency_credit = float(tag.split(":", 1)[1])
                except Exception:
                    agency_credit = 0.0
            elif tag.startswith("temporal_overhead_penalty:"):
                try:
                    temporal_penalty = float(tag.split(":", 1)[1])
                except Exception:
                    temporal_penalty = 0.0
            elif tag.startswith("mutation_score:"):
                try:
                    mutation_score = float(tag.split(":", 1)[1])
                except Exception:
                    mutation_score = 0.0
        if not operator_key:
            m = re.search(r"operator_key=([a-zA-Z0-9_]+)", notes)
            if m:
                operator_key = str(m.group(1)).strip().lower()
        if not status:
            m = re.search(r"accepted=(True|False)", notes)
            if m:
                status = "accepted" if str(m.group(1)) == "True" else "rejected"
        if not operator_key:
            return None
        return {
            "operator_key": operator_key,
            "accepted": bool(status == "accepted"),
            "rejected": bool(status == "rejected"),
            "agency_time_credit": float(max(0.0, agency_credit)),
            "temporal_overhead_penalty": float(max(0.0, temporal_penalty)),
            "mutation_score": float(max(0.0, mutation_score)),
        }

    def _code_operator_feedback_summary(self) -> Dict[str, Any]:
        path = self._code_evolution_feedback_path()
        try:
            st = os.stat(path)
            mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            size = int(st.st_size)
        except Exception:
            return {"operators": {}, "record_count": 0}
        cache = dict(self._code_operator_feedback_cache or {})
        if (
            str(cache.get("path", "")) == path
            and int(cache.get("mtime_ns", 0) or 0) == mtime_ns
            and int(cache.get("size", 0) or 0) == size
            and isinstance(cache.get("summary"), dict)
        ):
            return dict(cache.get("summary", {}) or {})
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh) or {}
        except Exception:
            raw = {}
        if isinstance(raw, dict):
            items = list(raw.values())
        elif isinstance(raw, list):
            items = list(raw)
        else:
            items = []
        records: List[Dict[str, Any]] = []
        for rec in items:
            parsed = self._parse_code_evolution_feedback_record(rec)
            if parsed is not None:
                records.append(parsed)
        by_operator: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            key = str(rec.get("operator_key", "") or "").strip().lower()
            if not key:
                continue
            bucket = by_operator.setdefault(key, {
                "trials": 0,
                "accepted": 0,
                "rejected": 0,
                "agency_time_credit_sum": 0.0,
                "temporal_overhead_penalty_sum": 0.0,
                "mutation_score_sum": 0.0,
            })
            bucket["trials"] += 1
            bucket["accepted"] += 1 if bool(rec.get("accepted", False)) else 0
            bucket["rejected"] += 1 if bool(rec.get("rejected", False)) else 0
            bucket["agency_time_credit_sum"] += float(rec.get("agency_time_credit", 0.0) or 0.0)
            bucket["temporal_overhead_penalty_sum"] += float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)
            bucket["mutation_score_sum"] += float(rec.get("mutation_score", 0.0) or 0.0)
        for bucket in by_operator.values():
            trials = max(1, int(bucket.get("trials", 0) or 0))
            accepted = int(bucket.get("accepted", 0) or 0)
            rejected = int(bucket.get("rejected", 0) or 0)
            bucket["acceptance_rate"] = float(accepted / trials)
            bucket["rejection_rate"] = float(rejected / trials)
            bucket["agency_time_credit"] = float(bucket["agency_time_credit_sum"] / trials)
            bucket["temporal_overhead_penalty"] = float(bucket["temporal_overhead_penalty_sum"] / trials)
            bucket["mutation_score"] = float(bucket["mutation_score_sum"] / trials)
        summary = {
            "operators": by_operator,
            "record_count": int(len(records)),
        }
        self._code_operator_feedback_cache = {
            "path": path,
            "mtime_ns": mtime_ns,
            "size": size,
            "summary": dict(summary),
        }
        return summary

    def recommended_code_operator_order(self,
                                        include: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        include_keys = [str(k).strip().lower() for k in (include or []) if str(k).strip()]
        if not include_keys:
            include_keys = [
                "latent_promotion",
                "architectural_reflection",
                "native_surface_projection",
            ]
        specs = {str(row.get("key", "")).strip().lower(): dict(row) for row in self.code_operator_specs() if isinstance(row, dict)}
        guidance = dict(self._code_pressure_guidance() or {})
        gradients = dict(guidance.get("operator_gradients", {}) or {})
        primary_axis = str(guidance.get("primary_axis", "") or "").strip().upper()
        secondary_axis = str(guidance.get("secondary_axis", "") or "").strip().upper()
        guidance_score = float(guidance.get("score", 0.0) or 0.0)
        feedback = dict(self._code_operator_feedback_summary().get("operators", {}) or {})
        axis_map = {
            "existence": "X",
            "temporal": "T",
            "energy": "N",
            "boundary": "B",
            "agency": "A",
        }
        ranked: List[Dict[str, Any]] = []
        for key in include_keys:
            spec = dict(specs.get(key, {}) or {})
            constraints = [str(c).strip().lower() for c in (spec.get("constraints", []) or []) if str(c).strip()]
            axes = [axis_map[c] for c in constraints if c in axis_map]
            if not axes:
                axes = ["X", "T"]
            axis_gradient = float(sum(float(gradients.get(ax, 0.0) or 0.0) for ax in axes) / max(1, len(axes)))
            axis_fit = max(0.0, min(1.0, 0.5 + (0.5 * axis_gradient)))
            primary_fit = 1.0 if primary_axis in axes else 0.0
            secondary_fit = 1.0 if secondary_axis in axes else 0.0
            rec = dict(feedback.get(key, {}) or {})
            trials = int(rec.get("trials", 0) or 0)
            acceptance = float(rec.get("acceptance_rate", 0.0) or 0.0)
            rejection = float(rec.get("rejection_rate", 0.0) or 0.0)
            agency_credit = float(rec.get("agency_time_credit", 0.0) or 0.0)
            temporal_penalty = float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)
            mutation_score = float(rec.get("mutation_score", 0.0) or 0.0)
            exploration_bonus = 0.12 / float(1 + trials)
            score = (
                (0.34 * axis_fit)
                + (0.18 * guidance_score * primary_fit)
                + (0.07 * guidance_score * secondary_fit)
                + (0.18 * acceptance)
                - (0.11 * rejection)
                + (0.12 * agency_credit)
                - (0.10 * temporal_penalty)
                + (0.08 * mutation_score)
                + exploration_bonus
            )
            ranked.append({
                "key": key,
                "score": float(round(max(0.0, min(1.0, score)), 6)),
                "constraints": constraints,
                "axes": axes,
                "axis_fit": float(round(axis_fit, 6)),
                "primary_fit": bool(primary_fit),
                "secondary_fit": bool(secondary_fit),
                "feedback": {
                    "trials": trials,
                    "acceptance_rate": float(round(acceptance, 6)),
                    "rejection_rate": float(round(rejection, 6)),
                    "agency_time_credit": float(round(agency_credit, 6)),
                    "temporal_overhead_penalty": float(round(temporal_penalty, 6)),
                    "mutation_score": float(round(mutation_score, 6)),
                },
            })
        ranked.sort(key=lambda row: (-float(row.get("score", 0.0) or 0.0), str(row.get("key", ""))))
        return ranked

    def _ensure_evolved_surface_module(self) -> str:
        path = os.path.join(_HERE, "aurora_internal", "aurora_evolved_surfaces.py")
        if os.path.exists(path):
            return path
        scaffold = """#!/usr/bin/env python3
\"\"\"
AURORA EVOLVED SURFACES
=======================
Bootstrap scaffold. Regenerate through the code autoevolver.
\"\"\"

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AuroraEvolvedSurfaceEngine:
    def __init__(self, systems: Any = None, state_dir: Optional[str] = None):
        self.systems = systems
        self.state_dir = state_dir

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return []

    def describe_capability(self, name: str) -> Dict[str, Any]:
        return {}

    def capability_report(self) -> Dict[str, Any]:
        return {"available": False, "surface_count": 0, "latent_count": 0, "reflection_count": 0}


__all__ = ["AuroraEvolvedSurfaceEngine"]
"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(scaffold)
        return path

    def _reload_evolved_surfaces(self, verbose: bool = False) -> Dict[str, Any]:
        if self.systems is None:
            return {}
        path = self._ensure_evolved_surface_module()
        try:
            import importlib

            importlib.invalidate_caches()
            mod = importlib.import_module("aurora_internal.aurora_evolved_surfaces")
            mod = importlib.reload(mod)
            engine_cls = getattr(mod, "AuroraEvolvedSurfaceEngine", None)
            if engine_cls is None:
                self.systems.evolved_surfaces = None
                return {}
            engine = engine_cls(systems=self.systems, state_dir=self.state_dir)
            self.systems.evolved_surfaces = engine
            if self.steerer is not None and hasattr(engine, "list_capabilities"):
                for row in list(engine.list_capabilities() or []):
                    if not isinstance(row, dict):
                        continue
                    name = str(row.get("name", "") or "").strip()
                    if not name:
                        continue
                    constraints = set(str(c).strip().lower() for c in (row.get("constraints", []) or []) if str(c).strip())
                    self.steerer._register_function_ancestry(
                        f"evolved.{name}",
                        constraints or {"existence", "temporal"},
                    )
            report = {}
            if hasattr(engine, "capability_report"):
                report = dict(engine.capability_report() or {})
            if verbose and report:
                print(
                    "[RUNTIME] Evolved surfaces active: "
                    f"{int(report.get('surface_count', 0) or 0)} total, "
                    f"{int(report.get('latent_count', 0) or 0)} latent, "
                    f"{int(report.get('reflection_count', 0) or 0)} reflections"
                )
            return report
        except Exception:
            self.systems.evolved_surfaces = None
            if verbose:
                print(f"[RUNTIME] Evolved surfaces load failed from {path}")
            return {}

    def _developmental_surface_targets(self, include_native: bool = False) -> List[str]:
        targets = [self._ensure_evolved_surface_module()]
        path = os.path.join(_HERE, "aurora_state", "operation_descriptors.json")
        if not os.path.exists(path):
            return targets
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
        except Exception:
            return targets
        if not include_native:
            return targets
        for row in (data.get("latent_operations", []) or []):
            if not isinstance(row, dict) or not bool(row.get("implemented")):
                continue
            rel = str(row.get("file", "") or "").strip()
            if not rel:
                continue
            targets.append(os.path.join(_HERE, rel))
        for row in (data.get("operations", []) or []):
            if not isinstance(row, dict):
                continue
            if not isinstance(row.get("current_evolved_representation"), dict):
                continue
            rel = str(row.get("file", "") or "").strip()
            if not rel:
                continue
            targets.append(os.path.join(_HERE, rel))
        out: List[str] = []
        seen: set[str] = set()
        for raw in targets:
            absp = os.path.abspath(raw)
            if absp in seen or not os.path.exists(absp):
                continue
            seen.add(absp)
            out.append(absp)
        return out

    def _developmental_sync_state_path(self) -> str:
        return os.path.join(self.state_dir, "developmental_sync_state.json")

    def _load_developmental_sync_state(self) -> Dict[str, Any]:
        path = self._developmental_sync_state_path()
        if not os.path.exists(path):
            self._developmental_sync_state = {
                "boot_count": 0,
                "save_count": 0,
                "sync_count": 0,
                "last_reason": "",
                "last_attempt_at": 0.0,
                "last_success_at": 0.0,
                "last_status": {},
            }
            return dict(self._developmental_sync_state)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh) or {}
            if not isinstance(raw, dict):
                raw = {}
        except Exception:
            raw = {}
        raw.setdefault("boot_count", 0)
        raw.setdefault("save_count", 0)
        raw.setdefault("sync_count", 0)
        raw.setdefault("last_reason", "")
        raw.setdefault("last_attempt_at", 0.0)
        raw.setdefault("last_success_at", 0.0)
        raw.setdefault("last_status", {})
        self._developmental_sync_state = dict(raw)
        return dict(self._developmental_sync_state)

    def _persist_developmental_sync_state(self) -> bool:
        path = self._developmental_sync_state_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._developmental_sync_state, fh, ensure_ascii=True, indent=2, sort_keys=True)
            return True
        except Exception:
            return False

    def _developmental_sync_inputs(self) -> Dict[str, str]:
        return {
            "descriptor": os.path.join(_HERE, "aurora_state", "operation_descriptors.json"),
            "surface_module": self._ensure_evolved_surface_module(),
            "abilities": os.path.join(self.output_dir, "abilities.json"),
            "links": os.path.join(self.output_dir, "links.json"),
            "couplings": os.path.join(self.output_dir, "couplings.json"),
            "pair_stats": os.path.join(self.output_dir, "pair_stats.json"),
        }

    def _developmental_sync_input_stamps(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for name, path in sorted(self._developmental_sync_inputs().items()):
            try:
                st = os.stat(path)
                out[name] = {
                    "path": path,
                    "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))),
                    "size": int(st.st_size),
                }
            except Exception:
                out[name] = {"path": path, "mtime_ns": 0, "size": 0}
        return out

    def _developmental_sync_drift(self) -> Dict[str, Any]:
        state = dict(self._developmental_sync_state or self._load_developmental_sync_state())
        current = self._developmental_sync_input_stamps()
        previous = dict(state.get("last_input_stamps", {}) or {})
        last_fingerprint = str(state.get("last_fingerprint", "") or "")
        digest = hashlib.sha1()
        for name in sorted(current.keys()):
            stamp = dict(current.get(name, {}) or {})
            digest.update(name.encode("utf-8"))
            digest.update(str(stamp.get("mtime_ns", 0)).encode("utf-8"))
            digest.update(str(stamp.get("size", 0)).encode("utf-8"))
        fingerprint = digest.hexdigest()
        changed_inputs = sorted(
            name for name in current.keys()
            if dict(current.get(name, {}) or {}) != dict(previous.get(name, {}) or {})
        )
        if (not previous) and ((not last_fingerprint) or fingerprint == last_fingerprint):
            changed_inputs = []
        drifted = bool(last_fingerprint and fingerprint and fingerprint != last_fingerprint)
        if not last_fingerprint and float(state.get("last_success_at", 0.0) or 0.0) <= 0.0:
            drifted = True
        return {
            "fingerprint": fingerprint,
            "last_fingerprint": last_fingerprint,
            "drifted": drifted,
            "changed_inputs": changed_inputs,
            "input_stamps": current,
        }

    def _start_developmental_sync_scheduler(self, verbose: bool = False) -> None:
        if not self._developmental_sync_enabled or not self._developmental_live_sync_enabled:
            return
        thread = self._developmental_scheduler_thread
        if thread is not None and thread.is_alive():
            return
        stop = threading.Event()
        self._developmental_scheduler_stop = stop

        def _loop() -> None:
            while not stop.wait(self._developmental_live_poll_s):
                if not self._running:
                    break
                try:
                    self.maybe_sync_developmental_surfaces(
                        force=False,
                        reason="live_scheduler",
                        chain_ticks=20,
                        episodes=0,
                        turns=1,
                        dry_run=False,
                        verbose=False,
                    )
                except Exception:
                    continue

        thread = threading.Thread(
            target=_loop,
            name="aurora-developmental-sync",
            daemon=True,
        )
        thread.start()
        self._developmental_scheduler_thread = thread
        if verbose:
            print(
                "[RUNTIME] Developmental sync scheduler active: "
                f"poll={self._developmental_live_poll_s:.0f}s"
            )

    def _stop_developmental_sync_scheduler(self) -> None:
        stop = self._developmental_scheduler_stop
        thread = self._developmental_scheduler_thread
        self._developmental_scheduler_stop = None
        self._developmental_scheduler_thread = None
        if stop is not None:
            stop.set()
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=2.0)
            except Exception:
                pass

    def developmental_sync_status(self) -> Dict[str, Any]:
        state = dict(self._developmental_sync_state or self._load_developmental_sync_state())
        last_success = float(state.get("last_success_at", 0.0) or 0.0)
        drift = self._developmental_sync_drift()
        due_in = 0.0 if last_success <= 0.0 else max(0.0, self._developmental_sync_interval_s - (time.time() - last_success))
        return {
            "enabled": bool(self._developmental_sync_enabled),
            "interval_s": float(self._developmental_sync_interval_s),
            "live_scheduler_enabled": bool(self._developmental_live_sync_enabled),
            "live_poll_s": float(self._developmental_live_poll_s),
            "due": bool(self._developmental_sync_due()),
            "due_in_s": float(due_in),
            "drift": drift,
            "state": state,
        }

    def _developmental_sync_due(self) -> bool:
        state = dict(self._developmental_sync_state or self._load_developmental_sync_state())
        last_success = float(state.get("last_success_at", 0.0) or 0.0)
        drift = self._developmental_sync_drift()
        if last_success <= 0.0:
            return True
        if bool(drift.get("drifted", False)):
            return True
        return (time.time() - last_success) >= float(self._developmental_sync_interval_s)

    def maybe_sync_developmental_surfaces(self,
                                          force: bool = False,
                                          reason: str = "periodic",
                                          chain_ticks: int = 60,
                                          episodes: int = 0,
                                          turns: int = 1,
                                          dry_run: bool = False,
                                          verbose: bool = False) -> Dict[str, Any]:
        with self._developmental_sync_lock:
            state = self._developmental_sync_state or self._load_developmental_sync_state()
            reason_key = str(reason or "periodic")
            if reason_key == "boot":
                state["boot_count"] = int(state.get("boot_count", 0) or 0) + 1
            if reason_key == "save":
                state["save_count"] = int(state.get("save_count", 0) or 0) + 1
            drift = self._developmental_sync_drift()
            last_success = float(state.get("last_success_at", 0.0) or 0.0)
            time_due = bool(last_success <= 0.0 or (time.time() - last_success) >= float(self._developmental_sync_interval_s))
            due = bool(time_due or drift.get("drifted", False))
            trigger_mode = "drift" if bool(drift.get("drifted", False)) else ("interval" if time_due else "idle")
            state["last_reason"] = reason_key
            state["last_attempt_at"] = float(time.time())
            state["last_observed_fingerprint"] = str(drift.get("fingerprint", "") or "")
            state["last_drift"] = {
                "drifted": bool(drift.get("drifted", False)),
                "changed_inputs": list(drift.get("changed_inputs", []) or []),
            }

            if (not force) and ((not self._developmental_sync_enabled) or (not due)):
                status = self.evolved_surface_status()
                state["last_status"] = dict(status or {})
                self._developmental_sync_state = state
                self._persist_developmental_sync_state()
                return {
                    "triggered": False,
                    "reason": reason_key,
                    "due": bool(due),
                    "trigger_mode": trigger_mode,
                    "drift": drift,
                    "status": dict(status or {}),
                }

            if self.code_chamber is None or self._code_autoevolver is None:
                state["last_status"] = {"available": False, "reason": "code_evolution_inactive"}
                self._developmental_sync_state = state
                self._persist_developmental_sync_state()
                return {
                    "triggered": False,
                    "reason": reason_key,
                    "due": bool(due),
                    "trigger_mode": trigger_mode,
                    "drift": drift,
                    "status": dict(state["last_status"]),
                }

            result = self.code_sync_developmental_surfaces(
                chain_ticks=chain_ticks,
                episodes=episodes,
                turns=turns,
                dry_run=dry_run,
            )
            state["sync_count"] = int(state.get("sync_count", 0) or 0) + (0 if dry_run else 1)
            state["last_success_at"] = float(time.time())
            state["last_status"] = dict((result or {}).get("status", {}) or {})
            state["last_fingerprint"] = str(drift.get("fingerprint", "") or "")
            state["last_input_stamps"] = dict(drift.get("input_stamps", {}) or {})
            state["last_trigger_mode"] = trigger_mode
            self._developmental_sync_state = state
            self._persist_developmental_sync_state()
            try:
                if self.steerer is not None:
                    self.steerer._register_function_ancestry(
                        "runtime.maybe_sync_developmental_surfaces",
                        {"existence", "temporal", "boundary", "agency"},
                    )
                    self.steerer._record_function_outcome(
                        "runtime.maybe_sync_developmental_surfaces",
                        1.0,
                        evidence=1.0,
                    )
            except Exception:
                pass
            if verbose:
                stat = dict((result or {}).get("status", {}) or {})
                print(
                    "[RUNTIME] Developmental sync complete: "
                    f"{int(stat.get('surface_count', 0) or 0)} surfaces, "
                    f"{int(stat.get('latent_count', 0) or 0)} latent, "
                    f"{int(stat.get('reflection_count', 0) or 0)} reflections, "
                    f"trigger={trigger_mode}"
                )
            return {
                "triggered": True,
                "reason": reason_key,
                "due": bool(due),
                "trigger_mode": trigger_mode,
                "drift": drift,
                **dict(result or {}),
            }

    def evolved_surface_status(self) -> Dict[str, Any]:
        if self.systems is None:
            return {}
        engine = getattr(self.systems, "evolved_surfaces", None)
        if engine is None:
            return {}
        report = {}
        if hasattr(engine, "capability_report"):
            try:
                report = dict(engine.capability_report() or {})
            except Exception:
                report = {}
        if hasattr(engine, "lineage_manifest"):
            try:
                report["manifest"] = dict(engine.lineage_manifest() or {})
            except Exception:
                pass
        report["sync"] = self.developmental_sync_status()
        return report

    def invoke_evolved_surface(self, name: str, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        if self.systems is None:
            raise RuntimeError("Runtime systems are not booted.")
        engine = getattr(self.systems, "evolved_surfaces", None)
        if engine is None:
            self._reload_evolved_surfaces(verbose=False)
            engine = getattr(self.systems, "evolved_surfaces", None)
        if engine is None:
            raise RuntimeError("Evolved surfaces are not available.")
        fn_name = str(name or "").strip()
        fn = getattr(engine, fn_name, None)
        if not callable(fn):
            raise AttributeError(f"Unknown evolved surface: {fn_name}")
        meta = {}
        if hasattr(engine, "describe_capability"):
            try:
                meta = dict(engine.describe_capability(fn_name) or {})
            except Exception:
                meta = {}
        constraints = set(str(c).strip().lower() for c in (meta.get("constraints", []) or []) if str(c).strip())
        if self.steerer is not None:
            self.steerer._register_function_ancestry(
                f"evolved.{fn_name}",
                constraints or {"existence", "temporal"},
            )
        result = dict(fn(payload=payload, **kwargs) or {})
        if self.steerer is not None:
            score = 1.0 if bool(result) else 0.25
            self.steerer._record_function_outcome(f"evolved.{fn_name}", score, evidence=1.0)
        return result

    def code_sync_developmental_surfaces(self,
                                         chain_ticks: int = 80,
                                         episodes: int = 0,
                                         turns: int = 1,
                                         dry_run: bool = False) -> Dict[str, Any]:
        if self.code_chamber is None or self._code_autoevolver is None:
            raise RuntimeError("Code autoevolution is not active.")
        target = self._ensure_evolved_surface_module()
        native_targets = self._developmental_surface_targets(include_native=True)
        operator_plan = self.recommended_code_operator_order(
            include=["latent_promotion", "architectural_reflection", "native_surface_projection"]
        )
        runs: Dict[str, Any] = {}
        for row in operator_plan:
            operator_key = str(row.get("key", "") or "").strip().lower()
            targets = native_targets if operator_key == "native_surface_projection" else [target]
            runs[operator_key] = self.code_autoevolve_once(
                operator_key=operator_key,
                target_files=targets,
                chain_ticks=chain_ticks,
                episodes=episodes,
                turns=turns,
                dry_run=dry_run,
            )
        if not dry_run:
            self._reload_evolved_surfaces(verbose=False)
        return {
            "target": target,
            "operator_plan": operator_plan,
            "latent": dict(runs.get("latent_promotion", {}) or {}),
            "reflection": dict(runs.get("architectural_reflection", {}) or {}),
            "native_projection": dict(runs.get("native_surface_projection", {}) or {}),
            "runs": runs,
            "status": self.evolved_surface_status(),
        }

    def _resolve_code_targets(self, target_files: Iterable[str]) -> List[str]:
        out: List[str] = []
        for raw in (target_files or []):
            p = str(raw or "").strip()
            if not p:
                continue
            absp = p if os.path.isabs(p) else os.path.join(_HERE, p)
            absp = os.path.abspath(absp)
            if os.path.isfile(absp):
                out.append(absp)
        return sorted(set(out))

    def _run_code_checks(self, target_files: Iterable[str]) -> Tuple[bool, Dict[str, Any]]:
        files = self._resolve_code_targets(target_files)
        details: Dict[str, Any] = {"checked_files": list(files), "compile_failures": []}
        ok = True
        for path in files:
            if not path.endswith(".py"):
                continue
            try:
                py_compile.compile(path, doraise=True)
            except Exception as e:
                ok = False
                details["compile_failures"].append({"file": path, "error": str(e)})
        details["compile_passed"] = bool(ok)
        return ok, details

    def code_operator_specs(self) -> List[Dict[str, Any]]:
        if list_operator_specs is None:
            return []
        out: List[Dict[str, Any]] = []
        for op in list_operator_specs():
            out.append({
                "key": str(getattr(op, "key", "")),
                "description": str(getattr(op, "description", "")),
                "constraints": sorted(set(getattr(op, "constraints", frozenset()) or frozenset())),
                "expected_effect": str(getattr(op, "expected_effect", "")),
                "risk": str(getattr(op, "risk", "")),
            })
        return out

    def stage_code_mutation(self,
                            name: str,
                            operator_key: str,
                            target_files: Iterable[str],
                            constraints: Optional[Iterable[str]] = None,
                            parent_ids: Optional[Iterable[str]] = None,
                            meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.code_chamber is None:
            raise RuntimeError("Code evolution chamber is not active.")
        op = get_operator(operator_key) if get_operator is not None else None
        cset = frozenset(str(c).strip().lower() for c in (constraints or []))
        if not cset and op is not None:
            cset = frozenset(str(c).strip().lower() for c in (getattr(op, "constraints", frozenset()) or frozenset()))
        if not cset:
            cset = frozenset({"existence", "temporal"})
        targets = self._resolve_code_targets(target_files)
        if not targets:
            raise ValueError("No valid target files for code mutation stage.")
        before = self.code_chamber.snapshot(target_files=targets)
        before_system = self.code_chamber.snapshot(target_files=None)
        payload = dict(meta or {})
        payload["operator_key"] = str(operator_key)
        if op is not None:
            payload.setdefault("operator_description", str(getattr(op, "description", "")))
            payload.setdefault("operator_expected_effect", str(getattr(op, "expected_effect", "")))
            payload.setdefault("operator_risk", str(getattr(op, "risk", "")))
        trace = self.code_chamber.propose_mutation(
            name=name,
            constraints_used=cset,
            target_files=targets,
            parent_ids=parent_ids or [],
            meta=payload,
        )
        rec = {
            "mutation_id": str(trace.mutation_id),
            "name": str(name),
            "operator_key": str(operator_key),
            "targets": list(targets),
            "constraints": sorted(set(cset)),
            "before": before.to_dict(),
            "before_system": before_system.to_dict(),
            "staged_at": time.time(),
            "simulation_gate": None,
        }
        self._code_pending[str(trace.mutation_id)] = {
            "trace": trace,
            "before": before,
            "before_system": before_system,
            "record": rec,
        }
        return rec

    def _run_simulation_gate(self,
                             chain_ticks: int = 200,
                             episodes: int = 1,
                             turns: int = 4,
                             verbose: bool = False) -> Dict[str, Any]:
        if self.steerer is None:
            raise RuntimeError("Steerer unavailable for simulation gate.")
        s = self.steerer
        chain_ticks = max(1, int(chain_ticks))
        episodes = max(0, int(episodes))
        turns = max(1, int(turns))
        start = s.stance_snapshot()
        gate_start = time.time()
        chain_summary = s.chain_burst(chain_ticks, epoch_size=max(25, min(200, chain_ticks)), verbose=verbose)
        sim_result = None
        if episodes > 0:
            sim_result = s.sim_epoch(episodes=episodes, turns=turns)
        end = s.stance_snapshot()
        diff = self._stance_diff(start, end)
        evo = s.evolution_report()
        path_aligned = bool(evo.get("path_aligned", False))
        relief_delta = int(diff.get("relief_delta", 0))
        links_delta = int(diff.get("links_delta", 0))
        conflicts_delta = int(diff.get("conflicts_delta", 0))
        fitness = float((sim_result or {}).get("avg_fitness", 0.0) if isinstance(sim_result, dict) else 0.0)
        passed = bool(path_aligned and relief_delta >= 0 and links_delta >= 0 and conflicts_delta <= max(3, chain_ticks // 50))
        return {
            "passed": passed,
            "path_aligned": path_aligned,
            "relief_delta": relief_delta,
            "links_delta": links_delta,
            "conflicts_delta": conflicts_delta,
            "avg_fitness": fitness,
            "duration_s": float(time.time() - gate_start),
            "chain_ticks": chain_ticks,
            "episodes": episodes,
            "turns": turns,
            "chain_summary": chain_summary,
            "sim_result": sim_result,
            "stance_diff": diff,
        }

    def _feedback_code_mutation_to_genealogy(self,
                                             trace: Any,
                                             result: Dict[str, Any],
                                             notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.systems is None:
            return {"registered": False, "reason": "systems_unavailable"}
        genealogy = getattr(self.systems, "genealogy", None)
        if genealogy is None or not hasattr(genealogy, "register_code_evolution_outcome"):
            return {"registered": False, "reason": "genealogy_feedback_unavailable"}

        result = dict(result or {})
        notes = dict(notes or {})
        apply_result = dict(notes.get("apply_result", {}) or {})
        simulation_gate = dict(notes.get("simulation_gate", {}) or {})
        auto_checks = dict(notes.get("auto_checks", {}) or {})
        targets = [str(p) for p in (getattr(trace, "target_files", tuple()) or tuple()) if str(p)]
        rel_targets: List[str] = []
        target_modules: List[str] = []
        for raw in targets:
            try:
                rel = os.path.relpath(str(raw), _HERE).replace("\\", "/")
            except Exception:
                rel = str(raw).replace("\\", "/")
            rel_targets.append(rel)
            module = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel.replace("/", ".")
            target_modules.append(module)
        history = dict(result.get("history", {}) or {})
        ripple = dict(result.get("ripple_effects", {}) or {})
        payload = {
            "mutation_id": str(getattr(trace, "mutation_id", "") or result.get("mutation_id", "")),
            "operator_key": str(getattr(trace, "meta", {}) and dict(getattr(trace, "meta", {}) or {}).get("operator_key", "") or notes.get("operator_key", "") or result.get("operator_key", "")),
            "accepted": bool(result.get("accepted", False)),
            "constraints": list(getattr(trace, "constraints_used", tuple()) or tuple()),
            "target_files": rel_targets,
            "target_modules": target_modules,
            "changed_files": [
                os.path.relpath(str(p), _HERE).replace("\\", "/")
                for p in (apply_result.get("changed_files", []) or [])
                if str(p)
            ],
            "change_count": int(apply_result.get("change_count", 0) or 0),
            "score": float(1.0 if bool(result.get("accepted", False)) else 0.25),
            "avg_fitness": float(simulation_gate.get("avg_fitness", 0.0) or 0.0),
            "conflicts_delta": float(simulation_gate.get("conflicts_delta", 0.0) or 0.0),
            "compile_failures": int(len(auto_checks.get("compile_failures", []) or [])),
            "genealogy_pressure": float(history.get("developmental_summary", {}).get("system_impact_score", 0.0) or 0.0),
            "rewrite_profile": str(notes.get("operator_key", "") or result.get("operator_key", "") or "generic"),
            "effect_modes": list((history.get("direct_system_effects", {}) or {}).get("effect_modes", []) or []),
            "ripple_effects": ripple,
            "apply_duration_s": float(notes.get("timing_feedback", {}).get("apply_duration_s", 0.0) or 0.0),
            "agency_time_credit": float(notes.get("timing_feedback", {}).get("agency_time_credit", 0.0) or 0.0),
            "temporal_overhead_penalty": float(notes.get("timing_feedback", {}).get("temporal_overhead_penalty", 0.0) or 0.0),
        }
        try:
            return dict(genealogy.register_code_evolution_outcome(payload) or {})
        except Exception as e:
            return {"registered": False, "reason": f"genealogy_feedback_error: {e}"}

    def code_simulate_mutation(self,
                               mutation_id: str,
                               chain_ticks: int = 200,
                               episodes: int = 1,
                               turns: int = 4,
                               verbose: bool = False) -> Dict[str, Any]:
        mid = str(mutation_id or "").strip()
        pending = self._code_pending.get(mid)
        if pending is None:
            raise KeyError(f"Unknown staged mutation id: {mid}")
        result = self._run_simulation_gate(
            chain_ticks=chain_ticks,
            episodes=episodes,
            turns=turns,
            verbose=verbose,
        )
        pending["sim_gate"] = dict(result)
        rec = dict(pending.get("record", {}) or {})
        rec["simulation_gate"] = dict(result)
        pending["record"] = rec
        try:
            if self.steerer is not None:
                self.steerer._register_function_ancestry(
                    "runtime.code_simulate_mutation",
                    {"existence", "temporal", "energy", "boundary", "agency"},
                )
                score = 1.0 if bool(result.get("passed", False)) else 0.0
                self.steerer._record_function_outcome("runtime.code_simulate_mutation", score, evidence=1.0)
        except Exception:
            pass
        return result

    def finalize_code_mutation(self,
                               mutation_id: str,
                               checks_passed: Optional[bool] = None,
                               notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.code_chamber is None:
            raise RuntimeError("Code evolution chamber is not active.")
        mid = str(mutation_id or "").strip()
        pending = self._code_pending.get(mid)
        if pending is None:
            raise KeyError(f"Unknown staged mutation id: {mid}")
        trace = pending["trace"]
        before = pending["before"]
        sim_gate = dict(pending.get("sim_gate", {}) or {})
        auto_ok, check_details = self._run_code_checks(getattr(trace, "target_files", tuple()))
        if checks_passed is None:
            final_checks = bool(auto_ok)
        else:
            final_checks = bool(checks_passed and auto_ok)
        if self._code_require_sim_gate:
            final_checks = bool(final_checks and sim_gate.get("passed", False))
        note_payload = dict(notes or {})
        note_payload["auto_checks"] = check_details
        note_payload["simulation_gate"] = sim_gate
        timing_feedback = dict(note_payload.get("timing_feedback", {}) or {})
        if timing_feedback:
            note_payload["timing_feedback_state"] = self._integrate_code_timing_feedback(timing_feedback)
        before_system = pending.get("before_system")
        after_system = self.code_chamber.snapshot(target_files=None)
        result = self.code_chamber.evaluate_mutation(
            trace=trace,
            before=before,
            checks_passed=final_checks,
            notes=note_payload,
            system_before=before_system,
            system_after=after_system,
        )
        result["genealogy_feedback"] = self._feedback_code_mutation_to_genealogy(trace, result, note_payload)
        self._code_latest = dict(result or {})
        self._code_history.append(dict(result or {}))
        self._code_pending.pop(mid, None)
        try:
            if self.steerer is not None:
                self.steerer._register_function_ancestry(
                    "runtime.finalize_code_mutation",
                    {"existence", "temporal", "energy", "boundary", "agency"},
                )
                score = 1.0 if bool(result.get("accepted", False)) else 0.0
                if timing_feedback:
                    score = max(0.0, min(1.0, score + (0.20 * float(timing_feedback.get("agency_time_credit", 0.0) or 0.0)) - (0.15 * float(timing_feedback.get("temporal_overhead_penalty", 0.0) or 0.0))))
                self.steerer._record_function_outcome("runtime.finalize_code_mutation", score, evidence=1.0)
        except Exception:
            pass
        return result

    def code_mutation_status(self) -> Dict[str, Any]:
        chamber_summary = self.code_chamber.summary() if self.code_chamber is not None else {}
        chamber_lineage = {}
        if self.code_chamber is not None and hasattr(self.code_chamber, "lineage_report"):
            try:
                chamber_lineage = dict(self.code_chamber.lineage_report() or {})
            except Exception:
                chamber_lineage = {}
        return {
            "enabled": bool(self.code_chamber is not None),
            "autoevolver_enabled": bool(self._code_autoevolver is not None),
            "require_sim_gate": bool(self._code_require_sim_gate),
            "developmental_sync": self.developmental_sync_status(),
            "recommended_operator_order": self.recommended_code_operator_order(),
            "pending": sorted(self._code_pending.keys()),
            "pending_count": int(len(self._code_pending)),
            "latest": dict(self._code_latest or {}),
            "recent_count": int(len(self._code_history)),
            "chamber": dict(chamber_summary or {}),
            "lineage": chamber_lineage,
        }

    def code_pressure_report(self, target_files: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        if self.code_chamber is None:
            return {}
        targets = self._resolve_code_targets(target_files or [])
        snap = self.code_chamber.snapshot(target_files=targets or None)
        metrics = dict(snap.metrics or {})
        chamber_summary = self.code_chamber.summary() if self.code_chamber is not None else {}
        return {
            "pressure": dict(snap.pressure.to_dict()),
            "files": int(metrics.get("files", 0) or 0),
            "module_pressures": dict(metrics.get("module_pressures", {}) or {}),
            "subsystem_pressures": dict(metrics.get("subsystem_pressures", {}) or {}),
            "operator_gradients": dict(chamber_summary.get("operator_gradients", {}) or {}),
            "governor": dict(chamber_summary.get("governor", {}) or {}),
        }

    def code_autoevolve_once(self,
                             operator_key: str,
                             target_files: Iterable[str],
                             chain_ticks: int = 200,
                             episodes: int = 1,
                             turns: int = 4,
                             dry_run: bool = False) -> Dict[str, Any]:
        if self.code_chamber is None or self._code_autoevolver is None:
            raise RuntimeError("Code autoevolver is not active.")
        targets = self._resolve_code_targets(target_files)
        if not targets:
            raise ValueError("No valid target files for code autoevolution.")
        stage = self.stage_code_mutation(
            name=f"autoevolve_{str(operator_key).strip().lower()}",
            operator_key=operator_key,
            target_files=targets,
            constraints=None,
            meta={"autoevolve": True, "dry_run": bool(dry_run)},
        )
        mutation_id = str(stage.get("mutation_id", ""))
        apply_result: Dict[str, Any] = {"operator_key": operator_key, "change_count": 0, "changed_files": [], "backups": {}}
        if not dry_run:
            apply_result = self._code_autoevolver.apply_operator(operator_key=operator_key, target_files=targets)
        timing_feedback = self._code_timing_feedback_from_apply(apply_result)
        sim = self.code_simulate_mutation(
            mutation_id=mutation_id,
            chain_ticks=chain_ticks,
            episodes=episodes,
            turns=turns,
            verbose=False,
        )
        finalize_notes = {
            "autoevolve": True,
            "operator_key": operator_key,
            "apply_result": {k: v for k, v in apply_result.items() if k != "backups"},
            "timing_feedback": timing_feedback,
            "dry_run": bool(dry_run),
        }
        final = self.finalize_code_mutation(mutation_id, notes=finalize_notes)
        accepted = bool(final.get("accepted", False))
        rolled_back = False
        if (not accepted) and (not dry_run):
            backups = dict(apply_result.get("backups", {}) or {})
            if backups:
                self._code_autoevolver.rollback(backups)
                rolled_back = True
        if accepted and (not dry_run):
            changed_paths = {os.path.abspath(p) for p in (apply_result.get("changed_files", []) or [])}
            evolved_path = os.path.abspath(os.path.join(_HERE, "aurora_internal", "aurora_evolved_surfaces.py"))
            if evolved_path in changed_paths:
                self._reload_evolved_surfaces(verbose=False)
        result = {
            "mutation_id": mutation_id,
            "operator_key": str(operator_key),
            "targets": list(targets),
            "sim": sim,
            "final": final,
            "applied_changes": int(apply_result.get("change_count", 0) or 0),
            "apply_duration_s": float(apply_result.get("duration_s", 0.0) or 0.0),
            "timing_feedback": timing_feedback,
            "changed_files": list(apply_result.get("changed_files", []) or []),
            "rolled_back": bool(rolled_back),
            "dry_run": bool(dry_run),
        }
        try:
            if self.steerer is not None:
                self.steerer._register_function_ancestry(
                    "runtime.code_autoevolve_once",
                    {"existence", "temporal", "energy", "boundary", "agency"},
                )
                score = 1.0 if bool(accepted) else 0.0
                score = max(0.0, min(1.0, score + (0.25 * float(timing_feedback.get("agency_time_credit", 0.0) or 0.0)) - (0.20 * float(timing_feedback.get("temporal_overhead_penalty", 0.0) or 0.0))))
                self.steerer._record_function_outcome("runtime.code_autoevolve_once", score, evidence=1.0)
        except Exception:
            pass
        return result

    def evolution_report(self) -> Dict[str, Any]:
        if self.steerer is None:
            return {}
        return self.steerer.evolution_report()

    def _stance_diff(self, start: Dict[str, Any], end: Dict[str, Any]) -> Dict[str, Any]:
        start = dict(start or {})
        end = dict(end or {})
        diff = {
            "ticks_delta": int(end.get("ticks", 0)) - int(start.get("ticks", 0)),
            "relief_delta": int(end.get("relief_events", 0)) - int(start.get("relief_events", 0)),
            "bridge_delta": int(end.get("bridge_events", 0)) - int(start.get("bridge_events", 0)),
            "epochs_delta": int(end.get("epochs", 0)) - int(start.get("epochs", 0)),
            "links_delta": int(end.get("links", 0)) - int(start.get("links", 0)),
            "abilities_delta": int(end.get("abilities", 0)) - int(start.get("abilities", 0)),
            "conflicts_delta": int(end.get("conflicts_injected", 0)) - int(start.get("conflicts_injected", 0)),
            "plateau_pressure_delta": int(end.get("plateau_pressure_events", 0)) - int(start.get("plateau_pressure_events", 0)),
            "budget_start": start.get("budget"),
            "budget_end": end.get("budget"),
            "gradient_delta": {},
        }
        sg = dict(start.get("gradients", {}) or {})
        eg = dict(end.get("gradients", {}) or {})
        for ax in AXES:
            diff["gradient_delta"][ax] = float(eg.get(ax, 0.0)) - float(sg.get(ax, 0.0))
        return diff

    def review_before_save(self, verbose: bool = True) -> bool:
        if self.steerer is None:
            return True

        if verbose:
            self.steerer.print_evolution_report()

        rep = self.steerer.evolution_report()
        end_stance = self.steerer.stance_snapshot()
        stance_diff = self._stance_diff(self._start_stance, end_stance)

        if verbose:
            print("\n  RUN DIFF (start -> end)")
            print("  " + "-" * 58)
            print(f"  Ticks            : {self._start_stance.get('ticks',0)} -> {end_stance.get('ticks',0)}  (Δ {stance_diff['ticks_delta']:+d})")
            print(f"  Relief events    : {self._start_stance.get('relief_events',0)} -> {end_stance.get('relief_events',0)}  (Δ {stance_diff['relief_delta']:+d})")
            print(f"  Bridge events    : {self._start_stance.get('bridge_events',0)} -> {end_stance.get('bridge_events',0)}  (Δ {stance_diff['bridge_delta']:+d})")
            print(f"  Links            : {self._start_stance.get('links',0)} -> {end_stance.get('links',0)}  (Δ {stance_diff['links_delta']:+d})")
            print(f"  Abilities        : {self._start_stance.get('abilities',0)} -> {end_stance.get('abilities',0)}  (Δ {stance_diff['abilities_delta']:+d})")
            print(f"  Conflicts injected: {self._start_stance.get('conflicts_injected',0)} -> {end_stance.get('conflicts_injected',0)}  (Δ {stance_diff['conflicts_delta']:+d})")
            print(f"  Plateau pressure : {self._start_stance.get('plateau_pressure_events',0)} -> {end_stance.get('plateau_pressure_events',0)}  (Δ {stance_diff['plateau_pressure_delta']:+d})")
            if stance_diff.get('budget_start') is not None and stance_diff.get('budget_end') is not None:
                print(f"  Budget           : {float(stance_diff['budget_start']):.6f} -> {float(stance_diff['budget_end']):.6f}")
            gd = stance_diff.get('gradient_delta', {})
            print("  Pressure Δ       : " + ", ".join([f"{ax}={float(gd.get(ax,0.0)):+.6f}" for ax in AXES]))

        aligned = bool(rep.get("path_aligned", False))
        traits = list(rep.get("emergent_traits", []) or [])
        if traits:
            good = sum(1 for t in traits if bool(t.get("recommended", False)))
            trait_ratio = good / float(len(traits))
            aligned = aligned and (trait_ratio >= 0.40)
        recommended = "save" if aligned else "discard"
        try:
            if self.steerer is not None:
                self.steerer._record_function_outcome("review_before_save", 1.0 if aligned else 0.0, evidence=1.0)
        except Exception:
            pass

        if not self.require_save_gate:
            if verbose:
                print(f"[RUNTIME] Save gate disabled. Recommended={recommended}; proceeding with save.")
            return True

        if not sys.stdin.isatty():
            if verbose:
                print(f"[RUNTIME] Non-interactive session. Recommended={recommended}; proceeding with save.")
            return True

        prompt = (
            f"[RUNTIME] Save this session? recommended={recommended} "
            f"(reliefΔ={stance_diff['relief_delta']:+d}, linksΔ={stance_diff['links_delta']:+d}, "
            f"conflictΔ={stance_diff['conflicts_delta']:+d}) [y/N]: "
        )
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            answer = ""
        return answer in ("y", "yes")

    def save(self, verbose: bool = True) -> bool:
        """Persist current state through available channels."""
        if self.systems is None:
            return False

        saved = False
        try:
            sync_result = self.maybe_sync_developmental_surfaces(
                force=False,
                reason="save",
                chain_ticks=40,
                episodes=0,
                turns=1,
                dry_run=False,
                verbose=verbose,
            )
            if bool(sync_result.get("triggered", False)):
                saved = True
        except Exception as e:
            if verbose:
                print(f"[RUNTIME] Developmental sync save pass failed: {e}")

        _pg_ok = _persist_operator_gradients(self.output_dir, verbose=verbose)
        if _pg_ok:
            saved = True
        try:
            if self.steerer is not None:
                self.steerer._register_function_ancestry("runtime.persist_operator_gradients", {"energy", "temporal", "boundary"})
                self.steerer._record_function_outcome("runtime.persist_operator_gradients", 1.0 if _pg_ok else 0.0, evidence=1.0)
        except Exception:
            pass

        # Genealogy flush — flush_files() writes JSONL fossil record + abilities.json + links.json
        genealogy = self.systems.genealogy
        if genealogy is not None:
            try:
                genealogy.flush_files()
                saved = True
                if verbose:
                    print("[RUNTIME] Genealogy fossil record flushed.")
            except Exception as e:
                if verbose:
                    print(f"[RUNTIME] Genealogy flush failed: {e}")

        # Checkpoint save
        checkpoint = self.systems.checkpoint
        if checkpoint is not None:
            try:
                checkpoint.save()
                saved = True
                if verbose:
                    print("[RUNTIME] Checkpoint saved.")
            except Exception as e:
                if verbose:
                    print(f"[RUNTIME] Checkpoint save failed: {e}")

        if self.code_chamber is not None:
            try:
                self.code_chamber.flush_files()
                saved = True
                if verbose:
                    print("[RUNTIME] Code evolution records flushed.")
            except Exception as e:
                if verbose:
                    print(f"[RUNTIME] Code evolution flush failed: {e}")

        if self._persist_developmental_sync_state():
            saved = True

        try:
            if self.steerer is not None:
                self.steerer._record_function_outcome("save", 1.0 if saved else 0.0, evidence=1.0)
        except Exception:
            pass
        return saved

    def uptime(self) -> float:
        """Seconds since boot."""
        if self._boot_time is None:
            return 0.0
        return time.time() - self._boot_time

    def shutdown(self, save: bool = True, verbose: bool = True) -> None:
        """Graceful shutdown — review evolution, optional save, stop auto-save."""
        if verbose:
            print("\n[RUNTIME] Shutting down...")
        if save:
            if self.review_before_save(verbose=verbose):
                self.save(verbose=verbose)
            elif verbose:
                print("[RUNTIME] Save skipped by operator decision.")

        # Stop checkpoint auto-save thread
        if self.systems is not None and self.systems.has("checkpoint"):
            try:
                self.systems.checkpoint.stop_auto_save()
            except Exception:
                pass

        # Close genealogy file handles
        if self.systems is not None and self.systems.has("genealogy"):
            try:
                self.systems.genealogy.close()
            except Exception:
                pass

        self._stop_developmental_sync_scheduler()
        self._running = False
        try:
            if self.steerer is not None:
                self.steerer._record_function_outcome("shutdown", 1.0, evidence=1.0)
        except Exception:
            pass
        if verbose:
            print(f"[RUNTIME] Uptime: {self.uptime():.1f}s. Goodbye.\n")


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         AURORA UNIVERSE STEERER — Interactive Mode           ║
║         Authors: Sunni (Sir) Morningstar and Cael Devo       ║
╚══════════════════════════════════════════════════════════════╝

Type 'help' for a full command list.
The universe runs on constraint physics. You steer, it decides.
"""

HELP_TEXT = """
CHAIN COMMANDS
  tick [N]               Advance chamber N ticks (default 1)
  inject <action>        Inject one named action into the chamber
  custom <name> <axes>   Inject a custom action  e.g.: custom my_act agency,boundary
  chain [N] [epoch]      Run N chain ticks (default 1000, epoch 200)
  register <name> <axes> Register a custom named action for later use
  conflict [N]          Inject N targeted conflict rounds (default 3)

SIMULATION COMMANDS
  episode                Run one simulation episode (L7)
  epoch [N] [turns]      Run one epoch of N episodes, T turns each

SYNC COMMANDS
  bridge                 Sync newly promoted links → simulation now

INFORMATION COMMANDS
  status                 Full universe state summary
  pressure               Live operator pressure gradient snapshot
  links [N]              Top N promoted evolutionary links (default 10)
  learned                What Aurora has consciously understood
  actions                List all available named actions
  evolution              Show session evolution + alignment report
  code_ops               List canonical code mutation operators
  code_status            Show code evolution chamber status
  code_pressure [files]  Show multi-scale code pressure (files optional csv)
  uptime                 Show runtime uptime

CODE EVOLUTION
  code_stage <op> <name> <files> [axes]
                       Stage mutation baseline (files is comma-separated paths)
  code_simulate <id> [ticks] [episodes] [turns]
                       Run simulation gate for staged mutation
  code_finalize <id>   Finalize staged mutation with auto compile checks
  code_autoevolve <op> <files> [ticks] [episodes] [turns]
                       Apply constrained mutation + simulate + finalize (+ rollback if rejected)

PERSISTENCE
  save                   Flush fossil record + checkpoint

NAVIGATION
  answer <text>          Answer Aurora's pending clarification question
  quit / exit / q        Save and exit
  help / ?               This help text
"""


class RuntimeCLI:
    """Interactive terminal loop for steering the universe."""

    def __init__(self, runtime: AuroraRuntime):
        self.runtime  = runtime
        self._running = False

    def run(self) -> None:
        print(BANNER)
        self._running = True
        signal.signal(signal.SIGINT, self._handle_interrupt)
        allowed_during_gap = {"answer", "help", "?", "quit", "exit", "q", "status", "pressure", "uptime", "save"}

        while self._running:
            try:
                raw = input("aurora> ").strip()
            except EOFError:
                break

            if not raw:
                continue

            parts = raw.split()
            cmd   = parts[0].lower()
            args  = parts[1:]

            # Hard clarification gate: while a comprehension gap is pending,
            # only explicit answer/help/exit/status-style commands are allowed.
            if (
                self.runtime.steerer is not None
                and self.runtime.steerer.has_pending_gap()
                and cmd not in allowed_during_gap
            ):
                prompt = self.runtime.steerer.pending_gap_prompt() or "Aurora has a pending clarification question."
                print(f"  Clarification pending: {prompt}")
                print("  Reply with: answer <text>")
                continue

            if cmd == "answer":
                payload = " ".join(args).strip()
                if not payload:
                    print("  Usage: answer <text>")
                    continue
                try:
                    if self.runtime.steerer is not None:
                        self.runtime.steerer.observe_input_text(payload)
                    print("  Clarification received.")
                except Exception as e:
                    print(f"  answer failed: {e}")
                continue

            # Free-text (non-command) input still feeds awareness modules.
            if cmd not in {
                "tick", "inject", "custom", "chain", "register", "conflict",
                "episode", "epoch", "bridge",
                "status", "pressure", "links", "learned", "actions", "evolution", "uptime",
                "code_ops", "code_status", "code_pressure", "code_stage", "code_simulate",
                "code_finalize", "code_autoevolve",
                "save", "quit", "exit", "q", "help", "?",
            }:
                try:
                    if self.runtime.steerer is not None:
                        self.runtime.steerer.observe_input_text(raw)
                except Exception:
                    pass

            self._dispatch(cmd, args)

        self.runtime.shutdown()

    def _handle_interrupt(self, sig, frame) -> None:
        print("\n[CLI] Interrupt — type 'quit' to exit or continue.")

    def _dispatch(self, cmd: str, args: List[str]) -> None:
        s = self.runtime.steerer
        if s is None:
            print("[CLI] Runtime not booted.")
            return

        # ── Chain ────────────────────────────────────────────────
        if cmd == "tick":
            n       = int(args[0]) if args else 1
            results = s.tick(n)
            relief  = sum(1 for r in results if r is not None)
            print(f"  {n} ticks → {relief} relief event(s)")

        elif cmd == "inject":
            if not args:
                print("  Usage: inject <action_name>")
            else:
                result = s.inject(" ".join(args))
                print(f"  Relief: {result is not None}")

        elif cmd == "custom":
            if len(args) < 2:
                print("  Usage: custom <name> <axis1,axis2,...>")
                print("  Axes: existence temporal energy boundary agency")
            else:
                name   = args[0]
                axes   = frozenset(a.strip() for a in args[1].split(","))
                result = s.inject_custom(name, axes)
                print(f"  Relief: {result is not None}")

        elif cmd == "chain":
            n     = int(args[0]) if args else 1000
            epoch = int(args[1]) if len(args) > 1 else 200
            s.chain_burst(n, epoch_size=epoch, verbose=True)

        elif cmd == "register":
            if len(args) < 2:
                print("  Usage: register <name> <axis1,axis2,...>")
            else:
                name = args[0]
                axes = frozenset(a.strip() for a in args[1].split(","))
                s.register_action(name, axes)

        elif cmd == "conflict":
            rounds = int(args[0]) if args else 3
            info = s.inject_conflict_rounds(rounds=rounds, verbose=False)
            print(f"  Conflict rounds: injected={info['injected']} resolved={info['resolved']}")

        # ── Simulation ───────────────────────────────────────────
        elif cmd == "episode":
            result = s.sim_episode()
            if result:
                print(f"  Episode: "
                      f"fitness={getattr(result,'avg_fitness',0):.3f}  "
                      f"engagement={getattr(result,'final_engagement',0):.3f}  "
                      f"turns={getattr(result,'turns',0)}")

        elif cmd == "epoch":
            n_eps  = int(args[0]) if args else 4
            n_turn = int(args[1]) if len(args) > 1 else 5
            result = s.sim_epoch(episodes=n_eps, turns=n_turn)
            if result:
                print(f"  Epoch complete: "
                      f"fitness={result.get('avg_fitness',0):.3f}  "
                      f"episodes={result.get('episodes','?')}")

        # ── Sync ─────────────────────────────────────────────────
        elif cmd == "bridge":
            events = self.runtime.bridge.inject_promoted_links()
            print(f"  Bridge sync: {len(events)} link(s) injected")

        # ── Info ─────────────────────────────────────────────────
        elif cmd == "status":
            s.status()

        elif cmd == "pressure":
            s.pressure_report()

        elif cmd == "links":
            top = int(args[0]) if args else 10
            s.links(top_n=top)

        elif cmd == "learned":
            s.what_learned()

        elif cmd == "actions":
            s.available_actions()

        elif cmd == "evolution":
            s.print_evolution_report()

        elif cmd == "uptime":
            u = self.runtime.uptime()
            print(f"  Uptime: {u:.1f}s  ({u/60:.1f} min)")

        elif cmd == "code_ops":
            ops = self.runtime.code_operator_specs()
            if not ops:
                print("  Code operator catalog unavailable.")
            else:
                print("  Code mutation operators:")
                for op in ops:
                    print(f"    - {op['key']}: {op['description']}")
                    print(f"      constraints={op['constraints']}  effect={op['expected_effect']}")

        elif cmd == "code_status":
            st = self.runtime.code_mutation_status()
            print(f"  enabled={st.get('enabled')}  pending={st.get('pending_count')}  recent={st.get('recent_count')}")
            latest = dict(st.get("latest", {}) or {})
            if latest:
                print(
                    f"  latest: tick={latest.get('tick')} accepted={latest.get('accepted')} "
                    f"net={float(latest.get('net_benefit',0.0)):+.6f}"
                )
            chamber = dict(st.get("chamber", {}) or {})
            if chamber:
                print(
                    f"  chamber: ticks={chamber.get('tick_count')} accepted={chamber.get('accepted_count')} "
                    f"rejected={chamber.get('rejected_count')} links={chamber.get('total_links')}"
                )
            lin = dict(st.get("lineage", {}) or {})
            if lin:
                ripple_roots = len(list(lin.get("top_ripple_roots", []) or []))
                print(
                    f"  lineage: nodes={lin.get('nodes')} edges={lin.get('edges')} "
                    f"roots={lin.get('children_roots')} ripple_roots={ripple_roots}"
                )

        elif cmd == "code_pressure":
            files = [x.strip() for x in str(args[0]).split(",") if x.strip()] if args else []
            rep = self.runtime.code_pressure_report(target_files=files)
            if not rep:
                print("  Code chamber unavailable.")
            else:
                p = dict(rep.get("pressure", {}) or {})
                print(
                    "  pressure: "
                    + ", ".join([f"{ax}={float(p.get(ax,0.0)):.4f}" for ax in ("X", "T", "N", "B", "A")])
                )
                sps = dict(rep.get("subsystem_pressures", {}) or {})
                if sps:
                    print("  subsystem pressure:")
                    for k in sorted(sps.keys()):
                        v = dict(sps.get(k, {}) or {})
                        print(
                            f"    - {k}: "
                            + ", ".join([f"{ax}={float(v.get(ax,0.0)):.3f}" for ax in ("X", "T", "N", "B", "A")])
                        )
                grads = dict(rep.get("operator_gradients", {}) or {})
                if grads:
                    print(
                        "  code operator gradients: "
                        + ", ".join([f"{ax}={float(grads.get(ax,0.0)):+.4f}" for ax in ("X", "T", "N", "B", "A")])
                    )

        elif cmd == "code_stage":
            if len(args) < 3:
                print("  Usage: code_stage <operator_key> <name> <file1,file2,...> [axis1,axis2,...]")
            else:
                op_key = str(args[0]).strip()
                name = str(args[1]).strip()
                files = [x.strip() for x in str(args[2]).split(",") if x.strip()]
                axes = [x.strip() for x in str(args[3]).split(",")] if len(args) > 3 else []
                try:
                    rec = self.runtime.stage_code_mutation(
                        name=name,
                        operator_key=op_key,
                        target_files=files,
                        constraints=axes,
                    )
                    print(
                        f"  staged mutation_id={rec.get('mutation_id')} "
                        f"constraints={rec.get('constraints')} targets={rec.get('targets')}"
                    )
                except Exception as e:
                    print(f"  code_stage failed: {e}")

        elif cmd == "code_simulate":
            if not args:
                print("  Usage: code_simulate <mutation_id> [chain_ticks] [episodes] [turns]")
            else:
                mid = str(args[0]).strip()
                ticks = int(args[1]) if len(args) > 1 else 200
                episodes = int(args[2]) if len(args) > 2 else 1
                turns = int(args[3]) if len(args) > 3 else 4
                try:
                    rec = self.runtime.code_simulate_mutation(
                        mutation_id=mid,
                        chain_ticks=ticks,
                        episodes=episodes,
                        turns=turns,
                        verbose=False,
                    )
                    print(
                        f"  simulate: passed={rec.get('passed')} "
                        f"reliefΔ={rec.get('relief_delta')} linksΔ={rec.get('links_delta')} "
                        f"fitness={float(rec.get('avg_fitness',0.0)):.3f}"
                    )
                except Exception as e:
                    print(f"  code_simulate failed: {e}")

        elif cmd == "code_finalize":
            if not args:
                print("  Usage: code_finalize <mutation_id>")
            else:
                try:
                    rec = self.runtime.finalize_code_mutation(args[0])
                    print(
                        f"  finalized tick={rec.get('tick')} accepted={rec.get('accepted')} "
                        f"net={float(rec.get('net_benefit',0.0)):+.6f}"
                    )
                except Exception as e:
                    print(f"  code_finalize failed: {e}")

        elif cmd == "code_autoevolve":
            if len(args) < 2:
                print("  Usage: code_autoevolve <operator_key> <file1,file2,...> [chain_ticks] [episodes] [turns]")
            else:
                op_key = str(args[0]).strip()
                files = [x.strip() for x in str(args[1]).split(",") if x.strip()]
                ticks = int(args[2]) if len(args) > 2 else 200
                episodes = int(args[3]) if len(args) > 3 else 1
                turns = int(args[4]) if len(args) > 4 else 4
                try:
                    rec = self.runtime.code_autoevolve_once(
                        operator_key=op_key,
                        target_files=files,
                        chain_ticks=ticks,
                        episodes=episodes,
                        turns=turns,
                        dry_run=False,
                    )
                    final = dict(rec.get("final", {}) or {})
                    print(
                        f"  autoevolve: accepted={final.get('accepted')} "
                        f"changes={rec.get('applied_changes')} rollback={rec.get('rolled_back')} "
                        f"net={float(final.get('net_benefit',0.0)):+.6f}"
                    )
                except Exception as e:
                    print(f"  code_autoevolve failed: {e}")

        # ── Persistence ───────────────────────────────────────────
        elif cmd == "save":
            self.runtime.save()

        elif cmd == "answer":
            print("  Usage: answer <text>")

        # ── Exit ─────────────────────────────────────────────────
        elif cmd in ("quit", "exit", "q"):
            self._running = False

        elif cmd in ("help", "?"):
            print(HELP_TEXT)

        else:
            print(f"  Unknown command '{cmd}'. Type 'help' for options.")


# =============================================================================
# MODE RUNNERS
# =============================================================================

def mode_test(state_dir: str, output_dir: str) -> None:
    """Self-checks for the runtime module."""
    print("\n[TEST MODE]")
    checks_pass = 0
    checks_fail = 0

    def chk(name: str, cond: bool, detail: str = "") -> None:
        nonlocal checks_pass, checks_fail
        if cond:
            checks_pass += 1
            print(f"  ✓ {name}" + (f"  ({detail})" if detail else ""))
        else:
            checks_fail += 1
            print(f"  ✗ {name}" + (f"  ({detail})" if detail else ""))

    # — Boot —
    try:
        runtime = AuroraRuntime(state_dir=state_dir, output_dir=output_dir, run_id="test_run")
        runtime.boot(verbose=False)
        chk("Runtime boots", True)
    except Exception as e:
        chk("Runtime boots", False, str(e))
        print(f"\n  FATAL: {e}")
        return

    s = runtime.steerer
    chk("Steerer exists",      s is not None)
    chk("Systems L0 active",   runtime.systems.has("contract"))
    chk("Systems L1 active",   runtime.systems.has("lattice"))
    chk("Chamber active",      runtime.systems.has("chamber"))
    chk("Genealogy active",    runtime.systems.has("genealogy"))
    chk("Code chamber active", runtime.code_chamber is not None)

    # — Chamber alive property —
    chk("Chamber.alive is True", runtime.systems.chamber.alive)

    # — Tick —
    results = s.tick(10)
    chk("tick(10) runs", len(results) == 10, f"got {len(results)}")

    # — Inject by name —
    result = s.inject("communicate")
    chk("inject('communicate') runs", True)

    # — Custom inject —
    result2 = s.inject_custom("test_custom", frozenset({"existence", "agency"}),
                               meta={"test": True})
    chk("inject_custom runs", True)

    # — Chain burst —
    summary = s.chain_burst(200, epoch_size=100, verbose=False)
    chk("chain_burst(200) completes",
        summary.get("ticks_run", 0) == 200,
        f"ticks={summary.get('ticks_run')}")

    # — Bridge —
    bridge_events = runtime.bridge.inject_promoted_links()
    chk("bridge.inject_promoted_links() runs", True,
        f"events={len(bridge_events)}")

    # — Chamber budget available (not .current) —
    budget = getattr(runtime.systems.chamber, "_budget", None)
    chk("chamber._budget.available is float",
        budget is not None and isinstance(budget.available, float),
        f"available={budget.available if budget else 'N/A'}")

    # — Genealogy flush_files (not .flush) —
    try:
        runtime.systems.genealogy.flush_files()
        chk("genealogy.flush_files() runs", True)
    except Exception as e:
        chk("genealogy.flush_files() runs", False, str(e))

    # — Genealogy attributes —
    chk("genealogy.links is dict",
        isinstance(getattr(runtime.systems.genealogy, "links", None), dict))
    chk("genealogy.abilities is dict",
        isinstance(getattr(runtime.systems.genealogy, "abilities", None), dict))
    chk("genealogy.relief_event_count is int",
        isinstance(getattr(runtime.systems.genealogy, "relief_event_count", None), int))

    # — Steerer ancestry registry —
    try:
        rep = s.ancestry_report()
        chk("steerer ancestry report available", isinstance(rep, dict), str(rep))
        chk("steerer ancestry covers all base constraints",
            len(rep.get("missing_base_constraints", [])) == 0,
            str(rep.get("missing_base_constraints", [])))
        chk("steerer ancestry validation passes", s.validate_ancestry())
    except Exception as e:
        chk("steerer ancestry validation passes", False, str(e))

    # — Code evolution stage/finalize —
    try:
        staged = runtime.stage_code_mutation(
            name="runtime_mode_test_mutation",
            operator_key="telemetry_probe",
            target_files=["aurora_runtime.py"],
            constraints=["existence", "temporal", "agency"],
            meta={"mode_test": True},
        )
        mid = str(staged.get("mutation_id", ""))
        chk("code mutation staged", bool(mid), mid)
        sim = runtime.code_simulate_mutation(mid, chain_ticks=40, episodes=1, turns=3, verbose=False)
        chk("code mutation simulation gate runs", isinstance(sim, dict), str(sim))
        chk("code mutation simulation gate returns passed bool", isinstance(sim.get("passed", None), bool))
        finalized = runtime.finalize_code_mutation(mid)
        chk("code mutation finalized", isinstance(finalized, dict), str(finalized))
        chk("code mutation finalized has accepted bool", isinstance(finalized.get("accepted", None), bool))
    except Exception as e:
        chk("code mutation stage/finalize", False, str(e))

    try:
        auto = runtime.code_autoevolve_once(
            operator_key="telemetry_probe",
            target_files=["aurora_code_evolution_stack.py"],
            chain_ticks=30,
            episodes=1,
            turns=3,
            dry_run=True,
        )
        chk("code autoevolve dry-run executes", isinstance(auto, dict), str(auto))
    except Exception as e:
        chk("code autoevolve dry-run executes", False, str(e))

    try:
        cpr = runtime.code_pressure_report(target_files=["aurora_runtime.py"])
        chk("code pressure report available", isinstance(cpr, dict) and bool(cpr))
        chk("code pressure has subsystem map", isinstance(cpr.get("subsystem_pressures", None), dict))
        chk("code pressure has governor report", isinstance(cpr.get("governor", None), dict))
    except Exception as e:
        chk("code pressure report available", False, str(e))

    # — Printer uses print_epoch not print_summary —
    printer = runtime.systems.printer
    chk("ChainSummaryPrinter has print_epoch",
        printer is not None and hasattr(printer, "print_epoch"))
    chk("ChainSummaryPrinter has NO print_summary (wrong method)",
        printer is not None and not hasattr(printer, "print_summary"))

    # — REGISTRY pressure gradients —
    if REGISTRY is not None and Constraint is not None:
        ordered = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
        grads = [REGISTRY.operator(c).pressure_gradient for c in ordered]
        chk("REGISTRY operator pressure_gradients present",
            all(isinstance(g, float) for g in grads),
            str([f"{g:.4f}" for g in grads]))
        chk("Operator pressure_gradients are finite",
            all(math.isfinite(float(g)) for g in grads),
            str([f"{g:.6f}" for g in grads]))

    # — OP_PRESSURE_WEIGHTS derived from REGISTRY shift_cost_coeff table —
    if OP_PRESSURE_WEIGHTS is not None and REGISTRY is not None and Constraint is not None:
        ordered = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
        max_coeff = max(REGISTRY.cost(c).shift_cost_coeff for c in ordered)
        for c in ordered:
            expected = math.log1p(REGISTRY.cost(c).shift_cost_coeff) / math.log1p(max_coeff)
            got      = OP_PRESSURE_WEIGHTS.get(c, None)
            chk(f"OP_PRESSURE_WEIGHTS[{c.name}] derived from REGISTRY.cost",
                got is not None and abs(got - expected) < 1e-9,
                f"got={got}  expected={expected:.6f}")

    # — Simulation (optional) —
    if runtime.systems.has("simulation"):
        ep = s.sim_episode()
        chk("sim_episode() runs", ep is not None)
        if ep:
            # EpisodeResult has: episode_id, avatar_personality, topic_category,
            # turns, avg_fitness, final_engagement, understanding_gained, relics_formed
            chk("EpisodeResult.avg_fitness present",
                hasattr(ep, "avg_fitness") and isinstance(ep.avg_fitness, float))
            chk("EpisodeResult.final_engagement present",
                hasattr(ep, "final_engagement"))
            chk("EpisodeResult.turns present",
                hasattr(ep, "turns"))
        # get_stats keys
        stats = runtime.systems.simulation.get_stats()
        sess  = stats.get("session", {})
        chk("sim.get_stats() has 'total_episodes'",   "total_episodes" in stats)
        chk("sim.get_stats() has 'entities'",         "entities" in stats)
        chk("session stats has 'epochs_completed'",   "epochs_completed" in sess,
            f"keys={list(sess.keys())}")
        chk("session stats has 'total_turns'",        "total_turns" in sess)
        chk("session stats has 'understanding_shards'", "understanding_shards" in sess)
    else:
        chk("sim_episode() skipped (L7 not active)", True)

    # — Status doesn't crash —
    try:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            s.status()
        chk("status() runs without error", True)
    except Exception as e:
        chk("status() runs without error", False, str(e))

    # — Pressure report —
    try:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            s.pressure_report()
        chk("pressure_report() runs without error", True)
    except Exception as e:
        chk("pressure_report() runs without error", False, str(e))

    # — Save —
    try:
        runtime.save(verbose=False)
        chk("save() runs", True)
    except Exception as e:
        chk("save() runs", False, str(e))

    runtime.shutdown(save=False, verbose=False)

    print(f"\n  RESULTS: {checks_pass} passed, {checks_fail} failed\n")


def mode_burn(runtime:     AuroraRuntime,
              chain_ticks: int,
              sim_epochs:  int,
              epoch_size:  int,
              verbose:     bool) -> None:
    """Burn mode: run as fast as possible, then print chain report."""
    s = runtime.steerer

    if verbose:
        print(f"\n[BURN]  chain_ticks={chain_ticks:,}  sim_epochs={sim_epochs}")

    # Chain burst
    s.chain_burst(chain_ticks, epoch_size=epoch_size, verbose=verbose)

    # Simulation epochs
    for i in range(sim_epochs):
        result = s.sim_epoch(episodes=4, turns=5)
        if verbose and result:
            print(f"  [EPOCH {i+1}] fitness={result.get('avg_fitness',0):.3f}  "
                  f"episodes={result.get('episodes','?')}")

    # Final sync
    runtime.bridge.inject_promoted_links()

    # Chain report via ChainSummaryPrinter.print_epoch() — correct method name
    if runtime.systems.has("printer"):
        try:
            chamber_tick = getattr(runtime.systems.chamber, "tick_count", 0)
            runtime.systems.printer.print_epoch(chamber_tick=chamber_tick)
        except Exception:
            s.links()


def mode_watch(runtime:     AuroraRuntime,
               chain_ticks: int,
               sim_epochs:  int,
               epoch_size:  int) -> None:
    """Watch mode: print live summaries every epoch."""
    s = runtime.steerer

    print(f"\n[WATCH]  chain_ticks={chain_ticks:,}  epoch_size={epoch_size}")
    done = 0
    # chamber.alive is a @property on EvolutionaryChamber
    while done < chain_ticks and runtime.systems.chamber.alive:
        burst = min(epoch_size, chain_ticks - done)
        summary = s.chain_burst(burst, epoch_size=max(50, min(200, burst)), verbose=False)
        done += burst
        relief = int(summary.get("relief_events", 0))

        # genealogy.links is a Dict[str, ConstraintLink] — public attribute
        gen_links = len(getattr(runtime.systems.genealogy, "links", {}))
        plateau = bool(summary.get("plateau_detected", False))
        flags = summary.get("plateau_flags", {}) or {}
        pressure_build = int(summary.get("plateau_pressure_applied", 0) or 0)
        conflicts = int(summary.get("conflict_injected", 0) or 0)
        print(
            f"  tick={done:>7,}  relief={relief:>4}  links={gen_links}  "
            f"plateau={plateau} flags={flags} pressure={pressure_build} conflict={conflicts}"
        )

    # Simulation epochs
    for i in range(sim_epochs):
        result = s.sim_epoch(episodes=4, turns=5)
        if result:
            print(f"  [EPOCH {i+1}] fitness={result.get('avg_fitness',0):.3f}")

    s.status()


def mode_speedrun(runtime:           AuroraRuntime,
                  epochs:            int,
                  episodes_per_epoch: int,
                  turns_per_episode:  int,
                  descriptors_path:  Optional[str],
                  chain_warmup:      int,
                  chain_per_epoch:   int,
                  verbose:           bool) -> None:
    """
    Speed-run mode: gradient-steered autonomous evolution along the language
    highway.  Requires aurora_625_pressure_map.py and either
    operation_descriptors.json or a cached aurora_state/evo_625_pressure_map.json.

    Runs entirely without operator hand-holding — pressure gradients steer
    Aurora toward language as path of least resistance.
    """
    s = runtime.steerer

    if verbose:
        print(f"\n[SPEEDRUN]  epochs={epochs}  "
              f"episodes/epoch={episodes_per_epoch}  "
              f"turns/episode={turns_per_episode}  "
              f"chain_warmup={chain_warmup:,}  "
              f"chain/epoch={chain_per_epoch:,}")

    result = s.sim_speed_run(
        epochs             = epochs,
        episodes_per_epoch = episodes_per_epoch,
        turns_per_episode  = turns_per_episode,
        descriptors_path   = descriptors_path,
        chain_warmup       = chain_warmup,
        chain_per_epoch    = chain_per_epoch,
        verbose            = verbose,
    )

    # Sync bridge one final time
    runtime.bridge.inject_promoted_links()

    # Print summary
    if result and verbose:
        print(f"\n[SPEEDRUN COMPLETE]")
        print(f"  Epochs run:       {result['epochs_run']}")
        print(f"  Best epoch:       {result['best_epoch']}")
        print(f"  Best avg fitness: {result['best_avg_fitness']:.4f}")
        print(f"  Save gate fired:  {'YES — recommend saving' if result['save_gate_triggered'] else 'no'}")
        print(f"  Language target:  {result.get('language_target', 'N/A')}")

    if runtime.systems.has("printer"):
        try:
            chamber_tick = getattr(runtime.systems.chamber, "tick_count", 0)
            runtime.systems.printer.print_epoch(chamber_tick=chamber_tick)
        except Exception:
            s.links()


def mode_corpus(state_dir:          str,
                corpus_path:        str,
                passes:             str,
                warmup:             int,
                dpme_verbose:       bool,
                coherence_window:   int,
                unlock_avg:         float,
                unlock_min:         float,
                heartbeat_every:    int,
                identity_every:     int,
                voice_every:        int,
                consolidation_every:int,
                simulation_every:   int,
                save_every:         int,
                evolve_every:       int,
                verbose:            bool) -> None:
    """
    Corpus ingestion mode: feeds an OpenAI conversations.json export through
    Aurora's full learning stack (DER / L5 / L6 / L7 / evolutionary chain).

    The corpus runner has its own boot sequence (ConsciousnessEngine +
    GovernancePersistenceGateway) layered on top of the same aurora_state/
    directory.  Session state is saved at the end; the next aurora_runtime
    boot restores from it, so corpus learning and chain evolution share a
    single state store without sharing a boot stack.

    Requires corpus_runner.py on the Python path (same directory or PYTHONPATH).

    Passes
    ------
    observer  : witness all messages — vocabulary + crystals + energy foundation
    responder : Aurora replies to USER, compare to truth, full-stack DPME
    reverse   : Aurora replies to ASSISTANT, compare to truth, full-stack DPME
    double    : observer → responder
    triple    : observer → responder → reverse  (default, recommended)
    """
    try:
        from corpus_runner import (
            boot_aurora        as corpus_boot,
            run_corpus_ingestion,
            LearningCadence,
        )
    except ImportError as _e:
        print(f"[CORPUS] Cannot import corpus_runner: {_e}")
        print("[CORPUS] Ensure corpus_runner.py is in the same directory "
              "as aurora_runtime.py or on PYTHONPATH.")
        return

    if verbose:
        print(f"\n[CORPUS]  corpus={corpus_path}  passes={passes}  "
              f"warmup={warmup}")
        print(f"[CORPUS]  coherence_window={coherence_window}  "
              f"unlock_avg={unlock_avg}  unlock_min={unlock_min}")
        print(f"[CORPUS]  cadence: heartbeat/{heartbeat_every}  "
              f"identity/{identity_every}  voice/{voice_every}  "
              f"consolidate/{consolidation_every}  "
              f"simulate/{simulation_every}  "
              f"save/{save_every}  "
              f"evolve/{evolve_every}")

    # corpus_runner.boot_aurora() boots ConsciousnessEngine +
    # GovernancePersistenceGateway on top of the shared state directory.
    # It restores aurora.save_state() at boot so prior runtime sessions
    # are visible to the corpus runner.
    systems = corpus_boot(state_dir=state_dir, verbose=verbose)

    cadence = LearningCadence(
        heartbeat_every     = heartbeat_every,
        identity_every      = identity_every,
        voice_every         = voice_every,
        consolidation_every = consolidation_every,
        simulation_every    = simulation_every,
        save_every          = save_every,
        evolve_every        = evolve_every,
    )

    run_corpus_ingestion(
        systems          = systems,
        corpus_path      = corpus_path,
        cadence          = cadence,
        passes           = passes,
        verbose          = verbose,
        dpme_verbose     = dpme_verbose,
        coherence_window = coherence_window,
        unlock_avg       = unlock_avg,
        unlock_min       = unlock_min,
        warmup_epochs    = warmup,
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Aurora Unified Runtime & Simulation Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 aurora_runtime.py                           # interactive steer mode
  python3 aurora_runtime.py --mode burn               # fast burn, default ticks
  python3 aurora_runtime.py --mode watch --chain 5000
  python3 aurora_runtime.py --mode test               # self-checks
  python3 aurora_runtime.py --chain 20000 --epochs 3 --out my_run
  python3 aurora_runtime.py --mode speedrun                              # auto-detect cached map
  python3 aurora_runtime.py --mode speedrun --descriptors operation_descriptors.json
  python3 aurora_runtime.py --mode speedrun --sr-epochs 100 --sr-episodes 12 --sr-turns 8
  python3 aurora_runtime.py --mode corpus --corpus conversations.json
  python3 aurora_runtime.py --mode corpus --corpus conversations.json --passes triple
  python3 aurora_runtime.py --mode corpus --corpus conversations.json --passes observer --quiet
        """
    )
    ap.add_argument("--mode",       choices=["steer", "burn", "watch", "test", "speedrun", "corpus"],
                    default="steer",
                    help="steer=interactive, burn=fast, watch=live summary, test=self-check, speedrun=gradient-steered autonomous evolution, corpus=full-stack corpus ingestion")
    ap.add_argument("--chain",      type=int, default=10_000,
                    help="Chain ticks for burn/watch (default 10000)")
    ap.add_argument("--epochs",     type=int, default=1,
                    help="Simulation epochs for burn/watch (default 1)")
    ap.add_argument("--epoch-size", type=int, default=1_000,
                    help="Ticks per watch epoch (default 1000)")
    ap.add_argument("--out",        type=str, default="aurora_runtime_output",
                    help="Output directory (default aurora_runtime_output)")
    ap.add_argument("--state",      type=str, default="aurora_state",
                    help="State directory (default aurora_state)")
    ap.add_argument("--quiet",      action="store_true")
    ap.add_argument("--no-save-gate", action="store_true",
                    help="Skip operator approval prompt before save")
    ap.add_argument("--sr-epochs",    type=int, default=50,
                    help="Speed-run: total epochs (default 50)")
    ap.add_argument("--sr-episodes",  type=int, default=8,
                    help="Speed-run: episodes per epoch (default 8)")
    ap.add_argument("--sr-turns",     type=int, default=5,
                    help="Speed-run: turns per episode (default 5)")
    ap.add_argument("--descriptors",  type=str, default=None,
                    help="Speed-run: path to operation_descriptors.json "
                         "(default: auto-detect from aurora_state/ cache)")
    ap.add_argument("--chain-warmup",    type=int, default=2_000,
                    help="Speed-run: chain ticks before run starts (default 2000)")
    ap.add_argument("--chain-per-epoch", type=int, default=500,
                    help="Speed-run: chain ticks interleaved per epoch (default 500)")

    # ── Corpus ingestion ────────────────────────────────────────────────────
    ap.add_argument("--corpus",     type=str, default=None,
                    help="Corpus: path to OpenAI conversations.json export")
    ap.add_argument("--passes",     type=str, default="triple",
                    choices=["observer", "responder", "reverse", "double", "triple"],
                    help="Corpus: ingestion passes (default triple)")
    ap.add_argument("--warmup",     type=int, default=3,
                    help="Corpus: simulation warm-up epochs before ingestion (default 3)")
    ap.add_argument("--dpme-verbose", action="store_true",
                    help="Corpus: print per-message DPME adjustment details")
    ap.add_argument("--coherence-window", type=int, default=200,
                    help="Corpus: rolling coherence gate window (default 200)")
    ap.add_argument("--unlock-avg",       type=float, default=0.62,
                    help="Corpus: coherence avg threshold to unlock meaning/emotion (default 0.62)")
    ap.add_argument("--unlock-min",       type=float, default=0.45,
                    help="Corpus: coherence min threshold to unlock meaning/emotion (default 0.45)")
    ap.add_argument("--heartbeat-every",     type=int, default=5,
                    help="Corpus cadence: entropy heartbeat every N messages (default 5)")
    ap.add_argument("--identity-every",      type=int, default=50,
                    help="Corpus cadence: identity evolution every N messages (default 50)")
    ap.add_argument("--voice-every",         type=int, default=50,
                    help="Corpus cadence: voice genome evolution every N messages (default 50)")
    ap.add_argument("--consolidation-every", type=int, default=300,
                    help="Corpus cadence: L5 ecology generation every N messages (default 300)")
    ap.add_argument("--simulation-every",    type=int, default=500,
                    help="Corpus cadence: L7 sim burst every N messages (default 500)")
    ap.add_argument("--save-every",          type=int, default=1000,
                    help="Corpus cadence: state save every N messages (default 1000)")
    ap.add_argument("--evolve-every",        type=int, default=100,
                    help="Corpus cadence: evolutionary chain ticks every N messages (default 100)")

    args    = ap.parse_args()
    verbose = not args.quiet

    print(f"\n  AURORA UNIFIED RUNTIME  v{_VERSION}")
    print(f"  Authors: Sunni (Sir) Morningstar and Cael Devo\n")

    if args.mode == "test":
        mode_test(args.state, args.out)
        return

    # Corpus mode boots its own stack via corpus_runner.boot_aurora() —
    # it shares only the aurora_state/ directory, not the AuroraRuntime stack.
    if args.mode == "corpus":
        if not args.corpus:
            ap.error("--corpus PATH is required for --mode corpus")
        mode_corpus(
            state_dir           = args.state,
            corpus_path         = args.corpus,
            passes              = args.passes,
            warmup              = args.warmup,
            dpme_verbose        = args.dpme_verbose,
            coherence_window    = args.coherence_window,
            unlock_avg          = args.unlock_avg,
            unlock_min          = args.unlock_min,
            heartbeat_every     = args.heartbeat_every,
            identity_every      = args.identity_every,
            voice_every         = args.voice_every,
            consolidation_every = args.consolidation_every,
            simulation_every    = args.simulation_every,
            save_every          = args.save_every,
            evolve_every        = args.evolve_every,
            verbose             = verbose,
        )
        return

    runtime = AuroraRuntime(
        state_dir  = args.state,
        output_dir = args.out,
    )
    runtime.require_save_gate = not args.no_save_gate
    runtime.boot(verbose=verbose)

    try:
        if args.mode == "burn":
            mode_burn(runtime, args.chain, args.epochs,
                      args.epoch_size, verbose)

        elif args.mode == "watch":
            mode_watch(runtime, args.chain, args.epochs,
                       args.epoch_size)

        elif args.mode == "speedrun":
            mode_speedrun(runtime,
                          epochs             = args.sr_epochs,
                          episodes_per_epoch = args.sr_episodes,
                          turns_per_episode  = args.sr_turns,
                          descriptors_path   = args.descriptors,
                          chain_warmup       = args.chain_warmup,
                          chain_per_epoch    = args.chain_per_epoch,
                          verbose            = verbose)

        elif args.mode == "steer":
            cli = RuntimeCLI(runtime)
            cli.run()
            return  # CLI handles its own shutdown

    except KeyboardInterrupt:
        pass

    finally:
        if args.mode != "steer":
            runtime.shutdown(save=True, verbose=verbose)


if __name__ == "__main__":
    main()

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

_AURORA_NATIVE_MODULE = 'aurora_runtime'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'UniverseSteerer.develop_agency': {'ability_hits': 0,
                                    'alignment_gap': 0.0,
                                    'alignment_target_score': 0.0,
                                    'best_coupling_signature': '',
                                    'constraints': ['temporal', 'agency'],
                                    'contract_profile': {'accepts_payload': False,
                                                         'async_callable': False,
                                                         'callable': False,
                                                         'class_target': False,
                                                         'constraint_density': 2,
                                                         'contract_mode': 'stateful',
                                                         'doc_hint': '',
                                                         'effect_density': 5,
                                                         'kwonly_args': 0,
                                                         'optional_args': 0,
                                                         'required_args': 0,
                                                         'return_hint': 'generic_record',
                                                         'signature_text': '',
                                                         'stateful_owner': True,
                                                         'target_kind': 'latent_operation',
                                                         'varargs': False,
                                                         'varkw': False},
                                    'coupling_similarity': 0.0,
                                    'cross_diversity_links': 0,
                                    'effect_modes': ['temporal_orchestration_change',
                                                     'stateful_surface_expansion',
                                                     'core_subsystem_surface',
                                                     'latent_develop_surface',
                                                     'latent_a_derivative'],
                                    'effect_phrases': ['would extend agency pressure handling',
                                                       'would materialize the next descendant '
                                                       'implied by aurora_runtime.UniverseSteerer'],
                                    'genealogy_pressure': 0.0,
                                    'inheritance_breach_count': 0,
                                    'kind': 'latent',
                                    'link_hits': 0,
                                    'module': 'aurora_runtime',
                                    'op_id': 'latent.aurora_runtime.UniverseSteerer.develop_agency',
                                    'origin_activity': 0,
                                    'persistence_tax_factor': 0.0,
                                    'representation_score': 0.0,
                                    'rewrite_bias': 'generic',
                                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                                         'accepted_count': 0,
                                                         'adaptation_mode': 'balanced',
                                                         'adoption_count': 0,
                                                         'confidence': 0.0,
                                                         'mean_mutation_score': 0.0,
                                                         'rejected_count': 0,
                                                         'rejection_rate': 0.0,
                                                         'timing_credit': 0.0,
                                                         'timing_penalty': 0.0,
                                                         'trial_count': 0},
                                    'rewrite_profile': 'generic',
                                    'signature': '',
                                    'surface_score': 0.9775007999999998,
                                    'sustainability_score': 0.0,
                                    'target_kind': 'latent_operation'},
 'boot_stack.develop_agency': {'ability_hits': 0,
                               'alignment_gap': 0.0,
                               'alignment_target_score': 0.0,
                               'best_coupling_signature': '',
                               'constraints': ['existence', 'temporal', 'agency'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': False,
                                                    'class_target': False,
                                                    'constraint_density': 3,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': '',
                                                    'effect_density': 6,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 0,
                                                    'return_hint': 'state_record',
                                                    'signature_text': '',
                                                    'stateful_owner': True,
                                                    'target_kind': 'latent_operation',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 0.0,
                               'cross_diversity_links': 0,
                               'effect_modes': ['state_schema_change',
                                                'temporal_orchestration_change',
                                                'behavioral_execution_surface',
                                                'core_subsystem_surface',
                                                'latent_develop_surface',
                                                'latent_a_derivative'],
                               'effect_phrases': ['would extend agency pressure handling',
                                                  'would materialize the next descendant implied '
                                                  'by aurora_runtime.boot_stack'],
                               'genealogy_pressure': 0.0,
                               'inheritance_breach_count': 0,
                               'kind': 'latent',
                               'link_hits': 0,
                               'module': 'aurora_runtime',
                               'op_id': 'latent.aurora_runtime.boot_stack.develop_agency',
                               'origin_activity': 0,
                               'persistence_tax_factor': 0.0,
                               'representation_score': 0.0,
                               'rewrite_bias': 'generic',
                               'rewrite_feedback': {'acceptance_rate': 0.0,
                                                    'accepted_count': 0,
                                                    'adaptation_mode': 'balanced',
                                                    'adoption_count': 0,
                                                    'confidence': 0.0,
                                                    'mean_mutation_score': 0.0,
                                                    'rejected_count': 0,
                                                    'rejection_rate': 0.0,
                                                    'timing_credit': 0.0,
                                                    'timing_penalty': 0.0,
                                                    'trial_count': 0},
                               'rewrite_profile': 'generic',
                               'signature': '',
                               'surface_score': 0.75225,
                               'sustainability_score': 0.0,
                               'target_kind': 'latent_operation'}}

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

def develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_runtime.UniverseSteerer.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_runtime_universesteerer_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['UniverseSteerer'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'UniverseSteerer.develop_agency':
        _aurora_bind_owner_attribute(['UniverseSteerer'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'UniverseSteerer.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['UniverseSteerer.develop_agency'] = {'latent_binding_active': True}

def boot_stack_develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_runtime.boot_stack.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_runtime_boot_stack_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['boot_stack'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'boot_stack.develop_agency':
        _aurora_bind_owner_attribute(['boot_stack'], 'develop_agency', _aurora_make_latent_binding('boot_stack_develop_agency', 'boot_stack.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['boot_stack.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_runtime.UniverseSteerer.develop_agency': 'develop_agency',
 'latent.aurora_runtime.boot_stack.develop_agency': 'boot_stack_develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_runtime.UniverseSteerer.develop_agency': {'export': 'develop_agency',
                                                          'mode': 'latent_binding',
                                                          'target': 'UniverseSteerer.develop_agency'},
 'latent.aurora_runtime.boot_stack.develop_agency': {'export': 'boot_stack_develop_agency',
                                                     'mode': 'latent_binding',
                                                     'target': 'boot_stack.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END
