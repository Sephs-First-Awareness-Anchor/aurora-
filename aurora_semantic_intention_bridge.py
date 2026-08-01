# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aurora_expression_perception import infer_word_role


EXTRACTION_NOISE = {
    'active', 'processes', 'operating', 'triggered', 'dominant',
    'pressure', 'partial', 'background', 'context', 'with',
    'from', 'this', 'that', 'what', 'which', 'some', 'have',
    'been', 'will', 'axis', 'tick', 'process', 'braid',
    'current', 'continuous', 'forming', 'lane', 'thread',
    # Braid bookkeeping is useful to the field but is not a semantic
    # target for a spoken response.
    'sedi', 'ambient', 'recalled', 'linguistic', 'predictive',
    'identity', 'predicates', 'memory', 'presence',
    'constraint', 'unresolved', 'tension', 'conflict', 'conflicts',
    'session', 'xaxis', 'comprehension',
}

AXIS_TONE_MAP: Dict[str, str] = {
    'X': 'precise',
    'T': 'reflective',
    'N': 'determined',
    'B': 'careful',
    'A': 'curious',
}

LANE_FROM_AXIS: Dict[str, str] = {
    'A': 'meaning',
    'N': 'meaning',
    'T': 'inquiry',
    'B': 'communication',
    'X': 'communication',
}

VALID_BIAS_TAGS = {'identity', 'memory', 'curiosity', 'constraint', 'predictive', 'sensory'}


@dataclass
class SemanticIntention:
    content_keywords: List[str] = field(default_factory=list)
    axis_tone_map: Dict[str, str] = field(default_factory=dict)
    semantic_lane: str = 'communication'
    template_bias_tags: List[str] = field(default_factory=list)
    unresolved_weight: float = 0.0
    confidence: float = 0.5


