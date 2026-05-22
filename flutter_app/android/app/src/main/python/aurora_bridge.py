"""
Aurora Python bridge — entry point for Chaquopy in the Flutter app.

This module is called from AuroraService.kt via Chaquopy.  It boots the
Aurora cognitive stack and exposes a simple text-in / text-out interface so
that all audio I/O stays on the Flutter/Kotlin side.
"""
from __future__ import annotations

import logging
import sys
import threading
import traceback
from typing import Optional

log = logging.getLogger("aurora_bridge")

_systems = None
_lock    = threading.Lock()


def _setup_paths() -> None:
    """
    aurora_core_ai/aurora.py uses bare imports (e.g. `from aurora_constraint_unit_adapter
    import ...`) that assume its own directory is on sys.path.  We replicate the
    original aurora_mobile.py bootstrap here.
    """
    for pkg_name in ("aurora_core_ai", "aurora_internal"):
        try:
            pkg = __import__(pkg_name)
            pkg_path = list(pkg.__path__)[0]
            if pkg_path not in sys.path:
                sys.path.insert(0, pkg_path)
        except Exception as exc:
            log.warning("path setup for %s: %s", pkg_name, exc)


def initialize(state_dir: str = "") -> str:
    """Boot the Aurora stack. Called once from AuroraService on startup."""
    global _systems
    _setup_paths()
    try:
        from aurora_core_ai.aurora import boot_aurora  # type: ignore
        kwargs: dict = {"verbose": False, "runtime_profile": "full"}
        if state_dir:
            kwargs["state_dir"] = state_dir
        with _lock:
            _systems = boot_aurora(**kwargs)
        log.info("Aurora boot complete")
        return "ready"
    except Exception as exc:
        log.error("boot_aurora failed: %s\n%s", exc, traceback.format_exc())
        return f"error: {exc}"


def handle_message(text: str) -> str:
    """Process one user turn. Returns Aurora's text response."""
    global _systems
    if _systems is None:
        return "Aurora is still initializing — please wait a moment."
    _setup_paths()
    try:
        from aurora_core_ai.aurora import process_external_user_turn  # type: ignore
        with _lock:
            result = process_external_user_turn(
                _systems,
                text,
                source_label="flutter_ui",
                session_id="mobile",
                auto_search_enabled=True,
                record_exchange=True,
                update_interactive_state=True,
                track_evolutionary_trace=True,
                run_periodic_maintenance=True,
                mode_name="BOUNDED",
            )
        return _extract_response(result)
    except TypeError:
        # Older Aurora build that doesn't accept keyword-only args
        try:
            from aurora_core_ai.aurora import process_external_user_turn  # type: ignore
            with _lock:
                result = process_external_user_turn(_systems, text)
            return _extract_response(result)
        except Exception as exc:
            log.error("handle_message (fallback): %s", exc)
            return "I encountered an error. Please try again."
    except Exception as exc:
        log.error("handle_message: %s\n%s", exc, traceback.format_exc())
        return "I encountered an error processing your request."


def _extract_response(result) -> str:
    """Mirror of aurora_mobile._extract_response — handles all result shapes."""
    if not isinstance(result, dict):
        return str(result or "").strip()
    resp_a = result.get("resp_A")
    if resp_a is not None:
        content = getattr(resp_a, "content", None)
        if isinstance(content, list):
            parts = [
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
                for b in content
                if (isinstance(b, dict) and b.get("type") == "text")
                or (not isinstance(b, dict) and getattr(b, "type", "") == "text")
            ]
            text = " ".join(str(p) for p in parts if p).strip()
            if text:
                return text
        elif content:
            return str(content).strip()
    for key in ("response_text", "text", "answer"):
        val = result.get(key)
        if val:
            return str(val).strip()
    return ""


def set_state(state: str) -> None:
    """Called by AuroraService when embodiment state changes."""
    pass  # state is managed by Flutter/Kotlin; Python side is stateless here


def provide_camera_frame(jpeg_bytes) -> None:
    """
    Called from Kotlin (AuroraService.provideCameraFrame) to push a CameraX
    frame into Aurora's visual stack.  jpeg_bytes is a Java byte[] from
    Chaquopy, decoded here to a BGR numpy array and fed to the cv2 shim's
    VideoCapture buffer.
    """
    try:
        import io as _io
        import numpy as _np
        from PIL import Image as _Image
        import cv2 as _cv2
        pil  = _Image.open(_io.BytesIO(bytes(jpeg_bytes))).convert('RGB')
        rgb  = _np.array(pil, dtype=_np.uint8)
        bgr  = rgb[:, :, ::-1].copy()
        _cv2.VideoCapture.provide_frame(bgr)
    except Exception as exc:
        log.warning("provide_camera_frame: %s", exc)
