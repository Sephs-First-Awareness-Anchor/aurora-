"""
I-state field operations — the instruction set of Aurora's Constraint Physics Machine.

Each I-state × recursion level pair defines a specific operation on the active crystal
cell. Operations are derived from constraint physics semantics — not imposed arbitrarily.

  I_IS    (X+)  ASSERT    — confirm existence; contribute toward crystal promotion
  I_ISNT  (X−)  NEGATE    — pressure against existence; raise boundary questioning
  I_CAN   (T+)  EXTEND    — temporal continuation; deepen temporal grounding
  I_CANNOT(T−)  BLOCK     — block continuation; hold propagation at current cell
  I_DO    (N+)  ACTIVATE  — energy assertion; raise N-axis intensity at cell
  I_DONOT (N−)  RESIST    — energy resistance; raise constraint cost of this cell
  I_SAW   (B+)  GROUND    — boundary definition; contribute is_grounded
  I_SOUGHT(B−)  SEARCH    — boundary seeking; flag cell as under active search
  I_DID   (A+)  COMMIT    — agency completion; mark cell as acted upon
  I_DIDNT (A−)  WITHHOLD  — agency withheld; reduce drive at this cell

Recursion scope — matches the IVM sea-anemone model:
  SURFACE  (0) — local: affects only the current cell
  SHALLOW  (1) — near: radiates via axis coupling to immediate neighbors
  MODERATE (2) — coupled: full coupling-physics propagation
  DEEP     (3) — axial: affects all cells sharing the dominant axis value
  CORE     (4) — global: field-wide operation across all cells

Negative I-states are PRESSURE, not absence. I_ISNT is active constraint tension on
the X axis — it operates on the cell just as powerfully as I_IS, in the opposing
direction. This is why all 10 states are here, not just the 5 positive ones.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Axis coupling weights — read-only physics (from aurora_constraint_evolutionary_sim)
# ---------------------------------------------------------------------------

_COUPLING: Dict[str, Dict[str, float]] = {
    "X": {"T": 0.30, "B": 0.20},
    "T": {"X": 0.25, "A": 0.20},
    "N": {"B": 0.35, "T": 0.20, "X": 0.15},
    "B": {"N": 0.30, "A": 0.25},
    "A": {"T": 0.20, "B": 0.25, "N": 0.15},
}

# ---------------------------------------------------------------------------
# I-state operation enum
# ---------------------------------------------------------------------------

class IStateOp(Enum):
    ASSERT   = "I_IS"
    NEGATE   = "I_ISNT"
    EXTEND   = "I_CAN"
    BLOCK    = "I_CANNOT"
    ACTIVATE = "I_DO"
    RESIST   = "I_DONOT"
    GROUND   = "I_SAW"
    SEARCH   = "I_SOUGHT"
    COMMIT   = "I_DID"
    WITHHOLD = "I_DIDNT"


_ISTATE_MAP: Dict[str, Tuple[IStateOp, str]] = {
    'I_IS':      (IStateOp.ASSERT,    'X'),
    'I_ISNT':    (IStateOp.NEGATE,    'X'),
    'I_CAN':     (IStateOp.EXTEND,    'T'),
    'I_CANNOT':  (IStateOp.BLOCK,     'T'),
    'I_DO':      (IStateOp.ACTIVATE,  'N'),
    'I_DONOT':   (IStateOp.RESIST,    'N'),
    'I_SAW':     (IStateOp.GROUND,    'B'),
    'I_SOUGHT':  (IStateOp.SEARCH,    'B'),
    'I_DID':     (IStateOp.COMMIT,    'A'),
    'I_DIDNT':   (IStateOp.WITHHOLD,  'A'),
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FieldOperation:
    istate_op:       IStateOp
    recursion_level: int          # 0–4
    axis:            str          # dominant axis: X/T/N/B/A
    intensity:       float        # 0.0–1.0


@dataclass
class PropagationEvent:
    axis:    str
    weight:  float   # coupling_weight × intensity


@dataclass
class OperationResult:
    op:            FieldOperation
    cell_address:  Tuple[float, ...]
    delta:         Dict[str, float]  # field name → value change
    propagated_to: List[PropagationEvent]
    success:       bool


# ---------------------------------------------------------------------------
# CPM state namespace inside crystal.current_overlay
# ---------------------------------------------------------------------------

_CPM_KEY = '_cpm'

def _cpm_state(crystal: Any) -> Dict[str, Any]:
    """Return (creating if absent) the CPM namespace inside the crystal overlay."""
    overlay: Dict[str, Any] = getattr(crystal, 'current_overlay', None)
    if overlay is None:
        return {}
    if _CPM_KEY not in overlay:
        overlay[_CPM_KEY] = {
            'assert_count':    0,
            'ground_count':    0,
            'activate_energy': 0.0,
            'extend_temporal': 0.0,
            'commit_agency':   0.0,
            'negate_pressure': 0.0,
            'block_count':     0,
            'resist_cost':     0.0,
            'search_count':    0,
            'withhold_count':  0,
        }
    return overlay[_CPM_KEY]


# ---------------------------------------------------------------------------
# Core operation application
# ---------------------------------------------------------------------------

def apply_operation(op: FieldOperation, crystal: Any, registry: Any) -> OperationResult:
    """
    Apply a FieldOperation to the given crystal cell.
    All CPM state is written to crystal.current_overlay['_cpm'] to avoid
    conflicting with existing overlay keys used by other subsystems.
    Propagation events are returned; the caller decides whether to apply them
    to neighboring cells.
    """
    if crystal is None:
        return OperationResult(op=op, cell_address=(), delta={},
                               propagated_to=[], success=False)

    cpm = _cpm_state(crystal)
    delta: Dict[str, float] = {}
    scale = op.intensity

    if op.istate_op == IStateOp.ASSERT:
        # I_IS: confirm existence — each assertion contributes toward crystal promotion
        cpm['assert_count'] += 1
        delta['assert_count'] = 1

    elif op.istate_op == IStateOp.GROUND:
        # I_SAW: boundary definition — contributes is_grounded signal
        cpm['ground_count'] += 1
        delta['ground_count'] = 1

    elif op.istate_op == IStateOp.ACTIVATE:
        # I_DO: energy assertion — raise N-axis energy at this cell
        inc = 0.10 * scale
        cpm['activate_energy'] = min(1.0, cpm['activate_energy'] + inc)
        delta['activate_energy'] = inc

    elif op.istate_op == IStateOp.EXTEND:
        # I_CAN: temporal continuation — deepen temporal grounding
        inc = 0.10 * scale
        cpm['extend_temporal'] = min(1.0, cpm['extend_temporal'] + inc)
        delta['extend_temporal'] = inc

    elif op.istate_op == IStateOp.COMMIT:
        # I_DID: agency completion — mark cell as acted upon
        inc = 0.10 * scale
        cpm['commit_agency'] = min(1.0, cpm['commit_agency'] + inc)
        delta['commit_agency'] = inc

    elif op.istate_op == IStateOp.NEGATE:
        # I_ISNT: existence pressure — active tension, not absence
        inc = 0.05 * scale
        cpm['negate_pressure'] = min(1.0, cpm['negate_pressure'] + inc)
        delta['negate_pressure'] = inc

    elif op.istate_op == IStateOp.BLOCK:
        # I_CANNOT: block continuation — hold propagation at this cell
        cpm['block_count'] += 1
        dec = 0.10 * scale
        cpm['extend_temporal'] = max(0.0, cpm['extend_temporal'] - dec)
        delta['block_count'] = 1
        delta['extend_temporal'] = -dec

    elif op.istate_op == IStateOp.RESIST:
        # I_DONOT: energy resistance — raises constraint cost
        inc = 0.05 * scale
        cpm['resist_cost'] = min(1.0, cpm['resist_cost'] + inc)
        delta['resist_cost'] = inc

    elif op.istate_op == IStateOp.SEARCH:
        # I_SOUGHT: boundary seeking — flag cell as under active search
        cpm['search_count'] += 1
        delta['search_count'] = 1

    elif op.istate_op == IStateOp.WITHHOLD:
        # I_DIDNT: agency withheld — reduce agency at this cell
        dec = 0.10 * scale
        cpm['commit_agency'] = max(0.0, cpm['commit_agency'] - dec)
        cpm['withhold_count'] += 1
        delta['withhold_count'] = 1
        delta['commit_agency'] = -dec

    # Recursion scope ≥ SHALLOW propagates via coupling physics
    propagated: List[PropagationEvent] = []
    if op.recursion_level >= 1 and op.axis in _COUPLING:
        for neighbor_axis, coupling_weight in _COUPLING[op.axis].items():
            propagated.append(PropagationEvent(
                axis=neighbor_axis,
                weight=coupling_weight * scale,
            ))

    cell_address = getattr(crystal, 'axis_bucket', ())
    return OperationResult(
        op=op,
        cell_address=cell_address,
        delta=delta,
        propagated_to=propagated,
        success=True,
    )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def istate_to_op(istate_name: str,
                 recursion_level: int,
                 intensity: float = 1.0) -> Optional[FieldOperation]:
    """Convert an I-state name + recursion level to a FieldOperation, or None if unknown."""
    if istate_name not in _ISTATE_MAP:
        return None
    op_type, axis = _ISTATE_MAP[istate_name]
    return FieldOperation(
        istate_op=op_type,
        recursion_level=max(0, min(4, recursion_level)),
        axis=axis,
        intensity=max(0.0, min(1.0, intensity)),
    )


def read_cell_cpm(crystal: Any) -> Dict[str, Any]:
    """Return a copy of the CPM state stored in a crystal's overlay. Safe to call on None."""
    if crystal is None:
        return {}
    overlay = getattr(crystal, 'current_overlay', None)
    if not overlay:
        return {}
    return dict(overlay.get(_CPM_KEY, {}))


def cell_symbol(crystal: Any) -> Optional[str]:
    """
    The tape symbol at this crystal cell: the crystal stage.
    Returns one of 'base' | 'composite' | 'higher_order' | 'quasi', or None.
    """
    if crystal is None:
        return None
    return getattr(crystal, 'stage', None)
