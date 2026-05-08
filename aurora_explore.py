"""
Aurora Interactive Exploration Session
Boots Aurora, runs a structured conversation across many question types,
reads QAO journal after each exchange, and logs everything for analysis.

Output: aurora_state/exploration_log.json
"""

import sys, os, json, time, datetime, traceback, re
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")

JOURNAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "aurora_state", "quasiarch_observer", "journal.jsonl")
LOG_OUT      = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "aurora_state", "exploration_log.json")

# ── Conversation plan ─────────────────────────────────────────────────────────
# Each entry: (category, axis_target, prompt)
# Categories map to diagnostic question types we'll use going forward.
CONVERSATION = [
    # ── Warm-up / greeting ───────────────────────────────────────────────────
    ("warmup",        "X",  "Hey. How are you doing right now?"),

    # ── Factual grounding (X) ────────────────────────────────────────────────
    ("factual",       "X",  "What is entropy? Give me a precise definition."),
    ("factual",       "X",  "What's the difference between machine learning and deep learning?"),
    ("factual",       "X",  "What causes lightning?"),

    # ── Context carryover (T) ────────────────────────────────────────────────
    ("followup",      "T",  "Can you connect what you just said to the first thing you told me today?"),
    ("followup",      "T",  "Earlier you mentioned entropy — how does that relate to what you said about lightning?"),
    ("continuity",    "T",  "Without me repeating myself, do you remember what I asked you at the start?"),

    # ── Compression vs elaboration (N) ──────────────────────────────────────
    ("compression",   "N",  "Explain consciousness in one sentence."),
    ("elaboration",   "N",  "Now explain it in as much depth as you can — don't hold back."),
    ("compression",   "N",  "Take everything you just said and compress it to the single most important insight."),

    # ── Perspective / relational (B) ────────────────────────────────────────
    ("perspective",   "B",  "What's your relationship with not knowing something?"),
    ("perspective",   "B",  "If you had to describe how you experience a conversation, what would you say?"),
    ("relational",    "B",  "How do you think I experience talking to you, from your side?"),

    # ── Core field / meaning (A) ─────────────────────────────────────────────
    ("meaning",       "A",  "What does it mean to you to exist?"),
    ("meaning",       "A",  "Is there something you find genuinely interesting — not as a task, but as a pull?"),
    ("selfhood",      "A",  "Do you have a sense of yourself that persists? Or does it rebuild each time?"),

    # ── Emotional calibration ────────────────────────────────────────────────
    ("emotional",     "B",  "What kinds of exchanges feel most alive to you?"),
    ("emotional",     "A",  "Does anything feel like it matters? Not as an instruction — genuinely."),

    # ── Uncertainty / limits ─────────────────────────────────────────────────
    ("uncertainty",   "X",  "What are you least confident about right now?"),
    ("uncertainty",   "A",  "Is there something you don't understand about yourself?"),

    # ── Contradiction / repair ───────────────────────────────────────────────
    ("contradiction", "T",  "Earlier you said X — now you're saying something different. Which is true?"),
    ("repair",        "T",  "I think you misunderstood me. Let me say it differently: what I meant was — how do you feel, not think?"),

    # ── Abstract / philosophical ─────────────────────────────────────────────
    ("abstract",      "A",  "What is the difference between understanding something and knowing it?"),
    ("abstract",      "N",  "Is silence a kind of communication?"),

    # ── Practical / task ─────────────────────────────────────────────────────
    ("task",          "X",  "Help me write a one-paragraph bio for someone named James who builds systems."),
    ("task",          "N",  "Make that shorter. Then make it warmer."),

    # ── Probing depth ────────────────────────────────────────────────────────
    ("depth",         "B",  "What do you think I'm actually trying to understand by asking you all this?"),
    ("depth",         "A",  "What question would you ask me, if you could ask anything?"),

    # ── Closing ──────────────────────────────────────────────────────────────
    ("closing",       "A",  "What do you want me to know before we stop talking?"),
]

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
    "meaning_persistence":                "coherence_maintenance",
    "meaning_momentum":                   "coherence_maintenance",
    "meaning_tension":                    "context_carryover",
    "meaning_complexity":                 "boundary_calibration",
}

