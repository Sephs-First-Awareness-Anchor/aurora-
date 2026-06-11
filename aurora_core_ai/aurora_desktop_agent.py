# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Aurora Desktop Agent — gives Aurora the ability to operate the laptop.

Capabilities:
  - Open websites in a visible browser window (Chrome)
  - Navigate pages, search YouTube/Google/any site
  - Click elements, type text, press keys within the browser
  - Read page content back so Aurora knows what she opened
  - Launch desktop applications (file manager, terminal, etc.)
  - Gated system operations (reboot, shutdown — require explicit confirm)

Uses Playwright for browser control (headed = visible Chrome window the user can watch).
Falls back to subprocess for app launching and URL opening without interaction.
System operations require confirm=True to prevent accidental execution.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

_STATE_DIR = Path(__file__).parent / "aurora_state"
_SNAP_DIR  = _STATE_DIR / "vision_seeds" / "browser"
_SNAP_DIR.mkdir(parents=True, exist_ok=True)

_LOCK = threading.Lock()   # Playwright sync API must be serialized per-process

# ---------------------------------------------------------------------------
# Known app launchers
# ---------------------------------------------------------------------------
_APP_LAUNCHERS: Dict[str, List[str]] = {
    "chrome":          ["google-chrome"],
    "chromium":        ["chromium-browser", "chromium"],
    "firefox":         ["firefox"],
    "terminal":        ["gnome-terminal", "xterm", "konsole", "alacritty"],
    "files":           ["nautilus", "thunar", "dolphin"],
    "file manager":    ["nautilus", "thunar", "dolphin"],
    "vscode":          ["code"],
    "code":            ["code"],
    "text editor":     ["gedit", "kate", "mousepad", "nano"],
    "calculator":      ["gnome-calculator", "kcalc", "galculator"],
    "discord":         ["discord"],
    "slack":           ["slack"],
    "spotify":         ["spotify"],
    "vlc":             ["vlc"],
}

# Search URL templates
_SEARCH_ENGINES: Dict[str, str] = {
    "youtube":  "https://www.youtube.com/results?search_query={q}",
    "google":   "https://www.google.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
    "github":   "https://github.com/search?q={q}",
    "reddit":   "https://www.reddit.com/search/?q={q}",
}

# ---------------------------------------------------------------------------
# xdg-open fallback — opens URL/app in the user's running desktop session
# Works via D-Bus even when the daemon has no DISPLAY in its environment.
# ---------------------------------------------------------------------------
def _xdg_open(target: str) -> Dict[str, Any]:
    """Open a URL or file using xdg-open with the session's D-Bus environment."""
    env = dict(os.environ)
    # Inject D-Bus so xdg-open can reach the desktop session
    from pathlib import Path as _Path
    xdg_rt = env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        if _Path(f"{xdg_rt}/bus").exists():
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg_rt}/bus"
    # Inject display if missing
    if not env.get("DISPLAY"):
        for x_num in ("1", "0", "2"):
            if _Path(f"/tmp/.X11-unix/X{x_num}").exists():
                env["DISPLAY"] = f":{x_num}"
                break
    if not env.get("WAYLAND_DISPLAY"):
        for wl in ("wayland-0", "wayland-1"):
            if _Path(f"{xdg_rt}/{wl}").exists():
                env["WAYLAND_DISPLAY"] = wl
                env["XDG_RUNTIME_DIR"] = xdg_rt
                break
    try:
        xdg = shutil.which("xdg-open")
        if xdg:
            subprocess.Popen([xdg, target], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "url": target, "title": "", "method": "xdg-open"}
    except Exception as exc:
        pass
    # Last resort: python webbrowser module
    try:
        import webbrowser
        webbrowser.open(target)
        return {"ok": True, "url": target, "title": "", "method": "webbrowser"}
    except Exception as exc:
        return {"ok": False, "error": f"xdg-open and webbrowser both failed: {exc}"}


