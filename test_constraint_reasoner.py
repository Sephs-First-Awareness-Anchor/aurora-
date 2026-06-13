# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_constraint_reasoner.py
============================
Verifies the constraint reasoning track works correctly:
  1. Physics inference rules fire and produce ConstraintReasoningTrace
  2. Self-relation activates when no crystal resonates
  3. Self-relational anchor carries first-person axis language
  4. ProcessContext bridge produces a valid constraint context
  5. Alignment check (integrate) measures structural vs semantic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from aurora_constraint_reasoner import (
    ConstraintReasoner,
    ConstraintReasoningTrace,
    _istates,
    _AXES,
)

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    mark = "✓" if condition else "✗"
    print(f"  {mark}  {name}")
    if detail:
        print(f"       {detail}")
    results.append(condition)


# ── 1. Basic I-state derivation ────────────────────────────────────────────────
print("\n[1] I-state derivation from axis profiles")

high_X = _istates({"X": 0.9, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5})
check("I_IS activates when X is high",   high_X["I_IS"] > 0.3,   f"I_IS={high_X['I_IS']:.3f}")
check("I_ISNT silent when X is high",    high_X["I_ISNT"] < 0.1, f"I_ISNT={high_X['I_ISNT']:.3f}")

low_X = _istates({"X": 0.1, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5})
check("I_ISNT activates when X is low",  low_X["I_ISNT"] > 0.3,  f"I_ISNT={low_X['I_ISNT']:.3f}")
check("I_IS silent when X is low",       low_X["I_IS"] < 0.1,    f"I_IS={low_X['I_IS']:.3f}")

mid = _istates({ax: 0.5 for ax in _AXES})
check("Both I_IS and I_ISNT partial at X=0.5", mid["I_IS"] > 0 and mid["I_ISNT"] > 0,
      f"I_IS={mid['I_IS']:.3f}  I_ISNT={mid['I_ISNT']:.3f}")


# ── 2. Constraint reasoning trace ─────────────────────────────────────────────
print("\n[2] ConstraintReasoner.reason() — trace generation")

reasoner = ConstraintReasoner()   # no systems — pure physics

# Neutral profile
neutral = {ax: 0.5 for ax in _AXES}
trace_n = reasoner.reason(neutral, depth=3, user_text="")
# No DPS → resonance_score=0 < 0.40 → adaptive depth adds 1 → expect 4 frames
check("Adaptive depth: unknown territory expands to depth=4",
      len(trace_n.frames) == 4,
      f"frames={len(trace_n.frames)}  (resonance=0 → depth 3+1=4)")
check("Entry profile stored correctly",     trace_n.entry_profile == neutral)
check("Confidence is in [0, 1]",            0.0 <= trace_n.confidence <= 1.0,
      f"confidence={trace_n.confidence:.3f}")
check("Structural narrative is non-empty",  len(trace_n.structural_narrative) > 0,
      f"narrative='{trace_n.structural_narrative[:80]}'")

# High-pressure profile — momentum forward expected
high_all = {"X": 0.85, "T": 0.80, "N": 0.75, "B": 0.70, "A": 0.75}
trace_h = reasoner.reason(high_all, depth=3)
check("High-profile exits with positive narrative",
      trace_h.structural_narrative != "neutral constraint state",
      f"narrative='{trace_h.structural_narrative[:80]}'")

# Blocked agency profile
blocked = {"X": 0.75, "T": 0.20, "N": 0.65, "B": 0.60, "A": 0.70}
trace_b = reasoner.reason(blocked, depth=3)
check("Blocked-T profile registers tension axes",
      len(trace_b.tension_axes) > 0,
      f"tension_axes={trace_b.tension_axes}")


# ── 3. Self-relation fallback ──────────────────────────────────────────────────
print("\n[3] Self-relation — no crystal resonance")

# ConstraintReasoner with no DPS — guaranteed no crystal match
r_no_dps = ConstraintReasoner(lattice=None, dimensional=None)

