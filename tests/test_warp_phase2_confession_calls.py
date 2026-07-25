# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 2 (2026-07-24, ratified Option A).

aurora_possibility_selves.py's provoke_reexperience() and dream_dialogue()
each called warp_guard(anchor, her_strength) -- the real aurora_warp_
protocol.warp_guard's signature is (source, layer, trigger, *,
unresolved_text="", ..., severity=0.5, persistence_key=""). Every call
raised TypeError, silently swallowed by a bare `except Exception: pass`
-- running dark since it was wired, no crash, no signal, just a no-op
that looked like a working confession path.

Fixed to call the real signature. These tests use a spy matching warp_
guard's EXACT real signature (not a permissive **kwargs stub) -- a
regression back to the wrong call shape would raise TypeError here the
same way it silently did in production, just visible instead of
swallowed.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_possibility_selves import (  # noqa: E402
    PossibilitySelf, DivergenceProfile, provoke_reexperience, dream_dialogue,
)
from aurora_warp_protocol import WarpTrigger  # noqa: E402


def _real_shaped_warp_guard_spy(calls):
    """Mirrors aurora_warp_protocol.warp_guard's real signature exactly
    -- a call shaped like the old bug (2 positional args) raises
    TypeError here just as it did against the real function."""
    def _spy(
        source: str, layer: str, trigger: str, *,
        unresolved_text: str = "", expected=None, actual=None,
        participants=None, profile=None, local_attempts=None,
        severity: float = 0.5, persistence_key: str = "",
    ):
        calls.append({
            "source": source, "layer": layer, "trigger": trigger,
            "unresolved_text": unresolved_text, "severity": severity,
            "persistence_key": persistence_key,
        })
        return None
    return _spy


def _resolving_self(self_id="ps1", anchor="N", meaning="test tension"):
    ps = PossibilitySelf(
        self_id=self_id,
        profile=DivergenceProfile(name="test", orientation={}, reorder="reverse"),
        orientation={"I_DO": 1.0},  # leading_stance lands in _RESOLVING_POLES
    )
    ps.resolved_anchors[anchor] = meaning
    return ps


def _systems_with_high_capacity(axis="N", pressure=0.9):
    class _FakeIdentityField:
        def status(self):
            return {"axis_pressures": {axis: pressure}}
    return {"identity_field": _FakeIdentityField()}


def test_provoke_reexperience_calls_warp_guard_with_real_signature():
    calls = []
    spy = _real_shaped_warp_guard_spy(calls)
    ps = _resolving_self()
    systems = _systems_with_high_capacity()

    provoke_reexperience([ps], systems, warp_guard=spy, max_per_self=10,
                          max_new_resolutions=10, persist=False)

    assert calls, "expected at least one her_resolved branch to fire and confess"
    call = calls[0]
    assert call["source"] == "possibility_selves"
    assert call["layer"] == "provoke_reexperience"
    assert call["trigger"] == WarpTrigger.AMBIGUITY
    assert call["unresolved_text"] == "N"
    assert isinstance(call["severity"], float)
    assert call["persistence_key"] == "N"


def test_dream_dialogue_calls_warp_guard_with_real_signature():
    calls = []
    spy = _real_shaped_warp_guard_spy(calls)
    ps = _resolving_self()
    systems = _systems_with_high_capacity()

    dream_dialogue([ps], systems, warp_guard=spy, max_per_self=10,
                    max_new_resolutions=10, turns=1)

    assert calls, "expected at least one her_resolved branch to fire and confess"
    call = calls[0]
    assert call["source"] == "possibility_selves"
    assert call["layer"] == "dream_dialogue"
    assert call["trigger"] == WarpTrigger.AMBIGUITY


def test_provoke_reexperience_degrades_gracefully_when_warp_guard_is_none():
    ps = _resolving_self()
    systems = _systems_with_high_capacity()
    # Must not raise -- warp_guard is optional (Any = None default).
    result = provoke_reexperience([ps], systems, warp_guard=None,
                                   max_per_self=10, max_new_resolutions=10,
                                   persist=False)
    assert isinstance(result, dict)


def test_dream_dialogue_degrades_gracefully_when_warp_guard_is_none():
    ps = _resolving_self()
    systems = _systems_with_high_capacity()
    result = dream_dialogue([ps], systems, warp_guard=None,
                             max_per_self=10, max_new_resolutions=10, turns=1)
    assert isinstance(result, dict)


def test_provoke_reexperience_warp_guard_exceptions_are_still_swallowed():
    """The bare except Exception: pass around the call is intentional and
    stays -- a confession-path failure must never break her dream cycle.
    Verified by a spy that always raises."""
    def _always_raises(*a, **kw):
        raise RuntimeError("warp field unavailable")

    ps = _resolving_self()
    systems = _systems_with_high_capacity()
    result = provoke_reexperience([ps], systems, warp_guard=_always_raises,
                                   max_per_self=10, max_new_resolutions=10,
                                   persist=False)
    assert isinstance(result, dict)
