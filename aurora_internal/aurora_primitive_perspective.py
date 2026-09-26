#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_primitive_perspective.py -- Layer 2.5: primitive internal perspective.

One admitted occurrence, processed through two irreducible access paths before
Aurora has represented anything about what differs between them.

WHAT THIS IS NOT
================
Not a sixth constraint.  Not a sixth representation dimension.  Not a second
DIFFERENCE -- the canonical NonCompDimension.DIFFERENCE keeps its meaning,
depth and 25-channel position untouched, and nothing here compares P0 to P1.
Not personality, emotion, goal, opinion or semantic framing.  Not a logic
brain and a feeling brain.

THE LINEAGE SPLIT IS INFORMATIONAL, NOT A REWEIGHTING
=====================================================
Weighting alone would leave both lineages as transformations of one
generator: multiply the same field by two constants and the second view is
recoverable from the first.  So the lineages differ in WHAT THEY MAY SEE.

    P0  reaction-access      the occurrence as local event impact.
                             Sees frozen local axis PHASE and INERTIA, each
                             response's predicate pole, resonance, depth and
                             react_gain -- the inputs of Aurora's own
                             reactive law (inject_stimulus -> apply_torque).
                             CANNOT see signed displacement, the global
                             polarity field, or any continuity.

    P1  alignment-access     the same occurrence as whole-subject
                             orientation.  Sees signed displacement, depth,
                             align_gain, T-cost, the PRE-occurrence global
                             polarity field, one coherence per being, and the
                             collective's history depth and capacity -- the
                             structure of Aurora's alignment law.  CANNOT see
                             local axis state or resonance.

    Both inspect the shared identity of the occurrence and of each response
    (occurrence, mode, predicate, axis, depth, silent).

    This paragraph is prose, and prose is not the fence.  The authoritative
    lists are P0_ACCESS / P1_ACCESS below, built from the same field tuples
    the views are built from, and a test fails if this paragraph ever claims
    P0 sees displacement or pole weights again.

Neither may see the other's output, finished or partial.  Neither may read
English, concepts, crystals, explicit DIFFERENCE, or any post-occurrence
state produced by this same occurrence.

The fence is enforced by construction, not by discipline: each lineage is
handed a view object that has no attribute for what it may not access.  A
lineage cannot reach past its view because there is nothing there to reach.

NO PRIMITIVE COMPARATOR
=======================
There is no compare(P0, P1), no difference score, no agreement flag, and no
branch anywhere that asks whether the two projections match.  PerspectivePair
is a container: both completed projections and the occurrence identity they
share.  Their coexistence is the whole point.  Aurora's existing relational
and DIFFERENCE machinery may later encounter their descendants and represent
how they relate -- at the depth where that belongs.

SIGNED POLARITY
===============
Never abs-stripped.  Axis projections stay signed end to end; magnitude is
used only where a distribution is explicitly wanted (depth share), and never
written back over the signed value.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

try:                                    # pragma: no cover - import shape only
    from aurora_ivm import ALIGN_GAIN, REACT_GAIN, T_COST_MULTIPLIER, RecursionLevel
except Exception:                       # pragma: no cover
    ALIGN_GAIN = {}
    REACT_GAIN = {}
    T_COST_MULTIPLIER = {}
    RecursionLevel = None               # type: ignore

# The collective's reactive stimulus strength: IStateBeing commit calls
# inject_stimulus(predicate, resonance * 0.3, level).  P0 evaluates that same
# law, so it uses the same coefficient rather than one of its own.
REACTIVE_STIMULUS_SCALE = 0.3

LINEAGE_P0 = "P0"
LINEAGE_P1 = "P1"
LINEAGES: Tuple[str, str] = (LINEAGE_P0, LINEAGE_P1)

