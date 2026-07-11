# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the classroom-curriculum staleness fix (2026-07-11):
DirectedTrainingCorpusBridge._load_cache() required an exact size/mtime
signature match against aurora_internal/train.txt to trust its own cache.
train.txt is a 206MB gitignored file not shipped to the scheduled CI
runner (or this dev environment) -- so the signature check always failed
against a nonexistent source file, silently discarding the real,
already-committed 24-samples-per-dimension cache
(aurora_state/training_corpus/directed_prompt_cache.json) and rebuilding
an empty one every time. The bridge is now the fallback data source
select_curriculum() (aurora_classroom.py) uses once fail_points.json's own
examples are exhausted for a dimension -- with the cache silently empty,
that fallback produced nothing, and staleness went unnoticed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.aurora_directed_training_corpus import DirectedTrainingCorpusBridge


def test_missing_source_file_still_trusts_existing_cache(tmp_path):
    corpus_path = tmp_path / "train.txt"  # deliberately never created
    cache_path = tmp_path / "directed_prompt_cache.json"
    cache_path.write_text(json.dumps({
        "source_signature": {"size": 999999999, "mtime": 123456789},
        "dimensions": {
            "contradiction_handling": ["a real conversational snippet about conflicting claims"],
        },
    }))

    bridge = DirectedTrainingCorpusBridge(
        corpus_path=str(corpus_path), cache_path=str(cache_path),
    )
    samples = bridge.samples_for_dimensions(["contradiction_handling"], limit=3)

    assert samples["contradiction_handling"] == [
        "a real conversational snippet about conflicting claims"
    ]


def test_present_source_file_still_requires_signature_match(tmp_path):
    """When train.txt genuinely IS present, a stale cache (wrong
    size/mtime) must still be rejected and rebuilt -- the loosened check
    only applies when the source is absent, not as a blanket bypass."""
    corpus_path = tmp_path / "train.txt"
    corpus_path.write_text("fresh corpus content with a contradiction to find\n" * 5)
    cache_path = tmp_path / "directed_prompt_cache.json"
    cache_path.write_text(json.dumps({
        "source_signature": {"size": 1, "mtime": 1},  # deliberately wrong
        "dimensions": {
            "contradiction_handling": ["stale cached snippet that should NOT be trusted"],
        },
    }))

    bridge = DirectedTrainingCorpusBridge(
        corpus_path=str(corpus_path), cache_path=str(cache_path),
    )
    samples = bridge.samples_for_dimensions(["contradiction_handling"], limit=3)

    assert "stale cached snippet that should NOT be trusted" not in samples.get(
        "contradiction_handling", []
    )


def test_real_committed_cache_has_data_for_known_dimensions():
    """The actual repo-committed cache must be usable as-is in an
    environment where train.txt (gitignored, 206MB) is absent -- the exact
    real-world case this fix addresses."""
    from aurora_internal.aurora_directed_training_corpus import (
        get_directed_training_corpus_bridge,
    )
    bridge = get_directed_training_corpus_bridge()
    samples = bridge.samples_for_dimensions(["contradiction_handling"], limit=3)
    assert samples.get("contradiction_handling"), (
        "real committed directed_prompt_cache.json should yield real samples "
        "even without aurora_internal/train.txt present"
    )
