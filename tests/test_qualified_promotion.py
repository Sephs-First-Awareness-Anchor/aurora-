# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage D: qualified promotion (directive VIII; tests 4, 5, 6).  Real genealogy, real dream bridge.

Dream and simulation evidence takes part in the same developmental architecture and may promote a relationship, but the promotion
keeps what it was made of (kind of occurrence, distinct inputs, external demonstration); a replay is not new evidence; and a
simulation's success does not certify external effectiveness.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal.aurora_dream_genealogy_bridge import DreamEvidenceRecord, DreamGenealogyBridge
from aurora_internal.constraint_genealogy import (ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem,
                                                  constraint_link_from_dict)

HI, LO = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1)
BEFORE = {"X": 0.9, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1}
AFTER = {"X": 0.2, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1}


@pytest.fixture()
def gen(tmp_path):
    return ConstraintGenealogyLogger("qualified_promotion", config=GenealogyConfig(), output_dir=str(tmp_path / "g"))


@pytest.fixture()
def bridge(tmp_path):
    return DreamGenealogyBridge(storage_dir=str(tmp_path / "b"))


def pair(gen):
    a, b = list(gen.abilities)[:2]
    return a, b


def dream(gen, bridge, episode, rep_ids, after=None, source="dream_episode"):
    rec = DreamEvidenceRecord(
        evidence_id=f"e_{episode}", episode_id=episode, evidence_type="improvement", pressure_before=dict(BEFORE),
        pressure_after=dict(after or AFTER), trace_abilities=list(rep_ids), cost_total={"T": 0.01}, confidence=0.8,
        origin_tags={"source": source, "seed_lineage_id": episode})
    for e in bridge.format_for_genealogy([rec]):
        notes = dict(e["notes"])
        notes["source"] = source
        gen.observe(pressure_before=PressureVec(**e["pressure_before"]), trace=[TraceItem(**t) for t in e["trace"]],
                    pressure_after=PressureVec(**e["pressure_after"]), notes=notes)


def lived(gen, turn, rep_ids, stream="user_input", ticks=1):
    token = I.begin_input(turn, turn, stream_type=stream, loads={"X": 1.0}, t=1)
    try:
        for _ in range(ticks):
            gen.observe(HI, [TraceItem("ABILITY", r) for r in rep_ids], LO)
    finally:
        I.end_input(token)


def samples(gen, rep):
    return int((gen.abilities[rep].consequence_profile or {}).get("samples", 0))


# -- Test 6: replay versus new consequence ------------------------------------------------------------------------------------

def test_a_replayed_dream_credits_nothing_new_neither_pairstats_nor_the_consequence_profile(gen, bridge):
    a, b = pair(gen)
    dream(gen, bridge, "ep1", [a, b])
    ps0 = gen._pair_stats[(a, b)].count
    s0 = samples(gen, a)
    for _ in range(6):
        dream(gen, bridge, "ep1", [a, b])
    assert gen._pair_stats[(a, b)].count == ps0 and samples(gen, a) == s0
    assert gen._replays_skipped == 6


def test_the_replay_is_still_recorded_as_an_event_only_its_crediting_is_skipped(gen, bridge):
    a, b = pair(gen)
    dream(gen, bridge, "ep1", [a, b])
    n0 = gen.relief_event_count
    dream(gen, bridge, "ep1", [a, b])
    assert gen.relief_event_count == n0 + 1


def test_a_genuinely_new_interaction_with_the_same_representations_is_credited(gen, bridge):
    a, b = pair(gen)
    dream(gen, bridge, "ep1", [a, b])
    ps0, s0 = gen._pair_stats[(a, b)].count, samples(gen, a)
    dream(gen, bridge, "ep2", [a, b])                                                    # a different episode
    assert gen._pair_stats[(a, b)].count == ps0 + 1 and samples(gen, a) == s0 + 1
    dream(gen, bridge, "ep1", [a, b], after={"X": 0.1, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1})   # the same episode, a different result
    assert gen._pair_stats[(a, b)].count == ps0 + 2


def test_a_lived_input_is_never_treated_as_a_replay(gen):
    a, b = pair(gen)
    lived(gen, "turn_1", [a, b], ticks=6)                                                 # the identical tick six times, lived
    assert gen._pair_stats[(a, b)].count == 6 and gen._replays_skipped == 0


def test_the_replay_memory_survives_a_restart(gen, bridge, tmp_path):
    a, b = pair(gen)
    dream(gen, bridge, "ep1", [a, b])
    gen._write_events_recent_file()
    again = ConstraintGenealogyLogger("qualified_promotion", config=GenealogyConfig(), output_dir=str(tmp_path / "g"))
    n = again._pair_stats[(a, b)].count if (a, b) in again._pair_stats else 0
    dream(again, bridge, "ep1", [a, b])
    assert again._replays_skipped >= 1 and (again._pair_stats[(a, b)].count if (a, b) in again._pair_stats else 0) == n


# -- Test 4: internal capability promotion --------------------------------------------------------------------------------------

def _promote_from_dreams(gen, bridge, a, b, episodes=80):
    for k in range(episodes):
        after = dict(AFTER, X=0.2 + (k % 5) * 0.01)                                      # distinct results, so distinct consequences
        dream(gen, bridge, f"ep{k}", [a, b], after=after)
        if (a, b) in gen._links_by_parents:
            return k + 1
    return None


