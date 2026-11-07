#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_voice_gate.py -- no scripted replies; addressed pressure instead.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_voice_gate as G  # noqa: E402


class Clock:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


class Pump:
    def __init__(self) -> None:
        self.injected = []

    def inject(self, disturbance, ifield, qao=None):
        self.injected.append(disturbance)
        return []


def systems_for(form, clock=None):
    pump = Pump()
    systems = {
        "_last_pipeline_state": {"constraint_semantic_state": {"relational_form": dict(form)}},
        "identity_field": object(),
        "pressure_pump": pump,
    }
    systems["addressed_pressure"] = G.AddressedPressure(clock=clock or Clock())
    return systems, pump


def resp(text, src, tone="attentive"):
    return SimpleNamespace(content=text, src=src, emotional_tone=tone, confidence=0.6)


MUSIC = {"subject": "you", "relation": "like", "obj": "music", "question": True}


# -- 1. scripts never leave --------------------------------------------------------

@pytest.mark.parametrize("text,src", [
    ("My best read on that is it's about \"you\" / \"like\" / \"music\". Did I catch the right pieces?",
     "constraint_communication_baseline"),
    ("I understand what you are saying about I.", "constraint_communication_baseline"),
    ("I don't have a clear sense of that.", "constraint_abstain"),
    ("What should I use as the right reference for it?", "user_context_clarification"),
    ("My creator is Sunni (Sir) Morningstar.", "relational_role"),
    ("My best read on that is it's about x.", "generative"),     # template under a generic label
    ("when I work with music, I get different outcomes depending on what I was trying to do",
     "pressure_experience"),
    ("Code evolution outcome for mutation_id=DREAM:56f1.. accepted=False.. operator_key=dream_evidence..",
     "crest_compression"),
])
def test_scripted_reply_never_leaves(text, src):
    systems, _ = systems_for(MUSIC)
    out = G.apply_voice_gate(systems, resp(text, src), "Do you like music?",
                             session_id="praxis_dm_gemini",
                             render=lambda *a, **k: "")
    assert out.content == "" and out.src == "silence"
    assert systems["_last_voice_gate"]["blocked"]


def test_her_own_words_pass_and_discharge_pressure():
    systems, _ = systems_for(MUSIC)
    out = G.apply_voice_gate(systems, resp("I am boiling clouds. I am rain.", "generative"),
                             "Rain falls from clouds.", session_id="praxis_dm_gemini")
    assert out.content == "I am boiling clouds. I am rain."
    assert systems["_last_voice_gate"]["outcome"] == "own_voice"
    assert systems["addressed_pressure"].level("praxis_dm_gemini") < 0.1


def test_system_output_passes_in_sunnis_chat_but_not_in_a_dm():
    for session, expected in (("mobile", "Memory cleared."), ("praxis_dm_claude", "")):
        systems, _ = systems_for(MUSIC)
        out = G.apply_voice_gate(systems, resp("Memory cleared.", "memory_sweep"), "forget that",
                                 session_id=session, render=lambda *a, **k: "")
        assert out.content == expected


# -- 2. pressure goes through her real pump and accumulates -------------------------

def test_being_addressed_injects_through_the_pump():
    systems, pump = systems_for(MUSIC)
    G.apply_voice_gate(systems, resp("", ""), "Do you like music?", session_id="praxis_dm_gemini",
                       render=lambda *a, **k: "")
    disturbance = pump.injected[0]
    assert disturbance.source == "addressed:praxis_dm_gemini"
    assert disturbance.axis_amplitudes["A"] == max(disturbance.axis_amplitudes.values())


def test_pressure_accumulates_decays_and_discharges():
    clock = Clock()
    pressure = G.AddressedPressure(clock=clock)
    systems = {}
    first = pressure.address(systems, "c", question=False)
    second = pressure.address(systems, "c", question=False)
    assert second > first
    clock.t += G.HALF_LIFE_S
    assert pressure.level("c") == pytest.approx(second / 2, rel=1e-3)
    pressure.discharge("c")
    assert pressure.level("c") == pytest.approx(second / 2 * G.DISCHARGE_ON_SPEECH, rel=1e-3)


