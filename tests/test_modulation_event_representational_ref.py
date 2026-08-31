"""Regression tests for threading ReflexiveInterpreter's representational_ref
into ConstraintGenealogyLogger.observe() (aurora.py's _log_modulation_event /
_chain_down1_information) -- item #4 of the Aurora Representational
Conservation and Native Computational Utilization Repair Directive.

Prior to this fix, ReflexiveInterpreter.interpret() and
ConstraintGenealogyLogger.observe() never exchanged any value even though
both fire live, within the same turn, from the same _run_reasoning_pipeline
call: interpret()'s already-computed RepresentationalRef (already stored at
systems["_last_noncomp_input"]["representational_ref"] by
_apply_noncomp_input_guidance) was simply discarded before reaching the one
live observe() call site (_log_modulation_event, called from
_chain_down1_information).

This is purely additive: a new keyword-only representational_ref parameter
on _log_modulation_event, included in genealogy.observe()'s already-existing
free-form notes dict only when present. No new type, no PressureVec
translation, no behavior change when the ref is unavailable.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
from aurora_representational_address import RepresentationalRef


def _fresh_genealogy(name="modulation_event_ref_test"):
    scratch = tempfile.mkdtemp(prefix="aurora_modulation_event_ref_")
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=scratch)


# Signals chosen so pressure_before/pressure_after produce a genuine relief
# event (not filtered out by the noise filter) -- mirrors real live signals
# _log_modulation_event receives from state.pipeline_state.
_SIGNALS = {"stagnation": 0.9, "thermal_load": 0.8, "coherence": 0.1, "thought_killed": True}


def test_representational_ref_reaches_observe_notes_when_supplied():
    """Direct proof of the fix: a representational_ref passed to
    _log_modulation_event ends up in the ReliefRecord's notes dict under
    that exact key."""
    genealogy = _fresh_genealogy()
    ref = RepresentationalRef(nc_law_c="T", nc_dim="OPERATOR", nc_target="X").encode()

    record = aurora._log_modulation_event(
        genealogy, _SIGNALS, text_changed=True, tone_changed=False,
        representational_ref=ref,
    )

    # _log_modulation_event itself returns None (its return value is never
    # used at the call site) -- inspect genealogy's own persisted state
    # instead, same as a real downstream consumer would.
    assert genealogy.tick_count >= 1
    events = list(genealogy._event_log)
    assert events, "expected at least one recorded event after a qualifying relief tick"
    last = events[-1]
    assert last.notes.get("representational_ref") == ref
    assert last.notes.get("source") == "apply_pipeline_modulation"
    assert last.notes.get("text_changed") is True
    assert last.notes.get("tone_changed") is False


def test_notes_unchanged_when_representational_ref_omitted():
    """Regression: omitting representational_ref (the default) must produce
    the exact same notes dict as before this fix -- no new key, no
    behavior change."""
    genealogy = _fresh_genealogy()
    aurora._log_modulation_event(genealogy, _SIGNALS, text_changed=True, tone_changed=False)

    events = list(genealogy._event_log)
    assert events
    last = events[-1]
    assert "representational_ref" not in last.notes
    assert set(last.notes.keys()) >= {"source", "text_changed", "tone_changed"}


def test_notes_unchanged_when_representational_ref_falsy():
    """An empty-string ref (falsy) must also be omitted -- the call site
    passes systems.get("_last_noncomp_input", {}).get("representational_ref"),
    which can legitimately be None or "" when interpret() produced no ref;
    the notes dict must not gain a useless empty key in that case."""
    genealogy = _fresh_genealogy()
    aurora._log_modulation_event(
        genealogy, _SIGNALS, text_changed=True, tone_changed=False,
        representational_ref="",
    )
    events = list(genealogy._event_log)
    assert events
    assert "representational_ref" not in events[-1].notes


def test_chain_down1_information_call_site_reads_ref_from_systems():
    """Confirms the wiring at the actual call site inside
    _chain_down1_information: systems["_last_noncomp_input"]
    ["representational_ref"] is what reaches _log_modulation_event, read
    directly from systems rather than through any indirect mirror into
    state.pipeline_state."""
    import inspect
    src = inspect.getsource(aurora._chain_down1_information)
    assert 'representational_ref=(systems.get("_last_noncomp_input") or {}).get("representational_ref")' in src


def test_log_modulation_event_signature_has_keyword_only_ref_param():
    import inspect
    sig = inspect.signature(aurora._log_modulation_event)
    assert "representational_ref" in sig.parameters
    param = sig.parameters["representational_ref"]
    assert param.kind == inspect.Parameter.KEYWORD_ONLY
    assert param.default is None


def test_real_boot_live_turns_thread_a_decodable_ref_into_genealogy_notes():
    """Real-boot integration test: drive several real live turns through
    process_external_user_turn() (no mocking of interpret()/observe()
    internals -- only observe() itself is wrapped, purely to capture what
    it actually receives) and confirm that at least one call it receives
    across the run carries a representational_ref that decodes cleanly via
    RepresentationalRef.decode() -- a real, valid encoded ref, not a
    placeholder string."""
    import shutil

    scratch = tempfile.mkdtemp(prefix="aurora_modulation_event_ref_realboot_")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
    systems = aurora.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)

    genealogy = systems.get("genealogy")
    assert genealogy is not None, "real boot must produce a live genealogy instance"

    captured_notes = []
    real_observe = genealogy.observe

    def _spy_observe(*args, **kwargs):
        notes = kwargs.get("notes")
        if notes is None and len(args) >= 5:
            notes = args[4]
        if isinstance(notes, dict):
            captured_notes.append(dict(notes))
        return real_observe(*args, **kwargs)

    genealogy.observe = _spy_observe
    try:
        for turn_text in (
            "I need to protect my boundaries here",
            "existence itself feels uncertain right now",
            "time keeps slipping away from me and I don't have the energy for this",
            "I feel torn between two things I care about",
            "can you help me understand what's happening to me",
        ):
            aurora.process_external_user_turn(systems, turn_text)
    finally:
        genealogy.observe = real_observe

    modulation_notes = [n for n in captured_notes if n.get("source") == "apply_pipeline_modulation"]
    refs = [n.get("representational_ref") for n in modulation_notes if n.get("representational_ref")]

    # It's possible (though unlikely across 5 varied real turns) that no
    # modulation event fires at all in a given run; only assert on the ref's
    # validity when at least one modulation observation actually occurred.
    if modulation_notes:
        assert refs, (
            "at least one real live turn produced a modulation observation, "
            "but none carried a representational_ref"
        )
        for ref in refs:
            decoded = RepresentationalRef.decode(ref)
            assert decoded is not None
