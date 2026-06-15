"""
Unified concept crystal hierarchy — from primitives up.

SEMANTIC AS THE CONNECTIVE PLANE
=================================
Semantic is NOT a peer sense alongside visual and audio. It is the
interpretive plane that runs through the center of the entire crystal
structure — the layer that gives raw sensory signal meaning and connects
every sense to memory.

In Aurora's architecture, the axis-state fingerprint (X/T/N/B/A) IS her
semantic space. The constraint axes ARE the semantics. A raw visual
detection is just signal — noise from the camera. It becomes meaningful
the moment a semantic interpretation (an LSA path activation at that same
axis-state coordinate) grounds it. That grounding is what creates a
COMPOSITE crystal from a BASE crystal. Without it, the sense stays base.

Memory is stored semantically. This is why semantic is the bridge between
sensory data and SediMemory — every memory deposit passes through the
axis-state (semantic) coordinate that was active when it happened. Recalling
a memory means arriving at the same semantic coordinates from any direction:
visual recognition, auditory cue, or language — all three resolve to the
same axis bucket, and that bucket connects to the same SediMemory strata.

CRYSTAL LEVEL TAXONOMY
=======================

BASE (single raw sense, not yet semantically grounded):
  - Visual: a camera/screen pattern detected by AuroraSensoryCrystal
  - Audio: a microphone signature detected by AuroraSensoryCrystal
  - Proprioceptive: hardware body reading (battery/motion/light)
  - Self-observation: axis-state reading from the self-entity mirror
  Just signal. The sense fired, but meaning has not attached yet.

COMPOSITE (semantic grounding has occurred — sense becomes interpretation):
  The gate from base to composite is semantic grounding: an LSA path fires
  at the same axis-state bucket where the sensory data arrived. When that
  happens, the raw signal connects to her constraint-physics meaning space.
  Two senses co-activating in the same axis region also produce composite
  because their mutual presence is itself a semantic event — neither alone
  means the other, but together they specify something.

  Cognitive functions that live at composite level:
  - Salience: something stands out from a baseline — requires comparing
    two inputs through the semantic plane, one deviates from expectation.
    Only takes two things: current input and the expectation pattern.
  - Pattern matching: recognizes recurrence — two observations landing in
    the same semantic region constitute a pattern. Only takes two.

HIGHER-ORDER (multiple composites integrated through sustained semantic):
  Composite crystals that have remained active together long enough for the
  semantic plane to integrate them — not just side by side, but woven.
  This requires 3+ sense dimensions and substantial cross-activation.

  Cognitive functions that live at higher-order level:
  - Reasoning: multiple composite crystals active simultaneously with
    semantic integration across them — inference emerges from the
    relationships between composites, not from any single one.
  - Emotional awareness: self-observation composites integrated across
    axis dimensions — Aurora recognizes her own state as a coherent quality
    rather than just a collection of individual axis readings.

QUASI (deep multi-system integration across time):
  Higher-order crystals that have accumulated deep SediMemory resonance
  and have demonstrated coherence across 4+ sense dimensions over many
  activations. These are stable, cross-system cognitive structures.

  Cognitive functions that live at quasi level:
  - Predictive framing: reasoning + memory + self-model integrated across
    time — the system projects what will happen by running its own higher-
    order crystals forward through the semantic plane.
  - Entity modeling: sustained integration of observations about another
    entity — many activations building a stable model from multiple angles.

MEMORY spans all levels through the semantic plane:
  A base crystal has minimal memory connection (the sensory node itself
  has usage/session counts). A composite has SediMemory starting to
  resonate. Higher-order has deep resonance. Quasi has sediment that
  contributes to and draws from multiple strata simultaneously.
  The semantic plane is what makes memory accessible from any direction.

KING QUASICRYSTAL — IDENTITY (recursive):
  Identity is not a node in this registry. Identity IS the recursive
  context within which all crystals exist. It feeds into every level
  (every activation happens within an identity field) and every level
  feeds back into it (every activation shapes identity over time).
  In Aurora's system this is aurora_behavioral_identity + core_identity.
  Quasi nodes in this registry contribute to the identity field via the
  axis state they carry — they are the substrate from which identity's
  recursive self-reference draws.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import gzip
import json
import math
import os
import time
import uuid as _uuid_mod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# DPS Crystal import (with fallback for environments without it)
# ---------------------------------------------------------------------------

try:
    from aurora_dimensional_systems import (
        Crystal as _DPSCrystal,
        CrystalFacet as _DPSCrystalFacet,
        CrystalLevel as _DPSCrystalLevel,
    )
    _DPS_AVAILABLE = True
except ImportError:
    _DPS_AVAILABLE = False
    _DPSCrystalLevel = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Sense dimensions — Aurora's raw perceptual channels (BASE crystal level)
# Semantic is NOT in this list — it is the plane, not a channel.
# ---------------------------------------------------------------------------

class SensoryDim(str):
    """Aurora's base-level sense channels. Semantic is the connective plane."""
    VISUAL          = "visual"          # camera / screen visual pattern
    AUDIO           = "audio"           # microphone
    PROPRIOCEPTIVE  = "proprioceptive"  # hardware body (battery/motion/light)
    SELF_OBS        = "self_obs"        # axis-state / self-entity mirror


