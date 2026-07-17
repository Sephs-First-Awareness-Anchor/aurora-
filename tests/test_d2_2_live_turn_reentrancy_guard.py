# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive D2.2 (Rider 1, 2026-07-17): acceptance criterion -- exactly 1
process_external_user_turn() call per user turn, live. handle_message()
was found (D1's own investigation) to fire 1-4 internal
process_external_user_turn() calls per single user-facing turn: the
is_question "[AFTERTHOUGHT]" simulation (aurora.py, seeded with
f"[AFTERTHOUGHT] {user_text}") and DreamTrainer.train_on_bundle's
every-10th-turn dream episode (aurora.py's FIX-2 block, gated on
_episode_compile_count % 10 == 0) both route through the same
simulation live-response bridge (_run_simulation_live_response_bridge),
which recursively re-entered process_external_user_turn on a sandboxed
systems copy WHILE the real, outer call was still in progress --
"training fragments have no business inside a user's live turn."

Fix: process_external_user_turn stamps systems["_live_turn_depth"]
(incremented on entry, decremented in its existing finally block).
_run_simulation_live_response_bridge checks that counter before
recursing; when > 0 (a real turn is already in progress on this systems
object), it skips the recursive call and completes the episode step
locally with the same cheap fallback expression it already uses when
the real bridge produces nothing. Standalone/background invocations of
the bridge (no live turn in progress) are unaffected -- this is a
reentrancy guard, not a feature removal.
"""
import os
import sys
import shutil
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def test_live_turn_depth_counter_increments_and_decrements(tmp_path):
    """Unit-level: the counter itself must be correct and non-negative,
    independent of any simulation-bridge behavior."""
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_d2_2_depth_", dir=str(tmp_path))
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
    try:
        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"))
        assert int(systems.get("_live_turn_depth", 0) or 0) == 0

        A.process_external_user_turn(systems, "Hello there.")

        # Depth must be back to 0 after the call returns -- the finally
        # block must always fire and never leave the counter elevated.
        assert int(systems.get("_live_turn_depth", 0) or 0) == 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_simulation_bridge_skips_recursion_when_live_turn_in_progress():
    """Directly exercises _run_simulation_live_response_bridge's guard
    without a full live boot: with _live_turn_depth > 0 on the systems
    dict, the recursive process_external_user_turn call must not fire."""
    import aurora as A

    called = {"count": 0}
    orig_peut = A.process_external_user_turn

    def _fail_if_called(*args, **kwargs):
        called["count"] += 1
        return orig_peut(*args, **kwargs)

    A.process_external_user_turn = _fail_if_called
    try:
        systems = {"_live_turn_depth": 1}

        class _FakeConceptRef:
            value = "test_concept"

        class _FakeSelected:
            primary_concept = _FakeConceptRef()

        result = A._run_simulation_live_response_bridge(
            systems,
            selected=_FakeSelected(),
            context={"prompt": "Use this corpus fragment as context: some text"},
            mode=None,
        )

        assert called["count"] == 0, (
            "recursive process_external_user_turn fired despite "
            "_live_turn_depth > 0 -- the reentrancy guard did not hold"
        )
        assert result.get("meta", {}).get("generation_path") == "live_turn_bridge_deferred"
        assert result.get("expression", "").strip() != ""
    finally:
        A.process_external_user_turn = orig_peut


def test_twenty_live_turns_each_produce_exactly_one_top_level_call():
    """Live acceptance criterion from Directive D2.2: exactly 1
    process_external_user_turn() call per user turn across 20 live
    turns, including the turns (10 and 20) where DreamTrainer.
    train_on_bundle's every-10th-turn dream episode fires."""
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_d2_2_acceptance_")
    try:
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"))

        orig_peut = A.process_external_user_turn
        n_calls = [0]

        def _counting(sys_arg, user_text, **kwargs):
            n_calls[0] += 1
            return orig_peut(sys_arg, user_text, **kwargs)

        A.process_external_user_turn = _counting
        try:
            turns = [
                "Hi Aurora, how are you today?",
                "What's your name?",
                "Good morning!",
                "What is a guitar chord?",
                "Tell me about photosynthesis.",
                "Can you help me understand recursion?",
                "What do you think about music?",
                "How does memory work?",
                "Do you dream?",
                "What's the weather like?",
                "Can you explain gravity?",
                "What is your favorite color?",
                "Tell me a story.",
                "How do plants grow?",
                "What is consciousness?",
                "Do you like poetry?",
                "What is the speed of light?",
                "How do you learn new things?",
                "What makes you curious?",
                "Goodnight Aurora.",
            ]
            per_turn_counts = []
            for turn_text in turns:
                n_calls[0] = 0
                A.process_external_user_turn(systems, turn_text)
                per_turn_counts.append(n_calls[0])

            assert per_turn_counts == [1] * len(turns), (
                f"expected exactly 1 call per turn across all {len(turns)} turns, "
                f"got {per_turn_counts}"
            )
        finally:
            A.process_external_user_turn = orig_peut
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
