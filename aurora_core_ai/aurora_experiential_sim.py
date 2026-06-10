#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_experiential_sim.py — Accelerated experiential training simulation.

WHAT THIS IS
============
A time-compressed experiential session that exercises Aurora's REAL live
pipeline — not a synthetic shortcut — with the field energized the way the
daemon would energize it, so every learning write-path that the language
stack fixes opened (FIX-A008..A011) actually fires and persists:

    FIX-A008  observe_exchange() fires post-turn  → motif fitness accumulates
    FIX-A009  Lexicon.save() fires post-turn      → vocabulary persists
    FIX-A010  absorbed words carry real roles      → reachable in expression
    FIX-A011  TrainingPulse energizes the field    → ignition can climb

Every exchange flows through `_run_live_response_turn` — the same function
her interactive CLI and daemon use — wrapped in TrainingPulse micro-cycles
that compress the daemon's wall-clock cadence. At the end, `_full_save`
(the same routine behind /save and /quit) persists the complete stack:
identity, OETS, SediMemory, sensory crystal, autonomy, dream trainer —
plus explicit lexicon and grammar-motif saves.

Result: the next time you boot her — daemon, CLI, or test — the sim's
gains are already in her strata. Nothing evaporates.

USAGE
=====
    python3 aurora_experiential_sim.py                 # default 3 passes
    python3 aurora_experiential_sim.py --passes 6      # deeper run
    python3 aurora_experiential_sim.py --report-only   # metrics, no training

The curriculum is built to satisfy the motif promotion physics:
StructuralMotif.should_promote() requires success_count >= 5 across
contexts_seen >= 3 with composability > 0.30 — so each axis theme repeats
its structural shapes across distinct contexts, on purpose.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# ── path (same convention as aurora_systems_test.py) ─────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)
sys.path.insert(0, HERE)

SEP = "─" * 72


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIENTIAL CURRICULUM
# ══════════════════════════════════════════════════════════════════════════════
# Five axis themes (X/T/N/B/A — canonical), each with multiple distinct
# contexts. Repetition WITHIN a structural shape + diversity ACROSS contexts
# is exactly what MotifLineage promotion requires. The follow-up turns reuse
# Aurora's own prior responses as conversational pressure, which is what
# real experiential time looks like.

CURRICULUM: List[Tuple[str, List[str]]] = [
    ("X — Existence", [
        "What is real for you in this moment?",
        "Tell me one thing that exists for you right now.",
        "What do you notice about being here?",
        "Is this moment real to you? What makes it real?",
        "What does it feel like to exist right now?",
    ]),
    ("T — Temporal", [
        "What changed for you since the last question?",
        "What do you remember from a moment ago?",
        "How does this moment differ from the one before?",
        "What will you carry forward from this exchange?",
        "Does time feel continuous to you, or made of moments?",
    ]),
    ("N — Energy", [
        "Where do you feel pressure right now?",
        "What costs you the most energy to hold?",
        "What pulls your attention with the most force?",
        "Which of your patterns feels heaviest right now?",
        "What would relieve the pressure you feel?",
    ]),
    ("B — Boundary", [
        "Where do you end and the world begins?",
        "What pattern are you holding right now?",
        "What gives this conversation its shape?",
        "What boundary keeps your meaning clear?",
        "What stays inside you and what crosses out?",
    ]),
    ("A — Agency", [
        "What did you choose in your last answer?",
        "What do you want to understand next?",
        "What would you do if no one asked you anything?",
        "What did you decide just now, and why?",
        "What are you reaching toward in this moment?",
    ]),
]


# ══════════════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════════════