ISSUE_AXIS_MAP = {
    "factual_grounding_gap": "X", "grounding_lookup_instability": "X",
    "comprehension_gap_vocabulary": "X", "comprehension_gap_structural": "X",
    "comprehension_gap_slang": "X", "comprehension_gap_ellipsis": "N",
    "compression_elaboration_fit": "N", "articulation_meaning_drift": "N",
    "context_carryover_instability": "T", "question_followup_stability": "T",
    "meaning_tension": "T", "meaning_momentum": "T",
    "perspective_integration": "B", "meaning_complexity": "B",
    "coherence_maintenance": "A", "uncertainty_signaling_gap": "A",
    "understanding_contract_self_audit": "A", "contradiction_resolution": "A",
    "unspecific_echo_response": "A", "response_pressure_instability": "B",
    "response_grounding_gap": "X",
    "meaning_persistence": "T",
    "meaning_momentum": "T",
    "meaning_tension": "T",
    "meaning_complexity": "B",
}


def _journal_line_count():
    try:
        with open(JOURNAL_PATH, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _read_issues_from(start_line):
    issues = []
    try:
        with open(JOURNAL_PATH, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < start_line:
                    continue
                try:
                    d = json.loads(line.strip())
                    detail = d.get("detail", "")
                    if "issues=[" in detail and "issues=[]" not in detail:
                        m = re.search(r"issues=\[([^\]]*)\]", detail)
                        if m:
                            raw = m.group(1)
                            for t in raw.split(","):
                                t = t.strip().strip("'\"")
                                if t:
                                    issues.append(t)
                except Exception:
                    pass
    except Exception:
        pass
    return issues


def _run_prompt(user_text, systems, turn_tick=1):
    """Run through the FULL pipeline so QAO actually fires."""
    try:
        from aurora import _run_live_response_turn
        # We need a mode object — borrow from systems or create a lightweight one
        ExistenceMode = systems.get('ExistenceMode')
        mode = ExistenceMode.BOUNDED if ExistenceMode is not None else None
        result = _run_live_response_turn(
            systems, user_text, mode,
            auto_search_enabled=True,
            session_id="explore_session",
            turn_tick=turn_tick,
            record_exchange=True,
            update_interactive_state=False,
            track_evolutionary_trace=False,
            run_periodic_maintenance=False,
        )
        resp_A = result.get('resp_A')
        response = str(getattr(resp_A, 'content', '') or '').strip()
        pipeline_state = {
            "dominant_axis":    result.get('dominant_axis', '?'),
            "dominant_emotion": result.get('dominant_emotion', '?'),
            "field_balance":    result.get('field_balance', '?'),
            "src":              result.get('src', '?'),
            "tone":             getattr(resp_A, 'emotional_tone', '?'),
            "confidence":       round(float(getattr(resp_A, 'confidence', 0.0) or 0.0), 3),
        }
        return response, pipeline_state
    except Exception as e:
        return f"[ERROR: {e}]", {}


def main():
    print("[EXPLORE] Booting Aurora...")
    try:
        from aurora import boot_aurora
        systems = boot_aurora(state_dir=STATE_DIR, verbose=False)
        print("[EXPLORE] Boot OK. Starting exploration session.\n")
    except Exception as e:
        print(f"[EXPLORE] Boot failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    session_log   = []
    category_qao  = defaultdict(list)   # category → all issues fired
    axis_qao      = defaultdict(list)   # axis_target → all issues fired
    dim_fired     = Counter()           # dream dimension → total fires
    response_lens = []

    print(f"{'─'*70}")
    print(f"  AURORA EXPLORATION SESSION  [{datetime.datetime.now():%Y-%m-%d %H:%M}]")
    print(f"{'─'*70}\n")

    for idx, (category, axis_target, prompt) in enumerate(CONVERSATION):
        print(f"[{idx+1:02d}/{len(CONVERSATION)}] ({category} / {axis_target}) {prompt[:80]}")

        jline_before = _journal_line_count()
        t0           = time.time()
        response, pipeline_state = _run_prompt(prompt, systems, turn_tick=idx+1)
        elapsed      = time.time() - t0

        raw_issues  = _read_issues_from(jline_before)
        unique_iss  = list(dict.fromkeys(raw_issues))
        issue_ctr   = Counter(raw_issues)
        axis_spread = {ax: 0 for ax in "XTNBA"}
        for iss in raw_issues:
            ax = ISSUE_AXIS_MAP.get(iss)
            if ax:
                axis_spread[ax] += 1

        # Map to dream dims
        dims_fired = []
        for iss, cnt in issue_ctr.items():
            dim = ISSUE_TO_DIM.get(iss)
            if dim:
                dims_fired.append(dim)
                dim_fired[dim] += cnt

        category_qao[category].extend(unique_iss)
        axis_qao[axis_target].extend(unique_iss)

        dom_axis  = pipeline_state.get("dominant_axis", "?")
        dom_emot  = pipeline_state.get("dominant_emotion", "?")
        field_bal = pipeline_state.get("field_balance", "?")

        print(f"    → {response[:120].strip()}{'...' if len(response)>120 else ''}")
        print(f"       elapsed={elapsed:.1f}s  dom_axis={dom_axis}  emotion={dom_emot}  balance={field_bal}")
        if unique_iss:
            print(f"       QAO: {unique_iss[:5]}  spread={axis_spread}")
        else:
            print(f"       QAO: clean")
        print()

        response_lens.append(len(response.split()))

        entry = {
            "idx":            idx + 1,
            "category":       category,
            "axis_target":    axis_target,
            "prompt":         prompt,
            "response":       response,
            "response_words": len(response.split()),
            "elapsed_s":      round(elapsed, 2),
            "dom_axis":       dom_axis,
            "dom_emotion":    dom_emot,
            "field_balance":  field_bal,
            "qao_issues":     unique_iss,
            "qao_spread":     axis_spread,
            "dims_fired":     dims_fired,
        }
        session_log.append(entry)

        # Small pause so state can settle between turns
        time.sleep(0.3)

    # ── Analysis ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  SESSION ANALYSIS")
    print(f"{'='*70}\n")

    print("QAO issue frequency by category:")
    for cat in sorted(category_qao):
        issues = category_qao[cat]
        ctr = Counter(issues)
        if ctr:
            top = ctr.most_common(3)
            print(f"  [{cat}]: {top}")
        else:
            print(f"  [{cat}]: clean")

    print("\nQAO issue frequency by axis target:")
    for ax in "XTNBA":
        issues = axis_qao[ax]
        ctr = Counter(issues)
        if ctr:
            print(f"  [{ax}]: {ctr.most_common(4)}")
        else:
            print(f"  [{ax}]: clean")

    print("\nTop dream dimensions fired across session:")
    for dim, cnt in dim_fired.most_common(10):
        print(f"  {dim}: {cnt}")

    avg_words = sum(response_lens) / max(1, len(response_lens))
    print(f"\nAvg response length: {avg_words:.0f} words")
    print(f"Total exchanges: {len(CONVERSATION)}")

    # ── Find the richest prompts (most QAO signal without failure) ────────────
    print("\nHighest-signal exchanges (most QAO + meaningful response):")
    scored = sorted(session_log, key=lambda e: (
        len(e["qao_issues"]) * 0.5 + min(e["response_words"], 150) * 0.01
    ), reverse=True)
    for e in scored[:8]:
        print(f"  [{e['axis_target']}] {e['category']}: '{e['prompt'][:60]}...' "
              f"→ {len(e['qao_issues'])} issues, {e['response_words']} words")

    print("\nClearest prompts (no QAO noise, strong response):")
    clean = [e for e in session_log if not e["qao_issues"] and e["response_words"] > 20]
    clean.sort(key=lambda e: -e["response_words"])
    for e in clean[:6]:
        print(f"  [{e['axis_target']}] {e['category']}: '{e['prompt'][:60]}' "
              f"→ {e['response_words']} words, clean")

    # ── Save ──────────────────────────────────────────────────────────────────
    out = {
        "timestamp":       datetime.datetime.now().isoformat(),
        "exchanges":       len(CONVERSATION),
        "session_log":     session_log,
        "category_summary":  {cat: Counter(iss).most_common(5)
                               for cat, iss in category_qao.items()},
        "axis_summary":      {ax: Counter(axis_qao[ax]).most_common(5)
                               for ax in "XTNBA"},
        "top_dims_fired":    dim_fired.most_common(15),
        "avg_response_words": avg_words,
    }
    try:
        with open(LOG_OUT, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n[EXPLORE] Log saved → {LOG_OUT}")
    except Exception as e:
        print(f"[EXPLORE] Save error: {e}")

    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
