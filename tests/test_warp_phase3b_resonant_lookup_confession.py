# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 3b (2026-07-25, ratified priority
#2 of 4: resonant_lookup() misses).

resonant_lookup() (Phase 1) already fails quiet when no query_axis_state
is given -- nothing to search with, nothing to confess. But a GENUINE
search (real query_axis_state, real crystals checked) that still comes
back with nothing above threshold is a textbook WarpTrigger.GAP
confession per the directive (Section 4, candidate #4) -- distinct from
resonant_or_extend()'s own tier-3 fallthrough to the real
check_and_extend() (the structural WarpCapable side). Both fire from the
same miss, by design: this is the universal WarpField confession side,
not a replacement for the coverage-gap machinery.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_dimensional_systems as ads  # noqa: E402
from aurora_dimensional_systems import CrystalProcessingSystem, Crystal, EvolutionTracker  # noqa: E402
from aurora_warp_protocol import WarpTrigger  # noqa: E402


def _dps():
    return CrystalProcessingSystem(tracker=EvolutionTracker())


def _crystal(cid, concept, sig=None):
    c = Crystal(crystal_id=cid, concept=concept)
    if sig is not None:
        c.constraint_signature = dict(sig)
    return c


def _real_shaped_warp_guard_spy(calls):
    """Mirrors warp_guard's real signature exactly -- a call shaped
    differently would raise TypeError here the same way it would
    against the real function."""
    def _spy(
        source: str, layer: str, trigger: str, *,
        unresolved_text: str = "", expected=None, actual=None,
        participants=None, profile=None, local_attempts=None,
        severity: float = 0.5, persistence_key: str = "",
    ):
        calls.append({
            "source": source, "layer": layer, "trigger": trigger,
            "unresolved_text": unresolved_text, "profile": profile,
            "severity": severity, "persistence_key": persistence_key,
        })
        return None
    return _spy


def test_no_query_axis_state_does_not_confess(monkeypatch):
    """Fail-quiet path (no query at all) is not a 'miss' -- nothing was
    searched, so nothing is confessed."""
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})

    result = dps.resonant_lookup("gamma", query_axis_state=None)

    assert result == []
    assert calls == []


def test_genuine_miss_confesses_via_warp_guard(monkeypatch):
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    dps = _dps()
    # orthogonal axis key-set -- resonant_lookup will find nothing to
    # even compare against, a genuine miss on a genuine search.
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"B": 1.0, "A": 0.0})

    result = dps.resonant_lookup("gamma", query_axis_state={"X": 1.0, "N": 0.0})

    assert result == []
    assert len(calls) == 1
    call = calls[0]
    assert call["source"] == "dimensional_crystal"
    assert call["layer"] == "resonant_lookup"
    assert call["trigger"] == WarpTrigger.GAP
    assert call["unresolved_text"] == "gamma"
    assert call["profile"] == {"X": 1.0, "N": 0.0}
    assert call["persistence_key"] == "resonant_miss:gamma"


def test_below_threshold_miss_also_confesses(monkeypatch):
    """A real candidate exists and shares the axis key-set, but its
    similarity is below threshold -- still a genuine miss."""
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "orthogonal", sig={"X": 0.0, "N": 1.0})

    result = dps.resonant_lookup("gamma", query_axis_state={"X": 1.0, "N": 0.0}, threshold=0.55)

    assert result == []
    assert len(calls) == 1
    assert calls[0]["trigger"] == WarpTrigger.GAP


def test_successful_match_does_not_confess(monkeypatch):
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})

    result = dps.resonant_lookup("gamma", query_axis_state={"X": 1.0, "N": 0.0}, threshold=0.5)

    assert len(result) == 1
    assert calls == []


def test_confession_exceptions_are_swallowed(monkeypatch):
    def _always_raises(*a, **kw):
        raise RuntimeError("warp field unavailable")
    monkeypatch.setattr(ads, "warp_guard", _always_raises)
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"B": 1.0, "A": 0.0})

    # Must not raise -- confession-path failures never break lookup.
    result = dps.resonant_lookup("gamma", query_axis_state={"X": 1.0, "N": 0.0})
    assert result == []


def test_confession_does_not_prevent_resonant_or_extend_gap_fallthrough(monkeypatch):
    """The Phase 4 tier-3 fallthrough to check_and_extend() must still
    fire exactly as before -- Phase 3b's confession is additive, not a
    replacement for the existing structural gap machinery."""
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})

    from aurora_warp_protocol import GAP_PERSISTENCE_REQUIRED

    last_tier = None
    for i in range(GAP_PERSISTENCE_REQUIRED + 1):
        _, tier = dps.resonant_or_extend(
            "gamma", query_axis_state={"B": 1.0, "A": 1.0}, tick=i,
        )
        last_tier = tier
        if tier == "gap":
            break

    assert last_tier == "gap"
    # one confession call per resonant_or_extend() attempt (each one
    # calls resonant_lookup() internally and misses every time)
    assert len(calls) == GAP_PERSISTENCE_REQUIRED
    assert all(c["trigger"] == WarpTrigger.GAP for c in calls)
