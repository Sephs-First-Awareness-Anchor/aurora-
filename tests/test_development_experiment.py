# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The history-dependence experiment only watches -- these check what it concludes."""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "flutter_app", "android", "app", "src", "main", "python"))

from aurora_internal import aurora_development_experiment as X  # noqa: E402
from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine  # noqa: E402


def ev(n, eid, rels=(), births=(), turn=None, comparison=None, episode="E1"):
    e = {"kind": "event", "n": n, "event_id": eid, "episode_id": episode, "actor": "x",
         "engaged": [[a, t, b, 0.5] for a, t, b in rels], "births": [list(x) for x in births]}
    if turn:
        e["turn"] = turn
    if comparison:
        e["comparison"] = comparison
    return e


def trace(events):
    return {"header": {}, "footer": {"messages": len(events)}, "events": events}


def test_histories_are_adjacent_contiguous_stretches():
    eps = [(f"E{i}", 10) for i in range(20)]
    a, b = X.pick_histories(eps, start=3, target_messages=25)
    assert a == ["E3", "E4", "E5"] and b == ["E6", "E7", "E8"]


def test_engaged_relations_are_the_webs_relations_among_the_messages_words():
    eng = OntologicalScaffoldingEngine()
    for w, role in (("river", "noun"), ("flows", "verb"), ("stone", "noun"), ("moon", "noun")):
        eng.web.add_node(w, role)
    eng.web.infer_relations_from_context(["river", "flows", "stone"])
    eng.web.infer_relations_from_context(["river", "flows", "stone"])
    words = X.content_words(eng.web, "The river flows, over a stone!")
    assert words == ["river", "flows", "stone"]
    rels = X.engaged_relations(eng.web, words)
    assert rels and all(r[0] in words and r[2] in words for r in rels)
    assert X.engaged_relations(eng.web, X.content_words(eng.web, "the moon")) == []


def test_births_see_new_and_changed_items():
    before = {"operation": {"c1": "trial"}, "path": {}}
    after = {"operation": {"c1": "promoted", "c2": "trial"}, "path": {"RP:1": "carved"}}
    got = sorted(X.births(before, after))
    assert got == [["operation", "c1", "became", "promoted"], ["operation", "c2", "born", "trial"],
                   ["path", "RP:1", "born", "carved"]]


def test_a_relation_recognized_only_after_the_other_history_is_traced_to_where_it_formed():
    prior_b = trace([ev(0, "b1", rels=[("tide", "related_to", "moon")], episode="EB")])
    original = trace([ev(0, "a1", rels=[("sea", "related_to", "salt")])])
    replicate = trace([ev(0, "a1", rels=[("sea", "related_to", "salt")])])
    cross = trace([ev(0, "a1", rels=[("sea", "related_to", "salt"), ("tide", "related_to", "moon")])])
    out = X.compare_on_history(original, cross, replicate, prior_b, label="t")
    assert out["recognized_relations"] == 1 and out["recognized_traced_to_prior_history"] == 1
    ex = out["examples"]["recognized_from_prior"][0]
    assert ex["relation"] == "tide|related_to|moon" and ex["from_prior_history"]["event_id"] == "b1"
    assert out["overlooked_relations"] == 0


def test_differences_inside_the_noise_floor_do_not_count():
    original = trace([ev(0, "a1", rels=[("sea", "r", "salt")], turn={"landings": {"action": "explain"}},
                         comparison={"label": "rehearsal_mismatch", "score": 0.10})])
    replicate = trace([ev(0, "a1", rels=[("sea", "r", "salt"), ("x", "r", "y")], turn={"landings": {"action": "ask"}},
                          comparison={"label": "rehearsal_mismatch", "score": 0.30})])
    cross = trace([ev(0, "a1", rels=[("sea", "r", "salt"), ("x", "r", "y")], turn={"landings": {"action": "ask"}},
                      comparison={"label": "rehearsal_mismatch", "score": 0.25})])
    out = X.compare_on_history(original, cross, replicate, None, label="t")
    assert out["recognized_relations"] == 0             # the replicate engaged it too: noise
    assert out["landing_shifts_beyond_noise"] == 0      # the replicate shifted the same way
    assert out["rehearsal_scores"]["better_beyond_noise"] == 0   # +0.15 is inside the 0.20 noise


