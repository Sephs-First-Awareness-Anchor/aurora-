# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A105: many Auroras rehearse her history; she takes in what they carved."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "flutter_app", "android", "app", "src", "main", "python"))

from aurora_internal import aurora_clone_harvest as CH  # noqa: E402
from aurora_internal.aurora_reasoning_paths import ReasoningPaths, CARVE_WEIGHT  # noqa: E402
from aurora_internal.aurora_unformed_patterns import UnformedPatterns  # noqa: E402
from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence  # noqa: E402
from aurora_internal.aurora_lexical_grounding import AuroraLexicalGrounding  # noqa: E402

AX = {"X": 0.1, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.1}
LAND_A = {"meaning_label": "tension", "action": "explain", "operation": "evaluate_proposition",
          "dominant_axis": "N", "abilities": ["a1", "a2"]}
LAND_B = {**LAND_A, "action": "ask", "operation": "seek_clarification"}


def path(land, w=CARVE_WEIGHT):
    return {"shape": "none|q|rel|obj|", "centroid": dict(AX), "landings": dict(land), "weight": w,
            "confirmations": 1, "misled": 0}


def y(cid, paths=(), ops=(), cands=(), patterns=(), ref=None, eps=("E1",)):
    return {"version": CH.HARVEST_VERSION, "clone_id": cid, "episodes": list(eps), "counters": {"rehearsed": 3},
            "paths": list(paths), "worn": [], "operations": list(ops), "candidates": list(cands),
            "unformed": {"reference": ref or {"n": 0, "counts": {}, "axis_sum": {}, "axis_sq": {}},
                         "patterns": list(patterns)}}


def test_shards_are_contiguous_whole_and_balanced():
    eps = [(f"E{i}", n) for i, n in enumerate([4, 4, 40, 2, 2, 2, 30, 6, 6, 4])]
    shards = CH.plan_shards(eps, 3)
    assert [e for s in shards for e in s] == [e for e, _ in eps]
    assert all(shards)
    sizes = [sum(n for e, n in eps if e in s) for s in shards]
    assert max(sizes) <= 60


def test_converging_clones_strengthen_one_path_and_divergence_keeps_every_landing():
    ys = [y("c1", [path(LAND_A)]), y("c2", [path(LAND_A)]), y("c3", [path(LAND_A)]), y("c4", [path(LAND_B)])]
    paths, worn, div = CH.merge_paths(ys)
    a = next(p for p in paths if p["landings"]["action"] == "explain")
    b = next(p for p in paths if p["landings"]["action"] == "ask")
    assert a["clones"] == 3 and b["clones"] == 1
    combined = 1 - (1 - CARVE_WEIGHT) ** 3
    assert abs(a["weight"] - round(combined * 0.75, 4)) < 1e-3          # its share of the pressure
    assert b["share"] == 0.25 and b["divergent_with"] == 1 and "action" in b["differences"]
    assert len(div) == 1 and sorted(div[0]["clones"]) == [1, 3]


def test_her_paths_take_clone_paths_as_independent_confirmations(tmp_path):
    rp = ReasoningPaths(state_dir=str(tmp_path))
    rp.paths["RP:mine"] = {**path(LAND_A, 0.5), "created_at": 0, "last_used": 0}
    out = rp.absorb_clone_paths([{**path(LAND_A, 0.4), "clones": 5}, {**path(LAND_B, 0.03), "clones": 1,
                                                                      "divergent_with": 1, "share": 0.2}])
    assert out == {"deepened": 1, "carved": 1, "divergent": 1}
    assert abs(rp.paths["RP:mine"]["weight"] - 0.7) < 1e-6 and rp.paths["RP:mine"]["clones"] == 5
    new = [p for k, p in rp.paths.items() if k != "RP:mine"][0]
    assert new["weight"] == CARVE_WEIGHT                                  # floor: kept, not dissolved
    assert rp.status()["clone_divergent"] == 1
    assert json.load(open(tmp_path / "reasoning_paths.json"))["paths"]["RP:mine"]["weight"] == 0.7


