"""
Directive PF1.1 -- PropositionFrame builder.

RW7/PF1.0 established that word *choice* is not the defect in Aurora's
delivered text (F1/G1's relevance-primary scoring already works); the
defect is that motif *selection* never varies -- every turn uses the
same skeleton because nothing before word selection ever decides what
she is trying to say. This module derives that "what to say" as a
small, structured PropositionFrame, from real existing machinery --
no new grammar tables, no scripted content.

Fail-quiet derivation ladder (each rung tried only if the one above
produced nothing):
  1. ThoughtState (systems['_current_thought_state']), not skipped --
     her own internal thought, parsed through the existing utterance
     parser (aurora_internal/aurora_utterance_parser.py) to pull a
     lightweight subject/relation/object out of unified_interpretation
     + self_application. Stance = thought.confidence. source="thought".
  2. Current-turn claims from working_memory.proposition_substrate
     (aurora_internal/aurora_proposition_substrate.py) -- real claim
     triples already extracted and scored elsewhere in the pipeline.
     Highest score_claim() wins. source="claim".
  3. NonComp anchor only (state.noncomp_input_state['anchor']) -- no
     relation, just a topic to be about. source="anchor".
  4. None -- composer behaves exactly as today. Zero regression
     surface; every consumer of build_frame() must treat None as
     "frame absent, fall back to existing pressure-only behavior."

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aurora_expression_perception import infer_word_role, is_bare_interrogative_token
from aurora_internal.aurora_semantic_probe_battery import _STRONG_FUNCTION_WORDS


@dataclass
class PropositionFrame:
    subject: str = ""
    relation: str = ""
    obj: str = ""
    negated: bool = False
    stance: float = 0.5
    unresolved: List[str] = field(default_factory=list)
    topic: str = ""
    source: str = ""  # "constraint_relation" | "thought" | "claim" | "anchor"
    complement: str = ""
    unknown_role: str = ""
    derivation_signature: str = ""
    # Directive P2: raw regional-density reading, kept separate from
    # `stance` so downstream consumers can tell "low because untested"
    # (corroboration-only) from "low because unfamiliar territory"
    # (density-driven). None when sedimemory was absent/empty/not
    # consulted -- never a fabricated number.
    density: Optional[float] = None


def _record_frame_decision(
    systems: Dict[str, Any],
    *,
    function_id: str,
    inputs: Dict[str, Any],
    frame: Optional[PropositionFrame],
    decision: str,
    reason: str,
    derived: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish frame-construction provenance to Aurora's native bridge."""
    bridge = systems.get("system_introspection") if isinstance(systems, dict) else None
    if bridge is None or not hasattr(bridge, "record_boundary_decision"):
        return
    try:
        bridge.record_boundary_decision(
            function_id=function_id,
            stage="proposition_frame_construction",
            inputs=inputs,
            derived={
                **dict(derived or {}),
                "frame_source": str(getattr(frame, "source", "") or ""),
                "frame_subject": str(getattr(frame, "subject", "") or ""),
                "frame_relation": str(getattr(frame, "relation", "") or ""),
                "frame_object": str(getattr(frame, "obj", "") or ""),
                "frame_complement": str(getattr(frame, "complement", "") or ""),
                "frame_unknown_role": str(getattr(frame, "unknown_role", "") or ""),
                "frame_derivation_signature": str(getattr(frame, "derivation_signature", "") or ""),
            },
            decision=decision,
            output=frame,
            reason=reason,
            confidence=0.94 if frame is not None else 0.75,
            tags=["proposition_frame", "meaning_to_language", decision],
        )
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="system_introspection:proposition_frame_probe",
            exc=_aurora_boundary_exc,
            context={"function": "_record_frame_decision", "source_file": __file__},
        )


# Same noise/length gate SemanticIntentionBridge already uses for
# thought-text token extraction -- reused, not reinvented.
_MIN_TOKEN_LEN = 3


