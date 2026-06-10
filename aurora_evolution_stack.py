#!/usr/bin/env python3
"""
AURORA EVOLUTION STACK (Combined Facade)
========================================
Consolidated access layer for genealogy/evolution chain primitives.

Purpose:
- Provide one canonical import surface for genealogy types and reporters.
- Keep existing constraint_genealogy implementation unchanged.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from aurora_internal.constraint_genealogy import (
    ConstraintGenealogyLogger,
    GenealogyConfig,
    ChainSummaryPrinter,
    AbilityProfile,
    TraceItem,
    PressureVec,
    ReliefRecord,
    ConstraintLink,
    PairStats,
    GenealogyDilationGovernor,
)

__all__ = [
    "ConstraintGenealogyLogger",
    "GenealogyConfig",
    "ChainSummaryPrinter",
    "AbilityProfile",
    "TraceItem",
    "PressureVec",
    "ReliefRecord",
    "ConstraintLink",
    "PairStats",
    "GenealogyDilationGovernor",
]
