"""
aurora_concept_imager.py — Image-concept grounding for Aurora's OETS.

When a semantic node in the Ontological Entity Tracking System (OETS)
reaches scaffolding level 2 (SEMANTIC) or above, this module fetches a
representative image for that concept, saves it to disk, and feeds it
through the vision pipeline into the sensory crystal.

Flow:
    OETS concept reaches SEMANTIC (level 2+)
        → queued in concept_images_fetched.json (skip if already done)
        → Wikipedia REST API → thumbnail URL
        → image downloaded → aurora_state/vision_seeds/concepts/{word}.jpg
        → LinuxCamera.extract_features(frame) → visual_dict_to_crystal_57d()
        → sensory_crystal.observe_frame() + HardwareInterface.process_visual()
        → concept now has a visual grounding alongside its semantic web entry

Tracker file: aurora_state/concept_images_fetched.json
    {"fetched": ["apple", "ocean", ...], "failed": ["xyzzy", ...]}
"""

from __future__ import annotations

import json
import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

def _load_tracker(state_dir: Path) -> Dict[str, List[str]]:
    p = state_dir / "concept_images_fetched.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                data.setdefault("fetched", [])
                data.setdefault("failed", [])
                data.setdefault("grounded", [])
                return data
        except Exception:
            pass
    return {"fetched": [], "failed": [], "grounded": []}


def _save_tracker(state_dir: Path, tracker: Dict[str, List[str]]) -> None:
    p = state_dir / "concept_images_fetched.json"
    try:
        tmp = str(p) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(tracker, f, indent=2)
        os.replace(tmp, str(p))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Image fetch via Wikipedia REST API
# ---------------------------------------------------------------------------

_WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{word}"
_HEADERS  = {"User-Agent": "Aurora-ConceptImager/1.0 (educational project)"}


def fetch_concept_image(word: str, state_dir: Path) -> Optional[Path]:
    """
    Fetch a representative image for `word` using the Wikipedia summary API.
    Saves to aurora_state/vision_seeds/concepts/{word}.jpg.
    Returns the saved path, or None if no image was found.
    """
    try:
        import requests
    except ImportError:
        logger.warning("[IMAGER] requests not available — pip install requests")
        return None

    concepts_dir = state_dir / "vision_seeds" / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    save_path = concepts_dir / f"{word}.jpg"

    if save_path.exists():
        return save_path  # already downloaded

    try:
        url = _WIKI_API.format(word=word.replace(" ", "_"))
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            logger.debug(f"[IMAGER] Wiki API {resp.status_code} for '{word}'")
            return None

        data = resp.json()
        thumb = data.get("thumbnail", {})
        img_url = thumb.get("source")
        if not img_url:
            logger.debug(f"[IMAGER] No thumbnail for '{word}'")
            return None

        img_resp = requests.get(img_url, headers=_HEADERS, timeout=12)
        if img_resp.status_code != 200:
            return None

        save_path.write_bytes(img_resp.content)
        logger.info(f"[IMAGER] Saved concept image: {word} → {save_path.name}")
        return save_path

    except Exception as e:
        logger.debug(f"[IMAGER] fetch failed for '{word}': {e}")
        return None


# ---------------------------------------------------------------------------
# Vision ingestion
# ---------------------------------------------------------------------------

