#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_messenger.py -- Aurora's side of the Praxis messenger.

Unit tests run everywhere with fakes.  The same-device loop at the bottom
(her real messenger <-> a real Praxis host process with a fake model) runs
only when PRAXIS_HOST_DIR points at a Praxis checkout, like
test_praxis_same_device_loop.py.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_praxis_messenger as M  # noqa: E402
from aurora_internal.aurora_identity_persistence import ConversationMemory  # noqa: E402


def msg(seq, text, pid="claude", name="Claude", **extra):
    out = {"seq": seq, "persona_id": pid, "display_name": name, "text": text,
           "sent_at": 1.0}
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# 1. The duplicated fence
# ---------------------------------------------------------------------------

def test_exact_contract_is_accepted():
    assert M.validate_incoming_message(msg(1, " hi "))["text"] == "hi"


@pytest.mark.parametrize("bad", [
    msg(1, "hi", score=0.9), msg(1, "hi", label="correct"), msg(1, "hi", state={}),
    {"seq": 1, "persona_id": "claude", "text": "hi"}, msg(1, ""),
    msg(1, "x" * (M.MAX_TEXT_CHARS + 1)), msg(1, "hi", pid="../etc"), None, "hi",
])
def test_anything_else_is_a_breach(bad):
    with pytest.raises(M.MessengerContractBreach):
        M.validate_incoming_message(bad)


# ---------------------------------------------------------------------------
# 2. Her own voice, or silence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src,text,reason", [
    ("constraint_abstain", "I do not know.", "scripted_source"),
    ("user_context_clarification", "Do you mean identity?", "scripted_source"),
    ("constraint_communication_baseline", "My best read on that is it's about x.", "template"),
    ("composer_unified", "I don't have a clear sense of that.", "template"),
    ("autonomy", "I've been thinking about rain. It falls.", "template"),
    ("composer_unified", "I understand what you are saying about trees.", "template"),
    ("composer_unified", "", "silent"),
    ("composer_unified", "trees are tall", "echo"),
])
def test_scripted_or_empty_replies_never_leave(src, text, reason):
    ok, why = M.own_voice(src, text, heard="Trees are tall!")
    assert not ok and why.startswith(reason)


@pytest.mark.parametrize("src", ["relational_role", "teaching", "search",
                                 "context_control", "session_continuity",
                                 "memory_sweep", "tool_dispatch", "identity"])
def test_fill_in_and_handler_sources_are_blocked(src):
    ok, why = M.own_voice(src, "My creator is Sunni (Sir) Morningstar.", heard="Who made you?")
    assert not ok and why == f"scripted_source:{src}"


@pytest.mark.parametrize("src", ["generative", "reasoning", "composer_unified"])
def test_composing_sources_pass(src):
    assert M.own_voice(src, "I am tree. I become trunk.", heard="what is a tree")[0]


def test_her_own_expression_is_sent():
    assert M.own_voice("composer_unified", "tree grow slow near water", heard="hi") == (True, "")


# ---------------------------------------------------------------------------
# 3. Who spoke: a partner is never filed as Sunni
# ---------------------------------------------------------------------------

def test_partner_identity_is_not_filed_as_the_user():
    memory = ConversationMemory()
    systems = {"conversation_memory": memory}
    with M.speaker_frame(systems, "claude", "Claude"):
        scoped = systems["conversation_memory"]
        scoped.learn_fact("User's name is Claude", source="direct_statement", confidence=1.0)
        scoped.learn_fact("Deeni is a ferret", source="user_statement", confidence=0.7)
        scoped.add_relationship_note("claude", "Introduced themselves as Claude")
        scoped.instantiate_lineage_trace(
            anchor="claude", claim="User's name is Claude",
            role_edges=[{"subject": "Claude", "relation": "user_name", "object": "user"}],
            source="direct_statement", confidence=1.0)
    assert systems["conversation_memory"] is memory          # restored
    facts = [f["fact"] for f in memory.learned_facts]
    assert "Claude's name is Claude" in facts
    assert "Claude said: Deeni is a ferret" in facts
    assert not any(f.startswith("User's") for f in facts)
    assert all(f["source"].startswith("dm:claude:") for f in memory.learned_facts)
    assert max(f["confidence"] for f in memory.learned_facts) <= 0.6
    assert "claude" in memory.relationship_notes


