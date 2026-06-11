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

# SECTION 1: FEATURE EXTRACTION
# ============================================================================

@dataclass
class VisualFeatureVector:
    """Feature vector for a single image."""
    image_path:   str
    image_hash:   str
    width:        int   = 0
    height:       int   = 0
    brightness:   float = 0.0   # 0=dark, 1=bright
    contrast:     float = 0.0   # 0=flat, 1=high contrast
    edge_density: float = 0.0   # 0=smooth, 1=many edges
    color_r:      float = 0.0   # avg red channel (0-1)
    color_g:      float = 0.0   # avg green channel (0-1)
    color_b:      float = 0.0   # avg blue channel (0-1)
    saturation:   float = 0.0   # 0=grayscale, 1=vivid
    aspect_ratio: float = 1.0   # w/h
    timestamp:    float = field(default_factory=time.time)

    def to_vector(self) -> List[float]:
        """8-dimensional feature vector for clustering."""
        return [
            self.brightness,
            self.contrast,
            self.edge_density,
            self.color_r,
            self.color_g,
            self.color_b,
            self.saturation,
            min(self.aspect_ratio, 3.0) / 3.0,
        ]

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "VisualFeatureVector":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


class FeatureExtractor:
    """
    Extracts feature vectors from image files.
    Uses PIL/Pillow if available; degrades to a stub otherwise.
    """

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}

    def extract(self, image_path: str) -> Optional[VisualFeatureVector]:
        """Extract features from an image file. Returns None if unavailable."""
        if not _PIL_AVAILABLE:
            return self._stub_extract(image_path)

        try:
            img = PILImage.open(image_path).convert("RGB")
            return self._extract_from_pil(image_path, img)
        except Exception as e:
            logger.debug(f"[Vision] Feature extraction failed for {image_path}: {e}")
            return None

    def _extract_from_pil(self, path: str, img) -> VisualFeatureVector:
        w, h = img.size
        pixels = list(img.getdata())  # List of (R, G, B) tuples

        n = max(1, len(pixels))
        r_vals = [p[0] / 255.0 for p in pixels]
        g_vals = [p[1] / 255.0 for p in pixels]
        b_vals = [p[2] / 255.0 for p in pixels]

        avg_r = sum(r_vals) / n
        avg_g = sum(g_vals) / n
        avg_b = sum(b_vals) / n

        brightness = (avg_r * 0.299 + avg_g * 0.587 + avg_b * 0.114)

        # Variance as contrast proxy
        def variance(vals, mean):
            return sum((v - mean) ** 2 for v in vals) / max(1, len(vals))

        contrast = math.sqrt(
            variance(r_vals, avg_r) * 0.299 +
            variance(g_vals, avg_g) * 0.587 +
            variance(b_vals, avg_b) * 0.114
        )

        # Edge density: simple horizontal gradient on a downsampled grid
        edge_density = self._estimate_edge_density(img)

        # Saturation: max(R,G,B) - min(R,G,B) per pixel, averaged
        sat_vals = [max(r, g, b) - min(r, g, b) for r, g, b in
                    [(p[0]/255., p[1]/255., p[2]/255.) for p in pixels]]
        saturation = sum(sat_vals) / n

        img_hash = hashlib.md5(open(path, 'rb').read(4096)).hexdigest()[:16]

        return VisualFeatureVector(
            image_path=path,
            image_hash=img_hash,
            width=w, height=h,
            brightness=brightness,
            contrast=min(contrast * 4, 1.0),
            edge_density=edge_density,
            color_r=avg_r, color_g=avg_g, color_b=avg_b,
            saturation=saturation,
            aspect_ratio=w / max(1, h),
        )

    def _estimate_edge_density(self, img, sample_size: int = 64) -> float:
        """Estimate edge density using a small downsampled version."""
        try:
            small = img.resize((sample_size, sample_size)).convert("L")
            gray = list(small.getdata())
            edges = 0
            for y in range(sample_size - 1):
                for x in range(sample_size - 1):
                    dx = abs(gray[y * sample_size + x] - gray[y * sample_size + x + 1])
                    dy = abs(gray[y * sample_size + x] - gray[(y + 1) * sample_size + x])
                    if (dx + dy) / 2 > 20:
                        edges += 1
            return edges / max(1, (sample_size - 1) ** 2)
        except Exception:
            return 0.0

    def _stub_extract(self, path: str) -> VisualFeatureVector:
        """Stub when PIL unavailable: return near-zero vector with file hash."""
        img_hash = hashlib.md5(path.encode()).hexdigest()[:16]
        return VisualFeatureVector(
            image_path=path, image_hash=img_hash,
            brightness=0.5, contrast=0.5, edge_density=0.5,
            color_r=0.5, color_g=0.5, color_b=0.5,
            saturation=0.5, aspect_ratio=1.0,
        )