# What each lineage is permitted to access.  Written down so the accessibility
# signature can be derived from it and a silent change to the fence shows up
# as a changed signature in persisted state.
# THE FENCE, LITERALLY.  Each lineage's access list is not a description kept
# beside the views -- it is built FROM the same field tuples the views are
# built from.  What ACCESS says exists = what the view physically holds = what
# the tests vary.  A field absent from these tuples does not exist inside that
# lineage's view: there is no attribute for it and no row key for it.
#
# View-level fields describe the occurrence as a whole; row-level fields
# describe one committed response.  `silent` is listed explicitly for both:
# each lineage inspects it, so it belongs in both signatures.
#
# P0 carries phase itself rather than the pole weights or cos(phase): on a
# ToroidalAxis those are functions of phase, so listing them was listing one
# window several times.  P0 carries no displacement: Aurora's reactive law
# does not use it, and a P0 that can SEE displacement could begin using it
# without anything here changing.
P0_VIEW_FIELDS: Tuple[str, ...] = ("occurrence_id", "existence_mode")
P0_ROW_FIELDS: Tuple[str, ...] = (
    "predicate", "constraint_axis", "polarity", "recursion_level", "silent",
    "resonance", "local_axis_phase", "local_axis_inertia", "react_gain",
)
P1_VIEW_FIELDS: Tuple[str, ...] = (
    "occurrence_id", "existence_mode", "pre_global_polarity",
    "collective_history_depth", "collective_history_capacity",
)
P1_ROW_FIELDS: Tuple[str, ...] = (
    "predicate", "constraint_axis", "recursion_level", "silent",
    "constraint_displacement", "align_gain", "t_cost", "being_coherence",
)
P0_ACCESS: Tuple[str, ...] = P0_VIEW_FIELDS + P0_ROW_FIELDS
P1_ACCESS: Tuple[str, ...] = P1_VIEW_FIELDS + P1_ROW_FIELDS

# What freeze() keeps.  Only fields capable of shaping a lineage (plus the
# frozen observations, which ARE the occurrence).  Anything else a caller
# passes -- generation counts, processed totals, synthesis counts -- is
# dropped at the door, so it can neither leak into a view nor perturb the
# digest of an informationally identical state.
FROZEN_AXIS_FIELDS: Tuple[str, ...] = ("phase", "inertia")
FROZEN_BEING_FIELDS: Tuple[str, ...] = ("coherence",)
FROZEN_COLLECTIVE_FIELDS: Tuple[str, ...] = ("history_depth", "history_capacity")
FROZEN_OBSERVATION_FIELDS: Tuple[str, ...] = ("silent", "resonance",
                                              "constraint_displacement")

# Fields a projection may never carry.  Asserted at construction, not only in
# tests: the perspective layer is not allowed to explain itself yet.
FORBIDDEN_PROJECTION_FIELDS = frozenset({
    "difference_score", "difference", "meaning", "interpretation",
    "conclusion", "emotion", "emotion_label", "concept", "concept_label",
    "semantic_role", "correctness", "correct", "judgment", "agreement",
    "disagreement", "score", "verdict",
})


def _plain(value: Any) -> Any:
    """Normalise a value for hashing: every Mapping (dict, MappingProxyType,
    anything) becomes a plain dict so sort_keys can order its contents;
    tuples become lists; enums become their names.

    Without this, json.dumps(default=str) turned a MappingProxyType into its
    string representation BEFORE sort_keys could normalise it, so identical
    information inserted in a different order hashed differently.
    """
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "name") and hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return str(value.name)
    return value


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(_plain(payload), sort_keys=True, default=str)
                          .encode("utf-8")).hexdigest()[:16]


def _signature(access: Sequence[str]) -> str:
    raw = "|".join(sorted(access))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _level_name(level: Any) -> str:
    return getattr(level, "name", str(level))


def _gain(table: Mapping[Any, float], level: Any, default: float) -> float:
    if not table:
        return default
    if level in table:
        return float(table[level])
    for key, value in table.items():
        if _level_name(key) == _level_name(level):
            return float(value)
    return default


