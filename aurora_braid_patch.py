# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_braid_patch.md
Precise insertion instructions for wiring aurora_braid_wiring.py into aurora.py.

Five surgical insertions. No existing lines are modified or removed.
Each block is additive only.

Landmark strings are unique in aurora.py — use them to locate exactly.
"""

# ============================================================================
# PATCH 1 of 5 — BOOT: Start the thought braid thread
# ============================================================================
# LOCATE this line in aurora.py (near line 24144):
#
#     _install_support_constraint_surfaces(systems)
#
#     return systems
#
# INSERT these lines BETWEEN those two (after _install, before return):

    # ---- THOUGHT BRAID — continuous cognitive thread ----
    try:
        from aurora_braid_wiring import boot_thought_braid
        boot_thought_braid(systems, verbose=verbose)
    except Exception:
        pass


# ============================================================================
# PATCH 2 of 5 — STATE: Build ThoughtState at turn start
# ============================================================================
# LOCATE this block in _run_live_response_turn (near line 25282):
#
#     if turn_tick is None:
#         turn_tick = int(getattr(working_memory, 'turn_count', 0) or 0) + 1
#
# INSERT these lines IMMEDIATELY AFTER (after turn_tick assignment):

    # ---- BRAID: Tap thought state for this turn ----
    try:
        from aurora_braid_wiring import begin_response_turn
        begin_response_turn(systems, user_text=user_text, turn_tick=turn_tick)
    except Exception:
        pass


# ============================================================================
# PATCH 3 of 5 — EXPRESSION ANCHOR: begin_expression before perception.express
# ============================================================================
# LOCATE this block in _run_live_response_turn (near line 20161):
#
#     _preserve_literal_response = bool(systems.pop("_preserve_literal_response_once", False))
#     _skip_surface_expression = bool(systems.pop("_skip_surface_expression_once", False))
#
#     if not _preserve_literal_response:
#         try:
#             if _skip_surface_expression:
#
# INSERT these lines BETWEEN the _skip_surface_expression assignment and
# the `if not _preserve_literal_response:` block:

    # ---- BRAID: Anchor expression layer before perception.express() ----
    try:
        from aurora_braid_wiring import begin_expression
        begin_expression(systems)
    except Exception:
        pass


# ============================================================================
# PATCH 4 of 5 — EXPRESSION CHECKPOINT: fire after perception.express returns
# ============================================================================
# LOCATE this block (near line 20173):
#
#             if _perc_a5 and _resp_draft and hasattr(_perc_a5, "express"):
#                 _expressed = _perc_a5.express(_resp_draft, tone=str(getattr(state, "response_tone", "neutral") or "neutral"))
#                 if _expressed and isinstance(_expressed, str) and len(_expressed.split()) >= 4:
#                     state.response_content = _expressed
#         except Exception:
#             pass
#
# INSERT these lines IMMEDIATELY AFTER the except Exception: pass block
# (still inside the `if not _preserve_literal_response:` block):

    # ---- BRAID: Checkpoint after expression generated ----
    try:
        from aurora_braid_wiring import checkpoint_expression
        _braid_draft = str(getattr(state, "response_content", "") or "")
        checkpoint_expression(systems, expression_text=_braid_draft)
    except Exception:
        pass


# ============================================================================
# PATCH 5 of 5 — RE-ENTRY: Feed final text back into braid
# ============================================================================
# LOCATE this comment (near line 20450):
#
#     # Build resp_A
#     resp_A = _MiniResp(state.response_content, state.response_tone, state.response_confidence)
#
# INSERT these lines IMMEDIATELY BEFORE the `# Build resp_A` comment:

    # ---- BRAID: Complete expression loop — RE-ENTRY signal ----
    try:
        from aurora_braid_wiring import complete_expression
        complete_expression(systems, state)
    except Exception:
        pass