# ============================================================================
# SECTION 2: CLUSTERING
# ============================================================================

@dataclass
class VisualCluster:
    """A cluster of visually similar images."""
    cluster_id:    str
    centroid:      List[float]   # 8-dim centroid
    members:       List[str]     # image paths
    confidence:    float = 0.0   # how stable/tight the cluster is
    concept_label: str   = ""    # OETS binding (empty until confident)
    oets_bound:    bool  = False
    created_at:    float = field(default_factory=time.time)
    updated_at:    float = field(default_factory=time.time)

    def update_centroid(self, vectors: List[List[float]]):
        """Recompute centroid from member vectors."""
        if not vectors:
            return
        n = len(vectors)
        dim = len(vectors[0])
        self.centroid = [sum(v[i] for v in vectors) / n for i in range(dim)]
        self.updated_at = time.time()

    def tightness(self, vectors: List[List[float]]) -> float:
        """Measure how tight this cluster is (1=very tight, 0=loose)."""
        if len(vectors) < 2:
            return 1.0
        distances = [_euclidean(self.centroid, v) for v in vectors]
        avg_dist = sum(distances) / len(distances)
        return max(0.0, 1.0 - avg_dist)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "VisualCluster":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


def _euclidean(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class SimpleKMeans:
    """Pure-Python k-means for feature vector clustering."""

    def __init__(self, k: int = 8, max_iter: int = 30, tol: float = 0.01):
        self.k = k
        self.max_iter = max_iter
        self.tol = tol

    def fit(self, vectors: List[List[float]]) -> List[int]:
        """
        Fit k-means. Returns cluster assignments (one per vector).
        Falls back to numpy if available (faster).
        """
        if not vectors:
            return []

        n = len(vectors)
        k = min(self.k, n)

        if _NP_AVAILABLE:
            return self._fit_numpy(vectors, k)
        return self._fit_pure(vectors, k)

    def _fit_numpy(self, vectors, k: int) -> List[int]:
        X = np.array(vectors)
        # k-means++ initialization
        centers = [X[np.random.randint(len(X))]]
        for _ in range(k - 1):
            dists = np.min(np.array([[np.linalg.norm(x - c) for c in centers]
                                      for x in X]), axis=1)
            probs = dists ** 2 / (dists ** 2).sum()
            centers.append(X[np.random.choice(len(X), p=probs)])
        centers = np.array(centers)

        assignments = np.zeros(len(X), dtype=int)
        for _ in range(self.max_iter):
            dists = np.array([[np.linalg.norm(x - c) for c in centers] for x in X])
            new_assignments = np.argmin(dists, axis=1)
            if np.all(new_assignments == assignments):
                break
            assignments = new_assignments
            for i in range(k):
                mask = assignments == i
                if mask.any():
                    centers[i] = X[mask].mean(axis=0)
        return assignments.tolist()

    def _fit_pure(self, vectors: List[List[float]], k: int) -> List[int]:
        """Pure Python k-means."""
        import random
        n = len(vectors)
        dim = len(vectors[0])

        # Random init
        centers = [list(vectors[i]) for i in random.sample(range(n), k)]
        assignments = [0] * n

        for _ in range(self.max_iter):
            # Assign
            new_assignments = []
            for v in vectors:
                dists = [_euclidean(v, c) for c in centers]
                new_assignments.append(dists.index(min(dists)))

            if new_assignments == assignments:
                break
            assignments = new_assignments

            # Update centers
            for i in range(k):
                members = [vectors[j] for j in range(n) if assignments[j] == i]
                if members:
                    centers[i] = [sum(m[d] for m in members) / len(members)
                                  for d in range(dim)]

        return assignments


# ============================================================================
# SECTION 3: OETS BINDING
# ============================================================================

class OETSVisionBinder:
    """
    Binds visual clusters to OETS ontology nodes as "looks_like" relations.

    Conservative naming: only assigns a concept_label when confidence > 0.75.
    Low confidence clusters are stored as "visual_region_N" until they mature.
    """

    CONFIDENCE_THRESHOLD = 0.75

    def __init__(self, oets=None):
        self._oets = oets  # OntologicalScaffoldingEngine instance (optional)

    def bind_cluster(self, cluster: VisualCluster,
                     all_vectors: List[VisualFeatureVector]) -> str:
        """
        Determine a concept label for the cluster (or keep unnamed).
        If confident, bind to OETS.
        Returns the label (or empty string if unnamed).
        """
        # Compute tightness as confidence proxy
        member_vecs = [fv.to_vector() for fv in all_vectors
                       if fv.image_path in cluster.members]
        if not member_vecs:
            return ""

        tightness = cluster.tightness(member_vecs)
        size_factor = min(len(cluster.members) / 10.0, 1.0)
        confidence = tightness * 0.7 + size_factor * 0.3
        cluster.confidence = confidence

        label = ""
        if confidence >= self.CONFIDENCE_THRESHOLD:
            label = self._infer_label(cluster)
            cluster.concept_label = label
            cluster.oets_bound = True

            if self._oets and label:
                self._bind_to_oets(cluster, label)
        else:
            cluster.concept_label = ""  # keep unnamed

        return label

    def _infer_label(self, cluster: VisualCluster) -> str:
        """Infer a rough semantic label from the cluster centroid."""
        c = cluster.centroid
        # c = [brightness, contrast, edge_density, r, g, b, saturation, aspect]
        brightness, contrast, edges, r, g, b, sat, aspect = c

        labels = []

        # Brightness descriptors
        if brightness > 0.7:
            labels.append("bright_scene")
        elif brightness < 0.3:
            labels.append("dark_scene")

        # Dominant color hue
        if sat > 0.3:
            max_channel = max(r, g, b)
            if max_channel == r and r > g + 0.15 and r > b + 0.15:
                labels.append("red_dominant")
            elif max_channel == g and g > r + 0.1:
                labels.append("green_dominant")
            elif max_channel == b and b > r + 0.1:
                labels.append("blue_dominant")
        else:
            labels.append("neutral_tone")

        # Edge density -- high edges suggest text/detail, low suggests solid areas
        if edges > 0.5:
            labels.append("detailed_texture")
        elif edges < 0.2:
            labels.append("smooth_area")

        # Aspect ratio
        if aspect > 1.8:
            labels.append("wide_scene")
        elif aspect < 0.6:
            labels.append("tall_subject")

        return "_".join(labels[:3]) if labels else "visual_pattern"

    def _bind_to_oets(self, cluster: VisualCluster, label: str):
        """Create or update an OETS node for this visual concept."""
        if not self._oets:
            return
        try:
            web = self._oets.web
            # Get or create node
            node = web.get_node(label)
            if node is None:
                web.add_node(label, role="visual_concept",
                             definition=f"Visual pattern cluster: {label}")

            # Add visual context
            node = web.get_node(label)
            if node:
                node.add_definition(
                    f"Visual cluster with {len(cluster.members)} images. "
                    f"Brightness={cluster.centroid[0]:.2f}, "
                    f"Edges={cluster.centroid[2]:.2f}.",
                    source="vision_bootstrap",
                    confidence=cluster.confidence,
                )
        except Exception:
            pass


# ============================================================================