def _frame_object(value: Any) -> str:
    """Normalize a frame object without promoting a question marker.

    Thought-text extraction already filters structural words.  Claims,
    turn-local claims, anchors, restored frames, and future producers do not
    all pass through that extraction route, so frame construction applies the
    same fail-quiet invariant before the object reaches SentenceComposer.
    The final binder repeats the check because frames can also be constructed
    directly outside this module.
    """
    obj = str(value or "").strip()
    return "" if is_bare_interrogative_token(obj) else obj


def density_confidence(systems: Dict[str, Any], topic: str, axis: str) -> Optional[float]:
    """Directive P2 -- regional density confidence, the missing stance
    signal. Not a classifier over the proposition's words: a lookup
    into how populated the region of her own constraint-space is that
    the proposition's configuration falls into, via SediMemory's
    existing `recall_semantic` (axis-filtered query over deposited
    fragments already organized onto the 25-slot NC lattice). Two
    propositions with identical phrasing but different topics get
    different readings only because one lands somewhere she's lived
    and the other doesn't.

    Fail-quiet: no sedimemory, no topic, or an empty result set all
    return None -- never a fabricated number. Normalized via the
    simplest honest function available (count share of max_results,
    scaled by mean resonance) -- no tuned constants.
    """
    topic = str(topic or "").strip()
    if not topic:
        return None
    sedimemory = systems.get("sedimemory") if isinstance(systems, dict) else None
    if sedimemory is None or not hasattr(sedimemory, "recall_semantic"):
        return None
    try:
        results = sedimemory.recall_semantic(
            query_text=topic, axis_filter=str(axis or "").strip() or None, max_results=8,
        )
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:density_confidence",
            exc=_aurora_boundary_exc,
            context={"function": "density_confidence", "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        return None
    if not results:
        return None
    resonances = [float(r.get("resonance", 0.0) or 0.0) for r in results]
    mean_resonance = sum(resonances) / len(resonances)
    count_share = min(1.0, len(results) / 8.0)
    return max(0.0, min(1.0, count_share * mean_resonance))


# PF1.4's own real-world verification (60-probe live-boot run) caught
# `unified_interpretation` in its ACTUAL delivered shape for the first
# time -- prior fixture text in PF1.1's unit tests was hand-written
# natural language, never this. aurora_thought_formation.py's own
# ThoughtState docstring says it plainly: "This is Aurora's internal
# thought -- NOT the response." Its real generators
# (_reason_through_dominant, _partial_interpretation) format it as an
# internal telemetry trace -- pipe-joined labeled segments ("Operating
# on: ... | Triggered by: warp_coverage_extension, x=0.50 | Dominant
# pressure: A-axis (0.62)") or a "[partial] ..." fallback -- never a
# sentence. Parsing that literally surfaced real internal tokens
# ("triggered", "x=0.50") straight into delivered text ("I triggered
# x=0.50."). This is the fix: refuse to parse the known telemetry
# shape at all, rather than trying to filter it token by token.
_TELEMETRY_MARKERS = (
    "Operating on:", "Active processes:", "Triggered by:",
    "Dominant pressure:", "Unresolved tension:", "Background:",
)


def _looks_like_internal_telemetry(text: str) -> bool:
    if text.startswith("[partial]"):
        return True
    return any(marker in text for marker in _TELEMETRY_MARKERS)


def _extract_triple_from_thought_text(text: str) -> Optional[Dict[str, Any]]:
    """Lightweight subject/relation/object extraction from Aurora's own
    plain-language thought text, via the existing utterance parser (for
    topic + negation) plus a single infer_word_role scan for the first
    verb-tagged token (relation) and the first non-topic noun-tagged
    token (object) -- the same "regex/role-tag over full-parse" honesty
    level already established for this kind of extraction elsewhere in
    this codebase (Track CP's extract_joints, SemanticIntentionBridge's
    keyword pull). Returns None if no usable topic is found, or if the
    text is recognizably internal telemetry rather than a thought
    expressed in language."""
    if not text or not str(text).strip():
        return None
    text = str(text)
    if _looks_like_internal_telemetry(text):
        return None
    try:
        from aurora_internal.aurora_utterance_parser import parse_utterance
        parsed = parse_utterance(text)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:99",
            exc=_aurora_boundary_exc,
            context={"function": "_extract_triple_from_thought_text", "handler_line": 99, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        parsed = {}

    topic = str(parsed.get("topic", "") or "").strip()
    topic_words = list(parsed.get("topic_words", []) or [])
    negated = bool(parsed.get("negated", False))
    if not topic and topic_words:
        topic = topic_words[0]
    if not topic or "=" in topic:
        return None

    relation = ""
    obj = ""
    tokens = [t.strip(".,!?;:\"'()").lower() for t in text.split()]
    topic_lower = topic.lower()
    for tok in tokens:
        if len(tok) < _MIN_TOKEN_LEN:
            continue
        # Defense in depth beyond the whole-text telemetry check above:
        # no genuine spoken word ever contains "=" -- catches stray
        # "key=value" tokens (e.g. topic strings assigned straight from
        # a ProcessContext.what_it_is_operating_on like
        # "aurora:activation=0.75") even outside the pipe-joined format.
        if "=" in tok:
            continue
        # W1 live-fire finding (PF1.6 residue characterization,
        # 2026-07-21): once the linguistic context started carrying real
        # turn text, contractions ("he's", "what's", "i'm") surfaced as
        # spurious relation/obj candidates -- infer_word_role has no
        # apostrophe-aware rule, so an unrecognized contraction defaults
        # to "noun" and binds straight into a content slot ("I am
        # planning he's."). A contraction is a compressed pronoun+verb,
        # never itself a usable standalone content word for this
        # extraction's purposes -- excluded outright, same as the "="
        # guard above.
        if "'" in tok:
            continue
        # Bug Report 2 (2026-08-03): infer_word_role has no wh-word entry
        # in its _ROLE_HINTS table (nor a matching suffix rule), so an
        # interrogative like "what"/"how"/"why" falls through to its
        # generic "unknown word -> noun" default -- confirmed live,
        # "What is a guitar chord?" produced a thought text where "what"
        # (appearing before any real content noun) got bound as `obj`,
        # and nothing ever overwrote it (obj is first-match-wins below),
        # so the delivered proposition frame carried relation="",
        # obj="what" even though the topic itself (guitar/chord) was
        # correctly identified upstream. A wh-word is a structural
        # question marker, never itself the content of a declarative
        # proposition -- excluded here the same way "=" tokens and
        # contractions already are, using the SAME strong-function-word
        # set (aurora_semantic_probe_battery._STRONG_FUNCTION_WORDS)
        # this codebase already treats as structural glue, not content.
        if tok in _STRONG_FUNCTION_WORDS:
            continue
        if tok == topic_lower:
            continue
        role = infer_word_role(tok)
        if not relation and role == "verb":
            relation = tok
            continue
        if not obj and role == "noun":
            obj = tok
        if relation and obj:
            break

    return {"subject": topic, "relation": relation, "obj": obj, "negated": negated, "topic": topic}



def _frame_from_constraint_relation(systems: Dict[str, Any]) -> Optional[PropositionFrame]:
    """Highest-authority frame: the current utterance's preserved relation.

    This does not infer a response category.  It carries the clause-level
    configuration that entered X and was retained through the live turn state.
    """
    if not isinstance(systems, dict):
        return None
    active = systems.get("_active_turn_state")
    relation = dict(getattr(active, "relational_form", {}) or {}) if active is not None else {}
    if not relation:
        parsed = dict(getattr(active, "parsed", {}) or {}) if active is not None else {}
        relation = dict(parsed.get("relational_form") or {})
    if not relation:
        return None
    subject = str(relation.get("subject", "") or "").strip()
    raw_obj = str(relation.get("obj", "") or "").strip()
    complement = str(relation.get("complement", "") or "").strip()
    relation_word = str(relation.get("relation", "") or "").strip()
    unknown_role = str(relation.get("unknown_role", "") or "").strip()
    obj = _frame_object(raw_obj)
    if not any((subject, relation_word, obj, complement)):
        return None
    # A missing subject/object is a genuine unknown slot, not permission to
    # place the interrogative token in spoken content.
    frame = PropositionFrame(
        subject=subject,
        relation=relation_word,
        obj=obj,
        complement=complement,
        unknown_role=unknown_role,
        negated=bool(relation.get("negated", False)),
        stance=float(relation.get("confidence", 0.5) or 0.5),
        unresolved=[unknown_role] if unknown_role else [],
        topic=subject or obj or complement,
        source="constraint_relation",
        derivation_signature="X^1*T^1*N^1*B^1*A^1",
    )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame._frame_from_constraint_relation",
        inputs={"relational_form": relation},
        frame=frame,
        decision="selected",
        reason="current utterance relation retained through the root-constraint turn state",
        derived={
            "complement": complement,
            "unknown_role": unknown_role,
            "derivation_signature": frame.derivation_signature,
        },
    )
    return frame

def _frame_from_thought_state(systems: Dict[str, Any]) -> Optional[PropositionFrame]:
    """W1 (PF1.6 residue characterization, 2026-07-21): unified_
    interpretation/self_application are built by aurora_thought_
    formation._reason_through_dominant() purely from administrative
    ProcessContexts (memory-ambient, identity-predicates, loop-counts)
    -- an internal telemetry trace, never the turn's own content, and
    always in the pipe-joined shape _looks_like_internal_telemetry()
    correctly rejects. Confirmed live: 0/60 probes ever reached this
    rung through that text. The real fix is upstream, in aurora_braid_
    wiring.py's _build_turn_process_contexts(), which now registers a
    "linguistic" process carrying the turn's actual text -- read
    directly from dominant_thread here, never through the telemetry
    strings, so there's nothing for the telemetry guard to reject in
    the first place."""
    thought_state = systems.get("_current_thought_state") if isinstance(systems, dict) else None
    if thought_state is None or bool(getattr(thought_state, "skipped", False)):
        return None

    triple = None
    for ctx in (getattr(thought_state, "dominant_thread", None) or []):
        if getattr(ctx, "process_type", "") == "linguistic":
            triple = _extract_triple_from_thought_text(
                str(getattr(ctx, "what_it_is_operating_on", "") or ""))
            if triple:
                break

    if not triple:
        # Fallback for the pre-fix shape (no linguistic context present,
        # e.g. an older/degraded thought_state) -- the telemetry guard
        # still applies here, so this rarely produces anything, by design.
        combined = " ".join(
            str(s) for s in (
                getattr(thought_state, "unified_interpretation", "") or "",
                getattr(thought_state, "self_application", "") or "",
            ) if s
        ).strip()
        triple = _extract_triple_from_thought_text(combined)
    if not triple:
        return None

    frame = PropositionFrame(
        subject=triple["subject"],
        relation=triple["relation"],
        obj=triple["obj"],
        negated=triple["negated"],
        stance=float(getattr(thought_state, "confidence", 0.5) or 0.5),
        unresolved=list(getattr(thought_state, "unresolved", []) or []),
        topic=triple["topic"],
        source="thought",
    )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame._frame_from_thought_state",
        inputs={
            "dominant_thread": list(getattr(thought_state, "dominant_thread", []) or []),
            "unified_interpretation": str(getattr(thought_state, "unified_interpretation", "") or ""),
        },
        frame=frame,
        decision="selected",
        reason="linguistic thought-state content yielded a proposition triple",
        derived={"triple": dict(triple)},
    )
    return frame


