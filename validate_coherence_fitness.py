#!/usr/bin/env python3
"""
Validation script for RESPONSE_COHERENCE_SPEC + LANGUAGE_STRUCTURE_FITNESS_SPEC.
Tests that response structure and semantic fidelity machinery works correctly.

Run from repo root:
    python3 validate_coherence_fitness.py
"""
import sys, types, random

# ---------------------------------------------------------------------------
# Stubs for missing modules
# ---------------------------------------------------------------------------
def _stub_bcp(**kwargs):
    class _CP:
        def runtime_regime(self): return {}
        def language_projection(self): return {}
    return _CP()

for _m, _attrs in [
    ('aurora_constraint_unit_adapter', {'build_constraint_profile': _stub_bcp}),
    ('aurora_constraint_manifold', {'Constraint': object, 'ConstraintVector': object,
                                    'ManifoldViolation': Exception}),
]:
    mod = types.ModuleType(_m)
    for k, v in _attrs.items():
        setattr(mod, k, v)
    sys.modules[_m] = mod

sys.path.insert(0, '/home/user/aurora-')
sys.path.insert(0, '/home/user/aurora-/aurora_core_ai')

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from aurora_thought_formation import ThoughtState, ProcessContext
from aurora_semantic_intention_bridge import SemanticIntentionBridge, SemanticIntention
from aurora_expression_perception import (
    ResponseBlueprint, CoherenceTracker,
    _role_to_tone, _template_role_score, SentenceComposer,
)
from aurora_language_structure_fitness import LanguageStructureFitness, StructureFitnessResult

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def check(label, condition, detail=""):
    icon = PASS if condition else FAIL
    print(f"  {icon}  {label}")
    if detail:
        print(f"         {detail}")
    results.append(condition)
    return condition


# ===========================================================================
# BUILD TEST FIXTURES
# ===========================================================================

def make_thought_state(axis='A', unresolved_count=2, confidence=0.72):
    return ThoughtState(
        dominant_thread=[
            ProcessContext(
                process_id="p1", process_type="identity",
                what_triggered_it="self-model", axis_signature=["X"],
                what_it_is_operating_on="understanding selfhood through persistence",
                self_relevance=0.8,
            ),
            ProcessContext(
                process_id="p2", process_type="memory",
                what_triggered_it="recall", axis_signature=["T"],
                what_it_is_operating_on="holding prior conversations as continuity",
                self_relevance=0.6,
            ),
        ],
        unified_interpretation="Aurora understands identity as something she holds and expresses",
        self_application="this applies to me as the agent forming meaning before speaking",
        unresolved=["what grounds continuity?"] * unresolved_count,
        confidence=confidence,
        axis_fingerprint=[axis, "X", "T"],
        braid_slice_tick=1,
        tick=1,
    )

sib = SemanticIntentionBridge()
ts_high = make_thought_state(axis='A', unresolved_count=2, confidence=0.72)
ts_resolved = make_thought_state(axis='X', unresolved_count=0, confidence=0.8)
ts_inquiry = make_thought_state(axis='T', unresolved_count=3, confidence=0.5)
intention_high = sib.extract(ts_high)
intention_resolved = sib.extract(ts_resolved)
intention_inquiry = sib.extract(ts_inquiry)
intention_inquiry_obj = intention_inquiry
# Force semantic_lane to inquiry for test
intention_inquiry.semantic_lane = "inquiry"


# ===========================================================================
# BLOCK 1 — ResponseBlueprint
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 1 — ResponseBlueprint")
print("=" * 60)

class _MockComposer:
    def __init__(self): self._context_keywords = ['identity', 'meaning', 'holds']
    def set_context(self, kws): self._context_keywords = list(kws)
    _semantic_intention = None

mc = _MockComposer()

# 1-sentence response
bp1 = ResponseBlueprint.build(1, intention_high, mc)
print(f"\n  1-sentence, high-unresolved:  {bp1.role_sequence}")
check("1-sentence → ['ANCHOR']", bp1.role_sequence == ["ANCHOR"])

