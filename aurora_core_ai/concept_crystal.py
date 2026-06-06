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
from __future__ import annotations

import gzip
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


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
# ConceptCrystalNode
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
# ConceptCrystalRegistry
# ---------------------------------------------------------------------------

class ConceptCrystalRegistry:
    """
    The full population of ConceptCrystalNodes, indexed by axis_bucket.

    Lookup: given a current axis state, find the nearest existing crystal
    (within 0.20 Euclidean distance in axis space) or create a new base
    node for this semantic coordinate.

    The registry does not know concept names. It knows axis-state regions
    and which senses have co-activated there, whether semantic grounding
    has occurred, and how much memory resonance has accumulated.

    From the outside, a crystal at axis-bucket (0.3, 0.7, 0.4, 0.6, 0.8)
    is just that — a stable cognitive structure at those coordinates.
    Whether that corresponds to "tree" or "trust" or "fatigue" is known
    only by what senses activate there and what language path fires there.
    """

    BUCKET_RESOLUTION: float = 0.10
    PROXIMITY_RADIUS:  float = 0.20
    MAX_NODES:         int   = 3000
    CULL_FRACTION:     float = 0.08

    def __init__(self) -> None:
        self._nodes:     Dict[str, ConceptCrystalNode] = {}
        self._ax_index:  Dict[tuple, str]               = {}
        self._promo_log: List[Dict[str, Any]]           = []

    # ── Axis bucket helpers ───────────────────────────────────────────────

    @staticmethod
    def _to_bucket(ax: Dict[str, float]) -> Tuple[float, ...]:
        r = ConceptCrystalRegistry.BUCKET_RESOLUTION
        return tuple(round(ax.get(k, 0.5) / r) * r for k in ("X", "T", "N", "B", "A"))

    def _nearest(self, ax: Dict[str, float]) -> Optional[str]:
        target  = self._to_bucket(ax)
        best_d  = float("inf")
        best_id: Optional[str] = None
        for bkt, nid in self._ax_index.items():
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, bkt)))
            if d < best_d:
                best_d  = d
                best_id = nid
        return best_id if best_d <= self.PROXIMITY_RADIUS else None

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
        by_age = sorted(self._nodes.values(), key=lambda n: n.last_seen)
        cut    = max(1, int(len(by_age) * self.CULL_FRACTION))
        for n in by_age[:cut]:
            self._nodes.pop(n.node_id, None)
            self._ax_index.pop(n.axis_bucket, None)

    # ── Public observation API ────────────────────────────────────────────

    def observe_sensory(
        self,
        ax:       Dict[str, float],
        dim:      str,                      # SensoryDim value string
        node_ref: str,
        overlay:  Optional[Dict[str, Any]] = None,
    ) -> ConceptCrystalNode:
        """
        Record a raw sense activation (visual, audio, proprioceptive, self_obs)
        at this axis coordinate. Returns the concept node that received it.

        This can build cross-sense relationships but CANNOT promote to composite
        without semantic grounding (observe_lsa). Signal requires interpretation.
        """
        node     = self._get_or_create(ax)
        promoted = node.observe(dim, node_ref, overlay)
        if promoted:
            self._log_promotion(node)
        return node

    def observe_lsa(self, ax: Dict[str, float], path_key: str) -> ConceptCrystalNode:
        """
        Record semantic grounding — an LSA path fired at this axis coordinate.

        This is the connective event between raw sense data and meaning.
        Without this, a sensory node stays BASE regardless of how often it fires.
        With this, composite promotion becomes possible — sense + interpretation.

        Also marks the axis coordinate as semantically active in SediMemory's
        language: after this, memory deposits at this coordinate will resonate
        with this concept crystal.
        """
        node     = self._get_or_create(ax)
        promoted = node.observe_lsa(path_key)
        if promoted:
            self._log_promotion(node)
        return node

    def observe_sedi(self, ax: Dict[str, float], delta: float = 0.05) -> None:
        """
        Accumulate SediMemory resonance at this axis coordinate.
        Memory deepening at the semantic plane — only strengthens existing nodes.
        Does NOT create new nodes (memory doesn't create concepts, it deepens them).
        """
        nid = self._nearest(ax)
        if nid is not None:
            node     = self._nodes[nid]
            promoted = node.observe_sedi(delta)
            if promoted:
                self._log_promotion(node)

    def clear_turn_overlays(self) -> None:
        """Called at turn start — clears all specific-instance overlays."""
        for n in self._nodes.values():
            n.clear_overlay()

    def set_function_class(self, ax: Dict[str, float], func: str) -> None:
        """
        Mark the concept crystal at this axis coordinate with a cognitive
        function classification. Only called when evidence is clear —
        never assumed, never assigned top-down.
        """
        nid = self._nearest(ax)
        if nid is not None:
            self._nodes[nid].function_class = func

    # ── Query API ─────────────────────────────────────────────────────────

    def query(self, ax: Dict[str, float]) -> Optional[ConceptCrystalNode]:
        nid = self._nearest(ax)
        return self._nodes.get(nid) if nid else None

    def query_grounded(self, ax: Dict[str, float]) -> Optional[ConceptCrystalNode]:
        """Return nearest crystal only if it has semantic grounding."""
        node = self.query(ax)
        return node if (node and node.is_grounded) else None

    def query_composite_or_higher(self, ax: Dict[str, float]) -> Optional[ConceptCrystalNode]:
        node = self.query(ax)
        return node if (node and node.stage in ("composite", "higher_order", "quasi")) else None

    def promoted_nodes(self) -> List[ConceptCrystalNode]:
        return [n for n in self._nodes.values() if n.stage != "base"]

    def nodes_by_stage(self, stage: str) -> List[ConceptCrystalNode]:
        return [n for n in self._nodes.values() if n.stage == stage]

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {s: 0 for s in ("base", "composite", "higher_order", "quasi")}
        grounded = 0
        for n in self._nodes.values():
            counts[n.stage] = counts.get(n.stage, 0) + 1
            if n.is_grounded:
                grounded += 1
        return {
            "total":         len(self._nodes),
            "grounded":      grounded,
            "ungrounded":    len(self._nodes) - grounded,
            "by_stage":      counts,
            "promo_events":  len(self._promo_log),
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, state_dir: str) -> None:
        path = os.path.join(state_dir, "concept_crystals.json.gz")
        try:
            data = {
                "nodes":     [n.to_dict() for n in self._nodes.values()],
                "promo_log": self._promo_log[-500:],
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
                self._nodes[node.node_id]        = node
                self._ax_index[node.axis_bucket] = node.node_id
            self._promo_log = data.get("promo_log", [])
        except Exception:
            pass

    def _log_promotion(self, node: ConceptCrystalNode) -> None:
        self._promo_log.append({
            "node_id":      node.node_id,
            "stage":        node.stage,
            "generation":   node.generation,
            "cross_hits":   node.cross_hits,
            "n_dims":       len(node.active_dims),
            "active_dims":  sorted(node.active_dims),
            "is_grounded":  node.is_grounded,
            "function_class": node.function_class,
            "ts":           time.time(),
        })

    def drain_promotions(self, since_ts: float = 0.0) -> List[Dict[str, Any]]:
        """
        Return all promotion events logged after since_ts. Non-destructive —
        the caller tracks the cursor; the log itself is kept for persistence.
        """
        return [p for p in self._promo_log if p.get("ts", 0.0) > since_ts]