def _frame_from_claims(systems: Dict[str, Any]) -> Optional[PropositionFrame]:
    working_memory = systems.get("working_memory") if isinstance(systems, dict) else None
    substrate = getattr(working_memory, "proposition_substrate", None) if working_memory is not None else None
    if substrate is None:
        return None
    try:
        current_turn = int(getattr(working_memory, "turn_count", 0) or 0)
        candidates = [
            node for node in getattr(substrate, "nodes", {}).values()
            if int(node.get("turn", -1) or -1) == current_turn
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda n: substrate.score_claim(n))
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:216",
            exc=_aurora_boundary_exc,
            context={"function": "_frame_from_claims", "handler_line": 216, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        return None

    subject = str(best.get("subject", "") or "").strip()
    if not subject:
        return None
    raw_obj = str(best.get("object", "") or "").strip()
    obj = _frame_object(raw_obj)
    frame = PropositionFrame(
        subject=subject,
        relation=str(best.get("relation", "") or "").strip(),
        obj=obj,
        negated=bool(best.get("negated", False)),
        stance=float(best.get("confidence", 0.5) or 0.5),
        unresolved=[],
        topic=subject,
        source="claim",
    )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame._frame_from_claims",
        inputs={"raw_claim": dict(best), "raw_object": raw_obj},
        frame=frame,
        decision="selected",
        reason="highest-scoring current-turn proposition substrate claim",
        derived={"object_was_structural": bool(raw_obj and not obj)},
    )
    return frame


