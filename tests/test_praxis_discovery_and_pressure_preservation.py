"""Praxis startup recovery must not remove messenger autonomy or XTNBA pressure.

Discovery is transport-only, and stays responsive even while Aurora reserves
her cognitive field for a live interaction. Actual observations/consequences
must still respect that field lock and travel through the original physics.
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

from aurora_praxis_bridge import (
    PraxisBridge, PRAXIS_CONTRACT_VERSION,
    PRAXIS_PROTOCOL_NAME, PRAXIS_PROTOCOL_VERSION, PRAXIS_SERVICE_NAME,
)
import aurora_praxis_messenger as messenger_module


def test_starting_server_is_discovered_during_boot_settle_without_admitting_experience(tmp_path):
    idle = False
    requests = []
    connected = threading.Event()
    bridge = PraxisBridge(
        {}, state_dir=str(tmp_path), poll_interval_s=0.01,
        live_idle=lambda: idle, field_lock=threading.Lock(),
    )

    def server(path, *, method="GET", payload=None):
        requests.append(path)
        if path == "/hello":
            connected.set()
            return {
                "service": PRAXIS_SERVICE_NAME,
                "protocol": PRAXIS_PROTOCOL_NAME,
                "protocol_version": PRAXIS_PROTOCOL_VERSION,
                "compatible_protocol_versions": [PRAXIS_PROTOCOL_VERSION],
                "contract_version": PRAXIS_CONTRACT_VERSION,
                "accepting": True,
            }
        raise AssertionError("No intake/action allowed while cognition is reserved")

    bridge._request = server
    bridge.start()
    try:
        assert connected.wait(1.5), "transport discovery must not wait for a live cognitive slot"
        assert bridge.discovery == "compatible"
        assert bridge.pulls_attempted == 0
        assert bridge.situations_witnessed == 0
        assert bridge.pressure_injections == 0
        assert bridge.sediment_deposits == 0
    finally:
        bridge.stop()
    assert requests == ["/hello"]


def test_compatible_discovery_does_not_hammer_server_while_cognition_is_busy(tmp_path, monkeypatch):
    bridge = PraxisBridge({}, state_dir=str(tmp_path), live_idle=lambda: False)
    replies = []
    bridge.handshake = lambda: replies.append("handshake") or setattr(bridge, "discovery", "compatible")
    assert bridge._channel_open() is True
    assert len(replies) == 1
    # Simulate a recent successful handshake; no repeated network work.
    bridge.last_handshake_at = __import__("time").time()
    assert bridge._channel_open() is True
    assert len(replies) == 1


def test_messenger_same_owner_restart_keeps_unanswered_pressure_and_initiative(tmp_path, monkeypatch):
    systems = {"own_understanding": object()}
    messenger = messenger_module.PraxisMessenger(
        systems, state_dir=str(tmp_path), live_idle=lambda: False, poll_s=60,
    )
    monkeypatch.setattr(messenger_module, "_MESSENGER", messenger)
    messenger.pending["gemma"] = {
        "message": {"seq": 9, "persona_id": "gemma", "display_name": "Gemma",
                    "text": "What is your understanding of rain?", "sent_at": 1.0},
        "attempts": 2, "last_attempt": 99.0,
    }
    if messenger.initiative is not None:
        messenger.initiative.levels["gemma"] = 0.8
    before_initiative = messenger.initiative
    revived = messenger_module.start_praxis_messenger(
        systems, state_dir=str(tmp_path), live_idle=lambda: False,
    )
    try:
        assert revived is messenger
        assert revived.pending["gemma"]["attempts"] == 2
        assert revived.initiative is before_initiative
        assert revived._thread is not None and revived._thread.is_alive()
        if revived.initiative is not None:
            assert revived.initiative.levels["gemma"] == 0.8
    finally:
        messenger.stop()


_APP_PATH = Path(__file__).resolve().parent.parent / "flutter_app/android/app/src/main/python"


@pytest.mark.skipif(not (_APP_PATH / "aurora_bridge.py").is_file(), reason="Android bridge not mounted")
def test_failed_local_praxis_bridge_is_not_misreported_as_server_not_initialized(monkeypatch):
    sys.path.insert(0, str(_APP_PATH))
    import aurora_bridge as app_bridge

    monkeypatch.setattr(app_bridge, "_praxis", None)
    monkeypatch.setattr(app_bridge, "_praxis_boot_attempted", True)
    monkeypatch.setattr(app_bridge, "_praxis_last_start_error", "OSError: storage temporarily unavailable")
    monkeypatch.setattr(app_bridge, "_schedule_praxis_bridge_recovery", lambda: None)
    result = json.loads(app_bridge.get_praxis_status())
    assert result["status"] == "error"
    assert "OSError" in result["error"]
    assert result["thread_alive"] is False


@pytest.mark.skipif(not (_APP_PATH / "aurora_bridge.py").is_file(), reason="Android bridge not mounted")
def test_failed_local_messenger_is_distinguished_from_praxis_server(monkeypatch):
    sys.path.insert(0, str(_APP_PATH))
    import aurora_bridge as app_bridge

    monkeypatch.setattr(app_bridge, "_praxis_messenger", None)
    monkeypatch.setattr(app_bridge, "_praxis_messenger_boot_attempted", True)
    monkeypatch.setattr(app_bridge, "_praxis_messenger_last_start_error", "ImportError: missing Messenger module")
    monkeypatch.setattr(app_bridge, "_schedule_praxis_messenger_recovery", lambda: None)
    result = json.loads(app_bridge.get_praxis_messenger_status())
    assert result["status"] == "error"
    assert "ImportError" in result["last_error"]


def test_discovery_and_messenger_modules_still_expose_original_pressure_pathways():
    # Structural guard: a future performance change must not delete the
    # original abilities responsible for pressure, sediment, environmental
    # consequence, the voice gate, reentry, or autonomous initiative.
    assert all(hasattr(PraxisBridge, name) for name in (
        "build_manifest", "pull_once", "_witness", "_route_to_constraint_physics",
        "_emit_constraint_evidence", "_emit_resolution_pressure", "_deposit_sediment",
    ))
    assert all(hasattr(messenger_module.PraxisMessenger, name) for name in (
        "handle_message", "pull_once", "_pressure", "_reenter_pending",
    ))
    from aurora_praxis_initiative import PraxisInitiative
    assert all(hasattr(PraxisInitiative, name) for name in (
        "gather_topics", "_inject", "_grow", "heard_from", "articulate", "_register_for_validation",
        "tick", "_attempt",
    ))
