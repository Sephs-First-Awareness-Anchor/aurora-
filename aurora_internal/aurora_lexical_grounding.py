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
        self._candidates[component.component_id] = candidate
        if len(self._candidates) > _MAX_CANDIDATES:
            oldest = sorted(self._candidates.values(), key=lambda c: c.created_at)[: len(self._candidates) - _MAX_CANDIDATES]
            for stale in oldest:
                self._candidates.pop(stale.component_id, None)
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        """Build 771 PR 4: evidence-derived score, gated on BOTH sample
        volume AND surface diversity AMONG VALIDATED EVIDENCE ONLY --
        mirrors aurora_communication_emergence.py's own _score_trial()
        exactly (`validated = [e for e in evidence if e.get("validated")]`,
        filtered before any volume/diversity check runs).

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
        record_evidence_outcome() -- called by a live caller that actually
        observed whether a provisional interpretation was confirmed or
        corrected, not by mere recurrence) count toward the volume+
        diversity floor. No live call site reports outcomes yet (that
        wiring is beyond this PR's scope), so today this means -- by
        deliberate construction, not by accident -- nothing can be
        promoted from evidence alone. That is the honest state until a
        real validation-reporting caller exists; it is not a regression
        from a working mechanism, it is the removal of a mechanism that
        was never actually earning what it claimed to.

        If this candidate already has a registered genealogy ability with
        its own measured consequence_profile (only possible after a prior
        promotion cycle), that confidence-weighted reading takes
        precedence once it exists.
        """
        candidate = self._candidates.get(component.component_id)
        if candidate is None:
            return 0.0
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if candidate.genealogy_ability_id and genealogy is not None:
            ability = dict(getattr(genealogy, "abilities", {}) or {}).get(candidate.genealogy_ability_id)
            consequence = getattr(ability, "consequence_profile", None) if ability is not None else None
            if consequence:
                return _clip01(dict(consequence).get("confidence", 0.0))
        validated = [e for e in candidate.evidence if e.get("validated") is True]
        evidence_count = len(validated)
        distinct_surfaces = len({str(e.get("surface_hash", "") or "") for e in validated if e.get("surface_hash")})
        if evidence_count < _MIN_EVIDENCE or distinct_surfaces < _MIN_DISTINCT_SURFACES:
            return _INERT_TRIAL_FLOOR
        return _clip01(0.55 + 0.06 * distinct_surfaces)

    def record_evidence_outcome(
        self,
        *,
        candidate_id: str,
        evidence_id: str,
        outcome_kind: str = "indeterminate",
        observed_effect: str = "",
    ) -> Dict[str, Any]:
        """The validation-reporting entrance _score_trial() actually gates
        on -- mirrors aurora_communication_emergence.py's own
        record_receiver_outcome() exactly: marks ONE specific evidence
        entry (identified by the evidence_id stamped on it when it was
        recorded) validated=True, with an outcome_kind describing what
        was actually observed. No live caller invokes this yet (that is
        future work, beyond this PR's scope) -- this only builds the
        mechanism honestly, it does not fabricate a caller for it.
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
                self._persist()
                return {"recorded": True, "candidate_id": candidate_id, "evidence_id": evidence_id}
        return {"recorded": False, "reason": "unknown_evidence_id"}

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
    ) -> Dict[str, Any]:
        """Entrance: observe one word sitting in one turn's structural
        context. Purely observational plumbing -- does not decide what the
        word MEANS, does not touch or alter any scaffold lookup, and (per
        PR 3's scope) is not yet called from any live comprehension path;
        PR 5 wires a real call site and the authority migration that goes
        with it.

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
            })
            self._persist()
            return {
                "action": "matched",
                "candidate_id": candidate.candidate_id,
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
        if not self.persist:
            return False
        payload = {
            "schema_version": 1,
            "tick": self._tick,
            "pending_context": self._pending_context,
            "candidates": {cid: cand.to_dict() for cid, cand in self._candidates.items()},
            "warp_trials": {cid: asdict(comp) for cid, comp in self._warp_trials.items()},
            "warp_promoted": {cid: asdict(comp) for cid, comp in self._warp_promoted.items()},
            "warp_gap_counter": dict(self._gap_counter),
            "warp_dissolved_count": int(getattr(self, "_warp_dissolved_count", 0) or 0),
            "warp_status": self.warp_status(),
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
