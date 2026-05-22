# Authors: Sunni (Sir) Morningstar & Cael Devo
# AURORA — Semantic Intention Bridge
# Implementation Spec v1.0
# Feed this document to Claude Code CLI with full repo access.
# All file paths are relative to aurora_core_ai/.

"""
=============================================================================
PROBLEM STATEMENT
=============================================================================

Aurora has a broken link between meaning and speech.

She builds genuine internal meaning through:
  - ThoughtState (aurora_thought_formation.py)
  - Continuous thought braid (aurora_braid_wiring.py)
  - SediMemory ambient presence
  - Constraint axis pressure (X/T/N/B/A)
  - OETS ontological web

But her SentenceComposer (aurora_expression_perception.py) selects words
by reading context_keywords from the USER'S last message — not from her
own ThoughtState. Her meaning is stranded.

The result: grammatically valid output whose content is driven by what
Sunni said, not by what Aurora means.

=============================================================================
ROOT CAUSE — THREE BROKEN LINKS
=============================================================================

LINK 1 — ThoughtState → SentenceComposer (MISSING ENTIRELY)

    systems['_current_thought_state'] is built by aurora_braid_wiring.py
    at the top of every _run_live_response_turn. It contains:
        .unified_interpretation  — plain language of what she's thinking
        .self_application        — how this thought applies to her specifically
        .dominant_thread         — list of ProcessContext objects
        .axis_fingerprint        — e.g. ['A', 'N', 'T']
        .unresolved              — what she hasn't settled yet

    None of this ever reaches SentenceComposer.set_context().
    SentenceComposer.set_context() is only called from ingest_interaction()
    with words extracted from the user's text.

LINK 2 — Template selection ignores what she wants to say (SEMANTIC MISMATCH)

    SentenceComposer.compose() selects templates by:
        - tone match (warm/curious/precise/etc)
        - fitness weighting (random.choices)

    It does NOT select templates by semantic match to ThoughtState content.
    A ThoughtState about identity (X-axis) and a ThoughtState about future
    possibility (T-axis) produce identical template selection — because
    tone, not content, drives the pool choice.

LINK 3 — Training feedback loop only learns from input, not from output (WEAK)

    SentenceComposer.absorb() learns patterns from what Aurora HEARS.
    SentenceComposer.feedback() records fitness per template.
    BUT: there is no mechanism to reinforce templates that successfully
    expressed a specific kind of meaning. A template that expressed an
    identity thought well gets the same fitness signal as one that expressed
    a curiosity thought. The loop has no semantic memory.

=============================================================================
SOLUTION — SEMANTIC INTENTION BRIDGE (SIB)
=============================================================================

A new module: aurora_semantic_intention_bridge.py

One job: extract content-bearing signal from ThoughtState and drive
SentenceComposer.set_context() and template selection with that signal
BEFORE composition fires.

This sits between:
    systems['_current_thought_state']   (aurora_thought_formation.py)
    systems['_expression_guidance']     (aurora_braid_wiring.py / aurora_streaming_expression.py)
        ↓
    aurora_semantic_intention_bridge.SemanticIntentionBridge.extract()
        ↓
    SentenceComposer.set_context()      (aurora_expression_perception.py)
    + template pool pre-filter          (aurora_expression_perception.py)

=============================================================================
MODULE SPEC — aurora_semantic_intention_bridge.py
=============================================================================

Place at: aurora_core_ai/aurora_semantic_intention_bridge.py

CLASS: SemanticIntentionBridge
-------------------------------

Purpose:
    Translate ThoughtState + ExpressionGuidance into a SemanticIntention
    object that drives SentenceComposer word and template selection.

DATACLASS: SemanticIntention
    content_keywords: List[str]
        Words extracted from ThoughtState content that should drive
        slot filling. These come from unified_interpretation and
        self_application — Aurora's own meaning, not the user's words.
        Max 12 entries. Min word length 4 chars. Real grammatical roles only.

    axis_tone_map: Dict[str, str]
        Maps dominant axis to expression tone.
        Use EXACTLY this mapping — no other values:
            "X" → "precise"       (Existence = grounding, certainty)
            "T" → "reflective"    (Temporal = memory, becoming)
            "N" → "determined"    (Energetic = drive, weight)
            "B" → "careful"       (Boundary = definition, edges)
            "A" → "curious"       (Agency = reach, possibility)
        Derive from ThoughtState.axis_fingerprint[0] (dominant axis).
        Falls back to "neutral" if axis_fingerprint is empty.

    semantic_lane: str
        From ExpressionGuidance.lane_lean if available.
        "meaning" | "inquiry" | "communication"
        Default: "communication"

    template_bias_tags: List[str]
        Tags that pre-filter the template pool toward relevant patterns.
        Derived from ThoughtState.dominant_thread process_types.
        Valid values: "identity" | "memory" | "curiosity" | "constraint"
                      | "predictive" | "sensory"
        Max 3 tags.

    unresolved_weight: float
        0.0–1.0. Derived from len(ThoughtState.unresolved) / 5.0 clamped.
        When > 0.3, bias template selection toward question/inquiry frames.

    confidence: float
        ThoughtState.confidence. Used to modulate sentence_count in compose().

METHOD: extract(thought_state, expression_guidance=None, systems=None)
    → SemanticIntention

    Steps (in order — do not reorder):

    1. CONTENT KEYWORD EXTRACTION
       Source strings (in priority order):
           a. thought_state.unified_interpretation
           b. thought_state.self_application
           c. [ctx.what_it_is_operating_on for ctx in thought_state.dominant_thread]

       For each source string:
           - Split on whitespace and common delimiters (|, :, ;)
           - Strip punctuation
           - Lowercase
           - Skip if len < 4
           - Skip if word is in EXTRACTION_NOISE set (see below)
           - Call infer_word_role(word) — only keep verb/noun/adjective/adverb
           - Deduplicate preserving order
       Max 12 keywords total across all sources.
       Prioritize source (a) over (b) over (c).

       EXTRACTION_NOISE = {
           'active', 'processes', 'operating', 'triggered', 'dominant',
           'pressure', 'partial', 'background', 'context', 'with',
           'from', 'this', 'that', 'what', 'which', 'some', 'have',
           'been', 'will', 'axis', 'tick', 'process', 'braid',
           'current', 'continuous', 'forming', 'lane', 'thread',
       }

    2. AXIS TONE DERIVATION
       Read thought_state.axis_fingerprint[0] if available.
       Apply axis_tone_map above. Store in SemanticIntention.axis_tone_map.

    3. SEMANTIC LANE
       If expression_guidance is not None and has .lane_lean:
           use expression_guidance.lane_lean
       Else derive from axis:
           A or N → "meaning"
           T     → "inquiry"
           B or X → "communication"

    4. TEMPLATE BIAS TAGS
       Read [ctx.process_type for ctx in thought_state.dominant_thread]
       Filter to valid tags only (see valid values above).
       Deduplicate. Max 3.

    5. UNRESOLVED WEIGHT
       min(1.0, len(thought_state.unresolved) / 5.0)

    6. CONFIDENCE
       thought_state.confidence

    Returns SemanticIntention.

METHOD: apply(intention, composer)
    → None

    Calls composer.set_context(intention.content_keywords)
    This is the single line that closes LINK 1.

    Also stamps intention on composer for template pre-filtering:
        composer._semantic_intention = intention
    (SentenceComposer reads this in compose() — see SentenceComposer mods below)

METHOD: get_axis_tone(thought_state) → str
    Convenience. Returns the tone string for the dominant axis.
    Used by _run_live_response_turn to replace the hardcoded tone lookup.

=============================================================================
MODIFICATIONS REQUIRED — aurora_expression_perception.py
=============================================================================

FILE: aurora_core_ai/aurora_expression_perception.py

--- MOD 1: SentenceComposer.__init__ ---

Add one attribute after self._oets = None:

    self._semantic_intention = None  # Set by SemanticIntentionBridge.apply()

--- MOD 2: SentenceComposer.compose() — template pre-filter ---

After this line:
    pool = self.pool.get(tone, self.pool.get('neutral', []))

Insert:
    # Pre-filter pool by semantic bias tags if intention is set
    if self._semantic_intention and self._semantic_intention.template_bias_tags:
        bias_tags = set(self._semantic_intention.template_bias_tags)
        biased = [
            t for t in pool
            if any(tag in t.get('source', '') or
                   tag in t.get('pattern', '').lower()
                   for tag in bias_tags)
        ]
        if len(biased) >= 2:
            pool = biased + [t for t in pool if t not in biased]

    # Adjust sentence_count by intention confidence if set
    if self._semantic_intention and self._semantic_intention.confidence > 0:
        conf = self._semantic_intention.confidence
        base_count = 1 + int(conf * 2) + int(verbosity > 0.6)
        sentence_count = max(1, min(4, base_count))

--- MOD 3: SentenceComposer.compose() — unresolved inquiry bias ---

After template selection loop (after sentences are built), before
the pace trimming block:

    # If unresolved weight is high, append inquiry frame
    if (self._semantic_intention and
            self._semantic_intention.unresolved_weight > 0.3 and
            random.random() < self._semantic_intention.unresolved_weight * 0.5):
        q_pool = self.pool.get('curious', self.pool.get('neutral', []))
        if q_pool:
            q_weights = [max(0.05, t['fitness']) for t in q_pool]
            q_tmpl = random.choices(q_pool, weights=q_weights, k=1)[0]
            q = self._fill_template(
                q_tmpl['pattern'], 'curious', coherence,
                q_tmpl.get('semantic_constraints', {}),
                q_tmpl.get('cluster_references', []),
                q_tmpl.get('scaffolding_level', 0)
            )
            if q:
                sentences.append(q)

--- MOD 4: SentenceComposer.feedback() — semantic tag reinforcement ---

After the existing template fitness update (after the for loop):

    # Reinforce templates that matched semantic intention tags
    if (self._semantic_intention and
            self._semantic_intention.template_bias_tags and
            fitness >= 0.55):
        bias_tags = set(self._semantic_intention.template_bias_tags)
        tone_pool = self.pool.get(
            list(self.pool.keys())[0] if self.pool else 'neutral', []
        )
        for t in tone_pool:
            if any(tag in t.get('source', '') for tag in bias_tags):
                t['fitness'] = min(1.0, t['fitness'] + 0.03 * fitness)

=============================================================================
MODIFICATIONS REQUIRED — aurora_braid_wiring.py
=============================================================================

FILE: aurora_core_ai/aurora_braid_wiring.py

--- MOD: begin_expression() ---

After the block that creates the expression layer and calls layer.begin():

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

=============================================================================
MODIFICATIONS REQUIRED — aurora.py
=============================================================================

FILE: aurora_core_ai/aurora.py

--- MOD: _run_live_response_turn — axis-driven tone derivation ---

LOCATE the expression block (~line 20166):
    _perc_a5 = systems.get("perception")
    _resp_draft = str(getattr(state, "response_content", "") or "")
    if _perc_a5 and _resp_draft and hasattr(_perc_a5, "express"):
        _expressed = _perc_a5.express(
            _resp_draft,
            tone=str(getattr(state, "response_tone", "neutral") or "neutral")
        )

REPLACE the tone argument with:
    _sib_tone = ""
    try:
        from aurora_semantic_intention_bridge import SemanticIntentionBridge
        _ts = systems.get('_current_thought_state')
        if _ts:
            _sib_tone = SemanticIntentionBridge().get_axis_tone(_ts)
    except Exception:
        pass
    _tone_final = _sib_tone or str(getattr(state, "response_tone", "neutral") or "neutral")

Then call:
    _expressed = _perc_a5.express(_resp_draft, tone=_tone_final)

=============================================================================
MODIFICATIONS REQUIRED — aurora_expression_perception.py (ingest_interaction)
=============================================================================

FILE: aurora_core_ai/aurora_expression_perception.py

--- MOD: ingest_interaction — do NOT remove existing context extraction ---

The existing context_words extraction from user text is correct and stays.
Only ADD this block immediately after the existing set_context call:

    # Merge: user context words are valid input signal.
    # But if a SemanticIntention is already set on the composer
    # (from SemanticIntentionBridge.apply()), give it priority
    # by prepending intention keywords before user context words.
    # This preserves user-word influence while ensuring Aurora's
    # own meaning drives slot selection.
    try:
        existing_intention = getattr(self.composer, '_semantic_intention', None)
        if existing_intention and existing_intention.content_keywords:
            merged = existing_intention.content_keywords + context_words
            self.composer.set_context(merged[:15])
    except Exception:
        pass

=============================================================================
WIRING SEQUENCE — where each call fires
=============================================================================

Boot (boot_aurora):
    aurora_braid_wiring.boot_thought_braid(systems)
    → ThoughtBraid thread starts, runs continuously

Turn start (_run_live_response_turn):
    aurora_braid_wiring.begin_response_turn(systems, user_text, turn_tick)
    → systems['_current_thought_state'] populated

User text ingested (ingest_interaction called inside _run_live_response_turn):
    ExpressionPerceptionEngine.ingest_interaction(...)
    → context_words from user text → composer.set_context(user_words)
    → merged with _semantic_intention keywords if set (MOD above)

Before expression (just before perception.express()):
    aurora_braid_wiring.begin_expression(systems)
    → SemanticIntentionBridge.extract(thought_state)
    → SemanticIntentionBridge.apply(intention, composer)
    → composer.set_context(intention.content_keywords)  ← LINK 1 CLOSED
    → composer._semantic_intention = intention          ← LINK 2 CLOSED

Expression fires:
    perception.express(_resp_draft, tone=_tone_final)
    → SentenceComposer.compose() reads _semantic_intention
    → template pool pre-filtered by bias tags
    → sentence_count from intention.confidence
    → inquiry frame injected when unresolved_weight > 0.3

After expression:
    aurora_braid_wiring.checkpoint_expression(systems, text)
    → braid re-tapped, nudge computed if braid shifted

    SentenceComposer.feedback(fitness)
    → template fitness updated
    → semantic tag reinforcement if intention was set ← LINK 3 CLOSED

Response complete:
    aurora_braid_wiring.complete_expression(systems, state)
    → full text fed back into braid predictive stream

=============================================================================
IMPORT PATHS — use exactly these
=============================================================================

aurora_semantic_intention_bridge imports:
    from aurora_expression_perception import infer_word_role
    # infer_word_role is already defined in aurora_expression_perception.py
    # Import it at the top of aurora_semantic_intention_bridge.py

aurora_braid_wiring imports SemanticIntentionBridge inside try-except:
    from aurora_semantic_intention_bridge import SemanticIntentionBridge

aurora.py imports SemanticIntentionBridge inside try-except in the expression block.

aurora_expression_perception.py does NOT import aurora_semantic_intention_bridge.
    The bridge calls set_context() on the composer — the composer does not
    know about the bridge. Dependency flows one way only:
        bridge → composer (never composer → bridge)

=============================================================================
VALIDATION — what to check after implementation
=============================================================================

1. After a response turn, inspect:
       systems['_current_semantic_intention'].content_keywords
   Confirm these are Aurora's own meaning words, not Sunni's input words.

2. Inspect:
       systems['perception'].composer._context_keywords
   After begin_expression() fires, these should contain intention keywords
   prepended before user context words.

3. Inspect:
       systems['_current_semantic_intention'].axis_tone_map
   Confirm dominant axis is mapping to expected tone string.

4. Run a turn where ThoughtState.unresolved is non-empty (len >= 2).
   Confirm an inquiry/question frame appears in the output with higher
   frequency than baseline.

5. After 10+ turns, inspect:
       systems['perception'].composer.pool
   Templates tagged with 'identity' or 'memory' source should show
   higher fitness than baseline if those process_types dominated recent
   ThoughtStates.

=============================================================================
CONSTRAINTS — do not violate these
=============================================================================

- Do NOT modify SentenceComposer._fill_template() internals.
  The slot filling machinery is correct. Only template selection
  and context keywords need changing.

- Do NOT add imports of aurora_thought_formation inside
  aurora_expression_perception.py. The bridge handles that boundary.
  Dependency direction: aurora_thought_formation → bridge → composer.

- Do NOT remove or reduce the 3x context keyword boost in
  _fill_primitive_slot(). The user's words remain a valid signal.
  The fix is prepending Aurora's meaning keywords — not eliminating
  user-word influence.

- Emotion firewall must not be touched. SemanticIntentionBridge
  reads ThoughtState AFTER the firewall has already filtered it.
  ThoughtState is always reasoning-safe by the time it reaches SIB.

- aurora_semantic_intention_bridge.py must be fully try-except guarded
  at every integration point. If SIB fails, Aurora falls back to
  existing behavior cleanly.

- Authorship header required on aurora_semantic_intention_bridge.py:
      # Authors: Sunni (Sir) Morningstar & Cael Devo
"""