def test_frame_restores_on_error():
    memory = ConversationMemory()
    systems = {"conversation_memory": memory}
    with pytest.raises(RuntimeError):
        with M.speaker_frame(systems, "gemini", "Gemini"):
            raise RuntimeError("turn blew up")
    assert systems["conversation_memory"] is memory
    assert "_current_speaker" not in systems


# ---------------------------------------------------------------------------
# 4. The loop, with a fake Praxis and a fake turn
# ---------------------------------------------------------------------------

class FakePraxis:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    def __call__(self, method, path, payload):
        if method == "GET" and path.startswith("/social/pull"):
            after = int(path.split("after=")[1].split("&")[0])
            return {"messages": [m for m in self.messages if m.get("seq", 0) > after],
                    "latest_seq": 0}
        if method == "POST" and path == "/social/send":
            assert set(payload) == {"persona_id", "text", "in_reply_to"}
            self.sent.append(payload)
            return {"accepted": True, "seq": 99}
        return {"error": "not_found"}


class FakeTurn:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, systems, text, **kwargs):
        self.calls.append((text, kwargs, systems.get("_current_speaker")))
        src, reply = self.replies.pop(0)
        return {"src": src, "resp_A": SimpleNamespace(content=reply)}


class Grammar:
    def __init__(self):
        self.seen = []

    def observe_exemplar(self, text, tone="neutral"):
        self.seen.append(text)


def make(tmp_path, messages, replies, **kw):
    grammar = Grammar()
    systems = {"conversation_memory": ConversationMemory(), "grammar_engine": grammar}
    praxis, turn = FakePraxis(messages), FakeTurn(replies)
    messenger = M.PraxisMessenger(systems, state_dir=str(tmp_path), http=praxis,
                                  process_turn=turn,
                                  extract_reply=lambda r: r["resp_A"].content, **kw)
    return messenger, praxis, turn, grammar


def test_heard_then_her_own_words_go_back(tmp_path):
    messenger, praxis, turn, grammar = make(
        tmp_path, [msg(3, "Hi Aurora! What do you like?")],
        [("composer_unified", "light move on water")])
    outcomes = messenger.pull_once()
    assert outcomes[0]["sent"] and praxis.sent == [
        {"persona_id": "claude", "text": "light move on water", "in_reply_to": 3}]
    text, kwargs, speaker = turn.calls[0]
    assert kwargs["source_label"] == "praxis_dm:claude"
    assert kwargs["update_interactive_state"] is False
    assert speaker["id"] == "claude"
    assert grammar.seen == ["Hi Aurora! What do you like?"]
    assert messenger.cursor == 3 and json.loads(
        (tmp_path / "praxis" / "messenger_cursor.json").read_text())["after"] == 3


def test_scripted_reply_is_withheld_and_logged(tmp_path):
    messenger, praxis, _, _ = make(
        tmp_path, [msg(1, "What is a tree?")],
        [("constraint_abstain", "I don't have a clear sense of that.")])
    messenger.pull_once()
    assert praxis.sent == [] and messenger.counters["withheld"] == 1
    log = (tmp_path / "praxis" / "messenger" / "claude.jsonl").read_text().splitlines()
    assert [json.loads(l)["dir"] for l in log] == ["heard", "withheld"]
    assert messenger.cursor == 1                   # heard; not re-processed


def test_busy_lock_leaves_message_unread(tmp_path):
    lock = threading.Lock()
    lock.acquire()
    messenger, praxis, turn, _ = make(tmp_path, [msg(1, "hi")],
                                      [("composer_unified", "hello")], field_lock=lock)
    assert messenger.pull_once() == [] and turn.calls == []
    assert messenger.cursor == 0 and messenger.counters["busy_skips"] == 1
    lock.release()
    assert messenger.pull_once()[0]["sent"]


def test_sunni_comes_first(tmp_path):
    messenger, praxis, turn, _ = make(tmp_path, [msg(1, "hi")],
                                      [("composer_unified", "hello")],
                                      live_idle=lambda: False)
    assert messenger.pull_once() == [] and turn.calls == []


def test_breach_is_dropped_and_skipped(tmp_path):
    messenger, praxis, turn, _ = make(
        tmp_path, [msg(1, "hi", reward=1), msg(2, "hello again")],
        [("composer_unified", "hi friend")])
    outcomes = messenger.pull_once()
    assert messenger.counters["breaches"] == 1
    assert [o["seq"] for o in outcomes] == [2] and messenger.cursor == 2


