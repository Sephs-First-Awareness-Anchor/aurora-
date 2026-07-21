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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aurora_expression_perception import infer_word_role


@dataclass
class PropositionFrame:
    subject: str = ""
    relation: str = ""
    obj: str = ""
    negated: bool = False
    stance: float = 0.5
    unresolved: List[str] = field(default_factory=list)
    topic: str = ""
    source: str = ""  # "thought" | "claim" | "anchor"


# Same noise/length gate SemanticIntentionBridge already uses for
# thought-text token extraction -- reused, not reinvented.
_MIN_TOKEN_LEN = 3


def _extract_triple_from_thought_text(text: str) -> Optional[Dict[str, Any]]:
    """Lightweight subject/relation/object extraction from Aurora's own
    plain-language thought text, via the existing utterance parser (for
    topic + negation) plus a single infer_word_role scan for the first
    verb-tagged token (relation) and the first non-topic noun-tagged
    token (object) -- the same "regex/role-tag over full-parse" honesty
    level already established for this kind of extraction elsewhere in
    this codebase (Track CP's extract_joints, SemanticIntentionBridge's
    keyword pull). Returns None if no usable topic is found."""
    if not text or not str(text).strip():
        return None
    try:
        from aurora_internal.aurora_utterance_parser import parse_utterance
        parsed = parse_utterance(str(text))
    except Exception:
        parsed = {}

    topic = str(parsed.get("topic", "") or "").strip()
    topic_words = list(parsed.get("topic_words", []) or [])
    negated = bool(parsed.get("negated", False))
    if not topic and topic_words:
        topic = topic_words[0]
    if not topic:
        return None

    relation = ""
    obj = ""
    tokens = [t.strip(".,!?;:\"'()").lower() for t in str(text).split()]
    topic_lower = topic.lower()
    for tok in tokens:
        if len(tok) < _MIN_TOKEN_LEN:
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


def _frame_from_thought_state(systems: Dict[str, Any]) -> Optional[PropositionFrame]:
    thought_state = systems.get("_current_thought_state") if isinstance(systems, dict) else None
    if thought_state is None or bool(getattr(thought_state, "skipped", False)):
        return None

    combined = " ".join(
        str(s) for s in (
            getattr(thought_state, "unified_interpretation", "") or "",
            getattr(thought_state, "self_application", "") or "",
        ) if s
    ).strip()
    triple = _extract_triple_from_thought_text(combined)
    if not triple:
        return None

    return PropositionFrame(
        subject=triple["subject"],
        relation=triple["relation"],
        obj=triple["obj"],
        negated=triple["negated"],
        stance=float(getattr(thought_state, "confidence", 0.5) or 0.5),
        unresolved=list(getattr(thought_state, "unresolved", []) or []),
        topic=triple["topic"],
        source="thought",
    )


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
    except Exception:
        return None

    subject = str(best.get("subject", "") or "").strip()
    if not subject:
        return None
    obj = str(best.get("object", "") or "").strip()
    return PropositionFrame(
        subject=subject,
        relation=str(best.get("relation", "") or "").strip(),
        obj=obj,
        negated=bool(best.get("negated", False)),
        stance=float(best.get("confidence", 0.5) or 0.5),
        unresolved=[],
        topic=subject,
        source="claim",
    )


def _frame_from_anchor(systems: Dict[str, Any], state: Any) -> Optional[PropositionFrame]:
    noncomp_input_state = dict(getattr(state, "noncomp_input_state", {}) or {})
    anchor = str(noncomp_input_state.get("anchor", "") or "").strip()
    if not anchor:
        return None
    return PropositionFrame(
        subject="self", relation="", obj=anchor, negated=False,
        stance=0.5, unresolved=[], topic=anchor, source="anchor",
    )


def build_frame(systems: Dict[str, Any], state: Any) -> Optional[PropositionFrame]:
    """Fail-quiet derivation ladder. Returns None (never raises) if no
    rung produces a usable frame -- callers must treat None exactly like
    "no PropositionFrame available," preserving today's behavior."""
    try:
        frame = _frame_from_thought_state(systems)
        if frame is not None:
            return frame
    except Exception:
        pass
    try:
        frame = _frame_from_claims(systems)
        if frame is not None:
            return frame
    except Exception:
        pass
    try:
        frame = _frame_from_anchor(systems, state)
        if frame is not None:
            return frame
    except Exception:
        pass
    return None
