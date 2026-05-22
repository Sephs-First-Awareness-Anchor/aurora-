#!/usr/bin/env python3
"""
aurora_live_vision.py -- Live screen observer for Aurora.

Captures the screen at a configurable interval, feeds frames through
Aurora's existing visual processing pipeline (FeatureExtractor ->
SensoryCompetencyEngine.process_visual_input), and maintains a rolling
scene log that Aurora can reference in conversation.

Usage (standalone test):
    python3 aurora_live_vision.py

Integration (from aurora.py boot):
    from aurora_live_vision import boot_screen_observer
    systems['screen_observer'] = boot_screen_observer(systems, interval=5.0)
"""

from __future__ import annotations

import json
import os
import sys
import time
import math
import threading
import hashlib
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR       = Path(__file__).parent
_STATE_DIR      = _BASE_DIR / "aurora_state"
_SCENE_LOG_PATH = _STATE_DIR / "screen_observer_log.json"

# ---------------------------------------------------------------------------
# Optional heavy imports (graceful degradation)
# ---------------------------------------------------------------------------
try:
    from PIL import ImageGrab as _PILGrab
    _PIL_GRAB_AVAILABLE = True
except ImportError:
    _PIL_GRAB_AVAILABLE = False

try:
    import cv2 as _cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# Aurora pipeline imports -- attempted lazily so this file loads even when
# the full stack is not booted.
def _try_import_pipeline():
    """Return (FeatureExtractor, ExistenceMode) or (None, None)."""
    try:
        from aurora_expression_perception import FeatureExtractor
        from aurora_constraint_engine import ExistenceMode
        return FeatureExtractor, ExistenceMode
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# ScreenObserver
# ---------------------------------------------------------------------------

