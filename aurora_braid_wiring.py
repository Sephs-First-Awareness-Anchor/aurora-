# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_braid_wiring.py

Wiring harness connecting the continuous thought braid and streaming
expression layer into Aurora's live runtime.

This module keeps all braid/expression wiring in one place, so aurora.py
receives exactly five one-line call sites rather than scattered inline logic.

FIVE CALL SITES IN aurora.py:
─────────────────────────────────────────────────────────────────────────
1. End of boot sequence (after all systems wired):

       from aurora_braid_wiring import boot_thought_braid
       boot_thought_braid(systems, verbose=verbose)

2. Top of _run_live_response_turn (after turn_tick is assigned):

       from aurora_braid_wiring import begin_response_turn
       begin_response_turn(systems, user_text=user_text, turn_tick=turn_tick)

3. Just BEFORE the perception.express() block (~line 20173):

       from aurora_braid_wiring import begin_expression
       begin_expression(systems)

4. Just AFTER perception.express() assigns _expressed / expression text:

       from aurora_braid_wiring import checkpoint_expression
       checkpoint_expression(systems, expression_text=_resp_draft)

5. After grammar engine + tone reconciliation, before return:

       from aurora_braid_wiring import complete_expression
       complete_expression(systems, state)

─────────────────────────────────────────────────────────────────────────

All five functions are fully try-except guarded.
If the braid or streaming layer is unavailable, Aurora continues normally.
There is no hard dependency — this wires in, it does not gate.

RE-ENTRY LOOP ALIGNMENT:
    This module closes the loop:
    STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING

    begin_response_turn() = STATE snapshot
    begin_expression()    = EXPRESSION anchor
    checkpoint_expression() = live braid tap during EXPRESSION
    complete_expression() = RE-ENTRY signal (feeds back to braid)

THOUGHT INTEGRATION:
    begin_response_turn() runs a lightweight ThoughtIntegrationSpace pass
    with the current braid slice. The result is stored at:

        systems['_current_thought_state']     — ThoughtState
        systems['_current_braid_slice']       — ThoughtStreamSlice
        systems['_expression_layer']          — StreamingExpressionLayer instance

    Downstream pipeline (downward chain, expression, grammar engine) can
    read systems['_current_thought_state'] for axis/lane/topic context.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_braid():
    """Return module-level ThoughtBraid singleton. None if unavailable."""
    try:
        from aurora_thought_formation import get_braid
        return get_braid()
    except Exception:
        return None


def _get_firewall():
    """Return module-level EmotionFirewall singleton. None if unavailable."""
    try:
        from aurora_thought_formation import get_firewall
        return get_firewall()
    except Exception:
        return None


def _get_continuity():
    """Return module-level ThoughtContinuity singleton. None if unavailable."""
    try:
        from aurora_thought_formation import get_continuity
        return get_continuity()
    except Exception:
        return None


