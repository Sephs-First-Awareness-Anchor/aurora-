#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_sensory_fallback.py
==========================
Pure-Python perception fallbacks — no cv2, no native layer, nothing beyond
numpy + Pillow (both already declared in the app build). These are what Aurora
drops to when the primary (native / cv2-shim) sensory path FAILS, so she still
perceives something instead of going blind.

Design intent: the already-coded native path is primary. This is only the
except-branch. Every function is total — it never raises; on catastrophic
failure it returns a safe, neutral perception so the caller never crashes.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple


def perceive_frame(jpeg_bytes: Any, prev_gray: Any = None) -> Tuple[Dict[str, Any], Any]:
    """Visual perception from a JPEG frame using ONLY Pillow + numpy.

    Extracts the same observation shape the native path produces (brightness,
    motion, dominant hue) plus an edge/detail density cue, so Aurora keeps a
    coarse but real sense of sight when the primary camera path is down.

    Returns (observation_dict, gray_frame). gray_frame is handed back so the
    caller can keep it for next-frame motion diffing. Never raises.
    """
    try:
        import io
        import numpy as np
        from PIL import Image

        pil = Image.open(io.BytesIO(bytes(jpeg_bytes))).convert("RGB")
        rgb = np.asarray(pil, dtype=np.float32)
        gray = rgb.mean(axis=2) / 255.0
        brightness = float(gray.mean())

        # Motion: mean absolute difference from the previous frame.
        motion = False
        if prev_gray is not None and getattr(prev_gray, "shape", None) == gray.shape:
            motion = float(np.mean(np.abs(gray - prev_gray))) > 0.04

        # Dominant hue from a center crop (borders are noisy).
        h, w = gray.shape
        crop = rgb[h // 4: 3 * h // 4, w // 4: 3 * w // 4].reshape(-1, 3).mean(axis=0)
        r, g, b = float(crop[0]), float(crop[1]), float(crop[2])
        mx = max(r, g, b)
        if mx <= 10:
            hue = "dark"
        elif mx == r:
            hue = "warm"
        elif mx == g:
            hue = "cool-green"
        else:
            hue = "cool-blue"

        # Detail / visual complexity: normalized gradient (edge) density — numpy only.
        gy = float(np.abs(np.diff(gray, axis=0)).mean()) if gray.shape[0] > 1 else 0.0
        gx = float(np.abs(np.diff(gray, axis=1)).mean()) if gray.shape[1] > 1 else 0.0
        detail = float(min(1.0, (gx + gy) * 6.0))

        obs = {
            "brightness":      round(brightness, 3),
            "motion_detected": bool(motion),
            "dominant_hue":    hue,
            "detail":          round(detail, 3),
            "objects":         [],
            "faces":           [],
            "confidence":      0.4,          # below the native path's 0.65 — it IS a fallback
            "source":          "python_fallback",
        }
        return obs, gray
    except Exception:
        # Catastrophic — return a safe neutral perception so nothing crashes.
        return (
            {
                "brightness": 0.0, "motion_detected": False, "dominant_hue": "dark",
                "detail": 0.0, "objects": [], "faces": [], "confidence": 0.0,
                "source": "python_fallback_degraded",
            },
            prev_gray,
        )
