# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Crest-Compression Placeholder-Leak Repair.

_meaning_text_is_grounded() (aurora.py) previously enforced a narrower
denylist (only "learned:") than the stricter, separately-maintained
_research_summary_is_usable(), which additionally rejected
"from_definition:", "from meaning:", "internal:", "pending:", "research:",
and "context:". Since _meaning_text_is_grounded() is the guard that
actually gates crest compression (_compress_at_crest ->
_grounded_topic_contribution), any concept node whose sole definition was
seeded with one of the stricter-list-only prefixes could pass the weak
guard and be compressed straight into state.response_content with
response_src == "crest_compression" -- an internal bookkeeping label
spoken as if it were real meaning.

The fix: both guards now check against one shared module-level constant,
_PLACEHOLDER_DEFINITION_PREFIXES, so they enforce the same invariant and
cannot drift apart again.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

import aurora as A  # noqa: E402
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb  # noqa: E402


# ---------------------------------------------------------------------------
# _meaning_text_is_grounded() direct coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prefix", A._PLACEHOLDER_DEFINITION_PREFIXES)
def test_meaning_text_is_grounded_rejects_each_placeholder_prefix(prefix):
    assert A._meaning_text_is_grounded(f"{prefix}aurorabloom") is False
    # Case-insensitivity, since the guard lowercases before comparing.
    assert A._meaning_text_is_grounded(f"{prefix.upper()}aurorabloom") is False


def test_meaning_text_is_grounded_still_rejects_the_exact_token_set():
    """Requirement 4: the pre-existing exact-token denylist must survive
    alongside the new prefix check, not be replaced by it."""
    for token in ("unknown", "n/a", "tbd", "pending", "is:**", "works:**"):
        assert A._meaning_text_is_grounded(token) is False


def test_meaning_text_is_grounded_accepts_real_content():
    """A guard tightened against placeholders must not start rejecting
    genuine grounded meaning, including content that legitimately contains
    a colon."""
    assert A._meaning_text_is_grounded("a luminous cloud of ionized gas") is True
    assert A._meaning_text_is_grounded("Note: this only applies at night") is True


def test_research_summary_is_usable_shares_the_same_constant_object():
    """Structural confirmation that _research_summary_is_usable() no longer
    carries its own separate hardcoded tuple (the drift this directive
    closes) -- it must reference the same _PLACEHOLDER_DEFINITION_PREFIXES
    object _meaning_text_is_grounded() uses."""
    import inspect
    source = inspect.getsource(A._research_summary_is_usable)
    assert "_PLACEHOLDER_DEFINITION_PREFIXES" in source
    assert '"from_definition:"' not in source


# ---------------------------------------------------------------------------
# _grounded_topic_contribution() end-to-end: a developed node whose sole
# definition is a placeholder must fall through to None (honest abstain),
# never reach crest compression.
# ---------------------------------------------------------------------------

def _systems_with_seeded_node(concept: str, definition_text: str) -> dict:
    web = OntologicalWeb()
    node = web.add_node(concept, role="noun", meaning=definition_text)
    # Force past the "actually developed" gate independent of the single
    # seeded definition's own confidence-driven depth contribution --
    # mirrors the directive's "artificially seed one OETS node" live-
    # verification step, applied at the unit level.
    node.ontological_depth = 0.9

    class _OETS:
        pass

    class _Perception:
        pass

    oets = _OETS()
    oets.web = web
    perception = _Perception()
    perception.oets = oets
    return {"perception": perception}


@pytest.mark.parametrize("prefix", A._PLACEHOLDER_DEFINITION_PREFIXES)
def test_grounded_topic_contribution_falls_through_on_placeholder_definition(prefix):
    concept = "aurorabloom"
    systems = _systems_with_seeded_node(concept, f"{prefix}{concept}")
    result = A._grounded_topic_contribution(f"what is {concept}?", systems)
    assert result is None


def test_grounded_topic_contribution_still_returns_content_for_real_definitions():
    """Negative control: the fix must not make a genuinely developed,
    grounded concept fall through too."""
    concept = "aurorabloom"
    systems = _systems_with_seeded_node(
        concept, "a slow release of light across the surface field"
    )
    result = A._grounded_topic_contribution(f"what is {concept}?", systems)
    assert result is not None
    assert result.get("source") == "grounded_concept"


# ---------------------------------------------------------------------------
# Live full-turn regression: live verification during this directive found
# that _compress_at_crest / _grounded_topic_contribution was NOT the only
# path a placeholder-prefixed definition could reach spoken output through.
# QuasiArchReasoner.reason() (two occurrences, both reading
# node.definitions[0] directly), _generate_perspective_from_core(), and the
# comprehension-response OETS-lookup step all read node.definitions[0]
# with their own narrower inline checks and never called
# _meaning_text_is_grounded() at all -- a genuinely different mechanism
# than the two guards this directive originally traced. Before this fix,
# driving a real turn through process_external_user_turn() for a node whose
# sole definition was "internal:aurorabloomxyz" delivered the literal
# string 'aurorabloomxyz. understanding, aurorabloomxyz.
# internal:aurorabloomxyz.' to resp_A.content. All four call sites now
# share the same _meaning_text_is_grounded() gate."""

@pytest.mark.parametrize("prefix", A._PLACEHOLDER_DEFINITION_PREFIXES)
def test_live_turn_never_delivers_a_placeholder_prefixed_definition(prefix, tmp_path):
    import shutil

    state_dir = tmp_path / "aurora_state"
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_dir)

    systems = A.boot_aurora(state_dir=str(state_dir), runtime_profile="surface", verbose=False)
    perception = systems.get("perception")
    web = perception.oets.web

    concept = "aurorabloomxyz"
    node = web.add_node(concept, role="noun", meaning=f"{prefix}{concept}")
    node.ontological_depth = 0.9
    node.definitions = [{"text": f"{prefix}{concept}", "source": "test", "confidence": 0.9, "timestamp": 0.0}]

    result = A.process_external_user_turn(systems, f"what is {concept}?")
    resp_a = getattr(result.get("resp_A"), "content", None) if isinstance(result, dict) else None
    delivered = str(resp_a or "")
    assert prefix not in delivered, f"placeholder prefix {prefix!r} leaked into delivered response: {delivered!r}"
