#!/usr/bin/env python3
"""Shared persistence utilities for Aurora."""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import os
import threading
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

PERSISTENCE_LOCK = threading.RLock()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Dict[str, Any], *, indent: int = 2, default=None) -> bool:
    """Atomically write JSON to disk under a process-wide persistence lock."""
    tmp = None
    with PERSISTENCE_LOCK:
        try:
            _ensure_parent(path)
            fd, tmp = __import__('tempfile').mkstemp(dir=str(path.parent), suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, default=default)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            return False


def write_breach_report(state_dir: Path, report: Dict[str, Any]) -> Optional[Path]:
    try:
        report_dir = state_dir / "breach_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        path = report_dir / f"breach_{ts}.json"
        payload = dict(report)
        payload.setdefault("timestamp", time.time())
        atomic_write_json(path, payload, indent=2, default=str)
        return path
    except Exception:
        return None


def monotonic_check(previous: Dict[str, Any], current: Dict[str, Any], keys: Dict[str, str]) -> Dict[str, Any]:
    """Return monotonicity violations where numeric values decreased."""
    violations = []
    for label, key in keys.items():
        prev = previous.get(key)
        cur = current.get(key)
        if isinstance(prev, (int, float)) and isinstance(cur, (int, float)) and cur < prev:
            violations.append({"field": key, "label": label, "previous": prev, "current": cur})
    return {"ok": not violations, "violations": violations}


