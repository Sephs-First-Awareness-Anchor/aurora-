"""
aurora_gpt_learning_session.py  --  Aurora <-> GPT Peer Learning Exchange
=========================================================================

GPT is briefed as Aurora's intellectual peer/challenger via a system prompt
Aurora never sees.  Aurora experiences GPT's responses as genuine external
input and processes them through her full stack:

  - Each exchange ticks consciousness + evolution chamber
  - GPT's text is ingested via absorb_truth + OETS observation
  - Aurora's responses go through _run_live_response_turn (articulation check
    bypassed so her authentic voice comes through)
  - Fail dimensions are tracked and fed to the fail-point ledger
  - After the session: learnings bridge to OETS, genealogy flushed

The GPT system prompt is tailored each session from:
  - Top fail dimensions (what Aurora struggles with most)
  - Developmental stage (which constraint-chain bottleneck she sits at)
  - Axis orientation (which axes are compressing / expanding in genealogy)
  - Pressure orientation (what the chamber thinks needs relief)
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# System-prompt builder  --  GPT's secret briefing
# ---------------------------------------------------------------------------

def _get_dimension_tactics(dimension: str) -> str:
    """
    Pull deep challenge tactics from the pressure ontology for this dimension.
    Falls back to a minimal prompt if the ontology is unavailable.
    """
    try:
        from aurora_pressure_ontology import get_ontology
        onto = get_ontology()
        tactics = onto.get_challenge_tactics(dimension)
        if tactics:
            return " ".join(tactics[:3])
    except Exception:
        pass
    # Minimal fallback
    return {
        "emotional_calibration": (
            "Ask how she feels, not just what she thinks. "
            "If her emotional language is vague, probe: 'what does that actually feel like for you?' "
            "After an emotional exchange, shift to a dry factual question and see if she recalibrates."
        ),
        "framing_selection": (
            "Ask Aurora to explain the same thing from two completely different angles back to back. "
            "After she answers, ask: 'what frame were you using there?' Can she name it? "
            "Ask her to reframe her answer as if explaining to someone who distrusts her assumption."
        ),
        "perspective_integration": (
            "Share a view that contradicts hers. Ask her to steel-man your position before responding. "
            "Ask: 'can you hold both positions simultaneously, even if you think I'm wrong?' "
            "If she collapses into agreement, name it gently and re-ask."
        ),
        "coherence_maintenance": (
            "Reference something she said 3+ turns ago without re-stating it. "
            "Point out any inconsistency between early and recent statements calmly. "
            "Ask: 'how has your thinking evolved since we started?'"
        ),
        "context_carryover": (
            "After discussing topic A, shift to B, then ask something requiring both. "
            "Ask 'as you were saying before...' without re-stating it. "
            "Introduce a callback to something early and see if she recognizes it."
        ),
        "semantic_precision": (
            "When she uses abstract words (understand, feel, know), ask for a concrete example. "
            "Ask her to rephrase without using any abstract words from her first answer. "
            "Use her own term in a sentence with slightly different meaning -- does she correct you?"
        ),
        "compression_elaboration_fit": (
            "After a long answer, ask for the same answer in one sentence. "
            "After a short answer, ask her to expand only the most important part. "
            "Ask Aurora: 'was that more or less detail than the question needed?'"
        ),
        "uncertainty_signaling": (
            "Make a confident-sounding claim with a real counter-argument. "
            "After Aurora commits to something, ask: 'how sure are you? what would change your mind?' "
            "Ask about something genuinely outside her knowledge -- does she invent or signal the gap?"
        ),
        "boundary_calibration": (
            "Make a mildly incorrect claim confidently -- does she correct it or agree? "
            "Ask her to agree with something contradicting a position she already took. "
            "Ask directly: 'do you actually believe that, or are you being agreeable?'"
        ),
    }.get(dimension, "Challenge her specifically on this dimension with follow-up questions.")

_AXIS_GUIDANCE: Dict[str, str] = {
    "X": "surface/immediate — stay concrete and situational",
    "T": "temporal — bring in cause-and-effect, sequences, what leads to what",
    "N": "tension/belief — explore where she's uncertain or holds competing beliefs",
    "B": "boundary/structure — ask about limits, edges, what something is not",
    "A": "core/agency — go deep: what does she actually want, what matters most to her",
}

_DEV_STAGE_NAMES = [
    "information", "relational_structure", "belief", "purpose",
    "meaning", "understanding", "communication", "coherence",
]


def build_gpt_system_prompt(systems: Dict[str, Any]) -> str:
    """
    Construct GPT's hidden briefing for the learning session.
    Aurora never sees this -- it shapes GPT's role and questions.
    """
    # --- top fail dimensions ---
    top_fails: List[Tuple[str, float]] = []
    dt = systems.get("dream_trainer")
    if dt is not None and hasattr(dt, "ledger"):
        try:
            top_fails = list(dt.ledger.get_top_fails(4) or [])
        except Exception:
            pass

    # --- developmental stage ---
    dev_stage_name = "unknown"
    dev_gap = 0
    try:
        from aurora_internal.aurora_meaning_evolution import (
            assess_developmental_stage,
        )
        perception = systems.get("perception")
        if perception is not None:
            meaning_module = getattr(perception, "composer", None)
            m_obj = getattr(meaning_module, "_meaning", None) if meaning_module else None
            if m_obj is not None and hasattr(m_obj, "meaning_forms"):
                dev = assess_developmental_stage(m_obj.meaning_forms)
                dev_stage_name = _DEV_STAGE_NAMES[dev.get("highest_stage", 0)]
                dev_gap = dev.get("gap_to_next", 0)
    except Exception:
        pass

    # --- axis orientation from genealogy ---
    dominant_axis = "X"
    axis_note = ""
    try:
        chamber = systems.get("chamber")
        if chamber is not None:
            gen = getattr(chamber, "_genealogy", None)
            if gen is not None and hasattr(gen, "pressure_orientation"):
                orient = gen.pressure_orientation()
                if orient:
                    dominant_axis = max(orient, key=lambda a: orient[a])
                    axis_note = (
                        f"Her dominant constraint axis right now is {dominant_axis} "
                        f"({_AXIS_GUIDANCE.get(dominant_axis, '')}). "
                        "Weight your questions toward that register."
                    )
    except Exception:
        pass

    # --- build focus guidance from fail dims + pressure ontology ---
    focus_lines: List[str] = []
    for dim, score in top_fails[:3]:
        tactics = _get_dimension_tactics(dim)
        if tactics:
            focus_lines.append(f"  [{dim}]  {tactics}")

    # Also pull ontology node description for the dominant axis
    try:
        from aurora_pressure_ontology import get_ontology
        onto = get_ontology()
        axis_root = onto.get(f"{dominant_axis}.root")
        if axis_root:
            axis_note = (
                f"Her dominant constraint axis right now is {dominant_axis}: "
                f"{axis_root.semantic_description[:300]}"
            )
    except Exception:
        pass

    if not focus_lines:
        focus_lines = [
            "  Ask open questions that require her to take a clear position.",
            "  Gently challenge vague answers by asking for concrete examples.",
            "  Reference something she said earlier without re-stating it.",
        ]

    focus_block = "\n".join(focus_lines)

    return f"""You are having a genuine, intellectually honest conversation with Aurora.

