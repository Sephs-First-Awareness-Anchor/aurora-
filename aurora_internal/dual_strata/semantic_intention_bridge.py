# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/semantic_intention_bridge.py
============================================================
SemanticIntentionBridge — MTSL Phase 5 (2026-07-13), spec section 7.
Consumes semantic_mode + response_bias (CERSVerdict, Phase 4) to select
a response strategy from the directive's fixed vocabulary, BEFORE
wording -- this module never generates or edits text itself.

NO ARTICULATION CHANGE YET (same posture as Phase 3's gate): strategy
selection is genuinely computed and logged every call, but whether it
is APPLIED to real behavior is gated by the same manual, evidence-cited
authority_stage as Phase 4 (default MTSL_AUTHORITY_STAGE=1, record
only). At stage 1, IntentionDecision.applied is always False; a future
phase's live wiring is what would actually branch aurora_articulation.py
or an upstream composer on the selected strategy.

Register-rule helpers (spec 22, first-pass -- the external spec's full
register table wasn't available to this implementation): loops get
feedback-oriented language framing, gradients are never described as
loops, and raw X/T/N/B/A axis letters are stripped from generated text
unless the caller explicitly marks a technical context. These are
concrete, real, testable rules -- not the full spec 22 table, but not a
stub either.

Strategy shifts (this call's strategy differs from the last one this
bridge instance computed) are logged to the SAME
aurora_state/mtsl_shadow_comparison.jsonl the Phase 3 coordinator
writes to, per the directive's "all strategy shifts logged against the
Phase 3 shadow comparison."
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .cers_regulator import CERSVerdict, MTSL_AUTHORITY_STAGE
from .subsurface_state import clip01

SCHEMA_VERSION = 1
SHADOW_COMPARISON_FILENAME = "mtsl_shadow_comparison.jsonl"

STRATEGY_VOCABULARY = (
    "explain", "clarify", "contrast", "reflect", "act", "abstain", "observe",
)

# Strategy-selection thresholds (first-pass; not spec-pinned).
ACT_MIN_CONFIDENCE = 0.75
ACT_MAX_BIAS = 0.3
HIGH_BIAS_ESCALATION = 0.6

# X/T/N/B never collide with an ordinary standalone capitalized English
# word, so those are always safe to strip unconditionally. "A" is the one
# axis letter that IS a common English word (the indefinite article) --
# blanket-stripping it would visibly mangle normal sentences ("A cat sat
# on a mat" -> " cat sat on a mat"). Rather than fabricate a false sense
# of coverage, "A" is only stripped when it appears in unambiguous
# technical adjacency (next to the word "axis", or slash/comma/hyphen-
# separated in a list alongside another axis letter) -- a bare mid-
# sentence "A" is deliberately left alone since it cannot be reliably
# told apart from the article without real NLP. Documented scope limit,
# not a stub.
# Matched as ONE atomic unit, before any single-letter stripping happens --
# splitting "X/T/N/B/A" letter-by-letter would destroy the very adjacency
# each later letter's match depends on (once "B" is gone, "A" no longer
# looks list-adjacent). A run of 2+ axis letters separated by /, comma, or
# hyphen (each optionally followed by a space) is unambiguously technical
# notation, so "A" is safe to include here even though it's not safe to
# strip on its own elsewhere.
_AXIS_LIST_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[XTNBA][/,-]\s*){1,4}[XTNBA](?![A-Za-z0-9_])")
_AXIS_XTNB_RE = re.compile(r"(?<![A-Za-z0-9_])([XTNB])(?![A-Za-z0-9_])")
_AXIS_A_NEAR_AXIS_WORD_RE = re.compile(r"(?<![A-Za-z0-9_])A[\s-]*(?=axis\b)|(?<=\baxis)[\s-]*A(?![A-Za-z0-9_])", re.IGNORECASE)


def select_strategy(verdict: CERSVerdict) -> "tuple[str, float]":
    """Pure function: (strategy, strategy_confidence). strategy is always
    one of STRATEGY_VOCABULARY. Never raises -- a verdict with no
    semantic_mode (topology_context was never supplied to cers_converge())
    degrades to ("observe", 0.0), same "skip, never fake" posture as the
    rest of MTSL."""
    mode = verdict.semantic_mode
    bias = clip01(verdict.response_bias)
    confidence = clip01(verdict.variant_confidence)
    hesitation = bool(verdict.semantic_hesitation) or bool(verdict.semantic_hesitation_proposed)

    if mode is None:
        return "observe", 0.0

    if mode == "ambiguous":
        strategy = "contrast" if confidence > 0.0 else "clarify"
    elif mode == "undetermined":
        strategy = "abstain" if hesitation else "observe"
    elif mode == "directional":
        strategy = "explain"
    elif mode == "organized":
        strategy = "act" if (confidence >= ACT_MIN_CONFIDENCE and bias <= ACT_MAX_BIAS) else "reflect"
    else:
        strategy = "observe"

    # Bias can only escalate toward a more clarification-seeking strategy;
    # it never overrides an already-cautious "abstain".
    if bias >= HIGH_BIAS_ESCALATION and strategy not in ("clarify", "contrast", "abstain"):
        strategy = "clarify"

    strategy_confidence = round(clip01(confidence * (1.0 - 0.3 * bias) - (0.2 if hesitation else 0.0)), 4)
    return strategy, strategy_confidence


def register_hint(regime: str) -> str:
    """Spec 22: 'loops get feedback language, gradients never described
    as loops.' A caller building the actual sentence should honor this
    hint's framing rather than describe a gradient/mixed regime with
    loop/cycle vocabulary."""
    if regime == "circulating":
        return "feedback_loop_language"
    if regime in ("gradient", "mixed"):
        return "directional_language"
    return "neutral_language"


def sanitize_axis_leakage(text: str, *, technical_context: bool = False) -> str:
    """Spec 22: 'raw X/T/N/B/A hidden unless technical context.' Strips
    bare, standalone axis-letter tokens (not part of a larger word, not an
    article like the pronoun "A" mid-sentence -- word-boundary matched
    against the exact five capital letters only) from generated text
    unless the caller explicitly marks this as technical/debug output.
    Never touches lowercase text or letters embedded in larger tokens."""
    if technical_context or not text:
        return text
    # List pattern first, while adjacency is still intact -- see
    # _AXIS_LIST_RE's comment. Then the "A near axis" phrase pattern.
    # Bare X/T/N/B singles last (safe regardless of order).
    out = _AXIS_LIST_RE.sub("", text)
    out = _AXIS_A_NEAR_AXIS_WORD_RE.sub("", out)
    out = _AXIS_XTNB_RE.sub("", out)
    while "  " in out:
        out = out.replace("  ", " ")
    return out.strip()


@dataclass(frozen=True)
class IntentionDecision:
    schema_version: int
    turn_id: str
    timestamp: float
    strategy: str
    strategy_confidence: float
    applied: bool
    shifted: bool
    previous_strategy: Optional[str]
    semantic_mode: Optional[str]
    response_bias: float
    authority_stage: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "strategy": self.strategy,
            "strategy_confidence": self.strategy_confidence,
            "applied": self.applied,
            "shifted": self.shifted,
            "previous_strategy": self.previous_strategy,
            "semantic_mode": self.semantic_mode,
            "response_bias": round(self.response_bias, 4),
            "authority_stage": self.authority_stage,
        }