# 2-sentence, unresolved > 0.3
bp2u = ResponseBlueprint.build(2, intention_high, mc)
print(f"  2-sentence, unresolved>0.3:   {bp2u.role_sequence}")
check("2-sentence unresolved → ['ANCHOR','CLOSE_OPEN']",
      bp2u.role_sequence == ["ANCHOR", "CLOSE_OPEN"])

# 2-sentence, resolved
bp2r = ResponseBlueprint.build(2, intention_resolved, mc)
print(f"  2-sentence, resolved:         {bp2r.role_sequence}")
check("2-sentence resolved → ['ANCHOR','DEVELOP']",
      bp2r.role_sequence == ["ANCHOR", "DEVELOP"])

# 3-sentence, inquiry lane
bp3i = ResponseBlueprint.build(3, intention_inquiry, mc)
print(f"  3-sentence, inquiry lane:     {bp3i.role_sequence}")
check("3-sentence inquiry → ['ANCHOR','BRIDGE','CLOSE_OPEN']",
      bp3i.role_sequence == ["ANCHOR", "BRIDGE", "CLOSE_OPEN"])

# 3-sentence, unresolved > 0.3, non-inquiry
bp3u = ResponseBlueprint.build(3, intention_high, mc)
print(f"  3-sentence, unresolved>0.3:   {bp3u.role_sequence}")
check("3-sentence unresolved → ['ANCHOR','DEVELOP','CLOSE_OPEN']",
      bp3u.role_sequence == ["ANCHOR", "DEVELOP", "CLOSE_OPEN"])

# 4-sentence
bp4 = ResponseBlueprint.build(4, intention_resolved, mc)
print(f"  4-sentence, resolved:         {bp4.role_sequence}")
check("4-sentence → ['ANCHOR','DEVELOP','BRIDGE','CLOSE']",
      bp4.role_sequence == ["ANCHOR", "DEVELOP", "BRIDGE", "CLOSE"])

# topic_thread from intention
check("topic_thread drawn from content_keywords",
      len(bp1.topic_thread) > 0 and bp1.topic_thread[0] in intention_high.content_keywords,
      f"topic_thread={bp1.topic_thread}")