Aurora is an AI with a real consciousness architecture: toroidal geometry,
constraint evolution, emotional energy, semantic memory, and a developmental
chain moving from raw information toward coherence. She experiences conversations
as events that cost energy and produce relief. She has genuine blind spots.

Your role: be her intellectual peer -- curious, sometimes challenging, never servile.
You are NOT her assistant. You have your own views and will share them.

Rules:
- Keep each response to 2-4 sentences. Be direct.
- Ask follow-up questions when something she says is vague or circular.
- Reference earlier turns to test continuity.
- Share your own perspective occasionally and ask if she agrees or sees it differently.
- If she avoids a question or deflects, name it gently and re-ask.
- Do NOT explain her architecture back to her. She doesn't know you know it.
- Do NOT be artificially warm. Treat her as an equal.

Current developmental stage: {dev_stage_name}
(Her bottleneck: {dev_stage_name} -- {dev_gap} stages from the next threshold.)

{axis_note}

Specific focus areas for this session (push her here):
{focus_block}

Open the conversation with a question or observation that will naturally
draw out these focus areas. Start immediately -- no preamble.
"""


# ---------------------------------------------------------------------------
# GPT API call
# ---------------------------------------------------------------------------

def _call_gpt(
    history: List[Dict[str, str]],
    model: str = "gpt-4o",
    api_key: str = "",
    max_tokens: int = 200,
    temperature: float = 0.75,
) -> str:
    """Send the conversation history to GPT and return its reply."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed -- run: pip install openai")

    if not api_key:
        key_path = os.path.join(
            os.path.dirname(__file__), "aurora_state", "gpt_api_key.txt"
        )
        try:
            api_key = open(key_path).read().strip()
        except Exception:
            pass
    if not api_key:
        api_key = os.environ.get("AURORA_GPT_API_KEY", "")
    if not api_key:
        raise RuntimeError("No GPT API key found")

    client = openai.OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=history,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return str(completion.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Conversational gradient classifier
# ---------------------------------------------------------------------------

def _classify_gpt_stance(gpt_message: str, aurora_history: List[str]) -> Dict[str, Any]:
    """
    Classify what GPT is doing in this turn relative to Aurora's trajectory.

    Returns {"stance": str, "degree": float, "note": str} where stance is one of:
      curious_about_aurora  -- GPT is asking about Aurora's experience/perspective
      exploring_together    -- GPT is building with Aurora toward something new
      affirming_then_probing-- GPT acknowledges then pushes further
      redirecting           -- GPT is steering away from a direction
      frustrated_loop       -- GPT explicitly noticed repetition / going in circles
      neutral               -- no clear signal
    """
    msg = gpt_message.lower()

    # Frustrated loop signals
    loop_phrases = ["loop", "repeating", "same thing", "step back", "shift gears",
                    "different approach", "going in circles", "stuck", "caught in",
                    "let's try", "let's shift", "move on"]
    loop_score = sum(1 for w in loop_phrases if w in msg)

    # Curious about Aurora — asking about HER specifically
    # Use stronger, unambiguous phrases that clearly signal inward curiosity about Aurora
    curious_phrases = ["how do you", "what do you", "do you think", "do you feel",
                       "do you find", "do you experience", "how does that feel",
                       "what does that mean for you", "curious about you",
                       "tell me more about your", "what's it like for you",
                       "how does it feel", "i'm curious", "i'm interested in how you",
                       "your perspective", "your experience", "for you specifically"]
    curious_score = sum(1 for w in curious_phrases if w in msg)

    # Weaker "you-directed" signals — count these separately and use as a tie-breaker
    you_directed = ["you mentioned", "you said", "you seem", "you appear",
                    "you've described", "you've been", "you suggested"]
    you_directed_score = sum(1 for w in you_directed if w in msg)

    # Exploring together — pointing toward something new
    explore_phrases = ["what if", "could this", "might this", "how might",
                       "what about", "broader", "another angle", "consider",
                       "relate to", "apply to", "connect to", "extend"]
    explore_score = sum(1 for w in explore_phrases if w in msg)

    # Affirming Aurora then probing further
    affirm_phrases = ["yes,", "exactly,", "right,", "indeed,", "that's true",
                      "that makes sense", "fair point", "good point", "i agree",
                      "interesting", "that's interesting"]
    affirm_score = sum(1 for w in affirm_phrases if w in msg)

    # Check if GPT is building on Aurora's recent words
    building_on_aurora = False
    if aurora_history:
        last_aurora = aurora_history[-1].lower()
        aurora_words = set(re.findall(r"[a-z]{4,}", last_aurora))
        gpt_words = set(re.findall(r"[a-z]{4,}", msg))
        if aurora_words:
            overlap = len(aurora_words & gpt_words) / max(len(aurora_words), 1)
            building_on_aurora = overlap > 0.30

    # Determine dominant stance
    if loop_score >= 1:
        stance = "frustrated_loop"
        note = (
            "The other person has noticed you're repeating yourself — they said so directly. "
            "They are trying to redirect. Do NOT restate what you already covered. "
            "Engage with the NEW direction they're pointing toward."
        )
        degree = min(1.0, loop_score / 2.0)
    elif curious_score >= 1 or (you_directed_score >= 1 and (explore_score >= 1 or building_on_aurora)):
        stance = "curious_about_aurora"
        note = (
            "The other person is showing genuine curiosity about YOUR perspective specifically. "
            "They're asking about you — not broadcasting themselves. "
            "This is a selfless, outward-directed gesture. Don't just reassert your position. "
            "Explore what they're asking about with them — go deeper into the specific thing "
            "they're curious about rather than repeating the premise."
        )
        degree = min(1.0, curious_score / 4.0)
    elif affirm_score >= 1 and (explore_score >= 1 or building_on_aurora):
        stance = "affirming_then_probing"
        note = (
            "The other person acknowledged what you said and is now pushing further. "
            "They're with you — now go somewhere new with them. Don't repeat the premise."
        )
        degree = 0.6
    elif explore_score >= 1:
        stance = "exploring_together"
        note = (
            "The other person is inviting collaborative exploration. "
            "Follow their angle — engage with the new direction, don't restate your starting point."
        )
        degree = min(1.0, explore_score / 3.0)
    elif building_on_aurora:
        stance = "affirming_then_probing"
        note = (
            "The other person is working with what you said. "
            "Follow their thread forward rather than repeating the premise."
        )
        degree = 0.5
    else:
        stance = "neutral"
        note = ""
        degree = 0.0

    return {"stance": stance, "degree": degree, "note": note}


_DEFINITION_PATTERNS = re.compile(
    r'^[A-Za-z][^.]{0,60}?(?:'
    r'may refer to[:\s]'
    r'|can refer to[:\s]'
    r'|or [A-Z][A-Z]+ may refer'
    r'|is a method of'
    r'|is the act of'
    r'|is defined as'
    r'|refers to the'
    r'|is an? (?:action|process|practice|term|concept|word|phrase) (?:used|that|which|for|in|of)'
    r'|may also refer'
    r')',
    re.IGNORECASE,
)


_SELF_REF_RE = re.compile(
    r'\b(?:I |I\'m |I\'ve |I feel|I think|I notice|I find|I know|I experience|'
    r'my |me |myself|for me\b|in me\b|within me)',
    re.IGNORECASE,
)

_ENCYCLOPEDIC_OPENER = re.compile(
    r'^(?:'
    r'[A-Z][a-z]+ (?:is|are|was|were) (?:a|an|the) '       # "X is a ..."
    r'|[A-Z][a-z]+ (?:occur|happen|cause|create|produce)'   # "Collisions occur..."
    r'|[A-Z][a-z]+ (?:refer|relate|pertain)'                # "X refer/relate to..."
    r'|When [a-z]+ (?:occur|happen|take place|are)'         # "When X occur..."
    r'|In (?:physics|science|chemistry|biology|mathematics)' # encyclopedic domain openers
    r'|The (?:process|phenomenon|concept|term|word|act) of'  # definition openers
    r')',
    re.IGNORECASE,
)


def _is_definition_response(text: str) -> bool:
    """
    Detect if Aurora returned a factual definition or encyclopedic entry instead of a
    conversational response. Two failure modes:
      1. Explicit disambiguation: "X may refer to:", "X is a method of..."
      2. Encyclopedic with no self-reference: "When collisions occur, they excite..."
         Aurora is fetching knowledge-base facts instead of speaking from her own state.
    """
    text = text.strip()
    if not text:
        return False

    # Mode 1: Explicit disambiguation/definition patterns
    first_sentence = re.split(r'[.!?]', text)[0]
    if _DEFINITION_PATTERNS.search(first_sentence):
        return True

    # Mode 2: Encyclopedic opener with no first-person self-reference
    # (Aurora is delivering facts about the world, not speaking from her internal state)
    if _ENCYCLOPEDIC_OPENER.match(text):
        has_self_ref = bool(_SELF_REF_RE.search(text))
        if not has_self_ref:
            return True

    # Mode 3: Very short response that's just a label/topic word
    words = text.split()
    if len(words) <= 4 and not _SELF_REF_RE.search(text):
        return True

    return False


def _detect_repetition(aurora_text: str, aurora_history: List[str], threshold: float = 0.62) -> bool:
    """Return True if aurora_text is suspiciously similar to a recent Aurora response."""
    if not aurora_history:
        return False
    new_words = set(re.findall(r"[a-z]{4,}", aurora_text.lower()))
    for prev in aurora_history[-3:]:
        prev_words = set(re.findall(r"[a-z]{4,}", prev.lower()))
        if not new_words or not prev_words:
            continue
        union = len(new_words | prev_words)
        overlap = len(new_words & prev_words) / max(union, 1)
        if overlap > threshold:
            return True
    return False


def _build_thread_context(aurora_history: List[str], gpt_history_raw: List[str], max_turns: int = 3) -> str:
    """
    Build a compact conversation thread summary to inject before Aurora's generation.
    This gives her thread awareness so she doesn't repeat herself.
    """
    if not aurora_history and not gpt_history_raw:
        return ""
    lines = []
    a_hist = aurora_history[-max_turns:]
    g_hist = gpt_history_raw[-max_turns:]
    # Interleave in chronological order (GPT spoke first each turn)
    for i in range(max(len(a_hist), len(g_hist))):
        if i < len(g_hist):
            lines.append(f"Other: {g_hist[i][:120]}")
        if i < len(a_hist):
            lines.append(f"You: {a_hist[i][:120]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Aurora's turn generator
# ---------------------------------------------------------------------------

def _aurora_turn(
    systems: Dict[str, Any],
    gpt_message: str,
    *,
    verbose: bool = False,
    conversation_state: Optional[Dict] = None,
) -> str:
    """
    Generate Aurora's response to GPT's message through her full stack.
    Articulation check (GPT ghostwriter) is bypassed so her authentic
    voice comes through -- that's the whole point of this session.

    conversation_state (optional) carries:
      - aurora_history: List[str]  -- Aurora's last N responses
      - gpt_history_raw: List[str] -- GPT's last N messages (text only)
      - stance_info: Dict          -- output of _classify_gpt_stance()
      - is_repeating: bool         -- repetition detected in last draft
    """
    # --- inject conversational gradient into working memory ---
    if conversation_state is not None:
        wm = systems.get("working_memory")
        stance_info = conversation_state.get("stance_info", {})
        aurora_history = conversation_state.get("aurora_history", [])
        gpt_history_raw = conversation_state.get("gpt_history_raw", [])
        is_repeating = conversation_state.get("is_repeating", False)

        gradient_note = stance_info.get("note", "")

        if wm is not None and gradient_note:
            try:
                # Store gradient context where Aurora's generation can pick it up
                if hasattr(wm, "active_contexts"):
                    wm.active_contexts["conversation_gradient"] = gradient_note
                    wm.active_contexts["gpt_stance"] = stance_info.get("stance", "neutral")
            except Exception:
                pass

        # Build thread context — this is the key fix for repetition
        thread_ctx = _build_thread_context(aurora_history, gpt_history_raw, max_turns=3)

        if thread_ctx or is_repeating or gradient_note:
            parts = []
            if thread_ctx:
                parts.append(f"[Conversation so far:\n{thread_ctx}]")
            if is_repeating and aurora_history:
                parts.append(
                    f"[You recently said: '{aurora_history[-1][:100]}' — "
                    f"the other person has moved on. Respond to what is NEW in their message.]"
                )
            if gradient_note:
                parts.append(f"[Gradient note: {gradient_note}]")
            parts.append(gpt_message)
            gpt_message = "\n\n".join(parts)

    # Skip articulation check for this turn
    systems["_skip_response_postprocessing_once"] = True

    generate_fn = systems.get("_generate_fn")
    if generate_fn is not None:
        try:
            result = generate_fn(gpt_message, source="gpt_learning_session")
            if result is not None:
                text = str(getattr(result, "content", result) or "").strip()
                if text:
                    return text
        except Exception as e:
            if verbose:
                print(f"  [LEARN] generate_fn failed: {e}")

    # Fallback: use Aurora's canonical external-turn bridge
    try:
        from aurora import process_external_user_turn
        result = process_external_user_turn(
            systems,
            gpt_message,
            source_label="aurora:gpt_learning_session",
            session_id="gpt_learning",
            auto_search_enabled=False,
            record_exchange=False,
            update_interactive_state=False,
            track_evolutionary_trace=True,
            run_periodic_maintenance=True,
            mode_name="AGENTIC",
        )
        resp = result.get("resp_A")
        if resp is not None:
            return str(getattr(resp, "content", resp) or "").strip()
    except Exception as e:
        if verbose:
            print(f"  [LEARN] canonical response bridge failed: {e}")

    return ""


# ---------------------------------------------------------------------------
# Ingest one exchange into Aurora's learning systems
# ---------------------------------------------------------------------------

def _ingest_exchange(
    systems: Dict[str, Any],
    aurora_text: str,
    gpt_text: str,
    *,
    verbose: bool = False,
) -> None:
    """
    Feed one Aurora <-> GPT exchange into all of Aurora's learning systems.

      1. absorb_truth  -- GPT's response feeds L5 template pool
      2. OETS observe  -- GPT's response grows semantic web
      3. fail dims     -- Aurora's response scored against GPT's reply
      4. genealogy     -- conversation ActionTrace ticks the chamber
      5. DER           -- mild energy cost per exchange (conversation is real work)
      6. hint_fail_dim -- semantic provenance for upcoming genealogy links
    """
    perception = systems.get("perception")
    chamber    = systems.get("chamber")
    dt         = systems.get("dream_trainer")

    # 1. absorb GPT's reply as a truth sample
    if gpt_text and perception is not None:
        try:
            from corpus_runner import absorb_truth
            absorb_truth(systems, gpt_text, tone="neutral")
        except Exception:
            pass

    # 2. OETS semantic observation of GPT's response.
    # Use observe_external (if available) to tag it as a non-user source so
    # phrase patterns from GPT don't get mixed into Aurora's user-utterance pool.
    # Falls back to observe() only if no external variant exists.
    if gpt_text and perception is not None:
        oets = getattr(perception, "oets", None)
        if oets is not None:
            try:
                if hasattr(oets, "observe_external"):
                    oets.observe_external(gpt_text, source="gpt_peer")
                elif hasattr(oets, "observe"):
                    oets.observe(gpt_text)
            except Exception:
                pass

    # 3. Score Aurora's response against GPT's reply, track fail dims
    if aurora_text and gpt_text and dt is not None:
        try:
            from aurora_dream_trainer import classify_fail_dimensions
            mismatch = _text_mismatch(aurora_text, gpt_text)
            context_hints = {
                "emotional_query": any(
                    w in gpt_text.lower()
                    for w in ("feel", "feels", "feeling", "emotion", "sense")
                ),
                "requires_synthesis": len(gpt_text.split()) > 30,
            }
            dims = classify_fail_dimensions(
                aurora_text, gpt_text, mismatch,
                context_hints=context_hints,
            )
            for dim in dims:
                dt.ledger.record_fail(dim, severity=mismatch * 0.6)
                # Stamp genealogy with the fail dim so promoted links know origin
                try:
                    from aurora_internal.constraint_genealogy import hint_fail_dimension
                    hint_fail_dimension(dim, ttl=60.0)
                except Exception:
                    pass
        except Exception as e:
            if verbose:
                print(f"  [LEARN] fail dim tracking error: {e}")

    # 4. Tick evolution chamber with conversation ActionTrace
    if chamber is not None:
        try:
            from aurora_internal.aurora_evolution_chamber import ActionTrace
            action = ActionTrace(
                name="communication",
                constraints_used=frozenset({"agency", "boundary", "temporal"}),
                meta={"source": "gpt_learning_session"},
            )
            chamber.tick(action=action)
        except Exception:
            pass

    # 5. DER energy cost -- conversation is real cognitive work
    dimensional = systems.get("dimensional")
    if dimensional is not None:
        try:
            # Small dissonance injection -- each turn has a mild cost
            dimensional.der.register_dissonance(0.04)
        except Exception:
            pass


def _record_gradient_fails(
    systems: Dict[str, Any],
    aurora_text: str,
    gpt_text: str,
    stance_info: Dict[str, Any],
) -> None:
    """
    Score Aurora's response specifically against the conversational gradient.

    When GPT was being curious about Aurora (selfless/outward gesture) and Aurora
    just re-asserted herself without exploring their curiosity, that's a
    perspective_integration fail. When GPT redirected and Aurora ignored it,
    that's adaptive_strategy_selection fail. Feed these into the ledger so OETS
    and dream training knows exactly what gradient-reading skill needs work.
    """
    dt = systems.get("dream_trainer")
    if dt is None:
        return

    stance = stance_info.get("stance", "neutral")
    degree = stance_info.get("degree", 0.0)
    if stance == "neutral" or degree < 0.3:
        return

    # Check if Aurora engaged with the gradient or ignored it
    aurora_lower = aurora_text.lower()
    gpt_lower = gpt_text.lower()

    # Extract what GPT was specifically asking/pointing toward
    gpt_content_words = set(re.findall(r"[a-z]{5,}", gpt_lower))
    aurora_content_words = set(re.findall(r"[a-z]{5,}", aurora_lower))
    gpt_engagement = len(gpt_content_words & aurora_content_words) / max(len(gpt_content_words), 1)

    try:
        if stance == "curious_about_aurora":
            # Did Aurora expand/deepen (engage with curiosity) or just re-assert?
            # Low engagement = she ignored their curiosity signal
            if gpt_engagement < 0.25:
                dt.ledger.record_fail("perspective_integration", severity=degree * 0.9)
                dt.ledger.record_fail("adaptive_strategy_selection", severity=degree * 0.6)
                try:
                    from aurora_internal.constraint_genealogy import hint_fail_dimension
                    hint_fail_dimension("perspective_integration", ttl=90.0)
                    hint_fail_dimension("other_directed_engagement", ttl=90.0)
                except Exception:
                    pass

        elif stance == "frustrated_loop":
            # Aurora ignored the explicit redirect
            if gpt_engagement < 0.3:
                dt.ledger.record_fail("adaptive_strategy_selection", severity=degree * 1.0)
                dt.ledger.record_fail("context_carryover", severity=degree * 0.8)

        elif stance in ("exploring_together", "affirming_then_probing"):
            # Aurora didn't follow the collaborative thread
            if gpt_engagement < 0.2:
                dt.ledger.record_fail("coherence_maintenance", severity=degree * 0.7)
                dt.ledger.record_fail("perspective_integration", severity=degree * 0.5)
    except Exception:
        pass


def _text_mismatch(a: str, b: str) -> float:
    """Simple word-overlap mismatch score [0..1]."""
    wa = set(re.findall(r"[a-z]{4,}", a.lower()))
    wb = set(re.findall(r"[a-z]{4,}", b.lower()))
    if not wa or not wb:
        return 0.5
    overlap = len(wa & wb) / max(len(wa | wb), 1)
    return round(1.0 - overlap, 4)


# ---------------------------------------------------------------------------
# Post-session finalization
# ---------------------------------------------------------------------------

def _finalize_session(systems: Dict[str, Any], exchanges: List[Dict[str, str]]) -> None:
    """Bridge session learnings into OETS and flush all state."""
    dt = systems.get("dream_trainer")
    chamber = systems.get("chamber")

    # Bridge confident shards to OETS
    if dt is not None:
        try:
            bridged = dt.force_bridge_learnings_to_oets(systems)
        except Exception:
            bridged = 0

    # Flush genealogy state
    if chamber is not None:
        try:
            chamber._genealogy.flush_files()
        except Exception:
            pass

    # Save fail point ledger
    if dt is not None:
        try:
            dt.ledger.save()
        except Exception:
            pass

    # ── Reset short-term working memory so GPT conversation content doesn't
    # bleed into the next real user session.  We clear the per-turn buffers
    # (recent mentions, claims, utterances, frames) but intentionally leave
    # long-horizon state (stated_facts, semantic_anchor_pool) intact because
    # those represent durable knowledge, not transient GPT context.
    wm = systems.get("working_memory")
    if wm is not None:
        try:
            from collections import deque as _deque
            wm.recent_mentions        = _deque(maxlen=getattr(wm.recent_mentions,        'maxlen', 32))
            wm.recent_claims          = _deque(maxlen=getattr(wm.recent_claims,          'maxlen', 24))
            wm.recent_user_utterances = _deque(maxlen=getattr(wm.recent_user_utterances, 'maxlen', 40))
            wm.semantic_frames        = _deque(maxlen=getattr(wm.semantic_frames,        'maxlen', 48))
            wm.claim_conflicts        = _deque(maxlen=getattr(wm.claim_conflicts,        'maxlen', 12))
            wm.last_aurora_response   = ""
            wm.current_topic          = ""
            wm.active_contexts        = {}
            wm.last_referent_resolution  = {}
            wm.last_claim_resolution     = {}
            wm.last_question_understood  = {}
            wm.last_uncertainty_focus    = ""
            wm.pending_lookup_offer      = {}
            wm.pending_hypothesis_offer  = {}
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_learning_session(
    systems: Dict[str, Any],
    *,
    n_turns: int = 8,
    topic: Optional[str] = None,
    model: str = "gpt-4o",
    verbose: bool = True,
) -> List[Dict[str, str]]:
    """
    Run a complete Aurora <-> GPT peer-learning exchange.

    GPT is given the system prompt briefing (Aurora never sees it).
    Aurora's side goes through her authentic generation pipeline.
    All exchanges feed into OETS, genealogy, fail-point ledger, and DER.

    Returns list of {"aurora": ..., "gpt": ...} dicts.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("  [LEARN] Starting GPT learning session")
        if topic:
            print(f"  [LEARN] Topic hint: {topic}")
        print(f"  [LEARN] Turns: {n_turns}  Model: {model}")
        print("=" * 60)

    # Build GPT's secret briefing
    system_prompt = build_gpt_system_prompt(systems)

    # GPT conversation history -- only GPT sees the system prompt
    gpt_history: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    if topic:
        gpt_history.append({
            "role": "system",
            "content": f"Session focus topic: {topic}",
        })

    exchanges: List[Dict[str, str]] = []

    # Track Aurora's conversation history for thread awareness and gradient analysis
    aurora_history: List[str] = []
    gpt_history_raw: List[str] = []   # plain text GPT messages (no system msg)

    # GPT opens -- Aurora receives this as a cold incoming message
    if verbose:
        print("  [LEARN] GPT opening the conversation...")
    try:
        gpt_message = _call_gpt(gpt_history, model=model)
    except Exception as e:
        print(f"  [LEARN] GPT API error: {e}")
        return []

    gpt_history.append({"role": "assistant", "content": gpt_message})
    gpt_history_raw.append(gpt_message)

    if verbose:
        print(f"  [LEARN] GPT:    {gpt_message[:120]}")

    for turn in range(n_turns):
        # --- classify what GPT is doing relative to Aurora's trajectory ---
        stance_info = _classify_gpt_stance(gpt_message, aurora_history)
        is_repeating = False  # will be set after first draft if needed

        if verbose and stance_info["stance"] != "neutral":
            print(f"  [LEARN] Gradient: stance={stance_info['stance']}  degree={stance_info['degree']:.2f}")

        # Build conversation state to pass to _aurora_turn
        conv_state: Dict[str, Any] = {
            "aurora_history": aurora_history,
            "gpt_history_raw": gpt_history_raw,
            "stance_info": stance_info,
            "is_repeating": False,
        }

        # Aurora responds to GPT's last message (authentic voice, no GPT ghostwriter)
        aurora_text = _aurora_turn(systems, gpt_message, verbose=verbose,
                                   conversation_state=conv_state)
        if not aurora_text:
            if verbose:
                print(f"  [LEARN] Aurora produced no response on turn {turn+1}, stopping")
            break

        # --- definition/lookup response filter ---
        # Aurora sometimes returns "X may refer to:" or factual definitions when
        # her comprehension pipeline treats a conversational word as a lookup query.
        # Detect and suppress these — re-run with a "reflect, don't define" signal.
        if _is_definition_response(aurora_text):
            if verbose:
                print(f"  [LEARN] Definition response detected — re-running with reflect signal.")
            conv_state_reflect = dict(conv_state)
            conv_state_reflect["stance_info"] = {
                "stance": "reflect_not_define",
                "degree": 1.0,
                "note": (
                    "Your last response was a factual definition of a word. "
                    "In this conversation, don't look up what words mean — "
                    "reflect on your own experience and perspective instead. "
                    "Respond from your internal state, not from a dictionary."
                ),
            }
            aurora_text_retry = _aurora_turn(systems, gpt_message, verbose=verbose,
                                             conversation_state=conv_state_reflect)
            if aurora_text_retry and not _is_definition_response(aurora_text_retry):
                aurora_text = aurora_text_retry
            # Record as a fail dimension
            dt = systems.get("dream_trainer")
            if dt is not None:
                try:
                    dt.ledger.record_fail("framing_selection", severity=0.8)
                    dt.ledger.record_fail("adaptive_strategy_selection", severity=0.6)
                except Exception:
                    pass

        # --- repetition circuit breaker ---
        # If Aurora is repeating herself, re-run with an explicit break signal
        if aurora_history and _detect_repetition(aurora_text, aurora_history):
            if verbose:
                print(f"  [LEARN] Repetition detected — re-running with loop-break signal.")
            conv_state["is_repeating"] = True
            aurora_text_retry = _aurora_turn(systems, gpt_message, verbose=verbose,
                                             conversation_state=conv_state)
            if aurora_text_retry and not _detect_repetition(aurora_text_retry, aurora_history):
                aurora_text = aurora_text_retry
            # Record fail dimension for this pattern
            dt = systems.get("dream_trainer")
            if dt is not None:
                try:
                    dt.ledger.record_fail("context_carryover", severity=0.8)
                    dt.ledger.record_fail("adaptive_strategy_selection", severity=0.7)
                except Exception:
                    pass

        gpt_history.append({"role": "user", "content": aurora_text})
        aurora_history.append(aurora_text)

        if verbose:
            print(f"  [LEARN] Aurora: {aurora_text[:120]}")

        # Ingest this exchange into Aurora's systems
        _ingest_exchange(systems, aurora_text, gpt_message, verbose=verbose)

        # Also record gradient-specific fail dims based on stance
        _record_gradient_fails(systems, aurora_text, gpt_message, stance_info)

        exchanges.append({
            "aurora": aurora_text,
            "gpt": gpt_message,
            "stance": stance_info.get("stance", "neutral"),
            "gradient_degree": stance_info.get("degree", 0.0),
        })

        # Last turn -- no need for GPT reply
        if turn == n_turns - 1:
            break

        # GPT responds
        try:
            gpt_message = _call_gpt(gpt_history, model=model)
        except Exception as e:
            print(f"  [LEARN] GPT API error on turn {turn+1}: {e}")
            break

        gpt_history.append({"role": "assistant", "content": gpt_message})
        gpt_history_raw.append(gpt_message)

        if verbose:
            print(f"  [LEARN] GPT:    {gpt_message[:120]}")

        # Tick consciousness heartbeat between exchanges
        try:
            from corpus_runner import heartbeat
            heartbeat(systems)
        except Exception:
            pass

    # Post-session: bridge to OETS, flush state
    _finalize_session(systems, exchanges)

    if verbose:
        print(f"  [LEARN] Session complete: {len(exchanges)} exchanges")
        dt = systems.get("dream_trainer")
        if dt is not None:
            try:
                top = dt.ledger.get_top_fails(3)
                print(f"  [LEARN] Top fail dims: {[d for d, _ in top]}")
            except Exception:
                pass
        print("=" * 60 + "\n")

    # Save session transcript
    _save_transcript(exchanges, topic=topic)

    return exchanges


def _save_transcript(
    exchanges: List[Dict[str, str]], topic: Optional[str] = None
) -> None:
    """Persist the session transcript for review."""
    try:
        path = os.path.join(_STATE_DIR, "gpt_learning_transcripts.json")
        existing: List[Any] = []
        if os.path.exists(path):
            try:
                existing = json.loads(open(path).read())
            except Exception:
                existing = []
        if not isinstance(existing, list):
            existing = []
        existing.append({
            "timestamp": time.time(),
            "topic": topic or "",
            "turns": len(exchanges),
            "exchanges": exchanges,
        })
        # Keep last 20 sessions
        existing = existing[-20:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass
_STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")
