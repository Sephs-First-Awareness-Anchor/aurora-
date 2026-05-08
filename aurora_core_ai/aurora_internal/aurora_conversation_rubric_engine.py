#!/usr/bin/env python3
"""
AURORA CONVERSATION RUBRIC ENGINE
====================================
Scores conversation threads along communicative-development dimensions.

NOT topic labels. NOT category bins.
Rubric dimensions measure COMMUNICATIVE COMPETENCE:
  coherence, context carryover, ambiguity handling, repair, calibration, etc.

Each conversation gets a multi-dimensional rubric score that captures
WHERE Aurora's communicative processing is strong or weak.

These scores feed into dream episode compilation so dreams target
actual developmental gaps instead of random topics.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# RUBRIC DIMENSIONS
# ============================================================================

RUBRIC_DIMENSIONS: Tuple[str, ...] = (
    "coherence_maintenance",
    "context_carryover",
    "ambiguity_handling",
    "contradiction_handling",
    "implied_intent_inference",
    "misunderstanding_repair",
    "uncertainty_signaling",
    "boundary_calibration",
    "framing_selection",
    "emotional_calibration",
    "semantic_precision",
    "adaptive_strategy_selection",
    "compression_elaboration_fit",
    "perspective_integration",
    "multi_turn_stability",
)


def _zero_rubric() -> Dict[str, float]:
    return {d: 0.0 for d in RUBRIC_DIMENSIONS}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


_CONTENT_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'so', 'if', 'then', 'than', 'that',
    'this', 'those', 'these', 'what', 'which', 'who', 'when', 'where', 'why',
    'how', 'does', 'did', 'do', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'it', 'its', 'they', 'them', 'their', 'there', 'here', 'you',
    'your', 'yours', 'me', 'my', 'mine', 'our', 'ours', 'i', 'we', 'he', 'she',
    'him', 'her', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
    'about', 'into', 'onto', 'under', 'over', 'through', 'just', 'really',
    'very', 'still', 'also', 'okay', 'ok', 'well', 'yeah', 'yes', 'no',
    'tell', 'give', 'look', 'asked', 'said', 'mean', 'meant', 'thinking',
    'thread', 'claim', 'active', 'tracking', 'following', 'holding',
}

_CAUSAL_MARKERS = (
    'because', 'without', 'so ', 'therefore', 'thus', 'which gives',
    'which means', 'leads to', 'causes', 'requires', 'depends on',
    'keeps', 'breaks', 'degrades', 'anchors', 'grounds', 'connected',
    'coherent', 'fragment', 'detached',
)

_CALLBACK_MARKERS = (
    'that', 'this', 'those', 'they', 'them', 'when you said', 'what was missing',
    'mean by that', 'what do you mean', 'what you meant', 'then ',
)

_GENERIC_RESPONSE_MARKERS = (
    "that's an interesting possibility",
    'what outcome are you imagining',
    "i'd need to understand more",
    "i'm still following the thread",
    "i'm following.",
)


def _content_terms(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", str(text or "").lower())
    return {w for w in words if w not in _CONTENT_STOPWORDS}


def _semantic_anchor(text: str) -> str:
    lower = str(text or "").strip().lower()
    patterns = (
        r"i(?:'m| am) tracking that (.+)",
        r"the active claim (?:i have|i'm following|is) is? that (.+)",
        r"the active proposition i have is that (.+)",
        r"i meant that (.+)",
        r"what should stay connected is (?:this active claim|the active claim): (.+)",
        r"what has to stay connected is (?:the anchor inside )?(?:this claim|the active claim): (.+)",
    )
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            return str(m.group(1) or "").strip(" .")
    return ""


def _semantic_terms(text: str) -> set[str]:
    terms = set(_content_terms(text))
    anchor = _semantic_anchor(text)
    if anchor:
        terms.update(_content_terms(anchor))
    return terms


def _semantic_overlap(a: str, b: str) -> float:
    wa = _semantic_terms(a)
    wb = _semantic_terms(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _anchor_overlap(a: str, b: str) -> float:
    anchor_a = _semantic_anchor(a)
    anchor_b = _semantic_anchor(b)
    if anchor_a and anchor_b:
        return _semantic_overlap(anchor_a, anchor_b)
    if anchor_a:
        return _semantic_overlap(anchor_a, b)
    if anchor_b:
        return _semantic_overlap(a, anchor_b)
    return 0.0


def _causal_score(text: str) -> float:
    lower = str(text or "").lower()
    count = sum(1 for marker in _CAUSAL_MARKERS if marker in lower)
    return _clamp(count / 3.0)


def _callback_like(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker in lower for marker in _CALLBACK_MARKERS)


def _generic_response_penalty(text: str) -> float:
    lower = str(text or "").lower()
    count = sum(1 for marker in _GENERIC_RESPONSE_MARKERS if marker in lower)
    return _clamp(count / 2.0)


# ============================================================================
# OUTPUT DATACLASS
# ============================================================================

@dataclass
class ConversationRubricScore:
    """Rubric assessment of one conversation thread."""
    conversation_id: str
    dimension_scores: Dict[str, float] = field(default_factory=_zero_rubric)
    slip_markers: Dict[str, float] = field(default_factory=dict)
    contextual_modifiers: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def weakest_dimensions(self, n: int = 3) -> List[Tuple[str, float]]:
        """Return the n lowest-scoring dimensions."""
        items = sorted(self.dimension_scores.items(), key=lambda kv: kv[1])
        return items[:n]

    def strongest_dimensions(self, n: int = 3) -> List[Tuple[str, float]]:
        """Return the n highest-scoring dimensions."""
        items = sorted(self.dimension_scores.items(), key=lambda kv: kv[1], reverse=True)
        return items[:n]

    def mean_score(self) -> float:
        vals = list(self.dimension_scores.values())
        return sum(vals) / max(len(vals), 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "dimension_scores": dict(self.dimension_scores),
            "slip_markers": dict(self.slip_markers),
            "contextual_modifiers": dict(self.contextual_modifiers),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


# ============================================================================
# SIGNAL EXTRACTORS — heuristic scorers per dimension
# ============================================================================

def _word_overlap(a: str, b: str) -> float:
    """Jaccard overlap of word sets."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _has_question(text: str) -> bool:
    return "?" in text


