# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Adoption tests: live turns share knowledge with history, existing subjects of
representation adopt discovered shapes through the one-method protocol, shapes
reach identity as relics at neutral success, words are tied to shapes by the
act they occur in, and the relation vocabulary is open to discovered kinds.
"""
import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurora_internal import aurora_live_experience as live  # noqa: E402
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger, role_subject  # noqa: E402
from test_resolution_ledger import _stream  # noqa: E402

_REP = {"id": "REPR:external_user:T>N", "subject": "external_user", "path": "T>N", "target": "N",
        "status": "earned", "positional": False, "z": 6.0}


def test_role_subject_shares_subjects_across_history_and_live():
    assert role_subject("user") == role_subject("historical_user") == role_subject("external_user") == "external_user"
    assert role_subject("assistant") == role_subject("historical_other_assistant") == role_subject("aurora") == "responder"
    assert role_subject("someone_else") == "someone_else"


def test_live_stream_shares_knowledge_but_not_context_with_history():
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    exchange = AuroraRepresentationExchange(ledger, state_dir=tempfile.mkdtemp(), persist=False)
    for ev in _stream(9000, "pair"):
        ledger.observe_event(**ev)
        exchange.after_event(ev["event_index"])
    history_before = ledger.last_bits("history")
    for i, ev in enumerate(_stream(40, "pair", seed=99)):
        ev = dict(ev, event_index=None, event_id=f"L{i}", episode_id="live1", stream="live")
        result = ledger.observe_event(**ev)
        exchange.after_event(result["event_index"], stream="live")
    assert ledger.last_bits("history") == history_before          # live never pollutes history's context
    subject, _ = ledger.last_bits("live")
    assert any(e["path"] == "T>N" for e in ledger.expectations(subject, "live"))   # history's knowledge applies live
    assert set(ledger.status()["streams"]) == {"history", "live"}


def test_live_module_feeds_the_shared_runtime_and_adopts_any_subject():
    class Subject:
        def accept_representation(self, rep, context):
            return None
    systems = {"state_dir": tempfile.mkdtemp(), "some_subject": Subject()}
    live.observe_user_event(systems, "hello there", session_id="s1", now=1000.0)
    live.observe_reply_event(systems, "hello!", session_id="s1", now=1002.0)
    live.observe_user_event(systems, "hi again", session_id="s2", now=5000.0)
    ledger, exchange = systems["resolution_ledger"], systems["representation_exchange"]
    assert ledger.next_event_index("live") == 3 and ledger.next_event_index("history") == 0
    assert systems["_live_last_event_ts"] == 5000.0
    assert "some_subject" in exchange.consumers()
    assert live.observe_reply_event(systems, "   ", session_id="s2") == {}


def test_reply_text_is_read_like_the_bridge_reads_it():
    class Resp:
        content = [{"type": "text", "text": "yo"}, {"type": "tool", "text": "no"}]
    assert live.reply_text_of({"resp_A": Resp()}) == "yo"
    assert live.reply_text_of({"text": " hi "}) == "hi"
    assert live.reply_text_of({}) == ""


def test_identity_adopts_an_earned_shape_as_a_neutral_relic_once():
    from aurora_behavioral_identity import BehavioralIdentityEngine

    class Stub:
        def __init__(self):
            self.calls = []

        def process_episode(self, summary, relics, pillars, mode):
            self.calls.append((summary, relics, mode))

    stub = Stub()
    first = BehavioralIdentityEngine.accept_representation(stub, dict(_REP), {})
    again = BehavioralIdentityEngine.accept_representation(stub, dict(_REP), {})
    assert first == {"adopted": True, "already": False} and again == {"adopted": True, "already": True}
    assert len(stub.calls) == 1
    summary, relics, mode = stub.calls[0]
    assert summary["success_rate"] == 0.5 and mode.name == "BOUNDED"
    assert relics[0]["theme"] == "shape:T>N" and relics[0]["seed_ids"] == [_REP["id"]]
    assert abs(sum(relics[0]["manifold_position"]) - 1.0) < 1e-9
    assert BehavioralIdentityEngine.accept_representation(stub, dict(_REP, status="in_use"), {}) is None
    assert BehavioralIdentityEngine.accept_representation(stub, dict(_REP, positional=True, id="x"), {}) is None


def test_communication_emergence_adopts_an_expectation_as_bounded_orientation():
    from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
    from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form
    ce = AuroraCommunicationEmergence(state_dir=tempfile.mkdtemp(), persist=False)
    form = extract_relational_form("hello")
    base = ce._possibility_activation_base(form)
    assert ce._possibility_activation(form) == base                      # no shape held: unchanged
    ctx = {"stream": "live", "event_index": 7, "expectation": {"target": "A", "p_high": 0.9, "p_high_marginal": 0.5}}
    assert ce.accept_representation(dict(_REP), ctx) == {"adopted": True}
    shaped = ce._possibility_activation(form)
    assert shaped["A"] > base["A"] and abs(sum(shaped.values()) - 1.0) < 1e-5
    assert ce.accept_representation(dict(_REP, status="candidate"), ctx) is None
    ce.accept_representation(dict(_REP), dict(ctx, event_index=8, expectation={"target": "A", "p_high": 0.5, "p_high_marginal": 0.5}))
    assert ce._possibility_activation(form) == base                      # only the newest event's expectation is held


def test_lexical_grounding_ties_words_to_the_act_they_occur_in():
    from aurora_internal.aurora_lexical_grounding import AuroraLexicalGrounding
    stub = SimpleNamespace()
    ctx = {"shape_words": [{"word": "big", "lift": 2.0, "count": 40}, {"word": "small", "lift": -2.0, "count": 40}]}
    assert AuroraLexicalGrounding.accept_representation(stub, dict(_REP), ctx) == {"grounded_words": 2}
    assert AuroraLexicalGrounding.act_grounded_words(stub, "big") == {_REP["id"]: 2.0}
    AuroraLexicalGrounding.accept_representation(stub, dict(_REP), {"shape_words": []})   # re-offer replaces
    assert AuroraLexicalGrounding.act_grounded_words(stub) == {}
    assert AuroraLexicalGrounding.accept_representation(stub, dict(_REP, status="in_use"), ctx) is None


def test_exchange_ties_tokens_to_a_shape_by_where_they_occur_not_what_they_are_called():
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    exchange = AuroraRepresentationExchange(ledger, state_dir=tempfile.mkdtemp(), persist=False)
    for ev in _stream(9000, "pair"):
        ledger.observe_event(**ev)
        exchange.after_event(ev["event_index"], tokens=["the", "big" if ev["text_length"] > 100 else "small"])
    rep = next(v for v in exchange.representations() if v["path"] == "T>N" and v["status"] == "earned")
    words = {w["word"]: w["lift"] for w in exchange.shape_words(rep["id"])}
    assert words.get("big", 0) > 1.0 and words.get("small", 0) < -1.0 and abs(words.get("the", 0.0)) < 0.1, words
    assert rep["positional"] is False
    assert any(v["positional"] for v in [{"positional": all(a in ("X", "B") for a in "X>B".split(">"))}])


def test_open_relation_vocabulary_accepts_discovered_kinds_and_counts_their_use():
    from aurora_internal.aurora_ontological_scaffolding import DiscoveredRelationKind, OntologicalWeb
    kind = DiscoveredRelationKind("warp_relation_x", {"X": 0.5})
    assert kind == DiscoveredRelationKind("warp_relation_x") and hash(kind) == hash(DiscoveredRelationKind("warp_relation_x"))
    assert kind.value == "warp_relation_x" and kind not in {"related_to"}
    web = OntologicalWeb()
    comp = SimpleNamespace(component_id="warp_relation_x", axis_profile={"X": 0.5})
    web._integrate_warp(comp)
    assert web._open_kinds["warp_relation_x"].value == "warp_relation_x"
    assert web._score_trial(comp) == 0.25                                   # untested: neutral floor
    web.record_relation_trial_use("warp_relation_x")
    web.record_relation_trial_use("warp_relation_x")
    web.record_relation_trial_outcome("warp_relation_x", True)
    assert abs(web._score_trial(comp) - (0.35 + 0.55 * 0.5)) < 1e-9         # use and consequence now move the score
    web._dissolve_warp("warp_relation_x")
    assert "warp_relation_x" not in web._open_kinds


def test_history_environment_shares_the_runtime_and_uses_role_subjects():
    path = ROOT / "flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py"
    spec = importlib.util.spec_from_file_location("aurora_hist_env_adoption_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    systems = {}
    env = mod.HistoricalExperienceEnvironment(systems, state_dir=tempfile.mkdtemp(), archive_path=None)
    env._state = {"event_index": 0}
    env._episodes = {"ep1": {"previous_episode_gap_seconds": 99.0}}
    event = {"event_id": "e0", "episode_id": "ep1", "actor": "user", "text": "hello there",
             "delta_seconds_from_previous_turn": None}
    assert env._resolution_event_kwargs(event, 0)["actor"] == "external_user"
    assert env._resolution_event_kwargs(dict(event, actor="historical_other_assistant"), 1)["actor"] == "responder"
    env._observe_resolution_ledger(event)
    assert systems["resolution_ledger"].next_event_index() == 1 and "representation_exchange" in systems


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:
                failures += 1
                print("FAIL", name, type(exc).__name__, str(exc)[:240])
    sys.exit(1 if failures else 0)