def _build_turn_process_contexts(systems: Dict[str, Any], tick: int, user_text: str = ""):
    """
    Build ProcessContext list representing active processes at turn start.
    Registers memory, constraint pressure, and identity as concurrent
    processes entering the integration space.
    """
    try:
        from aurora_thought_formation import make_process_context
    except Exception:
        return []

    contexts = []

    # Memory process — SediMemory live recall seeded into memory lane
    try:
        sm = systems.get('sedimemory')
        if sm is None:
            consciousness = systems.get('consciousness')
            sm = getattr(consciousness, 'sedimemory', None) if consciousness else None
        if sm is not None:
            # Attempt live recall using the user_text as query seed
            _sedi_topic = str(user_text or "")[:120]
            _recalled_strata = []
            if _sedi_topic and hasattr(sm, 'recall_semantic'):
                try:
                    _recalled_strata = list(sm.recall_semantic(
                        _sedi_topic,
                        axis_filter=("T", "B", "A"),
                        max_results=4,
                    ) or [])
                except Exception:
                    pass
            _sedi_context = (
                f"recalled:{len(_recalled_strata)}_strata" if _recalled_strata
                else "sedi_ambient"
            )
            _sedi_relevance = min(0.85, 0.55 + len(_recalled_strata) * 0.07)
            contexts.append(make_process_context(
                process_id=f"turn_memory_{tick}",
                process_type="memory",
                what_triggered_it="user_turn",
                what_it_is_operating_on=_sedi_context,
                self_relevance=_sedi_relevance,
                axis_signature=["X", "T"],
                tick=tick,
            ))
            # Store recalled strata in systems for downstream use
            if _recalled_strata:
                systems['_braid_sedi_recall'] = _recalled_strata
    except Exception:
        pass

    # Constraint process — open loops as unresolved pressure
    try:
        open_loops = systems.get('_open_loops') or []
        if open_loops:
            contexts.append(make_process_context(
                process_id=f"turn_constraint_{tick}",
                process_type="constraint",
                what_triggered_it="open_loops",
                what_it_is_operating_on=f"{len(open_loops)} unresolved loops",
                self_relevance=0.6,
                axis_signature=["B", "A"],
                tick=tick,
                unresolved_tension_weight=min(1.0, len(open_loops) * 0.12),
            ))
    except Exception:
        pass

    # Identity process — active identity predicates
    try:
        ci = systems.get('core_identity')
        if ci is not None:
            contexts.append(make_process_context(
                process_id=f"turn_identity_{tick}",
                process_type="identity",
                what_triggered_it="user_turn",
                what_it_is_operating_on="identity_predicates",
                self_relevance=0.7,
                axis_signature=["X", "A"],
                tick=tick,
            ))
    except Exception:
        pass

    # Curiosity process — any pending open curiosity loops
    try:
        curiosity_loops = systems.get('_open_curiosity_loops') or []
        if curiosity_loops:
            subject = str(getattr(curiosity_loops[0], 'subject', curiosity_loops[0]))[:60]
            contexts.append(make_process_context(
                process_id=f"turn_curiosity_{tick}",
                process_type="curiosity",
                what_triggered_it="open_curiosity",
                what_it_is_operating_on=subject,
                self_relevance=0.45,
                axis_signature=["T", "A"],
                tick=tick,
                unresolved_tension_weight=0.3,
            ))
    except Exception:
        pass

    return contexts


# ---------------------------------------------------------------------------
# 1. boot_thought_braid
# ---------------------------------------------------------------------------

def boot_thought_braid(systems: Dict[str, Any], *, verbose: bool = False) -> None:
    """
    CALL SITE 1 — End of boot sequence.

    Starts the ThoughtBraid background thread.
    The braid begins advancing immediately — it is always running.

    Stores:
        systems['_thought_braid_thread']  — StreamingThoughtThread instance
        systems['_thought_braid']         — ThoughtBraid singleton reference
    """
    try:
        from aurora_thought_formation import get_braid, ThoughtBraid, StreamingThoughtThread

        braid = get_braid()
        thread = StreamingThoughtThread(braid=braid, systems=systems, tick_interval_s=2.0)
        thread.start()

        systems['_thought_braid'] = braid
        systems['_thought_braid_thread'] = thread
        if systems.get('sedimemory') is not None and hasattr(braid, 'connect_sedimemory'):
            try:
                braid.connect_sedimemory(systems['sedimemory'])
                if verbose:
                    print("  [L3.5 → BRAID] Wired to SediMemory for Warp traversal carving")
            except Exception:
                pass
        if systems.get('contradiction_ledger') is not None and hasattr(braid, 'connect_contradiction_ledger'):
            try:
                braid.connect_contradiction_ledger(systems['contradiction_ledger'])
            except Exception:
                pass
        # Register as a WARP actuator under the routing key it emits as
        # demand.source (its _warp_level_name() = 'braid_stream').
        if systems.get('warp_field') is not None:
            try:
                systems['warp_field'].register_warp_capable('braid_stream', braid)
                if verbose:
                    print("  [WARP] ThoughtBraid registered as actuator ('braid_stream')")
            except Exception:
                pass

        if verbose:
            print("  [BRAID] Continuous thought braid online (2s tick)")

    except Exception as e:
        systems['_thought_braid'] = None
        systems['_thought_braid_thread'] = None
        if verbose:
            print(f"  [BRAID] Unavailable: {e}")


# ---------------------------------------------------------------------------
# 2. begin_response_turn
# ---------------------------------------------------------------------------

