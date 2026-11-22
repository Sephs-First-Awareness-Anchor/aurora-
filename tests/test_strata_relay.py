"""Encrypted relay: pairing, authorization, tampering, reconnection and real exchange."""
from __future__ import annotations

import json
import threading
import time
from urllib.parse import urlsplit

import pytest

from aurora_internal.dual_strata import relay_transport as tr
from aurora_internal.dual_strata.relay_gateway import RelayRegistry, create_server
from aurora_internal.dual_strata.strata_link import (
    StrataLinkClient, StrataLinkServer, configure_surface, ensure_secret, sign, verify,
)


def test_pairing_is_reusable_and_contains_no_gateway_provisioning_key(tmp_path):
    a = tr.relay_pairing_line(tmp_path, "https://relay.example.org", "http://192.168.1.8:8791")
    b = tr.relay_pairing_line(tmp_path, "https://relay.example.org", "http://192.168.1.8:8791")
    assert a == b
    assert a.startswith("aurora-relay://")
    origin, secret, cfg = tr.parse_relay_pairing(a)
    assert origin == "https://relay.example.org"
    assert secret == ensure_secret(tmp_path)
    assert cfg["local"] == "http://192.168.1.8:8791"
    phone = tmp_path / "phone"
    assert configure_surface(phone, a)["ok"]
    client = StrataLinkClient(phone, endpoint=origin, secret=secret)
    assert client._relay_transport is not None
    assert client.status()["route"] == "offline"
    assert "relay_home.json" not in str((phone / "strata_link" / "relay_surface.json").read_text())


@pytest.mark.parametrize("origin", [
    "http://relay.example.org", "https://user:password@relay.example.org",
    "https://relay.example.org/a", "https://relay.example.org?x=y",
    "ftp://relay.example.org",
])
def test_insecure_or_non_origin_relay_is_rejected(origin):
    with pytest.raises(ValueError):
        tr.validate_origin(origin)


def test_authenticated_encryption_is_domain_separated_and_not_plaintext():
    secret = "x" * 48
    message = {"body": "private developmental history", "headers": {"X-Aurora-Ts": "123"}}
    packet = tr._seal(secret, "private-room", "request", message)
    assert "private developmental history" not in packet
    assert tr._unseal(secret, "private-room", "request", packet) == message
    with pytest.raises(Exception):
        tr._unseal(secret, "private-room", "response", packet)
    with pytest.raises(Exception):
        tr._unseal("wrong" * 10, "private-room", "request", packet)
    import base64
    wire = bytearray(base64.urlsafe_b64decode(packet))
    wire[-3] ^= 1
    with pytest.raises(Exception):
        tr._unseal(secret, "private-room", "request",
                   base64.urlsafe_b64encode(wire).decode())


def test_relay_gateway_rejects_unregistered_and_unauthorized_rooms():
    registry = RelayRegistry("provisioning-" + "z" * 30)
    room, token = "r" * 36, "t" * 40
    assert registry.register(room, token, "wrong")[0] == 403
    assert registry.locate(room, token) is None
    assert registry.register(room, token, "provisioning-" + "z" * 30)[0] == 200
    assert registry.register(room, "wrong" * 12, "provisioning-" + "z" * 30)[0] == 403
    assert registry.locate(room, "wrong" * 12) is None
    assert registry.locate(room, token) is not None
    assert registry.exchange(registry.locate(room, token), "not-a-packet")[0] == 400


