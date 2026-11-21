"""Native system-wide nonlinear understanding test, no experimental field union.

One actual stream produces a relationship requiring two successive temporal
signals; the real ledger discovers it; the real representation exchange offers
it; the real communication-emergence consumer adopts the earned expectation.
A separate random null stream is the negative control. Continued live events
reuse historical knowledge without mistaking a remembered event for new data.

This is a traced pipeline test, not a claim that human-readable semantic
answers, all modalities, or device surface/subsurface sync have been proven.
"""
import json
import tempfile

from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange
from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
from test_resolution_ledger import _stream


def _run(mode, n=9000):
    root = tempfile.mkdtemp(prefix="aurora_native_joint_")
    ledger = AuroraResolutionLedger(state_dir=root, persist=False, max_path=3)
    exchange = AuroraRepresentationExchange(ledger, state_dir=root, persist=False)
    communication = AuroraCommunicationEmergence(state_dir=root, persist=False)
    earned_uses = []
    orig = communication.accept_representation

    def traced_consumer(rep, context):
        result = orig(rep, context)
        if result and rep.get("path") == "T>T>N":
            earned_uses.append({
                "representation_id": rep.get("id"),
                "stream": context.get("stream"),
                "event_index": context.get("event_index"),
                "predicted_target": dict(context.get("expectation") or {}).get("target"),
                "orientation_N": communication._shape_orientation().get("N", 0.0),
            })
        return result

    communication.accept_representation = traced_consumer
    exchange.register_consumer("real_communication", communication)
    for event in _stream(n, mode):
        ledger.observe_event(**event)
        exchange.after_event(event["event_index"], stream="history")
    discover = sorted({
        row["path"] for subject in ledger.status()["subjects"]
        for row in ledger.discovered(subject)
    })
    earned = sorted({
        row["path"] for row in exchange.representations(status="earned")
    })
    return ledger, exchange, earned_uses, discover, earned


def test_native_joint_history_is_learned_earned_and_used_by_real_communication():
    ledger, exchange, uses, discovered, earned = _run("xor")
    assert "T>T>N" in discovered, discovered
    assert "T>N" not in discovered, discovered
    assert "T>T>N" in earned, earned
    assert uses and all(u["predicted_target"] == "N" for u in uses)
    assert any(u["orientation_N"] > 0.0 for u in uses)
    before_history_index = ledger.next_event_index("history")
    before_live = len(uses)
    for i, ev in enumerate(_stream(40, "xor", seed=99)):
        live = dict(ev, event_index=None, event_id=f"live-{i}", episode_id="live-episode", stream="live")
        result = ledger.observe_event(**live)
        exchange.after_event(result["event_index"], stream="live")
    assert ledger.next_event_index("history") == before_history_index
    assert any(u["stream"] == "live" for u in uses[before_live:]), uses[-5:]
    print("NATIVE_XOR_TRANSFER", json.dumps({
        "discovered": discovered,
        "earned": earned,
        "historical_communication_adoptions": before_live,
        "live_communication_adoptions": len(uses)-before_live,
        "historical_events": before_history_index,
        "live_events": 40,
    }, sort_keys=True))


def test_native_null_history_has_no_spurious_joint_discovery_or_adoption():
    _, exchange, uses, discovered, earned = _run("null")
    assert "T>T>N" not in discovered, discovered
    assert "T>T>N" not in earned, earned
    assert not uses, uses[-5:]
    print("NATIVE_NULL_TRANSFER", json.dumps({
        "discovered": discovered,
        "earned": earned,
        "false_joint_communication_adoptions": len(uses)
    }, sort_keys=True))
