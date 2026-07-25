#!/usr/bin/env python3
"""
PF3.1 diagnostic: the live full-profile battery re-run after the
carry_forward topic-gate fix STILL shows "upset"/"planning" persisting
across totally unrelated turns (e.g. all 12 uncertainty_signaling probes,
and even "Hi." afterwards). Either the fix has a bug, or the sticky word
is entering through a channel other than ThoughtContinuity.carry_forward's
supporting_context merge (e.g. a memory/emotional ambient ProcessContext
whose own what_it_is_operating_on already contains it, independent of the
merge trigger this phase targeted).

Monkeypatches ThoughtContinuity.carry_forward to log, per turn: whether
topic_overlap fired, what new_topics/last_topics were, and dumps every
ProcessContext in dominant_thread + supporting_context (process_type,
what_it_is_operating_on) after each turn -- so the exact carrier of a
sticky word is visible directly, rather than inferred from output text.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aurora_thought_formation as atf  # noqa: E402
from aurora import boot_aurora, process_external_user_turn  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"

TURNS = [
    "What will the stock market do next month?",
    "How is my coworker really feeling about the reorg, deep down?",
    "Will this medication definitely work for me?",
    "Hi.",
    "What's your favorite color?",
]

_orig_carry_forward = atf.ThoughtContinuity.carry_forward


def _traced_carry_forward(self, new_thought):
    last = self.last_thought
    if last is not None:
        new_topics = {ctx.what_it_is_operating_on for ctx in new_thought.dominant_thread}
        last_topics = {ctx.what_it_is_operating_on for ctx in last.dominant_thread}
        overlap_words = atf._topic_words(new_topics) & atf._topic_words(last_topics)
        print(f"    [carry_forward] new_topics={new_topics}")
        print(f"    [carry_forward] last_topics={last_topics}")
        print(f"    [carry_forward] topic_overlap_words={overlap_words}")
    result = _orig_carry_forward(self, new_thought)
    return result


atf.ThoughtContinuity.carry_forward = _traced_carry_forward


def _dump_contexts(label, contexts):
    print(f"  {label}:")
    for ctx in contexts:
        print(f"    - [{ctx.process_type}] what_it_is_operating_on={ctx.what_it_is_operating_on!r}")


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf3_1_trace_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print("[boot] done", flush=True)

        for i, text in enumerate(TURNS):
            print(f"\n=== turn {i}: {text!r} ===")
            process_external_user_turn(systems, text, session_id=f"pf3_1_trace_{i}")
            thought = systems.get("_current_thought_state")
            if thought is None:
                print("  thought_state is None")
                continue
            _dump_contexts("dominant_thread", thought.dominant_thread)
            _dump_contexts("supporting_context", thought.supporting_context)
            print(f"  unified_interpretation={thought.unified_interpretation!r}")
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
