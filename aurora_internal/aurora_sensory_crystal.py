#!/usr/bin/env python3
"""
Aurora Sensory Crystal — 6-Facet Cross-Modal Understanding
===========================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Zero-state sensory competency seeded into Aurora's lineage system.

Crystal geometry (hexagonal bipyramid):

    TOP HALF  (visual):  HUE  / SHAPE  / MOTION
    ─────────────────── SEMANTIC MIDDLE PLANE ───────────────────
    BOTTOM HALF (audio): TONE / TIMBRE / RHYTHM

Bottom 3 facets draw from audio.features.v1 (20-d vector):
    TONE   — harmonicity [6] + chroma-lite [8:20]     (13 dims)
    TIMBRE — RMS [0], ZCR [1], centroid [2], bw [3], rolloff [4]  (5 dims)
    RHYTHM — spectral_flux [5] + onset_density [7]     (2 dims)

Top 3 facets draw from vision.features.v1 (57-d vector):
    HUE    — HSV histograms [0:24]                    (24 dims)
    SHAPE  — edge + orientation + shape proxy [24:51] (27 dims)
    MOTION — motion + symmetry [51:57]                 (6 dims)

Opposite facets pair through the semantic middle plane:
    tone <-> hue      (pitch/harmony  <-> colour)
    timbre <-> shape  (texture        <-> form/edge)
    rhythm <-> motion (onset/tempo    <-> movement/flow)

LINEAGE INTEGRATION
───────────────────
All operations are registered in lineage_canonical.CANONICAL_OPERATION_CONSTRAINTS.
The trait spec below seeds 5 lineage stages through Aurora's ability genealogy:

    1. sensory_intake_seed        (gen=1, N-axis)  — raw signal enters crystal
    2. sensory_crystal_clustering (gen=2, B-axis)  — observations cluster into nodes
    3. sensory_concept_promotion  (gen=2, A-axis)  — primitive → concept → promoted
    4. cross_modal_grounding      (gen=3, N-axis)  — audio×visual → semantic plane
    5. sensory_wisdom_distillation(gen=3, T-axis)  — mature nodes distill, dead emit wisdom

Call ensure_sensory_crystal_lineage(systems) at Aurora boot to seed these abilities
into the genealogy exactly like all other Aurora abilities.

PROMOTION RULES (match existing aurora_dimensional_systems crystal rules)
──────────────────────────────────────────────────────────────────────────
    usage_count   >= 14     (CONCEPT_PROMOTION_USAGE)
    session_count >= 3      (CONCEPT_PROMOTION_SESSIONS)
    confidence    >= 0.55   (CONCEPT_PROMOTION_CONFIDENCE)
    fitness = 0.40*conf + 0.35*usage_norm + 0.25*session_norm
    decay_rate = base * (0.15 + 0.85 * (1 - maturity))   [plateau-aware]
    distillation at maturity >= 0.80

State persisted to:
    aurora_state/sensory_crystal/audio/{tone,timbre,rhythm}/state.agb
    aurora_state/sensory_crystal/visual/{hue,shape,motion}/state.agb
    aurora_state/sensory_crystal/semantic/state.agb
"""

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import gzip
import hashlib
import json
import logging
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aurora_constraint_unit_adapter import build_constraint_profile
from aurora_representational_address import RepresentationalRef

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:79",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 79, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
    )
    HAS_NUMPY = False

logger = logging.getLogger(__name__)

# =============================================================================
# PROMOTION CONSTANTS  — mirror aurora_dimensional_systems crystal thresholds
# =============================================================================

CONCEPT_PROMOTION_USAGE       = 14
CONCEPT_PROMOTION_SESSIONS    = 3
CONCEPT_PROMOTION_CONFIDENCE  = 0.45
SIMILARITY_MATCH_THRESHOLD    = 0.93
ARCHETYPE_MATCH_THRESHOLD     = 0.82
DISTILLATION_MATURITY_GATE    = 0.80
EMA_ALPHA                     = 0.15
DEFAULT_CANDIDATE_CAP         = 80

USAGE_NORM_CAP      = 50.0
SESSION_BREADTH_CAP = 10.0

# =============================================================================
# REPRESENTATIONAL CITIZENSHIP  —  Sunni & Cael, Build 654
# =============================================================================
# A promoted SensoryNode's primary axis. Facet names are unique across
# domains (tone/timbre/rhythm are audio-only, hue/shape/motion are
# visual-only), so this is keyed on facet alone -- matching, and now the
# single source of truth for, AuroraSensoryCrystal's pre-existing
# _dps_route_observation() axis stamping (previously a separate, silently
# disagreeing table: tone/timbre/rhythm all defaulted to N and hue/shape/
# motion were B/B/T there, while DPS routing independently held T/B/N/X/B/A
# with its own stated per-facet reasoning below -- confirmed by direct grep,
# not assumed. Reconciled onto the DPS table because it carries actual
# reasoning per facet; the other was an unexamined copy with no rationale
# of its own). One table now feeds genealogy/evolution/citizenship AND DPS
# routing, so the same sensory representation cannot hold two different
# primitive axis identities depending on which subsystem is asked.
SENSORY_FACET_AXIS: Dict[str, str] = {
    "tone":   "T",   # temporal / tonal coherence
    "timbre": "B",   # boundary / textural edge
    "rhythm": "N",   # energy / onset pattern
    "hue":    "X",   # existence / colour identity
    "shape":  "B",   # boundary / form
    "motion": "A",   # agency / movement
}

# RepresentationalRef.nc_dim requires one of DIM_NAMES = (POLARITY,
# MAGNITUDE, OPERATOR, COST, DIFFERENCE). No prior code assigns sensory
# facets a position on that ladder, so this mapping is a stated design
# choice, not a rediscovered fact: tone/hue carry a categorical quality
# (OPERATOR); timbre/shape carry the distinguishing structure that lets one
# node be told apart from a neighboring one (DIFFERENCE); rhythm/motion
# carry temporal/intensity extent (MAGNITUDE).
SENSORY_FACET_DIM_NAME: Dict[str, str] = {
    "tone": "OPERATOR", "hue": "OPERATOR",
    "timbre": "DIFFERENCE", "shape": "DIFFERENCE",
    "rhythm": "MAGNITUDE", "motion": "MAGNITUDE",
}


def _facet_axis(domain: str, facet: str) -> str:
    return SENSORY_FACET_AXIS.get(facet, "N")


# =============================================================================
# LEARNED AXIS PARTICIPATION  —  Sunni & Cael, Build 656+ follow-up
# =============================================================================
# SENSORY_FACET_AXIS assigns every node on a facet the SAME starting axis,
# by category, before she has encountered a single instance of it. That is
# a reasonable prior (see its own stated rationale above), not a permanent
# verdict. What follows lets an individual representation's own
# encountered evidence override that prior for ITSELF -- other nodes on
# the same facet remain free to end up on a different axis if their own
# evidence points elsewhere.
AXIS_EVIDENCE_EMA_RATE    = 0.15   # matches EMA_ALPHA's smoothing elsewhere
AXIS_EVIDENCE_MIN_SAMPLES = 5      # don't reassign from a couple of ticks
AXIS_EVIDENCE_MARGIN      = 0.12   # dominant axis must clearly lead, not barely

_AXES5: Tuple[str, ...] = ("X", "T", "N", "B", "A")


SENSORY_CITIZEN_COST_BASE = 0.0006


def _axis_weighted_cost(axis: str, cost_base: float = SENSORY_CITIZEN_COST_BASE) -> Dict[str, float]:
    """Shared cost-shaping formula for a sensory citizen ability, used both
    at initial grant and whenever learned axis evidence reassigns which
    axis is primary -- same shape, different axis, one definition."""
    return {a: (cost_base * (1.4 if a == axis else 0.6)) for a in _AXES5}


def _node_axis_evidence_sample(node: "SensoryNode") -> Dict[str, float]:
    """One tick's raw 5-axis evidence sample, built entirely from
    quantities the node already tracks about its own encountered history
    -- no new instrumentation, no fabricated signal:

      X (existence/admissibility): confidence -- how certain her sense of
         this representation's own reality is.
      T (temporal/momentum):       session_count, normalized -- how much
         this representation has recurred and persisted across her
         sessions over time, not just within one.
      N (energy):                  usage_count, normalized -- how much raw
         activation it has actually drawn.
      B (boundary/integration):    len(cross_modal_links) -- how much
         cross-modal binding work it participates in.
      A (agency):                  fitness -- how much self-directed
         standing it has already earned toward its own promotion.
    """
    return {
        "X": _clamp01(node.confidence),
        "T": _clamp01(node.session_count / SESSION_BREADTH_CAP),
        "N": _clamp01(node.usage_count / USAGE_NORM_CAP),
        "B": _clamp01(len(node.cross_modal_links) / 4.0),
        "A": _clamp01(node.fitness),
    }


def _sensory_structured_state(node: "SensoryNode") -> Dict[str, Any]:
    """The representation's full live state, for AbilityProfile.
    structured_state (Sunni & Cael, Build 656+ follow-up: "put the sensory
    node's structured live state directly onto its intact representational
    surface so RCRW sees more than an AbilityProfile proxy"). Everything
    here was previously only reachable via the transient genealogy.
    observe() notes payload of whichever tick_citizen_participation() call
    happened to run last -- not part of the STANDING operand surface
    representation_record()/staged inquiry operands/RCRW actually read."""
    return {
        "centroid": list(node.centroid),
        "fitness": round(node.fitness, 4),
        "usage_count": node.usage_count,
        "session_count": node.session_count,
        "cross_modal_links": list(node.cross_modal_links),
        "maturity": round(node.maturity, 4),
        "axis_evidence": dict(node.axis_evidence),
        "axis_evidence_samples": node.axis_evidence_samples,
    }


def _update_axis_evidence(node: "SensoryNode") -> Optional[str]:
    """Fold one tick's sample into the node's running axis-evidence EMA
    and return a newly-earned dominant axis, or None if evidence doesn't
    yet clearly support moving off the current one. Never called more than
    once per tick_citizen_participation() call -- this is real encounter
    evidence, not a per-sample flood."""
    sample = _node_axis_evidence_sample(node)
    ev = dict(node.axis_evidence) if node.axis_evidence else {a: 0.0 for a in _AXES5}
    for a in _AXES5:
        prev = ev.get(a, 0.0)
        ev[a] = prev + AXIS_EVIDENCE_EMA_RATE * (sample[a] - prev)
    node.axis_evidence = ev
    node.axis_evidence_samples += 1

    if node.axis_evidence_samples < AXIS_EVIDENCE_MIN_SAMPLES:
        return None
    ranked = sorted(ev.items(), key=lambda kv: kv[1], reverse=True)
    dominant_axis, dominant_val = ranked[0]
    runner_up_val = ranked[1][1] if len(ranked) > 1 else 0.0
    if dominant_val - runner_up_val < AXIS_EVIDENCE_MARGIN:
        return None
    return dominant_axis


def _facet_dim_name(facet: str) -> str:
    return SENSORY_FACET_DIM_NAME.get(facet, "OPERATOR")


def sensory_representational_ref(domain: str, facet: str) -> RepresentationalRef:
    """D1-level RepresentationalRef for a sensory (domain, facet) axis --
    shared identity ground every node on that facet resolves against.
    Only nc_law_c/nc_dim are ever independently determined here; nc_target
    is left unresolved because no NonComp-target context exists for a
    sensory facet (see aurora_representational_address's doctrine: leave
    unresolved rather than guess)."""
    return RepresentationalRef.for_d1(constraint=_facet_axis(domain, facet), dimension=_facet_dim_name(facet))


def sensory_citizen_ability_id(domain: str, facet: str, node_id: str) -> str:
    """Stable (idempotent, re-derivable) genealogy AbilityProfile id for a
    specific sensory representation. Unlike register_code_evolution_outcome's
    mutation_id (time-hashed, unique per *event*), this is a pure function
    of the node's own identity -- the same node always resolves to the same
    ability id, so it can be looked up again later, not just created once."""
    axis = _facet_axis(domain, facet)
    digest = hashlib.sha1(f"{domain}:{facet}:{node_id}".encode()).hexdigest()[:16]
    return f"{axis}:SENSORY_REPR_{digest}"

# Maturity formula weights (match maturity.py in Agora / aurora standards)
WEIGHT_STABILITY   = 0.55
WEIGHT_NOVELTY     = 0.35
WEIGHT_COMPRESSION = 0.10
DECAY_FLOOR        = 0.15
DECAY_CEILING      = 0.85

# Cross-modal semantic node promotion
CROSS_MODAL_MIN_COOCCURRENCE = 10
CROSS_MODAL_MIN_NPMI         = 0.15
SEMANTIC_PROMOTION_FITNESS   = 0.60

# Concept floors per domain
AUDIO_CONCEPT_FLOOR   = 8
VISUAL_CONCEPT_FLOOR  = 10
SEMANTIC_CONCEPT_FLOOR = 6

# =============================================================================
# FACET GEOMETRY
# =============================================================================

AUDIO_FACET_INDICES: Dict[str, List[int]] = {
    "tone":   [6] + list(range(8, 20)),  # harmonicity + chroma  (13 dims)
    "timbre": list(range(0, 5)),          # RMS+ZCR+centroid+bw+rolloff (5 dims)
    "rhythm": [5, 7],                     # flux + onset density  (2 dims)
}

VISUAL_FACET_SLICES: Dict[str, Tuple[int, int]] = {
    "hue":    (0,  24),   # HSV histograms      (24 dims)
    "shape":  (24, 51),   # edge+orient+shape   (27 dims)
    "motion": (51, 57),   # motion+symmetry     (6 dims)
}

AUDIO_FACET_NAMES:  Tuple[str, ...] = ("tone", "timbre", "rhythm")
VISUAL_FACET_NAMES: Tuple[str, ...] = ("hue", "shape", "motion")

# Cross-modal pairings through the semantic middle plane
CROSS_MODAL_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("tone",   "hue"),
    ("timbre", "shape"),
    ("rhythm", "motion"),
)

LANE_LABEL: Dict[Tuple[str, str], str] = {
    ("tone",   "hue"):    "tonal_colour",
    ("timbre", "shape"):  "texture_form",
    ("rhythm", "motion"): "tempo_flow",
}

# =============================================================================
# ARCHETYPE SEEDS  — base primitives loaded on first boot when no saved state
# exists.  Gives Aurora a sensory vocabulary to cluster around immediately
# rather than growing from absolute zero.
#
# Each archetype name becomes the node_id prefix and the DPS concept key
# ("sensory:domain:facet:archetype_name").
# confidence is intentionally below all three promotion gates so seeds must
# earn their way up through real observations just like naturally grown nodes.
# =============================================================================

_FACET_NDIMS: Dict[str, int] = {
    "tone":   len(AUDIO_FACET_INDICES["tone"]),          # 13
    "timbre": len(AUDIO_FACET_INDICES["timbre"]),         # 5
    "rhythm": len(AUDIO_FACET_INDICES["rhythm"]),         # 2
    "hue":    VISUAL_FACET_SLICES["hue"][1]    - VISUAL_FACET_SLICES["hue"][0],    # 24
    "shape":  VISUAL_FACET_SLICES["shape"][1]  - VISUAL_FACET_SLICES["shape"][0],  # 27
    "motion": VISUAL_FACET_SLICES["motion"][1] - VISUAL_FACET_SLICES["motion"][0], # 6
}

