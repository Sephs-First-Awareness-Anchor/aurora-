#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Shared perception primitive types used by both expression_perception and hardware_io."""

import time
import numpy as np
from enum import Enum, auto
from typing import Dict
from dataclasses import dataclass, field


class PatternType(Enum):
    """Types of patterns Aurora can perceive."""
    TEMPORAL = auto()
    SPATIAL = auto()
    EMOTIONAL = auto()
    STRUCTURAL = auto()
    ABSTRACT = auto()


@dataclass
class DimensionalPattern:
    """A detected pattern with dimensional physics vector."""
    pattern_id: str
    pattern_type: PatternType
    salience: float
    complexity: float
    features: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def physics_vector(self) -> np.ndarray:
        base = [self.salience, self.complexity]
        feat_vals = list(self.features.values())[:8]
        feat_vals += [0.0] * (8 - len(feat_vals))
        vec = np.array(base + feat_vals, dtype=float)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 1e-9 else vec
