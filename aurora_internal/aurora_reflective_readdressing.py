"""
aurora_reflective_readdressing.py
=================================

Aurora's native reflective readdressing faculty.

This module does not add a command parser, response template, or second
reasoning engine.  It gives Aurora's existing turn pipeline a way to reopen a
recent reasoning state when new evidence, perspective, contradiction,
clarification, or self-directed inquiry makes that useful.

The faculty has four responsibilities:

1. Preserve a bounded, structured snapshot of completed reasoning turns.
2. Resolve whether a new utterance is continuous with and reflective upon a
   prior reasoning episode using Aurora's normal pragmatic parse and context.
3. Build a turn-local reapplication context that the normal X/T/N/B/A chain
   can process, including a temporary axis perspective rather than a permanent
   mutation.
4. Compare the original and reconsidered outcomes and publish that evidence to
   Aurora's existing understanding and QuasiArch systems.

No permanent belief, rule, or code change is made here.  Successful
readdressing becomes evidence for Aurora's already-existing developmental and
evolutionary systems, which retain authority over promotion.

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from aurora_internal.aurora_runtime_faults import (
    record_exception_from_locals as _aurora_record_exception_from_locals,
)

_AXES = ("X", "T", "N", "B", "A")
_MAX_TEXT = 1600
_SCHEMA_VERSION = 1
_REFLECTIVE_ACTIONS = {
    "consider", "reconsider", "rethink", "revisit", "reframe", "compare",
    "examine", "inspect", "look", "try", "imagine", "suppose", "approach",
    "view", "treat", "assume", "focus", "shift", "weigh", "reevaluate",
}

# Build 613 (Reflective-Introspection Misrouting Repair C): generic
# engineering vocabulary that occurs constantly in Aurora's own function
# names -- "state", "action", "response", "prediction" are exactly the
# words an ordinary external-world prompt about a simulated world uses too
# (RCEC's own prompts talk about "action"/"state"/"prediction" as world
# concepts). A term this generic matching SOME function name is lexical
# coincidence, not evidence Aurora is being asked to inspect her own
# source anatomy -- it must never count toward technical_evidence alone.
_GENERIC_ANATOMY_TERMS = frozenset({
    "state", "action", "response", "prediction", "process", "result",
    "system", "path", "input", "output", "data", "turn", "step", "value",
    "answer", "question", "world", "object", "item", "thing", "event",
})

# Build 613 (Repair C): a genuine technical self-inquiry names Aurora's
# own reasoning/response-formation process explicitly -- not merely "you"
# appearing somewhere in an otherwise ordinary second-person sentence
# ("how confident are you" is not "how did you produce that answer").
_EXPLICIT_SELF_INQUIRY_PATTERNS: Tuple[re.Pattern, ...] = tuple(re.compile(p) for p in (
    r"\byour (reasoning|answer|response|logic|thinking|process|route|reply)\b",
    r"\bhow (did|do|does) (you|that|this|it) (answer|respond|reason|arrive|decide|produce|conclude|come up|get to|work)\b",
    r"\bwhy did you (say|answer|respond|conclude|decide)\b",
    r"\bwhat (led|caused) you to\b",
    r"\bhow (was|is) (that|this|your) (answer|response) (produced|formed|generated|arrived at)\b",
    r"\bexplain (your|how you) (reasoning|answer|response|logic|thinking|process|route|reply)\b",
    r"\bwalk me through (your|how you) (reasoning|answer|response|logic|thinking|process|route|reply)\b",
    r"\b(your|the) (internal )?(reasoning process|thought process|response formation|reasoning path)\b",
    r"\bhow you (produced|formed|arrived at|got to|generated) (that|this|your)\b",
))


def _explicit_self_inquiry_reference(text: str) -> bool:
    low = str(text or "").lower()
    return any(pattern.search(low) for pattern in _EXPLICIT_SELF_INQUIRY_PATTERNS)


# Build 613 (Repair D): the core delivery invariant needs to recognize the
# specific shape of prose Aurora's own render_self_inquiry() produces --
# module paths, qualified function names, and its own narration phrasing
# -- independent of whatever response_src tag happens to be attached, so a
# mislabeled or lost tag still gets caught.
_REFLECTIVE_NARRATION_PHRASES: Tuple[str, ...] = (
    "the recorded path began through",
    "it then passed through",
    "the delivered answer itself was selected through",
    "also attempted an expression",
    "was not the authority for the delivered answer",
    "the strongest constraint perspective in that pass was",
    "the strongest recorded fault boundary was",
    "the main meaning anchors were",
)
_MODULE_PATH_PATTERN = re.compile(r"\baurora(?:_internal)?\.[a-zA-Z_][a-zA-Z0-9_.]*\b")
_QUALIFIED_CALL_PATTERN = re.compile(
    r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){2,}\b"
)


def is_reflective_route_narration(text: str) -> bool:
    """True when text reads as reflective-introspection route narration --
    module paths, qualified multi-segment function references, or
    render_self_inquiry()'s own phrasing -- regardless of what source tag
    the delivering pipeline attached to it. Legitimate when Aurora is
    genuinely asked how a prior answer was produced (see
    _explicit_self_inquiry_reference); the defect this guards against is
    delivering this shape of text as though it answered an unrelated
    prompt."""
    text = str(text or "")
    if not text:
        return False
    low = text.lower()
    if any(phrase in low for phrase in _REFLECTIVE_NARRATION_PHRASES):
        return True
    if _MODULE_PATH_PATTERN.search(text):
        return True
    if _QUALIFIED_CALL_PATTERN.search(text):
        return True
    return False


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _safe(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return str(value)[:240]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value if not isinstance(value, str) else value[:_MAX_TEXT]
    if isinstance(value, Mapping):
        return {str(k)[:120]: _safe(v, depth + 1) for k, v in list(value.items())[:80]}
    if isinstance(value, (list, tuple, set, deque)):
        return [_safe(v, depth + 1) for v in list(value)[:80]]
    return str(value)[:_MAX_TEXT]


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(_safe(payload), indent=2, ensure_ascii=True), encoding="utf-8")
    os.replace(temp, path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_safe(payload), ensure_ascii=True) + "\n")


def _tokens(text: Any) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9_'-]{1,}", str(text or "").lower())
        if len(token) >= 2
    }


def _signal_roles(parsed: Mapping[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for item in list(parsed.get("pragmatic_signals", []) or []):
        if isinstance(item, (list, tuple)) and item:
            out.add(str(item[0] or "").lower())
        elif isinstance(item, Mapping):
            out.add(str(item.get("role", "") or "").lower())
        elif item:
            out.add(str(item).lower())
    return out


def _merge_unique(*groups: Iterable[Any], limit: int = 16) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for group in groups:
        for raw in list(group or []):
            value = str(raw or "").strip()
            key = value.lower()
            if not value or key in seen:
                continue
            seen.add(key)
            result.append(value)
            if len(result) >= limit:
                return result
    return result


class AuroraReflectiveReaddressing:
    """Instance-owned coordinator for reflective reconsideration."""

    def __init__(
        self,
        *,
        state_dir: str,
        persist: bool = True,
        max_episode_memory: int = 24,
    ) -> None:
        self.state_dir = Path(state_dir).resolve()
        self.persist = bool(persist)
        self.max_episode_memory = max(6, int(max_episode_memory))
        self.history_path = self.state_dir / "reflective_readdressing_history.jsonl"
        self.last_path = self.state_dir / "last_reflective_readdressing.json"
        self._lock = threading.RLock()
        self._systems: Optional[Dict[str, Any]] = None
        self._episodes: Deque[Dict[str, Any]] = deque(maxlen=self.max_episode_memory)
        self._active_context: Dict[str, Any] = {}
        self._requested_context: Dict[str, Any] = {}
        self._last_result: Dict[str, Any] = {}
        # Build 613 (Repair A): the most recent prepare_turn() provenance
        # trace, regardless of whether a mode was granted.
        self._last_decision_trace: Dict[str, Any] = {}
        self._load_last()

    def attach_systems(self, systems: Optional[Dict[str, Any]]) -> None:
        self._systems = systems if isinstance(systems, dict) else None

    # ------------------------------------------------------------------
    # Completed-turn memory
    # ------------------------------------------------------------------

    def capture_turn(
        self,
        *,
        user_input: str,
        delivered_text: str,
        response_source: str = "",
        confidence: float = 0.0,
        systems: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = systems if isinstance(systems, dict) else self._systems or {}
        pipeline = dict(target.get("_last_pipeline_state") or {})
        introspection = dict(target.get("_last_system_introspection_episode") or {})
        diagnosis = dict(target.get("_last_system_diagnosis") or {})
        parsed = dict(
            pipeline.get("parsed")
            or target.get("_pre_parsed_utterance")
            or {}
        )
        _episode_id = str(introspection.get("episode_id") or "").strip()
        with self._lock:
            if not _episode_id or any(
                str(existing.get("episode_id", "") or "") == _episode_id
                for existing in self._episodes
            ):
                _episode_id = f"REF:{uuid.uuid4().hex[:14]}"
        snapshot = {
            "schema_version": _SCHEMA_VERSION,
            "episode_id": _episode_id,
            "timestamp": time.time(),
            "user_input": str(user_input or "")[:_MAX_TEXT],
            "delivered_text": str(delivered_text or "")[:_MAX_TEXT],
            "response_source": str(response_source or ""),
            "confidence": _clip01(confidence),
            "parsed": _safe(parsed),
            "reasoning_state": {
                "intent": str(pipeline.get("intent", "") or ""),
                "dominant_axis": str(pipeline.get("dominant_axis", "") or ""),
                "axis_activation": _safe(pipeline.get("axis_activation") or {}),
                "salient_concepts": _safe(pipeline.get("salient_concepts") or []),
                "meaning_summary": str(pipeline.get("meaning_summary", "") or "")[:_MAX_TEXT],
                "meaning_focus": str(pipeline.get("meaning_focus", "") or "")[:400],
                "goal_stack": _safe(pipeline.get("goal_stack") or []),
                "resolved_referent_topic": str(pipeline.get("resolved_referent_topic", "") or "")[:300],
                "resolved_claim": str(pipeline.get("resolved_claim", "") or "")[:_MAX_TEXT],
                "response_revisions": _safe(pipeline.get("response_revisions") or []),
                "interaction_strategy": str(pipeline.get("interaction_primary_strategy", "") or ""),
            },
            "introspection": {
                "steps": _safe(list(introspection.get("steps", []) or [])[-60:]),
                "final": _safe(introspection.get("final") or {}),
                "diagnosis": _safe(diagnosis),
            },
            # Preserve reflective lineage so a conversational continuation such
            # as "consider the same question again" can return to the matter
            # being examined rather than treating the explanation about that
            # matter as the new subject.
            "reflection": _safe(dict(target.get("_last_reflective_readdressing") or {})),
        }
        with self._lock:
            self._episodes.append(snapshot)
        if isinstance(target, dict):
            target["_last_reflective_reasoning_episode"] = snapshot
        return snapshot

    def latest_episode(self) -> Dict[str, Any]:
        with self._lock:
            if self._episodes:
                return dict(self._episodes[-1])
        systems = self._systems or {}
        return dict(systems.get("_last_reflective_reasoning_episode") or {})

    def _episode_by_id(self, episode_id: str) -> Dict[str, Any]:
        wanted = str(episode_id or "").strip()
        if not wanted:
            return {}
        with self._lock:
            for episode in reversed(self._episodes):
                if str(episode.get("episode_id", "") or "") == wanted:
                    return dict(episode)
        return {}

    def _focal_episode(self, latest: Mapping[str, Any]) -> Dict[str, Any]:
        """Resolve the enduring matter beneath a chain of reflection turns."""
        episode = dict(latest or {})
        seen: Set[str] = set()
        while episode:
            reflection = dict(episode.get("reflection") or {})
            parent_id = str(reflection.get("target_episode_id", "") or "")
            if not parent_id or parent_id in seen:
                break
            seen.add(parent_id)
            parent = self._episode_by_id(parent_id)
            if not parent:
                break
            episode = parent
        return episode

    # ------------------------------------------------------------------
    # Semantic resolution of reflective continuity
    # ------------------------------------------------------------------

    def _source_anatomy_match(
        self,
        parsed: Mapping[str, Any],
        systems: Mapping[str, Any],
    ) -> Tuple[float, List[Dict[str, Any]], List[str]]:
        """Build 613 (Repair C): generic engineering words (_GENERIC_
        ANATOMY_TERMS) are excluded from the candidate terms BEFORE
        matching -- they occur in Aurora's own function names constantly,
        and an ordinary external-world prompt that happens to use the
        word "action" or "state" is not thereby asking about her source
        anatomy. Returns (score, matches, terms_actually_searched) so
        prepare_turn() can record exactly what was searched (Repair A)."""
        bridge = systems.get("system_introspection")
        raw_terms = _merge_unique(
            parsed.get("topic_words", []) or [],
            parsed.get("entities", []) or [],
            [parsed.get("topic", "")],
            limit=6,
        )
        terms = [t for t in raw_terms if t.lower() not in _GENERIC_ANATOMY_TERMS]
        if bridge is None or not hasattr(bridge, "find_functions"):
            return 0.0, [], terms
        matches: List[Dict[str, Any]] = []
        score = 0.0
        for term in terms:
            if len(term) < 3:
                continue
            try:
                found = list(bridge.find_functions(term, limit=2) or [])
            except Exception:
                found = []
            for item in found:
                match = float(item.get("match_score", 0.0) or 0.0)
                # Exact or strong source-anatomy matches carry more weight.
                if match >= 4.0:
                    matches.append(dict(item))
                    score = max(score, min(1.0, match / 10.0))
        return score, matches[:6], terms

    def _continuity_score(
        self,
        user_input: str,
        parsed: Mapping[str, Any],
        previous: Mapping[str, Any],
    ) -> float:
        if not previous:
            return 0.0
        current = _tokens(" ".join([
            str(user_input or ""),
            " ".join(str(x) for x in parsed.get("topic_words", []) or []),
            " ".join(str(x) for x in parsed.get("entities", []) or []),
        ]))
        prior = _tokens(" ".join([
            str(previous.get("user_input", "") or ""),
            str(previous.get("delivered_text", "") or ""),
            " ".join(str(x) for x in (previous.get("reasoning_state") or {}).get("salient_concepts", []) or []),
            str((previous.get("reasoning_state") or {}).get("meaning_focus", "") or ""),
        ]))
        overlap = len(current & prior) / max(1, len(current | prior))
        score = min(0.55, overlap * 2.2)
        if bool(parsed.get("is_callback")):
            score += 0.25
        if bool(parsed.get("is_clarification")):
            score += 0.18
        vague = _tokens(user_input) & {"that", "this", "it", "there", "those", "them"}
        if vague:
            score += 0.14
        return _clip01(score)

    def _observed_path(self, episode: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Return a compact, truthful route through the recorded turn."""
        steps = list((episode.get("introspection") or {}).get("steps", []) or [])
        preferred = {
            "utterance_parsing",
            "reflective_reapplication",
            "proposition_frame_construction",
            "composer_output",
            "semantic_validation",
            "articulation_arbitration",
            "final_articulation",
        }
        path: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str]] = set()
        for raw in steps:
            if not isinstance(raw, Mapping) or raw.get("__truncated__"):
                continue
            stage = str(raw.get("stage", "") or "")
            function_id = str(raw.get("function_id", "") or "")
            if stage not in preferred or not function_id:
                continue
            key = (stage, function_id)
            if key in seen:
                continue
            seen.add(key)
            path.append({
                "stage": stage,
                "function_id": function_id,
                "decision": str(raw.get("decision", "") or ""),
                "reason": str(raw.get("reason", "") or "")[:400],
                "output": _safe(raw.get("output")),
            })
        return path[:8]

    def prepare_turn(
        self,
        user_input: str,
        parsed: Optional[Mapping[str, Any]] = None,
        systems: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolve a turn-local reflective context from normal semantic input.

        No exact command phrase is required.  Resolution uses Aurora's normal
        pragmatic frame, self-reference, source anatomy, referent continuity,
        and prior reasoning state.
        """
        target = systems if isinstance(systems, dict) else self._systems or {}
        if parsed is None:
            try:
                from aurora_internal.aurora_utterance_parser import UtteranceParser
                parsed = UtteranceParser().parse(user_input)
            except Exception:
                parsed = {}
        parsed = dict(parsed or {})
        # Build 613 (Repair B): a unique turn identity for THIS resolution
        # only -- a context built here can only ever be applied to the
        # turn that produced it.
        turn_token = uuid.uuid4().hex
        input_hash = hashlib.sha256(str(user_input or "").encode("utf-8")).hexdigest()[:24]
        latest = self.latest_episode()
        focal = self._focal_episode(latest)
        previous = focal or latest
        requested = dict(self._requested_context or {})
        self._requested_context = {}

        roles = _signal_roles(parsed)
        stance = str(parsed.get("stance", "") or "").lower()
        utterance_type = str(parsed.get("utterance_type", "") or "").lower()
        low = str(user_input or "").lower()
        second_person = bool(re.search(r"\b(you|your|yourself)\b", low))
        first_person = bool(re.search(r"\b(i|my|me|myself)\b", low))
        inquiry = utterance_type == "question" or "inquiry" in roles or str(user_input or "").strip().endswith("?")
        anatomy_score, anatomy_matches, anatomy_terms = self._source_anatomy_match(parsed, target)
        continuity = self._continuity_score(user_input, parsed, previous)
        latest_continuity = self._continuity_score(user_input, parsed, latest)
        # Continuity can be expressed either toward the enduring focal matter
        # or toward the immediately preceding reflective turn.
        continuity = max(continuity, latest_continuity)
        vague_reference = bool(_tokens(user_input) & {"that", "this", "it", "there", "those", "them", "same"})
        first_token = next(iter(re.findall(r"[a-z][a-z0-9_'-]*", low)), "")
        directive = False
        if first_token and not inquiry:
            try:
                from aurora_expression_perception import infer_word_role
                directive = (
                    str(infer_word_role(first_token) or "").lower() in {"action", "verb", "relation"}
                    or first_token in _REFLECTIVE_ACTIONS
                )
            except Exception:
                directive = first_token in _REFLECTIVE_ACTIONS

        # Build 613 (Repair C): a genuine technical self-inquiry needs an
        # EXPLICIT semantic request about Aurora's own reasoning/response
        # formation/internal route/prior answer -- not second-person
        # wording alone ("how confident are you" is ordinary address, not
        # a source-path request), and not a source-anatomy match alone
        # (RCEC's own vocabulary -- "action", "state", "prediction" --
        # collides lexically with Aurora's own generic function-name
        # vocabulary; see _GENERIC_ANATOMY_TERMS).
        explicit_self_reference = _explicit_self_inquiry_reference(user_input)

        relational_form = dict(parsed.get("relational_form") or {})
        relation_content = " ".join(
            str(relational_form.get(key, "") or "")
            for key in ("subject", "relation", "obj", "complement")
        ).strip()
        external_content = {
            token for token in _tokens(relation_content)
            if token not in {
                "you", "your", "yourself", "aurora", "self", "system",
                "process", "path", "reasoning", "response", "answer",
            }
        }
        technical_evidence = anatomy_score >= 0.38
        previous_reflection = dict(previous.get("reflection") or {})
        previous_was_self_inquiry = bool(
            str(previous.get("response_source", "") or "") == "reflective_introspection"
            or str(previous_reflection.get("mode", "") or "") == "self_inquiry"
        )
        previous_diagnosis_type = str(
            dict((previous.get("introspection") or {}).get("diagnosis") or {}).get("problem_type", "") or ""
        )
        previous_response_diagnosis = previous_diagnosis_type in {
            "composer_semantic_rejection",
            "semantic_validation_failure",
            "articulation_meaning_drift",
            "malformed_expression",
            "response_arbitration_failure",
        }
        causal_callback = str(relational_form.get("unknown_role", "") or "") == "cause"
        # A vague callback is not automatically a request for source-code
        # introspection.  Every recorded turn has introspection steps, so using
        # their mere presence caused ordinary questions such as "is that a
        # useful example?" to be hijacked by a technical trace.  Context-only
        # callbacks inherit self-inquiry authority only from an already active
        # self-inquiry lineage -- and (Repair C) still require an explicit
        # self-reference, so a merely hypothetical or weakly-overlapping
        # prompt cannot inherit authority from a stale prior introspection.
        episode_callback = bool(
            vague_reference
            and continuity >= 0.12
            and (previous_was_self_inquiry or (causal_callback and previous_response_diagnosis))
        )
        explicit_callback = bool(
            parsed.get("is_callback")
            and continuity >= 0.22
            and previous_was_self_inquiry
        )
        self_inquiry = bool(
            previous
            and inquiry
            and explicit_self_reference
            and (technical_evidence or explicit_callback or episode_callback)
            and not (external_content and not technical_evidence and not vague_reference)
            and not bool(parsed.get("is_opinion"))
        )

        relational_relation = str(relational_form.get("relation", "") or "").lower()
        confirmation_only = bool(
            previous
            and not inquiry
            and bool(parsed.get("is_callback"))
            and bool(parsed.get("is_clarification"))
            and not bool(parsed.get("negated"))
            and relational_relation in {"is", "be", "mean", "meant"}
            and not list(parsed.get("topic_words") or [])
        )
        # Build 613 (Repair C): an external-world prompt with a concrete
        # new subject (RCEC's vessels/conduits/sensors, or any other
        # ordinary noun) must stay centered on that subject rather than
        # being pulled toward a stale introspection episode merely because
        # it is phrased as a challenge/hypothesis/continuation and the
        # focal episode happens to have been reflective.
        _stale_reflective_pull = bool(
            external_content and previous_was_self_inquiry and not explicit_self_reference
        )
        challenge = bool(
            previous
            and not confirmation_only
            and not _stale_reflective_pull
            and (
                stance in {"challenging", "clarifying"}
                or bool(parsed.get("is_clarification"))
                or (bool(parsed.get("negated")) and continuity >= 0.22)
                or ("contrast" in roles and continuity >= 0.28)
            )
        )
        perspective_shift = bool(
            previous
            and not _stale_reflective_pull
            and (
                bool(parsed.get("is_hypothetical"))
                or stance in {"speculative", "tentative"}
                or "hypothesis" in roles
                or (
                    directive
                    and (
                        vague_reference
                        or continuity >= 0.06
                        or "similarity" in roles
                    )
                )
            )
            and continuity >= 0.05
        )
        reflective_continuation = bool(
            previous
            and not self_inquiry
            and not confirmation_only
            and not _stale_reflective_pull
            and continuity >= 0.62
            and (inquiry or first_person or second_person)
        )

        mode = ""
        reason = ""
        if requested:
            mode = str(requested.get("mode", "readdress") or "readdress")
            reason = str(requested.get("reason", "internally requested reconsideration") or "")
        elif self_inquiry:
            mode = "self_inquiry"
            reason = "the inquiry is directed at Aurora's own recent processing and resolves to a live reasoning episode"
        elif challenge:
            mode = "readdress"
            reason = "new clarification or contradiction bears directly on the previous reasoning episode"
        elif perspective_shift:
            mode = "perspective_shift"
            reason = "a new hypothetical or perspective is continuous with the previous reasoning episode"
        elif reflective_continuation:
            mode = "reflective_continuation"
            reason = "the current inquiry remains semantically continuous with the prior reasoning state"

        # Build 613 (Repair A): turn-local provenance, captured regardless
        # of whether a mode was granted -- a denial is as diagnostically
        # important as a grant. Never gates behavior; read-only record.
        decision_trace = {
            "input_hash": input_hash,
            "turn_token": turn_token,
            "selected_mode": mode,
            "latest_episode_id": str(latest.get("episode_id", "") or ""),
            "focal_episode_id": str((focal or previous).get("episode_id", "") or ""),
            "target_episode_id": str(previous.get("episode_id", "") or "") if mode else "",
            "source_anatomy_terms": list(anatomy_terms),
            "source_anatomy_matches": _safe(anatomy_matches),
            "source_anatomy_score": round(anatomy_score, 4),
            "continuity_score": round(continuity, 4),
            "vague_reference": vague_reference,
            "explicit_callback": explicit_callback,
            "episode_callback": episode_callback,
            "previous_was_self_inquiry": previous_was_self_inquiry,
            "explicit_self_reference": explicit_self_reference,
            "external_content_terms": sorted(external_content),
            "predicates": {
                "self_inquiry": {
                    "previous": bool(previous), "inquiry": inquiry,
                    "explicit_self_reference": explicit_self_reference,
                    "technical_evidence": technical_evidence,
                    "explicit_callback": explicit_callback,
                    "episode_callback": episode_callback,
                    "is_opinion": bool(parsed.get("is_opinion")),
                    "granted": self_inquiry,
                },
                "challenge": {
                    "previous": bool(previous), "confirmation_only": confirmation_only,
                    "stale_reflective_pull": _stale_reflective_pull, "granted": challenge,
                },
                "perspective_shift": {
                    "previous": bool(previous), "stale_reflective_pull": _stale_reflective_pull,
                    "continuity": continuity, "granted": perspective_shift,
                },
                "reflective_continuation": {
                    "previous": bool(previous), "self_inquiry": self_inquiry,
                    "confirmation_only": confirmation_only,
                    "stale_reflective_pull": _stale_reflective_pull,
                    "continuity": continuity, "granted": reflective_continuation,
                },
            },
        }
        self._last_decision_trace = decision_trace
        if isinstance(target, dict):
            target["_reflective_readdressing_trace"] = decision_trace

        if not mode:
            self._active_context = {}
            if isinstance(target, dict):
                target.pop("_pending_reflective_readdressing", None)
            return {}

        previous_reasoning = dict(previous.get("reasoning_state") or {})
        diagnosis = dict((previous.get("introspection") or {}).get("diagnosis") or {})
        likely = dict(diagnosis.get("likely_boundary") or {})
        diagnosis_type = str(diagnosis.get("problem_type", "") or "")
        response_diagnosis = diagnosis_type in {
            "composer_semantic_rejection",
            "semantic_validation_failure",
            "articulation_meaning_drift",
            "malformed_expression",
            "response_arbitration_failure",
        }
        fault_seeking = bool(
            _tokens(user_input)
            & {"wrong", "problem", "error", "failure", "failed", "fail", "bug", "malformed", "issue", "broke", "broken"}
        )
        observed_path = self._observed_path(previous)
        recontextualized = (
            f"Prior matter: {str(previous.get('user_input', '') or '').strip()}\n"
            f"Prior understanding expressed: {str(previous.get('delivered_text', '') or '').strip()}\n"
            f"New evidence or perspective: {str(user_input or '').strip()}"
        ).strip()
        context = {
            "schema_version": _SCHEMA_VERSION,
            "readdress_id": f"RAD:{uuid.uuid4().hex[:14]}",
            "created_at": time.time(),
            # Build 613 (Repair B): binds this context to THIS turn only.
            "turn_token": turn_token,
            "input_hash": input_hash,
            "mode": mode,
            "reason": reason,
            "target_episode_id": str(previous.get("episode_id", "") or ""),
            "latest_episode_id": str(latest.get("episode_id", "") or ""),
            "focal_episode_id": str((focal or previous).get("episode_id", "") or ""),
            "original_input": str(previous.get("user_input", "") or "")[:_MAX_TEXT],
            "original_response": str(previous.get("delivered_text", "") or "")[:_MAX_TEXT],
            "original_source": str(previous.get("response_source", "") or ""),
            "original_confidence": _clip01(previous.get("confidence", 0.0)),
            "original_reasoning": _safe(previous_reasoning),
            "original_parse": _safe(previous.get("parsed") or {}),
            "new_input": str(user_input or "")[:_MAX_TEXT],
            "new_parse": _safe(parsed),
            "recontextualized_text": recontextualized[:_MAX_TEXT],
            "continuity": round(continuity, 4),
            "self_reference": second_person,
            "source_anatomy_score": round(anatomy_score, 4),
            "source_anatomy_matches": _safe(anatomy_matches),
            "fault_seeking": fault_seeking,
            "diagnosis_type": diagnosis_type,
            "diagnosis_relevant_to_response": response_diagnosis,
            "observed_path": _safe(observed_path),
            "inspection_focus": {
                "function_id": str(likely.get("function_id", "") or ""),
                "file": str(likely.get("file", "") or ""),
                "line": int(likely.get("line", 0) or 0),
                "reason": str(likely.get("reason", "") or diagnosis.get("summary", "") or "")[:_MAX_TEXT],
                "confidence": _clip01(diagnosis.get("confidence", 0.0)),
            },
            "requested": _safe(requested),
            "status": "active",
        }
        self._active_context = context
        if isinstance(target, dict):
            target["_pending_reflective_readdressing"] = context
            target["_active_reflective_readdressing"] = context
        return context

    # ------------------------------------------------------------------
    # Grounded self-explanation and axis readdressing
    # ------------------------------------------------------------------

    def render_self_inquiry(self, context: Optional[Mapping[str, Any]] = None) -> str:
        ctx = dict(context or self._active_context or {})
        if not ctx:
            return "I do not have a recent reasoning episode to examine."
        focus = dict(ctx.get("inspection_focus") or {})
        original_reasoning = dict(ctx.get("original_reasoning") or {})
        source = str(ctx.get("original_source", "") or "the response pipeline")
        axis = str(original_reasoning.get("dominant_axis", "") or "")
        salient = [str(x) for x in list(original_reasoning.get("salient_concepts", []) or []) if str(x).strip()]
        path = list(ctx.get("observed_path", []) or [])
        parts: List[str] = []

        # Describe the recorded route first.  A runtime fault may coexist with
        # a successful response without being the mechanism that produced it.
        route_names: List[str] = []
        for item in path:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("function_id", "") or "")
            stage = str(item.get("stage", "") or "")
            if name and stage != "composer_output" and name not in route_names:
                route_names.append(name)
        if route_names:
            parts.append(f"The recorded path began through {route_names[0]}.")
            if len(route_names) > 1:
                parts.append(f"It then passed through {', '.join(route_names[1:4])}.")

        composer_attempts = [
            item for item in path
            if isinstance(item, Mapping) and str(item.get("stage", "") or "") == "composer_output"
        ]
        parts.append(f"The delivered answer itself was selected through {source}.")
        if composer_attempts and source != "composer_unified":
            parts.append("SentenceComposer also attempted an expression, but it was not the authority for the delivered answer.")
        if axis:
            parts.append(f"The strongest constraint perspective in that pass was {axis}.")
        if salient:
            parts.append(f"The main meaning anchors were {', '.join(salient[:4])}.")

        if bool(ctx.get("fault_seeking")) or bool(ctx.get("diagnosis_relevant_to_response")):
            if focus.get("function_id"):
                location = ""
                if focus.get("file"):
                    location = f" in {focus['file']}"
                    if focus.get("line"):
                        location += f":{focus['line']}"
                parts.append(f"The strongest recorded fault boundary was {focus['function_id']}{location}.")
                if focus.get("reason"):
                    parts.append(str(focus["reason"]).rstrip(".") + ".")
            else:
                parts.append("I did not record a confirmed function-level failure in that episode.")
        return " ".join(part.strip() for part in parts if part.strip())

    def axis_readdress_vector(
        self,
        base_projection: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, float]:
        """Blend the current perspective with the previous episode.

        Readdressing preserves continuity while allowing the new turn to pull
        the field elsewhere.  It does not permanently alter the field balancer.
        """
        ctx = dict(context or self._active_context or {})
        original = dict((ctx.get("original_reasoning") or {}).get("axis_activation") or {})
        mode = str(ctx.get("mode", "") or "")
        current = {axis: _clip01(base_projection.get(axis, 0.2), 0.2) for axis in _AXES}
        if not original:
            return current
        # Self inquiry needs continuity with the original state.  Challenge and
        # perspective shifts need more room for the new input to reorganize it.
        old_weight = {
            "self_inquiry": 0.55,
            "reflective_continuation": 0.42,
            "readdress": 0.30,
            "perspective_shift": 0.22,
        }.get(mode, 0.30)
        merged = {
            axis: max(0.0, current[axis] * (1.0 - old_weight) + _clip01(original.get(axis, 0.2), 0.2) * old_weight)
            for axis in _AXES
        }
        # Reconsideration itself is an agency/boundary act: keep these signals
        # present without forcing them dominant.
        if mode in {"readdress", "perspective_shift"}:
            merged["A"] += 0.08
            merged["B"] += 0.06
        total = sum(merged.values()) or 1.0
        return {axis: round(merged[axis] / total, 4) for axis in _AXES}

    # ------------------------------------------------------------------
    # Comparison, retention evidence, autonomous access
    # ------------------------------------------------------------------

    def finish_turn(
        self,
        *,
        delivered_text: str,
        response_source: str = "",
        confidence: float = 0.0,
        systems: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target = systems if isinstance(systems, dict) else self._systems or {}
        ctx = dict(self._active_context or target.get("_active_reflective_readdressing") or {})
        if not ctx:
            return {}
        current_pipeline = dict(target.get("_last_pipeline_state") or {})
        old_axes = dict((ctx.get("original_reasoning") or {}).get("axis_activation") or {})
        new_axes = dict(current_pipeline.get("axis_activation") or {})
        axis_delta = {
            axis: round(float(new_axes.get(axis, 0.0) or 0.0) - float(old_axes.get(axis, 0.0) or 0.0), 4)
            for axis in _AXES
        }
        original_text = str(ctx.get("original_response", "") or "").strip()
        new_text = str(delivered_text or "").strip()
        changed = bool(new_text and new_text != original_text)
        result = {
            "schema_version": _SCHEMA_VERSION,
            "readdress_id": str(ctx.get("readdress_id", "") or ""),
            "timestamp": time.time(),
            "mode": str(ctx.get("mode", "") or ""),
            "target_episode_id": str(ctx.get("target_episode_id", "") or ""),
            "reason": str(ctx.get("reason", "") or ""),
            "new_evidence": str(ctx.get("new_input", "") or "")[:_MAX_TEXT],
            "original": {
                "input": str(ctx.get("original_input", "") or "")[:_MAX_TEXT],
                "response": original_text[:_MAX_TEXT],
                "source": str(ctx.get("original_source", "") or ""),
                "confidence": _clip01(ctx.get("original_confidence", 0.0)),
                "dominant_axis": str((ctx.get("original_reasoning") or {}).get("dominant_axis", "") or ""),
            },
            "reconsidered": {
                "response": new_text[:_MAX_TEXT],
                "source": str(response_source or ""),
                "confidence": _clip01(confidence),
                "dominant_axis": str(current_pipeline.get("dominant_axis", "") or ""),
            },
            "axis_delta": axis_delta,
            "changed": changed,
            "status": "trial_complete",
            "promotion_authority": "existing_developmental_systems",
        }
        self._last_result = result
        if self.persist:
            try:
                _append_jsonl(self.history_path, result)
                _atomic_json(self.last_path, result)
            except Exception as exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="reflective_readdressing:persist",
                    exc=exc,
                    context={"function": "finish_turn", "source_file": __file__},
                )
        if isinstance(target, dict):
            target["_last_reflective_readdressing"] = result
            target.pop("_active_reflective_readdressing", None)
            target.pop("_pending_reflective_readdressing", None)
            self._publish(target, result)
        self._active_context = {}
        return result

    def _publish(self, systems: Dict[str, Any], result: Dict[str, Any]) -> None:
        compact = {
            "readdress_id": result.get("readdress_id", ""),
            "mode": result.get("mode", ""),
            "changed": bool(result.get("changed", False)),
            "axis_delta": dict(result.get("axis_delta") or {}),
            "original_source": (result.get("original") or {}).get("source", ""),
            "reconsidered_source": (result.get("reconsidered") or {}).get("source", ""),
            "reason": result.get("reason", ""),
        }
        contract = systems.get("understanding_contract")
        if contract is not None and hasattr(contract, "attach_pending_contributors"):
            try:
                contract.attach_pending_contributors({"reflective_readdressing": compact})
            except Exception as exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="reflective_readdressing:publish_understanding",
                    exc=exc,
                    context={"function": "_publish", "source_file": __file__},
                )
        observer = systems.get("quasiarch_observer")
        if observer is not None and hasattr(observer, "record_observation"):
            try:
                observer.record_observation(
                    target="aurora.reflective_readdressing",
                    data=compact,
                    source="REFLECTIVE_READDRESSING",
                )
            except Exception as exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="reflective_readdressing:publish_qao",
                    exc=exc,
                    context={"function": "_publish", "source_file": __file__},
                )

    def request_readdress(
        self,
        *,
        reason: str,
        mode: str = "readdress",
        focus: str = "",
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Allow Aurora's own systems to request reconsideration next turn."""
        self._requested_context = {
            "mode": str(mode or "readdress"),
            "reason": str(reason or "internal tension requested reconsideration")[:_MAX_TEXT],
            "focus": str(focus or "")[:400],
            "evidence": _safe(dict(evidence or {})),
            "requested_at": time.time(),
        }
        return dict(self._requested_context)

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "episodes_in_memory": len(self._episodes),
            "active_context": _safe(self._active_context),
            "pending_internal_request": _safe(self._requested_context),
            "last_result": _safe(self._last_result),
            "last_decision_trace": _safe(self._last_decision_trace),
            "state_dir": str(self.state_dir),
        }

    def last_decision_trace(self) -> Dict[str, Any]:
        """Build 613 (Repair A): the most recent prepare_turn() provenance
        trace, whether or not a mode was granted."""
        return dict(self._last_decision_trace)

    def _load_last(self) -> None:
        try:
            if self.last_path.exists():
                data = json.loads(self.last_path.read_text(encoding="utf-8") or "{}")
                if isinstance(data, dict):
                    self._last_result = data
        except Exception:
            self._last_result = {}


__all__ = [
    "AuroraReflectiveReaddressing",
    "is_reflective_route_narration",
]