# ---------------------------------------------------------------------------
# The frozen occurrence
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrimitiveOccurrenceSnapshot:
    """One admitted occurrence, frozen before either lineage touches it.

    Primitive/system-native information only.  No parsed concepts, no topic
    words, no intents or emotions inferred from English, no response drafts,
    no downstream semantic objects.
    """
    occurrence_id: str
    node_id: str
    existence_mode: str
    lattice_axes: Mapping[str, Mapping[str, Any]]
    observations: Mapping[str, Mapping[str, Any]]
    pre_global_polarity: Mapping[str, float]
    being_continuity: Mapping[str, Mapping[str, float]]
    collective_continuity: Mapping[str, float]
    captured_at: float = field(default_factory=time.time)

    def digest(self) -> str:
        """Identity of the frozen occurrence: EVERY frozen field, since every
        one of them can shape a lineage.  captured_at is deliberately left
        out, so two informationally identical states hash identically.

        The earlier digest omitted the global polarity field and both
        continuity summaries -- P1's essential inputs -- so two snapshots that
        generated different P1 views could share a digest.
        """
        return _stable_digest({
            "occurrence_id": self.occurrence_id,
            "node_id": self.node_id,
            "existence_mode": self.existence_mode,
            "lattice_axes": {k: dict(v) for k, v in self.lattice_axes.items()},
            "observations": {k: dict(v) for k, v in self.observations.items()},
            "pre_global_polarity": dict(self.pre_global_polarity),
            "being_continuity": {k: dict(v) for k, v in self.being_continuity.items()},
            "collective_continuity": dict(self.collective_continuity),
        })


# ---------------------------------------------------------------------------
# Access views -- the fence, as objects
# ---------------------------------------------------------------------------

class _AccessView:
    """A lineage's entire field of view.

    __slots__ means no attribute can exist on a view beyond the declared
    view fields and `rows`.  Each row is built from the lineage's row-field
    tuple and checked against it, then frozen read-only.  Whatever a lineage
    can inspect is therefore exactly its ACCESS list -- by construction.
    """

    __slots__ = ("rows",)
    VIEW_FIELDS: Tuple[str, ...] = ()
    ROW_FIELDS: Tuple[str, ...] = ()

    @property
    def access(self) -> Tuple[str, ...]:
        return self.VIEW_FIELDS + self.ROW_FIELDS

    def _freeze_rows(self, rows: Sequence[Dict[str, Any]]) -> None:
        for row in rows:
            if tuple(row) != self.ROW_FIELDS:
                raise AssertionError(
                    f"{type(self).__name__} row fields {tuple(row)} != declared "
                    f"{self.ROW_FIELDS}: a view may hold exactly its access, no more")
        self.rows = tuple(MappingProxyType(dict(row)) for row in rows)

    def contents(self) -> Dict[str, Any]:
        """Everything this lineage can inspect -- used for the formation
        digest, so provenance covers exactly the generating inputs."""
        return {
            "view": {name: getattr(self, name) for name in self.VIEW_FIELDS},
            "rows": [dict(row) for row in self.rows],
        }


def _response_axis(response: Any) -> str:
    return getattr(response, "constraint_axis", "") or getattr(response, "axis", "")


class _ReactionAccessView(_AccessView):
    """Everything P0 may see, and nothing else: local event impact.

    No global polarity field, no continuity of any kind, no displacement.
    """

    __slots__ = P0_VIEW_FIELDS
    VIEW_FIELDS = P0_VIEW_FIELDS
    ROW_FIELDS = P0_ROW_FIELDS

    def __init__(self, snapshot: PrimitiveOccurrenceSnapshot,
                 responses: Mapping[str, Any]) -> None:
        self.occurrence_id = snapshot.occurrence_id
        self.existence_mode = snapshot.existence_mode
        rows = []
        for predicate, response in sorted(responses.items()):
            axis = _response_axis(response)
            local = snapshot.lattice_axes.get(axis, {})
            level = getattr(response, "recursion_level", None)
            rows.append({
                "predicate": predicate,
                "constraint_axis": axis,
                "polarity": str(getattr(response, "polarity", "") or ""),
                "recursion_level": level,
                "silent": bool(getattr(response, "silent", False)),
                "resonance": float(getattr(response, "resonance", 0.0) or 0.0),
                "local_axis_phase": float(local.get("phase", 0.0) or 0.0),
                "local_axis_inertia": float(local.get("inertia", 1.0) or 1.0),
                "react_gain": _gain(REACT_GAIN, level, 1.0),
            })
        self._freeze_rows(rows)