def begin_response_turn(
    systems: Dict[str, Any],
    *,
    user_text: str = "",
    turn_tick: int = 0,
) -> None:
    """
    CALL SITE 2 — Top of _run_live_response_turn, after turn_tick is assigned.

    Taps the braid, builds a ThoughtState via ThoughtIntegrationSpace,
    carries it forward through ThoughtContinuity, and stores it in systems.

    This is the STATE phase of:
    STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING

    Stores:
        systems['_current_thought_state']  — ThoughtState (reasoning-safe)
        systems['_current_braid_slice']    — ThoughtStreamSlice (raw tap)
        systems['_turn_thought_tick']      — turn_tick for this response
    """
    try:
        from aurora_thought_formation import (
            ActiveSelfState,
            ThoughtIntegrationSpace,
            get_continuity,
        )

        # Snapshot self-state
        self_state = ActiveSelfState.load(systems)

        # Tap braid (non-consuming)
        braid = systems.get('_thought_braid')
        braid_slice = braid.tap() if braid is not None else None
        systems['_current_braid_slice'] = braid_slice

        # Build integration space with braid slice
        space = ThoughtIntegrationSpace(self_state, braid_slice=braid_slice)

        # Prime with carry-forward state from last thought
        continuity = get_continuity()
        continuity.prime_integration_space(space)

        # Register turn-level process contexts
        turn_contexts = _build_turn_process_contexts(systems, tick=turn_tick, user_text=user_text)
        for ctx in turn_contexts:
            space.register(ctx)

        # Structural reasoning track — runs parallel with semantic braid
        _cr = systems.get('constraint_reasoner')
        _constraint_trace = None
        if _cr is not None:
            try:
                _cr_profile = getattr(self_state, 'pressure_vec', None) or _cr.current_profile()
                _constraint_trace = _cr.reason(_cr_profile, depth=3, user_text=user_text)
                systems['_constraint_trace'] = _constraint_trace
                _cr_ctx = _cr.to_process_context(_constraint_trace, tick=turn_tick)
                if _cr_ctx is not None:
                    space.register(_cr_ctx)
            except Exception:
                _constraint_trace = None
                systems['_constraint_trace'] = None

        # Integrate — emotion firewall fires internally
        thought_state = space.integrate()

        # Alignment check: structural vs semantic — emit WarpDemand if divergent
        if _cr is not None and _constraint_trace is not None:
            try:
                _cr.integrate(_constraint_trace, thought_state)
            except Exception:
                pass

        # Carry forward through continuity
        thought_state = continuity.carry_forward(thought_state)

        systems['_current_thought_state'] = thought_state
        systems['_turn_thought_tick'] = turn_tick

    except Exception:
        # Degrade gracefully — downstream pipeline continues without braid context
        systems['_current_thought_state'] = None
        systems['_current_braid_slice'] = None
        systems['_turn_thought_tick'] = turn_tick


# ---------------------------------------------------------------------------
# 3. begin_expression
# ---------------------------------------------------------------------------

def begin_expression(systems: Dict[str, Any]) -> None:
    """
    CALL SITE 3 — Just BEFORE perception.express() is called.

    Anchors the StreamingExpressionLayer to the current ThoughtState.
    Returns initial ExpressionGuidance (stored in systems for downstream use).

    This is the start of the EXPRESSION phase.

    Stores:
        systems['_expression_layer']       — StreamingExpressionLayer instance
        systems['_expression_guidance']    — initial ExpressionGuidance
    """
    try:
        from aurora_streaming_expression import make_expression_layer

        thought_state = systems.get('_current_thought_state')
        if thought_state is None:
            return

        # Create a fresh expression layer for this response
        # (not the singleton — each response gets its own instance)
        layer = make_expression_layer()
        initial_guidance = layer.begin(thought_state)

        systems['_expression_layer'] = layer
        systems['_expression_guidance'] = initial_guidance

        # Stamp axis emphasis into pipeline state if available
        try:
            pipeline_state = systems.get('_pipeline_state') or {}
            if isinstance(pipeline_state, dict):
                pipeline_state['braid_lane_lean'] = initial_guidance.lane_lean
                pipeline_state['braid_anchor_axes'] = list(initial_guidance.anchor_axes)
        except Exception:
            pass

        # Wire SemanticIntentionBridge — drive composer from ThoughtState
        try:
            from aurora_semantic_intention_bridge import SemanticIntentionBridge
            thought_state = systems.get('_current_thought_state')
            expression_guidance = systems.get('_expression_guidance')
            perception = systems.get('perception')
            composer = getattr(perception, 'composer', None) if perception else None
            if thought_state is not None and composer is not None:
                sib = SemanticIntentionBridge()
                intention = sib.extract(
                    thought_state,
                    expression_guidance=expression_guidance,
                    systems=systems,
                )
                sib.apply(intention, composer)
                systems['_current_semantic_intention'] = intention
        except Exception:
            pass

    except Exception:
        systems['_expression_layer'] = None
        systems['_expression_guidance'] = None


