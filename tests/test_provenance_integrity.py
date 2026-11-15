# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Test 7 (directive IX): provenance integrity.

Testimony, observation, hypothetical material, inference, correction and unknown-origin data are introduced.  The basis of each must
remain intact through consolidation, restart and retrieval.  Three real layers, each held to the same rule:

  A. the propositional store (what she holds, and how): told / observed / corrected / supposed / unknown, through the engine's
     own consolidation, a real save and load of the web, and retrieval (verdict, qualification, what she would say);
  B. the evidence contract's events, including inference: fold -> JSON -> merge in pieces -> fold;
  C. the genealogy's ledger (what each occurrence did): kind of occurrence through Surface journalling, consolidation, flush and restore.
"""
from __future__ import annotations

import copy
import json

import pytest

from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_input_identity as I
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import evidence_qualification as Q
from aurora_internal.aurora_identity_persistence import OETSPersistence
from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem

# -- A. the propositional store ------------------------------------------------------------------------------------------------

LINES = [("Mara likes tea.", "told"), ("Teo drinks coffee.", "observed"), ("Lena owns a boat.", "supposed"),
         ("Omar likes jazz.", "told"), ("Omar does not like jazz.", "corrected"), ("Pia likes rain.", None)]
SUBJECTS = {"told": "mara", "observed": "teo", "supposed": "lena", "corrected": "omar", "unknown": "pia"}


def teach(web):
    for line, basis in LINES:
        kw = {} if basis is None else {"basis": basis}
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={}, **kw)


def predicates(web):
    out = {}
    for which, subj in SUBJECTS.items():
        rel = next(r for r in web.relations.values() if r.source_word == subj)
        (name, p), = [(k, v) for k, v in (rel.assertion.get("predicates") or {}).items()][:1]
        out[which] = {"predicate": name, "basis": dict(p["basis"]), "history": [(h["b"], bool(h.get("neg"))) for h in p.get("history", [])],
                      "n": p["n"], "denied": p.get("denied", 0), "verdict": P.verdict(p), "qualification": Q.qualification_of_predicate(p),
                      "voiced": P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")}
    return out


def retrieval(web):
    know = lambda c, q: C.knowledge({"oets": type("O", (), {"web": web})(), "perception": None}, c, q, reach=3, session_id="x")
    return {q: [i["lex"]["action"] for i in know([c], q)] for c, q in
            (("mara", "Does Mara like tea?"), ("teo", "What does Teo drink?"), ("lena", "What does Lena own?"),
             ("omar", "Does Omar like jazz?"), ("pia", "Does Pia like rain?"))}


@pytest.fixture()
def engine():
    e = OntologicalScaffoldingEngine()
    teach(e.web)
    return e


def test_what_each_basis_means_is_recorded_and_unheld_bases_are_never_voiced(engine):
    p = predicates(engine.web)
    assert p["told"]["verdict"] == "held" and p["told"]["voiced"] is not None
    assert p["observed"]["verdict"] == "held" and p["observed"]["qualification"]["latest_basis"] == "observed"
    assert p["supposed"]["verdict"] == "supposed" and p["supposed"]["n"] == 0
    assert p["supposed"]["voiced"]["action"] == "only suppose"                         # said as a supposition, never as a fact
    assert p["told"]["voiced"]["action"] != "only suppose"
    assert p["unknown"]["verdict"] == "unsaid" and p["unknown"]["n"] == 0 and p["unknown"]["voiced"] is None
    c = p["corrected"]
    assert c["qualification"]["corrected"] and c["qualification"]["contradicted"] and c["verdict"] == "denied"
    assert [b for b, _ in c["history"]] == ["told", "corrected"]                      # what was corrected is still there


def test_the_basis_of_each_survives_the_engines_own_consolidation(engine):
    before, said = predicates(engine.web), retrieval(engine.web)
    for _ in range(3):
        engine.consolidate()
    assert predicates(engine.web) == before and retrieval(engine.web) == said


def test_the_basis_of_each_survives_a_real_save_and_restart_and_a_second_one(engine, tmp_path):
    before, said = predicates(engine.web), retrieval(engine.web)
    for k in range(2):                                                                  # restart, then restart the restarted
        persistence = OETSPersistence(state_dir=str(tmp_path / f"s{k}"))
        assert persistence.save_web(engine)
        engine = OntologicalScaffoldingEngine()
        assert persistence.load_web(engine)
        assert predicates(engine.web) == before
        assert retrieval(engine.web) == said


def test_retrieval_after_restart_still_will_not_voice_what_was_never_held(engine, tmp_path):
    persistence = OETSPersistence(state_dir=str(tmp_path / "s"))
    persistence.save_web(engine)
    reborn = OntologicalScaffoldingEngine()
    persistence.load_web(reborn)
    said = retrieval(reborn.web)
    assert set(said["Does Pia like rain?"]) <= {"do not know"}                          # unknown origin: she can only say she does not know
    assert "likes" not in said["Does Pia like rain?"] + said["What does Lena own?"] and "owns" not in said["What does Lena own?"]
    assert "do not know" not in said["Does Mara like tea?"]


def test_a_basis_changed_in_storage_would_be_seen(engine, tmp_path):
    """A control: the checks above can fail.  Re-labelling a stored basis changes what the comparison reports."""
    before = predicates(engine.web)
    persistence = OETSPersistence(state_dir=str(tmp_path / "s"))
    persistence.save_web(engine)
    reborn = OntologicalScaffoldingEngine()
    persistence.load_web(reborn)
    rel = next(r for r in reborn.web.relations.values() if r.source_word == "pia")
    a = copy.deepcopy(rel.assertion)
    pred = next(iter(a["predicates"]))
    a["predicates"][pred]["basis"] = {"told": 1}
    rel.assertion = a
    assert predicates(reborn.web) != before


# -- B. the contract's events, including inference ----------------------------------------------------------------------------------

def _events():
    told = Q.make_event("mara|like|tea", "told", t=1, by="sunni")
    return [told,
            Q.make_event("teo|drink|coffee", "observed", t=2, by="sunni"),
            Q.make_event("lena|own|boat", "supposed", t=3, by="sunni"),
            Q.make_event("ravi|be|tall", "inferred", t=4, derived_from=[told["id"]], nonce="1"),
            Q.make_event("mara|like|tea", "inferred", t=4, derived_from=[told["id"]], nonce="2"),
            Q.make_event("omar|like|jazz", "told", t=5, by="sunni"),
            Q.make_event("omar|like|jazz", "corrected", negated=True, t=6, by="sunni"),
            Q.make_event("pia|like|rain", "unknown", t=7)]


def _by_subject(events):
    out = {}
    for e in events:
        out.setdefault(e["subject"], []).append(e)
    return {s: Q.fold(v) for s, v in out.items()}


def test_every_basis_keeps_its_standing_through_json_and_merging_in_pieces():
    events = _events()
    whole = _by_subject(events)
    wire = json.loads(json.dumps(events))                                               # a durable log, read back
    assert _by_subject(wire) == whole
    a, b = events[:3], events[3:]                                                       # consolidated in two pieces, either order
    merged = Q.merge(a, b)
    assert _by_subject(merged) == whole and _by_subject(Q.merge(b, a)) == whole
    q = {s: Q.qualification(r) for s, r in whole.items()}
    assert q["lena|own|boat"]["hypothetical_only"] and q["ravi|be|tall"]["inferred_only"]
    assert q["omar|like|jazz"]["corrected"] and Q.verdict(whole["pia|like|rain"]) == "unsaid"
    assert whole["mara|like|tea"]["n"] == 1 and whole["mara|like|tea"]["inferred"] == 1 and whole["teo|drink|coffee"]["n"] == 1


def test_an_inference_still_names_what_it_came_from_after_the_trip():
    events = _events()
    told = events[0]
    inferred = next(e for e in json.loads(json.dumps(events)) if e["basis"] == "inferred" and e["subject"] == "mara|like|tea")
    assert inferred["derived_from"] == [told["id"]]
    assert Q.fold([e for e in events if e["subject"] == "mara|like|tea"] + [inferred])["n"] == 1     # it adds nothing to its premise


# -- C. the genealogy ledger ---------------------------------------------------------------------------------------------------------

HI, LO = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1)


def mk(path, run_id, scope="canonical"):
    g = ConstraintGenealogyLogger(run_id, config=GenealogyConfig(), output_dir=str(path))
    g.persist_scope = scope
    return g


def occurrences(g):
    """One input of each origin, each crediting its own representation; one observation made outside any input."""
    r = list(g.abilities)
    plan = [("told", "user_input", "direct", r[0]), ("observed", "sensor_data", "direct", r[1]),
            ("derived", "synthetic_lineage", "direct", r[2]), ("overheard", "user_input", "ambient", r[3])]
    for name, stream, address, rep in plan:
        extra = {"derived_from": ["ev_premise"]} if name == "derived" else {}                # an inference names its premise
        token = I.begin_input(name, f"{name} input", stream_type=stream, address=address, loads={"X": 1.0}, t=1, **extra)
        try:
            g.observe(HI, [TraceItem("ABILITY", rep)], LO)
        finally:
            I.end_input(token)
    g.observe(HI, [TraceItem("ABILITY", r[4])], LO, notes={"source": "dream_episode", "seed_lineage_id": "d1"})      # hypothetical
    g.observe(HI, [TraceItem("ABILITY", r[5])], LO)                                                                   # no input at all: unknown origin
    return r


def kinds(g, reps):
    out = {}
    for i, r in enumerate(reps[:6]):
        row = g._rep_ledger.get(r)
        out[i] = None if row is None else {k: v["n_inputs"] for k, v in row["by"].items()}
    return out


def test_each_origins_kind_survives_surface_journalling_consolidation_and_restart(tmp_path):
    from aurora_runtime import _restore_genealogy_state
    canon = mk(tmp_path / "genealogy", "canon")
    surf = mk(tmp_path / "genealogy_surface", "surf_1", "session_state")
    ref = mk(tmp_path / "ref", "ref")
    reps = occurrences(surf)
    occurrences(ref)
    surf.flush_journal()
    canon.consolidate_journal(surf._journal_path())
    expected = kinds(ref, reps)
    assert kinds(canon, reps) == expected                                              # consolidation: same kinds as direct experience
    assert expected[0] == {"lived": 1} and expected[1] == {"lived": 1} and expected[3] == {"overheard": 1}
    assert expected[4] == {"hypothetical": 1}
    assert expected[5] is None                                                          # unknown origin: credited to no kind, not made lived
    canon.flush_files(force=True)
    reborn = mk(tmp_path / "genealogy", "canon_2")
    _restore_genealogy_state(reborn, str(tmp_path / "genealogy"))
    assert kinds(reborn, reps) == expected                                              # restart
    only_external = {r: reborn.representation_evidence(r)["applicability"] for r in reps[:6]}
    assert only_external[reps[1]] == "external_supported" and only_external[reps[0]] == "none"     # perceived is external; heard is not
    assert only_external[reps[4]] == "internal_only"


def test_a_derived_input_without_a_premise_is_refused_not_made_up():
    with pytest.raises(ValueError):
        I.make_input_event("t", "x", stream_type="synthetic_lineage")
    assert I.make_input_event("t", "x", stream_type="synthetic_lineage", derived_from=["ev_premise"])["occurrence"] == "derived"


def test_an_observation_made_outside_any_input_is_never_counted_as_lived(tmp_path):
    g = mk(tmp_path / "g", "g")
    r = list(g.abilities)[0]
    g.observe(HI, [TraceItem("ABILITY", r)], LO)
    ev = g.representation_evidence(r)
    assert ev["ancestry"] == "unattributed" and ev.get("lived_total", 0) == 0 and "lived" not in ev.get("by_kind", {})
