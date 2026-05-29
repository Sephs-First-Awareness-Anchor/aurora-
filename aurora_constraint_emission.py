# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_constraint_emission.py

EXPRESSION step of Aurora's canonical re-entry loop.

Emits utterances directly from the five-axis constraint state.
No translation layers, no fallback to slot labels, no meta-narration.

State → EXPRESSION (this) → RE-ENTRY → RECONCILIATION → UNDERSTANDING
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

# ── canonical structure ───────────────────────────────────────────────────────
CANONICAL_AXES = ("X", "T", "N", "B", "A")
CANONICAL_I_STATE_PAIRS = (
    ("I_IS",  "I_ISNT"),
    ("I_CAN", "I_CANNOT"),
    ("I_DO",  "I_DONOT"),
    ("I_SAW", "I_SOUGHT"),
    ("I_DID", "I_DIDNT"),
)

_AXIS_NAME_TO_CANONICAL: Dict[str, str] = {
    "X": "X", "T": "T", "N": "N", "B": "B", "A": "A",
    "x": "X", "t": "T", "n": "N", "b": "B", "a": "A",
    "existence": "X",
    "existential": "X",
    "temporal": "T",
    "time": "T",
    "energy": "N",
    "energetic": "N",
    "boundary": "B",
    "meaning": "B",
    "agency": "A",
    "agentive": "A",
    "understanding": "A",
}

# ── tuning constants (§3.6) ───────────────────────────────────────────────────
RESONANCE_FLOOR     = 0.15   # below this, content slot is unfillable
POLARITY_DEAD_BAND  = 0.05   # below |polarity|, axis sign is zero
POLARITY_WEAK       = 0.20   # above |polarity|, axis is committed
TRAJECTORY_MOVING   = 0.20   # above |trajectory|, tense commits
HEAT_MILD_FOCUS     = 0.30   # above heat, N adds intensifier
HEAT_STRONG_FOCUS   = 0.60   # above heat, N fronts and intensifies
MAGNITUDE_PRESENT   = 0.10   # below magnitude, axis isn't really firing
MAGNITUDE_HEDGE     = 0.30   # below magnitude on A+, hedge the assertion
MIN_RELATIONS       = 2      # OETS depth check minimum typed relations
MIN_USAGE_EXAMPLES  = 1      # OETS depth check minimum recorded examples

_IDENTITY_TOPICS: Set[str] = {"self", "name", "identity", "you", "aurora"}
_MODAL_TOKENS:    Tuple[str, ...] = ("can", "can't", "don't", "won't", "think", "could", "would")
_SELF_DEVELOPMENT_TERMS = re.compile(
    r"\b(language growth|develop(?:ing)? (?:your )?(?:own )?comprehension|"
    r"comprehension|evolv(?:e|ing)|full potential)\b",
    re.IGNORECASE,
)


# ── speech act ────────────────────────────────────────────────────────────────
class SpeechAct(Enum):
    ASSERTION      = auto()
    ABSTAIN        = auto()
    ACKNOWLEDGMENT = auto()
    DISAGREEMENT   = auto()
    AGREEMENT      = auto()
    REFUSAL        = auto()
    QUESTION       = auto()
    BACKCHANNEL    = auto()
    INVALIDATION   = auto()


# ── data structures ───────────────────────────────────────────────────────────
@dataclass
class AxisVector:
    """Per-axis snapshot for telemetry and context passing."""
    axis:       str
    polarity:   float = 0.0
    magnitude:  float = 0.0
    trajectory: float = 0.0
    heat:       float = 0.0


@dataclass
class InputFrame:
    """Parsed description of the current user turn (None = Aurora-initiated)."""
    text:                 str           = ""
    is_question:          bool          = False
    is_directed:          bool          = True
    is_imperative:        bool          = False
    is_contradiction:     bool          = False
    is_statement:         bool          = False
    is_self_referential:  bool          = False
    is_nonsense:          bool          = False
    established_sequence: bool          = False
    topic_concept:        Optional[str] = None
    aligns_with_oets:     bool          = False
    partial_alignment:    bool          = False


@dataclass
class SlotFrame:
    """The structural skeleton built by axis emitters."""
    agent:               str = ""
    tense_aux:           str = ""
    negation:            str = ""
    determiner:          str = ""
    entity:              str = ""
    predicate:           str = ""
    intensifier:         str = ""
    fronted:             str = ""
    leading:             str = ""
    sequence_connective: str = ""


@dataclass
class EmissionContext:
    """All state needed to produce one utterance."""
    axis_polarities:      Dict[str, float]
    axis_velocities:      Dict[str, float]
    n_heat:               float
    i_state_polarities:   Dict[str, float]
    oets:                 Any                    # OntologicalWeb
    identity:             Any                    # CoreRelationalIdentity
    input_frame:          Optional[InputFrame]   = None
    recent_words:         List[str]              = field(default_factory=list)
    meaning_anchors:      Any                    = None   # read-only spine
    working_memory:       Any                    = None
    sedi_memory:          Any                    = None
    constraint_genealogy: Any                    = None
    gap_system:           Any                    = None
    staged_subsurface_frame: Optional[Dict[str, Any]] = None
    staged_subsurface_frames: List[Dict[str, Any]] = field(default_factory=list)
    turn_id:              Optional[str]          = None


@dataclass
class EmissionResult:
    """What the emitter returns: text + metadata + seeking info."""
    text:             str
    speech_act:       SpeechAct
    slot_frame:       SlotFrame                            = field(default_factory=SlotFrame)
    seeking:          bool                                 = False
    seeking_flag_id:  Optional[str]                       = None
    axis_signature:   Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    abstained:        bool                                 = False
    slots:            Dict[str, Any]                       = field(default_factory=dict)
    timestamp:        float                                = field(default_factory=time.time)


