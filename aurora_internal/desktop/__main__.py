"""python -m aurora_internal.desktop {serve,status,open,stop}"""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def default_state_dir():
    if os.environ.get("AURORA_STATE_DIR"):
        return Path(os.environ["AURORA_STATE_DIR"]).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Aurora" / "state"
    return Path.home() / ".local" / "share" / "aurora" / "state"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aurora resident desktop")
    ap.add_argument("command", choices=["serve", "status", "open", "stop"], nargs="?", default="serve")
    ap.add_argument("--state-dir", type=Path, default=default_state_dir())
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--open", action="store_true", dest="open_hub")
    args = ap.parse_args(argv)
    root = args.state_dir.expanduser().resolve()
    os.environ["AURORA_STATE_DIR"] = str(root)
    os.environ["AURORA_SKIP_DEP_INSTALL"] = "1"
    from .server import owner_token, make_server
    token = owner_token(root)
    url = f"http://127.0.0.1:{args.port}"
    if args.command == "open":
        webbrowser.open(url + "/#" + token)
        return 0
    if args.command in {"status", "stop"}:
        data = json.dumps({"action": "stop"}).encode() if args.command == "stop" else None
        req = urllib.request.Request(url + ("/api/owner" if data else "/api/status"), data=data,
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            print(response.read().decode())
        return 0
    root.mkdir(parents=True, exist_ok=True)
    from aurora_internal.process_lock import ProcessLock
    from .common import read_json
    from .runtime import DesktopRuntime
    config = read_json(root / "desktop_config.json", {})
    # On Windows the resident itself owns the idle-sleep request. A window
    # process cannot hold it reliably after the window closes. OS shutdown,
    # explicit sleep and battery/power policy still take precedence.
    if os.name == "nt" and config.get("AURORA_KEEP_HOME_AWAKE"):
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            previous = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            if not previous:
                print("Aurora: OS refused idle sleep guard")
        except Exception as exc:
            print(f"Aurora: idle sleep guard unavailable: {exc}")
    for name in ("AURORA_PRAXIS_URL", "AURORA_STRATA_LINK_HOST", "AURORA_STRATA_LINK_PORT", "AURORA_ACM_BRIDGE", "AURORA_ACM_PORT"):
        if name in config:
            os.environ[name] = str(config[name])
    try:
        with ProcessLock(root / "desktop_resident.lock", blocking=False):
            import sys
            log = open(root / "desktop_resident.log", "a", encoding="utf-8", buffering=1)
            original_out, original_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = log
            runtime = DesktopRuntime(root)
            server = make_server(runtime, port=args.port, token=token)
            runtime.start()
            def lifecycle():
                while True:
                    if runtime._stop.wait(.5):
                        # Preserve recovery access until the field finishes and
                        # its normal save completes. Never kill a live turn.
                        if runtime.stop(timeout=.2):
                            server.shutdown()
                            return
            threading.Thread(target=lifecycle, daemon=True).start()
            if args.open_hub:
                webbrowser.open(url + "/#" + token)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                runtime._stop.set()
                while not runtime.stop(timeout=.5):
                    pass
            finally:
                server.server_close()
                sys.stdout, sys.stderr = original_out, original_err
                log.close()
            return 0
    except (BlockingIOError, PermissionError, OSError) as exc:
        if args.open_hub:
            webbrowser.open(url + "/#" + token)
        print(f"Resident did not start: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
