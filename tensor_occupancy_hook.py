# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tensor_occupancy_hook.py

Location 1 write path: raw occupancy log for FieldSlot (aurora_constraint_engine.py),
the actual runtime 625-slot tensor (Constraint x CompositionalSpace x State x
RecursionLevel).

This is an OWN, INDEPENDENT log -- aurora_state/tensor_occupancy.jsonl -- not
yet joined to a specific manifold noncomp. FieldSlot.deposit() only receives
a full 5-value ConstraintVector (X,T,N,B,A weights all at once) plus indices
into CompositionalSpace/State/RecursionLevel, none of which currently map to
a specific Dimension or Target the way constraint_genealogy.py's signatures
do. Resolving a deposit event down to one nc_name would require you to define
that mapping first (e.g. does a given (comp, state, recursion) combination
correspond to a specific Dimension? Is there a fixed Target per call site?).
Until that's defined, this hook logs the raw event faithfully rather than
forcing a false 1:1 correspondence.

Non-invasive: monkeypatches FieldSlot.deposit in place. Does not edit
aurora_constraint_engine.py.

Usage:
    import tensor_occupancy_hook
    tensor_occupancy_hook.install()
    # ... normal Aurora runtime, FieldSlot.deposit() calls now also logged ...
"""
from __future__ import annotations
import json
import time
from pathlib import Path

LOG_PATH = Path("aurora_state/tensor_occupancy.jsonl")
_installed = False
_original_deposit = None


def _logging_deposit(self, constraint: int, comp: int, state: int,
                      recursion: int, vec) -> None:
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({
                "timestamp":       time.time(),
                "constraint_idx":  constraint,
                "comp_idx":        comp,
                "state_idx":       state,
                "recursion_idx":   recursion,
                "constraint_label": type(self).CONSTRAINT_LABELS[constraint]
                    if 0 <= constraint < len(type(self).CONSTRAINT_LABELS) else None,
                "comp_label":       type(self).COMP_LABELS[comp]
                    if 0 <= comp < len(type(self).COMP_LABELS) else None,
                "state_label":      type(self).STATE_LABELS[state]
                    if 0 <= state < len(type(self).STATE_LABELS) else None,
                "recursion_label":  type(self).RECURSION_LABELS[recursion]
                    if 0 <= recursion < len(type(self).RECURSION_LABELS) else None,
                "vector": {
                    "X": vec.X, "T": vec.T, "N": vec.N, "B": vec.B, "A": vec.A,
                } if vec is not None else None,
            }) + "\n")
    except Exception:
        pass  # logging must never break the actual deposit

    return _original_deposit(self, constraint, comp, state, recursion, vec)


def install(field_slot_cls=None) -> None:
    """
    Monkeypatch FieldSlot.deposit to also log. Pass the FieldSlot class
    explicitly (from aurora_constraint_engine import FieldSlot) to avoid this
    module needing its own import path assumptions.
    """
    global _installed, _original_deposit
    if _installed:
        return
    if field_slot_cls is None:
        raise ValueError(
            "install() requires the FieldSlot class -- pass it in as "
            "field_slot_cls=FieldSlot (from aurora_constraint_engine import FieldSlot)."
        )
    _original_deposit = field_slot_cls.deposit
    field_slot_cls.deposit = _logging_deposit
    _installed = True


def uninstall(field_slot_cls) -> None:
    global _installed, _original_deposit
    if _installed and _original_deposit is not None:
        field_slot_cls.deposit = _original_deposit
        _installed = False
