# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


LANE_SIGNALS: Dict[str, List[str]] = {
    "meaning":       ["mean", "understand", "because", "reason", "purpose",
                      "sense", "feel", "believe", "think", "know"],
    "inquiry":       ["?", "wonder", "question", "curious", "why", "what",
                      "how", "when", "where", "whether", "if"],
    "communication": ["say", "tell", "share", "express", "here", "this",
                      "clear", "certain", "true", "real"],
}


@dataclass
class StructureFitnessResult:
    fidelity_score: float = 0.5
    keyword_coverage: float = 0.0
    scaffolding_match: float = 0.5
    lane_alignment: float = 0.5
    combined_fitness: float = 0.5
    details: Dict[str, Any] = field(default_factory=dict)


class LanguageStructureFitness:
    def score(
        self,
        expression_text: str,
        intention: Any,
        base_fitness: float,
        composer: Any = None,
    ) -> StructureFitnessResult:
        try:
            from aurora_semantic_intention_bridge import SemanticIntention
        except Exception:
            SemanticIntention = None

        if intention is None:
            return StructureFitnessResult(
                fidelity_score=0.5,
                combined_fitness=base_fitness,
            )

        expression_lower = expression_text.lower()

        # 1. Keyword coverage
        content_keywords = list(getattr(intention, 'content_keywords', []) or [])
        if content_keywords:
            hits = sum(1 for kw in content_keywords if kw in expression_lower)
            keyword_coverage = hits / len(content_keywords)
        else:
            keyword_coverage = 0.0

        # 2. Scaffolding match
        scaffolding_match = 0.5
        if composer is not None:
            try:
                last_used = getattr(composer, '_last_templates_used', []) or []
                # _last_templates_used is List[Tuple[tone, pattern]]
                # Need to look up scaffolding_level from the pool
                levels = []
                for tone_key, pattern in last_used:
                    tone_pool = composer.pool.get(tone_key, [])
                    for t in tone_pool:
                        if t.get('pattern') == pattern:
                            levels.append(t.get('scaffolding_level', 0))
                            break
                if levels:
                    avg_level = sum(levels) / len(levels)
                    confidence = float(getattr(intention, 'confidence', 0.5) or 0.5)
                    if confidence >= 0.7:
                        expected = 2
                    elif confidence >= 0.5:
                        expected = 1
                    else:
                        expected = 0
                    scaffolding_match = 1.0 if avg_level >= expected else (avg_level / expected if expected > 0 else 1.0)
            except Exception:
                scaffolding_match = 0.5

        # 3. Lane alignment
        semantic_lane = str(getattr(intention, 'semantic_lane', 'communication') or 'communication')
        signals = LANE_SIGNALS.get(semantic_lane, [])
        lane_alignment = 1.0 if any(sig in expression_lower for sig in signals) else 0.3

        # 4. Unresolved inquiry bonus
        unresolved_weight = float(getattr(intention, 'unresolved_weight', 0.0) or 0.0)
        inquiry_signals = LANE_SIGNALS["inquiry"]
        has_inquiry = any(sig in expression_lower for sig in inquiry_signals)
        inquiry_bonus = 0.10 if (unresolved_weight > 0.3 and has_inquiry) else 0.0

        # 5. Fidelity score
        fidelity_score = (
            keyword_coverage  * 0.40 +
            scaffolding_match * 0.25 +
            lane_alignment    * 0.20 +
            (inquiry_bonus / 0.15) * 0.15
        )
        fidelity_score = max(0.0, min(1.0, fidelity_score))

        # 6. Combined fitness
        combined_fitness = max(0.0, min(1.0, base_fitness * 0.65 + fidelity_score * 0.35))

        return StructureFitnessResult(
            fidelity_score=fidelity_score,
            keyword_coverage=keyword_coverage,
            scaffolding_match=scaffolding_match,
            lane_alignment=lane_alignment,
            combined_fitness=combined_fitness,
            details={
                'keyword_coverage': keyword_coverage,
                'scaffolding_match': scaffolding_match,
                'lane_alignment': lane_alignment,
                'inquiry_bonus': inquiry_bonus,
                'semantic_lane': semantic_lane,
                'base_fitness': base_fitness,
            },
        )