_SENSORY_ARCHETYPES: Dict[str, Dict[str, float]] = {
    # Audio — Tone (harmonicity + chroma, 13 dims)
    "tone": {
        "harmonic_consonance": 0.40,   # stable, reinforcing intervals
        "dissonant_tension":   0.38,   # unstable intervals, pressure to resolve
        "tonal_center":        0.42,   # root / tonic anchor
        "chroma_motion":       0.35,   # movement through tonal space
        "modal_color":         0.33,   # quality of the scale / mode
    },
    # Audio — Timbre (RMS+ZCR+centroid+bw+rolloff, 5 dims)
    "timbre": {
        "bright_attack":   0.40,   # high centroid, sharp onset
        "warm_body":       0.42,   # low centroid, smooth envelope
        "rough_texture":   0.37,   # high ZCR+bandwidth, noisy
        "thin_sparse":     0.33,   # low RMS, narrow bandwidth
        "full_resonance":  0.38,   # high RMS, wide bandwidth
    },
    # Audio — Rhythm (flux + onset density, 2 dims)
    "rhythm": {
        "steady_pulse":      0.42,   # regular onset density, low flux
        "syncopated_burst":  0.38,   # irregular onset, high flux
        "sparse_onset":      0.35,   # low density, silence between events
        "dense_cascade":     0.37,   # high density, continuous onset
    },
    # Visual — Hue (HSV histograms, 24 dims)
    "hue": {
        "warm_dominant":     0.42,   # reds / oranges predominant
        "cool_dominant":     0.40,   # blues / greens predominant
        "neutral_achromatic":0.38,   # greys, low saturation throughout
        "vivid_saturated":   0.36,   # high saturation across hue range
        "muted_desaturated": 0.35,   # globally low saturation
    },
    # Visual — Shape (edge+orientation+shape proxy, 27 dims)
    "shape": {
        "sharp_angular":    0.40,   # strong edges, peaked orientation histogram
        "smooth_curved":    0.38,   # weak edges, diffuse orientation
        "symmetric_form":   0.42,   # bilateral symmetry signal present
        "complex_scatter":  0.35,   # high edge density, uniform orientation
        "enclosed_boundary":0.37,   # strong contour, low interior texture
    },
    # Visual — Motion (motion magnitude+symmetry, 6 dims)
    "motion": {
        "static_frame":      0.45,   # near-zero motion magnitude
        "uniform_flow":      0.40,   # consistent directional motion
        "turbulent_scatter": 0.37,   # high motion variance, chaotic
        "oscillating_rhythm":0.38,   # periodic / rhythmic motion
    },
}


def _seed_archetype_nodes(facet: "SensoryClusterFacet", facet_name: str) -> None:
    """Populate a freshly-loaded (empty) facet with archetype primitive nodes."""
    archetypes = _SENSORY_ARCHETYPES.get(facet_name, {})
    ndims = _FACET_NDIMS.get(facet_name, 4)
    for arch_name, init_conf in archetypes.items():
        node_id = f"arch_{facet_name}_{arch_name}"
        # Centroid: tiny uniform value — real observations will pull it via EMA
        centroid = [0.1] * ndims
        node = SensoryNode(
            node_id       = node_id,
            name          = arch_name.replace("_", " "),
            domain        = facet.domain,
            facet         = facet_name,
            centroid      = centroid,
            radius        = 0.05,
            usage_count   = 0,
            session_count = 0,
            confidence    = init_conf,
            stage         = "primitive",
            lineage_id    = "archetype",
            generation    = 0,
        )
        node.compute_fitness()
        facet._nodes[node_id] = node
    if archetypes and logger.isEnabledFor(logging.DEBUG):
        logger.debug("[SensoryCrystal] Seeded %d archetypes into %s/%s",
                     len(archetypes), facet.domain, facet_name)


# =============================================================================
# HELPERS
# =============================================================================

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def _ema(cur: float, val: float, alpha: float = EMA_ALPHA) -> float:
    return alpha * val + (1.0 - alpha) * cur

def _cosine_sim(a: List[float], b: List[float]) -> float:
    if HAS_NUMPY:
        av = np.array(a, dtype=np.float64)
        bv = np.array(b, dtype=np.float64)
        na = float(np.linalg.norm(av))
        nb = float(np.linalg.norm(bv))
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        return float(np.dot(av, bv) / (na * nb))
    dot = sum(ai * bi for ai, bi in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)

def _npmi(p_av: float, p_a: float, p_v: float) -> float:
    if p_av < 1e-12 or p_a < 1e-12 or p_v < 1e-12:
        return 0.0
    pmi   = math.log2(p_av / (p_a * p_v))
    denom = -math.log2(p_av)
    return max(-1.0, min(1.0, pmi / denom)) if abs(denom) > 1e-12 else 0.0

def _bucket_level(value: float) -> str:
    value = float(value)
    if value >= 0.80:
        return "high"
    if value >= 0.55:
        return "mid"
    if value >= 0.30:
        return "emergent"
    return "low"

def _bucket_count(value: int, strong: int, mature: int) -> str:
    value = int(value)
    if value >= mature:
        return "mature"
    if value >= strong:
        return "strong"
    if value > 0:
        return "early"
    return "none"

def _extract_audio_facet(features_20d: List[float], facet: str) -> List[float]:
    return [features_20d[i] if i < len(features_20d) else 0.0
            for i in AUDIO_FACET_INDICES.get(facet, [])]

def _extract_visual_facet(features_57d: List[float], facet: str) -> List[float]:
    s, e = VISUAL_FACET_SLICES.get(facet, (0, 0))
    return [features_57d[i] if i < len(features_57d) else 0.0
            for i in range(s, e)]


# =============================================================================
# LAYER-5 FEATURE ADAPTERS  — bridge from HardwareInterface data dicts to the
# 20d audio / 57d visual format the sensory crystal expects.
#
# Layer 5 produces 32d general dicts (brightness, volume, pitch, faces, etc.).
# These adapters map whatever is available and zero-fill the rest.
# When richer spectral analysis (librosa, cv2 histograms) is wired upstream,
# those paths are automatically populated via the "features" sub-dict.
# =============================================================================

def audio_dict_to_crystal_20d(audio_data: Dict[str, Any]) -> List[float]:
    """Adapt a Layer-5 audio data dict to the 20d sensory crystal audio vector.

    Crystal layout (matches AUDIO_FACET_INDICES):
      [0]    RMS / volume        — overall loudness
      [1]    ZCR / pitch         — zero-crossing rate proxy
      [2]    spectral_centroid   — timbral brightness
      [3]    spectral_bandwidth  — spectral spread
      [4]    spectral_rolloff    — high-energy cutoff
      [5]    spectral_flux       — rate of spectral change
      [6]    harmonicity         — derived from audio category label
      [7]    onset_density       — voice / transient presence
      [8:20] chroma[0..11]       — filled if upstream provides chroma array
    """
    feat    = audio_data.get("features") or {}
    cat     = str(audio_data.get("category") or "")
    harm_map = {"music": 0.80, "speech": 0.45, "singing": 0.75,
                "noise": 0.10, "alarm": 0.20, "silence": 0.0}
    def _pull(*keys: str, default: float = 0.0) -> float:
        for key in keys:
            if key in audio_data and audio_data.get(key) is not None:
                try:
                    return float(audio_data.get(key))
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:344",
                        exc=_aurora_boundary_exc,
                        context={"function": "_pull", "handler_line": 344, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                    )
                    pass
            if key in feat and feat.get(key) is not None:
                try:
                    return float(feat.get(key))
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:349",
                        exc=_aurora_boundary_exc,
                        context={"function": "_pull", "handler_line": 349, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                    )
                    pass
        return float(default)
    out     = [0.0] * 20
    out[0]  = _pull("volume", "rms")
    out[1]  = _pull("pitch", "zcr", "zero_crossing_rate")
    out[2]  = _pull("centroid", "spectral_centroid")
    out[3]  = _pull("bandwidth", "spectral_bandwidth")
    out[4]  = _pull("rolloff", "spectral_rolloff")
    out[5]  = _pull("flux", "spectral_flux")
    out[6]  = _pull("harmonicity", default=harm_map.get(cat, 0.55 if audio_data.get("voice_detected", False) else 0.30))
    out[7]  = _pull("onset_density", default=(1.0 if audio_data.get("voice_detected", False) else 0.0))
    chroma  = (audio_data.get("chroma")
               or feat.get("chroma")
               or feat.get("chroma_stft")
               or [])
    for ci, cv in enumerate(chroma[:12]):
        out[8 + ci] = _clamp01(float(cv))
    return out


def visual_dict_to_crystal_57d(visual_data: Dict[str, Any]) -> List[float]:
    """Adapt a Layer-5 visual data dict to the 57d sensory crystal visual vector.

    Crystal layout (matches VISUAL_FACET_SLICES):
      [0:24]  hue   — HSV histogram bins (filled if cv2 histogram present)
      [24:51] shape — edge density, orientation, shape/object features
      [51:57] motion — motion magnitude, face count, object count, symmetry
    """
    feat = visual_data.get("features") or {}
    out  = [0.0] * 57

    # Hue [0:24] — from HSV histogram if available (cv2 processing path)
    hsv_hist = feat.get("hsv_histogram") or feat.get("hue_histogram") or []
    for hi, hv in enumerate(hsv_hist[:24]):
        out[hi] = _clamp01(float(hv))

    # Shape [24:51]
    out[24] = _clamp01(float(visual_data.get("brightness", 0.0)))           # edge proxy
    out[25] = _clamp01(float(feat.get("edge_density",  feat.get("edges",  0.0))))
    out[26] = _clamp01(float(feat.get("orientation",   0.0)))
    out[27] = _clamp01(float(feat.get("symmetry_score", feat.get("symmetry", 0.0))))
    out[28] = _clamp01(min(1.0, len(visual_data.get("objects", [])) / 10.0))
    out[29] = _clamp01(float(feat.get("shape_complexity", 0.0)))
    # fill remaining shape dims from features dict if present
    shape_extra = feat.get("shape_features") or []
    for si, sv in enumerate(shape_extra[:21]):   # [30:51]
        out[30 + si] = _clamp01(float(sv))

    # Motion [51:57]
    out[51] = 1.0 if visual_data.get("motion_detected", False) else 0.0
    out[52] = _clamp01(min(1.0, len(visual_data.get("faces",   [])) / 3.0))
    out[53] = _clamp01(min(1.0, len(visual_data.get("objects", [])) / 10.0))
    out[54] = _clamp01(float(feat.get("motion_magnitude", feat.get("flow_magnitude",  0.0))))
    out[55] = _clamp01(float(feat.get("symmetry",          0.0)))
    out[56] = _clamp01(float(feat.get("depth_variation",   0.0)))

    return out

