"""
Dual-strata cognition primitives for the experimental Aurora strata tree.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from .crest import Crest, CrestBundle
from .conscious_frame import ConsciousFrame
from .contextual_overlay import ContextualOverlay
from .dce_bridge import DualStrataBridge, DualStrataSnapshot
from .downward_traversal import expand_crest
from .micro_reasoning import MicroReasoningHypothesis, generate_micro_reasoning
from .prediction_field import PredictionPayload, PredictionSignal, build_prediction_signal
from .subsurface_state import SubsurfaceState
from .subsystem_waveforms import emit_subsystem_crests
from .activation_field import ActivationField, extract_seeds_from_systems
from .predictive_stager import PredictiveStager
from .sensory_observation import (
    SensoryObservationPacket,
    build_sensory_observation_packet,
    observation_to_unified_turn,
    sensory_gate_state_update,
)

__all__ = [
    "ActivationField",
    "Crest",
    "CrestBundle",
    "ConsciousFrame",
    "ContextualOverlay",
    "DualStrataBridge",
    "DualStrataSnapshot",
    "MicroReasoningHypothesis",
    "PredictionPayload",
    "PredictionSignal",
    "PredictiveStager",
    "SensoryObservationPacket",
    "SubsurfaceState",
    "build_prediction_signal",
    "build_sensory_observation_packet",
    "emit_subsystem_crests",
    "expand_crest",
    "extract_seeds_from_systems",
    "generate_micro_reasoning",
    "observation_to_unified_turn",
    "sensory_gate_state_update",
]
