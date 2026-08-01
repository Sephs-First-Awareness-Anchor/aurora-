# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-01): SemanticIntentionBridge
prefers the live upward-pass parse (systems['_active_turn_state'].parsed/
salient_concepts/raw_text) over ThoughtState's diagnostic prose when
building spoken content keywords, so internal bookkeeping vocabulary
('sedi', 'ambient', 'constraint', ...) and raw direct-address words
("Hello Aurora") stop leaking into composed output as if they were the
topic. Ported from auroragenerativecommunicationpatched.zip's patched
aurora_semantic_intention_bridge.py verbatim; the file's own logic
already matched this repo's TurnUnderstandingState shape (.parsed,
.salient_concepts, .raw_text), but depended on a systems['_active_turn_
state'] key that did not exist anywhere in this repo -- added as a
companion wiring line in aurora.py's _run_reasoning_pipeline, right
alongside the existing systems["_last_pipeline_state"] assignment.
"""
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_semantic_intention_bridge import SemanticIntentionBridge, EXTRACTION_NOISE


def _thought_state(unified="", self_app="", dominant_thread=None):
    return types.SimpleNamespace(
        unified_interpretation=unified,
        self_application=self_app,
        dominant_thread=dominant_thread or [],
        axis_fingerprint=[],
        unresolved=[],
        confidence=0.5,
    )


def _live_state(topic_words=None, entities=None, salient=None, topic="", raw_text=""):
    return types.SimpleNamespace(
        parsed={"topic_words": topic_words or [], "entities": entities or [], "topic": topic},
        salient_concepts=salient or [],
        raw_text=raw_text,
    )


def _ctx(what_it_is_operating_on="", process_type=None):
    return types.SimpleNamespace(
        what_it_is_operating_on=what_it_is_operating_on, process_type=process_type,
    )


def test_wiring_stores_state_in_systems_active_turn_state():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    assert 'systems["_active_turn_state"] = state' in source


def test_extraction_noise_includes_new_bookkeeping_terms():
    for word in ("sedi", "ambient", "constraint", "unresolved", "tension", "session"):
        assert word in EXTRACTION_NOISE


def test_live_parsed_topic_words_preferred_over_diagnostic_prose():
    bridge = SemanticIntentionBridge()
    thought_state = _thought_state(unified="axis tick process braid forming lane thread")
    live_state = _live_state(topic_words=["medication", "dosage"], raw_text="will this medication work")
    systems = {"_active_turn_state": live_state}

    intention = bridge.extract(thought_state, systems=systems)

    assert "medication" in intention.content_keywords
    assert "dosage" in intention.content_keywords
    # Diagnostic prose words must not leak in once a live parse exists.
    assert "axis" not in intention.content_keywords
    assert "forming" not in intention.content_keywords


def test_raw_direct_address_words_filtered_when_parser_did_not_retain_them():
    bridge = SemanticIntentionBridge()
    thought_state = _thought_state(
        dominant_thread=[_ctx(what_it_is_operating_on="hello aurora will this medication work")],
    )
    live_state = _live_state(
        topic_words=["medication"],
        raw_text="hello aurora will this medication work",
    )
    systems = {"_active_turn_state": live_state}

    intention = bridge.extract(thought_state, systems=systems)

    assert "medication" in intention.content_keywords
    assert "hello" not in intention.content_keywords
    assert "aurora" not in intention.content_keywords


def test_internal_bookkeeping_words_filtered_from_fallback_diagnostic_prose():
    bridge = SemanticIntentionBridge()
    thought_state = _thought_state(
        unified="sedi ambient recalled linguistic predictive constraint session tension",
    )
    systems = {}  # no live_state -- exercises the old fallback path

    intention = bridge.extract(thought_state, systems=systems)

    assert intention.content_keywords == []


def test_axis_telemetry_tokens_filtered_even_when_parsed_as_topic_words():
    bridge = SemanticIntentionBridge()
    thought_state = _thought_state()
    live_state = _live_state(topic_words=["x050", "t012", "medication"])
    systems = {"_active_turn_state": live_state}

    intention = bridge.extract(thought_state, systems=systems)

    assert "medication" in intention.content_keywords
    assert "x050" not in intention.content_keywords
    assert "t012" not in intention.content_keywords


def test_no_active_turn_state_falls_back_to_old_diagnostic_path_without_crashing():
    bridge = SemanticIntentionBridge()
    thought_state = _thought_state(
        unified="considering the medication dosage carefully",
        dominant_thread=[_ctx(what_it_is_operating_on="reviewing patient history")],
    )
    intention = bridge.extract(thought_state, systems=None)

    assert "medication" in intention.content_keywords
    assert "dosage" in intention.content_keywords


def test_real_boot_semantic_bridge_wiring_does_not_crash_live_turn():
    """Real end-to-end confirmation: boot Aurora and run a real turn --
    systems['_active_turn_state'] must be populated with the turn's own
    TurnUnderstandingState, and the live pipeline must not crash."""
    import shutil
    import tempfile
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_semantic_bridge_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result = A.process_external_user_turn(systems, "Hello Aurora, will this medication definitely work?")
        assert result, "live turn produced no result"

        active_state = systems.get("_active_turn_state")
        assert active_state is not None
        assert "medication" in active_state.raw_text.lower()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
