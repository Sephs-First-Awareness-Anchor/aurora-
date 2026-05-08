#!/usr/bin/env python3
"""
run_gpt_session.py — Boot Aurora and run a GPT peer-learning session.

Targets the current top fail dimensions. Runs until conversation quality
drops (n_turns=30 max). Bridges all learnings to OETS on completion.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")

def main():
    print("\n[GPT SESSION] Booting Aurora systems...")
    t0 = time.time()

    from aurora import boot_aurora, _run_live_response_turn
    from aurora_constraint_engine import ExistenceMode
    from aurora_dream_trainer import DreamTrainer

    systems = boot_aurora(state_dir=STATE_DIR, verbose=False)
    print(f"[GPT SESSION] Boot complete ({time.time()-t0:.1f}s)")

    # Report current fail-point top dims
    dt = systems.get("dream_trainer")
    if dt:
        print(f"\n[GPT SESSION] Current fail-point summary:\n{dt.fail_point_summary()}\n")

    # Wiring: socialize uses _run_live_response_turn with articulation check bypassed
    def _aurora_generate(prompt_text, source="gpt_session"):
        if not prompt_text or len(prompt_text.split()) < 2:
            return None
        prev = systems.get("_pipeline_source")
        systems["_pipeline_source"] = f"aurora:{source}"
        systems["_skip_response_postprocessing_once"] = True
        try:
            r = _run_live_response_turn(
                systems=systems,
                user_text=prompt_text,
                mode=ExistenceMode.AGENTIC,
                auto_search_enabled=False,
                session_id="gpt_learning",
                record_exchange=False,
                update_interactive_state=False,
                track_evolutionary_trace=True,
                run_periodic_maintenance=True,
            )
            if not isinstance(r, dict):
                return None
            return r.get("resp_A")
        finally:
            if prev is None:
                systems.pop("_pipeline_source", None)
            else:
                systems["_pipeline_source"] = prev

    systems["_generate_fn"] = _aurora_generate

    # Run the learning session — 30 turns, targeting top stall dims
    from aurora_gpt_learning_session import run_learning_session
    print("[GPT SESSION] Starting peer exchange (30 turns, targeting top fail dims)...\n")

    exchanges = run_learning_session(
        systems,
        n_turns=30,
        topic=None,   # session will auto-pick from fail dims
        verbose=True,
    )

    print(f"\n[GPT SESSION] Session complete. {len(exchanges)} exchanges logged.")

    # Force bridge learnings to OETS
    if dt:
        bridged = dt.force_bridge_learnings_to_oets(systems)
        print(f"[GPT SESSION] OETS bridge: {bridged} nodes created/reinforced.")

    # Save state
    try:
        chamber = systems.get("chamber")
        if chamber and hasattr(chamber, "_genealogy"):
            chamber._genealogy.flush_files()
        if dt:
            dt.ledger.save()
    except Exception as e:
        print(f"[GPT SESSION] Save warning: {e}")

    # Report updated fail dims
    if dt:
        print(f"\n[GPT SESSION] Updated fail-point summary:\n{dt.fail_point_summary()}")

    # Save transcript
    transcript_path = "aurora_state/gpt_session_transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(exchanges, f, indent=2)
    print(f"\n[GPT SESSION] Transcript saved to {transcript_path}")


if __name__ == "__main__":
    main()