def _frame_from_turn_local_claims(systems: Dict[str, Any]) -> Optional[PropositionFrame]:
    """PF3.2 (2026-07-21): turn-local consumer for claims WorkingMemory.
    _CLAIM_SKIP_SUBJECTS excluded from the substrate (pronoun/wh-word
    subjects, e.g. "He's a bit nervous around new people.") --
    aurora_working_memory.py's own docstring on _turn_local_claims and
    _CLAIM_SKIP_SUBJECTS explains why the substrate exclusion stays
    (contradiction identity keys by subject; an unresolved "he"/"she"
    colliding across referents would manufacture false contradictions).
    The frame needs no cross-turn identity, so it renders the pronoun as
    spoken ("he" stays "he") -- lower precedence than a real substrate
    claim (_frame_from_claims), higher than anchor. These claims were
    never persisted anywhere else, so there is no scored-edge signal to
    rank by (unlike substrate nodes' score_claim) -- most recent for
    this turn wins, the same recency default used elsewhere in this
    module when no stronger signal exists."""
    working_memory = systems.get("working_memory") if isinstance(systems, dict) else None
    turn_local = getattr(working_memory, "_turn_local_claims", None) if working_memory is not None else None
    if not turn_local:
        return None
    try:
        current_turn = int(getattr(working_memory, "turn_count", 0) or 0)
        candidates = [c for c in turn_local if int(c.get("turn", -1) or -1) == current_turn]
        if not candidates:
            return None
        best = candidates[-1]
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:260",
            exc=_aurora_boundary_exc,
            context={"function": "_frame_from_turn_local_claims", "handler_line": 260, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        return None

    subject = str(best.get("subject", "") or "").strip()
    if not subject:
        return None
    raw_obj = str(best.get("object", "") or "").strip()
    obj = _frame_object(raw_obj)
    frame = PropositionFrame(
        subject=subject,
        relation=str(best.get("relation", "") or "").strip(),
        obj=obj,
        negated=bool(best.get("negated", False)),
        stance=0.5,
        unresolved=[],
        topic=subject,
        source="claim",
    )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame._frame_from_turn_local_claims",
        inputs={"raw_claim": dict(best), "raw_object": raw_obj},
        frame=frame,
        decision="selected",
        reason="most recent current-turn claim outside the persistent substrate",
        derived={"object_was_structural": bool(raw_obj and not obj)},
    )
    return frame


