# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the crystal-stagnation root cause traced empirically on
2026-07-09: Aurora's crystal count sat completely flat (byte-for-byte
identical dps_crystals.json) for over a week despite dozens of scheduled
classroom lessons running. Instrumenting a live boot showed every
_get_or_create() call during a "generic" (no seed_prompt) lesson mapped to a
concept already in the index -- run_episode()'s synthetic dialogue with no
seed only exercises the target dimension's own name plus a handful of
connector words ("now", "feels", "likely"), none of which are ever new.

select_curriculum() used to only feed real fail_points.json conversation
excerpts to dimensions that were "stale" (see the removed _is_stale) or
trending WORSENING -- every other lesson (the common case) got seed_prompt=""
and ran fully generic, never introducing a concept the crystal-creation
pipeline could catch. This test locks in the fix: every dimension that has a
real example on record gets it, regardless of stale/trend status.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_classroom import select_curriculum


def _write_fail_points(tmp_path, records):
    (tmp_path / "fail_points.json").write_text(json.dumps({"records": records}))


def test_dimension_with_no_stale_history_still_gets_real_example(tmp_path):
    """A dimension with zero prior classroom lessons (so it could never have
    been flagged 'stale' under the old logic) must still get its real
    example -- this is the exact case that silently fell back to generic
    for every ordinary lesson before the fix."""
    records = {
        "context_carryover": {
            "fail_count": 5,
            "recent": [],
            "examples": [
                {
                    "conversation_id": "conv_1",
                    "user_turns": ["what did we say about the deadline earlier"],
                }
            ],
        }
    }
    _write_fail_points(tmp_path, records)

    plan = select_curriculum({}, n=1, state_dir=str(tmp_path))

    assert len(plan) == 1
    dim, seed_prompt, content_source = plan[0]
    assert dim == "context_carryover"
    assert seed_prompt == "what did we say about the deadline earlier"
    assert content_source == "real_failure_example:conv_1"


def test_dimension_without_fail_examples_falls_back_to_directed_corpus(tmp_path):
    """A dimension with no fail_points.json examples must still get real
    content from the directed training corpus (aurora_internal/train.txt via
    DirectedTrainingCorpusBridge) rather than going fully generic -- the
    corpus is a real, much larger text pool tagged to the same rubric
    dimensions (see aurora_directed_training_corpus.py)."""
    records = {
        "boundary_calibration": {"fail_count": 2, "recent": [], "examples": []},
    }
    _write_fail_points(tmp_path, records)

    plan = select_curriculum({}, n=1, state_dir=str(tmp_path))

    dim, seed_prompt, content_source = plan[0]
    assert dim == "boundary_calibration"
    assert seed_prompt.strip()
    assert content_source.startswith("directed_corpus:boundary_calibration:")


def test_dimension_unknown_to_both_sources_falls_back_to_generic(tmp_path):
    """A dimension with no fail_points examples AND no entry in the directed
    corpus's fixed dimension set must still degrade to "generic" rather than
    erroring."""
    records = {
        "not_a_real_rubric_dimension": {"fail_count": 2, "recent": [], "examples": []},
    }
    _write_fail_points(tmp_path, records)

    plan = select_curriculum({}, n=1, state_dir=str(tmp_path))

    assert plan[0] == ("not_a_real_rubric_dimension", "", "generic")


def test_multiple_dimensions_each_get_their_own_real_example(tmp_path):
    """Every one of the n selected lessons should carry real content when
    available -- not just the single worst-ranked one."""
    records = {
        "contradiction_handling": {
            "fail_count": 9, "recent": [],
            "examples": [{"conversation_id": "c1", "user_turns": ["that contradicts what you told me before"]}],
        },
        "uncertainty_signaling": {
            "fail_count": 7, "recent": [],
            "examples": [{"conversation_id": "c2", "user_turns": ["are you sure about that or just guessing"]}],
        },
        "ambiguity_handling": {
            "fail_count": 4, "recent": [],
            "examples": [{"conversation_id": "c3", "user_turns": ["I meant the other one, not that one"]}],
        },
    }
    _write_fail_points(tmp_path, records)

    plan = select_curriculum({}, n=3, state_dir=str(tmp_path))

    assert [p[0] for p in plan] == ["contradiction_handling", "uncertainty_signaling", "ambiguity_handling"]
    assert all(p[2].startswith("real_failure_example:") for p in plan)
    assert len(set(p[1] for p in plan)) == 3, "each lesson should get distinct real content"


