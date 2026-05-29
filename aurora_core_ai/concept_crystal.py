"""
Unified concept crystal hierarchy.

Every concept Aurora develops lives as a ConceptCrystalNode that spans ALL
of her sense dimensions simultaneously. The architecture:

  BASE crystal       — a node activated by a single sense (visual pattern,
                       audio signature, semantic LSA path, proprioceptive
                       body reading, or self-observation axis state)

  COMPOSITE crystal  — when two or more senses can both be equated with the
                       same concept (co-activate at the same axis state),
                       they form a composite crystal that holds both

  HIGHER-ORDER       — composite that has accumulated activations across
                       three or more dimensions and stable SediMemory resonance

  QUASI              — deeply integrated across four+ dimensions with strong
                       SediMemory sediment; the same level as King Quasicrystal
                       in the identity stack

The concept's identity is its axis-state fingerprint — the region of
constraint-physics space where it consistently activates. This is not a
human label; it is an emergent coordinate. The same concept can be reached
from any sense dimension that co-activates in that region.

The current_overlay field records how the specific instance being observed
RIGHT NOW deviates from the concept's accumulated archetype — this is "this
particular tree" vs. "trees in general" as Aurora has come to know them.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Sense dimensions — Aurora's first-class perceptual channels
# ---------------------------------------------------------------------------

class SensoryDim(str, Enum):
    VISUAL          = "visual"          # camera / screen visual pattern
    AUDIO           = "audio"           # microphone
    SEMANTIC        = "semantic"        # language field / LSA path crossing
    PROPRIOCEPTIVE  = "proprioceptive"  # hardware body (battery/motion/light)
    SELF_OBS        = "self_obs"        # axis state / self-model mirror


# Promotion thresholds — cross-dimension co-activations required per stage
_STAGE_THRESHOLDS: Dict[str, int] = {
    "base":         0,
    "composite":    3,
    "higher_order": 12,
    "quasi":        40,
}

# Dimension requirements per stage
_STAGE_MIN_DIMS: Dict[str, int] = {
    "base":         1,
    "composite":    2,
    "higher_order": 3,
    "quasi":        4,
}

# SediMemory resonance required for quasi
_QUASI_SEDI_FLOOR: float = 5.0


# ---------------------------------------------------------------------------
# ConceptCrystalNode
# ---------------------------------------------------------------------------

@dataclass
class ConceptCrystalNode:
    """
    A single concept as Aurora knows it — unified across all her senses.

    Identified by an axis_bucket (the discretized axis state where it
    reliably activates) rather than a human-assigned label. Concepts are
    not named top-down; they emerge from repeated co-occurrence of
    activations in the same constraint-physics region.

    The current_overlay records how the specific instance being observed
    now differs from the accumulated archetype — the "this specific one"
    dimension the user described.
    """
    node_id:         str
    stage:           str    # base | composite | higher_order | quasi
    generation:      int    # promotion count

    # Axis fingerprint — which region of constraint space this concept lives in
    axis_bucket:     Tuple[float, ...]   # (X, T, N, B, A) rounded to 0.1

    # Per-dimension sense links — node refs from each sensory system
    dim_links:       Dict[str, List[str]]   # SensoryDim.value → [node_ref, ...]

    # LSA path keys that co-activate in this axis region
    lsa_keys:        List[str]

    # Accumulated SediMemory resonance strength in this axis region
    sedi_resonance:  float

    # Cross-dimension co-activation count — drives promotion
    cross_hits:      int

    # Which dimensions have activated at least once for this node
    active_dims:     Set[str]

    # What's specific about the current observation vs. the archetype
    # Cleared at the start of every turn; populated by observe_sensory()
    current_overlay: Dict[str, Any]

    # Timestamps
    first_seen:      float
    last_seen:       float

    # ── Observation API ───────────────────────────────────────────────────

    def observe(
        self,
        dim:      SensoryDim,
        node_ref: str,
        overlay:  Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a sensory activation from one dimension.
        overlay: specific properties of THIS instance vs. the archetype.
        Returns True if this observation triggered a promotion.
        """
        self.last_seen = time.time()
        dk = dim.value if isinstance(dim, SensoryDim) else str(dim)
        self.dim_links.setdefault(dk, [])
        if node_ref not in self.dim_links[dk]:
            self.dim_links[dk].append(node_ref)
        self.active_dims.add(dk)

        # Count a cross-hit whenever we have 2+ active dimensions
        if len(self.active_dims) >= 2:
            self.cross_hits += 1

        if overlay:
            self.current_overlay.update(overlay)

        return self._try_promote()

    def observe_lsa(self, path_key: str) -> bool:
        """Record an LSA semantic path crossing that co-occurs in this axis region."""
        self.last_seen = time.time()
        if path_key not in self.lsa_keys:
            self.lsa_keys.append(path_key)
        self.active_dims.add(SensoryDim.SEMANTIC.value)
        if len(self.active_dims) >= 2:
            self.cross_hits += 1
        return self._try_promote()

    def observe_sedi(self, delta: float) -> bool:
        """Accumulate SediMemory resonance. Returns True on promotion."""
        self.sedi_resonance = min(50.0, self.sedi_resonance + delta)
        return self._try_promote()

    def clear_overlay(self) -> None:
        """Called at turn start — clears the specific-instance overlay."""
        self.current_overlay = {}

    # ── Promotion logic ───────────────────────────────────────────────────

    def _try_promote(self) -> bool:
        n_dims = len(self.active_dims)
        hits   = self.cross_hits
        sedi   = self.sedi_resonance
        next_s = None

        if self.stage == "base":
            if hits >= _STAGE_THRESHOLDS["composite"] and n_dims >= _STAGE_MIN_DIMS["composite"]:
                next_s = "composite"
        elif self.stage == "composite":
            if hits >= _STAGE_THRESHOLDS["higher_order"] and n_dims >= _STAGE_MIN_DIMS["higher_order"]:
                next_s = "higher_order"
        elif self.stage == "higher_order":
            if (hits >= _STAGE_THRESHOLDS["quasi"]
                    and n_dims >= _STAGE_MIN_DIMS["quasi"]
                    and sedi >= _QUASI_SEDI_FLOOR):
                next_s = "quasi"

        if next_s:
            self.stage = next_s
            self.generation += 1
            return True
        return False

    # ── Introspection ─────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        return {
            "node_id":        self.node_id,
            "stage":          self.stage,
            "generation":     self.generation,
            "cross_hits":     self.cross_hits,
            "active_dims":    sorted(self.active_dims),
            "n_lsa_keys":     len(self.lsa_keys),
            "sedi_resonance": round(self.sedi_resonance, 3),
            "axis_bucket":    list(self.axis_bucket),
            "overlay":        dict(self.current_overlay),
        }

    # ── Serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id":        self.node_id,
            "stage":          self.stage,
            "generation":     self.generation,
            "axis_bucket":    list(self.axis_bucket),
            "dim_links":      self.dim_links,
            "lsa_keys":       self.lsa_keys,
            "sedi_resonance": self.sedi_resonance,
            "cross_hits":     self.cross_hits,
            "active_dims":    sorted(self.active_dims),
            "first_seen":     self.first_seen,
            "last_seen":      self.last_seen,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConceptCrystalNode":
        return cls(
            node_id        = d["node_id"],
            stage          = d["stage"],
            generation     = d["generation"],
            axis_bucket    = tuple(d["axis_bucket"]),
            dim_links      = d["dim_links"],
            lsa_keys       = d["lsa_keys"],
            sedi_resonance = d["sedi_resonance"],
            cross_hits     = d["cross_hits"],
            active_dims    = set(d["active_dims"]),
            current_overlay= {},
            first_seen     = d["first_seen"],
            last_seen      = d["last_seen"],
        )


