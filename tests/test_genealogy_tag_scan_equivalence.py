# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The genealogy tag scans were rewritten to run in C (measured hot spots).
They must return exactly what the original Python formulations returned."""
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G

_PREFIXES = (
    "origin_", "root_slot:", "operation_lineage:", "seed_lineage:",
    "operator_action:", "purpose_lane:", "dominant_constraint:",
)
_TAGS = [
    "origin_kind:code", "root_slot:abc", "keep_me", "operator_action:x",
    "seed_lineage_extra", "dominant_constraint:A", "plain", "purpose_lane:Q",
    "origin_", "", "operation_lineage:", 7,
]


def _old_filter(tags):
    return [str(t) for t in tags
            if not any(str(t).startswith(p) for p in _PREFIXES)]


def _new_filter(tags):
    return [str(t) for t in tags if not str(t).startswith(_PREFIXES)]


def _old_last(tags, prefix, default=None):
    wanted = str(prefix or "")
    if wanted and not wanted.endswith(":"):
        wanted += ":"
    for raw in reversed(list(tags or [])):
        tag = str(raw)
        if tag.startswith(wanted):
            return tag[len(wanted):]
    return default


def test_prefix_filter_matches_the_generator_form():
    assert _new_filter(_TAGS) == _old_filter(_TAGS)
    assert _new_filter([]) == _old_filter([]) == []


def test_last_tag_value_matches_the_original_on_every_shape():
    cases = [
        (("a:1", "b:2", "a:3"), "a"), (["a:1"], "a:"), ((), "a"), (None, "a"),
        ([1, 2, "n:5"], "n"), (("x:1",), ""), (["a:1", "a:2"], "missing"),
        (("a:1", "b:2"), None),
    ]
    for tags, prefix in cases:
        assert G._last_tag_value(tags, prefix, "D") == _old_last(tags, prefix, "D")
    # An iterator cannot be reversed in place; it must still work.
    assert G._last_tag_value(iter(["x:1", "x:2"]), "x") == "2"


def test_last_tag_value_with_mixed_and_non_string_tags():
    for tags in (["a:1", 5, "a:2", b"a:9"], [7, 8], ["a:1", None], (b"a:1",)):
        assert G._last_tag_value(tags, "a", "D") == _old_last(tags, "a", "D")