def _op(seq, evid, ctx="live", fam="CFAM:x"):
    return {"operation": {"operation_id": "COMM:1", "component_id": "warp_communication_emergence_1",
                          "structural_family": fam, "applicability_family": "CAFAM:y",
                          "root_constraints": ["X", "B"], "canonical_signature": "X^1*B^1",
                          "primitive_sequence": list(seq), "parent_ids": [], "invariants": [],
                          "axis_gain": {"X": 0.1}, "status": "trial",
                          "evidence": [{"observation_id": f"O{evid}", "response_id": f"U:{evid}",
                                        "surface_hash": f"s{evid}", "validated": True, "outcome_kind": "positive",
                                        "receiver_score": 0.9, "relation_alignment": 1.0,
                                        "observation_context": ctx}]},
            "trial": {"component_id": "warp_communication_emergence_1", "level": "communication_emergence",
                      "axis_profile": {"I_IS": 0.2}, "parent_ids": []}}


def test_operations_grown_by_several_clones_union_evidence_and_she_decides_promotion(tmp_path):
    ys = [y("c1", ops=[_op(["bind"], 1)]), y("c2", ops=[_op(["bind"], 2)]),
          y("c3", ops=[_op(["admit"], 3)]), y("c4", ops=[_op(["bind"], 4, ctx="environmental_counterfactual")])]
    harvest = CH.merge_yields(ys)
    bind = next(o for o in harvest["operations"] if o["operation"]["primitive_sequence"] == ["bind"])
    assert bind["clones"] == 3 and len(bind["operation"]["evidence"]) == 3
    assert harvest["divergences"]["operations"][0]["structures"] == 2
    ce = AuroraCommunicationEmergence(state_dir=str(tmp_path), persist=True)
    out = ce.absorb_clone_operations(harvest["operations"])
    assert out["added"] == 2
    ops = {tuple(o.primitive_sequence): o for o in ce._operations.values()}
    assert len(ops[("bind",)].evidence) == 2                  # witness-only evidence stayed out
    assert all(o.status in ("trial", "promoted") for o in ops.values())
    assert all(e.get("carried_from") == "clone" for e in ops[("bind",)].evidence)
    again = ce.absorb_clone_operations(harvest["operations"])
    assert again["added"] == 0 and again["evidence"] == 0      # the same evidence never counts twice


def test_lexical_candidates_carry_live_evidence_only(tmp_path):
    cand = {"candidate": {"candidate_id": "LEX:1", "word": "river", "component_id": "warp_lexical_role_grounding_1",
                          "axis_profile": {"I_IS": 0.3}, "applicability_family": "LEXFAM:a", "parent_ids": [],
                          "dominant_constraints": ["N"], "status": "trial",
                          "evidence": [{"evidence_id": "e1", "provenance": "inherited_scaffold", "validated": True},
                                       {"evidence_id": "e2", "provenance": "historical_possibility"}]},
            "trial": {"component_id": "warp_lexical_role_grounding_1"}}
    lg = AuroraLexicalGrounding(state_dir=str(tmp_path), persist=True)
    out = lg.absorb_clone_candidates([cand])
    assert out["added"] == 1 and out["evidence"] == 1
    c = next(c for c in lg._candidates.values() if c.word == "river")
    assert [e["evidence_id"] for e in c.evidence] == ["e1"] and c.status == "trial"
    assert c.component_id in lg._warp_trials


def test_unformed_patterns_from_clones_join_hers(tmp_path):
    up = UnformedPatterns(state_dir=str(tmp_path))
    up.patterns["UP:mine"] = {"feature_counts": {"open:obj": 2, "query:why": 2}, "occurrences": 2,
                              "axis_sum": {a: 0.0 for a in AX}, "status": "forming", "first_at": 0,
                              "covered": 0, "handoffs": 0, "extended_by": {}}
    ys = [y("c1", patterns=[{"feature_counts": {"open:obj": 1, "query:why": 1}, "occurrences": 1, "covered": 0,
                             "axis_sum": {"N": 0.9}}], ref={"n": 4, "counts": {"form:question": 4},
                                                            "axis_sum": {"N": 2.0}, "axis_sq": {"N": 1.0}}),
          y("c2", patterns=[{"feature_counts": {"open:obj": 2, "query:why": 1}, "occurrences": 2, "covered": 1,
                             "axis_sum": {"N": 1.0}}])]
    merged = CH.merge_unformed(ys)
    assert len(merged["patterns"]) == 1 and merged["patterns"][0]["clones"] == 2
    out = up.absorb_clone_patterns(merged)
    assert out == {"joined": 1, "added": 0, "reference_turns": 4}
    assert up.patterns["UP:mine"]["occurrences"] == 5 and up.ref_n == 4


