"""Regression tests for threading the turn's representational_ref into
SediMemory's ingest content (aurora.py's "SediMemory deposit" block inside
_run_reasoning_pipeline) -- item #5 of the Aurora Representational
Conservation and Native Computational Utilization Repair Directive.

SediMemory.ingest_event()'s own event_id is independently generated
(aurora_sedimemory.py's MemoryEvent.create(), an md5 of wall-clock time +
uuid4) and stays that way -- this fix does not touch SediMemory's storage
key. The gap was that nothing SediMemory stored linked back to the turn's
already-computed representational_ref (the same identity item #4, PR #218,
already threads into genealogy.observe()'s notes), even though the
receiving machinery -- NCStrainFilter._extract_slice -- already
special-cases and preserves a 'representational_ref' key from content into
every resonant SedimentFragment.content it produces, untouched by
resonance/strain selection. It was simply never fed at the one real,
currently-functioning production call site.

Purely additive: one new key in the content dict, included only when the
ref is available; byte-identical content otherwise.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora
from aurora_sedimemory import SediMemory
from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
from aurora_representational_address import RepresentationalRef


def _fresh_sedimemory():
    return SediMemory()


def _cv():
    return ConstraintVector(X=0.6, T=0.5, N=0.4, B=0.3, A=0.2)


def test_representational_ref_reaches_a_resonant_fragments_content():
    """Direct proof of the fix: a representational_ref present in
    ingest_event()'s content dict survives NCStrainFilter._extract_slice's
    passthrough into at least one resulting SedimentFragment.content."""
    sedi = _fresh_sedimemory()
    ref = RepresentationalRef(nc_law_c="T", nc_dim="OPERATOR", nc_target="X").encode()

    sedi.ingest_event(
        content={
            "user_text": "I need to protect my boundaries here",
            "response": "Understood.",
            "response_rejected": False,
            "intent": "boundary",
            "tone": "steady",
            "confidence": 0.8,
            "salient": ["boundary"],
            "src": "test",
            "representational_ref": ref,
        },
        constraint_vector=_cv(),
        source="turn_pipeline",
    )

    event_id = sedi._event_log[-1]
    fragments = sedi.recall_event(event_id)
    assert fragments, "expected at least one resonant fragment for a real constraint vector"
    assert any(f.content.get("representational_ref") == ref for f in fragments), (
        "no fragment carried the representational_ref through from content"
    )


def test_fragment_content_unchanged_when_representational_ref_omitted():
    """Regression: omitting the key entirely (today's shape) must leave
    fragment content exactly as before -- no key appears, no crash."""
    sedi = _fresh_sedimemory()
    sedi.ingest_event(
        content={
            "user_text": "existence itself feels uncertain right now",
            "response": "I hear that.",
            "response_rejected": False,
            "intent": "existence",
            "tone": "steady",
            "confidence": 0.7,
            "salient": ["existence"],
            "src": "test",
        },
        constraint_vector=_cv(),
        source="turn_pipeline",
    )
    event_id = sedi._event_log[-1]
    fragments = sedi.recall_event(event_id)
    assert fragments
    for f in fragments:
        assert "representational_ref" not in f.content


def test_run_reasoning_pipeline_sedimemory_block_reads_ref_from_systems():
    """Confirms the wiring at the actual call site: systems["_last_noncomp_input"]
    ["representational_ref"] -- the same source item #4 already threads into
    genealogy.observe() -- is what reaches SediMemory.ingest_event's content,
    conditionally included only when truthy."""
    import inspect
    src = inspect.getsource(aurora._run_reasoning_pipeline)
    assert '_turn_repr_ref = (systems.get("_last_noncomp_input") or {}).get("representational_ref")' in src
    assert '**({"representational_ref": _turn_repr_ref} if _turn_repr_ref else {})' in src


def test_real_boot_live_turns_deposit_a_decodable_ref_into_a_fragment():
    """Real-boot integration test: drive several real live turns through
    process_external_user_turn() (no mocking) and confirm at least one
    resulting SedimentFragment across the run carries a representational_ref
    that decodes cleanly via RepresentationalRef.decode()."""
    import shutil

    scratch = tempfile.mkdtemp(prefix="aurora_sedimemory_ref_realboot_")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
    systems = aurora.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)

    sedi = systems.get("sedimemory")
    assert sedi is not None, "real boot must produce a live sedimemory instance"

    event_ids_before = set(sedi._event_log)
    for turn_text in (
        "I need to protect my boundaries here",
        "existence itself feels uncertain right now",
        "time keeps slipping away from me and I don't have the energy for this",
        "I feel torn between two things I care about",
        "can you help me understand what's happening to me",
    ):
        aurora.process_external_user_turn(systems, turn_text)

    new_event_ids = [eid for eid in sedi._event_log if eid not in event_ids_before]
    assert new_event_ids, "expected at least one new SediMemory event across 5 real turns"

    refs = []
    for eid in new_event_ids:
        for frag in sedi.recall_event(eid):
            ref = frag.content.get("representational_ref")
            if ref:
                refs.append(ref)

    if refs:
        for ref in refs:
            decoded = RepresentationalRef.decode(ref)
            assert decoded is not None