def test_real_gateway_roundtrip_reuses_signed_strata_server(tmp_path, monkeypatch):
    secret_key = "relay-host-provision-" + "k" * 25
    gateway = create_server(secret_key, "127.0.0.1", 0)
    gateway_thread = threading.Thread(target=gateway.serve_forever, daemon=True)
    gateway_thread.start()
    actual_origin = f"http://127.0.0.1:{gateway.server_address[1]}"
    original_post = tr._post

    # Substitute test-only loopback HTTP. Public Aurora configs still insist
    # on HTTPS, the hosted service needs TLS, and no production bypass exists.
    def test_transport_post(origin, path, body, token, timeout, provisioning_key=""):
        assert origin == "https://relay.test.invalid"
        return original_post(actual_origin, path, body, token, timeout, provisioning_key)
    monkeypatch.setattr(tr, "_post", test_transport_post)
    home = tmp_path / "desktop"
    pairing = tr.relay_pairing_line(home, "https://relay.test.invalid")
    _, shared_secret, phone_cfg = tr.parse_relay_pairing(pairing)
    home_file = home / "strata_link" / "relay_home.json"
    cfg = json.loads(home_file.read_text())
    cfg["provisioning_key"] = secret_key
    tr._write(home_file, cfg)
    server = StrataLinkServer(home, host="127.0.0.1", port=0,
                              state_install_allowed=False)
    pump = tr.RelayHomePump(home, server)
    assert pump.start()
    try:
        surface = tr.RelaySurfaceTransport(phone_cfg, shared_secret)
        body = json.dumps({"v": 1, "surface_id": "phone-one", "name": "phone",
                           "claim": True, "up": [], "link_key": "", "down_ack": 0}).encode()
        ts = repr(time.time())
        headers = {"X-Aurora-Ts": ts, "X-Aurora-Sig": sign(shared_secret, ts, body)}
        # A register can race with the first dial, but never skips auth.
        for _ in range(25):
            try:
                answer, response_headers = surface(body, headers)
                break
            except Exception:
                time.sleep(.1)
        else:
            pytest.fail("Desktop relay did not register or answer")
        assert verify(shared_secret, response_headers["X-Aurora-Ts"], answer,
                      response_headers["X-Aurora-Sig"])
        assert json.loads(answer)["v"] == 1
        assert surface.last_route == "relay"
        # The gateway releases the Surface as soon as it receives the reply,
        # which can precede the home pump's bookkeeping increment.
        for _ in range(40):
            if pump.processed >= 1:
                break
            time.sleep(.025)
        assert pump.processed >= 1
    finally:
        pump.stop()
        gateway.shutdown()
        gateway.server_close()
        gateway_thread.join(timeout=2)


def test_first_phone_claims_from_desktop_bootstrap_and_drains_uplink(tmp_path):
    """A first phone is not forced into permanent standby by desktop boot."""
    from aurora_internal.dual_strata.strata_link import link_dir
    home = tmp_path / "home"
    server = StrataLinkServer(home, host="127.0.0.1", port=0)
    server.set_home_surface("home-surface")
    first = server.handle_sync({"surface_id": "home-surface", "name": "home"})
    assert first["role"] == "active" and first["epoch"] == 1
    result = server.handle_sync({
        "surface_id": "phone-a", "name": "my phone", "claim": True,
        "up": [{"seq": 1, "channel": "raw_input", "kind": "state",
                "payload": {"text": "test", "expires_at": time.time() + 100}}],
    })
    assert result["role"] == "active"
    assert result["owner"] == "phone-a"
    assert result["surface_ready"] is True
    assert result["epoch"] == 2
    assert result["up_ack"] == 1
    assert (link_dir(home) / "raw_input.json").exists()
    # The exception is only for the first phone; a new phone still needs
    # the established checkpoint/handoff protocol.
    another = server.handle_sync({"surface_id": "phone-b", "claim": True})
    assert another["role"] == "standby"
    assert another["error"] == "checkpoint_handoff_required"
    assert another["owner"] == "phone-a"


def test_standby_pending_records_do_not_trigger_fast_polling(tmp_path, monkeypatch):
    """The pending queue must not create an endless two-second retry storm."""
    from aurora_internal.dual_strata import strata_link as sl
    client = StrataLinkClient(tmp_path, endpoint="http://127.0.0.1:9877",
                              secret="test", transport=lambda *_: (b"", {}))
    client.role = "standby"
    client.online = True
    client.outbox.append("raw_input", "state", {"text": "queued"})
    observed = []
    def one_sync():
        client._stop.set()
        observed.append("sync")
        return False
    monkeypatch.setattr(client, "sync_once", one_sync)
    # An iteration can end immediately after sync, but must not depend on
    # or clear the pending outbox to terminate.
    client._run()
    assert observed == ["sync"]
    assert client.outbox.stats()["pending"] == 1
