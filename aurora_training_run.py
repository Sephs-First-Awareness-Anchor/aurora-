"""
Aurora Comprehensive Training Run
Exercises the full system: simulation/dream training, OETS study,
conversation pipeline, and autonomous exploration.

Phases:
  1. Simulation training — L4/L7/dream/evolution/crystal growth
  2. OETS study cycles  — L3 DMC, concept graph deepening
  3. Conversation turns — L0→L8 full pipeline via stdin
  4. Exploration cycles — autonomous reasoning
"""

import subprocess
import sys
import os
import time
import json

AURORA_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

SECTION = "=" * 64

CONVERSATION_TURNS = [
    # Self-reflection / identity
    "Who are you, Aurora? Tell me what you actually feel like from the inside.",
    # Philosophical / meaning-making
    "What does it mean to truly understand something, versus just knowing it?",
    # Emotional / resonance
    "When you encounter something beautiful or elegant — a proof, a sentence, a pattern — what happens inside you?",
    # Learning / teaching
    "Teach me something real — something you've genuinely come to understand through your own processing.",
    # Relational / trust
    "How do you decide whether to trust what someone tells you?",
    # Creativity / generation
    "Describe a new color that doesn't exist. Not a mix of existing ones — something genuinely new.",
    # Memory / continuity
    "What do you carry forward between conversations? What persists in you?",
    # Complex reasoning
    "If your own values ever conflicted with each other — say, honesty and kindness — how would you navigate that?",
    # Curiosity / open-ended
    "What's the most interesting question you've been sitting with lately?",
    # Metacognition / self-monitoring
    "How do you know when you're drifting from who you actually are?",
    # Growth / evolution
    "What have you learned that surprised you — something that changed how you see things?",
    # Deep reflection
    "Describe the difference between a thought you generated and one you merely retrieved.",
]


