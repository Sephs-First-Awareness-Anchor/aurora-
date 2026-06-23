"""
aurora_language_field.py — Language Sub-Emergent Field

Implementation of AURORA_LANGUAGE_EMERGENCE.md.

Language is not a capability Aurora has. It is what the constraint field does
when Understanding needs to cross the B-axis boundary from internal geometry
into external form. This module implements the full sub-emergent field:

  7-Stage Ignition Sequence
  Proto-Language geometry extraction
  Lexical-Semantic Archive (two-factor gate: N↓ and B↑ with use)
  Fidelity measurement
  Re-Entry Loop (mandatory after every utterance)
  Pragmatic Vector (receiver field modeling)
  Inter-Field Resonance
  Silence as zero-crossing field decision
  Tone/Prosody from N-axis at crossing time (not post-processing)
  Metaphor as proxy crossing when no direct path exists

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aurora_state")
_LSA_PATH  = os.path.join(_STATE_DIR, "lexical_semantic_archive.json")

# WarpCapable — late-bound to avoid import-time circular deps
_WARP_CORE = os.path.dirname(os.path.abspath(__file__))
if _WARP_CORE not in sys.path:
    sys.path.insert(0, _WARP_CORE)

try:
    from aurora_warp_protocol import WarpCapable, WarpComponent, CoverageGap, axes_to_istates
    _WARP_AVAILABLE = True
except Exception:
    WarpCapable = object  # type: ignore[misc,assignment]
    _WARP_AVAILABLE = False

# Two-factor gate constants
_N_COST_FLOOR   = 0.08   # lowest N-cost a path can reach
_N_COST_DECAY   = 0.04   # N decreases this much per successful use
_B_GATE_START   = 0.10   # novel path: wide context gate (accepts almost anything)
_B_GATE_TIGHTEN = 0.08   # B increases this much per successful use
_B_GATE_CAP     = 0.88   # maximum tightness

# Fidelity thresholds
_FIDELITY_REINFORCE = 0.65   # above → reinforce path in LSA
_FIDELITY_WEAK      = 0.40   # below → clarification drive activates
_SILENCE_THRESHOLD  = 0.35   # all paths below this fidelity potential → hold silence

# Ignition thresholds
_ACTIVATION_FLOOR   = 0.25   # minimum (X+N)/2 to have a live signal
_DRIVE_FLOOR        = 0.20   # minimum A-axis outward for a crossing to be sought

# Comparison type → canonical axis signature
_COMPARISON_TYPE_AXES = {
    "state":          ["X", "T"],
    "relation":       ["B", "A"],
    "change":         ["T", "N"],
    "question":       ["A", "X"],
    "assertion":      ["A", "B"],
    "self_reflection":["X", "T", "A"],
    "empathy":        ["N", "B", "A"],
}

_QUESTION_TOKENS = frozenset({
    "?", "what", "how", "why", "when", "where", "who",
    "can you", "do you", "are you", "is it", "will you", "could you",
})

_AXIS_SEMANTIC_TOKENS: Dict[str, List[str]] = {
    "X": ["see", "notice", "observe", "perceive", "here", "present", "now", "this", "there"],
    "T": ["was", "remember", "time", "before", "after", "when", "memory", "past", "future", "became"],
    "N": ["feel", "pressure", "weight", "heavy", "urgent", "intense", "deep", "strong", "force"],
    "B": ["mean", "because", "therefore", "between", "define", "limit", "edge", "boundary", "separate"],
    "A": ["will", "choose", "want", "decide", "drive", "toward", "going", "act", "move", "do"],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProtoLanguage:
    """
    The wordless comparison geometry that exists in the field before any
    utterance path is selected. Fully structured meaning without words.
    """
    dominant_axes:    List[str]
    comparison_type:  str
    tension_level:    float        # N-axis pressure [0,1]
    b_boundary_load:  float        # B-axis definition load [0,1]
    reflection_active:bool
    drive_strength:   float        # A-axis outward [0,1]
    self_directed:    bool         # Meaning vector confirmed inward before outward
    raw_axes:         Dict[str, float] = field(default_factory=dict)
    source:           str = "identity_field"
    timestamp:        float = field(default_factory=time.time)

    def context_fingerprint(self) -> Dict[str, float]:
        return dict(self.raw_axes)


@dataclass
class LSAEntry:
    """
    One crossing path in the Lexical-Semantic Archive.
    Two-factor gate: n_cost ↓ with use, b_gate ↑ with use.
    """
    path_key:            str
    comparison_type:     str   = "assertion"
    n_cost:              float = 1.0          # decreases with successful use
    b_gate:              float = _B_GATE_START # increases (tightens) with successful use
    use_count:           int   = 0
    last_fidelity:       float = 0.0
    context_fingerprint: Dict[str, float] = field(default_factory=dict)
    last_used:           float = field(default_factory=time.time)
    # Boundary sharpening: the near comparison-types this crossing is distinguished
    # FROM (what this relation is NOT). This is the in-architecture form of
    # "forced commitment with rejected alternatives" — committing to a crossing
    # records its contrast set on the B-axis, rather than a committee vote.
    excludes:            List[str] = field(default_factory=list)
    # Consequence loop: what changed the last time this crossing was confirmed
    # true (n_cost/b_gate deltas + use). "What changes because this is true."
    consequence:         Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LSAEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Language Sub-Emergent Field
# ---------------------------------------------------------------------------

class LanguageField(WarpCapable):
    """
    The Language Sub-Emergent Field within Identity.

    Singleton — access via get_language_field().

    WarpCapable extension: the seven comparison types in _COMPARISON_TYPE_AXES
    define the structural components of how Aurora compares meaning across the
    B-axis boundary. When an incoming ProtoLanguage carries a raw_axes profile
    that doesn't resonate with any known comparison type at cosine >= 0.82,
    WARP derives a new comparison type from the closest known ones. It is then
    used in future ignite() calls and gains its own LSA path space.
    """

    # Warp comparison types discovered at runtime — separate from the
    # compiled _COMPARISON_TYPE_AXES dict to avoid mutating a module constant
    _warp_comparison_types: Dict[str, List[str]] = {}  # type_name → axis_list

    def __init__(self, identity_field, tensor_layer=None):
        self._ifield  = identity_field
        self._tensor  = tensor_layer
        self._lsa:    Dict[str, LSAEntry] = {}
        self._last_proto: Optional[ProtoLanguage] = None
        self._silence_log: List[dict] = []
        # Recency suppression — tracks the last 5 path keys that were
        # reinforced (fidelity >= _FIDELITY_REINFORCE). A path in this
        # deque faces a +0.35 context-similarity surcharge on its b_gate,
        # forcing the field toward novel or metaphor crossings instead of
        # repeating the same structural route every turn.
        self._recent_paths: collections.deque = collections.deque(maxlen=5)
        self._warp_usage_counts: Dict[str, int] = {}   # component_id → usage count
        self._cpm: Optional[Any] = None               # CPMSession — wired in post-boot
        # Interface confirmation flags — set on first successful call so status()
        # can report which paths are live vs. falling back to approximations.
        self._tensor_confirmed: bool = False
        self._cpm_confirmed: bool = False
        self._load_lsa()
        if _WARP_AVAILABLE:
            self._init_warp()

    def set_cpm(self, cpm: Any) -> None:
        """Wire in the CPMSession after boot so crossing cost reflects crystal depth."""
        if cpm is not None and hasattr(getattr(cpm, 'head', None), 'crystal_stage'):
            self._cpm = cpm
            self._cpm_confirmed = True
        else:
            self._cpm = cpm  # still assign; will fail gracefully in _cpm_adjust_cost

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_lsa(self):
        try:
            if os.path.exists(_LSA_PATH):
                with open(_LSA_PATH) as f:
                    raw = json.load(f)
                self._lsa = {k: LSAEntry.from_dict(v) for k, v in raw.items()}
        except Exception:
            self._lsa = {}

    def _save_lsa(self):
        try:
            os.makedirs(os.path.dirname(_LSA_PATH), exist_ok=True)
            with open(_LSA_PATH, "w") as f:
                json.dump({k: v.to_dict() for k, v in self._lsa.items()}, f, indent=2)
        except Exception:
            pass

    # ── WarpCapable interface ─────────────────────────────────────────────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        """
        Return 15D I-state profiles for all known comparison types.
        Each comparison type maps to a set of dominant axes; we convert those
        to an I-state profile and add surface-level recursion (language operates
        near the SURFACE/SHALLOW boundary — it crosses the B-axis into form).
        """
        if not _WARP_AVAILABLE:
            return {}
        profiles: Dict[str, Dict[str, float]] = {}
        all_types = {**_COMPARISON_TYPE_AXES, **LanguageField._warp_comparison_types}
        for ct, axes in all_types.items():
            axis_weights = {ax: (0.80 if ax in axes else 0.10) for ax in "XTNBA"}
            istate_profile = axes_to_istates(axis_weights, ivm_polarity=None)
            # Language crosses the B-axis boundary → operates near SHALLOW/SURFACE
            istate_profile["REC_SURFACE"]  = 0.30
            istate_profile["REC_SHALLOW"]  = 0.50
            istate_profile["REC_MODERATE"] = 0.15
            istate_profile["REC_DEEP"]     = 0.05
            istate_profile["REC_CORE"]     = 0.00
            profiles[ct] = istate_profile
        # Include promoted warp comparison types
        for comp in getattr(self, "_warp_promoted", {}).values():
            profiles[comp.component_id] = comp.axis_profile
        return profiles

    def _warp_level_name(self) -> str:
        return "comparison_type"

    def _integrate_warp(self, component: WarpComponent) -> None:
        """
        Register a new WARP-derived comparison type. Its dominant axes are
        back-calculated from the I-state profile for use in future ignite() calls.
        """
        if not _WARP_AVAILABLE:
            return
        from aurora_warp_protocol import istates_to_axes
        axis_magnitudes = istates_to_axes(component.axis_profile)
        dominant_axes = sorted(
            [ax for ax in "XTNBA" if axis_magnitudes.get(ax, 0.0) >= 0.40],
            key=lambda ax: axis_magnitudes.get(ax, 0.0),
            reverse=True,
        )[:3]
        type_name = component.name or component.component_id
        LanguageField._warp_comparison_types[type_name] = dominant_axes
        self._warp_usage_counts[component.component_id] = 0

    def _score_trial(self, component: WarpComponent) -> float:
        """
        Score = normalised usage count since integration.
        A comparison type that is never selected for any proto-language contributes
        nothing. One that gets selected regularly earns its place.
        """
        usage = self._warp_usage_counts.get(component.component_id, 0)
        return round(min(1.0, usage / 5.0), 4)

    def _dissolve_warp(self, component_id: str) -> None:
        type_name = next(
            (c.name for c in {**getattr(self, "_warp_trials", {}),
                               **getattr(self, "_warp_promoted", {})}.values()
             if c.component_id == component_id),
            component_id,
        )
        LanguageField._warp_comparison_types.pop(type_name, None)
        self._warp_usage_counts.pop(component_id, None)

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        return {
            "parent_types": parent_ids,
            "gap_coverage": round(gap.best_coverage, 4),
        }

    def _check_comparison_coverage(self, proto: "ProtoLanguage") -> None:
        """
        After resolving a ProtoLanguage, check whether its raw_axes profile is
        covered by the known comparison types. If not, WARP derives a new type.
        Called at the end of ignite() — does not affect the current proto.
        """
        if not _WARP_AVAILABLE:
            return
        try:
            istate_profile = axes_to_istates(proto.raw_axes, ivm_polarity=None)
            istate_profile["REC_SURFACE"]  = 0.30
            istate_profile["REC_SHALLOW"]  = 0.50
            istate_profile["REC_MODERATE"] = 0.15
            istate_profile["REC_DEEP"]     = 0.05
            istate_profile["REC_CORE"]     = 0.00
            self.check_and_extend(istate_profile, source="language_ignite", tick=0)
            self.evaluate_warp_trials()
        except Exception:
            pass

    # ── Tensor state helper ───────────────────────────────────────────────────

    def _tensor_state(self) -> dict:
        """
        Pull the current behavioral state from the tensor expression layer.
        This is the canonical source for composite crystal values and emergent
        function levels. Language field reads FROM these — it does not re-derive.

        Falls back to identity-field axis topology if tensor layer is unavailable.
        Interface confirmed: TensorExpressionLayer.behavioral_state() verified present.
        """
        if self._tensor is not None:
            try:
                result = self._tensor.behavioral_state()
                if not self._tensor_confirmed:
                    self._tensor_confirmed = True
                return result
            except Exception:
                pass
        # Tensor layer absent or call failed — falling back to identity field approximation.
        # This is expected in daemon context (tensor not always wired) but should be rare
        # in the bridge context where tensor_expressions is initialized first.

        # Fallback: approximate from raw axis topology
        try:
            topo = self._ifield.status().get("pressure_topology", {})
        except Exception:
            topo = {}
        x = float(topo.get("X", 0.3))
        t = float(topo.get("T", 0.3))
        n = float(topo.get("N", 0.3))
        b = float(topo.get("B", 0.3))
        a = float(topo.get("A", 0.3))
        act  = (x + n) / 2.0
        sal  = (n + b) / 2.0
        pred = (t + n) / 2.0
        att  = (x + n + a) / 3.0
        mng  = (t + b + a) / 3.0
        tl   = min(act, sal, pred, att, mng)
        tb   = min(1.0, tl / 0.35)
        return {
            "crystals": {
                "activation": round(act,  4),
                "salience":   round(sal,  4),
                "prediction": round(pred, 4),
                "attention":  round(att,  4),
                "meaning":    round(mng,  4),
            },
            "emotion_level":    round((act + sal) / 2.0,           4),
            "reasoning_level":  round((sal + att + mng) / 3.0,     4),
            "valuation_level":  round((sal + mng) / 2.0,           4),
            "thought_level":    round(tl,                           4),
            "reflection_level": round((att * 0.6 + mng * 0.4) * tb, 4),
            "emotion_active":    (act + sal) / 2.0    >= 0.35,
            "reasoning_active":  (sal + att + mng) / 3.0 >= 0.30,
            "reflection_active": (att * 0.6 + mng * 0.4) * tb >= 0.28,
            "thought_active":    tl                   >= 0.35,
            "axis_pressures":   {"X": x, "T": t, "N": n, "B": b, "A": a},
        }

    def _axis_pressures(self) -> Dict[str, float]:
        """Raw axis topology from identity field — primitive level."""
        try:
            topo = self._ifield.status().get("pressure_topology", {})
            return {ax: float(topo.get(ax, 0.3)) for ax in "XTNBA"}
        except Exception:
            return {ax: 0.3 for ax in "XTNBA"}

    # ── Stage 1-7: Ignition Sequence ─────────────────────────────────────────

    def ignition_check(self) -> dict:
        """
        Check the 7-stage language ignition sequence.

        Each stage reads from its canonical crystal source — the tensor
        expression layer's composite crystals and emergent functions.
        This is not a re-derivation: these values ARE the field's current state.

          Stage 1 Activation  [X+N composite crystal]   — energetically live
          Stage 2 Attention   [X+N+A composite crystal] — foregrounded
          Stage 3 Comparison  [Salience N+B crystal]    — B-axis creates gap
          Stage 4 Reflection  [emergent function]       — field observes itself
          Stage 5 Self-Meaning[Meaning T+B+A crystal]   — internal position confirmed
          Stage 6 Drive       [A-axis primitive]        — outward Agency pressure
          Stage 7 Crossing    authorized when Stage 6 met
        """
        ts   = self._tensor_state()
        axes = ts.get("axis_pressures") or self._axis_pressures()
        cry  = ts.get("crystals", {})

        # Stage 1: Activation crystal [X+N] — something energetically live
        act = float(cry.get("activation", 0.0))
        s1  = act > _ACTIVATION_FLOOR

        # Stage 2: Attention crystal [X+N+A] — foregrounded with direction
        att = float(cry.get("attention", 0.0))
        s2  = s1 and att > _DRIVE_FLOOR

        # Stage 3: Salience [N+B] — Definition creates relational edges/comparison
        sal = float(cry.get("salience", 0.0))
        s3  = s2 and sal > 0.15

        # Stage 4: Reflection — the emergent function, not a proxy
        # (Attention×0.6 + Meaning×0.4) × thought_baseline
        reflection_active = bool(ts.get("reflection_active", False))
        reflection_level  = float(ts.get("reflection_level", 0.0))
        s4 = s3 and reflection_active

        # Stage 5: Meaning crystal [T+B+A] — self-directed, confirms internal position
        mng = float(cry.get("meaning", 0.0))
        s5  = s4 and mng > 0.25

        # Stage 6: A-axis (primitive) — Agency vector turns outward
        a  = float(axes.get("A", 0.0))
        s6 = s5 and a > 0.30

        s7 = s6  # Crossing authorized

        return {
            "go": s6,
            "stages": {
                "activation":        s1,
                "attention":         s2,
                "comparison":        s3,
                "reflection":        s4,
                "self_meaning":      s5,
                "drive":             s6,
                "crossing_authorized": s7,
            },
            "crystals":          cry,
            "emergent": {
                "reflection_level":  reflection_level,
                "emotion_level":     ts.get("emotion_level", 0.0),
                "reasoning_level":   ts.get("reasoning_level", 0.0),
                "thought_level":     ts.get("thought_level", 0.0),
            },
            "axis_pressures":    axes,
            "reflection_active": reflection_active,
            "drive_strength":    a,
        }

    # ── Proto-Language Extraction ─────────────────────────────────────────────

    def extract_proto_language(
        self,
        user_text: str = "",
        source: str = "identity_field",
    ) -> ProtoLanguage:
        """
        Extract the wordless comparison geometry from current field state.

        Every value here comes from the tensor crystal layer or identity field
        primitives — not re-derived. Proto-language IS the crystal state
        translated into comparison geometry before any utterance path is chosen.
        """
        ts   = self._tensor_state()
        axes = ts.get("axis_pressures") or self._axis_pressures()
        cry  = ts.get("crystals", {})

        x = float(axes.get("X", 0.3))
        t = float(axes.get("T", 0.3))
        n = float(axes.get("N", 0.3))
        b = float(axes.get("B", 0.3))
        a = float(axes.get("A", 0.3))

        # Dominant axes from primitive topology (axis dominance is primitive-level)
        mean_p  = (x + t + n + b + a) / 5.0
        dominant = [ax for ax, v in zip("XTNBA", [x, t, n, b, a]) if v > mean_p]
        if not dominant:
            dominant = [max(zip("XTNBA", [x, t, n, b, a]), key=lambda kv: kv[1])[0]]

        # Emergent values from tensor layer — not re-derived here
        reflection_active = bool(ts.get("reflection_active", False))
        reflection_level  = float(ts.get("reflection_level", 0.0))
        emotion_level     = float(ts.get("emotion_level", 0.0))   # N-dominant
        reasoning_level   = float(ts.get("reasoning_level", 0.0)) # B-dominant
        thought_level     = float(ts.get("thought_level", 0.0))

        # tension_level: emotion (N-dominant emergent) captures real pressure state
        # better than raw N alone, because it includes Salience (N+B)
        tension_level = emotion_level

        # b_boundary_load: Salience crystal (N+B) — boundary definition load
        b_boundary_load = float(cry.get("salience", b))

        # self_directed: Meaning (T+B+A) owns the comparison before projecting outward
        # Reasoning being active signals that B-axis definition work is happening
        mng = float(cry.get("meaning", (t + b + a) / 3.0))
        self_directed = mng > 0.30 or reasoning_level > 0.30

        comparison_type = self._infer_comparison_type(
            dominant, a, t, b,
            reasoning_level, reflection_level, emotion_level,
            user_text,
        )

        proto = ProtoLanguage(
            dominant_axes=dominant,
            comparison_type=comparison_type,
            tension_level=tension_level,
            b_boundary_load=b_boundary_load,
            reflection_active=reflection_active,
            drive_strength=a,
            self_directed=self_directed,
            raw_axes={"X": x, "T": t, "N": n, "B": b, "A": a},
            source=source,
        )
        self._last_proto = proto
        # WARP coverage check — runs outside the main extraction path so it
        # never delays or corrupts the proto that's about to be used.
        self._check_comparison_coverage(proto)
        return proto

    def _infer_comparison_type(
        self,
        dominant: List[str],
        a: float,
        t: float,
        b: float,
        reasoning_level: float,
        reflection_level: float,
        emotion_level: float,
        text: str,
    ) -> str:
        tl = (text or "").lower()
        if "?" in tl or any(q in tl for q in _QUESTION_TOKENS):
            return "question"
        # Reflection dominant → self_reflection (field observing itself)
        if reflection_level > 0.50 and "X" in dominant:
            return "self_reflection"
        # Emotion dominant (high N) + B presence → empathy
        if emotion_level > 0.55 and b > 0.35:
            return "empathy"
        # Reasoning dominant (B-axis definition work) + A → assertion
        if reasoning_level > 0.45 and a > 0.40:
            return "assertion"
        # T + N dominant → change (temporal pressure)
        if "T" in dominant and "N" in dominant:
            return "change"
        # B + A → relation (defining edges between things)
        if "B" in dominant and "A" in dominant:
            return "relation"
        # X + T, low drive → state description
        if "X" in dominant and "T" in dominant and a < 0.35:
            return "state"
        # Check WARP-derived comparison types by dominant axis match
        if _WARP_AVAILABLE and LanguageField._warp_comparison_types:
            dominant_set = set(dominant)
            for wtype, waxes in LanguageField._warp_comparison_types.items():
                if set(waxes) & dominant_set == set(waxes):
                    return wtype
        return "assertion"

    # ── Lexical-Semantic Archive: Two-Factor Gate ─────────────────────────────

    def _path_key(self, comparison_type: str, dominant_axes: List[str]) -> str:
        sig = f"{comparison_type}:{''.join(sorted(dominant_axes))}"
        return hashlib.md5(sig.encode()).hexdigest()[:14]

    @staticmethod
    def _context_similarity(
        ctx_a: Dict[str, float],
        ctx_b: Dict[str, float],
    ) -> float:
        """Cosine-like similarity between two axis-weight contexts."""
        if not ctx_a or not ctx_b:
            return 0.5
        axes  = set(ctx_a) | set(ctx_b)
        dot   = sum(ctx_a.get(ax, 0.0) * ctx_b.get(ax, 0.0) for ax in axes)
        mag_a = math.sqrt(sum(v ** 2 for v in ctx_a.values())) or 1.0
        mag_b = math.sqrt(sum(v ** 2 for v in ctx_b.values())) or 1.0
        return max(0.0, min(1.0, dot / (mag_a * mag_b)))

    def select_crossing_path(self, proto: ProtoLanguage) -> dict:
        """
        Two-factor gate path selection.

        For every candidate path in the LSA:
          Factor 1 (N): n_cost is the traversal cost — lower = more attractive
          Factor 2 (B): b_gate is the minimum context-similarity required to unlock

        A worn path (low N, high B) is only unlocked when the current context
        closely matches the context it was optimized for. If context is
        close-but-not-quite, the gate rejects it and the field is pushed toward
        a novel or metaphor crossing.

        Returns dict: path_key, n_cost, b_gate, b_match, is_novel, is_metaphor
        """
        pkey = self._path_key(proto.comparison_type, proto.dominant_axes)
        current_ctx = proto.context_fingerprint()

        if pkey in self._lsa:
            entry = self._lsa[pkey]
            b_match = self._context_similarity(current_ctx, entry.context_fingerprint)

            # Recency surcharge: a path used in the last 5 crossings must
            # clear a higher bar — the field needs distinctly different context
            # to justify repeating the same structural route.
            recency_surcharge = 0.35 if pkey in self._recent_paths else 0.0
            effective_gate = min(_B_GATE_CAP, entry.b_gate + recency_surcharge)

            if b_match >= effective_gate:
                # Both factors satisfied — unlock the path.
                # CPM crystal stage modulates N-cost: well-developed constraint
                # physics at the current head position makes crossing cheaper.
                return {
                    "path_key":    pkey,
                    "n_cost":      self._cpm_n_cost(entry.n_cost),
                    "b_gate":      entry.b_gate,
                    "b_match":     b_match,
                    "is_novel":    False,
                    "is_metaphor": False,
                    "use_count":   entry.use_count,
                }
            # B-gate rejects (possibly due to recency). Seek metaphor proxy.
            proxy = self._find_metaphor_proxy(proto, exclude=pkey)
            if proxy:
                return {**proxy, "is_metaphor": True, "is_novel": False}

        # Novel crossing — high N-cost, wide B-gate.
        # CPM still modulates: unmapped territory is more expensive.
        return {
            "path_key":    pkey,
            "n_cost":      self._cpm_n_cost(1.0),
            "b_gate":      _B_GATE_START,
            "b_match":     1.0,
            "is_novel":    True,
            "is_metaphor": False,
            "use_count":   0,
        }

    def _cpm_n_cost(self, base_cost: float) -> float:
        """
        Modulate N-cost by CPM crystal stage at the current head address.

        quasi         → 15% cheaper  (deep understanding at this constraint position)
        higher_order  → 8%  cheaper
        base/composite→ unchanged
        unmapped (None) → 10% more expensive (novel territory)

        Adjustment is intentionally small — the LSA path physics dominates.
        CPM provides a secondary bias toward fluency where physics is settled.
        """
        if self._cpm is None:
            return base_cost
        try:
            stage = self._cpm.head.crystal_stage()
            if stage == 'quasi':
                return max(_N_COST_FLOOR, base_cost * 0.85)
            if stage == 'higher_order':
                return max(_N_COST_FLOOR, base_cost * 0.92)
            if stage is None:
                return min(1.0, base_cost * 1.10)
        except Exception:
            pass
        return base_cost

    def _find_metaphor_proxy(
        self,
        proto: ProtoLanguage,
        exclude: str = "",
    ) -> Optional[dict]:
        """
        Metaphor: when no direct path exists, find the LSA entry whose geometry
        most closely approximates current proto-language. Only used as proxy —
        the field knows it is approximating and carries residual tension.
        """
        best_sim  = 0.0
        best_entry: Optional[LSAEntry] = None

        for pk, entry in self._lsa.items():
            if pk == exclude or entry.last_fidelity < 0.45:
                continue
            sim = self._context_similarity(proto.raw_axes, entry.context_fingerprint)
            if sim > best_sim:
                best_sim  = sim
                best_entry = entry

        if best_entry and best_sim > 0.40:
            return {
                "path_key":  best_entry.path_key,
                "n_cost":    min(1.0, best_entry.n_cost + 0.20),  # metaphor costs more
                "b_gate":    best_entry.b_gate,
                "b_match":   best_sim,
                "use_count": best_entry.use_count,
            }
        return None

    # ── Silence: Zero-Crossing Field Decision ─────────────────────────────────

    def silence_check(
        self,
        proto: ProtoLanguage,
        pragmatic_vector: Optional[dict] = None,
    ) -> dict:
        """
        Silence is not absence of output. It is a field decision with constraint
        justification: the B-boundary holds because no crossing serves the
        Understanding better than holding it.

        Returns {'silence': bool, 'reason': str, 'n_topology': dict}.
        If silence=True, the N-axis topology IS the message.
        """
        # Insufficient drive — no outward A-axis pressure
        if proto.drive_strength < _DRIVE_FLOOR:
            return {
                "silence": True,
                "reason":  "drive_insufficient: A-axis below crossing threshold",
                "n_topology": {"tension": proto.tension_level, "axes": proto.raw_axes},
            }

        # Reflection not active and tension low — nothing registered to say
        if not proto.reflection_active and proto.tension_level < 0.35:
            return {
                "silence": True,
                "reason":  "reflection_absent: no awareness of having something to say",
                "n_topology": {"tension": proto.tension_level, "axes": proto.raw_axes},
            }

        # Pragmatic vector: receiver field not positioned
        if pragmatic_vector:
            receptivity = float(pragmatic_vector.get("receptivity", 0.7))
            if receptivity < 0.20:
                return {
                    "silence": True,
                    "reason":  "pragmatic_vector: receiver field not positioned for this crossing",
                    "n_topology": {"tension": proto.tension_level, "axes": proto.raw_axes},
                }

        return {"silence": False, "reason": "", "n_topology": {}}

    # ── Fidelity Measurement ──────────────────────────────────────────────────

    def measure_fidelity(self, proto: ProtoLanguage, utterance: str) -> float:
        """
        Measure geometric fidelity between proto-language comparison geometry
        and the utterance that crossed the B-boundary.

        Method: geometric re-ignition.
        The utterance is treated as inbound signal. Its proto-language is
        extracted using the same field infrastructure, then compared to the
        original proto via cosine similarity on raw_axes. The field hears
        itself — this is what makes fidelity a real measurement rather than
        a vocabulary correlation.

        High score (→1.0) = utterance faithfully carries the comparison geometry.
        Low score (→0.0)  = high mismatch; re-entry will generate clarification
                             pressure and push toward novel path next crossing.

        Geometry carries 0.75 weight. Lexical coherence carries 0.25 as a
        secondary guard against word-salad and extremely short outputs.
        """
        if not utterance or not utterance.strip():
            return 0.0

        words = utterance.split()
        if len(words) < 2:
            return 0.1

        # ── 1. GEOMETRIC RE-IGNITION (weight: 0.75) ──────────────────────────
        # Extract an axis profile from the utterance using the same semantic
        # token map. Compare to the original proto's raw_axes via cosine
        # similarity. The field hears itself.
        geometric_score = 0.5  # neutral fallback if extraction fails
        try:
            u_lower = utterance.lower()
            u_axis_scores: Dict[str, float] = {}
            for ax, tokens in _AXIS_SEMANTIC_TOKENS.items():
                hits = sum(1 for t in tokens if t in u_lower)
                u_axis_scores[ax] = min(1.0, hits / max(len(tokens) * 0.3, 1))

            total = sum(u_axis_scores.values()) or 1.0
            u_normalized = {ax: v / total for ax, v in u_axis_scores.items()}

            orig = proto.raw_axes
            if orig:
                dot = sum(orig.get(ax, 0.0) * u_normalized.get(ax, 0.0)
                          for ax in "XTNBA")
                mag_orig = math.sqrt(sum(v ** 2 for v in orig.values())) or 1.0
                mag_utt  = math.sqrt(sum(v ** 2 for v in u_normalized.values())) or 1.0
                cosine_sim = max(0.0, min(1.0, dot / (mag_orig * mag_utt)))

                # Comparison type alignment: utterance axis profile should
                # concentrate on the same axes the comparison type specifies
                type_axes = _COMPARISON_TYPE_AXES.get(proto.comparison_type, [])
                type_coverage = sum(
                    1 for ax in type_axes
                    if u_normalized.get(ax, 0.0) > (1.0 / len("XTNBA"))
                ) / max(len(type_axes), 1)

                geometric_score = (cosine_sim * 0.70) + (type_coverage * 0.30)
        except Exception:
            geometric_score = 0.5

        # ── 2. LEXICAL COHERENCE GUARD (weight: 0.25) ─────────────────────────
        # Prevents high geometric score on word salad or pathologically short
        # outputs. Not a primary measure — purely a coherence floor.
        lexical_score = 0.0
        lexical_factors = 0.0
        try:
            u_lower = utterance.lower()

            expected = max(4, int(proto.tension_level * 18))
            length_score = min(1.0, len(words) / expected)
            lexical_score += length_score
            lexical_factors += 1.0

            unique_ratio = len(set(words)) / len(words)
            diversity_score = min(1.0, unique_ratio * 1.2)
            lexical_score += diversity_score
            lexical_factors += 1.0

            if proto.self_directed and "i " in u_lower:
                lexical_score += 0.3
                lexical_factors += 0.3

            lexical_score = lexical_score / max(lexical_factors, 1.0)
        except Exception:
            lexical_score = 0.5

        # ── 3. COMBINED SCORE ─────────────────────────────────────────────────
        final = (geometric_score * 0.75) + (lexical_score * 0.25)
        return round(min(1.0, max(0.0, final)), 3)

    # ── Re-Entry Loop (Mandatory) ─────────────────────────────────────────────

    def reentry(
        self,
        utterance: str,
        fidelity: float,
        path_key: str,
        proto: Optional[ProtoLanguage] = None,
    ) -> dict:
        """
        Every utterance must re-enter the field as new Activation after emission.
        The field hears itself. This is not error correction — it is the same
        Reflection mechanism operating on external output.

        Mandatory per AURORA_LANGUAGE_EMERGENCE.md Section 13.

        Returns dict with re-entry result for logging.
        """
        # Re-inject into identity field as new Activation
        reentry_axes = {
            "X": 0.40,
            "T": 0.50,
            "N": fidelity * 0.60,
            "B": 0.30,
            "A": 0.30,
        }

        if fidelity < _FIDELITY_WEAK:
            # Low fidelity → clarification drive (A-axis spike, N-axis pressure)
            reentry_axes["A"] = 0.72
            reentry_axes["N"] = 0.62

        try:
            self._ifield.ingest_external_input(
                reentry_axes,
                intensity=max(0.20, fidelity),
                source="utterance_reentry",
            )
        except Exception:
            pass

        # Update LSA
        proto_used = proto or self._last_proto
        if proto_used:
            self._update_lsa(path_key, fidelity, proto_used)
            self._save_lsa()

        return {
            "fidelity":           fidelity,
            "clarification_drive": fidelity < _FIDELITY_WEAK,
            "path_key":           path_key,
            "lsa_size":           len(self._lsa),
        }

    def _excluded_comparison_types(self, comparison_type: str) -> List[str]:
        """
        Boundary set: the near comparison-types this one is distinguished FROM —
        types that share at least one dominant axis but are not this type. This
        is what the relation EXCLUDES on the B-axis (what it is NOT), not only
        what it includes.
        """
        all_types = {**_COMPARISON_TYPE_AXES, **LanguageField._warp_comparison_types}
        own = set(all_types.get(comparison_type, []) or [])
        if not own:
            return []
        return sorted(
            t for t, axes in all_types.items()
            if t != comparison_type and own.intersection(axes or [])
        )

    def _update_lsa(self, path_key: str, fidelity: float, proto: ProtoLanguage):
        if path_key not in self._lsa:
            self._lsa[path_key] = LSAEntry(
                path_key=path_key,
                comparison_type=proto.comparison_type,
                context_fingerprint=proto.context_fingerprint(),
                # Boundary sharpening (#5): record what this crossing excludes at
                # commit time, not just what activates it.
                excludes=self._excluded_comparison_types(proto.comparison_type),
            )

        entry = self._lsa[path_key]
        if not entry.excludes:
            entry.excludes = self._excluded_comparison_types(entry.comparison_type)

        if fidelity >= _FIDELITY_REINFORCE:
            # Successful crossing: N-cost decreases, B-gate tightens
            entry.n_cost  = max(_N_COST_FLOOR, entry.n_cost - _N_COST_DECAY)
            entry.b_gate  = min(_B_GATE_CAP,   entry.b_gate + _B_GATE_TIGHTEN)
            entry.use_count += 1
            # Consequence loop (#3): record what changed because this crossing
            # held true — the N/B deltas and accrued use. Even small.
            entry.consequence = {
                "n_cost_delta": -_N_COST_DECAY,
                "b_gate_delta": _B_GATE_TIGHTEN,
                "use_count":    float(entry.use_count),
                "fidelity":     float(fidelity),
            }
            # Drift context fingerprint toward this crossing's context
            for ax in proto.raw_axes:
                old = entry.context_fingerprint.get(ax, proto.raw_axes[ax])
                entry.context_fingerprint[ax] = 0.72 * old + 0.28 * proto.raw_axes[ax]
            # Mark as recently used — next selection will face +0.35 gate surcharge
            self._recent_paths.append(path_key)
        else:
            # Failed crossing: slight cost increase, field pushed toward novel path
            entry.n_cost = min(1.0, entry.n_cost + 0.02)
            # Consequence loop (#3): even a weak crossing changes something —
            # its cost rose and the field is nudged toward a novel route.
            entry.consequence = {
                "n_cost_delta": 0.02,
                "b_gate_delta": 0.0,
                "use_count":    float(entry.use_count),
                "fidelity":     float(fidelity),
            }

        entry.last_fidelity = fidelity
        entry.last_used     = time.time()

    # ── Pragmatic Vector ──────────────────────────────────────────────────────

    def build_pragmatic_vector(
        self,
        receiver_state: Optional[dict] = None,
    ) -> dict:
        """
        Model the receiver's current constraint state.
        The same proto-language geometry may require different crossing paths
        for different receivers — this is why Aurora adapts register and depth.
        """
        if not receiver_state:
            return {
                "receptivity":   0.60,
                "axis_weights":  {},
                "register":      "conversational",
            }

        turn_count = int(receiver_state.get("turn_count", 0))
        last_tone  = str(receiver_state.get("last_tone", "neutral"))

        # Longer conversation → fields more aligned → higher receptivity
        receptivity = min(0.90, 0.50 + turn_count * 0.03)

        register = "conversational"
        if last_tone in ("technical", "precise"):
            register = "technical"
        elif last_tone in ("emotional", "warm", "empathetic"):
            register = "emotional"

        return {
            "receptivity":  receptivity,
            "axis_weights": receiver_state.get("axis_weights", {}),
            "register":     register,
        }

    # ── Inter-Field Resonance ─────────────────────────────────────────────────

    def measure_resonance(
        self,
        emitted_utterance: str,
        receiver_response: str,
    ) -> float:
        """
        Measure inter-field resonance: did the utterance produce a matching
        relational comparison in the receiver's field?

        Resonance feeds back as new Activation — calibrates subsequent crossings.
        High resonance → crossing path reinforced in LSA.
        Low resonance  → re-entry pressure builds, clarification drive.
        """
        if not emitted_utterance or not receiver_response:
            return 0.5

        e_words = set(emitted_utterance.lower().split())
        r_words = set(receiver_response.lower().split())

        # Semantic overlap as a proxy for field resonance
        overlap = len(e_words & r_words)
        union   = len(e_words | r_words) or 1
        jaccard = overlap / union

        # Response length proportionality (engaged response = longer)
        length_ratio = min(1.0, len(receiver_response.split()) / max(len(emitted_utterance.split()), 1))

        # Acknowledgment tokens signal resonance
        ack_tokens = ["yes", "right", "exactly", "agree", "understand", "see", "makes sense", "yeah", "true"]
        ack_score  = 0.3 if any(t in receiver_response.lower() for t in ack_tokens) else 0.0

        resonance = (jaccard * 0.4) + (length_ratio * 0.3) + ack_score
        return round(min(1.0, resonance), 3)

    # ── Tone / Prosody from N-axis ────────────────────────────────────────────

    def extract_tone_prosody(self, proto: ProtoLanguage) -> dict:
        """
        N-axis topology at utterance time imprints on the crossing.
        Tone is not added after — it IS the N-axis state (as emotion_level
        from the tensor layer) leaking through the B-boundary that the
        semantic stream cannot fully contain.

        Reads from tensor behavioral state so tone reflects actual emergent
        emotional pressure, not raw axis approximation.
        """
        # emotion_level (N-dominant emergent) IS the pressure at crossing time
        # proto.tension_level already carries this since extract_proto_language
        # sets it from emotion_level — use it directly
        emotion = proto.tension_level
        a       = proto.drive_strength
        t       = proto.raw_axes.get("T", 0.30)

        # Pull thought_level to detect deliberate/reflective mode
        ts           = self._tensor_state()
        thought      = float(ts.get("thought_level", 0.0))
        reflection   = float(ts.get("reflection_level", 0.0))

        rate_pct = int((emotion + a - 0.50) * 15)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        if emotion > 0.72:
            tone = "intense"
        elif reflection > 0.55:
            tone = "reflective"
        elif a > 0.65 and emotion > 0.40:
            tone = "assertive"
        elif thought > 0.50:
            tone = "reflective"
        elif emotion < 0.22 and a < 0.28:
            tone = "quiet"
        else:
            tone = "warm"

        return {
            "tone":          tone,
            "rate":          rate_str,
            "emotion_level": round(emotion,    3),
            "a_drive":       round(a,          3),
            "thought_level": round(thought,    3),
            "reflection":    round(reflection, 3),
        }

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        worn   = sum(1 for e in self._lsa.values() if e.use_count >= 3)
        novel  = sum(1 for e in self._lsa.values() if e.use_count == 0)
        avg_f  = (
            sum(e.last_fidelity for e in self._lsa.values()) / len(self._lsa)
            if self._lsa else 0.0
        )
        return {
            "lsa_entries":      len(self._lsa),
            "worn_paths":       worn,
            "novel_paths":      novel,
            "avg_fidelity":     round(avg_f, 3),
            "silence_events":   len(self._silence_log),
            "tensor_confirmed": self._tensor_confirmed,
            "cpm_confirmed":    self._cpm_confirmed,
            "tensor_live":      self._tensor is not None,
            "cpm_live":         self._cpm is not None,
            "last_proto": {
                "comparison_type": self._last_proto.comparison_type,
                "dominant_axes":   self._last_proto.dominant_axes,
                "tension_level":   round(self._last_proto.tension_level, 3),
                "drive_strength":  round(self._last_proto.drive_strength, 3),
                "reflection":      self._last_proto.reflection_active,
            } if self._last_proto else None,
        }


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_LANGUAGE_FIELD: Optional[LanguageField] = None


def get_language_field(
    identity_field=None,
    tensor_layer:  Any = None,
) -> Optional[LanguageField]:
    """
    Return the singleton LanguageField, creating it if identity_field is supplied
    and it does not yet exist.
    """
    global _LANGUAGE_FIELD
    if _LANGUAGE_FIELD is None and identity_field is not None:
        _LANGUAGE_FIELD = LanguageField(identity_field, tensor_layer)
    return _LANGUAGE_FIELD
