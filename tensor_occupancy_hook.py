# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tensor_occupancy_hook.py

Location 1 write path: raw occupancy log for FieldSlot (aurora_constraint_engine.py),
the actual runtime 625-slot tensor (Constraint x CompositionalSpace x State x
RecursionLevel).

This is an OWN, INDEPENDENT log -- aurora_state/tensor_occupancy.jsonl.
FieldSlot.deposit() receives a full 5-value ConstraintVector (X,T,N,B,A
weights all at once) plus indices into CompositionalSpace/State/
RecursionLevel. Unlike constraint_genealogy.py's dominant_constraint/
dominant_dimension tags -- which already spoke the noncomp (law, dim,
target) vocabulary verbatim before this project touched them -- nothing
here was pre-labeled that way. CONSTRAINT_LABELS are already X/T/N/B/A
(Target, direct), but CompositionalSpace and State's labels
(linear/recursive/branching/convergent/emergent,
dormant/transient/active/persistent/agentic) are not Dimension words or
axis letters.

_STATE_TO_LAW and _COMP_TO_DIMENSION below are a DEFINED convention, not a
discovered fact -- authorized explicitly rather than assumed, per the
reasoning in each mapping's comment. Treat resolved_nc_name in the log as a
best-effort annotation, not verified ground truth the way the genealogy
bridge's anchors are.

Monkeypatches FieldSlot.deposit in place. Auto-installed from
ConstraintEngine.__init__ (aurora_constraint_engine.py) -- the one
production FieldSlot() instantiation, which every one of the 19+ modules
that construct a ConstraintEngine funnels through, so this covers all of
them without editing any of the 19+. install() is idempotent and wrapped in
try/except there, so a missing or broken hook module never breaks engine
construction.

Manual usage (e.g. against a FieldSlot used outside ConstraintEngine) still
works the same way:
    import tensor_occupancy_hook
    tensor_occupancy_hook.install(field_slot_cls=FieldSlot)
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional, Tuple

from aurora_constraint_signature_resolver import nc_name as _resolve_nc_name
import aurora_manifold_lookup

LOG_PATH = Path("aurora_state/tensor_occupancy.jsonl")
_installed = False
_original_deposit = None

# Target = CONSTRAINT_LABELS[constraint] directly -- no mapping needed, it's
# already X/T/N/B/A.
#
# Law <- STATE_LABELS, by analogy to Aurora's own I-state vocabulary
# (aurora_warp_protocol.py's I_IS/I_CAN/I_DO/I_SAW/I_DID axis meanings) and
# this file's own ExistenceMode ordering:
#   dormant    -> X  (bare existence, pre-activation)
#   transient  -> T  (ephemeral/temporal -- I_CAN's axis)
#   active     -> N  ("energy expressed" is I_DO's own definition)
#   persistent -> B  (a held, maintained boundary)
#   agentic    -> A  (word-identical to A's I_DID/agency axis)
_STATE_TO_LAW = {
    "dormant":    "X",
    "transient":  "T",
    "active":     "N",
    "persistent": "B",
    "agentic":    "A",
}

# Dimension <- COMP_LABELS, by analogy to each dimension's physics role (see
# aurora_warp_protocol.py's OPERATOR/POLARITY/MAGNITUDE/COST/DIFFERENCE
# table and constraint_genealogy.py's _AXIS_NC_DIM comment):
#   linear     -> OPERATOR    (unconditional single-path pass-through)
#   branching  -> POLARITY    (a fork IS a directional choice)
#   emergent   -> MAGNITUDE   (amplification / new intensity arising)
#   convergent -> COST        (funneling down, paid toward one outcome)
#   recursive  -> DIFFERENCE  (repeated self-application = rate of change)
_COMP_TO_DIMENSION = {
    "linear":     "OPERATOR",
    "branching":  "POLARITY",
    "emergent":   "MAGNITUDE",
    "convergent": "COST",
    "recursive":  "DIFFERENCE",
}


def resolve_field_slot_signature(
    constraint_label: Optional[str],
    comp_label: Optional[str],
    state_label: Optional[str],
) -> Optional[Tuple[str, str, str]]:
    """
    Best-effort (law, dim, target) resolve for one FieldSlot deposit, per the
    convention above. Returns None -- not a guess -- the moment any label is
    missing or unrecognized.
    """
    law = _STATE_TO_LAW.get(state_label or "")
    dim = _COMP_TO_DIMENSION.get(comp_label or "")
    target = constraint_label
    if not law or not dim or not target:
        return None
    return law, dim, target


def _logging_deposit(self, constraint: int, comp: int, state: int,
                      recursion: int, vec) -> None:
    try:
        constraint_label = (type(self).CONSTRAINT_LABELS[constraint]
            if 0 <= constraint < len(type(self).CONSTRAINT_LABELS) else None)
        comp_label = (type(self).COMP_LABELS[comp]
            if 0 <= comp < len(type(self).COMP_LABELS) else None)
        state_label = (type(self).STATE_LABELS[state]
            if 0 <= state < len(type(self).STATE_LABELS) else None)
        recursion_label = (type(self).RECURSION_LABELS[recursion]
            if 0 <= recursion < len(type(self).RECURSION_LABELS) else None)

        resolved_nc_name = None
        triple = resolve_field_slot_signature(constraint_label, comp_label, state_label)
        if triple is not None:
            try:
                candidate = _resolve_nc_name(*triple)
                if aurora_manifold_lookup.load_noncomp(candidate) is not None:
                    resolved_nc_name = candidate
            except KeyError:
                pass

        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps({
                "timestamp":       time.time(),
                "constraint_idx":  constraint,
                "comp_idx":        comp,
                "state_idx":       state,
                "recursion_idx":   recursion,
                "constraint_label": constraint_label,
                "comp_label":       comp_label,
                "state_label":      state_label,
                "recursion_label":  recursion_label,
                "resolved_nc_name": resolved_nc_name,
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