class _AlignmentAccessView(_AccessView):
    """Everything P1 may see, and nothing else: whole-subject orientation.

    No local axis state, no resonance.  Continuity is exactly one coherence
    per being and the collective's history depth and capacity -- not the
    whole summaries production keeps.
    """

    __slots__ = P1_VIEW_FIELDS
    VIEW_FIELDS = P1_VIEW_FIELDS
    ROW_FIELDS = P1_ROW_FIELDS

    def __init__(self, snapshot: PrimitiveOccurrenceSnapshot,
                 responses: Mapping[str, Any]) -> None:
        self.occurrence_id = snapshot.occurrence_id
        self.existence_mode = snapshot.existence_mode
        self.pre_global_polarity = MappingProxyType({
            str(k): float(v) for k, v in dict(snapshot.pre_global_polarity).items()})
        collective = dict(snapshot.collective_continuity)
        self.collective_history_depth = float(collective.get("history_depth", 0.0) or 0.0)
        self.collective_history_capacity = float(collective.get("history_capacity", 0.0) or 0.0)
        rows = []
        for predicate, response in sorted(responses.items()):
            level = getattr(response, "recursion_level", None)
            rows.append({
                "predicate": predicate,
                "constraint_axis": _response_axis(response),
                "recursion_level": level,
                "silent": bool(getattr(response, "silent", False)),
                "constraint_displacement": float(
                    getattr(response, "constraint_displacement", 0.0) or 0.0),
                "align_gain": _gain(ALIGN_GAIN, level, 0.0001),
                "t_cost": _gain(T_COST_MULTIPLIER, level, 1.0),
                "being_coherence": float(
                    dict(snapshot.being_continuity.get(predicate, {})).get("coherence", 1.0)),
            })
        self._freeze_rows(rows)


