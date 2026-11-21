"""Remote-first pairing must never substitute a LAN-only route for a VPN."""
from __future__ import annotations

import json
from types import SimpleNamespace
from aurora_internal.desktop import remote_link


def test_only_tailscale_routes_classify_as_remote():
    assert remote_link.remote_address("100.64.0.1")
    assert remote_link.remote_address("100.127.255.255")
    assert remote_link.remote_address("desktop.example.ts.net")
    assert not remote_link.remote_address("192.168.1.20")
    assert not remote_link.remote_address("10.0.0.23")
    assert not remote_link.remote_address("100.128.0.1")
    assert not remote_link.remote_address("127.0.0.1")
    assert not remote_link.remote_address("0.0.0.0")
    assert not remote_link.remote_address("203.0.113.20")


def test_desktop_selects_connected_mesh_address(monkeypatch):
    monkeypatch.setattr(remote_link.shutil, "which", lambda x: "/usr/bin/tailscale")
    def fake_run(*a, **kw):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "BackendState": "Running",
            "TailscaleIPs": ["100.94.51.22", "fd7a:115c:a1e0::1"],
            "Self": {"DNSName": "aurora-laptop.tail0000.ts.net."}
        }), stderr="")
    monkeypatch.setattr(remote_link.subprocess, "run", fake_run)
    status = remote_link.tailscale_status()
    assert status["online"]
    assert status["ipv4"] == "100.94.51.22"
    assert status["address"] == "aurora-laptop.tail0000.ts.net"
    assert remote_link.remote_diagnostics(
        {"AURORA_STRATA_LINK_HOST": status["ipv4"]})["remote_capable"]


def test_disconnected_daemon_is_not_called_remote_ready(monkeypatch):
    monkeypatch.setattr(remote_link.shutil, "which", lambda x: "/usr/bin/tailscale")
    monkeypatch.setattr(remote_link.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=0, stdout=json.dumps({
            "BackendState": "Stopped",
            "TailscaleIPs": ["100.94.51.22"],
            "Self": {"DNSName": "aurora-laptop.tail0000.ts.net."}
        }), stderr=""))
    status = remote_link.tailscale_status()
    assert not status["online"] and not status["address"]
    assert not remote_link.remote_diagnostics(
        {"AURORA_STRATA_LINK_HOST": "100.94.51.22"})["remote_capable"]


def test_no_vpn_is_not_ready(monkeypatch):
    monkeypatch.setattr(remote_link.shutil, "which", lambda x: None)
    status = remote_link.tailscale_status()
    assert not status["available"] and not status["online"]
    assert not remote_link.remote_diagnostics(
        {"AURORA_STRATA_LINK_HOST": "192.168.1.20"})["remote_capable"]