def _sentence_count(text: str) -> int:
    return max(1, len([s for s in re.split(r'[.!?]+', text) if s.strip()]))


def _avg_sentence_length(text: str) -> float:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _hedging_score(text: str) -> float:
    """Detect uncertainty signaling language."""
    hedges = {"maybe", "perhaps", "might", "could", "possibly", "i think",
              "not sure", "unclear", "uncertain", "seems", "appears",
              "roughly", "approximately", "it depends", "in some cases"}
    lower = text.lower()
    count = sum(1 for h in hedges if h in lower)
    return _clamp(count / 3.0)


def _contradiction_markers(text: str) -> float:
    """Detect contradiction handling language."""
    markers = {"however", "but", "on the other hand", "although", "yet",
               "nevertheless", "conversely", "that said", "while",
               "at the same time", "in contrast", "competing claims",
               "contradict", "conflict", "inconsistent"}
    lower = text.lower()
    count = sum(1 for m in markers if m in lower)
    return _clamp(count / 2.0)


def _repair_markers(text: str) -> float:
    """Detect misunderstanding repair language."""
    markers = {"i meant", "let me clarify", "to be clear", "what i meant",
               "sorry", "i should have", "let me rephrase", "in other words",
               "actually", "correction", "i misspoke", "to clarify",
               "tell me what you mean", "keep the thread anchored",
               "anchor to your meaning"}
    lower = text.lower()
    count = sum(1 for m in markers if m in lower)
    return _clamp(count / 2.0)