def _frame_from_anchor(systems: Dict[str, Any], state: Any) -> Optional[PropositionFrame]:
    noncomp_input_state = dict(getattr(state, "noncomp_input_state", {}) or {})
    anchor = str(noncomp_input_state.get("anchor", "") or "").strip()
    if not anchor:
        return None
    obj = _frame_object(anchor)
    frame = PropositionFrame(
        subject="self", relation="", obj=obj, negated=False,
        stance=0.5, unresolved=[], topic=anchor, source="anchor",
    )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame._frame_from_anchor",
        inputs={"raw_anchor": anchor},
        frame=frame,
        decision="selected",
        reason="noncomp input anchor supplied the final frame fallback",
        derived={"object_was_structural": bool(anchor and not obj)},
    )
    return frame


def _derive_frame(systems: Dict[str, Any], state: Any) -> Optional[PropositionFrame]:
    """Fail-quiet derivation ladder. Returns None (never raises) if no
    rung produces a usable frame -- callers must treat None exactly like
    "no PropositionFrame available," preserving today's behavior."""
    try:
        frame = _frame_from_constraint_relation(systems)
        if frame is not None:
            return frame
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:constraint_relation",
            exc=_aurora_boundary_exc,
            context={"function": "build_frame", "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        pass
    try:
        frame = _frame_from_thought_state(systems)
        if frame is not None:
            return frame
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:298",
            exc=_aurora_boundary_exc,
            context={"function": "build_frame", "handler_line": 298, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        pass
    try:
        frame = _frame_from_claims(systems)
        if frame is not None:
            return frame
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:304",
            exc=_aurora_boundary_exc,
            context={"function": "build_frame", "handler_line": 304, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        pass
    try:
        frame = _frame_from_turn_local_claims(systems)
        if frame is not None:
            return frame
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:310",
            exc=_aurora_boundary_exc,
            context={"function": "build_frame", "handler_line": 310, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        pass
    try:
        frame = _frame_from_anchor(systems, state)
        if frame is not None:
            return frame
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:316",
            exc=_aurora_boundary_exc,
            context={"function": "_derive_frame", "handler_line": 316, "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
        pass
    return None


def build_frame(systems: Dict[str, Any], state: Any) -> Optional[PropositionFrame]:
    """Directive PF1.1's fail-quiet derivation ladder (_derive_frame),
    plus Directive P2's regional-density blend: whichever rung fires,
    the resulting frame's stance can never exceed what her own
    experiential density in that region supports -- a proposition
    can't claim more confidence than she has standing to back it with,
    but a low corroboration-confidence claim in well-known territory
    isn't artificially dragged down further. Never raises; density
    blending is itself fail-quiet (a lookup failure just leaves
    stance/density as the ladder produced them)."""
    frame = _derive_frame(systems, state)
    if frame is None:
        _record_frame_decision(
            systems,
            function_id="aurora_internal.aurora_proposition_frame.build_frame",
            inputs={
                "has_thought_state": bool(systems.get("_current_thought_state")) if isinstance(systems, dict) else False,
                "has_working_memory": bool(systems.get("working_memory")) if isinstance(systems, dict) else False,
            },
            frame=None,
            decision="empty",
            reason="no thought, claim, turn-local claim, or anchor rung produced a usable frame",
        )
        return frame
    try:
        axis = str(dict(systems.get("_last_noncomp_input") or {}).get("constraint", "") or "").strip()
        topic = frame.topic or f"{frame.subject} {frame.obj}".strip()
        density = density_confidence(systems, topic, axis)
        frame.density = density
        if density is not None:
            frame.stance = min(frame.stance, density)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_proposition_frame.py:build_frame:density_blend",
            exc=_aurora_boundary_exc,
            context={"function": "build_frame", "source_file": "aurora_internal/aurora_proposition_frame.py"},
        )
    _record_frame_decision(
        systems,
        function_id="aurora_internal.aurora_proposition_frame.build_frame",
        inputs={"selected_rung": str(getattr(frame, "source", "") or "")},
        frame=frame,
        decision="emitted",
        reason="proposition frame completed density-aware construction",
        derived={"density": getattr(frame, "density", None), "stance": getattr(frame, "stance", None)},
    )
    return frame
