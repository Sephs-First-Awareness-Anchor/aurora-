"""Aurora's installable Linux/Windows desktop application.

The app is a *window and resident launcher*, not a second cognition runtime.
The single existing DesktopRuntime runs in a detached resident process and
keeps the authoritative state in the user's writable data directory.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request


def configure_source():
    """Support PyInstaller's bundled Python source and the checked-out repo."""
    if getattr(sys, "frozen", False):
        root = Path(sys._MEIPASS)
    else:
        root = Path(__file__).resolve().parents[2]
    if not root.is_dir():
        raise RuntimeError(f"Aurora runtime sources are missing: {root}")
    sys.path.insert(0, str(root))
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    return root


SOURCE_ROOT = configure_source()


def _state_dir() -> Path:
    from aurora_internal.desktop.__main__ import default_state_dir
    return default_state_dir()


def _backend_command(state_dir: Path):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--resident", "--state-dir", str(state_dir)]
    return [sys.executable, str(Path(__file__).resolve()), "--resident", "--state-dir", str(state_dir)]


def _probe(state_dir: Path):
    from aurora_internal.desktop.server import owner_token
    token = owner_token(state_dir)
    req = urllib.request.Request(
        "http://127.0.0.1:8790/api/status",
        headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=0.7) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def _start_resident(state_dir: Path):
    """Best effort launch; the existing POSIX/Windows lock rejects duplicates."""
    command = _backend_command(state_dir)
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL, "cwd": str(SOURCE_ROOT),
          "close_fds": True}
    if os.name == "nt":
        kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    return subprocess.Popen(command, **kw)


def _stop_resident(state_dir: Path):
    from aurora_internal.desktop.server import owner_token
    body = json.dumps({"action": "stop"}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8790/api/owner", data=body,
        headers={"Authorization": "Bearer " + owner_token(state_dir),
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read())


def _resident_free(state_dir: Path):
    from aurora_internal.process_lock import ProcessLock
    try:
        with ProcessLock(state_dir / "desktop_resident.lock", blocking=False):
            return True
    except (BlockingIOError, PermissionError):
        return False


def _pair(state_dir: Path, host: str) -> str:
    from scripts import aurora_home_setup
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = aurora_home_setup.main(
            ["pair", "--state-dir", str(state_dir), "--host", host])
    if code:
        raise RuntimeError(output.getvalue().strip() or "Could not create pairing")
    match = re.search(r"https?://[^\s]+#[^\s]+", output.getvalue())
    if not match:
        raise RuntimeError("Pairing did not produce a private link.")
    return match.group(0)


def run_gui(state_dir: Path):
    from PySide6.QtCore import QTimer, QUrl, Qt
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QApplication, QInputDialog, QMainWindow, QMessageBox, QToolBar,
        QVBoxLayout, QWidget, QLabel)
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from aurora_internal.desktop.server import owner_token
    from scripts.aurora_home_setup import home_network_address

    state_dir.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Aurora")
    window = QMainWindow()
    window.setWindowTitle("Aurora")
    window.resize(1120, 760)
    view = QWebEngineView()
    window.setCentralWidget(view)
    toolbar = QToolBar("Aurora")
    toolbar.setMovable(False)
    window.addToolBar(toolbar)
    status = QLabel("Connecting to Aurora...")
    toolbar.addWidget(status)
    toolbar.addSeparator()

    def show_hub():
        token = owner_token(state_dir)
        view.setUrl(QUrl("http://127.0.0.1:8790/#" + token))

    open_action = QAction("Hub", window)
    open_action.triggered.connect(show_hub)
    toolbar.addAction(open_action)

    reconnect = {"after_stop": False, "started": False, "loaded": False}
    def ready_tick():
        if _probe(state_dir) is not None:
            status.setText("Aurora resident connected")
            reconnect["started"] = True
            if not reconnect["loaded"]:
                reconnect["loaded"] = True
                show_hub()
            return
        reconnect["loaded"] = False
        if reconnect["after_stop"]:
            if not _resident_free(state_dir):
                status.setText("Aurora is saving before restart...")
                return
            reconnect["after_stop"] = False
            reconnect["started"] = False
        if not reconnect["started"] and _resident_free(state_dir):
            try:
                _start_resident(state_dir)
                reconnect["started"] = True
                status.setText("Starting Aurora...")
            except OSError as exc:
                status.setText(f"Cannot launch resident: {exc}")
            return
        status.setText("Waiting for Aurora resident...")

    def pair_phone():
        host, ok = QInputDialog.getText(
            window, "Pair Android Surface",
            "Desktop address the phone can reach (LAN or private VPN IPv4):",
            text=home_network_address())
        if not ok:
            return
        host = host.strip()
        if not host or any(c in host for c in " /\\#?@"):
            QMessageBox.warning(window, "Invalid address", "Enter a LAN or private VPN IP address/hostname.")
            return
        try:
            pairing = _pair(state_dir, host)
            if _probe(state_dir) is not None:
                _stop_resident(state_dir)
                reconnect["after_stop"] = True
                reconnect["started"] = True
            else:
                reconnect["started"] = False
                reconnect["loaded"] = False
        except Exception as exc:
            QMessageBox.warning(window, "Pairing error", str(exc))
            return
        QApplication.clipboard().setText(pairing)
        dialog = QMessageBox(window)
        dialog.setWindowTitle("Pair Android Surface")
        dialog.setText(
            "The private pairing link was copied to your clipboard. "
            "Paste it into Android Aurora → Hub → Pair with home. "
            "The desktop resident will restart gracefully with this address.")
        dialog.setInformativeText(pairing)
        dialog.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        dialog.exec()

    pair_action = QAction("Pair phone", window)
    pair_action.triggered.connect(pair_phone)
    toolbar.addAction(pair_action)
    timer = QTimer(window)
    timer.setInterval(1200)
    timer.timeout.connect(ready_tick)
    timer.start()
    window.show()
    ready_tick()
    return app.exec()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aurora Desktop App")
    parser.add_argument("--resident", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="Check runtime packaging imports")
    parser.add_argument("--state-dir", type=Path, default=_state_dir())
    args = parser.parse_args(argv)
    state = args.state_dir.expanduser().resolve()
    os.environ["AURORA_STATE_DIR"] = str(state)
    if args.resident:
        from aurora_internal.desktop.__main__ import main as resident_main
        return resident_main(["serve", "--state-dir", str(state)])
    if args.self_test:
        import aurora  # noqa: F401
        from aurora_internal.desktop.runtime import DesktopRuntime  # noqa: F401
        from aurora_internal.dual_strata.strata_link import StrataLinkServer  # noqa: F401
        print(json.dumps({"ok": True, "source": str(SOURCE_ROOT), "state": str(state)}))
        return 0
    return run_gui(state)


if __name__ == "__main__":
    raise SystemExit(main())