def test_a_landing_shift_beyond_noise_names_the_path_that_came_from_the_prior_history():
    prior = trace([ev(0, "b7", births=[("path", "RP:abc", "born", "carved")], episode="EB")])
    original = trace([ev(0, "a1", turn={"landings": {"action": "explain"}}, comparison={"label": "rehearsal_mismatch", "score": 0.1})])
    replicate = trace([ev(0, "a1", turn={"landings": {"action": "explain"}}, comparison={"label": "rehearsal_mismatch", "score": 0.1})])
    prior["events"][0]["births"].append(["ability", "B:NEW_1", "born", "exists"])
    cross = trace([ev(0, "a1", turn={"landings": {"action": "ask", "abilities": ["B:NEW_1"]}, "offered_path": {"path_id": "RP:abc"}},
                      comparison={"label": "rehearsal_match", "score": 0.6})])
    out = X.compare_on_history(original, cross, replicate, prior, label="t")
    assert out["landing_shifts_beyond_noise"] == 1
    assert out["examples"]["landing_shifts"][0]["path_offered_from_prior"][1] == "b7"
    assert out["examples"]["landing_shifts"][0]["abilities_born_in_prior"][0]["event_id"] == "b7"
    assert out["rehearsal_scores"]["better_beyond_noise"] == 1


def test_order_comparison_says_where_order_unique_relations_were_born():
    ab = {"relations": {"a|r|b": 0.5, "c|r|d": 0.4}, "operations": {"k1": "trial"}, "word_groundings": {},
          "abilities": ["x"], "paths": []}
    ba = {"relations": {"a|r|b": 0.5}, "operations": {"k1": "promoted"}, "word_groundings": {},
          "abilities": ["x", "y"], "paths": []}
    traces = {"A": trace([ev(0, "a3", rels=[("c", "r", "d")])]), "AB": trace([]), "B": trace([]), "BA": trace([])}
    out = X.compare_states(ab, ba, traces)
    assert out["relations"]["only_A_then_B"] == ["c|r|d"]
    assert out["relations"]["only_A_then_B_born_in"]["first_history"] == 1
    assert out["operations"]["same_status"] == 0 and out["abilities"]["only_B_then_A"] == 1


def test_freeze_and_thaw_carry_state_and_evolved_sources(tmp_path):
    repo = tmp_path / "repo"
    (repo / "aurora_state" / "historical_experience" / "baseline_v1").mkdir(parents=True)
    (repo / "aurora_state" / "paths.json").write_text("{\"w\": 1}")
    (repo / "aurora_state" / "historical_experience" / "baseline_v1" / "events.jsonl.gz").write_text("big")
    tar = tmp_path / "s.tar.gz"
    info = X.freeze(str(repo), "aurora_state", str(tar))
    assert info["files"] == 1                            # the archive itself is not frozen
    (repo / "aurora_state" / "paths.json").write_text("{}")
    X.thaw(str(repo), str(tar))
    assert json.loads((repo / "aurora_state" / "paths.json").read_text()) == {"w": 1}


def test_analysis_end_to_end_writes_a_report(tmp_path):
    def write(arm, events):
        with gzip.open(tmp_path / f"trace_{arm}.jsonl.gz", "wt") as fh:
            fh.write(json.dumps({"kind": "header", "arm": arm}) + "\n")
            for e in events:
                fh.write(json.dumps(e) + "\n")
            fh.write(json.dumps({"kind": "footer", "messages": len(events), "seconds": 1.0, "rehearsal": {}}) + "\n")
    write("A", [ev(0, "a1", rels=[("sea", "r", "salt")])])
    write("A_rep", [ev(0, "a1", rels=[("sea", "r", "salt")])])
    write("B", [ev(0, "b1", rels=[("tide", "r", "moon")], episode="EB")])
    write("BA", [ev(0, "a1", rels=[("sea", "r", "salt"), ("tide", "r", "moon")])])
    write("AB", [ev(0, "b1", rels=[("tide", "r", "moon")], episode="EB")])
    for arm in ("AB", "BA"):
        with gzip.open(tmp_path / f"state_{arm}.json.gz", "wt") as fh:
            json.dump({"relations": {"tide|r|moon": 0.5}, "operations": {}, "word_groundings": {}, "abilities": [], "paths": []}, fh)
    report = X.analyze(str(tmp_path))
    assert report["B_history_on_A"]["recognized_traced_to_prior_history"] == 1
    assert report["noise_floor"]["relation_difference"] == 0.0
    md = X.render_markdown(report)
    assert "tide|r|moon" in md and "Order" in md
