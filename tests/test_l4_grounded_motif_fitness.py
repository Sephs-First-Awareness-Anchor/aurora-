# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.3 L4: ground motif promotion fitness in grammaticality.

The diagnosis's own finding: motif promotion fitness had no
grammaticality term, so the subjectless skeleton (composability 0.8136)
outscored a valid agent-action-object one (0.4467) purely because it got
used and randomly scored >=0.5 more often. feedback() now scores each
motif against its OWN composed sentence with the Track-A _parseable
predicate as the DOMINANT term (weight 0.75) and the old fitness signal
demoted to secondary.
"""
import json
import os
import tempfile

from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome
from aurora_grammar_engine import MotifLineage, StructuralMotif, TokenRole, is_valid_clause_shape


def _make_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


class _FakeMotif:
    def __init__(self, pattern_id, role_sequence):
        self.pattern_id = pattern_id
        self.role_sequence = role_sequence


def test_grammatical_sentence_can_succeed_even_with_low_fitness():
    """Dominance check: a perfectly grammatical sentence scores
    0.75*1 + 0.25*fitness -- >=0.5 even at fitness=0."""
    c = _make_composer()
    calls = []

    class _FakeLineage:
        def record_success(self, role_sequence, ctx, token_count, orientation):
            calls.append(("success", role_sequence))

        def record_fail(self, role_sequence):
            calls.append(("fail", role_sequence))

    class _FakeEngine:
        _lineage = _FakeLineage()

    c.grammar_engine = _FakeEngine()
    motif = _FakeMotif("agent_action", (TokenRole.AGENT, TokenRole.ACTION))
    # "I understand the world." has a strong function word ("the") and
    # clears _parseable's per-sentence bar.
    c._last_motif_sentences = [(motif, "I understand the world.")]
    c._last_words_used = ["I", "understand", "the", "world"]

    c.feedback(0.0)  # fitness alone would have failed pre-L4

    assert ("success", motif.role_sequence) in calls


def test_ungrammatical_sentence_can_fail_even_with_high_fitness():
    """Dominance check, the other direction: a sentence that fails
    _parseable scores 0.75*0 + 0.25*fitness -- capped at 0.25, always
    below 0.5 no matter how high fitness is."""
    c = _make_composer()
    calls = []

    class _FakeLineage:
        def record_success(self, role_sequence, ctx, token_count, orientation):
            calls.append(("success", role_sequence))

        def record_fail(self, role_sequence):
            calls.append(("fail", role_sequence))

    class _FakeEngine:
        _lineage = _FakeLineage()

    c.grammar_engine = _FakeEngine()
    motif = _FakeMotif("bad_shape", (TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT))
    # R1.9.4: _parseable is now a clause-structure check, not just
    # strong-word presence -- "Photosynthesis expressed weight." alone is
    # actually valid SVO and would now pass. Use the diagnosis's full
    # verbatim salad sentence instead: two verbs (expressed, need) with no
    # coordinating structure between them, which the refined predicate
    # still correctly rejects.
    c._last_motif_sentences = [(motif, "Photosynthesis expressed weight terms need defensive.")]
    c._last_words_used = ["photosynthesis", "expressed", "weight", "terms", "need", "defensive"]

    c.feedback(1.0)  # fitness alone would have succeeded pre-L4

    assert ("fail", motif.role_sequence) in calls


def test_motif_grounding_is_logged():
    c = _make_composer()

    class _FakeLineage:
        def record_success(self, *a, **kw):
            pass

        def record_fail(self, *a, **kw):
            pass

    class _FakeEngine:
        _lineage = _FakeLineage()

    c.grammar_engine = _FakeEngine()
    motif = _FakeMotif("__test_logged_motif__", (TokenRole.AGENT, TokenRole.ACTION))
    c._last_motif_sentences = [(motif, "I understand the world.")]
    c._last_words_used = ["I", "understand", "the", "world"]

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "aurora_state", "motif_grounding_log.jsonl")
    log_path = os.path.normpath(log_path)
    before = 0
    if os.path.exists(log_path):
        with open(log_path) as f:
            before = sum(1 for _ in f)

    c.feedback(0.3)

    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) > before
    entry = json.loads(lines[-1])
    assert entry["skeleton_id"] == "__test_logged_motif__"
    assert entry["grammatical"] is True
    assert abs(entry["fitness"] - 0.3) < 1e-9


def test_goodhart_divergence_alert_fires_on_persistent_disagreement():
    c = _make_composer()

    class _FakeLineage:
        def record_success(self, *a, **kw):
            pass

        def record_fail(self, *a, **kw):
            pass

    class _FakeEngine:
        _lineage = _FakeLineage()

    c.grammar_engine = _FakeEngine()
    # Unique per test run -- the log file is real, cross-run-persistent
    # state by design, so a fixed id could collide with a stale entry
    # from an earlier run of this same test.
    skeleton_id = f"__test_divergent_motif_{id(c)}__"
    motif = _FakeMotif(skeleton_id, (TokenRole.AGENT, TokenRole.ACTION))

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "aurora_state", "motif_grounding_log.jsonl")
    log_path = os.path.normpath(log_path)

    # Alternate: grammatical sentence but LOW fitness every time --
    # persistent disagreement between the predicate and the old signal.
    for i in range(c._GOODHART_MIN_SAMPLES + 2):
        c._last_motif_sentences = [(motif, "I understand the world.")]
        c._last_words_used = ["I", "understand", "the", "world"]
        c.feedback(0.0)

    with open(log_path) as f:
        lines = [json.loads(l) for l in f]
    alerts = [l for l in lines if l.get("alert") == "goodhart_divergence"
              and l.get("skeleton_id") == skeleton_id]
    assert len(alerts) == 1  # fires once, not once per sample past the threshold


def test_recompute_promotion_from_validity_demotes_invalid_skeletons_only():
    tmp = tempfile.mkdtemp(prefix="aurora_l4_recompute_test_")
    lineage = MotifLineage(os.path.join(tmp, "grammar_motifs.json"))

    bad = lineage.get_or_create((
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT,
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR,
    ))
    bad.success_count, bad.fail_count = 3264, 748
    bad.contexts_seen = {f"c{i}" for i in range(15)}
    bad.promoted = True

    good = lineage.get_or_create((TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    good.success_count, good.fail_count = 2203, 2729
    good.contexts_seen = {f"c{i}" for i in range(15)}
    good.promoted = True

    result = lineage.recompute_promotion_from_validity()

    assert bad.pattern_id in [d["pattern_id"] for d in result["demoted"]]
    assert good.pattern_id not in [d["pattern_id"] for d in result["demoted"]]
    assert bad.promoted is False
    assert good.promoted is True
    # History/counters untouched -- only the derived flag changed.
    assert bad.success_count == 3264
    assert bad.fail_count == 748


def test_recompute_promotion_is_idempotent():
    tmp = tempfile.mkdtemp(prefix="aurora_l4_recompute_idempotent_")
    lineage = MotifLineage(os.path.join(tmp, "grammar_motifs.json"))
    bad = lineage.get_or_create((TokenRole.CONTEXT,))
    bad.promoted = True
    bad.success_count, bad.fail_count = 10, 0
    bad.contexts_seen = {"a", "b", "c"}

    first = lineage.recompute_promotion_from_validity()
    second = lineage.recompute_promotion_from_validity()

    assert first["demoted_count"] == 1
    assert second["demoted_count"] == 0  # already demoted, nothing left to do
    assert bad.promoted is False


def test_mini_gate_subjectless_skeleton_demotes_below_agent_action_object():
    """The mini-gate's literal assertion: under re-scoring, the 0.81
    subjectless skeleton loses its promoted status while the valid
    agent-action-object structure (composability 0.4467, lower raw score)
    keeps it -- eligibility, not the raw composability number, is what
    "demotes below" means once L1's gate is the deciding factor."""
    tmp = tempfile.mkdtemp(prefix="aurora_l4_minigate_")
    lineage = MotifLineage(os.path.join(tmp, "grammar_motifs.json"))

    bad = lineage.get_or_create((
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT,
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR,
    ))
    bad.success_count, bad.fail_count = 3264, 748
    bad.contexts_seen = {f"c{i}" for i in range(15)}
    bad.promoted = True
    bad_score_before = bad.composability_score()

    good = lineage.get_or_create((TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    good.success_count, good.fail_count = 2203, 2729
    good.contexts_seen = {f"c{i}" for i in range(15)}
    good.promoted = True
    good_score = good.composability_score()

    assert bad_score_before > good_score  # the diagnosis's own finding, reproduced

    lineage.recompute_promotion_from_validity()

    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    for _ in range(15):
        chosen = lineage.best_for_pressure(orientation, 1.0)
        assert chosen is not None
        assert chosen.pattern_id == good.pattern_id  # bad is now unreachable, period