def ingest_concept_image(
    image_path: Path,
    word: str,
    hardware: Any,
    sensory_crystal: Any,
) -> bool:
    """
    Load a saved concept image and feed it through the vision pipeline.
    - Extracts HSV/edge/motion features via LinuxCamera.extract_features()
    - Routes features through hardware.process_visual() → sensory crystal
    Returns True if successfully ingested.
    """
    try:
        import cv2
        import numpy as np
        from aurora_expression_perception import LinuxCamera
        from aurora_internal.aurora_sensory_crystal import visual_dict_to_crystal_57d
    except ImportError as e:
        logger.warning(f"[IMAGER] Missing import for ingestion: {e}")
        return False

    try:
        raw = np.frombuffer(image_path.read_bytes(), dtype=np.uint8)
        frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if frame is None:
            return False

        # Extract features the same way the camera does
        _tmp_cam = LinuxCamera.__new__(LinuxCamera)
        _tmp_cam.device_id = -1
        _tmp_cam.running = False
        _tmp_cam.last_frame = frame
        features = _tmp_cam.extract_features(frame)

        # Tag the source so OETS linkage is traceable
        features["concept_word"] = word
        features["source"] = "concept_image"

        # Feed to sensory crystal directly
        if sensory_crystal is not None:
            try:
                v57 = visual_dict_to_crystal_57d(features)
                sensory_crystal.observe_frame(
                    [0.0] * 20, v57,
                    session_id=f"concept:{word}",
                    visual_conf=0.75,
                )
            except Exception as ce:
                logger.debug(f"[IMAGER] Crystal feed failed for '{word}': {ce}")

        # Also route through HardwareInterface.process_visual for full pipeline
        if hardware is not None and hasattr(hardware, "process_visual"):
            try:
                hardware.process_visual(features, None)
            except Exception:
                pass

        logger.info(f"[IMAGER] Ingested concept image: '{word}'")
        return True

    except Exception as e:
        logger.warning(f"[IMAGER] Ingestion error for '{word}': {e}")
        return False


# ---------------------------------------------------------------------------
# Main cycle — drain SEMANTIC+ nodes that haven't been imaged yet
# ---------------------------------------------------------------------------

def run_concept_image_cycle(
    oets: Any,
    hardware: Any,
    sensory_crystal: Any,
    state_dir: str | Path,
    max_per_run: int = 6,
) -> int:
    """
    Find OETS nodes at SEMANTIC level (scaffolding_level >= 2) that haven't
    had an image fetched yet, fetch + ingest up to `max_per_run` of them.
    Returns count of successfully ingested images this run.
    """
    state_dir = Path(state_dir)
    tracker = _load_tracker(state_dir)
    fetched = set(tracker.get("fetched", []))
    failed = set(tracker.get("failed", []))
    grounded = set(tracker.get("grounded", []))

    # Collect candidates from OETS web
    candidates: List[str] = []
    try:
        web = getattr(oets, "web", None)
        if web is None:
            return 0
        for word, node in web.nodes.items():
            concept_path = state_dir / "vision_seeds" / "concepts" / f"{word}.jpg"
            if word in grounded:
                continue
            if word in failed and not concept_path.exists():
                continue
            sl = getattr(node, "scaffolding_level", 0)
            if sl >= 2:
                candidates.append(word)
    except Exception as e:
        logger.debug(f"[IMAGER] Candidate scan failed: {e}")
        return 0

    if not candidates:
        return 0

    # Sort by ontological depth descending — most developed concepts first
    try:
        candidates.sort(
            key=lambda w: getattr(oets.web.nodes.get(w), "ontological_depth", 0.0),
            reverse=True,
        )
    except Exception:
        pass

    ingested = 0
    for word in candidates[:max_per_run]:
        img_path = fetch_concept_image(word, state_dir)
        if img_path is not None:
            ok = ingest_concept_image(img_path, word, hardware, sensory_crystal)
            if ok:
                if word not in fetched:
                    tracker.setdefault("fetched", []).append(word)
                    fetched.add(word)
                if word not in grounded:
                    tracker.setdefault("grounded", []).append(word)
                    grounded.add(word)
                ingested += 1
            else:
                if word not in failed:
                    tracker.setdefault("failed", []).append(word)
                    failed.add(word)
        else:
            if word not in failed:
                tracker.setdefault("failed", []).append(word)
                failed.add(word)

        _save_tracker(state_dir, tracker)
        time.sleep(0.3)  # gentle rate-limit

    if ingested:
        logger.info(f"[IMAGER] Cycle complete: {ingested}/{len(candidates[:max_per_run])} images ingested")
    return ingested
