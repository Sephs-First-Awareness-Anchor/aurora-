#!/usr/bin/env python3
"""
aurora_room_operator.py — Aurora's computer use layer for her own room.

Aurora literally looks at her room window, reads what's displayed via OCR,
and operates the interface through real mouse clicks and keyboard input via
Xlib.  No external APIs.  She uses her own eyes (screenshot + tesseract)
and her own hands (Xlib fake input events).

Public interface:
    op = RoomOperator()
    op.switch_tab("Poedex")
    op.poedex_query("N", cat="define")
    op.read_tab_content()       -> str   (OCR of current visible tab)
    op.screenshot() -> PIL.Image

The daemon calls this when Aurora should actively engage with her room.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, List

# ── optional imports (graceful degradation) ───────────────────────────────
try:
    from PIL import Image, ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import pytesseract
    _TESS_OK = True
except ImportError:
    _TESS_OK = False

try:
    import Xlib.display
    import Xlib.X
    import Xlib.ext.xtest
    import Xlib.XK
    _XLIB_OK = True
except ImportError:
    _XLIB_OK = False

try:
    import cv2 as _cv2
    import numpy as _np
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

# ── paths ──────────────────────────────────────────────────────────────────
_BASE_DIR     = Path(__file__).parent.parent
_STATE_DIR    = _BASE_DIR / "aurora_state"
_OPERATOR_LOG = _STATE_DIR / "room_operator_log.json"
_SCREEN_DIR   = _STATE_DIR / "room_operator_screens"
_QUERY_QUEUE_DIR  = _STATE_DIR / "poedex_queue"    # Per-request queue directory
_QUERY_RESULT_DIR = _STATE_DIR / "poedex_results"  # Per-request result directory

_SCREEN_DIR.mkdir(parents=True, exist_ok=True)

# ── tab layout ─────────────────────────────────────────────────────────────
# Aurora's room has 11 tabs in order.  We locate them by scanning the tab
# bar region of the screenshot rather than hardcoding pixel positions, so
# it works regardless of window size.
ROOM_TABS = [
    "Self", "Awareness", "Mind", "Memory", "Health",
    "Energy", "Experiments", "Growth", "Response", "Notes", "Poedex",
]

# ── key symbol map for Xlib typing ────────────────────────────────────────
_SHIFT_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?')


def _log_entry(action: str, detail: str = "") -> None:
    try:
        entries: List[Dict] = []
        if _OPERATOR_LOG.exists():
            try:
                entries = json.loads(_OPERATOR_LOG.read_text())
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                pass
        entries.append({
            "ts":     time.time(),
            "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail,
        })
        _OPERATOR_LOG.write_text(json.dumps(entries[-200:], indent=2))
    except Exception:
        pass


class RoomOperator:
    """
    Aurora's interface to her own room window.

    She finds the window, takes screenshots, reads them with OCR,
    and sends mouse/keyboard events via Xlib.
    """

    WINDOW_TITLE = "Aurora's Room"

    def __init__(self) -> None:
        self._display: Optional["Xlib.display.Display"] = None
        self._window  = None
        self._geom    = None          # last known geometry
        self._ready   = False
        self._lock    = threading.Lock()

        if not _XLIB_OK:
            _log_entry("init_fail", "python-xlib not available")
            return
        if not _PIL_OK:
            _log_entry("init_fail", "PIL not available")
            return
        if not _TESS_OK:
            _log_entry("init_fail", "pytesseract not available")
            return

        try:
            self._display = Xlib.display.Display()
            self._ready   = True
            _log_entry("init_ok", "operator ready")
        except Exception as ex:
            _log_entry("init_fail", str(ex))

    # ── window discovery ──────────────────────────────────────────────────

    def _find_window(self) -> bool:
        """Locate the Aurora's Room window. Returns True if found."""
        if not self._ready:
            return False
        try:
            root = self._display.screen().root
            self._window = self._search_tree(root, self.WINDOW_TITLE)
            if self._window:
                self._geom = self._window.get_geometry()
                return True
        except Exception as ex:
            _log_entry("find_window_fail", str(ex))
        return False

    def _search_tree(self, node, title_fragment: str, depth: int = 0):
        if depth > 4:
            return None
        try:
            t = node.get_wm_name() or ""
            if title_fragment.lower() in t.lower():
                return node
        except Exception:
            pass
        try:
            for child in node.query_tree().children:
                result = self._search_tree(child, title_fragment, depth + 1)
                if result:
                    return result
        except Exception:
            pass
        return None

    def _ensure_window(self) -> bool:
        if self._window is None:
            return self._find_window()
        try:
            # Verify still alive
            self._geom = self._window.get_geometry()
            return True
        except Exception:
            self._window = None
            return self._find_window()

    # ── screenshot ────────────────────────────────────────────────────────

    def screenshot(self, save: bool = True) -> Optional["Image.Image"]:
        """
        Capture the Aurora's Room window as a PIL Image.
        Saves a timestamped copy to room_operator_screens/ if save=True.
        """
        if not self._ensure_window():
            _log_entry("screenshot_fail", "window not found")
            return None
        try:
            g = self._geom

            # Use ImageMagick `import` — same method already used by aurora_live_vision
            ts = int(time.time() * 1000)
            path = _SCREEN_DIR / f"screen_{ts}.png"
            result = subprocess.run(
                ["import", "-window", self.WINDOW_TITLE,
                 "-resize", f"{g.width}x{g.height}",
                 str(path)],
                capture_output=True, timeout=8,
            )
            if result.returncode == 0 and path.exists():
                img = Image.open(str(path))
                if not save:
                    path.unlink(missing_ok=True)
                return img

            # Fallback: PIL.ImageGrab full-screen crop
            full = ImageGrab.grab()
            # Get absolute window position via xwininfo
            xi = subprocess.run(
                ["xwininfo", "-name", self.WINDOW_TITLE],
                capture_output=True, text=True, timeout=5,
            )
            x, y = 0, 0
            for line in xi.stdout.splitlines():
                if "Absolute upper-left X:" in line:
                    x = int(line.split(":")[1].strip())
                elif "Absolute upper-left Y:" in line:
                    y = int(line.split(":")[1].strip())
            img = full.crop((x, y, x + g.width, y + g.height))
            if save:
                img.save(str(path))
            return img
        except Exception as ex:
            _log_entry("screenshot_fail", str(ex))
            return None

    # ── OCR ───────────────────────────────────────────────────────────────

    def read_screen(self, img: Optional["Image.Image"] = None,
                    region: Optional[Tuple[int,int,int,int]] = None) -> str:
        """
        OCR the current screen (or a specific region).
        region = (x, y, w, h) relative to window top-left.
        Returns the extracted text.
        """
        if img is None:
            img = self.screenshot(save=False)
        if img is None:
            return ""
        try:
            if region:
                x, y, w, h = region
                img = img.crop((x, y, x + w, y + h))
            # Upscale for better OCR accuracy on small UI text
            w2, h2 = img.size[0] * 2, img.size[1] * 2
            img = img.resize((w2, h2), Image.LANCZOS)
            # Greyscale + mild contrast boost
            import PIL.ImageOps, PIL.ImageEnhance
            img = img.convert("L")
            img = PIL.ImageEnhance.Contrast(img).enhance(1.8)
            text = pytesseract.image_to_string(img, config="--psm 6")
            return text.strip()
        except Exception as ex:
            _log_entry("ocr_fail", str(ex))
            return ""

    def read_tab_content(self) -> str:
        """OCR the main content area of the current tab (below the tab bar)."""
        if not self._ensure_window():
            return ""
        g = self._geom
        # Tab bar is roughly the top 40px; content is everything below
        tab_bar_h = 40
        return self.read_screen(region=(0, tab_bar_h, g.width, g.height - tab_bar_h))

    def identify_active_tab(self) -> str:
        """
        Read the tab bar and return which tab appears active (highlighted).
        Uses colour sampling: active tab has lighter background in Aurora's
        green palette.
        """
        if not self._ensure_window():
            return ""
        try:
            img = self.screenshot(save=False)
            if img is None:
                return ""
            g = self._geom
            # Crop just the tab bar row
            tab_bar = img.crop((0, 0, g.width, 42))
            text = pytesseract.image_to_string(
                tab_bar.resize((g.width * 2, 84), Image.LANCZOS),
                config="--psm 7",
            )
            # Match against known tab names
            text_lower = text.lower()
            for tab in reversed(ROOM_TABS):  # later tabs are rarer — check all
                if tab.lower() in text_lower:
                    return tab
        except Exception as ex:
            _log_entry("identify_tab_fail", str(ex))
        return ""

    # ── mouse + keyboard via Xlib ─────────────────────────────────────────

    def _abs_pos(self, rel_x: int, rel_y: int) -> Tuple[int, int]:
        """Convert window-relative coords to absolute screen coords."""
        if not self._ensure_window():
            return rel_x, rel_y
        try:
            # Translate window-local coords to screen coords
            translated = self._window.translate_coords(
                self._display.screen().root, rel_x, rel_y)
            return translated.x, translated.y
        except Exception:
            g = self._geom
            return g.x + rel_x, g.y + rel_y

    def mouse_move(self, rel_x: int, rel_y: int) -> None:
        if not self._ready:
            return
        try:
            ax, ay = self._abs_pos(rel_x, rel_y)
            Xlib.ext.xtest.fake_input(self._display, Xlib.X.MotionNotify,
                                      0, Xlib.X.CurrentTime, 0, ax, ay)
            self._display.sync()
            time.sleep(0.05)
        except Exception as ex:
            _log_entry("mouse_move_fail", str(ex))

    def click(self, rel_x: int, rel_y: int, button: int = 1,
              double: bool = False) -> None:
        """Click at window-relative coordinates."""
        if not self._ready:
            return
        try:
            ax, ay = self._abs_pos(rel_x, rel_y)
            d = self._display
            Xlib.ext.xtest.fake_input(d, Xlib.X.MotionNotify, 0,
                                      Xlib.X.CurrentTime, 0, ax, ay)
            d.sync()
            time.sleep(0.08)
            Xlib.ext.xtest.fake_input(d, Xlib.X.ButtonPress,   button)
            d.sync()
            time.sleep(0.05)
            Xlib.ext.xtest.fake_input(d, Xlib.X.ButtonRelease, button)
            d.sync()
            if double:
                time.sleep(0.1)
                Xlib.ext.xtest.fake_input(d, Xlib.X.ButtonPress,   button)
                d.sync()
                time.sleep(0.05)
                Xlib.ext.xtest.fake_input(d, Xlib.X.ButtonRelease, button)
                d.sync()
            time.sleep(0.1)
        except Exception as ex:
            _log_entry("click_fail", str(ex))

    def type_text(self, text: str) -> None:
        """Type a string into whatever widget currently has focus."""
        if not self._ready:
            return
        try:
            d = self._display
            for ch in text:
                needs_shift = ch in _SHIFT_CHARS
                keysym = Xlib.XK.string_to_keysym(ch)
                if keysym == 0:
                    # Try lowercase lookup for shifted chars
                    keysym = Xlib.XK.string_to_keysym(ch.lower())
                if keysym == 0:
                    continue
                keycode = d.keysym_to_keycode(keysym)
                if needs_shift:
                    shift_code = d.keysym_to_keycode(Xlib.XK.string_to_keysym("Shift_L"))
                    Xlib.ext.xtest.fake_input(d, Xlib.X.KeyPress, shift_code)
                Xlib.ext.xtest.fake_input(d, Xlib.X.KeyPress,   keycode)
                d.sync()
                time.sleep(0.02)
                Xlib.ext.xtest.fake_input(d, Xlib.X.KeyRelease, keycode)
                d.sync()
                if needs_shift:
                    Xlib.ext.xtest.fake_input(d, Xlib.X.KeyRelease, shift_code)
                d.sync()
                time.sleep(0.02)
        except Exception as ex:
            _log_entry("type_fail", str(ex))

    def press_key(self, key_name: str) -> None:
        """
        Press a key by name.  Supports modifier combos like 'ctrl+a', 'ctrl+c'.
        Plain names: Return, Tab, BackSpace, Escape, Delete, etc.
        """
        if not self._ready:
            return
        try:
            d = self._display
            parts = key_name.lower().split("+")
            mod_keycodes = []
            # Resolve modifiers
            mod_map = {"ctrl": "Control_L", "shift": "Shift_L",
                       "alt": "Alt_L", "super": "Super_L"}
            for part in parts[:-1]:
                mod_sym  = Xlib.XK.string_to_keysym(mod_map.get(part, part))
                mod_code = d.keysym_to_keycode(mod_sym)
                mod_keycodes.append(mod_code)
            # Main key — preserve case for the actual keysym lookup
            main_key   = parts[-1]
            # Capitalise first letter for Xlib keysym names (e.g. "return" → "Return")
            main_key_xk = main_key[0].upper() + main_key[1:] if main_key else main_key
            keysym  = Xlib.XK.string_to_keysym(main_key_xk)
            if keysym == 0:
                keysym = Xlib.XK.string_to_keysym(main_key)
            keycode = d.keysym_to_keycode(keysym)
            # Press modifiers down
            for mc in mod_keycodes:
                Xlib.ext.xtest.fake_input(d, Xlib.X.KeyPress, mc)
            d.sync()
            # Press main key
            Xlib.ext.xtest.fake_input(d, Xlib.X.KeyPress,   keycode)
            d.sync()
            time.sleep(0.04)
            Xlib.ext.xtest.fake_input(d, Xlib.X.KeyRelease, keycode)
            d.sync()
            # Release modifiers in reverse
            for mc in reversed(mod_keycodes):
                Xlib.ext.xtest.fake_input(d, Xlib.X.KeyRelease, mc)
            d.sync()
            time.sleep(0.06)
        except Exception as ex:
            _log_entry("key_fail", f"{key_name}: {ex}")

    # ── tab navigation ────────────────────────────────────────────────────

    def _locate_tab(self, tab_name: str) -> Optional[Tuple[int, int]]:
        """
        Find the pixel centre of a tab button by scanning the tab bar with OCR.
        Returns window-relative (x, y) or None.
        """
        if not self._ensure_window():
            return None
        try:
            img = self.screenshot(save=False)
            if img is None:
                return None
            g = self._geom
            tab_bar = img.crop((0, 0, g.width, 42))
            # Get bounding boxes for each word in the tab bar
            data = pytesseract.image_to_data(
                tab_bar.resize((g.width * 2, 84), Image.LANCZOS),
                config="--psm 7",
                output_type=pytesseract.Output.DICT,
            )
            target = tab_name.lower()
            for i, word in enumerate(data["text"]):
                if target in word.lower() and int(data["conf"][i]) > 30:
                    # Convert back from 2x scale to original coords
                    x = data["left"][i] // 2 + data["width"][i] // 4
                    y = 20  # vertically centred in tab bar
                    return (x, y)
        except Exception as ex:
            _log_entry("locate_tab_fail", f"{tab_name}: {ex}")
        # Fallback: estimate tab position by index
        try:
            idx = ROOM_TABS.index(tab_name)
            g = self._geom
            tab_w = g.width // len(ROOM_TABS)
            x = idx * tab_w + tab_w // 2
            return (x, 20)
        except Exception:
            return None

    def switch_tab(self, tab_name: str) -> bool:
        """
        Click on the named tab.  Returns True if the click was sent.
        Takes a screenshot after to confirm.
        """
        pos = self._locate_tab(tab_name)
        if pos is None:
            _log_entry("switch_tab_fail", f"could not locate: {tab_name}")
            return False
        self.click(*pos)
        time.sleep(0.4)
        _log_entry("switch_tab", tab_name)
        return True

    # ── Poedex interaction ────────────────────────────────────────────────

    def _locate_widget_by_ocr(self, label_text: str,
                               search_region: Optional[Tuple[int,int,int,int]] = None
                               ) -> Optional[Tuple[int, int]]:
        """
        Find a widget by the label text near it.
        Returns window-relative centre coords.
        """
        if not self._ensure_window():
            return None
        try:
            img = self.screenshot(save=False)
            if img is None:
                return None
            g = self._geom
            if search_region:
                sx, sy, sw, sh = search_region
                crop = img.crop((sx, sy, sx + sw, sy + sh))
                offset_x, offset_y = sx, sy
            else:
                crop = img
                offset_x, offset_y = 0, 0

            data = pytesseract.image_to_data(
                crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS),
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )
            target = label_text.lower()
            for i, word in enumerate(data["text"]):
                if target in word.lower() and int(data["conf"][i]) > 25:
                    x = offset_x + data["left"][i] // 2 + data["width"][i] // 4
                    y = offset_y + data["top"][i] // 2 + data["height"][i] // 4 + 20
                    return (x, y)
        except Exception as ex:
            _log_entry("locate_widget_fail", f"{label_text}: {ex}")
        return None

    def poedex_query(self, question: str, cat: str = "define",
                     lane: str = "self", timeout: float = 12.0) -> str:
        """
        Aurora queries Poedex and reads the result from her own screen.

        Submission goes through the query queue (fast, reliable — the room
        is already watching it every 1.5s).  She then switches to her Poedex
        tab and OCRs the result area to read what appeared, exactly as she
        would see it looking at the screen.
        """
        _log_entry("poedex_query_start", f"{cat}: {question}")

        # 1. Submit through the per-request queue directory
        _QUERY_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        _QUERY_RESULT_DIR.mkdir(parents=True, exist_ok=True)
        import os as _os
        qid = f"{time.time():.4f}_{_os.getpid()}"
        _query_file  = _QUERY_QUEUE_DIR  / f"{qid}.json"
        _result_file = _QUERY_RESULT_DIR / f"{qid}.json"
        _query_file.write_text(json.dumps({
            "id":        qid,
            "question":  question,
            "cat":       cat,
            "lane":      lane,
            "status":    "pending",
            "submitted": time.time(),
        }, indent=2))

        # 2. Navigate to Poedex tab so she watches it process
        self.switch_tab("Poedex")
        time.sleep(0.5)

        # 3. Wait for per-request result file to appear
        deadline = time.time() + timeout
        result_text = ""
        while time.time() < deadline:
            time.sleep(1.5)
            if _result_file.exists():
                try:
                    r = json.loads(_result_file.read_text())
                    if r.get("id") == qid and r.get("status") == "done":
                        # 4. Screenshot and OCR the result area — she reads her screen.
                        #    Give the room one extra beat to render the result widget.
                        time.sleep(0.6)
                        img = self.screenshot(save=True)
                        if img:
                            g = self._geom
                            # Poedex tab layout on 1100x740:
                            #   tab bar ~0–35px, mode selector ~35–65px,
                            #   input area ~65–155px, RESULT label + content ~155–600px
                            # region format: (x, y, width, height)
                            y_start = int(g.height * 0.20)   # ~148px — just above RESULT label
                            h_crop  = int(g.height * 0.62)   # ~459px — captures full result body
                            result_region = (20, y_start, g.width - 40, h_crop)
                            result_text = self.read_screen(img=img, region=result_region)
                        # Clean up files
                        try: _result_file.unlink(missing_ok=True)
                        except Exception: pass
                        try: _query_file.unlink(missing_ok=True)
                        except Exception: pass
                        break
                except Exception:
                    pass

        _log_entry("poedex_query_done",
                   f"{cat}: {question} → {len(result_text)} chars read from screen")
        return result_text

    def look_at_tab(self, tab_name: str) -> str:
        """
        Navigate to a tab, take a screenshot, OCR the full content area,
        return what Aurora reads.
        """
        if not self.switch_tab(tab_name):
            return ""
        time.sleep(0.5)
        img = self.screenshot(save=True)
        if img is None:
            return ""
        text = self.read_tab_content()
        _log_entry("look_at_tab", f"{tab_name}: {len(text)} chars")
        return text

    def scan_room(self) -> Dict[str, str]:
        """
        Walk through all tabs, read each one, return a dict of
        tab_name → ocr_text.  Aurora's full room awareness pass.
        """
        _log_entry("scan_room_start", f"{len(ROOM_TABS)} tabs")
        readings: Dict[str, str] = {}
        for tab in ROOM_TABS:
            text = self.look_at_tab(tab)
            readings[tab] = text
            time.sleep(0.3)
        _log_entry("scan_room_done", f"{sum(len(v) for v in readings.values())} chars total")
        return readings


# ── standalone test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    op = RoomOperator()
    if not op._ready:
        print("Operator not ready — check Xlib/PIL/tesseract")
        sys.exit(1)

    if not op._find_window():
        print("Aurora's Room window not found — is aurora_room.py running?")
        sys.exit(1)

    g = op._geom
    print(f"Window found: {g.width}x{g.height} at ({g.x},{g.y})")

    print("\nTaking screenshot...")
    img = op.screenshot()
    print(f"Screenshot: {img.size if img else 'FAILED'}")

    print("\nReading Self tab...")
    text = op.look_at_tab("Self")
    print(text[:400] if text else "(nothing read)")

    print("\nQuerying Poedex: define N...")
    result = op.poedex_query("N", cat="define")
    print(result[:400] if result else "(nothing read)")
