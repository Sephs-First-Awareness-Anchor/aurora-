"""
aurora_recursive_causal_reasoning_waveform.py
=============================================

Recursive Causal Reasoning Waveform (RCRW) for Aurora.

The live utterance is treated as an initial carrier disturbance (W0).  The
constraint architecture produces smaller, root-derived control wavelets that
interfere with the carrier while it moves through the system.  The resulting
global understanding (H) is then projected backward over the path that formed
it, producing an evidence-bounded effective interpretation of W0.  Aurora's
response is emitted as the next disturbance (W1), which becomes causal input
for the following cycle.

The architecture preserves three distinct records:

    raw_input               -- immutable external event
    provisional_interpretation -- the first constraint-bearing reading
    effective_interpretation   -- the later understanding's supported
                                  reconstruction of what the event was doing

Backward projection never changes history and never invents absent evidence.
It can confirm, weaken, suppress, or rebind provisional structures only when a
traceable source supports the change.

Every control wavelet and transformation declares X/T/N/B/A ancestry.  WARP
may promote recurrently useful wavelet configurations, while failed wavelets
dissolve.  The module is domain-agnostic: it steers relational structures,
attention, continuity, boundaries, pressure, and agency rather than relying on
human-language intent labels.

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import CoverageGap, WarpCapable, WarpComponent, istates_to_axes
from aurora_internal.aurora_constraint_semantic_continuity import (
    AXES,
    bind_referential_continuity,
    derive_constraint_semantic_state,
    relation_alignment,
)
from aurora_internal.aurora_meaning_evolution import canonical_signature


_ROOT_PRIMITIVES: Dict[str, Dict[str, Any]] = {
    "existence_admission": {
        "roots": ("X", "B"),
        "targets": ("entities", "identity"),
        "description": "stabilize which entities or qualities are admitted to the active reality",
    },
    "continuity_phase_lock": {
        "roots": ("X", "T", "B"),
        "targets": ("referents", "history", "relation"),
        "description": "preserve identity and relation across processing time",
    },
    "transformational_gradient": {
        "roots": ("T", "N", "A"),
        "targets": ("relation", "unknown", "resolution"),
        "description": "amplify the change required to move an unresolved relation toward understanding",
    },
    "boundary_separation": {
        "roots": ("X", "N", "B"),
        "targets": ("roles", "alternatives", "scope"),
        "description": "separate competing entities, roles, and scopes without erasing either side",
    },
    "agency_selection": {
        "roots": ("X", "T", "B", "A"),
        "targets": ("authority", "perspective", "response"),
        "description": "select which grounded perspective may author the next causal act",
    },
    "recursive_backprojection": {
        "roots": tuple(AXES),
        "targets": ("provisional_interpretation", "effective_interpretation"),
        "description": "let developed understanding reconstruct the supported meaning of its initiating disturbance",
    },
    "causal_emission": {
        "roots": tuple(AXES),
        "targets": ("response", "next_cycle"),
        "description": "emit the developed understanding as the next causal disturbance",
    },
}

_MAX_CYCLES = 500
_MAX_WAVELETS_PER_CYCLE = 18
_MAX_HISTORY_LINES = 1200
_EPS = 1e-9

# FIX-A012: same stopword set relation_alignment() already filters on
# (aurora_internal/aurora_constraint_semantic_continuity.py) -- reused here
# rather than re-declared, so entity-overlap checking stays consistent
# across both modules.
_DETERMINER_STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those", "some", "any",
    "each", "every", "my", "your", "his", "her", "its", "our", "their",
    "i", "me", "you", "he", "him", "she", "it", "we", "us", "they", "them",
}


def _clone(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:
        try:
            return json.loads(json.dumps(value, default=str))
        except Exception:
            return value


def _clip(value: Any, lo: float = 0.0, hi: float = 1.0, default: float = 0.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except Exception:
        return default


def _stable_hash(payload: Any, length: int = 14) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        raw = str(payload)
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _normalize_axes(values: Mapping[str, Any]) -> Dict[str, float]:
    raw = {ax: max(0.0, float(dict(values or {}).get(ax, 0.0) or 0.0)) for ax in AXES}
    total = sum(raw.values())
    if total <= _EPS:
        return {ax: 0.2 for ax in AXES}
    return {ax: round(raw[ax] / total, 6) for ax in AXES}


def _safe_text(value: Any, limit: int = 2000) -> str:
    return str(value or "")[:limit]




_STRUCTURAL_TERMS = frozenset({
    "is", "are", "am", "was", "were", "be", "been", "being",
    "do", "does", "did", "done", "has", "have", "had", "having",
    "what", "who", "whom", "whose", "which", "where", "when", "why", "how",
})


def _content_terms(value: Any) -> set[str]:
    """Return content-bearing terms for continuity evidence.

    RCRW already promises evidence-bounded reconstruction.  Historical focus
    may therefore influence a new carrier only when the current carrier (or an
    explicit referent binding for it) shares represented content with that
    focus.  Function words/pronouns are structural scaffolding, not evidence
    that two propositions are the same event.
    """
    import re

    return {
        token
        for token in re.findall(r"[a-z][a-z0-9']+", str(value or "").lower())
        if token not in _DETERMINER_STOPWORDS and len(token) > 1
    }


def _focus_claim_support(
    provisional: Mapping[str, Any],
    focus: Mapping[str, Any],
    referent_map: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Measure whether an active focus claim is evidence for this carrier.

    This is a boundary check, not a topic classifier.  The historical claim
    may participate when identity is continuous through shared represented
    content or through a referent map already established elsewhere.  Recency
    alone is deliberately insufficient.
    """
    current = dict(provisional or {})
    historical = dict(focus or {})
    refs = dict(referent_map or {})

    current_terms: set[str] = set()
    for key in ("raw_text", "subject", "obj", "complement", "relation"):
        current_terms.update(_content_terms(current.get(key, "")))

    focus_terms: set[str] = set()
    for key in ("subject", "object", "obj", "complement", "topic", "summary"):
        focus_terms.update(_content_terms(historical.get(key, "")))

    referent_terms: set[str] = set()
    referent_terms.update(_content_terms(refs.get("topic", "")))
    for value in dict(refs.get("referent_map") or {}).values():
        referent_terms.update(_content_terms(value))

    direct_overlap = current_terms & focus_terms
    referent_overlap = referent_terms & focus_terms

    current_relation = str(current.get("relation", "") or "").strip().lower()
    focus_relation = str(historical.get("relation", "") or "").strip().lower()

    def _relation_key(value: str) -> str:
        irregular = {
            "is": "be", "are": "be", "am": "be", "was": "be", "were": "be",
            "means": "mean", "does": "do", "did": "do",
            "has": "have", "had": "have", "owns": "own",
        }
        value = irregular.get(value, value)
        if len(value) > 3 and value.endswith("ies"):
            return value[:-3] + "y"
        if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
            return value[:-1]
        return value

    current_relation_key = _relation_key(current_relation)
    focus_relation_key = _relation_key(focus_relation)
    relation_compatible = bool(
        not current_relation_key
        or not focus_relation_key
        or current_relation_key == focus_relation_key
    )

    # Structural words never establish that two propositions share a participant.
    # The copula/auxiliaries, wh-words and the RELATION words themselves (already
    # checked separately as relation_compatible) passed _content_terms, so
    # "What is photosynthesis?" was "supported" by the unrelated claim "co-author
    # is Cael Devo" on the strength of the word "is" alone -- and recursive
    # backprojection then filled the question's empty object with "cael devo"
    # (confirmed live). Overlap must come from represented content.
    structural = set(_STRUCTURAL_TERMS)
    for _rel in (current_relation, focus_relation):
        if _rel:
            structural.add(_rel)
            structural.add(_relation_key(_rel))
    current_terms -= structural
    focus_terms -= structural
    referent_terms -= structural
    direct_overlap = current_terms & focus_terms
    referent_overlap = referent_terms & focus_terms

    supported = bool(
        focus_terms
        and (direct_overlap or referent_overlap)
        and relation_compatible
    )
    return {
        "supported": supported,
        "direct_overlap": sorted(direct_overlap),
        "referent_overlap": sorted(referent_overlap),
        "relation_compatible": relation_compatible,
        "current_relation": current_relation,
        "focus_relation": focus_relation,
        "current_terms": sorted(current_terms),
        "focus_terms": sorted(focus_terms),
    }

