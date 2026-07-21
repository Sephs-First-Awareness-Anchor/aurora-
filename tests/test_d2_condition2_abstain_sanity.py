# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
D2 Acceptance Memo Condition 2 (2026-07-17): "0/100 abstains must be
proven earned, not broken" -- a live sanity check with >=3 synthetic
genuinely-unanswerable turns run through process_external_user_turn()
(the same unified path D1/D2 byte-attribute to the device) surfaced two
real bugs, both fixed here:

  1. Root cause: ingest_interaction()'s blind vocabulary-learning path
     (aurora_expression_perception.py) stamps any 4+ char alphabetic
     token from raw input text as a lexicon entry with meaning
     "learned:<word>" and a POS role guessed by infer_word_role(), whose
     unconditional "default: noun" fallback accepts literally anything.
     build_relevance_anchor_set() then scores that same token as a
     RELEVANCE_DIRECT_ANCHOR match of ITSELF -- gibberish input (e.g.
     "zqxvornmal") becomes trivially "relevant" and gets echoed back as
     composed content, defeating the R1.9.2 G2 honest-abstain floor no
     matter where R_MIN is calibrated (a direct-anchor score sits above
     the entire distant/one-hop range R_MIN is derived within -- the
     memo's own prescribed "recalibrate R_MIN" fallback cannot fix this).
     Fixed: SentenceComposer._score_composer_candidate() caps relevance
     at RELEVANCE_DISTANT_FLOOR for words whose meaning is exactly the
     "learned:<word>" placeholder AND whose usage_count hasn't yet
     crossed _UNVERIFIED_VOCAB_USAGE_FLOOR (see
     tests/test_composer_relevance_selection.py for the unit-level
     proof). Words taught with a real definition
     (aurora_internal/aurora_comprehension_gap.py) or OETS-enriched
     (meaning="oets:<keyword>") are untouched.

  2. A second, smaller bug surfaced once (1) was fixed: SentenceComposer.
     compose()'s OWN internal abstain gate can return a real, non-empty
     string (one of _ABSTAIN_TEMPLATES, e.g. "I don't have a clear sense
     of that.") -- D2.1's voice-transplant unification code
     (aurora.py::_run_reasoning_pipeline) treated any non-empty resp_B
     content as grounded, mislabeling a genuine composer-level abstain as
     src="composer_unified" instead of recognizing it as an abstain.
     Fixed: the unification step now checks resp_B's content against
     SentenceComposer._ABSTAIN_TEMPLATES first and falls through to the
     true honest-abstain-and-seek net when it matches.

Residual, NOT fixed (out of this fix's scope, reported honestly): a
genuinely-unanswerable question built ENTIRELY from real English words
(a category-error nonsense question, e.g. "What is the square root of
the color purple divided by last Wednesday?") still does not abstain --
there is no gibberish token to catch, since every word is real. This is
a fundamentally different problem (whole-sentence semantic/logical
coherence, not per-word vocabulary trust) that this fix cannot and does
not attempt to address.
"""
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_composer_abstain_template_output_not_mislabeled_composer_unified():
    """Structural confirmation of bug 2's fix: the D2.1 unification block
    in aurora.py checks resp_B's content against the composer's own
    _ABSTAIN_TEMPLATES before treating it as grounded content."""
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index('# D2.1 (Directive D2, ratified 2026-07-17): voice transplant.')
    block = source[idx:idx + 3000]
    assert "_ABSTAIN_TEMPLATES" in block
    assert '_d2_unified_text = ""' in block


def test_unverified_vocab_cap_constant_exists_and_is_reasonable():
    from aurora_expression_perception import SentenceComposer
    floor = SentenceComposer._UNVERIFIED_VOCAB_USAGE_FLOOR
    assert isinstance(floor, int) and floor >= 1


def test_pure_gibberish_turn_abstains_honestly_live():
    """Live, end-to-end regression pinning bug 1's fix: a turn built
    entirely from invented tokens (no real English words at all) must
    produce a genuine constraint_abstain, with a logged reason, through
    the real process_external_user_turn() path -- the exact scenario
    that failed (0/4 abstained) before this fix."""
    sys.path.insert(0, REPO_ROOT)
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_d2_condition2_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        turn = "Zqxvornmal threbicultan fost yendrical mip?"
        result = A.process_external_user_turn(systems, turn)
        resp_a = result.get("resp_A")
        src = str(getattr(resp_a, "src", "") or "")
        content = str(getattr(resp_a, "content", "") or "")

        assert src == "constraint_abstain", (
            f"pure-gibberish turn did not honestly abstain: src={src!r} content={content!r}"
        )
        assert content.strip(), "an abstain response must still say something to the user"

        log_path = os.path.join(scratch_state, "constraint_fallback_log.jsonl")
        assert os.path.exists(log_path), "abstain must be logged (F2/N4 doctrine: generated, logged reason)"
        with open(log_path) as f:
            lines = [l for l in f if l.strip()]
        assert lines, "constraint_fallback_log.jsonl must have at least one entry"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
