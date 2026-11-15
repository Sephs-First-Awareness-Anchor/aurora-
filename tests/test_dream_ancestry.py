# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage C: dream ancestry (directive VIII, tests 1, 2, 3 and 6 at the integrated level).

Real genealogy, real dream bridge formatting.  Dreams trace back to the lived inputs that credited the representations they
use; they never create lived history, never credit themselves with the experiences that supplied their material, and
replaying one dream is not new independent evidence.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal.aurora_dream_genealogy_bridge import DreamEvidenceRecord, DreamGenealogyBridge
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem

HI, LO = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1)


@pytest.fixture()
def gen(tmp_path):
    return ConstraintGenealogyLogger("dream_ancestry", config=GenealogyConfig(), output_dir=str(tmp_path / "g"))


@pytest.fixture()
def bridge(tmp_path):
    return DreamGenealogyBridge(storage_dir=str(tmp_path / "b"))


def reps(gen, n):
    return list(gen.abilities)[:n]


def live(gen, turn, rep_ids, text=None):
    token = I.begin_input(turn, text or turn, loads={"X": 1.0}, t=1)
    try:
        for _ in range(2):
            gen.observe(HI, [TraceItem("ABILITY", r) for r in rep_ids], LO)
        return I.current_event()["id"]
    finally:
        I.end_input(token)


