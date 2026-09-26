#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_same_device_loop.py -- the whole same-device loop, reproducibly.

Destination: Aurora's repository `tests/` directory.

Two processes, one loopback interface, exactly as on the phone:

  - The Praxis host runs as a SEPARATE PROCESS from PRAXIS_HOST_DIR -- either
    the Praxis repository root, or the Python payload extracted from the
    built APK (assets/chaquopy/app.imy), which is the stronger test because
    it exercises the bytecode that actually ships.
  - Aurora's real aurora_praxis_bridge.PraxisBridge runs here, talking to it
    over 127.0.0.1.

Nothing from Praxis is imported into this process -- the separation this
whole architecture rests on is kept by the test itself.  The host is driven
through a tiny stdin command channel that belongs to the harness, not to the
contract: Aurora's bridge never sees it.

Covered: cold start, discovery, the experiential loop, SIGKILL of Praxis,
Aurora continuing while Praxis is absent (fail soft), restart on the same
state with history intact, reconnect, operator pause seen only as
availability, and a protocol mismatch producing a diagnostic state.

Skips if PRAXIS_HOST_DIR is not set.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from aurora_praxis_bridge import PRAXIS_CONTRACT_VERSION, PraxisBridge

HOST_DIR = os.environ.get("PRAXIS_HOST_DIR", "").strip()
if not HOST_DIR or not Path(HOST_DIR).is_dir():
    pytest.skip("PRAXIS_HOST_DIR not set -- same-device loop not run",
                allow_module_level=True)

# The host process.  Commands on stdin, one JSON status per line on stdout.
_HOST = textwrap.dedent("""
    import json, sys
    sys.path.insert(0, {host_dir!r})
    import praxis_android_host as host
    print(host.start({state!r}, port={port}), flush=True)
    for line in sys.stdin:
        cmd = line.strip()
        if cmd in ("status", "pause", "resume", "stop"):
            print(getattr(host, cmd)(), flush=True)
""")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class _Host:
    """Harness-side handle on the Praxis process.  Not part of the contract."""

    def __init__(self, state: Path, port: int) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-c", _HOST.format(host_dir=HOST_DIR,
                                                state=str(state), port=port)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.boot = json.loads(self.proc.stdout.readline())

    def command(self, cmd: str) -> dict:
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def kill(self) -> None:
        self.proc.send_signal(signal.SIGKILL)
        self.proc.wait(timeout=10)


class _Gateway:
    def __init__(self) -> None:
        self.received = []

    def receive(self, content, stream_type=None, mode=None, **kwargs):
        self.received.append(content)
        return type("R", (), {"verdict": "ADMITTED"})()


def _systems(gateway):
    class _Enum:
        SENSOR_DATA = "SENSOR_DATA"
        BOUNDED = "BOUNDED"
    return {"aurora": type("A", (), {"gateway": gateway})(),
            "StreamType": _Enum, "ExistenceMode": _Enum}


def _wait(predicate, timeout=20.0, step=0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(step)
    return False


@pytest.fixture()
def loop(tmp_path):
    port = _free_port()
    host = _Host(tmp_path / "praxis_home", port)
    assert host.boot["status"] == "running", host.boot
    gateway = _Gateway()
    bridge = PraxisBridge(_systems(gateway), state_dir=str(tmp_path / "aurora"),
                          endpoint=f"http://127.0.0.1:{port}",
                          poll_interval_s=0.2, timeout_s=2.0)
    state = {"host": host, "port": port, "root": tmp_path}
    yield bridge, gateway, state
    bridge.stop()
    try:
        state["host"].kill()
    except Exception:
        pass


def test_the_same_device_loop_end_to_end(loop):
    bridge, gateway, state = loop

    # -- cold start and discovery ------------------------------------------
    assert bridge.handshake() == "compatible"
    assert bridge.peer["contract_version"] == PRAXIS_CONTRACT_VERSION

    # -- the experiential loop ---------------------------------------------
    bridge.start()
    assert _wait(lambda: bridge.situations_witnessed >= 3), bridge.status()
    witnessed_before_death = bridge.situations_witnessed
    history_before = state["host"].command("status")["ledger"]["emissions_recorded"]
    assert history_before >= 1

    # -- Praxis dies without warning ----------------------------------------
    state["host"].kill()
    assert _wait(lambda: bridge.status()["status"] in ("offline", "unreachable")
                 or bridge.discovery == "unreachable", timeout=15)

    # Aurora is not blocked while Praxis is absent: a direct pull returns
    # promptly (bounded by the request timeout) and nothing raises.
    started = time.time()
    assert bridge.pull_once() == 0
    assert time.time() - started < 5.0
    assert bridge.situations_witnessed == witnessed_before_death

    # -- Android restarts it on the same state -------------------------------
    state["host"] = _Host(state["root"] / "praxis_home", state["port"])
    assert state["host"].boot["status"] == "running"
    assert state["host"].boot["ledger"]["emissions_recorded"] == history_before

    # -- Aurora reconnects on her own ---------------------------------------
    bridge.last_handshake_at = 0.0          # do not wait out the retry window
    assert _wait(lambda: bridge.situations_witnessed > witnessed_before_death,
                 timeout=25), bridge.status()
    assert bridge.discovery == "compatible"
    assert bridge.status()["contract_breaches"] == 0


def test_operator_pause_reaches_aurora_only_as_availability(loop):
    bridge, _gateway, state = loop
    assert bridge.handshake() == "compatible"
    state["host"].command("pause")
    assert bridge.handshake() == "not_accepting"
    assert bridge.status()["status"] in ("paused_by_praxis", "stopped")
    # Nothing about WHY -- no laws, no goals, no scheduler state -- crosses.
    blob = json.dumps(bridge.status()).lower()
    for leak in ("law", "goal", "scheduler", "family", "draws"):
        assert leak not in blob, leak
    state["host"].command("resume")
    assert bridge.handshake() == "compatible"


def test_a_protocol_mismatch_is_a_diagnostic_state(loop, monkeypatch):
    bridge, gateway, _state = loop
    import aurora_praxis_bridge as apb
    monkeypatch.setattr(apb, "PRAXIS_PROTOCOL_VERSION", 99)
    monkeypatch.setattr(apb, "PRAXIS_COMPATIBLE_PROTOCOL_VERSIONS", (99,))
    assert bridge.handshake() == "incompatible"
    bridge.start()
    time.sleep(1.0)
    assert bridge.situations_witnessed == 0
    assert gateway.received == []
    assert bridge.status()["status"] == "incompatible"


def test_the_operator_surface_has_no_socket(loop):
    _bridge, _gateway, state = loop
    import urllib.error
    import urllib.request
    base = f"http://127.0.0.1:{state['port']}"
    for path in ("/status", "/operator/status", "/operator/inspect"):
        try:
            urllib.request.urlopen(base + path, timeout=3)
            code = 200
        except urllib.error.HTTPError as err:
            code = err.code
        assert code == 404, path
