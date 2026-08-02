#!/usr/bin/env python3
"""
AURORA SUPPORT STACK (Consolidated Facade)
=========================================
Consolidates non-core support modules used by canonical runtime layers.
"""
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
# Authors: Sunni (Sir) Morningstar & Cael Devo

# Parser
from aurora_internal.aurora_utterance_parser import UtteranceParser, parse_utterance

# Identity persistence surface
from aurora_internal.aurora_identity_persistence import (
    CoreRelationalIdentity,
    EnhancedStatePersistence,
    ConversationMemory,
    OETSPersistence,
    seed_identity_into_oets,
    seed_identity_into_dna,
)

# Backward compatibility for older boot paths that still import the legacy name.
StatePersistence = EnhancedStatePersistence

# Governance / persistence / device-sync classes
try:
    from aurora_governance_persistence_gateway import AuroraStateSnapshot
    from aurora_persistence_utils import DeviceAwareness, RcloneInterface, DriveSync
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_support_stack.py:29",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 29, "source_file": "aurora_support_stack.py"},
    )
    AuroraStateSnapshot = None
    DeviceAwareness     = None
    RcloneInterface     = None
    DriveSync           = None

# Semantic scaffolding / OETS
try:
    from aurora_internal.aurora_ontological_scaffolding import (
        OntologicalScaffoldingEngine,
        ResearchResult,
        RelationType,
    )
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_support_stack.py:42",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 42, "source_file": "aurora_support_stack.py"},
    )
    OntologicalScaffoldingEngine = None
    ResearchResult = None
    RelationType = None

# Language-state expression evolution
try:
    from aurora_internal.aurora_language_state import (
        ExpressionEvolutionOrchestra,
        LSVMetrics,
    )
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_support_stack.py:53",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 53, "source_file": "aurora_support_stack.py"},
    )
    ExpressionEvolutionOrchestra = None
    LSVMetrics = None

# Relational comparison engine (differential meaning formation)
try:
    from aurora_internal.aurora_relational_comparison import (
        RelationalComparisonEngine,
        RelationalDelta,
    )
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_support_stack.py:63",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 63, "source_file": "aurora_support_stack.py"},
    )
    RelationalComparisonEngine = None
    RelationalDelta = None

# Noncomp manifold compiler compatibility re-export
try:
    from aurora_noncomp_manifold_compiler import *  # noqa: F401,F403
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_support_stack.py:70",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 70, "source_file": "aurora_support_stack.py"},
    )
    pass

__all__ = [
    "UtteranceParser",
    "parse_utterance",
    "CoreRelationalIdentity",
    "EnhancedStatePersistence",
    "StatePersistence",
    "ConversationMemory",
    "OETSPersistence",
    "seed_identity_into_oets",
    "seed_identity_into_dna",
    "OntologicalScaffoldingEngine",
    "ResearchResult",
    "RelationType",
    "ExpressionEvolutionOrchestra",
    "LSVMetrics",
    "AuroraStateSnapshot",
    "DeviceAwareness",
    "RcloneInterface",
    "DriveSync",
    "RelationalComparisonEngine",
    "RelationalDelta",
]
