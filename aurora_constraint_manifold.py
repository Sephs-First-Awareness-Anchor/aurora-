#!/usr/bin/env python3
"""Compatibility + consolidation shim for Aurora constraint manifold."""

from aurora_internal.aurora_constraint_manifold_patched import *  # noqa: F401,F403

# Engine-authoritative versions override the patched equivalents
from aurora_constraint_engine import (  # noqa: F401
    ConstraintVector,
    ManifoldViolation,
)