class _Organs(dict):
    pass


def test_absorb_once_records_lived_conversations_and_history_skips_their_rehearsal(tmp_path):
    state = tmp_path / "state"
    systems = {"reasoning_paths": ReasoningPaths(state_dir=str(state)),
               "unformed_patterns": UnformedPatterns(state_dir=str(state)), "state_dir": str(state)}
    harvest = CH.merge_yields([y("c1", [path(LAND_A)], eps=["E1", "E2"]), y("c2", [path(LAND_A)], eps=["E3"])])
    hp = tmp_path / "h.jsonl.gz"
    CH.write_harvest(str(hp), harvest)
    out = CH.absorb_harvest(systems, harvest_path=str(hp), state_dir=str(state))
    assert out["status"] == "absorbed" and out["episodes"] == 3
    assert out["results"]["operations"] == {"status": "absent"}
    assert out["results"]["paths"]["carved"] == 1
    assert CH.absorb_harvest(systems, harvest_path=str(hp), state_dir=str(state))["status"] == "already_absorbed"
    assert len(CH.load_ledger(str(state))["files"]) == 1            # recognised by bytes, no decode next boot
    assert CH.absorbed_episodes(str(state)) == {"E1", "E2", "E3"}

    import aurora_historical_experience_environment as H
    env = object.__new__(H.HistoricalExperienceEnvironment)
    env.systems, env.state_dir, env.rehearse, env._rehearsal, env.last_rehearsal = {}, state, True, None, {}
    env.skip_absorbed, env._absorbed_episodes = True, None
    env.rehearsal_counters = {k: 0 for k in ("rehearsed", "silent", "compared", "match", "partial",
                                             "mismatch", "fanned_out", "errors", "lived_by_clones")}
    ev = {"episode_id": "E2", "text": "What do you think?", "event_id": "x"}
    assert env._rehearse(ev, H.REHEARSAL_HEARD_SIDE, "E2", True) == {"skipped": "lived_by_clones"}
    assert env.rehearsal_counters["lived_by_clones"] == 1 and env.rehearsal_counters["rehearsed"] == 0


def test_clone_yield_is_the_processed_parts_only():
    start = {"paths": {"RP:a": {**path(LAND_A, 0.5)}}, "ce_ops": {}, "ce_trials": {}, "lg_cands": {},
             "lg_trials": {}, "unformed": {"ref_n": 2, "ref_counts": {"f": 2}, "ref_axis_sum": {"N": 1.0},
                                            "ref_axis_sq": {"N": 0.5}, "patterns": {}}}
    end = {"paths": {"RP:a": {**path(LAND_A, 0.6)}, "RP:b": path(LAND_B)},
           "ce_ops": {"c": _op(["bind"], 1)["operation"]}, "ce_trials": {},
           "lg_cands": {}, "lg_trials": {},
           "unformed": {"ref_n": 3, "ref_counts": {"f": 3, "g": 1}, "ref_axis_sum": {"N": 1.5},
                        "ref_axis_sq": {"N": 0.75}, "patterns": {}}}
    out = CH.clone_yield(start, end, clone_id="c", episodes=["E1"], counters={})
    gains = sorted(p["weight"] for p in out["paths"])
    assert abs(gains[0] - CARVE_WEIGHT) < 1e-6 and abs(gains[1] - 0.2) < 1e-3   # 0.5 -> 0.6 is a 0.2 confirmation
    assert out["unformed"]["reference"]["n"] == 1 and out["unformed"]["reference"]["counts"] == {"f": 1, "g": 1}
    assert len(out["operations"]) == 1


