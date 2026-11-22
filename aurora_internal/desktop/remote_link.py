"""Read-only private-network discovery for Android Surface remote pairing.

No credentials, login, or owner tokens are read. A remote-capable address
requires an *active* mesh VPN on the desktop, not just a home-LAN IP.
OS networking permission and the peer's own VPN membership are still required.
"""
from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from urllib.parse import urlsplit


def remote_address(host: str) -> bool:
    """Reject addresses that only work on the home LAN or public wildcard."""
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        return ip in ipaddress.ip_network("100.64.0.0/10")
    except ValueError:
        # DNS names must be explicitly confirmed by a VPN provider.
        return host.lower().rstrip(".").endswith(".ts.net")


def tailscale_status():
    """Read Tailscale's live local daemon state, never infer from installation."""
    exe = shutil.which("tailscale")
    if not exe:
        return {"available": False, "online": False, "reason": "Tailscale is not installed"}
    try:
        result = subprocess.run([exe, "status", "--json"],
            capture_output=True, text=True, timeout=5, check=False)
        if result.returncode:
            return {"available": True, "online": False,
                    "reason": (result.stderr or "VPN not connected").strip()[:250]}
        info = json.loads(result.stdout)
        online = str(info.get("BackendState") or "") == "Running"
        ip = next((str(a) for a in (info.get("TailscaleIPs") or [])
                   if remote_address(str(a))), "")
        self_node = info.get("Self") or {}
        dns = str(self_node.get("DNSName") or "").rstrip(".")
        # A stable Tailnet address is valid even when the local LAN changes.
        host = dns if dns.lower().endswith(".ts.net") else ip
        return {"available": True, "online": bool(online and host),
                "address": host if online else "", "ipv4": ip if online else "",
                "reason": "Connected" if online and host else "Tailscale is not connected"}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"available": True, "online": False,
                "reason": f"{type(exc).__name__}: {exc}"[:250]}


def remote_diagnostics(config: dict | None = None, relay: dict | None = None):
    """Show configured reachability without claiming internet availability."""
    config, relay = config or {}, relay or {}
    if relay.get("origin"):
        return {
            "provider": "built_in_encrypted_https_relay",
            "relay_origin": str(relay["origin"]),
            "room_configured": bool(relay.get("room") and relay.get("token")),
            "local_strata_listener": str(config.get("AURORA_STRATA_LINK_HOST") or ""),
            "phone_vpn_required": False,
            "desktop_must_remain_awake": True,
            "reachability": "see live_relay and test from Android on cellular",
        }
    return {
        "provider": "not_configured",
        "phone_vpn_required": False,
        "desktop_must_remain_awake": True,
        "reachability": "Set up a hosted HTTPS relay with Pair phone",
    }
