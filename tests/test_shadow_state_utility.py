# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 6 of 6.
Shadow state utility.

Covers: open_shadow_state() correctly isolates a copy, changes inside the
shadow never appear in the original state_dir until promote_shadow_deltas()
is called explicitly, and only the named keys move.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_shadow_state import (  # noqa: E402
    open_shadow_state,
    promote_shadow_deltas,
)


@pytest.fixture
def live_state_dir(tmp_path):
    state_dir = tmp_path / "aurora_state"
    state_dir.mkdir()
    (state_dir / "alpha.json").write_text('{"v": 1}')
    (state_dir / "beta.json").write_text('{"v": 1}')
    nested = state_dir / "nested"
    nested.mkdir()
    (nested / "gamma.json").write_text('{"v": 1}')
    return state_dir


def test_open_shadow_state_copies_and_cleans_up(live_state_dir):
    with open_shadow_state(str(live_state_dir)) as handle:
        assert handle.shadow_state_dir.exists()
        assert (handle.shadow_state_dir / "alpha.json").read_text() == '{"v": 1}'
        assert handle.shadow_state_dir != handle.live_state_dir
        scratch_root = handle.scratch_root
    assert not scratch_root.exists()  # cleaned up on exit


def test_open_shadow_state_raises_on_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        with open_shadow_state(str(tmp_path / "does_not_exist")):
            pass


def test_changes_inside_shadow_never_appear_in_original_until_promoted(live_state_dir):
    with open_shadow_state(str(live_state_dir)) as handle:
        (handle.shadow_state_dir / "alpha.json").write_text('{"v": 999}')
        (handle.shadow_state_dir / "new_file.json").write_text('{"v": "new"}')
        # The live dir must be untouched while inside the shadow.
        assert (live_state_dir / "alpha.json").read_text() == '{"v": 1}'
        assert not (live_state_dir / "new_file.json").exists()

    # Still untouched after the shadow is discarded (nothing was promoted).
    assert (live_state_dir / "alpha.json").read_text() == '{"v": 1}'
    assert not (live_state_dir / "new_file.json").exists()


def test_promote_shadow_deltas_moves_only_named_keys(live_state_dir):
    with open_shadow_state(str(live_state_dir)) as handle:
        (handle.shadow_state_dir / "alpha.json").write_text('{"v": 999}')
        (handle.shadow_state_dir / "beta.json").write_text('{"v": 999}')
        (handle.shadow_state_dir / "nested" / "gamma.json").write_text('{"v": 999}')

        promoted = promote_shadow_deltas(handle, ["alpha.json"])
        assert promoted == ["alpha.json"]

    # Only alpha.json was promoted -- beta.json and nested/gamma.json (both
    # also changed in the shadow) must remain at their ORIGINAL live values.
    assert (live_state_dir / "alpha.json").read_text() == '{"v": 999}'
    assert (live_state_dir / "beta.json").read_text() == '{"v": 1}'
    assert (live_state_dir / "nested" / "gamma.json").read_text() == '{"v": 1}'


def test_promote_shadow_deltas_supports_directories(live_state_dir):
    with open_shadow_state(str(live_state_dir)) as handle:
        (handle.shadow_state_dir / "nested" / "gamma.json").write_text('{"v": "changed"}')
        (handle.shadow_state_dir / "nested" / "delta.json").write_text('{"v": "added"}')
        promoted = promote_shadow_deltas(handle, ["nested"])
        assert promoted == ["nested"]

    assert (live_state_dir / "nested" / "gamma.json").read_text() == '{"v": "changed"}'
    assert (live_state_dir / "nested" / "delta.json").read_text() == '{"v": "added"}'


def test_promote_shadow_deltas_skips_keys_absent_from_shadow(live_state_dir):
    with open_shadow_state(str(live_state_dir)) as handle:
        promoted = promote_shadow_deltas(handle, ["does_not_exist.json"])
        assert promoted == []
    assert not (live_state_dir / "does_not_exist.json").exists()


def test_promote_shadow_deltas_never_deletes_unnamed_live_files(live_state_dir):
    """A blanket overwrite would remove alpha.json entirely if the shadow
    deleted it; promote_shadow_deltas() must never do a wholesale sync."""
    with open_shadow_state(str(live_state_dir)) as handle:
        os.remove(handle.shadow_state_dir / "alpha.json")
        promoted = promote_shadow_deltas(handle, ["beta.json"])
        assert promoted == ["beta.json"]
    assert (live_state_dir / "alpha.json").exists()  # never touched, still present
