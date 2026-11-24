"""Built-in encrypted relay does not require a system VPN on either device."""
from aurora_internal.desktop.remote_link import remote_diagnostics, remote_address


def test_legacy_tailscale_classification_is_not_required():
    assert remote_address("100.64.0.1")
    assert not remote_address("192.168.1.20")


def test_encrypted_gateway_is_explicitly_identified_without_vpn():
    status = remote_diagnostics(
        {"AURORA_STRATA_LINK_HOST": "0.0.0.0"},
        {"origin": "https://relay.example.org",
         "room": "room" * 8, "token": "token" * 8})
    assert status["provider"] == "built_in_encrypted_https_relay"
    assert status["room_configured"]
    assert status["phone_vpn_required"] is False
    assert "live_relay" in status["reachability"]


def test_no_relay_never_claims_remote_ready():
    status = remote_diagnostics({"AURORA_STRATA_LINK_HOST": "192.168.1.20"})
    assert status["provider"] == "not_configured"
    assert status["phone_vpn_required"] is False
