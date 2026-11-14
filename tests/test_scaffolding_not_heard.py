#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_scaffolding_not_heard.py -- FIX-A127.

Curriculum and bookkeeping text is not language heard from a speaker.  Measured
on live turns: directed-training wrappers, the pressure router's diagnostic
label, and her own appended "[Internal: ...]" note were all ingested as heard
language (vocabulary, structure, OETS).  Nothing is added to her: the wrapper is
derived from the corpus's own template tables, and the markers are recognized,
not rewritten.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_directed_training_corpus as corpus
from aurora_expression_perception import strip_internal_annotation


def test_every_template_wrapper_is_removed_and_the_material_kept():
    tables = {**corpus._PROMPT_TEMPLATES, **corpus._FOLLOWUP_TEMPLATES}
    for template in tables.values():
        material = "the fence posts rotted behind the barn"
        assert corpus.without_scaffold(template.format(snippet=material)) == material


def test_text_that_is_not_a_template_is_returned_unchanged():
    spoken = "The fence posts rotted behind the barn."
    assert corpus.without_scaffold(spoken) == spoken
    assert corpus.without_scaffold("") == ""


def test_internal_note_only_stripped_from_the_very_end():
    assert strip_internal_annotation("Thanks. [Internal: reasoning now]") == "Thanks."
    quoted = "She wrote [Internal: x] on the card and left."
    assert strip_internal_annotation(quoted) == quoted


def test_constraint_emitter_delegates_to_the_same_rule():
    from aurora_constraint_emission import ConstraintEmitter  # noqa: F401
    import inspect, aurora_constraint_emission as m
    src = inspect.getsource(m)
    assert "strip_internal_annotation(text or \"\")" in src


def test_pressure_routing_label_is_a_recognized_transport_marker():
    import aurora_simulation_engine as sim
    stripped, source = sim._strip_internal_transport_marker("[PRESSURE ROUTING] gap signal at 0.2")
    assert source == "pressure" and "PRESSURE" not in stripped


def test_internal_flag_perceives_but_does_not_learn(tmp_path, monkeypatch):
    from aurora_expression_perception import ExpressionPerceptionEngine
    eng = ExpressionPerceptionEngine(state_dir=str(tmp_path))
    seen = []
    monkeypatch.setattr(eng.composer, "absorb", lambda t, tone="neutral": seen.append(t))
    before = eng.total_perceptions
    eng.ingest_interaction({"input": "Zymurgical flibbertigibbets wander endlessly.", "internal": True}, mode="sim")
    assert eng.total_perceptions == before + 1 and seen == []
    eng.ingest_interaction({"input": "The posts were completely rotten. [Internal: noting this]"}, mode="gateway")
    assert seen == ["The posts were completely rotten."]


def test_spec_candidate_with_pressure_label_is_marked_internal():
    import types
    import aurora_simulation_engine as sim
    fake = types.SimpleNamespace()
    topic = sim.SimulationSession._shape_topic_for_turn(
        fake,
        {"prompt_candidates": ["[PRESSURE ROUTING] knowledge_gap signal at 0.21 — training needed on x."]},
        0, {"behavior_modes": {}}, [])
    assert topic["episode_source"] == "pressure"
    assert not topic["prompt"].startswith("[PRESSURE")
    plain = sim.SimulationSession._shape_topic_for_turn(
        fake, {"prompt_candidates": ["Does the fence hold?"], "episode_source": "ordinary"},
        0, {"behavior_modes": {}}, [])
    assert plain["episode_source"] == "ordinary" and plain["prompt"] == "Does the fence hold?"


def test_bridge_command_string_splits_action_and_token():
    import importlib.util, pathlib
    path = pathlib.Path("flutter_app/android/app/src/main/python/aurora_bridge.py")
    src = path.read_text()
    start = src.index("def strata_link_transfer_cmd")
    block = src[start:src.index("\ndef ", start + 10)]
    seen = []
    ns = {"strata_link_transfer": lambda a, t="": seen.append((a, t)) or "{}"}
    exec(block, ns)
    ns["strata_link_transfer_cmd"]("handoff_claim: tok123 ")
    ns["strata_link_transfer_cmd"]("seed")
    assert seen == [("handoff_claim", "tok123"), ("seed", "")]
