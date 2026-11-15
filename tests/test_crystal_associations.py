# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build plan P1: associations between crystals are stored once with their source; only recurrence counts."""
import os

import pytest

from aurora_internal import crystal_associations as L
from aurora_internal.crystal_associations import AssociationStore, project_oets, apply_to_crystals


def rel(rid, a, b, rtype="related_to", source="co-occurrence", strength=1.0, confidence=1.0):
    return {"relation_id": rid, "source_word": a, "target_word": b, "relation_type": rtype,
            "source_of_knowledge": source, "strength": strength, "confidence": confidence}


def web(*rels):
    return {r["relation_id"]: r for r in rels}


# -- one record per association -----------------------------------------------------------------------------------------------------------

def test_an_association_is_one_record_however_often_it_is_met():
    s = AssociationStore()
    for i in range(1000):
        s.add("sunni", "builder", "related_to", ref=f"occ{i}", source="co-occurrence")
    assert len(s) == 1                                                  # one record, a thousand pieces of evidence attached
    assert len(s.evidence("sunni", "builder", "related_to")) == 1000


def test_recording_the_same_evidence_again_changes_nothing():
    s = AssociationStore()
    assert s.add("a", "b", "related_to", ref="r1", source="co-occurrence", strength=0.8) is True
    before = s.to_dict()
    assert s.add("a", "b", "related_to", ref="r1", source="co-occurrence", strength=0.8) is False
    assert s.to_dict() == before


def test_projecting_the_same_web_twice_is_the_same_as_once():
    w = web(rel("r1", "a", "b"), rel("r2", "b", "c", "enables"), rel("r3", "a", "c", source="backfill_role_heuristic"))
    once = project_oets(w)
    twice = project_oets(w, project_oets(w))
    assert twice.to_dict() == once.to_dict()


def test_symmetric_types_are_one_record_in_either_order_directed_types_are_not():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="x", source="co-occurrence")
    s.add("b", "a", "related_to", ref="y", source="co-occurrence")
    assert len(s) == 1
    s.add("a", "b", "enables", ref="p", source="co-occurrence")
    s.add("b", "a", "enables", ref="q", source="co-occurrence")
    assert len(s) == 3                                                  # a enables b and b enables a are different things


def test_degenerate_input_is_refused():
    s = AssociationStore()
    assert not s.add("a", "a", "related_to", ref="x", source="co-occurrence")
    assert not s.add("", "b", "related_to", ref="x", source="co-occurrence")
    assert not s.add("a", "b", "related_to", ref="", source="co-occurrence")
    assert len(s) == 0


# -- only recurrence counts ------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("source,basis", [
    ("co-occurrence", "recurrence"), ("co-expression", "recurrence"), ("research", "looked_up"),
    ("backfill_role_heuristic", "heuristic"), ("seeded", "seeded"), ("adjacency", "unattributed"),
    ("axis_embodiment", "unattributed"), ("definition_analysis", "unattributed"), ("something_new", "unknown"), ("", "unknown"),
])
def test_every_source_has_a_basis_and_an_unlisted_one_is_unknown(source, basis):
    assert L.basis_of(source) == basis


@pytest.mark.parametrize("source", ["research", "backfill_role_heuristic", "seeded", "adjacency", "axis_embodiment",
                                    "definition_analysis", "invented"])
def test_evidence_that_is_not_recurrence_is_kept_but_does_not_count(source):
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="x", source=source, strength=1.0)
    assert len(s) == 1 and s.strength("a", "b", "related_to") == 0.0
    assert s.connections_for("a") == {} and s.view("a")["counted"] == {}
    assert s.view("a")["uncounted_evidence"] == {L.basis_of(source): 1}


def test_recurrence_earns_a_link_that_a_label_could_not():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="h", source="backfill_role_heuristic")
    assert s.strength("a", "b", "related_to") == 0.0
    s.add("a", "b", "related_to", ref="o", source="co-occurrence", strength=0.6, confidence=1.0)
    assert s.strength("a", "b", "related_to") == pytest.approx(0.6)     # the heuristic evidence neither adds nor dilutes it
    assert s.view("a")["uncounted_evidence"] == {"heuristic": 1}        # and is still on record, as what it is


def test_strength_is_the_mean_of_counted_evidence_scaled_by_confidence():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="1", source="co-occurrence", strength=1.0, confidence=0.5)
    s.add("a", "b", "related_to", ref="2", source="co-expression", strength=0.5, confidence=1.0)
    assert s.strength("a", "b", "related_to") == pytest.approx((0.5 + 0.5) / 2)


