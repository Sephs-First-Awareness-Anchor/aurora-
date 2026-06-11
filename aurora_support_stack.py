#!/usr/bin/env python3
"""
AURORA SUPPORT STACK (Consolidated Facade)
=========================================
Consolidates non-core support modules used by canonical runtime layers.
"""
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
except Exception:
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
except Exception:
    OntologicalScaffoldingEngine = None
    ResearchResult = None
    RelationType = None

# Language-state expression evolution
try:
    from aurora_internal.aurora_language_state import (
        ExpressionEvolutionOrchestra,
        LSVMetrics,
    )
except Exception:
    ExpressionEvolutionOrchestra = None
    LSVMetrics = None

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
]
