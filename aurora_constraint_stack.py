#!/usr/bin/env python3
"""
AURORA CONSTRAINT STACK (Combined Facade)
=========================================
Consolidated access layer for constraint pressure + diff/cost scoring.

Purpose:
- Provide one canonical import surface for DifferenceBuffer + CostDiffScore.
- Preserve backward compatibility with legacy modules.
"""

from aurora_internal.aurora_difference_buffer import (
    DifferenceHistoryBuffer,
    DifferenceSnapshot,
    make_difference_buffer,
)

from aurora_internal.aurora_cost_diff_score import (
    OP_PRESSURE_WEIGHTS,
    OPPOSED_OPERATOR_SCALES,
    TICK_PARTICIPATION_WEIGHTS,
    OPERATOR_PRESSURE_NAMES,
    MAX_AMPLIFIER,
    CostDiffScore,
    cross_dim_amplifier,
    dominant_pressure_axis,
    per_operator_pressure,
    pressure_mutation_state,
    pressure_description,
    score_for_variant_moral_weight,
    score_from_cost,
)

__all__ = [
    "DifferenceHistoryBuffer",
    "DifferenceSnapshot",
    "make_difference_buffer",
    "OP_PRESSURE_WEIGHTS",
    "OPPOSED_OPERATOR_SCALES",
    "TICK_PARTICIPATION_WEIGHTS",
    "OPERATOR_PRESSURE_NAMES",
    "MAX_AMPLIFIER",
    "CostDiffScore",
    "cross_dim_amplifier",
    "dominant_pressure_axis",
    "per_operator_pressure",
    "pressure_mutation_state",
    "pressure_description",
    "score_for_variant_moral_weight",
    "score_from_cost",
]
