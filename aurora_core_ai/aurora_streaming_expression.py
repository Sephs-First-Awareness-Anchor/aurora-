# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_streaming_expression.py

Streaming expression layer — lightweight braid re-tap at expression checkpoints.

THE PROBLEM THIS SOLVES:
    Without this, a response reads from a single frozen ThoughtState tap.
    The first sentence and the last sentence share the same thought snapshot.
    The braid evolves during expression but expression cannot feel it.
    Output fires before thought finishes — because thought was never designed
    to keep running during output.

WHAT THIS DOES:
    At natural expression checkpoints (sentence/clause/paragraph breaks),
    re-tap the braid, compute a lightweight BraidNudge, and return updated
    ExpressionGuidance to shift emphasis for what comes next.

    Full ThoughtIntegrationSpace is NOT re-run — too expensive mid-response.
    The anchor ThoughtState remains authoritative throughout the response.
    Nudges are bounded, additive, and emotion-safe.

    The firewall fires AGAIN at each checkpoint — emotional content cannot
    enter expression even through the nudge path. Double protection.

LIFECYCLE PER RESPONSE:
    guidance = layer.begin(thought_state)        → anchor, get initial guidance
    ...expression begins...
    guidance = layer.checkpoint(text_so_far)     → re-tap at natural break, maybe nudge
    guidance = layer.checkpoint(text_so_far)     → again at next break
    ...response ends...
    layer.complete(full_text, thought_state)     → close loop, feed back to braid

NUDGE CAPS:
    Per-checkpoint max axis shift:  0.12  (12% per axis per checkpoint)
    Cumulative max axis shift:      0.25  (25% total drift from anchor per response)
    These caps ensure the anchor thought remains the primary driver.
    Nudges shift emphasis — they never override.

RE-ENTRY LOOP ALIGNMENT:
    This module operates in the EXPRESSION phase of:
    STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING
    layer.complete() feeds the RE-ENTRY signal back via braid.feed_expression_back().
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_thought_formation import (
    ThoughtBraid,
    ThoughtState,
    ThoughtStreamSlice,
    EmotionFirewall,
    ProcessContext,
    get_braid,
    get_firewall,
)


# ---------------------------------------------------------------------------
# ExpressionGuidance — what the expression generator receives per checkpoint
# ---------------------------------------------------------------------------

