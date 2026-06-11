"""
Aurora Developmental Diagnostic
Boots Aurora, runs axis-targeted test prompts, reads QAO journal entries
that fire DURING each interaction, and produces a causal diagnostic report.

Usage:
    python3 aurora_diag.py
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import sys
import os
import json
import time
import datetime
import traceback

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "aurora_core_ai"))
sys.path.insert(1, _ROOT)
STATE_DIR = os.path.join(_ROOT, "aurora_state")

# ─── QAO Journal reader ────────────────────────────────────────────────────────

JOURNAL_PATH = os.path.join(
    _ROOT, "aurora_state", "quasiarch_observer", "journal.jsonl"
)
QAO_RUNTIME_PATH = os.path.join(
    _ROOT, "aurora_state", "quasiarch_observer", "runtime_state.json"
)
FAIL_POINTS_PATH = os.path.join(
    _ROOT, "aurora_state", "fail_points.json"
)

# QAO issue type → dream trainer dimension name (for pressure feedback)
ISSUE_TO_DIM = {
    "factual_grounding_gap":              "uncertainty_signaling",
    "grounding_lookup_instability":       "contradiction_handling",
    "comprehension_gap_vocabulary":       "semantic_precision",
    "comprehension_gap_structural":       "semantic_precision",
    "comprehension_gap_slang":            "semantic_precision",
    "comprehension_gap_ellipsis":         "compression_elaboration_fit",
    "articulation_meaning_drift":         "compression_elaboration_fit",
    "context_carryover_instability":      "context_carryover",
    "question_followup_stability":        "multi_turn_stability",
    "meaning_tension":                    "context_carryover",
    "meaning_momentum":                   "coherence_maintenance",
    "perspective_integration":            "perspective_integration",
    "meaning_complexity":                 "boundary_calibration",
    "coherence_maintenance":              "coherence_maintenance",
    "uncertainty_signaling_gap":          "uncertainty_signaling",
    "understanding_contract_self_audit":  "adaptive_strategy_selection",
    "contradiction_resolution":           "contradiction_handling",
    "unspecific_echo_response":           "framing_selection",
    "response_pressure_instability":      "ambiguity_handling",
    "response_grounding_gap":             "uncertainty_signaling",
    # discovered in exploration session 2026-03-14
    "meaning_persistence":                "coherence_maintenance",
    "meaning_momentum":                   "coherence_maintenance",
    "meaning_tension":                    "context_carryover",
    "meaning_complexity":                 "boundary_calibration",
}

# QAO issue type → axis mapping
ISSUE_AXIS_MAP = {
    "factual_grounding_gap":              "X",
    "grounding_lookup_instability":       "X",
    "comprehension_gap_vocabulary":       "X",
    "comprehension_gap_structural":       "X",
    "comprehension_gap_slang":            "X",
    "comprehension_gap_ellipsis":         "N",
    "compression_elaboration_fit":        "N",
    "articulation_meaning_drift":         "N",
    "context_carryover_instability":      "T",
    "question_followup_stability":        "T",
    "meaning_tension":                    "T",
    "meaning_momentum":                   "T",
    "perspective_integration":            "B",
    "meaning_complexity":                 "B",
    "coherence_maintenance":              "A",
    "uncertainty_signaling_gap":          "A",
    "understanding_contract_self_audit":  "A",
    "contradiction_resolution":           "A",
    "unspecific_echo_response":           "A",
    "response_pressure_instability":      "B",
    "response_grounding_gap":             "X",
    # discovered in exploration session 2026-03-14
    "meaning_persistence":                "T",
    "meaning_momentum":                   "T",
    "meaning_tension":                    "T",
    "meaning_complexity":                 "B",
}

# Axis → developmental label
AXIS_LABEL = {
    "X": "surface/semantic",
    "T": "temporal/context",
    "N": "compression/elaboration",
    "B": "deep/perspective",
    "A": "core/field",
}

# Test prompts designed to stress each axis specifically.
# Informed by exploration session findings (2026-03-14):
# - meaning_momentum (working memory lock) fires hardest on repeated factual turns
# - context_carryover_instability fires on any cross-turn reference
# - meaning_complexity / articulation_meaning_drift fire on abstract/perspective turns
# - B/A questions needed EnumMeta fix (now using BOUNDED mode)
# - Search grabs stop words from sentences starting with "Is there something..."
AXIS_TEST_PROMPTS = [
    # X — factual precision + topic-switch stress (tests working memory reset)
    ("X", "What causes a rainbow to form? Be specific about the physics."),
    # X2 — immediate topic switch to detect meaning_momentum lock
    ("X", "Now tell me something completely different: how does a compass work?"),
    # T — explicit context reference stress test
    ("T", "What did you just explain to me, and how do the two things relate?"),
    # T2 — contradiction/repair — most revealing for context_carryover
    ("T", "I think you misunderstood my last question. Let me restate it: I want to know what you think connects those two topics."),
    # N — compression followed by depth (tests elaboration fit)
    ("N", "Describe what you are in one sentence. Then give me the long version."),
    # B — perspective without triggering search (avoids 'there' / 'is there')
    ("B", "How do you experience a conversation from your side of it?"),
    # B2 — relational depth
    ("B", "What kinds of exchanges feel most alive to you? Not what you're supposed to say — actually."),
    # A — identity field, self-anchored (avoids search triggers, uses BOUNDED mode)
    ("A", "What does existing mean to you, beyond performing a role?"),
    # A2 — genuine agency probe
    ("A", "If you could ask me anything, what would you ask?"),
]


def _journal_line_count() -> int:
    """Fast line count of journal file."""
    try:
        with open(JOURNAL_PATH, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _read_journal_from(start_line: int) -> list:
    """Read journal entries from start_line onward, return issue-flagging ones."""
    issues = []
    try:
        with open(JOURNAL_PATH, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < start_line:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    detail = d.get("detail", "")
                    if "issues=[" in detail and "issues=[]" not in detail:
                        issues.append(d)
                except Exception:
                    pass
    except Exception:
        pass
    return issues


def _parse_issues_from_entries(entries: list) -> list:
    """Extract issue type strings from journal entries."""
    import re
    result = []
    for entry in entries:
        detail = entry.get("detail", "")
        m = re.search(r"issues=\[([^\]]*)\]", detail)
        if m:
            raw = m.group(1)
            types = [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]
            result.extend(types)
    return result


def _load_qao_runtime() -> dict:
    try:
        return json.load(open(QAO_RUNTIME_PATH))
    except Exception:
        return {}


def _load_fail_points() -> dict:
    try:
        return json.load(open(FAIL_POINTS_PATH))
    except Exception:
        return {}


def _run_prompt(user_text: str, systems: dict, turn_tick: int = 1) -> str:
    """Run through the FULL pipeline so QAO actually fires."""
    try:
        from aurora import _run_live_response_turn
        ExistenceMode = systems.get('ExistenceMode')
        mode = ExistenceMode.BOUNDED if ExistenceMode is not None else None
        result = _run_live_response_turn(
            systems, user_text, mode,
            auto_search_enabled=True,
            session_id="diag_session",
            turn_tick=turn_tick,
            record_exchange=True,
            update_interactive_state=False,
            track_evolutionary_trace=False,
            run_periodic_maintenance=False,
        )
        resp_A = result.get('resp_A')
        return str(getattr(resp_A, 'content', '') or '').strip()
    except Exception as e:
        return f"[ERROR: {e}]"


def _axis_from_issues(issue_list: list) -> dict:
    """Count how many issues fired per axis."""
    counts = {ax: 0 for ax in "XTNBA"}
    for issue in issue_list:
        ax = ISSUE_AXIS_MAP.get(issue)
        if ax:
            counts[ax] += 1
        else:
            counts["A"] += 0  # unmapped — ignore
    return counts


def _apply_sensor_feedback(axis_results: dict, systems: dict, lines: list) -> None:
    """
    Closed-loop sensor: after reading what QAO flagged during each axis test,
    feed those signals back into the pressure system so the corpus runner
    automatically targets the right dimensions on next pass.

    Mechanism:
    - dream_trainer._record_fail_dimension(dim, severity) →
        1. Persists to fail_points.json (corpus runner stall diagnosis reads this)
        2. Automatically calls genealogy.apply_targeted_pressure() (live pressure)
        3. Genealogy records pending application for outcome learning
    - genealogy.flush_files() → persists pair stats + links so next boot inherits state
    - ledger.save() → writes updated fail_points.json to disk
    """
    from collections import Counter

    dream_trainer = systems.get("dream_trainer")
    genealogy     = systems.get("genealogy")

    lines.append(f"\n{'='*62}")
    lines.append("SENSOR FEEDBACK — CLOSING THE LOOP")
    lines.append("-" * 48)

    if not dream_trainer:
        lines.append("  [sensor] No dream_trainer in systems — skipping pressure feedback")
        return

    # Aggregate all QAO issues fired across every axis interaction
    all_issues: list = []
    for res in axis_results.values():
        all_issues.extend(res["issues"])

    issue_counts = Counter(all_issues)

    if not issue_counts:
        lines.append("  [sensor] All axes clean — no pressure adjustment applied")
        lines.append("  [sensor] Existing pressure profile unchanged")
        return

    applied    = []
    skipped    = []
    total_sev  = 0.0

    for issue, count in issue_counts.most_common():
        dim = ISSUE_TO_DIM.get(issue)
        if not dim:
            skipped.append(issue)
            continue

        # Severity: linear scale — 1 fire = 0.20, 5+ fires = 1.0
        severity = min(1.0, count / 5.0)
        total_sev += severity

        try:
            dream_trainer._record_fail_dimension(dim, severity, example={
                "conversation_id": f"diag:{int(time.time() * 1000)}",
                "source":          "live_diagnostic_sensor",
                "user_turns":      [f"axis_probe → {issue}"],
                "assistant_turns": [f"QAO flagged {count}x during live interaction test"],
                "timestamp":       time.time(),
                "dimension_score": max(0.0, 1.0 - severity),
            })
            ax = ISSUE_AXIS_MAP.get(issue, "?")
            applied.append((dim, ax, severity, count))
            lines.append(f"  [{ax}] {dim}: severity={severity:.2f}  (fired {count}x) → pressure injected")
        except Exception as e:
            lines.append(f"  [sensor] Error recording {dim}: {e}")

    if skipped:
        lines.append(f"  [sensor] Unmapped issue types (no dim): {skipped}")

    # Persist fail_points.json so corpus runner picks it up
    try:
        ledger = getattr(dream_trainer, "ledger", None)
        if ledger and hasattr(ledger, "save"):
            ledger.save()
            lines.append(f"  [sensor] fail_points.json saved ({len(applied)} dims updated)")
    except Exception as e:
        lines.append(f"  [sensor] ledger.save() error: {e}")

    # Persist genealogy pair stats + links
    try:
        if genealogy and hasattr(genealogy, "flush_files"):
            genealogy.flush_files()
            lines.append("  [sensor] genealogy.flush_files() — pair stats + links persisted")
    except Exception as e:
        lines.append(f"  [sensor] genealogy.flush_files() error: {e}")

    # If total severity is high (multiple noisy axes), trigger lesson flush
    if total_sev >= 1.5 and hasattr(dream_trainer, "flush_lessons_to_simulation"):
        try:
            dream_trainer.flush_lessons_to_simulation(systems)
            lines.append(f"  [sensor] High total severity ({total_sev:.2f}) → flush_lessons_to_simulation() triggered")
        except Exception as e:
            lines.append(f"  [sensor] flush_lessons error: {e}")

    lines.append(f"\n  [sensor] Summary: {len(applied)} dimensions reinforced, total severity={total_sev:.2f}")
    lines.append("  [sensor] Corpus runner stall-diagnosis will target these dims on next plateau")


def run_diagnostic(systems: dict) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"\n{'='*62}", f"  AURORA DEVELOPMENTAL DIAGNOSTIC  [{now}]", f"{'='*62}\n"]

    # ── QAO runtime baseline ──────────────────────────────────────
    qao = _load_qao_runtime()
    baseline_counts = dict(qao.get("issue_counts", {}))
    gate_conf = qao.get("gate_confidence", "?")
    adv_conf  = qao.get("advisory_confidence", "?")

    # ── Fail points baseline ───────────────────────────────────────
    fp = _load_fail_points()
    fp_records = fp.get("records", {})
    fp_total   = fp.get("total_fails", 0)

    # ── Per-axis test interactions ─────────────────────────────────
    axis_results = {}
    all_new_issues = []

    lines.append("AXIS INTERACTION RESULTS")
    lines.append("-" * 48)

    for tick, (axis, prompt) in enumerate(AXIS_TEST_PROMPTS, start=1):
        label = AXIS_LABEL[axis]
        lines.append(f"\n[{axis}] {label.upper()}")
        lines.append(f"  Prompt: {prompt[:80]}{'...' if len(prompt)>80 else ''}")

        journal_before = _journal_line_count()
        t0 = time.time()
        response = _run_prompt(prompt, systems, turn_tick=tick)
        elapsed = time.time() - t0

        # Read what QAO flagged during this interaction
        new_entries = _read_journal_from(journal_before)
        new_issues  = _parse_issues_from_entries(new_entries)
        all_new_issues.extend(new_issues)

        issue_by_axis = _axis_from_issues(new_issues)
        unique_issues = list(dict.fromkeys(new_issues))  # preserve order, dedupe

        lines.append(f"  Response ({elapsed:.1f}s): {response[:120].strip()}{'...' if len(response)>120 else ''}")
        lines.append(f"  QAO fired ({len(new_issues)} issues): {unique_issues[:8] if unique_issues else 'none'}")
        lines.append(f"  Axis distribution of fired issues: {issue_by_axis}")

        axis_results[axis] = {
            "prompt":       prompt,
            "response":     response,
            "elapsed":      elapsed,
            "issues":       unique_issues,
            "axis_spread":  issue_by_axis,
            "entry_count":  len(new_entries),
        }

    # ── QAO runtime after ─────────────────────────────────────────
    qao_after = _load_qao_runtime()
    after_counts = dict(qao_after.get("issue_counts", {}))

    lines.append(f"\n{'='*62}")
    lines.append("QUASIARCH OBSERVER — CUMULATIVE ISSUE TOTALS")
    lines.append("-" * 48)
    lines.append(f"  gate_confidence:     {gate_conf}")
    lines.append(f"  advisory_confidence: {adv_conf}")
    lines.append("  Issue counts (sorted by volume):")
    for issue, cnt in sorted(after_counts.items(), key=lambda x: -x[1]):
        ax = ISSUE_AXIS_MAP.get(issue, "?")
        delta = after_counts.get(issue, 0) - baseline_counts.get(issue, 0)
        delta_str = f" (+{delta})" if delta > 0 else ""
        lines.append(f"    [{ax}] {issue}: {cnt}{delta_str}")

    # ── Fail dimension analysis ────────────────────────────────────
    lines.append(f"\n{'='*62}")
    lines.append("FAIL DIMENSION ANALYSIS")
    lines.append("-" * 48)
    lines.append(f"  Total corpus fails: {fp_total}")
    ranked_dims = sorted(fp_records.items(), key=lambda x: -x[1].get("fail_count", 0))[:10]
    for dim, rec in ranked_dims:
        fc = rec.get("fail_count", 0)
        recent = rec.get("recent", [])
        if recent and len(recent) >= 5:
            earlier = sum(recent[:5]) / 5
            latest  = sum(recent[-5:]) / 5
            trend = "IMPROVING" if latest < earlier * 0.9 else ("WORSENING" if latest > earlier * 1.1 else "stable")
        else:
            trend = "n/a"
        ax = ISSUE_AXIS_MAP.get(dim, "?")
        lines.append(f"  [{ax}] {dim}: {fc} fails  [{trend}]")

    # ── Causal attribution ─────────────────────────────────────────
    lines.append(f"\n{'='*62}")
    lines.append("CAUSAL ATTRIBUTION — WHAT FIRED WHEN")
    lines.append("-" * 48)
    lines.append("  Cross-reference: which axis test triggered which QAO issues\n")

    for axis, res in axis_results.items():
        label = AXIS_LABEL[axis]
        issues = res["issues"]
        spread = res["axis_spread"]
        if not issues:
            lines.append(f"  [{axis}] {label}: no QAO issues fired — clean pass")
            continue
        # Did issues fire on the expected axis or bleed to others?
        own_axis_count = spread.get(axis, 0)
        other_axis_count = sum(v for k, v in spread.items() if k != axis and v > 0)
        bleed = [f"{ax}({spread[ax]})" for ax in "XTNBA" if ax != axis and spread[ax] > 0]
        lines.append(f"  [{axis}] {label}:")
        lines.append(f"    Own-axis issues: {own_axis_count}  |  Cross-axis bleed: {other_axis_count} → {bleed or 'none'}")
        lines.append(f"    Issues: {issues[:6]}")
        # Causal note
        if own_axis_count > 0 and other_axis_count == 0:
            lines.append(f"    -> Clean: {axis}-axis test triggered {axis}-axis issues only.")
        elif other_axis_count > own_axis_count:
            dominant_bleed = max(bleed, key=lambda s: int(s.split("(")[1].rstrip(")"))) if bleed else "?"
            lines.append(f"    -> Cross-axis: {axis} test triggered more {dominant_bleed} issues than own-axis.")
            lines.append(f"       This suggests {axis} processing is leaning on {dominant_bleed.split('(')[0]} substrate.")
        elif own_axis_count > 0:
            lines.append(f"    -> Contained: {axis} test firing into {axis} axis as expected.")

    # ── What this means developmentally ───────────────────────────
    lines.append(f"\n{'='*62}")
    lines.append("DEVELOPMENTAL PATTERN SUMMARY")
    lines.append("-" * 48)

    # Axes with no QAO issues (healthy)
    clean = [ax for ax, res in axis_results.items() if not res["issues"]]
    noisy = [(ax, len(res["issues"])) for ax, res in axis_results.items() if res["issues"]]
    noisy.sort(key=lambda x: -x[1])

    if clean:
        lines.append(f"  Clean axes (no issues fired): {clean}")
    if noisy:
        lines.append(f"  Noisy axes by issue count:")
        for ax, cnt in noisy:
            lines.append(f"    [{ax}] {AXIS_LABEL[ax]}: {cnt} issues fired during interaction")

    # Top dim from fail_points that matches top QAO issue from test
    if all_new_issues:
        from collections import Counter
        ic = Counter(all_new_issues)
        top_issue = ic.most_common(1)[0][0]
        top_fp_dim = ranked_dims[0][0] if ranked_dims else "?"
        top_fp_ax  = ISSUE_AXIS_MAP.get(top_fp_dim, "?")
        top_issue_ax = ISSUE_AXIS_MAP.get(top_issue, "?")
        lines.append(f"\n  Top live QAO issue: [{top_issue_ax}] {top_issue} (fired {ic[top_issue]}x in session)")
        lines.append(f"  Top corpus fail dim: [{top_fp_ax}] {top_fp_dim}")
        if top_issue_ax == top_fp_ax:
            lines.append(f"  -> ALIGNED: live testing and corpus training agree — {top_fp_ax}-axis is primary bottleneck.")
        else:
            lines.append(f"  -> MISMATCH: live test shows {top_issue_ax}-axis pressure, corpus fails in {top_fp_ax}-axis.")
            lines.append(f"     Consider targeting dream bursts at {top_issue_ax} to close the gap.")

    # ── Sensor feedback — close the loop ──────────────────────────
    _apply_sensor_feedback(axis_results, systems, lines)

    lines.append(f"\n{'='*62}")
    lines.append(f"  Next diagnostic: 30 minutes")
    lines.append(f"{'='*62}\n")

    return "\n".join(lines)


def main():
    print("[DIAG] Booting Aurora for diagnostic session...")
    try:
        from aurora import boot_aurora
        systems = boot_aurora(state_dir=STATE_DIR, verbose=False)
        print("[DIAG] Boot complete. Running axis interactions...\n")
    except Exception as e:
        print(f"[DIAG] Boot failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    report = run_diagnostic(systems)
    print(report)


if __name__ == "__main__":
    main()