def test_values_are_clamped_to_zero_one():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="1", source="co-occurrence", strength=7.0, confidence=-3.0)
    e = s.evidence("a", "b", "related_to")["1"]
    assert e["strength"] == 1.0 and e["confidence"] == 0.0


# -- the one view of a concept -------------------------------------------------------------------------------------------------------------

def test_a_concept_is_viewed_once_with_everything_attached():
    w = web(rel("r1", "sunni", "builder", "is_a"), rel("r2", "sunni", "aurora", "enables"),
            rel("r3", "tea", "sunni", "related_to"), rel("r4", "sunni", "king", "related_to", source="research"),
            rel("r5", "x", "y"))
    v = project_oets(w).view("sunni")
    assert set(v["counted"]) == {"is_a", "enables", "related_to"}
    assert v["counted"]["is_a"][0] == {"with": "builder", "strength": 1.0, "direction": "out", "evidence": 1}
    assert v["counted"]["related_to"][0]["with"] == "tea" and v["counted"]["related_to"][0]["direction"] == "both"
    assert v["uncounted_evidence"] == {"looked_up": 1}                  # the looked-up association is on record, not counted
    assert "x" not in str(v) and "y" not in str(v)


def test_connections_for_takes_the_strongest_across_types():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="1", source="co-occurrence", strength=0.3)
    s.add("a", "b", "enables", ref="2", source="co-occurrence", strength=0.9)
    assert s.connections_for("a") == {"b": pytest.approx(0.9)}
    assert s.connections_for("b") == {"a": pytest.approx(0.9)}


# -- persistence ---------------------------------------------------------------------------------------------------------------------------

def test_save_and_load_roundtrip_and_a_missing_or_broken_file_is_an_empty_store(tmp_path):
    s = project_oets(web(rel("r1", "a", "b"), rel("r2", "b", "c", "enables", source="research")))
    p = str(tmp_path / "links.json")
    s.save(p)
    assert AssociationStore.load(p).to_dict() == s.to_dict()
    assert len(AssociationStore.load(str(tmp_path / "missing.json"))) == 0
    (tmp_path / "bad.json").write_text("{not json")
    assert len(AssociationStore.load(str(tmp_path / "bad.json"))) == 0
    assert [f for f in os.listdir(tmp_path) if f.startswith(".crystal_associations.")] == []   # no temp file left behind


