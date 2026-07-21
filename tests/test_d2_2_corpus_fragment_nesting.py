# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive D2.2 (Rider 1, 2026-07-17): the relational-probe corpus-fragment
self-nesting bug. A probe prompt built as
"Use this corpus fragment as context: {snippet}" is a turn like any
other, so its own exchange can get logged back into the fail-point
ledger as a future example. The next probe-building pass then picked
that already-wrapped text back up as source_snippet and wrapped it
AGAIN, compounding the prefix linearly every cycle -- observed live as
dozens of repeats of the same prefix in one string (see D1's trace,
documented in known_fixes_registry.md).

Two-layer fix: (1) FailPointLedger._sanitize_example strips the wrapper
at WRITE time, mirroring the existing [AFTERTHOUGHT] strip already in
that function for the identical bug class; (2)
DreamTrainer._build_relational_probe_specs strips it again at READ time
as defense-in-depth, and "use"/"corpus"/"fragment" are excluded from
relational-pair extraction so the wrapper's own words can never be
mined as a fake "relational pair" in the first place.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dream_trainer import (
    DreamTrainer,
    FailPointLedger,
    _CORPUS_FRAGMENT_PREFIX,
    _extract_relational_pairs,
    _strip_corpus_fragment_wrapper,
)


def test_strip_corpus_fragment_wrapper_single_occurrence():
    text = f"{_CORPUS_FRAGMENT_PREFIX}the cat sat on the mat"
    assert _strip_corpus_fragment_wrapper(text) == "the cat sat on the mat"


def test_strip_corpus_fragment_wrapper_compounded_occurrences():
    text = (_CORPUS_FRAGMENT_PREFIX * 6) + "the cat sat on the mat"
    assert _strip_corpus_fragment_wrapper(text) == "the cat sat on the mat"


def test_strip_corpus_fragment_wrapper_idempotent_on_clean_text():
    assert _strip_corpus_fragment_wrapper("the cat sat on the mat") == "the cat sat on the mat"
    assert _strip_corpus_fragment_wrapper("") == ""


def test_extract_relational_pairs_never_mines_wrapper_words():
    """The wrapper phrase itself must never be minable as a relational
    pair -- this is what let "use"/"corpus" become the (left, right) fed
    back into the NEXT wrap, live."""
    wrapped_texts = [
        f"{_CORPUS_FRAGMENT_PREFIX}{_CORPUS_FRAGMENT_PREFIX}some real corpus content about photosynthesis",
    ]
    pairs = _extract_relational_pairs(wrapped_texts, limit=4)
    for left, right in pairs:
        assert left not in ("use", "corpus", "fragment")
        assert right not in ("use", "corpus", "fragment")


def test_sanitize_example_strips_corpus_fragment_wrapper_at_write_time(tmp_path):
    """FailPointLedger._sanitize_example (write path) must strip the
    wrapper the same way it already strips [AFTERTHOUGHT] -- catching the
    bug at the point of storage, before any read-time defense is needed."""
    ledger = FailPointLedger(state_dir=str(tmp_path))
    compounded = (_CORPUS_FRAGMENT_PREFIX * 12) + "a fresh corpus snippet about tides"
    ledger.record_fail(
        "semantic_precision",
        severity=0.6,
        example={
            "conversation_id": "conv_1",
            "source": "relational_probe",
            "user_turns": [compounded],
            "assistant_turns": ["I considered the tides."],
            "timestamp": 0.0,
        },
    )
    examples = ledger.get_examples("semantic_precision", limit=1)
    assert examples, "record_fail did not store an example"
    stored_user_turn = examples[0]["user_turns"][0]
    assert _CORPUS_FRAGMENT_PREFIX.strip().lower() not in stored_user_turn.lower()
    assert stored_user_turn == "a fresh corpus snippet about tides"


def test_relational_probe_specs_do_not_compound_across_repeated_cycles(tmp_path):
    """End-to-end regression: simulate several probe-building cycles where
    each cycle's own prompt_candidate gets logged back into the ledger
    (exactly what happens live when a probe-seeded turn's exchange is
    recorded as a fail-point example), and confirm the wrapper prefix
    never grows past one occurrence in any generated prompt_candidate."""
    trainer = DreamTrainer(state_dir=str(tmp_path))
    dim = "semantic_precision"

    trainer.ledger.record_fail(
        dim,
        severity=0.6,
        example={
            "conversation_id": "conv_seed",
            "source": "test",
            "user_turns": ["photosynthesis converts light into chemical energy"],
            "assistant_turns": ["plants use chlorophyll to capture light"],
            "timestamp": 0.0,
        },
    )

    max_prefix_repeats_seen = 0
    for cycle in range(5):
        specs = trainer._build_relational_probe_specs([(dim, 0.8)], limit=2)
        assert specs, f"cycle {cycle}: no specs produced"
        for spec in specs:
            for candidate in spec.get("prompt_candidates", []):
                repeats = candidate.count(_CORPUS_FRAGMENT_PREFIX.strip())
                max_prefix_repeats_seen = max(max_prefix_repeats_seen, repeats)
                assert repeats <= 1, (
                    f"cycle {cycle}: prompt_candidate has {repeats} repeats of the "
                    f"corpus-fragment wrapper -- compounding regressed: {candidate!r}"
                )
        # Simulate the probe's own exchange getting logged back into the
        # ledger, exactly as a live probe-seeded turn would be recorded.
        top_candidate = specs[0]["prompt_candidates"][0]
        trainer.ledger.record_fail(
            dim,
            severity=0.7,
            example={
                "conversation_id": f"conv_cycle_{cycle}",
                "source": "relational_probe",
                "user_turns": [top_candidate],
                "assistant_turns": ["a generated reply to the probe"],
                "timestamp": float(cycle + 1),
            },
        )

    assert max_prefix_repeats_seen <= 1