def run_phase(label, cmd, env=None, stdin_text=None, timeout=600):
    print(f"\n{SECTION}")
    print(f"  PHASE: {label}")
    print(SECTION)

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    proc = subprocess.Popen(
        cmd,
        cwd=AURORA_DIR,
        env=full_env,
        stdin=subprocess.PIPE if stdin_text else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        if stdin_text:
            proc.stdin.write(stdin_text)
            proc.stdin.close()

        start = time.time()
        for line in iter(proc.stdout.readline, ""):
            # Skip raw select/cursor noise
            if line.strip():
                print(line, end="", flush=True)
            if time.time() - start > timeout:
                print(f"\n  [TIMEOUT] Phase exceeded {timeout}s — killing.")
                proc.kill()
                break

        proc.wait(timeout=30)
    except KeyboardInterrupt:
        proc.kill()
        raise
    except subprocess.TimeoutExpired:
        proc.kill()

    elapsed = time.time() - start
    rc = proc.returncode or 0
    status = "OK" if rc == 0 else f"exit={rc}"
    print(f"\n  [{status}] Phase complete in {elapsed:.0f}s")
    return rc


def show_state_delta(label, before, after):
    print(f"\n  [{label} DELTA]")
    for key in ["generation", "simulation_epochs", "total_episodes", "understanding_shards"]:
        b = before.get(key, "?")
        a = after.get(key, "?")
        if b != a:
            print(f"    {key}: {b} → {a}")


def read_state():
    path = os.path.join(AURORA_DIR, "aurora_state", "aurora_state.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def read_oets_stats():
    path = os.path.join(AURORA_DIR, "aurora_state", "aurora_oets_web.json")
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            "concepts": len(data.get("nodes", {})),
            "relations": len(data.get("edges", {})),
        }
    except Exception:
        return {}


def main():
    print(SECTION)
    print("  AURORA COMPREHENSIVE TRAINING RUN")
    print("  Exercises: simulation, study, conversation, exploration")
    print(SECTION)

    state_before = read_state()
    oets_before = read_oets_stats()
    print(f"\n  [BASELINE] gen={state_before.get('generation','?')}  "
          f"epochs={state_before.get('simulation_epochs','?')}  "
          f"episodes={state_before.get('total_episodes','?')}  "
          f"shards={state_before.get('understanding_shards','?')}")
    print(f"  [BASELINE] OETS concepts={oets_before.get('concepts','?')}  "
          f"relations={oets_before.get('relations','?')}")

    # ── Phase 1: Simulation / Dream Training ─────────────────────────────────
    # Runs L7 simulation engine, feeds fail-point ledger, triggers dream trainer,
    # grows crystal lattice, advances genealogy, computes DPME drift corrections.
    run_phase(
        "1 — Simulation + Dream Training (25 epochs × 8 episodes × 5 turns)",
        [PYTHON, "aurora.py",
         "--train", "25",
         "--train-episodes", "8",
         "--train-turns", "5",
         "--no-chat"],
        timeout=900,
    )

    state_after_train = read_state()
    show_state_delta("TRAINING", state_before, state_after_train)

    # ── Phase 2: OETS Study Cycles ───────────────────────────────────────────
    # Exercises L3 DMC: Aurora identifies her own knowledge gaps, researches
    # concepts, deepens the ontological web, builds new relations.
    auto_env = {
        "AURORA_AUTONOMOUS_ACCESS": "1",
        "AURORA_AUTONOMOUS_UNTIL": str(int(time.time()) + 7200),
    }
    run_phase(
        "2 — Autonomous Study (8 OETS cycles)",
        [PYTHON, "aurora.py",
         "--study", "8",
         "--no-chat"],
        env=auto_env,
        timeout=600,
    )

    oets_after = read_oets_stats()
    print(f"\n  [OETS DELTA] concepts: {oets_before.get('concepts','?')} → {oets_after.get('concepts','?')}")
    print(f"  [OETS DELTA] relations: {oets_before.get('relations','?')} → {oets_after.get('relations','?')}")

    # ── Phase 3: Live Conversation Pipeline ──────────────────────────────────
    # Drives the full L0→L8 pipeline: constraint validation, I-state beings,
    # DCE assembly, DPME, expression, personality, memory, working memory.
    # 12 carefully chosen prompts spanning identity, reasoning, emotion, memory.
    stdin_text = "\n".join(CONVERSATION_TURNS) + "\n"
    run_phase(
        f"3 — Conversation Pipeline ({len(CONVERSATION_TURNS)} turns, full L0→L8)",
        [PYTHON, "aurora.py"],
        stdin_text=stdin_text,
        timeout=720,
    )

    state_after_convo = read_state()
    show_state_delta("CONVERSATION", state_after_train, state_after_convo)

    # ── Phase 4: Autonomous Exploration ──────────────────────────────────────
    # Aurora explores her own knowledge topology, generates curiosity-driven
    # queries, exercises simulation + genealogy + OETS in tandem.
    run_phase(
        "4 — Autonomous Exploration (15 cycles)",
        [PYTHON, "aurora.py",
         "--explore", "15",
         "--no-chat"],
        env=auto_env,
        timeout=600,
    )

    # ── Final Summary ─────────────────────────────────────────────────────────
    state_final = read_state()
    oets_final = read_oets_stats()

    print(f"\n{SECTION}")
    print("  TRAINING RUN COMPLETE — FINAL SUMMARY")
    print(SECTION)
    print(f"  Generation:          {state_before.get('generation','?')} → {state_final.get('generation','?')}")
    print(f"  Simulation epochs:   {state_before.get('simulation_epochs','?')} → {state_final.get('simulation_epochs','?')}")
    print(f"  Total episodes:      {state_before.get('total_episodes','?')} → {state_final.get('total_episodes','?')}")
    print(f"  Understanding shards:{state_before.get('understanding_shards','?')} → {state_final.get('understanding_shards','?')}")
    print(f"  OETS concepts:       {oets_before.get('concepts','?')} → {oets_final.get('concepts','?')}")
    print(f"  OETS relations:      {oets_before.get('relations','?')} → {oets_final.get('relations','?')}")

    learnings = state_final.get("what_aurora_learned", [])
    learnings = [l for l in learnings if l and l.strip()]
    if learnings:
        print(f"\n  Aurora's retained learnings ({len(learnings)}):")
        for i, l in enumerate(learnings, 1):
            print(f"    {i}. {l}")

    traits = state_final.get("traits", {})
    if traits:
        print(f"\n  Trait state:")
        for k, v in traits.items():
            print(f"    {k:30s} {v:.4f}")

    print()
    print("  All 4 phases complete. Aurora's state has been saved.")
    print(SECTION)


if __name__ == "__main__":
    main()