@dataclass
class ExpressionGuidance:
    """
    Actionable expression guidance produced at each checkpoint.

    The expression generator reads this and adjusts emphasis for what comes next.
    axis_emphasis values are deltas from neutral (0.0 = no shift from anchor).
    Positive values = lean into this axis in expression.
    Negative values = de-emphasize this axis — it has resolved or receded.

    This is guidance, not instruction. The anchor ThoughtState remains
    authoritative. This just says: the braid has shifted, here is the direction.
    """
    axis_emphasis: Dict[str, float] = field(
        default_factory=lambda: {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    )
    lane_lean: str = "communication"     # "communication" | "meaning" | "inquiry"
    carry_topics: List[str] = field(default_factory=list)   # keep these present
    release_topics: List[str] = field(default_factory=list) # these have resolved
    nudge_strength: float = 0.0          # 0.0 = anchor only, 1.0 = full braid shift
    checkpoint_index: int = 0
    braid_tick: int = 0
    is_initial: bool = False             # True for begin() return value
    anchor_axes: List[str] = field(default_factory=list)  # axes of anchor ThoughtState

    def dominant_shift_axis(self) -> str:
        """Which axis is the braid currently pulling hardest on."""
        if not self.axis_emphasis:
            return "A"
        return max(self.axis_emphasis.items(), key=lambda x: abs(x[1]), default=("A", 0.0))[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axis_emphasis": {k: round(v, 4) for k, v in self.axis_emphasis.items()},
            "lane_lean": self.lane_lean,
            "carry_topics": list(self.carry_topics),
            "release_topics": list(self.release_topics),
            "nudge_strength": round(self.nudge_strength, 4),
            "checkpoint_index": self.checkpoint_index,
            "braid_tick": self.braid_tick,
            "is_initial": self.is_initial,
            "anchor_axes": list(self.anchor_axes),
        }


# ---------------------------------------------------------------------------
# BraidNudge — the computed delta between fresh braid tap and expression anchor
# ---------------------------------------------------------------------------

@dataclass
class BraidNudge:
    """
    Lightweight delta between a fresh braid tap and the current expression anchor.

    Not a full re-integration. Just a directional shift signal.
    Computed by comparing fresh braid axis signals to anchor ThoughtState.
    Emotional content is always stripped before this is computed (firewall).

    axis_delta: positive = braid pulling harder on this axis than anchor was.
                negative = braid has de-emphasized this axis since anchor.
    """
    axis_delta: Dict[str, float] = field(
        default_factory=lambda: {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    )
    new_topics: List[str] = field(default_factory=list)     # topics entering braid since anchor
    resolving_topics: List[str] = field(default_factory=list)  # topics settling in braid
    predictive_lean: str = ""     # what braid predictive stream is pointing toward
    raw_strength: float = 0.0     # magnitude of delta before capping
    braid_tick: int = 0
    emotion_filtered: bool = True  # always True — firewall always fires


# ---------------------------------------------------------------------------
# CheckpointDetector — detects natural expression breaks in streaming text
# ---------------------------------------------------------------------------

# Sentence boundary patterns
_SENTENCE_ENDINGS = re.compile(r'[.!?][\s\n]')
# Paragraph boundary
_PARAGRAPH_BREAK = re.compile(r'\n\n')
# Minimum characters between checkpoints to prevent over-sampling
_MIN_CHARS_BETWEEN_CHECKPOINTS = 10
# Fallback: force checkpoint every N chars if no natural break found
_MAX_CHARS_WITHOUT_CHECKPOINT = 300


class CheckpointDetector:
    """
    Detects natural expression breaks suitable for braid re-tapping.

    Operates on cumulative expression text with a last-seen position cursor.
    Works with both streaming (token-by-token) and batch (sentence-at-a-time) contexts.

    Priority order:
        1. Paragraph break  (\n\n)
        2. Sentence ending  (. ! ? followed by whitespace)
        3. Fallback         (every _MAX_CHARS_WITHOUT_CHECKPOINT chars)

    Minimum _MIN_CHARS_BETWEEN_CHECKPOINTS since last checkpoint always enforced
    to prevent checkpoint flood on short sentences.
    """

    def __init__(self):
        self._last_checkpoint_pos: int = 0

    def is_at_checkpoint(self, text: str, last_checkpoint_pos: int) -> bool:
        """
        Return True if text contains a valid checkpoint since last_checkpoint_pos.
        Caller is responsible for updating last_checkpoint_pos on True return.
        """
        search_from = last_checkpoint_pos
        new_text = text[search_from:]

        if len(new_text) < _MIN_CHARS_BETWEEN_CHECKPOINTS:
            return False

        # Paragraph break — highest priority
        if _PARAGRAPH_BREAK.search(new_text):
            return True

        # Sentence ending
        if _SENTENCE_ENDINGS.search(new_text):
            return True

        # Fallback — force checkpoint after _MAX_CHARS_WITHOUT_CHECKPOINT
        if len(new_text) >= _MAX_CHARS_WITHOUT_CHECKPOINT:
            return True

        return False

    def find_checkpoint_position(self, text: str, last_checkpoint_pos: int) -> int:
        """
        Find the position of the first valid checkpoint in text since last_checkpoint_pos.
        Returns the position or len(text) if no natural break found.
        """
        search_from = last_checkpoint_pos
        new_text = text[search_from:]

        # Paragraph break
        m = _PARAGRAPH_BREAK.search(new_text)
        if m:
            return search_from + m.end()

        # Sentence ending
        m = _SENTENCE_ENDINGS.search(new_text)
        if m:
            return search_from + m.end()

        # Fallback
        return len(text)

    def reset(self) -> None:
        self._last_checkpoint_pos = 0


# ---------------------------------------------------------------------------
# StreamingExpressionLayer — main class
# ---------------------------------------------------------------------------

_MAX_NUDGE_PER_CHECKPOINT = 0.12   # max axis shift per checkpoint
_MAX_CUMULATIVE_NUDGE = 0.25       # max total axis drift from anchor per response
_MIN_NUDGE_STRENGTH = 0.05         # below this, nudge is not worth reporting


class StreamingExpressionLayer:
    """
    Manages lightweight braid re-tapping at expression checkpoints.

    The anchor ThoughtState is set at begin() and remains authoritative.
    Checkpoints re-tap the braid, compute bounded BraidNudges, and return
    ExpressionGuidance that shifts emphasis for the next expression segment.

    The firewall fires at every checkpoint — emotional signal cannot enter
    expression through the nudge path. This is double protection:
        1. Firewall fires during initial ThoughtIntegrationSpace integration
        2. Firewall fires again at every checkpoint nudge computation

    Thread safety: single-response use. Not designed for concurrent access.
    """

    def __init__(
        self,
        braid: Optional[ThoughtBraid] = None,
        firewall: Optional[EmotionFirewall] = None,
    ):
        self._braid = braid or get_braid()
        self._firewall = firewall or get_firewall()
        self._anchor: Optional[ThoughtState] = None
        self._checkpoint_count: int = 0
        self._last_checkpoint_pos: int = 0
        self._cumulative_delta: Dict[str, float] = {ax: 0.0 for ax in "XTNBA"}
        self._detector = CheckpointDetector()
        self._anchor_topic_set: set = set()
        self._response_start_time: float = 0.0

    # ---- Public API --------------------------------------------------------

    def begin(self, thought_state: ThoughtState) -> ExpressionGuidance:
        """
        Anchor to the current ThoughtState.
        Call at the start of response generation.
        Returns initial ExpressionGuidance derived from anchor alone (no nudge yet).
        """
        self._anchor = thought_state
        self._checkpoint_count = 0
        self._last_checkpoint_pos = 0
        self._cumulative_delta = {ax: 0.0 for ax in "XTNBA"}
        self._detector.reset()
        self._response_start_time = time.time()

        # Build anchor topic set for carry/release computation
        self._anchor_topic_set = {
            ctx.what_it_is_operating_on
            for ctx in thought_state.dominant_thread
            if ctx.what_it_is_operating_on
        }

        return self._guidance_from_anchor()

    def checkpoint(self, text_so_far: str) -> Optional[ExpressionGuidance]:
        """
        Call at natural expression breaks with the text generated so far.

        Re-taps the braid and computes a nudge if:
            - A natural checkpoint is detected in text_so_far
            - The nudge magnitude exceeds _MIN_NUDGE_STRENGTH
            - The cumulative cap has not been reached

        Returns ExpressionGuidance or None if no checkpoint is triggered.

        The expression generator should use the returned guidance to shift
        emphasis for the next segment. If None is returned, continue with
        the last guidance.
        """
        if self._anchor is None:
            return None

        if not self._detector.is_at_checkpoint(text_so_far, self._last_checkpoint_pos):
            return None

        self._last_checkpoint_pos = self._detector.find_checkpoint_position(
            text_so_far, self._last_checkpoint_pos
        )
        self._checkpoint_count += 1

        # Re-tap braid — non-consuming
        fresh_slice = self._braid.tap()

        # Compute nudge (firewall fires inside _compute_nudge)
        nudge = self._compute_nudge(fresh_slice)

        # Skip if nudge is negligible
        if nudge.raw_strength < _MIN_NUDGE_STRENGTH:
            return self._guidance_from_anchor(
                checkpoint_index=self._checkpoint_count,
                braid_tick=fresh_slice.braid_tick,
            )

        # Apply cumulative cap
        capped_delta = self._apply_cumulative_cap(nudge.axis_delta)

        # Update cumulative tracker
        for ax, val in capped_delta.items():
            self._cumulative_delta[ax] = self._cumulative_delta.get(ax, 0.0) + val

        return self._build_guidance(nudge, capped_delta, fresh_slice.braid_tick)

    def complete(self, full_text: str, thought_state: ThoughtState) -> None:
        """
        Call when response generation completes.

        Feeds the full expression back into the braid via feed_expression_back(),
        closing the thought ↔ expression ↔ thought loop.

        This is the RE-ENTRY signal in:
        STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING

        The braid's predictive stream is reshaped by what was just expressed,
        influencing the next thought cross-section.
        """
        self._braid.feed_expression_back(full_text, thought_state)
        # Reset for next response
        self._anchor = None
        self._checkpoint_count = 0
        self._last_checkpoint_pos = 0
        self._cumulative_delta = {ax: 0.0 for ax in "XTNBA"}

    def current_checkpoint_count(self) -> int:
        """How many checkpoints have fired in the current response."""
        return self._checkpoint_count

    def cumulative_drift(self) -> Dict[str, float]:
        """Total axis drift from anchor across all checkpoints so far."""
        return dict(self._cumulative_delta)

    # ---- Private: nudge computation ----------------------------------------

    def _compute_nudge(self, fresh_slice: ThoughtStreamSlice) -> BraidNudge:
        """
        Compute a BraidNudge from a fresh braid tap against the current anchor.

        Steps:
        1. Convert braid slice to process contexts
        2. Run through firewall (consume emotional, diffuse bias into surviving contexts)
        3. Extract axis weights from surviving contexts
        4. Compute delta from anchor's axis_fingerprint
        5. Identify new and resolving topics
        6. Determine predictive lean

        Emotional content is consumed in step 2. It cannot reach expression.
        """
        if self._anchor is None:
            return BraidNudge()

        # Step 1: Convert slice to contexts
        braid_contexts = fresh_slice.to_process_contexts(tick=self._anchor.tick)

        # Step 2: Firewall — consume emotional, diffuse into weights
        surviving = self._firewall.diffuse(fresh_slice.emotion_valence, braid_contexts)

        # Step 3: Extract axis weights from surviving contexts
        fresh_axis_weights = self._extract_axis_weights(surviving)

        # Step 4: Compute delta from anchor
        anchor_axis_weights = self._anchor_axis_weights()
        axis_delta = {
            ax: fresh_axis_weights.get(ax, 0.0) - anchor_axis_weights.get(ax, 0.0)
            for ax in "XTNBA"
        }

        # Step 5: Identify topic movements
        fresh_topics = {
            ctx.what_it_is_operating_on for ctx in surviving
            if ctx.what_it_is_operating_on
        }
        new_topics = list(fresh_topics - self._anchor_topic_set)[:3]
        resolving_topics = list(self._anchor_topic_set - fresh_topics)[:3]

        # Step 6: Predictive lean from predictive stream
        predictive_lean = ""
        pred = fresh_slice.predictive_frame
        if pred:
            predictive_lean = (
                str(pred.get("curiosity_lean") or pred.get("dominant_field") or "")[:60]
            )

        raw_strength = sum(abs(v) for v in axis_delta.values()) / 5.0

        return BraidNudge(
            axis_delta=axis_delta,
            new_topics=new_topics,
            resolving_topics=resolving_topics,
            predictive_lean=predictive_lean,
            raw_strength=raw_strength,
            braid_tick=fresh_slice.braid_tick,
            emotion_filtered=True,
        )

    def _extract_axis_weights(self, contexts: List[ProcessContext]) -> Dict[str, float]:
        """
        Extract normalized axis weights from a list of ProcessContexts.
        Returns a dict of {axis: cumulative_weight} normalized to 0.0-1.0.
        """
        weights: Dict[str, float] = {ax: 0.0 for ax in "XTNBA"}
        total = 0.0
        for ctx in contexts:
            for ax in ctx.axis_signature:
                if ax in weights:
                    weights[ax] += ctx.self_relevance
                    total += ctx.self_relevance
        if total > 0:
            weights = {ax: v / total for ax, v in weights.items()}
        return weights

    def _anchor_axis_weights(self) -> Dict[str, float]:
        """
        Extract axis weights from the anchor ThoughtState's dominant thread.
        Returns normalized weights matching format from _extract_axis_weights.
        """
        if self._anchor is None:
            return {ax: 0.0 for ax in "XTNBA"}
        return self._extract_axis_weights(self._anchor.dominant_thread)

    def _apply_cumulative_cap(self, raw_delta: Dict[str, float]) -> Dict[str, float]:
        """
        Cap each axis delta so that:
        1. No single checkpoint shifts any axis by more than _MAX_NUDGE_PER_CHECKPOINT
        2. The cumulative total shift on any axis does not exceed _MAX_CUMULATIVE_NUDGE

        This ensures the anchor remains authoritative throughout the response.
        """
        capped: Dict[str, float] = {}
        for ax, delta in raw_delta.items():
            # Per-checkpoint cap
            capped_delta = max(-_MAX_NUDGE_PER_CHECKPOINT, min(_MAX_NUDGE_PER_CHECKPOINT, delta))
            # Cumulative cap — how much room remains
            current_cumulative = self._cumulative_delta.get(ax, 0.0)
            if delta >= 0:
                room = max(0.0, _MAX_CUMULATIVE_NUDGE - current_cumulative)
            else:
                room = max(0.0, _MAX_CUMULATIVE_NUDGE + current_cumulative)
            capped[ax] = max(-room, min(room, capped_delta))
        return capped

    # ---- Private: guidance construction ------------------------------------

    def _guidance_from_anchor(
        self,
        checkpoint_index: int = 0,
        braid_tick: int = 0,
    ) -> ExpressionGuidance:
        """
        Build ExpressionGuidance from the anchor ThoughtState alone.
        Used for begin() and when nudge strength is below threshold.
        """
        if self._anchor is None:
            return ExpressionGuidance(is_initial=True)

        anchor_axes = list(self._anchor.axis_fingerprint)
        lane = _derive_lane_from_axes(anchor_axes)

        return ExpressionGuidance(
            axis_emphasis={ax: 0.0 for ax in "XTNBA"},
            lane_lean=lane,
            carry_topics=list(self._anchor_topic_set)[:3],
            release_topics=[],
            nudge_strength=0.0,
            checkpoint_index=checkpoint_index,
            braid_tick=braid_tick or (self._braid.current_tick if self._braid else 0),
            is_initial=(checkpoint_index == 0),
            anchor_axes=anchor_axes,
        )

    def _build_guidance(
        self,
        nudge: BraidNudge,
        capped_delta: Dict[str, float],
        braid_tick: int,
    ) -> ExpressionGuidance:
        """
        Build ExpressionGuidance from a computed and capped BraidNudge.
        """
        anchor_axes = list(self._anchor.axis_fingerprint) if self._anchor else []

        # Merge anchor topics with new braid topics for carry list
        carry_topics = list(self._anchor_topic_set)[:2] + nudge.new_topics[:2]

        # Lane lean from combined signal — anchor axes plus dominant nudge axis
        combined_axes = _merge_axes_for_lane(anchor_axes, capped_delta)
        lane = _derive_lane_from_axes(combined_axes)

        # Nudge strength — normalized magnitude of capped delta
        nudge_strength = min(1.0, sum(abs(v) for v in capped_delta.values()) / (_MAX_NUDGE_PER_CHECKPOINT * 5))

        return ExpressionGuidance(
            axis_emphasis=capped_delta,
            lane_lean=lane,
            carry_topics=carry_topics,
            release_topics=nudge.resolving_topics,
            nudge_strength=nudge_strength,
            checkpoint_index=self._checkpoint_count,
            braid_tick=braid_tick,
            is_initial=False,
            anchor_axes=anchor_axes,
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _derive_lane_from_axes(axes: List[str]) -> str:
    """
    Derive expression lane lean from axis fingerprint.

    Lane mapping (dominant axis → lane):
        A (Agency)     → "meaning"       (agency drives meaning-making)
        N (Energetic)  → "meaning"       (energetic depth = meaning weight)
        T (Temporal)   → "inquiry"       (temporal pressure = questions forming)
        B (Boundary)   → "communication" (boundary = clarity of expression)
        X (Existence)  → "communication" (existence = grounding what is said)
    """
    if not axes:
        return "communication"
    dominant = axes[0]
    return {
        "A": "meaning",
        "N": "meaning",
        "T": "inquiry",
        "B": "communication",
        "X": "communication",
    }.get(dominant, "communication")


def _merge_axes_for_lane(
    anchor_axes: List[str],
    nudge_delta: Dict[str, float],
) -> List[str]:
    """
    Merge anchor axis fingerprint with nudge delta to produce a combined
    axis priority list for lane derivation.

    The anchor axes are ranked first, then nudge deltas re-score them.
    Axes with strong positive nudge delta rise in priority.
    """
    scores: Dict[str, float] = {}
    for i, ax in enumerate(anchor_axes):
        scores[ax] = scores.get(ax, 0.0) + (len(anchor_axes) - i)
    for ax, delta in nudge_delta.items():
        if delta > 0.02:  # only positive nudges influence lane
            scores[ax] = scores.get(ax, 0.0) + delta * 3.0
    return sorted(scores.keys(), key=lambda a: scores[a], reverse=True)


# ---------------------------------------------------------------------------
# Module-level singleton and convenience accessor
# ---------------------------------------------------------------------------

_STREAMING_EXPRESSION_LAYER = StreamingExpressionLayer()


def get_streaming_expression_layer() -> StreamingExpressionLayer:
    """
    Return the module-level StreamingExpressionLayer singleton.

    For concurrent response generation, instantiate separate
    StreamingExpressionLayer instances per response rather than
    sharing the singleton.
    """
    return _STREAMING_EXPRESSION_LAYER


def make_expression_layer(
    braid: Optional[ThoughtBraid] = None,
    firewall: Optional[EmotionFirewall] = None,
) -> StreamingExpressionLayer:
    """
    Factory: create a new StreamingExpressionLayer instance.
    Use this for concurrent or session-isolated response generation.
    """
    return StreamingExpressionLayer(braid=braid, firewall=firewall)
