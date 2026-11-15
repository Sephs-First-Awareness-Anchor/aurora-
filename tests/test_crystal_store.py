# Authors: Sunni (Sir) Morningstar & Cael Devo
"""One crystal store: a word is one crystal whatever bookkeeping label it arrived under; namespaced entities are left alone; nothing is lost in the merge."""
import ast
import os
import re

import pytest

from aurora_dimensional_systems import Crystal, CrystalLevel, CrystalProcessingSystem
from aurora_internal import crystal_store as CS


class Tracker:
    def record(self, *a, **k):
        pass


def registry():
    return CrystalProcessingSystem(tracker=Tracker())


def put(dps, concept, facets=(), usage=0, conns=None, level=CrystalLevel.BASE):
    """Plant a crystal exactly as an older save would hold it: under its (possibly labelled) name, bypassing the canonical path."""
    import hashlib
    cid = hashlib.md5(concept.encode()).hexdigest()[:12]
    c = Crystal(crystal_id=cid, concept=concept, level=level)
    for role, content in facets:
        c.add_facet(role, content, confidence=0.5)
    c.usage_count = usage
    c.connections = dict(conns or {})
    dps.crystals[cid] = c
    dps.concept_index[concept] = cid
    return c


# -- the names ------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,bare,prefix", [
    ("learned:come", "come", "learned"), ("foundational:light", "light", "foundational"), ("from_definition:time", "time", "from_definition"),
    ("from meaning:cost", "cost", "from meaning"), ("internal:x", "x", "internal"), ("pending:y", "y", "pending"), ("research:z", "z", "research"),
    ("context:w", "w", "context"),
])
def test_a_word_under_a_bookkeeping_label_is_the_word(name, bare, prefix):
    assert CS.canonical(name) == (bare, prefix) and CS.bare_of(name) == bare


@pytest.mark.parametrize("name", [
    "come", "learned:", "learned: ", "tensor:MANIFOLD:X:NC[N:COST]", "sensory:semantic:warm", "REFAB:X:OPERATOR", "behavioral:audio:sensitivity",
    "turn:12", "https://otter.ai", "concept:abc", "tensor_variant:a:b", "Learned:come",
])
def test_a_namespaced_entity_or_a_bare_label_is_left_as_it_is(name):
    assert CS.canonical(name) == (name, None)


def test_the_labels_are_the_ones_the_rest_of_the_system_already_treats_as_bookkeeping():
    src = open(os.path.join(os.path.dirname(__file__), "..", "aurora.py"), encoding="utf-8").read()
    m = re.search(r"_PLACEHOLDER_DEFINITION_PREFIXES = \((.*?)\)", src, re.S)
    theirs = set(ast.literal_eval("(" + m.group(1) + ")"))
    assert theirs <= set(CS.PREFIXES) and set(CS.PREFIXES) - theirs == {"foundational:"}


# -- creation: the same crystal from either name ---------------------------------------------------------------------------------------------------

def test_creating_a_word_under_a_label_gives_the_crystal_of_the_word_with_the_label_as_provenance():
    d = registry()
    a, b, c = d._get_or_create("learned:come"), d._get_or_create("come"), d._get_or_create("foundational:come")
    assert a is b is c and len(d.crystals) == 1 and a.concept == "come"
    assert sorted(f.content for f in a.facets.values() if f.role.startswith("provenance:")) == ["foundational", "learned"]
    assert d.get_crystal("learned:come") is a and d.get_crystal("internal:come") is a and d.get_crystal("nothing") is None
    again = d._get_or_create("learned:come")
    assert again is a and sum(1 for f in a.facets.values() if f.role.startswith("provenance:")) == 2


def test_other_names_are_still_their_own_crystals():
    d = registry()
    a, b = d._get_or_create("tensor:MANIFOLD:X"), d._get_or_create("sensory:semantic:warm")
    assert a is not b and len(d.crystals) == 2 and a.concept == "tensor:MANIFOLD:X"


def test_a_name_with_provenance_alone_does_not_count_toward_growth_by_the_old_rule():
    d = registry()
    c = d._get_or_create("learned:come")
    c.usage_count = 99
    assert c.can_evolve() is False                      # one provenance facet is not three learned ones


# -- the fold ------------------------------------------------------------------------------------------------------------------------------------------

def test_a_labelled_duplicate_is_merged_into_the_crystal_of_its_word_and_loses_nothing():
    d = registry()
    word = put(d, "come", [("lexicon:verb", "X:OPERATOR"), ("oets:i_is", "to move toward")], usage=5, conns={"zzz": 0.4, "www": 0.8}, level=CrystalLevel.COMPOSITE)
    dup = put(d, "learned:come", [("lexicon:noun", "learned:come"), ("oets:oets", "def:come"), ("provenance:internal", "internal")], usage=2, conns={"zzz": 0.9, "yyy": 0.3, "www": 0.2})
    other = put(d, "go", conns={dup.crystal_id: 0.6})
    r = CS.fold_duplicates(d)
    assert r == {"folded": 1, "renamed": 0, "aliases": 1}
    assert dup.crystal_id not in d.crystals and d.crystals[word.crystal_id] is word
    roles = {(f.role, f.content) for f in word.facets.values()}
    assert {("lexicon:verb", "X:OPERATOR"), ("oets:i_is", "to move toward"), ("oets:oets", "def:come"), ("provenance:learned", "learned"),
            ("provenance:internal", "internal")} <= roles                                              # a label it already carried is kept too
    assert ("lexicon:noun", "come") in roles and ("lexicon:noun", "learned:come") not in roles          # the label-only facet says the word, as seeding does
    assert word.usage_count == 7 and word.connections == {"zzz": 0.9, "yyy": 0.3, "www": 0.8} and word.level == CrystalLevel.COMPOSITE
    assert other.connections == {word.crystal_id: 0.6}                                                   # ties to the duplicate now tie to the one
    assert d.get_crystal("learned:come") is word and d.concept_index["learned:come"] == word.crystal_id