# ---------------------------------------------------------------------------
# Projections
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerspectiveProjection:
    """One lineage's pre-semantic view of one occurrence."""
    lineage_id: str
    occurrence_id: str
    source_mode: str
    predicate_activation: Mapping[str, float]
    axis_projection: Mapping[str, float]
    depth_distribution: Mapping[str, float]
    continuity_indicators: Mapping[str, float]
    accessibility_signature: str
    coherence: float
    maturity: float
    provenance: Tuple[str, ...]
    formed_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        for name in FORBIDDEN_PROJECTION_FIELDS:
            if name in self.predicate_activation or name in self.axis_projection:
                raise ValueError(f"projection may not carry '{name}'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "source_mode": self.source_mode,
            "predicate_activation": {k: round(v, 6) for k, v in
                                     sorted(self.predicate_activation.items())},
            "axis_projection": {k: round(v, 6) for k, v in
                                sorted(self.axis_projection.items())},
            "depth_distribution": {k: round(v, 6) for k, v in
                                   sorted(self.depth_distribution.items())},
            "continuity_indicators": {k: round(v, 6) for k, v in
                                      sorted(self.continuity_indicators.items())},
            "accessibility_signature": self.accessibility_signature,
            "coherence": round(self.coherence, 6),
            "maturity": round(self.maturity, 6),
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class PerspectivePair:
    """Both completed projections and the occurrence they share.

    A container.  It has no comparator, no difference field, and no method
    that asks whether the two agree -- that relation belongs to Aurora's
    existing representational machinery, at its own depth.
    """
    occurrence_id: str
    p0: PerspectiveProjection
    p1: PerspectiveProjection
    snapshot_digest: str = ""
    # Three identities, each named for exactly what it proves:
    #   snapshot_digest   the frozen occurrence (every frozen field except
    #                     the capture time).
    #   access_digest     OCCURRENCE-ACCESS inputs only: both views' complete
    #                     contents, committed responses included.  Identical
    #                     across engines with different histories.
    #   formation_digest  EVERYTHING responsible for this exact pair: the
    #                     access inputs plus each lineage's pre-formation
    #                     development (the only state a projection can read).
    #                     Equal formation digests mean equal outputs.
    access_digest: str = ""
    formation_digest: str = ""
    formed_at: float = field(default_factory=time.time)

    def get(self, lineage_id: str) -> Optional[PerspectiveProjection]:
        return {LINEAGE_P0: self.p0, LINEAGE_P1: self.p1}.get(str(lineage_id))

    def to_dict(self) -> Dict[str, Any]:
        return {"occurrence_id": self.occurrence_id,
                "snapshot_digest": self.snapshot_digest,
                "access_digest": self.access_digest,
                "formation_digest": self.formation_digest,
                "P0": self.p0.to_dict(), "P1": self.p1.to_dict()}


# ---------------------------------------------------------------------------
# Lineage development
# ---------------------------------------------------------------------------

def _maturity(occurrences: int) -> float:
    """Saturating, bounded, and a pure function of this lineage's own count."""
    return 1.0 - math.exp(-int(occurrences) / 48.0)


def _calibration(magnitude_mean: float) -> float:
    """Scale keeping a lineage's projections comparable to ITS OWN history."""
    return 1.0 if float(magnitude_mean) <= 1e-9 else float(magnitude_mean)


# The only pieces of a lineage's pre-existing development that can shape its
# projection.  Projections receive a view holding exactly these, so the
# formation digest can name everything responsible for an output.
LINEAGE_DEVELOPMENT_FIELDS: Tuple[str, ...] = ("occurrences", "magnitude_mean")


class _DevelopmentView:
    """A lineage's pre-formation development, fenced like its access view.

    Captured BEFORE either lineage projects (and before either absorbs), so
    it is the same whichever lineage runs first.  Holds exactly
    LINEAGE_DEVELOPMENT_FIELDS; axis_recurrence, timestamps and the rest of
    the lineage state are out of reach.
    """

    __slots__ = LINEAGE_DEVELOPMENT_FIELDS

    def __init__(self, occurrences: int, magnitude_mean: float) -> None:
        self.occurrences = int(occurrences)
        self.magnitude_mean = float(magnitude_mean)

    @property
    def maturity(self) -> float:
        return _maturity(self.occurrences)

    def calibration(self) -> float:
        return _calibration(self.magnitude_mean)

    def contents(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in LINEAGE_DEVELOPMENT_FIELDS}


@dataclass
class PerspectiveLineageState:
    """A lineage's own history.  Never merged with, or copied from, the other.

    Development permitted here is calibration, recurrence sensitivity and
    maturity -- never the other lineage's internal state, never a shared
    transform, never an average of both histories.
    """
    lineage_id: str
    occurrences: int = 0
    magnitude_mean: float = 0.0
    axis_recurrence: Dict[str, int] = field(default_factory=dict)
    accessibility_signature: str = ""
    last_occurrence_id: str = ""
    updated_at: float = 0.0

    @property
    def maturity(self) -> float:
        return _maturity(self.occurrences)

    def calibration(self) -> float:
        return _calibration(self.magnitude_mean)

    def development_view(self) -> "_DevelopmentView":
        return _DevelopmentView(self.occurrences, self.magnitude_mean)

    def absorb(self, projection: PerspectiveProjection) -> None:
        magnitude = sum(abs(v) for v in projection.axis_projection.values())
        self.occurrences += 1
        rate = 1.0 / min(self.occurrences, 64)
        self.magnitude_mean += rate * (magnitude - self.magnitude_mean)
        for axis, value in projection.axis_projection.items():
            if abs(value) > 1e-9:
                self.axis_recurrence[axis] = self.axis_recurrence.get(axis, 0) + 1
        self.accessibility_signature = projection.accessibility_signature
        self.last_occurrence_id = projection.occurrence_id
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {"lineage_id": self.lineage_id, "occurrences": self.occurrences,
                "magnitude_mean": self.magnitude_mean,
                "axis_recurrence": dict(self.axis_recurrence),
                "accessibility_signature": self.accessibility_signature,
                "last_occurrence_id": self.last_occurrence_id,
                "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PerspectiveLineageState":
        state = cls(lineage_id=str(raw.get("lineage_id", "")))
        state.occurrences = int(raw.get("occurrences", 0))
        state.magnitude_mean = float(raw.get("magnitude_mean", 0.0))
        state.axis_recurrence = {str(k): int(v) for k, v in
                                 (raw.get("axis_recurrence") or {}).items()}
        state.accessibility_signature = str(raw.get("accessibility_signature", ""))
        state.last_occurrence_id = str(raw.get("last_occurrence_id", ""))
        state.updated_at = float(raw.get("updated_at", 0.0))
        return state


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class PrimitivePerspectiveEngine:
    """Freezes one occurrence and forms two independent primitive views."""

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self.state_dir = state_dir
        self._lock = threading.RLock()
        self.states: Dict[str, PerspectiveLineageState] = {
            LINEAGE_P0: PerspectiveLineageState(LINEAGE_P0),
            LINEAGE_P1: PerspectiveLineageState(LINEAGE_P1),
        }
        self.formed = 0
        self.last_pair: Optional[PerspectivePair] = None
        self._load()

    # -- freeze ------------------------------------------------------------

    @staticmethod
    def freeze(envelope: Any, observations: Mapping[str, Any], *,
               lattice_axes: Mapping[str, Mapping[str, Any]],
               global_polarity: Mapping[str, float],
               being_continuity: Mapping[str, Mapping[str, float]],
               collective_continuity: Mapping[str, float],
               occurrence_id: str = "") -> PrimitiveOccurrenceSnapshot:
        """Capture the occurrence BEFORE commit, so no same-generation lattice
        consequence can contaminate either lineage."""
        node_id = str(getattr(envelope, "node_id", "") or "")
        mode = getattr(envelope, "mode", None)
        frozen_observations = {
            str(predicate): {
                "silent": bool(getattr(observation, "silent", False)),
                "resonance": float(getattr(observation, "resonance", 0.0) or 0.0),
                "constraint_displacement": float(
                    getattr(observation, "constraint_displacement", 0.0) or 0.0),
            }
            for predicate, observation in (observations or {}).items()
        }

        def _keep(mapping: Any, fields: Sequence[str]) -> Dict[str, Any]:
            source = dict(mapping or {})
            return {name: source[name] for name in fields if name in source}
        return PrimitiveOccurrenceSnapshot(
            occurrence_id=str(occurrence_id or node_id),
            node_id=node_id,
            existence_mode=getattr(mode, "name", str(mode)),
            lattice_axes={str(k): _keep(v, FROZEN_AXIS_FIELDS)
                          for k, v in (lattice_axes or {}).items()},
            observations=frozen_observations,
            pre_global_polarity={str(k): float(v) for k, v in
                                 dict(global_polarity or {}).items()},
            being_continuity={str(k): _keep(v, FROZEN_BEING_FIELDS)
                              for k, v in (being_continuity or {}).items()},
            collective_continuity={k: float(v) for k, v in
                                   _keep(collective_continuity, FROZEN_COLLECTIVE_FIELDS).items()},
        )

    # -- the two lineages --------------------------------------------------

    @staticmethod
    def _reactive_impulse(row: Mapping[str, Any]) -> float:
        """Aurora's own reactive law, evaluated on the FROZEN axis.

        Exactly what commit does to the local axis, without doing it:
        IStateBeing commit calls inject_stimulus(predicate, resonance * 0.3,
        level), which calls ToroidalAxis.apply_torque with REACT_GAIN[level].
        apply_torque turns toward the predicate's own pole the short way round
        the torus -- so the sign depends on which half the axis currently
        sits in (phase above or below pi) -- and divides by the axis's
        inertia.  The result is the signed angular impulse this response
        would give its local axis: local event impact in Aurora's physics.
        """
        phase = float(row["local_axis_phase"]) % (2.0 * math.pi)
        inertia = float(row["local_axis_inertia"]) or 1.0
        effective = row["resonance"] * REACTIVE_STIMULUS_SCALE * row["react_gain"]
        toward_positive = not str(row["polarity"]).lower().startswith("neg")
        if toward_positive:
            direction = 1.0 if phase > math.pi else -1.0
        else:
            direction = 1.0 if phase < math.pi else -1.0
        return direction * effective / inertia

    def _project_p0(self, view: _ReactionAccessView,
                    development: _DevelopmentView) -> PerspectiveProjection:
        """Local event impact: the signed impulse each response would give its
        local axis under Aurora's reactive law.  REACT_GAIN makes SURFACE and
        SHALLOW effects naturally more available; nothing here says what that
        means."""
        state = development
        axis_projection: Dict[str, float] = {}
        activation: Dict[str, float] = {}
        depth: Dict[str, float] = {}
        provenance = []
        for row in view.rows:
            if row["silent"]:
                continue
            signed = self._reactive_impulse(row)
            axis = row["constraint_axis"] or "?"
            axis_projection[axis] = axis_projection.get(axis, 0.0) + signed
            activation[row["predicate"]] = signed
            level = _level_name(row["recursion_level"])
            depth[level] = depth.get(level, 0.0) + abs(signed)
            provenance.append(row["predicate"])
        total = sum(depth.values())
        depth = {k: v / total for k, v in depth.items()} if total else depth
        return PerspectiveProjection(
            lineage_id=LINEAGE_P0, occurrence_id=view.occurrence_id,
            source_mode=view.existence_mode,
            predicate_activation=activation, axis_projection=axis_projection,
            depth_distribution=depth, continuity_indicators={},
            accessibility_signature=_signature(view.access),
            coherence=min(1.0, total / max(state.calibration(), 1e-9))
            if total else 0.0,
            maturity=state.maturity, provenance=tuple(provenance),
        )

    @staticmethod
    def _orientation_anchor(depth: float, capacity: float) -> float:
        """How established the whole-subject orientation is.

        The collective's continuity memory is a bounded history of past
        syntheses.  A subject that has lived no occurrences has a polarity
        field but no orientation EARNED through experience; one whose memory
        window is full has a fully established one.  The anchor is the fraction
        of that native window filled.  (The linear form is this layer's
        modelling choice; both quantities are the collective's own.)
        """
        if capacity <= 0.0:
            return 1.0
        return max(0.0, min(1.0, depth / capacity))

    def _project_p1(self, view: _AlignmentAccessView,
                    development: _DevelopmentView) -> PerspectiveProjection:
        """Whole-subject orientation.

        Mirrors the STRUCTURE of Aurora's alignment law,
        ToroidalAxis.apply_alignment_torque: mismatch = global - local,
        scaled by ALIGN_GAIN, with T-cost charged.  P1 is not granted local
        axis state, so the occurrence's own signed displacement stands where
        local polarity stands: how far this occurrence's push sits from where
        the subject is (anchored-)oriented.  That substitution is deliberate
        and is the reason this is a structural mirror, not a verbatim call.

        T-cost enters as it does in the native law: it does not steer the
        pull, it prices it.  It therefore shapes depth_distribution -- where
        alignment spends temporal energy -- not the signed axis projection.
        """
        state = development
        anchor = self._orientation_anchor(view.collective_history_depth,
                                          view.collective_history_capacity)
        axis_projection: Dict[str, float] = {}
        activation: Dict[str, float] = {}
        depth: Dict[str, float] = {}
        indicators: Dict[str, float] = {"orientation_anchor": anchor}
        provenance = []
        for row in view.rows:
            if row["silent"]:
                continue
            gain = row["align_gain"]
            t_cost = row["t_cost"]
            axis = row["constraint_axis"] or "?"
            oriented = anchor * float(view.pre_global_polarity.get(axis, 0.0))
            coherence = row["being_coherence"]
            mismatch = oriented - row["constraint_displacement"]          # signed
            signed = mismatch * gain * (0.5 + 0.5 * coherence)
            axis_projection[axis] = axis_projection.get(axis, 0.0) + signed
            activation[row["predicate"]] = signed
            level = _level_name(row["recursion_level"])
            depth[level] = depth.get(level, 0.0) + abs(signed) * t_cost
            indicators.setdefault(f"oriented:{axis}", oriented)
            provenance.append(row["predicate"])
        total = sum(depth.values())
        depth = {k: v / total for k, v in depth.items()} if total else depth
        magnitude = sum(abs(v) for v in axis_projection.values())
        return PerspectiveProjection(
            lineage_id=LINEAGE_P1, occurrence_id=view.occurrence_id,
            source_mode=view.existence_mode,
            predicate_activation=activation, axis_projection=axis_projection,
            depth_distribution=depth, continuity_indicators=indicators,
            accessibility_signature=_signature(view.access),
            coherence=min(1.0, magnitude / max(state.calibration(), 1e-9))
            if magnitude else 0.0,
            maturity=state.maturity, provenance=tuple(provenance),
        )

    # -- forming -----------------------------------------------------------

    def form(self, snapshot: PrimitiveOccurrenceSnapshot,
             responses: Mapping[str, Any], *,
             order: Sequence[str] = LINEAGES) -> PerspectivePair:
        """Form both projections from the frozen occurrence.

        `order` exists so execution order can be varied in tests.  Meaning is
        invariant to it: each lineage reads only its own view and its own
        pre-existing state, and BOTH state updates are applied only after both
        projections are complete -- so neither can ever develop on the back of
        the other's turn having gone first.
        """
        views = {
            LINEAGE_P0: _ReactionAccessView(snapshot, responses),
            LINEAGE_P1: _AlignmentAccessView(snapshot, responses),
        }
        # Development is captured once, BEFORE either lineage projects, so it
        # is identical whichever order the lineages run in.
        development = {lineage: self.states[lineage].development_view()
                       for lineage in LINEAGES}
        builders = {
            LINEAGE_P0: lambda: self._project_p0(views[LINEAGE_P0],
                                                 development[LINEAGE_P0]),
            LINEAGE_P1: lambda: self._project_p1(views[LINEAGE_P1],
                                                 development[LINEAGE_P1]),
        }
        access_digest = _stable_digest(
            {lineage: view.contents() for lineage, view in views.items()})
        projections: Dict[str, PerspectiveProjection] = {}
        for lineage_id in order:
            if lineage_id in builders:
                projections[lineage_id] = builders[lineage_id]()

        with self._lock:
            for lineage_id in LINEAGES:                 # canonical order
                if lineage_id in projections:
                    self.states[lineage_id].absorb(projections[lineage_id])
            self.formed += 1
            pair = PerspectivePair(
                occurrence_id=snapshot.occurrence_id,
                p0=projections[LINEAGE_P0], p1=projections[LINEAGE_P1],
                snapshot_digest=snapshot.digest(),
                access_digest=access_digest,
                formation_digest=_stable_digest({
                    "access": access_digest,
                    "development": {lineage: dev.contents()
                                    for lineage, dev in development.items()},
                }))
            self.last_pair = pair
        self.save()
        return pair

    # -- persistence -------------------------------------------------------

    @property
    def path(self) -> Optional[str]:
        return os.path.join(self.state_dir, "perspective_lineages.json") \
            if self.state_dir else None

    def _load(self) -> None:
        path = self.path
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            return
        for lineage_id, payload in (raw.get("lineages") or {}).items():
            if lineage_id in self.states:
                self.states[lineage_id] = PerspectiveLineageState.from_dict(payload)
        self.formed = int(raw.get("formed", 0))

    def save(self) -> None:
        path = self.path
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            payload = {"formed": self.formed,
                       "lineages": {k: v.to_dict() for k, v in self.states.items()}}
            handle = tempfile.NamedTemporaryFile(
                "w", dir=os.path.dirname(path), delete=False, encoding="utf-8")
            with handle as out:
                json.dump(payload, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(handle.name, path)
        except Exception:
            return

    # -- diagnostics (read-only) -------------------------------------------

    def diagnostics(self, pair: Optional[PerspectivePair] = None) -> Dict[str, Any]:
        """Read-only. No value here feeds back into development: absorb() is
        driven by projections alone, never by anything reported here."""
        pair = pair or self.last_pair
        out: Dict[str, Any] = {
            "formed": self.formed,
            "lineage_maturity": {k: round(v.maturity, 6)
                                 for k, v in self.states.items()},
            "lineage_occurrences": {k: v.occurrences for k, v in self.states.items()},
            "accessibility_signatures": {
                LINEAGE_P0: _signature(P0_ACCESS), LINEAGE_P1: _signature(P1_ACCESS)},
        }
        if pair is not None:
            out.update({
                "occurrence_id": pair.occurrence_id,
                "P0_axis_projection": dict(pair.p0.axis_projection),
                "P1_axis_projection": dict(pair.p1.axis_projection),
                "P0_source_predicates": list(pair.p0.provenance),
                "P1_source_predicates": list(pair.p1.provenance),
                "P0_depth_distribution": dict(pair.p0.depth_distribution),
                "P1_depth_distribution": dict(pair.p1.depth_distribution),
            })
        return out
