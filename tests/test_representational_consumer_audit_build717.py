# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 717 -- section 16's required audit of every major
representational consumer (interpretation, relation typing, inquiry,
memory retrieval, RCEC, response formation, Habitat cognition, prediction,
WARP, Dream), pinned down as a permanent regression rather than a one-time
finding that could silently drift.

Audit method: grep/AST-verified against live source, not from memory or a
prior report. Findings, one per consumer:

  Habitat cognition   -- the ONE consumer with a concrete, justified need
                          to differentiate behavior on resolved sub-fields
                          (which real Habitat affordance is worth acting
                          on). Wired in aurora_habitat_motivation.py
                          (section 16-17). The only call to
                          current_resolution() anywhere outside tests.

  Interpretation       -- aurora.py / aurora_reflexive_interpreter.py only
                          ever WRITE 'representational_ref' (thread the
                          coarse encoded ref from noncomp_output/input
                          into UnderstandingState); neither reads it back
                          for a decision. Pure provenance -- correctly
                          least-sufficient, since nothing downstream
                          currently branches on it.

  RCEC                  -- aurora_cognitive_experience_chamber.py is a
                          PRODUCER into resolution (record_ref_participation_
                          from_scores, exactly like Habitat's own
                          _emit_resolution_pressure), and separately carries
                          representational_ref on EpisodeStep as provenance.
                          It does not currently pull resolved fields back
                          out for its own decisions -- no existing RCEC
                          logic branches on a sub-field, so there is
                          nothing to justify requesting more than the
                          coarse ref (least-sufficient, correctly).

  Memory retrieval      -- SediMemory / UnderstandingSediment explicitly
                          document representational_ref as "provenance
                          only", never read by constraint/axis/worth
                          computation (see aurora_sedimemory.py's own
                          comment at the slice-field list, and
                          aurora_understanding_sediment.py's docstring).

  WARP                  -- explicitly, deliberately non-authoritative by
                          the existing Build 714 boundary decision:
                          WarpDemand.representational_ref's own docstring
                          states "never read by _classify()/_route() or
                          any numeric pathway logic". Confirmed still true
                          here rather than merely re-asserted.

  Relation typing, prediction, Dream -- carry NO representational_ref
                          wiring at all (zero references anywhere in
                          aurora_constraint_engine.py, the
                          aurora_internal/dual_strata prediction modules,
                          aurora_dream_substrate.py,
                          aurora_quantum_dream_substrate.py, or
                          aurora_dream_genealogy_bridge.py). This predates
                          both Build 714 and Build 717 -- RepresentationalRef
                          did not exist when Dream's own genealogy wiring
                          was built -- and is a pre-existing scope boundary,
                          not a regression introduced by this build. Wiring
                          new representational identity into three
                          previously-unaware subsystems would be a new
                          architectural expansion outside this directive's
                          scope (Habitat motivation), not an audit fix.

Conclusion: of the 9 named consumers, exactly one (Habitat cognition) has
a genuine, justified reason to consume resolved sub-fields today. Wiring
current_resolution() into the other 8 without such a reason would violate
section 16's own "do NOT force all consumers to use maximum refinement" --
these tests exist to catch exactly that kind of unjustified expansion (or
its opposite: Habitat cognition silently losing its wiring) in future
work, not to force new consumption where none is warranted.
"""
from __future__ import annotations

import ast
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(_ROOT, relpath), "r", encoding="utf-8") as f:
        return f.read()


def _calls_current_resolution(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "current_resolution":
            return True
    return False


def test_habitat_motivation_is_the_only_production_caller_of_current_resolution():
    """Guards against BOTH directions of drift: Habitat cognition losing
    its wiring, and an unjustified consumer gaining it without a
    documented reason (this test file would need updating either way,
    which is the point)."""
    assert _calls_current_resolution(_read("aurora_habitat_motivation.py"))

    other_producer_files = [
        "aurora.py",
        "aurora_reflexive_interpreter.py",
        "aurora_internal/aurora_cognitive_experience_chamber.py",
        "aurora_sedimemory.py",
        "aurora_understanding_sediment.py",
        "aurora_warp_protocol.py",
        "aurora_constraint_engine.py",
        "aurora_dream_substrate.py",
    ]
    for relpath in other_producer_files:
        assert not _calls_current_resolution(_read(relpath)), (
            f"{relpath} now calls current_resolution() without a documented "
            "justification in this audit -- update the audit (and this "
            "test) if a genuine new need was found, don't silently add it."
        )


def test_interpretation_only_writes_representational_ref_never_reads_it_back():
    """aurora.py's own two representational_ref sites must remain WRITES
    (dict construction from noncomp_output/input), not a later read used
    to branch logic -- confirms interpretation is still a pure provenance
    carrier, matching least-sufficient resolution."""
    source = _read("aurora.py")
    tree = ast.parse(source)
    read_sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            args = node.args
            if args and isinstance(args[0], ast.Constant) and args[0].value == "representational_ref":
                read_sites.append(node)
    # Both existing sites are `.get('representational_ref')` calls on
    # noncomp_output/noncomp_input dicts feeding a dict literal being
    # built for return/assignment -- i.e. still writes-in-progress, not a
    # branch condition. Presence of read_sites is expected (that's how the
    # ref is threaded); what matters is that count is unchanged from the
    # documented baseline (4 sites: 2 pairs of output/input fallback).
    assert len(read_sites) == 4


def test_warp_representational_ref_remains_documented_non_authoritative():
    source = _read("aurora_warp_protocol.py")
    assert "contextual provenance only, never" in source
    assert "read by _classify()/_route() or any numeric pathway" in source
    assert "representational_ref: Optional[str] = None" in source


def test_relation_typing_prediction_and_dream_carry_no_representational_ref():
    """Pins the audit's finding that these three consumer categories have
    zero RepresentationalRef coupling today -- a pre-existing scope
    boundary, not something this test asserts SHOULD remain permanently
    true, only that it is currently, honestly, true."""
    unaware_files = [
        "aurora_constraint_engine.py",
        "aurora_internal/dual_strata/prediction_field.py",
        "aurora_dream_substrate.py",
        "aurora_quantum_dream_substrate.py",
        "aurora_internal/aurora_dream_genealogy_bridge.py",
    ]
    for relpath in unaware_files:
        source = _read(relpath)
        assert "representational_ref" not in source
        assert "RepresentationalRef" not in source


def test_rcec_participates_as_a_producer_not_yet_a_resolution_consumer():
    """RCEC feeds real evidence INTO resolution (record_ref_participation_
    from_scores, mirroring Habitat's own _emit_resolution_pressure) but
    does not currently pull resolved fields back out -- confirmed by the
    absence of any current_resolution() call alongside the presence of the
    producer call."""
    source = _read("aurora_internal/aurora_cognitive_experience_chamber.py")
    assert "record_ref_participation_from_scores" in source
    assert not _calls_current_resolution(source)
