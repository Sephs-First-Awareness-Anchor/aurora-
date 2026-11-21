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
import shutil
import subprocess
import time
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


def _startup_registration():
    """Per-user login startup, without admin rights or any command terminal."""
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--background"]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--background"]
    if os.name == "nt":
        return command, None
    return command, Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart" / "aurora.desktop"


def _is_login_enabled() -> bool:
    command, path = _startup_registration()
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run") as key:
                val, _ = winreg.QueryValueEx(key, "AuroraDesktop")
                return val == subprocess.list2cmdline(command)
        except FileNotFoundError:
            return False
    return bool(path and path.exists() and "Exec=" in path.read_text(encoding="utf-8"))


def _set_login_enabled(enabled: bool):
    command, path = _startup_registration()
    if os.name == "nt":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run") as key:
            if enabled:
                winreg.SetValueEx(key, "AuroraDesktop", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
            else:
                try:
                    winreg.DeleteValue(key, "AuroraDesktop")
                except FileNotFoundError:
                    pass
        return
    if path is None:
        raise RuntimeError("Login startup is supported on Windows and Linux desktop sessions.")
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    import shlex
    args = " ".join(shlex.quote(item) for item in command)
    path.write_text("[Desktop Entry]\\nType=Application\\nName=Aurora Background\\n" +
        "Exec=" + args + "\\nTerminal=false\\nX-GNOME-Autostart-enabled=true\\n",
        encoding="utf-8")


def run_gui(state_dir: Path):
    from PySide6.QtCore import QTimer, QUrl, Qt
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDialog, QFormLayout, QInputDialog,
        QMainWindow, QMessageBox, QScrollArea, QToolBar,
        QVBoxLayout, QWidget, QLabel, QPushButton)
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from aurora_internal.desktop.server import owner_token
    from scripts.aurora_home_setup import home_network_address
    from aurora_internal.dual_strata import strata_migration as migration
    from aurora_internal.hub_panels import strata_panel
    from aurora_internal.desktop.common import read_json
    from aurora_internal.desktop.remote_link import tailscale_status, remote_diagnostics

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

    reconnect = {"after_stop": False, "started": False, "loaded": False,
                 "backup_pending": False, "backup_in_progress": False,
                 "disabled": False}
    seen_migrations = set()
    def report_pending():
        pending = migration.load_pending(state_dir)
        if pending and pending.get("status") in ("awaiting_choice", "ready"):
            pair_review.setText("Review first pairing •")
            mid = str(pending.get("migration_id") or "")
            if mid and mid not in seen_migrations:
                seen_migrations.add(mid)
                QMessageBox.information(window, "Aurora's first pairing",
                    "A phone has sent its existing history to the desktop. "
                    "Review each store before Aurora installs anything. "
                    "Select 'Review first pairing' in the toolbar.")
        else:
            pair_review.setText("Review first pairing")

    def restart_after_save():
        if _probe(state_dir) is None:
            reconnect["after_stop"] = False
            reconnect["started"] = False
            reconnect["loaded"] = False
        else:
            _stop_resident(state_dir)
            reconnect["after_stop"] = True
            reconnect["started"] = True

    def first_pairing():
        pending = migration.load_pending(state_dir)
        if not pending:
            QMessageBox.information(window, "First pairing",
                "No phone migration is waiting. Use 'Pair phone' first, "
                "then reopen this screen once the phone uploads its history.")
            return
        if pending.get("status") == "applied":
            QMessageBox.information(window, "First pairing", "History was already migrated and verified.")
            return
        if pending.get("status") == "failed":
            QMessageBox.warning(window, "First pairing", str(pending.get("error") or "Migration failed"))
            return
        dialog = QDialog(window)
        dialog.setWindowTitle("Review Aurora's first pairing")
        dialog.resize(810, 580)
        layout = QVBoxLayout(dialog)
        summary = QLabel(
            "Review the staged phone history. Histories are unioned, present state travels "
            "with her Surface, and conflicting developmental stores require your explicit "
            "selection. A suggestion is not an automatic decision.")
        summary.setWordWrap(True)
        layout.addWidget(summary)
        report = pending.get("report") or {}
        counts = report.get("counts") or {}
        layout.addWidget(QLabel("Changes: " + ", ".join(f"{k}: {v}" for k, v in counts.items())))
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        chosen = dict(pending.get("choices") or {})
        decisions = {}
        for rel in report.get("choices_needed") or []:
            details = (report.get("stores") or {}).get(rel) or {}
            combo = QComboBox(dialog)
            suggestion = details.get("suggested", "phone")
            combo.addItem("Choose a side (suggested: " + suggestion + ")", "")
            combo.addItem("Use phone's store", "phone")
            combo.addItem("Keep desktop's store", "home")
            found = combo.findData(chosen.get(rel, ""))
            if found > 0:
                combo.setCurrentIndex(found)
            phone = details.get("phone") or {}
            home = details.get("home") or {}
            label = QLabel(
                rel + "\nPhone: " + str(phone.get("records", 0)) +
                " records · Desktop: " + str(home.get("records", 0)) + " records")
            label.setWordWrap(True)
            form.addRow(label, combo)
            decisions[rel] = combo
        if not decisions:
            form.addRow(QLabel(
                "No conflicts require manual selection. The staged change still needs your approval."))
        scroll.setWidget(content)
        layout.addWidget(scroll)
        apply_button = QPushButton("Save choices and restart to install verified state", dialog)
        layout.addWidget(apply_button)

        def apply():
            selected = {name: combo.currentData() for name, combo in decisions.items()}
            missing = [name for name, side in selected.items() if not side]
            if missing:
                QMessageBox.warning(dialog, "Choose a side", "Choose phone or desktop for all " +
                    str(len(missing)) + " conflicting stores before installing.")
                return
            confirm = QMessageBox.question(
                dialog, "Apply Aurora's first pairing?",
                "This will gracefully restart Aurora's resident, preserve migration archives, "
                "and install the verified state before opening her stores. "
                "Keep your earlier phone and desktop checkpoints until you confirm continuity.")
            if confirm != QMessageBox.StandardButton.Yes:
                return
            if selected:
                result = migration.choose(state_dir, selected)
                if not result.get("ok") or result.get("missing"):
                    QMessageBox.warning(dialog, "Migration choices", str(result))
                    return
            elif pending.get("status") != "ready":
                QMessageBox.warning(dialog, "Migration not ready", "The snapshot is still being staged.")
                return
            try:
                restart_after_save()
            except Exception as exc:
                QMessageBox.warning(dialog, "Resident restart", str(exc))
                return
            dialog.accept()
            status.setText("Applying first pairing on Aurora's next cold start...")

        apply_button.clicked.connect(apply)
        dialog.exec()

    review_action = QAction("Review first pairing", window)
    review_action.triggered.connect(first_pairing)
    toolbar.addAction(review_action)
    pair_review = review_action

    def connection_info():
        pending = migration.load_pending(state_dir) or {}
        panel = strata_panel(str(state_dir))
        diag = remote_diagnostics(read_json(state_dir / "desktop_config.json", {}))
        data = {
            "resident": "online" if _probe(state_dir) is not None else "not responding",
            "private_network": diag,
            "paired": panel.get("paired"),
            "listening": panel.get("listening"),
            "holder": panel.get("holder"),
            "devices": panel.get("devices"),
            "move": panel.get("move"),
            "first_pairing": {k: pending.get(k) for k in
                              ("status", "migration_id", "error") if k in pending},
            "downlink_enabled": panel.get("downlink_enabled"),
        }
        QMessageBox.information(window, "Aurora: remote link and devices",
            json.dumps(data, indent=2, default=str)[:7000] +
            "\\n\\nA VPN being active on this desktop does not prove the "
            "phone is reachable. Verify an actual cellular sync from the "
            "phone's Hub. Keep home powered and awake.")

    connection_action = QAction("Connection status", window)
    connection_action.triggered.connect(connection_info)
    toolbar.addAction(connection_action)

    def backup_state():
        if reconnect["backup_in_progress"] or reconnect["backup_pending"]:
            return
        confirm = QMessageBox.question(window, "Back up Aurora's history",
            "Aurora will gracefully stop, make a complete cold backup of her desktop "
            "state, and then restart. Do not close her app during the backup.")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        reconnect["backup_pending"] = True
        try:
            if _probe(state_dir) is not None:
                _stop_resident(state_dir)
                reconnect["after_stop"] = True
                reconnect["started"] = True
        except Exception as exc:
            reconnect["backup_pending"] = False
            QMessageBox.warning(window, "Backup", str(exc))

    backup_action = QAction("Back up history", window)
    backup_action.triggered.connect(backup_state)
    toolbar.addAction(backup_action)

    def cold_backup():
        from datetime import datetime
        import threading
        reconnect["backup_pending"] = False
        reconnect["backup_in_progress"] = True
        status.setText("Backing up Aurora's saved history...")
        target = state_dir.parent / ("backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        def copy():
            from aurora_internal.process_lock import ProcessLock
            try:
                with ProcessLock(state_dir / "desktop_resident.lock", blocking=False):
                    shutil.copytree(state_dir, target, ignore=shutil.ignore_patterns("desktop_resident.lock"))
                result = f"Verified cold-state copy completed: {target}"
            except Exception as exc:
                result = f"Backup failed: {type(exc).__name__}: {exc}"
            # Worker passes only plain data through the Qt event polling loop.
            reconnect["backup_result"] = result
            reconnect["backup_in_progress"] = False
            reconnect["started"] = False
        threading.Thread(target=copy, name="aurora-cold-backup", daemon=False).start()

    def ready_tick():
        if reconnect.get("backup_result"):
            message = reconnect.pop("backup_result")
            QMessageBox.information(window, "Aurora backup", message)
        if reconnect["backup_in_progress"]:
            status.setText("Backing up Aurora's saved history...")
            return
        if reconnect["disabled"]:
            status.setText("Aurora is stopped. Press Start to resume her resident.")
            return
        if reconnect["backup_pending"] and _probe(state_dir) is None and _resident_free(state_dir):
            reconnect["after_stop"] = False
            cold_backup()
            return
        if _probe(state_dir) is not None:
            status.setText("Aurora resident connected")
            reconnect["started"] = True
            if not reconnect["loaded"]:
                reconnect["loaded"] = True
                show_hub()
            report_pending()
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
        # Remote connection is the default requirement, not an optional
        # LAN address that silently fails when the phone switches to cellular.
        vpn = tailscale_status()
        if not vpn["online"]:
            reply = QMessageBox.question(
                window, "Secure connection is not ready",
                "Away-from-home pairing needs a private route that survives "
                "Wi-Fi/cellular changes. Connect Tailscale on this desktop "
                "and the phone once, using the same Tailnet.\\n\\n"
                + str(vpn["reason"]) + "\\n\\n"
                "Open the official Tailscale setup page now? "
                "Aurora will then detect your connected VPN address automatically.")
            if reply == QMessageBox.StandardButton.Yes:
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl("https://tailscale.com/download"))
            return
        host = vpn["ipv4"] or vpn["address"]
        answer = QMessageBox.question(
            window, "Pair phone over private network",
            "Desktop private VPN address: " + host + "\\n\\n"
            "The phone must have its own Tailscale connection to the same Tailnet. "
            "This keeps her link routed through the VPN on home Wi-Fi or cellular, "
            "while the desktop is powered and connected.\\n\\n"
            "Create her pairing link using this private VPN address?")
        if answer != QMessageBox.StandardButton.Yes:
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
            "The private pairing link was copied. Open Aurora on the phone → "
            "Hub → Pair with home and paste it. Keep Tailscale on both "
            "devices and keep the desktop awake. The resident will restart "
            "gracefully with the remote-capable address.")
        dialog.setInformativeText(pairing)
        dialog.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        dialog.exec()

    pair_action = QAction("Pair phone", window)
    pair_action.triggered.connect(pair_phone)
    toolbar.addAction(pair_action)
    def start_now():
        reconnect["disabled"] = False
        reconnect["started"] = False
        ready_tick()

    def stop_now():
        if QMessageBox.question(window, "Stop Aurora?",
                "Aurora will finish admitted work, save and stop. "
                "You can restart her here without using a terminal.") != QMessageBox.StandardButton.Yes:
            return
        reconnect["disabled"] = True
        try:
            if _probe(state_dir) is not None:
                _stop_resident(state_dir)
        except Exception as exc:
            QMessageBox.warning(window, "Could not stop resident", str(exc))

    def restart_now():
        reconnect["disabled"] = False
        try:
            restart_after_save()
        except Exception as exc:
            QMessageBox.warning(window, "Restart failed", str(exc))

    start_action = QAction("Start", window)
    start_action.triggered.connect(start_now)
    toolbar.addAction(start_action)
    restart_action = QAction("Restart", window)
    restart_action.triggered.connect(restart_now)
    toolbar.addAction(restart_action)
    stop_action = QAction("Stop", window)
    stop_action.triggered.connect(stop_now)
    toolbar.addAction(stop_action)

    login_action = QAction("Run at login", window)
    login_action.setCheckable(True)
    try:
        login_action.setChecked(_is_login_enabled())
    except Exception:
        pass
    def toggle_login(enabled):
        try:
            _set_login_enabled(enabled)
        except Exception as exc:
            login_action.setChecked(not enabled)
            QMessageBox.warning(window, "Startup preference", str(exc))
    login_action.toggled.connect(toggle_login)
    toolbar.addAction(login_action)
    timer = QTimer(window)
    timer.setInterval(1500)
    timer.timeout.connect(ready_tick)
    timer.start()
    window.show()
    ready_tick()
    return app.exec()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aurora Desktop App")
    parser.add_argument("--resident", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="Check runtime packaging imports")
    parser.add_argument("--state-dir", type=Path, default=_state_dir())
    args = parser.parse_args(argv)
    state = args.state_dir.expanduser().resolve()
    os.environ["AURORA_STATE_DIR"] = str(state)
    if args.resident:
        from aurora_internal.desktop.__main__ import main as resident_main
        return resident_main(["serve", "--state-dir", str(state)])
    if args.background:
        if _probe(state) is None and _resident_free(state):
            _start_resident(state)
        return 0
    if args.self_test:
        import aurora  # noqa: F401
        from aurora_internal.desktop.runtime import DesktopRuntime  # noqa: F401
        from aurora_internal.dual_strata.strata_link import StrataLinkServer  # noqa: F401
        print(json.dumps({"ok": True, "source": str(SOURCE_ROOT), "state": str(state)}))
        return 0
    return run_gui(state)


if __name__ == "__main__":
    raise SystemExit(main())
