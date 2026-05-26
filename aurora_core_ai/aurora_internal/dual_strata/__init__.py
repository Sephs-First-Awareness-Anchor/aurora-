"""
Dual-strata cognition primitives for the experimental Aurora strata tree.
"""

from .crest import Crest, CrestBundle
from .conscious_frame import ConsciousFrame
from .contextual_overlay import ContextualOverlay
from .dce_bridge import DualStrataBridge, DualStrataSnapshot
from .downward_traversal import expand_crest
from .micro_reasoning import MicroReasoningHypothesis, generate_micro_reasoning
from .prediction_field import PredictionPayload, PredictionSignal, build_prediction_signal
from .subsurface_state import SubsurfaceState
from .subsystem_waveforms import emit_subsystem_crests

__all__ = [
    "Crest",
    "CrestBundle",
    "ConsciousFrame",
    "ContextualOverlay",
    "DualStrataBridge",
    "DualStrataSnapshot",
    "MicroReasoningHypothesis",
    "PredictionPayload",
    "PredictionSignal",
    "SubsurfaceState",
    "build_prediction_signal",
    "emit_subsystem_crests",
    "expand_crest",
    "generate_micro_reasoning",
]