# ---------------------------------------------------------------------------
# ConceptCrystalRegistry
# ---------------------------------------------------------------------------

class ConceptCrystalRegistry:
    """
    The full population of ConceptCrystalNodes, indexed by axis_bucket.

    Axis-bucket lookup: given the current axis state, find the nearest
    existing crystal (within 0.20 Euclidean distance) or create a new
    base-level crystal for this region of constraint space.

    This is the unified store that spans ALL of Aurora's senses for
    every concept she is developing. It does not know concept names —
    it knows axis-state regions and which senses have co-activated there.
    """

    BUCKET_RESOLUTION: float = 0.10   # axis values discretized to 0.1
    PROXIMITY_RADIUS:  float = 0.20   # max Euclidean distance to merge buckets
    MAX_NODES:         int   = 3000   # cap to prevent unbounded growth
    CULL_FRACTION:     float = 0.08   # fraction culled when cap is reached

    def __init__(self) -> None:
        self._nodes:     Dict[str, ConceptCrystalNode] = {}   # node_id → node
        self._ax_index:  Dict[tuple, str]               = {}   # axis_bucket → node_id
        self._promo_log: List[Dict[str, Any]]           = []

    # ── Axis bucket helpers ───────────────────────────────────────────────

    @staticmethod
    def _to_bucket(ax: Dict[str, float]) -> Tuple[float, ...]:
        r = ConceptCrystalRegistry.BUCKET_RESOLUTION
        return tuple(round(ax.get(k, 0.5) / r) * r for k in ("X", "T", "N", "B", "A"))

    def _nearest(self, ax: Dict[str, float]) -> Optional[str]:
        """
        Return node_id of the nearest bucket within PROXIMITY_RADIUS,
        or None if no bucket is close enough.
        """
        target = self._to_bucket(ax)
        best_d = float("inf")
        best_id: Optional[str] = None
        for bkt, nid in self._ax_index.items():
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, bkt)))
            if d < best_d:
                best_d = d
                best_id = nid
        if best_d <= self.PROXIMITY_RADIUS:
            return best_id
        return None

    def _get_or_create(self, ax: Dict[str, float]) -> ConceptCrystalNode:
        nid = self._nearest(ax)
        if nid is not None:
            return self._nodes[nid]

        if len(self._nodes) >= self.MAX_NODES:
            self._cull()

        bkt  = self._to_bucket(ax)
        nid  = str(uuid.uuid4())[:12]
        node = ConceptCrystalNode(
            node_id        = nid,
            stage          = "base",
            generation     = 0,
            axis_bucket    = bkt,
            dim_links      = {},
            lsa_keys       = [],
            sedi_resonance = 0.0,
            cross_hits     = 0,
            active_dims    = set(),
            current_overlay= {},
            first_seen     = time.time(),
            last_seen      = time.time(),
        )
        self._nodes[nid]    = node
        self._ax_index[bkt] = nid
        return node

    def _cull(self) -> None:
        to_remove = sorted(self._nodes.values(), key=lambda n: n.last_seen)
        cut = max(1, int(len(to_remove) * self.CULL_FRACTION))
        for n in to_remove[:cut]:
            self._nodes.pop(n.node_id, None)
            self._ax_index.pop(n.axis_bucket, None)

    # ── Public sense observation API ──────────────────────────────────────

    def observe_sensory(
        self,
        ax:       Dict[str, float],
        dim:      SensoryDim,
        node_ref: str,
        overlay:  Optional[Dict[str, Any]] = None,
    ) -> ConceptCrystalNode:
        """
        Record a raw sense activation at this axis state.
        overlay: what's specific about this particular instance vs. the archetype.
        Returns the node that received the observation.
        """
        node     = self._get_or_create(ax)
        promoted = node.observe(dim, node_ref, overlay)
        if promoted:
            self._log_promotion(node)
        return node

    def observe_lsa(self, ax: Dict[str, float], path_key: str) -> ConceptCrystalNode:
        """
        Record a semantic LSA path crossing at this axis state.
        Semantic is treated as a first-class sense dimension — not separate
        from the sensory crystal, but as a peer dimension within the
        ConceptCrystalNode that can pair with any other sense.
        """
        node     = self._get_or_create(ax)
        promoted = node.observe_lsa(path_key)
        if promoted:
            self._log_promotion(node)
        return node

    def observe_sedi(self, ax: Dict[str, float], delta: float = 0.05) -> None:
        """
        Accumulate SediMemory resonance on the crystal at this axis state.
        Does NOT create a new node — resonance only strengthens existing ones.
        """
        nid = self._nearest(ax)
        if nid is not None:
            node     = self._nodes[nid]
            promoted = node.observe_sedi(delta)
            if promoted:
                self._log_promotion(node)

    def clear_turn_overlays(self) -> None:
        """Called at the start of each turn — clears all specific-instance overlays."""
        for n in self._nodes.values():
            n.clear_overlay()

    # ── Query API ─────────────────────────────────────────────────────────

    def query(self, ax: Dict[str, float]) -> Optional[ConceptCrystalNode]:
        """Return the concept crystal nearest to this axis state, or None."""
        nid = self._nearest(ax)
        return self._nodes.get(nid) if nid else None

    def query_composite_or_higher(self, ax: Dict[str, float]) -> Optional[ConceptCrystalNode]:
        """Return the nearest crystal that has at least reached composite stage."""
        node = self.query(ax)
        if node and node.stage in ("composite", "higher_order", "quasi"):
            return node
        return None

    def nodes_by_stage(self, stage: str) -> List[ConceptCrystalNode]:
        return [n for n in self._nodes.values() if n.stage == stage]

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {"base": 0, "composite": 0, "higher_order": 0, "quasi": 0}
        for n in self._nodes.values():
            counts[n.stage] = counts.get(n.stage, 0) + 1
        return {
            "total":        len(self._nodes),
            "by_stage":     counts,
            "promo_events": len(self._promo_log),
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, state_dir: str) -> None:
        path = os.path.join(state_dir, "concept_crystals.json.gz")
        try:
            data = {
                "nodes":    [n.to_dict() for n in self._nodes.values()],
                "promo_log": self._promo_log[-500:],   # keep last 500
            }
            with gzip.open(path, "wt", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def load(self, state_dir: str) -> None:
        path = os.path.join(state_dir, "concept_crystals.json.gz")
        if not os.path.exists(path):
            return
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
            for nd in data.get("nodes", []):
                node = ConceptCrystalNode.from_dict(nd)
                self._nodes[node.node_id]            = node
                self._ax_index[node.axis_bucket]     = node.node_id
            self._promo_log = data.get("promo_log", [])
        except Exception:
            pass

    def _log_promotion(self, node: ConceptCrystalNode) -> None:
        self._promo_log.append({
            "node_id":    node.node_id,
            "stage":      node.stage,
            "generation": node.generation,
            "cross_hits": node.cross_hits,
            "n_dims":     len(node.active_dims),
            "active_dims":sorted(node.active_dims),
            "ts":         time.time(),
        })
