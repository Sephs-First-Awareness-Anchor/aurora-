# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/semantic_variant_registry.py
============================================================
SemanticVariantRegistry — MTSL Phase 2 (2026-07-13), spec section
5-6.3/9/10. NO AUTHORITY: this module stores and matches organization,
it never decides meaning, salience, or response (that's Phase 4/5).

Semantic Variants (SV = BMF + MC + TS + context family + outcome
evidence) live in the existing crystal architecture
(aurora_dimensional_systems.CrystalProcessingSystem / Crystal), not a
parallel database (spec non-goal):

    Parent: the existing `tensor:<slot_id>` coordinate crystal
    (cers_tensor_locator.py conventions).
    Child:  `tensor_variant:<slot_id>:<topology_id>`, one crystal per
    distinct organization observed at that coordinate. Its full state
    is held in a single "variant_state" facet whose `content` this
    module owns and mutates directly -- Crystal.add_facet() only
    strengthens confidence on a repeated role, it never overwrites
    content, so updates locate the existing facet object and mutate it
    in place. Same direct-mutation idiom cers_tensor_locator.py uses
    for constraint_signature.

`semantic_variant_index.json` is a compact, disposable index
(MC -> [{variant_id, topology_id, status}]) for fast candidate lookup
without walking every crystal -- never the source of truth; the
crystal facet is. If the index is lost, matching degrades to "no
candidates found, create fresh" rather than losing data (crystals are
still there for direct lookup by id).

Design choices not pinned down by the directive's own text (the full
external spec section wasn't available to this implementation) are
first-pass, documented decisions flagged inline -- same posture as
topology_frame.py's crest/trough axes. Matching thresholds
(SAME/FAMILY) are the directive's own numbers; the per-dimension
weights and lifecycle counts are this implementation's first pass,
"to be calibrated from lived history" per the directive's own words
about the thresholds.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .subsurface_state import clip01
from .topology_tracker import TopologyFingerprint, TopologySignature, _canon

SCHEMA_VERSION = 1
INDEX_FILENAME = "semantic_variant_index.json"

# Matching thresholds (directive section 5) -- "to be calibrated from
# lived history" per the directive's own words.
SAME_THRESHOLD = 0.82
FAMILY_THRESHOLD = 0.65

# Matching component weights over spec 9's dimensions (first-pass; not
# spec-pinned). Sum to 1.0.
_W_AXES = 0.20
_W_EDGES = 0.25
_W_LOOPS = 0.15
_W_ORDER = 0.10
_W_ROLES = 0.15
_W_PATTERN = 0.15
assert abs((_W_AXES + _W_EDGES + _W_LOOPS + _W_ORDER + _W_ROLES + _W_PATTERN) - 1.0) < 1e-9

# Context family is blended in on top of the topology-similarity score,
# weighted less than the organization match itself (first-pass).
_W_CONTEXT = 0.15
_W_TS = 1.0 - _W_CONTEXT

# Lifecycle thresholds (directive section 5 / FIX-A012).
REINFORCE_MIN_OBSERVATIONS = 3          # first-pass: provisional -> reinforced
PROMOTE_MIN_OBSERVATIONS = 8
PROMOTE_MIN_CONTEXT_FAMILIES = 3
PROMOTE_MIN_OUTCOME_SUPPORT = 0.60
PROMOTE_MIN_RESTART_SURVIVALS = 2       # ">= 2 process restarts" (directive section 5)

_QUIESCENT_REGIME = "quiescent"
_EVIDENCE_CAP = 20                      # cap on dream/classroom evidence entries kept per variant


def _edges_of(path: Tuple[str, ...]) -> frozenset:
    if len(path) < 2:
        return frozenset()
    return frozenset((path[i], path[(i + 1) % len(path)]) for i in range(len(path)))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


