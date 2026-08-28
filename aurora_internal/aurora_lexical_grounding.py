"""
aurora_lexical_grounding.py
============================

Build 771 (Constraint-Native Lexical Grounding), PR 3.

This module gives Aurora a place to grow her OWN, consequence-earned
interpretation of a word's structural role, sitting alongside -- never
replacing -- the hand-authored scaffolding in aurora_utterance_parser.py
(_WORD_ROLES / _PHRASE_ROLES) and aurora_constraint_semantic_continuity.py
(_RELATION_VERBS). Those lookups remain the working communicative baseline;
nothing in this module deletes or bypasses them (PR 1 tagged their output
"inherited_scaffold" so it can be told apart from what grows here).

Two things this module deliberately does NOT do, because doing either would
quietly reintroduce the same problem this build exists to remove:

1. It never stores an English label as a word's meaning. A LexicalCandidate
   carries an axis_profile, a structural applicability_family, and lineage --
   never a gloss. "because = causal relation" is not grounding; it just
   presumes the reader already understands "causal" and "relation".

2. `applicability_family` -- the key candidates are discovered and compared
   under -- is built ONLY from observable structural geometry: which slot
   (subject/relation/object/complement) the word occupies in
   extract_relational_form()'s output, what else is bound around it, live
   axis activation, continuity/negation/question shape, participant count,
   and already-earned ancestry. Never a semantic category name ("temporal",
   "causal", "comparative"). Two candidates for the same word in two
   genuinely different structural contexts may go on to earn two different
   consequence-derived meanings -- but the family they're discovered under
   never smuggles that distinction in ahead of time.

This is a new sibling WarpCapable surface (own trial pool, own promotion
gate), modeled directly on aurora_communication_emergence.py, NOT an
extension of it -- that module is lexical-blind by design (see its own
comments), so lexical grounding needs its own purpose-built trial pool
rather than repurposing one built to be lexical-free. OETS
(aurora_ontological_scaffolding.py) remains the single word address book;
this module reads/writes its SemanticNode/senses store by word key rather
than keeping a parallel index.

PR 3 scope: this module is additive and unconsumed. Nothing in the live
comprehension path calls observe_lexical_context() yet, and nothing
consumes a promoted LexicalCandidate as an authority over scaffolding --
that migration is PR 5's job, gated on PR 4's genealogy-consequence
scoring. _score_trial() here is a deliberately inert placeholder (a fixed
neutral floor, mirroring OETS's own "insufficient evidence" floor) so
nothing can reach "promoted" status from this module alone yet.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import (
    WarpCapable,
    WarpComponent,
    WarpTrigger,
    axes_to_istates,
    istates_to_axes,
    warp_guard,
)
from aurora_internal.aurora_constraint_semantic_continuity import AXES

_NEGATIVE_ISTATE = {"X": "I_ISNT", "T": "I_CANNOT", "N": "I_DONOT", "B": "I_SOUGHT", "A": "I_DIDNT"}
_POSITIVE_ISTATE = {"X": "I_IS", "T": "I_CAN", "N": "I_DO", "B": "I_SAW", "A": "I_DID"}
_RECURSION_DIMS = ("REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE")

# _score_trial()'s floor for a candidate that hasn't yet cleared the
# evidence-diversity minimums below. Deliberately well below
# aurora_warp_protocol.PROMOTION_SCORE (0.60).
_INERT_TRIAL_FLOOR = 0.34

# Build 771 PR 4: promotion requires BOTH minimums -- recurrence alone
# (evidence_count) is never sufficient; it must also recur across
# genuinely different surface wording (distinct_surfaces -- see
# _surface_hash()'s own docstring for why surface, not structural slot, is
# the diversity axis available within one matched candidate). Mirrors
# aurora_communication_emergence.py's _MIN_VALIDATED_TRIALS/
# _MIN_DISTINCT_SURFACES pattern exactly.
_MIN_EVIDENCE = 4
_MIN_DISTINCT_SURFACES = 2

_MAX_CANDIDATES = 4000
_MAX_PENDING_CONTEXT = 500
_MAX_SEEN_HISTORICAL_POSSIBILITIES = 60000

# Build 772 (Historical Lexical Consequence Attribution): bounded storage for
# the causal-attribution/replay index -- mirrors _pending_context's own
# capped, oldest-evicted pattern exactly. See aurora_internal/
# aurora_lexical_grounding.py's module docstring extension below for why
# these exist.
_MAX_HISTORICAL_IMPLICATIONS = 30000
_MAX_HISTORICAL_UNRESOLVED = 10000
_MAX_PER_WORD_IMPLICATIONS = 50
_MAX_REPLAY_PER_PROMOTION = 25

# Build 772: record_evidence_outcome()'s outcome_kind stays exactly the same
# 3 values aurora.py's live receiver-outcome fan-out already uses
# ("positive"/"negative"/"indeterminate") -- candidate_support() never reads
# anything else. discrimination_kind is a SEPARATE, purely descriptive field
# for observability (never read by scoring) that names WHAT KIND of
# historical signal produced a given outcome_kind. This mapping is the one
# place that decision is made, so "does X count toward promotion" is always
# answerable by reading one table, never by re-deriving it ad hoc at each
# call site. Every discrimination_kind that could plausibly recur many times
# without ever being a genuine discriminating consequence (continuation,
# conservation, unresolved) maps to "indeterminate" -- candidate_support()
# treats that identically to unvalidated, however many times it recurs.
_DISCRIMINATION_TO_OUTCOME = {
    "explicit_correction": "negative",
    "contradiction": "negative",
    "differentiation_supported": "positive",
    "successful_relational_continuation": "indeterminate",
    "repeated_contextual_conservation": "indeterminate",
    "unresolved_continuation": "indeterminate",
}


def _clip01(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def _stable_hash(payload: Any, length: int = 14) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        raw = str(payload)
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _surface_hash(raw_text: str) -> str:
    """Build 771 PR 4's diversity signal, mirroring
    aurora_communication_emergence.py's own _surface_hash()/
    distinct_surfaces precedent exactly. An exact applicability_family
    match always shares identical structural geometry by construction (two
    observations only match exactly when their geometry hash is the same),
    so structural fields can never vary WITHIN one candidate's own
    evidence -- they cannot be this candidate's recurrence-across-context
    signal. Different literal sentences CAN share one structural geometry
    while differing in surface wording ("A glorp is heavier than a cup."
    vs "A glorp weighs more than a mug." could both bind the same
    subject/relation/object shape) -- that surface diversity, not
    structural-slot diversity, is what "the same word recurring across
    genuinely different exchanges" actually looks like at this layer."""
    normalized = re.sub(r"\s+", " ", str(raw_text or "").strip().lower())
    return _stable_hash(normalized, 12)


def _expand_to_15d(axis_profile: Mapping[str, float]) -> Dict[str, float]:
    """Mirror AxisCoverageChecker._ensure_full_dims()'s own expansion of a
    legacy 5-axis dict, so a pending-context lookup keyed by this exact
    expansion matches the CoverageGap's own axis_profile (which is always
    the post-expansion 15D form -- see AxisCoverageChecker.check())."""
    profile = dict(axis_profile or {})
    if any(k in _NEGATIVE_ISTATE.values() or k in _POSITIVE_ISTATE.values() for k in profile):
        result = dict(profile)
    else:
        result = axes_to_istates({ax: float(profile.get(ax, 0.0) or 0.0) for ax in AXES}, ivm_polarity=None)
    for dim in _RECURSION_DIMS:
        result.setdefault(dim, 0.0)
    return result


def _profile_key(axis_profile: Mapping[str, float]) -> str:
    dims = list(_NEGATIVE_ISTATE.values()) + list(_POSITIVE_ISTATE.values()) + list(_RECURSION_DIMS)
    normalized = {dim: round(float(dict(axis_profile or {}).get(dim, 0.0) or 0.0), 3) for dim in dims}
    return _stable_hash(normalized, 16)


def _identity_axis_profile(
    word: str, applicability_family: str, axis_activation: Mapping[str, float]
) -> Dict[str, float]:
    """The axis profile WarpGenerator derives BOTH the gap-persistence
    signature (_gap_signature) AND the resulting component_id (_make_id)
    from -- purely numeric axis coordinates, with no notion of "word" or
    "family" built into either. When real axis_activation is supplied, it
    is used directly (the genuine live pressure reading). When it is not
    (the common case with no live comprehension call site wired yet, and
    the default this module falls back to), returning one flat profile for
    every word would collapse every word's gap-persistence counter and
    generated component_id onto the same identity -- Codex review, PR
    #179: "observing three different words starts a trial for only the
    third word". WarpGenerator has no other notion of "these are different
    things" to fall back on, so this derives a deterministic, word+family-
    keyed synthetic profile instead: one axis (chosen by hash) pushed
    clearly above AxisCoverageChecker's dominance floor (0.40) -- clearly
    above even after axes_to_istates()'s neutral-polarity split halves it.
    This carries NO semantic content -- it is an identity discriminator,
    never a claim about the word's actual constraint pressure -- and the
    SAME (word, family) pair always produces the SAME profile, which is
    required for GAP_PERSISTENCE_REQUIRED's repeat-observation counting to
    ever fire at all.
    """
    real = {ax: _clip01(dict(axis_activation or {}).get(ax, 0.0)) for ax in AXES}
    if any(real.values()):
        return real
    digest = hashlib.sha1(f"{word}:{applicability_family}".encode("utf-8")).digest()
    dominant = AXES[digest[0] % len(AXES)]
    magnitude = 0.85 + 0.13 * (digest[1] / 255.0)
    return {ax: (magnitude if ax == dominant else 0.05) for ax in AXES}