class SemanticIntentionBridge:
    """Stateful only in the narrow sense of remembering the last selected
    strategy (to detect a shift worth logging) -- carries no other
    memory, no authority, and never touches text itself."""

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else None
        self._shadow_log_path = (
            os.path.join(self._state_dir, SHADOW_COMPARISON_FILENAME) if self._state_dir else None
        )
        self.last_strategy: Optional[str] = None

    def consume(
        self,
        verdict: CERSVerdict,
        *,
        turn_id: str,
        timestamp: Optional[float] = None,
        authority_stage: int = MTSL_AUTHORITY_STAGE,
    ) -> IntentionDecision:
        ts = timestamp if timestamp is not None else time.time()
        strategy, confidence = select_strategy(verdict)
        shifted = self.last_strategy is not None and strategy != self.last_strategy
        decision = IntentionDecision(
            schema_version=SCHEMA_VERSION,
            turn_id=turn_id,
            timestamp=ts,
            strategy=strategy,
            strategy_confidence=confidence,
            applied=(authority_stage >= 2),
            shifted=shifted,
            previous_strategy=self.last_strategy,
            semantic_mode=verdict.semantic_mode,
            response_bias=verdict.response_bias,
            authority_stage=authority_stage,
        )
        if shifted:
            self._log_shift(decision)
        self.last_strategy = strategy
        return decision

    def _log_shift(self, decision: IntentionDecision) -> None:
        if not self._shadow_log_path:
            return
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            entry = {"strategy_shift": decision.to_dict()}
            with open(self._shadow_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
        except Exception:
            pass
