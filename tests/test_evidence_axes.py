# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A144 revised (directive: Developmental Evidence, Simulated Experience, and Consequence-Grounded Promotion).

Occurrence, basis, ancestry, context, attribution, consequence and scope are kept apart; dreams and simulations are
real occurrences whose represented worlds are not external; a replay is not new evidence; a genuinely new
consequence is.  Directive IX tests 1-7 are expressed here at the contract level (isolated testing, not integrated
and not on a device).
"""
from __future__ import annotations

import hashlib
import json
import random

import pytest

from aurora_internal import evidence_qualification as Q


def ev(subject="a|b|c", basis=None, **kw):
    kw.setdefault("t", 1)
    return Q.make_event(subject, basis, **kw)


# -- violations(): conflicting duplicate ids (Codex P2 on #253) ---------------------------------------------------

def test_violations_reports_a_laundered_duplicate_id_instead_of_keeping_the_last_version():
    real = ev(basis="supposed", occurrence="dreamed")
    forged = dict(real, basis="told", occurrence="heard")          # same id, an example presented as testimony
    assert Q.violations([real], [forged, real])                     # the last-wins dict comprehension passed this
    assert Q.violations([real], [real, forged])
    assert any("different ways in the after stream" in v for v in Q.violations([real], [forged, real]))


def test_violations_reports_conflicting_duplicates_already_in_before_and_identical_duplicates_are_fine():
    real = ev(basis="told", occurrence="heard")
    other = dict(real, by="someone else")
    assert any("before stream" in v for v in Q.violations([real, other], [real, other]))
    assert Q.violations([real, real], [real]) == []                 # the same event twice is one event
    assert Q.violations([real], [real, real, real]) == []


def test_every_version_of_a_duplicated_before_event_must_survive():
    a = ev(basis="told", occurrence="heard")
    b = dict(a, by="second")
    out = Q.violations([a, b], [a])
    assert any("rewritten" in v or "was told" in v for v in out)


# -- identity: stable across replay, distinct for separate occurrences, stable across schema growth -----------

def test_the_same_occurrence_replayed_has_the_same_id_and_a_separate_one_has_another():
    a = ev(basis="told", by="sunni", occurrence="heard")
    assert a["id"] == ev(basis="told", by="sunni", occurrence="heard")["id"]
    assert a["id"] != ev(basis="told", by="sunni", occurrence="heard", t=2)["id"]
    assert a["id"] != ev(basis="told", by="sunni", occurrence="heard", nonce="again")["id"]


def test_an_event_written_before_the_new_fields_keeps_its_id():
    legacy = {"subject": "a|b|c", "basis": "told", "negated": False, "by": "sunni", "t": 5, "derived_from": []}
    expected = hashlib.blake2b(json.dumps(legacy, sort_keys=True).encode("utf-8"), digest_size=10).hexdigest()
    assert Q.make_event("a|b|c", "told", by="sunni", t=5)["id"] == expected


def test_new_axes_are_part_of_identity_so_a_dream_and_a_hearing_of_the_same_words_are_different_events():
    heard = ev(basis="supposed", occurrence="heard")
    dreamed = ev(basis="supposed", occurrence="dreamed")
    assert heard["id"] != dreamed["id"]


# -- occurrence and basis are different questions (directive VI table) --------------------------------------------

@pytest.mark.parametrize("occ,basis", [("dreamed", "told"), ("dreamed", "observed"), ("dreamed", "corrected"),
                                       ("simulated", "observed"), ("simulated", "told"), ("imagined", "observed"),
                                       ("derived", "told"), ("perceived", "told"), ("tested", "told")])
def test_an_occurrence_cannot_carry_content_stronger_than_it_is(occ, basis):
    with pytest.raises(ValueError):
        Q.make_event("a|b|c", basis, t=1, occurrence=occ, derived_from=["x"] if occ == "derived" else ())


@pytest.mark.parametrize("occ", ["dreamed", "simulated", "imagined"])
def test_a_hypothetical_occurrence_cannot_claim_the_external_world(occ):
    with pytest.raises(ValueError):
        ev(occurrence=occ, context={"world": "external"})
    ok = ev(occurrence=occ, context={"world": {"dreamed": "dreamed", "simulated": "simulated", "imagined": "imagined"}[occ]})
    assert ok["basis"] == "supposed" and Q.fold([ok])["n"] == 0


def test_the_basis_defaults_to_what_the_occurrence_is_and_to_unknown_when_nothing_is_said():
    assert ev(occurrence="heard")["basis"] == "told"
    assert ev(occurrence="perceived")["basis"] == "observed"
    assert ev(occurrence="dreamed")["basis"] == "supposed"
    assert ev(occurrence="derived", derived_from=["p"])["basis"] == "inferred"
    assert ev()["basis"] == "unknown"                               # never told


def test_hearing_is_an_occurrence_and_what_was_said_is_testimony_not_observed_fact():
    said = ev(occurrence="heard", by="sunni")
    rec = Q.fold([said])
    assert rec["occurrence"] == {"heard": 1} and rec["basis"] == {"told": 1} and Q.verdict(rec) == "held"
    suppose = ev("m|l|t", occurrence="heard", basis="supposed")      # heard as an example: still hearing, content hypothetical
    assert Q.verdict(Q.fold([suppose])) == "supposed"
    assert Q.occurrence_of_stream("user_input") == "heard" and "observed" not in Q.OCCURRENCES["heard"]


def test_a_recollection_never_adds_evidence_and_a_recalled_dream_does_not_confirm_its_contents():
    told = ev(occurrence="heard", t=1)
    recall = ev(occurrence="recalled", basis="told", ancestry=[told["id"]], t=2)
    rec = Q.fold([told, recall])
    assert rec["n"] == 1 and rec["recalled"] == 1                   # recalling is real; it is not a second testimony
    dream = ev("x|y|z", occurrence="dreamed", t=1)
    recalled_dream = ev("x|y|z", occurrence="recalled", basis="supposed", ancestry=[dream["id"]], t=2)
    assert Q.verdict(Q.fold([dream, recalled_dream])) == "supposed"


# -- legacy: carried standing is kept, labelled, and clarified by genuine evidence --------------------------------

def test_carried_legacy_evidence_keeps_its_standing_but_is_labelled_unattributed():
    carried = [ev(carried=True, t=i, nonce=str(i)) for i in range(3)]
    rec = Q.fold(carried)
    q = Q.qualification(rec)
    assert q["verdict"] == "held" and q["unattributed_standing"] and q["verdict_attributed"] == "unsaid"
    assert rec["basis"] == {"unknown": 3}                            # never relabelled told


def test_new_unknown_evidence_never_counts_and_only_legacy_may_carry_standing():
    fresh = [ev(basis="hearsay", t=i, nonce=str(i)) for i in range(5)]
    q = Q.qualification(Q.fold(fresh))
    assert q["verdict"] == "unsaid" and not q["unattributed_standing"]
    with pytest.raises(ValueError):
        ev(basis="told", carried=True)
    with pytest.raises(ValueError):
        ev(occurrence="heard", basis="unknown", carried=True)


def test_genuine_evidence_clarifies_carried_standing_and_a_correction_settles_it():
    carried = [ev(carried=True, t=i, nonce=str(i)) for i in range(2)]
    denial = ev(basis="told", negated=True, t=10, occurrence="heard")
    rec = Q.fold(carried + [denial])
    assert Q.verdict(rec) == "held"                                  # 2 carried held vs 1 denial: standing not flipped by one voice
    assert Q.qualification(rec)["verdict_attributed"] == "denied"    # what the attributed evidence alone says is visible
    assert Q.qualification(rec)["contradicted"]
    corrected = Q.fold(carried + [denial, ev(basis="corrected", negated=True, t=11, occurrence="heard")])
    assert Q.verdict(corrected) == "denied"


def test_the_predicate_view_reports_the_unattributed_part_of_a_stores_standing():
    q = Q.qualification_of_predicate({"n": 5, "denied": 0, "basis": {"told": 2}, "history": []})
    assert q["unattributed_n"] == 3 and q["unattributed_standing"] and q["verdict"] == "held"
    clean = Q.qualification_of_predicate({"n": 2, "denied": 0, "basis": {"told": 1, "observed": 1}, "history": []})
    assert clean["unattributed_n"] == 0 and not clean["unattributed_standing"]


# -- ancestry: traced, partial, unattributed, never manufactured (Tests 1-3) -------------------------------------

def _lived(n=2):
    return [ev(f"exp{i}|did|thing", occurrence="perceived", t=i, nonce=str(i), context={"world": "external"}) for i in range(n)]


def test_experiential_precedence_a_dream_traces_back_to_the_lived_events_it_came_from():
    lived = _lived(3)
    dream = ev("d|r|m", occurrence="dreamed", t=10, ancestry=[lived[0]["id"], lived[2]["id"]],
               context={"world": "dreamed"})
    g = Q.grounding(lived + [dream], dream["id"])
    assert g["lived_roots"] == sorted([lived[0]["id"], lived[2]["id"]]) and not g["ungrounded"] and g["status"] == "traced"
    assert lived[1]["id"] not in g["lived_roots"]                    # only what it actually came from


def test_a_dream_does_not_create_the_experiences_it_arose_from():
    lived = _lived(2)
    before = Q.merge(lived)
    dream = ev("d|r|m", occurrence="dreamed", t=10, ancestry=[lived[0]["id"]], context={"world": "dreamed"})
    after = Q.merge(before, [dream])
    assert Q.violations(before, after) == []
    assert [e for e in after if e.get("occurrence") in Q.LIVED] == before     # no lived event was added by dreaming
    assert Q.fold([dream])["n"] == 0                                           # and the dream itself counts as nothing said


def test_novel_recombination_is_preserved_without_changing_the_provenance_of_its_constituents():
    a = ev("mara|likes|tea", occurrence="heard", by="sunni", t=1)
    b = ev("tea|needs|water", occurrence="heard", by="sunni", t=2)
    dream = ev("mara|needs|water", occurrence="dreamed", t=9, ancestry=[a["id"], b["id"]], context={"world": "dreamed"},
               consequence={"target": "rel:mara-water", "change": "related", "attribution": [a["id"], b["id"]]})
    log = [a, b, dream]
    assert Q.fold([a]) == Q.fold([x for x in log if x["subject"] == a["subject"]])    # constituents unchanged
    assert Q.fold([b]) == Q.fold([x for x in log if x["subject"] == b["subject"]])
    assert Q.demonstration(log, "rel:mara-water")["applicability"] == "internal_only"
    assert Q.fold([dream])["supposed"] == 1                                            # not credited as something said


def test_without_supported_ancestry_nothing_is_invented_and_the_uncertainty_is_what_is_reported():
    dream = ev("x|y|z", occurrence="dreamed", t=1, context={"world": "dreamed"})
    log = [dream]
    g = Q.grounding(log, dream["id"])
    assert g["ungrounded"] and g["lived_roots"] == [] and g["status"] == "unattributed" and g["dangling"] == []
    assert Q.merge(log) == log                                       # grounding made up no events
    named_but_missing = ev("x|y|z", occurrence="dreamed", t=2, ancestry=["gone"], ancestry_status="partial",
                           context={"world": "dreamed"})
    g2 = Q.grounding([named_but_missing], named_but_missing["id"])
    assert g2["dangling"] == ["gone"] and g2["ungrounded"] and g2["status"] == "partial"


def test_ancestry_cannot_be_declared_traced_when_nothing_is_traced():
    with pytest.raises(ValueError):
        ev(occurrence="dreamed", ancestry_status="traced")


def test_grounding_follows_premises_and_reports_a_cycle_without_looping():
    root = ev("r|r|r", occurrence="heard", t=1)
    mid = ev("m|m|m", occurrence="derived", t=2, derived_from=[root["id"]])
    top = ev("t|t|t", occurrence="dreamed", t=3, ancestry=[mid["id"]], context={"world": "dreamed"})
    assert Q.grounding([root, mid, top], top["id"])["lived_roots"] == [root["id"]]
    a = {"id": "A", "subject": "s", "basis": "supposed", "t": 1, "ancestry": ["B"]}
    b = {"id": "B", "subject": "s", "basis": "supposed", "t": 2, "ancestry": ["A"]}
    assert Q.grounding([a, b], "A")["cycle"] is True


# -- consequences: replay vs new, internal vs external (Tests 4-6) -----------------------------------------------

def _dream_consequence(change="useful", attribution=("p", "q"), t=1, **kw):
    return ev("d|r|m", occurrence="dreamed", t=t, context={"world": "dreamed", "domain": kw.pop("domain", "language")},
              consequence={"target": "cap:link", "change": change, "attribution": list(attribution)}, **kw)


def test_internal_promotion_evidence_is_not_external_verification():
    d = Q.demonstration([_dream_consequence()], "cap:link")
    assert d["internal_demonstrated"] and d["external_supported"] == 0 and d["applicability"] == "internal_only"


def test_replaying_a_dream_or_rerunning_it_to_the_same_result_is_not_new_independent_evidence():
    first = _dream_consequence(t=1)
    d_replay = Q.demonstration([first, first, first], "cap:link")
    assert d_replay["independent"] == 1 and d_replay["occurrences"] == 1
    rerun = [_dream_consequence(t=t) for t in (1, 2, 3, 4)]          # re-dreamed at other times, same result
    d = Q.demonstration(rerun, "cap:link")
    assert d["occurrences"] == 4 and d["independent"] == 1 and d["replays_ignored"] == 3


def test_a_genuinely_new_interaction_producing_a_distinct_consequence_is_new_evidence():
    base = [_dream_consequence(t=1), _dream_consequence(t=2)]
    new = _dream_consequence(change="useful in a new way", attribution=("p", "q", "r"), t=3)
    d = Q.demonstration(base + [new], "cap:link")
    assert d["independent"] == 2 and d["occurrences"] == 3


def test_a_recollection_demonstrates_nothing():
    original = _dream_consequence()
    recalled = ev("d|r|m", occurrence="recalled", basis="supposed", t=5, ancestry=[original["id"]],
                  context={"world": "dreamed"}, consequence={"target": "cap:link", "change": "other", "attribution": ["z"]})
    assert Q.demonstration([original, recalled], "cap:link")["independent"] == 1


def test_a_simulation_predicting_success_then_failing_externally_keeps_both_and_revises_applicability():
    sim = ev("plan|works|-", occurrence="simulated", t=1, context={"world": "simulated", "domain": "reach"},
             consequence={"target": "cap:reach", "change": "predicted success", "attribution": ["m1"]})
    assert Q.demonstration([sim], "cap:reach")["applicability"] == "internal_only"
    test = ev("plan|works|-", occurrence="tested", t=2, negated=True, context={"world": "external", "domain": "reach"},
              consequence={"target": "cap:reach", "change": "predicted success", "attribution": ["m1"]})
    d = Q.demonstration([sim, test], "cap:reach")
    assert d["applicability"] == "external_contradicted" and d["external_contradicted"] == 1
    assert d["by_world"] == {"simulated": 1, "external": 1} and d["internal_demonstrated"]   # the simulation's history stays
    ok = ev("plan|works|-", occurrence="tested", t=3, context={"world": "external", "domain": "reach"},
            consequence={"target": "cap:reach", "change": "second attempt", "attribution": ["m2"]})
    assert Q.demonstration([sim, test, ok], "cap:reach")["applicability"] == "external_mixed"


def test_external_support_needs_a_lived_observed_test_in_the_external_world_not_testimony_or_a_dream():
    said = ev("cap|works|-", occurrence="heard", t=1, context={"world": "external"},
              consequence={"target": "cap:x", "change": "works", "attribution": []})
    assert Q.demonstration([said], "cap:x")["applicability"] == "none"       # someone said it works
    tested = ev("cap|works|-", occurrence="tested", t=2, context={"world": "external"},
                consequence={"target": "cap:x", "change": "works", "attribution": []})
    assert Q.demonstration([said, tested], "cap:x")["applicability"] == "external_supported"


def test_generalisation_needs_distinct_domains_and_open_attribution_stays_visible():
    d = Q.demonstration([_dream_consequence(domain="language"), _dream_consequence(domain="reasoning", t=2)], "cap:link")
    assert d["generalized"] and d["domains"] == ["language", "reasoning"] and d["attribution_open"]
    done = ev("d|r|m", occurrence="dreamed", t=1, context={"world": "dreamed"},
              consequence={"target": "cap:k", "change": "c", "attribution": ["a"], "attribution_complete": True})
    assert not Q.demonstration([done], "cap:k")["attribution_open"]


# -- provenance integrity through the trips a durable log takes (Test 7, contract level) -----------------------------

def test_every_basis_survives_json_merge_and_replay_unchanged():
    one_of_each = [ev("a|b|c", occurrence="heard", t=1), ev("a|b|c", occurrence="perceived", t=2),
                   ev("a|b|c", occurrence="dreamed", t=3), ev("a|b|c", occurrence="derived", t=4, derived_from=["p"]),
                   ev("a|b|c", basis="corrected", occurrence="heard", t=5, negated=True), ev("a|b|c", basis="hearsay", t=6),
                   ev("a|b|c", carried=True, t=7)]
    trip = json.loads(json.dumps(one_of_each))
    assert Q.violations(one_of_each, trip + trip) == []
    assert Q.violations(one_of_each, Q.merge(trip)) == []
    assert [e["basis"] for e in Q.merge(trip)] == ["told", "observed", "supposed", "inferred", "corrected", "unknown", "unknown"]
    assert Q.fold(trip) == Q.fold(list(reversed(trip)))


def test_a_deferral_that_relabels_a_dream_as_experience_is_caught():
    dream = ev(occurrence="dreamed", t=1)
    laundered = dict(dream, occurrence="perceived", basis="observed")
    assert any("was supposed and is now observed" in v for v in Q.violations([dream], [laundered]))
    # and the laundered event is not one of the events the contract would have accepted as a dream
    with pytest.raises(ValueError):
        Q.make_event("a|b|c", "observed", t=1, occurrence="dreamed")


def test_order_independence_and_idempotence_hold_with_every_axis_present():
    rng = random.Random(21)
    for _ in range(30):
        evs = []
        for i in range(rng.randint(2, 10)):
            occ = rng.choice(["heard", "perceived", "dreamed", "simulated", "tested", "recalled", ""])
            basis = None if occ else rng.choice(["told", "unknown"])
            evs.append(ev("a|b|c", basis=basis if not occ else None, occurrence=occ, t=i, nonce=str(i),
                          negated=rng.random() < 0.3,
                          context={"world": "dreamed"} if occ == "dreamed" else {}))
        shuffled = list(evs)
        rng.shuffle(shuffled)
        assert Q.fold(evs) == Q.fold(shuffled) == Q.fold(evs + evs)


def test_the_streams_the_code_really_has_map_to_occurrences_and_the_unclear_ones_stay_unspecified():
    assert Q.occurrence_of_stream("sensor_data") == "perceived" and Q.occurrence_of_stream("knowledge_feed") == "read"
    assert Q.occurrence_of_stream("synthetic_lineage") == "derived"
    for unclear in ("system_event", "exploration", "self_reflection", "", "neither"):
        assert Q.occurrence_of_stream(unclear) == "", unclear
    # dream replay arrives as a knowledge_feed with internal_origin="dream_replay" (aurora_dream_trainer): the origin wins
    assert Q.occurrence_of_stream("knowledge_feed", "dream_replay") == "dreamed"
    assert Q.occurrence_of_stream("knowledge_feed", "something_else") == "read"
    # and a dreamed occurrence can never then carry told/observed content
    with pytest.raises(ValueError):
        Q.make_event("a|b|c", "told", t=1, occurrence=Q.occurrence_of_stream("knowledge_feed", "dream_replay"))