def _agb_save(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with gzip.open(str(path), "wb") as fh:
        fh.write(raw)

def _agb_load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with gzip.open(str(path), "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("[SensoryCrystal] Load failed %s: %s", path, exc)
        return None

# =============================================================================
# CRYSTAL NODE  —  lives on one facet, follows Aurora crystal promotion rules
# =============================================================================

@dataclass
class SensoryNode:
    """
    A learned concept node on one facet of the sensory crystal.

    Lifecycle mirrors Aurora's crystal level progression:
        primitive  ->  concept  ->  promoted

    - primitive: raw observation cluster, below promotion threshold
    - concept:   meets usage/session/confidence gates
    - promoted:  exceptional fitness + has at least one cross-modal link

    Dead nodes emit WisdomShard-compatible dicts (domain = "audio" or "vision").
    """
    node_id:       str
    domain:        str     # "audio" | "visual"
    facet:         str     # "tone"|"timbre"|"rhythm" | "hue"|"shape"|"motion"
    centroid:      List[float]
    name:          str   = ""
    radius:        float = 0.0

    usage_count:   int   = 0
    session_count: int   = 0
    confidence:    float = 0.0
    fitness:       float = 0.0

    stage:         str   = "primitive"   # primitive | concept | promoted
    lineage_id:    str   = ""
    generation:    int   = 0
    born_at:       float = field(default_factory=time.time)
    last_seen:     float = field(default_factory=time.time)
    maturity:      float = 0.0

    cross_modal_links: List[str] = field(default_factory=list)

    # Wisdom output on death
    wisdom_tone_bias:      float = 0.0
    wisdom_structure_bias: float = 0.0

    # Representational citizenship (Sunni & Cael, Build 654): set once, at
    # the concept->promoted transition, by
    # SensoryClusterFacet.grant_representational_citizenship(). None before
    # that -- a node's mere existence as a concept does not entitle it to
    # an address; independence (fitness + cross-modal grounding) does.
    representational_ref:  Optional[str] = None
    citizen_ability_id:    Optional[str] = None

    # Learned axis participation (Sunni & Cael, Build 656+ follow-up):
    # SENSORY_FACET_AXIS assigns a STARTING axis by facet category (a
    # design choice, stated as such at its own definition) -- this is the
    # representation establishing which axis it actually loads on, for
    # itself, from what she has actually encountered of it, one tick at a
    # time. Persisted (unlike _last_citizen_fitness below) because the
    # entire point is that it accumulates across sessions, not within one.
    axis_evidence:         Dict[str, float] = field(default_factory=dict)
    axis_evidence_samples: int = 0

    # Bookkeeping only, never persisted: the fitness value last reported to
    # genealogy via tick_citizen_participation(), so that method can tell
    # whether this node has done anything new since its last consequence
    # tick without re-reporting stale activity every cycle.
    _last_citizen_fitness: float = field(default=0.0, repr=False, compare=False)

    _last_session: str = field(default="", repr=False, compare=False)

    def update_centroid(self, obs: List[float]) -> None:
        rate = EMA_ALPHA * (DECAY_FLOOR + DECAY_CEILING * (1.0 - self.maturity))
        self.centroid = [_ema(c, o, rate) for c, o in zip(self.centroid, obs)]
        self.last_seen = time.time()

    def compute_fitness(self) -> float:
        f = (0.40 * self.confidence
           + 0.35 * _clamp01(self.usage_count   / USAGE_NORM_CAP)
           + 0.25 * _clamp01(self.session_count / SESSION_BREADTH_CAP))
        self.fitness = _clamp01(f)
        return self.fitness

    def is_promotable(self) -> bool:
        return (self.usage_count   >= CONCEPT_PROMOTION_USAGE
            and self.session_count >= CONCEPT_PROMOTION_SESSIONS
            and self.confidence    >= CONCEPT_PROMOTION_CONFIDENCE)

    def emit_wisdom(self) -> Dict[str, Any]:
        self.wisdom_tone_bias      = _clamp01((self.confidence - 0.5) * 2.0)
        self.wisdom_structure_bias = _clamp01((self.fitness    - 0.5) * 2.0)
        return {
            "tone_bias":        self.wisdom_tone_bias,
            "structure_bias":   self.wisdom_structure_bias,
            "fitness_at_death": self.fitness,
            "cause_of_death":   "cull",
            "domain":           self.domain,
            "lineage_key":      self.lineage_id,
            "generation":       self.generation,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()
                if not k.startswith("_")} | {"_last_session": self._last_session}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SensoryNode":
        node = cls(
            node_id       = d["node_id"],
            name          = d.get("name", ""),
            domain        = d["domain"],
            facet         = d["facet"],
            centroid      = d["centroid"],
            radius        = d.get("radius",        0.0),
            usage_count   = d.get("usage_count",   0),
            session_count = d.get("session_count", 0),
            confidence    = d.get("confidence",    0.0),
            fitness       = d.get("fitness",       0.0),
            stage         = d.get("stage",         "primitive"),
            lineage_id    = d.get("lineage_id",    ""),
            generation    = d.get("generation",    0),
            born_at       = d.get("born_at",       time.time()),
            last_seen     = d.get("last_seen",     time.time()),
            maturity      = d.get("maturity",      0.0),
            cross_modal_links         = d.get("cross_modal_links",         []),
            wisdom_tone_bias          = d.get("wisdom_tone_bias",          0.0),
            wisdom_structure_bias     = d.get("wisdom_structure_bias",     0.0),
            representational_ref      = d.get("representational_ref",     None),
            citizen_ability_id        = d.get("citizen_ability_id",       None),
            axis_evidence             = dict(d.get("axis_evidence", {}) or {}),
            axis_evidence_samples     = d.get("axis_evidence_samples",   0),
        )
        node._last_session = d.get("_last_session", "")
        return node

# =============================================================================
# CRYSTAL FACET  —  one face of the bipyramid
# =============================================================================

class SensoryClusterFacet:
    """
    One face of the sensory crystal.  Manages a population of SensoryNodes
    for a single dimension (tone, timbre, rhythm, hue, shape, or motion).

    N-axis gate:  sensory.intake    — signal enters the crystal
    B-axis gate:  sensory.cluster   — observations cluster into nodes
    A-axis gate:  sensory.promote   — primitive → concept selection
    T-axis gate:  sensory.distill   — mature nodes distill (maturity >= 0.80)
    """

    def __init__(self, domain: str, facet: str,
                 concept_floor: int = 8,
                 candidate_cap: int = DEFAULT_CANDIDATE_CAP) -> None:
        self.domain        = domain
        self.facet         = facet
        self.concept_floor = concept_floor
        self.candidate_cap = candidate_cap

        self._nodes:          Dict[str, SensoryNode] = {}
        self._total_obs:      int   = 0
        self._novelty_window: List[int] = []
        self._novelty_rate:   float = 1.0
        self._stability:      float = 0.0
        self._maturity:       float = 0.0
        self._pending_wisdom: List[Dict[str, Any]] = []
        # Called when a node advances to "promoted" — set by AuroraSensoryCrystal
        # to inject promoted concepts into the DPS quasi-crystal ladder.
        self.promotion_hook: Optional[Any] = None
        # Sunni & Cael (Build 654 fix): tick_advanced_promotion() below reads
        # self._evolution_hook unconditionally -- this was never initialized
        # here, so any facet driven straight from AuroraSensoryCrystal.boot()
        # (never routed through register_evolution_hook, which set the
        # attribute only on the crystal object, never on child facets) raised
        # AttributeError the moment a node actually reached the promotion
        # gate. Confirmed via direct reproduction, not just code reading.
        self._evolution_hook: Optional[Callable[[Dict[str, Any]], None]] = None
        # Genealogy reference for representational citizenship (Build 654):
        # set by AuroraSensoryCrystal.register_genealogy(), mirroring
        # promotion_hook/_evolution_hook's per-facet wiring pattern.
        self._genealogy_ref: Optional[Any] = None

    # B-axis: sensory.cluster
    def observe(self, vec: List[float], session_id: str,
                confidence_hint: float = 0.5) -> Optional[str]:
        """
        Ingest one feature vector slice.  Find/create nearest SensoryNode.
        Returns matched node_id or None.

        Operation: sensory.intake (N) -> sensory.cluster (B)
        """
        if not any(v != 0.0 for v in vec):
            return None
        self._total_obs += 1
        new_concept = False

        node = self._nearest(vec)
        sim = _cosine_sim(node.centroid, vec) if node is not None else 0.0
        threshold = SIMILARITY_MATCH_THRESHOLD
        if node is not None and str(getattr(node, "lineage_id", "") or "") == "archetype":
            threshold = min(SIMILARITY_MATCH_THRESHOLD, ARCHETYPE_MATCH_THRESHOLD)
        if node is not None and sim >= threshold:
            node.update_centroid(vec)
            node.usage_count += 1
            if session_id and session_id != node._last_session:
                node.session_count += 1
                node._last_session  = session_id
            node.confidence = _ema(node.confidence, confidence_hint)
            node.compute_fitness()
            return node.node_id

        if len(self._nodes) < self.candidate_cap:
            nid  = str(uuid.uuid4())
            node = SensoryNode(
                node_id    = nid,
                domain     = self.domain,
                facet      = self.facet,
                centroid   = vec[:],
                lineage_id = str(uuid.uuid4()),
            )
            node._last_session = session_id
            node.usage_count   = 1
            node.session_count = 1
            node.confidence    = confidence_hint
            node.compute_fitness()
            self._nodes[nid] = node
            new_concept = True
            self._novelty_window.append(1)
            return nid

        return None

    def _nearest(self, vec: List[float]) -> Optional[SensoryNode]:
        best, best_sim = None, -1.0
        for n in self._nodes.values():
            s = _cosine_sim(n.centroid, vec)
            if s > best_sim:
                best_sim, best = s, n
        return best

    # A-axis: sensory.promote
    def tick_promotion(self) -> List[str]:
        """primitive -> concept for nodes meeting gates.  Operation: sensory.promote (A)"""
        out = []
        for node in self._nodes.values():
            if node.stage == "primitive" and node.is_promotable():
                node.stage       = "concept"
                node.generation += 1
                out.append(node.node_id)
                logger.debug("[SensoryCrystal/%s/%s] primitive->concept %s  "
                             "usage=%d sess=%d conf=%.2f",
                             self.domain, self.facet, node.node_id[:8],
                             node.usage_count, node.session_count, node.confidence)
        return out

    def tick_advanced_promotion(self) -> List[str]:
        """concept -> promoted for high-fitness nodes with cross-modal links."""
        out = []
        for node in self._nodes.values():
            if (node.stage == "concept"
                    and node.fitness             >= 0.72
                    and node.usage_count         >= CONCEPT_PROMOTION_USAGE * 2
                    and node.cross_modal_links):
                node.stage       = "promoted"
                node.generation += 1
                out.append(node.node_id)
                logger.debug("[SensoryCrystal/%s/%s] concept->promoted %s  fitness=%.2f",
                             self.domain, self.facet, node.node_id[:8], node.fitness)
                # Append to sensory telemetry log for evolution pipeline and hub
                try:
                    import json as _json, time as _time
                    _tlog = Path(__file__).parent.parent / "aurora_state" / "sensory_telemetry.jsonl"
                    _tlog.parent.mkdir(parents=True, exist_ok=True)
                    _entry = {
                        "ts":        _time.time(),
                        "event":     "node_promoted",
                        "domain":    self.domain,
                        "facet":     self.facet,
                        "node_id":   node.node_id[:12],
                        "fitness":   round(node.fitness, 3),
                        "usage":     node.usage_count,
                        "generation": node.generation,
                        "links":     len(node.cross_modal_links),
                    }
                    with open(str(_tlog), "a") as _fh:
                        _fh.write(_json.dumps(_entry) + "\n")
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:667",
                        exc=_aurora_boundary_exc,
                        context={"function": "tick_advanced_promotion", "handler_line": 667, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                    )
                    pass
                # Inject into DPS crystal order ladder (BASE→COMPOSITE→FULL→QUASI)
                if self.promotion_hook is not None:
                    try:
                        self.promotion_hook(self.domain, self.facet, node)
                    except Exception as _ph_e:
                        _aurora_record_exception_from_locals(
                            locals(),
                            module=__name__,
                            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:673",
                            exc=_ph_e,
                            context={"function": "tick_advanced_promotion", "handler_line": 673, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                        )
                        logger.debug("[SensoryCrystal] promotion_hook error: %s", _ph_e)
                if self._evolution_hook is not None:
                    try:
                        axis = _facet_axis(self.domain, self.facet)
                        drive_value = _clamp01(node.fitness)
                        # Sunni & Cael (Multimodal Representational Autonomy):
                        # preserve the fields the evolutionary consumer needs
                        # to attribute this pressure back to the exact
                        # sensory representation that produced it -- stage
                        # and session breadth were previously dropped here,
                        # even though the node already carries them.
                        evidence = {
                            "ts": _time.time(),
                            "event": "sensory_promotion",
                            "domain": self.domain,
                            "facet": self.facet,
                            "node_id": node.node_id,
                            "modality": self.domain,
                            "stage": node.stage,
                            "mutation_name": f"sensory.{self.domain}.{self.facet}",
                            "spacing": axis,
                            "constraint_axes": {axis: drive_value},
                            "pressure_profile": {
                                "total_confidence": round(node.fitness, 3),
                                "links": len(node.cross_modal_links),
                            },
                            "pressure_after": {axis: drive_value},
                            "axis_drive": {axis: drive_value},
                            "notes": {
                                "confidence": round(node.fitness, 3),
                                "fitness": round(node.fitness, 3),
                                "usage": node.usage_count,
                                "session_count": node.session_count,
                                "maturity": round(node.maturity, 3),
                                "cross_modal_links": list(node.cross_modal_links[:8]),
                            },
                        }
                        self._evolution_hook(evidence)
                    except Exception as _ev_e:
                        _aurora_record_exception_from_locals(
                            locals(),
                            module=__name__,
                            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:704",
                            exc=_ev_e,
                            context={"function": "tick_advanced_promotion", "handler_line": 704, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                        )
                        logger.debug("[SensoryCrystal] evolution_hook error: %s", _ev_e)
                # Sunni & Cael (Build 654): promotion crossing this gate is
                # exactly the independence threshold the citizenship model
                # names -- fitness high enough, usage deep enough, and a
                # cross-modal link already earned. Grant the node its own
                # address and durable genealogy identity here, alongside
                # (not instead of) the evolutionary-pressure evidence above,
                # which remains the chamber's own separate concern.
                if self._genealogy_ref is not None:
                    try:
                        self.grant_representational_citizenship(node)
                    except Exception as _cit_e:
                        _aurora_record_exception_from_locals(
                            locals(),
                            module=__name__,
                            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:grant_citizenship",
                            exc=_cit_e,
                            context={"function": "tick_advanced_promotion", "handler_line": 846, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                        )
                        logger.debug("[SensoryCrystal] citizenship grant error: %s", _cit_e)
        return out

    # ------------------------------------------------------------------
    # Representational citizenship (Sunni & Cael, Build 654)
    # ------------------------------------------------------------------
    def grant_representational_citizenship(self, node: "SensoryNode") -> Optional[str]:
        """Give a promoted sensory representation the four capabilities
        that make it a citizen of the genealogy/Difference/inquiry/RCRW/
        evolution economy, rather than raw material that only ever feeds
        someone else's promotion:

          1. Self-addressability  -- a RepresentationalRef of its own.
          2. Durable, re-derivable genealogy identity -- a stable
             AbilityProfile id (sensory_citizen_ability_id), not the
             one-shot time-hashed id register_code_evolution_outcome()
             produces for dream/code evidence.
          3. Ancestral/modal grounding, honestly tagged -- "sensory_
             representation", never "code_evolution": nothing about this
             ability's provenance is disguised.
          4. Eligibility to interact with other representations --
             registering it directly into genealogy.abilities makes it
             reachable by every OTHER active item's
             representation_collision_candidates()/representation_gap_
             candidates() search (both scan the full abilities/links
             registry, seeded only by the caller's own active items --
             confirmed by reading _representation_index()).

        Idempotent: a node that already has a citizen_ability_id is
        returned unchanged. Does not touch the pre-existing evolution-hook
        evidence path (self._evolution_hook) -- that remains the chamber's
        separate pressure-pulse mechanism; this is genealogy identity.
        """
        if node.citizen_ability_id and node.citizen_ability_id in getattr(self._genealogy_ref, "abilities", {}):
            return node.citizen_ability_id

        genealogy = self._genealogy_ref
        if genealogy is None:
            return None

        ref = sensory_representational_ref(self.domain, self.facet)
        aid = sensory_citizen_ability_id(self.domain, self.facet, node.node_id)

        if aid not in genealogy.abilities:
            from aurora_internal.constraint_genealogy import AbilityProfile
            axis = _facet_axis(self.domain, self.facet)
            genealogy.abilities[aid] = AbilityProfile(
                id=aid,
                axis=axis,
                # Sunni & Cael, "Autonomous Development Integrity" pass,
                # blocker 5: this is the ability's actual birth moment --
                # this construction doesn't route through
                # _augment_ability_profile_with_origin, so origin_axis must
                # be stamped explicitly here or it would default to None
                # and only get backfilled (incorrectly, from whatever .axis
                # happens to be by then) the first time something ELSE
                # calls that function on it. The existing "initial_axis:"
                # effect_tag below records the same fact informally; this
                # is the structural, typed version of it.
                origin_axis=axis,
                requires=(axis,),
                cost=_axis_weighted_cost(axis),
                risk={a: 0.0 for a in ("X", "T", "N", "B", "A")},
                structured_state=_sensory_structured_state(node),
                effect_tags=(
                    "sensory_representation",
                    f"sensory_domain:{self.domain}",
                    f"sensory_facet:{self.facet}",
                    f"sensory_node_id:{node.node_id}",
                    f"sensory_modality:{self.domain}",
                    f"representational_ref:{ref.encode()}",
                    f"sensory_fitness:{node.fitness:.3f}",
                    # The category-level starting prior, permanently
                    # recorded for the audit trail -- kept even if a later
                    # learned_axis: tag (tick_citizen_participation) moves
                    # the ability's own live .axis field elsewhere.
                    f"initial_axis:{axis}",
                ),
                notes=(
                    f"Sensory representation: domain={self.domain} facet={self.facet} "
                    f"node_id={node.node_id} fitness={node.fitness:.3f} "
                    f"cross_modal_links={len(node.cross_modal_links)}. "
                    "Not a code mutation -- this ability's origin is a promoted "
                    "perceptual concept, and its tags say so."
                ),
            )

        node.representational_ref = ref.encode()
        node.citizen_ability_id = aid
        node._last_citizen_fitness = node.fitness
        return aid

    def migrate_legacy_citizens(self) -> int:
        """Backfill citizenship for nodes promoted before this facet ever
        had a genealogy reference (Sunni & Cael, Build 656 follow-up):
        register_genealogy() only wires the reference -- a node promoted in
        an earlier session, loaded back from persisted state with
        stage="promoted" and citizen_ability_id=None, would otherwise stay
        permanently stranded, since tick_advanced_promotion() (the only
        other call site for grant_representational_citizenship) never
        fires again for a node that already reached "promoted". Confirmed
        against this build's own shipped sensory state, not hypothetical:
        loading it and calling register_genealogy() alone left every
        already-promoted node at citizen_ability_id=None with zero sensory
        citizen abilities registered. Idempotent -- grant_representational_
        citizenship() already skips nodes that already have a citizen id.
        Returns the number of nodes migrated this call."""
        if self._genealogy_ref is None:
            return 0
        migrated = 0
        for node in self._nodes.values():
            if node.stage == "promoted" and not node.citizen_ability_id:
                if self.grant_representational_citizenship(node) is not None:
                    migrated += 1
        return migrated

    def tick_citizen_participation(self) -> int:
        """Ongoing consequence-observation for already-promoted citizens
        (Sunni & Cael, Build 654): without this, a promoted node's genealogy
        ability is registered once and then never touched again -- reachable
        as a passive counterpart when something ELSE searches, but never an
        active seed that can trigger a collision/gap search itself, and
        never visible to PairStats/RCRW co-activation. Called once per
        AuroraSensoryCrystal.end_session() (bounded: at most one genealogy
        observation per promoted node per session, not per raw sample).

        Only reports nodes whose fitness has genuinely moved since their
        last citizen tick -- an idle promoted node produces no consequence
        and is not re-reported merely because a session ended.

        Returns the number of nodes reported this tick.
        """
        if self._genealogy_ref is None:
            return 0
        import dataclasses
        from aurora_internal.constraint_genealogy import AbilityProfile, PressureVec, TraceItem
        reported = 0
        for node in self._nodes.values():
            if node.stage != "promoted" or not node.citizen_ability_id:
                continue
            delta = node.fitness - node._last_citizen_fitness
            if abs(delta) < 1e-6:
                continue
            existing = self._genealogy_ref.abilities.get(node.citizen_ability_id)
            # The axis pressure is logged against is the representation's
            # CURRENT axis -- its own learned axis if evidence has already
            # earned one (see _update_axis_evidence below), the facet-level
            # starting prior otherwise. Never silently recomputed from the
            # facet alone once she has evidence of her own about it.
            axis = existing.axis if existing is not None else _facet_axis(self.domain, self.facet)
            # Sunni & Cael: this pressure is SYNTHETIC, derived from the
            # node's own self-assessed fitness metric, not from a measured
            # world/environment outcome -- unresolved confidence is the
            # "before" pressure on this node's axis; relief is however much
            # fitness improved this tick. A fitness regression (delta < 0)
            # is expressed as pressure rising instead of falling -- never
            # clamped away or hidden. Legitimate for what it always fed
            # (relief-event bookkeeping, PairStats/RCRW co-activation, the
            # axis_evidence developmental-proxy learner below), but it must
            # NOT be credited to consequence_profile as if it were a
            # measured world consequence -- that would let a representation
            # improve its own confidence score by improving its own
            # confidence score. See the "synthetic_self_assessment" notes
            # flag on the observe() call below.
            before_val = _clamp01(1.0 - node._last_citizen_fitness)
            after_val = _clamp01(1.0 - node.fitness)
            p_before = PressureVec(**{a: (before_val if a == axis else 0.0) for a in _AXES5})
            p_after = PressureVec(**{a: (after_val if a == axis else 0.0) for a in _AXES5})
            # Sunni & Cael (Build 656 follow-up): the ability created by
            # grant_representational_citizenship() carried a snapshot of the
            # node's state at the MOMENT of promotion -- fitness, usage,
            # cross_modal_links -- and, being a frozen dataclass, never
            # changed again even as the live node kept learning. That was
            # confirmed directly: raise a node's fitness after citizenship,
            # run this method, and the ability's own fields were unchanged.
            # Replace it here with the node's CURRENT state (centroid,
            # fitness, usage_count, session_count, cross_modal_links,
            # maturity) every time it has genuinely moved, so a later
            # lookup of genealogy.abilities[citizen_ability_id] sees the
            # representation as it is now, not as it was at birth.
            live_state = _sensory_structured_state(node)
            # Sunni & Cael (Build 656+ follow-up, "the mechanism to
            # establish that herself as she encounters them"): fold this
            # tick's own state into the node's running axis-evidence EMA.
            # A representation whose actually-encountered history clearly
            # favors a different axis than SENSORY_FACET_AXIS's category
            # prior earns a reassignment for ITSELF -- other nodes on the
            # same facet are untouched and may end up differently, or not
            # at all, depending on their OWN evidence.
            learned_axis = _update_axis_evidence(node)
            new_axis = learned_axis if (learned_axis is not None and learned_axis != axis) else axis
            starting_prior = _facet_axis(self.domain, self.facet)
            if existing is not None:
                refreshed_tags = tuple(
                    t for t in existing.effect_tags
                    if not t.startswith("sensory_fitness:") and not t.startswith("learned_axis:")
                ) + (f"sensory_fitness:{live_state['fitness']:.3f}",)
                if new_axis != starting_prior:
                    # Sticky, not just this-tick: the tag reflects "does the
                    # CURRENT axis differ from the original category prior",
                    # not "did it change on THIS tick" -- otherwise it would
                    # vanish again the moment a later tick reconfirms the
                    # same already-learned axis instead of moving further.
                    refreshed_tags = refreshed_tags + (f"learned_axis:{new_axis}",)
                if new_axis != axis:
                    logger.info(
                        "[SensoryCrystal/%s/%s] %s: axis %s->%s (own encountered evidence, %d samples)",
                        self.domain, self.facet, node.node_id[:8], axis, new_axis,
                        node.axis_evidence_samples,
                    )
                self._genealogy_ref.abilities[node.citizen_ability_id] = dataclasses.replace(
                    existing,
                    axis=new_axis,
                    requires=(new_axis,),
                    cost=_axis_weighted_cost(new_axis),
                    effect_tags=refreshed_tags,
                    structured_state=_sensory_structured_state(node),
                    notes=(
                        f"Sensory representation: domain={self.domain} facet={self.facet} "
                        f"node_id={node.node_id} fitness={live_state['fitness']:.3f} "
                        f"usage={live_state['usage_count']} session={live_state['session_count']} "
                        f"cross_modal_links={len(live_state['cross_modal_links'])} "
                        f"maturity={live_state['maturity']:.3f}. "
                        "Not a code mutation -- this ability's origin is a promoted "
                        "perceptual concept, and its tags say so."
                    ),
                )
                # Sunni & Cael: this ability was just replaced in place --
                # the entry count genealogy's relevance-index cache stamps
                # against didn't change, so without this the cache would
                # keep the representation filed under its stale collision
                # signature. Confirmed by direct reproduction: a citizen
                # earns axis B, representation_record() correctly reports
                # B, but the relevance index still had it under axis:T and
                # was absent from axis:B until this call was added.
                if hasattr(self._genealogy_ref, "mark_representation_index_dirty"):
                    self._genealogy_ref.mark_representation_index_dirty()
            try:
                self._genealogy_ref.observe(
                    pressure_before=p_before,
                    trace=[TraceItem(kind="ABILITY", id=node.citizen_ability_id)],
                    pressure_after=p_after,
                    notes={
                        "source": "sensory_citizen_participation",
                        "domain": self.domain,
                        "facet": self.facet,
                        "node_id": node.node_id,
                        "fitness_delta": round(delta, 4),
                        "live_state": live_state,
                        "axis_evidence": dict(node.axis_evidence),
                        # Sunni & Cael: this tick's pressure is derived from
                        # the node's OWN fitness self-assessment, not a
                        # measured world outcome -- _attribute_consequence()
                        # must not credit it to consequence_profile as if
                        # Aurora's physics had actually changed. Everything
                        # ELSE this observation feeds (relief bookkeeping,
                        # PairStats, the axis_evidence proxy learner) is
                        # unaffected; this flag is read by exactly one
                        # place.
                        "synthetic_self_assessment": True,
                    },
                )
                node._last_citizen_fitness = node.fitness
                reported += 1
            except Exception as _tick_e:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:tick_citizen_participation",
                    exc=_tick_e,
                    context={"function": "tick_citizen_participation", "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                )
                logger.debug("[SensoryCrystal] citizen participation tick error: %s", _tick_e)
        return reported

    # Maturity
    def compute_maturity(self) -> float:
        if not self._nodes:
            self._maturity = 0.0
            return 0.0
        window   = self._novelty_window[-50:] or [1]
        nov_rate = _clamp01(sum(window) / max(1, len(window)))
        promoted = [n for n in self._nodes.values() if n.stage != "primitive"]
        stab     = (_clamp01(sum(n.confidence for n in promoted) / len(promoted))
                    if promoted else 0.0)
        compr    = _clamp01(len(promoted) / max(1, len(self._nodes)))
        self._novelty_rate = _ema(self._novelty_rate, nov_rate)
        self._stability    = _ema(self._stability,    stab)
        m = _clamp01(WEIGHT_STABILITY * self._stability
                   + WEIGHT_NOVELTY   * (1.0 - self._novelty_rate)
                   + WEIGHT_COMPRESSION * compr)
        self._maturity = m
        for n in self._nodes.values():
            n.maturity = m
        return m

    @property
    def maturity(self) -> float:
        return self._maturity

    @property
    def ready_for_distillation(self) -> bool:
        return self._maturity >= DISTILLATION_MATURITY_GATE

    # Culling
    def cull(self, wisdom_out: List[Dict[str, Any]]) -> None:
        if len(self._nodes) <= self.concept_floor:
            return
        victims = sorted(
            [n for n in self._nodes.values() if n.stage == "primitive"],
            key=lambda n: n.fitness
        )[: max(0, len(self._nodes) - self.candidate_cap)]
        for n in victims:
            wisdom_out.append(n.emit_wisdom())
            del self._nodes[n.node_id]

    def add_cross_modal_link(self, node_id: str, peer_id: str) -> bool:
        n = self._nodes.get(node_id)
        if n and peer_id not in n.cross_modal_links:
            n.cross_modal_links.append(peer_id)
            return True
        return False

    def end_session(self, wisdom_out: List[Dict[str, Any]]) -> None:
        """Operation: sensory.end_session (T, B, A)"""
        self._novelty_window.append(0)
        self.compute_maturity()
        self.tick_promotion()
        self.tick_advanced_promotion()
        self.cull(wisdom_out)

    def get_promoted(self) -> List[SensoryNode]:
        return [n for n in self._nodes.values() if n.stage in ("concept", "promoted")]

    def get_node(self, node_id: str) -> Optional[SensoryNode]:
        return self._nodes.get(node_id)

    def save(self, base: Path) -> None:
        """Operation: sensory.distill (T) — persistence after session."""
        payload = {
            "domain": self.domain, "facet": self.facet,
            "total_obs": self._total_obs, "novelty_rate": self._novelty_rate,
            "stability": self._stability, "maturity": self._maturity,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
        }
        _agb_save(base / "state.agb", payload)

    def load(self, base: Path) -> bool:
        d = _agb_load(base / "state.agb")
        if d is None:
            return False
        self._total_obs     = d.get("total_obs",    0)
        self._novelty_rate  = d.get("novelty_rate", 1.0)
        self._stability     = d.get("stability",    0.0)
        self._maturity      = d.get("maturity",     0.0)
        self._nodes = {nid: SensoryNode.from_dict(nd)
                       for nid, nd in d.get("nodes", {}).items()}
        logger.info("[SensoryCrystal/%s/%s] Loaded %d nodes maturity=%.2f",
                    self.domain, self.facet, len(self._nodes), self._maturity)
        return True

# =============================================================================
# SEMANTIC NODE  —  lives in the middle plane
# =============================================================================

@dataclass
class SemanticCrystalNode:
    """
    A cross-modal meaning node in the semantic middle plane.

    Born when a promoted audio node and a promoted visual node
    co-occur >= CROSS_MODAL_MIN_COOCCURRENCE times with nPMI >= threshold.

    Lifecycle:  candidate  ->  concept  ->  promoted

    On promotion writes cross-modal links back into both SensoryClusterFacets,
    completing the bipyramid geometry.

    Operation: sensory.cross_modal_link (N×A = "force")
    """
    node_id:        str
    lane:           str   # "tonal_colour" | "texture_form" | "tempo_flow"
    audio_facet:    str
    visual_facet:   str
    audio_node_id:  str
    visual_node_id: str

    co_occurrence_count: int   = 0
    npmi:                float = 0.0
    confidence:          float = 0.0
    fitness:             float = 0.0
    stage:               str   = "candidate"

    lineage_id:  str   = ""
    generation:  int   = 0
    born_at:     float = field(default_factory=time.time)
    last_seen:   float = field(default_factory=time.time)
    maturity:    float = 0.0

    wisdom_tone_bias:      float = 0.0
    wisdom_structure_bias: float = 0.0

    def compute_fitness(self) -> float:
        coo  = _clamp01(self.co_occurrence_count / (CROSS_MODAL_MIN_COOCCURRENCE * 5))
        npmi = _clamp01((self.npmi + 1.0) / 2.0)
        self.fitness = _clamp01(0.45 * self.confidence + 0.35 * coo + 0.20 * npmi)
        return self.fitness

    def is_promotable_concept(self) -> bool:
        return (self.co_occurrence_count >= CROSS_MODAL_MIN_COOCCURRENCE
            and self.npmi               >= CROSS_MODAL_MIN_NPMI)

    def is_promotable_promoted(self) -> bool:
        return self.stage == "concept" and self.fitness >= SEMANTIC_PROMOTION_FITNESS

    def emit_wisdom(self) -> Dict[str, Any]:
        self.wisdom_tone_bias      = _clamp01((self.confidence - 0.5) * 2.0)
        self.wisdom_structure_bias = _clamp01((self.fitness    - 0.5) * 2.0)
        return {
            "tone_bias": self.wisdom_tone_bias,
            "structure_bias": self.wisdom_structure_bias,
            "fitness_at_death": self.fitness, "cause_of_death": "cull",
            "domain": "multimodal", "lineage_key": self.lineage_id,
            "generation": self.generation,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticCrystalNode":
        data = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        # Legacy-state resilience (FIX-A007): pre-facet seed/state schemas carry
        # only `lane`. Derive audio_facet/visual_facet from the canonical
        # CROSS_MODAL_PAIRS lane mapping so restore never hard-fails and the
        # 6-facet crystal always boots.
        if "audio_facet" not in data or "visual_facet" not in data:
            lane = str(data.get("lane", "") or "")
            for (a_facet, v_facet), label in LANE_LABEL.items():
                if label == lane:
                    data.setdefault("audio_facet", a_facet)
                    data.setdefault("visual_facet", v_facet)
                    break
            else:
                data.setdefault("audio_facet", "")
                data.setdefault("visual_facet", "")
        return cls(**data)

# =============================================================================
# AURORA SENSORY CRYSTAL  —  full 6-facet assembly
# =============================================================================

class AuroraSensoryCrystal:
    """
    Full 6-facet sensory competency crystal for Aurora.

    Assembles AudioFacets (tone/timbre/rhythm) + VisualFacets (hue/shape/motion)
    + semantic middle plane (SemanticCrystalNode lattice).

    Wire into Aurora runtime:

        # At boot (after boot_aurora):
        from aurora_internal.aurora_sensory_crystal import (
            AuroraSensoryCrystal, ensure_sensory_crystal_lineage
        )
        ensure_sensory_crystal_lineage(systems)          # seed abilities
        crystal = AuroraSensoryCrystal(state_dir="/path/to/aurora_strata/aurora_state")
        crystal.boot()
        systems["sensory_crystal"] = crystal

        # During interaction (in process_audio_prosody / process_visual_grounding):
        crystal.start_session(session_id)
        crystal.observe_frame(audio_20d, vision_57d, session_id)

        # At consolidation (dismiss / consolidation_stage):
        wisdom = crystal.end_session()
        for shard in wisdom:
            wisdom_store.add_shard(WisdomShard(..., **shard))
    """

    def __init__(self, state_dir: str = _STATE_ROOT) -> None:
        self._base = Path(state_dir) / "sensory_crystal"
        self._session_id = ""

        # Audio facets (bottom of crystal)
        self._audio: Dict[str, SensoryClusterFacet] = {
            name: SensoryClusterFacet("audio", name, concept_floor=AUDIO_CONCEPT_FLOOR)
            for name in AUDIO_FACET_NAMES
        }
        # Visual facets (top of crystal)
        self._visual: Dict[str, SensoryClusterFacet] = {
            name: SensoryClusterFacet("visual", name, concept_floor=VISUAL_CONCEPT_FLOOR)
            for name in VISUAL_FACET_NAMES
        }
        # Semantic middle plane
        self._semantic:        Dict[str, SemanticCrystalNode] = {}
        self._cooccur:         Dict[str, int]  = {}
        self._audio_marginal:  Dict[str, int]  = {}
        self._visual_marginal: Dict[str, int]  = {}
        self._total_frames:    int             = 0
        self._last_matches:    Dict[str, Dict[str, Optional[str]]] = {
            "audio": {},
            "visual": {},
            "semantic": {},
        }
        self._last_recognitions: List[str] = []

        self._novelty_window: List[int] = []
        self._maturity:       float     = 0.0
        # DPS reference — set via wire_dimensional() after boot_aurora().
        # When set, promoted nodes are injected into the DPS Crystal order
        # ladder (BASE → COMPOSITE → FULL_CONCEPT → QUASI).
        self._dps_ref: Optional[Any] = None
        self._evolution_hook: Optional[Callable[[Dict[str, Any]], None]] = None
        # Genealogy reference (Build 654) — set via register_genealogy(),
        # propagated to every child facet so grant_representational_
        # citizenship()/tick_citizen_participation() can reach it.
        self._genealogy_ref: Optional[Any] = None

    # ------------------------------------------------------------------
    # Boot  —  Operation: sensory.crystal_boot (X, T)
    # ------------------------------------------------------------------

    def boot(self) -> None:
        """Load persisted state. Safe on first boot (zero knowledge)."""
        for name, facet in self._audio.items():
            facet.load(self._base / "audio" / name)
            if not facet._nodes:
                _seed_archetype_nodes(facet, name)
        for name, facet in self._visual.items():
            facet.load(self._base / "visual" / name)
            if not facet._nodes:
                _seed_archetype_nodes(facet, name)
        sem_d = _agb_load(self._base / "semantic" / "state.agb")
        if sem_d:
            self._semantic       = {nid: SemanticCrystalNode.from_dict(d)
                                    for nid, d in sem_d.get("semantic", {}).items()}
            self._cooccur        = sem_d.get("cooccur",        {})
            self._audio_marginal  = sem_d.get("audio_marginal",  {})
            self._visual_marginal = sem_d.get("visual_marginal", {})
            self._total_frames   = sem_d.get("total_frames",   0)
            self._maturity       = sem_d.get("maturity",       0.0)
        logger.info("[SensoryCrystal] Booted  audio=%s  visual=%s  semantic=%d",
                    {n: len(f._nodes) for n, f in self._audio.items()},
                    {n: len(f._nodes) for n, f in self._visual.items()},
                    len(self._semantic))

    def start_session(self, session_id: str) -> None:
        self._session_id = session_id

    def _describe_node(self, node: Optional[SensoryNode], facet_name: str) -> str:
        if node is None:
            return ""
        node_name = str(getattr(node, "name", "") or "").strip()
        if node_name:
            return node_name.replace("_", " ")
        node_id = str(node.node_id or "")
        if str(node.lineage_id or "") == "archetype" and node_id.startswith(f"arch_{facet_name}_"):
            return node_id[len(f"arch_{facet_name}_"):].replace("_", " ")
        if node.stage in {"concept", "promoted"}:
            return f"{facet_name} {node.stage}"
        return facet_name

    # ------------------------------------------------------------------
    # DPS quasi-crystal bridge  —  promoted nodes → CrystalOrder ladder
    # ------------------------------------------------------------------

    def wire_dimensional(self, dps: Any) -> None:
        """
        Connect this crystal to Aurora's DimensionalProcessingSystem (DPS).

        Once wired, every sensory node that advances to "promoted" state will
        also be injected into the DPS Crystal order ladder:
            BASE → COMPOSITE → FULL_CONCEPT → QUASI

        The DPS crystal key is:
            "sensory:{domain}:{facet}:{node_id}"
        so each promoted sensory node gets its own evolving DPS crystal that
        climbs the quasi-crystal ladder as observations reinforce it.

        Call this from aurora.py after boot:
            if systems.get("sensory_crystal") and systems.get("dimensional"):
                dps = getattr(systems["dimensional"], "dps", None)
                if dps:
                    systems["sensory_crystal"].wire_dimensional(dps)
        """
        self._dps_ref = dps
        for domain, facets in (("audio", self._audio), ("visual", self._visual)):
            for facet_name, facet in facets.items():
                # Closure captures domain and facet_name correctly
                def _make_hook(d: str, fn: str) -> Any:
                    def _hook(dom: str, fac: str, node: "SensoryNode") -> None:
                        self._inject_to_dps(dom, fac, node, count_use=True)
                    return _hook
                facet.promotion_hook = _make_hook(domain, facet_name)
        self._sync_to_dps(count_use=False)
        logger.info("[SensoryCrystal] DPS quasi-promotion bridge wired (%d facets)",
                    len(self._audio) + len(self._visual))

    def register_evolution_hook(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Register a hook that receives evidence dicts for chamber input.

        Sunni & Cael (Build 654 fix): previously this only set
        self._evolution_hook on the crystal object itself -- every child
        SensoryClusterFacet's OWN _evolution_hook (the attribute
        tick_advanced_promotion() actually reads) stayed unset, so a hook
        registered through this documented API never reached the code that
        calls it. Confirmed via direct reproduction: a fresh facet raised
        AttributeError the moment a node reached the promotion gate,
        regardless of whether this method had ever been called. Now
        propagates to every audio/visual facet, matching the pattern
        wire_dimensional() already uses for promotion_hook.
        """
        self._evolution_hook = hook
        for facet in self._audio.values():
            facet._evolution_hook = hook
        for facet in self._visual.values():
            facet._evolution_hook = hook

    def register_genealogy(self, genealogy: Any) -> int:
        """Give every facet a reference to live genealogy so promoted nodes
        can be granted representational citizenship (Sunni & Cael, Build
        654) and so already-promoted citizens can report ongoing activity
        via tick_citizen_participation().

        Also backfills citizenship for any node that was already
        "promoted" before genealogy was ever wired -- e.g. loaded from
        persisted state at boot, before this method's first call this
        process. Without this, those nodes stay permanently stranded:
        nothing else ever re-visits an already-"promoted" node. Confirmed
        against this build's own shipped sensory state (real persisted
        promoted audio nodes with citizen_ability_id=None until this
        backfill runs). Returns the number of nodes migrated.
        """
        self._genealogy_ref = genealogy
        for facet in self._audio.values():
            facet._genealogy_ref = genealogy
        for facet in self._visual.values():
            facet._genealogy_ref = genealogy
        migrated = 0
        for facet in self._audio.values():
            migrated += facet.migrate_legacy_citizens()
        for facet in self._visual.values():
            migrated += facet.migrate_legacy_citizens()
        return migrated

    def tick_citizen_participation(self) -> int:
        """Bounded, per-session consequence-observation pass across every
        facet's already-promoted citizens (Sunni & Cael, Build 654). Call
        alongside end_session()'s existing promotion ticks -- NOT per raw
        sample, which would flood genealogy with per-frame observations.
        Returns the total number of nodes reported this pass."""
        total = 0
        for facet in self._audio.values():
            total += facet.tick_citizen_participation()
        for facet in self._visual.values():
            total += facet.tick_citizen_participation()
        return total

    def _ensure_node_name(self, domain: str, facet_name: str, node: "SensoryNode") -> None:
        if str(getattr(node, "name", "") or "").strip():
            return
        facet_map = self._audio if domain == "audio" else self._visual
        facet = facet_map.get(facet_name)
        if facet is None:
            node.name = f"{facet_name} pattern {node.node_id[:6]}"
            return
        best_label = ""
        best_sim = -1.0
        for peer in facet._nodes.values():
            if peer.node_id == node.node_id:
                continue
            label = str(getattr(peer, "name", "") or "").strip()
            if not label:
                label = self._describe_node(peer, facet_name)
            if not label:
                continue
            sim = _cosine_sim(node.centroid, peer.centroid)
            if sim > best_sim:
                best_sim = sim
                best_label = label
        if best_label and best_sim >= ARCHETYPE_MATCH_THRESHOLD:
            node.name = best_label
        elif best_label and best_sim >= 0.70:
            node.name = f"{best_label} variant"
        else:
            node.name = f"{facet_name} pattern {node.node_id[:6]}"

    def _inject_to_dps(
        self,
        domain: str,
        facet_name: str,
        node: "SensoryNode",
        *,
        count_use: bool = True,
    ) -> None:
        """
        Inject a promoted SensoryNode into the DPS crystal order ladder.

        Creates or deepens a DPS Crystal for this concept, adds facets that
        encode sensory domain, cross-modal links, and fitness — then calls
        crystal.evolve() so it can climb BASE→COMPOSITE→FULL_CONCEPT→QUASI.
        """
        if self._dps_ref is None:
            return
        try:
            self._ensure_node_name(domain, facet_name, node)
            concept = f"sensory:{domain}:{facet_name}:{node.node_id}"
            crystal = self._dps_ref._get_or_create(concept)
            if count_use:
                crystal.use()
            crystal.add_facet("sensory_domain", domain, confidence=node.confidence)
            crystal.add_facet("sensory_facet", facet_name, confidence=node.confidence)
            crystal.add_facet("sensory_identity", node.name or node.node_id[:12], confidence=node.confidence)
            crystal.add_facet("sensory_stage", node.stage, confidence=node.confidence)
            crystal.add_facet("sensory_generation", f"gen:{node.generation}", confidence=node.confidence)
            crystal.add_facet("sensory_lineage", node.lineage_id or node.node_id[:12], confidence=node.confidence)
            crystal.add_facet("sensory_usage_band", _bucket_count(node.usage_count, CONCEPT_PROMOTION_USAGE, CONCEPT_PROMOTION_USAGE * 2), confidence=node.confidence)
            crystal.add_facet("sensory_session_band", _bucket_count(node.session_count, CONCEPT_PROMOTION_SESSIONS, CONCEPT_PROMOTION_SESSIONS * 3), confidence=node.confidence)
            crystal.add_facet("sensory_confidence_band", _bucket_level(node.confidence), confidence=node.confidence)
            crystal.add_facet("sensory_fitness_band", _bucket_level(node.fitness), confidence=node.confidence)
            crystal.add_facet("sensory_maturity_band", _bucket_level(node.maturity), confidence=node.confidence)
            crystal.add_facet("sensory_cross_modal_count", _bucket_count(len(node.cross_modal_links), 1, 3), confidence=node.confidence)
            for idx, link_id in enumerate(node.cross_modal_links[:4]):
                crystal.add_facet(
                    role=f"cross_modal_link_{idx}",
                    content=f"cross_modal:{link_id}",
                    confidence=node.confidence * 0.80,
                )
            evolved = crystal.evolve()
            if evolved:
                logger.info("[SensoryCrystal→DPS] %s:%s:%s  DPS level→%s",
                            domain, facet_name, node.node_id[:8],
                            getattr(crystal.level, "name", str(crystal.level)))
        except Exception as _e:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1107",
                exc=_e,
                context={"function": "_inject_to_dps", "handler_line": 1107, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
            )
            logger.debug("[SensoryCrystal] DPS injection failed for %s:%s: %s",
                         domain, facet_name, _e)

    def _inject_semantic_to_dps(
        self,
        node: "SemanticCrystalNode",
        *,
        count_use: bool = True,
    ) -> None:
        if self._dps_ref is None:
            return
        try:
            # EDIT (one-crystal doctrine): the DPS key is the node's CONCEPT
            # (its cross-modal name, falling back to its lane), NOT its
            # node_id. Per-node keys gave every semantic observation its own
            # crystal, so nothing accumulated — concept crystals stayed
            # starved while node crystals multiplied. Now every observation
            # of the same concept lands on the SAME crystal, which gains
            # facets and association and climbs the ladder the way the
            # architecture intended. The node_id is preserved as a facet.
            _cname = (node.name or "").strip() or node.lane
            concept = f"sensory:semantic:{_cname}"
            crystal = self._dps_ref._get_or_create(concept)
            if count_use:
                crystal.use()
            crystal.add_facet("semantic_node", node.node_id[:12], confidence=node.confidence)
            crystal.add_facet("semantic_lane", node.lane, confidence=node.confidence)
            crystal.add_facet("semantic_stage", node.stage, confidence=node.confidence)
            crystal.add_facet("semantic_generation", f"gen:{node.generation}", confidence=node.confidence)
            crystal.add_facet("semantic_audio_facet", node.audio_facet, confidence=node.confidence)
            crystal.add_facet("semantic_visual_facet", node.visual_facet, confidence=node.confidence)
            crystal.add_facet("semantic_audio_node", node.audio_node_id[:12], confidence=node.confidence)
            crystal.add_facet("semantic_visual_node", node.visual_node_id[:12], confidence=node.confidence)
            crystal.add_facet("semantic_npmi_band", _bucket_level((node.npmi + 1.0) / 2.0), confidence=node.confidence)
            crystal.add_facet("semantic_confidence_band", _bucket_level(node.confidence), confidence=node.confidence)
            crystal.add_facet("semantic_fitness_band", _bucket_level(node.fitness), confidence=node.confidence)
            crystal.add_facet("semantic_cooccurrence_band", _bucket_count(node.co_occurrence_count, CROSS_MODAL_MIN_COOCCURRENCE, CROSS_MODAL_MIN_COOCCURRENCE * 3), confidence=node.confidence)
            evolved = crystal.evolve()
            if evolved:
                logger.info(
                    "[SensoryCrystal→DPS] semantic:%s:%s  DPS level→%s",
                    node.lane,
                    node.node_id[:8],
                    getattr(crystal.level, "name", str(crystal.level)),
                )
        except Exception as exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1153",
                exc=exc,
                context={"function": "_inject_semantic_to_dps", "handler_line": 1153, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
            )
            logger.debug("[SensoryCrystal] semantic DPS injection failed for %s: %s", node.node_id[:8], exc)

    def _sync_to_dps(self, *, count_use: bool) -> None:
        if self._dps_ref is None:
            return
        for domain, facets in (("audio", self._audio), ("visual", self._visual)):
            for facet_name, facet in facets.items():
                for node in facet.get_promoted():
                    self._inject_to_dps(domain, facet_name, node, count_use=count_use)
        for node in self._semantic.values():
            if node.stage in {"concept", "promoted"}:
                self._inject_semantic_to_dps(node, count_use=count_use)

    def _effective_axis_for_node(self, domain: str, facet_name: str, node_id: str) -> str:
        """The axis future perception of THIS SPECIFIC representation
        should use (Sunni & Cael, "the remaining missing circuit"): her own
        learned axis for this exact node if one has been earned, the
        facet-level category prior otherwise. Without this, a sensory
        citizen could earn axis B through tick_citizen_participation() and
        have representation_record() correctly report B, while every NEW
        observation of that same representation kept landing back on the
        facet's static prior via DPS routing -- what she learned about a
        representation never fed back into how the next encounter with it
        was perceived. Confirmed directly before this fix: genealogy said
        B, the next DPS-routed observation still stamped T.

        node_id may be "" (no specific match, e.g. a brand-new candidate
        still below the promotion gate) -- falls back to the facet prior,
        exactly as before this method existed.
        """
        if node_id and self._genealogy_ref is not None:
            facet_map = self._audio if domain == "audio" else self._visual
            facet = facet_map.get(facet_name)
            node = facet._nodes.get(node_id) if facet is not None else None
            if node is not None and node.citizen_ability_id:
                ability = self._genealogy_ref.abilities.get(node.citizen_ability_id)
                if ability is not None:
                    return str(ability.axis)
        return _facet_axis(domain, facet_name)

    def _dps_route_observation(
        self,
        domain:     str,
        facet_name: str,
        confidence: float,
        node_id:    str = "",
    ) -> None:
        """
        Route a live sensory observation into the unified DPS crystal registry.

        Every observation on a given facet (e.g. "audio:tone") lands on the
        same DPS Crystal, not a per-node one-shot.  Accumulated observations
        drive the crystal from BASE → COMPOSITE → FULL_CONCEPT → QUASI just
        as concept crystals do — sensory learning IS concept crystallization.
        """
        if self._dps_ref is None:
            return
        try:
            concept = f"sensory:{domain}:{facet_name}"
            crystal = self._dps_ref._get_or_create(concept)
            crystal.add_facet(
                role=f"{domain}_{facet_name}",
                content=f"observation@{domain}:{facet_name}",
                confidence=confidence,
            )
            crystal.use()
            # Stamp constraint_signature from this representation's
            # EFFECTIVE axis -- her own learned axis for this specific
            # matched node if she has earned one, the SENSORY_FACET_AXIS
            # category prior otherwise. Ancestry stays separate: the prior
            # itself (SENSORY_FACET_AXIS) is never rewritten by this --
            # only which axis THIS observation's pressure is stamped
            # against changes.
            axis = self._effective_axis_for_node(domain, facet_name, node_id)
            sig = crystal.constraint_signature or {}
            old = sig.get(axis, confidence)
            sig[axis] = round(old * 0.85 + confidence * 0.15, 4)
            crystal.constraint_signature = sig
            crystal.evolve()
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1210",
                exc=_aurora_boundary_exc,
                context={"function": "_dps_route_observation", "handler_line": 1210, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
            )
            pass

    # ------------------------------------------------------------------
    # Core observe  —  Operations: sensory.intake (N), sensory.cluster (B)
    # ------------------------------------------------------------------

    def observe_frame(self,
                      audio_20d:  List[float],
                      vision_57d: List[float],
                      session_id: str   = "",
                      audio_conf: float = 0.5,
                      visual_conf: float = 0.5) -> Dict[str, Any]:
        """
        Ingest one synchronised audio+vision frame.

        Routes features to each of the 6 facets, then checks all 3 pairing
        lanes for co-occurrence.  When co-occurrence threshold is met a
        SemanticCrystalNode forms in the middle plane.

        Operation: sensory.observe_frame (N, T, B, A)
        """
        if session_id:
            self._session_id = session_id
        self._total_frames += 1

        # Route to audio facets
        audio_hits: Dict[str, Optional[str]] = {}
        for name, facet in self._audio.items():
            vec = _extract_audio_facet(audio_20d, name)
            audio_hits[name] = facet.observe(vec, self._session_id, audio_conf)
            if audio_hits[name] is not None:
                self._dps_route_observation("audio", name, audio_conf, node_id=audio_hits[name])

        # Route to visual facets
        visual_hits: Dict[str, Optional[str]] = {}
        for name, facet in self._visual.items():
            vec = _extract_visual_facet(vision_57d, name)
            visual_hits[name] = facet.observe(vec, self._session_id, visual_conf)
            if visual_hits[name] is not None:
                self._dps_route_observation("visual", name, visual_conf, node_id=visual_hits[name])

        # Check pairing lanes for co-occurrence
        sem_hits: Dict[str, Optional[str]] = {}
        new_sem = False

        for a_facet, v_facet in CROSS_MODAL_PAIRS:
            a_nid = audio_hits.get(a_facet)
            v_nid = visual_hits.get(v_facet)
            if not a_nid or not v_nid:
                continue

            self._audio_marginal[a_nid]  = self._audio_marginal.get(a_nid,  0) + 1
            self._visual_marginal[v_nid] = self._visual_marginal.get(v_nid, 0) + 1

            key = f"{a_nid}:{v_nid}"
            self._cooccur[key] = self._cooccur.get(key, 0) + 1
            count = self._cooccur[key]

            lane = LANE_LABEL[(a_facet, v_facet)]
            sem  = self._find_semantic(a_nid, v_nid)

            if sem is None and count >= CROSS_MODAL_MIN_COOCCURRENCE:
                # Compute nPMI for the new node
                p_av = count / max(1, self._total_frames)
                p_a  = self._audio_marginal[a_nid]  / max(1, self._total_frames)
                p_v  = self._visual_marginal[v_nid]  / max(1, self._total_frames)
                sem  = SemanticCrystalNode(
                    node_id        = str(uuid.uuid4()),
                    lane           = lane,
                    audio_facet    = a_facet,
                    visual_facet   = v_facet,
                    audio_node_id  = a_nid,
                    visual_node_id = v_nid,
                    lineage_id     = str(uuid.uuid4()),
                )
                sem.co_occurrence_count = count
                sem.npmi                = _npmi(p_av, p_a, p_v)
                self._semantic[sem.node_id] = sem
                new_sem = True
                logger.debug("[SensoryCrystal] New semantic node lane=%s  "
                             "audio=%s visual=%s", lane, a_nid[:8], v_nid[:8])

            if sem is not None:
                sem.co_occurrence_count = count
                p_av = count / max(1, self._total_frames)
                p_a  = self._audio_marginal[a_nid]  / max(1, self._total_frames)
                p_v  = self._visual_marginal[v_nid]  / max(1, self._total_frames)
                sem.npmi       = _npmi(p_av, p_a, p_v)
                sem.confidence = _ema(sem.confidence, min(audio_conf, visual_conf))
                sem.last_seen  = time.time()
                sem.compute_fitness()
                sem_hits[lane] = sem.node_id

        self._novelty_window.append(1 if new_sem else 0)
        self._last_matches = {
            "audio": dict(audio_hits),
            "visual": dict(visual_hits),
            "semantic": dict(sem_hits),
        }
        recognitions: List[str] = []
        for facet_name, node_id in audio_hits.items():
            node = self._audio[facet_name].get_node(node_id) if node_id else None
            desc = self._describe_node(node, facet_name)
            if desc:
                recognitions.append(f"heard {desc}")
        for facet_name, node_id in visual_hits.items():
            node = self._visual[facet_name].get_node(node_id) if node_id else None
            desc = self._describe_node(node, facet_name)
            if desc:
                recognitions.append(f"saw {desc}")
        for lane in sem_hits:
            recognitions.append(f"cross-modal {lane.replace('_', ' ')}")
        self._last_recognitions = recognitions[:6]
        return {"audio": audio_hits, "visual": visual_hits, "semantic": sem_hits}

    def concept_registry_summary(self) -> Dict[str, Any]:
        """Summary of the semantic concept registry (FIX-A013).

        corpus_runner.py calls this at boot banner, cadence saves, and
        end-of-ingestion — it never existed, so every corpus run crashed
        at the first verbose cadence checkpoint. Shape matches the
        runner's expectations: {'total': int, 'by_stage': {stage: count}}.
        """
        by_stage: Dict[str, int] = {}
        for n in self._semantic.values():
            s = str(getattr(n, "stage", "unknown") or "unknown")
            by_stage[s] = by_stage.get(s, 0) + 1
        return {"total": len(self._semantic), "by_stage": by_stage}

    def _find_semantic(self, a_nid: str, v_nid: str) -> Optional[SemanticCrystalNode]:
        for n in self._semantic.values():
            if n.audio_node_id == a_nid and n.visual_node_id == v_nid:
                return n
        return None

    # ------------------------------------------------------------------
    # Promotion  —  Operation: sensory.promote (A)
    # ------------------------------------------------------------------

    def _tick_semantic_promotion(self) -> None:
        """
        candidate -> concept -> promoted.
        Promoted nodes write cross-modal links back into both facets.
        Operation: sensory.cross_modal_link (N×A = force)
        """
        for node in self._semantic.values():
            if node.stage == "candidate" and node.is_promotable_concept():
                node.stage       = "concept"
                node.generation += 1
                logger.debug("[SensoryCrystal] semantic candidate->concept %s lane=%s",
                             node.node_id[:8], node.lane)

            elif node.stage == "concept" and node.is_promotable_promoted():
                node.stage       = "promoted"
                node.generation += 1
                # Write cross-modal links back into both facets
                af = self._audio.get(node.audio_facet)
                vf = self._visual.get(node.visual_facet)
                if af:
                    af.add_cross_modal_link(node.audio_node_id,  node.visual_node_id)
                if vf:
                    vf.add_cross_modal_link(node.visual_node_id, node.audio_node_id)
                logger.info("[SensoryCrystal] semantic->promoted %s lane=%s "
                            "fitness=%.2f cross-modal links written",
                            node.node_id[:8], node.lane, node.fitness)
                self._inject_semantic_to_dps(node, count_use=True)

    # ------------------------------------------------------------------
    # Session end  —  Operation: sensory.end_session (T, B, A)
    # ------------------------------------------------------------------

    def get_gap_report(self) -> Dict[str, List[str]]:
        """
        Report which sensory modalities and concepts have gaps.
        Called by the curiosity engine each cycle to drive multi-modal gap resolution.

        Returns dict with four lists:
          needs_visual   — facets with no real visual observations beyond archetypes
          needs_audio    — facets with no real audio observations beyond archetypes
          needs_second   — audio nodes present but lacking any cross-modal visual link
          needs_semantic — cross-modal semantic nodes stuck at candidate stage
        """
        needs_visual:   List[str] = []
        needs_audio:    List[str] = []
        needs_second:   List[str] = []
        needs_semantic: List[str] = []

        for name, facet in self._visual.items():
            real = [n for n in facet._nodes.values()
                    if str(getattr(n, "lineage_id", "")) != "archetype"]
            if not real:
                needs_visual.append(name)

        for name, facet in self._audio.items():
            real = [n for n in facet._nodes.values()
                    if str(getattr(n, "lineage_id", "")) != "archetype"]
            if not real:
                needs_audio.append(name)
            else:
                for node in real:
                    if (getattr(node, "stage", "") in ("base", "candidate")
                            and not getattr(node, "cross_modal_links", None)):
                        label = str(getattr(node, "name", None) or name)
                        if label not in needs_second:
                            needs_second.append(label)

        for node in self._semantic.values():
            if getattr(node, "stage", "") == "candidate":
                label = f"{getattr(node, 'lane', 'cross-modal')} perception"
                if label not in needs_semantic:
                    needs_semantic.append(label)

        return {
            "needs_visual":   needs_visual[:6],
            "needs_audio":    needs_audio[:6],
            "needs_second":   needs_second[:6],
            "needs_semantic": needs_semantic[:6],
        }

    def ingest(self, concept: str, modality: str = "semantic",
               data: str = "", source: str = "") -> None:
        """
        Ingest concept-level observational data from external sources (teaching,
        user examples, world-knowledge search results).

        For semantic modality: promotes the concept into the DPS crystal if wired.
        For visual/audio modality: treated as a novelty observation bump so the
        pressure axes update and curiosity engine registers the gap as partially filled.
        """
        if not concept or not data:
            return
        label = f"{concept}:{modality}"
        if label not in self._last_recognitions:
            self._last_recognitions.append(label)
            if len(self._last_recognitions) > 32:
                self._last_recognitions = self._last_recognitions[-32:]

        self._novelty_window.append(1)
        if len(self._novelty_window) > 48:
            self._novelty_window = self._novelty_window[-48:]

        if modality == "semantic" and self._dps_ref is not None:
            try:
                key = f"concept:{concept[:40]}"
                crystal = self._dps_ref._get_or_create(key)
                crystal.add_facet("semantic_definition", (data or "")[:80], confidence=0.72)
                if source:
                    crystal.add_facet("semantic_source", source[:40], confidence=0.50)
                crystal.evolve()
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1460",
                    exc=_aurora_boundary_exc,
                    context={"function": "ingest", "handler_line": 1460, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
                )
                pass

    def observe_semantic(self, concept: str, weight: float = 1.0,
                         source: str = "corpus") -> None:
        """
        Compatibility surface for corpus ingestion.

        Corpus training emits lightweight semantic word observations; route them
        through the existing concept-level ingest path so they can affect
        recognitions, novelty, and DPS semantic facets when wired.
        """
        concept = str(concept or "").strip()
        if not concept:
            return
        self.ingest(
            concept=concept,
            modality="semantic",
            data=f"observed semantic corpus token weight={float(weight or 0.0):.3f}",
            source=source,
        )

    def end_session(self) -> List[Dict[str, Any]]:
        """
        End-of-interaction consolidation.  Runs promotion, maturity, cull, save.
        Returns list of WisdomShard-compatible dicts from dead nodes.
        Call from dismiss() / consolidation_stage().

        Operation: sensory.end_session (T, B, A)
        """
        wisdom: List[Dict[str, Any]] = []

        for facet in self._audio.values():
            facet.end_session(wisdom)
        for facet in self._visual.values():
            facet.end_session(wisdom)

        # Representational citizenship (Sunni & Cael, Build 654): report
        # ongoing activity for already-promoted citizens once per session,
        # after this session's own promotion ticks above so a node
        # promoted THIS session already has a citizen_ability_id to report
        # against next time, and any node promoted in a PRIOR session gets
        # its consequence tick now.
        self.tick_citizen_participation()

        # Semantic middle plane
        self._tick_semantic_promotion()
        self._sync_to_dps(count_use=True)
        self._cull_semantic(wisdom)
        self._compute_semantic_maturity()

        self._save()

        return wisdom

    def _compute_semantic_maturity(self) -> None:
        if not self._semantic:
            self._maturity = 0.0
            return
        window   = self._novelty_window[-50:] or [1]
        nov      = _clamp01(sum(window) / max(1, len(window)))
        promoted = [n for n in self._semantic.values() if n.stage != "candidate"]
        stab     = (_clamp01(sum(n.confidence for n in promoted) / len(promoted))
                    if promoted else 0.0)
        compr    = _clamp01(len(promoted) / max(1, len(self._semantic)))
        self._maturity = _clamp01(
            WEIGHT_STABILITY * stab + WEIGHT_NOVELTY * (1 - nov) + WEIGHT_COMPRESSION * compr)

    def _cull_semantic(self, wisdom: List[Dict[str, Any]]) -> None:
        if len(self._semantic) <= SEMANTIC_CONCEPT_FLOOR:
            return
        victims = sorted(
            [n for n in self._semantic.values() if n.stage == "candidate"],
            key=lambda n: n.fitness
        )[: max(0, len(self._semantic) - 60)]
        for n in victims:
            wisdom.append(n.emit_wisdom())
            del self._semantic[n.node_id]

    # ------------------------------------------------------------------
    # Persistence  —  Operation: sensory.distill (T)
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist current crystal state without ending the session.
        Call from _full_save() so the crystal survives restarts mid-session."""
        self._save()

    def _save(self) -> None:
        for name, facet in self._audio.items():
            facet.save(self._base / "audio" / name)
        for name, facet in self._visual.items():
            facet.save(self._base / "visual" / name)
        payload = {
            "total_frames":    self._total_frames,
            "maturity":        self._maturity,
            "semantic":        {nid: n.to_dict() for nid, n in self._semantic.items()},
            "cooccur":         self._cooccur,
            "audio_marginal":  self._audio_marginal,
            "visual_marginal": self._visual_marginal,
        }
        _agb_save(self._base / "semantic" / "state.agb", payload)
        # Write hub-readable snapshot so aurora_hub.py Audio tab can display
        # live facet maturities, node counts, and cross-modal lane activity.
        try:
            hub_state = self.get_state()
            hub_state["saved_at"] = time.time()
            hub_path = self._base.parent / "sensory_crystal_state.json"
            hub_path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json
            with open(str(hub_path), "w") as _fh:
                _json.dump(hub_state, _fh)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1564",
                exc=_aurora_boundary_exc,
                context={"function": "_save", "handler_line": 1564, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
            )
            pass

    # ------------------------------------------------------------------
    # State report
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        state = {
            "maturity":        round(self._maturity, 3),
            "total_frames":    self._total_frames,
            "semantic_nodes":  len(self._semantic),
            "audio": {n: {"nodes": len(f._nodes), "promoted": len(f.get_promoted()),
                          "maturity": round(f.maturity, 3)}
                      for n, f in self._audio.items()},
            "visual": {n: {"nodes": len(f._nodes), "promoted": len(f.get_promoted()),
                           "maturity": round(f.maturity, 3)}
                       for n, f in self._visual.items()},
            "lanes": {
                LANE_LABEL[pair]: {
                    "nodes":    len([s for s in self._semantic.values()
                                     if s.lane == LANE_LABEL[pair]]),
                    "promoted": len([s for s in self._semantic.values()
                                     if s.lane == LANE_LABEL[pair]
                                     and s.stage != "candidate"]),
                }
                for pair in CROSS_MODAL_PAIRS
            },
            "recognitions": {
                "recent": list(self._last_recognitions[:6]),
                "last_matches": {
                    "audio": dict(self._last_matches.get("audio") or {}),
                    "visual": dict(self._last_matches.get("visual") or {}),
                    "semantic": dict(self._last_matches.get("semantic") or {}),
                },
            },
        }
        state["lineage_signature"] = (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")
        state["runtime_regime"] = self.runtime_regime()
        state["language_projection"] = self.language_projection()
        return state

    def _constraint_axes(self) -> Dict[str, float]:
        audio_maturity = max((float(f.maturity or 0.0) for f in self._audio.values()), default=0.0)
        visual_maturity = max((float(f.maturity or 0.0) for f in self._visual.values()), default=0.0)
        promoted_audio = sum(len(f.get_promoted()) for f in self._audio.values())
        promoted_visual = sum(len(f.get_promoted()) for f in self._visual.values())
        promoted_semantic = len([n for n in self._semantic.values() if n.stage != "candidate"])
        return {
            "X": min(1.0, 0.20 + visual_maturity * 0.40 + min(1.0, self._total_frames / 200.0) * 0.15),
            "T": min(1.0, 0.20 + min(1.0, self._total_frames / 240.0) * 0.45 + self._maturity * 0.15),
            "N": min(1.0, 0.20 + audio_maturity * 0.35 + max(audio_maturity, visual_maturity) * 0.15),
            "B": min(1.0, 0.20 + min(1.0, (promoted_audio + promoted_visual) / 18.0) * 0.35 + self._maturity * 0.15),
            "A": min(1.0, 0.15 + min(1.0, promoted_semantic / 12.0) * 0.45 + self._maturity * 0.20),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        recent_window = self._novelty_window[-12:]
        novelty = sum(recent_window) / max(1, len(recent_window))
        candidate_semantic = len([n for n in self._semantic.values() if n.stage == "candidate"])
        return {
            "X": min(1.0, max((float(f.maturity or 0.0) for f in self._visual.values()), default=0.0)),
            "T": min(1.0, self._total_frames / 300.0),
            "N": min(1.0, max((float(f.maturity or 0.0) for f in self._audio.values()), default=0.0) + novelty * 0.25),
            "B": min(1.0, candidate_semantic / 12.0),
            "A": 1.0 if self._session_id else min(1.0, candidate_semantic / 12.0 + novelty * 0.2),
        }

    def constraint_profile(self):
        return build_constraint_profile(
            unit_id="aurora_sensory_crystal",
            unit_kind="sensory_crystal",
            operational_role="cross_modal_curriculum_grounding",
            genealogy="XTNBBA",
            axis_weights=self._constraint_axes(),
            pressure_axes=self._pressure_axes(),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        return self.constraint_profile().runtime_regime()

    def language_projection(self) -> Dict[str, Any]:
        return self.constraint_profile().language_projection()

    def universal_representation(self) -> Dict[str, Any]:
        profile = self.constraint_profile()
        rep = profile.universal_representation()
        rep["unit_state"] = {
            "session_id": self._session_id,
            "total_frames": self._total_frames,
            "maturity": round(self._maturity, 3),
            "semantic_nodes": len(self._semantic),
            "recent_recognitions": list(self._last_recognitions[:6]),
        }
        return rep


# =============================================================================
# LINEAGE TRAIT SPEC  —  seeds ability into Aurora's genealogy
# =============================================================================

TRAIT_ID = "aurora_sensory_crystal_v1"

# Sunni & Cael: the canonical set of sensory AbilityProfile IDs
# ensure_sensory_crystal_lineage() registers into the live genealogy.
# Named here (module level) rather than only as inline dict keys inside
# that function so callers/tests can verify registration without
# duplicating the literal ID list.
SENSORY_ABILITY_IDS = (
    "N:SENSORY_INTAKE",
    "B:SENSORY_CLUSTER",
    "A:SENSORY_PROMOTE",
    "N:SENSORY_CROSS_MODAL",
    "T:SENSORY_DISTILL",
)

def _make_lineage_trait_spec() -> Optional[Any]:
    """
    Build the LineageTraitSpec for the sensory crystal abilities.
    Returns None if lineage machinery isn't available (graceful degradation).

    5 stages mapping to the XTNBA axis progression:
        sensory_intake_seed        gen=1  N  (signal becomes change-pressure)
        sensory_crystal_clustering gen=2  B  (boundary shaping of concept space)
        sensory_concept_promotion  gen=2  A  (interpretive selection)
        cross_modal_grounding      gen=3  N  (N×A = force: energy directed by agency)
        sensory_wisdom_distillation gen=3 T  (temporal compression / what persists)
    """
    try:
        from aurora_internal.aurora_lineage_bound_traits import (
            LineageTraitSpec, OperationBinding,
        )
        from aurora_internal.aurora_ability_lineage_compiler import (
            LineageStage, SystemWriteback,
        )
    except ImportError as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:1686",
            exc=_aurora_boundary_exc,
            context={"function": "_make_lineage_trait_spec", "handler_line": 1686, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
        )
        return None

    stages = (
        LineageStage(
            stage_id        = "sensory_intake_seed",
            generation      = 1,
            label           = "Sensory Intake Seed",
            kind            = "seed",
            dominant_axis   = "N",
            constraints     = ("energy", "temporal", "existence"),
            summary         = ("Raw audio and visual signals enter the crystal system "
                               "as change-pressure — meaning as latent potential."),
            purpose_lane    = "meaning",
            operator_action = "energy_economics",
            parents         = (),
            target_files    = ("aurora_internal/aurora_sensory_crystal.py",),
            ripple_effects  = (
                "Audio and visual streams become first-class meaning sources.",
                "N-axis pressure rises proportional to sensory novelty rate.",
            ),
            system_writebacks = (
                SystemWriteback("working_memory", "sensory_intake_active",  "set",       True),
                SystemWriteback("pipeline",       "sensory_intake",         "append_unique", "sensory.intake"),
                SystemWriteback("rubric",         "target_dimensions",      "append_unique", "semantic_precision"),
            ),
            notes = "Zero-state boot: all facets start empty, maturity=0.0.",
        ),
        LineageStage(
            stage_id        = "sensory_crystal_clustering",
            generation      = 2,
            label           = "Sensory Crystal Clustering",
            kind            = "coupling",
            dominant_axis   = "B",
            constraints     = ("boundary", "energy", "existence"),
            summary         = ("Observations cluster into SensoryNodes — "
                               "boundary shaping of the raw sensory concept space."),
            purpose_lane    = "meaning",
            operator_action = "boundary_shaping",
            parents         = ("sensory_intake_seed",),
            target_files    = ("aurora_internal/aurora_sensory_crystal.py",),
            ripple_effects  = (
                "Concept floor enforced per facet (audio=8, visual=10).",
                "Cosine similarity gates cluster membership at 0.93.",
            ),
            system_writebacks = (
                SystemWriteback("working_memory", "sensory_cluster_active",  "set",       True),
                SystemWriteback("pipeline",       "sensory_cluster",         "append_unique", "sensory.cluster"),
            ),
            notes = "B-axis gate: SIMILARITY_MATCH_THRESHOLD=0.93.",
        ),
        LineageStage(
            stage_id        = "sensory_concept_promotion",
            generation      = 2,
            label           = "Sensory Concept Promotion",
            kind            = "coupling",
            dominant_axis   = "A",
            constraints     = ("agency", "boundary", "energy"),
            summary         = ("Primitive nodes that meet usage/session/confidence gates "
                               "are selected into concept stage — interpretive selection."),
            purpose_lane    = "meaning",
            operator_action = "agency_direction",
            parents         = ("sensory_crystal_clustering",),
            target_files    = ("aurora_internal/aurora_sensory_crystal.py",),
            ripple_effects  = (
                "Promoted concepts become cross-modal pairing candidates.",
                "A-axis pressure decreases as stable concept population grows.",
            ),
            system_writebacks = (
                SystemWriteback("working_memory", "sensory_promotion_active", "set", True),
                SystemWriteback("pipeline",       "sensory_promote",          "append_unique", "sensory.promote"),
                SystemWriteback("rubric",         "target_dimensions",        "append_unique", "coherence_maintenance"),
            ),
            notes = ("Promotion gates: usage>=14, sessions>=3, confidence>=0.55. "
                     "Advanced promotion (concept->promoted) requires cross-modal link."),
        ),
        LineageStage(
            stage_id        = "cross_modal_grounding",
            generation      = 3,
            label           = "Cross-Modal Grounding",
            kind            = "compound",
            dominant_axis   = "N",
            constraints     = ("energy", "agency", "boundary", "existence"),
            summary         = ("Audio and visual promoted nodes that co-occur >= 10 times "
                               "with nPMI >= 0.15 form SemanticCrystalNodes in the middle "
                               "plane — N×A = force: energy directed by agency."),
            purpose_lane    = "meaning",
            operator_action = "energy_economics",
            parents         = ("sensory_concept_promotion",),
            target_files    = ("aurora_internal/aurora_sensory_crystal.py",),
            ripple_effects  = (
                "Cross-modal links written back into both audio and visual facets.",
                "Semantic middle plane populates with tonal_colour / texture_form / tempo_flow nodes.",
                "Meaning formed from lived experience rather than symbolic assignment.",
                "Promoted sensory and semantic nodes project into the dimensional crystal ladder.",
            ),
            system_writebacks = (
                SystemWriteback("working_memory", "cross_modal_grounding_active", "set", True),
                SystemWriteback("pipeline",       "cross_modal_link",  "append_unique", "sensory.cross_modal_link"),
                SystemWriteback("genealogy",      "cross_modal_lanes",  "append_unique", "tonal_colour"),
                SystemWriteback("genealogy",      "cross_modal_lanes",  "append_unique", "texture_form"),
                SystemWriteback("genealogy",      "cross_modal_lanes",  "append_unique", "tempo_flow"),
            ),
            notes = ("nPMI computed per frame: pmi=log2(P(a,v)/(P(a)*P(v))), "
                     "npmi=pmi/-log2(P(a,v)).  Lane geometry is fixed: "
                     "tone<->hue, timbre<->shape, rhythm<->motion."),
        ),
        LineageStage(
            stage_id        = "sensory_wisdom_distillation",
            generation      = 3,
            label           = "Sensory Wisdom Distillation",
            kind            = "compound",
            dominant_axis   = "T",
            constraints     = ("temporal", "energy", "existence"),
            summary         = ("Mature facets (maturity>=0.80) distill into compact tags. "
                               "Dead nodes emit WisdomShards — what was learned survives "
                               "even after the node is culled."),
            purpose_lane    = "meaning",
            operator_action = "temporal_orchestration",
            parents         = ("cross_modal_grounding",),
            target_files    = ("aurora_internal/aurora_sensory_crystal.py",),
            ripple_effects  = (
                "WisdomShards (domain=audio/vision/multimodal) fed to ExpressionWisdomStore.",
                "Plateau-aware decay: high maturity -> slower centroid drift.",
                "Concept floor prevents catastrophic forgetting.",
                "Repeated session sync strengthens higher-order sensory crystals toward QUASI.",
            ),
            system_writebacks = (
                SystemWriteback("working_memory", "sensory_distillation_active", "set", True),
                SystemWriteback("expression",     "wisdom_domains",  "append_unique", "audio"),
                SystemWriteback("expression",     "wisdom_domains",  "append_unique", "vision"),
                SystemWriteback("expression",     "wisdom_domains",  "append_unique", "multimodal"),
                SystemWriteback("pipeline",       "sensory_distill", "append_unique", "sensory.distill"),
            ),
            notes = "Distillation at maturity>=0.80. End-session cull emits wisdom from dead primitives.",
        ),
    )

    bindings = (
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal.observe_frame",
            stage_ids      = ("sensory_intake_seed", "sensory_crystal_clustering",
                              "cross_modal_grounding"),
            dominant_axis  = "N",
            purpose_lane   = "meaning",
            ripple_domains = ("working_memory", "pipeline", "genealogy"),
            notes          = "Routes audio+visual features to 6 facets and seeds co-occurrence.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "SensoryClusterFacet.tick_promotion",
            stage_ids      = ("sensory_concept_promotion",),
            dominant_axis  = "A",
            purpose_lane   = "meaning",
            ripple_domains = ("working_memory",),
            notes          = "A-axis: interpretive selection of surviving concepts.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal._tick_semantic_promotion",
            stage_ids      = ("cross_modal_grounding",),
            dominant_axis  = "N",
            purpose_lane   = "meaning",
            ripple_domains = ("working_memory", "genealogy"),
            notes          = "N×A force: writes cross-modal links on promoted semantic nodes.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal._inject_to_dps",
            stage_ids      = ("sensory_concept_promotion", "cross_modal_grounding"),
            dominant_axis  = "A",
            purpose_lane   = "meaning",
            ripple_domains = ("genealogy", "pipeline"),
            notes          = "Promoted sensory concepts are projected into the dimensional crystal ladder.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal._inject_semantic_to_dps",
            stage_ids      = ("cross_modal_grounding",),
            dominant_axis  = "N",
            purpose_lane   = "meaning",
            ripple_domains = ("genealogy", "pipeline"),
            notes          = "Cross-modal semantic nodes deepen the dimensional ladder as higher-order meaning crystals.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal._sync_to_dps",
            stage_ids      = ("sensory_wisdom_distillation",),
            dominant_axis  = "T",
            purpose_lane   = "meaning",
            ripple_domains = ("expression", "genealogy", "pipeline"),
            notes          = "Session-bounded resynchronization lets sensory and semantic crystals accumulate lived reinforcement over time.",
        ),
        OperationBinding(
            module         = "aurora_internal.aurora_sensory_crystal",
            qualname       = "AuroraSensoryCrystal.end_session",
            stage_ids      = ("sensory_wisdom_distillation", "sensory_concept_promotion"),
            dominant_axis  = "T",
            purpose_lane   = "meaning",
            ripple_domains = ("expression", "working_memory", "pipeline"),
            notes          = "T-axis: temporal compression + wisdom emission at session end.",
        ),
    )

    return LineageTraitSpec(
        trait_id           = TRAIT_ID,
        label              = "Aurora Sensory Crystal v1",
        rationale          = (
            "Gives Aurora first-person sensory understanding: raw audio and visual "
            "signals evolve into crystal concepts that can be promoted, cross-modal "
            "linked, and distilled into wisdom — all through the same XTNBA constraint "
            "genealogy that governs every other ability in the system."
        ),
        selected_strategy  = "constraint_recapitulation_v1",
        stages             = stages,
        bindings           = bindings,
        runtime_patch_targets = (
            {
                "step_id": "sensory_crystal.init",
                "target":  "systems",
                "action":  "merge_state",
                "payload": {"sensory_crystal_initialized": True},
            },
        ),
    )


def ensure_sensory_crystal_lineage(systems: Dict[str, Any],
                                    state_dir: str = _STATE_ROOT,
                                    verbose: bool = False) -> bool:
    """
    Seed the sensory crystal abilities into Aurora's lineage system.
    Call once at boot after boot_aurora().

    Idempotent: if the trait is already materialized it does nothing.

    Returns True if newly materialized, False if already present.
    """
    # Trait materialization and live genealogy ability registration are
    # separate responsibilities (Sunni & Cael). A persisted trait directory
    # from a prior boot means the ONE-TIME on-disk materialization step can
    # be skipped -- it does NOT mean the freshly-constructed in-memory
    # ConstraintGenealogyLogger for THIS process already has the sensory
    # AbilityProfiles registered. Every restart gets a new logger instance;
    # the injection loop below must run every time, gated only by its own
    # per-ability idempotency check, never by trait-directory existence.
    trait_dir = Path(state_dir) / "ability_lineages" / TRAIT_ID
    already_materialized = trait_dir.exists()
    result = False

    if already_materialized:
        if verbose:
            logger.info("[SensoryCrystal] Lineage trait already materialized — "
                        "skipping re-materialization, still registering live abilities.")
    else:
        spec = _make_lineage_trait_spec()
        if spec is None:
            logger.warning("[SensoryCrystal] Lineage machinery not available — "
                           "crystal will run without genealogy registration.")
        else:
            try:
                registry = systems.get("lineage_trait_registry")
                if registry is None:
                    try:
                        from aurora_internal.aurora_lineage_bound_traits import (
                            LineageBoundTraitRegistry,
                        )
                        registry = LineageBoundTraitRegistry(
                            storage_dir=str(Path(state_dir) / "ability_lineages")
                        )
                    except ImportError:
                        logger.warning("[SensoryCrystal] LineageBoundTraitRegistry not found.")
                        registry = None

                if registry is not None:
                    result = registry.materialize(spec)
                    if verbose or result:
                        logger.info("[SensoryCrystal] Lineage trait materialized: %s", TRAIT_ID)
            except Exception as exc:
                logger.warning("[SensoryCrystal] Lineage materialization failed: %s", exc)

    # ── Genealogy AbilityProfile injection ────────────────────────────────────
    # Always attempted, regardless of trait materialization state -- the
    # per-ability "not in genealogy.abilities" check below is what makes
    # this idempotent, not an early return above.
    # Register sensory crystal operations as first-class AbilityProfile entries
    # in the live ConstraintGenealogyLogger.  Without this the genealogy cannot
    # form causal ancestry chains that trace back to these operations.
    genealogy = systems.get("genealogy")
    if genealogy is not None and hasattr(genealogy, "abilities"):
        try:
            from aurora_evolution_stack import AbilityProfile
            _SENSORY_ABILITY_PROFILES: Dict[str, Any] = {
                "N:SENSORY_INTAKE": AbilityProfile(
                    id           = "N:SENSORY_INTAKE",
                    axis         = "N",
                    requires     = ("N", "T", "X"),
                    cost         = {"X": 0.05, "T": 0.10, "N": 0.20, "B": 0.05, "A": 0.05},
                    risk         = {"N": 0.05, "T": 0.03},
                    effect_tags  = ("sensory", "intake", "energy", "perception"),
                    notes        = "",
                ),
                "B:SENSORY_CLUSTER": AbilityProfile(
                    id           = "B:SENSORY_CLUSTER",
                    axis         = "B",
                    requires     = ("B", "N"),
                    cost         = {"X": 0.05, "T": 0.05, "N": 0.10, "B": 0.20, "A": 0.05},
                    risk         = {"B": 0.05},
                    effect_tags  = ("sensory", "cluster", "boundary", "perception"),
                    notes        = "",
                ),
                "A:SENSORY_PROMOTE": AbilityProfile(
                    id           = "A:SENSORY_PROMOTE",
                    axis         = "A",
                    requires     = ("A", "B", "N"),
                    cost         = {"X": 0.10, "T": 0.10, "N": 0.15, "B": 0.10, "A": 0.25},
                    risk         = {"A": 0.10, "N": 0.05},
                    effect_tags  = ("sensory", "promote", "agency", "crystal"),
                    notes        = "",
                ),
                "N:SENSORY_CROSS_MODAL": AbilityProfile(
                    id           = "N:SENSORY_CROSS_MODAL",
                    axis         = "N",
                    requires     = ("N", "A", "B"),
                    cost         = {"X": 0.10, "T": 0.10, "N": 0.25, "B": 0.15, "A": 0.20},
                    risk         = {"N": 0.10, "A": 0.05},
                    effect_tags  = ("sensory", "cross_modal", "meaning", "grounding"),
                    notes        = "nPMI cross-modal linking: tone↔hue, timbre↔shape, rhythm↔motion (gen=3, N-axis)",
                ),
                "T:SENSORY_DISTILL": AbilityProfile(
                    id           = "T:SENSORY_DISTILL",
                    axis         = "T",
                    requires     = ("T", "N"),
                    cost         = {"X": 0.05, "T": 0.25, "N": 0.15, "B": 0.10, "A": 0.05},
                    risk         = {"T": 0.05},
                    effect_tags  = ("sensory", "distill", "wisdom", "temporal"),
                    notes        = "Maturity-gated distillation + WisdomShard emission (sensory.distill, gen=3, T-axis)",
                ),
            }
            injected = 0
            for ability_id, profile in _SENSORY_ABILITY_PROFILES.items():
                if ability_id not in genealogy.abilities:
                    genealogy.abilities[ability_id] = profile
                    injected += 1
            if verbose and injected:
                logger.info("[SensoryCrystal] Injected %d sensory AbilityProfiles into genealogy "
                            "causal chain", injected)
        except Exception as _ga_e:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:2021",
                exc=_ga_e,
                context={"function": "ensure_sensory_crystal_lineage", "handler_line": 2021, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
            )
            logger.debug("[SensoryCrystal] Genealogy AbilityProfile injection failed: %s", _ga_e)

    return bool(result)


# =============================================================================
# FACTORY
# =============================================================================

def build_aurora_sensory_crystal(state_dir: str = _STATE_ROOT) -> "AuroraSensoryCrystal":
    """
    Convenience factory.  Creates and boots a full AuroraSensoryCrystal.

    Typical usage in aurora.py or aurora_runtime.py:

        from aurora_internal.aurora_sensory_crystal import (
            build_aurora_sensory_crystal, ensure_sensory_crystal_lineage
        )

        # After boot_aurora():
        ensure_sensory_crystal_lineage(systems, state_dir=args.state_dir)
        crystal = build_aurora_sensory_crystal(state_dir=args.state_dir)
        systems["sensory_crystal"] = crystal
    """
    crystal = AuroraSensoryCrystal(state_dir=state_dir)
    crystal.boot()
    return crystal
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")


def build_audio_20d_from_der(
    x: float, t: float, n: float, b: float, a: float
) -> List[float]:
    """
    Synthesize a 20-d audio feature vector from DER axis pressures.

    Used when no microphone is available (corpus training, daemon idle cycles).
    Maps Aurora's internal constraint state to the acoustic dimensions the
    sensory crystal's audio facets understand.
    """
    x = max(0.0, min(1.0, float(x)))
    t = max(0.0, min(1.0, float(t)))
    n = max(0.0, min(1.0, float(n)))
    b = max(0.0, min(1.0, float(b)))
    a = max(0.0, min(1.0, float(a)))

    vec = [0.0] * 20
    vec[0] = x           # RMS ← X (existence energy → amplitude)
    vec[1] = n           # ZCR ← N (novelty → spectral roughness)
    vec[2] = a           # centroid ← A (agency → timbral brightness)
    vec[3] = b           # bandwidth ← B (boundary → spectral spread)
    vec[4] = (x + b) * 0.5  # rolloff ← mean(X, B)
    vec[5] = t           # flux ← T (temporal change rate)
    vec[7] = 0.8 * t + 0.2 * a  # onset_density
    vec[6] = a           # harmonicity ← A
    dominant = int(a * 11.9999)
    spread = max(0.5, (1.0 - n) * 2.5)
    chroma_sum = 0.0
    for i in range(12):
        dist = min(abs(i - dominant), 12 - abs(i - dominant))
        raw = math.exp(-dist / spread)
        vec[8 + i] = raw
        chroma_sum += raw
    if chroma_sum > 0:
        for i in range(12):
            vec[8 + i] = vec[8 + i] / chroma_sum * a
    return vec


def build_vision_57d_from_image_file(image_path: str) -> Optional[List[float]]:
    """
    Extract a 57-d visual feature vector from an image file using PIL only.

    No cv2 required — works in corpus training where cv2 may not be installed.
    Returns None if PIL is unavailable or extraction fails.
    """
    try:
        from PIL import Image as _PILImg
    except ImportError as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:2100",
            exc=_aurora_boundary_exc,
            context={"function": "build_vision_57d_from_image_file", "handler_line": 2100, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
        )
        return None

    try:
        img = _PILImg.open(image_path).convert("RGB")
        w, h = img.size
        pixels = list(img.getdata())
        n_pix = max(1, len(pixels))

        r_vals = [p[0] / 255.0 for p in pixels]
        g_vals = [p[1] / 255.0 for p in pixels]
        b_vals = [p[2] / 255.0 for p in pixels]
        avg_r = sum(r_vals) / n_pix
        avg_g = sum(g_vals) / n_pix
        avg_b = sum(b_vals) / n_pix

        hue_bins = [0.0] * 24
        sat_sum = 0.0
        for r, g, bv in zip(r_vals, g_vals, b_vals):
            mx, mn = max(r, g, bv), min(r, g, bv)
            delta = mx - mn
            sat = delta / max(mx, 1e-9)
            sat_sum += sat
            if delta < 0.001:
                continue
            if mx == r:
                hue = ((g - bv) / delta) % 6.0
            elif mx == g:
                hue = (bv - r) / delta + 2.0
            else:
                hue = (r - g) / delta + 4.0
            hue_bins[int(hue / 6.0 * 24) % 24] += sat
        hue_sum = sum(hue_bins) or 1.0
        vec = [v / hue_sum for v in hue_bins]

        brightness = avg_r * 0.299 + avg_g * 0.587 + avg_b * 0.114
        var_r = sum((v - avg_r) ** 2 for v in r_vals) / n_pix
        var_g = sum((v - avg_g) ** 2 for v in g_vals) / n_pix
        var_b = sum((v - avg_b) ** 2 for v in b_vals) / n_pix
        edge_proxy = _clamp01((var_r + var_g + var_b) ** 0.5 * 4.0)
        saturation = sat_sum / n_pix
        aspect = _clamp01(min(3.0, w / max(1, h)) / 3.0)
        shape_complexity = _clamp01(abs(var_r - var_b) / max(var_g + 1e-9, 0.01))
        vec.extend([
            brightness, edge_proxy, 0.0, saturation, 0.0,
            shape_complexity, avg_r, avg_g, avg_b, aspect,
        ])
        vec.extend([0.0] * 17)
        vec.extend([0.0] * 6)  # motion facet — zeros for static image
        return vec[:57]
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_sensory_crystal.py:2150",
            exc=_aurora_boundary_exc,
            context={"function": "build_vision_57d_from_image_file", "handler_line": 2150, "source_file": "aurora_internal/aurora_sensory_crystal.py"},
        )
        return None


@dataclass
class CrystalConceptRecord:
    """
    Tracks which modalities (semantic/visual/audio) have been observed for a
    named concept. Gates progression through the unified crystal lifecycle:

        base         — only 1 modality observed
        composite    — ANY 2 of 3 modalities observed
        higher_order — ALL 3 modalities observed
        quasicrystal — all 3 + deep integration (set externally)
    """
    concept: str
    modalities: set = field(default_factory=set)
    stage: str = "base"
    semantic_weight: float = 0.0
    visual_node_ids: List[str] = field(default_factory=list)
    audio_node_ids: List[str] = field(default_factory=list)
    semantic_node_ids: List[str] = field(default_factory=list)
    usage_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def modality_count(self) -> int:
        return len(self.modalities)

    def can_promote_to_composite(self) -> bool:
        return self.stage == "base" and self.modality_count() >= 2

    def can_promote_to_higher_order(self) -> bool:
        return self.stage == "composite" and self.modalities >= {"semantic", "visual", "audio"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "modalities": list(self.modalities),
            "stage": self.stage,
            "semantic_weight": self.semantic_weight,
            "visual_node_ids": self.visual_node_ids,
            "audio_node_ids": self.audio_node_ids,
            "semantic_node_ids": self.semantic_node_ids,
            "usage_count": self.usage_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrystalConceptRecord":
        obj = cls(concept=d["concept"])
        obj.modalities = set(d.get("modalities", []))
        obj.stage = d.get("stage", "base")
        obj.semantic_weight = d.get("semantic_weight", 0.0)
        obj.visual_node_ids = d.get("visual_node_ids", [])
        obj.audio_node_ids = d.get("audio_node_ids", [])
        obj.semantic_node_ids = d.get("semantic_node_ids", [])
        obj.usage_count = d.get("usage_count", 0)
        obj.first_seen = d.get("first_seen", time.time())
        obj.last_seen = d.get("last_seen", time.time())
        return obj
