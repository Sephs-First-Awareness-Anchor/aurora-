# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3 (2026-07-21), PF3.1 (second mechanism): fixing ThoughtContinuity's
axis-letter merge trigger eliminated byte-identical duplicate outputs but
did not materially drop Cluster D residue. Tracing further (word_sources
inspection + direct lexicon.json inspection) found a SEPARATE leak: heavily
reinforced hub words ("planning", usage_count 496+ in the real, persistent
lexicon) were entering composer._context_keywords via ExpressionPerception
Engine._build_expression's OETS relation-neighbor enrichment (aurora_
expression_perception.py, the "Pull words from relations" block), with NO
filtering for relation source. aurora_constraint_emission.build_relevance_
anchor_set already caps co-occurrence-sourced relation strength at the
one-hop floor for exactly this reason ("86% of this graph's relations are
co-occurrence-sourced and 84% of those sit at strength 1.0 -- a saturated
frequency proxy, not a semantic-relevance signal") -- but that dampening
never reached this call site, because words pulled in here get written
straight into context_keywords, which the anchor builder then treats as
DIRECT anchors (relevance 1.0), bypassing the one-hop cap entirely.

The fix excludes co-occurrence-sourced relations from this specific
enrichment pull, reusing the same source_of_knowledge check the anchor
builder already established rather than inventing a new one.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_expression_perception import ExpressionPerceptionEngine  # noqa: E402


class _FakeRelation:
    def __init__(self, source_word, target_word, source_of_knowledge):
        self.source_word = source_word
        self.target_word = target_word
        self.source_of_knowledge = source_of_knowledge


class _FakeNode:
    def __init__(self, relations, definitions=None):
        self.relations = relations
        self.definitions = definitions or []


class _FakeWeb:
    def __init__(self, nodes):
        self._nodes = nodes

    def get_node(self, word):
        return self._nodes.get(word)


class _FakeOets:
    def __init__(self, nodes):
        self.web = _FakeWeb(nodes)


class _FakeLexicon:
    def __init__(self):
        self.entries = {}

    def add_word(self, word, meaning, role, valence=0.0, lineage=""):
        self.entries[word] = SimpleNamespace(
            word=word, meaning=meaning, role=role, valence=valence, lineage=lineage)


class _FakeComposer:
    def __init__(self, context_keywords):
        self._context_keywords = context_keywords
        self.set_context_calls = []

    def set_context(self, keywords):
        self.set_context_calls.append(list(keywords))
        self._context_keywords = list(keywords)

    def compose(self, *a, **kw):
        return "stub response"


def _build_fake_engine(node):
    fake_self = SimpleNamespace()
    fake_self.oets = _FakeOets({"market": node})
    fake_self.composer = _FakeComposer(["market"])
    fake_self.lexicon = _FakeLexicon()
    fake_self._personality_traits = None
    return fake_self


def test_cooccurrence_relations_excluded_from_context_enrichment():
    """A co-occurrence-sourced relation (the saturated-hub shape confirmed
    live: "planning" reaching unrelated turns) must not be pulled into
    context_keywords."""
    node = _FakeNode(relations={
        "market->planning": _FakeRelation("market", "planning", "co-occurrence"),
    })
    fake_self = _build_fake_engine(node)

    ExpressionPerceptionEngine._build_expression(
        fake_self, offspring=None, assembly=None, i_state="i_is", input_text="market")

    final_context = fake_self.composer.set_context_calls[-1]
    assert "planning" not in final_context


def test_non_cooccurrence_relations_still_enrich_context():
    """Deliberate, structural relations (definition_analysis, category_
    sharing, etc.) are real signal and must still flow through -- this
    fix must not blanket-suppress the enrichment mechanism itself."""
    node = _FakeNode(relations={
        "market->economy": _FakeRelation("market", "economy", "category_sharing"),
    })
    fake_self = _build_fake_engine(node)

    ExpressionPerceptionEngine._build_expression(
        fake_self, offspring=None, assembly=None, i_state="i_is", input_text="market")

    final_context = fake_self.composer.set_context_calls[-1]
    assert "economy" in final_context


def test_mixed_relations_keep_only_non_cooccurrence():
    node = _FakeNode(relations={
        "market->planning": _FakeRelation("market", "planning", "co-occurrence"),
        "market->economy": _FakeRelation("market", "economy", "category_sharing"),
    })
    fake_self = _build_fake_engine(node)

    ExpressionPerceptionEngine._build_expression(
        fake_self, offspring=None, assembly=None, i_state="i_is", input_text="market")

    final_context = fake_self.composer.set_context_calls[-1]
    assert "economy" in final_context
    assert "planning" not in final_context