def test_a_failed_save_leaves_the_old_file_intact_and_no_temp_file(tmp_path, monkeypatch):
    p = str(tmp_path / "links.json")
    old = project_oets(web(rel("r1", "a", "b")))
    old.save(p)
    new = project_oets(web(rel("r1", "a", "b"), rel("r2", "c", "d")))
    monkeypatch.setattr(L.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        new.save(p)
    assert AssociationStore.load(p).to_dict() == old.to_dict()
    assert [f for f in os.listdir(tmp_path) if f.startswith(".crystal_associations.")] == []


# -- applying to crystals (the only place anything is written) ---------------------------------------------------------------------

class FakeCrystal:
    def __init__(self):
        self.connections = {}


def world():
    s = project_oets(web(rel("r1", "a", "b", strength=0.9), rel("r2", "a", "c", strength=0.5), rel("r3", "a", "d", strength=0.7),
                         rel("r4", "a", "e", source="backfill_role_heuristic"), rel("r5", "a", "ghost", strength=1.0)))
    idx = {c: f"id_{c}" for c in "abcde"}                               # "ghost" has no crystal
    cr = {f"id_{c}": FakeCrystal() for c in "abcde"}
    return s, idx, cr


def test_dry_run_is_the_default_and_changes_nothing():
    s, idx, cr = world()
    out = apply_to_crystals(s, idx, cr)
    assert out["dry_run"] is True and out["crystals_with_connections"] == 4
    assert all(c.connections == {} for c in cr.values())


def test_apply_writes_only_counted_links_to_existing_crystals_strongest_first_and_bounded():
    s, idx, cr = world()
    out = apply_to_crystals(s, idx, cr, max_per_crystal=2, dry_run=False)
    assert cr["id_a"].connections == {"id_b": 0.9, "id_d": 0.7}         # bounded to the two strongest; c fell off the end
    assert "id_e" not in cr["id_a"].connections                         # heuristic only: never reaches a crystal
    assert "ghost" not in str(cr["id_a"].connections)                   # no crystal for it: none is created
    assert cr["id_b"].connections == {"id_a": 0.9}                      # symmetric type: both ends
    assert cr["id_e"].connections == {}
    assert out["dry_run"] is False


def test_a_concept_whose_crystal_has_gone_is_not_linked_to():
    s, idx, cr = world()
    idx["ghost"] = "id_ghost"                                           # indexed, but the crystal itself is not there
    apply_to_crystals(s, idx, cr, dry_run=False)
    assert all("id_ghost" not in c.connections for c in cr.values())


def test_apply_keeps_existing_connections_and_the_stronger_value_wins():
    s, idx, cr = world()
    cr["id_a"].connections = {"id_b": 0.95, "id_x": 0.2}
    apply_to_crystals(s, idx, cr, dry_run=False)
    assert cr["id_a"].connections["id_b"] == 0.95 and cr["id_a"].connections["id_x"] == 0.2
    assert cr["id_a"].connections["id_d"] == 0.7


def test_apply_twice_is_the_same_as_once():
    s, idx, cr = world()
    apply_to_crystals(s, idx, cr, dry_run=False)
    first = {k: dict(c.connections) for k, c in cr.items()}
    apply_to_crystals(s, idx, cr, dry_run=False)
    assert {k: dict(c.connections) for k, c in cr.items()} == first


def test_it_works_on_the_real_crystal_and_its_serialisation():
    from aurora_dimensional_systems import Crystal
    s, idx, _ = world()
    cr = {f"id_{c}": Crystal(crystal_id=f"id_{c}", concept=c) for c in "abcde"}
    apply_to_crystals(s, idx, cr, dry_run=False)
    assert cr["id_a"].connections["id_b"] == 0.9
    back = Crystal.from_dict(cr["id_a"].to_dict())
    assert back.connections == cr["id_a"].connections                   # survives the crystal's own save and load


# -- isolation -----------------------------------------------------------------------------------------------------------------------------

def test_the_module_imports_nothing_from_the_rest_of_aurora():
    import ast
    tree = ast.parse(open(L.__file__, encoding="utf-8").read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m.startswith("aurora") for m in mods)


def test_nothing_in_the_running_system_calls_it():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f not in ("crystal_associations.py", "crystal_convergence.py", "crystal_facets.py", "crystal_weave.py", "crystal_promotion.py", "crystal_grammar.py", "crystal_runtime.py", "crystal_substitutability.py", "crystal_interior.py"):
                if "crystal_associations" in open(os.path.join(base, f), encoding="utf-8", errors="ignore").read():
                    hits.append(f)
    assert hits == []


# -- what was said (the propositional store's assertion records) ------------------------------------------------------------------------

def said(rid, src, tgt, preds, **kw):
    return {rid: {"relation_id": rid, "source_word": src, "target_word": tgt, "relation_type": "related_to",
                  "source_of_knowledge": "assertion", "strength": 1.0, "confidence": 1.0, "assertion": {"predicates": preds}, **kw}}


def test_a_predicate_said_between_two_things_is_an_association_from_subject_to_object():
    from aurora_internal.crystal_associations import project_assertions
    s = project_assertions(said("r1", "mara", "tea", {"like": {"n": 4, "denied": 0, "basis": {"told": 4}}}))
    assert s.strength("mara", "tea", "like") == pytest.approx(1.0)
    assert s.strength("tea", "mara", "like") == 0.0                      # it runs one way
    assert s.view("mara")["counted"]["like"][0]["direction"] == "out" and s.view("tea")["counted"]["like"][0]["direction"] == "in"


def test_being_denied_weakens_an_association_in_proportion_and_contests_it():
    from aurora_internal.crystal_associations import project_assertions
    vals, cont = [], []
    for denied in range(0, 5):
        s = project_assertions(said("r1", "mara", "tea", {"like": {"n": 4, "denied": denied, "basis": {"told": 4}}}))
        vals.append(s.strength("mara", "tea", "like"))
        cont.append(s.contested("mara", "tea", "like"))
    assert vals == [pytest.approx(1.0), pytest.approx(0.5), 0.0, 0.0, 0.0]               # (held - denied) over all the times it was said, floored at 0
    assert cont == [0.0, pytest.approx(0.5), pytest.approx(1.0), pytest.approx(0.5), 0.0]   # argued over most when split evenly, not at the ends


def test_a_correction_decides_and_what_came_before_stays_in_the_relations_own_history():
    from aurora_internal.crystal_associations import project_assertions
    p = {"like": {"n": 5, "denied": 1, "basis": {"told": 4, "corrected": 1}, "settled": {"d": 1, "t": 1, "by": "sunni"}}}
    s = project_assertions(said("r1", "mara", "tea", p))
    assert s.strength("mara", "tea", "like") == 0.0
    ev = s.evidence("mara", "tea", "like")
    assert len(ev) == 1 and next(iter(ev.values()))["basis"] == "corrected"


def test_the_basis_is_how_it_came_to_be_held():
    from aurora_internal.crystal_associations import project_assertions
    s = project_assertions(said("r1", "a", "b", {"be a": {"n": 3, "denied": 0, "basis": {"observed": 3}}}))
    assert next(iter(s.evidence("a", "b", "be a").values()))["basis"] == "observed"
    s2 = project_assertions(said("r1", "a", "b", {"be a": {"n": 3, "denied": 0}}))              # no basis recorded: told
    assert next(iter(s2.evidence("a", "b", "be a").values()))["basis"] == "told"


def test_projecting_assertions_twice_is_the_same_as_once_and_empty_predicates_add_nothing():
    from aurora_internal.crystal_associations import project_assertions
    w = said("r1", "a", "b", {"like": {"n": 2, "denied": 1, "basis": {"told": 2}}, "ghost": {"n": 0}})
    once = project_assertions(w)
    assert project_assertions(w, project_assertions(w)).to_dict() == once.to_dict()
    assert "ghost" not in str(once.to_dict())


def test_a_relation_with_nothing_said_along_it_adds_nothing_here():
    from aurora_internal.crystal_associations import project_assertions
    assert len(project_assertions(web(rel("r1", "a", "b")))) == 0


def test_incoming_lists_what_a_concept_holds_with_the_degree_and_ignores_the_uncounted():
    s = AssociationStore()
    s.add("a", "letter", "is_a", ref="1", source="co-occurrence", strength=0.9)
    s.add("b", "letter", "is_a", ref="2", source="backfill_role_heuristic", strength=1.0)
    s.add("letter", "word", "is_a", ref="3", source="co-occurrence", strength=0.5)
    assert s.incoming("letter", "is_a") == {"a": pytest.approx(0.9)}


# -- the per-concept index answers exactly what a scan of every link would -----------------------------------------------------------------------------

def _scan_connections(s, c):
    out = {}
    for (a, b, rtype) in s._links:
        if c not in (a, b):
            continue
        other = b if a == c else a
        v = s.strength(a, b, rtype)
        if v > out.get(other, 0.0):
            out[other] = v
    return out


def _scan_incoming(s, c, rtype):
    return {a: s.strength(a, b, t) for (a, b, t) in s._links if t == rtype and b == c and a != c and s.strength(a, b, t) > 0.0}


def test_the_index_agrees_with_a_full_scan_through_interleaved_writes_and_a_load():
    import random
    rnd = random.Random(3)
    s = AssociationStore()
    names = [f"c{i}" for i in range(15)]
    for step in range(120):
        a, b = rnd.sample(names, 2)
        s.add(a, b, rnd.choice(["is_a", "related_to", "causes"]), ref=f"r{step}", source=rnd.choice(["conversation", "seeded", "co-occurrence"]), strength=rnd.random())
        if step % 7 == 0:                                                       # reads between writes, so the index is used while keys are still arriving
            for c in names[:4]:
                assert s.connections_for(c) == _scan_connections(s, c)
    for c in names + ["nothing"]:
        assert s.connections_for(c) == _scan_connections(s, c) and list(s.connections_for(c)) == list(_scan_connections(s, c))
        assert s.incoming(c, "is_a") == _scan_incoming(s, c, "is_a")
    back = AssociationStore.from_dict(s.to_dict())
    assert all(back.connections_for(c) == _scan_connections(back, c) for c in names)
    s.add("c0", "newcomer", "related_to", ref="late", source="conversation", strength=0.5)      # a key added after reads is seen at once
    assert s.connections_for("newcomer") == {"c0": 0.5}


def test_equal_strengths_are_chosen_by_name_so_a_pass_is_the_same_whatever_order_things_arrived_in():
    class C:
        connections = None
    for order in (["a", "b", "c", "d"], ["d", "c", "b", "a"], ["c", "a", "d", "b"]):
        s = AssociationStore()
        for o in order:
            s.add("hub", o, "related_to", ref=f"r{o}", source="conversation", strength=0.5)
        crystals = {"H": C(), **{o: C() for o in "abcd"}}
        idx = {"hub": "H", **{o: o for o in "abcd"}}
        apply_to_crystals(s, idx, crystals, max_per_crystal=2, dry_run=False)
        assert sorted(crystals["H"].connections) == ["a", "b"]