def test_trials_travel_slim():
    item = _op(["bind"], 1)
    item["trial"]["parameters"] = {"structural_family": "x" * 500}
    harvest = CH.merge_yields([y("c1", ops=[item])])
    assert "parameters" not in harvest["operations"][0]["trial"]
    assert harvest["operations"][0]["trial"]["axis_profile"] == {"I_IS": 0.2}


def test_streamed_absorption_in_tiny_chunks_matches_the_whole(tmp_path, monkeypatch):
    monkeypatch.setattr(CH, "ABSORB_CHUNK", 1)
    state = tmp_path / "state"
    systems = {"reasoning_paths": ReasoningPaths(state_dir=str(state)),
               "unformed_patterns": UnformedPatterns(state_dir=str(state)),
               "communication_emergence": AuroraCommunicationEmergence(state_dir=str(state), persist=True)}
    other = {**AX, "X": 0.9, "N": 0.1}
    harvest = CH.merge_yields([
        y("c1", [path(LAND_A), {**path(LAND_B), "centroid": other}], ops=[_op(["bind"], 1), _op(["admit"], 2)],
          patterns=[{"feature_counts": {"open:obj": 1}, "occurrences": 1, "covered": 0, "axis_sum": {}}],
          ref={"n": 2, "counts": {"form:question": 2}, "axis_sum": {"N": 1.0}, "axis_sq": {"N": 0.5}})])
    hp = tmp_path / "h.jsonl.gz"
    CH.write_harvest(str(hp), harvest)
    assert CH.read_header(str(hp))["harvest_id"] == harvest["harvest_id"]
    assert CH.load_harvest(str(hp))["operations"] == harvest["operations"]
    out = CH.absorb_harvest(systems, harvest_path=str(hp), state_dir=str(state))
    assert out["results"]["paths"]["carved"] == 2
    assert out["results"]["operations"]["added"] == 2
    assert out["results"]["unformed"]["added"] == 1 and out["results"]["unformed"]["reference_turns"] == 2
    assert out["results"]["candidates"] == {"status": "absent"}
    assert systems["unformed_patterns"].ref_n == 2


def test_motif_lineage_travels_and_her_promotion_rule_decides(tmp_path):
    """FIX-A113: what clones' rehearsal credited in each sentence shape
    reaches her lineage; promotion is still her own should_promote()."""
    from aurora_grammar_engine import GrammarEngine, TokenRole as R
    seq = (R.AGENT, R.ACTION, R.OBJECT)

    def snap(s, f, ctx):
        return {"motifs": {"agent_action_object": {"seq": [r.value for r in seq], "s": s, "f": f, "ctx": ctx}}}

    y1 = {**y("c1", eps=["E1"]), "motifs": CH.motif_deltas(snap(2, 0, ["a"]), snap(5, 0, ["a", "b", "c", "e", "g"]))}
    y2 = {**y("c2", eps=["E2"]), "motifs": CH.motif_deltas(snap(2, 0, ["a"]), snap(4, 1, ["a", "d", "h", "i"]))}
    assert y1["motifs"] == [{"seq": ["agent", "action", "object"], "s": 3, "f": 0, "ctx": ["b", "c", "e", "g"]}]
    harvest = CH.merge_yields([y1, y2])
    assert harvest["motifs"][0]["s"] == 5 and harvest["motifs"][0]["clones"] == 2
    hp = tmp_path / "h.jsonl.gz"
    CH.write_harvest(str(hp), harvest)
    assert CH.load_harvest(str(hp))["motifs"][0]["ctx"] == ["b", "c", "d", "e", "g", "h", "i"]

    state = tmp_path / "state"
    eng = GrammarEngine(state_dir=str(state))
    eng._lineage._motifs.clear()
    m = eng._lineage.get_or_create(seq)
    m.success_count, m.contexts_seen = 2, {"a"}
    out = CH.absorb_harvest({"grammar_engine": eng, "state_dir": str(state)}, harvest_path=str(hp),
                            state_dir=str(state))
    assert out["results"]["motifs"] == {"absorbed": 1, "promoted": 1, "demoted": 0}
    assert (m.success_count, m.fail_count, len(m.contexts_seen)) == (7, 1, 8) and m.promoted


