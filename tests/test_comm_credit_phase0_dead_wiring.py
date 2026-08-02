# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Communication Credit Unification, Phase 0 (2026-07-28): repair dead
wiring, re-scoped per verification against the actual current code
(Break 1's central claim -- "comprehension-gap system unreachable on
ordinary turns" -- turned out to be false; a separate, correctly-wired
call path already exists via dual_question_pipeline(). Only the
genuinely dead legacy hooks are fixed/removed here).

Break 1: `_cgs` was referenced inside `_run_live_response_turn()`'s
parser-exception except block without ever being locally bound there
(only bound in a different scope, the boot function) -- guaranteed
NameError on every real parser failure. The sibling
`except Exception: pass` two lines below does NOT catch it (siblings
of the same try, not nested), so the NameError propagated out of the
whole fallback path instead of being silently absorbed as it looked
like on inspection.

Break 1 cleanup: a second, permanently-dead hook read
systems['_comprehension_gap'] (a key never assigned anywhere) and
called track_resolution() (a method that doesn't exist anywhere) --
removed outright, per the spec's own recommended fix.

Break 2: aurora.py's perception.ingest_interaction(user_text,
_resp_text_p) call passed two positional strings against the real
signature ingest_interaction(interaction: dict, mode: str = "sim") --
interaction.get(...) raised AttributeError on every single turn,
silently swallowed by the surrounding try/except. Fixed to pass a
dict and mode="persistent" (genuine live dialogue, not a simulation).

These call sites are deeply embedded in _run_live_response_turn(), a
~1300-line function requiring a full live boot to exercise end-to-end
-- this campaign's established pattern for such cases (see
test_m1_1a_relation_pairs.py's test_chain_down5_understanding_calls_
tier2_logger) is direct source-level structural verification, plus a
real behavioral test of the isolated fixed call shape against the
actual target method wherever that's cheap enough to construct
directly (it is here -- no full engine boot needed).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_expression_perception as aep  # noqa: E402


def _read_aurora_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


def _run_live_response_turn_block():
    source = _read_aurora_source()
    start = source.index("def _run_live_response_turn(")
    # Next top-level `def ` after this one marks the function's end.
    end = source.index("\ndef ", start + 10)
    return source[start:end]


def test_cgs_is_bound_before_use_in_parser_exception_handler():
    """The exact bug: _cgs referenced via hasattr(_cgs, ...) inside the
    parser's except block without ever being locally assigned there."""
    block = _run_live_response_turn_block()
    assign_idx = block.index('_cgs = systems.get("comprehension_gap_system")')
    use_idx = block.index('hasattr(_cgs, "process")')
    assert assign_idx < use_idx, "_cgs must be bound before its first use in this block"


def test_dead_comprehension_gap_alias_key_is_gone():
    """Break 1 cleanup's own acceptance bar: no code reads the
    never-assigned '_comprehension_gap' systems key (aurora.py had FOUR
    occurrences, not just the two the original spec cited -- two were a
    harmless-but-pointless dead-key check before an `or` fallback to the
    real key, one (line ~24484 pre-fix) was a genuinely dead feature
    with no fallback at all, silently never firing) or calls the
    nonexistent track_resolution() method as a real call (not just
    mentioned in an explanatory comment, which this file's own fix
    commentary legitimately does)."""
    source = _read_aurora_source()
    assert '"_comprehension_gap"' not in source
    assert ".track_resolution(" not in source


def test_ingest_interaction_call_site_passes_a_dict_not_two_strings():
    block = _run_live_response_turn_block()
    assert '_perc_a6.ingest_interaction({"input": user_text}, mode="persistent")' in block
    # the old broken call shape must not have silently come back
    assert "_perc_a6.ingest_interaction(user_text, _resp_text_p)" not in block


def test_ingest_interaction_new_call_shape_works_against_the_real_method():
    """Behavioral confirmation, not just a source-text check: the FIXED
    call shape must not raise against the real, unmodified
    ExpressionPerceptionEngine.ingest_interaction()."""
    class _FakePerceptionSelf:
        oets = None
        composer = None

        def perceive(self, raw, ex_mode):
            return {"raw": raw, "ex_mode": ex_mode}

    fake = _FakePerceptionSelf()
    # "ok" is in the method's own _LEXICON_NOISE set, so the word-learning
    # path (which would need a real lexicon/oets) never engages -- this
    # isolates exactly the bug's failure point (interaction.get(...))
    # without needing to construct a full real engine.
    result = aep.ExpressionPerceptionEngine.ingest_interaction(
        fake, {"input": "ok"}, mode="persistent"
    )
    assert result["raw"]["text"] == "ok"
    assert result["raw"]["tone"] == "neutral"
    from foundational_contract import ExistenceMode
    assert result["ex_mode"] == ExistenceMode.PERSISTENT


def test_old_broken_call_shape_would_have_raised():
    """Confirms the bug this fix addresses was real: the OLD call shape
    (two positional strings) genuinely raises against the real method,
    which is exactly why it needed fixing rather than being a
    theoretical concern."""
    class _FakePerceptionSelf:
        oets = None
        composer = None

        def perceive(self, raw, ex_mode):
            return {}

    fake = _FakePerceptionSelf()
    try:
        aep.ExpressionPerceptionEngine.ingest_interaction(fake, "ok", "some response")
        assert False, "expected AttributeError from the old two-positional-string call shape"
    except AttributeError:
        pass


def test_ingest_interaction_call_site_only_reachable_with_a_real_response():
    """The outer gate (perception present, real user_text, real response
    content) is unchanged -- this fix only corrects the call's argument
    shape, not when it fires."""
    block = _run_live_response_turn_block()
    call_idx = block.index('_perc_a6.ingest_interaction({"input": user_text}, mode="persistent")')
    gate_idx = block.rindex('if _perc_a6 and user_text and _resp_text_p:', 0, call_idx)
    assert call_idx - gate_idx < 1500, "the gate should immediately precede this call, not some earlier one"


def test_fail_ledger_gap_routing_uses_the_real_key():
    """Found while writing this file's own tests, not in the original
    spec: aurora.py:~24484 read systems['_comprehension_gap'] with NO
    fallback at all (unlike the two sibling call sites elsewhere in the
    file that at least had `or systems.get('comprehension_gap_system')`)
    -- so the whole 'FIX 1: ClarificationMemory -> fail ledger' feature
    (recurring comprehension-gap types feeding the dream training fail
    ledger every 5 turns) had been permanently dead since it was
    written. Fixed to the real key."""
    block = _run_live_response_turn_block()
    assert '_cgs_fl = systems.get("comprehension_gap_system")' in block
    assert '_cgs_fl = systems.get("_comprehension_gap")' not in block


def test_gap_resolution_helpers_use_the_real_key_without_a_dead_check():
    """The two other '_comprehension_gap' sites (outside
    _run_live_response_turn, in the gap-resolution helper functions) had
    a harmless-but-pointless `.get("_comprehension_gap") or
    .get("comprehension_gap_system")` -- simplified to the one real key
    per this fix's cleanup, matching the spec's own acceptance test #3
    ("no code reads _comprehension_gap")."""
    source = _read_aurora_source()
    assert source.count('gap_system = systems.get("comprehension_gap_system")') >= 2