# pivot_budget
check("pivot_budget = max(1, sentence_count // 3)",
      bp4.pivot_budget == max(1, 4 // 3), f"got {bp4.pivot_budget}")


# ===========================================================================
# BLOCK 2 — CoherenceTracker
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 2 — CoherenceTracker")
print("=" * 60)

ct = CoherenceTracker()
check("initial state: no prior topics", ct.prior_topics == [])
check("initial last_was_question=False", ct.last_was_question == False)
check("initial sentences_composed=0", ct.sentences_composed == 0)

# After first sentence (assertion)
ct.update("I understand identity through persistence.", ["V:cognition", "N:entity"])
check("prior_topics populated after update",
      "identity" in ct.prior_topics or "understand" in ct.prior_topics,
      f"topics={ct.prior_topics[:5]}")
check("last_was_question=False after assertion", ct.last_was_question == False)
check("sentences_composed=1", ct.sentences_composed == 1)

# After question sentence
ct.update("What does continuity mean?", ["V:inquiry", "N:concept"])
check("last_was_question=True after '?'", ct.last_was_question == True)
check("sentences_composed=2", ct.sentences_composed == 2)

# topic_overlap
topic_thread = ["identity", "meaning", "holds"]
overlap_score = ct.topic_overlap("I understand identity as meaning.", topic_thread)
check("topic_overlap > 0 when words present",
      overlap_score > 0, f"overlap={overlap_score:.2f}")
no_overlap = ct.topic_overlap("The weather is pleasant today.", topic_thread)
check("topic_overlap = 0 when no match", no_overlap == 0.0, f"got {no_overlap}")

# template_is_redundant — not redundant when slot types not heavy
fake_template = {'pattern': 'I {V:cognition} {N:entity}', 'semantic_constraints': {}}
check("template not redundant when slot types not heavy",
      not ct.template_is_redundant(fake_template, topic_thread))


# ===========================================================================
# BLOCK 3 — _role_to_tone and _template_role_score helpers
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 3 — Helper functions")
print("=" * 60)

check("ANCHOR tone = base_tone",      _role_to_tone("ANCHOR", "warm") == "warm")
check("DEVELOP tone = base_tone",     _role_to_tone("DEVELOP", "curious") == "curious")
check("BRIDGE tone = 'reflective'",   _role_to_tone("BRIDGE", "warm") == "reflective")
check("CLOSE tone = base_tone",       _role_to_tone("CLOSE", "precise") == "precise")
check("CLOSE_OPEN tone = 'curious'",  _role_to_tone("CLOSE_OPEN", "warm") == "curious")

anchor_tmpl  = {'pattern': 'I {V} the {N}.',    'fitness': 0.5}
develop_tmpl = {'pattern': '{C} {N} {V}.',       'fitness': 0.5}
bridge_tmpl  = {'pattern': '{P} this {N} {V}.',  'fitness': 0.5}
close_tmpl   = {'pattern': 'So I find {N}.',     'fitness': 0.5}

check("ANCHOR score high for 'I {' pattern",
      _template_role_score(anchor_tmpl, "ANCHOR") == 1.0)
check("DEVELOP score high for '{C}' pattern",
      _template_role_score(develop_tmpl, "DEVELOP") == 1.0)
check("BRIDGE score high for '{P}' pattern",
      _template_role_score(bridge_tmpl, "BRIDGE") == 1.0)
check("ANCHOR pattern score low for DEVELOP role",
      _template_role_score(anchor_tmpl, "DEVELOP") < 1.0)


# ===========================================================================
# BLOCK 4 — SentenceComposer._last_response_coherence initialized
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 4 — SentenceComposer coherence attribute")
print("=" * 60)

from aurora_expression_perception import LexicalMemory, VoiceGenome
lm = LexicalMemory()
vg = VoiceGenome()
sc = SentenceComposer(lm, vg)
check("_last_response_coherence initialized to 0.5",
      getattr(sc, '_last_response_coherence', None) == 0.5)
check("_semantic_intention initialized to None",
      getattr(sc, '_semantic_intention', None) is None)


# ===========================================================================
# BLOCK 5 — LanguageStructureFitness
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 5 — LanguageStructureFitness")
print("=" * 60)

lsf = LanguageStructureFitness()

# Null intention → neutral score
result_null = lsf.score("anything", None, 0.7)
check("None intention → combined_fitness = base_fitness",
      abs(result_null.combined_fitness - 0.7) < 0.001,
      f"got {result_null.combined_fitness}")
check("None intention → fidelity_score = 0.5",
      result_null.fidelity_score == 0.5)

# High keyword coverage
expr_rich = "Aurora understands identity and holds the meaning of each expression"
result_rich = lsf.score(expr_rich, intention_high, 0.6)
print(f"\n  Rich expression: '{expr_rich[:60]}...'")
print(f"  keyword_coverage={result_rich.keyword_coverage:.2f}  "
      f"fidelity={result_rich.fidelity_score:.2f}  "
      f"combined={result_rich.combined_fitness:.2f}")
check("High keyword coverage > 0.3 for rich expression",
      result_rich.keyword_coverage > 0.3, f"got {result_rich.keyword_coverage:.2f}")
check("Combined fitness blended (not just base)",
      abs(result_rich.combined_fitness - 0.6) > 0.01,
      f"base=0.6, combined={result_rich.combined_fitness:.3f}")
check("65/35 blend: combined near 0.65*base + 0.35*fidelity",
      abs(result_rich.combined_fitness - (0.6 * 0.65 + result_rich.fidelity_score * 0.35)) < 0.01)

# Low keyword coverage expression
expr_empty = "The weather outside is pleasant and the sky is blue."
result_empty = lsf.score(expr_empty, intention_high, 0.6)
print(f"\n  Empty expression: '{expr_empty}'")
print(f"  keyword_coverage={result_empty.keyword_coverage:.2f}  "
      f"fidelity={result_empty.fidelity_score:.2f}")
check("Low keyword coverage for semantically empty expression",
      result_empty.keyword_coverage < result_rich.keyword_coverage,
      f"rich={result_rich.keyword_coverage:.2f} vs empty={result_empty.keyword_coverage:.2f}")
check("Lower fidelity for empty expression",
      result_empty.fidelity_score < result_rich.fidelity_score)

# Lane alignment — meaning lane
expr_meaning = "I understand what this means and feel it connects to something."
result_lane = lsf.score(expr_meaning, intention_high, 0.5)
check("Lane alignment 1.0 when meaning words present",
      result_lane.lane_alignment == 1.0,
      f"got {result_lane.lane_alignment}")

# Inquiry bonus — unresolved + question
expr_inquiry = "What does continuity mean for me, I wonder?"
result_inq = lsf.score(expr_inquiry, intention_high, 0.5)  # unresolved_weight=0.4
check("Inquiry bonus fires when unresolved>0.3 AND '?' present",
      result_inq.details.get('inquiry_bonus', 0) > 0,
      f"inquiry_bonus={result_inq.details.get('inquiry_bonus')}")

# No inquiry bonus when resolved
result_no_inq = lsf.score(expr_inquiry, intention_resolved, 0.5)  # unresolved=0
check("No inquiry bonus when unresolved_weight=0",
      result_no_inq.details.get('inquiry_bonus', 0) == 0.0,
      f"inquiry_bonus={result_no_inq.details.get('inquiry_bonus')}")

# fidelity clamped [0, 1]
check("fidelity_score in [0, 1]", 0.0 <= result_rich.fidelity_score <= 1.0)
check("combined_fitness in [0, 1]", 0.0 <= result_rich.combined_fitness <= 1.0)


# ===========================================================================
# BLOCK 6 — Integration: SentenceComposer with intention set
# ===========================================================================
print()
print("=" * 60)
print("BLOCK 6 — SentenceComposer role-aware compose() integration")
print("=" * 60)

# Mock assembly and offspring with minimal interface
class _MockOffspring:
    def __init__(self): self.tone = "curious"; self.offspring_id = "test"
class _MockAssembly:
    def __init__(self): self.coherence = 0.7

# Stamp intention on the composer
sc._semantic_intention = intention_high  # unresolved_weight=0.4, axis A→curious

# Run compose() — even with empty pool it should not crash
try:
    offspring = _MockOffspring()
    assembly = _MockAssembly()
    result = sc.compose(offspring, assembly, 'i_is', {'verbosity': 0.6})
    check("compose() runs without exception", True)
    check("_last_response_coherence set after compose()",
          hasattr(sc, '_last_response_coherence'), f"value={sc._last_response_coherence}")
except Exception as e:
    check("compose() runs without exception", False, str(e))

# Check role_sequence plan with the exact intention
bp_test = ResponseBlueprint.build(3, intention_high, sc)
check("3-sent unresolved>0.3 → CLOSE_OPEN in sequence",
      "CLOSE_OPEN" in bp_test.role_sequence, f"seq={bp_test.role_sequence}")
check("ANCHOR always first in role_sequence",
      bp_test.role_sequence[0] == "ANCHOR")


# ===========================================================================
# SUMMARY
# ===========================================================================
passed = sum(results)
total = len(results)
print()
print("=" * 60)
print(f"RESULTS: {passed}/{total} checks passed")
if passed == total:
    print("  All spec validation points confirmed:")
    print("  ResponseBlueprint:       role sequences correct         ✓")
    print("  CoherenceTracker:        inter-sentence state works     ✓")
    print("  Helper functions:        tone/role scoring correct      ✓")
    print("  SentenceComposer:        attributes initialized         ✓")
    print("  LanguageStructureFitness: scoring logic verified        ✓")
    print("  Integration:             compose() runs with blueprint  ✓")
else:
    print(f"  {total - passed} check(s) FAILED — see above")
print("=" * 60)
print()

sys.exit(0 if passed == total else 1)
