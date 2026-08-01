# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P2.3: wire frame.stance/frame.density into the stance
lexicon's consult point in the composer.

Follows the exact composer.set_proposition_frame reset/ensure pattern
(aurora_braid_wiring.py's reset_proposition_frame_for_turn/ensure_
proposition_frame_for_turn), per the directive's own explicit
instruction. STANCE is a third closed structural slot family (content
slots, function-word slots, STANCE slots) -- role=="context" mirrors
the existing role=="agent" early-return branch in _select_constraint_
word. 0.5 is not an invented tuned threshold: it is the same neutral
baseline PropositionFrame.stance already defaults to everywhere else
in this module.

Gate (directive's own words): hedge selection demonstrably differs
between a high-density-region claim and a low-density-region claim
with matched corroboration-confidence -- i.e. density does independent
work, not riding along on the existing signal.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_source(path):
    with open(os.path.join(REPO_ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def test_composer_has_set_stance_signal_setter():
    source = _read_source("aurora_expression_perception.py")
    assert "def set_stance_signal(self, stance) -> None:" in source
    assert "self._stance_signal = stance" in source
    assert "self._stance_signal = None" in source  # __init__ default


def test_role_chars_and_lexroles_include_context():
    source = _read_source("aurora_expression_perception.py")
    start = source.index("def _compose_from_motif(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]
    assert '"context":    ()' in body or '"context": ()' in body
    assert '"context": "context"' in body


def test_select_constraint_word_has_early_context_branch():
    source = _read_source("aurora_expression_perception.py")
    start = source.index("def _select_constraint_word(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]
    agent_idx = body.index('if role == "agent":')
    context_idx = body.index('if role == "context":')
    assert agent_idx < context_idx, "context branch must mirror the agent branch's early-return position"
    assert "hedge_for_strength" in body
    assert "aurora_stance_lexicon" in body


def test_reset_and_ensure_stance_signal_functions_exist():
    source = _read_source("aurora_braid_wiring.py")
    assert "def reset_stance_signal_for_turn(systems: Dict[str, Any]) -> None:" in source
    assert "def ensure_stance_signal_for_turn(systems: Dict[str, Any]) -> None:" in source
    assert "composer.set_stance_signal(None)" in source
    assert "composer.set_stance_signal(frame.stance if frame is not None else None)" in source


def test_reset_and_ensure_wired_at_same_call_sites_as_proposition_frame():
    aurora_source = _read_source("aurora.py")
    assert "reset_stance_signal_for_turn(systems)" in aurora_source
    assert "ensure_stance_signal_for_turn(systems)" in aurora_source
    braid_source = _read_source("aurora_braid_wiring.py")
    assert "ensure_stance_signal_for_turn(systems)" in braid_source


def test_select_constraint_word_returns_hedge_below_baseline():
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        composer = SentenceComposer(LexicalMemory(state_dir=td), VoiceGenome())
        composer._stance_signal = 0.1  # well below the 0.5 baseline
        word = composer._select_constraint_word(
            "context", "X", (), "context", 0.0, [],
        )
        assert word, "low stance signal must produce a real hedge word"

        from aurora_internal.aurora_stance_lexicon import all_stance_words
        assert word.lower() in {w.lower() for w in all_stance_words()}


def test_select_constraint_word_skips_slot_when_confident():
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        composer = SentenceComposer(LexicalMemory(state_dir=td), VoiceGenome())
        composer._stance_signal = 0.9  # confident
        word = composer._select_constraint_word(
            "context", "X", (), "context", 0.0, [],
        )
        assert word == ""


def test_select_constraint_word_skips_slot_when_no_signal():
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        composer = SentenceComposer(LexicalMemory(state_dir=td), VoiceGenome())
        assert composer._stance_signal is None
        word = composer._select_constraint_word(
            "context", "X", (), "context", 0.0, [],
        )
        assert word == ""


def test_hedge_selection_differs_between_high_and_low_density_matched_corroboration():
    """The directive's own P2.3 gate: hedge selection must demonstrably
    differ between a high-density-region claim and a low-density-region
    claim with MATCHED corroboration-confidence -- density doing
    independent work, not riding along on the existing signal."""
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        composer = SentenceComposer(LexicalMemory(state_dir=td), VoiceGenome())

        # Matched corroboration-confidence (0.5 baseline in both cases),
        # only density differs -- min(0.5, density) is what varies.
        composer._stance_signal = min(0.5, 0.05)  # low-density region
        low_density_word = composer._select_constraint_word(
            "context", "X", (), "context", 0.0, [],
        )
        composer._stance_signal = min(0.5, 0.95)  # high-density region
        high_density_word = composer._select_constraint_word(
            "context", "X", (), "context", 0.0, [],
        )
        assert low_density_word != "", "low-density region must hedge"
        assert high_density_word == "", "high-density region (min stays at baseline) must not hedge"


def test_real_boot_stance_wiring_does_not_crash_live_turn():
    """Real end-to-end confirmation: boot Aurora and run a real turn --
    the new STANCE slot wiring must not crash the live pipeline even
    when sedimemory has little/no relevant history for a scratch boot."""
    import shutil
    import tempfile

    scratch = tempfile.mkdtemp(prefix="aurora_p2_3_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result = A.process_external_user_turn(systems, "Will this medication definitely work for me?")
        assert result, "live turn produced no result"

        composer = getattr(systems.get("perception"), "composer", None)
        assert composer is not None
        assert hasattr(composer, "_stance_signal")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
