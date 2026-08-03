# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive NC2: relation-strengthen cascade fix (priority starvation).

OntologicalWeb.add_relation()'s "relation already exists, strengthen
it" branch used to return early WITHOUT calling
self.nodes[source].add_relation(relation) / self.nodes[target].
add_relation(relation) -- the only path that reached SemanticNode.
_recalculate_depth(), which is what applies research_priority's
built-in study_decay (0.5 ** times_researched). A word that had
already been researched many times could never fall out of study
rotation, because every re-discovery of an already-known relation
silently skipped the entire recalculation cascade for both endpoint
nodes.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_ontological_scaffolding import (  # noqa: E402
    OntologicalWeb, RelationType,
)


def _fresh_web():
    web = OntologicalWeb()
    web.add_node("grow", "verb")
    web.add_node("garden", "noun")
    return web


# ── Coverage 1: double add_relation() cascades both times ──────────────

def test_add_relation_cascades_on_first_call_and_again_on_second():
    web = _fresh_web()
    calls = {"grow": 0, "garden": 0}
    orig_grow = web.nodes["grow"]._recalculate_depth
    orig_garden = web.nodes["garden"]._recalculate_depth

    def spy_grow():
        calls["grow"] += 1
        orig_grow()

    def spy_garden():
        calls["garden"] += 1
        orig_garden()

    web.nodes["grow"]._recalculate_depth = spy_grow
    web.nodes["garden"]._recalculate_depth = spy_garden

    web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    assert calls["grow"] == 1, "first (brand-new) call must cascade exactly once"
    assert calls["garden"] == 1

    web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    assert calls["grow"] == 2, "second (strengthen) call must cascade again"
    assert calls["garden"] == 2


# ── Coverage 2: research_priority decay actually applies on strengthen ──

def test_strengthen_applies_study_decay_to_research_priority():
    web = _fresh_web()
    web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)

    node = web.nodes["grow"]
    priority_before = node.research_priority

    # Simulate this word having just been researched again (the real
    # research pipeline increments times_researched before re-running
    # relation inference, which is what re-discovers this relation).
    node.times_researched += 1

    web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    priority_after = node.research_priority

    assert priority_after <= priority_before, (
        f"research_priority must decay (or stay equal) once times_researched "
        f"increases and a strengthen-only pass runs -- got {priority_before} -> {priority_after}"
    )
    # With times_researched now >= 1, study_decay <= 0.5 -- the drop must be
    # real, not a no-op float-equality accident.
    assert priority_after < priority_before or node.times_researched == 0


def test_strengthen_without_recascade_would_have_left_priority_frozen():
    """Sanity check on the test itself: confirm research_priority is NOT
    recalculated automatically just by incrementing times_researched --
    the cascade through _recalculate_depth() is what's actually being
    tested above, not some other mechanism."""
    web = _fresh_web()
    web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    node = web.nodes["grow"]
    priority_before = node.research_priority
    node.times_researched += 1
    assert node.research_priority == priority_before, (
        "incrementing times_researched alone must not silently recompute "
        "priority -- only an explicit _recalculate_depth() cascade does"
    )


# ── Coverage 3: regression guard, brand-new-relation branch unchanged ───

def test_brand_new_relation_still_cascades_exactly_once_each_endpoint():
    web = _fresh_web()
    calls = {"grow": 0, "garden": 0}
    orig_grow = web.nodes["grow"]._recalculate_depth
    orig_garden = web.nodes["garden"]._recalculate_depth
    web.nodes["grow"]._recalculate_depth = lambda: (calls.__setitem__("grow", calls["grow"] + 1), orig_grow())
    web.nodes["garden"]._recalculate_depth = lambda: (calls.__setitem__("garden", calls["garden"] + 1), orig_garden())

    rel = web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    assert rel is not None
    assert calls == {"grow": 1, "garden": 1}, "no double-cascade, no missed cascade on the new-relation path"


def test_brand_new_relation_result_unaffected_by_nc2_change():
    """The new-relation branch's own return value/relation bookkeeping
    is untouched by NC2 -- same relation object, same registries."""
    web = _fresh_web()
    rel = web.add_relation("grow", "garden", RelationType.ENABLES, strength=0.3, confidence=0.3)
    assert rel.source_word == "grow"
    assert rel.target_word == "garden"
    assert rel.relation_type == RelationType.ENABLES
    assert rel.relation_id in web.relations
    assert rel.relation_id in web.nodes["grow"].relations
    assert rel.relation_id in web.nodes["garden"].relations