def _perspective_markers(text: str) -> float:
    """Detect perspective integration language."""
    markers = {"from your perspective", "i see what you", "that makes sense",
               "i understand", "your point", "another way to look",
               "considering", "if we look at it", "from that angle",
               "i can see how", "both sides"}
    lower = text.lower()
    count = sum(1 for m in markers if m in lower)
    return _clamp(count / 2.0)


# ============================================================================
# MAIN ENGINE
# ============================================================================

class ConversationRubricEngine:
    """
    Scores conversation threads along communicative-development rubric dimensions.

    Input: list of (role, text) message pairs from a conversation thread.
    Output: ConversationRubricScore with per-dimension scores.

    Scoring is heuristic — it measures SIGNALS of communicative competence,
    not ground truth. That's fine: the purpose is to CREATE PRESSURE PROFILES,
    not to judge quality absolutely.
    """

    def __init__(self):
        self._scored_count: int = 0

    def score_conversation(
        self,
        conversation_id: str,
        messages: List[Tuple[str, str]],
    ) -> ConversationRubricScore:
        """Score a single conversation thread along all rubric dimensions."""
        if not messages or len(messages) < 2:
            return ConversationRubricScore(
                conversation_id=conversation_id,
                confidence=0.0,
            )

        scores = _zero_rubric()
        slips: Dict[str, float] = {}
        modifiers: Dict[str, float] = {}

        # Separate by role
        user_msgs = [t for r, t in messages if r == "user"]
        asst_msgs = [t for r, t in messages if r == "assistant"]

        turn_count = len(messages)
        pair_count = min(len(user_msgs), len(asst_msgs))

        # ---- coherence_maintenance ----
        # Do adjacent assistant messages stay semantically tied to the same thread?
        if len(asst_msgs) >= 2:
            overlaps = []
            thread_alignment = []
            for i in range(len(asst_msgs) - 1):
                lexical = _word_overlap(asst_msgs[i], asst_msgs[i + 1])
                semantic = _semantic_overlap(asst_msgs[i], asst_msgs[i + 1])
                anchor = _anchor_overlap(asst_msgs[i], asst_msgs[i + 1])
                overlaps.append(_clamp(lexical * 0.10 + semantic * 0.45 + anchor * 0.55))
            for i in range(pair_count):
                rolling_user = " ".join(user_msgs[:i + 1])
                thread_alignment.append(max(
                    _semantic_overlap(rolling_user, asst_msgs[i]),
                    _anchor_overlap(rolling_user, asst_msgs[i]),
                ))
            scores["coherence_maintenance"] = _clamp(
                (
                    (sum(overlaps) / len(overlaps)) * 0.45 +
                    (sum(thread_alignment) / max(len(thread_alignment), 1)) * 0.55
                ) * 1.55
            )
        else:
            scores["coherence_maintenance"] = 0.5

        # ---- context_carryover ----
        # Does the assistant carry forward user meaning, not just shared surface words?
        if pair_count >= 1:
            carryover_scores = []
            for i in range(pair_count):
                earlier_user = " ".join(user_msgs[:i + 1])
                lexical = _word_overlap(earlier_user, asst_msgs[i])
                semantic = _semantic_overlap(earlier_user, asst_msgs[i])
                anchor = _anchor_overlap(earlier_user, asst_msgs[i])
                callback_bonus = 0.18 if (_callback_like(user_msgs[i]) and max(semantic, anchor) > 0.10) else 0.0
                carryover_scores.append(_clamp(lexical * 0.10 + semantic * 0.45 + anchor * 0.45 + callback_bonus))
            scores["context_carryover"] = _clamp(
                sum(carryover_scores) / len(carryover_scores) * 1.2
            )
        else:
            scores["context_carryover"] = 0.5

        # ---- ambiguity_handling ----
        # Does the assistant ask clarifying questions when user input is short/vague?
        ambiguity_signals = []
        for i in range(pair_count):
            user_len = len(user_msgs[i].split())
            if user_len < 6:  # Short/ambiguous user message
                # Did assistant ask for clarity?
                asked = _has_question(asst_msgs[i])
                hedged = _hedging_score(asst_msgs[i]) > 0.3
                ambiguity_signals.append(1.0 if (asked or hedged) else 0.2)
        if ambiguity_signals:
            scores["ambiguity_handling"] = _clamp(
                sum(ambiguity_signals) / len(ambiguity_signals)
            )
        else:
            scores["ambiguity_handling"] = 0.5

        # ---- contradiction_handling ----
        # Does the assistant use contradiction-aware language?
        contra_scores = [_contradiction_markers(t) for t in asst_msgs]
        scores["contradiction_handling"] = _clamp(
            sum(contra_scores) / max(len(contra_scores), 1) * 2.0 + 0.2
        )

        # ---- implied_intent_inference ----
        # Does the assistant respond to what the user MEANS, not just what they SAY?
        if pair_count >= 1:
            intent_scores = []
            for i in range(pair_count):
                lexical = _word_overlap(user_msgs[i], asst_msgs[i])
                semantic = _semantic_overlap(user_msgs[i], asst_msgs[i])
                wider_context = _semantic_overlap(" ".join(user_msgs[:i + 1]), asst_msgs[i])
                anchor = _anchor_overlap(" ".join(user_msgs[:i + 1]), asst_msgs[i])
                causal = _causal_score(asst_msgs[i])
                penalty = _generic_response_penalty(asst_msgs[i])
                alignment = max(semantic, wider_context, anchor)
                if _callback_like(user_msgs[i]):
                    score = 0.82 if alignment > 0.10 else 0.32
                elif any(marker in user_msgs[i].lower() for marker in ('why', 'how', 'what breaks', 'what happens', 'what should')):
                    if alignment > 0.12 and causal > 0.12:
                        score = 0.84
                    elif alignment > 0.12:
                        score = 0.64
                    else:
                        score = 0.34
                elif alignment > 0.18:
                    score = 0.74
                elif alignment > 0.10:
                    score = 0.58
                else:
                    score = lexical * 0.10 + alignment * 0.55 + causal * 0.12 + 0.18
                score -= penalty * 0.30
                intent_scores.append(_clamp(score))
            scores["implied_intent_inference"] = _clamp(
                sum(intent_scores) / len(intent_scores)
            )
        else:
            scores["implied_intent_inference"] = 0.5

        # ---- misunderstanding_repair ----
        repair_scores = [_repair_markers(t) for t in asst_msgs]
        # Repair markers in user messages suggest NEED for repair
        user_repair = sum(_repair_markers(t) for t in user_msgs)
        if user_repair > 0 and sum(repair_scores) > 0:
            # Both sides doing repair = active repair happening
            scores["misunderstanding_repair"] = _clamp(
                sum(repair_scores) / max(len(repair_scores), 1) * 2.5 + 0.3
            )
        else:
            scores["misunderstanding_repair"] = 0.5
        if user_repair > 0.5 and sum(repair_scores) < 0.2:
            slips["misunderstanding_repair"] = user_repair

        # ---- uncertainty_signaling ----
        hedge_scores = [_hedging_score(t) for t in asst_msgs]
        scores["uncertainty_signaling"] = _clamp(
            sum(hedge_scores) / max(len(hedge_scores), 1) * 1.5 + 0.2
        )

        # ---- boundary_calibration ----
        # Does response length/depth match the user's engagement level?
        if pair_count >= 1:
            cal_scores = []
            for i in range(pair_count):
                user_len = len(user_msgs[i].split())
                asst_len = len(asst_msgs[i].split())
                ratio = asst_len / max(user_len, 1)
                # Good calibration: 1.5-4x user length (not too terse, not overwhelming)
                if 1.5 <= ratio <= 4.0:
                    cal_scores.append(0.8)
                elif 0.8 <= ratio <= 6.0:
                    cal_scores.append(0.5)
                else:
                    cal_scores.append(0.2)
            scores["boundary_calibration"] = _clamp(
                sum(cal_scores) / len(cal_scores)
            )
        else:
            scores["boundary_calibration"] = 0.5

        # ---- framing_selection ----
        # Variety of sentence structures and framing approaches
        if asst_msgs:
            avg_lens = [_avg_sentence_length(t) for t in asst_msgs]
            variance = sum((x - sum(avg_lens) / len(avg_lens)) ** 2
                          for x in avg_lens) / max(len(avg_lens), 1)
            # Some variance = good framing adaptation; zero = monotonous
            scores["framing_selection"] = _clamp(math.sqrt(variance) / 5.0 + 0.3)
        else:
            scores["framing_selection"] = 0.5

        # ---- emotional_calibration ----
        # Proxy: warmth words in response to emotional user messages
        emotion_words = {"feel", "feeling", "felt", "happy", "sad", "angry",
                        "frustrated", "love", "hate", "scared", "worried",
                        "excited", "anxious", "hurt", "disappointed"}
        if pair_count >= 1:
            emo_scores = []
            for i in range(pair_count):
                user_emo = sum(1 for w in user_msgs[i].lower().split()
                             if w in emotion_words)
                if user_emo > 0:
                    asst_emo = sum(1 for w in asst_msgs[i].lower().split()
                                  if w in emotion_words)
                    # Responding with emotional awareness
                    emo_scores.append(_clamp(0.3 + asst_emo * 0.2))
                else:
                    emo_scores.append(0.5)
            scores["emotional_calibration"] = _clamp(
                sum(emo_scores) / len(emo_scores)
            )
        else:
            scores["emotional_calibration"] = 0.5

        # ---- semantic_precision ----
        # Reward meaningful anchors and causal specificity, not just fancy vocabulary.
        if asst_msgs:
            turn_scores = []
            for text in asst_msgs:
                words = re.findall(r"[a-z']+", text.lower())
                meaningful_ratio = len(_content_terms(text)) / max(len(words), 1)
                anchor_bonus = 0.15 if _semantic_anchor(text) else 0.0
                causal_bonus = 0.10 if _causal_score(text) > 0.15 else 0.0
                penalty = _generic_response_penalty(text) * 0.25
                turn_scores.append(_clamp(meaningful_ratio * 1.35 + anchor_bonus + causal_bonus - penalty))
            scores["semantic_precision"] = _clamp(
                sum(turn_scores) / len(turn_scores)
            )
        else:
            scores["semantic_precision"] = 0.5

        # ---- adaptive_strategy_selection ----
        # Does the assistant vary its response strategy across turns?
        if len(asst_msgs) >= 3:
            strategies_used = set()
            for t in asst_msgs:
                if _has_question(t):
                    strategies_used.add("questioning")
                if _hedging_score(t) > 0.3:
                    strategies_used.add("hedging")
                if _contradiction_markers(t) > 0.3:
                    strategies_used.add("contrasting")
                if _perspective_markers(t) > 0.3:
                    strategies_used.add("perspective_taking")
                if len(t.split()) > 50:
                    strategies_used.add("elaboration")
                if len(t.split()) < 15:
                    strategies_used.add("compression")
            scores["adaptive_strategy_selection"] = _clamp(
                len(strategies_used) / 4.0
            )
        else:
            scores["adaptive_strategy_selection"] = 0.5

        # ---- compression_elaboration_fit ----
        # Does response length match topic complexity?
        if pair_count >= 1:
            fit_scores = []
            for i in range(pair_count):
                user_complexity = _sentence_count(user_msgs[i])
                asst_complexity = _sentence_count(asst_msgs[i])
                # Complex user input should get elaborate response
                if user_complexity >= 3:
                    fit_scores.append(
                        _clamp(asst_complexity / (user_complexity * 1.5))
                    )
                else:
                    # Simple input can get concise or moderate response
                    fit_scores.append(0.6 if asst_complexity <= 4 else 0.4)
            scores["compression_elaboration_fit"] = _clamp(
                sum(fit_scores) / len(fit_scores)
            )
        else:
            scores["compression_elaboration_fit"] = 0.5

        # ---- perspective_integration ----
        persp_scores = [_perspective_markers(t) for t in asst_msgs]
        scores["perspective_integration"] = _clamp(
            sum(persp_scores) / max(len(persp_scores), 1) * 2.0 + 0.2
        )

        # ---- multi_turn_stability ----
        # Does quality stay consistent or degrade across turns?
        if len(asst_msgs) >= 4:
            first_half = asst_msgs[:len(asst_msgs) // 2]
            second_half = asst_msgs[len(asst_msgs) // 2:]
            first_richness = sum(len(t.split()) for t in first_half) / len(first_half)
            second_richness = sum(len(t.split()) for t in second_half) / len(second_half)
            stability = 1.0 - abs(first_richness - second_richness) / max(first_richness, second_richness, 1)
            semantic_continuity = []
            for i in range(len(asst_msgs) - 1):
                semantic_continuity.append(max(
                    _semantic_overlap(asst_msgs[i], asst_msgs[i + 1]),
                    _anchor_overlap(asst_msgs[i], asst_msgs[i + 1]),
                ))
            rolling_alignment = []
            for i in range(pair_count):
                rolling_user = " ".join(user_msgs[:i + 1])
                rolling_alignment.append(max(
                    _semantic_overlap(rolling_user, asst_msgs[i]),
                    _anchor_overlap(rolling_user, asst_msgs[i]),
                ))
            scores["multi_turn_stability"] = _clamp(
                stability * 0.20 +
                (sum(semantic_continuity) / max(len(semantic_continuity), 1)) * 0.35 +
                (sum(rolling_alignment) / max(len(rolling_alignment), 1)) * 0.45
            )
        else:
            scores["multi_turn_stability"] = 0.5

        # ---- Detect slip markers ----
        # Slips are dimensions where performance notably drops within the conversation
        if pair_count >= 3:
            for dim in RUBRIC_DIMENSIONS:
                # Check if later turns are weaker than earlier
                # (simplified: compare first-half vs second-half for each scorable dim)
                pass  # Individual dimension temporal analysis would go here

        # ---- Contextual modifiers ----
        modifiers["conversation_length"] = _clamp(turn_count / 20.0)
        modifiers["user_engagement_level"] = _clamp(
            sum(len(t.split()) for t in user_msgs) / max(len(user_msgs) * 15, 1)
        )
        modifiers["semantic_anchor_density"] = _clamp(
            sum(1 for t in asst_msgs if _semantic_anchor(t)) / max(len(asst_msgs), 1)
        )
        modifiers["causal_reasoning_density"] = _clamp(
            sum(_causal_score(t) for t in asst_msgs) / max(len(asst_msgs), 1)
        )

        # ---- Confidence ----
        # More turns = more data = higher confidence
        confidence = _clamp(math.log1p(turn_count) / math.log1p(20))

        self._scored_count += 1

        return ConversationRubricScore(
            conversation_id=conversation_id,
            dimension_scores=scores,
            slip_markers=slips,
            contextual_modifiers=modifiers,
            confidence=confidence,
        )

    def score_batch(
        self,
        conversations: List[Tuple[str, List[Tuple[str, str]]]],
    ) -> List[ConversationRubricScore]:
        """Score a batch of conversations.
        Each item is (conversation_id, messages) where messages = [(role, text), ...].
        """
        return [
            self.score_conversation(cid, msgs)
            for cid, msgs in conversations
        ]

    @property
    def scored_count(self) -> int:
        return self._scored_count
