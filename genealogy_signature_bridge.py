# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
genealogy_signature_bridge.py

Location 2 write path: whenever constraint_genealogy.py's machinery assigns
a (Law, Dimension, Target) identity to an event, call emit_genealogy_experience()
to push it through PressureExperienceLedger.record() using the exact same
anchor key that bridge_ledger_to_noncomps.py already matches against
nc_name in the manifold files.

This module does NOT modify constraint_genealogy.py or guess where inside
its 6,627 lines the right call site is -- that file is large enough that
the actual hook point (wherever a signature is finalized for a real event,
as opposed to the many internal scoring helpers like
_lineage_grade_payload / _lineage_generation_from_counts) needs to be
identified by you or traced properly rather than assumed. This module is
the receiving end, ready to be called from wherever that turns out to be.

Candidate hook point (found while wiring aurora_warp_protocol.py against
this same file, not yet acted on): the block in constraint_genealogy.py
that constructs a promoted ConstraintLink already has all three values in
scope at once -- dom_axis (Target), and the tags list carries
"dominant_constraint:<Law>" / "dominant_dimension:<Dimension>" whenever
aurora_closure_basis's physics-grounded lineage grading succeeds (it falls
back to a string-frequency heuristic otherwise, in which case those tags
are placeholders, not real signal). Wiring a call to
emit_genealogy_experience() there is a real behavior change to the
promotion path that this pass deliberately left untouched -- confirm before
wiring it in.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from typing import Any, Dict

from aurora_constraint_signature_resolver import nc_name as _nc_name


def emit_genealogy_experience(
    law: str,
    dim: str,
    target: str,
    meaning: str,
    pursuing: str,
    causal_action: str,
    consequence: Dict[str, Any],
    outcome: Dict[str, Any],
    ledger: Any = None,
) -> Dict[str, Any]:
    """
    Resolve (law, dim, target) to the matching noncomp's nc_name and record
    the experience via PressureExperienceLedger, anchored so
    bridge_ledger_to_noncomps.py will find it on the next pass.

    `ledger` should be a PressureExperienceLedger instance (pass
    PressureExperienceLedger.get() from aurora_internal.aurora_pressure_ledger);
    left as a parameter rather than imported directly so this module has no
    hard dependency on that path being importable from wherever it's called.
    """
    anchor = _nc_name(law, dim, target)

    if ledger is None:
        raise ValueError(
            "emit_genealogy_experience requires a PressureExperienceLedger "
            "instance -- pass PressureExperienceLedger.get()."
        )

    exp = ledger.record(
        anchor=anchor,
        meaning=meaning,
        pursuing=pursuing,
        causal_action=causal_action,
        consequence=consequence,
        outcome=outcome,
        source="genealogy",
    )
    return exp.to_dict() if hasattr(exp, "to_dict") else exp
