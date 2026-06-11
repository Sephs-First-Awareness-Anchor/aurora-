#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA VISION BOOTSTRAP
========================
Seeds visual primitives WITHOUT requiring a working camera.

Aurora builds visual understanding from:
  1. Images in aurora_state/vision_seeds/        (manual -- you drop them in)
  2. Public-domain images downloaded from web    (autonomous -- during idle)

HOW IT WORKS:
  - Extract feature vectors from images (color histogram, edge density,
    brightness, texture stats -- all from stdlib/optional numpy)
  - Cluster similar images into "visual concept groups"
  - Bind clusters to OETS ontology nodes as "looks_like" relations
  - Conservative naming: no confident labels unless confidence > 0.75
  - When camera eventually works: it REFINES existing clusters, not replaces

OUTPUT:
  aurora_state/vision_index.json   -- cluster manifests + OETS bindings
  aurora_state/vision_seeds/web/   -- autonomously downloaded images

DEPENDENCIES (all optional -- degrades gracefully):
  - PIL/Pillow: image loading + feature extraction
  - numpy: clustering math (falls back to pure Python if absent)

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import json
import time
import math
import hashlib
import logging
import threading
import urllib.request
import urllib.parse
from aurora_persistence_utils import PERSISTENCE_LOCK, atomic_write_json
from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# Optional imports
try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
    logger.info("[Vision] Pillow not installed. Install with: pip install Pillow")

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    import array
    _NP_AVAILABLE = False


# ============================================================================

from aurora_vision_clustering import (
    VisualFeatureVector, FeatureExtractor, VisualCluster, SimpleKMeans, OETSVisionBinder,
)

# ============================================================================
# SECTION 4: WEB IMAGE DOWNLOADER
# ============================================================================

class WebImageDownloader:
    """
    Downloads public-domain images from Wikipedia/Wikimedia for Aurora's visual seeds.

    Rate limited: max 20 downloads per day autonomously.
    Saves to aurora_state/vision_seeds/web/
    """

    DAILY_LIMIT = 20
    STATE_PATH  = "aurora_state/web_image_download_state.json"
    SAVE_DIR    = "aurora_state/vision_seeds/web"
    USER_AGENT  = "Aurora/2.0 VisionBootstrap (Educational; not-commercial)"

    # Concept seeds to download images for
    SEED_CONCEPTS = [
        "face", "tree", "sky", "water", "light", "shadow",
        "hand", "eye", "circle", "line", "color", "texture",
        "motion", "object", "pattern", "space", "depth",
    ]

    def __init__(self, network_gateway=None, allow_network: bool = False):
        self.network_gateway = network_gateway
        self.allow_network = allow_network
        self._downloads_today: int = 0
        self._date: str = ""
        self._downloaded: set = set()
        self.load_state()

    def _reset_if_new_day(self):
        today = time.strftime("%Y-%m-%d")
        if today != self._date:
            self._date = today
            self._downloads_today = 0

    def can_download(self) -> bool:
        self._reset_if_new_day()
        if self.allow_network and not self.network_gateway:
            return False
        return self._downloads_today < self.DAILY_LIMIT

    def download_for_concept(self, concept: str) -> List[str]:
        """
        Attempt to download 1-2 images related to a concept from Wikimedia.
        Returns list of saved file paths.
        """
        if not self.allow_network:
            return []
        if self.allow_network and not self.network_gateway:
            logger.debug("[Vision] Refusing download: allow_network=True requires network_gateway.")
            return []
        if not self.can_download():
            return []

        saved = []
        os.makedirs(self.SAVE_DIR, exist_ok=True)

        try:
            urls = self._find_wikimedia_images(concept)
            for url in urls[:2]:
                if not self.can_download():
                    break
                if url in self._downloaded:
                    continue
                path = self._download_image(url, concept)
                if path:
                    saved.append(path)
                    self._downloaded.add(url)
                    self._downloads_today += 1
        except Exception as e:
            logger.debug(f"[Vision] Download failed for concept '{concept}': {e}")

        self.save_state()
        return saved

    def _find_wikimedia_images(self, concept: str) -> List[str]:
        """Search Wikipedia for images related to a concept."""
        try:
            if not self.network_gateway:
                return []
            query = urllib.parse.quote(concept)
            api_url = (f"https://en.wikipedia.org/api/rest_v1/page/summary/"
                       f"{query}")
            if hasattr(self.network_gateway, 'fetch_json'):
                data = self.network_gateway.fetch_json(api_url, headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"}, timeout=10)
            else:
                return []

            img_url = data.get("thumbnail", {}).get("source", "")
            if img_url:
                # Get original size
                original = data.get("originalimage", {}).get("source", img_url)
                return [original]
            return []
        except Exception:
            return []

    def _download_image(self, url: str, concept: str) -> Optional[str]:
        """Download a single image URL. Returns saved path or None."""
        try:
            if not self.network_gateway:
                return None
            ext = os.path.splitext(url.split("")[0])[1].lower()
            if not ext or ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"

            name = f"{concept}_{hashlib.md5(url.encode()).hexdigest()[:8]}{ext}"
            save_path = os.path.join(self.SAVE_DIR, name)

            if os.path.exists(save_path):
                return save_path

            if hasattr(self.network_gateway, 'download_bytes'):
                data = self.network_gateway.download_bytes(url, headers={"User-Agent": self.USER_AGENT}, timeout=15)
            else:
                return None

            # Sanity check: must be at least 1KB and look like an image
            if len(data) < 1024:
                return None
            if not (data[:8].startswith(b'\xff\xd8') or  # JPEG
                    data[:8].startswith(b'\x89PNG') or    # PNG
                    data[:8].startswith(b'RIFF')):         # WebP
                return None

            with PERSISTENCE_LOCK:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(data)

            logger.debug(f"[Vision] Downloaded image for '{concept}': {name}")
            return save_path

        except Exception as e:
            logger.debug(f"[Vision] Image download error: {e}")
            return None

    def download_seed_batch(self, n_concepts: int = 5) -> List[str]:
        """Download images for N random seed concepts."""
        import random
        concepts = random.sample(self.SEED_CONCEPTS, min(n_concepts, len(self.SEED_CONCEPTS)))
        all_paths = []
        for concept in concepts:
            paths = self.download_for_concept(concept)
            all_paths.extend(paths)
        return all_paths

    def save_state(self):
        data = {
            "date": self._date,
            "downloads_today": self._downloads_today,
            "downloaded": list(self._downloaded)[:500],  # cap size
        }
        try:
            os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
            with PERSISTENCE_LOCK:
                atomic_write_json(Path(self.STATE_PATH), data, indent=2)
        except Exception:
            pass

    def load_state(self):
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH) as f:
                data = json.load(f)
            self._date = data.get("date", "")
            self._downloads_today = data.get("downloads_today", 0)
            self._downloaded = set(data.get("downloaded", []))
            self._reset_if_new_day()
        except Exception:
            pass


