#!/usr/bin/env python3
"""
W1 diagnostic: is the thought rung starved (ThoughtIntegrationSpace.integrate()
skipping, < 2 registered processes) or is it succeeding but PF1.5's telemetry
guard (aurora_internal.aurora_proposition_frame._looks_like_internal_telemetry)
rejecting its own legitimate output, since _reason_through_dominant's ONLY
output format is that same pipe-joined telemetry shape?

One boot (surface profile), a handful of real turns, direct inspection of
systems['_current_thought_state'] right after begin_response_turn fires --
no full battery needed for this question.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_internal.aurora_proposition_frame import (  # noqa: E402
    _looks_like_internal_telemetry, build_frame,
)

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "He's a bit nervous around new people.",
    "What's the best way to refinish them without replacing them?",
    "The report says sales are up, but the revenue numbers are actually down.",
    "I told my friend I was fine, but I've been crying all week.",
]


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_w1_diag_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        for i, text in enumerate(TURNS):
            process_external_user_turn(systems, text, session_id=f"w1_diag_{i}")
            thought = systems.get("_current_thought_state")
            print(f"\n--- turn {i}: {text!r} ---")
            if thought is None:
                print("  thought_state is None (exception path in begin_response_turn)")
                continue
            print(f"  skipped={thought.skipped}")
            print(f"  confidence={thought.confidence}")
            print(f"  len(dominant_thread)={len(thought.dominant_thread)}")
            print(f"  unified_interpretation={thought.unified_interpretation!r}")
            print(f"  self_application={thought.self_application!r}")
            combined = " ".join(s for s in (thought.unified_interpretation, thought.self_application) if s)
            print(f"  _looks_like_internal_telemetry(combined)={_looks_like_internal_telemetry(combined)}")
            frame = build_frame(systems, type("S", (), {"noncomp_input_state": {}})())
            print(f"  build_frame -> source={getattr(frame, 'source', None)}")
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