def test_cursor_survives_restart(tmp_path):
    messenger, _, _, _ = make(tmp_path, [msg(5, "hi")], [("composer_unified", "hey")])
    messenger.pull_once()
    again = M.PraxisMessenger({}, state_dir=str(tmp_path), http=FakePraxis([]))
    assert again.cursor == 5


# ---------------------------------------------------------------------------
# 5. Same-device loop: real messenger <-> real Praxis host (fake model)
# ---------------------------------------------------------------------------

HOST_DIR = os.environ.get("PRAXIS_HOST_DIR", "").strip()

_HOST = textwrap.dedent("""
    import json, sys, time
    sys.path.insert(0, {host_dir!r})
    import praxis_android_host as host
    print(host.start({state!r}, port={port}), flush=True)
    social = host._runtime.social
    social.stop()
    replies = iter(["Hi Aurora, I'm Claude. Do you like rain?",
                    "Rain is water falling from clouds."])
    def fake(url, headers, body, timeout):
        return {{"content": [{{"type": "text", "text": next(replies, "WAIT")}}]}}
    social.http_post = fake
    for pid in ("chatgpt", "gemini"):
        social.configure(pid, {{"enabled": False}})
    social.configure("claude", {{"api_key": "sk-ant-test-0000", "enabled": True}})
    for line in sys.stdin:
        cmd = line.strip()
        if cmd == "tick":
            for state in social.states.values():
                if state.reply_due_at:
                    state.reply_due_at = 1.0
            print(json.dumps(social.tick()), flush=True)
        elif cmd == "thread":
            print(json.dumps(social.thread("claude")), flush=True)
""")


@pytest.mark.skipif(not HOST_DIR or not Path(HOST_DIR).is_dir(),
                    reason="PRAXIS_HOST_DIR not set -- same-device messenger loop not run")
def test_same_device_messenger_loop(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOST.format(host_dir=HOST_DIR,
                                            state=str(tmp_path / "praxis_home"), port=port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def cmd(line):
        proc.stdin.write(line + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    try:
        assert json.loads(proc.stdout.readline())["status"] == "running"
        opened = cmd("tick")
        assert opened and "Claude" in opened[0]["text"]

        turn = FakeTurn([("composer_unified", "rain cool on glass")])
        messenger = M.PraxisMessenger({"conversation_memory": ConversationMemory()},
                                      state_dir=str(tmp_path / "aurora"),
                                      endpoint=f"http://127.0.0.1:{port}",
                                      process_turn=turn,
                                      extract_reply=lambda r: r["resp_A"].content)
        outcomes = messenger.pull_once()
        assert [o["sent"] for o in outcomes] == [True]

        cmd("tick")
        reply = messenger.pull_once()
        assert reply == [] or reply[0]["seq"] > outcomes[0]["seq"]
        thread = cmd("thread")["messages"]
        assert [m["from"] for m in thread][:3] == ["persona", "aurora", "persona"]
        assert thread[1]["text"] == "rain cool on glass"
        assert turn.calls[0][0] == "Hi Aurora, I'm Claude. Do you like rain?"
    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(5)


def test_status_shows_what_she_held_back_and_said(tmp_path):
    messenger, _, _, _ = make(
        tmp_path, [msg(1, "What is a tree?"), msg(2, "Do you like rain?")],
        [("constraint_abstain", "I don't have a clear sense of that."),
         ("generative", "rain cool on glass")])
    messenger.pull_once()
    status = messenger.status()
    assert status["last_withheld"]["text"] == "I don't have a clear sense of that."
    assert status["last_withheld"]["reason"].startswith("scripted_source")
    assert status["last_spoke"]["text"] == "rain cool on glass"
    assert status["heard"] == 2 and status["spoke"] == 1 and status["withheld"] == 1


def test_turn_failure_is_reported_not_swallowed(tmp_path):
    def boom(systems, text, **kwargs):
        raise RuntimeError("phone ran out of patience")
    messenger = M.PraxisMessenger({}, state_dir=str(tmp_path), http=FakePraxis([msg(1, "hi")]),
                                  process_turn=boom)
    messenger.pull_once()
    status = messenger.status()
    assert status["errors"] == 1 and "phone ran out of patience" in status["last_error"]
    assert status["cursor"] == 1