def test_motif_evidence_alone_does_not_promote_a_thin_shape(tmp_path):
    from aurora_grammar_engine import GrammarEngine, TokenRole as R
    eng = GrammarEngine(state_dir=str(tmp_path))
    eng._lineage._motifs.clear()
    out = eng.absorb_clone_motifs([{"seq": ["agent", "action"], "s": 9, "f": 0, "ctx": ["only"]}])
    assert out == {"absorbed": 1, "promoted": 0, "demoted": 0}       # one context: not composable yet


def _said_web(*statements):
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb
    from aurora_internal.aurora_propositional_understanding import integrate_form
    web = OntologicalWeb()
    for subj, rel, obj in statements:
        integrate_form(web, {"subject": subj, "relation": rel, "obj": obj}, heard="", speaker="sunni",
                       listener="aurora", profile={"X": 0.0, "T": 1.0, "N": 0.0, "B": 0.0, "A": 0.0})
    return web


def test_propositions_and_concept_positions_travel_from_clones(tmp_path):
    """FIX-A115: what clones heard asserted, and where concepts sat, reaches her."""
    from types import SimpleNamespace
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb
    clone_web = _said_web(("I", "love", "records"))
    start = CH.organ_snapshot({"oets": SimpleNamespace(web=OntologicalWeb())})
    end = CH.organ_snapshot({"oets": SimpleNamespace(web=_said_web(("I", "love", "records"), ("I", "love", "records")))})
    yd = {**y("c1", eps=["E1"]), "propositions": CH.proposition_deltas(start, end),
          "concepts": CH.concept_deltas(start, end)}
    assert yd["propositions"][0]["predicates"]["love"]["n"] == 2 and yd["propositions"][0]["by"] == {"sunni": 2}
    harvest = CH.merge_yields([yd, {**yd, "clone_id": "c2", "episodes": ["E2"]}])
    assert harvest["propositions"][0]["n"] == 4 and harvest["concepts"][0]["n"] == 4
    hp = tmp_path / "h.jsonl.gz"
    CH.write_harvest(str(hp), harvest)

    her = OntologicalWeb()
    her.add_node("records", "noun")
    state = tmp_path / "state"
    out = CH.absorb_harvest({"oets": SimpleNamespace(web=her), "state_dir": str(state)},
                            harvest_path=str(hp), state_dir=str(state))
    assert out["results"]["propositions"] == {"absorbed": 1, "created": 1}
    rel = [r for r in her.relations.values() if r.source_word == "sunni"][0]
    assert rel.assertion["predicates"]["love"]["n"] == 4 and rel.assertion["profile"]["T"] == 1.0
    assert her.nodes["records"].axis_samples == 4 and her.nodes["records"].axis_profile["T"] == 1.0
    del clone_web


def test_each_run_is_a_segment_and_nothing_is_lost_before_the_phone_absorbs_it(tmp_path):
    hp = tmp_path / "h.jsonl.gz"
    run1 = CH.merge_yields([y("c1", [path(LAND_A)], eps=["E1"])])
    CH.write_harvest(str(hp), run1)
    state_a = tmp_path / "phone_a"                      # booted on run 1
    sys_a = {"reasoning_paths": ReasoningPaths(state_dir=str(state_a)), "state_dir": str(state_a)}
    assert CH.absorb_harvest(sys_a, harvest_path=str(hp), state_dir=str(state_a))["status"] == "absorbed"

    run2 = CH.merge_yields([y("c2", [path(LAND_A)], eps=["E2"])], lived_before=["E1"])
    CH.write_harvest(str(hp), run2)
    assert [h["harvest_id"] for h in CH.read_headers(str(hp))] == [run1["harvest_id"], run2["harvest_id"]]
    assert CH.read_header(str(hp))["lived_episodes"] == ["E1", "E2"]
    CH.write_harvest(str(hp), run2)                     # the same run written twice stays one segment
    assert len(CH.read_headers(str(hp))) == 2

    out_a = CH.absorb_harvest(sys_a, harvest_path=str(hp), state_dir=str(state_a))
    assert out_a["status"] == "absorbed" and out_a["harvest_id"] == run2["harvest_id"]
    assert [x["status"] for x in out_a["segments"]] == ["already_absorbed", "absorbed"]

    state_b = tmp_path / "phone_b"                      # never booted on run 1
    sys_b = {"reasoning_paths": ReasoningPaths(state_dir=str(state_b)), "state_dir": str(state_b)}
    out_b = CH.absorb_harvest(sys_b, harvest_path=str(hp), state_dir=str(state_b))
    assert [x["status"] for x in out_b["segments"]] == ["absorbed", "absorbed"]
    assert CH.absorbed_episodes(str(state_b)) == {"E1", "E2"}