def test_no_fail_points_data_falls_back_to_default_pool(tmp_path):
    """A fresh environment with no fail history at all should still get real
    content off the default dimension pool via the directed corpus, not pure
    generic -- the corpus doesn't depend on fail_points.json existing."""
    plan = select_curriculum({}, n=2, state_dir=str(tmp_path))
    assert len(plan) == 2
    assert all(p[2].startswith("directed_corpus:") for p in plan)
    assert all(p[1].strip() for p in plan)


def test_rotation_persists_across_scheduled_runs(tmp_path):
    """Regression for the fail_points.json staleness bug (2026-07-11):
    select_curriculum() used to re-scan from the front of each dimension's
    example pool on every call, so every scheduled run picked the exact same
    handful of conversation ids forever -- fail_points.json examples never
    grow during scheduled runs (the live-diagnostic writer isn't part of
    that path), so nothing ever changed. Rotation state persisted to
    classroom_corpus_rotation.json must make successive calls (simulating
    successive scheduled runs against the same state_dir) advance through
    distinct real content for a dimension instead of repeating."""
    records = {
        "contradiction_handling": {
            "fail_count": 9, "recent": [],
            "examples": [
                {"conversation_id": "c1", "user_turns": ["that contradicts what you told me before"]},
                {"conversation_id": "c2", "user_turns": ["but earlier you said the opposite"]},
            ],
        },
    }
    _write_fail_points(tmp_path, records)

    seen_sources = []
    for _ in range(5):
        plan = select_curriculum({}, n=1, state_dir=str(tmp_path))
        seen_sources.append(plan[0][2])

    assert len(set(seen_sources)) == 5, (
        f"expected 5 distinct sources across 5 successive runs, got {seen_sources}"
    )
    assert seen_sources[0] == "real_failure_example:c1"
    assert seen_sources[1] == "real_failure_example:c2"
    # Once fail_points.json's own examples are exhausted, must fall through
    # to the (much larger) directed corpus rather than repeating c1/c2.
    assert seen_sources[2].startswith("directed_corpus:contradiction_handling:")
    assert seen_sources[3].startswith("directed_corpus:contradiction_handling:")

    rotation_file = tmp_path / "classroom_corpus_rotation.json"
    assert rotation_file.exists()
    saved = json.loads(rotation_file.read_text())
    assert "contradiction_handling" in saved


def test_rotation_wraps_around_once_pool_exhausted(tmp_path):
    """With only one real candidate total, the second call must not go
    generic -- it should wrap around and reuse the same real content rather
    than freezing on nothing."""
    records = {
        "ambiguity_handling": {
            "fail_count": 3, "recent": [],
            "examples": [{"conversation_id": "only_one", "user_turns": ["I meant the other one"]}],
        },
    }
    _write_fail_points(tmp_path, records)

    # Monkeypatch the directed corpus out so fail_points' single example is
    # the entire pool for this dimension, forcing exhaustion after one call.
    import aurora_classroom as classroom_mod

    class _EmptyBridge:
        def samples_for_dimensions(self, dimensions, limit=3):
            return {d: [] for d in dimensions}

    orig = classroom_mod.get_directed_training_corpus_bridge
    classroom_mod.get_directed_training_corpus_bridge = lambda: _EmptyBridge()
    try:
        first = select_curriculum({}, n=1, state_dir=str(tmp_path))[0]
        second = select_curriculum({}, n=1, state_dir=str(tmp_path))[0]
    finally:
        classroom_mod.get_directed_training_corpus_bridge = orig

    assert first[2] == "real_failure_example:only_one"
    # Wrapped around instead of degrading to generic.
    assert second[2] == "real_failure_example:only_one"
