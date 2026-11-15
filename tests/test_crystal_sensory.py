# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Perception in the one crystal store: a facet is one crystal; its nodes are particulars held by what was observed; cross-modal ties are counted co-occurrence."""
import gzip
import json
import os

from aurora_dimensional_systems import CrystalProcessingSystem
from aurora_internal import crystal_facets as F
from aurora_internal import crystal_runtime as R
from aurora_internal import crystal_sensory as S
from aurora_internal import crystal_weave as W
from aurora_internal.crystal_associations import AssociationStore


class Tracker:
    def record(self, *a, **k):
        pass


def node(nid, facet, domain, uses=5, sessions=2, conf=0.6, name="", stage="primitive"):
    return {"node_id": nid, "domain": domain, "facet": facet, "name": name, "usage_count": uses, "session_count": sessions, "confidence": conf,
            "stage": stage, "lineage_id": "L", "generation": 1}


def write(path, d):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(json.dumps(d).encode("utf-8"))


def state(tmp, tone=(), hue=(), semantic=()):
    base = os.path.join(str(tmp), "sensory_crystal")
    write(f"{base}/audio/tone/state.agb", {"nodes": list(tone)})
    write(f"{base}/visual/hue/state.agb", {"nodes": list(hue)})
    write(f"{base}/semantic/state.agb", {"semantic": {s["node_id"]: s for s in semantic}})
    return str(tmp)


def sem(nid, count=18, conf=0.58):
    return {"node_id": nid, "lane": "tonal_colour", "audio_facet": "tone", "visual_facet": "hue", "co_occurrence_count": count, "confidence": conf}


ACC = lambda n: 1.0 - 0.9 ** max(0, int(n))          # (the weave's own: each exposure weak)


def test_a_node_is_a_particular_of_its_facet_held_by_what_was_observed_not_a_crystal(tmp_path):
    d = state(tmp_path, tone=[node("n1", "tone", "audio", uses=6, sessions=1, conf=0.46)])
    book, store = F.FacetBook(), AssociationStore()
    r = S.place(book, store, d, ACC)
    assert r["nodes"] == 1
    rows = book.facets_for("sensory:audio:tone")["particular"]
    assert rows[0]["key"] == "n1" and 0.0 < rows[0]["degree"] < 1.0 and rows[0]["content"]["observations"] == 6


def test_more_sessions_hold_a_node_more_strongly_than_more_frames_in_one_session(tmp_path):
    one = state(tmp_path / "a", tone=[node("n", "tone", "audio", uses=40, sessions=1, conf=0.5)])
    many = state(tmp_path / "b", tone=[node("n", "tone", "audio", uses=40, sessions=4, conf=0.5)])
    deg = []
    for d in (one, many):
        b = F.FacetBook()
        S.place(b, AssociationStore(), d, ACC)
        deg.append(b.degree("sensory:audio:tone", "particular", "n"))
    assert deg[1] > deg[0]


def test_a_node_nothing_observed_places_nothing_and_a_seed_is_named_by_its_archetype(tmp_path):
    d = state(tmp_path, tone=[node("arch_tone_warm_body", "tone", "audio", uses=0, sessions=0), node("arch_tone_tonal_center", "tone", "audio", uses=3, sessions=1)])
    b = F.FacetBook()
    assert S.place(b, AssociationStore(), d, ACC)["nodes"] == 1
    assert b.facets_for("sensory:audio:tone")["particular"][0]["content"]["name"] == "tonal_center"


def test_what_the_lifecycle_stage_says_does_not_change_what_counts(tmp_path):
    a = state(tmp_path / "a", tone=[node("n", "tone", "audio", stage="primitive")])
    b2 = state(tmp_path / "b", tone=[node("n", "tone", "audio", stage="promoted")])
    out = []
    for d in (a, b2):
        b = F.FacetBook()
        S.place(b, AssociationStore(), d, ACC)
        out.append(b.degree("sensory:audio:tone", "particular", "n"))
    assert out[0] == out[1]


def test_cross_modal_nodes_seen_together_tie_their_facets_by_counted_co_occurrence(tmp_path):
    d = state(tmp_path, semantic=[sem("s1", 18), sem("s2", 4)])
    store = AssociationStore()
    r = S.place(F.FacetBook(), store, d, ACC)
    assert r["cross_modal_ties"] == 2
    conn = store.connections_for("sensory:audio:tone")
    assert conn.get("sensory:visual:hue", 0.0) > 0.0 and store.basis_counts().get("recurrence", 0) >= 1


def test_only_a_facet_with_counted_perception_behind_it_gets_a_crystal(tmp_path):
    d = state(tmp_path, tone=[node("n", "tone", "audio")])
    b = F.FacetBook()
    S.place(b, AssociationStore(), d, ACC)
    assert S.concepts_with_evidence(b) == ["sensory:audio:tone"]


def test_the_pass_makes_one_crystal_per_facet_with_its_nodes_inside_and_its_tie_to_the_paired_facet(tmp_path):
    d = state(tmp_path, tone=[node("n1", "tone", "audio"), node("n2", "tone", "audio", uses=9, sessions=3)], hue=[node("h1", "hue", "visual")], semantic=[sem("s1")])
    dps = CrystalProcessingSystem(tracker=Tracker())
    r = R.run_pass(dps, d, force=True)
    assert r["ok"] and r["sensory_crystals_created"] == 2
    tone, hue = dps.crystals[dps.concept_index["sensory:audio:tone"]], dps.crystals[dps.concept_index["sensory:visual:hue"]]
    assert hue.crystal_id in tone.connections and tone.crystal_id in hue.connections
    part = next(f for f in tone.facets.values() if f.role == "fk:particular")
    assert {e["key"] for e in part.content["entries"]} == {"n1", "n2"}
    assert not [c for c in dps.concept_index if c.startswith("sensory:") and c.count(":") > 2]             # no crystal per node
    assert R.run_pass(dps, d, force=True)["sensory_crystals_created"] == 0 and len(dps.concept_index) == 2


def test_a_node_reaching_promotion_makes_no_crystal_of_its_own_only_its_facets():
    from aurora_internal import aurora_sensory_crystal as SC
    dps = CrystalProcessingSystem(tracker=Tracker())
    sc = SC.AuroraSensoryCrystal.__new__(SC.AuroraSensoryCrystal)
    sc._dps_ref = dps
    n = SC.SensoryNode(node_id="abc123", domain="audio", facet="tone", centroid=[0.0], name="x", confidence=0.9, stage="promoted")
    sc._inject_to_dps("audio", "tone", n)
    assert list(dps.concept_index) == ["sensory:audio:tone"]


def test_it_reads_only_and_imports_nothing_of_the_stack():
    import ast
    src = open(S.__file__).read()
    mods = {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("aurora")}
    assert mods <= {"aurora_internal.crystal_facets", "aurora_internal.crystal_associations"}
    assert not any(w in src for w in ("write_text", "os.replace", "os.remove", '"wb"', "'wb'", "atomic_write"))
