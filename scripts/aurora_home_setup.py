#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_home_setup.py -- setting up the desktop as her home, in as few steps
as possible (surface restructure: easy setup on both ends).

    python3 scripts/aurora_home_setup.py pair
        Chooses this machine's address on the home network, names this
        desktop, and prints the one line to paste on the phone
        (Hub tab -> Subsurface link -> tap).  Restart the stack afterwards
        (scripts/strata_stack.sh restart) so home listens on that address.

    python3 scripts/aurora_home_setup.py status
        Who holds her, the devices home knows, a move under way, each phone's
        first pairing, and whether home is reachable from the network.

    python3 scripts/aurora_home_setup.py first-pairing [--accept-suggested]
                                                       [--side store=phone|home ...]
                                                       [--apply] [--restart-stack]
        A phone that lived as the whole mind sends its history home when it
        pairs.  This shows what differs, records your choice for each store
        (or takes the side that has lived more, with --accept-suggested), and
        with --apply installs it.  Applying is done with the resident stopped;
        --restart-stack stops it, applies, and starts it again.

Nothing here decides anything about her.  It sets up where home listens,
what this desktop is called, and carries out Sir's own choices.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aurora_internal.dual_strata import strata_link as sl          # noqa: E402
from aurora_internal.dual_strata import strata_migration as sm     # noqa: E402
from aurora_internal.process_lock import ProcessLock
from aurora_internal.desktop.__main__ import default_state_dir
from aurora_internal.desktop.common import write_json
from aurora_internal.hub_panels import strata_panel                # noqa: E402


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def home_network_address() -> str:
    """This machine's address on its local network.  Connecting a UDP socket
    sends nothing; it only asks the system which interface would be used."""
    for probe in ("10.255.255.255", "192.168.255.255", "172.31.255.255"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((probe, 1))
            address = sock.getsockname()[0]
            if address and not address.startswith("127."):
                return address
        except OSError:
            continue
        finally:
            sock.close()
    return ""


def _native_resident_running(state_dir: Path) -> bool:
    """Check the unified desktop resident's cross-platform process lock."""
    try:
        with ProcessLock(state_dir / "desktop_resident.lock", blocking=False):
            return False
    except (BlockingIOError, PermissionError):
        return True


def _resident_running(state_dir: Path) -> bool:
    """The resident runs from the stack's pid file or as a systemd service
    (scripts/strata_stack.sh starts it either way)."""
    if os.name == "nt":
        return False  # The Windows resident uses desktop_resident.lock, never a POSIX pid.
    pid_file = state_dir / "strata_stack" / "pids" / "subsurface.pid"
    try:
        pid = int(pid_file.read_text().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, IndexError):
        pass
    for scope in ([], ["--user"]):
        try:
            done = subprocess.run(["systemctl", *scope, "is-active", "aurora-subsurface.service"],
                                  capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.stdout.strip() == "active":
            return True
    return False


def cmd_pair(args) -> int:
    state_dir = Path(args.state_dir)
    link = sl.link_dir(state_dir)
    host = args.host or home_network_address()
    if not host:
        print("Couldn't find this machine's address on the home network. "
              "Pass it with --host (for example --host 192.168.1.20).")
        return 1
    # A resident reads desktop_config.json before starting its listener. Preserve
    # the other settings, including configurations written by Windows PowerShell.
    config_path = state_dir / "desktop_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else {}
    port = args.port if args.port is not None else int(config.get("AURORA_STRATA_LINK_PORT")
                                                       or os.environ.get("AURORA_STRATA_LINK_PORT") or sl.DEFAULT_PORT)
    if not 1 <= port <= 65535:
        print("Choose a port from 1 to 65535.")
        return 1
    if host in {"0.0.0.0", "::"}:
        print("Choose the address the phone can dial on the desktop's private network.")
        return 1
    config.update(AURORA_STRATA_LINK_HOST=host, AURORA_STRATA_LINK_PORT=port)
    write_json(config_path, config)
    (link / "listen_host.txt").write_text(host, encoding="utf-8")
    if args.name or not (link / "device_name.txt").exists():
        (link / "device_name.txt").write_text((args.name or "desktop")[:64], encoding="utf-8")
    line = sl.pairing_line(state_dir, host, port)
    print("Home will listen on", f"{host}:{port}", "as", repr(sl.device_name(state_dir)))
    print()
    print("On the phone: Hub tab -> Subsurface link -> tap, and paste this line:")
    print()
    print("   ", line)
    print()
    print("Keep it private: it is the key to the link.")
    if _native_resident_running(state_dir):
        print("Restart the unified resident to listen on the new address.")
    elif _resident_running(state_dir):
        print("Legacy stack is running; use its own restart controls, not both runtimes.")
    return 0


def cmd_status(args) -> int:
    panel = strata_panel(args.state_dir)
    pending = sm.load_pending(args.state_dir)
    _print({
        "paired": panel.get("paired"),
        "listening": panel.get("listening"),
        "holder": panel.get("holder"),
        "devices": panel.get("devices"),
        "move": panel.get("move"),
        "recent_moves": panel.get("recent_moves"),
        "first_pairing": panel.get("first_pairing"),
        "first_pairing_waiting": None if not pending else {
            "migration_id": pending.get("migration_id"), "status": pending.get("status"),
            "choices_needed": len(pending.get("report", {}).get("choices_needed", [])),
            "choices_made": len(pending.get("choices") or {})},
        "shared_inquiry": panel.get("shared_inquiry"),
        "downlink_enabled": panel.get("downlink_enabled"),
    })
    return 0


def cmd_first_pairing(args) -> int:
    state_dir = Path(args.state_dir)
    pending = sm.load_pending(state_dir)
    if not pending:
        print("No phone has sent its history home yet. Pair the phone first; "
              "it starts sending as soon as it is paired.")
        return 0
    if pending.get("status") == "applied":
        print("This first pairing is already applied. The phone becomes her surface at its next start.")
        return 0
    sides = dict(s.split("=", 1) for s in args.side if "=" in s)
    if sides or args.accept_suggested:
        result = sm.choose(state_dir, sides, accept_suggested=args.accept_suggested)
        if not result.get("ok"):
            _print(result)
            return 1
    sm.main(["report", "--state-dir", str(state_dir)])
    if not args.apply:
        print("\nWhen every store has a side, run again with --apply "
              "(add --restart-stack to stop and start the stack around it).")
        return 0
    stack = REPO_ROOT / "scripts" / "strata_stack.sh"
    if _native_resident_running(state_dir):
        print("The unified resident owns this state. Choices have been saved; "
              "restart the resident gracefully to apply them before its stores open. "
              "Do not launch the legacy strata stack.")
        return 1
    running = _resident_running(state_dir)
    if running and not args.restart_stack:
        print("The resident is running. Applying is done with it stopped: "
              "add --restart-stack, or stop it yourself first.")
        return 1
    if running:
        subprocess.run(["bash", str(stack), "stop"], check=True)
    try:
        # The same OS lock as the native resident. Hold it throughout the
        # installation so a login task cannot start between a check and apply.
        try:
            with ProcessLock(state_dir / "desktop_resident.lock", blocking=False):
                result = sm.apply_pending_migration(state_dir)
        except (BlockingIOError, PermissionError):
            print("The desktop state is in use. Restart the resident after choosing stores. "
                  "It applies the ready migration before opening its stores.")
            return 1
        _print(result or {"status": "nothing_ready"})
        ok = result is not None and result.get("ok")
    finally:
        if running:
            subprocess.run(["bash", str(stack), "start"], check=True)
    if ok:
        print("\nApplied. The phone picks up the receipt by itself and becomes her surface at its next start.")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Set up this desktop as Aurora's home.")
    parser.add_argument("command", choices=("pair", "status", "first-pairing"))
    parser.add_argument("--state-dir", default=default_state_dir())
    parser.add_argument("--host", default="", help="pair: the address the phone dials (found automatically)")
    parser.add_argument("--port", type=int)
    parser.add_argument("--name", default="", help="pair: what this desktop is called (default: desktop)")
    parser.add_argument("--side", action="append", default=[], help="first-pairing: store=phone or store=home")
    parser.add_argument("--accept-suggested", action="store_true",
                        help="first-pairing: take the side that has lived more for every store not chosen")
    parser.add_argument("--apply", action="store_true", help="first-pairing: install it now")
    parser.add_argument("--restart-stack", action="store_true",
                        help="first-pairing --apply: stop the stack, apply, start it again")
    args = parser.parse_args(argv)
    Path(args.state_dir).mkdir(parents=True, exist_ok=True)
    return {"pair": cmd_pair, "status": cmd_status, "first-pairing": cmd_first_pairing}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
