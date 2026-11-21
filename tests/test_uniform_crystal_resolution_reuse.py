"""The SAME ordinary crystals feed qualified understanding, recall and speech.

No new crystal class, specialized type, or separate knowledge store is used.
"""
import json
from types import SimpleNamespace

from concept_crystal import ConceptCrystalRegistry
from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal import crystal_facets as F
from aurora_internal.aurora_representation_crystals import RepresentationCrystals
from aurora_internal.aurora_live_experience import crystal_context_for_turn


def _runtime():
    dps = CrystalProcessingSystem(EvolutionTracker())
    registry = ConceptCrystalRegistry()
    registry.bind(dps.crystals, dps.concept_index)
    dps._get_or_create("lantern")
    return dps, registry


def _facet(crystal, role):
    return next(f for f in crystal.facets.values() if f.role == role)


def test_one_ordinary_concept_crystal_retains_histories_and_genuine_correction():
    dps, registry = _runtime()
    book = F.FacetBook()
    book.add("lantern", "condition", "switch-and-battery",
             {"type": "depends_on", "other": "battery"},
             ref="experience:one", source="conversation", basis="observed",
             strength=0.8, context={"episode": "first", "battery": "connected"},
             consequence={"lit": True}, ancestry=["ep:first"])
    idx = {"lantern": dps.concept_index["lantern"]}
    F.apply_to_crystals(book, idx, dps.crystals, dry_run=False)
    cr = registry.crystal_by_id(idx["lantern"])
    initial = _facet(cr, "fk:condition").confidence
    assert initial == 0.8
    count_before = len(dps.crystals)
    book.add("lantern", "condition", "switch-and-battery",
             {"type": "depends_on", "other": "battery"},
             ref="experience:two", source="conversation", basis="corrected",
             strength=0.5, polarity=-1,
             context={"episode": "second", "battery": "disconnected"},
             consequence={"lit": False}, ancestry=["ep:second"])
    F.apply_to_crystals(book, idx, dps.crystals, dry_run=False)
    assert len(dps.crystals) == count_before
    facet = _facet(cr, "fk:condition")
    assert abs(facet.confidence - 0.4) < 1e-8
    entry = facet.content["entries"][0]
    assert entry["contexts"] == 2
    assert {o["ref"] for o in entry["occasions"]} == {"experience:one", "experience:two"}
    assert {o["polarity"] for o in entry["occasions"]} == {1, -1}
    assert entry["occasions"][0]["context"] != entry["occasions"][1]["context"]
    assert F.FacetBook.from_dict(book.to_dict()).to_dict() == book.to_dict()
    again = json.dumps(cr.to_dict(), sort_keys=True)
    F.apply_to_crystals(book, idx, dps.crystals, dry_run=False)
    assert json.dumps(cr.to_dict(), sort_keys=True) == again


def test_recall_reads_same_existing_facets_without_new_evidence_or_crystals():
    dps, registry = _runtime()
    book = F.FacetBook()
    book.add("lantern", "episode_ref", "turn1",
             {"summary": "I repaired the lantern.", "id": "turn1"},
             ref="conv:turn1:heard:lantern", source="conversation", basis="told",
             context={"session": "day1", "turn_id": "turn1"})
    book.add("lantern", "episode_ref", "turn1",
             {"summary": "I repaired the lantern.", "id": "turn1"},
             ref="dream:turn1", source="dreamed", basis="supposed",
             context={"session": "dream"})
    F.apply_to_crystals(book, {"lantern": dps.concept_index["lantern"]}, dps.crystals, dry_run=False)
    store = RepresentationCrystals(registry)
    record = {
        "id": "REPR:external_user:T>N", "subject": "external_user",
        "path": "T>N", "target": "N", "status": "earned",
        "z": 5.1, "word_evidence": [
            {"word": "lantern", "lift": 2.0, "count": 20},
            {"word": "battery", "lift": -1.5, "count": 12},
        ],
    }
    assert store.upsert(record, delta={"n": 0})
    exchange = SimpleNamespace(_crystals=store, _last_index={"live": 12})
    systems = {"_concept_crystal_registry": registry,
               "dimensional": dps, "representation_exchange": exchange}
    before = [json.dumps(c.to_dict(), sort_keys=True) for c in registry.all_crystals()]
    count = len(dps.crystals)
    view = crystal_context_for_turn(systems, "What do you remember about the lantern?")
    assert len(view["facets"]) == 1 and len(view["representations"]) == 1
    assert view["facets"][0]["occasions"][0]["basis"] == "told"
    assert view["facets"][0]["contexts"] == 2  # the dream remains distinguishable, not promoted
    assert view["representations"][0]["path"] == "T>N"
    assert view["representations"][0]["facet_role"] == "lsa:res:external_user:T>N"
    assert crystal_context_for_turn(systems, "What do you remember about the lantern?") is view
    assert crystal_context_for_turn(systems, "What do you remember about nothing?") == {
        "facets": [], "representations": []}
    after = [json.dumps(c.to_dict(), sort_keys=True) for c in registry.all_crystals()]
    assert len(dps.crystals) == count and before == after


def test_dissolved_or_unrelated_representations_cannot_become_remembered_facts():
    dps, registry = _runtime()
    store = RepresentationCrystals(registry)
    for status, subject, path, word in [
        ("candidate", "external_user", "T>N", "lantern"),
        ("earned", "responder", "A>T", "banana"),
    ]:
        assert store.upsert({
            "id": f"REPR:{subject}:{path}", "subject": subject, "path": path,
            "target": path[-1], "status": status,
            "z": 6.0, "word_evidence": [{"word": word, "lift": 2.0}],
        }, delta={"n": 0})
    assert store.recall_relevant("Tell me about lantern") == []
    assert len(registry.all_crystals()) >= 1