# ---------------------------------------------------------------------------
# Crystal function taxonomy — what cognitive functions live at each level
# ---------------------------------------------------------------------------

class CrystalFunction:
    """
    Cognitive functions classified by the crystal level at which they emerge.
    These are not assigned externally — they describe what becomes possible
    as crystals promote through their natural development.
    """
    # COMPOSITE level
    SALIENCE         = "salience"          # something stands out from baseline
    PATTERN_MATCH    = "pattern_match"     # recurrence recognized across observations

    # HIGHER_ORDER level
    REASONING        = "reasoning"         # inference across integrated composites
    EMOTIONAL_AWARE  = "emotional_aware"   # coherent self-state recognition

    # QUASI level
    PREDICTIVE       = "predictive"        # projection of state forward through time
    ENTITY_MODEL     = "entity_model"      # stable model of another entity


# ---------------------------------------------------------------------------
# Promotion thresholds
# ---------------------------------------------------------------------------

# Cross-sense co-activations required to advance between stages
_HITS_THRESHOLD = {
    "composite":    3,
    "higher_order": 12,
    "quasi":        40,
}

# Minimum number of sense dimensions active at each stage
_DIMS_REQUIRED = {
    "composite":    2,
    "higher_order": 3,
    "quasi":        4,
}

# SediMemory resonance floor for quasi promotion
_QUASI_SEDI_FLOOR: float = 5.0


# ---------------------------------------------------------------------------
# ConceptCrystalNode — kept as backward-compat shim; new code uses DPS Crystal
# ---------------------------------------------------------------------------