# ── main emitter ──────────────────────────────────────────────────────────────
class ConstraintEmitter:
    """
    Emits text directly from the five-axis constraint state.
    One emission path. No anchor fallback. No meta-narration. No echo.
    """

    def emit(self, ctx: EmissionContext) -> EmissionResult:
        # 0. Integration check — close any open seeking flags before new output (§7)
        self.check_and_run_integration(ctx)
        input_text = str(ctx.input_frame.text or "") if ctx.input_frame else ""
        if _SELF_DEVELOPMENT_TERMS.search(input_text):
            return EmissionResult(
                text="",
                speech_act=SpeechAct.ABSTAIN,
                axis_signature=self._axis_signature(ctx),
                abstained=True,
            )

        # 1. Identity fast-path — must come first (§8)
        if ctx.input_frame and ctx.input_frame.is_self_referential:
            result = self._identity_fast_path(ctx)
            if result is not None:
                return result

        # 2. Speech-act classification (§4)
        act = self._classify_speech_act(ctx)

        # 3. Pure constraint abstain — honest inability, not missing content
        if act == SpeechAct.ABSTAIN:
            fr = ctx.input_frame
            if fr and fr.is_question and fr.is_directed:
                # Constraint inability (I_CANT/I_DONOT firing) → voiced abstain
                ip = ctx.i_state_polarities
                if ip.get("I_CANNOT", 0.0) > 0.5 or ip.get("I_DONOT", 0.0) > 0.5:
                    return self._emit_abstain(ctx)
                # No content for this question — silent, let comprehension respond
                return self._emit_silent(ctx)
            return self._emit_abstain(ctx)

        # 3.5 INVALIDATION fast-path (100% scripted-free)
        if act == SpeechAct.INVALIDATION:
            slots = SlotFrame()
            self._fill_invalidation_slots(ctx, slots)
            text = self._assemble(slots, act, ctx)
            return EmissionResult(
                text=text,
                speech_act=act,
                slot_frame=slots,
                axis_signature=self._axis_signature(ctx),
            )

        # 4. Per-axis structural slots (§3)
        slots = SlotFrame()
        self._axis_A_emit(ctx, slots)
        self._axis_T_emit(ctx, slots)
        self._axis_B_emit(ctx, slots)
        self._axis_X_emit(ctx, slots)
        self._axis_N_modulate(ctx, slots)

        # 5. Leading token from speech act (§4)
        self._set_leading_token(ctx, act, slots)

        # 6. OETS content slot resolution with depth check (§5, §2.3)
        entity_ok    = self._resolve_content_slot(ctx, "entity",    slots, {"noun", "proper_noun"})
        predicate_ok = self._resolve_content_slot(ctx, "predicate", slots, {"verb"})

        # 7. Seeking pathway for missing required predicate (§6)
        # DISAGREEMENT has a short-circuit form ("That's not quite right") that
        # fires in _assemble when no predicate is present — only seek if it has
        # an entity but needs a predicate to complete the claim.
        needs_pred = (
            act in (SpeechAct.ASSERTION, SpeechAct.QUESTION)
            and bool(slots.agent)
        ) or (
            act == SpeechAct.DISAGREEMENT
            and bool(slots.agent)
            and entity_ok        # have the "what", missing the "does"
        )
        if needs_pred and not predicate_ok:
            slot_kind = "both" if not entity_ok else "predicate"
            return self._seek_gap(ctx, slot_kind, slots, act)

        # 7b. Acknowledgment with no content on a question — silent, let comprehension respond
        if (act == SpeechAct.ACKNOWLEDGMENT
                and not entity_ok and not predicate_ok
                and ctx.input_frame and ctx.input_frame.is_question):
            return self._emit_silent(ctx)

        # 8. Surface assembly (§9)
        text = self._assemble(slots, act, ctx)
        if not text.strip():
            # Empty assembly — silent, let comprehension generate the response
            return self._emit_silent(ctx)

        return EmissionResult(
            text=text,
            speech_act=act,
            slot_frame=slots,
            seeking=False,
            seeking_flag_id=None,
            axis_signature=self._axis_signature(ctx),
            abstained=False,
            slots={
                "A":    slots.agent,
                "T":    slots.tense_aux,
                "B":    slots.negation,
                "X":    f"{slots.determiner} {slots.entity}".strip(),
                "N":    slots.intensifier or slots.fronted,
                "pred": slots.predicate,
            },
        )

    # ── identity fast-path (§8) ───────────────────────────────────────────────
    def _identity_fast_path(self, ctx: EmissionContext) -> Optional[EmissionResult]:
        fr = ctx.input_frame
        if not (fr and fr.is_question and fr.is_self_referential):
            return None

        topic  = (fr.topic_concept or "").lower()
        query  = (fr.text or "").lower()
        is_id_topic = (
            topic in _IDENTITY_TOPICS
            or any(t in query for t in ("name", "who are you", "what are you", "aurora"))
        )
        if not is_id_topic:
            return None

        identity = ctx.identity
        if identity is None:
            return None

        name: Optional[str] = getattr(identity, "self_name", None)
        if not name:
            entities = getattr(identity, "entities", {}) or {}
            self_ent = entities.get("aurora")
            name = getattr(self_ent, "name", None) if self_ent else None
        if not name:
            return None

        if any(t in query for t in ("name", "who are you", "what are you")):
            text = f"I'm {name}."
        elif "are you" in query:
            text = f"Yes, I'm {name}."
        else:
            text = f"I am {name}."

        return EmissionResult(
            text=text,
            speech_act=SpeechAct.ASSERTION,
            slot_frame=SlotFrame(agent="I", tense_aux="am", entity=name),
            axis_signature=self._axis_signature(ctx),
        )

    # ── speech-act classification (§4) ───────────────────────────────────────
    def _classify_speech_act(self, ctx: EmissionContext) -> SpeechAct:
        fr   = ctx.input_frame
        ip   = ctx.i_state_polarities
        mag_A = abs(ctx.axis_polarities.get("A", 0.0))

        i_is   = ip.get("I_IS",     0.0)
        i_isnt = ip.get("I_ISNT",   0.0)
        i_can  = ip.get("I_CAN",    0.0)
        i_cant = ip.get("I_CANNOT", 0.0)
        i_do   = ip.get("I_DO",     0.0)
        i_dont = ip.get("I_DONOT",  0.0)

        if fr is None:
            return SpeechAct.ASSERTION if (i_can > 0.3 or i_is > 0.3) else SpeechAct.QUESTION

        if fr.is_nonsense:
            return SpeechAct.INVALIDATION

        if fr.is_imperative and fr.is_directed:
            if i_cant > 0.4 or i_dont > 0.4:
                return SpeechAct.REFUSAL
            if i_can > 0.4 or i_do > 0.4:
                return SpeechAct.ASSERTION
            return SpeechAct.ACKNOWLEDGMENT

        if fr.is_question and fr.is_directed:
            if i_is > 0.3 or i_can > 0.3:
                return SpeechAct.ASSERTION
            if i_isnt > 0.5 or i_cant > 0.5:
                # Try assertion; seeking fires if content missing (§4 note)
                return SpeechAct.ASSERTION
            return SpeechAct.ASSERTION

        if fr.is_statement:
            if fr.is_contradiction and i_isnt > 0.3:
                return SpeechAct.DISAGREEMENT
            if fr.aligns_with_oets and i_is > 0.3:
                return SpeechAct.AGREEMENT
            if fr.partial_alignment and mag_A >= MAGNITUDE_HEDGE:
                return SpeechAct.ASSERTION   # scope-restricted via B-axis
            if fr.partial_alignment:
                return SpeechAct.ACKNOWLEDGMENT
            if i_is > 0.3:
                return SpeechAct.AGREEMENT

        return SpeechAct.ACKNOWLEDGMENT

    # ── leading token (§4) ───────────────────────────────────────────────────
    def _set_leading_token(
        self, ctx: EmissionContext, act: SpeechAct, slots: SlotFrame
    ) -> None:
        heat = ctx.n_heat
        if act == SpeechAct.DISAGREEMENT:
            slots.leading = "no"
        # ASSERTION, QUESTION, REFUSAL, BACKCHANNEL, AGREEMENT, ACKNOWLEDGMENT — no leading token

    # ── per-axis emitters (§3.1–§3.5) ────────────────────────────────────────
    def _axis_A_emit(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Agency: person + modal (§3.5). I-State signals override raw axis."""
        p   = ctx.axis_polarities.get("A", 0.0)
        mag = abs(p)
        ip  = ctx.i_state_polarities
        fr  = ctx.input_frame

        i_cant = ip.get("I_CANNOT", 0.0)
        i_dont = ip.get("I_DONOT",  0.0)
        i_can  = ip.get("I_CAN",    0.0)
        i_do   = ip.get("I_DO",     0.0)

        if i_cant > 0.5:
            slots.agent = "I can't"
        elif i_dont > 0.5:
            slots.agent = "I don't"
        elif i_can > 0.5 and mag >= MAGNITUDE_HEDGE:
            slots.agent = "I can"
        elif i_do > 0.5 and mag >= MAGNITUDE_HEDGE:
            slots.agent = "I"
        elif p > POLARITY_WEAK and mag >= MAGNITUDE_HEDGE:
            slots.agent = "I"
        elif p > POLARITY_WEAK:
            slots.agent = "I think"
        elif p < -POLARITY_WEAK:
            if fr and fr.is_directed:
                slots.agent = "you"
            else:
                slots.agent = "it"
        # near-zero / weak → no agent (fragment surface acceptable)

    def _axis_T_emit(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Temporal: tense + aux + optional sequence connective (§3.2)."""
        traj  = ctx.axis_velocities.get("T", 0.0)
        mag_T = abs(ctx.axis_polarities.get("T", 0.0))

        if traj > TRAJECTORY_MOVING:
            slots.tense_aux = "will"
        elif traj < -TRAJECTORY_MOVING:
            slots.tense_aux = "was"
        else:
            slots.tense_aux = "am"

        fr = ctx.input_frame
        if fr and fr.established_sequence and mag_T >= 0.40:
            connective = {"will": "then", "was": "still", "am": "now"}.get(
                slots.tense_aux, ""
            )
            if connective:
                slots.sequence_connective = connective

    def _axis_B_emit(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Boundary: negation or scope qualifier (§3.4)."""
        p    = ctx.axis_polarities.get("B", 0.0)
        mag  = abs(p)
        heat = ctx.n_heat
        fr   = ctx.input_frame

        if p > POLARITY_WEAK:
            if mag > 0.7 and heat >= HEAT_MILD_FOCUS:
                slots.negation = "always"
        elif p < -POLARITY_WEAK:
            if fr and fr.is_contradiction:
                if not any(tok in slots.agent for tok in ("can't", "don't", "won't", "not")):
                    slots.negation = "not"
            elif mag >= MAGNITUDE_HEDGE:
                slots.negation = "only"
            else:
                if not any(tok in slots.agent for tok in ("can't", "don't", "won't")):
                    slots.negation = "not"

    def _axis_X_emit(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Existence: determiner slot; content word filled later by OETS (§3.1)."""
        p   = ctx.axis_polarities.get("X", 0.0)
        mag = abs(p)
        fr  = ctx.input_frame

        if mag < MAGNITUDE_PRESENT:
            if fr and fr.text:
                slots.determiner = "that"   # deictic
            # else suppress X entirely
        elif p > POLARITY_DEAD_BAND:
            slots.determiner = "the" if (fr and fr.text) else "a"
        else:   # p < -POLARITY_DEAD_BAND
            if not slots.negation:
                slots.negation = "no"
            else:
                slots.determiner = "any"    # compresses to "no X" in assembly

    def _axis_N_modulate(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Energy: focus / emphasis / word-order — never selects vocabulary (§3.3)."""
        heat = ctx.n_heat
        if heat >= HEAT_STRONG_FOCUS:
            slots.fronted     = "X"
            slots.intensifier = "really"
        elif heat >= HEAT_MILD_FOCUS:
            slots.intensifier = "actually"

    # ── OETS content slot resolution (§5, §2.3) ──────────────────────────────
    def _resolve_content_slot(
        self,
        ctx:       EmissionContext,
        slot_name: str,
        slots:     SlotFrame,
        roles:     Set[str],
    ) -> bool:
        """
        Fill slots.entity or slots.predicate from OETS resonance.
        Applies depth check (§2.3). Returns True if slot was filled.
        No anchor fallback — slot is either a real OETS word or unfilled.
        """
        oets = ctx.oets
        if oets is None:
            return self._resolve_content_slot_from_staged(ctx, slot_name, slots, roles)

        recent: Set[str]   = set(ctx.recent_words)
        axis_vec           = ctx.axis_polarities
        prefer_strong      = bool(slots.intensifier)

        best_word:      Optional[str] = None
        best_resonance: float         = 0.0

        for word, node in oets.nodes.items():
            if node.role not in roles:
                continue

            activation = node.comprehension_confidence
            if word in recent:
                activation = min(1.0, activation + 0.4)
            if activation <= 0.0:
                continue

            alignment   = self._axis_alignment(node, axis_vec)
            depth_bonus = 1.0 + node.ontological_depth
            resonance   = activation * alignment * depth_bonus

            if prefer_strong:
                resonance *= (1.0 + abs(node.emotional_valence) * 0.3)

            if resonance > best_resonance:
                best_resonance = resonance
                best_word      = word

        if best_word is None:
            # CBU Directive Alignment: Resolve content from the 125-law manifold
            from aurora_internal.aurora_constraint_manifold_patched import MANIFOLD_FIRST_LAYER_PHASE_A, MANIFOLD_FIRST_LAYER_PHASE_B
            dom_ax = ctx.dominant_axis() if hasattr(ctx, "dominant_axis") else max(ctx.axis_polarities, key=lambda k: abs(ctx.axis_polarities[k]))
            notation = f"{dom_ax}.O[{dom_ax}]"
            cell = MANIFOLD_FIRST_LAYER_PHASE_A.get(notation) or MANIFOLD_FIRST_LAYER_PHASE_B.get(notation)
            if cell:
                text = cell.get('slot_description', '') or cell.get('effect_law', '')
                if text:
                    best_word = " ".join(text.split()[:4]).lower().strip(".,;")
                    if slot_name == "entity":
                        slots.entity = best_word
                    else:
                        slots.predicate = best_word
                    return True
            return self._resolve_content_slot_from_staged(ctx, slot_name, slots, roles)

        # §2.3 depth check — hollow node routes to seeking just like no hit
        candidate = (
            oets.get_node(best_word) if hasattr(oets, "get_node")
            else oets.nodes.get(best_word)
        )
        if candidate and self._is_depth_hollow(candidate):
            return self._resolve_content_slot_from_staged(ctx, slot_name, slots, roles)

        if slot_name == "entity":
            slots.entity = best_word
            node = candidate
            if node:
                if node.role in ("proper_noun", "name"):
                    slots.determiner = ""
                elif slots.determiner == "the" and node.comprehension_confidence < 0.5:
                    slots.determiner = "a"
        else:
            slots.predicate = best_word

        return True

    def _resolve_content_slot_from_staged(
        self,
        ctx:       EmissionContext,
        slot_name: str,
        slots:     SlotFrame,
        roles:     Set[str],
    ) -> bool:
        """
        Use a pre-staged Subsurface projection before declaring a content gap.

        This path only consumes explicit slot_projections from PredictiveStager;
        it does not scrape free text or fall back to the topic label blindly.
        """
        current_topic = self._normalise_staged_token(
            ctx.input_frame.topic_concept if ctx.input_frame else ""
        )
        best: Optional[Dict[str, Any]] = None
        best_score = 0.0

        staged_frames: List[Dict[str, Any]] = []
        if isinstance(ctx.staged_subsurface_frame, dict):
            staged_frames.append(ctx.staged_subsurface_frame)
        staged_frames.extend([f for f in ctx.staged_subsurface_frames if isinstance(f, dict)])

        seen_frame_ids: Set[int] = set()
        for frame in staged_frames:
            ident = id(frame)
            if ident in seen_frame_ids:
                continue
            seen_frame_ids.add(ident)

            frame_ts = float(frame.get("ts") or frame.get("generated_at") or 0.0)
            if frame_ts and (time.time() - frame_ts) > 900.0:
                continue

            for cand in list(frame.get("slot_projections") or []):
                if not isinstance(cand, dict):
                    continue
                cand_slot = str(cand.get("slot_kind") or "")
                if cand_slot and cand_slot not in {slot_name, "both"}:
                    continue
                cand_roles = set(str(r) for r in (cand.get("roles") or []))
                if cand_roles and not cand_roles.intersection(roles):
                    continue

                token = self._normalise_staged_token(cand.get("token"))
                if not token:
                    continue

                cand_topic = self._normalise_staged_token(cand.get("topic"))
                confidence = float(cand.get("confidence", 0.0) or 0.0)
                if confidence < 0.42:
                    continue

                if slot_name == "entity" and current_topic:
                    if token != current_topic and cand_topic != current_topic:
                        continue
                elif slot_name == "predicate" and current_topic and cand_topic:
                    if cand_topic != current_topic:
                        continue

                axis_focus = str(cand.get("axis_focus") or "").upper()
                axis_bonus = 0.08 if axis_focus and abs(ctx.axis_polarities.get(axis_focus, 0.0)) >= MAGNITUDE_PRESENT else 0.0
                topic_bonus = 0.08 if current_topic and (token == current_topic or cand_topic == current_topic) else 0.0
                source = str(cand.get("source") or "")
                source_bonus = {
                    "articulation.habit": 0.18,
                    "prompt.lexical": 0.12,
                    "prompt.phrase": 0.1,
                    "prompt.owned_entity": 0.12,
                    "runtime.capability": 0.14,
                    "fallback.seed": 0.09,
                    "language_projection": 0.06,
                    "sedi.semantic": 0.05,
                    "oets.node": 0.04,
                    "oets.relation": -0.08,
                    "oets.definition": -0.1,
                }.get(source, 0.0)
                score = confidence + axis_bonus + topic_bonus + source_bonus
                if score > best_score:
                    best = cand
                    best_score = score

        if not best:
            return False

        token = self._normalise_staged_token(best.get("token"))
        if slot_name == "entity":
            slots.entity = token
            if not slots.determiner:
                slots.determiner = "the"
            if "proper_noun" in set(best.get("roles") or []):
                slots.determiner = ""
        else:
            slots.predicate = token
        return True

    @staticmethod
    def _normalise_staged_token(value: Any) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"[^a-z0-9_ -]+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or len(text) > 40 or text in {"none", "null", "unknown"}:
            return ""
        return text

    def _is_depth_hollow(self, node: Any) -> bool:
        """§2.3: hollow if fails all three structural-depth criteria."""
        relations = getattr(node, "relations", {}) or {}
        if len(relations) >= MIN_RELATIONS:
            return False
        cluster_ids = getattr(node, "cluster_ids", set()) or set()
        if cluster_ids:
            return False
        usage_examples = getattr(node, "usage_examples", []) or []
        if len(usage_examples) >= MIN_USAGE_EXAMPLES:
            return False
        return True

    def _axis_alignment(self, node: Any, axis_vec: Dict[str, float]) -> float:
        nc = getattr(node, "noncomp_id", None)
        if not nc:
            return 0.5
        prefix = nc.split(":")[0].upper()
        return min(1.0, 0.4 + abs(axis_vec.get(prefix, 0.0)) * 0.6)

    # ── active seeking pathway (§6) ───────────────────────────────────────────
    def _seek_gap(
        self,
        ctx:       EmissionContext,
        slot_kind: str,
        slots:     SlotFrame,
        act:       SpeechAct,
    ) -> EmissionResult:
        topic = (ctx.input_frame.topic_concept or "") if ctx.input_frame else ""
        input_text = (ctx.input_frame.text or "") if ctx.input_frame else ""

        # §6.1 Seeking surface (manifold-generated slots)
        self._fill_seeking_slots(ctx, slot_kind, topic, input_text, slots)
        text = self._assemble(slots, SpeechAct.QUESTION, ctx)

        # §6.2 Route ComprehensionGap to input-side gap system
        self._route_comprehension_gap(ctx, slot_kind, topic, act, text)

        # §6.3 Set seeking flag in working memory
        flag_id = self._set_seeking_flag(ctx, slot_kind, topic)

        # §6.4 Push to OETS research queue (handled inside _route_comprehension_gap)

        return EmissionResult(
            text=text,
            speech_act=SpeechAct.QUESTION,
            slot_frame=slots,
            seeking=True,
            seeking_flag_id=flag_id,
            axis_signature=self._axis_signature(ctx),
            abstained=False,
        )

    def _fill_seeking_slots(self, ctx: EmissionContext, slot_kind: str, topic: str, input_text: str, slots: SlotFrame) -> None:
        """§6.1: Fill slots for generative seeking question."""
        import re as _re

        # Clear any determiner/negation set by axis X emit — seeking templates own their entity phrasing
        slots.determiner = ""
        slots.negation   = ""
        slots.tense_aux  = ""
        slots.predicate  = ""

        # Priority 1: explicit topic from utterance parser
        if topic and topic.strip():
            unclear = topic.strip()
            _tl = unclear.lower()
            # Don't seek on short words, common vocabulary, or names — the field
            # should generate from its state, not interrogate the user about basics
            _trivial = {
                "bro", "sis", "dude", "mate", "yall", "guys", "man", "fam",
                "what", "that", "this", "like", "just", "okay", "yeah", "nope",
                "nah", "huh", "hmm", "sup", "hey", "hi", "yo", "oh", "up",
                "aurora", "seph", "cael", "me", "you", "us", "them", "it",
            }
            if len(_tl) >= 5 and _tl not in _trivial:
                slots.agent = "What do you mean"
                slots.predicate = "by"
                slots.entity = f"'{unclear}'"
                return

        # Priority 2: axis reference in input text ("T axis", "X-axis", etc.)
        # input_text may be "[Conversation so far:\n...\n]\n\n{query}" — strip context prefix
        _bare = input_text or ""
        if "]\n\n" in _bare:
            _bare = _bare.split("]\n\n", 1)[1]
        _itext_up = _bare.upper()
        for _ax_ch in ("X", "T", "N", "B", "A"):
            if (f"{_ax_ch} AXIS" in _itext_up or f"{_ax_ch}-AXIS" in _itext_up
                    or f"{_ax_ch}_AXIS" in _itext_up):
                slots.agent = "What do you mean"
                slots.predicate = "by"
                slots.entity = f"'the {_ax_ch} axis'"
                return

        # Priority 3: scan input text for any OETS technical term the emitter can't fill
        if _bare and ctx.oets is not None:
            _words = _re.findall(r"[A-Za-z_]{3,}", _bare)
            for _w in _words:
                # SKIP: don't ask what common/basic words mean to prevent recursive definition loops.
                if len(_w) < 5 or _w.lower() in {
                    # People / relationships
                    "girl", "boy", "gender", "sex", "person", "human", "being", "friend",
                    "people", "someone", "anyone", "everyone",
                    # Common actions / states
                    "good", "bad", "great", "fine", "okay", "right", "wrong",
                    "run", "stop", "start", "open", "close", "done", "work",
                    "fast", "slow", "high", "low", "big", "small", "long", "short",
                    # Cognition / feeling
                    "love", "feel", "think", "know", "want", "need", "mean", "said",
                    "understand", "heard", "sense",
                    # Filler / discourse
                    "totally", "really", "actually", "just", "like", "very", "pretty",
                    "basically", "literally", "honestly", "definitely", "probably",
                    # Common nouns
                    "name", "app", "thing", "stuff", "part", "time", "place", "word",
                    "screen", "text", "message", "button", "input", "system", "state",
                    "idea", "point", "question", "answer", "reason", "result",
                    # Aurora's world
                    "aurora", "field", "wave", "axis", "crest",
                }:
                    continue

                _node = ctx.oets.nodes.get(_w) or ctx.oets.nodes.get(_w.lower())
                if _node and float(getattr(_node, 'comprehension_confidence', 0.0)) < 0.5:
                    slots.agent = "What do you mean"
                    slots.predicate = "by"
                    slots.entity = f"'{_w}'"
                    return

        # Fallback: IVM dominant axis description
        from aurora_internal.aurora_constraint_manifold_patched import MANIFOLD_FIRST_LAYER_PHASE_A, MANIFOLD_FIRST_LAYER_PHASE_B
        pols = ctx.axis_polarities
        dominant = max(pols, key=lambda k: abs(pols[k])) if pols else "X"
        notation = f"{dominant}.O[{dominant}]"
        cell = MANIFOLD_FIRST_LAYER_PHASE_A.get(notation) or MANIFOLD_FIRST_LAYER_PHASE_B.get(notation)
        desc = cell.get('slot_description', '').lower().strip(".") if cell else f"{dominant}-axis"
        slots.agent = "What do you mean"
        slots.predicate = "by that"
        slots.entity = f"in terms of the {desc}"

    def _fill_invalidation_slots(self, ctx: EmissionContext, slots: SlotFrame) -> None:
        """Fill slots for generative invalidation (nonsense handling)."""
        from aurora_internal.aurora_constraint_manifold_patched import MANIFOLD_FIRST_LAYER_PHASE_A, MANIFOLD_FIRST_LAYER_PHASE_B
        
        pols = ctx.axis_polarities
        dominant = max(pols, key=lambda k: abs(pols[k])) if pols else "X"
        notation = f"{dominant}.O[{dominant}]"
        cell = MANIFOLD_FIRST_LAYER_PHASE_A.get(notation) or MANIFOLD_FIRST_LAYER_PHASE_B.get(notation)
        desc = cell.get('slot_description', '').lower().strip(".") if cell else f"{dominant}-axis configuration"
        
        slots.agent = "I"
        slots.tense_aux = "am"
        slots.predicate = "discarding"
        slots.entity = f"the {desc}"

    def _route_comprehension_gap(
        self,
        ctx:       EmissionContext,
        slot_kind: str,
        topic:     str,
        act:       SpeechAct,
        question:  str,
    ) -> None:
        try:
            from aurora_internal.aurora_comprehension_gap import ComprehensionGap, GapType
            gap_id   = f"gap_{uuid.uuid4().hex[:8]}"
            gap = ComprehensionGap(
                gap_id=gap_id,
                gap_type=GapType.VOCABULARY,
                unclear_element=topic or slot_kind,
                source_text=(ctx.input_frame.text if ctx.input_frame else ""),
                question=question,
                context_before=f"slot_kind={slot_kind}, act={act.name}",
                confidence_before=0.0,
                axis_tension=ctx.axis_polarities,
            )
            gs = ctx.gap_system
            if gs and hasattr(gs, "memory") and hasattr(gs.memory, "active_gaps"):
                gs.memory.active_gaps[gap_id] = gap
        except Exception:
            pass

        # §6.4 Boost research priority on the OETS node
        try:
            if ctx.oets and topic and hasattr(ctx.oets, "nodes"):
                oets_node = ctx.oets.nodes.get(topic)
                if oets_node and hasattr(oets_node, "research_priority"):
                    oets_node.research_priority = min(
                        1.0, oets_node.research_priority + 0.3
                    )
        except Exception:
            pass

    def _topic_signature(self, topic: str, ctx: EmissionContext) -> str:
        dominant = max(
            ctx.axis_polarities,
            key=lambda k: abs(ctx.axis_polarities[k]),
            default="X",
        )
        raw = f"{topic}:{dominant}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _set_seeking_flag(
        self, ctx: EmissionContext, slot_kind: str, topic: str
    ) -> str:
        flag_id = f"seek_{uuid.uuid4().hex[:8]}"
        wm = ctx.working_memory
        if wm is None:
            return flag_id
        try:
            if not hasattr(wm, "seeking_flags"):
                wm.seeking_flags = {}
            sig      = self._topic_signature(topic, ctx)
            flag_key = f"{slot_kind}:{sig}"
            wm.seeking_flags[flag_key] = {
                "flag_id":                flag_id,
                "raised_at_turn":         ctx.turn_id,
                "axis_snapshot":          dict(ctx.axis_polarities),
                "predicted_answer_shape": slot_kind,
                "topic":                  topic,
                "status":                 "open",
            }
        except Exception:
            pass
        return flag_id

    # ── integration callback (§7) ─────────────────────────────────────────────
    def check_and_run_integration(self, ctx: EmissionContext) -> Optional[str]:
        """
        §7.1: Call at start of each turn. Checks for open seeking flags that
        match the current input's content shape. Runs mandatory integration
        steps if a match is found. Returns the closed flag_id or None.
        """
        wm = ctx.working_memory
        if wm is None or not hasattr(wm, "seeking_flags"):
            return None
        if not ctx.input_frame or not ctx.input_frame.text:
            return None

        open_flags = {
            k: v for k, v in wm.seeking_flags.items()
            if isinstance(v, dict) and v.get("status") == "open"
        }
        if not open_flags:
            return None

        # §7.1: most recent open flag whose predicted_answer_shape matches reply
        frame         = ctx.input_frame
        matched_key   = None
        matched_flag  = None

        for fk, fv in open_flags.items():
            topic = fv.get("topic", "")
            shape = fv.get("predicted_answer_shape", "")
            if topic and topic.lower() in frame.text.lower():
                matched_key, matched_flag = fk, fv
                break
            if frame.is_statement and shape in ("entity", "both"):
                matched_key, matched_flag = fk, fv
                break

        if matched_key is None:
            return None

        self._run_integration_steps(ctx, matched_key, matched_flag)
        return matched_flag.get("flag_id")

    def _run_integration_steps(
        self,
        ctx:       EmissionContext,
        flag_key:  str,
        flag:      Dict[str, Any],
    ) -> None:
        topic      = flag.get("topic") or ""
        shape      = flag.get("predicted_answer_shape", "entity")
        axis_snap  = flag.get("axis_snapshot", {})
        reply_text = ctx.input_frame.text if ctx.input_frame else ""

        # §7.2.1 OETS patch — locate or create node, attach definition + example
        try:
            if ctx.oets and topic:
                node = ctx.oets.nodes.get(topic)
                if node is None and hasattr(ctx.oets, "get_or_create_node"):
                    node = ctx.oets.get_or_create_node(topic)
                if node:
                    if hasattr(node, "add_definition"):
                        node.add_definition(reply_text, source="user_answer", confidence=0.7)
                    if hasattr(node, "add_usage_example"):
                        node.add_usage_example(reply_text, context="seeking_integration")
        except Exception:
            pass

        # §7.2.2 SediMemory channel carve along seeking axis configuration
        try:
            sedi = ctx.sedi_memory
            if sedi and hasattr(sedi, "ingest_event"):
                from aurora_sedimemory import ConstraintVector, ExistenceMode as _EM
                cv = ConstraintVector(
                    x=axis_snap.get("X", 0.0),
                    t=axis_snap.get("T", 0.0),
                    n=axis_snap.get("N", 0.0),
                    b=axis_snap.get("B", 0.0),
                    a=axis_snap.get("A", 0.0),
                )
                sedi.ingest_event(
                    content={
                        "seeking_closure": topic,
                        "shape":           shape,
                        "reply":           reply_text,
                    },
                    constraint_vector=cv,
                    source="constraint_emission_integration",
                )
        except Exception:
            pass

        # §7.2.3 Constraint genealogy pressure-relief event
        try:
            gen = ctx.constraint_genealogy
            if gen and hasattr(gen, "record_event"):
                from aurora_internal.constraint_genealogy import PressureVec
                relief = PressureVec(
                    x=abs(axis_snap.get("X", 0.0)) * 0.5,
                    t=abs(axis_snap.get("T", 0.0)) * 0.5,
                    n=ctx.n_heat * 0.5,
                    b=abs(axis_snap.get("B", 0.0)) * 0.5,
                    a=abs(axis_snap.get("A", 0.0)) * 0.5,
                )
                gen.record_event(relief, x_risk=0.1)
        except Exception:
            pass

        # §7.2.4 Close the seeking flag
        try:
            if hasattr(ctx.working_memory, "seeking_flags"):
                sf = ctx.working_memory.seeking_flags.get(flag_key)
                if sf:
                    sf["status"]         = "closed"
                    sf["closed_at_turn"] = ctx.turn_id
                    sf["resolution"]     = reply_text[:200]
        except Exception:
            pass

        # §7.2.5 Verification gate: next turn will re-run _resolve_content_slot;
        # if it still fails, seeking naturally re-fires — no extra bookkeeping needed.

    # ── honest constraint-driven abstain (§2.5) ──────────────────────────────
    def _emit_silent(self, ctx: EmissionContext) -> EmissionResult:
        """Empty pass-through — emitter has nothing to contribute; comprehension runs instead."""
        return EmissionResult(
            text="",
            speech_act=SpeechAct.ABSTAIN,
            abstained=True,
            axis_signature=self._axis_signature(ctx),
        )

    def _emit_abstain(self, ctx: EmissionContext) -> EmissionResult:
        """
        Fires only when speech-act is ABSTAIN (constraint-native inability).
        Not for missing vocabulary — that routes through _seek_gap.
        """
        p_A    = ctx.axis_polarities.get("A", 0.0)
        p_X    = ctx.axis_polarities.get("X", 0.0)
        mag_A  = abs(p_A)
        mag_X  = abs(p_X)
        ip     = ctx.i_state_polarities
        i_cant = ip.get("I_CANNOT", 0.0)
        i_dont = ip.get("I_DONOT",  0.0)

        if i_cant > 0.5:
            text = "I can't say."
        elif mag_A < MAGNITUDE_PRESENT:
            text = "Mm."
        elif p_A > POLARITY_WEAK and mag_X > 0.4:
            text = "I don't have a clear sense of that."
        elif p_A > POLARITY_WEAK and mag_A >= MAGNITUDE_HEDGE:
            text = "I'm not sure."
        elif i_dont > 0.5:
            text = "I don't."
        else:
            fr   = ctx.input_frame
            text = (
                "I don't have that yet."
                if (fr and fr.is_self_referential)
                else "I'm not sure."
            )

        return EmissionResult(
            text=text,
            speech_act=SpeechAct.ABSTAIN,
            abstained=True,
            axis_signature=self._axis_signature(ctx),
        )

    # ── surface assembly (§9) ─────────────────────────────────────────────────
    def _assemble(self, slots: SlotFrame, act: SpeechAct, ctx: EmissionContext) -> str:
        # ── short-circuit forms ──
        if act == SpeechAct.BACKCHANNEL or (
            act == SpeechAct.ACKNOWLEDGMENT
            and not slots.entity and not slots.predicate
        ):
            return ""

        if act == SpeechAct.AGREEMENT and not slots.predicate:
            return ""

        if act == SpeechAct.DISAGREEMENT and not slots.predicate:
            return ""

        if act == SpeechAct.REFUSAL:
            agent = slots.agent or "I can't"
            pred  = f" {slots.predicate}" if slots.predicate else ""
            return self._fmt(f"{agent}{pred}.")

        # ── full SVO path ──
        parts: List[str] = []
        subject, modal = self._split_subject_modal(slots.agent or "I")
        scope = slots.negation if slots.negation in {"always", "only", "just"} else ""
        negation = slots.negation if slots.negation and not scope else ""
        det_entity = f"{slots.determiner} {slots.entity}".strip()
        predicate = slots.predicate

        # Slot compatibility: an I-state capability signal can set the surface
        # agent to "I can", while content resolution may independently select a
        # copula such as "is".  Modals require a base verb, and identity copulas
        # should bind as identity, not capability: "I am Aurora", not
        # "I can is the aurora".
        force_aux = ""
        if modal and self._is_auxiliary_predicate(predicate):
            predicate = ""
        if modal and self._is_copular_predicate(predicate):
            if self._is_identity_entity(slots.entity):
                modal = ""
                predicate = ""
                force_aux = slots.tense_aux or "am"
                det_entity = self._format_identity_entity(slots.entity)
            else:
                predicate = self._base_verb(predicate)
        elif modal and self._is_identity_entity(slots.entity) and not self._predicate_can_take_identity(predicate):
            return ""
        elif modal and det_entity and not predicate:
            return ""

        x_fronted = bool(slots.fronted and det_entity)

        if slots.leading:
            parts.append(slots.leading + ",")

        if slots.sequence_connective:
            parts.append(slots.sequence_connective)

        if x_fronted:
            parts.append(det_entity + " —")

        parts.append(subject)

        if modal:
            parts.append(modal)
        elif force_aux or self._aux_needed(slots, act):
            aux = self._agree_aux(subject, force_aux or slots.tense_aux)
            if aux:
                parts.append(aux)

        # Negation — skip if already embedded in agent
        if negation and modal not in {"can't", "don't", "won't"}:
            parts.append(negation)

        if scope:
            parts.append(scope)

        # §9: predicate precedes determiner/entity in the normal SVO path.
        if predicate:
            pred = predicate
            if modal in {"can", "can't", "don't", "won't", "will", "would", "could", "should"}:
                pred = self._base_verb(pred)
            if slots.intensifier:
                pred = f"{slots.intensifier} {pred}"
            parts.append(pred)

        if det_entity and not x_fronted:
            parts.append(det_entity)

        if not parts:
            return ""

        terminal = "?" if act == SpeechAct.QUESTION else "."
        return self._fmt(" ".join(parts), terminal)

    @staticmethod
    def _split_subject_modal(agent: str) -> Tuple[str, str]:
        agent = re.sub(r"\s+", " ", str(agent or "")).strip()
        modal_map = {
            "I can't": ("I", "can't"),
            "I cannot": ("I", "can't"),
            "I don't": ("I", "don't"),
            "I do not": ("I", "don't"),
            "I can": ("I", "can"),
            "I think": ("I", "think"),
        }
        return modal_map.get(agent, (agent or "I", ""))

    @staticmethod
    def _base_verb(predicate: str) -> str:
        pred = str(predicate or "").strip()
        lower = pred.lower()
        irregular = {
            "am": "be",
            "are": "be",
            "is": "be",
            "did": "do",
            "done": "do",
            "was": "be",
            "were": "be",
            "been": "be",
            "had": "have",
            "has": "have",
            "held": "hold",
            "made": "make",
            "saw": "see",
            "seen": "see",
            "went": "go",
            "gone": "go",
        }
        if lower in irregular:
            return irregular[lower]
        if lower.endswith("ing") and len(lower) > 5:
            return lower[:-3]
        if lower.endswith("ed") and len(lower) > 4:
            stem = lower[:-2]
            if stem.endswith(stem[-1:] * 2):
                stem = stem[:-1]
            return stem
        return pred

    @staticmethod
    def _is_copular_predicate(predicate: str) -> bool:
        return str(predicate or "").strip().lower() in {
            "am", "are", "is", "be", "being", "been", "was", "were"
        }

    @staticmethod
    def _is_auxiliary_predicate(predicate: str) -> bool:
        return str(predicate or "").strip().lower() in {
            "can", "can't", "cannot", "could", "couldn't", "would", "wouldn't",
            "should", "shouldn't", "will", "won't", "do", "does", "did",
            "may", "might", "must"
        }

    @staticmethod
    def _is_identity_entity(entity: str) -> bool:
        return str(entity or "").strip().lower() in {"aurora", "self", "identity"}

    @staticmethod
    def _format_identity_entity(entity: str) -> str:
        text = str(entity or "").strip()
        if text.lower() == "aurora":
            return "Aurora"
        return text

    @staticmethod
    def _predicate_can_take_identity(predicate: str) -> bool:
        return str(predicate or "").strip().lower() in {
            "be", "become", "call", "name", "identify", "remember", "recognize",
            "describe", "explain", "answer"
        }

    @staticmethod
    def _agree_aux(subject: str, aux: str) -> str:
        aux = str(aux or "")
        if aux != "am":
            return aux
        subject_l = subject.lower()
        if subject_l.startswith("you") or subject_l in {"we", "they"}:
            return "are"
        if subject_l.startswith("it") or subject_l.startswith("there") or subject_l in {"she", "he", "that", "this"}:
            return "is"
        return "am"

    @staticmethod
    def _aux_needed(slots: SlotFrame, act: SpeechAct) -> bool:
        if not slots.tense_aux:
            return False
        if slots.tense_aux in {"will", "was", "were", "did", "have", "had"}:
            return True
        if slots.negation == "not":
            return True
        # Present-tense lexical predicates take bare present; identity has its
        # own fast-path, so "I understand the quasar" beats "I'm understand...".
        return not bool(slots.predicate)

    def _fmt(self, text: str, terminal: str = ".") -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        # Contractions
        text = re.sub(r'\bI am\b',     "I'm",     text)
        text = re.sub(r'\bI will\b',   "I'll",    text)
        text = re.sub(r'\byou will\b', "you'll",  text)
        text = re.sub(r'\bthere is\b', "there's", text)
        text = re.sub(r'\bdo not\b',   "don't",   text)
        text = re.sub(r'\bcan not\b',  "can't",   text)
        text = re.sub(r'\bwill not\b', "won't",   text)
        text = re.sub(r'\bit is\b',    "it's",    text)
        text = re.sub(r'\bnot any\b',  "no",      text)
        # Comma cleanup
        text = re.sub(r'\s+,', ',', text)
        text = re.sub(r',\s*,', ',', text)
        if text:
            text = text[0].upper() + text[1:]
        if text and text[-1] not in '.!?':
            text += terminal
        return text

    # ── telemetry ─────────────────────────────────────────────────────────────
    def _axis_signature(
        self, ctx: EmissionContext
    ) -> Dict[str, Tuple[float, float, float]]:
        return {
            axis: (
                ctx.axis_polarities.get(axis, 0.0),
                abs(ctx.axis_polarities.get(axis, 0.0)),
                ctx.n_heat,
            )
            for axis in CANONICAL_AXES
        }


# ── emission context builder (§11) ───────────────────────────────────────────
class EmissionContextBuilder:
    """
    Defensive bridge from live Aurora subsystems to EmissionContext.
    Builds per turn. Fails gracefully when subsystems are absent.
    """

    def build(
        self,
        systems:      Dict[str, Any],
        input_frame:  Optional[InputFrame] = None,
        recent_words: Optional[List[str]]  = None,
        turn_id:      Optional[str]        = None,
    ) -> EmissionContext:
        lattice    = systems.get("ivm_lattice") or systems.get("lattice")
        collective = systems.get("i_state_collective") or systems.get("collective")
        oets       = (
            systems.get("oets")
            or systems.get("ontological_web")
            or self._get_oets_web(systems)
        )
        identity   = self._get_identity(systems)
        wm         = systems.get("working_memory")
        sedi       = systems.get("sedi_memory") or systems.get("sedimemory")
        genealogy  = systems.get("constraint_genealogy") or systems.get("genealogy")
        gap_system = systems.get("comprehension_gap_system")
        staged_frame = systems.get("_staged_subsurface_frame")
        staged_frames = systems.get("_staged_subsurface_frames")
        ma         = self._get_meaning_anchors(systems)

        axis_polarities: Dict[str, float] = {}
        axis_velocities: Dict[str, float] = {}
        n_heat = 0.0

        if lattice is not None:
            try:
                for name, axis in lattice.vertices.axes.items():
                    axis_key = _AXIS_NAME_TO_CANONICAL.get(str(name), _AXIS_NAME_TO_CANONICAL.get(str(name).lower(), str(name)))
                    axis_polarities[axis_key] = float(getattr(axis, "polarity", 0.0))
                    axis_velocities[axis_key] = float(getattr(axis, "angular_velocity", 0.0))
                dissonance = lattice.compute_dissonance()
                n_heat     = float(dissonance.get("total_heat", 0.0))
            except Exception:
                pass

        i_state_polarities: Dict[str, float] = {}
        if collective is not None:
            try:
                for pred, being in collective.beings.items():
                    i_state_polarities[pred] = float(being.axis_polarity)
            except Exception:
                pass

        return EmissionContext(
            axis_polarities      = axis_polarities,
            axis_velocities      = axis_velocities,
            n_heat               = n_heat,
            i_state_polarities   = i_state_polarities,
            oets                 = oets,
            identity             = identity,
            input_frame          = input_frame,
            recent_words         = list(recent_words) if recent_words else [],
            meaning_anchors      = ma,
            working_memory       = wm,
            sedi_memory          = sedi,
            constraint_genealogy = genealogy,
            gap_system           = gap_system,
            staged_subsurface_frame = staged_frame if isinstance(staged_frame, dict) else None,
            staged_subsurface_frames = [f for f in (staged_frames or []) if isinstance(f, dict)],
            turn_id              = turn_id,
        )

    @staticmethod
    def _get_oets_web(systems: Dict[str, Any]) -> Any:
        try:
            perception = systems.get("perception")
            scaffolding = (
                systems.get("ontological_scaffolding")
                or systems.get("oets_scaffolding")
                or (getattr(perception, "oets", None) if perception else None)
            )
            if scaffolding and hasattr(scaffolding, "web"):
                return scaffolding.web
        except Exception:
            pass
        return None

    @staticmethod
    def _get_identity(systems: Dict[str, Any]) -> Any:
        try:
            chamber = systems.get("chamber")
            if chamber and hasattr(chamber, "_identity"):
                return chamber._identity
            return systems.get("identity") or systems.get("core_identity")
        except Exception:
            return None

    @staticmethod
    def _get_meaning_anchors(systems: Dict[str, Any]) -> Any:
        try:
            from aurora_internal.aurora_language_state import MeaningAnchors  # noqa: F401
            chamber = systems.get("chamber")
            if chamber and hasattr(chamber, "_meaning_anchors"):
                return chamber._meaning_anchors
        except Exception:
            pass
        return None


# ── convenience constructor (backward-compatible) ─────────────────────────────
def build_emission_context(
    lattice,
    collective,
    oets,
    identity,
    input_frame:          Optional[InputFrame] = None,
    recent_words:         Optional[List[str]]  = None,
    meaning_anchors=None,
    working_memory=None,
    sedi_memory=None,
    constraint_genealogy=None,
    gap_system=None,
    turn_id:              Optional[str]        = None,
) -> EmissionContext:
    axis_polarities: Dict[str, float] = {}
    axis_velocities: Dict[str, float] = {}
    for name, axis in lattice.vertices.axes.items():
        axis_polarities[name] = float(axis.polarity)
        axis_velocities[name] = float(getattr(axis, "angular_velocity", 0.0))

    dissonance = lattice.compute_dissonance()
    n_heat     = float(dissonance.get("total_heat", 0.0))

    i_state_polarities: Dict[str, float] = {
        pred: float(being.axis_polarity)
        for pred, being in collective.beings.items()
    }

    return EmissionContext(
        axis_polarities      = axis_polarities,
        axis_velocities      = axis_velocities,
        n_heat               = n_heat,
        i_state_polarities   = i_state_polarities,
        oets                 = oets,
        identity             = identity,
        input_frame          = input_frame,
        recent_words         = list(recent_words) if recent_words else [],
        meaning_anchors      = meaning_anchors,
        working_memory       = working_memory,
        sedi_memory          = sedi_memory,
        constraint_genealogy = constraint_genealogy,
        gap_system           = gap_system,
        turn_id              = turn_id,
    )


# ── self-test (§10.1) ─────────────────────────────────────────────────────────
def _self_test() -> bool:  # noqa: C901
    print("[CE self-test] running §10.1 unit tests...")
    emitter = ConstraintEmitter()
    passed = 0
    failed = 0

    def check(name: str, cond: bool, note: str = "") -> None:
        nonlocal passed, failed
        if cond:
            print(f"  PASS  [{name}]")
            passed += 1
        else:
            print(f"  FAIL  [{name}] {note}")
            failed += 1

    def _ctx(
        A=0.0, T_vel=0.0, heat=0.0, B=0.0, X=0.0, T_pol=0.0,
        i_states=None, frame=None, oets=None, identity=None, staged=None,
    ) -> EmissionContext:
        return EmissionContext(
            axis_polarities    = {"A": A, "T": T_pol, "N": 0.0, "B": B, "X": X},
            axis_velocities    = {"T": T_vel},
            n_heat             = heat,
            i_state_polarities = i_states or {},
            oets               = oets,
            identity           = identity,
            input_frame        = frame,
            staged_subsurface_frame = staged,
        )

    # ── stub OETS types ──
    class _EmptyOETS:
        nodes = {}
        def get_node(self, w): return None

    class _Node:
        def __init__(self, role, hollow=False):
            self.role = role
            self.comprehension_confidence = 0.9
            self.ontological_depth = 0.5
            self.emotional_valence = 0.0
            self.noncomp_id = "X:POLARITY"
            self.relations      = {} if hollow else {"r1": None, "r2": None}
            self.cluster_ids    = set() if hollow else {"c1"}
            self.usage_examples = [] if hollow else [object()]
            self.research_priority = 0.5

    class _HollowOETS:
        def __init__(self): self.nodes = {"quasar": _Node("noun", hollow=True)}
        def get_node(self, w): return self.nodes.get(w)

    class _RichOETS:
        def __init__(self):
            self.nodes = {
                "aurora": _Node("noun"),
                "sense":  _Node("verb"),
            }
            self.nodes["sense"].noncomp_id = "A:POLARITY"
        def get_node(self, w): return self.nodes.get(w)

    class _Identity:
        self_name = "Aurora"

    # Test 1 — identity question → contains "Aurora", not seeking
    r1 = emitter.emit(_ctx(
        A=0.5, identity=_Identity(),
        frame=InputFrame(
            text="what's your name?", is_question=True, is_directed=True,
            is_self_referential=True, topic_concept="name",
        ),
    ))
    check("T1 identity", "Aurora" in r1.text and not r1.seeking,
          f"text={r1.text!r} seeking={r1.seeking}")

    # Test 2 — question, no OETS resonance, topic=quasar → seeking, "?" in text
    r2 = emitter.emit(_ctx(
        A=0.5, oets=_EmptyOETS(), i_states={"I_IS": 0.4},
        frame=InputFrame(
            text="what is a quasar?", is_question=True, is_directed=True,
            topic_concept="quasar",
        ),
    ))
    check("T2 seeking quasar",
          r2.seeking and "?" in r2.text and "<X_SLOT>" not in r2.text,
          f"text={r2.text!r} seeking={r2.seeking}")

    # Test 3 — imperative + I_CANT → REFUSAL, contains "can't"
    r3 = emitter.emit(_ctx(
        A=0.6, i_states={"I_CANNOT": 0.8},
        frame=InputFrame(text="do that", is_imperative=True, is_directed=True),
    ))
    check("T3 refusal",
          ("can't" in r3.text or "cannot" in r3.text)
          and r3.speech_act == SpeechAct.REFUSAL,
          f"text={r3.text!r} act={r3.speech_act}")

    # Test 4 — aligns_with_oets, all axes quiet, I_IS → backchannel ≤4 words
    r4 = emitter.emit(_ctx(
        A=0.1, heat=0.0, i_states={"I_IS": 0.5},
        frame=InputFrame(text="the sky is blue", is_statement=True, aligns_with_oets=True),
    ))
    wc = len(r4.text.split())
    check("T4 short backchannel", wc <= 4, f"text={r4.text!r} words={wc}")

    # Test 5 — strong A+, X+, valid OETS hits → real assertion, no <X_SLOT>
    r5 = emitter.emit(_ctx(
        A=0.8, X=0.7, heat=0.0, oets=_RichOETS(),
        i_states={"I_IS": 0.6, "I_CAN": 0.6},
        frame=InputFrame(text="tell me something", is_question=True, is_directed=True),
    ))
    check("T5 real assertion",
          not r5.seeking
          and "<X_SLOT>" not in r5.text
          and "<PRED_SLOT>" not in r5.text,
          f"text={r5.text!r} seeking={r5.seeking}")

    # Test 6 — contradicts_oets, B-, I_ISNT → contains "no" or "not"
    r6 = emitter.emit(_ctx(
        A=0.5, B=-0.5, i_states={"I_ISNT": 0.6},
        frame=InputFrame(
            text="you are happy", is_statement=True, is_contradiction=True,
        ),
    ))
    check("T6 negation",
          "no" in r6.text.lower() or "not" in r6.text.lower(),
          f"text={r6.text!r}")

    # Test 7 — depth-hollow OETS hit → routes to seeking like no hit
    r7 = emitter.emit(_ctx(
        A=0.6, X=0.5, oets=_HollowOETS(),
        i_states={"I_IS": 0.4},
        frame=InputFrame(
            text="what is a quasar?", is_question=True, is_directed=True,
            topic_concept="quasar",
        ),
    ))
    check("T7 hollow routes to seeking", r7.seeking,
          f"text={r7.text!r} seeking={r7.seeking}")

    # Test 8 — hollow OETS hit, but Subsurface has a staged slot projection
    staged_quasar = {
        "ts": time.time(),
        "slot_projections": [
            {
                "token": "quasar",
                "roles": ["noun"],
                "slot_kind": "entity",
                "confidence": 0.86,
                "axis_focus": "X",
                "topic": "quasar",
            },
            {
                "token": "understand",
                "roles": ["verb"],
                "slot_kind": "predicate",
                "confidence": 0.78,
                "axis_focus": "A",
                "topic": "quasar",
            },
        ],
    }
    r8 = emitter.emit(_ctx(
        A=0.6, X=0.5, oets=_HollowOETS(), staged=staged_quasar,
        i_states={"I_IS": 0.4},
        frame=InputFrame(
            text="what is a quasar?", is_question=True, is_directed=True,
            topic_concept="quasar",
        ),
    ))
    check("T8 staged frame resolves hollow hit",
          not r8.seeking and "quasar" in r8.text and "understand" in r8.text,
          f"text={r8.text!r} seeking={r8.seeking}")

    print(f"\n[CE self-test] {passed}/{passed + failed} passed.")
    return failed == 0


if __name__ == "__main__":
    import sys
    ok = _self_test()
    sys.exit(0 if ok else 1)