def test_a_relived_pass_for_new_organs_counts_nothing_twice(tmp_path):
    """FIX-A115: history first lived before motifs/propositions/concepts
    existed is lived again for those organs only; paths are not re-reported,
    and the phone takes the new organs for conversations it already lived."""
    from aurora_grammar_engine import GrammarEngine
    hp = tmp_path / "h.jsonl.gz"
    legacy = CH.merge_yields([y("c1", [path(LAND_A)], eps=["E1", "E2"])])
    legacy.pop("organs")                                 # an old harvest names no organs
    CH.write_harvest(str(hp), legacy)
    head = CH.read_header(str(hp))
    assert CH.lived_for(head, ("paths",)) == {"E1", "E2"}
    assert CH.lived_for(head, ("motifs", "propositions", "concepts")) == set()

    relived = CH.clone_yield({}, {"paths": {"p": {"weight": 0.5, "shape": "s", "centroid": {}, "landings": {}}},
                                  "motifs": {"agent_action": {"seq": ["agent", "action"], "s": 3, "f": 0,
                                                              "ctx": ["a", "b", "c"]}}},
                             clone_id="c2", episodes=["E1"], counters={}, organs=("motifs",))
    assert relived["paths"] == [] and relived["motifs"][0]["s"] == 3
    run = CH.merge_yields([relived], lived_before=["E1", "E2"])
    assert run["organs"] == ["motifs"]
    CH.write_harvest(str(hp), run)
    assert CH.lived_for(CH.read_header(str(hp)), ("motifs",)) == {"E1"}

    state = tmp_path / "phone"
    phone = {"reasoning_paths": ReasoningPaths(state_dir=str(state)), "grammar_engine": GrammarEngine(state_dir=str(state)),
             "state_dir": str(state)}
    phone["grammar_engine"]._lineage._motifs.clear()
    CH.write_harvest(str(tmp_path / "only_legacy.jsonl.gz"), legacy)
    CH.absorb_harvest(phone, harvest_path=str(tmp_path / "only_legacy.jsonl.gz"), state_dir=str(state))
    out = CH.absorb_harvest(phone, harvest_path=str(hp), state_dir=str(state))
    assert [x["status"] for x in out["segments"]] == ["already_absorbed", "absorbed"]
    assert out["results"]["motifs"]["absorbed"] == 1 and "paths" not in out["results"] or \
        out["results"].get("paths", {}).get("carved", 0) == 0


def test_listening_feeds_the_three_listening_organs_without_a_turn(monkeypatch):
    from types import SimpleNamespace
    from aurora_grammar_engine import GrammarEngine
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb
    import aurora
    import tempfile
    monkeypatch.setattr(aurora, "_project_utterance_axes", lambda text, systems: {"X": 0.1, "T": 0.6, "N": 0.1, "B": 0.1, "A": 0.1})
    web = OntologicalWeb()
    web.add_node("records", "noun")
    eng = GrammarEngine(state_dir=tempfile.mkdtemp())
    eng._lineage._motifs.clear()
    systems = {"oets": SimpleNamespace(web=web), "grammar_engine": eng}
    first = {"actor": "assistant", "text": "What do you love?"}
    reply = {"actor": "user", "text": "I love old soul records."}
    out = CH.listen_to(systems, reply, first, CH.LISTEN_ORGANS)
    assert out["statements"] == 2 and out["motifs"] == 1
    rel = [r for r in web.relations.values() if r.source_word == "sunni"][0]
    assert rel.assertion["by"] == {"sunni": 1}
    assert CH.listen_to(systems, first, None, ("motifs",))["motifs"] == 0   # nothing it answered: no demonstration
