"""Discover and operate host services through Aurora's existing device adapters.

Inventory is evidence of OS exposure. Only an attempted operation verifies access.
The injected provider/adapter seam is also used for hardware-free integration tests.
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .common import digest, read_json, write_json
from .policy import HostPolicy

# Fixed read-only script: no user text is interpolated into PowerShell.
WINDOWS_INVENTORY = r"""+$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
@{
 os = @(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture,TotalVisibleMemorySize)
 cpu = @(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
 gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion)
 storage = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace)
 devices = @(Get-CimInstance Win32_PnPEntity | Select-Object Name,PNPClass,Status,DeviceID)
 network = @(Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,LinkSpeed)
 services = @(Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode)
 software = @(Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher)
} | ConvertTo-Json -Depth 5 -Compress
"""


def discover_host():
    out = {"platform": platform.system(), "machine": platform.machine(),
           "cpu_count": os.cpu_count(), "devices": [], "errors": []}
    if platform.system() == "Windows":
        try:
            p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_INVENTORY],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
            if p.returncode:
                raise OSError(p.stderr.strip()[:400])
            out.update(json.loads(p.stdout.lstrip("\ufeff")))
        except Exception as exc:
            out["errors"].append(f"Windows inventory: {exc}")
    try:
        import sounddevice
        out["audio"] = [dict(d) for d in sounddevice.query_devices()]
    except Exception as exc:
        out["audio"] = []
        out["errors"].append(f"Audio enumeration: {type(exc).__name__}")
    out["adapters"] = {name: importlib.util.find_spec(module) is not None for name, module in
                       {"camera": "cv2", "microphone": "sounddevice", "speaker": "pyttsx3",
                        "screen": "PIL", "browser": "playwright", "input": "pyautogui"}.items()}
    out["applications"] = {name: exe for name in ("msedge", "chrome", "firefox", "code", "notepad", "calc")
                           if (exe := shutil.which(name))}
    return out


class HostServices:
    def __init__(self, state_dir, systems, *, provider=discover_host, adapter=None, observer=None):
        self.state_dir = Path(state_dir)
        self.systems = systems
        self.policy = HostPolicy(systems)
        self.provider = provider
        self.adapter = adapter or self._existing_adapter
        self.observer = observer
        self._lock = threading.RLock()
        self.inventory = read_json(self.state_dir / "host_inventory.json", {})
        self.access = {}
        self.last_refresh = 0.0
        self.active = True
        self.sensors = read_json(self.state_dir / "desktop_sensors.json", {})

    def sensor_control(self, device, enabled):
        if device not in {"camera", "microphone", "screen"}:
            raise ValueError("unsupported continuous sensor")
        self.sensors[device] = bool(enabled)
        write_json(self.state_dir / "desktop_sensors.json", self.sensors)
        return dict(self.sensors)

    def dependency_version(self, name, params):
        # Only structure consequential to this operation invalidates it. A new
        # unrelated USB device or free-space reading must not erase learning.
        structure = {"platform": self.inventory.get("platform"), "operation": name}
        if name == "host_probe":
            device = str(params.get("device") or "")
            structure["adapter"] = self.inventory.get("adapters", {}).get(device)
            structure["devices"] = [r for r in self.inventory.get("devices", [])
                                    if device.lower() in str(r).lower()]
        else:
            adapter_source = Path(__file__).resolve().parents[2] / "aurora_desktop_agent.py"
            structure["adapter_source"] = __import__("hashlib").sha256(adapter_source.read_bytes()).hexdigest()
        return digest(structure)

    def refresh(self):
        with self._lock:
            inventory = self.provider()
            inventory["version"] = digest(inventory)
            changed = inventory["version"] != self.inventory.get("version")
            self.inventory = inventory
            self.last_refresh = time.time()
            write_json(self.state_dir / "host_inventory.json", inventory)
            if changed and self.observer:
                self.observer({"kind": "host_inventory", "inventory": inventory,
                               "epistemic_status": "observed_os_exposure", "timestamp": self.last_refresh})
            return self.status()

    def status(self):
        return {"active": self.active, "inventory": self.inventory, "access": dict(self.access),
                "continuous_sensors": dict(self.sensors),
                "last_refresh": self.last_refresh,
                "permission_note": "Adapter presence and OS enumeration do not verify physical access."}

    def snapshot(self, name, params):
        if name == "desktop_file_manager" and params.get("path"):
            p = Path(params["path"]).expanduser()
            try:
                stat = p.stat()
                return {"exists": True, "directory": p.is_dir(), "size": stat.st_size,
                        "sha256": __import__("hashlib").sha256(p.read_bytes()).hexdigest()
                        if p.is_file() and stat.st_size <= 1_048_576 else None}
            except FileNotFoundError:
                return {"exists": False}
        return {"inventory_version": self.inventory.get("version"),
                "access": self.access.get(name, {}).copy()}

    def execute(self, name, params=None):
        params = dict(params or {})
        reason = self.policy.check(name, params)
        if reason or not self.active:
            return {"ok": False, "error": reason or "services_stopped", "authorized": False}
        with self._lock:
            before = self.snapshot(name, params)
            started = time.monotonic()
            try:
                result = dict(self.adapter(name, params))
            except Exception as exc:
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}
            result["authorized"] = True
            self.access[name] = {"verified": bool(result.get("ok")), "attempted_at": time.time(),
                                 "error": result.get("error", ""),
                                 "duration_ms": round((time.monotonic() - started) * 1000, 2)}
            after = self.snapshot(name, params)
            event = {"kind": "host_operation", "operation": name, "parameters": params,
                     "before": before, "after": after, "result": result,
                     "inventory_version": self.inventory.get("version"), "timestamp": time.time(),
                     "dependency_version": self.dependency_version(name, params),
                     "epistemic_status": "observed_operation"}
            if self.observer:
                self.observer(event)
            return {**result, "observation": event}

    def _existing_adapter(self, name, params):
        import aurora_desktop_agent as desktop
        if name == "host_probe":
            device = str(params.get("device") or "")
            if device == "camera":
                from aurora_hardware_io import capture_frame
                path = capture_frame(str(self.state_dir / "vision_seeds" / "camera" / "frame_latest.png"))
                hw = self.systems.get("hardware")
                if path and hw is not None and hasattr(hw, "process_visual"):
                    import cv2
                    hw.process_visual(cv2.imread(path))
                return {"ok": bool(path), "path": path, "error": "" if path else "camera_unavailable"}
            if device == "microphone":
                import sounddevice
                sample = sounddevice.rec(1600, samplerate=16000, channels=1, blocking=True)
                hw = self.systems.get("hardware")
                if hw is not None and hasattr(hw, "process_audio"):
                    hw.process_audio(sample.flatten().tolist(), sample_rate=16000)
                return {"ok": bool(len(sample)), "frames": len(sample)}
            if device == "screen":
                from PIL import ImageGrab
                frame = ImageGrab.grab()
                path = self.state_dir / "vision_seeds" / "screen_latest.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                frame.save(path)
                hw = self.systems.get("hardware")
                if hw is not None and hasattr(hw, "process_visual"):
                    import numpy as np
                    hw.process_visual(np.asarray(frame))
                return {"ok": True, "path": str(path), "size": list(frame.size)}
            if device == "speaker":
                if (self.state_dir / "quiet_mode").exists():
                    return {"ok": False, "error": "quiet_mode"}
                import pyttsx3
                engine = pyttsx3.init()
                try:
                    engine.say(str(params.get("text") or "Aurora audio check"))
                    engine.runAndWait()
                finally:
                    engine.stop()
                return {"ok": True, "audibility": "requires_owner_confirmation"}
            return {"ok": False, "error": "unknown_device"}
        mapping = {"desktop_launch_app": desktop.launch_application, "desktop_file_manager": desktop.file_manager_op,
                   "desktop_shell_command": desktop.shell_command, "desktop_system_action": desktop.system_operation,
                   "desktop_process_control": desktop.process_control, "desktop_macro": desktop.macro_automation,
                   "desktop_clipboard": desktop.clipboard_op, "desktop_media_capture": desktop.capture_system_audio}
        if name in mapping:
            return mapping[name](**params)
        # Browser methods live on the calling worker: Playwright is thread-affine.
        agent = desktop.get_agent()
        if name == "desktop_open_url":
            from aurora_internal.tool_registry import _external_ai_url_forbidden
            if _external_ai_url_forbidden(str(params.get("url") or "")):
                return {"ok": False, "error": "external_ai_model_use_forbidden_by_architecture"}
            return agent.open_url(**params)
        if name == "desktop_search":
            return agent.search(**params)
        if name == "desktop_browser_action":
            from aurora_internal.tool_registry import _external_ai_url_forbidden
            if _external_ai_url_forbidden(agent.current_url()):
                return {"ok": False, "error": "external_ai_model_use_forbidden_by_architecture"}
            action = params.get("action")
            if action == "read":
                return agent.read_page(selector=params.get("target", ""))
            if action == "url":
                return {"ok": True, "url": agent.current_url(), "title": agent.current_title()}
            if action == "screenshot":
                path = agent.screenshot()
                return {"ok": bool(path), "path": path}
            if action == "click":
                return agent.click(params.get("target", ""))
            if action == "type":
                return agent.type_text(params.get("text", ""), selector=params.get("target", ""))
            if action == "press":
                return agent.press_key(params.get("target") or params.get("text", ""))
        return {"ok": False, "error": "unsupported_host_operation"}