class ScreenObserver:
    """
    Captures the screen on a background daemon thread, extracts visual
    features via Aurora's pipeline, and maintains a rolling scene log.
    """

    SCREEN_DIR = str(_STATE_DIR / "vision_seeds" / "screen")
    _LOG_MAXLEN = 50     # scene log size

    def __init__(self, systems: Dict[str, Any], interval: float = 5.0):
        self._systems  = systems
        self._interval = max(1.0, float(interval))

        # Internal state
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count  = 0
        self._lock         = threading.Lock()
        self._scene_log: deque = deque(maxlen=self._LOG_MAXLEN)
        self._current_scene: Dict[str, Any] = {}
        self._prev_brightness: Optional[float] = None
        self._prev_edge_density: Optional[float] = None

        # Lazy-init pipeline refs
        self._FeatureExtractor = None
        self._ExistenceMode    = None
        self._extractor        = None

        # Circuit breaker: stop retrying capture after consecutive failures
        self._capture_fail_streak = 0
        self._capture_disabled    = False

        # Visual inquiry tracking — when Aurora sees something genuinely novel with
        # no concept match across multiple frames, she queues a structured observation
        # dict. The daemon reads it, gates it through cognitive signals (entropy/
        # coherence), and generates a purposeful question from the scene data.
        self._no_concept_streak: int = 0
        self._pending_visual_inquiry: Optional[Dict[str, Any]] = None
        self._visual_inquiry_min_frames: int = 6   # require N consecutive novel frames
        self._last_inquiry_ts: float = 0.0         # cooldown: min 300s between inquiries

        # Ensure screen dir exists
        os.makedirs(self.SCREEN_DIR, exist_ok=True)
        self._cleanup_legacy_frames()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background capture daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="ScreenObserver",
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the capture loop to stop."""
        self._running = False

    def is_running(self) -> bool:
        return self._running and (self._thread is not None) and self._thread.is_alive()

    def current_scene(self) -> Dict[str, Any]:
        """Return the most recent observation dict (empty if none yet)."""
        with self._lock:
            return dict(self._current_scene)

    def get_scene_log(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return last N scene observation dicts."""
        with self._lock:
            log = list(self._scene_log)
        return log[-n:] if n < len(log) else log

    def status(self) -> Dict[str, Any]:
        """Summary dict for /screen command in aurora.py."""
        scene = self.current_scene()
        status = {
            "running":        self.is_running(),
            "interval":       self._interval,
            "frame_count":    self._frame_count,
            "last_capture":   scene.get("timestamp"),
            "scene_type":     scene.get("scene_type", "none"),
            "brightness":     scene.get("brightness"),
            "edge_density":   scene.get("edge_density"),
            "motion":         scene.get("motion_magnitude"),
            "concepts":       scene.get("concepts_matched", []),
            "screen_dir":     self.SCREEN_DIR,
        }
        cv = self.constraint_profile()
        status["lineage_signature"] = "".join(ax for ax in ("X","T","N","B","A") if getattr(cv, ax) > 0.01)
        status["runtime_regime"] = self.runtime_regime()
        status["language_projection"] = self.language_projection()
        return status

    def get_pending_visual_inquiry(self) -> Optional[Dict[str, Any]]:
        """
        Return and clear any pending visual inquiry observation dict.

        Returns a structured dict (not a canned string) so the daemon can gate
        it through Aurora's cognitive pipeline and generate a purposeful question
        from the actual scene data rather than a fixed template.

        Dict keys: scene_type, edge_density, brightness, motion, concepts_matched,
                   no_match_streak, ts.
        """
        with self._lock:
            q = self._pending_visual_inquiry
            self._pending_visual_inquiry = None
        return q

    def get_scene_description(self) -> str:
        """Brief natural-language description of the current scene."""
        scene = self.current_scene()
        if not scene:
            return "No screen observation available yet."

        stype  = scene.get("scene_type", "unknown")
        bright = scene.get("brightness", 0.0)
        edge   = scene.get("edge_density", 0.0)
        motion = scene.get("motion_magnitude", 0.0)
        ts_raw = scene.get("timestamp")
        ts_str = time.strftime("%H:%M:%S", time.localtime(ts_raw)) if ts_raw else "?"

        motion_str = "static"
        if motion > 0.3:
            motion_str = "lots of movement"
        elif motion > 0.1:
            motion_str = "some movement"
        elif motion > 0.02:
            motion_str = "slight movement"

        type_desc = {
            "text_heavy":  "dense text content (code or document)",
            "image_rich":  "colorful / image-rich content",
            "terminal":    "a dark terminal or console",
            "idle":        "an idle or static screen",
            "active":      "active mixed content",
        }.get(stype, stype)

        concepts = scene.get("concepts_matched", [])
        concepts_str = (
            f" Concepts detected: {', '.join(concepts[:3])}." if concepts else ""
        )

        return (
            f"At {ts_str} the screen shows {type_desc}. "
            f"Brightness {bright:.2f}, edge density {edge:.2f}, {motion_str}.{concepts_str}"
        )

    def _constraint_axes(self) -> Dict[str, float]:
        scene = self.current_scene()
        concepts = list(scene.get("concepts_matched", []) or [])
        brightness = float(scene.get("brightness", 0.0) or 0.0)
        edge_density = float(scene.get("edge_density", 0.0) or 0.0)
        motion = float(scene.get("motion_magnitude", 0.0) or 0.0)
        concept_density = min(1.0, len(concepts) / 6.0)
        return {
            "X": min(1.0, 0.35 + brightness * 0.35 + concept_density * 0.20),
            "T": min(1.0, 0.20 + min(1.0, self._frame_count / 40.0) * 0.45 + motion * 0.20),
            "N": min(1.0, 0.15 + motion * 0.55 + abs(brightness - 0.5) * 0.25),
            "B": min(1.0, 0.20 + edge_density * 0.45 + concept_density * 0.25),
            "A": min(1.0, 0.10 + (0.45 if self._pending_visual_inquiry else 0.0) + concept_density * 0.20),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.35))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.15)),
            B=float(ax.get("B", 0.20)),
            A=float(ax.get("A", 0.10)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(_ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                "running": self.is_running(),
                "frame_count": self._frame_count,
                "current_scene": self.current_scene(),
                "pending_visual_inquiry": self._pending_visual_inquiry,
                "recent_log_size": len(self.get_scene_log(10)),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_extractor(self):
        """Lazy-init the FeatureExtractor once."""
        if self._extractor is not None:
            return
        FE, EM = _try_import_pipeline()
        self._FeatureExtractor = FE
        self._ExistenceMode    = EM
        if FE is not None:
            self._extractor = FE()

    def _derive_scene_type(self, brightness: float, edge_density: float,
                           saturation: float, motion: float) -> str:
        if edge_density > 0.35:
            return "text_heavy"
        if saturation > 0.4:
            return "image_rich"
        if brightness < 0.3 and edge_density > 0.2:
            return "terminal"
        if motion < 0.02:
            return "idle"
        return "active"

    def _compute_motion(self, brightness: float, edge_density: float) -> float:
        """Simple motion proxy: normalised diff from previous frame values."""
        if self._prev_brightness is None:
            return 0.0
        db = abs(brightness    - self._prev_brightness)
        de = abs(edge_density  - self._prev_edge_density)
        # weight edge changes more (content change) than brightness
        raw = db * 0.4 + de * 0.6
        return min(1.0, raw * 5.0)   # scale so typical page scroll ~0.15

    def _cleanup_legacy_frames(self) -> None:
        try:
            screen_dir = Path(self.SCREEN_DIR)
            for path in screen_dir.glob("frame_*.png"):
                try:
                    path.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    def _frame_path(self) -> str:
        return os.path.join(self.SCREEN_DIR, "frame_latest.png")

    def _capture_frame(self):
        """Grab screen, resize, return (PIL image, path)."""
        if self._capture_disabled:
            return None, None

        path = self._frame_path()
        
        # --- attempt 0: Android/Mobile check ---
        # On Android (Chaquopy), capturing is handled by the Kotlin side.
        # We just check if the file exists and is recent.
        is_android = os.path.exists("/data/data/com.termux") or "ANDROID_ROOT" in os.environ
        if is_android:
            if os.path.exists(path):
                try:
                    from PIL import Image as _PILImage
                    # Use a copy to avoid locking issues if Kotlin is writing
                    with open(path, "rb") as f:
                        img = _PILImage.open(f).copy()
                    return img, path
                except Exception:
                    pass
            return None, None

        # --- attempt 1: PIL.ImageGrab via subprocess (X-connection-safe) ---
        if _PIL_GRAB_AVAILABLE:
            try:
                import subprocess as _sp
                _script = (
                    f"from PIL import ImageGrab as _G;"
                    f"img=_G.grab();"
                    f"img=img.resize((640,400));"
                    f"img.save({path!r},'PNG',optimize=False)"
                )
                r = _sp.run(
                    ["python3", "-c", _script],
                    capture_output=True, timeout=10,
                )
                if r.returncode == 0 and os.path.exists(path):
                    from PIL import Image as _PILImage
                    img = _PILImage.open(path).copy()
                    self._capture_fail_streak = 0
                    return img, path
            except Exception:
                pass  # fall through to ImageMagick

        # --- attempt 2: ImageMagick (Wayland-compatible) ---
        try:
            import subprocess as _sp2, shutil
            from PIL import Image as _PILImage2
            if shutil.which("import"):
                r2 = _sp2.run(
                    ["import", "-window", "root", "-resize", "640x400", path],
                    capture_output=True, timeout=8,
                )
                if r2.returncode == 0 and os.path.exists(path):
                    img = _PILImage2.open(path).copy()
                    self._capture_fail_streak = 0
                    return img, path
        except Exception:
            pass

        # Both methods failed — update circuit breaker
        self._capture_fail_streak += 1
        if self._capture_fail_streak >= 5:
            self._capture_disabled = True
            self._capture_fail_streak = 0
            # Re-enable after 60 s via a timer thread
            def _reenable():
                time.sleep(60)
                self._capture_disabled = False
            threading.Thread(target=_reenable, daemon=True).start()

        return None, None

    def _extract_features(self, path: str, img) -> Optional[Any]:
        """Run FeatureExtractor._extract_from_pil; return VisualFeatureVector or None."""
        if self._extractor is None or img is None:
            return None
        try:
            return self._extractor._extract_from_pil(path, img)
        except Exception:
            return None

    def _make_visual_data(self, fv, path: str, motion: float,
                          ts: float) -> Dict[str, Any]:
        """Build the visual_data dict for process_visual_input."""
        if fv is None:
            return {
                "brightness": 0.5, "contrast": 0.5, "edge_density": 0.2,
                "color_r": 0.5, "color_g": 0.5, "color_b": 0.5,
                "saturation": 0.2, "motion_detected": motion > 0.05,
                "motion_magnitude": motion, "source": "screen_capture",
                "timestamp": ts, "frame_path": path, "label": "screen",
                "features": {},
            }
        return {
            "brightness":       fv.brightness,
            "contrast":         fv.contrast,
            "edge_density":     fv.edge_density,
            "color_r":          fv.color_r,
            "color_g":          fv.color_g,
            "color_b":          fv.color_b,
            "saturation":       fv.saturation,
            "motion_detected":  motion > 0.05,
            "motion_magnitude": motion,
            "source":           "screen_capture",
            "timestamp":        ts,
            "frame_path":       path,
            "label":            "screen",
            "features": {
                "brightness":   fv.brightness,
                "contrast":     fv.contrast,
                "edge_density": fv.edge_density,
                "saturation":   fv.saturation,
                "color_r":      fv.color_r,
                "color_g":      fv.color_g,
                "color_b":      fv.color_b,
            },
        }

    def _feed_sensory(self, visual_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send visual_data to SensoryCompetencyEngine if available."""
        sensory = self._systems.get("sensory")
        if sensory is None or self._ExistenceMode is None:
            return {}
        try:
            result = sensory.process_visual_input(
                visual_data,
                self._ExistenceMode.BOUNDED,
            )
            return result or {}
        except Exception:
            return {}

    def _maybe_ingest_vision_bootstrap(self, path: str, edge_density: float) -> List[str]:
        """
        If the frame is non-trivial, pass to vision_bootstrap for OETS binding.
        Returns a list of concept labels matched.
        """
        vb = self._systems.get("vision_bootstrap")
        if vb is None or edge_density <= 0.15:
            return []
        try:
            # Prefer fine-grained method; fall back to bulk ingest occasionally
            if hasattr(vb, "ingest_image"):
                result = vb.ingest_image(path)
                if isinstance(result, dict):
                    return result.get("concepts", [])
                return []
            # Bulk ingest every 20 frames to avoid hammering the whole folder
            if self._frame_count % 20 == 0:
                vb.ingest_folder(self.SCREEN_DIR)
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        self._init_extractor()
        while self._running:
            loop_start = time.time()
            try:
                ts = time.time()

                # 1. Capture screen
                img, path = self._capture_frame()
                if img is None:
                    time.sleep(self._interval)
                    continue

                # 2. Extract features
                fv = self._extract_features(path, img)

                # 3. Compute motion from feature deltas
                brightness   = fv.brightness   if fv else 0.5
                edge_density = fv.edge_density if fv else 0.2
                saturation   = fv.saturation   if fv else 0.2
                motion = self._compute_motion(brightness, edge_density)

                # 4. Build visual_data
                visual_data = self._make_visual_data(fv, path, motion, ts)

                # 5. Feed sensory pipeline
                sensory_result = self._feed_sensory(visual_data)
                _raw_patterns = sensory_result.get("patterns", [])
                # Ensure JSON-serializable (sensory pipeline may return numpy/sets)
                patterns = [str(p) for p in (_raw_patterns if isinstance(_raw_patterns, (list, tuple)) else [])]

                # 6. Ingest into vision_bootstrap (OETS binding)
                _raw_concepts = self._maybe_ingest_vision_bootstrap(path, edge_density)
                concepts = [str(c) for c in (_raw_concepts if isinstance(_raw_concepts, (list, tuple)) else [])]

                # 7. Derive scene type
                scene_type = self._derive_scene_type(
                    brightness, edge_density, saturation, motion
                )

                # 8. Build observation
                observation = {
                    "timestamp":       ts,
                    "frame":           path,
                    "brightness":      round(brightness, 4),
                    "edge_density":    round(edge_density, 4),
                    "saturation":      round(saturation, 4),
                    "motion":          round(motion, 4),
                    "motion_magnitude":round(motion, 4),
                    "scene_type":      scene_type,
                    "concepts_matched":concepts,
                    "patterns":        patterns,
                    "frame_count":     self._frame_count,
                }

                # 9. Update state under lock
                with self._lock:
                    self._current_scene = observation
                    self._scene_log.append(observation)
                    self._prev_brightness   = brightness
                    self._prev_edge_density = edge_density
                    self._frame_count      += 1
                    _snap = list(self._scene_log)

                    # Track novel-scene streak for visual inquiry generation.
                    # High edge density = something visually structured is present.
                    # No concept matches = Aurora doesn't know what it is yet.
                    _is_novel = (edge_density > 0.2) and (len(concepts) == 0)
                    if _is_novel:
                        self._no_concept_streak += 1
                    else:
                        self._no_concept_streak = 0

                    # After N consecutive novel frames, queue a structured observation
                    # dict for the daemon to process through the cognitive pipeline.
                    # Hard cooldown (300s) prevents inquiry spam regardless of streak.
                    _cooldown_ok = (time.time() - self._last_inquiry_ts) >= 300
                    if (self._no_concept_streak >= self._visual_inquiry_min_frames
                            and self._pending_visual_inquiry is None
                            and _cooldown_ok):
                        self._pending_visual_inquiry = {
                            "scene_type":       scene_type,
                            "edge_density":     round(edge_density, 3),
                            "brightness":       round(brightness, 3),
                            "motion":           round(motion, 3),
                            "saturation":       round(saturation, 3),
                            "concepts_matched": list(concepts),
                            "no_match_streak":  self._no_concept_streak,
                            "ts":               time.time(),
                        }
                        self._last_inquiry_ts   = time.time()
                        self._no_concept_streak = 0  # reset streak after queuing

                # 10. Persist scene log for hub / external readers
                try:
                    with open(_SCENE_LOG_PATH, "w") as _f:
                        json.dump(_snap, _f)
                except Exception:
                    pass

                # 11. SediMemory ingest — visual observation as constraint event
                # Only from subsurface (this thread is daemon-owned); never touches surface state.
                try:
                    _sedi = self._systems.get("sedimemory")
                    if _sedi is not None:
                        # Map visual metrics → 5-axis constraint vector
                        # X: spatial complexity (edge density proxy)
                        # T: temporal change (motion proxy)
                        # N: conceptual richness (concept count)
                        # B: binding depth (saturation as colour binding)
                        # A: autonomy weight — constant low (observer not acting)
                        _n_concepts = len(concepts)
                        _cv_x = max(0.05, min(1.0, float(edge_density) * 2.0))
                        _cv_t = max(0.05, min(1.0, float(motion) * 3.0))
                        _cv_n = max(0.05, min(1.0, _n_concepts / 5.0))
                        _cv_b = max(0.05, min(1.0, float(saturation) * 1.5))
                        _cv_a = 0.1  # observer stance — low autonomous weight

                        try:
                            from aurora_constraint_engine import ExistenceMode as _EM
                        except Exception:
                            _EM = None

                        try:
                            from aurora_sedimemory import ConstraintVector as _CV
                            _sedi_cv = _CV(X=_cv_x, T=_cv_t, N=_cv_n, B=_cv_b, A=_cv_a)
                        except Exception:
                            _sedi_cv = None

                        if _sedi_cv is not None:
                            _em = _EM.BOUNDED if _EM is not None else None
                            _sedi.ingest_event(
                                content={
                                    "source":       "screen_observer",
                                    "scene_type":   scene_type,
                                    "brightness":   round(brightness, 4),
                                    "edge_density": round(edge_density, 4),
                                    "saturation":   round(saturation, 4),
                                    "motion":       round(motion, 4),
                                    "concepts":     concepts[:8],
                                    "patterns":     patterns[:8],
                                    "ts":           ts,
                                },
                                constraint_vector=_sedi_cv,
                                source="screen_observer",
                                **({"existence_mode": _em} if _em is not None else {}),
                            )
                except Exception:
                    pass

            except Exception:
                pass   # never crash the daemon thread

            # Sleep remainder of interval
            elapsed = time.time() - loop_start
            sleep_for = max(0.0, self._interval - elapsed)
            time.sleep(sleep_for)


# ---------------------------------------------------------------------------
# Convenience boot function
# ---------------------------------------------------------------------------

def boot_screen_observer(systems: Dict[str, Any], interval: float = 5.0) -> ScreenObserver:
    """
    Create and start a ScreenObserver.  Wire into systems dict and return it.

    Example (in aurora.py boot):
        systems['screen_observer'] = boot_screen_observer(systems, interval=5.0)
    """
    obs = ScreenObserver(systems, interval=interval)
    obs.start()
    return obs


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[aurora_live_vision] Standalone test -- capturing for 15 s ...")
    systems: Dict[str, Any] = {}
    obs = boot_screen_observer(systems, interval=3.0)
    for i in range(5):
        time.sleep(3)
        status = obs.status()
        print(f"  frame={status['frame_count']}  "
              f"scene={status['scene_type']}  "
              f"bright={status['brightness']}  "
              f"edge={status['edge_density']}  "
              f"motion={status['motion']}")
    obs.stop()
    print("[aurora_live_vision] Done.")
    print(obs.get_scene_description())
