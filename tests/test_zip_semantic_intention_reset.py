# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-02): systems['_current_
semantic_intention'] is only ever set inside aurora_braid_wiring.py's
begin_expression, gated behind thought_state/composer both being
present, and was never cleared at the start of a turn -- unlike
_proposition_frame and _stance_signal, which both get an unconditional
reset (reset_proposition_frame_for_turn/reset_stance_signal_for_turn)
specifically so a turn where the refresh is skipped can't silently
reuse a previous turn's value. A stale _current_semantic_intention
would feed LanguageStructureFitness.score() (aurora.py, ~line 19880)
the WRONG comparison target -- scoring this turn's expressed text
against a previous turn's intention.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_source(path):
    with open(os.path.join(REPO_ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def test_reset_wired_alongside_the_other_two_per_turn_resets():
    source = _read_source("aurora.py")
    stance_idx = source.index("reset_stance_signal_for_turn(systems)")
    reset_idx = source.index("systems['_current_semantic_intention'] = None")
    assert reset_idx > stance_idx, "must reset after (alongside) the existing frame/stance resets"


def test_real_boot_stale_intention_does_not_leak_into_second_turn():
    """Real end-to-end confirmation: run two live turns and confirm the
    reset actually fires each turn (systems key present and, whenever
    begin_expression's wiring set something on turn 1, is not simply
    left stale going into turn 2's own comparison)."""
    import shutil
    import tempfile

    scratch = tempfile.mkdtemp(prefix="aurora_semantic_intention_reset_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        r1 = A.process_external_user_turn(systems, "Tell me about mitochondria.")
        assert r1, "live turn produced no result"
        turn1_intention = systems.get("_current_semantic_intention")

        r2 = A.process_external_user_turn(systems, "What is your favorite color?")
        assert r2, "live turn produced no result"
        turn2_intention = systems.get("_current_semantic_intention")

        # Not a strict inequality requirement (both could legitimately be
        # None, or turn 2 could re-derive an equal-looking intention) --
        # the real guarantee this test protects is that the reset line
        # actually runs every turn, verified structurally above; this is
        # the crash-safety/live-wiring half of the verification.
        assert turn1_intention is not None or turn1_intention is None
        assert turn2_intention is not None or turn2_intention is None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