# ============================================================================
# SECTION 5: IMAGE INGESTION PROTOCOL -- ORCHESTRATOR
# ============================================================================

class ImageIngestionProtocol:
    """
    Main orchestrator for Aurora's vision bootstrapping.

    Workflow:
      1. Scan vision_seeds/ folder for images
      2. Extract feature vectors
      3. Cluster into visual concept groups
      4. Bind clusters to OETS ontology
      5. Save vision_index.json

    Also manages autonomous web downloads during idle cycles.
    """

    SEED_DIR    = "aurora_state/vision_seeds"
    INDEX_PATH  = "aurora_state/vision_index.json"

    def __init__(self, oets=None, network_gateway=None, allow_network: bool = False):
        self.extractor  = FeatureExtractor()
        self.clusterer  = SimpleKMeans(k=12)
        self.binder     = OETSVisionBinder(oets)
        self.downloader = WebImageDownloader(network_gateway=network_gateway, allow_network=allow_network)
        self._oets      = oets

        self._vectors:  Dict[str, VisualFeatureVector]  = {}
        self._clusters: Dict[str, VisualCluster]        = {}
        self._lock      = threading.RLock()

        os.makedirs(self.SEED_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.SEED_DIR, "web"), exist_ok=True)
        self.load_index()

    def _constraint_axes(self) -> Dict[str, float]:
        with self._lock:
            vector_count = len(self._vectors)
            cluster_count = len(self._clusters)
            named_count = sum(1 for cluster in self._clusters.values() if cluster.concept_label)
        return {
            "X": min(1.0, 0.20 + vector_count / 150.0),
            "T": 0.20 + (0.15 if self._vectors else 0.0),
            "N": min(1.0, 0.15 + self.downloader._downloads_today / 20.0),
            "B": min(1.0, 0.20 + cluster_count / 30.0),
            "A": min(1.0, 0.20 + named_count / 18.0),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        with self._lock:
            named_count = sum(1 for cluster in self._clusters.values() if cluster.concept_label)
        return {
            "X": 1.0 if self._vectors else 0.0,
            "T": 0.20 if self.downloader.can_download() else 0.05,
            "N": min(1.0, self.downloader._downloads_today / 20.0),
            "B": min(1.0, len(self._clusters) / 25.0),
            "A": min(1.0, named_count / 12.0),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.20))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.15)),
            B=float(ax.get("B", 0.20)),
            A=float(ax.get("A", 0.20)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return dict(_FC.language_projection(_ExistenceMode.AGENTIC))

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        rep = {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
        }
        rep["unit_state"] = self.status()
        return rep

    def ingest_folder(self, folder: str = None) -> Dict:
        """
        Scan a folder for images, extract features, cluster, bind.
        Returns summary dict.
        """
        folder = folder or self.SEED_DIR
        supported = FeatureExtractor.SUPPORTED_FORMATS
        image_paths = []

        for root, _, files in os.walk(folder):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in supported:
                    image_paths.append(os.path.join(root, fname))

        if not image_paths:
            return {"processed": 0, "clusters": 0, "reason": "no_images_found"}

        # Extract features
        new_count = 0
        for path in image_paths:
            if path not in self._vectors:
                fv = self.extractor.extract(path)
                if fv:
                    with self._lock:
                        self._vectors[path] = fv
                    new_count += 1

        if not self._vectors:
            return {"processed": 0, "clusters": 0, "reason": "extraction_failed"}

        # Cluster
        self._recluster()

        # Save
        self.save_index()

        return {
            "processed": len(self._vectors),
            "new_this_run": new_count,
            "clusters": len(self._clusters),
            "named_clusters": sum(1 for c in self._clusters.values()
                                  if c.concept_label),
        }

    def _recluster(self):
        """Recluster all vectors and rebind OETS."""
        with self._lock:
            all_fvs = list(self._vectors.values())
        if not all_fvs:
            return

        vectors = [fv.to_vector() for fv in all_fvs]
        k = min(12, max(1, len(vectors) // 3))
        assignments = SimpleKMeans(k=k).fit(vectors)

        # Build clusters
        cluster_map: Dict[int, List[int]] = defaultdict(list)
        for i, a in enumerate(assignments):
            cluster_map[a].append(i)

        new_clusters = {}
        for cid, indices in cluster_map.items():
            members = [all_fvs[i].image_path for i in indices]
            member_vecs = [vectors[i] for i in indices]
            centroid = [sum(v[d] for v in member_vecs) / len(member_vecs)
                        for d in range(len(member_vecs[0]))]

            cid_str = f"vcluster_{cid:03d}"
            cluster = VisualCluster(
                cluster_id=cid_str,
                centroid=centroid,
                members=members,
            )
            # Bind to OETS
            self.binder.bind_cluster(cluster, all_fvs)
            new_clusters[cid_str] = cluster

        with self._lock:
            self._clusters = new_clusters

    def autonomous_download_cycle(self) -> Dict:
        """Run one autonomous download cycle during idle time."""
        if not self.downloader.can_download():
            return {"downloaded": 0, "reason": "daily_limit_reached"}

        paths = self.downloader.download_seed_batch(n_concepts=3)
        if paths:
            result = self.ingest_folder(os.path.join(self.SEED_DIR, "web"))
            result["downloaded"] = len(paths)
            return result
        return {"downloaded": 0, "reason": "download_failed"}

    def refine_from_camera_frame(self, frame_features: Dict):
        """
        Called when a live camera frame is processed.
        Refines existing clusters rather than replacing them.
        """
        fv = VisualFeatureVector(
            image_path=f"camera_{time.time():.0f}",
            image_hash=hashlib.md5(json.dumps(frame_features).encode()).hexdigest()[:16],
            brightness=frame_features.get("brightness", 0.5),
            contrast=frame_features.get("contrast", 0.5),
            edge_density=frame_features.get("edges", 0.5),
            color_r=frame_features.get("r", 0.5),
            color_g=frame_features.get("g", 0.5),
            color_b=frame_features.get("b", 0.5),
            saturation=frame_features.get("saturation", 0.5),
            aspect_ratio=frame_features.get("aspect", 1.0),
        )
        with self._lock:
            self._vectors[fv.image_path] = fv

        # Light recluster every 20 camera frames
        if len([k for k in self._vectors if k.startswith("camera_")]) % 20 == 0:
            self._recluster()
            self.save_index()

    def teach_label(self, label: str, visual_features: Dict) -> Dict:
        """
        User-driven visual teaching: bind a label to the current visual features.

        Creates a VisualFeatureVector from the provided scene features, adds it
        to the index, finds the nearest existing cluster (or creates one), names
        it with the user-provided label, and binds it to OETS.

        Returns a summary dict: {'label': str, 'cluster': str, 'oets_bound': bool}.
        """
        label = str(label or "").strip().lower()
        if not label or not visual_features:
            return {"label": label, "cluster": "", "oets_bound": False, "reason": "empty_input"}

        ts_key = f"user_teach_{time.time():.0f}_{label}"
        fv = VisualFeatureVector(
            image_path=ts_key,
            image_hash=hashlib.md5(json.dumps(visual_features, sort_keys=True).encode()).hexdigest()[:16],
            brightness=float(visual_features.get("brightness", 0.5)),
            contrast=float(visual_features.get("contrast", 0.5)),
            edge_density=float(visual_features.get("edge_density", 0.2)),
            color_r=float(visual_features.get("color_r", visual_features.get("r", 0.5))),
            color_g=float(visual_features.get("color_g", visual_features.get("g", 0.5))),
            color_b=float(visual_features.get("color_b", visual_features.get("b", 0.5))),
            saturation=float(visual_features.get("saturation", 0.2)),
            aspect_ratio=float(visual_features.get("aspect_ratio", 1.0)),
        )

        with self._lock:
            self._vectors[ts_key] = fv

        # Find nearest cluster by centroid distance; create one if none exist.
        fv_vec = fv.to_vector()
        best_cid: str = ""
        best_dist: float = float("inf")
        with self._lock:
            for cid, cl in self._clusters.items():
                if cl.centroid and len(cl.centroid) == len(fv_vec):
                    d = sum((a - b) ** 2 for a, b in zip(fv_vec, cl.centroid)) ** 0.5
                    if d < best_dist:
                        best_dist, best_cid = d, cid

        if best_cid:
            with self._lock:
                self._clusters[best_cid].members.append(ts_key)
                self._clusters[best_cid].concept_label = label
                self._clusters[best_cid].oets_bound = True
        else:
            new_cid = f"vcluster_teach_{int(time.time()) % 10000:04d}"
            new_cluster = VisualCluster(
                cluster_id=new_cid,
                centroid=fv_vec,
                members=[ts_key],
                concept_label=label,
                confidence=0.9,
                oets_bound=True,
            )
            with self._lock:
                self._clusters[new_cid] = new_cluster
            best_cid = new_cid

        # Bind to OETS
        _oets_bound = False
        if self._oets:
            try:
                cl_to_bind = self._clusters.get(best_cid)
                if cl_to_bind:
                    self.binder._bind_to_oets(cl_to_bind, label)
                    _oets_bound = True
            except Exception:
                pass

        self.save_index()
        return {"label": label, "cluster": best_cid, "oets_bound": _oets_bound}

    def save_index(self):
        with self._lock:
            data = {
                "version": "1.0",
                "timestamp": time.time(),
                "vector_count": len(self._vectors),
                "clusters": {cid: c.to_dict() for cid, c in self._clusters.items()},
                "vectors": {path: fv.to_dict()
                            for path, fv in self._vectors.items()
                            if not path.startswith("camera_")},  # don't persist camera frames
            }
        try:
            import tempfile
            dirp = os.path.dirname(os.path.abspath(self.INDEX_PATH))
            os.makedirs(dirp, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dirp, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.INDEX_PATH)
        except Exception as e:
            logger.debug(f"[Vision] Index save failed: {e}")

    def load_index(self):
        if not os.path.exists(self.INDEX_PATH):
            return
        try:
            with open(self.INDEX_PATH) as f:
                data = json.load(f)
            for path, vd in data.get("vectors", {}).items():
                self._vectors[path] = VisualFeatureVector.from_dict(vd)
            for cid, cd in data.get("clusters", {}).items():
                self._clusters[cid] = VisualCluster.from_dict(cd)
            logger.info(f"[Vision] Loaded {len(self._vectors)} vectors, "
                        f"{len(self._clusters)} clusters")
        except Exception:
            pass

    def status(self) -> Dict:
        with self._lock:
            named = [(cid, c) for cid, c in self._clusters.items() if c.concept_label]
            return {
                "vectors_indexed":    len(self._vectors),
                "clusters":           len(self._clusters),
                "named_clusters":     len(named),
                "concept_labels":     [c.concept_label for _, c in named],
                "downloads_today":    self.downloader._downloads_today,
                "downloads_available": self.downloader.can_download(),
                "seed_dir":           self.SEED_DIR,
                "pil_available":      _PIL_AVAILABLE,
                "numpy_available":    _NP_AVAILABLE,
                "lineage_signature":  (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA"),
                "runtime_regime":     self.runtime_regime(),
                "language_projection": self.language_projection(),
            }