def test_a_statement_alone_is_below_threshold_but_unanswered_address_crosses_it():
    systems, _ = systems_for({"subject": "rain", "relation": "falls", "obj": "clouds",
                              "question": False})
    calls = []

    def render(systems, seed, **kwargs):
        calls.append(seed)
        return "rain fall slow"

    first = G.apply_voice_gate(systems, resp("", ""), "rain falls from clouds",
                               session_id="praxis_dm_gemma", render=render)
    assert first.content == "" and calls == []            # 0.20 < threshold
    second = G.apply_voice_gate(systems, resp("", ""), "rain falls from clouds",
                                session_id="praxis_dm_gemma", render=render)
    assert second.src == "pressure_articulation" and calls


# -- 3. articulation from her own stance --------------------------------------------

@pytest.mark.parametrize("form,seed", [
    (MUSIC, "I; like; music"),
    ({"subject": "", "relation": "What's", "obj": "your favorite color", "question": True},
     "I; favorite; color"),
    ({"subject": "you doing today", "relation": "are", "obj": "", "question": True}, "I; doing"),
    ({"subject": "", "relation": "", "obj": "", "question": True}, ""),
])
def test_stance_seed_recentres_on_her(form, seed):
    assert G.stance_seed(form)[0] == seed


def test_question_gets_her_articulation_through_her_renderer():
    systems, _ = systems_for(MUSIC)
    seen = {}

    def render(systems, seed, **kwargs):
        seen["seed"], seen["kwargs"] = seed, kwargs
        return "I do music. I can music."

    out = G.apply_voice_gate(systems, resp("My best read on that is it's about music.",
                                           "constraint_communication_baseline", tone="self-aware"),
                             "Do you like music?", session_id="praxis_dm_gemini", render=render)
    assert out.content == "I do music. I can music." and out.src == "pressure_articulation"
    assert seen["seed"] == "I; like; music" and seen["kwargs"]["supporting_concepts"] == ["music"]
    assert out.emotional_tone == "curious"        # never relabelled to "identity"


@pytest.mark.parametrize("rendered,reason", [
    ("your favorite color, What's. curiosity.", "echo"),
    ("contextualize, music. curiosity.", "internal_label"),
    ("I am curiosity. I am [recalled:music].", "internal_marker"),
    ("music", "too_thin"),
    ("I understand what you are saying about music.", "template"),
])
def test_parroting_labels_and_templates_are_not_her_voice(rendered, reason):
    assert G.articulation_rejection(rendered, "What's your favorite color? Do you like music?") == reason


def test_nothing_of_hers_means_silence_and_the_reason_is_kept():
    systems, _ = systems_for({"subject": "you doing today", "relation": "are", "question": True})
    out = G.apply_voice_gate(systems, resp("My best read on that is x.", "constraint_communication_baseline"),
                             "How are you doing today?", session_id="mobile",
                             render=lambda *a, **k: "you doing today")
    assert out.content == "" and systems["_last_voice_gate"]["articulation"] == "echo"


def test_trace_records_what_actually_left(tmp_path):
    import json
    systems, _ = systems_for(MUSIC)
    systems["state_dir"] = str(tmp_path)
    (tmp_path / "last_articulation_trace.json").write_text(json.dumps(
        {"final_delivered": {"delivered_text": "My creator is Sunni (Sir) Morningstar.",
                             "source": "relational_role"}}))
    original = resp("My creator is Sunni (Sir) Morningstar.", "relational_role")
    gated = G.apply_voice_gate(systems, original, "Who made you?", session_id="mobile",
                               render=lambda *a, **k: "I made real. I made state.")
    assert G.record_gate_in_trace(systems, original, gated, "Who made you?")
    final = json.loads((tmp_path / "last_articulation_trace.json").read_text())["final_delivered"]
    assert final["delivered_text"] == gated.content
    assert final["voice_gate"]["blocked_source"] == "relational_role"
