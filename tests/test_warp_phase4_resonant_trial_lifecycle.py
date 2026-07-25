# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 4 (2026-07-24, ratified).

resonant_or_extend() is the "operate on theory until disproven" middle
tier the directive asked for: check_and_extend() alone only ever saw a
binary choice (existing coverage, or total gap derived from scratch).
This adds the missing middle -- a resonance hit that isn't an exact
match becomes a WARP TRIAL, not ground truth, scored over time by the
same evaluate_warp_trials()/TRIAL_TICKS/PROMOTION_SCORE machinery
check_and_extend() already uses (aurora_warp_protocol.py:945-1049).

Three tiers exercised directly against a real CrystalProcessingSystem
(no mocking of the WARP mixin -- the whole point is that this reuses
the real trial lifecycle verbatim):
  1. exact match (get_crystal hit) -- unchanged, no trial spawned.
  2. resonance match, no exact match -- provisional trial, seeded
     trial_score_ema from the similarity score, idempotent on repeat
     calls for the same concept (which naturally become tier-1 exact
     matches once the trial's own _integrate_warp creates the concept's
     crystal).
  3. no match at all -- falls through to the real check_and_extend(),
     unmodified, gated by its own GAP_PERSISTENCE_REQUIRED.
"""
import hashlib
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dimensional_systems import CrystalProcessingSystem, Crystal, EvolutionTracker  # noqa: E402


def _dps():
    return CrystalProcessingSystem(tracker=EvolutionTracker())


def _crystal(cid, concept, sig=None):
    c = Crystal(crystal_id=cid, concept=concept)
    if sig is not None:
        c.constraint_signature = dict(sig)
    return c


# ---- tier 1: exact match ----

def test_exact_match_returns_existing_crystal_and_spawns_no_trial():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    result, tier = dps.resonant_or_extend("alpha", query_axis_state={"X": 1.0, "N": 0.0})

    assert tier == "exact"
    assert result is dps.crystals["c1"]
    assert dps._warp_trials == {}


def test_exact_match_wins_even_with_no_query_axis_state():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha")
    dps.concept_index["alpha"] = "c1"

    result, tier = dps.resonant_or_extend("alpha", query_axis_state=None)
    assert tier == "exact"
    assert result is dps.crystals["c1"]


# ---- tier 2: resonance match, no exact match ----

def test_resonance_match_creates_provisional_trial():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    result, tier = dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})

    assert tier == "resonant_trial"
    assert result is not None
    assert result.concept == "beta"
    # a real crystal now exists under the new concept, created through
    # the same _get_or_create() every crystal uses (via _integrate_warp)
    assert dps.get_crystal("beta") is result


def test_resonance_match_seeds_trial_score_from_similarity():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})

    assert len(dps._warp_trials) == 1
    component = next(iter(dps._warp_trials.values()))
    # near-identical vectors -> similarity close to 1.0, and the
    # directive's own framing: the resonance hit IS the hypothesis, not
    # a zero-starting trial like check_and_extend's own trials.
    assert component.trial_score_ema > 0.99
    assert component.parent_ids == ["c1"]
    assert component.name == "beta"


def test_resonance_match_marks_crystal_with_provisional_and_genealogy_facets():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    result, _ = dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})

    roles = sorted(f.role for f in result.facets.values())
    assert roles == ["warp_genealogy", "warp_provisional"]


def test_resonance_match_is_idempotent_on_repeat_calls():
    """Second call for the same concept must not spawn a duplicate
    trial or stamp duplicate genealogy facets -- it naturally becomes a
    tier-1 exact match once the first call's _integrate_warp creates
    the concept's own crystal."""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    first, first_tier = dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})
    second, second_tier = dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})

    assert first_tier == "resonant_trial"
    assert second_tier == "exact"
    assert first is second
    assert len(dps._warp_trials) == 1
    assert len(first.facets) == 2  # unchanged by the repeat call


def test_resonance_match_component_id_is_deterministic_and_guards_reintegration():
    """Even if a trial is already tracked under the deterministic id
    (e.g. a caller bypasses get_crystal somehow), resonant_or_extend
    must not re-run _integrate_warp for it."""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})
    expected_id = "resonant:" + hashlib.md5(b"beta").hexdigest()[:12]
    assert expected_id in dps._warp_trials

    # Force back to the pre-exact-match state to exercise the trial-id
    # guard directly rather than only via the natural tier-1 shortcut.
    dps.concept_index.pop("beta", None)
    crystal_id_for_beta = next(
        cid for cid, c in dps.crystals.items() if c.concept == "beta"
    )
    dps.crystals.pop(crystal_id_for_beta)

    dps.resonant_or_extend("beta", query_axis_state={"X": 1.0, "N": 0.0})
    assert len(dps._warp_trials) == 1  # still just the one tracked trial


# ---- tier 3: no match at all -- falls through to check_and_extend ----

def test_no_match_and_no_query_axis_state_returns_none_fail_quiet():
    dps = _dps()
    result, tier = dps.resonant_or_extend("gamma", query_axis_state=None)
    assert result is None
    assert tier == "none"


def test_no_match_with_query_axis_state_falls_through_to_real_check_and_extend():
    """One existing, orthogonal crystal -- resonant_lookup finds no
    match for the query, so every call reaches the real
    check_and_extend(). GAP_PERSISTENCE_REQUIRED gates it exactly as it
    does for every other WARP-capable level -- unmodified by this
    directive. (A totally empty system instead trips
    check_and_extend()'s own 6th-axis-anomaly path -- WarpGenerator.
    generate() intentionally returns None there rather than firing, so
    this test seeds one unrelated crystal to exercise the ordinary
    persistent-gap path instead.)"""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.concept_index["alpha"] = "c1"

    from aurora_warp_protocol import GAP_PERSISTENCE_REQUIRED

    last_tier = None
    for i in range(GAP_PERSISTENCE_REQUIRED + 1):
        result, tier = dps.resonant_or_extend(
            "gamma", query_axis_state={"B": 1.0, "A": 1.0}, tick=i,
        )
        last_tier = tier
        if tier == "gap":
            assert result is not None
            break
    assert last_tier == "gap", "expected the persistent gap to eventually fire"


def test_no_match_before_persistence_threshold_returns_none():
    dps = _dps()
    result, tier = dps.resonant_or_extend("gamma", query_axis_state={"B": 1.0, "A": 1.0}, tick=0)
    assert result is None
    assert tier == "none"
