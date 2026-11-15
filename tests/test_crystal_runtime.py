# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The crystal pass against a live registry: additive, fail-safe, rate-limited, switchable, and what it writes is what the weave found."""
import hashlib
import json
import os
import re

import pytest

from aurora_dimensional_systems import Crystal, CrystalLevel
from aurora_internal import crystal_runtime as R, crystal_substitutability as S


class Dps:
    """The registry's own shape and creation path (see CrystalProcessingSystem._get_or_create)."""
    def __init__(self, concepts=()):
        self.crystals, self.concept_index = {}, {}
        for c in concepts:
            self._get_or_create(c)

    def _get_or_create(self, concept):
        cid = self.concept_index.get(concept)
        if cid and cid in self.crystals:
            return self.crystals[cid]
        cid = hashlib.md5(concept.encode()).hexdigest()[:12]
        cr = Crystal(crystal_id=cid, concept=concept)
        self.crystals[cid], self.concept_index[concept] = cr, cid
        return cr


def rel(i, a, b, t, st=0.8, src="conversation"):
    return {"relation_id": f"r{i}", "source_word": a, "target_word": b, "relation_type": t, "strength": st, "confidence": 0.9, "source_of_knowledge": src}


def state(tmp_path, n=8):
    rels = {}
    for i in range(n):
        rels[f"a{i}"] = rel(i, f"fruit{i}", "fruit", "is_a", 0.9)
        for j, x in enumerate(("sweet", "eat", "tree")):
            rels[f"b{i}{j}"] = rel(f"{i}{j}", f"fruit{i}", x, "related_to", 0.6)
    (tmp_path / "aurora_oets_web.json").write_text(json.dumps({"nodes": {}, "relations": rels}))
    said = ". ".join(f"the {x} {c} the {y} runs" for x in ("cat", "dog", "bird", "fish") for c in ("and", "or", "but") for y in ("cat", "dog", "bird", "fish"))
    mem = {"entries": [{"timestamp": 100.0 + i, "session_id": "s", "user_said": said, "aurora_said": said} for i in range(3)]}
    (tmp_path / "aurora_conversation_memory.json").write_text(json.dumps(mem))
    return str(tmp_path)


def dps_for(n=8):
    return Dps([f"fruit{i}" for i in range(n)] + ["sweet", "eat", "tree", "cat", "dog", "bird", "fish", "and", "or", "but"])


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setitem(R._last, "t", None)
    monkeypatch.delenv("AURORA_CRYSTAL_WEAVE", raising=False)


# -- what it writes ----------------------------------------------------------------------------------------------------------------------------------

def test_the_pass_writes_links_facets_and_maturity_into_the_crystals_that_exist(tmp_path):
    d, dps = state(tmp_path), dps_for()
    r = R.run_pass(dps, d)
    assert r["ok"] and r["links"]["links"] > 0 and r["facets"]["facets"] > 0 and r["maturity"]["crystals"] > 0
    f0 = dps.get_crystal if hasattr(dps, "get_crystal") else None
    c = dps.crystals[dps.concept_index["fruit0"]]
    assert c.connections and any(f.role.startswith("fk:") for f in c.facets.values()) and c.maturity is not None and c.maturity["associative"] > 0.0
    assert dps.crystals[dps.concept_index["cat"]].maturity["associative"] >= 0.0                 # looked at, even where nothing was found


def test_a_generalization_that_holds_counted_members_gets_a_crystal_standing_above_them(tmp_path):
    d, dps = state(tmp_path), dps_for()
    assert "fruit" not in dps.concept_index
    r = R.run_pass(dps, d)
    assert r["generalization_crystals_created"] >= 1 and "fruit" in dps.concept_index
    hub = dps.crystals[dps.concept_index["fruit"]]
    assert hub.level > dps.crystals[dps.concept_index["fruit0"]].level and hub.level <= CrystalLevel.FULL_CONCEPT
    assert hub.connections and hub.maturity is not None


def test_a_label_with_no_counted_member_never_gets_a_crystal(tmp_path):
    (tmp_path / "aurora_oets_web.json").write_text(json.dumps({"nodes": {}, "relations": {"x": rel(1, "a", "label", "is_a", 1.0, src="seeded")}}))
    dps = Dps(["a"])
    assert R.run_pass(dps, str(tmp_path))["generalizations"] == 0 and "label" not in dps.concept_index


def test_the_words_she_uses_the_same_way_stand_in_for_each_other_and_are_linked(tmp_path):
    d, dps = state(tmp_path), dps_for()
    r = R.run_pass(dps, d)
    assert r["classes"] >= 1 and r["substitute_links"] > 0
    a, o = dps.crystals[dps.concept_index["and"]], dps.crystals[dps.concept_index["or"]]
    assert dps.concept_index["or"] in a.connections and dps.concept_index["and"] in o.connections


# -- additive ---------------------------------------------------------------------------------------------------------------------------------------

def test_nothing_that_was_there_is_removed_and_the_stronger_value_wins(tmp_path):
    d, dps = state(tmp_path), dps_for()
    c = dps.crystals[dps.concept_index["fruit0"]]
    c.add_facet("mine", {"v": 1}, confidence=0.4)
    c.connections["keepme"] = 0.77
    c.connections[dps.concept_index["sweet"]] = 0.99
    usage, level = c.usage_count, c.level
    R.run_pass(dps, d)
    assert any(f.role == "mine" for f in c.facets.values()) and c.connections["keepme"] == 0.77 and c.connections[dps.concept_index["sweet"]] == 0.99
    assert c.usage_count == usage and c.level == level