def dream(gen, bridge, episode, rep_ids, evidence_id="e1"):
    """Push one dream episode's evidence through the dream bridge's own formatting into observe, as the orchestrator does."""
    rec = DreamEvidenceRecord(
        evidence_id=evidence_id, episode_id=episode, evidence_type="improvement",
        pressure_before={"X": 0.9, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
        pressure_after={"X": 0.2, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
        pressure_relief={"X": 0.7}, trace_abilities=list(rep_ids),
        cost_total={"T": 0.01}, risk_estimate=0.01, confidence=0.8,
        origin_tags={"source": "dream_episode", "evidence_class": "improvement", "seed_lineage_id": episode})
    for entry in bridge.format_for_genealogy([rec]):
        gen.observe(pressure_before=PressureVec(**entry["pressure_before"]), trace=[TraceItem(**t) for t in entry["trace"]],
                    pressure_after=PressureVec(**entry["pressure_after"]), state_sig_before=entry["state_sig_before"],
                    state_sig_after=entry["state_sig_after"], notes=dict(entry["notes"]))
    return I.identity_from_notes(rec.origin_tags)["id"]


# -- Test 1: experiential precedence ------------------------------------------------------------------------------------

def test_a_dream_traces_back_to_the_lived_inputs_that_supplied_its_material(gen, bridge):
    a, b = reps(gen, 2)
    lived_a = live(gen, "turn_a", [a])
    lived_b = live(gen, "turn_b", [b])
    dream(gen, bridge, "ep1", [a, b])
    anc = gen.ancestry_of([a, b])
    assert anc["status"] == "traced" and set(anc["lived_inputs"]) == {lived_a, lived_b}


def test_dreaming_creates_no_lived_history(gen, bridge):
    a, = reps(gen, 1)
    lived = live(gen, "turn_a", [a])
    before = gen.representation_evidence(a)
    dream_id = dream(gen, bridge, "ep1", [a])
    for _ in range(3):
        dream(gen, bridge, f"ep_more_{_}", [a])
    after = gen.representation_evidence(a)
    assert after["lived_inputs"] == before["lived_inputs"] == [lived] and after["lived_total"] == before["lived_total"] == 1
    assert dream_id not in after["lived_inputs"]
    assert "hypothetical" in after["by_kind"] and after["by_kind"]["lived"]["ticks"] == before["by_kind"]["lived"]["ticks"]


def test_the_dream_is_a_dreamed_occurrence_with_its_own_identity(gen, bridge):
    a, = reps(gen, 1)
    live(gen, "turn_a", [a])
    dream_id = dream(gen, bridge, "ep1", [a])
    assert gen._input_events[dream_id]["occurrence"] == "dreamed" and gen._input_events[dream_id]["turn_id"] == "dream:ep1"


# -- Test 2: novel recombination ---------------------------------------------------------------------------------------

def test_a_relationship_that_first_appears_in_a_dream_keeps_each_constituents_own_provenance(gen, bridge):
    a, b = reps(gen, 2)
    exp_a = live(gen, "turn_a", [a])
    exp_b = live(gen, "turn_b", [b])
    for k in range(6):
        dream(gen, bridge, f"ep{k}", [a, b])                              # they were never active together in anything lived
    assert gen.representation_evidence(a)["lived_inputs"] == [exp_a]
    assert gen.representation_evidence(b)["lived_inputs"] == [exp_b]
    anc = gen.ancestry_of([a, b])
    assert set(anc["lived_inputs"]) == {exp_a, exp_b} and anc["status"] == "traced"
    for r in (a, b):                                                       # the dreams are recorded as dreams, not as their experience
        assert gen.representation_evidence(r)["by_kind"]["hypothetical"]["n_inputs"] == 6


# -- Test 3: a dream element with no experiential ancestry -----------------------------------------------------------------

def test_an_element_with_no_recorded_ancestry_stays_unattributed_and_no_history_is_made_for_it(gen, bridge):
    a, ungrounded = reps(gen, 2)
    lived = live(gen, "turn_a", [a])
    dream(gen, bridge, "ep1", [a, ungrounded])
    ev = gen.representation_evidence(ungrounded)
    assert ev["ancestry"] == "unattributed" and ev["lived_inputs"] == [] and "lived" not in ev["by_kind"]
    anc = gen.ancestry_of([a, ungrounded])
    assert anc["status"] == "partial" and anc["unattributed"] == [ungrounded] and anc["lived_inputs"] == [lived]


def test_a_representation_the_ledger_never_saw_is_unattributed_not_traced(gen):
    assert gen.representation_evidence("NOT:SEEN")["ancestry"] == "unattributed"
    assert gen.ancestry_of(["NOT:SEEN"])["status"] == "unattributed"


# -- Test 6: replay versus a genuinely new interaction -----------------------------------------------------------------------

def test_replaying_a_dream_is_the_same_input_and_a_new_one_is_a_new_input(gen, bridge):
    a, b = reps(gen, 2)
    live(gen, "turn_a", [a]); live(gen, "turn_b", [b])
    first = dream(gen, bridge, "epX", [a, b])
    for _ in range(4):
        assert dream(gen, bridge, "epX", [a, b]) == first                  # the same episode: the same identity
    kind = gen.representation_evidence(a)["by_kind"]["hypothetical"]
    assert kind["n_inputs"] == 1 and kind["ticks"] == 1                    # replayed five times: one occurrence, credited once
    assert gen._replays_skipped == 4
    dream(gen, bridge, "epY", [a, b], evidence_id="e2")
    assert gen.representation_evidence(a)["by_kind"]["hypothetical"]["n_inputs"] == 2


def test_a_replayed_dream_does_not_change_which_lived_inputs_it_traces_to(gen, bridge):
    a, = reps(gen, 1)
    lived = live(gen, "turn_a", [a])
    for _ in range(3):
        dream(gen, bridge, "epX", [a])
    assert gen.ancestry_of([a])["lived_inputs"] == [lived]


# -- identity, persistence, and what stays unchanged -------------------------------------------------------------------------

def test_notes_that_name_no_episode_get_no_identity_nothing_is_guessed():
    assert I.identity_from_notes({"source": "dream_episode"}) is None
    assert I.identity_from_notes({"seed_lineage_id": "ep"}) is None
    assert I.identity_from_notes({"source": "something_else", "seed_lineage_id": "ep"}) is None
    assert I.identity_from_notes(None) is None


def test_the_dream_identity_does_not_depend_on_the_clock(monkeypatch):
    a = I.identity_from_notes({"source": "dream_episode", "seed_lineage_id": "ep"})
    monkeypatch.setattr(I.time, "time", lambda: 9_999_999_999.0)               # a later replay of the same episode
    assert a == I.identity_from_notes({"source": "dream_episode", "seed_lineage_id": "ep"})
    monkeypatch.undo()
    assert a == I.identity_from_notes({"source": "dream_episode", "seed_lineage_id": "ep"})
    assert a["id"] != I.identity_from_notes({"source": "dream_episode", "seed_lineage_id": "ep2"})["id"]
    assert a["id"] != I.identity_from_notes({"source": "simulation", "seed_lineage_id": "ep"})["id"]


def test_the_ledger_survives_a_restart_and_an_unreadable_one_is_unattributed_not_a_crash(gen, bridge, tmp_path):
    a, = reps(gen, 1)
    lived = live(gen, "turn_a", [a])
    dream(gen, bridge, "ep1", [a])
    gen._write_events_recent_file()
    again = ConstraintGenealogyLogger("dream_ancestry", config=GenealogyConfig(), output_dir=str(tmp_path / "g"))
    assert again.ancestry_of([a])["lived_inputs"] == [lived]
    assert again.representation_evidence(a)["by_kind"]["hypothetical"]["n_inputs"] == 1
    (tmp_path / "g" / "rep_ledger.json").write_text("{not json")
    broken = ConstraintGenealogyLogger("dream_ancestry", config=GenealogyConfig(), output_dir=str(tmp_path / "g"))
    assert broken.ancestry_of([a])["status"] == "unattributed"


def test_the_dream_path_changes_no_real_attribution(gen, bridge, tmp_path):
    other = ConstraintGenealogyLogger("dream_ancestry_b", config=GenealogyConfig(), output_dir=str(tmp_path / "gb"))
    a = reps(gen, 1)[0]
    live(gen, "turn_a", [a])
    dream(gen, bridge, "ep1", [a])
    token = I.begin_input("turn_a", "turn_a", loads={"X": 1.0}, t=1)           # the same sequence, on a genealogy that never sees identity
    I.end_input(token)
    for _ in range(2):
        other.observe(HI, [TraceItem("ABILITY", a)], LO)
    rec = DreamEvidenceRecord(evidence_id="e1", episode_id="ep1", evidence_type="improvement",
                              pressure_before={"X": 0.9, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
                              pressure_after={"X": 0.2, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1}, trace_abilities=[a],
                              origin_tags={"source": "dream_episode", "seed_lineage_id": "ep1"})
    # the same dream observation without any identity machinery reaching it (notes stripped of the source)
    e = dict(DreamGenealogyBridge(storage_dir=str(tmp_path / "b2")).format_for_genealogy([rec])[0])
    notes = {k: v for k, v in e["notes"].items() if k not in ("source", "seed_lineage_id")}
    other.observe(PressureVec(**e["pressure_before"]), [TraceItem("ABILITY", a)], PressureVec(**e["pressure_after"]), notes=notes)
    assert gen.abilities[a].consequence_profile == other.abilities[a].consequence_profile