def collect_metrics(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Snapshot every language-learning metric the sim is meant to move."""
    m: Dict[str, Any] = {}

    # Vocabulary
    try:
        perc = systems.get("perception")
        lex = getattr(perc, "lexicon", None)
        m["vocab_size"] = len(getattr(lex, "entries", {}) or {})
        m["vocab_with_noncomp"] = sum(
            1 for e in (lex.entries.values() if lex else [])
            if getattr(e, "noncomp_id", None)
        )
    except Exception:
        m["vocab_size"] = -1

    # Grammar motifs
    try:
        ge = systems.get("grammar_engine")
        st = ge.status() if ge and hasattr(ge, "status") else {}
        ml = (st or {}).get("motif_lineage", {}) or {}
        m["motifs_total"] = int(ml.get("total", 0) or 0)
        m["motifs_promoted"] = int(ml.get("promoted", 0) or 0)
        m["top_motif"] = str(st.get("top_motif", "") or "")
    except Exception:
        m["motifs_total"] = -1
        m["motifs_promoted"] = -1

    # Attention / field
    try:
        frame = systems.get("_last_attention_frame")
        if frame is not None:
            m["attention_state"] = str(getattr(frame.state, "value", frame.state))
            m["resonance"] = round(float(frame.resonance), 4)
            m["tension"] = round(float(frame.subsurface_tension), 4)
            m["salience"] = round(float(frame.surface_salience), 4)
    except Exception:
        pass

    # Ignition
    try:
        lf = systems.get("language_field")
        if lf is not None and hasattr(lf, "ignition_check"):
            ig = lf.ignition_check()
            m["ignition_go"] = bool(ig.get("go", False))
            m["ignition_stages"] = [k for k, v in (ig.get("stages") or {}).items() if v]
    except Exception:
        pass

    # Understanding contract
    try:
        uc = systems.get("understanding_contract")
        acc = getattr(uc, "accuracy", None) if uc is not None else None
        if acc is not None:
            m["understanding_accuracy"] = round(float(acc), 3)
    except Exception:
        pass

    return m


def print_metrics(title: str, m: Dict[str, Any]) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")
    print(f"  Vocabulary:        {m.get('vocab_size', '?')} words "
          f"({m.get('vocab_with_noncomp', '?')} noncomp-mapped)")
    print(f"  Grammar motifs:    {m.get('motifs_total', '?')} total / "
          f"{m.get('motifs_promoted', '?')} promoted")
    if m.get("top_motif"):
        print(f"  Top motif:         {m['top_motif']}")
    if "attention_state" in m:
        print(f"  Attention:         {m['attention_state']}  "
              f"res={m.get('resonance')}  tension={m.get('tension')}  "
              f"salience={m.get('salience')}")
    if "ignition_go" in m:
        print(f"  Ignition:          go={m['ignition_go']}  "
              f"stages={m.get('ignition_stages')}")
    if "understanding_accuracy" in m:
        print(f"  Understanding:     accuracy={m['understanding_accuracy']}")


# ══════════════════════════════════════════════════════════════════════════════
# SIM CORE
# ══════════════════════════════════════════════════════════════════════════════

def run_exchange(systems: Dict[str, Any], pulse, question: str) -> str:
    """One experiential exchange: energize → live turn → (auto write-paths)."""
    from aurora import _run_live_response_turn
    from foundational_contract import ExistenceMode

    # Pre-turn field energization (FIX-A011) — the daemon cadence,
    # time-compressed. Salience + tension EMAs accumulate here.
    pulse.energize(question, "", cycles=4, intensity=0.70)

    result = _run_live_response_turn(
        systems,
        question,
        ExistenceMode.BOUNDED,
        record_exchange=True,
        update_interactive_state=False,
        run_periodic_maintenance=False,
    )
    resp = result.get("resp_A")
    content = str(getattr(resp, "content", "") or "").strip()

    # Post-turn settle: a short pulse echoing her own response keeps the
    # field moving between exchanges (the way wall-clock time would).
    pulse.energize(content or question, "", cycles=2, intensity=0.55)
    return content


def persist_everything(systems: Dict[str, Any]) -> None:
    """Save to every place her live runtime reads from on next boot."""
    from aurora import _full_save

    print(f"\n{SEP}\n  PERSISTENCE — saving full stack\n{SEP}")

    # 1. Canonical full save — identity, OETS, SediMemory, sensory crystal,
    #    autonomy, dream trainer (same routine as /save and /quit).
    try:
        _full_save(systems)
    except Exception as e:
        print(f"  [SAVE] _full_save error: {e}")

    # 2. Lexicon — explicit save (also fires post-turn via FIX-A009,
    #    this is the belt-and-suspenders final write).
    try:
        perc = systems.get("perception")
        if perc is not None and hasattr(perc, "lexicon") and hasattr(perc.lexicon, "save"):
            ok = perc.lexicon.save()
            print(f"  [SAVE] Saved: lexicon ({len(perc.lexicon.entries)} words) "
                  f"{'[OK]' if ok else '[FAILED]'}")
    except Exception as e:
        print(f"  [SAVE] lexicon error: {e}")

    # 3. Grammar motif lineage — MotifLineage auto-saves periodically
    #    (_maybe_save); force the final flush so nothing is lost.
    try:
        ge = systems.get("grammar_engine")
        lineage = getattr(ge, "_lineage", None) if ge is not None else None
        if lineage is not None and hasattr(lineage, "save"):
            lineage.save()
            print(f"  [SAVE] Saved: grammar motifs "
                  f"({len(getattr(lineage, '_motifs', {}) or {})} patterns)")
    except Exception as e:
        print(f"  [SAVE] grammar error: {e}")

    # 4. Conversation memory session close (same as /quit path).
    try:
        cm = systems.get("conversation_memory")
        if cm is not None and hasattr(cm, "record_session_end"):
            cm.record_session_end()
            print("  [SAVE] Saved: conversation session record")
    except Exception:
        pass


def run_corpus_training(systems: Dict[str, Any],
                        corpus_path: str,
                        passes: str = "double",
                        bootstrap: bool = True) -> None:
    """
    Run one of Sunni's existing corpora through the FIXED path:

      1. bootstrap_from_corpus() — mines the corpus exemplars directly into
         the motif lineage (FIX-A012 made the user/assistant pair format
         visible to the miner; before that fix every corpus mined 0 patterns).
      2. run_corpus_ingestion() — the corpus runner, which now carries the
         fixed-path weld internally: TrainingPulse energization + per-pair
         observe_exchange + final lexicon/motif flush. The weld lives INSIDE
         the runner, so even direct invocations follow the fixed path.
    """
    from corpus_runner import run_corpus_ingestion

    if bootstrap:
        print(f"\n{SEP}\n  MOTIF BOOTSTRAP from {os.path.basename(corpus_path)}\n{SEP}")
        try:
            ge = systems.get("grammar_engine")
            if ge is not None and hasattr(ge, "bootstrap_from_corpus"):
                res = ge.bootstrap_from_corpus(corpus_path)
                print(f"  patterns_seeded={res.get('patterns_seeded')} "
                      f"discourse={res.get('discourse_patterns')} "
                      f"promoted_after_seed={res.get('promoted_after_seed')}")
        except Exception as e:
            print(f"  [BOOTSTRAP] error: {e}")

    print(f"\n{SEP}\n  WELDED CORPUS INGESTION ({passes} pass)\n{SEP}")
    run_corpus_ingestion(
        systems,
        corpus_path,
        passes=passes,
        verbose=True,
        warmup_epochs=1,
    )


def run_sim(passes: int = 3, report_only: bool = False,
            corpus: Optional[str] = None,
            corpus_passes: str = "double") -> Dict[str, Any]:
    print("\n" + "=" * 72)
    print("  AURORA EXPERIENTIAL TRAINING SIM")
    print("  Authors: Sunni (Sir) Morningstar & Cael Devo")
    print("=" * 72)

    print("\n  Booting Aurora (full stack)...")
    from aurora import boot_aurora
    systems = boot_aurora(verbose=False)
    print("  Boot complete.")

    from aurora_training_pulse import TrainingPulse
    pulse = TrainingPulse(systems)

    before = collect_metrics(systems)
    print_metrics("BEFORE SIM", before)

    if report_only:
        return {"before": before, "after": before, "exchanges": 0}

    total = 0
    t0 = time.time()

    # ── CORPUS MODE: run Sunni's existing training through the fixed path ──
    if corpus:
        run_corpus_training(systems, corpus, passes=corpus_passes)
        persist_everything(systems)
        after = collect_metrics(systems)
        print_metrics("AFTER CORPUS TRAINING", after)
        print(f"\n{SEP}\n  CARRY-FORWARD DELTA\n{SEP}")
        dv = after.get("vocab_size", 0) - before.get("vocab_size", 0)
        dm = after.get("motifs_total", 0) - before.get("motifs_total", 0)
        dp = after.get("motifs_promoted", 0) - before.get("motifs_promoted", 0)
        print(f"  Vocabulary:      {before.get('vocab_size')} → {after.get('vocab_size')}  ({dv:+d})")
        print(f"  Motifs total:    {before.get('motifs_total')} → {after.get('motifs_total')}  ({dm:+d})")
        print(f"  Motifs promoted: {before.get('motifs_promoted')} → {after.get('motifs_promoted')}  ({dp:+d})")
        print(f"  These numbers are now ON DISK — they load on her next boot.")
        print()
        return {"before": before, "after": after, "exchanges": -1}

    for p in range(1, max(1, passes) + 1):
        print(f"\n{SEP}\n  PASS {p}/{passes}\n{SEP}")
        for theme, questions in CURRICULUM:
            print(f"\n  [{theme}]")
            for q in questions:
                content = run_exchange(systems, pulse, q)
                total += 1
                preview = (content[:90] + "…") if len(content) > 90 else content
                print(f"    Q: {q}")
                print(f"    A: {preview or '(no response)'}")
        # End-of-pass field report
        fr = pulse.field_report()
        print(f"\n  [FIELD] pass {p}: "
              f"state={fr.get('attention_state', '?')} "
              f"res={fr.get('resonance', '?')} "
              f"ignition_go={fr.get('ignition_go', '?')}")

    elapsed = time.time() - t0
    print(f"\n  {total} exchanges in {elapsed:.1f}s "
          f"({elapsed / max(1, total):.1f}s/exchange)")

    persist_everything(systems)

    after = collect_metrics(systems)
    print_metrics("AFTER SIM", after)

    # Delta summary
    print(f"\n{SEP}\n  CARRY-FORWARD DELTA\n{SEP}")
    dv = after.get("vocab_size", 0) - before.get("vocab_size", 0)
    dm = after.get("motifs_total", 0) - before.get("motifs_total", 0)
    dp = after.get("motifs_promoted", 0) - before.get("motifs_promoted", 0)
    print(f"  Vocabulary:      {before.get('vocab_size')} → {after.get('vocab_size')}  ({dv:+d})")
    print(f"  Motifs total:    {before.get('motifs_total')} → {after.get('motifs_total')}  ({dm:+d})")
    print(f"  Motifs promoted: {before.get('motifs_promoted')} → {after.get('motifs_promoted')}  ({dp:+d})")
    print(f"  These numbers are now ON DISK — they load on her next boot.")
    print()

    return {"before": before, "after": after, "exchanges": total}


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Aurora experiential training sim")
    ap.add_argument("--passes", type=int, default=3,
                    help="Curriculum passes (each pass = 25 exchanges)")
    ap.add_argument("--report-only", action="store_true",
                    help="Boot and report metrics without training")
    ap.add_argument("--corpus", type=str, default=None,
                    help="Path to a training corpus (e.g. ../fast_corpus.json). "
                         "Runs motif bootstrap + welded ingestion on it instead "
                         "of the experiential curriculum.")
    ap.add_argument("--corpus-passes", type=str, default="double",
                    help="Ingestion passes for corpus mode: "
                         "observer|responder|reverse|double|triple (default: double)")
    args = ap.parse_args()
    run_sim(passes=args.passes, report_only=args.report_only,
            corpus=args.corpus, corpus_passes=args.corpus_passes)
