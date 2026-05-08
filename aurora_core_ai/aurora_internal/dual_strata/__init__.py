"""
Dual-strata cognition primitives for the experimental Aurora strata tree.
"""

from .conscious_frame import ConsciousFrame
from .dce_bridge import DualStrataBridge, DualStrataSnapshot
from .micro_reasoning import MicroReasoningHypothesis, generate_micro_reasoning
from .prediction_field import PredictionPayload, PredictionSignal, build_prediction_signal
from .subsurface_state import SubsurfaceState

__all__ = [
    "ConsciousFrame",
    "DualStrataBridge",
    "DualStrataSnapshot",
    "MicroReasoningHypothesis",
    "PredictionPayload",
    "PredictionSignal",
    "SubsurfaceState",
    "build_prediction_signal",
    "generate_micro_reasoning",
]
