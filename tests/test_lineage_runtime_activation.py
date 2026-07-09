# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for a real data-loss bug found while investigating why
dev_index stayed pinned near its floor across every scheduled autonomous
run: _deep_merge() in aurora_internal/aurora_lineage_runtime_activation.py
only handled dict/dict, list/list, bool/bool, and number/number merges.
When the existing value was a live object (e.g. systems['genealogy']'s
ConstraintGenealogyLogger, already restored with its real persisted
abilities/links earlier in boot) and the incoming value was a plain dict
from a stored ability-lineage manifest, it fell through to `return right`,
silently discarding the object and replacing it with the manifest's bare
dict on every single boot.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.aurora_lineage_runtime_activation import _deep_merge


class _FakeLiveObject:
    """Stands in for a real engine/logger instance already installed in
    systems -- has its own real state that must survive a merge."""

    def __init__(self):
        self.abilities = {f"a{i}": i for i in range(50)}
        self.links = {f"l{i}": i for i in range(5)}


def test_object_vs_dict_preserves_existing_object_state():
    live = _FakeLiveObject()
    manifest_payload = {"cross_modal_lanes": ["tonal_colour", "texture_form"]}

    result = _deep_merge(live, manifest_payload)

    assert result is live, "the real object must survive, not get replaced by the manifest dict"
    assert len(result.abilities) == 50, "existing abilities must not be discarded"
    assert len(result.links) == 5, "existing links must not be discarded"
    assert result.cross_modal_lanes == ["tonal_colour", "texture_form"], (
        "the manifest's own intent must still land, just without destroying the object"
    )


def test_object_vs_dict_merges_nested_dict_attr_instead_of_replacing():
    live = _FakeLiveObject()
    live.settings = {"a": 1}
    result = _deep_merge(live, {"settings": {"b": 2}})

    assert result.settings == {"a": 1, "b": 2}


def test_none_vs_dict_still_returns_the_dict():
    # No live object to preserve -- this must keep working exactly as before.
    assert _deep_merge(None, {"x": 1}) == {"x": 1}


def test_dict_vs_dict_unaffected():
    assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_list_vs_list_unaffected():
    assert _deep_merge([1, 2], [2, 3]) == [1, 2, 3]


def test_bool_vs_bool_unaffected():
    assert _deep_merge(False, True) is True


def test_number_vs_number_unaffected():
    assert _deep_merge(3, 7) == 7


def test_string_left_falls_back_to_replace_not_setattr():
    # Strings aren't "live objects" -- must not attempt setattr on them.
    assert _deep_merge("old", {"a": 1}) == {"a": 1}


if __name__ == "__main__":
    test_object_vs_dict_preserves_existing_object_state()
    test_object_vs_dict_merges_nested_dict_attr_instead_of_replacing()
    test_none_vs_dict_still_returns_the_dict()
    test_dict_vs_dict_unaffected()
    test_list_vs_list_unaffected()
    test_bool_vs_bool_unaffected()
    test_number_vs_number_unaffected()
    test_string_left_falls_back_to_replace_not_setattr()
    print("All _deep_merge regression tests passed.")
