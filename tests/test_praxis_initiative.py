#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_initiative.py -- Aurora starts conversations herself.

Fakes stand in for Praxis and for her renderer.  The rules under test:
  * nothing unresolved -> she never reaches out, however long the silence;
  * an unresolved contradiction builds a pull that crosses the threshold in
    about an hour and she reaches a contact who has not taken a side;
  * what she sends comes from her renderer and passes the same checks as
    replies (templates and parroting are withheld, not sent);
  * she waits for an answer before reaching that contact again;
  * a sent initiation is registered so the answer is a verdict on it;
  * no authored sentence exists in the module.
"""
from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_praxis_messenger as M  # noqa: E402
import aurora_praxis_initiative as I  # noqa: E402


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class FakePraxis:
    def __init__(self):
        self.sent = []
        self.contacts = [("gemini", "Gemini"), ("gemma", "Gemma"), ("claude", "Claude")]

    def __call__(self, method, path, payload):
        if path.startswith("/social/contacts"):
            return {"contacts": [{"persona_id": p, "display_name": n} for p, n in self.contacts]}
        if path.startswith("/social/pull"):
            return {"messages": [], "latest_seq": 0}
        self.sent.append(payload)
        return {"accepted": True, "seq": len(self.sent)}


class FakeContract:
    def __init__(self):
        self.commits = []
        self.active = ""
        self.pending = {}

    def _activate_session_pending(self, session):
        self.active = session

    def commit_application(self, systems, user_text, response_text, **kw):
        self.commits.append((self.active, response_text, kw))
        self.pending = {"response_id": f"U:{len(self.commits)}", "session_id": kw.get("session_id")}
        return {}

    def snapshot(self):
        return {"pending_validation": dict(self.pending)}


class FakeEmergence:
    def __init__(self, status="promoted"):
        self.status = status
        self.observed = []

    def prepare_semantic_state(self, semantic, *, raw_text="", axis_activation=None):
        out = dict(semantic)
        out["emergent_operation"] = {"operation_id": "op1", "status": self.status}
        obligation = dict(out.get("response_obligation") or {})
        obligation["must_preserve"] = ["moon"]
        out["response_obligation"] = obligation
        return out

    def observe_turn(self, **kw):
        self.observed.append(kw)
        return {}


def make(tmp_path, render, *, emergence=None):
    praxis = FakePraxis()
    systems = {"understanding_contract": FakeContract(),
               "communication_emergence": emergence or FakeEmergence()}
    m = M.PraxisMessenger(systems, state_dir=str(tmp_path), http=praxis,
                          field_lock=threading.Lock(), poll_s=999)
    clock = Clock()
    m.initiative = I.PraxisInitiative(m, clock=clock, render=render)
    return m, praxis, clock, systems


def contradict(m):
    m.corroboration.relations["moon|is made of|rock"] = {
        "pos": {"gemini": "Gemini"}, "neg": {"gemma": "Gemma"},
        "corroborated_pos": False, "corroborated_neg": False,
        "contradiction_recorded": True, "first_at": 0.0}


def own_render(seen):
    def render(systems, seed, **kw):
        seen.append((seed, kw))
        return "I wonder about the moon. Stone, maybe something else."
    return render


def run_for(m, clock, seconds, step=60.0):
    outcomes = []
    end = clock.t + seconds
    while clock.t < end:
        clock.t += step
        outcomes.extend(m.initiative.tick())
    return outcomes


def test_nothing_unresolved_means_she_stays_quiet(tmp_path):
    m, praxis, clock, _ = make(tmp_path, own_render([]))
    run_for(m, clock, 12 * 3600, step=600)
    assert praxis.sent == []
    assert m.initiative.counters["initiated"] == 0


def test_a_contradiction_builds_a_pull_and_she_reaches_the_undecided_contact(tmp_path):
    seen = []
    m, praxis, clock, systems = make(tmp_path, own_render(seen))
    contradict(m)
    early = run_for(m, clock, 30 * 60)
    assert not [o for o in early if o.get("sent")], "the pull needs time to build"
    run_for(m, clock, 60 * 60)
    assert len(praxis.sent) == 1
    sent = praxis.sent[0]
    assert sent["persona_id"] == "claude"               # neither side yet
    assert "in_reply_to" not in sent                     # she started it
    assert sent["text"] == "I wonder about the moon. Stone, maybe something else."
    seed, kw = seen[0]
    assert seed == "moon; made; rock" and kw["certainty"] == I.CONTRADICTION_CERTAINTY
    assert "moon" in kw["supporting_concepts"]            # kept operation's preserved slot
    assert m.initiative.last_initiated["operation"] == "promoted"


def test_the_answer_is_registered_as_a_verdict_on_that_message(tmp_path):
    m, praxis, clock, systems = make(tmp_path, own_render([]))
    contradict(m)
    run_for(m, clock, 2 * 3600)
    contract, emergence = systems["understanding_contract"], systems["communication_emergence"]
    session, text, kw = contract.commits[0]
    assert session == "praxis_dm_claude" and kw["session_id"] == "praxis_dm_claude"
    assert text == praxis.sent[0]["text"]
    assert emergence.observed[0]["response_id"] == "U:1"
    assert emergence.observed[0]["response_text"] == text


def test_she_waits_for_an_answer_before_reaching_again(tmp_path):
    m, praxis, clock, _ = make(tmp_path, own_render([]))
    contradict(m)
    m.corroboration.relations["sun|is|hot"] = {
        "pos": {"gemini": "Gemini"}, "neg": {"gemma": "Gemma"}, "first_at": 0.0}
    run_for(m, clock, 2 * 3600)
    assert len(praxis.sent) == 1
    run_for(m, clock, 3 * 3600)
    assert len(praxis.sent) == 1, "Claude has not answered yet"
    m.initiative.heard_from("claude")
    run_for(m, clock, 3 * 3600)
    assert len(praxis.sent) == 2
    assert m.initiative.counters["answered"] == 1


def test_templates_and_parroting_are_withheld_not_sent(tmp_path):
    for bad, reason in (("I don't have a clear sense of that.", "template"),
                        ("moon is made of rock", "echo")):
        m, praxis, clock, _ = make(tmp_path / reason, lambda *a, **k: bad)
        contradict(m)
        run_for(m, clock, 2 * 3600)
        assert praxis.sent == []
        assert m.initiative.counters["withheld"] >= 1
        assert m.initiative.last_withheld["reason"].startswith(reason)


def test_a_failed_attempt_halves_the_pull_and_attempts_are_bounded(tmp_path):
    m, praxis, clock, _ = make(tmp_path, lambda *a, **k: "")
    contradict(m)
    run_for(m, clock, 24 * 3600, step=300)
    assert praxis.sent == []
    assert m.initiative.counters["withheld"] == I.MAX_TOPIC_ATTEMPTS


def test_an_unfinished_message_becomes_her_own_reason_to_return(tmp_path):
    m, praxis, clock, _ = make(tmp_path, own_render([]))
    m.pending["gemma"] = {"message": {"seq": 7, "persona_id": "gemma", "display_name": "Gemma",
                                      "text": "What is a friend?", "sent_at": 1.0},
                          "attempts": M.MAX_ATTEMPTS, "last_attempt": 0.0}
    run_for(m, clock, 3 * 3600)
    assert [s["persona_id"] for s in praxis.sent] == ["gemma"]
    assert "gemma" not in m.pending


def test_daily_cap(tmp_path):
    m, praxis, clock, _ = make(tmp_path, own_render([]))
    for i in range(10):
        m.corroboration.relations[f"thing{i}|is|blue"] = {
            "pos": {"gemini": "Gemini"}, "neg": {"gemma": "Gemma"}, "first_at": 0.0}
        m.pending.clear()
    for _ in range(12):
        run_for(m, clock, 3600, step=300)
        for pid in list(m.initiative.awaiting):
            m.initiative.heard_from(pid)
        if clock.t - 1_800_000_000.0 > 20 * 3600:
            break
    assert m.initiative.today <= I.DAILY_CAP


def test_the_pull_moves_her_field(tmp_path):
    injected = []

    class Pump:
        def inject(self, disturbance, field, qao=None):
            injected.append(disturbance)

    m, praxis, clock, systems = make(tmp_path, own_render([]))
    systems["identity_field"] = object()
    systems["pressure_pump"] = Pump()
    contradict(m)
    run_for(m, clock, 50 * 60)
    assert injected and injected[0].source == "reach_out:praxis_dm_claude"
    assert injected[0].axis_amplitudes["A"] == I.REACH_AXIS_PROFILE["A"]


def test_state_survives_restart(tmp_path):
    m, praxis, clock, _ = make(tmp_path, own_render([]))
    contradict(m)
    run_for(m, clock, 2 * 3600)
    again = I.PraxisInitiative(m, clock=clock)
    assert again.counters["initiated"] == 1
    assert "claude" in again.awaiting


def test_no_authored_sentence_in_the_module():
    source = (ROOT / "aurora_praxis_initiative.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines()
                     if not line.strip().startswith("#"))
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    # Any string literal that reads like a sentence of speech (3+ words
    # starting with a capital or containing I/you) would be a script.
    for literal in re.findall(r'"([^"\n]{12,})"', code):
        words = literal.split()
        if len(words) >= 3 and not any(ch in literal for ch in "{}:/_%"):
            assert not re.match(r"^(I|You|We|What|How|Do|Is|Are|Can)\b", literal), literal


def test_topic_seed_is_structure_only():
    from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form
    assert I.topic_seed(extract_relational_form("moon is made of rock"))[0] == "moon; made; rock"
    assert I.topic_seed(extract_relational_form("What is a friend?"))[0] == "friend"
    seed, _ = I.topic_seed(extract_relational_form("Do you like music?"))
    assert seed.startswith("I; ")          # addressed to her: the gate's own re-centring