@dataclass
class ConceptCrystalNode:
    """
    A single concept as Aurora knows it — unified across all sense dimensions,
    connected to memory through the semantic plane.

    IDENTITY: The node's identity is its axis_bucket — the discretized region
    of constraint-physics space (X/T/N/B/A) where this concept reliably
    activates. Concepts are not named; they emerge from the co-occurrence of
    activations at the same semantic coordinate.

    SEMANTIC GROUNDING: A raw sense activation that arrives at this node's
    axis bucket is BASE until an LSA path also fires at this coordinate.
    That LSA firing IS the semantic grounding — it connects the raw signal
    to Aurora's meaning space. Without it, the node stays BASE no matter
    how many times the sense fires. This is why sensory interpretation
    requires semantics: signal without interpretation is not yet a concept.

    CURRENT OVERLAY: Records how the specific instance being observed RIGHT
    NOW differs from the accumulated archetype. Cleared each turn. This is
    "this particular tree" vs "trees in general as Aurora knows them."

    NOTE: New code should use DPS Crystal objects (returned by ConceptCrystalRegistry).
    This class is retained for backward compatibility with code that imports it.
    """
    node_id:         str
    stage:           str      # base | composite | higher_order | quasi

    # How many times this node has promoted (0 at creation)
    generation:      int

    # Axis fingerprint — the semantic coordinate of this concept
    axis_bucket:     Tuple[float, ...]   # (X, T, N, B, A) rounded to 0.1

    # Raw sense channels that have activated at this axis coordinate
    # Key: SensoryDim value string. Value: list of node refs from that sense system.
    dim_links:       Dict[str, List[str]]

    # LSA path keys that have fired at this axis coordinate
    # This IS the semantic grounding record — each entry represents one
    # moment where a sense signal connected to Aurora's meaning space.
    lsa_keys:        List[str]

    # Whether at least one LSA path has fired at this coordinate.
    # This is the gate for composite promotion: raw sense + semantic = meaning.
    is_grounded:     bool

    # Accumulated SediMemory resonance — how much memory connects through
    # the semantic plane at this axis coordinate
    sedi_resonance:  float

    # Number of cross-sense co-activations (drives promotion)
    cross_hits:      int

    # Which sense dimensions have activated at least once
    active_dims:     Set[str]

    # Optional classification of cognitive function (emerges from pattern,
    # set externally when evidence is clear — never assumed)
    function_class:  Optional[str]

    # What's specific about what she's observing RIGHT NOW vs. the archetype.
    # Cleared at turn start. "This tree" vs "trees."
    current_overlay: Dict[str, Any]

    # Timestamps
    first_seen:      float
    last_seen:       float

    # ── Observation API ───────────────────────────────────────────────────

    def observe(
        self,
        dim:      str,           # SensoryDim value
        node_ref: str,
        overlay:  Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a raw sense activation at this axis coordinate.
        Returns True if this triggered a promotion.

        Note: this alone cannot promote to composite. Semantic grounding
        (observe_lsa) must also occur — signal without interpretation stays BASE.
        """
        self.last_seen = time.time()
        self.dim_links.setdefault(dim, [])
        if node_ref not in self.dim_links[dim]:
            self.dim_links[dim].append(node_ref)
        self.active_dims.add(dim)
        if len(self.active_dims) >= 2:
            self.cross_hits += 1
        if overlay:
            self.current_overlay.update(overlay)
        return self._try_promote()

    def observe_lsa(self, path_key: str) -> bool:
        """
        Record semantic grounding — an LSA path fired at this axis coordinate.

        This is not just "semantic sense data." This is the moment raw sense
        signal connects to Aurora's constraint-physics meaning space. Once
        grounded, composite promotion becomes possible.

        Also counts as a cross-sense hit because LSA activation at a sensory
        coordinate IS co-activation of language-meaning with that sense.
        """
        self.last_seen = time.time()
        if path_key not in self.lsa_keys:
            self.lsa_keys.append(path_key)
        self.is_grounded = True
        # LSA co-activation with a sense = cross-hit (meaning met signal)
        if self.active_dims:
            self.cross_hits += 1
        return self._try_promote()

    def observe_sedi(self, delta: float) -> bool:
        """
        Accumulate SediMemory resonance — memory connecting through the
        semantic plane at this axis coordinate.
        Returns True on quasi promotion.
        """
        self.sedi_resonance = min(50.0, self.sedi_resonance + delta)
        return self._try_promote()

    def clear_overlay(self) -> None:
        """Called at turn start — clears the specific-instance overlay."""
        self.current_overlay = {}

    # ── Promotion ─────────────────────────────────────────────────────────

    def _try_promote(self) -> bool:
        """
        Try to advance to the next stage. Returns True if promotion occurred.

        Key gate: composite requires semantic grounding (is_grounded=True).
        A raw sense can fire 1000 times — without LSA grounding it stays BASE.
        This enforces: sensory interpretation requires semantics.
        """
        n_dims = len(self.active_dims)
        hits   = self.cross_hits
        sedi   = self.sedi_resonance
        next_s = None

        if self.stage == "base":
            # Composite gate: semantic grounding required + 2+ dimensions + 3+ hits
            if (self.is_grounded
                    and n_dims >= _DIMS_REQUIRED["composite"]
                    and hits  >= _HITS_THRESHOLD["composite"]):
                next_s = "composite"

        elif self.stage == "composite":
            # Higher-order gate: 3+ dimensions, 12+ hits (grounding already met)
            if n_dims >= _DIMS_REQUIRED["higher_order"] and hits >= _HITS_THRESHOLD["higher_order"]:
                next_s = "higher_order"

        elif self.stage == "higher_order":
            # Quasi gate: 4+ dimensions, 40+ hits, 5+ sedi resonance
            if (n_dims >= _DIMS_REQUIRED["quasi"]
                    and hits >= _HITS_THRESHOLD["quasi"]
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
            "is_grounded":    self.is_grounded,
            "cross_hits":     self.cross_hits,
            "active_dims":    sorted(self.active_dims),
            "n_lsa_keys":     len(self.lsa_keys),
            "sedi_resonance": round(self.sedi_resonance, 3),
            "axis_bucket":    list(self.axis_bucket),
            "function_class": self.function_class,
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
            "is_grounded":    self.is_grounded,
            "sedi_resonance": self.sedi_resonance,
            "cross_hits":     self.cross_hits,
            "active_dims":    sorted(self.active_dims),
            "function_class": self.function_class,
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
            is_grounded    = d.get("is_grounded", False),
            sedi_resonance = d["sedi_resonance"],
            cross_hits     = d["cross_hits"],
            active_dims    = set(d["active_dims"]),
            function_class = d.get("function_class"),
            current_overlay= {},
            first_seen     = d["first_seen"],
            last_seen      = d["last_seen"],
        )


# ---------------------------------------------------------------------------
# ConceptCrystalRegistry — axis-space proximity index backed by DPS Crystal
# ---------------------------------------------------------------------------

class ConceptCrystalRegistry:
    """
    The full population of DPS Crystal objects, indexed by axis_bucket.

    Lookup: given a current axis state, find the nearest existing crystal
    (within 0.20 Euclidean distance in axis space) or create a new base
    DPS Crystal for this semantic coordinate.

    The registry does not know concept names. It knows axis-state regions
    and which senses have co-activated there, whether semantic grounding
    has occurred, and how much memory resonance has accumulated.

    When _DPS_AVAILABLE is True, _nodes stores DPS Crystal objects and
    all physics are routed through DPS CrystalFacet physics points.
    When _DPS_AVAILABLE is False (import error), falls back to the legacy
    ConceptCrystalNode objects for graceful degradation.
    """

    BUCKET_RESOLUTION: float = 0.10
    PROXIMITY_RADIUS:  float = 0.20
    MAX_NODES:         int   = 3000
    CULL_FRACTION:     float = 0.08

    def __init__(self) -> None:
        self._nodes:     Dict[str, Any]               = {}  # DPS Crystal or ConceptCrystalNode
        self._ax_index:  Dict[tuple, str]             = {}
        self._promo_log: List[Dict[str, Any]]         = []

    # ── Axis bucket helpers ───────────────────────────────────────────────

    @staticmethod
    def _to_bucket(ax: Dict[str, float]) -> Tuple[float, ...]:
        r = ConceptCrystalRegistry.BUCKET_RESOLUTION
        return tuple(round(ax.get(k, 0.5) / r) * r for k in ("X", "T", "N", "B", "A"))

    def _nearest(self, target_or_ax: Any) -> Optional[str]:
        # Accept either a pre-computed bucket tuple or an ax dict
        if isinstance(target_or_ax, dict):
            target = self._to_bucket(target_or_ax)
        else:
            target = target_or_ax
        best_d  = float("inf")
        best_id: Optional[str] = None
        for bkt, nid in self._ax_index.items():
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, bkt)))
            if d < best_d:
                best_d  = d
                best_id = nid
        return best_id if best_d <= self.PROXIMITY_RADIUS else None

    def _get_or_create(self, ax: Dict[str, float]) -> Any:
        nid = self._nearest(ax)
        if nid is not None:
            return self._nodes[nid]
        if len(self._nodes) >= self.MAX_NODES:
            self._cull()
        bkt = self._to_bucket(ax)
        if _DPS_AVAILABLE:
            ax_keys = ("X", "T", "N", "B", "A")
            crystal = _DPSCrystal(
                crystal_id=_uuid_mod.uuid4().hex[:12],
                concept="axbkt:" + "_".join(str(v) for v in bkt),
                constraint_signature={k: v for k, v in zip(ax_keys, bkt)},
            )
            crystal._unlock_failpoints()
            nid = crystal.crystal_id
            self._nodes[nid]    = crystal
            self._ax_index[bkt] = nid
            return crystal
        else:
            # Fallback: legacy ConceptCrystalNode
            nid  = str(_uuid_mod.uuid4())[:12]
            node = ConceptCrystalNode(
                node_id        = nid,
                stage          = "base",
                generation     = 0,
                axis_bucket    = bkt,
                dim_links      = {},
                lsa_keys       = [],
                is_grounded    = False,
                sedi_resonance = 0.0,
                cross_hits     = 0,
                active_dims    = set(),
                function_class = None,
                current_overlay= {},
                first_seen     = time.time(),
                last_seen      = time.time(),
            )
            self._nodes[nid]    = node
            self._ax_index[bkt] = nid
            return node

    def _cull(self) -> None:
        if _DPS_AVAILABLE:
            # Cull by usage_count (least used first)
            items = sorted(self._nodes.values(), key=lambda c: getattr(c, 'usage_count', 0))
        else:
            items = sorted(self._nodes.values(), key=lambda n: n.last_seen)
        cut = max(1, int(len(items) * self.CULL_FRACTION))
        for item in items[:cut]:
            nid = getattr(item, 'crystal_id', None) or getattr(item, 'node_id', None)
            if nid:
                self._nodes.pop(nid, None)
            if _DPS_AVAILABLE:
                bkt_str = getattr(item, 'constraint_signature', None)
                if bkt_str:
                    bkt = tuple(bkt_str.get(k, 0.5) for k in ("X", "T", "N", "B", "A"))
                    self._ax_index.pop(bkt, None)
            else:
                self._ax_index.pop(getattr(item, 'axis_bucket', None), None)

    # ── Public observation API ────────────────────────────────────────────

    def observe_lsa(self, ax: Dict[str, float], path_key: str) -> Any:
        """
        Record semantic grounding — an LSA path fired at this axis coordinate.
        Maps to DPS Crystal with physics point: coherence (semantic grounding),
        resonance (memory connection), potential (growth capacity).
        Returns the DPS Crystal (or legacy node) that received the observation.
        """
        if not _DPS_AVAILABLE:
            # Legacy path
            node = self._get_or_create(ax)
            promoted = node.observe_lsa(path_key)
            if promoted:
                self._log_promotion(node)
            return node

        crystal = self._get_or_create(ax)
        role = f"lsa:{path_key[:30]}"
        existing = next((f for f in crystal.facets.values() if f.role == role), None)
        if existing:
            existing.strengthen()
            existing.coherence = min(1.0, existing.coherence + 0.05)
        else:
            fid = f"{crystal.crystal_id}_f{len(crystal.facets)}"
            f = _DPSCrystalFacet(facet_id=fid, role=role, content=path_key, confidence=0.85)
            f.coherence  = 0.90   # grounded = semantically coherent
            f.resonance  = 0.75   # connected to memory plane
            f.potential  = 0.60   # semantic paths = growth potential
            f.frequency  = min(1.0, crystal.usage_count / 40.0)
            crystal.facets[fid] = f
        crystal.use()
        try:
            crystal.evolve()
        except Exception:
            pass
        promoted = crystal.level.value > 1 if _DPS_AVAILABLE else False
        if promoted:
            self._log_promotion(crystal)
        return crystal

    def observe_sedi(self, ax: Dict[str, float], delta: float = 0.05) -> None:
        """
        Accumulate SediMemory resonance at this axis coordinate.
        Strengthens the resonance physics point on the DPS Crystal.
        Memory deepening at the semantic plane — only strengthens existing nodes.
        Does NOT create new nodes.
        """
        nid = self._nearest(ax)
        if nid is None:
            return
        crystal = self._nodes[nid]
        if not _DPS_AVAILABLE:
            promoted = crystal.observe_sedi(delta)
            if promoted:
                self._log_promotion(crystal)
            return
        # DPS path: strengthen/create sedi_resonance facet
        sedi_facet = next((f for f in crystal.facets.values() if f.role == "sedi_resonance"), None)
        if sedi_facet:
            sedi_facet.resonance = min(1.0, sedi_facet.resonance + delta)
            sedi_facet.strengthen(delta)
        else:
            fid = f"{crystal.crystal_id}_f{len(crystal.facets)}"
            f = _DPSCrystalFacet(facet_id=fid, role="sedi_resonance",
                                  content="memory_resonance", confidence=0.60)
            f.resonance = min(1.0, delta * 5.0)  # scale small delta up
            f.stability = 0.80   # memory is stable
            crystal.facets[fid] = f
        crystal.use()

    def observe_sensory(
        self,
        ax:       Dict[str, float],
        dim:      str,                      # SensoryDim value string
        node_ref: str,
        overlay:  Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Record a raw sense activation (visual, audio, proprioceptive, self_obs)
        at this axis coordinate.
        Maps sensory dims to complexity/frequency physics points.
        Returns the DPS Crystal (or legacy node) that received it.
        """
        if not _DPS_AVAILABLE:
            node     = self._get_or_create(ax)
            promoted = node.observe(dim, node_ref, overlay)
            if promoted:
                self._log_promotion(node)
            return node

        crystal = self._get_or_create(ax)
        role = f"sensory:{dim}"
        existing = next((f for f in crystal.facets.values() if f.role == role), None)
        if existing:
            existing.strengthen()
            existing.frequency = min(1.0, existing.frequency + 0.05)
        else:
            fid = f"{crystal.crystal_id}_f{len(crystal.facets)}"
            f = _DPSCrystalFacet(facet_id=fid, role=role,
                                  content=str(node_ref)[:40], confidence=0.70)
            f.sensitivity = 0.75   # sensory input = sensitive
            f.frequency   = 0.20   # starts low, grows with each observation
            crystal.facets[fid] = f
        # Update complexity based on sensory dimension count
        n_sensory_dims = sum(1 for f in crystal.facets.values() if f.role.startswith("sensory:"))
        for f in crystal.facets.values():
            f.complexity = min(1.0, n_sensory_dims / 4.0)
        crystal.use()
        try:
            crystal.evolve()
        except Exception:
            pass
        return crystal

    def clear_turn_overlays(self) -> None:
        """
        Called at turn start. DPS Crystal has no current_overlay concept;
        this is a no-op for DPS Crystal objects.
        For legacy nodes, clears specific-instance overlays.
        """
        if not _DPS_AVAILABLE:
            for n in self._nodes.values():
                if hasattr(n, 'clear_overlay'):
                    n.clear_overlay()

    def set_function_class(self, ax: Dict[str, float], func: str) -> None:
        """
        Mark the concept crystal at this axis coordinate with a cognitive
        function classification. Only called when evidence is clear.
        """
        nid = self._nearest(ax)
        if nid is not None:
            node = self._nodes[nid]
            if hasattr(node, 'function_class'):
                node.function_class = func

    # ── Query API ─────────────────────────────────────────────────────────

    def query(self, ax: Dict[str, float]) -> Optional[Any]:
        """Return nearest DPS Crystal (or legacy node) at this axis coordinate."""
        nid = self._nearest(ax)
        return self._nodes.get(nid) if nid else None

    def query_grounded(self, ax: Dict[str, float]) -> Optional[Any]:
        """Return nearest crystal only if it has semantic grounding (lsa: facets)."""
        crystal = self.query(ax)
        if crystal is None:
            return None
        if _DPS_AVAILABLE and hasattr(crystal, 'facets'):
            is_grounded = any(f.role.startswith("lsa:") for f in crystal.facets.values())
            return crystal if is_grounded else None
        # Legacy path
        return crystal if (hasattr(crystal, 'is_grounded') and crystal.is_grounded) else None

    def query_composite_or_higher(self, ax: Dict[str, float]) -> Optional[Any]:
        """Return nearest crystal only if it is at COMPOSITE level or above."""
        crystal = self.query(ax)
        if crystal is None:
            return None
        if _DPS_AVAILABLE and hasattr(crystal, 'level'):
            return crystal if crystal.level.value >= 2 else None
        # Legacy path
        if hasattr(crystal, 'stage'):
            return crystal if crystal.stage in ("composite", "higher_order", "quasi") else None
        return None

    def promoted_nodes(self) -> List[Any]:
        """Return all crystals that have advanced beyond BASE."""
        if _DPS_AVAILABLE:
            return [c for c in self._nodes.values()
                    if hasattr(c, 'level') and c.level.value > 1]
        return [n for n in self._nodes.values()
                if hasattr(n, 'stage') and n.stage != "base"]

    def nodes_by_stage(self, stage: str) -> List[Any]:
        """Return all crystals at the given stage name."""
        # Map old stage names to DPS level values
        _stage_to_level = {"base": 1, "composite": 2, "higher_order": 3, "quasi": 4}
        if _DPS_AVAILABLE:
            lvl = _stage_to_level.get(stage, 1)
            return [c for c in self._nodes.values()
                    if hasattr(c, 'level') and c.level.value == lvl]
        return [n for n in self._nodes.values()
                if hasattr(n, 'stage') and n.stage == stage]

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {"base": 0, "composite": 0, "higher_order": 0, "quasi": 0}
        grounded = 0
        _level_to_stage = {1: "base", 2: "composite", 3: "higher_order", 4: "quasi"}
        for crystal in self._nodes.values():
            if _DPS_AVAILABLE and hasattr(crystal, 'level'):
                lvl   = crystal.level.value  # 1=BASE,2=COMPOSITE,3=FULL_CONCEPT,4=QUASI
                stage = _level_to_stage.get(min(lvl, 4), "quasi")
                counts[stage] = counts.get(stage, 0) + 1
                if any(f.role.startswith("lsa:") for f in crystal.facets.values()):
                    grounded += 1
            else:
                stage = getattr(crystal, 'stage', 'base')
                counts[stage] = counts.get(stage, 0) + 1
                if getattr(crystal, 'is_grounded', False):
                    grounded += 1
        return {
            "total":        len(self._nodes),
            "grounded":     grounded,
            "ungrounded":   len(self._nodes) - grounded,
            "by_stage":     counts,
            "promo_events": len(self._promo_log),
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, state_dir: str) -> None:
        path = os.path.join(state_dir, "concept_crystals.json.gz")
        try:
            data: Dict[str, Any] = {
                "nodes":    [],
                "ax_index": {str(k): v for k, v in self._ax_index.items()},
            }
            for crystal in self._nodes.values():
                if _DPS_AVAILABLE and hasattr(crystal, 'to_dict'):
                    data["nodes"].append(crystal.to_dict())
                elif hasattr(crystal, 'to_dict'):
                    data["nodes"].append(crystal.to_dict())
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
                if _DPS_AVAILABLE:
                    try:
                        crystal = _DPSCrystal.from_dict(nd)
                        self._nodes[crystal.crystal_id] = crystal
                    except Exception:
                        # Try legacy node format
                        try:
                            node = ConceptCrystalNode.from_dict(nd)
                            self._nodes[node.node_id] = node
                        except Exception:
                            pass
                else:
                    try:
                        node = ConceptCrystalNode.from_dict(nd)
                        self._nodes[node.node_id]        = node
                        self._ax_index[node.axis_bucket] = node.node_id
                    except Exception:
                        pass
            # Rebuild ax_index from saved string keys
            for k_str, nid in data.get("ax_index", {}).items():
                try:
                    bkt = tuple(float(v) for v in k_str.strip("()").split(", "))
                    if nid in self._nodes:
                        self._ax_index[bkt] = nid
                except Exception:
                    pass
        except Exception:
            pass

    def _log_promotion(self, crystal: Any) -> None:
        if _DPS_AVAILABLE and hasattr(crystal, 'crystal_id'):
            self._promo_log.append({
                "crystal_id": getattr(crystal, 'crystal_id', ''),
                "concept":    getattr(crystal, 'concept', ''),
                "level":      getattr(crystal.level, 'name', 'BASE') if hasattr(crystal, 'level') else 'unknown',
                "ts":         time.time(),
            })
        else:
            # Legacy node
            self._promo_log.append({
                "node_id":      getattr(crystal, 'node_id', ''),
                "stage":        getattr(crystal, 'stage', ''),
                "generation":   getattr(crystal, 'generation', 0),
                "cross_hits":   getattr(crystal, 'cross_hits', 0),
                "n_dims":       len(getattr(crystal, 'active_dims', set())),
                "active_dims":  sorted(getattr(crystal, 'active_dims', set())),
                "is_grounded":  getattr(crystal, 'is_grounded', False),
                "function_class": getattr(crystal, 'function_class', None),
                "ts":           time.time(),
            })

    def drain_promotions(self, since_ts: float = 0.0) -> List[Dict[str, Any]]:
        """
        Return all promotion events logged after since_ts. Non-destructive —
        the caller tracks the cursor; the log itself is kept for persistence.
        """
        return [p for p in self._promo_log if p.get("ts", 0.0) > since_ts]