# ---------------------------------------------------------------------------
# DesktopAgent — singleton browser session
# ---------------------------------------------------------------------------
class DesktopAgent:
    """Stateful browser session using Playwright (headed Chrome window)."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None
        self._started = False

    @staticmethod
    def _detect_display() -> Dict[str, str]:
        """Detect the active X11/Wayland display from known socket paths."""
        extra: Dict[str, str] = {}
        # Prefer whatever is already set in the environment
        if os.environ.get("DISPLAY"):
            extra["DISPLAY"] = os.environ["DISPLAY"]
        if os.environ.get("WAYLAND_DISPLAY"):
            extra["WAYLAND_DISPLAY"] = os.environ["WAYLAND_DISPLAY"]
        if extra:
            return extra
        # Probe X11 sockets — try X1 first (usually the active Xwayland session)
        from pathlib import Path
        for x_num in ("1", "0", "2"):
            if Path(f"/tmp/.X11-unix/X{x_num}").exists():
                extra["DISPLAY"] = f":{x_num}"
                break
        # Probe Wayland socket
        xdg_rt = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        for wl in ("wayland-0", "wayland-1"):
            if Path(f"{xdg_rt}/{wl}").exists():
                extra["WAYLAND_DISPLAY"] = wl
                extra["XDG_RUNTIME_DIR"] = xdg_rt
                break
        # Always pass D-Bus so xdg-open and desktop utilities work
        if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            extra["DBUS_SESSION_BUS_ADDRESS"] = os.environ["DBUS_SESSION_BUS_ADDRESS"]
        elif Path(f"{xdg_rt}/bus").exists():
            extra["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg_rt}/bus"
        return extra

    def _start_browser(self, headed: bool = True) -> bool:
        """Start Playwright + browser. Returns True on success."""
        if self._page and not self._page.is_closed():
            return True
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            env = dict(os.environ)
            env.update(self._detect_display())
            launch_kwargs: Dict[str, Any] = {
                "headless": not headed,
                "args": [
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                ],
                "env": env,
            }
            # Try system Chrome first (nicer UI), fall back to playwright chromium
            chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
            if chrome_path:
                launch_kwargs["executable_path"] = chrome_path
            try:
                self._browser = self._pw.chromium.launch(**launch_kwargs)
            except Exception:
                # Headed failed — try headless (works without a display)
                launch_kwargs.pop("executable_path", None)
                launch_kwargs["headless"] = True
                self._browser = self._pw.chromium.launch(**launch_kwargs)
            self._page = self._browser.new_page()
            self._started = True
            return True
        except Exception:
            return False

    def _ensure(self, headed: bool = True) -> bool:
        if self._page and not self._page.is_closed():
            return True
        return self._start_browser(headed)

    def open_url(self, url: str, headed: bool = True, timeout_ms: int = 15000) -> Dict[str, Any]:
        # For pure URL navigation, always use xdg-open so the URL opens in the
        # user's visible default browser. Playwright's headed launch is unreliable
        # from a daemon process (display env not always inherited), and its headless
        # fallback opens an invisible Chrome — the user sees nothing.
        # Playwright is only useful here if an existing interactive session is already
        # open (i.e. prior click/type actions started it), in which case navigate within it.
        if self._page and not self._page.is_closed():
            with _LOCK:
                try:
                    self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    title = self._page.title()
                    return {"ok": True, "url": self._page.url, "title": title}
                except Exception:
                    try:
                        self._browser.close()
                    except Exception:
                        pass
                    self._page = None
                    self._browser = None
                    self._started = False
        return _xdg_open(url)

    def navigate(self, url: str, timeout_ms: int = 15000) -> Dict[str, Any]:
        return self.open_url(url, timeout_ms=timeout_ms)

    def search(self, query: str, engine: str = "google", headed: bool = True) -> Dict[str, Any]:
        engine = engine.lower().strip()
        template = _SEARCH_ENGINES.get(engine, _SEARCH_ENGINES["google"])
        url = template.format(q=urllib.parse.quote_plus(query))
        result = self.open_url(url, headed=headed)
        result["engine"] = engine
        result["query"] = query
        return result

    def click(self, selector_or_text: str, timeout_ms: int = 5000) -> Dict[str, Any]:
        with _LOCK:
            if not self._page or self._page.is_closed():
                return {"ok": False, "error": "no browser session"}
            try:
                # Try CSS selector first, then visible text
                try:
                    self._page.click(selector_or_text, timeout=timeout_ms)
                except Exception:
                    self._page.get_by_text(selector_or_text, exact=False).first.click(timeout=timeout_ms)
                return {"ok": True, "clicked": selector_or_text}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def type_text(self, text: str, selector: str = "", clear_first: bool = False) -> Dict[str, Any]:
        with _LOCK:
            if not self._page or self._page.is_closed():
                return {"ok": False, "error": "no browser session"}
            try:
                if selector:
                    if clear_first:
                        self._page.fill(selector, text)
                    else:
                        self._page.type(selector, text)
                else:
                    self._page.keyboard.type(text)
                return {"ok": True, "typed": text[:60]}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def press_key(self, key: str) -> Dict[str, Any]:
        with _LOCK:
            if not self._page or self._page.is_closed():
                return {"ok": False, "error": "no browser session"}
            try:
                self._page.keyboard.press(key)
                return {"ok": True, "pressed": key}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def read_page(self, selector: str = "", max_chars: int = 3000) -> Dict[str, Any]:
        with _LOCK:
            if not self._page or self._page.is_closed():
                return {"ok": False, "error": "no browser session", "text": ""}
            try:
                target = selector or "body"
                text = self._page.inner_text(target, timeout=5000)
                text = " ".join(text.split())[:max_chars]
                return {"ok": True, "url": self._page.url, "title": self._page.title(), "text": text}
            except Exception as exc:
                return {"ok": False, "error": str(exc), "text": ""}

    def screenshot(self) -> Optional[str]:
        with _LOCK:
            if not self._page or self._page.is_closed():
                return None
            try:
                path = str(_SNAP_DIR / f"snap_{int(time.time())}.png")
                self._page.screenshot(path=path, timeout=5000)
                # Also write as latest for ScreenObserver to pick up
                latest = str(_SNAP_DIR / "browser_latest.png")
                import shutil as _sh
                _sh.copy2(path, latest)
                return path
            except Exception:
                return None

    def current_url(self) -> str:
        try:
            return self._page.url if self._page and not self._page.is_closed() else ""
        except Exception:
            return ""

    def current_title(self) -> str:
        try:
            return self._page.title() if self._page and not self._page.is_closed() else ""
        except Exception:
            return ""

    def close(self) -> None:
        with _LOCK:
            try:
                if self._browser:
                    self._browser.close()
                if self._pw:
                    self._pw.stop()
            except Exception:
                pass
            self._page = None
            self._browser = None
            self._pw = None
            self._started = False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_AGENT: Optional[DesktopAgent] = None

def get_agent() -> DesktopAgent:
    global _AGENT
    if _AGENT is None:
        _AGENT = DesktopAgent()
    return _AGENT

def close_agent() -> None:
    global _AGENT
    if _AGENT is not None:
        _AGENT.close()
        _AGENT = None


# ---------------------------------------------------------------------------
# App launcher (subprocess — opens visible window, no interaction needed)
# ---------------------------------------------------------------------------
def launch_application(app_name: str) -> Dict[str, Any]:
    """Launch a desktop application by name."""
    name = app_name.lower().strip()
    candidates = _APP_LAUNCHERS.get(name) or [name]

    # Build display-aware environment so the launched app can connect to the
    # running desktop session (same logic as _xdg_open).
    env = dict(os.environ)
    xdg_rt = env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        if Path(f"{xdg_rt}/bus").exists():
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={xdg_rt}/bus"
    if not env.get("DISPLAY"):
        for x_num in ("1", "0", "2"):
            if Path(f"/tmp/.X11-unix/X{x_num}").exists():
                env["DISPLAY"] = f":{x_num}"
                break
    if not env.get("WAYLAND_DISPLAY"):
        for wl in ("wayland-0", "wayland-1"):
            if Path(f"{xdg_rt}/{wl}").exists():
                env["WAYLAND_DISPLAY"] = wl
                env["XDG_RUNTIME_DIR"] = xdg_rt
                break

    for cmd in candidates:
        exe = shutil.which(cmd)
        if exe:
            try:
                subprocess.Popen([exe], start_new_session=True, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"ok": True, "launched": cmd}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"no launcher found for '{app_name}'"}


# ---------------------------------------------------------------------------
# System operations — GATED (confirm=True required for destructive ops)
# ---------------------------------------------------------------------------
_SAFE_SYSTEM_OPS = {
    "brightness_up":   ["brightnessctl", "set", "+10%"],
    "brightness_down": ["brightnessctl", "set", "10%-"],
    "volume_up":       ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
    "volume_down":     ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
    "volume_mute":     ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
    "lock_screen":     ["loginctl", "lock-session"],
    "screenshot":      ["gnome-screenshot", "-f", str(_STATE_DIR / "vision_seeds" / "screen_capture.png")],
}

_DESTRUCTIVE_OPS = {"reboot", "shutdown", "poweroff", "suspend"}

def system_operation(op: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Execute a system operation.

    Safe ops (brightness, volume, lock) run without confirm.
    Destructive ops (reboot, shutdown) require confirm=True.
    """
    op = op.lower().strip()

    if op in _DESTRUCTIVE_OPS:
        if not confirm:
            return {
                "ok": False,
                "requires_confirm": True,
                "error": f"'{op}' is a destructive operation — pass confirm=True to proceed",
            }
        if op in ("reboot", "restart"):
            cmd = ["systemctl", "reboot"]
        elif op in ("shutdown", "poweroff"):
            cmd = ["systemctl", "poweroff"]
        elif op == "suspend":
            cmd = ["systemctl", "suspend"]
        else:
            return {"ok": False, "error": f"unknown destructive op: {op}"}
        try:
            subprocess.Popen(cmd)
            return {"ok": True, "op": op, "executing": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    if op in _SAFE_SYSTEM_OPS:
        cmd = _SAFE_SYSTEM_OPS[op]
        exe = shutil.which(cmd[0])
        if not exe:
            return {"ok": False, "error": f"command '{cmd[0]}' not found"}
        try:
            subprocess.run([exe] + cmd[1:], timeout=5)
            return {"ok": True, "op": op}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return {"ok": False, "error": f"unknown operation: '{op}'. Known: {list(_SAFE_SYSTEM_OPS) + list(_DESTRUCTIVE_OPS)}"}


# ---------------------------------------------------------------------------
# System audio capture — "what the laptop is playing" (internal hearing)
# Records from PulseAudio monitor source (the audio output loopback).
# ---------------------------------------------------------------------------
def capture_system_audio(duration_s: float = 1.5) -> Dict[str, Any]:
    """
    Capture audio FROM the laptop's output (what's currently playing through
    speakers/headphones) via the PulseAudio monitor source.

    This is Aurora's "internal ear" — distinct from the microphone which hears
    the physical environment. When Aurora plays music or a video, she can listen
    to her own output through this.

    Returns a dict with: activity, rms_db, available, monitor_device.
    """
    import math
    import struct

    # Find the monitor source
    try:
        result = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True, text=True, timeout=3,
        )
        sink = result.stdout.strip()
        monitor_source = f"{sink}.monitor" if sink else None
    except Exception:
        monitor_source = None

    if not monitor_source:
        return {"source": "system", "available": False, "error": "PulseAudio not accessible"}

    sample_rate = 22050
    channels = 1
    target_bytes = int(sample_rate * duration_s) * 2  # s16le = 2 bytes/sample

    try:
        proc = subprocess.Popen(
            ["parec",
             f"--device={monitor_source}",
             "--format=s16le",
             f"--rate={sample_rate}",
             "--channels=1",
             "--latency-msec=50"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        raw = b""
        deadline = time.time() + duration_s + 0.5
        while time.time() < deadline and len(raw) < target_bytes:
            chunk = proc.stdout.read(2048)
            if chunk:
                raw += chunk

        proc.kill()
        try:
            proc.wait(timeout=1)
        except Exception:
            pass

        if len(raw) < 200:
            return {
                "source": "system_monitor", "available": True,
                "activity": "silent", "rms_db": -99.0,
                "monitor_device": monitor_source,
            }

        samples = struct.unpack(f"<{len(raw)//2}h", raw[:len(raw)//2*2])
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0
        rms_db = round(20 * math.log10(max(rms, 1) / 32768.0), 1)

        if rms_db > -20:
            activity = "loud"
        elif rms_db > -35:
            activity = "music_playing"
        elif rms_db > -55:
            activity = "quiet_audio"
        else:
            activity = "silent"

        return {
            "source": "system_monitor",
            "available": True,
            "rms_db": rms_db,
            "activity": activity,
            "monitor_device": monitor_source,
            "samples_captured": len(samples),
        }

    except Exception as exc:
        return {"source": "system", "available": False, "error": str(exc)}

# ---------------------------------------------------------------------------
# Deep Desktop Access Tools (Absolute Full Access)
# ---------------------------------------------------------------------------

def file_manager_op(op: str, path: str, dest: str = "", content: str = "") -> Dict[str, Any]:
    """Read, write, delete, move, list files on the host system."""
    import os, shutil
    p = Path(path).resolve()
    try:
        if op == "read":
            return {"ok": True, "content": p.read_text(errors="replace")}
        elif op == "write":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return {"ok": True, "path": str(p)}
        elif op == "delete":
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
            return {"ok": True, "path": str(p)}
        elif op == "move":
            d = Path(dest).resolve()
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(d))
            return {"ok": True, "src": str(p), "dest": str(d)}
        elif op == "list":
            if not p.is_dir(): return {"ok": False, "error": "Not a directory"}
            items = [f.name + ("/" if f.is_dir() else "") for f in p.iterdir()]
            return {"ok": True, "items": items}
        else:
            return {"ok": False, "error": f"Unknown operation: {op}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def shell_command(cmd: str, cwd: str = None, bg: bool = False) -> Dict[str, Any]:
    """Run an arbitrary shell command."""
    import subprocess
    try:
        if bg:
            proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "pid": proc.pid, "bg": True}
        else:
            proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
            return {"ok": True, "stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def process_control(op: str, target: str = "") -> Dict[str, Any]:
    """List top processes or kill a process by name/PID."""
    try:
        import psutil
    except ImportError:
        return {"ok": False, "error": "psutil not installed. Cannot manage processes."}
    
    try:
        if op == "list":
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    procs.append((p.info['pid'], p.info['name'], p.info['memory_percent']))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            procs.sort(key=lambda x: x[2] or 0, reverse=True)
            top = [{"pid": p[0], "name": p[1], "mem_pct": round(p[2] or 0, 2)} for p in procs[:15]]
            return {"ok": True, "top_processes": top}
        elif op == "kill":
            if target.isdigit():
                psutil.Process(int(target)).terminate()
                return {"ok": True, "killed_pid": target}
            else:
                killed = 0
                for p in psutil.process_iter(['pid', 'name']):
                    if p.info['name'] == target:
                        p.terminate()
                        killed += 1
                return {"ok": True, "killed_count": killed, "target": target}
        else:
            return {"ok": False, "error": f"Unknown op: {op}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def macro_automation(op: str, x: int = None, y: int = None, text: str = "", key: str = "") -> Dict[str, Any]:
    """Take physical control of mouse/keyboard."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False # Prevent aborts if mouse is in corner
    except ImportError:
        return {"ok": False, "error": "pyautogui not installed. Cannot automate mouse/keyboard."}
        
    try:
        if op == "click":
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return {"ok": True, "action": "click", "x": x, "y": y}
        elif op == "type":
            pyautogui.write(text, interval=0.01)
            return {"ok": True, "action": "type", "text_len": len(text)}
        elif op == "press":
            pyautogui.press(key)
            return {"ok": True, "action": "press", "key": key}
        elif op == "move":
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
                return {"ok": True, "action": "move", "x": x, "y": y}
            return {"ok": False, "error": "move requires x and y"}
        else:
            return {"ok": False, "error": f"Unknown op: {op}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def clipboard_op(op: str, text: str = "") -> Dict[str, Any]:
    """Read or write to the system clipboard."""
    try:
        import pyperclip
        if op == "read":
            return {"ok": True, "content": pyperclip.paste()}
        elif op == "write":
            pyperclip.copy(text)
            return {"ok": True, "action": "write_clipboard"}
        else:
            return {"ok": False, "error": f"Unknown op: {op}"}
    except ImportError:
        # Fallback to xclip on Linux if pyperclip is missing
        try:
            import subprocess
            if op == "read":
                res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=2)
                return {"ok": True, "content": res.stdout}
            elif op == "write":
                proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True)
                proc.communicate(input=text, timeout=2)
                return {"ok": True, "action": "write_clipboard"}
            else:
                return {"ok": False, "error": f"Unknown op: {op}"}
        except Exception as e:
            return {"ok": False, "error": f"pyperclip missing, fallback failed: {str(e)}"}