# ---------------------------------------------------------------------------
# 4. checkpoint_expression
# ---------------------------------------------------------------------------

def checkpoint_expression(
    systems: Dict[str, Any],
    expression_text: str = "",
) -> Optional[Dict[str, Any]]:
    """
    CALL SITE 4 — Just AFTER perception.express() assigns the expression text.

    Re-taps the braid against the generated text.
    Returns a guidance dict if a meaningful nudge was computed, else None.

    In a batch expression system (non-streaming), this fires once after the
    full expression is generated. The guidance is available for post-processing
    (grammar engine, tone reconciliation) to apply a subtle directional shift.

    Stores:
        systems['_expression_guidance']    — updated ExpressionGuidance (or unchanged)
        systems['_expression_nudge']       — nudge dict if significant, else None

    Returns:
        Dict with nudge data, or None if no significant nudge.
    """
    try:
        layer = systems.get('_expression_layer')
        if layer is None or not expression_text:
            return None

        guidance = layer.checkpoint(expression_text)
        if guidance is None:
            return None

        systems['_expression_guidance'] = guidance

        # Only return nudge data if strength is meaningful
        if guidance.nudge_strength < 0.05:
            systems['_expression_nudge'] = None
            return None

        nudge_data = {
            'nudge_strength': guidance.nudge_strength,
            'lane_lean': guidance.lane_lean,
            'axis_emphasis': dict(guidance.axis_emphasis),
            'carry_topics': list(guidance.carry_topics),
            'release_topics': list(guidance.release_topics),
            'braid_tick': guidance.braid_tick,
            'dominant_shift_axis': guidance.dominant_shift_axis(),
        }
        systems['_expression_nudge'] = nudge_data

        # Optionally stamp nudge into pipeline_state for grammar engine
        try:
            _ps = systems.get('_pipeline_state') or {}
            if isinstance(_ps, dict) and nudge_data:
                _ps['braid_nudge_lane'] = nudge_data['lane_lean']
                _ps['braid_nudge_strength'] = nudge_data['nudge_strength']
        except Exception:
            pass

        return nudge_data

    except Exception:
        systems['_expression_nudge'] = None
        return None


# ---------------------------------------------------------------------------
# 5. complete_expression
# ---------------------------------------------------------------------------

def complete_expression(systems: Dict[str, Any], state: Any) -> None:
    """
    CALL SITE 5 — After grammar engine + tone reconciliation, before return.

    Feeds the final response text back into the braid — closing the loop.

    This is the RE-ENTRY signal in:
    STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING

    The braid's predictive stream is reshaped by what was just expressed.
    The next thought will have been informed by this response.
    Thought does not end here — it continues, now carrying what was said.

    Cleans up:
        systems['_expression_layer']    → None (layer is per-response)
        systems['_expression_nudge']    → None
    """
    try:
        layer = systems.get('_expression_layer')
        thought_state = systems.get('_current_thought_state')

        if layer is None or thought_state is None:
            return

        # Get final response text from state
        final_text = ""
        try:
            final_text = str(getattr(state, 'response_content', '') or '').strip()
        except Exception:
            pass

        if not final_text:
            return

        # Close the expression loop — feeds back into braid predictive stream
        layer.complete(final_text, thought_state)

        # Log RE-ENTRY event for diagnostic use
        try:
            systems['_last_reentry_tick'] = int(
                systems.get('_turn_thought_tick') or 0
            )
            systems['_last_reentry_text_len'] = len(final_text)
        except Exception:
            pass

    except Exception:
        pass
    finally:
        # Always clean up per-response state
        systems['_expression_layer'] = None
        systems['_expression_nudge'] = None


# ---------------------------------------------------------------------------
# Shutdown helper
# ---------------------------------------------------------------------------

def shutdown_thought_braid(systems: Dict[str, Any]) -> None:
    """
    Clean braid shutdown. Call when Aurora is shutting down.
    Stops the background thread gracefully.
    """
    try:
        thread = systems.get('_thought_braid_thread')
        if thread is not None and hasattr(thread, 'stop'):
            thread.stop()
        systems['_thought_braid_thread'] = None
        systems['_thought_braid'] = None
    except Exception:
        pass