@dataclass(frozen=True)
class TopologyProfile:
    """Compact, storable summary of a TopologySignature -- used for both
    persistence (the variant crystal's topology_profile field) and
    matching. Deliberately smaller than the full TopologySignature:
    only the fields the directive's matching dimensions (spec 9)
    actually need (active axes, directed edges via loop paths, loop
    membership, source/sink roles, order, creation/dissipation
    pattern via regime + circulation_fraction)."""
    active_axes: Tuple[str, ...]
    loop_paths: Tuple[Tuple[str, ...], ...]
    sources: Tuple[str, ...]
    sinks: Tuple[str, ...]
    regime: str
    circulation_fraction: float

    @classmethod
    def from_signature(cls, sig: TopologySignature) -> "TopologyProfile":
        axes = sorted({a for path, _ in sig.loops for a in path} | set(sig.sources) | set(sig.sinks))
        return cls(
            active_axes=tuple(axes),
            loop_paths=tuple(tuple(path) for path, _ in sig.loops),
            sources=tuple(sig.sources),
            sinks=tuple(sig.sinks),
            regime=sig.regime,
            circulation_fraction=round(float(sig.circulation_fraction), 4),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_axes": list(self.active_axes),
            "loop_paths": [list(p) for p in self.loop_paths],
            "sources": list(self.sources),
            "sinks": list(self.sinks),
            "regime": self.regime,
            "circulation_fraction": self.circulation_fraction,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TopologyProfile":
        return cls(
            active_axes=tuple(d.get("active_axes", []) or []),
            loop_paths=tuple(tuple(p) for p in (d.get("loop_paths", []) or [])),
            sources=tuple(d.get("sources", []) or []),
            sinks=tuple(d.get("sinks", []) or []),
            regime=str(d.get("regime", "") or ""),
            circulation_fraction=float(d.get("circulation_fraction", 0.0) or 0.0),
        )


def topology_similarity(a: TopologyProfile, b: TopologyProfile) -> float:
    """Weighted similarity over spec 9's matching dimensions (context
    family excluded here -- blended in separately, see _combined_score).
    All components are 0..1; weights sum to 1.0."""
    axes_score = _jaccard(frozenset(a.active_axes), frozenset(b.active_axes))

    a_edges = frozenset().union(*(_edges_of(p) for p in a.loop_paths)) if a.loop_paths else frozenset()
    b_edges = frozenset().union(*(_edges_of(p) for p in b.loop_paths)) if b.loop_paths else frozenset()
    edges_score = _jaccard(a_edges, b_edges)

    a_loop_sets = frozenset(frozenset(p) for p in a.loop_paths)
    b_loop_sets = frozenset(frozenset(p) for p in b.loop_paths)
    loops_score = _jaccard(a_loop_sets, b_loop_sets)

    if a.loop_paths and b.loop_paths:
        if _canon(a.loop_paths[0]) == _canon(b.loop_paths[0]):
            order_score = 1.0
        elif set(a.loop_paths[0]) == set(b.loop_paths[0]):
            order_score = 0.5
        else:
            order_score = 0.0
    elif not a.loop_paths and not b.loop_paths:
        order_score = 1.0
    else:
        order_score = 0.0

    roles_score = _jaccard(
        frozenset(a.sources) | frozenset(a.sinks),
        frozenset(b.sources) | frozenset(b.sinks),
    )

    regime_match = 1.0 if a.regime == b.regime else 0.0
    circ_closeness = 1.0 - min(1.0, abs(a.circulation_fraction - b.circulation_fraction))
    pattern_score = 0.5 * regime_match + 0.5 * circ_closeness

    return round(
        _W_AXES * axes_score + _W_EDGES * edges_score + _W_LOOPS * loops_score +
        _W_ORDER * order_score + _W_ROLES * roles_score + _W_PATTERN * pattern_score,
        4,
    )


@dataclass
class SemanticVariant:
    """SV = BMF + MC + TS + context family + outcome evidence (directive
    section 1). Mutable -- registry methods update fields in place and
    persist the result; callers should treat the object returned from a
    registry call as the current state, not hold stale copies."""
    variant_id: str
    manifold_slot_id: str
    topology_id: str
    topology_profile: TopologyProfile
    base_meaning_form: str
    context_families: Tuple[str, ...] = ()
    meaning_candidates: Dict[str, float] = field(default_factory=dict)
    dream_evidence: Tuple[Dict[str, Any], ...] = ()
    classroom_evidence: Tuple[Dict[str, Any], ...] = ()
    genealogical_links: Tuple[str, ...] = ()
    observation_count: int = 0
    outcome_positive: int = 0
    outcome_negative: int = 0
    contradiction_count: int = 0
    confidence: float = 0.0
    status: str = "provisional"
    restart_survivals: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    merged_into: Optional[str] = None
    split_from: Optional[str] = None

    @property
    def outcome_support(self) -> float:
        total = self.outcome_positive + self.outcome_negative
        if total <= 0:
            return 0.5  # neutral prior -- no evidence yet, matches CrystalFacet's default confidence
        return round(self.outcome_positive / total, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "variant_id": self.variant_id,
            "manifold_slot_id": self.manifold_slot_id,
            "topology_id": self.topology_id,
            "topology_profile": self.topology_profile.to_dict(),
            "base_meaning_form": self.base_meaning_form,
            "context_families": list(self.context_families),
            "meaning_candidates": dict(self.meaning_candidates),
            "dream_evidence": list(self.dream_evidence),
            "classroom_evidence": list(self.classroom_evidence),
            "genealogical_links": list(self.genealogical_links),
            "observation_count": self.observation_count,
            "outcome_positive": self.outcome_positive,
            "outcome_negative": self.outcome_negative,
            "contradiction_count": self.contradiction_count,
            "confidence": self.confidence,
            "status": self.status,
            "restart_survivals": self.restart_survivals,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "merged_into": self.merged_into,
            "split_from": self.split_from,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticVariant":
        return cls(
            variant_id=str(d.get("variant_id", "") or ""),
            manifold_slot_id=str(d.get("manifold_slot_id", "") or ""),
            topology_id=str(d.get("topology_id", "") or ""),
            topology_profile=TopologyProfile.from_dict(d.get("topology_profile", {}) or {}),
            base_meaning_form=str(d.get("base_meaning_form", "") or ""),
            context_families=tuple(d.get("context_families", []) or []),
            meaning_candidates=dict(d.get("meaning_candidates", {}) or {}),
            dream_evidence=tuple(d.get("dream_evidence", []) or []),
            classroom_evidence=tuple(d.get("classroom_evidence", []) or []),
            genealogical_links=tuple(d.get("genealogical_links", []) or []),
            observation_count=int(d.get("observation_count", 0) or 0),
            outcome_positive=int(d.get("outcome_positive", 0) or 0),
            outcome_negative=int(d.get("outcome_negative", 0) or 0),
            contradiction_count=int(d.get("contradiction_count", 0) or 0),
            confidence=float(d.get("confidence", 0.0) or 0.0),
            status=str(d.get("status", "provisional") or "provisional"),
            restart_survivals=int(d.get("restart_survivals", 0) or 0),
            created_at=float(d.get("created_at", 0.0) or 0.0),
            updated_at=float(d.get("updated_at", 0.0) or 0.0),
            merged_into=d.get("merged_into"),
            split_from=d.get("split_from"),
        )


@dataclass(frozen=True)
class SemanticVariantMatch:
    variant: SemanticVariant
    score: float
    created: bool
    family_linked: bool


def _recompute_confidence(v: SemanticVariant) -> float:
    obs_component = min(1.0, v.observation_count / PROMOTE_MIN_OBSERVATIONS)
    family_component = min(1.0, len(v.context_families) / PROMOTE_MIN_CONTEXT_FAMILIES)
    outcome_component = v.outcome_support
    return round(clip01(0.5 * obs_component + 0.25 * family_component + 0.25 * outcome_component), 4)


def _check_promotion(v: SemanticVariant) -> bool:
    return (
        v.status in ("provisional", "reinforced")
        and v.observation_count >= PROMOTE_MIN_OBSERVATIONS
        and len(v.context_families) >= PROMOTE_MIN_CONTEXT_FAMILIES
        and v.outcome_support >= PROMOTE_MIN_OUTCOME_SUPPORT
        and v.contradiction_count == 0
        and v.restart_survivals >= PROMOTE_MIN_RESTART_SURVIVALS
    )


def _reinforce(variant: SemanticVariant, *, context_family: Optional[str], now: float) -> SemanticVariant:
    variant.observation_count += 1
    if context_family and context_family not in variant.context_families:
        variant.context_families = variant.context_families + (context_family,)
    variant.updated_at = now
    variant.confidence = _recompute_confidence(variant)
    if variant.status == "provisional" and variant.observation_count >= REINFORCE_MIN_OBSERVATIONS:
        variant.status = "reinforced"
    if _check_promotion(variant):
        variant.status = "promoted"
    return variant


class SemanticVariantRegistry:
    """Thin coordination layer over the crystal registry (dps) -- holds
    only a compact, disposable MC -> variant-id index in memory/on
    disk; full variant state always lives in the crystal facet. No
    long-lived variant cache: every match_or_create()/record_*() call
    reads through to the crystal so this stays a single source of
    truth, matching the directive's "not a parallel database" non-goal.
    """

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else None
        self._index_path = os.path.join(self._state_dir, INDEX_FILENAME) if self._state_dir else None
        self._index: Dict[str, List[Dict[str, str]]] = {}
        self._seen_this_boot: set = set()
        self._dirty = False
        if self._index_path:
            self._load_index()

    # ── compact index persistence ──

    def _load_index(self) -> None:
        try:
            if not os.path.exists(self._index_path):
                return
            with open(self._index_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                self._index = {
                    k: list(v) for k, v in (raw.get("index", {}) or {}).items()
                }
        except Exception:
            pass

    def save_index(self) -> bool:
        if not self._index_path:
            return False
        if not self._dirty:
            return False
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "index": self._index,
                "saved_at": time.time(),
            }
            tmp = self._index_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True)
            os.replace(tmp, self._index_path)
            self._dirty = False
            return True
        except Exception:
            return False

    def _index_upsert(self, variant: SemanticVariant) -> None:
        entries = self._index.setdefault(variant.manifold_slot_id, [])
        for e in entries:
            if e.get("variant_id") == variant.variant_id:
                if e.get("status") != variant.status:
                    e["status"] = variant.status
                    self._dirty = True
                return
        entries.append({
            "variant_id": variant.variant_id,
            "topology_id": variant.topology_id,
            "status": variant.status,
        })
        self._dirty = True

    # ── crystal read/write (full state lives here, index is only a lookup aid) ──

    def _read_variant(self, dps: Any, manifold_slot_id: str, topology_id: str) -> Optional[SemanticVariant]:
        if not topology_id or dps is None or not hasattr(dps, "get_crystal"):
            return None
        concept = f"tensor_variant:{manifold_slot_id}:{topology_id}"
        crystal = dps.get_crystal(concept)
        if crystal is None:
            return None
        for f in crystal.facets.values():
            if f.role == "variant_state":
                try:
                    variant = SemanticVariant.from_dict(json.loads(f.content))
                except Exception:
                    return None
                if variant.variant_id not in self._seen_this_boot:
                    variant.restart_survivals += 1
                    self._seen_this_boot.add(variant.variant_id)
                return variant
        return None

    def _write_variant(self, dps: Any, variant: SemanticVariant) -> None:
        if dps is None or not hasattr(dps, "_get_or_create"):
            return
        # Promotion may become true purely from restart_survivals clearing
        # its gate (bumped as a side effect of _read_variant, not by any
        # reinforcement/outcome call) -- re-check here, the one chokepoint
        # every mutation path writes through, so that case is never missed.
        if variant.status in ("provisional", "reinforced") and _check_promotion(variant):
            variant.status = "promoted"
        concept = f"tensor_variant:{variant.manifold_slot_id}:{variant.topology_id}"
        crystal = dps._get_or_create(concept)
        crystal.use()
        payload = json.dumps(variant.to_dict(), sort_keys=True)
        existing_facet = None
        for f in crystal.facets.values():
            if f.role == "variant_state":
                existing_facet = f
                break
        if existing_facet is not None:
            existing_facet.content = payload
            existing_facet.confidence = variant.confidence
        else:
            crystal.add_facet(role="variant_state", content=payload, confidence=variant.confidence)
        try:
            parent = dps._get_or_create(f"tensor:{variant.manifold_slot_id}")
            parent.connections[crystal.crystal_id] = max(
                parent.connections.get(crystal.crystal_id, 0.0), variant.confidence,
            )
        except Exception:
            pass
        try:
            crystal.evolve()
        except Exception:
            pass
        self._seen_this_boot.add(variant.variant_id)

    def _combined_score(
        self, profile: TopologyProfile, candidate: SemanticVariant, context_family: Optional[str],
    ) -> float:
        ts_score = topology_similarity(profile, candidate.topology_profile)
        context_score = 1.0 if (context_family and context_family in candidate.context_families) else 0.0
        return round(_W_TS * ts_score + _W_CONTEXT * context_score, 4)

    # ── public API ──

    def match_or_create(
        self,
        *,
        manifold_slot_id: Optional[str],
        base_meaning_form: Optional[str],
        ts: Optional[TopologySignature],
        context_family: Optional[str] = None,
        dps: Any = None,
        fingerprint_bands: int = 5,
    ) -> Optional[SemanticVariantMatch]:
        """Match this tick's (MC, TS) against known variants at this
        coordinate, reinforcing the closest SAME-threshold match or
        creating a new variant (FAMILY-linked if a close-but-not-same
        relative exists). Returns None -- never fakes a variant -- when
        dps is unavailable (graceful degradation, same posture as
        cers_tensor_locator.py) or when ts carries no real signal
        (quiescent regime / zero observations: noise must never create
        a variant)."""
        if dps is None or not manifold_slot_id:
            return None
        if ts is None or ts.regime == _QUIESCENT_REGIME or ts.observations <= 0:
            return None

        profile = TopologyProfile.from_signature(ts)
        topology_id = TopologyFingerprint.from_signature(ts, bands=fingerprint_bands).fingerprint_id
        now = time.time()

        best_variant: Optional[SemanticVariant] = None
        best_score = -1.0
        for entry in self._index.get(manifold_slot_id, []):
            candidate = self._read_variant(dps, manifold_slot_id, entry.get("topology_id", ""))
            if candidate is None or candidate.status in ("merged", "retired"):
                continue
            score = self._combined_score(profile, candidate, context_family)
            if score > best_score:
                best_score = score
                best_variant = candidate

        if best_variant is not None and best_score >= SAME_THRESHOLD:
            reinforced = _reinforce(best_variant, context_family=context_family, now=now)
            self._write_variant(dps, reinforced)
            self._index_upsert(reinforced)
            return SemanticVariantMatch(variant=reinforced, score=best_score, created=False, family_linked=False)

        family_link = best_variant.variant_id if (best_variant is not None and best_score >= FAMILY_THRESHOLD) else None

        new_variant = SemanticVariant(
            variant_id=f"{manifold_slot_id}:{topology_id}",
            manifold_slot_id=manifold_slot_id,
            topology_id=topology_id,
            topology_profile=profile,
            base_meaning_form=base_meaning_form or "",
            context_families=(context_family,) if context_family else (),
            observation_count=1,
            confidence=0.2,  # first-pass low prior: a fresh, once-seen, unreinforced variant
            status="provisional",
            created_at=now,
            updated_at=now,
            genealogical_links=(family_link,) if family_link else (),
        )
        self._write_variant(dps, new_variant)
        self._index_upsert(new_variant)
        return SemanticVariantMatch(
            variant=new_variant, score=max(best_score, 0.0), created=True, family_linked=family_link is not None,
        )

    def record_outcome(
        self, dps: Any, manifold_slot_id: str, topology_id: str, *, positive: bool,
    ) -> Optional[SemanticVariant]:
        variant = self._read_variant(dps, manifold_slot_id, topology_id)
        if variant is None:
            return None
        if positive:
            variant.outcome_positive += 1
        else:
            variant.outcome_negative += 1
        variant.updated_at = time.time()
        variant.confidence = _recompute_confidence(variant)
        if _check_promotion(variant):
            variant.status = "promoted"
        self._write_variant(dps, variant)
        self._index_upsert(variant)
        return variant

    def record_contradiction(self, dps: Any, manifold_slot_id: str, topology_id: str) -> Optional[SemanticVariant]:
        variant = self._read_variant(dps, manifold_slot_id, topology_id)
        if variant is None:
            return None
        variant.contradiction_count += 1
        variant.updated_at = time.time()
        self._write_variant(dps, variant)
        self._index_upsert(variant)
        return variant

    def record_simulated_evidence(
        self, dps: Any, manifold_slot_id: str, topology_id: str, *, source: str, note: str = "",
    ) -> Optional[SemanticVariant]:
        """FIX-A012: dream/classroom evidence is source-tagged, stored in
        its own facet-backed field, and never alone satisfies promotion
        -- promotion's gates (observation_count, context family count,
        outcome support, restart persistence) are driven only by
        record_outcome()/reinforcement, never by this method."""
        if source not in ("dream", "classroom"):
            raise ValueError(f"unknown simulated-evidence source: {source!r}")
        variant = self._read_variant(dps, manifold_slot_id, topology_id)
        if variant is None:
            return None
        entry = {"source": source, "ts": time.time(), "note": str(note or "")}
        if source == "dream":
            variant.dream_evidence = (variant.dream_evidence + (entry,))[-_EVIDENCE_CAP:]
        else:
            variant.classroom_evidence = (variant.classroom_evidence + (entry,))[-_EVIDENCE_CAP:]
        variant.updated_at = time.time()
        self._write_variant(dps, variant)
        self._index_upsert(variant)
        return variant

    def retire(self, dps: Any, manifold_slot_id: str, topology_id: str, *, reason: str = "") -> Optional[SemanticVariant]:
        """Never deletes -- archives evidence and lineage in place
        (registry discipline)."""
        variant = self._read_variant(dps, manifold_slot_id, topology_id)
        if variant is None:
            return None
        variant.status = "retired"
        variant.updated_at = time.time()
        if reason:
            variant.genealogical_links = variant.genealogical_links + (f"retired:{reason}",)
        self._write_variant(dps, variant)
        self._index_upsert(variant)
        return variant

    def merge(
        self, dps: Any, manifold_slot_id: str, keep_topology_id: str, absorb_topology_id: str,
    ) -> Optional[SemanticVariant]:
        """Absorb one variant's evidence into another; the absorbed
        variant is marked status="merged" with a merged_into pointer,
        never deleted (registry discipline)."""
        keep = self._read_variant(dps, manifold_slot_id, keep_topology_id)
        absorb = self._read_variant(dps, manifold_slot_id, absorb_topology_id)
        if keep is None or absorb is None:
            return None
        keep.observation_count += absorb.observation_count
        keep.outcome_positive += absorb.outcome_positive
        keep.outcome_negative += absorb.outcome_negative
        keep.context_families = tuple(sorted(set(keep.context_families) | set(absorb.context_families)))
        keep.dream_evidence = (keep.dream_evidence + absorb.dream_evidence)[-_EVIDENCE_CAP:]
        keep.classroom_evidence = (keep.classroom_evidence + absorb.classroom_evidence)[-_EVIDENCE_CAP:]
        keep.genealogical_links = keep.genealogical_links + (absorb.variant_id,)
        keep.updated_at = time.time()
        keep.confidence = _recompute_confidence(keep)
        if _check_promotion(keep):
            keep.status = "promoted"
        absorb.status = "merged"
        absorb.merged_into = keep.variant_id
        absorb.updated_at = time.time()
        self._write_variant(dps, keep)
        self._write_variant(dps, absorb)
        self._index_upsert(keep)
        self._index_upsert(absorb)
        return keep

    def split(
        self, dps: Any, manifold_slot_id: str, source_topology_id: str, *, new_context_family: str,
    ) -> Optional[SemanticVariant]:
        """Fork a new, independent variant off an existing one's
        organization for a context family that no longer belongs
        merged in -- the source variant is untouched (still active);
        the new one carries a split_from lineage pointer."""
        source = self._read_variant(dps, manifold_slot_id, source_topology_id)
        if source is None:
            return None
        now = time.time()
        new_topology_id = f"{source.topology_id}:split:{new_context_family}"
        new_variant = SemanticVariant(
            variant_id=f"{manifold_slot_id}:{new_topology_id}",
            manifold_slot_id=manifold_slot_id,
            topology_id=new_topology_id,
            topology_profile=source.topology_profile,
            base_meaning_form=source.base_meaning_form,
            context_families=(new_context_family,),
            observation_count=1,
            confidence=0.2,
            status="provisional",
            created_at=now,
            updated_at=now,
            split_from=source.variant_id,
        )
        self._write_variant(dps, new_variant)
        self._index_upsert(new_variant)
        return new_variant
