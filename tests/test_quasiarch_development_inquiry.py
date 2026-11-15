# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage F: QuasiArch answers the six developmental questions from recorded evidence, and says what it cannot tell.

Real genealogy loggers throughout; the observer is the real AuroraQuasiArchObserver.  Honesty is the thing under test: no ancestry
is manufactured, uncertainty is stated, the inquiry changes nothing, and the answers survive consolidation and restart.
"""
from __future__ import annotations

import json
import os

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal import quasiarch_development_inquiry as Q
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem

HI = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1)
LO = PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1)


def mk(path, run_id="g", scope="canonical"):
    g = ConstraintGenealogyLogger(run_id, config=GenealogyConfig(), output_dir=str(path))
    g.persist_scope = scope
    return g


def lived(g, turn, reps, stream="user_input", before=HI, after=LO):
    token = I.begin_input(turn, f"text of {turn}", stream_type=stream, loads={"X": 1.0}, t=1)
    try:
        g.observe(before, [TraceItem("ABILITY", r) for r in reps], after)
    finally:
        I.end_input(token)


def dream(g, episode, reps, x=0.2, source="dream_episode"):
    g.observe(HI, [TraceItem("ABILITY", r) for r in reps], PressureVec(X=x, T=0.4, N=0.1, B=0.1, A=0.1),
              notes={"source": source, "seed_lineage_id": episode})


@pytest.fixture()
def g(tmp_path):
    return mk(tmp_path / "genealogy")


def reps(g):
    return list(g.abilities)


def story(g):
    """Lived: r0,r1,r2 heard in turn 1; r0,r1 again heard in turn 2; r0 perceived in turn 3.  Dream ep1 over r0, r1 and r5 (never lived)."""
    r = reps(g)
    lived(g, "turn_1", [r[0], r[1], r[2]])
    lived(g, "turn_2", [r[0], r[1]])
    lived(g, "turn_3", [r[0]], stream="sensor_data")
    dream(g, "ep1", [r[0], r[1], r[5]])
    return r


def state(g):
    return json.dumps({"profiles": {k: a.consequence_profile for k, a in g.abilities.items()},
                       "rep": g._rep_ledger, "pairs": {f"{l}|{r}": v for (l, r), v in g._pair_ledger.items()},
                       "pstats": {f"{l}|{r}": (v.count, dict(v.relief_sum)) for (l, r), v in g._pair_stats.items()},
                       "inputs": dict(g._input_events), "links": sorted(g.links), "tick": g.tick_count,
                       "replays": g._replays_skipped, "applied": g._applied.to_dict(),
                       "shadow": [[list(k), v] for k, v in g._input_effects.items()]}, sort_keys=True, default=str)


# -- 1. which experiences supplied a dream's ancestral material ----------------------------------------------------------------------

def test_a_dreams_ancestry_names_the_lived_inputs_and_leaves_the_untraceable_unattributed(g):
    r = story(g)
    a = Q.dream_ancestry(g, "ep1")
    assert a["found"] and a["status"] == "partial" and a["authoritative"] is False
    assert a["unattributed"] == [r[5]]
    named = {x["name"]: x["occurrence"] for x in a["lived_ancestors"]}
    assert named == {"turn_1": "heard", "turn_2": "heard", "turn_3": "perceived"}
    assert a["representations"][r[5]]["lived_ancestors"] == []                       # nothing is manufactured for it
    assert a["representations"][r[0]]["ancestry"] == "traced"


def test_how_the_ancestors_combined_is_stated_as_not_attributed(g):
    story(g)
    a = Q.dream_ancestry(g, "ep1")
    assert any("which ancestor supplied which combination" in u for u in a["unknown"])
    assert any("no recorded experiential ancestry" in u for u in a["unknown"])


def test_a_dream_made_only_of_lived_material_is_fully_traced(g):
    r = story(g)
    dream(g, "ep2", [r[0], r[1]])
    a = Q.dream_ancestry(g, "ep2")
    assert a["status"] == "traced" and a["unattributed"] == []


def test_an_unknown_episode_is_reported_unknown_not_guessed(g):
    story(g)
    a = Q.dream_ancestry(g, "no_such_episode")
    assert a["found"] is False and a["resolution"]["how"] == "not recorded" and "representations" not in a


def test_a_name_matching_more_than_one_input_is_ambiguous_not_picked(g):
    r = reps(g)
    lived(g, "same_name", [r[0]])
    lived(g, "same_name", [r[1]], stream="sensor_data")
    res = Q.resolve_episode(g, "same_name")
    assert res["how"] == "ambiguous" and res["input"] is None and len(res["candidates"]) == 2


def test_ledger_rows_that_keep_only_recent_inputs_are_declared(g, monkeypatch):
    monkeypatch.setattr(ConstraintGenealogyLogger, "_LEDGER_INPUTS_CAP", 2)
    r = reps(g)
    for k in range(5):
        dream(g, f"e{k}", [r[0], r[1]], x=0.2 + k * 0.01)
    a = Q.dream_ancestry(g, "e0")                                                     # long ago: the capped rows no longer list it
    assert a["status"] == "unknown" and any("keep only their most recent inputs" in u for u in a["unknown"])
    assert any("is not known" in u for u in a["unknown"])
    assert not any("keep only their most recent inputs" in u for u in Q.dream_ancestry(g, "e4")["unknown"])      # it is listed: no doubt


# -- 2. what relationships emerged ----------------------------------------------------------------------------------------------------

def test_relationships_say_whether_they_were_only_ever_dreamed_or_also_lived(g):
    r = story(g)
    rel = {tuple(x["pair"]): x for x in Q.new_relationships(g, "ep1")["relationships"]}
    both = rel[(r[0], r[1])]
    only = rel[(r[1], r[5])]
    assert both["also_lived"] is True and both["only_ever_dreamed_or_simulated"] is False
    assert only["only_ever_dreamed_or_simulated"] is True and only["also_lived"] is False


def test_a_promoted_relationship_carries_its_qualification_and_says_it_rests_on_dreams(g):
    a, b = reps(g)[:2]
    for k in range(80):
        dream(g, f"ep{k}", [a, b], x=0.2 + (k % 5) * 0.01)
        if (a, b) in g._links_by_parents:
            break
    assert (a, b) in g._links_by_parents
    row = [x for x in Q.new_relationships(g, f"ep{k}")["relationships"] if tuple(x["pair"]) == (a, b)][0]
    assert row["promoted"] is True and row["link_qualification"]["internal_only"] is True
    assert row["link_qualification"]["externally_demonstrated"] is False
    assert any("external test" in u for u in Q.new_relationships(g, f"ep{k}")["unknown"])


# -- 3. what was consequential ---------------------------------------------------------------------------------------------------------

def test_consequence_is_the_measured_effect_not_a_judgement(g):
    r = story(g)
    c = Q.consequential_changes(g, "ep1")
    by = {x["representation"]: x for x in c["changes"]}
    assert by[r[0]]["effect"] == "relieved pressure" and by[r[0]]["net_relief"] > 0 and r[0] in c["consequential"]


def test_loading_and_nil_effects_are_reported_as_what_they_are(g):
    r = story(g)
    iid = g.find_inputs("ep1")[0]
    zero = {a: 0.0 for a in Q.AXES}
    g._input_effects[(iid, r[3])] = {"n": 2, "crowd": 1, "relief": dict(zero, X=-0.3)}          # measured: pressure went up
    g._input_effects[(iid, r[4])] = {"n": 1, "crowd": 1, "relief": dict(zero)}                    # measured: nothing
    by = {x["representation"]: x["effect"] for x in Q.consequential_changes(g, "ep1")["changes"]}
    assert by[r[3]] == "loaded pressure" and by[r[4]] == "none measured" and by[r[0]] == "relieved pressure"
    c = Q.consequential_changes(g, "ep1")["consequential"]
    assert r[3] in c and r[4] not in c


def test_an_episodes_own_effect_is_declared_unknown_when_it_is_not_held(g, tmp_path):
    story(g)
    g.flush_files(force=True)
    from aurora_runtime import _restore_genealogy_state
    again = mk(tmp_path / "genealogy", "g2")
    _restore_genealogy_state(again, str(tmp_path / "genealogy"))
    c = Q.consequential_changes(again, "ep1")
    assert c["found"] and c["changes"] == [] and any("not held" in u for u in c["unknown"])


# -- 4. internal and external validation ------------------------------------------------------------------------------------------------

def test_validation_separates_dreamed_heard_and_externally_demonstrated(g):
    r = story(g)
    v = Q.validation(g)
    assert r[5] in v["groups"]["internal_only"] and v["internal_validation"][r[5]] == "supported"
    assert r[2] in v["groups"]["lived_not_externally_demonstrated"]                  # heard, never tested in the world
    assert r[0] in v["groups"]["internal_only"] or r[0] in v["groups"]["external_supported"]
    assert any("hearing something is not that" in u for u in Q.validation(g, [r[2]])["unknown"])


def test_an_external_test_that_failed_is_reported_as_contradicting_what_a_dream_supported(g):
    r = reps(g)
    dream(g, "sim", [r[7]], source="simulation")
    lived(g, "test_1", [r[7]], stream="sensor_data", before=LO, after=HI)            # the world loaded pressure
    v = Q.validation(g, [r[7]])
    assert v["groups"]["external_contradicted"] == [r[7]] and v["internal_validation"][r[7]] == "supported"


def test_asking_about_a_capability_the_ledger_never_saw_is_answered_not_a_crash(g):
    v = Q.validation(g, ["X:NEVER_SEEN"])
    assert v["groups"]["none"] == ["X:NEVER_SEEN"] and v["n_examined"] == 1


def test_an_external_success_is_external_validation(g):
    r = reps(g)
    lived(g, "test_1", [r[7]], stream="sensor_data")
    assert Q.validation(g, [r[7]])["groups"]["external_supported"] == [r[7]]


# -- 5. what remains hypothetical or uncertain ------------------------------------------------------------------------------------------

def test_uncertainty_lists_what_is_unattributed_hypothetical_or_unqualified(g):
    r = story(g)
    import dataclasses
    g.abilities[r[9]] = dataclasses.replace(g.abilities[r[9]], consequence_profile={"samples": 3})   # legacy: a profile with no ledger row
    a, b = r[0], r[1]
    for k in range(80):
        dream(g, f"p{k}", [r[10], r[11]], x=0.2 + (k % 5) * 0.01)
        if (r[10], r[11]) in g._links_by_parents:
            break
    items = Q.uncertain(g)["items"]
    assert r[9] in items["capabilities_with_no_recorded_ancestry"]["examples"]
    assert items["links_resting_only_on_dreams_or_simulations"]["n"] >= 1
    assert r[5] in items["capabilities_hypothetical_only"]
    assert items["replays_not_counted_as_new_evidence"] == 0


def test_replays_and_open_gaps_are_reported(g):
    r = reps(g)
    for _ in range(4):
        dream(g, "same", [r[0], r[1]])
    g._applied.mark("origin_x", 1)
    g._applied.mark("origin_x", 4)
    g._applied.note_gap("origin_x", 2, 3)
    items = Q.uncertain(g)["items"]
    assert items["replays_not_counted_as_new_evidence"] == 3
    assert items["evidence_not_yet_consolidated_from_the_surface"] == [{"origin": "origin_x", "missing_from": 2, "missing_to": 3}]


def test_a_link_minted_before_qualification_existed_is_listed_as_unqualified(g):
    a, b = reps(g)[:2]
    for k in range(80):
        dream(g, f"ep{k}", [a, b], x=0.2 + (k % 5) * 0.01)
        if (a, b) in g._links_by_parents:
            break
    g.links[g._links_by_parents[(a, b)]].evidence_qualification = None
    assert Q.uncertain(g)["items"]["links_with_no_evidence_qualification"]["n"] == 1


# -- the inquiry changes nothing -------------------------------------------------------------------------------------------------------

def test_no_question_changes_any_state(g):
    story(g)
    before = state(g)
    for q, kw in (("dream_ancestry", {"episode": "ep1"}), ("new_relationships", {"episode": "ep1"}),
                  ("consequential_changes", {"episode": "ep1"}), ("validation", {}), ("uncertain", {}),
                  ("dream_ancestry", {"episode": "nothing"}), ("not_a_question", {})):
        Q.inquire(g, q, **kw)
    assert state(g) == before


def test_the_module_touches_the_genealogy_only_through_read_accessors():
    import ast
    tree = ast.parse(open(Q.__file__, encoding="utf-8").read())
    touched = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "g"}
    reads = {"input_identity", "find_inputs", "reps_credited_under", "pairs_credited_under", "ancestry_of", "representation_evidence",
             "pair_evidence", "input_effects", "_links_by_parents", "links", "abilities", "_rep_ledger", "_applied", "_replays_skipped"}
    assert touched <= reads, sorted(touched - reads)
    stores = [n for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete))
              and any(isinstance(t, (ast.Attribute, ast.Subscript)) and "g" in {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
                      for t in (n.targets if hasattr(n, "targets") else [n.target]))]
    assert stores == []


# -- the basis survives consolidation and restart ---------------------------------------------------------------------------------------

def test_the_answers_survive_a_restart_with_their_basis_intact(g, tmp_path):
    from aurora_runtime import _restore_genealogy_state
    story(g)
    before = {q: Q.inquire(g, q, **kw) for q, kw in (("dream_ancestry", {"episode": "ep1"}), ("new_relationships", {"episode": "ep1"}),
                                                    ("validation", {}))}
    g.flush_files(force=True)
    again = mk(tmp_path / "genealogy", "g2")
    _restore_genealogy_state(again, str(tmp_path / "genealogy"))
    after = {q: Q.inquire(again, q, **kw) for q, kw in (("dream_ancestry", {"episode": "ep1"}), ("new_relationships", {"episode": "ep1"}),
                                                       ("validation", {}))}
    assert after == before


def test_the_answers_after_consolidation_equal_those_from_direct_experience(tmp_path):
    from aurora_internal import genealogy_evidence_journal as J
    canon = mk(tmp_path / "genealogy", "canon")
    surf = mk(tmp_path / "genealogy_surface", "surf_1", "session_state")
    ref = mk(tmp_path / "ref", "ref")
    story(surf)
    story(ref)
    surf.flush_journal()
    canon.consolidate_journal(surf._journal_path())
    for q, kw in (("dream_ancestry", {"episode": "ep1"}), ("new_relationships", {"episode": "ep1"}), ("validation", {})):
        assert Q.inquire(canon, q, **kw) == Q.inquire(ref, q, **kw), q


# -- the observer ----------------------------------------------------------------------------------------------------------------------

def test_the_quasiarch_observer_investigates_through_the_same_inquiry(g, tmp_path):
    from aurora_internal.aurora_quasiarch_observer import AuroraQuasiArchObserver
    story(g)
    obs = AuroraQuasiArchObserver(state_dir=str(tmp_path / "qa"))
    obs.attach_systems({"genealogy": g})
    assert obs.investigate_development("dream_ancestry", episode="ep1") == Q.dream_ancestry(g, "ep1")
    assert obs.investigate_development("nonsense")["found"] is False
    bare = AuroraQuasiArchObserver(state_dir=str(tmp_path / "qa2"))
    assert bare.investigate_development("validation")["unknown"] == ["no genealogy is attached to this observer"]


def test_nothing_in_cognition_or_speech_calls_the_inquiry():
    root = os.path.join(os.path.dirname(__file__), "..")
    callers = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("tests", "scripts", ".git", "node_modules", "__pycache__")]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
                text = open(os.path.join(dirpath, f), encoding="utf-8", errors="ignore").read()
                if ("investigate_development" in text or "quasiarch_development_inquiry" in text) and rel not in (
                        "aurora_internal/aurora_quasiarch_observer.py", "aurora_internal/quasiarch_development_inquiry.py"):
                    callers.append(rel)
    assert callers == []                                                                 # a diagnostic, read on request, never fed back