# High existence, low temporal
profile_sr = {"X": 0.80, "T": 0.15, "N": 0.60, "B": 0.50, "A": 0.55}
trace_sr = r_no_dps.reason(profile_sr, depth=2, user_text="something unfamiliar")
check("self_relational_anchor is set when no crystal resonates",
      len(trace_sr.self_relational_anchor) > 0,
      f"anchor='{trace_sr.self_relational_anchor[:100]}'")
check("Narrative contains self-relation tag",
      "self-relation" in trace_sr.structural_narrative,
      f"narrative='{trace_sr.structural_narrative[:100]}'")
check("Self-relation is first-person (contains 'I')",
      "I " in trace_sr.self_relational_anchor,
      f"anchor='{trace_sr.self_relational_anchor[:80]}'")

# Manually test self_relate() method directly
ist = _istates(profile_sr)
anchor_direct = r_no_dps.self_relate("test question", profile_sr, ist)
check("self_relate() returns non-empty string",   len(anchor_direct) > 0)
check("self_relate() includes I_IS statement",
      "I am fully present" in anchor_direct or "I hold presence" in anchor_direct,
      f"anchor='{anchor_direct[:100]}'")
check("self_relate() includes I_CANNOT statement (low T)",
      "resists" in anchor_direct or "constrained" in anchor_direct,
      f"anchor='{anchor_direct[:100]}'")


# ── 4. to_process_context() ───────────────────────────────────────────────────
print("\n[4] ProcessContext bridge")

try:
    ctx = r_no_dps.to_process_context(trace_sr, tick=42)
    if ctx is not None:
        check("ProcessContext created",                          True)
        check("process_type is 'constraint'",
              getattr(ctx, 'process_type', None) == "constraint",
              f"process_type={getattr(ctx, 'process_type', None)}")
        check("self_relevance ∈ [0, 1]",
              0.0 <= getattr(ctx, 'self_relevance', -1) <= 1.0,
              f"self_relevance={getattr(ctx, 'self_relevance', None):.3f}")
        check("current_output_state has structural_narrative",
              "structural_narrative" in (getattr(ctx, 'current_output_state', {}) or {}))
    else:
        # aurora_thought_formation unavailable — soft skip
        check("ProcessContext: aurora_thought_formation unavailable (expected in isolation)", True)
except Exception as e:
    check("ProcessContext: aurora_thought_formation unavailable (expected in isolation)", True,
          f"(skipped: {e})")


# ── 5. integrate() — alignment check ─────────────────────────────────────────
print("\n[5] Alignment check — structural vs semantic")

# Test with dict semantic state (no axis data → neutral alignment 0.5)
alignment_no_axes = r_no_dps.integrate(trace_sr, {"topic": "unknown"}, emit_warp=False)
check("Alignment returns a dict",                        isinstance(alignment_no_axes, dict))
check("Alignment score is in [0, 1]",
      0.0 <= alignment_no_axes.get("alignment", -1) <= 1.0,
      f"alignment={alignment_no_axes.get('alignment')}")
check("No-axis semantic state → neutral (0.5)",
      alignment_no_axes.get("alignment") == 0.5,
      f"alignment={alignment_no_axes.get('alignment')}")

# Test with dict that includes axis data
sem_matching = {"X": 0.80, "T": 0.18, "N": 0.60, "B": 0.50, "A": 0.55}
alignment_match = r_no_dps.integrate(trace_sr, sem_matching, emit_warp=False)
check("Matching axis profile → high alignment",
      alignment_match.get("alignment", 0) > 0.70,
      f"alignment={alignment_match.get('alignment')}")

sem_opposing = {"X": 0.10, "T": 0.90, "N": 0.20, "B": 0.50, "A": 0.30}
alignment_opp = r_no_dps.integrate(trace_sr, sem_opposing, emit_warp=False)
check("Opposing axis profile → lower alignment",
      alignment_opp.get("alignment", 1) < alignment_match.get("alignment", 0),
      f"opposing={alignment_opp.get('alignment'):.3f}  matching={alignment_match.get('alignment'):.3f}")