class SemanticIntentionBridge:
    def extract(
        self,
        thought_state: Any,
        expression_guidance: Any = None,
        systems: Any = None,
    ) -> SemanticIntention:
        # 1. Content keyword extraction — Aurora's own meaning words.
        # The live TurnUnderstandingState is preferred when present.  Its
        # parsed/salient terms are the result of Aurora's upward pass; the
        # raw linguistic braid context is still useful, but comes second so
        # a greeting or direct address cannot crowd out the actual topic.
        source_strings: List[str] = []
        live_state = systems.get('_active_turn_state') if isinstance(systems, dict) else None
        live_terms: List[str] = []
        if live_state is not None:
            try:
                parsed = dict(getattr(live_state, 'parsed', {}) or {})
                live_terms.extend(list(parsed.get('topic_words', []) or []))
                live_terms.extend(list(parsed.get('entities', []) or []))
                live_terms.extend(list(getattr(live_state, 'salient_concepts', []) or []))
                topic = str(parsed.get('topic', '') or '').strip()
                if topic:
                    live_terms.append(topic)
            except Exception:
                live_terms = []
        # The parser has already removed direct address and function words
        # from these terms.  Treat them as the authority for which words in
        # the received utterance are meaningful; otherwise the diagnostic
        # ThoughtState prose below can reintroduce "Hello Aurora" as if it
        # were a response topic.
        live_semantic_words = {
            re.sub(r'[^\w]', '', str(term or '')).lower()
            for term in live_terms
            if str(term or '').strip()
        }
        raw_turn = " ".join(str(getattr(live_state, 'raw_text', '') or '').lower().split())
        raw_turn_words = set(re.findall(r"[a-z]+", raw_turn))
        # A parsed live topic is already the most faithful external meaning
        # signal.  The current ThoughtState serializes its internal status
        # as prose (axis readings, unresolved conflicts, etc.); it may inform
        # pressure and tone, but must not dilute the content anchors that are
        # handed to language selection.  The older diagnostic fallback stays
        # available only when Aurora truly has no parsed semantic material.
        if not live_semantic_words:
            unified = getattr(thought_state, 'unified_interpretation', None)
            if unified:
                source_strings.append(str(unified))
            self_app = getattr(thought_state, 'self_application', None)
            if self_app:
                source_strings.append(str(self_app))
        dominant_thread = getattr(thought_state, 'dominant_thread', None) or []
        if not live_semantic_words:
            for ctx in dominant_thread:
                what = getattr(ctx, 'what_it_is_operating_on', None)
                context_text = str(what or '')
                if raw_turn and " ".join(context_text.lower().split()) == raw_turn:
                    # The received utterance is already represented by
                    # ``live_terms`` above.  Re-adding it here would restore a
                    # direct address as if it were Aurora's own topic.
                    continue
                if what:
                    source_strings.append(str(what))

        keywords: List[str] = []
        seen: set = set()

        def add_keyword(raw: Any) -> bool:
            word = re.sub(r'[^\w]', '', str(raw or '')).lower()
            if (len(word) < 3 or word in seen
                    or "_" in word):
                return False
            if not any(ch.isalpha() for ch in word):
                return False
            # Internal bookkeeping should never become a spoken target,
            # unless the user actually made that word a parsed topic.
            if word in EXTRACTION_NOISE and word not in live_semantic_words:
                return False
            # Raw turn words that the parser did not retain are address or
            # syntax, not content.  This keeps the diagnostics' echo of the
            # full user turn from bypassing the parser's direct-address pass.
            if live_semantic_words and word in raw_turn_words and word not in live_semantic_words:
                return False
            # Axis telemetry frequently appears as x050/t050/etc. in the
            # dominant thread.  It is a coordinate, never a spoken concept.
            if re.fullmatch(r'[xtnba]\d+', word):
                return False
            role = infer_word_role(word)
            if role not in ('verb', 'noun', 'adjective', 'adverb'):
                return False
            keywords.append(word)
            seen.add(word)
            return True

        for raw in live_terms:
            add_keyword(raw)
            if len(keywords) >= 12:
                break

        for src in source_strings:
            tokens = re.split(r'[\s|:;]+', src)
            for raw in tokens:
                add_keyword(raw)
                if len(keywords) >= 12:
                    break
            if len(keywords) >= 12:
                break

        # 2. Axis tone derivation
        axis_fp = getattr(thought_state, 'axis_fingerprint', None) or []
        dominant_axis = axis_fp[0] if axis_fp else ''
        tone = AXIS_TONE_MAP.get(dominant_axis, 'neutral')
        axis_tone = {dominant_axis: tone} if dominant_axis else {}

        # 3. Semantic lane
        if expression_guidance is not None and hasattr(expression_guidance, 'lane_lean'):
            lane = expression_guidance.lane_lean or LANE_FROM_AXIS.get(dominant_axis, 'communication')
        else:
            lane = LANE_FROM_AXIS.get(dominant_axis, 'communication')

        # 4. Template bias tags from dominant_thread process_types
        bias_tags: List[str] = []
        seen_tags: set = set()
        for ctx in dominant_thread:
            pt = getattr(ctx, 'process_type', None)
            if pt and pt in VALID_BIAS_TAGS and pt not in seen_tags:
                bias_tags.append(pt)
                seen_tags.add(pt)
                if len(bias_tags) >= 3:
                    break

        # 5. Unresolved weight
        unresolved = getattr(thought_state, 'unresolved', None) or []
        unresolved_weight = min(1.0, len(unresolved) / 5.0)

        # 6. Confidence
        confidence = float(getattr(thought_state, 'confidence', 0.5) or 0.5)

        return SemanticIntention(
            content_keywords=keywords,
            axis_tone_map=axis_tone,
            semantic_lane=lane,
            template_bias_tags=bias_tags,
            unresolved_weight=unresolved_weight,
            confidence=confidence,
        )

    def apply(self, intention: SemanticIntention, composer: Any) -> None:
        composer.set_context(intention.content_keywords)
        composer._semantic_intention = intention

    def get_axis_tone(self, thought_state: Any) -> str:
        axis_fp = getattr(thought_state, 'axis_fingerprint', None) or []
        dominant_axis = axis_fp[0] if axis_fp else ''
        return AXIS_TONE_MAP.get(dominant_axis, 'neutral')
