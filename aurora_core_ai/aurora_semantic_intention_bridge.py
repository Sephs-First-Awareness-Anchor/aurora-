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
        # 1. Content keyword extraction — Aurora's own meaning words
        source_strings: List[str] = []
        unified = getattr(thought_state, 'unified_interpretation', None)
        if unified:
            source_strings.append(str(unified))
        self_app = getattr(thought_state, 'self_application', None)
        if self_app:
            source_strings.append(str(self_app))
        dominant_thread = getattr(thought_state, 'dominant_thread', None) or []
        for ctx in dominant_thread:
            what = getattr(ctx, 'what_it_is_operating_on', None)
            if what:
                source_strings.append(str(what))

        keywords: List[str] = []
        seen: set = set()
        for src in source_strings:
            tokens = re.split(r'[\s|:;]+', src)
            for raw in tokens:
                word = re.sub(r'[^\w]', '', raw).lower()
                if len(word) < 4:
                    continue
                if word in EXTRACTION_NOISE:
                    continue
                if word in seen:
                    continue
                role = infer_word_role(word)
                if role not in ('verb', 'noun', 'adjective', 'adverb'):
                    continue
                keywords.append(word)
                seen.add(word)
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
