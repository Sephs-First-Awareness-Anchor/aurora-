# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 1 (2026-07-24, ratified).

CrystalProcessingSystem grows a cosine-similarity resonance graph between
crystals (_crystal_vector, _update_crystal_links, self.crystal_links) --
the same shape EnergyRegulatorSystem._update_links_for_facet() already
proved out for facets, lifted one layer up -- plus resonant_lookup(), a
second-tier retrieval-by-relatedness path alongside the exact-match
concept_index.

resonant_lookup()'s query-vector interface was the one open decision:
ratified as "thread the caller's actual IVM position.phases through"
(NOT a hash of the concept string). These tests exercise that contract
directly: no query_axis_state -> fail-quiet empty list, never a
fabricated hash-based guess.

Tested against directly-constructed Crystal objects (no IVMEnvelope
fixture exists anywhere in the test suite to reuse, and process()'s new
wiring is a trivial try/except around the same method these tests cover
directly).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dimensional_systems import CrystalProcessingSystem, Crystal, EvolutionTracker  # noqa: E402


def _dps():
    return CrystalProcessingSystem(tracker=EvolutionTracker())


def _crystal(cid, concept, sig=None, mean=None):
    c = Crystal(crystal_id=cid, concept=concept)
    if sig is not None:
        c.constraint_signature = dict(sig)
    if mean is not None:
        c.axis_mean = dict(mean)
    return c


# ---- _crystal_vector ----

def test_crystal_vector_none_when_no_signature_or_mean():
    dps = _dps()
    c = _crystal("c1", "alpha")
    assert dps._crystal_vector(c) is None


def test_crystal_vector_fuses_signature_and_mean_equal_weight():
    dps = _dps()
    c = _crystal("c1", "alpha", sig={"X": 1.0}, mean={"X": 0.0})
    vec = dps._crystal_vector(c)
    assert vec == {"X": 0.5}


def test_crystal_vector_unions_axes_missing_from_either_side():
    dps = _dps()
    c = _crystal("c1", "alpha", sig={"X": 1.0}, mean={"N": 0.4})
    vec = dps._crystal_vector(c)
    assert vec == {"X": 0.5, "N": 0.2}


# ---- _update_crystal_links ----

def test_update_crystal_links_noop_for_unknown_crystal_id():
    dps = _dps()
    dps._update_crystal_links("does_not_exist")
    assert dps.crystal_links == {}


def test_update_crystal_links_noop_when_source_has_no_vector():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha")
    dps._update_crystal_links("c1")
    assert "c1" not in dps.crystal_links


def test_update_crystal_links_finds_similar_crystal():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "beta", sig={"X": 0.9, "N": 0.1})
    dps._update_crystal_links("c1")
    assert "c1" in dps.crystal_links
    assert "c2" in dps.crystal_links["c1"]
    weight = dps.crystal_links["c1"]["c2"]
    assert 0.0 < weight <= 1.0


def test_update_crystal_links_weights_sum_to_one():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "beta", sig={"X": 0.9, "N": 0.1})
    dps.crystals["c3"] = _crystal("c3", "gamma", sig={"X": 0.8, "N": 0.2})
    dps._update_crystal_links("c1")
    total = sum(dps.crystal_links["c1"].values())
    assert abs(total - 1.0) < 1e-9


def test_update_crystal_links_ignores_mismatched_axis_keysets():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "beta", sig={"B": 0.9, "A": 0.1})
    dps._update_crystal_links("c1")
    assert "c1" not in dps.crystal_links


def test_update_crystal_links_excludes_below_floor_similarity():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "opposite", sig={"X": -1.0, "N": 0.0})
    dps._update_crystal_links("c1", floor=0.9)
    assert "c1" not in dps.crystal_links or "c2" not in dps.crystal_links.get("c1", {})


def test_update_crystal_links_removes_stale_entry_when_no_longer_similar():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "beta", sig={"X": 0.9, "N": 0.1})
    dps._update_crystal_links("c1")
    assert "c1" in dps.crystal_links

    # Now c1 loses its vector entirely (simulating a reset) -- the stale
    # link entry must be cleaned up, not left dangling with old weights.
    dps.crystals["c1"].constraint_signature = None
    dps.crystals["c1"].axis_mean = {}
    dps._update_crystal_links("c1")
    assert "c1" not in dps.crystal_links


# ---- resonant_lookup ----

def test_resonant_lookup_returns_empty_without_query_axis_state():
    """Ratified contract: no fabricated hash-based fallback. A caller
    with no real live axis position gets nothing, not a guess."""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    assert dps.resonant_lookup("unknown_concept") == []
    assert dps.resonant_lookup("unknown_concept", query_axis_state={}) == []
    assert dps.resonant_lookup("unknown_concept", query_axis_state=None) == []


def test_resonant_lookup_finds_related_crystal_above_threshold():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c2"] = _crystal("c2", "beta", sig={"X": 0.0, "N": 1.0})

    results = dps.resonant_lookup("unknown", query_axis_state={"X": 1.0, "N": 0.0}, threshold=0.5)
    assert len(results) == 1
    crystal, score = results[0]
    assert crystal.concept == "alpha"
    assert score > 0.99


def test_resonant_lookup_excludes_exact_concept_match():
    """This is the second-tier path -- a caller already failed the exact
    match, so resonant_lookup must not just hand the same concept back."""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0, "N": 0.0})

    results = dps.resonant_lookup("alpha", query_axis_state={"X": 1.0, "N": 0.0})
    assert results == []


def test_resonant_lookup_respects_threshold():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "orthogonal", sig={"X": 0.0, "N": 1.0})

    results = dps.resonant_lookup("unknown", query_axis_state={"X": 1.0, "N": 0.0}, threshold=0.55)
    assert results == []


def test_resonant_lookup_ranks_descending_and_respects_top_k():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "close", sig={"X": 1.0, "N": 0.05})
    dps.crystals["c2"] = _crystal("c2", "closer", sig={"X": 1.0, "N": 0.0})
    dps.crystals["c3"] = _crystal("c3", "closest", sig={"X": 1.0, "N": -0.02})

    results = dps.resonant_lookup("unknown", query_axis_state={"X": 1.0, "N": 0.0},
                                   threshold=0.5, top_k=2)
    assert len(results) == 2
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_resonant_lookup_ignores_crystal_with_no_vector():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "unprocessed")  # no sig, no mean
    results = dps.resonant_lookup("unknown", query_axis_state={"X": 1.0})
    assert results == []


def test_resonant_lookup_ignores_mismatched_axis_keyset():
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"B": 1.0, "A": 0.0})
    results = dps.resonant_lookup("unknown", query_axis_state={"X": 1.0, "N": 0.0})
    assert results == []


# ---- process() / process_concepts() wiring stays alive-but-silent ----

def test_process_wiring_does_not_raise_when_crystal_links_update_fails():
    """The try/except around _update_crystal_links() in process() and
    process_concepts() must never surface -- this directly exercises
    that the method itself tolerates being called on a system with only
    one crystal (no peers to compare against) without raising."""
    dps = _dps()
    dps.crystals["c1"] = _crystal("c1", "alpha", sig={"X": 1.0})
    dps._update_crystal_links("c1")  # only crystal in the system, no peers
    assert "c1" not in dps.crystal_links