def _word_slot(word: str, form: Mapping[str, Any]) -> str:
    """Which structural slot (if any) extract_relational_form() actually
    bound this word into -- observed placement, not a grammar-theory
    prediction of where it "should" go. Purely structural: this reads
    which of the already-bound subject/relation/obj/complement strings
    contains the word, nothing about what the word means.
    """
    w = str(word or "").strip().lower()
    if not w:
        return "unbound"
    for slot in ("relation", "subject", "obj", "complement"):
        value = str(form.get(slot, "") or "").lower()
        if value and w in value.split():
            return slot
    return "unbound"


def _lexical_geometry(
    word: str,
    form: Mapping[str, Any],
    axis_activation: Mapping[str, float],
    parent_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """The ONLY inputs a family may legitimately be built from (Build 771
    invariant 5): clause topology (slot), position/neighboring bindings,
    live axis activation, continuity characteristics, relation direction
    (which slot -- subject vs object carries opposite directional roles),
    participant configuration, pressure geometry, and already-earned
    ancestry. No semantic category ever appears here.
    """
    rel = dict(form or {})
    slot = _word_slot(word, rel)
    neighbors = {
        "subject_bound": bool(rel.get("subject")) and slot != "subject",
        "relation_bound": bool(rel.get("relation")) and slot != "relation",
        "object_bound": bool(rel.get("obj")) and slot != "obj",
        "complement_bound": bool(rel.get("complement")) and slot != "complement",
    }
    participant_count = sum(1 for k in ("subject", "relation", "obj", "complement") if rel.get(k))
    continuity = bool(rel.get("continuity_bindings")) or bool(rel.get("unresolved_references"))
    activation = {ax: _clip01(dict(axis_activation or {}).get(ax, 0.0)) for ax in AXES}
    dominant_axis = ""
    if any(activation.values()):
        dominant_axis = max(AXES, key=lambda ax: activation[ax])
    return {
        "slot": slot,
        "question": bool(rel.get("question")),
        "directive": bool(rel.get("directive")),
        "negated": bool(rel.get("negated")),
        "neighbors": neighbors,
        "participant_count": int(participant_count),
        "continuity": continuity,
        "dominant_axis": dominant_axis,
        "axis_bucket": {ax: round(activation[ax], 1) for ax in AXES},
        "ancestry": sorted(str(p) for p in (parent_ids or [])),
    }


def _applicability_family(geometry: Mapping[str, Any]) -> str:
    return "LEXFAM:" + _stable_hash(dict(geometry or {}), 14)


def _geometry_similarity(current: Mapping[str, Any], candidate: Mapping[str, Any]) -> float:
    """Bounded structural similarity between two word-in-context geometries
    for the SAME word (see _select_candidate) -- never a comparison of
    words or meanings, only of clause topology/neighbors/axis/continuity.
    """
    left, right = dict(current or {}), dict(candidate or {})
    if not left or not right:
        return 0.0
    if bool(left.get("question")) != bool(right.get("question")):
        return 0.0
    score = 0.0
    if left.get("slot") == right.get("slot"):
        score += 0.30
    if bool(left.get("directive")) == bool(right.get("directive")):
        score += 0.06
    if bool(left.get("negated")) == bool(right.get("negated")):
        score += 0.06
    if bool(left.get("continuity")) == bool(right.get("continuity")):
        score += 0.10
    if left.get("dominant_axis") and left.get("dominant_axis") == right.get("dominant_axis"):
        score += 0.18
    if left.get("participant_count") == right.get("participant_count"):
        score += 0.10
    ln, rn = dict(left.get("neighbors") or {}), dict(right.get("neighbors") or {})
    if ln and rn:
        matches = sum(1 for k in ln if ln.get(k) == rn.get(k))
        score += 0.20 * (matches / max(1, len(ln)))
    return round(_clip01(score), 6)


@dataclass
class LexicalCandidate:
    """One Aurora-native representational hypothesis for how a word
    participates in a structural configuration -- deliberately no `gloss`
    field. structural_geometry mirrors EmergentCommunicationOperation's own
    applicability_shape field: the raw structural signals the
    applicability_family hash was built from, kept for similarity
    comparison and (in PR 4) genealogy tagging -- never an English
    definition.
    """
    candidate_id: str
    word: str
    component_id: str
    axis_profile: Dict[str, float]
    applicability_family: str
    parent_ids: List[str]
    structural_geometry: Dict[str, Any] = field(default_factory=dict)
    # The 5-axis constraints this candidate's axis_profile actually leans
    # on, derived once at integration time (istates_to_axes() thresholded)
    # -- stored rather than re-derived at registration, mirroring
    # EmergentCommunicationOperation.root_constraints being computed once
    # and read later by _register_genealogy(), never recomputed from a
    # possibly-drifted live profile.
    dominant_constraints: List[str] = field(default_factory=list)
    status: str = "trial"
    created_at: float = field(default_factory=time.time)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    genealogy_ability_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuroraLexicalGrounding(WarpCapable):
    """Cultivates consequence-earned lexical role candidates through
    Aurora's own X/T/N/B/A roots -- a sibling surface to
    AuroraCommunicationEmergence, not an extension of it."""

    def __init__(
        self,
        *,
        state_dir: str = "aurora_state",
        persist: bool = True,
        genealogy: Any = None,
    ) -> None:
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = os.path.join(self.state_dir, "lexical_grounding_state.json")
        self.systems: Dict[str, Any] = {}
        self._candidates: Dict[str, LexicalCandidate] = {}
        # profile_key(15D axis profile) -> pending word/family context,
        # written just before check_and_extend() so _warp_params()/
        # _integrate_warp() (which only ever receive the gap's own
        # axis_profile) can recover which word/geometry spawned it. Mirrors
        # aurora_communication_emergence.py's _profile_family side channel.
        self._pending_context: Dict[str, Dict[str, Any]] = {}
        self._tick: int = 0
        # Build 771 PR 7: dedup for observe_historical_lexical_possibility()
        # -- mirrors aurora_communication_emergence.py's own
        # _seen_possibilities exactly, so replaying the same historical
        # episode (checkpoint restore, re-processed baseline) never feeds
        # the same exchange pair twice.
        self._seen_historical_possibilities: Dict[str, float] = {}
        # Build 771 PR 7 (Codex review, PR #184): mirrors
        # aurora_communication_emergence.py's own _persistence_suspended
        # exactly, so a caller checkpointing multiple durable substrates
        # together (see aurora_historical_experience_environment.py's
        # _save_crystal_substrate()) can hold this module's writes back
        # until its own explicit save() runs, keeping this substrate from
        # ever advancing ahead of a sibling substrate between checkpoints.
        self._persistence_suspended: int = 0
        # Consequence-closure follow-up: transient, unpersisted record of
        # which (candidate_id, evidence_id) pairs observe_lexical_context()
        # touched since the last drain -- the turn's own causal trace for
        # this module. Never written to disk (drain_turn_consumption_trace()
        # is read-and-clear, called once per emitted response by aurora.py's
        # _build_communication_contributors()), so a restart mid-turn simply
        # loses an in-flight turn's attribution the same way every other
        # contributor's own "_last_*" breadcrumb already does -- not a new
        # durability requirement invented for this module.
        self._turn_consumption_trace: List[Dict[str, str]] = []
        # Build 772 (Historical Lexical Consequence Attribution): the
        # causal-attribution/replay index -- one structure serving two
        # purposes at once: (1) "preserve enough causal attribution to
        # revisit that candidate when subsequent chronological events
        # arrive" for correction/contradiction/continuation detection
        # (PR 2), and (2) the index developmental replay (PR 3) uses to
        # find which historical pairs are worth re-deriving once a new
        # promotion improves what Aurora can resolve. Bounded and
        # oldest-evicted, mirroring _pending_context's own pattern exactly
        # -- persisted so a restart never loses causal attribution that
        # was already durably retained, but never grows unbounded across
        # a 50k-event archive.
        self._historical_implications: Dict[str, Dict[str, Any]] = {}
        self._historical_implications_by_word: Dict[str, List[str]] = {}
        self._historical_unresolved: Dict[str, Dict[str, Any]] = {}
        self._historical_unresolved_by_word: Dict[str, List[str]] = {}
        self._historical_diag: Dict[str, int] = {
            "historical_pairs_examined": 0,
            "lexical_candidates_formed_historical": 0,
            "historical_outcomes_attributed": 0,
            "explicit_corrections_detected": 0,
            "discriminating_historical_consequences": 0,
            "candidates_promoted_with_historical_contribution": 0,
            "unresolved_historical_lexical_gaps": 0,
            "replay_eligible_observations": 0,
            "replayed_observations": 0,
            "new_distinctions_from_replay": 0,
            "promotions_from_replay": 0,
        }
        # (loaded_at, pairs) -- aurora_oets_web.json's opposite_of relations,
        # cached rather than re-read from disk on every one of a 50k-event
        # archive's historical pairs (see _load_contradicts_pairs() at PR 2).
        self._contradicts_pairs_cache: Tuple[float, set] = (0.0, set())
        self._init_warp(genealogy=genealogy)
        self._load()

    def attach_systems(self, systems: Mapping[str, Any]) -> None:
        self.systems = dict(systems or {}) if not isinstance(systems, dict) else systems
        genealogy = self.systems.get("genealogy")
        if genealogy is not None:
            self.set_warp_genealogy(genealogy)
        sedi = self.systems.get("sedimemory")
        if sedi is not None:
            try:
                self.connect_sedimemory(sedi)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # WarpCapable implementation
    # ------------------------------------------------------------------

    def _warp_level_name(self) -> str:
        return "lexical_role_grounding"

    def evaluate_warp_trials(self) -> Tuple[List[str], List[str]]:
        """Override for two reasons:

        1. Persist AFTER WarpCapable's own dict mutation completes.
        WarpCapable.evaluate_warp_trials() calls _dissolve_warp() (or moves
        a component into _warp_promoted) BEFORE removing it from
        self._warp_trials -- persisting only from inside _dissolve_warp(),
        as this module's other hooks do (matching
        aurora_communication_emergence.py's own precedent), saves a
        snapshot where a just-dissolved trial is still listed as active.
        Codex review, PR #179: "Restarting immediately therefore resurrects
        the dissolved component as an active WARP trial." This second
        persist, once the base class has actually returned, guarantees the
        saved state matches the real in-memory state.

        2. Build 771 PR 4: WarpCapable has no promotion callback at all (it
        moves a component into self._warp_promoted directly, with nothing
        for a subclass to hook), so this is also the only point where a
        freshly-promoted candidate's status can be updated and its
        consequence-earned grounding registered into genealogy + written
        back into OETS -- mirrors aurora_communication_emergence.py's own
        evaluate_development() wrapper exactly.
        """
        promoted, dissolved = super().evaluate_warp_trials()
        for component_id in promoted:
            candidate = self._candidates.get(component_id)
            if candidate is None:
                continue
            candidate.status = "promoted"
            candidate.genealogy_ability_id = self._register_genealogy(candidate, self._warp_promoted.get(component_id))
            self._write_back_oets(candidate)
        if promoted or dissolved:
            self._persist()
        return promoted, dissolved

    def _register_genealogy(self, candidate: "LexicalCandidate", component: Optional[WarpComponent]) -> str:
        """Mirrors aurora_communication_emergence.py's own
        _register_genealogy() precedent exactly: builds the registration
        payload from the candidate's own already-computed fields (never
        re-derives ancestry from a possibly-drifted live profile), calls
        genealogy's registration method, and returns the resulting
        ability_id (empty string on any failure -- registration is
        best-effort and must never break the WARP promotion it's
        reacting to)."""
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if genealogy is None:
            return ""
        distinct_surfaces = len({str(e.get("surface_hash", "") or "") for e in candidate.evidence if e.get("surface_hash")})
        payload = {
            "word": candidate.word,
            "component_id": candidate.component_id,
            "applicability_family": candidate.applicability_family,
            "constraints": list(candidate.dominant_constraints),
            "parent_ids": list(candidate.parent_ids),
            "trial_score": float(getattr(component, "trial_score_ema", 0.0) or 0.0),
            "evidence_count": len(candidate.evidence),
            "distinct_surfaces": distinct_surfaces,
        }
        if hasattr(genealogy, "register_emergent_lexical_grounding"):
            try:
                result = dict(genealogy.register_emergent_lexical_grounding(payload) or {})
                return str(result.get("ability_id", "") or "")
            except Exception:
                return ""
        return ""

    def _write_back_oets(self, candidate: "LexicalCandidate") -> None:
        """On promotion, write the consequence-earned grounding back into
        OETS (the single word address book -- no parallel index kept
        here). gloss stays empty: nothing reads it as authority, it is
        never anything but a human-debug label, and this build's whole
        point is that the meaning is the axis_profile/applicability_family/
        lineage, not an English string. source="constraint_earned" is the
        one value PR 1 reserved specifically for this moment. Best-effort
        and silent on failure -- OETS may not be wired into self.systems
        in every boot context, and that must never break WARP promotion.
        """
        if not candidate.genealogy_ability_id:
            return
        oets = self.systems.get("oets")
        web = getattr(oets, "web", None) if oets is not None else None
        if web is None or not hasattr(web, "nodes"):
            return
        try:
            node = web.nodes.get(candidate.word)
            if node is None or not hasattr(node, "add_sense"):
                return
            sense_id = f"{candidate.word}.{candidate.applicability_family}"
            node.add_sense(
                sense_id=sense_id,
                gloss="",
                source="constraint_earned",
                confidence=0.5,
                grounded_ability_id=candidate.genealogy_ability_id,
            )
        except Exception:
            pass

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        # A minimal per-axis coverage baseline, mirroring
        # aurora_communication_emergence.py's own root-pressure seeding:
        # AxisCoverageChecker.check() vacuously returns "no gap" when its
        # component dict is empty, so without SOME existing profile a
        # genuinely novel word-in-context signature could never even be
        # recognized as new. These five entries are a stable floor, not a
        # claim that any axis is itself "resolved" for lexical purposes.
        profiles: Dict[str, Dict[str, float]] = {
            f"lexical_root_pressure:{ax}": {_NEGATIVE_ISTATE[ax]: 1.0, _POSITIVE_ISTATE[ax]: 0.15}
            for ax in AXES
        }
        for candidate in self._candidates.values():
            if candidate.status == "promoted":
                comp = self._warp_promoted.get(candidate.component_id)
                if comp is not None:
                    profiles[candidate.component_id] = dict(comp.axis_profile)
        return profiles

    def _warp_params(self, gap: Any, parent_ids: List[str]) -> Dict[str, Any]:
        context = dict(self._pending_context.get(_profile_key(gap.axis_profile), {}) or {})
        return {
            "word": str(context.get("word", "") or ""),
            "applicability_family": str(context.get("applicability_family", "") or ""),
            "structural_geometry": dict(context.get("geometry") or {}),
            "provenance": str(context.get("provenance", "inherited_scaffold") or "inherited_scaffold"),
            "parent_ids": list(dict.fromkeys(list(parent_ids or []) + list(context.get("parent_ids") or []))),
            "surface_hash": str(context.get("surface_hash", "") or ""),
            "extra_evidence": dict(context.get("extra_evidence") or {}),
        }

    def _integrate_warp(self, component: WarpComponent) -> None:
        params = dict(component.parameters or {})
        word = str(params.get("word", "") or "")
        if not word:
            return
        candidate_id = "LEX:" + _stable_hash(
            {"word": word, "component": component.component_id, "family": params.get("applicability_family", "")},
            14,
        )
        # Recover the 5-axis constraints this candidate's 15D axis_profile
        # actually leans on, once, at birth -- mirrors
        # aurora_communication_emergence.py's own `roots` derivation
        # (threshold 0.12) and is stored on the candidate rather than
        # re-derived later, same precedent as EmergentCommunicationOperation
        # .root_constraints being computed once at integration time.
        axes_5d = istates_to_axes(dict(component.axis_profile or {}))
        dominant_constraints = [ax for ax in AXES if float(axes_5d.get(ax, 0.0) or 0.0) >= 0.12] or list(AXES)
        candidate = LexicalCandidate(
            candidate_id=candidate_id,
            word=word,
            component_id=component.component_id,
            axis_profile=dict(component.axis_profile),
            applicability_family=str(params.get("applicability_family", "") or ""),
            parent_ids=list(dict.fromkeys(list(component.parent_ids or []) + list(params.get("parent_ids") or []))),
            structural_geometry=dict(params.get("structural_geometry") or {}),
            dominant_constraints=dominant_constraints,
        )
        # Codex review, PR #184: the pair that FOUNDS a trial (the first
        # observation of a genuinely novel word/family combination) must
        # get its own evidence entry too, seeded from the same extra_evidence
        # observe_lexical_context()'s MATCHED branch already threads through
        # -- otherwise a founding historical pair's provenance
        # (possibility_id, epistemic hedging) is silently dropped, and only
        # LATER matched pairs against this candidate ever carry it.
        extra_evidence = dict(params.get("extra_evidence") or {})
        founding_evidence_id = _stable_hash(
            {"candidate": candidate_id, "component": component.component_id, "founding": True}, 12
        )
        candidate.evidence.append({
            "evidence_id": founding_evidence_id,
            "provenance": str(params.get("provenance", "inherited_scaffold") or "inherited_scaffold"),
            "slot": dict(params.get("structural_geometry") or {}).get("slot", "unbound"),
            "selection_kind": "trial_founding",
            "surface_hash": str(params.get("surface_hash", "") or ""),
            "tick": component.trial_tick,
            "validated": False,
            **extra_evidence,
        })
        # Consequence-closure follow-up: the founding pair is just as much
        # a live participant in this turn's causal chain as any later
        # matched pair against the same candidate -- see the identical note
        # (including the historical-replay exclusion) in
        # observe_lexical_context()'s matched branch.
        if str(params.get("provenance", "") or "") != "historical_possibility":
            self._turn_consumption_trace.append({
                "candidate_id": candidate_id,
                "evidence_id": founding_evidence_id,
                "word": word,
                "applicability_family": str(params.get("applicability_family", "") or ""),
            })
        self._candidates[component.component_id] = candidate
        if len(self._candidates) > _MAX_CANDIDATES:
            oldest = sorted(self._candidates.values(), key=lambda c: c.created_at)[: len(self._candidates) - _MAX_CANDIDATES]
            for stale in oldest:
                self._candidates.pop(stale.component_id, None)
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        """Delegates to candidate_support() -- see that method for the
        actual scoring logic. Kept as a thin WarpCapable-protocol adapter
        (component -> candidate lookup) so candidate_support() itself can
        be called directly with a LexicalCandidate by callers that never
        touch a WarpComponent, e.g. comprehension-gap ambiguity comparison
        (Build 771 consequence-closure follow-up)."""
        candidate = self._candidates.get(component.component_id)
        if candidate is None:
            return 0.0
        return self.candidate_support(candidate)

    def candidate_support(self, candidate: "LexicalCandidate") -> float:
        """Build 771 PR 4: evidence-derived score, gated on BOTH sample
        volume AND surface diversity AMONG VALIDATED, POSITIVELY-OUTCOMED
        EVIDENCE ONLY -- mirrors aurora_communication_emergence.py's own
        _score_trial() exactly (`validated = [e for e in evidence if
        e.get("validated")]`, filtered before any volume/diversity check
        runs), extended by the consequence-closure follow-up below.

        Codex review, PR #181/#182: the first version of this method
        scored ALL evidence -- volume and surface diversity alone, with no
        requirement that any observation was ever actually confirmed or
        corrected by a real downstream consequence. That let repeated
        SCAFFOLD-DRIVEN parses (recorded as evidence purely because a
        word occupied a slot, never because anyone checked whether that
        interpretation held up) accumulate enough volume+diversity to
        promote on their own -- "varied repetitions of an incorrect
        interpretation are sufficient to grant semantic authority" is
        exactly the frequency-is-not-understanding failure this whole
        build exists to prevent, and the first version of this method
        committed it despite its own docstring saying it wouldn't.

        Fixed: only evidence entries with validated=True (set by
        record_evidence_outcome()) count toward the volume+diversity
        floor.

        Consequence-closure follow-up: validated=True alone was still not
        enough. record_evidence_outcome() marks an entry validated=True
        whenever ANY real downstream consequence reached it -- confirmed
        OR corrected -- because "validated" means "consequence was
        actually checked," not "consequence was favorable." Counting a
        CORRECTED evidence entry toward promotion the same as a CONFIRMED
        one would let a wrong interpretation's own correction feed its
        promotion -- the same frequency-is-not-understanding failure in a
        new shape. Only evidence whose outcome_kind is specifically
        "positive" (the exact label aurora.py's _finalize_validated_
        communication() already uses for a genuinely confirmed receiver
        outcome, never invented here) counts as a discriminating success;
        a corrected entry stays validated (so it is never re-attributed
        or double-counted) but does not help the floor on its own.

        Build 772 (Historical Lexical Consequence Attribution): "no penalty
        machinery" stopped being the honest description once historical
        chronology could supply EXPLICIT corrections/contradictions against
        an already-promotable trial (see record_evidence_outcome()'s
        discrimination_kind param) -- the directive's own bar is "explicit
        correction must be capable of WEAKENING the implicated
        interpretation," which merely not-helping can never do once the
        floor is already cleared. Once the volume+diversity minimums are
        met, a `regression_penalty` mirrors aurora_communication_emergence.
        py's own _score_trial() exactly (`min(0.55, 0.18 * len(negative))`)
        -- the identical established shape for how negative evidence should
        suppress a sibling module's trial score, not a new formula invented
        for this one. A candidate that has ALREADY been promoted is
        unaffected by this (its score comes from genealogy's consequence_
        profile below, never re-derived from raw evidence again) --
        promotion is never retracted; a genuinely different sense of the
        same word earns its own independent promotion via WARP's existing
        no-winner-take-all trial pool instead.

        If this candidate already has a registered genealogy ability with
        its own measured consequence_profile (only possible after a prior
        promotion cycle), that confidence-weighted reading takes
        precedence once it exists -- genealogy's own consequence
        attribution is the authoritative post-promotion signal.
        """
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if candidate.genealogy_ability_id and genealogy is not None:
            ability = dict(getattr(genealogy, "abilities", {}) or {}).get(candidate.genealogy_ability_id)
            consequence = getattr(ability, "consequence_profile", None) if ability is not None else None
            if consequence:
                return _clip01(dict(consequence).get("confidence", 0.0))
        validated = [
            e for e in candidate.evidence
            if e.get("validated") is True and str(e.get("outcome_kind") or "") == "positive"
        ]
        evidence_count = len(validated)
        distinct_surfaces = len({str(e.get("surface_hash", "") or "") for e in validated if e.get("surface_hash")})
        if evidence_count < _MIN_EVIDENCE or distinct_surfaces < _MIN_DISTINCT_SURFACES:
            return _INERT_TRIAL_FLOOR
        negative = [
            e for e in candidate.evidence
            if e.get("validated") is True and str(e.get("outcome_kind") or "") == "negative"
        ]
        regression_penalty = min(0.55, 0.18 * len(negative))
        return _clip01(0.55 + 0.06 * distinct_surfaces - regression_penalty)

    def record_evidence_outcome(
        self,
        *,
        candidate_id: str,
        evidence_id: str,
        outcome_kind: str = "indeterminate",
        observed_effect: str = "",
        discrimination_kind: str = "",
        evidence_source: str = "live",
    ) -> Dict[str, Any]:
        """The validation-reporting entrance candidate_support() actually
        gates on -- mirrors aurora_communication_emergence.py's own
        record_receiver_outcome() exactly: marks ONE specific evidence
        entry (identified by the evidence_id stamped on it when it was
        recorded) validated=True, with an outcome_kind describing what
        was actually observed.

        Consequence-closure follow-up: called from aurora.py's
        _finalize_validated_communication(), the SAME existing fan-out
        that already routes a receiver's next-turn outcome to every other
        contributor (concept_crystal, representation, communication_
        emergence, ...) -- a lexical candidate is just one more
        attributable participant in that same causal chain, reached via
        contributors["lexical_grounding"] entries drain_turn_consumption_
        trace() supplied when this candidate's evidence was created. No
        lexical-specific success oracle is introduced here: outcome_kind
        is always exactly the "positive"/"negative"/"indeterminate" label
        that fan-out already derived for every other contributor from the
        SAME receiver signal (confirmation, correction, or an existing
        relational-preservation/failure surface) -- never a new judgment
        invented for this module alone.

        Build 772 (Historical Lexical Consequence Attribution):
        discrimination_kind and evidence_source are the "only as necessary"
        extension the directive asks for -- both purely descriptive,
        neither read by candidate_support()'s scoring (which only ever
        reads outcome_kind). discrimination_kind names WHICH historical
        signal (see _DISCRIMINATION_TO_OUTCOME) produced this outcome_kind,
        e.g. "explicit_correction"/"repeated_contextual_conservation";
        evidence_source distinguishes "live"/"historical"/"developmental_
        replay" provenance for the historical diagnostics counters. Every
        existing call site (aurora.py's live receiver-outcome fan-out)
        omits both, so live behavior is byte-for-byte unchanged -- this is
        not a second promotion mechanism, just finer-grained tagging on
        the exact same evidence entries the existing mechanism already
        writes.
        """
        # self._candidates is keyed by component_id, not candidate_id --
        # candidate_id is the LexicalCandidate's own identity field, the
        # natural thing an external caller would hold onto, so search by
        # it rather than exposing the internal component_id keying.
        candidate = next((c for c in self._candidates.values() if c.candidate_id == candidate_id), None)
        if candidate is None:
            return {"recorded": False, "reason": "unknown_candidate"}
        for evidence in reversed(candidate.evidence):
            if str(evidence.get("evidence_id", "") or "") == str(evidence_id or ""):
                evidence["validated"] = True
                evidence["outcome_kind"] = str(outcome_kind or "indeterminate")
                evidence["observed_effect"] = str(observed_effect or "")
                if discrimination_kind:
                    evidence["discrimination_kind"] = str(discrimination_kind)
                evidence["evidence_source"] = str(evidence_source or "live")
                self._persist()
                return {"recorded": True, "candidate_id": candidate_id, "evidence_id": evidence_id}
        return {"recorded": False, "reason": "unknown_evidence_id"}

    def drain_turn_consumption_trace(self) -> List[Dict[str, str]]:
        """Read-and-clear: returns every (candidate_id, evidence_id) pair
        touched since the last drain, then empties the internal list.

        Consequence-closure follow-up: called once per emitted response by
        aurora.py's _build_communication_contributors() -- the SAME point
        that already captures every other contributor's own breadcrumb
        (concept_crystal, representation, language_field, ...) into that
        turn's contributors dict. Drain-on-read rather than an explicit
        per-turn reset call: it cannot leak a stale entry across turns even
        if some caller forgets to reset it, and it naturally scopes to
        "everything touched since the last time this was read" regardless
        of how many nested calls into observe_lexical_context() happened
        underneath. Never persisted -- this is turn-scoped runtime
        bookkeeping, not durable state; an interrupted turn simply loses
        its own in-flight attribution the same way every other
        contributor's own "_last_*" breadcrumb already does.
        """
        trace = list(self._turn_consumption_trace)
        self._turn_consumption_trace = []
        return trace

    def _dissolve_warp(self, component_id: str) -> None:
        candidate = self._candidates.get(component_id)
        if candidate is not None:
            candidate.status = "dissolved"
        self._persist()

    # ------------------------------------------------------------------
    # Observation entrance
    # ------------------------------------------------------------------

    def _select_candidate(
        self, word: str, geometry: Mapping[str, Any], applicability_family: str
    ) -> Tuple[Optional[LexicalCandidate], Dict[str, Any]]:
        """Mirrors AuroraCommunicationEmergence._select_operation()'s
        exact-match-then-similarity-with-threshold pattern, scoped to
        candidates for THIS word only -- a lexical candidate is always
        word-keyed, so "similar enough" is judged only among a word's own
        prior candidates, never borrowed across words."""
        same_word = [c for c in self._candidates.values() if c.word == word and c.status in {"trial", "promoted"}]
        exact = [c for c in same_word if c.applicability_family == applicability_family]
        if exact:
            exact.sort(key=lambda c: (c.status == "promoted", len(c.evidence), c.created_at), reverse=True)
            return exact[0], {"kind": "exact", "score": 1.0}

        ranked: List[Tuple[float, LexicalCandidate]] = []
        for candidate in same_word:
            score = _geometry_similarity(geometry, candidate.structural_geometry)
            if score > 0.0:
                ranked.append((score, candidate))
        if not ranked:
            return None, {"kind": "none", "score": 0.0}
        ranked.sort(key=lambda item: (item[0], item[1].status == "promoted", len(item[1].evidence), item[1].created_at), reverse=True)
        score, candidate = ranked[0]
        if score < 0.72:
            return None, {"kind": "below_threshold", "score": score}
        return candidate, {"kind": "structural_nearest", "score": score}

    def _submit_gap(
        self,
        *,
        word: str,
        axis_profile: Mapping[str, float],
        applicability_family: str,
    ) -> Optional[WarpComponent]:
        """Fires the universal confession (warp_guard) for observability,
        then grows this module's own local trial pool via
        check_and_extend() -- modeled on aurora_language_field.py's
        _confess_comparison_uncertainty precedent for the warp_guard call,
        and kept unconditional (not gated behind whether a global warp_field
        is wired into self.systems) so this module stays testable in
        isolation, per PR 3's scope.
        """
        try:
            warp_guard(
                source="lexical_grounding",
                layer="word_role_resolution",
                trigger=WarpTrigger.NO_LANGUAGE_FORM,
                unresolved_text=word,
                profile=dict(axis_profile),
                severity=0.4,
                persistence_key=f"lexical:{word}:{applicability_family}",
            )
        except Exception:
            pass
        self._tick += 1
        component = self.check_and_extend(dict(axis_profile), source="lexical_grounding", tick=self._tick)
        if component is not None:
            # check_and_extend() calls _integrate_warp() (whose own
            # _persist() runs) BEFORE inserting the new component into
            # self._warp_trials -- that insertion happens after
            # _integrate_warp() returns, here, inside check_and_extend()
            # itself. Persisting again now that check_and_extend() has
            # actually returned guarantees the saved warp_trials dict
            # includes this trial. Codex review, PR #179: without this,
            # "the candidate reloads as a trial but its WarpComponent does
            # not, so it can never be evaluated, promoted, or dissolved."
            self._persist()
        return component

    def observe_lexical_context(
        self,
        *,
        word: str,
        relational_form: Mapping[str, Any],
        axis_activation: Optional[Mapping[str, float]] = None,
        provenance: str = "inherited_scaffold",
        extra_evidence: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Entrance: observe one word sitting in one turn's structural
        context. Purely observational plumbing -- does not decide what the
        word MEANS, does not touch or alter any scaffold lookup.

        extra_evidence (Build 771 PR 7): optional fields merged into the
        evidence entry on a match -- used by
        observe_historical_lexical_possibility() to carry its epistemic
        hedging (truth_assumed, receiver_validation_assumed, ...) into the
        evidence trail without this method needing to know anything about
        historical exchanges. Every live call site simply omits it.

        Returns a dict describing what happened this call: {"action":
        "matched" | "trial_started" | "trial_continuing" | "no_signal", ...}
        """
        word_key = str(word or "").strip().lower()
        if not word_key:
            return {"action": "no_signal", "reason": "empty_word"}

        form = dict(relational_form or {})
        activation = {ax: _clip01(dict(axis_activation or {}).get(ax, 0.0)) for ax in AXES}
        geometry = _lexical_geometry(word_key, form, activation)
        family = _applicability_family(geometry)

        candidate, selection = self._select_candidate(word_key, geometry, family)
        if candidate is not None:
            evidence_id = _stable_hash({"candidate": candidate.candidate_id, "tick": self._tick, "n": len(candidate.evidence)}, 12)
            candidate.evidence.append({
                "evidence_id": evidence_id,
                "provenance": str(provenance or "inherited_scaffold"),
                "slot": geometry.get("slot", "unbound"),
                "selection_kind": selection.get("kind", ""),
                "surface_hash": _surface_hash(str(form.get("raw_text", "") or "")),
                "tick": self._tick,
                "validated": False,
                **dict(extra_evidence or {}),
            })
            self._persist()
            # Consequence-closure follow-up: this evidence entry is now a
            # live participant in THIS turn's causal chain -- remember its
            # (candidate_id, evidence_id) identity so drain_turn_consumption_
            # trace() can hand it to aurora.py's contributor fan-out, the
            # same existing mechanism that already routes a receiver's
            # eventual outcome to every other contributor. Historical replay
            # (observe_historical_lexical_possibility(), always tagged
            # provenance="historical_possibility") is explicitly excluded --
            # it runs on a background thread with no live receiver turn to
            # eventually attribute an outcome from, and its own epistemic
            # hedging (truth_assumed=False) already marks it as never
            # receiver-validated by design.
            if str(provenance or "") != "historical_possibility":
                self._turn_consumption_trace.append({
                    "candidate_id": candidate.candidate_id,
                    "evidence_id": evidence_id,
                    "word": word_key,
                    "applicability_family": family,
                })
            return {
                "action": "matched",
                "candidate_id": candidate.candidate_id,
                "evidence_id": evidence_id,
                "applicability_family": family,
                "selection": selection,
            }

        axis_profile = _identity_axis_profile(word_key, family, activation)
        profile_key = _profile_key(_expand_to_15d(axis_profile))
        self._pending_context[profile_key] = {
            "word": word_key,
            "applicability_family": family,
            "geometry": geometry,
            "provenance": str(provenance or "inherited_scaffold"),
            "parent_ids": list(geometry.get("ancestry") or []),
            "surface_hash": _surface_hash(str(form.get("raw_text", "") or "")),
            # Codex review, PR #184: without this, a NOVEL relation/family
            # loses extra_evidence entirely -- the pair that FOUNDS a trial
            # via _integrate_warp() never got an evidence entry at all, so
            # historical provenance (possibility_id, epistemic hedging) only
            # ever reached later MATCHED pairs, never the founding one.
            "extra_evidence": dict(extra_evidence or {}),
        }
        if len(self._pending_context) > _MAX_PENDING_CONTEXT:
            for stale_key in list(self._pending_context.keys())[: len(self._pending_context) - _MAX_PENDING_CONTEXT]:
                self._pending_context.pop(stale_key, None)

        component = self._submit_gap(word=word_key, axis_profile=axis_profile, applicability_family=family)
        if component is not None:
            return {
                "action": "trial_started",
                "component_id": component.component_id,
                "applicability_family": family,
            }
        existing_trial = next(
            (c for c in self._candidates.values() if c.word == word_key and c.applicability_family == family and c.status == "trial"),
            None,
        )
        if existing_trial is not None:
            return {"action": "trial_continuing", "candidate_id": existing_trial.candidate_id, "applicability_family": family}
        return {"action": "no_signal", "applicability_family": family}

    def _derive_relation_and_form(self, raw_text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Parse-only: recovers (relation_word, relational_form) for
        raw_text without ever triggering extract_relational_form()'s own
        live-feed side effect (feed_lexical_grounding=False). Shared by
        observe_historical_lexical_possibility()'s original-observation
        path and _trigger_developmental_replay()'s non-inflation
        pre-check (Build 772 PR 3), so both read the CURRENT
        representational machinery identically. Returns (relation, None)
        only when extract_relational_form() itself raised -- a valid
        parse with no relation found returns (relation="", form=dict),
        distinguishable from a genuine parse failure."""
        try:
            from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form
            form = extract_relational_form(raw_text, feed_lexical_grounding=False)
        except Exception:
            return "", None
        relation = str(dict(form or {}).get("relation", "") or "").strip().lower()
        return relation, dict(form or {})

    def observe_historical_lexical_possibility(
        self,
        *,
        raw_text: str,
        observed_response_text: str,
        possibility_id: str = "",
        observed_source: str = "historical_other_assistant",
        epistemic_status: str = "observation_not_truth",
        causal_status: str = "sequence_observed_causality_not_asserted",
        defer_persistence: bool = False,
        provenance: str = "historical_possibility",
        extra_evidence: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build 771 PR 7: let one historical (user, other-assistant)
        exchange pair pressure this same lexical-grounding mapping --
        mirrors aurora_communication_emergence.py's own
        observe_structural_possibility() epistemic hedging exactly
        (truth_assumed: False, receiver_validation_assumed: False,
        receiver_validation_eligible=False equivalent), and is a second
        OBSERVER of the same event that method already processes, not a
        parallel pipeline: it reuses observe_lexical_context() as its own
        entrance rather than reimplementing candidate selection/growth.

        The historical assistant's response is never treated as truth, a
        definition, a demonstration, or receiver validation of anything --
        it is admitted only as evidence that the relation word in the
        user's own utterance sits in a structurally intelligible position,
        the same epistemic status live use already assigns to a scaffold-
        bound relation (provenance="historical_possibility" here,
        distinct from both "inherited_scaffold" and "consequence_earned"
        so this evidence's origin stays traceable). Live experience stays
        authoritative for stabilization -- this only ever supplies
        additional evidence entries a real trial's own promotion gate
        (PR 4's evidence+diversity floor) must still clear independently.

        defer_persistence mirrors observe_structural_possibility()'s own
        flag exactly: while set, this call's own writes are held back so a
        caller checkpointing multiple durable substrates together (see
        aurora_historical_experience_environment.py's
        _save_crystal_substrate()) can flush them all at one explicit
        save() boundary, never letting this substrate advance ahead of a
        sibling substrate between checkpoints.

        Build 772 (Historical Lexical Consequence Attribution): provenance
        and extra_evidence are the re-entrance surface Developmental
        Replay (PR 3) uses to reinterpret an already-observed pair under
        improved representational resolution, tagged provenance=
        "developmental_replay" instead of the default. Every genuinely
        NEW original observation keeps the default "historical_possibility"
        -- ONLY original observations feed the discrimination-detection
        pass below (_attribute_historical_discrimination) and the causal-
        attribution index it writes to; a replay re-entrance never
        re-triggers discrimination detection against itself or double-logs
        the same underlying pair as a second independent chronological
        event, matching "a replay is a reinterpretation of existing
        evidence, not a new environmental event."
        """
        raw = str(raw_text or "").strip()
        observed = str(observed_response_text or "").strip()
        if not raw or not observed:
            return {"admitted": False, "reason": "exchange_requires_two_nonempty_surfaces"}

        resolved_possibility_id = str(possibility_id or "LEXPOSS:" + _stable_hash({
            "u": _surface_hash(raw),
            "o": _surface_hash(observed),
        }, 16))
        if resolved_possibility_id in self._seen_historical_possibilities:
            return {"admitted": False, "duplicate": True, "reason": "possibility_already_observed", "possibility_id": resolved_possibility_id}
        self._seen_historical_possibilities[resolved_possibility_id] = time.time()
        if len(self._seen_historical_possibilities) > _MAX_SEEN_HISTORICAL_POSSIBILITIES:
            oldest = sorted(self._seen_historical_possibilities, key=self._seen_historical_possibilities.get)
            for key in oldest[: len(self._seen_historical_possibilities) - _MAX_SEEN_HISTORICAL_POSSIBILITIES]:
                self._seen_historical_possibilities.pop(key, None)

        if defer_persistence:
            self._persistence_suspended += 1
        try:
            relation, form = self._derive_relation_and_form(raw)
            if form is None:
                return {"admitted": False, "reason": "relational_form_unavailable", "possibility_id": resolved_possibility_id}
            if not relation:
                if provenance == "historical_possibility":
                    self._record_historical_unresolved(resolved_possibility_id, raw, observed, observed_source)
                return {"admitted": False, "reason": "no_relational_configuration", "possibility_id": resolved_possibility_id}

            observation = self.observe_lexical_context(
                word=relation,
                relational_form=form,
                provenance=provenance,
                extra_evidence={
                    "possibility_id": resolved_possibility_id,
                    "observed_source": str(observed_source or "historical_other_assistant"),
                    "epistemic_status": str(epistemic_status or "observation_not_truth"),
                    "causal_status": str(causal_status or "sequence_observed_causality_not_asserted"),
                    "observed_surface_hash": _surface_hash(observed),
                    "truth_assumed": False,
                    "receiver_validation_assumed": False,
                    **dict(extra_evidence or {}),
                },
            )
            if provenance == "historical_possibility":
                self._attribute_historical_discrimination(
                    relation=relation, raw=raw, observed=observed, observation=observation,
                    possibility_id=resolved_possibility_id, observed_source=observed_source,
                )
            return {
                "admitted": True,
                "possibility_id": resolved_possibility_id,
                "word": relation,
                **observation,
            }
        finally:
            if defer_persistence:
                self._persistence_suspended = max(0, self._persistence_suspended - 1)

    def _get_contradicts_pairs(self) -> set:
        """Cached wrapper over aurora_contradiction_perception.py's own
        _load_contradicts_pairs() -- that function re-reads
        aurora_oets_web.json from disk on every call, which is fine for a
        live turn but not for a backfill pass over tens of thousands of
        historical pairs. Refreshed at most every 300s; OETS antonym
        relations changing mid-backfill is not a correctness concern this
        cache needs to chase precisely."""
        loaded_at, pairs = self._contradicts_pairs_cache
        if time.time() - loaded_at > 300:
            try:
                from aurora_internal.aurora_contradiction_perception import _load_contradicts_pairs
                pairs = _load_contradicts_pairs(self.state_dir)
            except Exception:
                pairs = set()
            self._contradicts_pairs_cache = (time.time(), pairs)
        return pairs

    def _record_historical_unresolved(self, possibility_id: str, raw: str, observed: str, observed_source: str) -> None:
        """Build 772 PR 2: preserve the 'unknown noun inside an otherwise-
        understandable relation' case instead of silently discarding it on
        the no_relational_configuration early return -- this is the
        population _trigger_developmental_replay() (PR 3) later checks
        once a promotion might newly resolve one of these words' blocking
        terms. Keyed by every salient content word in the pair (not just
        one), since any of them promoting later could be what unblocks
        this specific pair. Bounded/oldest-evicted, mirrors
        _record_historical_implication()'s own pattern."""
        try:
            from aurora_internal.aurora_relation_pairs import WORD_RE, STOPWORDS
            words = {w for w in WORD_RE.findall(raw.lower()) if w not in STOPWORDS}
        except Exception:
            words = set()
        if not words:
            return
        self._historical_implications.pop(possibility_id, None)
        self._historical_unresolved[possibility_id] = {
            "possibility_id": possibility_id,
            "raw_text_trunc": raw[:400],
            "observed_response_trunc": observed[:400],
            "observed_source": str(observed_source or ""),
            "replayed_for_words": [],
        }
        for word in words:
            ids = self._historical_unresolved_by_word.setdefault(word, [])
            ids.append(possibility_id)
            if len(ids) > _MAX_PER_WORD_IMPLICATIONS:
                del ids[: len(ids) - _MAX_PER_WORD_IMPLICATIONS]
        if len(self._historical_unresolved) > _MAX_HISTORICAL_UNRESOLVED:
            oldest = list(self._historical_unresolved.keys())[: len(self._historical_unresolved) - _MAX_HISTORICAL_UNRESOLVED]
            for stale_pid in oldest:
                self._historical_unresolved.pop(stale_pid, None)
        self._historical_diag["unresolved_historical_lexical_gaps"] = len(self._historical_unresolved)
        self._historical_diag["replay_eligible_observations"] += 1

    def _record_historical_implication(
        self, *, possibility_id: str, word: str, applicability_family_at_observation: str,
        candidate_id: str, evidence_id: str, joints: List[Dict[str, Any]],
        raw: str, observed: str, observed_source: str,
    ) -> None:
        """Build 772 PR 2/3: the causal-attribution/replay-index entry for
        ONE historical pair that resolved a relation for `word`. Preserved
        regardless of whether this pair triggered a collision this turn --
        a future pair (or a future promotion, per PR 3) may still need to
        compare against it. Bounded per-word (oldest evicted) and globally
        (oldest evicted), mirroring _pending_context's own pattern."""
        self._historical_unresolved.pop(possibility_id, None)
        self._historical_implications[possibility_id] = {
            "possibility_id": possibility_id,
            "word": word,
            "applicability_family_at_observation": applicability_family_at_observation,
            "candidate_id": candidate_id,
            "evidence_id": evidence_id,
            "joints": list(joints or []),
            "raw_text_trunc": raw[:400],
            "observed_response_trunc": observed[:400],
            "observed_source": str(observed_source or ""),
            "replayed_for_words": [],
        }
        ids = self._historical_implications_by_word.setdefault(word, [])
        ids.append(possibility_id)
        if len(ids) > _MAX_PER_WORD_IMPLICATIONS:
            evicted, ids[:] = ids[: len(ids) - _MAX_PER_WORD_IMPLICATIONS], ids[len(ids) - _MAX_PER_WORD_IMPLICATIONS:]
            for old_pid in evicted:
                self._historical_implications.pop(old_pid, None)
        if len(self._historical_implications) > _MAX_HISTORICAL_IMPLICATIONS:
            oldest = list(self._historical_implications.keys())[: len(self._historical_implications) - _MAX_HISTORICAL_IMPLICATIONS]
            for stale_pid in oldest:
                self._historical_implications.pop(stale_pid, None)
        self._historical_diag["replay_eligible_observations"] += 1

    def _attribute_historical_discrimination(
        self, *, relation: str, raw: str, observed: str,
        observation: Mapping[str, Any], possibility_id: str, observed_source: str,
    ) -> None:
        """Build 772 PR 2: compares THIS pair's relation word against
        recently implicated candidates for the SAME word, using the same
        narrow, fail-quiet collision primitives aurora_contradiction_
        perception.py already uses for live turns (negation-flip,
        closed-set conflict, OETS antonym conflict) -- applied here to a
        window of prior HISTORICAL implications for this word rather than
        a live rolling turn window. The evidence source is always the
        TRANSITION between two observed pairs, never an assumption that
        either participant possessed semantic authority: a collision
        against a prior implicated candidate weakens THAT candidate
        (negative), and only ever strengthens an ALTERNATIVE Aurora
        already structurally represents before this call (never a
        candidate invented from the correction's own wording). Absent a
        collision, at most an indeterminate signal is recorded -- silence,
        repetition, and mere continuation are never promotion-eligible
        (see _DISCRIMINATION_TO_OUTCOME).
        """
        self._historical_diag["historical_pairs_examined"] += 1
        action = str(observation.get("action") or "")
        candidate_id = str(observation.get("candidate_id") or "")
        evidence_id = str(observation.get("evidence_id") or "")
        if action == "trial_started" and not evidence_id:
            # The founding evidence entry's id never reaches this method's
            # caller directly (observe_lexical_context()'s trial_started
            # branch returns only component_id) -- recover it from the
            # freshly-founded candidate's own (necessarily singleton at
            # this instant) evidence list.
            component_id = str(observation.get("component_id") or "")
            founding = self._candidates.get(component_id)
            if founding is not None and founding.evidence:
                candidate_id = founding.candidate_id
                evidence_id = str(founding.evidence[-1].get("evidence_id") or "")
            self._historical_diag["lexical_candidates_formed_historical"] += 1
        family = str(observation.get("applicability_family") or "")
        if not candidate_id or not evidence_id:
            return

        today_joints: List[Dict[str, Any]] = []
        try:
            import aurora_expression_perception as aep
            from aurora_internal.aurora_relation_pairs import extract_joints, is_negated_near
            raw_low = raw.lower()
            today_joints = [
                {"operator_relation": op, "argument_word": arg, "negated": is_negated_near(raw_low, arg.lower())}
                for op, arg, _pattern in extract_joints(raw, aep.infer_word_role)
                if op == relation
            ]
        except Exception:
            today_joints = []

        if today_joints:
            window_pairs: List[Dict[str, Any]] = []
            for prior_pid in list(self._historical_implications_by_word.get(relation, []))[-6:]:
                prior_entry = self._historical_implications.get(prior_pid)
                if not prior_entry:
                    continue
                for joint in prior_entry.get("joints") or []:
                    window_pairs.append({**joint, "possibility_id": prior_pid})

            collision_kind = ""
            if window_pairs:
                try:
                    from aurora_internal.aurora_contradiction_perception import find_collisions
                    collisions = find_collisions(today_joints, window_pairs, self._get_contradicts_pairs())
                except Exception:
                    collisions = []
                # Only the first collision is acted on -- bounded, and
                # avoids one pair spamming outcome-records across every
                # stale implication still sitting in the window.
                if collisions:
                    _new_pair, prior_pair, reason = collisions[0]
                    prior_pid = str(prior_pair.get("possibility_id") or "")
                    prior_entry = self._historical_implications.get(prior_pid)
                    if prior_entry and prior_entry.get("candidate_id") and prior_entry.get("evidence_id"):
                        collision_kind = "explicit_correction" if reason == "negation_flip" else "contradiction"
                        self.record_evidence_outcome(
                            candidate_id=prior_entry["candidate_id"], evidence_id=prior_entry["evidence_id"],
                            outcome_kind=_DISCRIMINATION_TO_OUTCOME[collision_kind],
                            observed_effect=f"historical_{reason}",
                            discrimination_kind=collision_kind, evidence_source="historical",
                        )
                        self._historical_diag["historical_outcomes_attributed"] += 1
                        self._historical_diag["discriminating_historical_consequences"] += 1
                        if collision_kind == "explicit_correction":
                            self._historical_diag["explicit_corrections_detected"] += 1
                        # Q3 gate: the alternative must already be a
                        # candidate Aurora structurally represented BEFORE
                        # this call (action == "matched"), never one this
                        # same call just opened, and never invented from
                        # the correction's own English wording.
                        if action == "matched" and candidate_id != prior_entry["candidate_id"]:
                            self.record_evidence_outcome(
                                candidate_id=candidate_id, evidence_id=evidence_id,
                                outcome_kind="positive",
                                observed_effect=f"historical_{reason}_differentiation",
                                discrimination_kind="differentiation_supported", evidence_source="historical",
                            )
                            self._historical_diag["historical_outcomes_attributed"] += 1

            if not collision_kind:
                repeated = any(
                    wp.get("operator_relation") == j["operator_relation"]
                    and wp.get("argument_word") == j["argument_word"]
                    and bool(wp.get("negated")) == j["negated"]
                    for j in today_joints for wp in window_pairs
                )
                weak_kind = "repeated_contextual_conservation" if repeated else "unresolved_continuation"
                self.record_evidence_outcome(
                    candidate_id=candidate_id, evidence_id=evidence_id,
                    outcome_kind=_DISCRIMINATION_TO_OUTCOME[weak_kind], observed_effect="",
                    discrimination_kind=weak_kind, evidence_source="historical",
                )
                self._historical_diag["historical_outcomes_attributed"] += 1

        self._record_historical_implication(
            possibility_id=possibility_id, word=relation, applicability_family_at_observation=family,
            candidate_id=candidate_id, evidence_id=evidence_id, joints=today_joints,
            raw=raw, observed=observed, observed_source=observed_source,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.persist or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                raw = dict(json.load(handle) or {})
            self._tick = int(raw.get("tick", 0) or 0)
            self._pending_context = dict(raw.get("pending_context") or {})
            self._seen_historical_possibilities = {
                str(key): float(value or 0.0)
                for key, value in dict(raw.get("seen_historical_possibilities") or {}).items()
            }
            for component_id, item in dict(raw.get("candidates") or {}).items():
                rec = dict(item or {})
                candidate = LexicalCandidate(
                    candidate_id=str(rec.get("candidate_id", "") or ""),
                    word=str(rec.get("word", "") or ""),
                    component_id=str(rec.get("component_id", component_id) or component_id),
                    axis_profile={str(k): float(v or 0.0) for k, v in dict(rec.get("axis_profile") or {}).items()},
                    applicability_family=str(rec.get("applicability_family", "") or ""),
                    parent_ids=list(rec.get("parent_ids") or []),
                    structural_geometry=dict(rec.get("structural_geometry") or {}),
                    dominant_constraints=list(rec.get("dominant_constraints") or []),
                    status=str(rec.get("status", "trial") or "trial"),
                    created_at=float(rec.get("created_at", time.time()) or time.time()),
                    evidence=list(rec.get("evidence") or []),
                    genealogy_ability_id=str(rec.get("genealogy_ability_id", "") or ""),
                )
                self._candidates[candidate.component_id] = candidate
            self._warp_trials = {
                str(component_id): self._restore_warp_component(item)
                for component_id, item in dict(raw.get("warp_trials") or {}).items()
            }
            self._warp_promoted = {
                str(component_id): self._restore_warp_component(item)
                for component_id, item in dict(raw.get("warp_promoted") or {}).items()
            }
            self._gap_counter = {
                str(key): int(value or 0)
                for key, value in dict(raw.get("warp_gap_counter") or {}).items()
            }
            self._warp_dissolved_count = int(raw.get("warp_dissolved_count", 0) or 0)
            # Build 772: missing-key-safe -- a state file saved before this
            # build existed simply has none of these keys, and every dict.get
            # below falls back to empty, exactly like a fresh install.
            self._historical_implications = dict(raw.get("historical_implications") or {})
            self._historical_implications_by_word = {
                str(word): list(ids or [])
                for word, ids in dict(raw.get("historical_implications_by_word") or {}).items()
            }
            self._historical_unresolved = dict(raw.get("historical_unresolved") or {})
            self._historical_unresolved_by_word = {
                str(word): list(ids or [])
                for word, ids in dict(raw.get("historical_unresolved_by_word") or {}).items()
            }
            self._historical_diag.update({
                str(key): int(value or 0)
                for key, value in dict(raw.get("historical_diag") or {}).items()
                if key in self._historical_diag
            })
        except Exception:
            self._candidates = {}
            self._pending_context = {}

    @staticmethod
    def _restore_warp_component(item: Mapping[str, Any]) -> WarpComponent:
        rec = dict(item or {})
        return WarpComponent(
            component_id=str(rec.get("component_id", "") or ""),
            level=str(rec.get("level", "lexical_role_grounding") or "lexical_role_grounding"),
            axis_profile={str(k): float(v or 0.0) for k, v in dict(rec.get("axis_profile") or {}).items()},
            parent_ids=list(rec.get("parent_ids") or []),
            name=str(rec.get("name", "") or "") or None,
            parameters=dict(rec.get("parameters") or {}),
            trial_tick=int(rec.get("trial_tick", 0) or 0),
            trial_score_ema=float(rec.get("trial_score_ema", 0.0) or 0.0),
            promoted=bool(rec.get("promoted", False)),
            dissolved=bool(rec.get("dissolved", False)),
            created_at=float(rec.get("created_at", time.time()) or time.time()),
            sixth_axis_signal=float(rec.get("sixth_axis_signal", 0.0) or 0.0),
            topology_gap_ref=rec.get("topology_gap_ref"),
        )

    def save(self) -> bool:
        return self._persist(force=True)

    def _persist(self, *, force: bool = False) -> bool:
        if not self.persist or (self._persistence_suspended > 0 and not force):
            return False
        payload = {
            "schema_version": 1,
            "tick": self._tick,
            "pending_context": self._pending_context,
            "seen_historical_possibilities": dict(self._seen_historical_possibilities),
            "candidates": {cid: cand.to_dict() for cid, cand in self._candidates.items()},
            "warp_trials": {cid: asdict(comp) for cid, comp in self._warp_trials.items()},
            "warp_promoted": {cid: asdict(comp) for cid, comp in self._warp_promoted.items()},
            "warp_gap_counter": dict(self._gap_counter),
            "warp_dissolved_count": int(getattr(self, "_warp_dissolved_count", 0) or 0),
            "warp_status": self.warp_status(),
            "historical_implications": self._historical_implications,
            "historical_implications_by_word": self._historical_implications_by_word,
            "historical_unresolved": self._historical_unresolved,
            "historical_unresolved_by_word": self._historical_unresolved_by_word,
            "historical_diag": dict(self._historical_diag),
            "saved_at": time.time(),
        }
        try:
            Path(self.state_dir).mkdir(parents=True, exist_ok=True)
            return bool(atomic_write_json(Path(self.storage_path), payload, indent=2, default=str))
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        return {
            "candidate_count": len(self._candidates),
            "trial_count": len(self._warp_trials),
            "promoted_count": len(self._warp_promoted),
            "warp_status": self.warp_status(),
            # Build 772: observability only -- nothing in this module or its
            # callers reads "historical" back into any scoring/gating path.
            "historical": dict(self._historical_diag),
        }

    # ------------------------------------------------------------------
    # Build 771 PR 5: consumption query surface
    # ------------------------------------------------------------------

    def resolve_promoted_role(
        self,
        word: str,
        relational_form: Mapping[str, Any],
        axis_activation: Optional[Mapping[str, float]] = None,
    ) -> Optional[LexicalCandidate]:
        """Read-only query: is there a PROMOTED candidate for this exact
        (word, structural geometry)? This is the one authority-migration
        query surface PR 5's consumption call sites are allowed to read
        from -- returns None for anything short of a promoted,
        consequence-earned candidate, never a trial, never merely high
        evidence_count (a trial candidate has cleared no gate at all; only
        "promoted" has cleared _score_trial()'s evidence+diversity floor
        and PROMOTION_SCORE). Exact applicability_family match only -- no
        similarity fallback here, since consumption is where an incorrect
        guess would actually reach the user, not just get compared
        internally.
        """
        word_key = str(word or "").strip().lower()
        if not word_key:
            return None
        form = dict(relational_form or {})
        activation = {ax: _clip01(dict(axis_activation or {}).get(ax, 0.0)) for ax in AXES}
        geometry = _lexical_geometry(word_key, form, activation)
        family = _applicability_family(geometry)
        for candidate in self._candidates.values():
            if candidate.word == word_key and candidate.applicability_family == family and candidate.status == "promoted":
                return candidate
        return None

    def has_promoted_relation_role(self, word: str) -> bool:
        """Coarser sibling of resolve_promoted_role(): has Aurora, in ANY
        past structural context, promoted a candidate for this word whose
        geometry shows it occupying the "relation" slot? Unlike
        resolve_promoted_role(), this does not require reconstructing
        today's exact applicability_family (which extract_relational_
        form()'s own _looks_verb() cannot do -- it decides relation-verb-
        hood word-by-word, before any RelationalForm exists to derive a
        geometry from). This is a deliberately structural question ("does
        this word ever occupy this slot"), never a semantic one ("what
        does this word mean") -- consistent with _RELATION_VERBS itself
        being a binary structural test, not a category assignment.
        """
        word_key = str(word or "").strip().lower()
        if not word_key:
            return False
        return any(
            candidate.word == word_key
            and candidate.status == "promoted"
            and dict(candidate.structural_geometry or {}).get("slot") == "relation"
            for candidate in self._candidates.values()
        )

    def promoted_candidates_for_word(self, word: str) -> List[LexicalCandidate]:
        """Build 771 PR 6: every PROMOTED candidate for this word, across
        every applicability_family it has earned one under. This is the
        polysemy surface -- a word can legitimately hold several
        consequence-earned candidates at once (the "since" case: temporal-
        shaped vs causal-shaped geometry, each promoted independently).
        Read-only; deciding whether that plurality is genuine ambiguity
        worth asking about is comprehension-gap policy, not this module's
        concern -- see aurora_comprehension_gap.py's own consumer.
        """
        word_key = str(word or "").strip().lower()
        if not word_key:
            return []
        return [c for c in self._candidates.values() if c.word == word_key and c.status == "promoted"]

    def promoted_candidates_near(
        self,
        word: str,
        relational_form: Mapping[str, Any],
        axis_activation: Optional[Mapping[str, float]] = None,
    ) -> List[LexicalCandidate]:
        """Build 771 PR 6 fix (Codex review, PR #183): the geometry-scoped
        sibling of promoted_candidates_for_word() that ambiguity comparison
        actually needs. promoted_candidates_for_word() returns every
        candidate a word has EVER earned across its whole history --
        comparing those directly treats two candidates from totally
        unrelated past contexts (declarative "is" vs. interrogative "is",
        a word promoted once in a discarded structural shape) as if they
        were both live options for THIS turn, which is not what "multiple
        materially-different, similarly-supported candidates remain" is
        supposed to mean.

        Returns only candidates whose OWN geometry is either an exact
        applicability_family match to today's turn, or scores >= 0.72
        similarity against it (the identical threshold
        _select_candidate() itself uses to decide two geometries are close
        enough to be the same live option) -- so only candidates that
        could plausibly BOTH apply to this exact utterance are ever
        compared as competing.
        """
        word_key = str(word or "").strip().lower()
        if not word_key:
            return []
        form = dict(relational_form or {})
        activation = {ax: _clip01(dict(axis_activation or {}).get(ax, 0.0)) for ax in AXES}
        geometry = _lexical_geometry(word_key, form, activation)
        family = _applicability_family(geometry)
        near: List[LexicalCandidate] = []
        for candidate in self._candidates.values():
            if candidate.word != word_key or candidate.status != "promoted":
                continue
            if candidate.applicability_family == family:
                near.append(candidate)
                continue
            if _geometry_similarity(geometry, candidate.structural_geometry) >= 0.72:
                near.append(candidate)
        return near


# ─── Global singleton, mirroring aurora_warp_protocol.get_warp_field()/
# install_warp_field() exactly ──────────────────────────────────────────
# aurora_utterance_parser.py and aurora_constraint_semantic_continuity.py
# are pure text-in/dict-out functions with no `systems` or instance handle
# threaded through their public signatures (PR 2's should_ask() precedent:
# "same public signature, so callers need no change"). A lazily-created
# global singleton is the only way PR 5's consumption call sites can reach
# a live AuroraLexicalGrounding without widening either module's public
# API or its callers, which span too much of the codebase to safely touch
# here.

_global_lexical_grounding: Optional["AuroraLexicalGrounding"] = None


def get_lexical_grounding() -> "AuroraLexicalGrounding":
    """Return the global AuroraLexicalGrounding, creating it lazily
    (persist=False) if boot never installed a real, systems-attached
    instance. Mirrors get_warp_field() exactly."""
    global _global_lexical_grounding
    if _global_lexical_grounding is None:
        _global_lexical_grounding = AuroraLexicalGrounding(persist=False)
    return _global_lexical_grounding


def install_lexical_grounding(instance: "AuroraLexicalGrounding") -> None:
    """Install the system's AuroraLexicalGrounding as the global singleton.
    Call once at boot after creating it with attach_systems() wired.
    Mirrors install_warp_field() exactly."""
    global _global_lexical_grounding
    _global_lexical_grounding = instance