def checksum_dict(data: Dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Cross-device persistence: Drive sync + Device awareness
# ---------------------------------------------------------------------------

import socket
import subprocess
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class DeviceRecord:
    """Record of a device that has hosted Aurora."""
    hostname:      str
    last_seen:     float
    last_sync:     float
    session_count: int   = 1
    notes:         str   = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "DeviceRecord":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


class DeviceAwareness:
    """
    Tracks which device Aurora is running on.
    Detects device switches and flags them so Aurora can acknowledge continuity.

    Device log: aurora_state/device_log.json
    """

    DEVICE_LOG_PATH = "aurora_state/device_log.json"

    def __init__(self):
        self.current_hostname: str = socket.gethostname()
        self._devices: Dict[str, DeviceRecord] = {}
        self._previous_hostname: Optional[str] = None
        self._device_switched: bool = False
        self._switch_note: str = ""
        self.load()

    def check(self) -> Dict:
        """
        Run on boot. Returns device switch info dict.
        Keys: switched (bool), from_hostname, to_hostname, message
        """
        # Find previous hostname (most recently seen, not current)
        other_devices = [d for h, d in self._devices.items()
                         if h != self.current_hostname]
        if other_devices:
            prev = max(other_devices, key=lambda d: d.last_seen)
            self._previous_hostname = prev.hostname
        else:
            self._previous_hostname = None

        # Update or create current device record
        now = time.time()
        if self.current_hostname in self._devices:
            self._devices[self.current_hostname].last_seen = now
            self._devices[self.current_hostname].session_count += 1
        else:
            self._devices[self.current_hostname] = DeviceRecord(
                hostname=self.current_hostname,
                last_seen=now,
                last_sync=0.0,
            )

        self._device_switched = (self._previous_hostname is not None and
                                  self._previous_hostname != self.current_hostname)

        if self._device_switched:
            self._switch_note = (
                f"Device switched from '{self._previous_hostname}' "
                f"to '{self.current_hostname}'"
            )
            logger.info(f"[DeviceAwareness] {self._switch_note}")
        else:
            self._switch_note = ""

        self.save()

        return {
            "switched":       self._device_switched,
            "from_hostname":  self._previous_hostname,
            "to_hostname":    self.current_hostname,
            "message":        self._switch_note,
            "session_count":  self._devices[self.current_hostname].session_count,
        }

    def record_sync(self):
        """Call after a successful sync to record timestamp."""
        if self.current_hostname in self._devices:
            self._devices[self.current_hostname].last_sync = time.time()
            self.save()

    def device_switched(self) -> bool:
        return self._device_switched

    def switch_message(self) -> str:
        return self._switch_note

    def save(self):
        data = {
            "version": "1.0",
            "devices": {h: d.to_dict() for h, d in self._devices.items()},
            "timestamp": time.time(),
        }
        os.makedirs(os.path.dirname(self.DEVICE_LOG_PATH), exist_ok=True)
        try:
            import tempfile
            dirp = os.path.dirname(os.path.abspath(self.DEVICE_LOG_PATH))
            fd, tmp = tempfile.mkstemp(dir=dirp, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.DEVICE_LOG_PATH)
        except Exception as e:
            logger.debug(f"[DeviceAwareness] Save failed: {e}")

    def load(self):
        if not os.path.exists(self.DEVICE_LOG_PATH):
            return
        try:
            with open(self.DEVICE_LOG_PATH) as f:
                data = json.load(f)
            for h, d in data.get("devices", {}).items():
                self._devices[h] = DeviceRecord.from_dict(d)
        except Exception:
            pass

    def all_devices(self) -> List[Dict]:
        return [{"hostname": h, **d.to_dict()} for h, d in self._devices.items()]


# ============================================================================
# SECTION 2: RCLONE INTERFACE
# ============================================================================

class RcloneInterface:
    """
    Thin wrapper around the rclone binary.
    Handles sync, check, and availability detection.
    """

    def __init__(self,
                 remote_name: str = "gdrive",
                 remote_path: str = "Aurora/aurora_state",
                 local_path:  str = "aurora_state"):
        self.remote_name = remote_name
        self.remote_path = remote_path
        self.local_path  = local_path
        self._available: Optional[bool] = None
        self._rclone_path = self._find_rclone()

    def _find_rclone(self) -> str:
        """Find rclone binary path."""
        for candidate in ["rclone", "/usr/bin/rclone", "/usr/local/bin/rclone",
                          os.path.expanduser("~/bin/rclone")]:
            try:
                result = subprocess.run([candidate, "version"],
                                        capture_output=True, timeout=5)
                if result.returncode == 0:
                    return candidate
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "rclone"  # will fail gracefully later

    def is_available(self) -> bool:
        """Check if rclone is installed and configured."""
        if self._available is not None:
            return self._available
        try:
            result = subprocess.run(
                [self._rclone_path, "listremotes"],
                capture_output=True, text=True, timeout=10
            )
            self._available = (result.returncode == 0 and
                                self.remote_name + ":" in result.stdout)
            if not self._available:
                logger.info(f"[rclone] Remote '{self.remote_name}' not found. "
                            f"Run: rclone config")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._available = False
            logger.info("[rclone] rclone not found. Install from https://rclone.org/install/")
        return self._available

    @property
    def remote_full(self) -> str:
        return f"{self.remote_name}:{self.remote_path}"

    def sync_up(self, dry_run: bool = False) -> Dict:
        """Push local → remote."""
        return self._run_sync(self.local_path, self.remote_full, dry_run)

    def sync_down(self, dry_run: bool = False) -> Dict:
        """Pull remote → local."""
        return self._run_sync(self.remote_full, self.local_path, dry_run)

    def _run_sync(self, src: str, dst: str, dry_run: bool = False) -> Dict:
        """Run rclone sync src → dst."""
        if not self.is_available():
            return {"success": False, "reason": "rclone_unavailable"}

        cmd = [self._rclone_path, "sync", src, dst,
               "--transfers", "4",
               "--checkers", "8",
               "--contimeout", "30s",
               "--timeout", "60s",
               "--retries", "2",
               "--low-level-retries", "5",
               "--stats", "0",
               "-q"]

        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            success = result.returncode == 0
            return {
                "success": success,
                "returncode": result.returncode,
                "stderr": result.stderr[:500] if not success else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "timeout"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def check_newer_remote(self) -> bool:
        """
        Check if remote has a newer aurora_state.json than local.
        Returns True if remote is newer (should pull).
        """
        if not self.is_available():
            return False

        local_file = os.path.join(self.local_path, "aurora_state.json")
        local_mtime = os.path.getmtime(local_file) if os.path.exists(local_file) else 0.0

        try:
            cmd = [self._rclone_path, "lsjson",
                   f"{self.remote_full}/aurora_state.json",
                   "--no-modtime=false"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0 or not result.stdout.strip():
                return False

            items = json.loads(result.stdout)
            if not items:
                return False

            # Parse rclone's ModTime (RFC3339)
            from datetime import timezone
            mod_time_str = items[0].get("ModTime", "")
            if not mod_time_str:
                return False

            # Try parsing
            try:
                from datetime import datetime as dt
                if mod_time_str.endswith("Z"):
                    mod_time_str = mod_time_str[:-1] + "+00:00"
                remote_dt = dt.fromisoformat(mod_time_str)
                remote_mtime = remote_dt.timestamp()
                return remote_mtime > local_mtime + 60  # 60s grace period
            except Exception:
                return False

        except Exception:
            return False


# ============================================================================
# SECTION 3: DRIVE SYNC ORCHESTRATOR
# ============================================================================

class DriveSync:
    """
    Aurora's cross-device memory bridge via Google Drive + rclone.

    Boot sequence:
      1. DeviceAwareness.check() — detect device switch
      2. If remote newer → sync_down (pull latest state)
      3. Start background thread syncing up every interval_seconds

    Background thread:
      - Every interval_seconds: sync_up
      - On failure: log quietly, use local backup
      - Always keeps local state intact
    """

    DEFAULT_INTERVAL = 300.0   # 5 minutes

    def __init__(self,
                 remote_name:    str = "gdrive",
                 local_path:     str = "aurora_state",
                 sync_interval:  float = DEFAULT_INTERVAL):

        self.device       = DeviceAwareness()
        self.rclone       = RcloneInterface(remote_name=remote_name,
                                            local_path=local_path)
        self.interval     = sync_interval
        self.local_path   = local_path

        self._thread: Optional[threading.Thread] = None
        self._running   = False
        self._lock      = threading.Lock()
        self._last_sync_time: float = 0.0
        self._last_sync_result: Dict = {}
        self._sync_count: int = 0
        self._device_info: Dict = {}

    # ----------------------------------------------------------------
    # Boot sequence
    # ----------------------------------------------------------------

    def boot(self) -> Dict:
        """
        Call on Aurora startup. Checks device, pulls if needed.
        Returns dict with device_switch info and sync result.
        """
        # Step 1: Device awareness check
        device_info = self.device.check()
        self._device_info = device_info

        # Step 2: Check if remote is newer (pull if so)
        pull_result = {"performed": False}
        if self.rclone.is_available():
            try:
                if self.rclone.check_newer_remote():
                    logger.info("[DriveSync] Remote is newer — pulling state")
                    pull_result = self.rclone.sync_down()
                    pull_result["performed"] = True
                    if pull_result.get("success"):
                        self.device.record_sync()
            except Exception as e:
                logger.debug(f"[DriveSync] Boot pull check failed: {e}")
        else:
            logger.info("[DriveSync] rclone unavailable — running from local state only")

        return {
            "device": device_info,
            "pull":   pull_result,
            "rclone_available": self.rclone.is_available(),
        }

    # ----------------------------------------------------------------
    # Manual sync
    # ----------------------------------------------------------------

    def force_sync(self) -> Dict:
        """Force an immediate upload to Drive. Returns result dict."""
        if not self.rclone.is_available():
            return {"success": False, "reason": "rclone_unavailable"}
        result = self.rclone.sync_up()
        if result.get("success"):
            self.device.record_sync()
            self._last_sync_time = time.time()
            self._sync_count += 1
        self._last_sync_result = result
        return result

    # ----------------------------------------------------------------
    # Background thread
    # ----------------------------------------------------------------

    def start(self):
        """Start background sync thread."""
        if self._thread and self._thread.is_alive():
            return
        self._running = True

        def _loop():
            while self._running:
                time.sleep(self.interval)
                if self._running:
                    try:
                        result = self.rclone.sync_up()
                        with self._lock:
                            self._last_sync_result = result
                            self._last_sync_time = time.time()
                            self._sync_count += 1
                        if result.get("success"):
                            self.device.record_sync()
                        else:
                            logger.debug(f"[DriveSync] Background sync failed: "
                                         f"{result.get('reason', 'unknown')}")
                    except Exception as e:
                        logger.debug(f"[DriveSync] Background sync error: {e}")

        self._thread = threading.Thread(target=_loop, daemon=True,
                                         name="DriveSyncBackground")
        self._thread.start()
        logger.info(f"[DriveSync] Background sync started (every {self.interval}s)")

    def stop(self):
        self._running = False

    # ----------------------------------------------------------------
    # Status / awareness
    # ----------------------------------------------------------------

    def device_switched(self) -> bool:
        return self.device.device_switched()

    def switch_message(self) -> str:
        return self.device.switch_message()

    def get_device_info(self) -> Dict:
        return self._device_info

    def status(self) -> Dict:
        with self._lock:
            return {
                "rclone_available":   self.rclone.is_available(),
                "current_device":     self.device.current_hostname,
                "device_switched":    self.device.device_switched(),
                "last_sync_time":     self._last_sync_time,
                "last_sync_ago_s":    (time.time() - self._last_sync_time
                                       if self._last_sync_time else None),
                "sync_count":         self._sync_count,
                "last_sync_result":   self._last_sync_result,
                "sync_interval_s":    self.interval,
                "background_running": (self._thread is not None and
                                       self._thread.is_alive()),
                "all_devices":        self.device.all_devices(),
            }


# ============================================================================
# SECTION 3b: GIT STATE SYNC
# ============================================================================

class GitStateSync:
    """
    Git-backed cross-device state sync — works on every device with git.

    Boot:  fetch + fast-forward merge → all devices start from same state
    Push:  stage aurora_state/ changes, commit with hostname+timestamp, push

    Complements DriveSync: when rclone isn't configured this is the primary
    mechanism ensuring consistent state across Android, desktop, and cloud.
    """

    def __init__(self, state_dir: str = "aurora_state",
                 remote: str = "origin", branch: str = ""):
        self.state_dir = state_dir
        self.remote    = remote
        self.branch    = branch
        self._repo_root: Optional[str] = None
        self._available: Optional[bool] = None
        self._current_branch: str = ""

    def _find_repo_root(self) -> Optional[str]:
        if self._repo_root is not None:
            return self._repo_root
        cwd = (os.path.abspath(self.state_dir)
               if os.path.isdir(self.state_dir) else os.getcwd())
        try:
            r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True, timeout=10, cwd=cwd)
            if r.returncode == 0:
                self._repo_root = r.stdout.strip()
                return self._repo_root
        except Exception:
            pass
        return None

    def _get_current_branch(self, repo_root: str) -> str:
        try:
            r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                               capture_output=True, text=True, timeout=10, cwd=repo_root)
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return ""

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = self._find_repo_root() is not None
        return self._available

    def boot(self) -> Dict:
        """Pull latest state from remote on boot."""
        root = self._find_repo_root()
        if root is None:
            return {"performed": False, "reason": "not_a_git_repo"}

        branch = self.branch or self._get_current_branch(root)
        if not branch or branch == "HEAD":
            return {"performed": False, "reason": "detached_head"}
        self._current_branch = branch

        try:
            fetch_r = subprocess.run(
                ["git", "fetch", self.remote, branch, "--quiet"],
                capture_output=True, text=True, timeout=30, cwd=root)
            if fetch_r.returncode != 0:
                return {"performed": False,
                        "reason": f"fetch_failed: {fetch_r.stderr[:200]}"}
        except Exception as e:
            return {"performed": False, "reason": f"fetch_error: {e}"}

        try:
            behind_r = subprocess.run(
                ["git", "rev-list", "--count",
                 f"HEAD..{self.remote}/{branch}"],
                capture_output=True, text=True, timeout=10, cwd=root)
            behind = int(behind_r.stdout.strip() or "0")
        except Exception:
            behind = 0

        if behind == 0:
            return {"performed": True, "success": True,
                    "reason": "already_up_to_date", "pulled_files": 0}

        try:
            pull_r = subprocess.run(
                ["git", "merge", "--ff-only",
                 f"{self.remote}/{branch}"],
                capture_output=True, text=True, timeout=30, cwd=root)
            if pull_r.returncode == 0:
                files_r = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD@{1}", "HEAD",
                     "--", self.state_dir],
                    capture_output=True, text=True, timeout=10, cwd=root)
                nfiles = len([l for l in files_r.stdout.splitlines() if l.strip()])
                logger.info(f"[GitStateSync] Pulled {nfiles} state file(s) from {branch}")
                return {"performed": True, "success": True,
                        "reason": "pulled", "pulled_files": nfiles,
                        "behind": behind}
            else:
                logger.debug(f"[GitStateSync] ff-only merge failed (local diverged): "
                             f"{pull_r.stderr[:200]}")
                return {"performed": True, "success": False,
                        "reason": f"ff_failed: {pull_r.stderr[:200]}"}
        except Exception as e:
            return {"performed": True, "success": False,
                    "reason": f"merge_error: {e}"}

    def push_state(self, message: str = "") -> Dict:
        """Stage aurora_state/ changes and push."""
        root = self._find_repo_root()
        if root is None:
            return {"performed": False, "reason": "not_a_git_repo"}

        branch = self._current_branch or self._get_current_branch(root)
        if not branch or branch == "HEAD":
            return {"performed": False, "reason": "detached_head"}

        try:
            status_r = subprocess.run(
                ["git", "status", "--porcelain", "--", self.state_dir],
                capture_output=True, text=True, timeout=10, cwd=root)
            if not status_r.stdout.strip():
                return {"performed": True, "success": True,
                        "reason": "nothing_to_commit", "committed": False}
        except Exception as e:
            return {"performed": False, "reason": f"status_error: {e}"}

        try:
            add_r = subprocess.run(
                ["git", "add", "--", self.state_dir],
                capture_output=True, text=True, timeout=15, cwd=root)
            if add_r.returncode != 0:
                return {"performed": True, "success": False,
                        "reason": f"add_failed: {add_r.stderr[:200]}"}
        except Exception as e:
            return {"performed": True, "success": False,
                    "reason": f"add_error: {e}"}

        hostname = socket.gethostname()
        ts = int(time.time())
        msg = message or f"state: {hostname} {ts}"
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Aurora",
            "GIT_AUTHOR_EMAIL": "aurora@local",
            "GIT_COMMITTER_NAME": "Aurora",
            "GIT_COMMITTER_EMAIL": "aurora@local",
        }
        try:
            commit_r = subprocess.run(
                ["git", "-c", "commit.gpgsign=false",
                 "commit", "-m", msg],
                capture_output=True, text=True, timeout=15,
                cwd=root, env=git_env)
            if commit_r.returncode != 0:
                return {"performed": True, "success": False,
                        "reason": f"commit_failed: {commit_r.stderr[:200]}",
                        "committed": False}
        except Exception as e:
            return {"performed": True, "success": False,
                    "reason": f"commit_error: {e}", "committed": False}

        try:
            push_r = subprocess.run(
                ["git", "push", self.remote, branch, "--quiet"],
                capture_output=True, text=True, timeout=60, cwd=root)
            success = push_r.returncode == 0
            if success:
                logger.info(f"[GitStateSync] Pushed state to {branch}")
            else:
                logger.debug(f"[GitStateSync] Push failed: {push_r.stderr[:200]}")
            return {"performed": True, "success": success, "committed": True,
                    "reason": "pushed" if success else
                    f"push_failed: {push_r.stderr[:200]}"}
        except Exception as e:
            return {"performed": True, "success": False, "committed": True,
                    "reason": f"push_error: {e}"}

    def status(self) -> Dict:
        root = self._find_repo_root()
        return {
            "git_available": self.is_available(),
            "repo_root": root,
            "branch": self._current_branch,
            "remote": self.remote,
        }


