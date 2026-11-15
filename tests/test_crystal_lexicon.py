# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The lexicon in the one crystal store: one entry per word; its role, channel, meaning and valence at their facets, each with its true basis."""
import json

from aurora_dimensional_systems import Crystal, CrystalLevel, CrystalProcessingSystem
from aurora_internal import crystal_facets as F
from aurora_internal import crystal_lexicon as L
from aurora_internal import crystal_runtime as R


class Tracker:
    def record(self, *a, **k):
        pass


def entry(meaning="", role="noun", valence=0.0, usage=0, last=0.0, lineage="", nid=None):
    return {"meaning": meaning, "role": role, "emotional_valence": valence, "usage_count": usage, "last_used": last, "lineage": lineage, "noncomp_id": nid}


# -- folding -----------------------------------------------------------------------------------------------------------------------------------------

def test_a_label_entry_folds_into_the_words_own_entry():
    folded, rep = L.fold_entries({
        "come": entry("learned:come", "verb", 0.0, 1, 5.0, "i_is", "X:OPERATOR"),
        "learned:come": entry("def:come", "noun", 0.2, 2, 9.0, "oets", None)})
    assert list(folded) == ["come"] and rep["merged"] == 1
    e = folded["come"]
    assert e["role"] == "verb" and e["noncomp_id"] == "X:OPERATOR" and e["lineage"] == "i_is"          # the word's own fields win
    assert e["usage_count"] == 3 and e["last_used"] == 9.0 and e["emotional_valence"] == 0.2         # usage adds, later use kept, a blank is filled


def test_a_real_meaning_is_never_replaced_by_a_placeholder_and_a_placeholder_gives_way_to_a_real_one():
    keep, _ = L.fold_entries({"am": entry("existence"), "learned:am": entry("def:am")})
    assert keep["am"]["meaning"] == "existence"
    gain, _ = L.fold_entries({"am": entry("learned:am"), "learned:am": entry("a state of being")})
    assert gain["am"]["meaning"] == "a state of being"


def test_a_label_with_no_word_entry_becomes_the_words_entry_and_the_fold_is_idempotent_and_order_free():
    src = {"learned:gift": entry("def:gift", "noun", usage=4), "tree": entry("plant"), "learned:tree": entry("def:tree", usage=1)}
    a, rep = L.fold_entries(src)
    assert set(a) == {"gift", "tree"} and rep == {"merged": 1, "renamed": 1, "entries": 2} and a["gift"]["usage_count"] == 4
    assert L.fold_entries(a)[0] == a
    assert L.fold_entries(dict(reversed(list(src.items()))))[0] == a


def test_a_namespaced_entity_is_not_a_label():
    f, _ = L.fold_entries({"tensor:x": entry("m"), "tensor": entry("n")})
    assert set(f) == {"tensor:x", "tensor"}


def test_fold_file_rewrites_only_when_there_is_something_to_fold(tmp_path):
    p = tmp_path / "lexicon.json"
    p.write_text(json.dumps({"version": 1, "entries": {"a": entry("x"), "learned:a": entry("def:a", usage=2)}}))
    assert L.fold_file(str(tmp_path))["merged"] == 1
    d = json.loads(p.read_text())
    assert list(d["entries"]) == ["a"] and d["entries"]["a"]["usage_count"] == 2 and d["version"] == 1
    before = p.read_text()
    assert L.fold_file(str(tmp_path))["merged"] == 0 and p.read_text() == before


def test_meaning_that_is_a_label_or_pointer_is_not_a_meaning():
    for t in ("", "learned:x", "def:x", "oets:time", "from_definition:x", "x", "unknown"):
        assert not L.is_real_meaning("x", t), t
    assert L.is_real_meaning("x", "a thing she can name")


# -- placing --------------------------------------------------------------------------------------------------------------------------------------

def test_what_a_lexicon_entry_knows_goes_to_its_facets_with_its_true_basis_and_none_of_it_counts():
    book = F.FacetBook()
    n = L.place(book, {"am": entry("existence", "verb", 0.3, 9, 0.0, "", "X:OPERATOR"), "come": entry("learned:come", "verb", 0.0, 1, 0.0, "i_is", "X:OPERATOR")})
    assert n == {"lexicon": 2, "definition": 1, "emotion": 1}                     # `learned:come` is not a definition; zero valence is not a valence
    held = book.held_for("am", ("lexicon", "definition", "emotion"))
    assert {k: v[0]["bases"] for k, v in held.items()} == {"lexicon": ["seeded"], "definition": ["seeded"], "emotion": ["seeded"]}
    assert book.held_for("come", ("lexicon",))["lexicon"][0]["bases"] == ["unattributed"]
    assert book.facets_for("am") == {} and book.facets_for("come") == {}           # given or derived is never counted