def _operation_record(name: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    spec = dict(_ROOT_PRIMITIVES[name])
    roots = tuple(spec.get("roots") or AXES)
    return {
        "operation": name,
        "root_constraints": list(roots),
        "canonical_signature": canonical_signature(roots),
        "targets": list(spec.get("targets") or []),
        "description": str(spec.get("description", "") or ""),
        "payload": _clone(dict(payload or {})),
    }


@dataclass
class CausalWavelet:
    wavelet_id: str
    primitive: str
    roots: List[str]
    amplitude: float
    phase: float
    polarity: int
    target: str
    source: str
    # Optional per-axis distribution for wavelets whose total intervention
    # energy is scalar but whose operational orientation is not uniform.
    # Empty preserves the historical equal-share behavior for every existing
    # wavelet.
    axis_profile: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    parent_ids: List[str] = field(default_factory=list)
    status: str = "transient"

    def signed_effect(self) -> float:
        return float(self.polarity) * float(self.amplitude) * math.cos(float(self.phase))

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["signed_effect"] = round(self.signed_effect(), 6)
        out["canonical_signature"] = canonical_signature(tuple(self.roots or AXES))
        return out


@dataclass
class CausalCycle:
    cycle_id: str
    created_at: float
    raw_input: str
    initial_semantic_state: Dict[str, Any]
    provisional_interpretation: Dict[str, Any]
    wavelets: List[Dict[str, Any]]
    interference: Dict[str, Any]
    global_understanding: Dict[str, Any]
    effective_interpretation: Dict[str, Any]
    response_wave: Dict[str, Any] = field(default_factory=dict)
    receiver_disturbance: Dict[str, Any] = field(default_factory=dict)
    genealogy_trace: Dict[str, Any] = field(default_factory=dict)
    status: str = "propagating"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuroraRecursiveCausalReasoningWaveform(WarpCapable):
    """Domain-agnostic recursive causal steering field.

    The class is both a live reasoning coordinator and a WARP-capable surface.
    Recurrently useful interference configurations may become promoted control
    wavelets, but no wavelet may replace raw evidence or directly author a
    response.  It only changes the constraint conditions under which Aurora's
    existing systems develop understanding.
    """

    def __init__(
        self,
        *,
        state_dir: str,
        persist: bool = True,
        genealogy: Any = None,
    ) -> None:
        self._init_warp(genealogy=genealogy)
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.persist = bool(persist)
        self.genealogy = genealogy
        self.systems: Dict[str, Any] = {}
        self.state_path = self.state_dir / "recursive_causal_reasoning_waveform.json"
        self.history_path = self.state_dir / "recursive_causal_reasoning_waveform_history.jsonl"
        self._cycles: List[Dict[str, Any]] = []
        self._active_cycle: Dict[str, Any] = {}
        self._pending_response_cycle_id = ""
        self._promoted_wavelets: Dict[str, Dict[str, Any]] = {}
        self._trial_wavelets: Dict[str, Dict[str, Any]] = {}
        self._dissolved_count = 0
        self._load()
        if genealogy is not None:
            self.set_warp_genealogy(genealogy)

    # ------------------------------------------------------------------
    # WARP surface
    # ------------------------------------------------------------------
    def _warp_level_name(self) -> str:
        return "recursive_causal_reasoning_waveform"

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        profiles: Dict[str, Dict[str, float]] = {}
        for name, spec in _ROOT_PRIMITIVES.items():
            roots = tuple(spec.get("roots") or AXES)
            base = {ax: (1.0 if ax in roots else 0.08) for ax in AXES}
            profiles[f"RCRW:PRIMITIVE:{name}"] = _normalize_axes(base)
        for wid, record in self._promoted_wavelets.items():
            profiles[str(wid)] = _normalize_axes(dict(record.get("axis_profile") or {}))
        return profiles

    def _integrate_warp(self, component: WarpComponent) -> None:
        params = dict(component.parameters or {})
        roots = [ax for ax in AXES if float(component.axis_profile.get(ax, 0.0) or 0.0) > 0.08]
        primitive = str(params.get("primitive", "recursive_backprojection") or "recursive_backprojection")
        if primitive not in _ROOT_PRIMITIVES:
            primitive = "recursive_backprojection"
        rec = {
            "component_id": component.component_id,
            "primitive": primitive,
            "roots": roots or list(_ROOT_PRIMITIVES[primitive]["roots"]),
            "axis_profile": _normalize_axes(component.axis_profile),
            "parent_ids": list(component.parent_ids or []),
            "created_at": float(component.created_at),
            "uses": 0,
            "successes": 0,
            "alignment_gain": 0.0,
            "status": "trial",
        }
        self._trial_wavelets[component.component_id] = rec
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        rec = dict(self._trial_wavelets.get(component.component_id) or {})
        uses = max(0, int(rec.get("uses", 0) or 0))
        successes = max(0, int(rec.get("successes", 0) or 0))
        gain = float(rec.get("alignment_gain", 0.0) or 0.0)
        if uses <= 0:
            return 0.25
        rate = successes / max(1, uses)
        mean_gain = gain / max(1, uses)
        return _clip(0.35 + 0.45 * rate + 0.20 * _clip(mean_gain, 0.0, 1.0))

    def _dissolve_warp(self, component_id: str) -> None:
        self._trial_wavelets.pop(str(component_id), None)
        self._dissolved_count += 1
        self._persist()

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        gap_profile = dict(getattr(gap, "axis_profile", {}) or {})
        profile = _normalize_axes(istates_to_axes(gap_profile) if gap_profile else {})
        dominant = max(AXES, key=lambda ax: profile.get(ax, 0.0))
        primitive = {
            "X": "existence_admission",
            "T": "continuity_phase_lock",
            "N": "transformational_gradient",
            "B": "boundary_separation",
            "A": "agency_selection",
        }.get(dominant, "recursive_backprojection")
        return {
            "primitive": primitive,
            "dominant_axis": dominant,
            "source": str(getattr(gap, "source", "") or ""),
            "parent_ids": list(parent_ids or []),
        }

    def evaluate_warp_trials(self) -> Tuple[List[str], List[str]]:
        promoted, dissolved = super().evaluate_warp_trials()
        for component_id in promoted:
            trial = dict(self._trial_wavelets.pop(component_id, {}) or {})
            trial["status"] = "promoted"
            trial["promoted_at"] = time.time()
            self._promoted_wavelets[component_id] = trial
            self._register_promoted_wavelet(component_id, trial)
        for component_id in dissolved:
            self._trial_wavelets.pop(component_id, None)
        if promoted or dissolved:
            self._persist()
        return promoted, dissolved

    # ------------------------------------------------------------------
    # Live cycle
    # ------------------------------------------------------------------
    def attach_systems(self, systems: Mapping[str, Any]) -> None:
        self.systems = systems if isinstance(systems, dict) else dict(systems or {})
        if self.genealogy is None:
            self.genealogy = self.systems.get("genealogy")
        if self.genealogy is not None:
            self.set_warp_genealogy(self.genealogy)
        sedi = self.systems.get("sedimemory")
        if sedi is not None and hasattr(self, "connect_sedimemory"):
            try:
                self.connect_sedimemory(sedi)
            except Exception:
                pass

    def receive_disturbance(self, raw_text: str, *, systems: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Register the next external disturbance and link it to W1.

        The method does not judge the new utterance as positive or negative.
        It simply records that Aurora's previous response has now entered a new
        causal environment.  Existing receiver-validation systems remain the
        authority for developmental credit.
        """
        if systems is not None:
            self.attach_systems(systems)
        event = {
            "received_at": time.time(),
            "raw_text": _safe_text(raw_text),
            "raw_hash": _stable_hash(str(raw_text or "").strip().lower(), 12),
            "caused_by_response_cycle": str(self._pending_response_cycle_id or ""),
        }
        if self._pending_response_cycle_id:
            cycle = self._find_cycle(self._pending_response_cycle_id)
            if cycle is not None:
                cycle["receiver_disturbance"] = _clone(event)
                if cycle.get("status") == "emitted":
                    cycle["status"] = "reentered"
                    # FIX-A012 (Sunni & Cael): recognizing a disturbance
                    # happened is not the same as revisiting what it
                    # disturbed -- this was the exact gap: the flag went up,
                    # nothing ever read it. Attempt reconciliation now,
                    # while we still have the cycle in hand.
                    self._reconcile_disturbed_cycle(cycle, raw_text, systems=systems)
                self._persist()
        return event

    def _reconcile_disturbed_cycle(self, cycle: MutableMapping[str, Any],
                                    disturbance_text: str,
                                    *, systems: Optional[Mapping[str, Any]] = None) -> None:
        """FIX-A012: decides ONLY whether a disturbance mechanically
        conflicts with a prior cycle -- shared entities (same token-overlap
        check relation_alignment already uses elsewhere) plus an explicit
        negation/correction signal (RelationalForm.negated, or one of a
        small set of correction words). It never decides WHAT the
        resolution is: the actual revision runs through
        derive_constraint_semantic_state, the SAME derivation every
        ordinary turn already uses, fed the prior claim and the new
        disturbance together as two clauses (the same multi-clause shape
        FIX-A008 already produces for an ordinary multi-claim sentence)
        instead of inventing a new resolution mechanism here.
        """
        try:
            import re as _re
            from aurora_internal.aurora_constraint_semantic_continuity import (
                extract_relational_form, derive_constraint_semantic_state,
            )
            prior_form = dict(
                cycle.get("effective_interpretation")
                or dict(cycle.get("initial_semantic_state") or {}).get("relational_form")
                or {}
            )
            if not prior_form:
                return
            disturbance_form = extract_relational_form(disturbance_text)

            def _entity_tokens(form: Mapping[str, Any]) -> set:
                toks: set = set()
                # FIX-A012: scan clauses too, not just the top-level
                # subject/obj/complement -- the active/primary clause
                # selection (existing convention, unchanged here) can
                # promote a LESS entity-relevant clause to the top level
                # while the entities we actually need to check live in a
                # secondary clause (confirmed directly: turn 7's own parse
                # promotes "the scooter has nothing to do with it" to
                # top-level while "the workshop never trusted him" sits in
                # `clauses`). Checking clauses too is reading data this
                # module already produces, not adding a new extraction path.
                forms_to_scan = [form] + list(form.get("clauses") or [])
                for f in forms_to_scan:
                    for slot in ("subject", "obj", "complement"):
                        value = str(f.get(slot, "") or "").lower()
                        toks.update(t for t in _re.findall(r"[a-z][a-z0-9']+", value)
                                    if t not in _DETERMINER_STOPWORDS)
                return toks

            prior_tokens = _entity_tokens(prior_form)
            disturbance_tokens = _entity_tokens(disturbance_form)
            overlap = prior_tokens & disturbance_tokens
            negation_signal = bool(disturbance_form.get("negated")) or bool(
                _re.search(r"\b(actually|no|never|wrong|not true|nothing to do)\b",
                           str(disturbance_text or "").lower())
            )
            if not overlap or not negation_signal:
                return  # no mechanical evidence of conflict -- leave the cycle alone

            combined = dict(prior_form)
            combined["clauses"] = list(prior_form.get("clauses") or []) + [dict(disturbance_form)]
            revised = derive_constraint_semantic_state(
                combined, axis_activation={}, genealogy=self.genealogy,
            )
            revised_form = dict(revised.get("relational_form") or {})

            cycle.setdefault("reconciliation_log", []).append({
                "disturbance_text": _safe_text(disturbance_text),
                "previous_effective_interpretation": dict(cycle.get("effective_interpretation") or {}),
                "revised_effective_interpretation": dict(revised_form),
                "overlap_entities": sorted(overlap),
                "reconciled_at": time.time(),
            })
            if revised_form:
                cycle["effective_interpretation"] = revised_form
            cycle["status"] = "reconciled"

            # Propagate to OntologicalWeb: decay the specific prior relation(s)
            # between the disturbed entities, rather than letting the graph
            # keep carrying a claim that was just directly contradicted.
            # Decays strength/confidence -- does not delete the relation or
            # assign it a new type; that stays FIX-A011's job, next time
            # these entities co-occur again.
            web = None
            if isinstance(systems, Mapping):
                perception = systems.get("perception")
                oets = getattr(perception, "oets", None)
                web = getattr(oets, "web", None)
            if web is not None and hasattr(web, "get_relation_between"):
                entities = sorted(overlap)
                for i, a in enumerate(entities):
                    for b in entities[i + 1:]:
                        rel = web.get_relation_between(a, b)
                        if rel is not None:
                            rel.strength = max(0.0, float(rel.strength or 0.0) * 0.3)
                            rel.confidence = max(0.0, float(rel.confidence or 0.0) * 0.3)
                            # FIX-A013: attribute this failure back to the
                            # (signature, type) pattern that selected it, so
                            # the same underlying gap registers as a pattern
                            # the moment it recurs on ANY other entity pair
                            # sharing that structural signature -- not just
                            # decaying this one relation and forgetting why.
                            if hasattr(web, "register_selection_failure"):
                                try:
                                    web.register_selection_failure(rel)
                                except Exception:
                                    pass
            self._persist()
        except Exception:
            pass

    def _maybe_stage_representation_inquiry(self, axes: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        """Native inquiry-to-experiment consumer (Sunni & Cael, reconstructed
        build-650-fixed-v5 extension). Ask genealogy for at most one
        admissible pending representational inquiry (exact-signature 'RC:'
        or cross-family 'RI:') and stage it for THIS already-occurring
        cycle. An unresolved inquiry never starts a cycle by itself -- this
        is only ever reached because prepare_semantic_state() is already
        running one for its own, unrelated reason."""
        genealogy = self.genealogy
        if genealogy is None or not hasattr(genealogy, "stage_representation_inquiry"):
            return None
        try:
            staged = genealogy.stage_representation_inquiry(
                "recursive_causal_waveform",
                {"axis_activation": dict(axes or {})},
                limit=1,
            )
        except Exception:
            return None
        return dict(staged[0]) if staged else None

    def _representation_inquiry_wavelet(self, stage: Mapping[str, Any]) -> CausalWavelet:
        """Build the trial wavelet carrying intact operand state and merged
        primitive grounding for a staged representational inquiry. No
        semantic answer is attached -- only the same X/T/N/B/A surface and
        provenance every other wavelet already carries."""
        profile = dict(stage.get("relational_axis_profile") or {})
        return CausalWavelet(
            wavelet_id="RIW:" + _stable_hash({
                "stage": str(stage.get("stage_id", "")), "t": time.time_ns(),
            }, 14),
            primitive="recursive_backprojection",
            roots=list(_ROOT_PRIMITIVES["recursive_backprojection"]["roots"]),
            amplitude=_clip(0.10 + 0.5 * sum(float(profile.get(ax, 0.0) or 0.0) for ax in AXES), 0.0, 1.0),
            phase=0.0,
            polarity=1,
            target="representation_relation",
            source="representation_inquiry",
            # The staged relation already carries its own consequence-derived
            # X/T/N/B/A orientation.  Preserve that operational distinction in
            # the interference itself rather than carrying it as metadata while
            # perturbing every inquiry identically.  Total trial energy remains
            # constant; only its native axis distribution differs.
            axis_profile=_normalize_axes(profile),
            evidence={
                "stage_id": str(stage.get("stage_id", "")),
                "inquiry_id": str(stage.get("inquiry_id", "")),
                "operand_states": _clone(list(stage.get("operands", []) or [])),
                "constraint_basis": _clone(dict(stage.get("constraint_basis", {}) or {})),
                "relational_axis_profile": _clone(profile),
            },
            parent_ids=list(stage.get("operand_ids", []) or []),
            status="transient",
        )

    def prepare_semantic_state(
        self,
        semantic_state: Mapping[str, Any],
        *,
        raw_text: str,
        referent_map: Optional[Mapping[str, Any]] = None,
        claim_resolution: Optional[Mapping[str, Any]] = None,
        meaning_forms: Optional[Sequence[Mapping[str, Any]]] = None,
        axis_activation: Optional[Mapping[str, Any]] = None,
        systems: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Propagate W0 through transient and promoted control wavelets."""
        if systems is not None:
            self.attach_systems(systems)
        initial = _clone(dict(semantic_state or {}))
        provisional = _clone(dict(initial.get("relational_form") or {}))
        axes = _normalize_axes(axis_activation or initial.get("axis_activation") or {})
        wavelets = self._generate_wavelets(
            provisional,
            initial,
            axes,
            referent_map=referent_map,
            claim_resolution=claim_resolution,
        )
        representation_stage = self._maybe_stage_representation_inquiry(axes)
        representation_control: Optional[Dict[str, Any]] = None
        if representation_stage is not None:
            # Exact within-RCRW control: the same initiating semantic state and
            # same naturally generated wavelets, differing only by the staged
            # representation-inquiry intervention.  This does not author a
            # second response or touch live state; it isolates what the inquiry
            # itself changes in the recursive causal field.
            control_interference = self._interfere(axes, wavelets)
            inquiry_wavelet = self._representation_inquiry_wavelet(representation_stage)
            wavelets = list(wavelets) + [inquiry_wavelet]
        interference = self._interfere(axes, wavelets)
        if representation_stage is not None:
            control_after = dict(control_interference.get("axis_after") or {})
            experimental_after = dict(interference.get("axis_after") or {})
            marginal_delta = {
                ax: round(
                    float(experimental_after.get(ax, 0.0) or 0.0)
                    - float(control_after.get(ax, 0.0) or 0.0),
                    9,
                )
                for ax in AXES
            }
            representation_control = {
                "method": "same_cycle_without_inquiry_wavelet",
                "axis_before": _clone(dict(axes)),
                "control_axis_after": _clone(control_after),
                "experimental_axis_after": _clone(experimental_after),
                "marginal_axis_delta": marginal_delta,
                "marginal_l1": round(sum(abs(v) for v in marginal_delta.values()), 9),
                "inquiry_axis_profile": _clone(dict(inquiry_wavelet.axis_profile or {})),
                "inquiry_wavelet_id": inquiry_wavelet.wavelet_id,
            }
        effective_form, reconstruction = self._backproject(
            provisional,
            referent_map=referent_map,
            claim_resolution=claim_resolution,
            wavelets=wavelets,
        )
        revised = derive_constraint_semantic_state(
            effective_form,
            axis_activation=interference["axis_after"],
            genealogy=self.genealogy,
            referent_map=referent_map,
            claim_resolution=claim_resolution,
            meaning_forms=meaning_forms,
        )
        understanding = self._develop_global_understanding(
            initial=initial,
            revised=revised,
            wavelets=wavelets,
            reconstruction=reconstruction,
            interference=interference,
        )
        cycle_id = "RCRW:" + _stable_hash({
            "time": time.time_ns(),
            "raw": raw_text,
            "proposition": initial.get("proposition_id", ""),
        }, 16)
        cycle = CausalCycle(
            cycle_id=cycle_id,
            created_at=time.time(),
            raw_input=_safe_text(raw_text),
            initial_semantic_state=initial,
            provisional_interpretation=provisional,
            wavelets=[wave.to_dict() for wave in wavelets],
            interference=interference,
            global_understanding=understanding,
            effective_interpretation=_clone(effective_form),
            genealogy_trace=self._cycle_genealogy(wavelets, revised),
            status="understood",
        ).to_dict()
        cycle["representation_experiment"] = representation_stage
        cycle["representation_experiment_control"] = representation_control
        self._active_cycle = cycle
        self._cycles.append(cycle)
        self._cycles = self._cycles[-_MAX_CYCLES:]

        revised["recursive_causal_waveform"] = {
            "cycle_id": cycle_id,
            "carrier_wave": {
                "raw_input_hash": _stable_hash(raw_text, 12),
                "proposition_id": initial.get("proposition_id", ""),
                "axis_before": axes,
            },
            "control_wavelets": [wave.to_dict() for wave in wavelets],
            "interference": _clone(interference),
            "global_understanding": _clone(understanding),
            "effective_interpretation": _clone(effective_form),
            "reconstruction": _clone(reconstruction),
            "genealogy_trace": _clone(cycle["genealogy_trace"]),
        }
        self._publish_active_cycle(revised)
        self._persist()
        return revised

    def complete_cycle(
        self,
        *,
        delivered_text: str,
        response_source: str,
        confidence: float,
        systems: Optional[Mapping[str, Any]] = None,
        pressure_before: Optional[Mapping[str, Any]] = None,
        pressure_after: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Emit W1 and let H retrospectively evaluate W0.

        Completion measures whether the emitted response preserved the
        effective relation.  Low alignment generates WARP pressure; high
        alignment reinforces the wavelets that participated.  The response is
        then stored as the initiating disturbance for the next causal cycle.
        """
        if systems is not None:
            self.attach_systems(systems)
        if not self._active_cycle:
            return {}
        cycle = self._active_cycle
        effective = dict(cycle.get("effective_interpretation") or {})
        alignment = relation_alignment(effective, delivered_text)
        response_wave = {
            "emitted_at": time.time(),
            "text": _safe_text(delivered_text),
            "text_hash": _stable_hash(delivered_text, 12),
            "source": str(response_source or ""),
            "confidence": _clip(confidence),
            "relation_alignment": alignment,
            "causal_parent_cycle": str(cycle.get("cycle_id", "") or ""),
            "operation": _operation_record("causal_emission", {
                "response_source": str(response_source or ""),
                "alignment": alignment,
            }),
        }
        cycle["response_wave"] = response_wave
        cycle["status"] = "emitted"
        cycle["completed_at"] = time.time()
        cycle["global_understanding"]["response_alignment"] = _clone(alignment)
        cycle["global_understanding"]["retrospective_confidence"] = round(
            0.55 * float(cycle["global_understanding"].get("coherence", 0.0) or 0.0)
            + 0.45 * float(alignment.get("score", 0.0) or 0.0),
            6,
        )
        self._pending_response_cycle_id = str(cycle.get("cycle_id", "") or "")
        self._update_wavelet_evidence(cycle, alignment)
        self._confess_gap_if_needed(cycle, alignment)
        self._complete_representation_experiment_for_cycle(
            cycle, alignment,
            pressure_before=pressure_before,
            pressure_after=pressure_after,
        )
        promoted, dissolved = self.evaluate_warp_trials()
        cycle["warp_evaluation"] = {"promoted": promoted, "dissolved": dissolved}
        self._publish_completion(cycle)
        self._append_history(cycle)
        self._persist()
        return _clone(cycle)

    def _complete_representation_experiment_for_cycle(
        self,
        cycle: MutableMapping[str, Any],
        alignment: Mapping[str, Any],
        *,
        pressure_before: Optional[Mapping[str, Any]] = None,
        pressure_after: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Complete a staged relation only from consequence evidence that is
        both lived and attributable enough to admit.

        The staged inquiry already has an exact internal control captured at
        prepare time: the same RCRW state without the inquiry wavelet.  Here we
        combine that isolated marginal intervention with the app turn's native
        operator-pressure snapshots.  No response-quality score is converted
        into synthetic X/T/N/B/A relief.  Missing measurements are explicitly
        inconclusive rather than treated as either success or failure.
        """
        stage = dict(cycle.get("representation_experiment") or {})
        if not stage or not stage.get("stage_id"):
            return
        genealogy = self.genealogy
        if genealogy is None or not hasattr(genealogy, "complete_representation_experiment"):
            return

        control = dict(cycle.get("representation_experiment_control") or {})
        marginal_delta = {
            ax: float(dict(control.get("marginal_axis_delta") or {}).get(ax, 0.0) or 0.0)
            for ax in AXES
        }
        marginal_abs = {ax: abs(v) for ax, v in marginal_delta.items()}
        marginal_l1 = sum(marginal_abs.values())

        before_ops_raw = dict(dict(pressure_before or {}).get("operator_gradients") or {})
        after_ops_raw = dict(dict(pressure_after or {}).get("operator_gradients") or {})
        snapshots_valid = bool(before_ops_raw) and bool(after_ops_raw) and all(
            ax in before_ops_raw and ax in after_ops_raw for ax in AXES
        )

        before_pressure = {ax: abs(float(before_ops_raw.get(ax, 0.0) or 0.0)) for ax in AXES}
        after_pressure = {ax: abs(float(after_ops_raw.get(ax, 0.0) or 0.0)) for ax in AXES}
        observed_relief = {
            ax: max(0.0, before_pressure[ax] - after_pressure[ax]) for ax in AXES
        }

        axis_before = {
            ax: float(dict(control.get("axis_before") or {}).get(ax, 0.0) or 0.0) for ax in AXES
        }
        control_after = {
            ax: float(dict(control.get("control_axis_after") or {}).get(ax, 0.0) or 0.0) for ax in AXES
        }
        control_change_l1 = sum(abs(control_after[ax] - axis_before[ax]) for ax in AXES)
        intervention_fraction = (
            marginal_l1 / (marginal_l1 + control_change_l1)
            if marginal_l1 > _EPS else 0.0
        )

        max_marginal = max(marginal_abs.values()) if marginal_abs else 0.0
        axis_gate = {
            ax: (marginal_abs[ax] / max_marginal if max_marginal > _EPS else 0.0)
            for ax in AXES
        }
        attributable_relief = {
            ax: observed_relief[ax] * axis_gate[ax] * intervention_fraction
            for ax in AXES
        }

        observed_total = sum(observed_relief.values())
        if marginal_l1 > _EPS and observed_total > _EPS:
            marginal_dist = {ax: marginal_abs[ax] / marginal_l1 for ax in AXES}
            relief_dist = {ax: observed_relief[ax] / observed_total for ax in AXES}
            axis_overlap = sum(min(marginal_dist[ax], relief_dist[ax]) for ax in AXES)
        else:
            axis_overlap = 0.0
        causal_confidence = max(0.0, min(1.0, intervention_fraction * axis_overlap))
        causal_evidence_valid = bool(snapshots_valid and marginal_l1 > _EPS)

        coherence = float(cycle.get("interference", {}).get("coherence", 0.0) or 0.0)
        retrospective_confidence = float(
            cycle.get("global_understanding", {}).get("retrospective_confidence", 0.0) or 0.0
        )

        try:
            result = genealogy.complete_representation_experiment(
                str(stage.get("stage_id", "")),
                consumer="recursive_causal_waveform",
                coactivated_ids=list(stage.get("operand_ids", []) or []),
                # PressureVec uses higher=worse.  Pass only the portion of
                # measured pressure decrease that overlaps axes the controlled
                # inquiry intervention actually changed.
                pressure_before=attributable_relief,
                pressure_after={ax: 0.0 for ax in AXES},
                outcome={
                    "actual_coactivation": True,
                    "causal_evidence_valid": causal_evidence_valid,
                    "causal_evidence_mode": "controlled_rcrw_marginal_x_lived_operator_pressure",
                    "causal_confidence": round(causal_confidence, 9),
                    "intervention_fraction": round(intervention_fraction, 9),
                    "axis_overlap": round(axis_overlap, 9),
                    "marginal_axis_delta": {ax: round(v, 9) for ax, v in marginal_delta.items()},
                    "observed_operator_pressure_before": {ax: round(v, 9) for ax, v in before_pressure.items()},
                    "observed_operator_pressure_after": {ax: round(v, 9) for ax, v in after_pressure.items()},
                    "observed_positive_relief": {ax: round(v, 9) for ax, v in observed_relief.items()},
                    "attributable_relief": {ax: round(v, 9) for ax, v in attributable_relief.items()},
                    "response_alignment": _clone(dict(alignment or {})),
                    "coherence": round(coherence, 6),
                    "retrospective_confidence": round(retrospective_confidence, 6),
                },
            )
        except Exception:
            return
        cycle["representation_experiment_result"] = result

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _generate_wavelets(
        self,
        form: Mapping[str, Any],
        semantic_state: Mapping[str, Any],
        axes: Mapping[str, float],
        *,
        referent_map: Optional[Mapping[str, Any]],
        claim_resolution: Optional[Mapping[str, Any]],
    ) -> List[CausalWavelet]:
        rel = dict(form or {})
        unresolved = set(str(x) for x in list(semantic_state.get("unresolved") or []))
        wavelets: List[CausalWavelet] = []

        def add(primitive: str, amplitude: float, target: str, source: str, evidence: Mapping[str, Any], polarity: int = 1, phase: float = 0.0, parent_ids: Optional[Sequence[str]] = None, status: str = "transient") -> None:
            spec = _ROOT_PRIMITIVES[primitive]
            wavelets.append(CausalWavelet(
                wavelet_id="RW:" + _stable_hash({
                    "primitive": primitive,
                    "target": target,
                    "source": source,
                    "evidence": evidence,
                    "n": len(wavelets),
                }, 14),
                primitive=primitive,
                roots=list(spec["roots"]),
                amplitude=_clip(amplitude, 0.0, 1.0),
                phase=float(phase),
                polarity=1 if polarity >= 0 else -1,
                target=str(target),
                source=str(source),
                evidence=_clone(dict(evidence or {})),
                parent_ids=list(parent_ids or []),
                status=status,
            ))

        entity_count = sum(bool(rel.get(key)) for key in ("subject", "obj", "complement"))
        if entity_count:
            add("existence_admission", 0.18 + 0.06 * entity_count, "entities", "provisional_relation", {
                "subject": rel.get("subject", ""), "object": rel.get("obj", ""), "complement": rel.get("complement", ""),
            })
        elif "entity" in unresolved:
            add("existence_admission", 0.55, "entities", "unresolved_structure", {"unresolved": sorted(unresolved)})

        if rel.get("relation"):
            add("continuity_phase_lock", 0.30, "relation", "provisional_relation", {"relation": rel.get("relation", "")})
            add("transformational_gradient", 0.24, "resolution", "response_obligation", {
                "unknown_role": rel.get("unknown_role", ""), "question": bool(rel.get("question")),
            })
        else:
            add("continuity_phase_lock", 0.48, "relation", "unresolved_structure", {"unresolved": sorted(unresolved)})

        if rel.get("unresolved_references"):
            add("continuity_phase_lock", 0.65, "referents", "reference_gap", {
                "unresolved_references": list(rel.get("unresolved_references") or []),
                "referent_map": dict(referent_map or {}),
            })

        if rel.get("alternatives") or rel.get("negated"):
            add("boundary_separation", 0.42, "alternatives", "relational_boundary", {
                "alternatives": list(rel.get("alternatives") or []), "negated": bool(rel.get("negated")),
            })
        elif rel.get("unknown_role"):
            add("boundary_separation", 0.28, "unknown", "unknown_localization", {"unknown_role": rel.get("unknown_role", "")})

        add("agency_selection", 0.22 + 0.18 * float(bool(rel.get("question"))), "authority", "response_obligation", {
            "owner": rel.get("owner", ""), "question": bool(rel.get("question")),
        })

        claim = dict(claim_resolution or {})
        focus = dict(claim.get("focus_claim") or {})
        focus_support = _focus_claim_support(rel, focus, referent_map) if focus else {"supported": False}
        if focus and focus_support.get("supported"):
            add(
                "continuity_phase_lock",
                0.24,
                "history",
                "claim_continuity",
                {"focus_claim": focus, "support": focus_support},
            )

        # Promoted WARP wavelets participate as smaller endogenous causes.
        for component_id, rec in list(self._promoted_wavelets.items())[:8]:
            primitive = str(rec.get("primitive", "") or "")
            if primitive not in _ROOT_PRIMITIVES:
                continue
            profile = _normalize_axes(dict(rec.get("axis_profile") or {}))
            resonance = sum(profile.get(ax, 0.0) * float(axes.get(ax, 0.0) or 0.0) for ax in AXES)
            if resonance < 0.12:
                continue
            add(
                primitive,
                min(0.34, 0.12 + resonance * 0.28),
                str(_ROOT_PRIMITIVES[primitive]["targets"][0]),
                "promoted_wavelet",
                {"component_id": component_id, "resonance": round(resonance, 6)},
                parent_ids=[component_id],
                status="promoted",
            )
        return wavelets[:_MAX_WAVELETS_PER_CYCLE]

    def _interfere(self, axis_before: Mapping[str, Any], wavelets: Sequence[CausalWavelet]) -> Dict[str, Any]:
        before = _normalize_axes(axis_before)
        raw = dict(before)
        contributions: List[Dict[str, Any]] = []
        for wave in wavelets:
            effect = wave.signed_effect()
            profile_raw = {
                ax: max(0.0, float(dict(wave.axis_profile or {}).get(ax, 0.0) or 0.0))
                for ax in wave.roots
            }
            profile_total = sum(profile_raw.values())
            if profile_total > _EPS:
                axis_effects = {
                    ax: effect * (profile_raw[ax] / profile_total) for ax in wave.roots
                }
            else:
                share = effect / max(1, len(wave.roots))
                axis_effects = {ax: share for ax in wave.roots}
            for ax, axis_effect in axis_effects.items():
                raw[ax] = max(0.0, raw.get(ax, 0.0) + axis_effect)
            contributions.append({
                "wavelet_id": wave.wavelet_id,
                "primitive": wave.primitive,
                "roots": list(wave.roots),
                "signed_effect": round(effect, 6),
                "axis_effects": {ax: round(v, 9) for ax, v in axis_effects.items()},
                "target": wave.target,
            })
        after = _normalize_axes(raw)
        delta = {ax: round(after[ax] - before[ax], 6) for ax in AXES}
        coherence = 1.0 - min(1.0, sum(abs(delta[ax]) for ax in AXES) / 2.0)
        return {
            "axis_before": before,
            "axis_after": after,
            "axis_delta": delta,
            "contributions": contributions,
            "coherence": round(coherence, 6),
            "constructive_energy": round(sum(max(0.0, item["signed_effect"]) for item in contributions), 6),
            "destructive_energy": round(sum(abs(min(0.0, item["signed_effect"])) for item in contributions), 6),
        }

    def _backproject(
        self,
        provisional: Mapping[str, Any],
        *,
        referent_map: Optional[Mapping[str, Any]],
        claim_resolution: Optional[Mapping[str, Any]],
        wavelets: Sequence[CausalWavelet],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        original = _clone(dict(provisional or {}))
        effective = bind_referential_continuity(original, referent_map=referent_map)
        changes: List[Dict[str, Any]] = []

        for field_name in ("subject", "obj", "complement"):
            before = str(original.get(field_name, "") or "")
            after = str(effective.get(field_name, "") or "")
            if before != after and after:
                changes.append({
                    "slot": field_name,
                    "before": before,
                    "after": after,
                    "evidence": "referential_continuity",
                    "operation": _operation_record("recursive_backprojection", {"slot": field_name}),
                })

        # A prior claim may restore structure only when the present carrier or
        # an already-resolved referent supplies continuity evidence.  Recency
        # by itself is not evidence: otherwise independent participants can be
        # spliced into an unrelated live relation.
        focus = dict(dict(claim_resolution or {}).get("focus_claim") or {})
        focus_support = _focus_claim_support(original, focus, referent_map) if focus else {"supported": False}
        if not focus_support.get("supported"):
            focus = {}

        if not effective.get("relation") and focus:
            candidate_relation = str(focus.get("relation", "") or "").strip()
            if candidate_relation:
                effective["relation"] = candidate_relation
                changes.append({
                    "slot": "relation",
                    "before": "",
                    "after": candidate_relation,
                    "evidence": "active_focus_claim",
                    "operation": _operation_record("recursive_backprojection", {"slot": "relation"}),
                })

                # Negation is part of the causal relation, not decoration on
                # its participants.  When RCRW legitimately restores the
                # historical relation itself, restore that relation's polarity
                # too unless the current carrier contains explicit negative
                # evidence of its own (which is already preserved as True).
                if not bool(original.get("negated", False)):
                    historical_negated = bool(focus.get("negated", False))
                    if bool(effective.get("negated", False)) != historical_negated:
                        effective["negated"] = historical_negated
                        changes.append({
                            "slot": "negated",
                            "before": bool(original.get("negated", False)),
                            "after": historical_negated,
                            "evidence": "active_focus_claim_relation_polarity",
                            "operation": _operation_record(
                                "recursive_backprojection",
                                {"slot": "negated", "relation_restored": True},
                            ),
                        })

        for field_name, focus_key in (("subject", "subject"), ("obj", "object"), ("complement", "complement")):
            if effective.get(field_name):
                continue
            value = str(focus.get(focus_key, "") or "").strip()
            if value:
                effective[field_name] = value
                changes.append({
                    "slot": field_name,
                    "before": "",
                    "after": value,
                    "evidence": "active_focus_claim",
                    "operation": _operation_record("recursive_backprojection", {"slot": field_name}),
                })

        effective["recursive_reconstruction"] = {
            "raw_preserved": True,
            "changes": changes,
            "wavelet_ids": [wave.wavelet_id for wave in wavelets],
            "operation": _operation_record("recursive_backprojection", {
                "change_count": len(changes),
                "principle": "later understanding may revise interpretation but not raw history",
            }),
        }
        return effective, {
            "changed": bool(changes),
            "changes": changes,
            "raw_input_preserved": True,
            "support_required": True,
        }

    def _develop_global_understanding(
        self,
        *,
        initial: Mapping[str, Any],
        revised: Mapping[str, Any],
        wavelets: Sequence[CausalWavelet],
        reconstruction: Mapping[str, Any],
        interference: Mapping[str, Any],
    ) -> Dict[str, Any]:
        form = dict(revised.get("relational_form") or {})
        unresolved = list(revised.get("unresolved") or [])
        completeness = _clip(revised.get("completeness", 0.0))
        coherence = _clip(interference.get("coherence", 0.0))
        causal_chain = [
            _operation_record("existence_admission", {"entities": [form.get("subject"), form.get("obj"), form.get("complement")]}),
            _operation_record("continuity_phase_lock", {"relation": form.get("relation", "")}),
            _operation_record("transformational_gradient", {"unknown": form.get("unknown_role", "")}),
            _operation_record("boundary_separation", {"alternatives": form.get("alternatives", [])}),
            _operation_record("agency_selection", {"owner": form.get("owner", "")}),
            _operation_record("recursive_backprojection", {"reconstruction": dict(reconstruction or {})}),
        ]
        return {
            "proposition_id": str(revised.get("proposition_id", "") or initial.get("proposition_id", "")),
            "effective_relation": {
                "subject": form.get("subject", ""),
                "relation": form.get("relation", ""),
                "object": form.get("obj", ""),
                "complement": form.get("complement", ""),
                "unknown_role": form.get("unknown_role", ""),
            },
            "unresolved": unresolved,
            "completeness": round(completeness, 6),
            "coherence": round(coherence, 6),
            "causal_chain": causal_chain,
            "wavelet_count": len(wavelets),
            "hurricane_condition": round(0.60 * completeness + 0.40 * coherence, 6),
            "retrospective_rule": "the developed understanding reconstructs the supported meaning of its initiating disturbance",
        }

    def _cycle_genealogy(self, wavelets: Sequence[CausalWavelet], revised: Mapping[str, Any]) -> Dict[str, Any]:
        roots = []
        parent_ids: List[str] = []
        for wave in wavelets:
            roots.extend(wave.roots)
            parent_ids.extend(wave.parent_ids)
        roots = list(dict.fromkeys(roots or list(AXES)))
        return {
            "root_constraints": roots,
            "canonical_signature": canonical_signature(tuple(roots)),
            "wavelet_ancestry": [
                {
                    "wavelet_id": wave.wavelet_id,
                    "primitive": wave.primitive,
                    "roots": list(wave.roots),
                    "signature": canonical_signature(tuple(wave.roots)),
                    "parent_ids": list(wave.parent_ids),
                }
                for wave in wavelets
            ],
            "parent_operation_ids": list(dict.fromkeys(parent_ids)),
            "semantic_genealogy": _clone(dict(revised.get("genealogy_trace") or {})),
        }

    # ------------------------------------------------------------------
    # Evidence, development, publication
    # ------------------------------------------------------------------
    def _update_wavelet_evidence(self, cycle: Mapping[str, Any], alignment: Mapping[str, Any]) -> None:
        score = _clip(alignment.get("score", 0.0))
        initial_score = _clip(dict(cycle.get("initial_semantic_state") or {}).get("completeness", 0.0))
        final_condition = _clip(dict(cycle.get("global_understanding") or {}).get("hurricane_condition", 0.0))
        gain = max(0.0, final_condition - initial_score) * score
        for wave in list(cycle.get("wavelets") or []):
            if str(wave.get("status", "")) not in {"trial", "promoted"}:
                continue
            for parent_id in list(wave.get("parent_ids") or []):
                rec = self._trial_wavelets.get(parent_id) or self._promoted_wavelets.get(parent_id)
                if rec is None:
                    continue
                rec["uses"] = int(rec.get("uses", 0) or 0) + 1
                if score >= 0.72:
                    rec["successes"] = int(rec.get("successes", 0) or 0) + 1
                rec["alignment_gain"] = float(rec.get("alignment_gain", 0.0) or 0.0) + gain

    def _confess_gap_if_needed(self, cycle: Mapping[str, Any], alignment: Mapping[str, Any]) -> None:
        score = _clip(alignment.get("score", 0.0))
        global_understanding = dict(cycle.get("global_understanding") or {})
        unresolved = list(global_understanding.get("unresolved") or [])
        if score >= 0.68 and not unresolved:
            return
        axes = dict(dict(cycle.get("interference") or {}).get("axis_after") or {})
        pressure = {ax: float(axes.get(ax, 0.0) or 0.0) for ax in AXES}
        for slot in unresolved:
            if slot in {"entity", "subject", "object"}:
                pressure["X"] += 0.30
                pressure["B"] += 0.20
            elif slot in {"relation"}:
                pressure["T"] += 0.24
                pressure["N"] += 0.30
                pressure["B"] += 0.20
            else:
                pressure["A"] += 0.18
                pressure["B"] += 0.16
        if score < 0.50:
            pressure["A"] += 0.25
            pressure["N"] += 0.20
        normalized_pressure = _normalize_axes(pressure)
        negative_dims = {
            "I_ISNT": normalized_pressure["X"],
            "I_CANNOT": normalized_pressure["T"],
            "I_DONOT": normalized_pressure["N"],
            "I_SOUGHT": normalized_pressure["B"],
            "I_DIDNT": normalized_pressure["A"],
            "REC_SURFACE": 0.05,
            "REC_SHALLOW": 0.12,
            "REC_MODERATE": 0.24,
            "REC_DEEP": 0.34 + 0.20 * (1.0 - score),
            "REC_CORE": 0.12 + 0.16 * (1.0 - score),
        }
        tick = int(time.time())
        try:
            self.check_and_extend(
                negative_dims,
                source=f"rcrw:{cycle.get('cycle_id', '')}:alignment={score:.3f}",
                tick=tick,
                topology_gap_ref=str(cycle.get("cycle_id", "") or ""),
            )
        except Exception:
            pass

    def _register_promoted_wavelet(self, component_id: str, rec: Mapping[str, Any]) -> None:
        genealogy = self.genealogy or self.systems.get("genealogy")
        if genealogy is None:
            return
        payload = {
            "component_id": component_id,
            "primitive": str(rec.get("primitive", "") or ""),
            "constraints": list(rec.get("roots") or AXES),
            "canonical_signature": canonical_signature(tuple(rec.get("roots") or AXES)),
            "parent_ids": list(rec.get("parent_ids") or []),
            "trial_score": float(
                getattr(self._warp_promoted.get(component_id), "trial_score_ema", 0.0) or 0.0
            ),
            "uses": int(rec.get("uses", 0) or 0),
            "successes": int(rec.get("successes", 0) or 0),
            "alignment_gain": float(rec.get("alignment_gain", 0.0) or 0.0),
        }
        if hasattr(genealogy, "register_recursive_causal_waveform"):
            try:
                out = dict(genealogy.register_recursive_causal_waveform(payload) or {})
                if out.get("ability_id"):
                    self._promoted_wavelets[component_id]["genealogy_ability_id"] = out["ability_id"]
            except Exception:
                pass

    def _publish_active_cycle(self, revised: Mapping[str, Any]) -> None:
        if not isinstance(self.systems, dict):
            return
        self.systems["_active_recursive_causal_cycle"] = _clone(self._active_cycle)
        self.systems["_last_recursive_causal_semantics"] = _clone(dict(revised or {}))
        introspection = self.systems.get("system_introspection")
        if introspection is not None and hasattr(introspection, "record_boundary_decision"):
            try:
                introspection.record_boundary_decision(
                    "aurora_internal.aurora_recursive_causal_reasoning_waveform.AuroraRecursiveCausalReasoningWaveform.prepare_semantic_state",
                    stage="recursive_causal_propagation",
                    inputs={
                        "raw_input": self._active_cycle.get("raw_input", ""),
                        "provisional_interpretation": self._active_cycle.get("provisional_interpretation", {}),
                    },
                    derived={
                        "wavelets": self._active_cycle.get("wavelets", []),
                        "interference": self._active_cycle.get("interference", {}),
                    },
                    decision="backproject_global_understanding",
                    output={
                        "effective_interpretation": self._active_cycle.get("effective_interpretation", {}),
                        "global_understanding": self._active_cycle.get("global_understanding", {}),
                    },
                    reason="the developed understanding recursively reconstructed its initiating disturbance without altering raw history",
                    confidence=float(self._active_cycle.get("global_understanding", {}).get("hurricane_condition", 0.0) or 0.0),
                    tags=["X", "T", "N", "B", "A", "recursive", "causal", "waveform"],
                )
            except Exception:
                pass

    def _publish_completion(self, cycle: Mapping[str, Any]) -> None:
        if not isinstance(self.systems, dict):
            return
        self.systems["_last_recursive_causal_cycle"] = _clone(dict(cycle or {}))
        contract = self.systems.get("understanding_contract")
        if contract is not None and hasattr(contract, "attach_pending_contributors"):
            try:
                contract.attach_pending_contributors({
                    "recursive_causal_reasoning_waveform": {
                        "cycle_id": cycle.get("cycle_id", ""),
                        "hurricane_condition": dict(cycle.get("global_understanding") or {}).get("hurricane_condition", 0.0),
                        "response_alignment": dict(cycle.get("response_wave") or {}).get("relation_alignment", {}),
                        "wavelet_count": len(list(cycle.get("wavelets") or [])),
                        "root_constraints": list(dict(cycle.get("genealogy_trace") or {}).get("root_constraints") or AXES),
                    }
                })
            except Exception:
                pass
        observer = self.systems.get("quasiarch_observer")
        if observer is not None and hasattr(observer, "observe"):
            try:
                observer.observe(
                    target="aurora.recursive_causal_reasoning_waveform",
                    issue="recursive_causal_cycle",
                    context={
                        "cycle_id": cycle.get("cycle_id", ""),
                        "effective_interpretation": cycle.get("effective_interpretation", {}),
                        "response_wave": cycle.get("response_wave", {}),
                    },
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Persistence and queries
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        return {
            "cycles": len(self._cycles),
            "active_cycle_id": str(self._active_cycle.get("cycle_id", "") or ""),
            "pending_response_cycle_id": self._pending_response_cycle_id,
            "trial_wavelets": len(self._trial_wavelets),
            "promoted_wavelets": len(self._promoted_wavelets),
            "dissolved_wavelets": self._dissolved_count,
            "warp": self.warp_status(),
            "root_constraints": list(AXES),
            "canonical_signature": canonical_signature(AXES),
        }

    def latest_cycle(self) -> Dict[str, Any]:
        return _clone(self._cycles[-1] if self._cycles else {})

    def cycle(self, cycle_id: str) -> Dict[str, Any]:
        found = self._find_cycle(str(cycle_id or ""))
        return _clone(found or {})

    def trace_to_roots(self, cycle_id: Optional[str] = None) -> Dict[str, Any]:
        rec = self._find_cycle(str(cycle_id or "")) if cycle_id else (self._cycles[-1] if self._cycles else None)
        if rec is None:
            return {}
        genealogy = dict(rec.get("genealogy_trace") or {})
        return {
            "cycle_id": rec.get("cycle_id", ""),
            "raw_input_preserved": True,
            "root_constraints": genealogy.get("root_constraints", list(AXES)),
            "canonical_signature": genealogy.get("canonical_signature", canonical_signature(AXES)),
            "wavelet_ancestry": genealogy.get("wavelet_ancestry", []),
            "parent_operation_ids": genealogy.get("parent_operation_ids", []),
            "causal_chain": dict(rec.get("global_understanding") or {}).get("causal_chain", []),
        }

    def _find_cycle(self, cycle_id: str) -> Optional[MutableMapping[str, Any]]:
        if not cycle_id:
            return self._cycles[-1] if self._cycles else None
        for rec in reversed(self._cycles):
            if str(rec.get("cycle_id", "")) == cycle_id:
                return rec
        return None

    def _load(self) -> None:
        if not self.persist or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self._cycles = [dict(x) for x in list(data.get("cycles") or []) if isinstance(x, Mapping)][-_MAX_CYCLES:]
        self._active_cycle = dict(data.get("active_cycle") or {})
        self._pending_response_cycle_id = str(data.get("pending_response_cycle_id", "") or "")
        self._promoted_wavelets = {str(k): dict(v) for k, v in dict(data.get("promoted_wavelets") or {}).items()}
        self._trial_wavelets = {str(k): dict(v) for k, v in dict(data.get("trial_wavelets") or {}).items()}
        self._dissolved_count = int(data.get("dissolved_count", 0) or 0)

    def _persist(self) -> None:
        if not self.persist:
            return
        payload = {
            "schema_version": 1,
            "updated_at": time.time(),
            "cycles": self._cycles[-_MAX_CYCLES:],
            "active_cycle": self._active_cycle,
            "pending_response_cycle_id": self._pending_response_cycle_id,
            "promoted_wavelets": self._promoted_wavelets,
            "trial_wavelets": self._trial_wavelets,
            "dissolved_count": self._dissolved_count,
        }
        try:
            atomic_write_json(self.state_path, payload, default=str)
        except Exception:
            pass

    def _append_history(self, cycle: Mapping[str, Any]) -> None:
        if not self.persist:
            return
        try:
            line = json.dumps(dict(cycle or {}), sort_keys=True, default=str)
            with self.history_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            # Bound the diagnostic history without touching live state.
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
            if len(lines) > _MAX_HISTORY_LINES:
                self.history_path.write_text("\n".join(lines[-_MAX_HISTORY_LINES:]) + "\n", encoding="utf-8")
        except Exception:
            pass
