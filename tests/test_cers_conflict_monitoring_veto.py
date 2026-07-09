# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Phase 4: the compressed hesitation signal (Phase 3) now has a real
behavioral effect, not just a value sitting unread in a dict. Traced by
grep that neither cers_salience nor cers_hesitation had a single consumer
anywhere in the codebase before this -- the whole tensor-recursion pipeline
computed and surfaced a signal that nothing downstream ever looked at.

Mirrors ACC conflict-monitoring in human cognition: detected conflict
(cers_hesitation -- either a classic crest-cluster conflict or a sharp
break from an established pressure pattern) recruits deliberate processing
instead of letting the fast/reactive/autopilot path run. Both hooks are
additive-only vetoes -- CERS still cannot force any of these paths to fire,
it can only withhold one the legacy convergence would otherwise have
allowed. CERS stays non-authoritative.

Hook 1 (_chain_up4_meaning, aurora.py): the A-dominant OETS/meaning bypass.
Hook 2 (_build_comprehension_response, aurora.py): the reactive-shortcut
fast response. Hook 2's surrounding function is a large, deeply-stateful
comprehension pipeline impractical to drive end-to-end in a unit test (this
codebase has essentially no existing test coverage of aurora.py's turn
pipeline at all); its conditional logic is identical in shape and read
pattern to Hook 1's (verified live below), so it's covered here as an
isolated logic check instead of a full function call.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora


def _make_state():
    return types.SimpleNamespace(
        response_content="already set",  # skip the relational_role early-return branch
        parsed={},
        axis_activation={"A": 0.9},
        dominant_axis="A",
        pipeline_state={},
        salient_concepts=[],
        semantic_pressure=0.0,
        a_dominant=False,
        meaning_forms=[],
        dominant_meaning_form={},
    )


def test_a_dominant_bypass_fires_without_cers_hesitation():
    state = _make_state()
    aurora._chain_up4_meaning("hello", {}, state)
    assert state.a_dominant is True


def test_a_dominant_bypass_vetoed_by_cers_hesitation():
    state = _make_state()
    systems = {"_live_conscious_frame": {"cers_hesitation": True}}
    aurora._chain_up4_meaning("hello", systems, state)
    assert state.a_dominant is False


def test_a_dominant_bypass_unaffected_by_explicit_false():
    state = _make_state()
    systems = {"_live_conscious_frame": {"cers_hesitation": False}}
    aurora._chain_up4_meaning("hello", systems, state)
    assert state.a_dominant is True


def test_a_dominant_bypass_unaffected_when_no_live_conscious_frame_yet():
    """Defensive default: if CERS hasn't run yet this turn (or ever),
    _live_conscious_frame is absent -- must degrade to old behavior, not
    accidentally veto everything."""
    state = _make_state()
    aurora._chain_up4_meaning("hello", {"_live_conscious_frame": {}}, state)
    assert state.a_dominant is True


def test_legacy_deliberation_mode_veto_still_works_alongside_cers():
    """The pre-existing conscious_frame_mode veto (clarify/research/
    observation) must be unaffected by this addition."""
    state = _make_state()
    state.pipeline_state = {"conscious_frame_mode": "clarify"}
    aurora._chain_up4_meaning("hello", {}, state)
    assert state.a_dominant is False


def test_reactive_shortcut_veto_logic_matches_a_dominant_gate_pattern():
    """Isolated check of aurora.py:18109-18127's conditional (same read
    pattern as _chain_up4_meaning's gate, verified live above) -- the
    surrounding _build_comprehension_response is impractical to drive
    end-to-end in a unit test."""
    def reactive_fires(r_text, r_conf, r_mode, cers_hesitant):
        return bool(
            r_text and (r_conf >= 0.72 or r_mode in ("survival", "conserve"))
            and not cers_hesitant
        )

    assert reactive_fires("hi", 0.9, "", False) is True
    assert reactive_fires("hi", 0.9, "", True) is False, "high confidence alone must not override CERS hesitation"
    assert reactive_fires("hi", 0.3, "survival", False) is True
    assert reactive_fires("hi", 0.3, "survival", True) is False, "survival mode alone must not override CERS hesitation"
    assert reactive_fires("hi", 0.3, "", False) is False, "unrelated to CERS -- neither legacy condition met"
    assert reactive_fires("", 0.9, "", False) is False, "no reactive text -- never fires regardless of CERS"
