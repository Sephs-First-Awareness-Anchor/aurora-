"""
Android cv2 shim for Aurora.

Replaces opencv-python-headless (no Android build in Chaquopy's mirror) with
numpy + Pillow implementations of the cv2 functions Aurora's cognitive stack
uses.  Camera frames are injected via VideoCapture.provide_frame() from the
Kotlin CameraX bridge through aurora_bridge.provide_camera_frame().
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

import numpy as np

# ── Constants ──────────────────────────────────────────────────────────────────
COLOR_BGR2RGB  = 4
COLOR_BGR2GRAY = 6
COLOR_BGR2HSV  = 40
COLOR_RGB2BGR  = 5
COLOR_GRAY2BGR = 8

CAP_PROP_FRAME_WIDTH  = 3
CAP_PROP_FRAME_HEIGHT = 4
CAP_PROP_FPS          = 5

IMREAD_COLOR     = 1
IMREAD_GRAYSCALE = 0


# ── cv2.data stub ──────────────────────────────────────────────────────────────
class _DataModule:
    # Haar cascade XML files are not available on Android.
    # CascadeClassifier is a no-op stub; this path is never read.
    haarcascades = "/sdcard/"

data = _DataModule()


# ── Color conversion ───────────────────────────────────────────────────────────
def cvtColor(frame: np.ndarray, code: int) -> np.ndarray:
    if frame is None or frame.size == 0:
        return frame
    if code in (COLOR_BGR2RGB, COLOR_RGB2BGR):
        return frame[:, :, ::-1].copy()
    if code == COLOR_BGR2GRAY:
        b = frame[:, :, 0].astype(np.float32)
        g = frame[:, :, 1].astype(np.float32)
        r = frame[:, :, 2].astype(np.float32)
        return (0.114 * b + 0.587 * g + 0.299 * r).astype(np.uint8)
    if code == COLOR_BGR2HSV:
        return _bgr_to_hsv(frame)
    if code == COLOR_GRAY2BGR:
        return np.stack([frame, frame, frame], axis=-1)
    return frame


def _bgr_to_hsv(bgr: np.ndarray) -> np.ndarray:
    rgb = bgr[:, :, ::-1].astype(np.float32) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    maxc  = np.maximum(np.maximum(r, g), b)
    minc  = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    v = maxc
    s = np.where(maxc > 0, delta / maxc, 0.0)

    h = np.zeros_like(maxc)
    m  = delta > 0
    mr = m & (maxc == r)
    mg = m & (maxc == g)
    mb = m & (maxc == b)
    h[mr] = ((g[mr] - b[mr]) / delta[mr]) % 6.0
    h[mg] = (b[mg] - r[mg]) / delta[mg] + 2.0
    h[mb] = (r[mb] - g[mb]) / delta[mb] + 4.0
    h = h * 60.0
    # OpenCV convention: H ∈ [0,180], S and V ∈ [0,255]
    return np.stack([h / 2.0, s * 255.0, v * 255.0], axis=-1).astype(np.uint8)


# ── Channel operations ─────────────────────────────────────────────────────────
def split(frame: np.ndarray):
    return frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]


def merge(channels):
    return np.stack(list(channels), axis=-1)


def absdiff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)


# ── Edge detection ─────────────────────────────────────────────────────────────
def Canny(gray: np.ndarray, threshold1: float, threshold2: float, **_) -> np.ndarray:
    """Gradient-magnitude edge approximation (not full Canny, functional for motion)."""
    g  = gray.astype(np.float32)
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    mag = np.sqrt(gx ** 2 + gy ** 2)
    out = np.zeros_like(gray, dtype=np.uint8)
    out[mag > threshold1] = 255
    return out


# ── Histogram ──────────────────────────────────────────────────────────────────
def calcHist(images, channels, mask, histSize, ranges, **_) -> np.ndarray:
    img = images[0]
    ch  = channels[0]
    flat = (img[:, :, ch] if img.ndim == 3 else img).ravel()
    bins = histSize[0]
    hist, _ = np.histogram(flat, bins=bins, range=tuple(ranges))
    return hist.astype(np.float32).reshape(bins, 1)


# ── File I/O ───────────────────────────────────────────────────────────────────
def imwrite(filename: str, img: np.ndarray, params=None) -> bool:
    if img is None:
        return False
    try:
        from PIL import Image
        arr = img[:, :, ::-1] if img.ndim == 3 and img.shape[2] >= 3 else img
        Image.fromarray(arr.astype(np.uint8)).save(filename)
        return True
    except Exception:
        return False


def imread(filename: str, flags: int = IMREAD_COLOR) -> Optional[np.ndarray]:
    try:
        from PIL import Image
        mode = 'RGB' if flags != IMREAD_GRAYSCALE else 'L'
        arr  = np.array(Image.open(filename).convert(mode))
        if flags != IMREAD_GRAYSCALE and arr.ndim == 3:
            return arr[:, :, ::-1].copy()  # RGB → BGR
        return arr
    except Exception:
        return None


# ── Face detection stub (no Haar XML files on Android) ────────────────────────
class CascadeClassifier:
    def __init__(self, path: str = ""):
        pass  # XML file not present on Android

    def empty(self) -> bool:
        return True

    def detectMultiScale(self, image, scaleFactor=1.1, minNeighbors=3,
                         flags=0, minSize=None, maxSize=None):
        return np.array([])


# ── Camera (frames injected from Android CameraX via aurora_bridge) ────────────
class VideoCapture:
    """
    Android VideoCapture shim.

    Aurora's cv2.VideoCapture(0) calls hit this class.  Real frames come from
    the Kotlin CameraX capture loop: CameraX → AuroraService.provideCameraFrame
    → aurora_bridge.provide_camera_frame → VideoCapture.provide_frame.

    read() returns the most recently pushed frame, or (False, None) when none
    is available yet.
    """
    _lock: threading.Lock              = threading.Lock()
    _pending_frame: Optional[np.ndarray] = None

    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self._open     = True

    @classmethod
    def provide_frame(cls, frame_bgr: np.ndarray) -> None:
        with cls._lock:
            cls._pending_frame = frame_bgr

    def isOpened(self) -> bool:
        return self._open

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with VideoCapture._lock:
            frame = VideoCapture._pending_frame
            VideoCapture._pending_frame = None
        if frame is not None:
            return True, frame
        return False, None

    def set(self, prop: int, value) -> bool:
        return True

    def get(self, prop: int):
        if prop == CAP_PROP_FRAME_WIDTH:  return 640.0
        if prop == CAP_PROP_FRAME_HEIGHT: return 480.0
        if prop == CAP_PROP_FPS:          return 1.0
        return 0.0

    def release(self) -> None:
        self._open = False