def test_the_higher_level_and_earlier_birth_are_kept():
    d = registry()
    word = put(d, "light", level=CrystalLevel.BASE)
    dup = put(d, "foundational:light", level=CrystalLevel.COMPOSITE)
    word.created_at, dup.created_at = 200.0, 100.0
    CS.fold_duplicates(d)
    assert word.level == CrystalLevel.COMPOSITE and word.created_at == 100.0


def test_a_labelled_crystal_with_no_crystal_of_its_word_becomes_it():
    d = registry()
    only = put(d, "learned:gift", [("lexicon:noun", "learned:gift")], usage=3)
    cid = only.crystal_id
    r = CS.fold_duplicates(d)
    assert r["renamed"] == 1 and r["folded"] == 0 and d.crystals[cid] is only and only.concept == "gift"
    assert d.concept_index["gift"] == cid and d.concept_index["learned:gift"] == cid and only.usage_count == 3
    assert ("lexicon:noun", "gift") in {(f.role, f.content) for f in only.facets.values()}
    assert any(f.role == "provenance:learned" and f.content == "learned" for f in only.facets.values())


def test_folding_twice_changes_nothing_more_and_other_namespaces_are_untouched():
    d = registry()
    put(d, "come", [("lexicon:verb", "X:OPERATOR")], usage=5)
    put(d, "learned:come", [("lexicon:noun", "learned:come")], usage=2)
    t = put(d, "tensor:MANIFOLD:X", [("cers_visit", "1")])
    CS.fold_duplicates(d)
    snap = {cid: c.to_dict() for cid, c in d.crystals.items()}
    assert CS.fold_duplicates(d) == {"folded": 0, "renamed": 0, "aliases": 0} or CS.fold_duplicates(d)["folded"] == 0
    assert {cid: c.to_dict() for cid, c in d.crystals.items()} == snap and d.crystals[t.crystal_id] is t


def test_a_pair_of_labels_for_one_word_all_land_on_the_one_crystal():
    d = registry()
    word = put(d, "time", usage=1)
    put(d, "from_definition:time", [("oets:oets", "from_definition:time")], usage=1)
    put(d, "learned:time", [("lexicon:noun", "learned:time")], usage=1)
    r = CS.fold_duplicates(d)
    assert r["folded"] == 2 and len(d.crystals) == 1 and word.usage_count == 3
    assert sorted(f.content for f in word.facets.values() if f.role.startswith("provenance:")) == ["from_definition", "learned"]


def test_the_crystal_links_follow_the_fold():
    d = registry()
    word = put(d, "come")
    dup = put(d, "learned:come")
    other = put(d, "go")
    d.crystal_links = {dup.crystal_id: {other.crystal_id: 0.7}, other.crystal_id: {dup.crystal_id: 0.5, word.crystal_id: 0.2}}
    CS.fold_duplicates(d)
    assert d.crystal_links == {word.crystal_id: {other.crystal_id: 0.7}, other.crystal_id: {word.crystal_id: 0.5}}
    assert d.folded_ids == {dup.crystal_id: word.crystal_id}


def test_the_primary_index_has_one_entry_per_crystal_even_with_aliases():
    d = registry()
    put(d, "come")
    put(d, "learned:come")
    CS.fold_duplicates(d)
    assert len(d.concept_index) == 2 and CS.primary_index(d) == {"come": d.concept_index["come"]}


def test_the_seeding_writes_the_bare_word_where_it_used_to_write_the_label():
    from aurora_crystal_ingestion import seed_dps_from_lexicon_and_oets

    class E:
        def __init__(self, role, nid):
            self.role, self.noncomp_id, self.valence = role, nid, 0.0

    class Lex:
        entries = {"learned:come": E("noun", None), "come": E("verb", "X:OPERATOR")}

    class Perc:
        lexicon, oets = Lex(), None
    d = registry()
    seed_dps_from_lexicon_and_oets(d, {"perception": Perc()})
    assert len(d.crystals) == 1
    c = next(iter(d.crystals.values()))
    assert {("lexicon:noun", "come"), ("lexicon:verb", "X:OPERATOR")} <= {(f.role, f.content) for f in c.facets.values()}


def test_only_what_has_been_learned_counts_toward_growth_by_the_old_rule_never_where_a_name_came_from():
    d = registry()
    c = put(d, "come", [("lexicon:verb", "a"), ("oets:x", "b"), ("provenance:learned", "learned")], usage=10)
    assert c.maturity is None and c.can_evolve() is False
    c.add_facet("oets:y", "c", confidence=0.5)
    assert c.can_evolve() is True