def test_running_it_again_changes_nothing_more(tmp_path):
    d, dps = state(tmp_path), dps_for()
    R.run_pass(dps, d, force=True)
    once = {cid: c.to_dict() for cid, c in dps.crystals.items()}
    R.run_pass(dps, d, force=True)
    again = {cid: c.to_dict() for cid, c in dps.crystals.items()}
    assert {k: (v["facets"].keys(), v["connections"], v["maturity"]) for k, v in once.items()} == {k: (v["facets"].keys(), v["connections"], v["maturity"]) for k, v in again.items()}


# -- safe to call from a save ------------------------------------------------------------------------------------------------------------------------

def test_it_can_be_turned_off(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_CRYSTAL_WEAVE", "0")
    dps = dps_for()
    assert R.run_pass(dps, state(tmp_path)) == {"skipped": "disabled"} and all(c.maturity is None for c in dps.crystals.values())


def test_it_runs_at_most_once_per_interval_unless_forced(tmp_path):
    d, dps = state(tmp_path), dps_for()
    t = [1000.0]
    assert R.run_pass(dps, d, clock=lambda: t[0])["ok"]
    t[0] += 10
    assert R.run_pass(dps, d, clock=lambda: t[0]) == {"skipped": "interval"}
    assert R.run_pass(dps, d, clock=lambda: t[0], force=True)["ok"]
    t[0] += R.MIN_INTERVAL
    assert R.run_pass(dps, d, clock=lambda: t[0])["ok"]


def test_it_never_raises_whatever_it_is_given(tmp_path):
    assert R.run_pass(object(), str(tmp_path))["ok"] is False
    assert R.run_pass(None, str(tmp_path / "nope"))["ok"] is False
    assert R.run_pass(Dps(["a"]), str(tmp_path / "nope"))["ok"] is True                        # no state at all: nothing to weave, nothing broken


def test_a_failed_pass_does_not_start_the_interval(tmp_path):
    d = state(tmp_path)
    assert R.run_pass(object(), d)["ok"] is False and R._last["t"] is None
    assert R.run_pass(dps_for(), d)["ok"] is True


# -- where it is called --------------------------------------------------------------------------------------------------------------------------------

def test_only_the_save_calls_it_and_it_sits_just_before_the_registry_is_persisted():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f != "crystal_runtime.py" and re.search(r"(from|import)\s+[\w.]*crystal_runtime", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == ["aurora.py"]
    src = open(os.path.join(root, "aurora.py"), encoding="utf-8").read()
    i = src.index("crystal_runtime.run_pass(")
    assert src.index("dimensional.save_state(state_dir)", i) - i < 1500 and "save_state(state_dir)" not in src[i - 1500:i]


# -- the rules a generalization follows, and the grammar reaching the registry -----------------------------------------------------------------

def test_a_generalization_never_reaches_the_top_level_by_structure_and_is_never_lowered(tmp_path):
    d = state(tmp_path, n=60)
    dps = dps_for(60)
    for i in range(60):
        dps.crystals[dps.concept_index[f"fruit{i}"]].level = CrystalLevel.QUASI                 # many members already at the top
    R.run_pass(dps, d, force=True)
    assert dps.crystals[dps.concept_index["fruit"]].level == CrystalLevel.FULL_CONCEPT           # above them as far as structure goes, never given the top level
    dps2 = dps_for(60)
    hub = dps2._get_or_create("fruit")
    hub.level = CrystalLevel.FULL_CONCEPT
    R.run_pass(dps2, d, force=True)
    assert hub.level == CrystalLevel.FULL_CONCEPT                                                # members are base-level: it is not pulled down to them


def test_the_class_she_finds_and_the_role_group_that_joins_it_reach_the_registry(tmp_path):
    d, dps = state(tmp_path), dps_for()
    role = dps._get_or_create("pragmatic:addition")                                              # a group's crystal, where one exists
    R.run_pass(dps, d)
    klass = [c for c in dps.concept_index if c.startswith("lexclass:S:")]
    assert klass                                                                                  # the class is a crystal of its own
    assert any(dps.concept_index[k] in role.connections for k in klass)                           # and the role group joined it
    assert any(dps.concept_index[k] in dps.crystals[dps.concept_index["and"]].connections for k in klass)   # and the words she found hold it


def test_the_pass_grows_the_interior_of_a_crystal_that_stands_at_the_top_level_and_spawns_nothing_for_it(tmp_path, monkeypatch):
    from aurora_internal import crystal_interior as I
    d = state(tmp_path)
    plain, deep = dps_for(), dps_for()
    R.run_pass(plain, d, force=True)
    assert all(not c.interior for c in plain.crystals.values())                      # no standing at the top level yet: no interior
    monkeypatch.setattr(I, "standing", lambda crystal: 0.8)
    r = R.run_pass(deep, d, force=True)
    assert r["interior"]["crystals_with_interior"] > 0 and r["interior"]["layers"] > 0 and r["interior"]["dry_run"] is False
    with_interior = [c for c in deep.crystals.values() if c.interior]
    assert with_interior and all(l["weight"] > 0 for c in with_interior for l in c.interior["layers"])
    assert sorted(deep.crystals) == sorted(plain.crystals) and deep.concept_index == plain.concept_index              # the aspects are inside, not new crystals
