# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A145 (directive V, Stage B): missing provenance stays "unknown"; it is never silently turned into testimony.

Every path she reads from must treat an unattributed statement the way FIX-A143 treats an example: kept (what,
when, by whom), changing nothing she holds, never voiced as a fact.  Standing she already had is untouched
(nothing developed is disabled by migration), and a later genuine statement clarifies the standing.
"""
from __future__ import annotations

import copy
import inspect

from aurora_internal import aurora_clone_harvest as H
from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import evidence_qualification as Q
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb


def _say(web, line, basis, speaker="sunni"):
    kw = {} if basis is None else {"basis": basis}
    for st in P.statements_in(line):
        P.integrate_form(web, st, heard=line, speaker=speaker, listener="aurora", profile={}, **kw)


def _rel(web, src):
    return next(r for r in web.relations.values() if r.source_word == src)


def _known(web, concepts, question):
    return C.knowledge({"oets": type("O", (), {"web": web})(), "perception": None}, concepts, question, reach=3,
                       session_id="x")


def test_a_caller_who_gives_no_basis_gets_unknown_kept_but_not_held():
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", None)
    p = dict(_rel(web, "mara").assertion["predicates"]["like"])
    assert p["basis"] == {"unknown": 1} and p["n"] == 0 and P.verdict(p) == "unsaid"
    assert P.standing(_rel(web, "mara"), "like")["held"] is False


def test_an_unrecognised_basis_is_unknown_not_told():
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", "hearsay")
    assert _rel(web, "mara").assertion["predicates"]["like"]["basis"] == {"unknown": 1}


def test_unknown_provenance_is_never_voiced_as_a_fact_on_any_path():
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", None)
    rel = _rel(web, "mara")
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora") is None
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora", predicate="like") is None
    assert _known(web, ["mara"], "What does Mara like?") == []               # nothing she holds to offer
    said = [i["lex"] for i in _known(web, ["mara"], "Does Mara like tea?")]
    # asked directly, she can only say she does not know (not that Mara likes tea, and not that she does not)
    assert said and all(l["action"] == "do not know" for l in said), said


def test_unknown_provenance_changes_nothing_she_holds():
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", "told")
    before = copy.deepcopy({k: (r.strength, r.confidence, dict(r.assertion or {})) for k, r in web.relations.items()})
    nodes_before = {k: copy.deepcopy(getattr(n, "profile", None)) for k, n in web.nodes.items()}
    _say(web, "Mara likes tea.", None)                          # the same words again, nobody says where from
    after = {k: (r.strength, r.confidence, dict(r.assertion or {})) for k, r in web.relations.items()}
    for key, (strength, confidence, assertion) in before.items():
        a_strength, a_confidence, a_assertion = after[key]
        assert (strength, confidence) == (a_strength, a_confidence)
        assert a_assertion["n"] == assertion["n"] and a_assertion.get("by") == assertion.get("by")
        assert a_assertion["predicates"]["like"]["n"] == assertion["predicates"]["like"]["n"]
    assert nodes_before == {k: getattr(n, "profile", None) for k, n in web.nodes.items()}


def test_unknown_is_kept_in_the_history_so_it_can_be_clarified_later():
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", None)
    _say(web, "Mara likes tea.", "told")
    p = dict(_rel(web, "mara").assertion["predicates"]["like"])
    assert p["basis"] == {"unknown": 1, "told": 1} and p["n"] == 1 and P.verdict(p) == "held"
    assert [h["b"] for h in p["history"]] == ["unknown", "told"]


def test_standing_that_predates_provenance_is_kept_and_reported_as_unattributed():
    """A predicate written before FIX-A137 has n and no basis record.  It keeps its standing exactly."""
    web = OntologicalWeb()
    _say(web, "Mara likes tea.", "told")
    rel = _rel(web, "mara")
    legacy = dict(rel.assertion)
    legacy["predicates"] = {"like": {"n": 4, "denied": 0, "surface": "likes", "modal": {}}}
    rel.assertion = legacy
    assert P.verdict(rel.assertion["predicates"]["like"]) == "held"
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")["action"] == "likes"
    q = Q.qualification_of_predicate(rel.assertion["predicates"]["like"])
    assert q["unattributed_n"] == 4 and q["unattributed_standing"] and q["verdict"] == "held"
    _say(web, "Mara likes tea.", "told")                        # genuine evidence clarifies, it does not reset
    q2 = Q.qualification_of_predicate(_rel(web, "mara").assertion["predicates"]["like"])
    assert q2["unattributed_n"] == 4 and q2["basis"] == {"told": 1} and q2["verdict"] == "held"


def test_the_turn_entry_still_records_what_a_person_says_as_testimony_and_an_example_as_supposed():
    src = inspect.getsource(P.integrate_turn)
    assert 'basis = "corrected" if _CORRECTION.match' in src and '"told"' in src and '"supposed"' in src


def test_every_production_caller_of_integrate_form_says_its_basis():
    """No caller may rely on a default (the old default was the silent upgrade this fix removes)."""
    import ast
    import pathlib
    root = pathlib.Path(P.__file__).resolve().parents[1]
    missing = []
    for path in list(root.glob("aurora*.py")) + list((root / "aurora_internal").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if name in ("integrate_form", "_record_assertion") and not any(k.arg == "basis" for k in node.keywords):
                    missing.append(f"{path.name}:{node.lineno}")
    assert missing == [], missing


def test_harvested_text_and_the_identity_record_are_testimony_by_decision_not_by_default():
    assert 'basis="told"' in inspect.getsource(H)
    assert 'basis="told"' in inspect.getsource(P.integrate_core_identity)


def test_the_recorder_itself_defaults_to_unknown_not_told():
    import types
    rel = types.SimpleNamespace(assertion=None)
    P._record_assertion(rel, predicate="like", surface="likes", negated=False, modality="", speaker="sunni",
                        time_ref="", profile={}, context="")
    assert rel.assertion["predicates"]["like"]["basis"] == {"unknown": 1}
    assert rel.assertion["predicates"]["like"]["n"] == 0 and "n" not in {k for k in rel.assertion if k == "by"}