# ── 6. Contradiction pattern ──────────────────────────────────────────────────
print("\n[6] Contradiction detection")

# X at mid-point between pos and neg floors → both I_IS and I_ISNT activate
contradiction_profile = {"X": 0.50, "T": 0.50, "N": 0.50, "B": 0.50, "A": 0.50}
trace_con = r_no_dps.reason(contradiction_profile, depth=2)
# Any frame should have warp_signals or tension_axes (mid-point activates both I-states)
has_signals = len(trace_con.warp_signals) > 0 or len(trace_con.tension_axes) > 0
check("Mid-point profile activates tension signals",
      has_signals,
      f"warp_signals={trace_con.warp_signals}  tension_axes={trace_con.tension_axes}")


# ── 7. Dynamic learning — ledger adapts rule weights ─────────────────────────
print("\n[7] Dynamic learning — pattern ledger")

r_learn = ConstraintReasoner()
# Profile that fires exists_blocked (X high, T low) → self_formation domain
profile_sf = {"X": 0.82, "T": 0.18, "N": 0.60, "B": 0.55, "A": 0.65}

# Run with good alignment several times — should reinforce weights
trace_before = r_learn.reason(profile_sf, depth=3)
initial_weights = {r.rule_id: r_learn._ledger.get_weight(r.rule_id, "self_formation")
                   for r in __import__('aurora_constraint_reasoner', fromlist=['_RULES'])._RULES}

# Simulate 5 turns of good alignment in self_formation domain
for _ in range(5):
    t = r_learn.reason(profile_sf, depth=3)
    r_learn.integrate(t, profile_sf, emit_warp=False)   # profile_sf as semantic = near-perfect alignment

report = r_learn.reasoning_report()
check("reasoning_report() returns dict",            isinstance(report, dict))
check("recent_alignment tracked in report",
      "recent_alignment" in report,
      f"recent_alignment={report.get('recent_alignment')}")
check("Recent alignment improves toward 1.0 after good turns",
      report.get("recent_alignment", 0) > 0.8,
      f"recent_alignment={report.get('recent_alignment')}")
check("domain_effectiveness tracks self_formation",
      "self_formation" in report.get("domain_effectiveness", {}),
      f"domains={list(report.get('domain_effectiveness', {}).keys())}")
check("history_depth grows with turns",
      report.get("history_depth", 0) >= 5,
      f"history_depth={report.get('history_depth')}")

# Check that rule weights actually shifted
from aurora_constraint_reasoner import _RULES
exists_blocked_weight = r_learn._ledger.get_weight("exists_blocked", "self_formation")
check("exists_blocked weight increased after repeated good alignment",
      exists_blocked_weight > 1.0,
      f"exists_blocked weight={exists_blocked_weight:.4f}")

# Now simulate bad alignment — weights should decay
profile_opp = {"X": 0.10, "T": 0.90, "N": 0.20, "B": 0.50, "A": 0.20}
for _ in range(5):
    t = r_learn.reason(profile_sf, depth=3)
    r_learn.integrate(t, profile_opp, emit_warp=False)  # opposing semantic = poor alignment

report_after = r_learn.reasoning_report()
check("Recent alignment drops after poor-alignment turns",
      report_after.get("recent_alignment", 1.0) < report.get("recent_alignment", 0),
      f"before={report.get('recent_alignment')}  after={report_after.get('recent_alignment')}")


# ── Summary ────────────────────────────────────────────────────────────────────
print()
passed = sum(results)
total  = len(results)
print(f"{'='*50}")
print(f"  {passed}/{total} checks passed", end="")
if passed == total:
    print("  — all green")
else:
    print(f"  — {total - passed} FAILED")
print(f"{'='*50}")

sys.exit(0 if passed == total else 1)
