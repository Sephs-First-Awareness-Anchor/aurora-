# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for comprehension_confidence being a write-once field
(2026-07-12): SemanticNode.comprehension_confidence only ever moved via
its 0.1 dataclass default or a one-time manual boost to 0.8 for a handful
of hand-seeded identity words (seed_identity_into_oets). Nothing in the
real study/consolidation pipeline (encounter(), _recalculate_depth(), the
sibling of _update_scaffolding_level()) ever updated it for ordinary
vocabulary.

Confirmed against the real aurora_state/aurora_oets_web.json: 560 of 569
nodes sat at exactly 0.1, including "am" with times_encountered=1614 and
ontological_depth=0.385 -- a word she has used well over a thousand times
still gated a "what do you mean by X" clarifying question
(aurora_constraint_emission.py's comprehension_confidence < 0.5 check)
because nothing ever raised its confidence past the default, even though
scaffolding_level/ontological_depth (driven by the very similar
_update_scaffolding_level(), which DOES get called) climbed normally.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.aurora_ontological_scaffolding import SemanticNode


def test_heavily_encountered_word_crosses_the_clarifying_question_threshold():
    """The exact real-world case: "am", times_encountered=1614,
    ontological_depth=0.385 (both taken directly from the real committed
    aurora_state/aurora_oets_web.json). Must end up >= 0.5 so
    aurora_constraint_emission.py's comprehension_confidence < 0.5 gate no
    longer fires a clarifying question for it."""
    node = SemanticNode(word="am", role="verb")
    node.times_encountered = 1614
    node.ontological_depth = 0.3846

    node._update_comprehension_confidence()

    assert node.comprehension_confidence >= 0.5


def test_freshly_encountered_unfamiliar_word_still_gates_the_question():
    """A word encountered once with no real depth must NOT jump to high
    confidence -- the fix should raise confidence in proportion to real
    evidence of understanding, not blanket-unlock everything."""
    node = SemanticNode(word="xyzzy", role="noun")
    node.times_encountered = 1
    node.ontological_depth = 0.0

    node._update_comprehension_confidence()

    assert node.comprehension_confidence < 0.5


def test_encounter_alone_raises_confidence_without_new_definitions():
    """The exact mechanism that was missing: repeated exposure via
    encounter() (not just definitions/examples/relations via
    _recalculate_depth()) must move comprehension_confidence, since a
    heavily-used function word like "am" may not get fresh definitions
    added on every use."""
    node = SemanticNode(word="am", role="verb")
    node.ontological_depth = 0.3846
    before = node.comprehension_confidence

    for _ in range(1614):
        node.encounter()

    assert node.comprehension_confidence > before
    assert node.times_encountered == 1614


def test_comprehension_confidence_never_decreases():
    """Uses max() against the current value -- a seeded/earned confidence
    must never erode just because a later recalculation's raw formula
    happens to be lower (e.g. the 0.8 hand-seeded identity-word boost from
    seed_identity_into_oets must survive later _recalculate_depth() calls)."""
    node = SemanticNode(word="coherence", role="noun")
    node.comprehension_confidence = 0.8  # simulates the identity seed boost
    node.ontological_depth = 0.1         # low, as a fresh/low-signal recompute would see
    node.times_encountered = 0

    node._update_comprehension_confidence()

    assert node.comprehension_confidence == 0.8


def test_recalculate_depth_also_updates_comprehension_confidence():
    """_recalculate_depth() must call the comprehension_confidence sibling
    the same way it already calls _update_scaffolding_level() -- real
    definitions accumulating is itself evidence of understanding, and
    should be reflected without waiting on encounter() alone."""
    node = SemanticNode(word="resilience", role="noun")
    node.add_definition("the capacity to recover from difficulty", confidence=0.9)
    node.add_definition("elasticity under strain", confidence=0.85)
    node.add_definition("the ability to withstand hardship", confidence=0.8)

    assert node.ontological_depth > 0.1
    assert node.comprehension_confidence > 0.1