def test_a_relationship_that_first_exists_in_dreams_can_be_promoted_and_says_it_is_internal_only(gen, bridge):
    a, b = pair(gen)
    used = _promote_from_dreams(gen, bridge, a, b)
    assert used is not None, "distinct dream consequences must still be able to promote a relationship"
    link = gen.links[gen._links_by_parents[(a, b)]]
    q = link.evidence_qualification
    assert q["ledger"] == "recorded" and q["internal_only"] is True and q["externally_demonstrated"] is False
    assert "lived" not in q["by_kind"] and q["by_kind"]["hypothetical"]["n_inputs"] >= 1


def test_the_qualification_survives_serialisation_and_old_links_without_it_still_load(gen, bridge):
    a, b = pair(gen)
    assert _promote_from_dreams(gen, bridge, a, b) is not None
    link = gen.links[gen._links_by_parents[(a, b)]]
    again = constraint_link_from_dict(link.to_dict())
    assert again.evidence_qualification == link.evidence_qualification
    legacy = link.to_dict()
    legacy.pop("evidence_qualification")
    assert constraint_link_from_dict(legacy).evidence_qualification is None


def test_a_link_with_both_lived_and_dreamed_evidence_reports_both(gen, bridge):
    a, b = pair(gen)
    for k in range(40):
        if k % 2:
            lived(gen, f"turn_{k}", [a, b])
        else:
            dream(gen, bridge, f"ep{k}", [a, b], after=dict(AFTER, X=0.2 + (k % 5) * 0.01))
        if (a, b) in gen._links_by_parents:
            break
    q = gen.links[gen._links_by_parents[(a, b)]].evidence_qualification
    assert q["by_kind"]["lived"]["n_inputs"] >= 1 and q["by_kind"]["hypothetical"]["n_inputs"] >= 1
    assert q["internal_only"] is False


def test_replaying_one_dream_cannot_promote_a_relationship_by_repetition_alone(gen, bridge):
    a, b = pair(gen)
    for _ in range(300):
        dream(gen, bridge, "ep_only", [a, b])
    assert (a, b) not in gen._links_by_parents and gen._pair_stats[(a, b)].count == 1


def test_a_pair_with_no_recorded_ledger_is_unattributed_not_presumed(gen):
    assert gen.pair_evidence("NOT", "SEEN") == {"ledger": "unattributed"}


# -- Test 5: simulation disagreement -----------------------------------------------------------------------------------------------

def test_a_simulation_that_predicted_success_is_kept_while_an_external_contradiction_revises_applicability(gen, bridge):
    a, = list(gen.abilities)[:1]
    dream(gen, bridge, "sim1", [a], source="simulation")                                  # the simulation predicts success
    before = gen.representation_evidence(a)
    assert before["applicability"] == "internal_only" and before["by_kind"]["hypothetical"]["relief"]["X"] > 0
    token = I.begin_input("test_1", "the external test", stream_type="sensor_data", loads={"X": 1.0}, t=1)   # perceived: external
    try:
        gen.observe(LO, [TraceItem("ABILITY", a)], HI)                                    # the world: the pressure went UP
    finally:
        I.end_input(token)
    after = gen.representation_evidence(a)
    assert after["applicability"] == "external_contradicted" and after["by_kind"]["lived"]["n_external"] == 1
    assert after["by_kind"]["hypothetical"] == before["by_kind"]["hypothetical"]          # the simulation history is retained untouched


def test_external_success_after_a_simulation_is_external_support_and_mixed_when_both_occur(gen, bridge):
    a, = list(gen.abilities)[:1]
    dream(gen, bridge, "sim1", [a], source="simulation")
    for k, (b4, af) in enumerate([(HI, LO), (LO, HI)]):
        token = I.begin_input(f"test_{k}", f"t{k}", stream_type="sensor_data", loads={"X": 1.0}, t=1)
        try:
            gen.observe(b4, [TraceItem("ABILITY", a)], af)
        finally:
            I.end_input(token)
        if k == 0:
            assert gen.representation_evidence(a)["applicability"] == "external_supported"
    assert gen.representation_evidence(a)["applicability"] == "external_mixed"


def test_hearing_something_is_lived_but_is_not_an_external_demonstration(gen):
    a, = list(gen.abilities)[:1]
    lived(gen, "turn_1", [a])                                                             # heard, not perceived/acted/tested
    ev = gen.representation_evidence(a)
    assert ev["by_kind"]["lived"]["n_external"] == 0 and ev["applicability"] == "none"


def test_nothing_the_qualification_records_changes_any_gate_or_profile(gen, bridge, tmp_path):
    """The same lived-only sequence on two genealogies yields identical profiles and pair stats; identity machinery only adds records."""
    other = ConstraintGenealogyLogger("qp_b", config=GenealogyConfig(), output_dir=str(tmp_path / "gb"))
    a, b = pair(gen)
    for k in range(5):
        lived(gen, f"turn_{k}", [a, b])
        for _ in range(1):
            other.observe(HI, [TraceItem("ABILITY", a), TraceItem("ABILITY", b)], LO)
    assert gen.abilities[a].consequence_profile == other.abilities[a].consequence_profile
    assert gen._pair_stats[(a, b)].count == other._pair_stats[(a, b)].count