def test_an_oets_definition_that_is_a_label_is_not_placed_as_a_definition():
    book = F.FacetBook()
    F.place_oets_node(book, {"word": "come", "definitions": [{"text": "learned:come", "source": "initial"}, {"text": "to move toward", "source": "initial"}]})
    assert [r["content"]["text"] for r in book.held_for("come", ("definition",))["definition"]] == ["to move toward"]


# -- on crystals --------------------------------------------------------------------------------------------------------------------------------------

def registry():
    return CrystalProcessingSystem(tracker=Tracker())


def crystal(dps, name):
    c = Crystal(crystal_id=f"id_{name}", concept=name, level=CrystalLevel.BASE)
    dps.crystals[c.crystal_id] = c
    dps.concept_index[name] = c.crystal_id
    return c


def test_held_facets_are_visible_on_the_crystal_at_zero_confidence_create_no_crystal_and_never_drive_growth():
    d = registry()
    c = crystal(d, "am")
    book = F.FacetBook()
    L.place(book, {"am": entry("existence", "verb", 0.3, 0, 0.0, "", "X:OPERATOR"), "ghost": entry("a spirit", "noun")})
    rep = F.apply_held_to_crystals(book, d.concept_index, d.crystals, dry_run=False)
    assert rep["crystals_touched"] == 1 and "ghost" not in d.concept_index
    roles = {f.role: f for f in c.facets.values()}
    assert set(roles) == {"held:lexicon", "held:definition", "held:emotion"} and all(f.confidence == 0.0 for f in roles.values())
    assert roles["held:definition"].content["entries"][0]["content"] == {"text": "existence"}
    before = c.can_evolve() if hasattr(c, "can_evolve") else None
    assert F.apply_held_to_crystals(book, d.concept_index, d.crystals, dry_run=False)["crystals_touched"] == 1       # again: same, no new facets
    assert len(c.facets) == 3 and (c.can_evolve() if hasattr(c, "can_evolve") else None) == before


def test_a_held_entry_that_later_gains_counted_evidence_leaves_the_held_facet():
    d = registry()
    c = crystal(d, "am")
    book = F.FacetBook()
    L.place(book, {"am": entry("existence")})
    F.apply_held_to_crystals(book, d.concept_index, d.crystals, dry_run=False)
    assert c.facets and next(iter(c.facets.values())).content["entries"]
    k = F.content_key("existence")
    book.add("am", "definition", k, {"text": "existence"}, ref="told:1", source="told")          # said to her
    F.apply_held_to_crystals(book, d.concept_index, d.crystals, dry_run=False)
    assert next(f for f in c.facets.values() if f.role == "held:definition").content == {"entries": []}
    F.apply_to_crystals(book, d.concept_index, d.crystals, dry_run=False)
    assert any(f.role == "fk:definition" for f in c.facets.values())


# -- the pass -----------------------------------------------------------------------------------------------------------------------------------------

def test_the_pass_folds_the_lexicon_in_view_and_places_it_on_the_words_crystal(tmp_path):
    (tmp_path / "lexicon.json").write_text(json.dumps({"version": 1, "entries": {
        "come": entry("learned:come", "verb", 0.0, 1, 0.0, "i_is", "X:OPERATOR"), "learned:come": entry("def:come", "noun", 0.0, 0, 0.0, "oets", None),
        "am": entry("existence", "verb", 0.3, 9, 0.0, "", "X:OPERATOR")}}))
    d = registry()
    crystal(d, "come"), crystal(d, "am")
    r = R.run_pass(d, str(tmp_path), force=True)
    assert r["ok"] and r["held"]["crystals_touched"] >= 2
    am = {f.role: f for f in d.crystals[d.concept_index["am"]].facets.values()}
    assert am["held:definition"].content["entries"][0]["content"] == {"text": "existence"}
    come = {f.role: f for f in d.crystals[d.concept_index["come"]].facets.values()}
    assert "held:definition" not in come and "held:lexicon" in come            # `learned:come` is no definition; its role and channel are placed
    assert "learned:come" not in d.concept_index
    assert "learned:come" in json.loads((tmp_path / "lexicon.json").read_text())["entries"]       # the pass only reads the file


# -- the vocabulary itself -------------------------------------------------------------------------------------------------------------------------

def test_the_vocabulary_folds_labels_when_it_loads_and_files_a_new_word_under_the_word():
    import aurora_expression_perception as E
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with open(f"{td}/lexicon.json", "w") as fh:
            json.dump({"version": 1, "entries": {"come": entry("learned:come", "verb", usage=1), "learned:come": entry("def:come", "noun", usage=2)}}, fh)
        m = E.LexicalMemory(state_dir=td)
        assert "learned:come" not in m.entries and m.entries["come"].role == "verb" and m.entries["come"].usage_count == 3
        m.add_word("learned:zebra", "learned:zebra", "noun")
        assert "zebra" in m.entries and "learned:zebra" not in m.entries
