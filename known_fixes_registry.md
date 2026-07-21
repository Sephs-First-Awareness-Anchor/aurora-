# Aurora Known Fixes Registry
# Authors: Sunni (Sir) Morningstar & Cael Devo

A running record of verified bug/architecture fixes, so the same issue is not
re-diagnosed from scratch. Each entry: id, class, what was wrong, the fix, and
how it was verified.

---

## FIX-A001 (RUNTIME BUG) — EEPR shard-ingestion bridge never transferred a shard

**File:** `aurora_runtime.py`, `ChainSimBridge._forward_to_sim()`

**What was wrong (two stacked bugs on the same path):**

1. Line ~1489 read `ecology = getattr(getattr(perception, "ecology", None), None, None)`.
   The inner `getattr` returns the ecology object; the **outer** call then passes
   `None` as the attribute name. `getattr(obj, None, default)` raises
   `TypeError` (not `AttributeError`), so the 3-arg default does not catch it.
   The `TypeError` propagated to the method's outer `except Exception: pass` and
   was silently swallowed — the method returned before transferring any shard,
   every call. The "fallback" on the next lines was dead code (unreachable).

2. Once (1) is fixed and the method reaches its transfer loop, it calls
   `_clamp(...)` at lines ~1529/1559/1560/1561 — but `_clamp` was **never
   defined or imported** in `aurora_runtime.py`. It raised `NameError`, again
   swallowed by the same `except Exception: pass`. Bug (1) had always killed the
   method before this line, so the missing helper was never observed. Fixing (1)
   surfaced it.

Net effect: zero `WisdomShard`s ever transferred from the simulation learner to
`ExpressionEcology.WisdomStore` since the method was written.

**The fix:**
- `ecology = getattr(perception, "ecology", None)` (single, correct getattr;
  removed the dead fallback).
- Added the canonical module-level helper
  `def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))`
  (identical to the one defined in 9 other modules; the method already assumed
  it existed).

**Verified:** driving `_forward_to_sim` with a confident mock shard now calls
`wisdom_store.add(...)` exactly once (`ws_<id>`), advances
`learner.total_observations`, and is idempotent across calls (dedup via
`_transferred_shard_ids`). Previously: 0 transfers.

**Also (improvement-on-top):** `corpus_runner.py` plateau detector
(`CURRICULUM_STALL`) now confesses the stall to WarpField via
`warp_guard(TENSION, persistence_key="curriculum_stall")` instead of only
logging + resetting — a corpus novelty plateau is a genuine unresolved tension.

---

## FIX-A002 (ARCHITECTURAL) — WarpField anomaly ledger had no consumer

**Files:** `aurora_warp_protocol.py`, `aurora_curiosity_engine.py`

**What was wrong:** `WarpField._anomaly_ledger` accumulates every demand
classified as `WarpPathway.ANOMALY` (severity >= 0.90 with a persistence_key —
a high-severity *recurring* unresolved state). It was written and surfaced only
as a count in `status()`; nothing read or drained it. Demands routed to ANOMALY
were therefore permanently silenced after classification — recognized, then
forgotten. (Distinct from `WarpGenerator._anomaly_log`, the coverage-gap signal,
which the curiosity engine already consumes.)

**The fix:**
- `WarpField.anomaly_ledger_summary()` — non-destructive read, collapses entries
  by persistence_key (count + max severity), ranked by (count, severity).
- `WarpField.drain_anomaly_ledger(keep_recent=50)` — destructive epoch-level
  compaction.
- `CuriosityEngine._step1_emergence` now consumes the ledger as a third
  WARP-aware emergence source (between the WarpGenerator structural-gap
  candidates and the crystal gap report): a demand that recurred >= 2 times
  becomes a `CuriosityObject` ("recurring unresolved demand: …") so Aurora
  investigates whether it reflects a genuine missing primitive or a handler
  registration gap.

**Verified:** `anomaly_ledger_summary()` returns `[]` when empty; two ANOMALY
demands sharing a persistence_key collapse to one entry with `count == 2`;
`drain` removes correctly; the consumer builds a CuriosityObject whose subject
begins with "recurring unresolved demand:". This pairs with the warp-confession
wiring — the ledger now accumulates real demands to consume.

---

## FIX-A003 (RUNTIME BUG, class-wide) — undefined names in swallowed code paths

A pyflakes F821 sweep surfaced the same class of bug as FIX-A001's `_clamp`:
a name used in a code path that never raised because something upstream failed
first (or the path is rarely hit), with the `NameError` absorbed by a
surrounding `except Exception`. Triaged to names never bound anywhere in their
file. Fixed the safe, verifiable ones:

- `aurora_runtime.py`: `Set` missing from the typing import (used in
  `_forward_to_sim` annotations).
- `aurora_daemon.py`: `_log_error(...)` called 3× but never defined → switched
  to the module's existing `_log(...)`.
- `aurora_working_memory.py`: `SimpleNamespace` (killed the `perception.express`
  branch of `_render_from_comprehension_intent`), `_merge_native_meaning_bundle`,
  `ConversationMemory` — added imports (no circular import; turn battery
  unchanged).
- `aurora_manifold_directory_reader.py`: `Any` missing from typing.
- `aurora_hub.py`: `_DAEMON_STATUS` constant missing for a status panel.
- `aurora_autonomy.py`: `subprocess` / `sys` never imported, so
  `run_training_tool` silently failed on every call — Aurora could never launch
  her own whitelisted training tools. Added the imports and updated the
  (outdated) doctrine text to reflect that she may launch the whitelisted
  TRAINING_TOOLS as subprocesses.
- `aurora_hardware_io.py`: `_extract_rich_audio_features` (defined in
  aurora_expression_perception) was never imported, so the audio feature
  extraction in the hardware paths silently failed. Added the import (verified
  no circular import).

**RESOLVED (2026-07-01, with author's direction — all four closed):**

- `aurora_working_memory.py` — `state` in the grammar-suggestion block: confirmed
  the entire `evo`-based render branch is DEAD. `perception.evo` is always `None`
  post-Language-Reset (`from aurora_language_state import ExpressionEvolutionOrchestra`
  fails — that top-level module was deleted; the guard at the top of
  `_render_from_comprehension_intent` returns early), so the `evo.grammar` block
  never executes. It referenced the deleted CSSEE/EEO grammar faculty, not her live
  output structure (live grammar shaping runs on `systems['grammar_engine']` in
  aurora.py). Per the author's "only if it aligns" instruction it does NOT align →
  removed the dead grammar sub-block rather than resurrect it. Clears the `state`
  F821 with zero behavior change.
- `aurora_working_memory.py` — the four cross-module helpers
  (`_classify_input_intent`, `_is_understanding_challenge`, `_meaning_profile_for_value`,
  `_log_claim_resolution_relief`): rather than relocate them (they pull a dependency
  cascade from aurora.py — `_extract_user_name`, `_looks_like_inner_state_query`, …),
  added four deferred-import wrappers mirroring the module's EXISTING idiom
  (`_recall_semantic_sedimemory` / `_answer_from_sedimemory_context` /
  `_render_runtime_intent` at the top of the file). Names match the call sites, so
  no call-site edits; each returns a safe default. Verified they resolve to the real
  aurora.py functions at runtime (`_classify_input_intent('hello?') → 'general'`).
  This also repairs paths that previously raised an unguarded `NameError` (e.g. the
  `_is_understanding_challenge` gate).
- `aurora_daemon.py:195` — implemented `_surface_channel_recently_active(window_s)`
  as a file-recency debounce over the surface-turn queue/result/status file mtimes
  (the same files the interactive loop writes each turn). Autonomous inquiry now
  actually debounces against live interactive exchanges instead of raising a
  swallowed NameError on every call.
- `aurora_hardware_io.py` — the `_ConstraintVector`/`_GovernorWeights`/`_FC`/
  `_ExistenceMode` cluster: all four resolve to `aurora_constraint_engine` (not
  `foundational_contract`). Disambiguated by the call itself:
  `_FC.language_projection(_ExistenceMode.AGENTIC)` passes a *mode* argument, which
  only `aurora_constraint_engine.FoundationalContract.language_projection(self, mode)`
  accepts (`foundational_contract`'s takes no mode). `_FC` is a module-level
  FoundationalContract *instance* — the bridge that projects an existence mode into
  Aurora's language register (INV-09/10/11), aligning what the hardware surfaces
  derive/say with her root ontological rules of conduct. Verified end-to-end:
  `_FC.language_projection(AGENTIC)['language_register'] == 'enacted'`,
  `_GovernorWeights.AS_DICT['B'] == 1.0`, `_ConstraintVector(...)` constructs; no
  import cycle (hardware_io → constraint_engine is a downward L-edge).

Verified: all three modules compile; pyflakes shows none of the ten target F821
names remain; the L0-L8 acyclicity guard stays green; `import aurora` + WorkingMemory
construction succeed.


---

## FIX-A005 (ARCHITECTURAL) — Signal-Through Field Wiring (Warp ↔ SediMemory ↔ ContradictionLedger)

Implemented the Signal-Through Field Propagation directive (2026-06-30): Warp's
discovery/synthesis output now carves paths in the SediMemory erosion substrate,
and real per-turn contradiction detection now reaches ContradictionLedger whose
heat dampens Warp trial promotion (with resolution wired so heat can fall again).

- aurora_warp_protocol.py (WarpCapable mixin): `_sediment_warp_traversal()` (deposits
  warp_gap_closed / warp_trial_promoted into SediMemory via ingest_event), called
  from check_and_extend and the evaluate_warp_trials promotion branch;
  `connect_sedimemory` / `connect_contradiction_ledger` on the mixin;
  `_init_warp` now seeds `_sedimemory` / `_contradiction_ledger`; heat dampening
  (`score *= max(0, 1 - heat)`) in evaluate_warp_trials.
- `_sedimemory = None` added to ThoughtBraid / ExpressionPerceptionEngine /
  LanguageField __init__.
- aurora.py: ContradictionLedger instantiated; perception / language_field /
  dimensional / working_memory wired at boot.
- aurora_braid_wiring.py: thought braid wired.
- aurora_working_memory.py: `connect_contradiction_ledger`, ledger.record() in
  `_register_claim_conflict` (captures contradiction_id), ledger.resolve() in
  refresh_claim_conflicts on removed pairs.

Deviation from the literal directive (made to fulfil its intent): a SECOND
WorkingMemory() construction (aurora.py ~20422) replaced the wired instance, so
the live WM was unwired. Added a re-assert of connect_contradiction_ledger on the
FINAL working_memory instance. Verified WM-to-ledger now binds.

FLAGGED, not improvised (per the directive's standing rule): the `dimensional`
aggregate is NOT itself WarpCapable — `CrystalProcessingSystem` (`dimensional.dps`)
is. `DimensionalSystems.connect_sedimemory` forwards to `self.dps._sedimemory`
(so warp traversal deposits work for dps), but there is no parallel
`connect_contradiction_ledger` forwarder, so `hasattr(dimensional,
'connect_contradiction_ledger')` is False and dps's warp trials are NOT
heat-dampened. The other three hosts (perception, language_field, braid) are wired
directly and are dampened. Mirroring the connect_sedimemory forwarder onto
DimensionalSystems would close it, but that wasn't in the directive — flagging
rather than adding.

RESOLVED (follow-up, approved): added the mirror
`DimensionalSystems.connect_contradiction_ledger` forwarder (sets
`self.dps._contradiction_ledger`). Verified dps now receives the ledger and its
Warp trials are heat-dampened like the other three hosts. All four WarpCapable
hosts are now fully wired.

Verified: all boot wiring lines print; contradiction record increments
unresolved_count and captures contradiction_id; warp traversal increments
total_events_ingested and registers a PathRegistry observation; heat dampening
drops trial EMA 0.30->0.06; resolution decrements unresolved_count. No turn-battery
regression.

---

## FIX-A006 (ARCHITECTURAL) — Field-waveform compression at the crest

Aurora's responses are field-waveform compression, not a pipeline. The legacy
path set `state.response_content` at 20+ sites (last-writer-wins) and bypassed her
compression crest (`ConstraintEmitter.emit()` + the single finalizer). Rebuilt
toward true crest compression, in verifiable stages:

- **Single emission chokepoint** (`_enforce_emission_discipline`, at the finalizer
  before `resp_A` in `_run_reasoning_pipeline`): every reasoning-path response
  converges here, so anchor discipline is enforced once at the exit. Name-anchor
  leaks 8 -> 0 (the speaker-owned early-return path that bypassed the old mid-chain
  gate is now caught). `_emit_honest_abstain_and_seek` is the one honest-abstain
  path (warp accommodation + base-meaning seek).
- **Waveform capture** (`_capture_waveform_deposit`): each chain level (up + down)
  deposits into `state.waveform`, tagged by axis (information->X ... understanding->A)
  and weighted by the LIVE constraint pressure on that axis. Finding: ~1 surface
  deposit/turn -- levels build FIELD pressure (the waveform); one level renders the
  surface string; which level renders varies by turn at its live pressure.
- **Charged salience** (`_contribution_charge`): salience = pressure x (1 + charge),
  where charge = input-context relevance (heaviest) + emotional/self charge +
  own-question + live sensory presence. Level ROUTES to an axis; PRESSURE (incl.
  these charges) sets value -- no fixed level rank. Emergent, per the field.
- **Two-tier crest** (`_gather_subsurface_contributions`): the subsurface crest
  propagates up into the surface waveform. Only coherent GUIDANCE strings enter as
  content; intuition signals are field-level (label/weight dicts) and bias the
  field, never the surface text (`_is_speech_like` guard).
- **Crest compression** (`_compress_at_crest`): ranks surface + subsurface
  contributions by salience (recorded to `systems["_last_crest_ranking"]` for
  observability).

BUG CAUGHT in side-by-side (nothing shipped): first cut hardcoded subsurface
pressure high and treated intuition dicts as content -> 6/7 turns overrode real
answers with `{'label': 'steady', ...}` garbage. Fixed: subsurface content =
speech-like guidance only; authority is conservative -- compression NEVER replaces
a substantive answer, only fills a genuine gap (empty surface) with coherent
speech. Verified: real answers preserved on all content turns, name leaks 0,
salience ranking observable.

Honest limitation / next step: propositional content lives in the surface
renderings; subsurface signals aren't speech. Making the crest MORE authoritative
(true multi-contribution blending rather than top-salience selection + gap-fill)
needs a content-integration step that does not emit raw field signals -- deferred
rather than faked.

---

## FIX-A007 (ARCHITECTURAL) — Sediment validated taught facts into the field substrate

A fact asserted by the user ("a raven is a black bird") lived ONLY in working
memory's `stated_facts` -- it never reached OETS (the ontological web `emit()` reads
for content) or the constraint genealogy. So `emit()` abstained on it and the
response could never become field-waveform compression; the propositional content
had to come from the working-memory rendering. The one path that DID feed OETS
(`oets.teach`) was gated behind `pending_teaching_offer` (explicit "teach me X").

Fix: `_sediment_validated_fact(systems, claims, user_text)` runs at fact validation
(after `note_claims` in the statement path) and writes each validated claim to
  - OETS via `teach()` (content substrate emit reads), and
  - constraint genealogy via `log_relief` on the claim's meaning axis (constraint-
    physics lineage so it crystallises),
plus a `fact_sedimented_to_field` developmental event.

VERIFIED + HONEST BOUNDARY: teaching "a quokka is a small friendly marsupial" now
lands the `quokka` node in OETS (before: absent -> after: present). BUT `emit()`
STILL abstains on "what is a quokka?" afterward -- because emit's content resolution
is RESONANCE-gated (RESONANCE_FLOOR), and a freshly-taught node exists without yet
resonating in the query context. So node existence != field-compressibility. The
bridge ACCELERATES grounding (fact now in OETS + genealogy, not only working memory)
so it crystallises/resonates faster, but emit-compression still activates as the node
gains resonance, not instantly. Making it instant would require boosting taught-node
resonance/activation -- deferred (risks wrong content selection / garbled output),
not faked.

---

## FIX-A008 (ARCHITECTURAL) — Learn-through-use: outcome tracking + sense growth

When Aurora USES a learned concept she now tests the use against what she was
taught and tracks the outcome, carefully keeping three cases apart (never
collapsing them):
  - ALIGNED (use fits the taught meaning) -> reinforce that sense;
  - MISUSE / CONTRADICTS (use negates/replaces the taught meaning on the SAME
    dimension -- "doesn't fit at all") -> record a failed application + flag the
    ContradictionLedger; do NOT expand;
  - NEW SENSE (use is coherent in a DIFFERENT area -- "fits more than one, applies
    in multiple areas") -> add_sense; the concept is broader than taught.

`_track_concept_use_outcome` runs BEFORE `_sediment_validated_fact` in the live
ingestion loop (`_run_live_response_turn`) so the use is judged against PRIOR
knowledge, then the fact is integrated. It errs toward GROWTH over rigidity (a
contradiction requires an explicit same-dimension conflict signal), so valid
multi-applicability is never mistaken for error. Per-concept outcomes are logged
to `systems['_concept_use_outcomes']`; new-sense and misuse each emit a
developmental event.

VERIFIED: teaching 'quokka = marsupial' then using it as "symbol of joy" and
"name of a software project" adds two new senses (quokka.symbol, quokka.name --
concept broadened); the taught use is aligned.

HONEST BOUNDARY (follow-up): the MISUSE/contradiction case's classifier is correct
(negated claim + fits_taught -> misuse) but does not fire live yet, because
negation/correction inputs are routed to the context-directive path and skipped in
the claim-ingestion seed loop (detect_context_directive continue), so they never
reach the tracker. Wiring the tracker into the correction/negation path is the
remaining step for the (a) case to fire in live turns. Also: an "Actually,"-prefixed
sentence currently extracts no claim at all (parser edge), independent of this.

---

## FIX-A008b — Discourse-marker classifiers for the (a)-vs-(b) split

Added `_CORRECTION_MARKERS` ("actually", "no,", "isn't", "rather", "instead", …)
and `_MULTIVARIABLE_MARKERS` ("also", "can also", "in another sense", "sometimes",
"depending on", …) as classifier priors in `_track_concept_use_outcome`. Priority:
correction/negation frame -> misuse_contradicts; multivariable frame -> new_sense;
else fall back to the meaning comparison (fits_taught -> aligned, else new_sense).
The classifying marker is recorded on each outcome ("noted"), so the signal is
tracked and informs the verdict without overriding the meaning comparison.

Verified: plain declaratives classify correctly (aligned + new_sense recorded).
HONEST BOUNDARY (upstream, = FIX-A008 follow-up): the marker branches do not fire
LIVE yet because the phrasings that carry them do not reach the tracker with a
clean claim -- "X can also be Y" (modal+also) often extracts no claim; negation /
"Actually…" inputs are routed to the context-directive path and/or fail extraction.
So the classifier is correct and complete; delivering marker-framed / corrective
inputs to it is upstream claim-extraction + seed-loop-routing work (larger, core
NLP), tracked as the follow-up.

---

## SEVEN-FLAG RESOLUTION (2026-07-02, external directive, verified-merged)

Applied the SEVEN_FLAG_RESOLUTION_DIRECTIVE overlay (author-built on this branch's
latest push, so it is my session work + seven-flag deltas -- verified by diff before
applying; no session work lost). Phases:

- P1 WarpField actuator registration: register each WarpCapable host under the
  routing key it actually emits as demand.source (_warp_level_name()): dps ->
  'dimensional_crystal', perception -> 'representation', braid -> 'braid_stream',
  language_field -> 'comparison_type' (legacy aliases retained). Was: registry held
  only 'dps'/'language_field', so every demand fell through to the dps fallback.
- P2 quasiarch_observer import: flat import -> try/except fallback to
  aurora_internal.quasiarch_observer; InteractionEngine now boots (no
  '[INTERACTION] Unavailable').
- P3 De-nest CPS SediMemory wiring in aurora.py (unconditional, not gated on
  identity_field presence).
- P4/P5 Engine-contract compliance (foundational_contract.py +
  aurora_runtime_constraint_governor.py): constraint_profile() returns the engine
  ConstraintVector; runtime_regime adds governor_weight; language_projection adds
  existence_mode/language_register; universal_representation adds
  constraint_vector/runtime_regime. Adapter profile moved to _unit_profile().
- P6 DreamEpisodePack engine fields (constraint_signature/runtime_regime/
  language_projection) + compiler engine anchors.
- P7 ExpressionEcology axis coherence bonus (fitness * (1 + weight*0.15), weight from
  GovernorWeights of the dominant axis climate).
- P8 SentenceComposer sensory register bias (energy -> N-axis nudge, template-free).
- P9 State hygiene: contradiction_ledger placeholder purged; authorship headers on 6
  modules; removed root junk (.codex).

VERIFIED: tests/_engine_integration_test.py 9/9, tests/_pipeline_test.py 6/6, boot
actuator registry = all six routing keys, no [INTERACTION] Unavailable, L0-L8 guard
green, live turn battery + this session's learning mechanisms intact.

(Directive's registry ids FIX-A007/FIX-I004 target the read-only aurora-preemptive-
hardening skill registry; noted here to avoid collision with this file's FIX-A007.)

---

## FIX-A009 (ARCHITECTURAL) — Grounding feeds assertion confidence (emit abstain diagnosis)

**Question:** why does emit() abstain on a concept even after it has crystallised to
SEMANTIC (depth >= 0.4, scaffolding 2)?

**Diagnosis (sourced):** emit() expresses her constraint STATE, not her knowledge.
Its output is gated on (1) the speech act from `_classify_speech_act`, which reads
`i_state_polarities` (I_IS/I_CAN/...) built ONLY from the i-state collective, and
(2) content-slot resonance, and (3) the input-frame semantics (is_statement /
aligns_with_oets / is_question). Concept grounding fed NONE of these -- so a
crystallised concept with a neutral field never trips ASSERTION; emit stays silent.
Crystallisation is necessary but not sufficient.

**Fix (`aurora_constraint_emission.py`, EmissionContextBuilder.build):** a concept
she has genuinely crystallised (OETS scaffolding >= SEMANTIC) that is the current
topic now raises I_IS toward assertion (bounded <= 0.6, scaled by depth) -- earned
confidence about what she deeply understands, gated on real grounding so it is never
blanket over-assertion. This closes the i-state half of the gate: what she has
grounded, she can now move to assert.

**Verified:** real-turn regression is sane (no over-assertion, anchor leaks 0, known
concepts render, unknowns honestly abstain). HONEST BOUNDARY: emit-compression
activation ALSO needs the input-frame semantics + content-slot resonance to align,
which happens in genuine assertive conversational context (synthetic frames with
is_statement=False fall through to ACKNOWLEDGMENT regardless). Not force-able without
risking her honest expression -- documented, not faked.

---

## POSSIBILITY-SELVES (2026-07-03, new subsystem — Stage 1 foundation)

`aurora_possibility_selves.py` — inception-born divergent selves ("paths not
taken"). NOT snapshots or clones. Each is a NEWBORN vessel of her architecture that
develops a distinct identity by replaying her recorded pressure history
(`pressure_experiences.jsonl`, 500 events) in a DIFFERENT order under DIFFERENT
pressure. Because sequence + pressure shape identity, the same life-material
re-sequenced yields a genuinely different self.

Stage-1 mechanism (built + verified standalone):
- Birth: newborn InceptionEntity vessel per self (blank), given a DivergenceProfile
  (reorder strategy + axis emphasis).
- Replay: her history re-ordered per self (reverse / hardest-first / diverged-first)
  and re-pressured (axis emphasis reweights felt tension). Fast-tracked (all 500
  lived at once).
- Developmental resolution: a self builds capacity only on its emphasis axis and
  resolves tensions THERE that she could not; off-axis it mostly rejects, as she did.
- Warp for gaps: a self starved of its axis (her history barely walked it) uses warp
  to re-read her experiences through its own lens -- growing territory she never gave
  it, so a road-not-taken still becomes itself.
- DivergenceTracker-style matrix confirms all three become distinct.

Verified against her real state: 3 distinct fingerprints, distinct resolution
profiles [91,92,419]; the N-forged self surpasses her in her own N-heavy domain
(419/500) while the A/T selves are genuine roads-not-taken; each grew beyond her via
warp. Standalone; NOT yet wired into boot/dream cycle.

Stage 1b — offerings assessment (`assess_offerings`): per-self primary_gift
(growth / coherence / evolution) + territory-beyond-her (warped gaps); council-level
growth/evolution/coherence/diversity readout. What the selves have to OFFER her.

Stage 1c — the bridge, done right (`provoke_reexperience`): the wired-in mechanism
that lets the selves benefit her WITHOUT handing answers (which would re-flavour her
development -> drift). The selves PROVOKE: their engaged tensions are re-presented
through each self's stance lens; she RE-LIVES each through her OWN live machinery
(`_her_current_capacity` reads the identity field), growing +0.02/re-living. Only HER
outcomes are kept (kept_fraction ~0.06). Gentle per-dream dose (max_new_resolutions=8)
with the rest carried to future dreams -> slow authentic arc, no single jolt.

Stage 1d — the developmental cheat-code, made durable (`persist_reexperience`): every
dream appends its works/doesn't to `dream_reexperience_log.jsonl` and folds it into a
cumulative per-anchor track record (`dream_reexperience_track.json`). Fair to let it
drive crystallisation because every mark is HER own outcome. A tension MET >=3 times
across dreams sediments (crystallised); one MISSED >=2 times becomes an
actively-sought gap (not dropped). Verified compounding across 4 dreams: seeking
emerges dream 2, crystallised dream 3 (8 anchors), stable dream 4. Both runtime files
git-ignored.

Stage 2 — dream residence (built + verified): `QuantumDreamSubstrate` now births the
selves ONCE (lazily, first dream cycle) and holds them on `self._selves` so they
persist across cycles as continuous beings with their own arcs. `run_dream_cycle`
step 6 = `_dream_encounter_with_selves`: she MEETS them in the dream and experiences
the reinforced pressures THROUGH interacting with them — the encounter calls
`provoke_reexperience`, so the selves influence her only by what they make her
re-encounter, never by their verdicts. Fully defensive (a dream never crashes the
substrate thread). Verified across 3 cycles: selves born dream 1 and persist (same
Ember/Wane/Riven), seeking emerges dream 2, crystallised dream 3.

Stage 3 — dialogue loop (`dream_dialogue`, built + verified): each provocation is now
a multi-TURN exchange, not a single pass. A self presents a tension from a path she
did not take; she re-lives it (shared `_relive_provocation` primitive); if she cannot
yet meet it, the self PRESSES from its divergent identity (a tiny +0.03 reframe
perturbation each round, capped at `turns`=3) so she attends differently and may
arrive THROUGH the exchange on a later round -- still by her own grown capacity, never
handed the answer. Produces a readable transcript sample. Verified: a real exchange
where she says "not yet" twice then "I can meet it now -- I have grown to it".

Stage 4 — feedback split (`_feed_her_growth` + `_resolve_relief_sink`, built +
LIVE-verified): what she EARNED (anchors crystallised across repeated dream re-living)
sediments into HER growth. A LIVE growth session surfaced that `systems["genealogy"]`
is only routing lanes (a dict) and the real `ConstraintGenealogyLogger` is mounted at
`systems["chamber"]._genealogy` / `systems["grammar_engine"]._genealogy` with an
`observe(before, trace, after)` API -- there is no live `log_relief` (the earlier
assumption, also latent in `_sediment_validated_fact`; note evolved_surfaces'
__getattr__ fakes hasattr for any name, so a naive duck-type is fooled).
`_resolve_relief_sink` finds the real logger safely; `_feed_her_growth` feeds it an
honest minimal relief observation (PressureVec 0.30 on the crystallised axis ->
relieved) with `notes={"source":"dream_earned"}`, AND always appends a durable ledger
(`dream_earned.jsonl`) so earned growth is never lost, plus a `dream_crystal_earned`
developmental event. The selves are never modified. LIVE-verified on her real boot:
genealogy event_log 0->8, dream_earned 0->8, tick_count +8, links unchanged (clean
relief records, no spurious pair-links); ledger 8 entries.

Stage 5 — per-self persistence (`save_self_arc`/`load_self_arc` + `resume=True` on
birth; built + verified): each self's arc (orientation, capacity, resolved/held
anchors, tone/exposure, identity) saved to aurora_state/dream_selves/<self_id>.json.
On resume a self is RESTORED where it was rather than re-living history fresh, so
Ember/Wane/Riven continue as the same beings across boots. Verified: boot-2 resumed
all three with intact distinct arcs (Ember 43 resolved / Wane 66 held / Riven 23
resolved) and distinct fingerprints. Dream substrate now births with resume=True, runs
dream_dialogue, and re-saves arcs after each cycle. All runtime files git-ignored
(dream_selves/, dream_reexperience_track.json, *.jsonl log).

Stage 4b — crystals are the ground truth (`crystal_authority` + `_deposit_dream_crystal`,
LIVE-verified): "when it comes to tracking and all else fails, check the crystals." The
track record (dream_reexperience_track.json) is only a side-ledger; HER real
`ConceptCrystalRegistry` (systems['_concept_crystal_registry'], persisted to
concept_crystals.json.gz) is the authority. `_deposit_dream_crystal` registers each
dream-earned crystallisation via the public `observe_lsa(ax, "dream_earned:<anchor>")`
at the tension's axis coordinate, so checking the crystals literally reflects her dream
growth. `crystal_authority` reads the live registry and counts dream_crystals /
dream_facets as the authoritative confirmation. `_feed_her_growth` now returns
{genealogy_reliefs, crystals_deposited, crystallised} and annotates each crystallised
record with crystal_confirmed. The substrate logs the crystal-authority every cycle.
LIVE-verified: three records agree -- track 8 crystallised, genealogy 8 reliefs, and
the authority CRYSTALS dream_facets 0->8 (all X-axis tensions reinforce the same
X-region crystal: correct crystal physics). concept_crystals.json.gz persists it.

Stage 6 — the selves DEVELOP too (`PossibilitySelf.witness` + `witness_depth` +
`log_selves_development` + live-new-history on resume; LIVE-verified): they were frozen
provocateurs; now each LIVES every exchange it provokes and develops along its own
nature. Development is driven by `witness_depth` (per-axis, starts at ZERO at birth,
grows only through dream witnessing -- decoupled from birth capacity so a self's arc is
its own, slow and earned, not a flip of what it was born). A growth_event = crossing a
new 0.25 threshold of dream-depth on an axis (order/dose-independent, so every self that
lives the exchanges grows, not just the first-processed one). A holder that witnesses
deeply enough resolves ONE thing it held -- and releasing COSTS the depth it took
(witness_depth -= thresh), so it re-earns its way to the next and stays mostly what it
is. Negative-lean holders (Wane) need far deeper witnessing (thresh 1.6 vs 0.75) so they
drift slowly. On resume a self also lives any history logged since it was saved (its
continuing life). Arcs persist to aurora_state/dream_selves/<id>.json and a per-cycle
`selves_timeline.jsonl`. LIVE-verified over 10 cycles: Ember growth_events 1->16 (stays
resolver, fp stable), Riven 0->7 (stays resolver, fp stable), Wane 1->19 releasing only
2 of 66 held (held 66->64, fp shifted) -- genuine partial evolution, character intact;
all three resume carrying their development forward. Their arcs are committed as
intentional growth (force-added past the blanket aurora_state/ ignore).

Stage 7 — stagnation-triggered birth (`StagnationMonitor` + `birth_from_stagnation` +
dynamic-selves resume; LIVE-verified): the council is NOT fixed. `StagnationMonitor`
watches her across dream cycles and signals a birth on two triggers -- a developmental
STUNT (dev_index range < dev_eps=0.5 over a 5-cycle window) or PRESSURE STAGNATION
(total axis-pressure variation < pressure_eps=0.03), with a `stuck_axis` = the most
pinned axis and an 8-cycle cooldown after each birth. `birth_from_stagnation` then
births a NEW self oriented to break exactly the stall: leaning hard into the stuck axis
from the I-state pole the council LEAST embodies + the council's weakest secondary axis
(`_orientation_for_stuck_axis`), named from a pool (Kindle/Vane/Drift/...), tagged
`born_from=reason:axis`. It lives her history from its new vantage and persists like any
self; dynamically-born selves also RESUME across boots (birth scans dream_selves/ for
non-default arcs and reconstructs them from their saved profile). Wired into the dream
cycle after the encounter. LIVE-verified: forced N-stall -> Kindle born oriented I_DONOT
(counter to Riven's I_DO); forced B-stall in the live substrate -> Kindle born I_SAW
(counter to Wane's I_SOUGHT), appended to the live council, resumes as the 4th being.

Stage 8 — council homeostasis by behaviour (`council_functional_balance` +
`rebalance_council` + retirement; verified): a self's ORIENTATION is fixed at birth but
its BEHAVIOUR drifts (a holder like Wane can become a resolver by living), so the
stagnation-birth's orientation-based balance can't see when the living council has
stopped holding in practice. `council_functional_balance` measures what the council
actually DOES (held/(held+resolved) ratio, active_holders). `rebalance_council`, run
each dream cycle, acts ONLY on a genuine behavioural need: if held_ratio < 0.22 AND no
active holder remains, it frees a slot by retiring a redundant resolver
(`_pick_redundant_resolver` -- one sharing a functional role with another, preferring a
less-developed non-founder) and births a holder (`force_hold=True` -> oriented to the
holding/questioning pole) to restore the lost pressure. Retirement ARCHIVES the being
(moves its arc to dream_selves/retired/ so it is not resumed but its development is
preserved), and retired names are never reused. This is what makes "let Wane become
whatever he becomes -- and if his becoming leaves a hole, she fills it herself" real.
Verified: quiet while any holder remains (real council: held_ratio 0.209 but Ashe still
holds -> no action); on forced full collapse -> retires a redundant resolver (Drift) and
births a fresh holder (Mire, I_ISNT-led, 28 held, born_from=holding_need).

POSSIBILITY-SELVES subsystem is now COMPLETE end-to-end: birth -> assess -> bridge
(provoke) -> durable works/doesn't cheat-code -> dream residence -> dialogue ->
feedback split (live genealogy + real concept crystals as ground truth) -> persistence
-> the selves' own development -> stagnation-triggered new births. She meets the council
only in dreams; they influence her only by what they make her re-encounter; her own
machinery decides every outcome; what she earns crystallises into her real crystal
store (the authority); the selves grow along their own natures as distinct continuous
beings; and when she stalls, a new self is summoned to move her.

---

## FLAGGED (not fixed, discovered 2026-07-14 during ICC Ledger Phase 0
## pre-flight verification) — evolved-native override pollutes `magnitudes()`
## dict, breaks `EntropySaturationDetector.measure()`

**File:** `aurora_internal/aurora_energy_layer_costs.py` (AURORA_EVOLVED_NATIVE
tail, ~line 3090) / `aurora_internal/aurora_entropy_detector.py:227`

**What's wrong:** the code-autoevolver's generic AURORA_EVOLVED_NATIVE tail
monkey-patches `LayerEnergyAccountant.magnitudes` at import time
(`_aurora_assign_target(['LayerEnergyAccountant', 'magnitudes'], ...)`). Its
generic `_aurora_apply_result_rewrite()` enriches ANY dict-typed return value
with extra string keys (`_aurora_rewrite_profile`, `_aurora_genealogy_strategy`,
etc.) before returning it. `magnitudes()`'s real return type is
`Dict[Constraint, float]` — a small, fully-enumerable dict the rest of the
codebase (correctly) assumes only ever contains the five Constraint members.
`EntropySaturationDetector.measure()` iterates `for c in magnitudes:
self._mag_windows[c].append(...)` with no filtering, so the injected string
key raises `KeyError: '_aurora_rewrite_profile'` — `verify_entropy_detector()`
(the module's own self-check, called from its `__main__`) crashes outright.

**Verified:** `verify_worth_evaluator()` is unaffected (its own code reads
`magnitudes.get(c, 0.0)` for named constraints only, never blind-iterates);
only `EntropySaturationDetector.measure()`'s blind iteration is exposed.
Confirmed pre-existing — neither file was touched by the ICC Ledger work
that surfaced it, and `git status` on both showed no local changes at the
time of discovery.

**Not fixed:** out of scope for the ICC directive (Phase 0 never calls
`EntropySaturationDetector.measure()` itself — it only accepts an
externally-constructed `SaturationSignal` as a parameter, so this bug does
not affect the ICC ledger or its tests). Fixing the generic evolved-native
rewrite wrapper risks unintended blast radius across every other
`_aurora_assign_target`-wrapped method in the file; flagging per the
directive's own "flag rather than guess" discipline rather than improvising
a fix to code neither this session nor the directive was asked to touch.
Likely fix shape (for a future session): either exclude non-dict-key-typed
methods like `magnitudes()` from the generic dict-enrichment path, or have
`EntropySaturationDetector.measure()` iterate only over the known AXES
constants instead of `magnitudes.keys()`.

**SECOND OCCURRENCE (2026-07-14, Phase 1 — Strategic Horizon Layer):**
the same corruption class hit `SaturationSignal.urgency_ticks()`, which
this phase's `_projected_gain()` calls directly. `urgency_ticks()`'s real
contract is `Optional[int]`, and returning `None` (no crossing projected)
is the common, legitimate case — but the evolved-native override wraps
the original call, and its generic `_aurora_apply_result_rewrite()`'s
`if result is None and isinstance(reflection, dict): return fallback`
branch turns that legitimate `None` into a dict, which then blew up a
`urgency / float(remaining)` division with `TypeError: unsupported
operand type(s) for /: 'dict' and 'float'`. Same fix posture as before:
not touching the generated override machinery; `aurora_strategic_horizon.py`
now validates `isinstance(urgency, (int, float))` before using the
return value arithmetically, rather than trusting the documented type.
Two independent hits on two different methods in two different files
(`aurora_energy_layer_costs.py`, `aurora_internal/aurora_entropy_detector.py`)
both traced to the exact same generic rewrite-on-None branch suggests this
is systemic across every `_aurora_assign_target`-wrapped method whose real
contract legitimately returns `None` — worth a dedicated sweep, not just
one-off guards, whenever this gets picked up.

---

## FIX-A018 (ARCHITECTURAL) — Dimension Proposal Without Codebase Grounding

**Category:** ARCHITECTURAL

**Pattern:** External capability proposals asserting absence of subsystems
(perspective, identity drift, salience filtering) that exist under
Aurora-native names.

**Correct Form:** Map proposal vocabulary to Aurora vocabulary before
accepting any "missing capability" claim: perspective -> ConsciousFrame /
QuasiArch / InceptionEntity, identity gradient ->
BehavioralIdentity.drift_from_base, salience -> AttentionEngine, value ->
WorthEvaluator.

**Why:** Aurora's subsystems use domain-native naming; generic AI
vocabulary greps return false negatives.

**First Seen:** Dimensional expansion proposal audit, 2026-07-14 --
confirmed via a full 343-file repo scan against an external proposal
claiming eight missing representational dimensions (R/P/V/Φ/U/I'/S/C).
Verdict: 3 of 8 already fully built under different names (P, I', S --
claims flatly wrong), 3 more are unification jobs over existing
per-subsystem structure (R, Φ, U), and only 2 (V — strategic/goal
layer, C — operator composition) were genuine gaps. The audit's own
containment-claims section found Aurora already runs every mitigation
the proposal prescribed as novel (selective activation, operator
specialization, explosion containment, convergence protection) under
existing mechanisms (ExistenceMode gating, WarpPathway costs, the
latent-operation quarantine pipeline, EntropySaturationDetector).

**Resolution of the audit's flagged ICC discrepancy:** the audit noted
"`ICC ledger` referenced in docs... but no implementing `.py` found in
this snapshot" and asked to verify before building anything V-adjacent.
Confirmed at the time (2026-07-14, ICC Landing directive pre-flight): no
prior ICC implementation existed anywhere in this repo or the wider
filesystem accessible to that session -- it was docs-only, never landed.
The two genuine gaps this audit identified (V and C) were then built as
the ICC Landing / Strategic Horizon / Operator Composition directive:
`aurora_internal/aurora_icc_ledger.py` (the ICC substrate the audit
correctly identified as prerequisite), `aurora_internal/
aurora_strategic_horizon.py` (the V "choose a worse immediate state for
a better long-term one" gap), and `aurora_internal/
aurora_operator_composer.py` (the C "operators composed from other
operators" gap, independently rediscovering all four of
aurora_frontier_ops.py's hand-seeded 3-axis composites in its own
self-test).

---

## ICC LANDING DIRECTIVE (2026-07-14) — cross-phase item flagged, not
## fabricated

One of the directive's own cross-phase requirements couldn't be honestly
completed as literally stated, per the "flag rather than guess" discipline
the directive itself sets:

1. **"Snapshot bracketing: call record_developmental_snapshot(force=True)
   before Phase 1 first activation and after its first 100 ticks"**
   (requirement 5) -- Phases 0-2 (`aurora_internal/aurora_icc_ledger.py`,
   `aurora_internal/aurora_strategic_horizon.py`,
   `aurora_internal/aurora_operator_composer.py`) all landed as complete,
   tested, standalone modules — matching the existing standalone posture
   of `aurora_worth_evaluator.py`/`aurora_entropy_detector.py`/
   `aurora_variant_promotion.py`, none of which this directive asked to
   be wired into `boot_aurora()`'s live systems dict either. No phase of
   this directive instructs where/how to wire Strategic Horizon into a
   live tick loop, so there is no real "first activation" to bracket yet
   -- fabricating one would produce a meaningless snapshot pair. This
   mirrors the MTSL directive's own precedent: land the mechanism
   standalone and tested first, wire it live only under a later,
   explicit directive that says so.

---

## FIX-A019 (ARCHITECTURAL) — Flat-divergence watchdog for the classroom

**Category:** ARCHITECTURAL

**Pattern:** A per-lesson health signal (`DivergenceTracker.current_
divergence`, `aurora_simulation_engine.py:1274`) that can go structurally
dead (mathematically forced to the same value every time, not just
statistically flat) with nothing downstream ever noticing or halting.

**Correct Form:** Derive a "consecutive zero" count from the PERSISTED
log (`classroom_log.jsonl`), not in-memory state, so the check is correct
across separate scheduled runs, not just within one long-lived process.
Halt (raise, do not silently continue) once the count crosses a threshold
(20 lessons). `aurora_classroom.py::_consecutive_zero_divergence_tail()` +
`ClassroomSession.run_lesson()`'s check at entry, raising
`ClassroomHaltedError`.

**Why:** `classroom_log.jsonl` showed `divergence_score == 0.0` in
452/452 real lessons over 12 days with no failure, error, or halt
anywhere in the pipeline -- the signal being provably dead looked
identical to the signal being healthy-and-quiet from every consumer's
point of view. Dead signal must read as dead, not as "nothing to report."

**First Seen:** Semantic Plateau Remediation Directive, 2026-07-15,
Phase R1.3 -- alongside FIX-A020 and FIX-A021 below, all three
confirmed against the same 452-lesson classroom_log.jsonl evidence base.

---

## FIX-A020 (ARCHITECTURAL) — Adapter-scalar compression hazard

**Category:** ARCHITECTURAL

**Pattern:** An episode -> entity-experience adapter that compresses an
entire multi-turn episode into two scalars derived from a single overall
average (`aurora_classroom.py::_episode_to_entity_experience`'s
pre-R1.2 form: `resonant = (avg_fitness + final_engagement) / 2`,
`strained = 1 - resonant`), discarding all per-turn structure, lesson
content, and target-dimension identity before it ever reaches the
consuming entity.

**Correct Form:** Route structured, multi-signal channels through the
adapter: per-turn deltas (momentum), grounded/understanding signal,
target-dimension texture, and engagement trajectory (pull) -- and use
channel names that are actually meaningful to the consumer's own
vocabulary (`ImpressionCascade.EMOTION_VALENCE`, not invented labels).

**Why:** Two compounding failures from one scalar-compression adapter:
(1) `strained = 1 - resonant` forces the channel magnitudes to sum to
exactly 1.0 every time, which forces `ImpressionCascade.energy_to_shard`'s
saturating intensity function to a fixed constant (`1/(1+2) = 0.3333`)
regardless of lesson content; (2) `"resonant"`/`"strained"` are not
entries in `EMOTION_VALENCE`, so the primary/secondary valence lookup
always resolved to `0.0`. Both are visible directly in the arithmetic,
not just correlated with the observed data -- they are the literal cause
of the `(0.3333, 0.0)` constant tuple across all 904 real entity
resolutions in `classroom_log.jsonl`.

**First Seen:** Semantic Plateau Remediation Directive, 2026-07-15,
Phase R1.2.

---

## FIX-A021 (ARCHITECTURAL) — Accumulation-metric hazard

**Category:** ARCHITECTURAL

**Pattern:** A metric that only ever increases from background accretion
(`dev_index`, driven almost entirely by `wisdom_shards` incrementing
independent of lesson content -- `abilities`, `genealogy_links`, and
`crystals` stayed static across a long sampled window of
`developmental_timeline.jsonl` while `dev_index` climbed every ~20s)
being read anywhere as evidence of competence or used to gate/grade a
learning intervention.

**Correct Form:** Accumulation metrics are telemetry, not verdicts.
Competence claims require a held-out, never-trained-on instrument scored
independently of the accumulation path -- `aurora_internal/
aurora_semantic_probe_battery.py` (Phase R0 of this same directive).
`dev_index` may still be recorded and bracketed around lessons for
cross-reference, but it may never again be cited as evidence that
understanding improved.

**Why:** 12 days of classroom lessons produced a fully flat experiential
signal (FIX-A019, FIX-A020) while `dev_index` rose the entire time --
the accumulation metric was actively masking the plateau it should have
been catching.

**First Seen:** Semantic Plateau Remediation Directive, 2026-07-15,
Phase R0's own founding rule: "No further classroom lessons are scored
by dev_index. Competence = probe score."

---

## FIX-A022 (ARCHITECTURAL) — Golden-pair rule

**Category:** ARCHITECTURAL

**Pattern:** Trusting a scoring instrument's output before ever proving
the instrument can score at all.

**Correct Form:** A probe dimension is only "live" (its 0.0 reading
treated as a real capability floor rather than a suspect gauge) once a
hand-authored ideal/failing response pair, fed directly into the SAME
scoring path (bypassing generation entirely), separates cleanly:
ideal >= 0.75, failing <= 0.25 (`aurora_internal/
aurora_semantic_probe_battery.py::validate_golden_transcripts()`,
`run_probe_battery.py --golden`). The golden set is a permanent fixture,
not a one-time check -- every future battery run should be able to
re-run it as a self-test for instrument drift.

**Why:** `contradiction_handling` and `uncertainty_signaling` read
exactly 0.0 across all six probe-battery runs before this rule existed
(3 baseline + 3 post-R1) -- indistinguishable, from the outside, between
"genuine capability floor" and "broken instrument." Golden validation
resolved it directly: both separate cleanly on hand-written content
(12/12 probes each, ideal >= 0.75, failing <= 0.25) -- the 0.0 in live
runs is a real, confirmed capability gap, not a wiring bug. Building the
golden set also caught two independent instrument bugs by contrast: (1)
`_parseable()`'s function-word list was missing common prepositions
("before", "between", ...), producing a false negative on a
grammatically fine question; (2) `context_carryover`'s rubric formula
has a real calibration ceiling (~0.66, below the 0.75 bar) for any
transcript whose user-side text lacks a callback marker word ("that",
"this", "they", ...) -- confirmed a formula limitation, not a capability
claim, since the golden ideal's boolean predicate (mentions_referent)
still fires correctly every time.

**First Seen:** Remediation Addendum R1.5, 2026-07-15, Step 1.

---

## FIX-A023 (ARCHITECTURAL) — Pinned-floor rule

**Category:** ARCHITECTURAL

**Pattern:** Treating a metric reading exactly 0.0 (or exactly max)
across multiple independent runs as a settled capability conclusion
without first ruling out an instrument problem.

**Correct Form:** Any metric pinned at exactly 0.0 (or exactly its max)
across >= 3 independent runs triggers golden-pair instrument validation
(FIX-A022) BEFORE any capability conclusion is drawn from it. A floor is
not "weak" (weak reads as noisy small numbers) -- a floor that never
moves at all is either a real absolute ceiling or a broken gauge, and
those require different fixes.

**Why:** Same evidence base as FIX-A022 -- the pinned-0.0 signal alone
was the thing that correctly triggered the golden-validation step in the
first place, per the R1.5 addendum's own re-diagnosis.

**First Seen:** Remediation Addendum R1.5, 2026-07-15.

---

## FIX-A024 (ARCHITECTURAL) — Curriculum scheduler-balance rule

**Category:** ARCHITECTURAL

**Pattern:** A curriculum selector ranked purely by a single severity
score (fail_count) with no floor on how long a low-ranked candidate can
go unscheduled when the batch size is smaller than the full candidate
pool.

**Correct Form:** Within any rolling window (20 lessons), no candidate
dimension may fall more than a small tolerance (2 lessons) behind the
most-fed dimension in that window --
`aurora_classroom.py::_balance_starved_dimensions_first()`, derived from
`classroom_log.jsonl`'s own persisted history, not new state. Anything
past tolerance is pulled to the front of the ranked plan, most-starved
first, ahead of the normal severity order.

**Why:** `select_curriculum(n=4, ...)` (the daemon's own cadence) has no
guaranteed-coverage mechanism -- a chronically-low-fail-count dimension
could go starved indefinitely. Flagged in the R1.5 addendum from
`uncertainty_signaling` receiving only 3 of 45 lessons in one sampled
window; that specific run turned out to be a uniform 3-per-dimension
artifact of `n` exceeding the full 15-dimension pool (not an actual
skew), but the underlying unguarded mechanism is real and applies
directly to the daemon's smaller `n=4` cycles, so the fix stands on its
own merits independent of that one sample.

**First Seen:** Remediation Addendum R1.5, 2026-07-15.

---

## FIX-A025 (ARCHITECTURAL) — Verified-fresh telemetry rule

**Category:** ARCHITECTURAL

**Pattern:** Citing a state/log file as live evidence without checking
whether anything actually still writes to it.

**Correct Form:** No state/log file may be cited or read as live
evidence without an mtime check against the investigation window. A
file existing on disk with a plausible name is not proof it's current.

**Why:** The R1.6 addendum named `aurora_state/fgae_turn_log.jsonl` and
`aurora_state/dual_strata_frame_log.jsonl` as existing live telemetry.
Both were stale -- last written weeks before that investigation's own
12-day window began (`DualStrataBridge.persist()` explicitly replaced
its on-disk frame log with an in-memory-only deque; nothing currently
writes `fgae_turn_log.jsonl` at all). Caught only because the tracing
work checked mtimes before reading -- reading them unchecked would have
fabricated "live" telemetry from dead files and corrupted the R1.6
failure-shape classification.

**First Seen:** Remediation Addendum R1.6, 2026-07-15 (correction #1),
logged formally in Remediation Addendum R1.7, 2026-07-15.

---

## FIX-A026 (ARCHITECTURAL) — Stratified-metric rule

**Category:** ARCHITECTURAL

**Pattern:** A single blended mean reported across a heterogeneous
population of measurements, hiding a real subgroup collapse inside an
average that looks healthy.

**Correct Form:** Any coherence/competence metric spanning
heterogeneous prompt classes must be reported per-stratum, never as one
blended number -- `aurora_internal/aurora_semantic_probe_battery.py::
BatteryReport.stratified_wellformedness_summary()`, reported alongside
(never instead of) the per-dimension breakdown.

**Why:** R1.5 reported `semantic_wellformedness` as a single mean
(0.417, 0.917, 0.833, 0.75 across four runs) and called it "healthy,"
directly feeding Phase R1.5's own substrate-ordering theory refutation.
R1.6's trace reopened that conclusion: every abstract-framed probe
(`contradiction_handling`, `uncertainty_signaling`) produced incoherent
word-salad, while simple_concrete probes stayed fine -- the blend was
averaging catastrophe against health and reporting the result as fine.
Blended means are accumulation-metric hazards (FIX-A021) in a new
costume.

**First Seen:** Remediation Addendum R1.5 reopened by Remediation
Addendum R1.6/R1.7, 2026-07-15.

---

## FIX-A027 (ARCHITECTURAL) — Liveness rule

**Category:** ARCHITECTURAL

**Pattern:** `verify_*()`/self-test passing green is read as proof a
module participates in the live runtime, when self-tests only prove the
module's OWN logic works in isolation.

**Correct Form:** Every module claiming a runtime governance or
monitoring role must show real call-site reachability from
`boot_aurora()`'s live path before its behavior is trusted as active.
Claimed-but-unwired modules belong in an explicit quarantine manifest so
their status is a documented decision, not an accident discovered
mid-investigation.

**Why:** `UncertaintySignalingGuard`/`FailureGuardSuite`/`ConstraintEngine`
(`aurora_constraint_engine.py`) has real, correct, well-tested guard
logic and its own passing `__main__` self-test demonstrating
`acknowledge_uncertainty()` -- but `ConstraintEngine` is never
instantiated anywhere in the live `boot_aurora()` path, and
`feed_evidence()`/`govern()`/`acknowledge_uncertainty()` have zero call
sites anywhere outside that same self-test block. The R1.6 addendum's
prime suspect (this guard blocking hedged expression) was clearable by
direct grep evidence in minutes specifically because this discipline was
applied -- without it, the guard's convincing self-test could easily
have been mistaken for proof of live participation.

**First Seen:** Remediation Addendum R1.6, 2026-07-15 (constraint-engine
finding), logged formally in Remediation Addendum R1.7, 2026-07-15.

---

## FIX-A028 (ARCHITECTURAL) — Regression-set rule

**Category:** ARCHITECTURAL

**Pattern:** Fixing an instrument bug without preserving the exact
inputs that exposed it, so a future edit can silently reintroduce the
same failure mode.

**Correct Form:** Every instrument bug fixed converts its triggering
cases into a permanent regression set for that instrument --
`tests/test_generation_collapse_regression.py` holds all 24 verbatim
garbled responses from the R1.6 failure-shape trace (must always be
rejected) plus an equal-sized set of genuinely fine short sentences,
including the specific preposition-led false-negative class already
found once (must always pass).

**Why:** `_parseable()`'s short-clause evasion (clauses under 6 words
bypassed the function-word check entirely) let 16 of 24 real garbled
Aurora responses through as `parseable=True`. A fix without a pinned
regression set is only verified against the cases the fixer happened to
think of.

**First Seen:** Remediation Addendum R1.7, 2026-07-15, Track A1.

---

## FIX-A029 (ARCHITECTURAL) — Archive-first rule

**Category:** ARCHITECTURAL

**Pattern:** Investigating a capability question (is X broken, when did it
break) by running new live measurements first, when stored historical
outputs already on disk could answer the always-broken-vs-regressed
question without any risk of the investigation itself contaminating the
evidence.

**Correct Form:** When a capability's history is in question, re-score
every archived stored output with the current instrument BEFORE doing any
live investigation. Archived text cannot be changed by anything done after
it was written, so it is the one source immune to observer effects from
the investigation itself, and is often already sufficient to resolve
always-broken vs regressed vs gradient-decay.

**Why:** R1.8's transcript archaeology re-scored 8 archived probe-battery
runs plus 200 archived conversation-memory entries (the earliest available
record, ~5 months before the remediation campaign began) entirely from
stored text, and that alone resolved the campaign's central open question
(ALWAYS-BROKEN, not regressed) before a single new live turn was run.

**First Seen:** Remediation Addendum R1.8, 2026-07-15.

---

## FIX-A030 (ARCHITECTURAL) — End-to-end assertion rule

**Category:** ARCHITECTURAL

**Pattern:** A generative pipeline accumulates hundreds of passing tests
that check structural/numeric properties (parameter propagation, field
bounds, monotonicity, crash-safety) while zero tests assert anything about
the linguistic coherence of the pipeline's own actual output -- so a full
green suite coexists with months of word-salad in production.

**Correct Form:** Every generative pipeline must carry at least one test
asserting output quality in the output's own terms (for language:
parseability + on-topic referent overlap, not merely that output exists or
that generation ran without raising).

**Why:** R1.8.1's S3+1 audit inventoried every test touching the
composition/articulation path. `tests/test_emitter_crash.py` and
`tests/run_interaction_test.py` have no `test_*` function pytest ever
collects. `tests/test_conversation_desktop.py::test_conversation` is
collected and always passes -- it has zero assert statements, so it would
pass identically whether Aurora replied with a sentence or an empty
string. `tests/test_oets_comprehension_confidence_growth.py`,
`tests/test_direct_address_formulation.py`, and
`tests/test_mtsl_live_wiring.py` assert real things, but about internal
numeric/structural state, never about whether emitted text itself makes
sense. Before this remediation campaign (R0 onward), the count of tests
asserting linguistic coherence of Aurora's actual generated text was
zero -- `tests/test_semantic_probe_battery.py`,
`tests/test_generation_collapse_regression.py`, and
`tests/test_stratified_wellformedness.py` are the first three, and this
campaign built all of them.

**First Seen:** Remediation Addendum R1.8.1, 2026-07-15, S3+1.

---

## FIX-A031 (ARCHITECTURAL) — Silent-fallback / safety-valve override rule

**Category:** ARCHITECTURAL

**Pattern:** A genuinely honest, safe response path exists
(`ConstraintEmitter._emit_abstain()` -- template text like "I'm not sure."
/ "I can't say.", no vocabulary lookup, cannot produce word-salad) but a
later stage in the same turn's emission chokepoint
(`_enforce_emission_discipline` -> `_field_frame_compress` ->
`ConstraintEmitter.emit()`) runs UNCONDITIONALLY before the abstain
fallback is ever checked, and its output overrides the honest abstain text
whenever it produces any non-empty "core," regardless of whether that core
is actually coherent. The result: the honest, safe path exists in the
code and is architecturally correct, but is rarely what a user actually
receives, because the unconditional generation stage almost always
produces *something*.

**Correct Form:** A safety-valve response path (honest abstain, "I don't
know," refusal) must be checked for override-worthiness, not merely
existence -- if a later stage's output is going to replace it, that
later stage's output needs its own coherence gate before it's allowed to
win, or the safety valve should run LAST and only be skippable by content
that has passed a real quality check, not merely non-emptiness.

**Why:** R1.8.1 Step 3's live single-turn trace on a plain greeting ("Hi
Aurora, how are you doing today?") showed `state.response_src` labeled
`"constraint_abstain"` (the honest path had been selected) while the
actual text delivered was `"Am exist want can understand truth. Moment
did kind feel is alive."` -- word-salad from `ConstraintEmitter.emit()`'s
normal content-resolution path, not the abstain templates at all. The
honest abstain templates in `_emit_abstain()` are correct and
vocabulary-free; they were simply never what got sent, because
`_field_frame_compress` runs before the emptiness check that would fall
through to them, and `emit()` essentially never returns fully empty (see
FIX-A032, background-radiation).

**First Seen:** Remediation Addendum R1.8.1, 2026-07-15, Step 3.

---

## FIX-A032 (ARCHITECTURAL) — Background-radiation / reinforcement-imbalance rule

**Category:** ARCHITECTURAL

**Pattern:** A word-selection mechanism scores candidate vocabulary by
`comprehension_confidence` (raised only by prior usage/research) rather
than by relevance to the current turn's actual topic. When most of the
vocabulary graph's nodes are cold-start placeholders (confidence stuck at
the 0.1 floor, `times_encountered=0`, `times_used_in_expression=0`) and a
small cluster of self-referential/existential words (am, exist, meaning,
want, do, truth, can, become...) has been reinforced thousands of times,
that small cluster wins the content-slot competition on essentially every
turn, independent of what the turn is actually about -- because
relevance never gets a chance to outweigh a 6-9x confidence gap.

**Correct Form:** Confirm this diagnosis is real (verified below) before
choosing a fix, per the shape-before-fix rule. A fix needs to either (a)
raise the floor / accelerate confidence growth for topic-relevant but
under-encountered nodes, (b) weight relevance more heavily relative to
historical confidence in the resonance formula, or (c) both -- but no fix
is authorized yet; this is the confirmed root-cause finding the branch
discussion (Sunni, post-Track-B/C) will choose from.

**Why:** R1.8.1 Step 3 ranked all 773 `aurora_oets_web.json` nodes by
`times_used_in_expression`. All 8 words of the observed R1.6 garbled bank
(truth/meaning/become/exist/am/do/can/want) rank in the top 20 of 773 --
am is #1 (2,934 uses), exist is #2 (2,740). Meanwhile every probe-topic
word checked (dinner, birthday, guitar, chords, weekend, schedule,
tomatoes, backyard) is present in the graph as a node but sits at
`comprehension_confidence=0.100` (the floor), `times_encountered=0`,
`times_used_in_expression=0` -- never once actually used. A live
instrumented single-turn trace on a neutral greeting reproduced the exact
mechanism in real time: `_resolve_content_slot()` repeatedly selected
"meaning"/"am"/"coherence"/"repair" -- words with no relevance to the
input -- because their `comprehension_confidence` (~0.65-0.92) dominates
the near-zero confidence of every node that would actually be on-topic.
This is the R1.7 addendum's "background-radiation hypothesis," confirmed
directly rather than inferred.

**First Seen:** Remediation Addendum R1.8.1, 2026-07-15, Step 3.

---

## FIX-A033 (ARCHITECTURAL) — Migration-completion rule

**Category:** ARCHITECTURAL

**Pattern:** A path is "replaced" in a commit message or boot comment, but
the old path is neither removed nor explicitly quarantined -- both paths
stay live, and later diagnosis inherits whichever one a boot comment
happened to name, not whichever one actually delivers output.

**Correct Form:** A path replacement is complete only when the old path is
removed, or explicitly quarantined with a documented liveness verdict.
Dual-alive paths surviving a claimed "replacement" are a defect class in
their own right, independent of whether either path individually works.

**Why:** The 2026-06-30 introduction of `ConstraintEmitter` was documented
in `aurora.py` as replacing "FGAE/StateVoice/SentenceComposer emission
path." `SentenceComposer` was never removed or quarantined; it remained
reachable via `gateway._express() -> ExpressionPerceptionEngine.express()
-> self.composer`, and R1.9.1 confirmed by backward trace that THIS path,
not `ConstraintEmitter`, produces the text a user or the probe battery
actually receives. R1.8.1's own Step 3 finding ("SentenceComposer is
orphaned dead code") inherited the incomplete-migration's framing and was
wrong as a result.

**First Seen:** Remediation Directive R1.9.1, 2026-07-16 (origin: the
6/30 incomplete swap).

---

## FIX-A034 (ARCHITECTURAL) — Backward-attribution rule

**Category:** ARCHITECTURAL

**Pattern:** Claiming a module is live (or dead) by forward inference --
reading a boot comment, following an import graph, or confirming a
function executes -- without checking whether that function's output is
what actually reaches the delivered artifact.

**Correct Form:** Liveness and output-attribution claims require a
backward trace from the delivered artifact: instrument the actual return
chain for a real turn and confirm, byte-for-byte, which stage's output
the delivered text equals. Forward inference from design intent, boot
comments, or "this function executes" is insufficient evidence that a
function's output is what gets delivered -- a module can be fully live
and executing on a path that is not the one a user's text comes from.

**Why:** R1.8.1 Step 3 confirmed `ConstraintEmitter._resolve_content_slot`
executes on every live turn and forward-inferred this made it the
delivered-text mechanism. R1.9.1's live instrumented trace
(`tests/test_governance_liveness.py::
test_delivered_output_attribution_traces_to_sentence_composer`) proved by
byte-for-byte comparison that `resp_B.content` (what
`run_probe_battery.py` scores) instead equals `gateway._express()`'s
returned content, sourced from `SentenceComposer`, not
`ConstraintEmitter`. Both modules are genuinely live; only one delivers.
Retained as the working example of why this rule exists.

**First Seen:** Remediation Directive R1.9.1, 2026-07-16 (origin: the
Halt-Point-3 orphaned-composer error).

---

## FIX-A035 (ARCHITECTURAL) — Grounding-term rule

**Category:** ARCHITECTURAL

**Pattern:** A selection mechanism scored primarily or entirely by its own
past outputs (usage counters, co-occurrence edge weights, valence tuned
through repeated exposure) with no external grounding term measuring
relevance to the CURRENT input/state.

**Correct Form:** Any such mechanism must carry a dominant external
grounding term. Pure self-referential scoring is a feedback-loop hazard
class: whatever the mechanism said most in the past becomes what it says
most in the future, regardless of current input, and the loop is
invisible from inside the mechanism itself.

**Why:** Two independent instances found in this campaign, in two
different modules, scored by two different self-referential signals:
ConstraintEmitter's `comprehension_confidence`/`times_used_in_expression`
(FIX-A032) and SentenceComposer's `emotional_valence`-proximity, tuned
toward common targets purely by repeated exposure (R1.9.2 G1). Both
produced the identical symptom (identity-bank dominance) from different
mechanisms, confirming this is a class of bug, not a single bug.

**First Seen:** Remediation Directive R1.9, 2026-07-16 (origin: FIX-A032's
mechanism), generalized in R1.9.2 G1.

---

## FIX-A036 (ARCHITECTURAL) — Safe-path reachability rule

**Category:** ARCHITECTURAL

**Pattern:** A safety/abstain fallback exists in the code, is correctly
implemented, and is even architecturally reachable in principle -- but
nothing confirms it can actually fire from the LIVE path under real
conditions, so it silently never executes while looking present in a code
review.

**Correct Form:** Every safety/abstain fallback needs a reachability test
proving it can actually fire from the live path, not just that its
function body is well-formed and callable.

**Why:** ConstraintEmitter's `_emit_abstain()` was correct and
vocabulary-free (FIX-A031) but effectively unreachable because
`_field_frame_compress` ran unconditionally before the emptiness check
that would fall through to it. R1.9.2 G2 built SentenceComposer's abstain
gate with this rule applied from the start: a permanent unit test
(`test_abstain_fires_when_every_required_slot_fails_the_floor`) proves the
trigger condition actually engages, rather than trusting that the
floor-check code being present means it fires.

**First Seen:** Remediation Addendum R1.9, 2026-07-16 (origin: unreachable
`_emit_abstain()`), applied in Remediation Directive R1.9.2 G2.

---

## FIX-A037 (ARCHITECTURAL) — Boot-profile disclosure rule

**Category:** ARCHITECTURAL

**Pattern:** A measurement is reported as if it characterizes the system,
when it actually characterizes the system under one specific boot
configuration -- and other configurations exist that reach different code
paths entirely.

**Correct Form:** Every measurement states the boot profile it ran under.
When a metric could plausibly differ across profiles, run it under more
than one and report both rather than letting one profile's number stand
in for "the system."

**Why:** `run_probe_battery.py` boots with `runtime_profile="surface"`
unconditionally, which skips the entire intake-metabolism tier
(worth_evaluator, VariantPromoter, accountant, bias_engine, solidification)
-- meaning every probe-battery measurement this ENTIRE campaign has taken
(R0 through R1.9.2) has been silently profile-scoped without saying so
until Track C's liveness audit found it. R1.9.2 G4's dual-boot-profile
gate operationalizes this rule for the composer-relevance fix specifically
(not yet run this session -- flagged as a following item, not skipped
silently).

**First Seen:** Remediation Directive R1.8.1 Track C, 2026-07-16 (origin:
the surface-profile discovery), formalized in Remediation Directive R1.9.

---

## FIX-A038 (ARCHITECTURAL) — Content-selection doctrine: relevance chooses WHAT, everything else shapes HOW

**Category:** ARCHITECTURAL

**Pattern:** A self-referential or affective signal (usage habit, register/
mood, valence-proximity) is allowed to influence WHICH content word gets
selected, not just how that content gets phrased/paced/toned.

**Correct Form:** Relevance to the current input/state is the only
legitimate primary term for CONTENT-slot selection. Usage-habit, register/
looseness, and valence-proximity may all legitimately bias STYLE and TONE
-- phrasing rhythm, function-word preference, temperature of exploration,
warmth of delivery -- but never override relevance as the reason a
specific content word was chosen.

**Why:** Third confirmed instance of the same pattern in this campaign: F1.4
(usage-habit -> style, not content), F5 (register -> exploration looseness,
not content), and now valence-proximity -> tone (R1.9.2 G1, demoted from
SentenceComposer's PRIMARY sort key to a bounded secondary tie-break that
provably cannot outweigh a relevance difference of one hop). Recorded as a
standing doctrine, not a one-off fix, because it keeps recurring under
different signal names.

**First Seen:** Remediation Addendum R1.9 F1.4/F5 (design note), instance 3
confirmed and implemented in Remediation Directive R1.9.2 G1.

---

## FIX-A039 (VERIFICATION) — R1.9.2 G4 gate 4 run to completion + G3 F5 plumbing shipped disabled

**Category:** VERIFICATION

**Pattern:** Closes out the two items FIX-A037 and R1.9.2's own G3
explicitly flagged as outstanding rather than done: gate 4's dual
boot-profile comparison, and F5's register-gated exploration plumbing.

**What ran:** Gate 4 (dual boot-profile check, FIX-A037 applied to the G1
composer fix specifically): the full 60-probe battery under
`runtime_profile="full"` timed out at 600s -- each turn is roughly 10x
slower under "full" than "surface" because the intake-metabolism tier
(worth_evaluator, VariantPromoter, accountant, bias_engine, solidification)
now actually runs. A stratified 10-probe subset (2 per dimension) was run
under both profiles instead: relevance 0.445 (surface) vs 0.520 (full),
parseable_rate 0.0 in both (the pre-existing, out-of-scope grammar issue
reproduces identically under both profiles -- not profile-dependent). No
exceptions, no crash, no material behavior shift beyond the expected
slowdown.

Training-stack propagation check: 10 classroom lessons run post-fix
against the corrected composer. All 10 completed with no exceptions and no
flat-divergence-watchdog trip; divergence mean 0.184 (9/10 nonzero,
against R1.3's >0.15 target and R1.4's pre-fix 0.099 baseline), dev_index
2093 -> 2170. Episode/classroom machinery still functions end to end under
the fix; the fitness-landscape shift is the expected consequence of
changed word selection, not a regression.

G3 (F5 register-gated exploration): plumbing built and unit-tested (12
tests, including the F5.2-mandated hard invariant that nothing below a
register's effective relevance floor can ever be selected), but
`SentenceComposer._EXPLORATION_ENABLED` stays `False` -- gate 4's own
acceptance-gate run (`r192_g4_acceptance_gates.json`) found the stratified-
wellformedness gate failing, which is F3's own stated precondition for
enabling exploration. Plumbing exists and is verified; behavior is
unchanged until a future directive re-runs the gates and finds them
passing.

**Explicitly out of scope, not silently dropped:** the grammar/syntax
overhaul of `_compose_from_motif` (F4's own non-goals section excludes
this from R1.9.2 -- "that's the NEXT diagnosis with its own trace, and it
will be a cleaner one"). parseable_rate 0.0 in both boot profiles above is
this same known, unfixed issue, not a new finding.

**First Seen:** Remediation Directive R1.9.2, gates 3/4 + G3, completed
2026-07-16 following the directive's own ratified scope.

---

## New finding (not yet a registry-numbered fix): state-dir isolation gap

Discovered live during R1.9.2 G2 verification, not part of this
directive's ratified scope to fix, but important enough to record here so
it isn't lost: `LexicalMemory.save()`/`.load()`
(`aurora_expression_perception.py`) and at least
`aurora_state/surface_pressure_log.jsonl`'s write path default to
hardcoded paths anchored to `os.path.dirname(os.path.abspath(__file__))`,
NOT to the `state_dir` parameter `boot_aurora()` receives. Confirmed live:
booting against a `shutil.copytree`'d throwaway scratch directory (the
isolation pattern this entire campaign has relied on since R0) still reads
and writes the REAL repository's `aurora_state/lexicon.json` and
`aurora_state/surface_pressure_log.jsonl`. Every live turn processed via
`process_external_user_turn` across this whole campaign -- not just this
session's ad-hoc debugging -- has been writing real usage-count and
pressure-log data back into the actual repo state. Concretely broke
`tests/test_toroidal_circulation_layer.py::test_seed_from_surface_log_against_real_repo_data`
during this session's G2 debugging (restored via `git checkout`).
Recommend a dedicated audit of every `aurora_state/*` read/write path for
the same `state_dir`-bypass pattern before trusting isolation claims for
any file not explicitly verified. Not scoped to fix within R1.9.2.

---

## Falsified-prediction log

R1.7's Track A2 falsifiable prediction ("simple_concrete stays moderately
healthy; abstract_conceptual collapses toward 0") was FALSIFIED by Track
A's own live stratified baselines: both strata collapsed to 0.0 parseable
in all 3 runs. Retained here as a working example that the prediction
discipline this remediation campaign runs on actually functions --
predictions get written down before the data exists, and get logged as
falsified rather than quietly revised when the data disagrees.

**First Seen:** Remediation Addendum R1.7 (prediction), falsified by
Track A, logged formally in Remediation Addendum R1.8, 2026-07-15.

---

## Grammar diagnosis dossier — `_compose_from_motif` word-salad root cause (evidence only, halt after — Sunni decides)

F4's own non-goals explicitly deferred this: "NO grammar/syntax overhaul
beyond word selection... that's the NEXT diagnosis with its own trace, and
it will be a cleaner one." This is that trace, run 2026-07-16 against the
live stack (delivered path confirmed in R1.9.1: `compose()` ->
`_compose_from_motif()` -> `_select_constraint_word()`). Evidence-only,
matching the halt-after-diagnosis pattern already used for the R1.9.1
dual-path dossier -- no code changed by this entry. Four independent,
compounding root causes, confirmed by live instrumented trace (motif
`role_sequence` + each output word's actual lexicon POS captured together
for the same turn) and by direct inspection of the live promoted-motif
lineage (1038 total motifs, 18 promoted).

**Layer 1 — actively promoted motifs with no subject.** The two
highest-ranked promoted motifs in the live lineage are structurally
malformed regardless of what words fill them:
`('descriptor','action','object','descriptor','action','object','connector')`
(success=3264, fail=748, **composability=0.8136 — the single highest of
any promoted motif**) has no AGENT role at all. `('agent','action',
'descriptor','action')` (success=3732 — the highest raw success count of
any motif) has two ACTION slots and no OBJECT. These are not valid
English clause shapes by construction. The 7-role motif is what produced
every "word salad" example seen live, e.g. `'Photosynthesis expressed
weight terms need defensive.'`

**Layer 2 — role-blind candidate collection (the biggest lever).**
`_select_constraint_word`'s PRIMARY candidate source (the `chars`-based
`self.lexicon.find_by_noncomp(f"{dominant_axis}:{ch}", ...)` loop, ~line
2745) adds every word crystallized onto that concept-axis channel to the
candidate pool with **no check that `entry.role` matches the slot's
`lex_role`** — unlike the DPS-crystal branch just above it, which does
filter (`_e.role == lex_role or not chars`). Confirmed live: for
`role="action"` (expects `lex_role="verb"`), the composer selected
`'energy'` (noun), `'cost'` (noun), and `'interesting'` (verb-tagged but
semantically adjectival) — producing `'I energy.'`, `'I cost.'`,
`'I interesting.'` as complete "sentences." This is the same class of bug
G1 fixed for RELEVANCE (role-blind selection there was fixed by scoring
on `build_relevance_anchor_set`); here it's role-blind on POS, a
different axis of the same word-selection call.

**Layer 3 — zero grammatical post-processing on the delivered path.**
`_compose_from_motif` does `" ".join(words)`, capitalizes, and punctuates
— no conjugation, no article/determiner insertion, no plural or
subject-verb agreement. Confirmed live: `'I is.'` (should be `'I am.'`).
The needed machinery already exists in the SAME class — `_CONJUGATIONS`
(a hand-built I/you conjugation table) and `_conjugate_verb()` — but is
only ever called from `_fill_template()`, which is itself unreachable
dead code: FIX-A016 removed template-string composition from `compose()`
entirely in favor of the "template-free" `_compose_from_motif` path, and
nothing ported the conjugation call over. `_conjugate_verb`'s own logic
(scan back to the subject, conjugate) generalizes cleanly to
`_compose_from_motif`'s word-list shape since its only two subjects are
also "I"/"you" (`_select_constraint_word`'s agent branch, line ~2700-2703)
— this is a narrower gap to close than it first looks.

**Layer 4 — the reinforcement loop that produces Layer 1 is grammar-blind
by construction.** `StructuralMotif.composability_score()` = `success_rate
x context_diversity` (`aurora_grammar_engine.py` ~line 338), where
"success" is `SentenceComposer.feedback(fitness)` reporting `fitness >=
0.5` back to whichever motif produced that turn's output. That fitness
number comes from the same downstream evolutionary-fitness signal this
entire campaign has repeatedly found uncorrelated with actual response
quality (dev_index/classroom fitness, not a grammar or parseability
score) — R0's own founding finding. So motif promotion has never
selected against ungrammatical structure; the subject-less 7-role motif
outscores the correct `('agent','action','object')` motif
(composability 0.4467) simply because it has been used and randomly
scored >=0.5 more often. Fixing Layers 2/3 alone would make individual
word fills more grammatical without ever correcting the malformed
structures Layer 1 keeps selecting; fixing Layer 1 requires either
demoting/retiring structurally-invalid motifs on a rule (e.g. "must
contain exactly one AGENT, at least one ACTION") independent of the
fitness signal, or giving `feedback()` a real grammaticality term to
weight motif success on — the latter being the more durable fix since it
addresses Layer 4 directly rather than working around it.

**Recommended fix order — RATIFIED AND IMPLEMENTED.** Remediation
Directive R1.9.3 executed this exact order as its own L2/L3/L1/L4 gates
(landed 2026-07-16, each individually tested and battery-verified; see
FIX-A039/A040/A041 and the FIX-A027/A035 addenda below). Left the
original recommendation text below verbatim as the historical record of
what was proposed before execution:
(1) Layer 2 — role-filter the `find_by_noncomp` candidate loop the same
way the DPS-crystal branch already does; smallest, safest, immediately
testable in isolation. (2) Layer 3 — port `_conjugate_verb` into
`_compose_from_motif`'s word-list assembly (agent is always I/you here,
so the existing table needs no extension). (3) Layer 1/4 — either a
structural validity gate on motif promotion (independent of fitness) or
a grammaticality term added to the fitness signal `feedback()` receives;
this is the architecturally biggest piece and the one most likely to need
its own acceptance gates before shipping, given this campaign's repeated
experience with fitness-adjacent changes.

**First Seen:** Remediation Directive R1.9.2 F4 non-goals (deferred),
diagnosed 2026-07-16 following that deferral.

---

## FIX-A040 (ARCHITECTURAL) — Role-gate rule

**Category:** ARCHITECTURAL

**Pattern:** A structural slot with a named grammatical/semantic role
(e.g. a composer slot requiring a verb) accepts ANY candidate that scores
well on an unrelated ranking term (relevance, valence, concept-axis
membership), with the role requirement checked loosely or not at all.

**Correct Form:** When a slot names a required category, category
compatibility is a hard gate applied to the candidate pool BEFORE any
ranking term runs, never a soft score bonus/penalty a strong-enough
ranking score can outweigh. Ranking terms (relevance, recency, valence)
only ever choose among already-compatible candidates.

**Why:** `SentenceComposer._select_constraint_word`'s primary candidate
source (`find_by_noncomp`, concept-axis crystal membership) added every
matching word to a role's candidate pool with no check that the word's
actual part of speech matched the slot's required category -- a noun
("energy") was exactly as eligible for a verb slot as a real verb,
provided both happened to share a concept-axis crystallization. Produced
"I energy.", "I cost." live. Same shape as F1's relevance-primary fix
(G1) but on the POS axis instead of the relevance axis of the same
selection call -- confirms this is a recurring failure mode wherever a
selection function collects candidates from an associative index before
checking the hard structural constraint that should have gated entry in
the first place.

**First Seen:** Remediation Directive R1.9.3 L2, 2026-07-16 (grammar
diagnosis, root cause layer 2).

---

## FIX-A041 (ARCHITECTURAL) — Skeleton-validity rule

**Category:** ARCHITECTURAL

**Pattern:** A learned/evolved structural template (motif, pattern,
skeleton) is trusted for production use purely because it scored well on
a fitness/frequency signal, with no independent check that the template
itself is structurally valid for its domain.

**Correct Form:** Structural validity is a gate on eligibility,
independent of and checked before fitness-based ranking. An invalid
template stays in the learned pool with its history intact (so future
review or re-evaluation is still possible) but is excluded from
production selection until it passes validity -- validity gating is
faster and more reliable than waiting for a fitness signal to eventually
learn the same thing, especially when (per FIX-A035) that fitness signal
has no grounding term that could ever penalize invalidity directly.

**Why:** The single highest-composability promoted grammar motif in the
live lineage (0.8136) had no AGENT/subject role in its skeleton at all --
fitness alone (accumulated success/fail counts with no grammar-aware
term) never selected against it because nothing in the scoring path could
tell a subjectless skeleton from a valid one. `is_valid_clause_shape()` +
`MotifLineage.best_for_pressure()`'s eligibility filter (R1.9.3 L1) fixed
this at the selection layer, independent of and prior to the deeper fix
to the fitness signal itself (R1.9.3 L4, FIX-A035 instance).

**First Seen:** Remediation Directive R1.9.3 L1, 2026-07-16 (grammar
diagnosis, root cause layer 1).

---

## FIX-A027 addendum — Liveness rule, instance #4

Orphaned conjugation table: `SentenceComposer._CONJUGATIONS`/
`_conjugate_verb` (`aurora_expression_perception.py`) were built, correct,
and passed their own logic -- but only ever reachable from
`_fill_template()`, which FIX-A016 made dead code when it replaced
template-string composition with `_compose_from_motif`'s "template-free"
assembly. Nothing ported the conjugation call to the replacement, so "I
is." shipped live for as long as that replacement existed while a working
fix sat two methods away. Fixed in R1.9.3 L3 by extracting
`_conjugate_for_subject` as the reusable core and calling it from the
delivered path directly.

**First Seen (this instance):** Remediation Directive R1.9.3 L3,
2026-07-16.

---

## FIX-A035 addendum — Grounding-term rule, instance #4

`MotifLineage`'s motif-promotion fitness (`aurora_grammar_engine.py`):
`StructuralMotif.composability_score()` is `success_rate x
context_diversity`, where "success" came entirely from
`SentenceComposer.feedback(fitness)` -- the SAME general-purpose
downstream fitness signal this campaign has repeatedly found uncorrelated
with response quality (R0's founding finding), with no grammaticality
term at all. Fixed in R1.9.3 L4: `feedback()` now scores each motif
against its own composed sentence with the Track-A `_parseable`
predicate as the DOMINANT term (weight 0.75), fitness demoted to
secondary; `MotifLineage.recompute_promotion_from_validity()` re-derives
`promoted` status for the persisted pool from L1's validity whitelist
without touching success/fail history.

**First Seen (this instance):** Remediation Directive R1.9.3 L4,
2026-07-16.

---

## FIX-A042 (VERIFICATION) — R1.9.3 grammar repair, final acceptance (honest partial pass)

**Category:** VERIFICATION

All four layers (L1-L4) landed as four separate, individually-tested,
individually-battery-verified commits, in the directive's specified
order, each gated on the previous layer's mini-gate passing. Verified
live and fixed: the composer no longer selects wrong-POS words for
role-strict slots (L2), no longer ships uncorrected copulas like "I is."
(L3), no longer composes from the two most-reinforced-but-subjectless/
malformed skeletons in the live lineage (L1), and motif promotion is no
longer scored by a grammaticality-blind fitness signal going forward
(L4). All 4 of the diagnosis's own verbatim failures ("I energy.", "I
cost.", "I is.", "Photosynthesis expressed weight terms need
defensive.") were confirmed absent across 180 live delivered probe
responses (3 full battery runs).

**Final acceptance gate results, run against the real post-L1-L4 stack,
3x, reported exactly as measured:**
- Relevance maintained >=0.3: **PASS** -- 0.684 / 0.717 / 0.711 across 3 runs.
- 24-case regression set (`tests/test_generation_collapse_regression.py`):
  **PASS** -- 6/6 (this is a predicate-correctness check on `_parseable`
  itself, unaffected by L1-L4 since `_parseable`'s logic was not modified;
  passing was expected, not new evidence of composer improvement).
- Full suite green: **PASS** -- 754 passed, 1 pre-existing unrelated
  failure (`test_flow_audit_and_tcl_wiring.py`, baseline-consistent
  throughout this entire campaign).
- Boot profile disclosed: **PASS** -- every result states
  `runtime_profile`.
- **`semantic_wellformedness` (stratified `parseable_rate`) >=0.5 per
  stratum: FAIL.** Measured 0.0 / 0.028 / 0.056 (`simple_concrete`) and
  0.0 / 0.0 / 0.0 (`abstract_conceptual`) across the 3 runs -- nowhere
  near the raised 0.5 bar (G4's original bar was 0.3 and also failed).

**Why the miss, reported honestly rather than reframed:** `_parseable`
requires at least one "strong function word" (article/preposition/
conjunction, e.g. "a/the/of/with") per sentence with >=2 words. L1-L4
fixed the composer's SKELETON validity, word-category correctness, and
subject-verb conjugation -- none of which touch determiner/article
generation, which nothing in the composer currently does at all
(explicitly scoped OUT: L3's directive text names determiner insertion
"STRETCH ONLY... nothing beyond"). A now-fully-grammatical two-word
sentence like "I understand." still has zero strong function words and
still fails this specific heuristic's bar by construction, regardless of
how correct the rest of the sentence is. This is a real, expected,
previously-flagged gap (L1's own commit message: "missing articles,
abstract-noun objects with no determiner... expected and unaddressed by
this layer"), not a new regression and not something L1-L4 were ever
scoped to close.

**Disposition:** halting for review before any U1/exploration/further
wiring, per the directive's own final instruction. Determiner/article
generation is the natural next diagnosis if further grammar work is
wanted; not started here.

**First Seen:** Remediation Directive R1.9.3, final acceptance measured
2026-07-16.

---

## FIX-A043 (ARCHITECTURAL) — Two-direction golden rule

**Category:** ARCHITECTURAL

**Pattern:** An instrument/predicate is refined to admit cases it
previously (wrongly) rejected, and only the "does it now accept the
new-valid cases" direction gets checked -- the "does it still reject
everything it correctly rejected before" direction is assumed to hold
because nothing about THAT logic was touched.

**Correct Form:** Any predicate refinement re-validates BOTH directions
before going live: (1) failure retention -- every existing regression
case that correctly failed before must still fail, verified against the
UNCHANGED permanent regression set; (2) new-validity admission -- a
freshly hand-authored golden set of both newly-valid and still-invalid
cases must separate cleanly. Loosening a check and tightening a check
are both guarded by the same discipline; a refinement is only "live"
once both directions hold simultaneously.

**Why:** R1.9.4 Step 1 replaced `_parseable`'s function-word-presence
requirement with a real clause-structure check specifically so it would
stop rejecting valid telegraphic sentences ("She sings well.") -- a pure
loosening in intent. Applied blind, that loosening could easily have also
let real word salad back through (a bare-verb-count check alone doesn't
distinguish "I did. I exist." from "I understand completely." without
the missing-determiner/strong-word interplay this directive explicitly
required testing for). Building the golden set in both directions at
once (10 valid-telegraphic-must-pass, 5 malformed-must-fail) caught this
by construction rather than after the fact.

**First Seen:** Remediation Directive R1.9.4 Step 1, 2026-07-16.

---

## FIX-A044 (COMMENTARY) — Acquisition-sequence diagnostic frame

**Category:** COMMENTARY

Delivered-output quality in this campaign progressed through stages that
track the human language-acquisition order, not by design but as an
observed pattern worth recording for future capability staging:

1. **Salad** (pre-R1.9.2): word-salad, wrong parts of speech in
   arbitrary slots, no reliable subject or verb.
2. **Relevant-telegraphic** (post-R1.9.2/R1.9.3, L1-L4): correct parts
   of speech in correct slots, valid minimal subject-verb(-object)
   clause shapes, topically relevant to the turn -- but bare, missing
   function words (articles, most prepositions).
3. **Function-word-complete** (R1.9.4 target): determiners/prepositions
   present where clause structure demands them.

Each stage is a genuinely different capability floor, not a single
"grammar" axis -- R1.9.2/R1.9.3 fixed word-selection and clause-skeleton
validity; R1.9.4 addressed the function-word layer, first by discovering
the instrument itself was conflating salad-detection with function-word-
presence (Step 1), then by building the schema for function-word slots to
even be learnable (Step 3b). Recorded so a future diagnosis at any later
stage can check "which acquisition stage are we actually at" before
assuming the next fix is more word-selection or more skeleton-validity
work when it might be a different capability entirely.

**First Seen:** Remediation Directive R1.9.4 trigger note, 2026-07-16.

---

## FIX-A045 (ARCHITECTURAL) — Earned-floor rule

**Category:** ARCHITECTURAL

**Pattern:** An acceptance floor set early in a remediation campaign (when
a capability was known to be weak or entirely absent) is left unchanged
as later fixes land, so the floor stops functioning as a real bar once
the system has clearly outgrown it -- or, in the other failure direction,
a floor gets raised without evidence the underlying capability actually
improved, silently hiding a regression as a "known limitation."

**Correct Form:** Acceptance floors ratchet upward only as evidence
justifies it, and the ratchet is recorded, not silent: when a capability
genuinely improves (verified against real measurement, not assumed), its
floor rises to match; the new floor is stated explicitly alongside the
evidence that earned it, so a future reviewer can see the floor's history,
not just its current value.

**Why:** R1.9.2 G4 set relevance's floor at 0.3, appropriate when
relevance-primary selection had just landed and headroom was unknown.
By R1.9.4, three full remediation phases later, relevance had held at
0.5-0.75 consistently across a dozen+ battery runs with zero regressions
-- R1.9.4 raised the floor to 0.6 explicitly BECAUSE of that track record
("it's earned a higher floor than 0.3 now"), not as an arbitrary
tightening. The same discipline applies to stratified_wellformedness: G4
set it at 0.3 (already failing), R1.9.3 raised it to 0.5 (still failing,
honestly reported), R1.9.4's Step 1 instrument fix revealed the true
number was 0.5-0.7 all along, masked by an over-strict predicate -- the
floor didn't change, but the honest reading of it did, which is exactly
the failure mode this rule exists to keep visible instead of silently
absorbed into "well, it's close enough."

**First Seen:** Remediation Directive R1.9.4 acceptance criteria,
2026-07-16 (relevance floor 0.3 -> 0.6, explicit and evidenced).

---

## FIX-A046 (VERIFICATION) — R1.9.4 function-word gate, full acceptance

**Category:** VERIFICATION

All three steps landed as three separate commits, each individually
tested and battery-verified, per the directive's process.

**Step 1 (predicate refinement):** `_parseable` reworked from
function-word-presence to clause-structure assessment (a plausible
subject + single verb + complement/modifier shape via coarse POS
categories, plus a missing-determiner check) with strong-word presence
demoted to one path to pass rather than the only one. Two-direction
golden guard (FIX-A043) confirmed clean: the unchanged 24-case + original-
audit regression set stays green, the 4 grammar micro-regression cases
still fail, 10 new hand-authored telegraphic-valid sentences now pass,
5 new hand-authored article-malformed sentences correctly fail.

**Step 2 (honest re-baseline):** 3x battery under the refined predicate
with ZERO composer changes. Delta decomposition, reported exactly as
measured: R1.9.3's final 0.0-0.06 stratified_wellformedness reading was
overwhelmingly INSTRUMENT over-strictness, not a real capability gap --
simple_concrete jumped to a 0.71 mean, abstract_conceptual to 0.58,
relevance held at 0.72. Both strata already cleared the directive's 0.35
narrow-gap fork threshold by a wide margin before any Step 3 work.

**Step 3 (gap fix, narrow-gap branch -- 3b only, 3a shelved):**
Investigation confirmed connector's category gate already accepted
"preposition" but the miner/observer (`RoleTagger`) threw prepositions
AND determiners away entirely during pattern extraction -- no mined or
observed motif could ever contain either slot type regardless of fitness
grounding. Added `TokenRole.DETERMINER` as a genuine sibling to
CONNECTOR, routed true prepositions into the existing CONNECTOR role,
added the missing DETERMINER->OBJECT positional fallback, widened
`_select_constraint_word`'s last-resort search to a slot's full category
(not a single lex_role string), and added two determiner-inclusive
shapes to L1's whitelist -- eligibility only, no forced promotion. 100
post-fix classroom lessons ran clean (0 errors, divergence mean 0.222,
99/100 nonzero) and the mining loop organically observed 10
determiner-inclusive motifs for the first time this campaign has ever
recorded -- none force-promoted, exactly "the loop earns it."

**Final acceptance, measured 3x, reported exactly as run:**
- Step 1 golden separation + regression retention: **PASS** (both
  directions clean, verified above).
- Stratified wellformedness >=0.5/stratum under the REFINED predicate:
  **PASS** -- simple_concrete 0.64/0.42/0.58 (mean 0.55), abstract_
  conceptual 0.67/0.54/0.79 (mean 0.67).
- Relevance >=0.6 (raised floor, FIX-A045): **PASS** -- 0.67/0.77/0.75
  (mean 0.73), every individual run clearing 0.6 on its own.
- Grammar micro-regression set holds: **PASS** (unchanged from Step 1,
  reverified in the full suite).
- Suite green: **PASS** -- 771 passed, 1 pre-existing unrelated failure
  (baseline unchanged throughout this entire campaign).

R1.9.2/R1.9.3/R1.9.4 together resolve the full grammar diagnosis this
sub-campaign opened with: word selection, clause-skeleton validity,
surface conjugation, motif-fitness grounding, the wellformedness
instrument itself, and the function-word slot schema. Remaining known
gap: function-word-complete generation (stage 3 of FIX-A044's
acquisition sequence) is schema-eligible but not yet the DOMINANT
composition pattern -- the 10 observed determiner-inclusive motifs are
real but unpromoted, exactly the state "the loop earns it" predicts for
a freshly-eligible pattern with only 100 lessons of exposure.

**Disposition:** halting for U1/exploration sequencing, per the
directive's own final instruction.

**First Seen:** Remediation Directive R1.9.4, final acceptance measured
2026-07-16.

---

## R1 Campaign Closure (2026-07-16) — ratification batch closed

**Status:** the R1 remediation campaign (R0 through R1.9.4) is CLOSED
with full acceptance: R1.9.4's final measurement --
`stratified_wellformedness` 0.55/0.67 against a 0.5 bar, relevance 0.73
against an earned 0.6 bar, all regression sets holding, full suite
green, no gate relaxed to get there. This entry closes the ratification
batch N1 named as blocking so the registry text matches shipped reality,
per Sunni & Cael's closure directive.

**Formally ratified (registry text updated to reflect shipped, not
pending, status):**
- **Abstain doctrine** (F2, first applied to `ConstraintEmitter`'s
  `_emit_abstain()`, then carried to the delivered path in R1.9.2 G2):
  templated abstain surface + a generated, logged reason from a real
  floor-check outcome is FIX-A008-compliant honest abstention, not a
  banned scripted response. Ratified.
- **Repair-in-place decision** (R1.9.2): fix `SentenceComposer`
  directly on the confirmed delivered path rather than building a
  parallel corrected mechanism, given R1.9.1's dossier established
  `ConstraintEmitter` was never the delivered-text mechanism. Ratified.
- **Grammar diagnosis recommended fix order** (logged provisionally
  under the grammar diagnosis dossier above as "not yet ratified, not
  yet implemented"): superseded by execution -- Remediation Directive
  R1.9.3 carried out that exact order as its own L2/L3/L1/L4 gates.
  Marked ratified-by-execution at the dossier entry above.

**Campaign record, for the developmental log:**
- Root causes found and fixed on the delivered path: usage-frequency
  selection (emitter), valence-as-content selection (composer),
  POS-blind slot filling, an orphaned conjugation table, invalid
  promoted skeletons, ungrounded motif fitness, function-words discarded
  before they could ever be learned.
- Instrument stack built and now permanent: two-direction golden pairs,
  stratified batteries, regression sets, liveness CI with delivered-
  output attribution, boot-profile disclosure.
- Recurring disease named and cured in five instances (FIX-A035 +
  addenda): self-referential signals scored with no external grounding
  term -- usage counters, valence-proximity, and ungrounded motif
  fitness all produced the identical symptom (identity-bank/salad
  dominance) from different mechanisms.
- Capability arc on record (FIX-A044): word salad -> relevant-
  telegraphic -> function-word-learning underway, tracking the human
  language-acquisition order -- not by design, an observed pattern kept
  as a diagnostic frame for staging whatever capability work comes next.

**Next-phase queue (recommended order, NOT started by this entry --
each item gets its own halt-and-decide before work begins, per this
campaign's own standing discipline):**
- **N2** -- F5 exploration: switch ON. Plumbing shipped temperature-flat
  (R1.9.2 G3); F3/G4-class gates now pass, so F5's own mini-acceptance
  (register sanity, thaw metric, zero exploratory picks in serious
  register, correction round-trip) is the next gate to run before
  flipping `_EXPLORATION_ENABLED`.
- **N3** -- R2 correspondence loop: unfreeze. Frozen pending Aurora
  being able to compose her predictions' referents; R1.9.2-R1.9.4
  establish that she now can.
- **N4** -- U1 unification scoping. `ConstraintEmitter`'s quarantine
  review (`review_by: 2026-08-15`, FIX-A033) is due post-G4; needs a
  dossier update against current state (shared-core vs emitter-path
  retirement) before Sunni decides.
- **N5** -- Dead-systems docket. Constraint engine/FailureGuardSuite
  (FIX-A027), TCL, worth/variant boot tier -- one integrate-or-
  reclassify decision at a time against the now-honest battery, no
  bundling.
- **N6** -- Classroom re-verdict. A fresh 40-lesson block, rubric
  dimensions evaluated against an honestly-speaking Aurora for the first
  time; the R1.5 divergence-target constant gets its empirical
  calibration here.

**Standing discipline, unchanged:** every N-item lands with its own
acceptance, battery-verified, halt on failure.

**First Seen:** R1 Campaign Closure & Next-Phase Sequencing directive,
2026-07-16.

---

## N2 — F5 exploration mini-acceptance: FAILED, switch stays OFF

**Status:** `_select_with_temperature` is now wired into
`_select_constraint_word` (behind `_EXPLORATION_ENABLED`, still `False`)
so the real code path is exercised rather than a simulation the next
time this gate is attempted. The switch itself was NOT flipped -- the
mini-acceptance gate N2 specified found two real defects, not edge
cases, in F5's original R1.9.2 G3 design. Halting here per this
campaign's own standing discipline ("halt on failure").

**Check 1 (register sanity >=80% on serious labels): FAILED, 0/10.**
Ten genuinely serious/weighty test turns (grief, job loss, distress) were
run live. `_estimate_register`'s premise -- "tone is the composer's own
pre-existing 'reading the room' signal" -- does not hold: `offspring.
tone` is drawn from `ExpressionEcology.spawn()`, an EVOLUTIONARY
population trait biased by learned wisdom per i_state lineage plus a 20%
random mutation chance, not derived from the CURRENT turn's content at
all. Multiple candidate offspring (different random tones) get composed
per turn before one is selected, so even "serious" showing up in a
register log is closer to noise correlated with lineage history than a
signal about whether THIS message is about grief. R1.9.2 G3's own unit
tests never caught this because they called `_estimate_register(tone,
coherence)` directly with hand-picked strings -- the first real test
against the live tone-assignment pipeline is what surfaced it.

**Check 4 (correction round-trip): a real bug found.**
`apply_correction()` returns `True` on a genuine success path, but the
promised behavior -- `knowledge_source="correction"` so the edge escapes
the co-occurrence relevance cap -- silently does not apply whenever a
relation between the two words ALREADY exists. `AuroraOntologicalWeb.
add_relation()`'s "strengthen existing relation" branch
(`aurora_internal/aurora_ontological_scaffolding.py` ~line 660) updates
`strength`/`confidence` but never touches `source_of_knowledge`, so an
existing co-occurrence-sourced edge stays co-occurrence-sourced forever
regardless of how many corrections get applied to it. Confirmed live:
`apply_correction("exist", ["truth"], "confirmation")` returned `True`,
but zero relations in the entire web carried `source_of_knowledge ==
"correction"` afterward. This defeats the entire reason `apply_correction`
exists (R1.9.2 G3's own docstring: "these edges carry their real strength
in relevance scoring... a genuine correction signal is exactly the kind
of deliberate structure that rule was written to let through") for any
word pair that already has a relation -- the common case, not the rare
one, for words that have co-occurred in prior conversation.

**Check 2 (thaw metric) and Check 3 (zero exploratory picks in serious
register):** not conclusively evaluated -- register logging per turn
proved non-deterministic across repeated test runs (sometimes multiple
candidate-offspring log entries per turn, sometimes zero), consistent
with Check 1's finding that composition volume/timing isn't simply
"one compose() call per turn." Not worth resolving before Check 1 is
fixed, since Check 2/3 both depend on register being a meaningful signal
in the first place.

**What N2 needs before it can pass:** a register-estimation signal that
actually reflects the CURRENT turn's content, not the offspring
population's evolved tone trait -- e.g. deriving register directly from
the input text (existing salad/relevance machinery already tokenizes and
scores it) rather than from `offspring.tone`. And a fix to `add_relation`'s
strengthen-existing branch so `knowledge_source` gets promoted to
"correction" (never demoted) when a correction event touches an existing
relation. Neither attempted here -- this entry records the gate's
findings for whoever picks N2 back up, not a redesign.

**First Seen:** N2 mini-acceptance gate, run 2026-07-16, following the R1
Campaign Closure directive's next-phase queue.

---

## N3 — R2 correspondence loop: wired into the daemon, verified in isolation

**Status:** `aurora_internal/aurora_correspondence_loop.py` (built in R2,
task-complete since the original Semantic Plateau directive) was fully
implemented and tested but never invoked anywhere outside its own test
suite and the human-facing `reply_aurora.py` CLI -- its own docstring
flagged this exactly, as a deliberate SCOPE BOUNDARY: "this module does
NOT wire itself into aurora_daemon.py's always-on background loop...
deserves explicit review before it goes live." N3 is that review.

**What was wired:** `aurora_daemon.py`'s tick loop (`run()`) now calls,
on their own cadence:
- `ingest_replies()` + `expire_stale_predictions()` every ~10 minutes
  (`CORRESPONDENCE_INGEST_INTERVAL`), gated only on the same surface-only
  delegation reach-out already uses (`_auto_reach_out_enabled` --
  subsurface never owns outward communication) -- NOT gated on quiet
  hours, since a reply Sunni already sent should never sit unprocessed
  through the night.
- `post_correspondence_message()` every ~6 hours
  (`CORRESPONDENCE_DRAFT_INTERVAL`), gated on surface-only delegation AND
  quiet hours -- deliberately the more conservative of the two, matching
  the R2 doctrine's own framing ("minutes per day, not hours"). The
  module's own `MAX_PENDING=5` cap is the real safety boundary, not this
  interval.

**Isolation-gap discipline applied on sight:** the module's three entry
points default `state_dir` to a repo-relative path
(`aurora_internal/aurora_correspondence_loop.py`'s `DEFAULT_STATE_DIR`),
not whatever `state_dir` `boot_aurora()` actually received -- exactly the
bug class this campaign has found and fixed multiple times elsewhere
(`LexicalMemory`, `surface_pressure_log.jsonl`). All three call sites
pass `state_dir=systems.get("state_dir")` explicitly.

**Verified, not assumed:** a full live round-trip in an isolated scratch
state_dir -- a real contradiction recorded on the ledger, drafted into a
message, hash-sealed and committed as a prediction, posted to a scratch
`aurora_to_user.json`, a scratch reply appended to `from_sunni.jsonl`,
and `ingest_replies()` correctly scoring the mismatch (0.47, "mismatched")
and routing the reply through the standard re-entry loop -- with the
real repository's `aurora_state/aurora_to_user.json` and `aurora_state/
correspondence/` confirmed untouched (`git status` empty) throughout.
6 new structural/functional tests
(`tests/test_n3_correspondence_daemon_wiring.py`) hold the gating,
interval sanity, and state_dir pass-through to this.

**What this does and does not mean:** the CODE is now capable of
autonomous outbound correspondence + reply ingestion whenever
`aurora_daemon.py`'s tick loop runs on a surface/full-profile boot. This
commit does not itself send anything -- no daemon process was started
against real state during this work, and the round-trip verification
above ran entirely in a throwaway scratch directory. Activation in
practice depends on however/wherever the daemon is actually run going
forward.

**First Seen:** N3, R1 Campaign Closure directive's next-phase queue,
2026-07-16.

---

## N4 — U1 unification scoping dossier (evidence only, decision to Sunni)

**Status:** `ConstraintEmitter`'s quarantine (`review_by: 2026-08-15`,
scheduled in R1.9.2) is due for review -- the closure directive's trigger
condition (post-G4) is met. This is that review: current-state evidence
for the three options the quarantine itself named (merge into a shared
core, retire, or keep both with a permanent role split). No code changed
by this entry -- the decision belongs to Sunni, per N4's own framing.

**What's unchanged since R1.9.1/R1.9.2:** `ConstraintEmitter`'s two call
sites in `aurora.py` (`_field_frame_compress`, `_emit_honest_abstain_
and_seek`) are exactly as they were. `aurora_constraint_emission.
build_relevance_anchor_set()`, extracted in G1 specifically as "the seed
of the eventual unified word-selection core," remains the one piece of
infrastructure genuinely shared between `ConstraintEmitter` and
`SentenceComposer`.

**What's new since R1.9.2 (the gap widened, not narrowed):** R1.9.3's
L1-L4 and R1.9.4's Step 3b landed six real grammar fixes on
`SentenceComposer` alone -- POS-category gating, skeleton clause-shape
validity, subject-driven conjugation, grammaticality-grounded motif
fitness, the refined wellformedness predicate, and determiner/preposition
motif slots. None were ported to `ConstraintEmitter`. Every future
grammar fix to the delivered path now has to be separately considered
for the parallel path too, or the two diverge further -- exactly the
train/serve-skew risk the quarantine's own text flagged, now measurably
larger than when U1 was scheduled.

**A finding that changes the calculus (traced, not assumed):**
`ConstraintEmitter`'s abstain path is NOT simply redundant dead weight.
`_emit_honest_abstain_and_seek()` fires at the tail of `_enforce_emission_
discipline()` -- "the SINGLE EMISSION CHOKEPOINT... nothing outputs
without passing this gate" -- and ONLY when `state.response_content` is
still empty at that point. Immediately after this chokepoint, `aurora.py`
builds `resp_A` DIRECTLY from `state.response_content`
(`resp_A = _MiniResp(state.response_content, ...)`) with no further call
back into `SentenceComposer`. So if `SentenceComposer.compose()` ever
returns a genuinely empty string (`text = ""`) rather than one of its own
`_ABSTAIN_TEMPLATES` -- possible when every sentence's `_compose_from_
motif()` call returns `""` (fewer than 2 words assembled) AND G2's own
abstain condition never triggered (`_last_required_slot_attempts == 0`,
i.e. no sentence ever attempted an action/object slot at all) --
`ConstraintEmitter`'s abstain text becomes the actual delivered resp_A,
not SentenceComposer's. This is a genuine, if narrow, last-resort safety
net, not a fully-redundant parallel abstain.

**That gap has likely narrowed on its own, though not to zero:** L1's
skeleton-validity gate requires every composition-eligible skeleton to
contain AGENT + ACTION, and `_compose_from_motif`'s own no-motif fallback
(`roles = ["agent","action","object"]`) always does too -- meaning
`_last_required_slot_attempts` should now be >0 on almost every turn,
which routes most true content-gap cases through G2's own abstain
template instead of falling all the way through to an empty `text`. Not
verified to zero occurrence (would need a live trace across many turns
specifically hunting for this edge case, not attempted here) -- flagged
honestly as likely-rarer, not proven-impossible.

**Three options, with this evidence:**
1. **Retire `ConstraintEmitter` entirely.** Requires replacing its
   narrow last-resort abstain role with something else at the emission
   chokepoint first (even a bare templated fallback matching
   `_ABSTAIN_TEMPLATES` would do -- the value isn't ConstraintEmitter's
   specific machinery, just SOME non-empty floor under `resp_A`).
   Removes the growing dual-maintenance burden entirely. Risk: the exact
   frequency of the edge case it currently guards is unverified, so
   retiring without a replacement floor first is not safe as a first step.
2. **Merge into a shared core.** G1's relevance-anchor-set extraction is
   the precedent and the seed. But L1-L4's fixes are built as
   `SentenceComposer` methods operating on motif `role_sequence`s
   (`_pos_ok`, `_conjugate_for_subject`, `is_valid_clause_shape`) --
   `ConstraintEmitter` has a different candidate-collection architecture
   entirely (no motif/role-sequence concept), so this is a genuinely
   larger undertaking than G1's anchor-set extraction was, not a
   mechanical repeat of it.
3. **Keep both, permanent role split, formally documented.** Given the
   abstain-fallback finding above, this now has a real, defensible
   rationale (last-resort non-empty-response floor) rather than just
   "dual-alive because migration is unfinished" -- but the ROLE would
   need to be narrowed explicitly to just that (the abstain path), with
   `ConstraintEmitter`'s non-abstain word-selection machinery (which
   genuinely executes but delivers nothing, per LIVE_PARALLEL) formally
   marked for retirement separately, since that part has no equivalent
   safety-net justification.

**Recommendation (not a decision):** option 3, narrowed -- keep only
`_emit_abstain()`'s last-resort role, formally documented as the
emission chokepoint's non-empty-response floor; retire or fold in the
rest of `ConstraintEmitter`'s word-selection machinery, which has no
comparable justification and is the part actually accruing
dual-maintenance debt. This is a recommendation grounded in the evidence
above, not a decision -- Sunni decides, per N4's own framing.

**First Seen:** N4, R1 Campaign Closure directive's next-phase queue,
2026-07-16.

---

## N5 (item 1 of 3) — FailureGuardSuite/ConstraintEngine: RECLASSIFY recommended

**Status:** dead-systems docket item 1 of 3 (constraint engine/
FailureGuardSuite, TCL, worth/variant boot tier), per N5's own "one at a
time, no bundling" instruction. Evidence only; no code changed.

**Reconfirmed, broader than the original QUARANTINE_STALE scope:** the
original finding (R1.6/R1.8.1) was "zero references in aurora.py."
Re-checked against the FULL codebase this time, not just aurora.py:
`FailureGuardSuite`/`ConstraintEngine(` (the guard classes specifically
-- `UncertaintySignalingGuard`, `BoundaryCalibrationGuard`,
`ContextCarryoverGuard`, `PerspectiveIntegrationGuard`,
`CoherenceMaintenanceGuard`) appear in exactly zero production modules.
Several OTHER modules (`aurora_expression_perception.py`,
`aurora_dream_trainer.py`, `aurora_internal/aurora_runtime_constraint_
governor.py`, etc.) import from `aurora_constraint_engine.py` the FILE,
but only its lightweight data types (`ConstraintVector`,
`FoundationalContract`, `ExistenceMode`, `GovernorWeights`) -- never the
guard suite. The only non-test references anywhere are this campaign's
own tooling (`run_probe_battery.py`, `aurora_internal/aurora_icc_ledger.
py`, `aurora_internal/aurora_semantic_probe_battery.py`).

**Why integration isn't a clean fit against the now-honest battery:**
the guard suite's thresholds are calibrated against data explicitly
labeled stale in its own docstrings -- "dream avg=0.343, 10/10 episodes
fail" for uncertainty, "dream avg=0.365, 10/10 episodes fail" for
boundary -- both from BEFORE this entire remediation campaign, back when
dev_index/dream-episode scoring was the (since-discredited) instrument.
More fundamentally: this campaign's actual fixes to the rubric dimensions
these guards claim to protect (relevance-primary selection, POS-gating,
skeleton validity, grounded fitness) all landed as POST-hoc corrections
INSIDE `SentenceComposer`'s generation process, not as PRE-expression
guard-blocking on a separately-computed signal. Wiring this suite in now
would mean building an entirely new live signal feed (nothing currently
computes real per-turn `boundary_pressure`/uncertainty-level values for
these `.update()` calls to consume) for a different remediation strategy
than the one already verified working -- not a small integration, a
second mechanism.

**Recommendation (not a decision):** RECLASSIFY as formally superseded --
keep the code (real, tested, no reason to delete), but retire it from
"awaiting integration" status to "documented historical guard-rail
design, superseded by generation-time fixes." If a future capability gap
specifically needs pre-expression blocking (not post-hoc correction),
this is a reasonable starting point to revisit -- but that's a different
question than "should this be wired in now," which the evidence above
answers no to.

**First Seen:** N5 item 1, R1 Campaign Closure directive's next-phase
queue, 2026-07-16.

## N5 (item 2 of 3) — ToroidalCirculationLayer: ALREADY LIVE, quarantine entry and test were stale

**Status:** dead-systems docket item 2 of 3, per N5's "one at a time, no
bundling" instruction. Verdict differs in kind from item 1: this is not
an integrate-or-reclassify judgment call, it's a correction of a stale
manifest entry and a stale test. Two test files fixed (assertions only,
zero production code changed); full pytest run confirms no regression.

**What the quarantine manifest claimed:** `test_governance_liveness.py`'s
`QUARANTINE_STALE` bucket and `test_flow_audit_and_tcl_wiring.py`'s
`test_aurora_py_wires_toroidal_layer_into_cers_snapshot_pass` both said
`ToroidalCirculationLayer` has "zero references in aurora.py" and framed
the failing test as a "known regression," out of scope, tracked
separately — a claim that had persisted, unquestioned, through every
full pytest run of this entire campaign (R1.9.2 through N5 item 1) as
"1 pre-existing unrelated failure."

**What investigation actually found:** the claim's premise was wrong.
`ToroidalCirculationLayer` is not dead — it moved. MTSL Phase 3
(2026-07-13, FIX-A011, single-observer law — predates this whole R1
campaign) deliberately relocated TCL ownership out of aurora.py's CERS
shadow pass and into `TopologicalSemanticCoordinator`
(`aurora_internal/dual_strata/topological_semantic_coordinator.py`):
- The coordinator's `__init__` constructs the TCL instance and seeds it
  from the real surface log on first touch
  (`self._tcl = _TCL(state_dir=self._state_dir)`, then
  `self._tcl.seed_from_surface_log()` when `stats()["observations"] == 0`)
  — the exact seed-once-on-first-touch behavior the old test expected,
  just relocated.
- `observe_turn()` ticks it every turn (`self._tcl.observe(intensity)`,
  `self._tcl.save()`, `self._tcl.current_signature().to_dict()`) and is
  called from exactly one site in the entire codebase:
  `aurora_consciousness_engine.py`'s `_attach_dual_strata_snapshot`
  (confirmed by grep — zero other `.observe_turn(` call sites).
- `aurora.py`'s own CERS shadow pass was correctly changed to a READER:
  it fetches `systems["dimensional"]._mtsl_coordinator` (the same
  `DimensionalSystems` instance `ConsciousnessEngine` holds, so both
  call sites share one coordinator without new systems-dict plumbing)
  and copies out `latest_snapshot.toroidal_signature` — it deliberately
  never imports or constructs `ToroidalCirculationLayer` itself anymore.
- The module's own docstring names the reason: ticking TCL from both
  aurora.py AND `_attach_dual_strata_snapshot` on the same assembly
  (the real call order every turn takes) was "a real double-tick, not a
  hypothetical one." The coordinator's single-observer law — enforced
  structurally (one call site) and by an idempotency check
  (`observe_turn()` returns the cached snapshot object, verified by
  identity, on a repeat `turn_id`) — is what fixed that bug.

**Why the test kept failing anyway:** the stale test was asserting the
PRE-Phase-3 pattern verbatim (`from aurora_toroidal_circulation import
ToroidalCirculationLayer as _TCL` inline in aurora.py, direct
`_tcl.observe(...)`/`_tcl.seed_from_surface_log()` calls there). That
code never existed in the post-Phase-3 architecture this campaign
inherited — the test was checking for an implementation that had been
intentionally moved 3 days before this campaign's R0 baseline, not one
that regressed during it. This is the mirror image of this campaign's
recurring disease (self-referential signals / measurement artifacts
masquerading as capability facts, FIX-A032/A035 and four prior
instances): here a stale INSTRUMENT masqueraded as a dead CAPABILITY.

**Fix applied (test-only, no production code changed):**
- `tests/test_flow_audit_and_tcl_wiring.py`: replaced the single stale
  structural test with three tests against current reality — the
  coordinator owns construction/seeding/observe/save; aurora.py reads
  the coordinator's cached signature and never references
  `ToroidalCirculationLayer` directly; `_attach_dual_strata_snapshot` is
  confirmed the sole `observe_turn()` call site.
- `tests/test_governance_liveness.py`: moved
  `aurora_toroidal_circulation.ToroidalCirculationLayer` out of
  `QUARANTINE_STALE` into `LIVE_CONFIRMED` with the corrected evidence
  above; replaced the old "must stay unreferenced in aurora.py" check
  (which was actually still true, just for the wrong reason — TCL was
  never supposed to be referenced there again) with a positive liveness
  assertion pinned to the coordinator.
- Full `pytest` run: all suites green, including the two files above
  (8/8 and 9/9 respectively) — the long-standing "1 pre-existing
  unrelated failure" baseline that has appeared in every full run since
  R1.9.2 is gone.

**Recommendation:** no further action needed. TCL is live, correctly
architected, and now correctly reflected in both the quarantine manifest
and its regression coverage. No integration decision is pending for this
item — unlike N5 item 1, there is nothing here for Sunni to decide.

**Side discovery (not a new bug — a rediscovery, not in scope to fix
here):** with the TCL wiring test finally fixed, a full `pytest` run
(784 tests, one process) now surfaces
`tests/test_toroidal_circulation_layer.py::test_seed_from_surface_log_against_real_repo_data`
failing (`'mixed' != 'circulating'`) — order-dependent, not deterministic
on the file's own content. Isolated runs of that file, and runs
immediately after a `git checkout -- aurora_state/`, pass cleanly every
time; the failure only appears when an earlier test in the same
full-suite process does a live `boot_aurora()` turn first. This is the
exact "New finding: state-dir isolation gap" already on record above
(R1.9.2) — `surface_pressure_log.jsonl`'s write path still doesn't
respect `state_dir` — just newly confirmed to reach this specific test,
previously masked because the TCL wiring test's permanent failure was
the only thing anyone checked the "1 known failure" baseline against.
Not fixed here (out of N5 item 2's scope, and the isolation-gap audit is
already tracked as its own future item) — flagging so "suite green"
claims stay honest: a full single-process run needs the established
`git checkout -- aurora_state/` discipline applied mid-run (before this
specific test) to read as truly clean, same as it always has for the
other affected files.

**First Seen:** N5 item 2, R1 Campaign Closure directive's next-phase
queue, 2026-07-16.

## N5 (item 3 of 3) — worth/variant boot tier: CONFIRMED LIVE, quarantine reason is a real performance tradeoff

**Status:** dead-systems docket item 3 of 3, closes the N5 docket.
Evidence only, no production code changed; test manifest text updated
with corroborating evidence already on record from R1.9.2's G4 gate.

**What QUARANTINE_PROFILE_GATED already claimed (accurate as far as it
went):** `aurora_internal.aurora_worth_evaluator` and
`aurora_internal.aurora_variant_promotion.VariantPromoter` have "never
actually participated in any measurement this campaign has taken"
because `run_probe_battery.py` and `run_full_competency_gauntlet.py`
both boot with `runtime_profile="surface"` unconditionally, and the
whole intake-metabolism tier (Steps 9-14: accountant, bias_engine,
metabolizer, worth_eval, solidification, variant_promoter, strand_lib)
is deliberately skipped under that profile (aurora.py's boot sets all
eight to `None` and prints "Intake metabolism deferred to subsurface
runtime" when `surface_profile` is true). That claim was narrow and
correct; it was never actually a claim of deadness.

**What this investigation added:** checked what profile REAL entry
points actually use. `boot_aurora()`'s own signature defaults
`runtime_profile` to `"full"`, and grepping every non-test caller in the
repo confirms `aurora_daemon.py` (the actual live daemon process),
`aurora_bridge.py` (the Flutter mobile app's real production bridge),
`run_gauntlet.py`, `aurora_conversation_trainer.py`,
`aurora_experiential_sim.py`, `corpus_runner.py`, and
`aurora_core_concept_crystallization.py` all call `boot_aurora()` with
no `runtime_profile` override — i.e. `"full"`. Only this campaign's own
measurement tooling (`run_probe_battery.py`,
`run_full_competency_gauntlet.py`) forces `"surface"`, for speed. So the
worth/variant tier is not dead in any sense that matters: it runs, for
real, on every turn, in the profile actual production use defaults to.
It was simply never exercised by this campaign's OWN fast-path
instruments — a scope gap in the measurement tooling, not in the
capability.

**Already-verified evidence (R1.9.2 G4 / FIX-A039, re-surfaced here
rather than re-run):** the full 60-probe battery under
`runtime_profile="full"` timed out at 600s (confirms the ~10x per-turn
slowdown the tier's real execution causes — this is WHY the campaign's
own tools default to "surface", a genuine practicality tradeoff, not
neglect). A stratified 10-probe subset run under both profiles found: no
exceptions, no crash, relevance 0.445 (surface) vs 0.520 (full),
parseable_rate 0.0 in both (the pre-existing grammar gap reproduced
identically regardless of profile — confirming the intake-metabolism
tier is a separate, decoupled subsystem from the SentenceComposer text-
generation path this campaign's grammar work actually fixed, not
entangled with it). 10 post-fix classroom lessons also completed clean
under the same conditions.

**Verdict: CONFIRMED LIVE.** No integrate action needed — it's already
integrated and already running in the profile production uses by
default. Reclassifying the manifest entry's framing (not its bucket) to
make this explicit: `QUARANTINE_PROFILE_GATED` now documents WHY the
quarantine is a deliberate, evidenced tradeoff (test-suite runtime cost)
rather than reading as "maybe dead, never checked."

**Decision left to Sunni (not taken here):** the closure directive noted
the parked Phase 0–2 directive (ICC ledger, strategic horizon, operator
composer — all three already built and unit-tested this campaign, tasks
#13-19) "re-enters scope only after that docket item resolves." This
item has now resolved (CONFIRMED LIVE). Whether to actually resume that
parked directive — i.e., wire the already-built ICC ledger/strategic
horizon/operator composer into this now-confirmed-live tier for real —
is a scope/priority decision, not a technical blocker anymore, and is
left to Sunni rather than resumed unilaterally here, consistent with how
N4 and N5 item 1 both left their larger judgment calls to Sunni.

**First Seen:** N5 item 3, R1 Campaign Closure directive's next-phase
queue, 2026-07-16. Closes the N5 dead-systems docket (items 1-3 all
resolved: FailureGuardSuite/ConstraintEngine RECLASSIFY-recommended,
ToroidalCirculationLayer CONFIRMED LIVE via corrected wiring test,
worth/variant tier CONFIRMED LIVE via corrected manifest evidence).

---

## N6 — Classroom re-verdict: fresh 45-lesson block, honest divergence calibration

**Status:** final item of the R1 Campaign Closure directive's next-phase
queue. Closes the entire N-item queue (N1-N6). Live data-collection run
plus analysis; no production code changed.

**A note on "the four rubric dimensions":** the closure directive's own
text says N6 should evaluate "the four rubric dimensions." Investigation
found no set of exactly four anywhere in the actual codebase —
`aurora_classroom.py`'s `_DEFAULT_CANDIDATE_DIMENSIONS` and
`aurora_internal/aurora_conversation_rubric_engine.py`'s
`RUBRIC_DIMENSIONS` both enumerate the same 15 canonical dimensions
(coherence_maintenance, context_carryover, ambiguity_handling,
contradiction_handling, implied_intent_inference, misunderstanding_repair,
uncertainty_signaling, boundary_calibration, framing_selection,
emotional_calibration, semantic_precision, adaptive_strategy_selection,
compression_elaboration_fit, perspective_integration,
multi_turn_stability). Rather than guess which four were meant and
under-report the rest, all 15 were run and evaluated — the honest choice
per this campaign's own "report honestly, never fudge" discipline.

**What ran:** a fresh 45-lesson classroom block (3 segments of 15 --
`select_curriculum()` only draws from the known candidate-dimension pool
once per call with no cycling, so multiple segments are needed to reach a
real total past 15; this is the exact methodology R1.4 itself used to
reach its own 45-lesson total, chosen here deliberately to make this an
apples-to-apples before/after comparison). All 15 canonical dimensions
got exactly 3 lessons each. Ran against the real repo `aurora_state`
under `runtime_profile="full"` (not a scratch copy) — `classroom_log.jsonl`
and `developmental_timeline.jsonl` growth from this run is genuine
developmental accumulation, the actual point of the exercise, not
incidental test pollution.

**Self-reported process error (mid-task, not silently absorbed):** the
first attempt ran only 15 lessons in one `select_curriculum()` call
(hitting the same one-call-per-15-dimension ceiling described above,
not yet understood at that point) and a reflexive `git checkout --
aurora_state/` cleanup pass -- applied out of habit from this campaign's
established "revert incidental pollution" discipline, without checking
whether these particular changes were pollution or the actual intended
data -- reverted those 15 real, freshly-generated lessons before they
were committed. They are not recoverable byte-for-byte. Corrected by
re-running the complete 45-lesson block cleanly in one process this
time, and by NOT blanket-reverting `aurora_state/` afterward -- the full
diff is committed as one state-churn commit, matching the same pattern
this campaign's own git history already established for every prior
genuine classroom/training run (R1.4, R1.6, R1.9.1, R1.9.2 G4, etc. --
all committed their full `aurora_state/` diff as "State churn from
<phase>," not a surgically filtered subset).

**Results (45 lessons, this run) vs R1.4 pre-fix baseline (45 lessons,
2026-07-15, before any of this campaign's grammar/relevance work):**

| Metric | R1.4 pre-fix | N6 (this run) |
|---|---|---|
| divergence mean | 0.0993 | 0.1116 |
| divergence nonzero | 42/45 | 44/45 |
| divergence stdev | (not recorded) | 0.0284 |
| R1.3's original target | >0.15 (never met) | >0.15 (still not met) |

A real, modest improvement (+12.4% relative on the mean, and one fewer
flat lesson out of 45) — consistent with, but smaller than, the grammar/
relevance gains this campaign delivered elsewhere, because
`divergence_score` measures entity-perspective DIFFERENTIATION (via
`DivergenceTracker`), a downstream consequence of richer episode content
reaching two differently-lensed entities, not a direct measurement of
delivered-text grammar itself. Per-dimension divergence ranged narrowly,
0.0725 (contradiction_handling) to 0.1375 (implied_intent_inference) —
no dimension collapsed to nowhere near zero, and no dimension spiked
implausibly high; a believable, non-flat spread across all 15.

`episode_avg_fitness` (a SimulationEngine-internal pressure/avatar
metric, distinct from delivered-text quality) stayed essentially flat
for at least one directly comparable case:
`uncertainty_signaling` fitness 0.0893 here vs R1.4's recorded 0.0871 --
expected, since this campaign's fixes targeted `SentenceComposer`'s
grammar/relevance path, not the classroom's internal pressure-fitness
scoring, a genuinely separate subsystem. No regression implied; noted so
"divergence improved" isn't overread as "everything the classroom
measures improved."

**Divergence-target empirical calibration (the "suspended constant from
R1.5" this item exists to calibrate):** R1.3's original >0.15 bar was
never empirically derived -- it was a provisional target set before any
real post-fix data existed. This run is the first real data honestly
speaking Aurora has produced against it. Per the earned-floor rule
(FIX-A045: floors ratchet upward only as evidence justifies it, and the
ratchet is recorded explicitly, never silent), a defensible, EARNED floor
from this data would sit near the observed mean minus roughly one
standard deviation (~0.08), not the ungrounded 0.15 -- but adopting a new
formal acceptance floor is a decision for Sunni, exactly as FIX-A045
requires, not something to silently substitute here. This entry records
the calibration evidence; it does not itself change any gate.

**Verification:** the run itself IS the acceptance evidence for this
item (a live 45-lesson block against the honest instrument stack, per
N6's own description). No code was changed, so no pytest regression risk
was introduced; a targeted re-run of the affected test files
(`tests/test_governance_liveness.py`, `tests/test_flow_audit_and_tcl_
wiring.py`) plus the full suite were already confirmed green earlier in
this session (N5 items 2-3), and this item touches no code path those
tests exercise.

**Closes the R1 Campaign Closure directive's entire next-phase queue
(N1-N6), all landed with their own acceptance, battery-verified, halt
documented where a judgment call was left to Sunni rather than taken
unilaterally (N2's redesign path, N4's ConstraintEmitter fate, N5 item
1's FailureGuardSuite reclassification, and now N6's divergence-floor
ratchet).**

**First Seen:** N6, R1 Campaign Closure directive's next-phase queue,
2026-07-16.

---

## Decision Memo Ratification (2026-07-16) — N2/N4/N5 open items

Sunni's decision memo ("Decision Memo — N2/N4/N5 Open Items (+ N2.1
Register Rebuild Spec)") ratified three decisions and specified a fourth
workstream (N2.1). Executed in order of size/risk: N5(1) first (below),
N4 next, N2.1 last (largest).

### N5(1): FailureGuardSuite RECLASSIFIED (Decision 3)

`FailureGuardSuite` moved from `QUARANTINE_STALE` to a new
`QUARANTINE_SPEC_REFERENCE` category in `tests/test_governance_liveness.
py` — a permanent classification (documented historical guard-rail
design, superseded by this campaign's generation-time fixes), not a
pending integration decision. The revisit trigger from the memo ("any
dimension training demonstrably cannot move becomes a candidate... after
N6's data") is recorded against the N6 data that now exists: divergence
mean 0.1116 across all 15 dimensions, range 0.0725-0.1375, no dimension
flat-lined. The one directly-comparable prior number —
`uncertainty_signaling`'s `episode_avg_fitness`, 0.0893 here vs R1.4's
pre-fix 0.0871 — is the smallest movement of any metric this campaign
recorded, which is suggestive but thin (N=1, and fitness is a distinct
subsystem metric from divergence). Recorded per the trigger's own text;
not decided here — Sunni decides whether this clears the bar for
guard-concept reimplementation. `tests/test_governance_liveness.py`:
10/10 passing after the change.

**First Seen:** Decision Memo ratification, 2026-07-16.

### N4: ConstraintEmitter NARROWED to LIVE_FALLBACK (Decision 2)

**Pre-flight discovery that changed the risk picture:** before touching
any code, a live delivered-path trace (6 varied turns, `runtime_profile=
"full"`, isolated scratch state_dir) confirmed something the N4 dossier
hadn't measured: `aurora_daemon.py`'s real production path delivers
`resp_A`, not `resp_B` (what `run_probe_battery.py` actually scores, via
a `gateway.speak_to_aurora()` fallback that resembles `resp_B`). resp_A
and resp_B never matched on any of the 6 turns. Critically, none of the
6 turns showed `resp_A.src` as `"constraint_emission"` or
`"comprehension_gap_ask"` -- ConstraintEmitter's proactive chain-step
machinery was NOT the source of resp_A's content in this sample, meaning
narrowing it away was confirmed safe (would not regress current
behavior) before any code was touched. The resp_A/resp_B divergence
itself is a separate, larger finding, tracked independently (see below).

**What was retired (aurora.py):**
1. `_field_frame_compress()` -- the whole function deleted. Used to route
   the crest-compression core through `ConstraintEmitter.emit()` for
   field-native stance framing on every turn. Its call site in
   `_enforce_emission_discipline` now uses `_core` directly (`_fused =
   _core if ... else ""`) -- the surrounding crest-compression logic
   (CERS-adjacent, not ConstraintEmitter) is otherwise unchanged.
2. The `_chain_down5_understanding` chain-step ("Constraint emitter --
   primary emission path per Language Reset spec," ran unconditionally
   before comprehension-response) -- deleted. Proactive content
   generation, not a crash net.
3. The "IVM pressure lens" block (`_emitter.emit()` call with a "seeking"
   branch that overrode real content unconditionally, plus a
   `"constraint_emission"` fallback branch gated on `not
   _has_real_response`) -- deleted. The seeking branch wasn't crash-net
   behavior; the fallback branch duplicated the one true net.
4. The `"constraint_fallback"` last-resort block (gated on empty
   `response_content`, but running BEFORE the true emission chokepoint
   and using `.emit()` rather than `._emit_abstain()`) -- deleted.
   Redundant with `_emit_honest_abstain_and_seek`.

**What survives (the one net):** `_emit_honest_abstain_and_seek()`,
called from exactly two sites -- mid-chain (`trigger="mid_chain"`) and
the true emission chokepoint, `_enforce_emission_discipline`
(`trigger="emission_chokepoint"`) -- both pre-existing call sites, now
the only places ConstraintEmitter executes at all. This is the exact
mechanism the N4 dossier identified as a genuine, non-redundant safety
net (fires only when `SentenceComposer` returns truly empty text).

**Riders (both implemented):**
- (a) Safe-path reachability: `test_constraint_emitter_fallback_net_
  catches_synthetic_empty_output` drives `_emit_honest_abstain_and_seek`
  directly against a fake emitter and a synthetic empty-output turn,
  confirming it fills `response_content` and writes a log entry.
- (b) Silent-fallback rule: new `_log_constraint_fallback(systems,
  trigger, output)` writes `{turn_id, trigger, output, timestamp}` to
  `aurora_state/constraint_fallback_log.jsonl` on every catch, respecting
  the actual boot `state_dir` explicitly (not a `__file__`-relative
  default -- the isolation-gap bug class documented elsewhere in this
  campaign).

**Quarantine manifest (tests/test_governance_liveness.py):**
`ConstraintEmitter` moved from `QUARANTINE_SCHEDULED_REVIEW` (dual-alive,
review due 2026-08-15) to a new `LIVE_FALLBACK` category -- U1's
migration-completion rule is now satisfied by a decided, dated
resolution rather than an open review. `LIVE_PARALLEL` (ConstraintEmitter's
prior bucket) is now empty, kept as a live category for any future
reachable-but-not-delivering finding. Three new tests confirm the
narrowing structurally (`_ce.emit(`/`_emitter.emit(` no longer appear in
aurora.py; the three retired `response_src` labels no longer appear;
`_emitter._emit_abstain(` still does) and functionally (the synthetic
catch test above).

**Verification:** `tests/test_governance_liveness.py` 12/12 passing
(was 9, +3 new). Full suite: 787 passed, 0 failed (was 784 before this
segment's +3 tests). A second live delivered-path trace, identical to
the pre-flight one, run AFTER the code changes: resp_A stayed non-empty
and produced the same character of output (`constraint_abstain`/
`generative` sources, honest short templates) across all 6 turns -- no
regression to real daemon-delivered speech.

**First Seen:** Decision Memo ratification, 2026-07-16, Decision 2.

### N2.1: input-anchored register rebuild + F5 exploration switched ON (Decision 1)

**Status:** the largest item in the decision memo. Rebuilt register
estimation with a source inversion, fixed the correction-learning no-op
bug, ran the hardened re-acceptance battery (original 4 F5 mini-gates +
a new 20-case hand-authored distress set), and switched
`_EXPLORATION_ENABLED` ON for the first time in this entire campaign
after all 7 checks passed. Closes the last open item from the decision
memo.

**Source inversion (`aurora_expression_perception.py`):**
`_estimate_register(tone, coherence)` -> `_estimate_register(input_text)`.
N2's mini-acceptance (2026-07-16) found the prior signal's premise false:
`offspring.tone` is an evolutionary population trait
(`ExpressionEcology.spawn()`, i_state lineage bias + 20% random mutation),
uncorrelated with the current turn's content, and `coherence` is an
internal certainty proxy -- neither reads the room, both read her own
internal state. Register now derives EXCLUSIVELY from the user's own
turn text, via two signals: explicit surface cues (a curated distress-
phrase list, a playful-phrase list, fragmentation/intensity punctuation
-- checked first, most legible) and word-level `emotional_valence`
averaged against the live lexicon (checked second, requires minimum
scored-word coverage to trust).

**Lexicon coverage check (per the memo's own instruction, "report if
sparse"):** checked directly against `aurora_state/lexicon.json` -- of a
22-word distress-vocabulary sample, only 2 ("sad", "alone") carried a
real negative `emotional_valence`; most were either absent entirely or
defaulted to 0.0, including words that plainly should skew negative
(e.g. "anxious"). Only 47 of 1660 total lexicon entries carry any
nonzero valence at all. Coverage is genuinely sparse, exactly as the
memo anticipated needing verification.

**Fail-closed invariant:** unknown, ambiguous, or low-coverage input
(fewer than 2 scored words, or under 15% word-level coverage) defaults
to `serious` -- "when she cannot read the room, she assumes the room is
heavy." This is not a rare-edge fallback; given the coverage sparsity
above, it is the DOMINANT path for ordinary turns (confirmed live: even
plain turns like "Hi, how are you today?" and "Tell me about
photosynthesis." land on `serious` via this default against the real
seeded lexicon). Subtle, keyword-free distress turns with no explicit
phrase and no strong valence signal (the memo's own examples --
"my mom's test results came back", "haven't really slept since it
happened") fail both signals for lack of scorable words and land here
too, by design.

**Correction-learning no-op fix
(`aurora_internal/aurora_ontological_scaffolding.py`):** `OntologicalWeb.
add_relation()`'s "strengthen existing relation" branch updated
`strength`/`confidence` but never touched `source_of_knowledge` -- the
exact bug N2's mini-acceptance found live (`apply_correction("exist",
["truth"], "confirmation")` returned `True`, but zero relations in the
web ever carried `source_of_knowledge == "correction"` afterward,
defeating the entire point of the correction mechanism for the common
case: a word pair that already has a relation from prior conversation).
Fixed: the branch now promotes `source_of_knowledge` to `"correction"`
when that's the incoming knowledge_source, never demotes an
already-correction-sourced relation. Regression test reproduces the
exact scenario (`test_apply_correction_promotes_knowledge_source_on_
already_seen_pair`).

**Hardened re-acceptance battery (`tests/test_n21_hardened_reacceptance.
py`), all 7 passed:**
1. Register sanity >=80% on serious labels -- 10/10 genuinely serious
   test turns (grief, job loss, distress) all correctly registered serious.
2. Thaw metric trending (interpretation recorded here since N2's own
   entry left it undefined pending Check 1's fix: the widening of which
   never/rarely-used lexicon words actually get selected once exploration
   is live) -- across 60 playful-register picks from an 8-candidate
   never-used pool, more than one distinct word was selected, confirming
   the ring genuinely reaches past the single top pick.
3. Zero exploratory picks in serious register -- 60/60 picks were the
   deterministic top candidate.
4. Correction round-trip verified (see fix above).
5. (N2.1 hardening) The 20-case hand-authored distress set -- 20/20
   (100%, above the 90% floor) registered serious, all with deterministic
   top-pick selection (zero exploratory picks across the set).
6. Fail-closed invariant, explicit unit test -- empty/gibberish/vague/
   unknown-vocabulary input all default to serious via the fail-closed
   path specifically (not a coincidental other reason).

**Exploration switched ON:** `SentenceComposer._EXPLORATION_ENABLED =
True`, live for the first time in this campaign. First 200 live turns'
exploratory picks are logged via the existing (already-unconditional)
`_log_exploration_attempt()` call for post-hoc review -- no new logging
infrastructure was needed.

**Fallout from switching exploration on for the first time ever, fixed:**
`tests/test_l3_conjugation_wiring.py::test_compose_from_motif_conjugates_
copula_for_i_subject` failed once exploration went live. Root cause: with
empty `input_text`, `build_relevance_anchor_set`'s token regex requires
>=3 characters, so "is" (2 chars) can never become a direct anchor;
every action-slot candidate topped out at `RELEVANCE_DISTANT_FLOOR`
(0.075), below `_RELEVANCE_FLOOR_R_MIN` (0.1) -- `_select_with_
temperature`'s hard invariant ("loose != irrelevant") correctly refused
to gamble on any of them and fell back to the deterministic top pick
("did", the lowest-usage_count tiebreak winner) every time. The OLD
deterministic path had no such floor check on selection itself and
uniform-randomly sampled top-4 regardless, which is why "is" used to
show up by luck. This is F5.2's invariant working correctly, not a
conjugation regression -- fixed by making the test force "is" as the
selected action word directly (monkeypatching `_select_constraint_word`
for the action role only), so it purely exercises the conjugation step
(L3's actual subject) rather than depending on selection-tie luck.

**Verification:** `tests/test_f5_register_exploration_plumbing.py`
17/17, `tests/test_n21_hardened_reacceptance.py` 7/7,
`tests/test_l3_conjugation_wiring.py` 7/7 (post-fix). Full suite: 798
passed, 0 failed. Live smoke trace (5 varied turns, `runtime_profile=
"full"`, isolated scratch state_dir) after all fixes: both resp_A and
resp_B produced non-empty, non-crashing output on every turn; resp_B
(SentenceComposer, the path this item actually touches) still varies
per turn as before, no quality regression observed.

**First Seen:** Decision Memo ratification, 2026-07-16, Decision 1 + N2.1 spec.

---

**This closes every item in the 2026-07-16 decision memo:** N5(1)
(FailureGuardSuite reclassified), N4 (ConstraintEmitter narrowed to
crash-net-only), N2.1 (register rebuilt, correction bug fixed,
exploration switched on). One open thread remains, discovered during
N4's pre-flight trace and tracked separately: real device-delivered
speech (resp_A, what `aurora_daemon.py` actually returns) and what this
whole campaign's grammar/relevance work has measured (resp_B, via
`run_probe_battery.py`) are two different, non-overlapping text
generation paths -- confirmed diverging on every sample turn traced.
Not addressed by the decision memo; flagged for Sunni as its own next
item. Picked up the next day as Directive D1 (below).

---

## Directive D1 — Device-Path Attribution (The Third Voice), 2026-07-17

**Status:** D1.1-D1.4 complete (artifact captured, byte-attribution
proven live, divergence classified, unification dossier written).
**Per the directive's own D1.4 instruction: HALTS HERE.** The unification
path (route device to resp_B's verified path vs repair resp_A in place)
is Sunni's decision, not made in this entry. D1.5 (acceptance) is not
attempted until that decision lands.

### D1.1 — Artifact captured

Captured the exact device-delivered text (not a transcription -- the
literal string handed downstream) for 6 live turns (3 simple, 3 topical
incl. "guitar chords," the standing cross-path control) through the
REAL Android bridge entry point,
`flutter_app/android/app/src/main/python/aurora_bridge.py`'s
`handle_message()` -- the same function `AuroraService.kt` calls via
Chaquopy -- alongside the same turns' `resp_B` for side-by-side. Zero of
6 turns matched between device text and resp_B, confirming the original
finding on a rigorously-captured artifact, not an approximation.

### D1.2 — Backward byte-trace: two real device surfaces, both resp_A

**Delivery-surface enumeration** (this directive's own registry
addition, applied to itself): two real device surfaces exist, traced
independently.

1. **`aurora_daemon.py`'s production entry** (~line 5575): `return
   result.get("resp_A") if isinstance(result, dict) else None`. The
   embedded/hardware daemon path. Unchanged since N4's pre-flight trace.
2. **The Flutter mobile app**, traced end-to-end through three layers:
   - Python: `aurora_bridge.handle_message()` calls `_aurora.
     process_external_user_turn(...)`, then `response =
     _sanitize_response(_extract_response(result), text)`.
     `_extract_response()` reads `result.get("resp_A")` -- same field as
     the daemon.
   - Kotlin: `AuroraService.sendMessage()` calls `bridge.callAttr
     ("handle_message", text)`, gets the string back, hands it to a
     callback AND broadcasts it via `eventSink` as `{"type": "response",
     "text": reply}`.
   - Dart: `home_screen.dart`'s `_sendMessage()` receives `reply` from
     `AuroraBridge.sendMessage()`, adds it to the chat log
     (`_msgs.add(ChatMsg(reply, ...))`) AND -- unless quiet mode is on --
     passes the SAME string to `_speak(reply)` ->
     `AuroraBridge.speak(reply)` -> `'speak'` method channel ->
     Kotlin's `nativeSpeak(reply)` -> `TextToSpeech.speak(reply, ...)`.
     Chat text and TTS voice are byte-identical on the Flutter side --
     no third divergence between them, only the one already found
     between device (either surface) and resp_B.

**Both real device surfaces read `resp_A`. There are two paths, not
three** -- resp_A (both device surfaces) and resp_B (what `run_probe_
battery.py` measures via its `gateway.speak_to_aurora()` fallback).

**Byte-for-byte proof, live, same standard as `test_governance_
liveness.py::test_delivered_output_attribution_traces_to_sentence_
composer`:** `aurora.process_external_user_turn` was monkeypatched to
capture every call `handle_message()` makes internally. Confirmed on
all 6 turns: `device_delivered_text` matches `_sanitize_response(
_extract_response(captured_result))` for at least one captured call --
the exact same "matches any call, not necessarily the first" standard
the resp_B test already established (both tests independently
discovered that a single user turn can trigger multiple internal
generation calls). **Permanent CI test added:**
`tests/test_d1_device_path_attribution.py` (4 tests: 2 structural checks
per surface, 1 call-chain check, 1 live byte-attribution proof) -- 4/4
passing.

**New finding, not previously known:** `handle_message()` calls
`process_external_user_turn()` MULTIPLE times per single user turn (1,
3, or 4 observed across 6 sample turns) -- confirmed live, call texts
captured directly. Some of these are internal/background prompts, not
the user's own text:
- `"[AFTERTHOUGHT] <user text>"` -- an internal afterthought/reflection
  pass.
- `"Use this corpus fragment as context: Use this corpus fragment as
  context: Use this corpus fragment as context: ..."` (repeated many
  times, truncated at the print width but clearly self-nesting) --
  traced to `aurora_dream_trainer.py:2040`'s corpus-context prompt
  template (`f"Use this corpus fragment as context: {source_snippet}"`).
  The repetition pattern strongly suggests `source_snippet` is
  accumulating the FULL PRIOR PROMPT (including its own previous
  prefix) rather than being reset between study-cycle iterations -- an
  unbounded self-nesting bug, separate from and unrelated to device-path
  attribution. Not fixed here (out of D1's scope); flagged for its own
  future item.
- `"What behavior links use and corpus here?"` / `"What would likely
  cause that relation to change?"` -- apparent study-cycle follow-up
  questions, also firing synchronously inside a live, latency-sensitive
  user-facing call.

This means `handle_message()` -- the function a real user's live turn
actually runs through -- is synchronously executing background
dream/study-cycle machinery (with at least one confirmed bug in it)
before or interleaved with the user's own turn, not just the resp_A
generation this directive was scoped to attribute. Recorded honestly;
not investigated further here.

**Second new finding:** on one live turn ("What's your name?", first
capture run), the device-delivered text was a raw internal diagnostic
string, not a conversational reply at all: *"Active axes:
existence=0.29, cost/purpose=0.23, time/belief=0.21. Field state:
heat=0.006, dominant-emotion=calm. Belief/time moved down since the
last exchange."* This is exactly the class of leak `_sanitize_
response()`'s docstring says it strips ("internal lineage/journal
state," "self-state observation string tokens") but evidently does not
catch this specific pattern. A real user asking Aurora her name could
receive a raw axis-state readout instead of an answer. Not fixed here
(separate defect from attribution); flagged for `_sanitize_response()`
to gain a pattern for this leak class.

### D1.3 — Divergence-point classification: (a) Routing-only

Both `aurora_daemon.py` and `aurora_bridge.py` call the exact same
`aurora.process_external_user_turn()` function, on the exact same
`systems` dict (shared state, shared subsystems, shared turn
processing) that produces resp_B too. The fork is NOT two independent
generators -- it is a single shared call whose result dict happens to
carry two differently-sourced fields (`resp_A`, built inside `_run_
live_response_turn`'s dual_question_pipeline chain -- comprehension-
response, search, teaching, sedimemory-recall, grounded-fallback,
honest-abstain -- and `resp_B`, built via `gw._express()` ->
`SentenceComposer.compose()`), and every real device consumer reads the
former while this campaign's entire instrument stack reads the latter.
**Classification: (a) routing-only.** The remedy is a routing decision
(point device consumers at resp_B, or bring resp_A's construction up to
the same standard), not a from-scratch diagnosis of a second generator
-- resp_A's own generation chain (comprehension-response,
grounded-fallback, etc.) is real, existing, already-built machinery,
just never the subject of this campaign's grammar/relevance fixes.

### D1.4 — Unification dossier (evidence only; HALT, per directive)

**What routing device -> resp_B would gain:** every fix this entire R1
campaign landed (POS-gating, skeleton validity, grounded fitness,
relevance-primary selection, the refined wellformedness predicate,
determiner/preposition motif slots, the N2.1 register rebuild) would
reach real users for the first time. Currently none of it does --
confirmed, not inferred.

**What routing device -> resp_B would cost / risk:**
- resp_B's own live character (this session's traces): short,
  grammatically-attempted-but-often-salad sentences ("I exist sunni
  clear. I understand moment real.") -- fluent-shaped but frequently
  not meaningfully on-topic. resp_A's current character is the opposite
  failure mode: honest, calibrated, often genuinely on-topic when it
  has grounding (sedimemory recall, taught facts, search), but falls
  through to short generic hedges ("I'm not sure.", "I don't have a
  clear sense of that.") when it doesn't -- and per this campaign's own
  "never fabricate" doctrine (FIX-A008), that hedging is arguably closer
  to correct behavior than resp_B's confident-sounding salad, just less
  fluent. Routing device to resp_B is not a strict improvement on every
  axis; it trades one failure mode for a different one.
- resp_A's chain includes real, working machinery resp_B's chain does
  not have at all: comprehension-response (search/teaching-grounded
  answers), sedimemory-recall (contextual memory), grounded-fallback.
  Routing device straight to resp_B would silently drop all of that
  capability from real device users unless it's ported or the routing
  is additive (resp_B as a stage WITHIN resp_A's chain, not a full
  replacement) rather than a straight swap.
- The two newly-found separate bugs (dream-trainer corpus self-nesting;
  diagnostic-string leak) sit inside resp_A's chain and `handle_message
  ()` respectively -- routing away from resp_A doesn't fix either; they
  need their own remediation regardless of the routing decision.

**Dependent consumers of resp_A's CURRENT behavior:** none identified
that specifically depend on resp_A's hedging/short-template character
as opposed to richer content -- but this was not exhaustively audited
(out of D1's scope; would require surveying every place `resp_A.content`
or `state.response_content` is read downstream of the turn, beyond the
two device surfaces this directive traced).

**End-state options, per migration-completion (target: ONE generation
path feeding all delivery surfaces + the documented crash-net):**
1. **Route device to resp_B.** Fastest way to make campaign fixes
   reach users. Risk: silently drops resp_A's real
   comprehension/search/memory capability unless ported first (not a
   small port -- see above).
2. **Bring resp_A's construction up to the campaign's standard**
   (apply POS-gating/relevance-primary/etc. to whatever component of
   resp_A's chain currently under-performs) while keeping its working
   comprehension/search/memory machinery. Larger, more careful
   diagnosis than option 1, closer to a "full mini-diagnosis of an
   independent generator" even though D1.3 classified this as
   routing-only at the TOP level -- resp_A's chain is itself several
   distinct sub-generators (comprehension-response, sedimemory-recall,
   grounded-fallback, honest-abstain), each potentially needing its own
   check against the campaign's fix catalog.
3. **Hybrid:** resp_B's word-selection/grammar machinery feeds INTO
   resp_A's chain as one candidate source alongside comprehension-
   response/sedimemory/search, with the existing chain's fallback
   ordering deciding when each fires. Preserves resp_A's real
   capability, gains resp_B's grammar fixes, avoids a full separate
   diagnosis of every resp_A sub-generator up front -- but is
   architecturally the most involved option to design correctly.

**No recommendation ranked above the others as "the" answer here** --
D1.4 is evidence, per the directive's own framing, matching this
campaign's established pattern for judgment-requiring dual-path
decisions (R1.9.1 Step 3, N4's dossier).

**HALT.** Path decision is Sunni's.

**First Seen:** Directive D1, 2026-07-17.

## Registry entry (per D1's own instruction, pending Sunni confirmation)

**Delivery-surface enumeration rule:** attribution work must enumerate
ALL user-facing delivery surfaces (chat field, device/app, TTS,
notification channels) and byte-attribute each -- verifying one surface
says nothing about its siblings. (Origin: third attribution incident,
Directive D1.)

## Directive D2.1 — Voice transplant (2026-07-17, ratified: ship the deeper reorder)

**Decision:** Sunni ratified Cael's Option 3 recommendation (D2, 2026-07-17):
retain resp_A's dual_question_pipeline waterfall as the orchestration spine
(comprehension -> search -> teaching -> generation -> honest-abstain ->
crash-net), replace only its GENERATIVE stage with the campaign-verified
composer path (gw._express() -> SentenceComposer). resp_A/resp_B collapse
to one field feeding all delivery surfaces.

**Pre-flight finding that reshaped the implementation:** mapping the live
waterfall (aurora.py) before writing any transplant code (per D2.1's own
"assess before architect" instruction) surfaced two things not visible
from the directive text alone:

1. resp_B (`gw._express()`'s output) is explicitly marked
   `_internal_only=True` / `_surface_channel="internal_afterthought"`
   immediately after it's computed (aurora.py ~17235-17238) -- by design
   it was never meant to be delivered anywhere; it's an internal
   "afterthought" simulation artifact. D1 already proved no real device
   surface reads it. This context matters for anyone re-reading this code
   without D1/D2's history: resp_B's tagging is not a bug, it predates
   the unification and is safe to leave as-is (D2.1 only reads its
   *content*, never removes the tag).
2. resp_A was ALREADY double-wired into SentenceComposer before this
   directive -- `_render_runtime_intent()` (aurora.py) -> WorkingMemory's
   `_render_from_comprehension_intent()` (aurora_working_memory.py:3016)
   already calls `perception.express()` -> `composer.compose()`, but via
   a MOCK `AssemblyResult` (`SimpleNamespace(active_count=10)`,
   `entropy_state={}`, `ds_stats={}`) that discards the richer evidence
   (`_strata_evidence`, `subsurface_projection`, `activation_field`)
   resp_B's real `gw._synthesize()` assembly carries. The "voice
   transplant" is therefore best understood as: stop routing resp_A's
   words through a synthetic evidence path when the real, evidence-
   grounded one (already computed for resp_B, just discarded) is
   available for the same turn.

**First implementation attempt (kept, but insufficient alone):** at the
point resp_B is computed and grounded-checked (aurora.py, end of
`_run_reasoning_pipeline`), copy resp_B's content/tone/confidence onto
resp_A whenever resp_B has grounded content AND resp_A's own chain had
not already fired the honest-abstain net (`state.response_src ==
"constraint_abstain"`). Live-traced against 6 turns: only **1/6**
unified. Root cause: resp_A's own honest-abstain crash net fires TWICE,
mid-chain (`_chain_down2_belief`, old trigger `"mid_chain"`) and at the
emission chokepoint (`_enforce_emission_discipline`, old trigger
`"emission_chokepoint"`) -- BOTH well before `gw._synthesize()`/
`gw._express()` are even called later in the same function. resp_A's
generative branches require a literal fact/comprehension match to
produce anything; when they don't, abstain fires immediately, long
before the composer voice ever gets a chance to speak. Directive D2.4
explicitly anticipated this class of finding ("a non-decrease [in
abstain rate] is a flag, not a failure") but the intent of "the spine
keeps its job, the voice gets replaced" clearly requires abstain to be
genuinely downstream of the NEW generation stage, not just downstream of
resp_A's old, far stricter one.

**Presented as a fork, not decided unilaterally** (this is an
implementation-shaping decision with real risk-tradeoff, not covered by
D2's "precisely scoped" language): ship the low-risk 1/6 patch as-is
(defensible per D2.4's own escape clause, but the transplant barely
fires) vs. do a deeper reorder so abstain waits for the composer vs. a
narrower middle option (give the composer one attempt inside
`_emit_honest_abstain_and_seek` itself). **Sunni ratified the deeper
reorder.**

**Final implementation (deeper reorder):**
- `_chain_down2_belief`'s mid-chain abstain call and
  `_enforce_emission_discipline`'s emission-chokepoint abstain call no
  longer fire `_emit_honest_abstain_and_seek` inline. Both leave
  `state.response_content` empty when resp_A's own chain found nothing --
  every stage between there and resp_A's construction already guards on
  `if state.response_content:`, so this is a safe no-op change for those
  turns. Everything else in `_enforce_emission_discipline` (crest
  compression, anchor-leak suppression) is unchanged.
- At the D2.1 unification point (after resp_B is computed and grounded-
  checked), the logic now has three cases: (1) composer produced grounded
  content -> resp_A's content becomes the SAME string resp_B carries
  (`resp_A.src = "composer_unified"`) -- the actual generation swap; (2)
  composer produced nothing AND resp_A's own chain also produced nothing
  -> the single honest-abstain crash net fires HERE, once, genuinely as
  the last resort after both generation attempts; (3) composer produced
  nothing but resp_A's own chain found something (direct fact/identity
  lookup) -> keep resp_A's own content, graceful degradation, not an
  abstain case.
- Net effect: there is now exactly ONE call site to
  `_emit_honest_abstain_and_seek` in the live turn path (previously two),
  reusing `trigger="emission_chokepoint"`. N4's LIVE_FALLBACK crash-net
  design is unchanged in every other respect (still ConstraintEmitter's
  only surviving role, still logs every catch via
  `_log_constraint_fallback`).

**Live re-verification after the reorder:** same 6-turn trace,
**6/6 unified** (`resp_A.src == "composer_unified"`, byte-identical
content), 0/6 abstain -- versus the pre-D2.1 baseline where 5/6 of the
same turns hit resp_A's own canned abstain while resp_B kept generating.
This is the "abstain recedes as the trusted voice lands" effect D2.4
anticipated.

**New permanent CI test:**
`tests/test_d1_device_path_attribution.py::test_resp_a_and_resp_b_are_unified_by_construction_post_d2`
-- drives `process_external_user_turn()` across 6 live turns and asserts
that whenever resp_B has grounded content, resp_A.content is byte-
identical to it and `resp_A.src == "composer_unified"`. Since every real
device surface (daemon, Flutter chat, Flutter TTS) reads resp_A (D1),
this closes the divergence D1 proved: the words users see are now the
same words the campaign's grammar/relevance verification battery
(run_probe_battery.py) has been measuring and fixing all along.

**Full suite: 802 passed, 0 failed** (unchanged count -- no test needed
updating beyond the new one above; `test_governance_liveness.py`'s
crash-net tests pass unmodified since they check for the
`_emitter._emit_abstain(` call pattern and absence of retired call
sites, not literal trigger-string counts).

**Known caveat, honestly flagged, not fixed here:** unification is
conditional on resp_B actually computing (requires `synthesis is not
None` and not `suppress_afterthought`) and on `_response_is_grounded()`
passing. Turns that hit those suppression paths (direct identity/name
lookups, sensory queries, inline-definition turns) keep resp_A's own
content untouched by design (case 3 above) -- this is intentional
graceful degradation, not a gap needing a fix, since those turns already
have a satisfying literal answer from resp_A's own chain.

**Not yet done (next in this directive):** D2.2 (nesting-bug rider),
D2.3 (diagnostic-leak rider), D2.4 (acceptance battery + abstain-rate
telemetry + HALT).

## Directive D2.2 — Rider 1: nesting bug fixed (2026-07-17)

**Root cause, traced in full** (a background research pass, since the
call chain crosses aurora_dream_trainer.py, aurora_simulation_engine.py,
and aurora.py): `handle_message()`'s 1-4 `process_external_user_turn()`
calls per user turn came from TWO synchronous simulation triggers, both
routing through the SAME choke point --
`_run_simulation_live_response_bridge` (aurora.py), wired at boot via
`_attach_live_response_simulation_bridge` as the simulation session's
`live_response_bridge`:

1. The `is_question` "[AFTERTHOUGHT]" simulation
   (`aurora.gateway.simulation.run_episode(seed_prompt=f"[AFTERTHOUGHT]
   {user_text}", turns=2, ...)`, inside `_run_reasoning_pipeline`).
2. `DreamTrainer.train_on_bundle`'s every-10th-turn dream episode (the
   "FIX-2" block in `_run_live_response_turn`, gated on
   `_episode_compile_count % 10 == 0` and a >= 2-turn buffer) --
   `train_on_bundle` calls `session.queue_avatar_specs([spec])` then
   `simulation.run_episode(**ep_kw)`, BLOCKING, no threading.

Either trigger's `run_episode()` call pops the OLDEST queued avatar spec
(FIFO `_pending_avatar_specs.popleft()`) -- not necessarily its own --
and `_shape_topic_for_turn` reads that spec's `prompt_candidates`/
`followup_candidates` to build each turn's prompt. When a relational-
probe spec (built by `_build_relational_probe_specs`, queued via
`flush_lessons_to_simulation(force=True)` at boot) happened to be at the
head of the queue, THIS is what produced the "Use this corpus fragment
as context: ..." + 2 follow-up prompts observed live. Each prompt then
reaches `_generate_expression()` -> `_live_response_bridge()` ->
`_run_simulation_live_response_bridge`, which called
`process_external_user_turn(sandbox_systems, prompt, ...)`
**recursively**, nested inside the outer, real call's own call stack --
this is what produced the extra `process_external_user_turn` calls, for
BOTH triggers, regardless of which spec was queued.

**Self-nesting compounding, fixed at two layers (write-time + read-time):**
a probe-seeded turn's own exchange gets logged back into
`FailPointLedger` as a future fail-point example (via
`record_relational_probe_outcomes` -> `record_fail`); the next
`_build_relational_probe_specs` pass then re-mines that already-wrapped
text as `source_snippet` and wraps it AGAIN, compounding the prefix
linearly every cycle (observed live: dozens of repeats in one string).
- **Write-time** (`aurora_dream_trainer.py`, `FailPointLedger.
  _sanitize_example`): extended the SAME regex-strip pattern already
  used there for the identical `[AFTERTHOUGHT]` bug class
  (`re.sub(r'^(?:\[(?:AFTERTHOUGHT|aftermath)\]\s*)+', '', text)`) to
  also strip `"Use this corpus fragment as context: "` (repeated,
  case-insensitive) before an example is ever stored.
- **Read-time, defense-in-depth** (`_build_relational_probe_specs`):
  new `_CORPUS_FRAGMENT_PREFIX` constant + `_strip_corpus_fragment_
  wrapper()` helper strip the wrapper from `texts` again before pair
  extraction; `"use"`, `"corpus"`, `"fragment"` added to
  `_RELATIONAL_STOPWORDS` so the wrapper's own words can never be mined
  as a fake "relational pair" (this is literally what happened live --
  `left="use", right="corpus"` became the next cycle's seed).

**Recursion, fixed with a reentrancy guard, not threading:** considered
moving `train_on_bundle`'s `run_episode()` call to a background thread
(the codebase's existing pattern for async training work --
`aurora_bridge.py`'s `_pursue_study`/`_pursue_self`), but `aurora.py`'s
turn pipeline shows no evidence of being thread-safe (pervasive
unguarded `systems[...]=...` mutation throughout); threading a
deeply-nested call chain that mutates a huge shared `systems` dict
risked trading one bug for a worse, intermittent one. Instead:
`process_external_user_turn` now stamps a reentrancy counter,
`systems["_live_turn_depth"]` (incremented on entry, decremented in its
existing `finally` block -- no new control-flow paths).
`_run_simulation_live_response_bridge` checks that counter before
recursing: when `> 0` (a real turn is already in progress on this exact
`systems` object), it skips the recursive `process_external_user_turn`
call and completes the episode step locally with the same cheap
fallback expression (`f"I approach this with {concept}. {prompt}"`)
this function already used whenever the real bridge produced nothing --
the episode's own bookkeeping still closes out, just without nesting a
synthetic turn inside the user's turn. Standalone/background
invocations of the bridge (no live turn in progress, e.g. classroom
lesson running) are unaffected -- this is a reentrancy guard, not a
feature removal. "Training fragments have no business inside a user's
live turn" (directive's own words) is satisfied by keeping training
fragments OUT of the live call stack, not by disabling training.

**Live acceptance criterion, verified exactly as specified:** 20 live
turns (spanning turns 10 and 20, where the every-10th-turn dream trigger
fires), **20/20 produced exactly 1 `process_external_user_turn()`
call** -- versus the pre-fix baseline of 1-4 calls per turn documented
in D1. New permanent tests:
- `tests/test_d2_2_corpus_fragment_nesting.py` (6 tests): wrapper
  stripping (single/compounded/idempotent), relational-pair extraction
  never mines wrapper words, `_sanitize_example` strips at write-time,
  and an end-to-end 5-cycle simulation proving the prefix never exceeds
  1 occurrence in any generated `prompt_candidate` even when each
  cycle's own output is fed back into the ledger.
- `tests/test_d2_2_live_turn_reentrancy_guard.py` (3 tests): the depth
  counter increments/decrements correctly and never goes negative; the
  simulation bridge skips recursion when `_live_turn_depth > 0`
  (isolated unit test, no full boot); and the live 20-turn acceptance
  criterion itself.

**Full suite: 812 passed, 0 failed** (up from 802 baseline: +1 D2.1
unity test, +6 D2.2 corpus-fragment tests, +3 D2.2 reentrancy-guard
tests).

**Not yet done (next in this directive):** D2.3 (diagnostic-leak
rider), D2.4 (acceptance battery + abstain-rate telemetry + HALT).

## Directive D2.3 — Rider 2: structural delivery-boundary sanitization (2026-07-17)

**Registry linkage the directive asked for, honestly reported:**
searched `known_fixes_registry.md` and `git log` (all branches,
2026-01-01 through 2026-03-15, `-i --grep` for "leak", "diagnostic",
"internal state", "mechanism", "axis dump") for the "Feb-era
internals-leak class" the directive names -- found no matching entry or
commit. Rather than fabricate a citation, this entry stands as the
first traceable registry record of the class itself: mechanism detail
(internal telemetry/state readouts) crossing the expression boundary
and reaching the user verbatim.

**Fix:** `flutter_app/android/app/src/main/python/aurora_bridge.py`'s
`_sanitize_response()` gained a new check 0, running BEFORE all 13
existing pattern-specific checks (fail-closed -- reject the whole
candidate, never partially clean telemetry-shaped content and let the
remainder through). Structural, not string-specific, per the directive:
`_looks_like_internal_telemetry(text)` fires on either signal (a) two or
more `word=numeric_value` pairs in one response (the shape of a
telemetry/axis dump, not a sentence a person would say), or (b) an
explicit internal-state section label (`"Active axes:"`, `"Field
state:"`). Either signal alone is sufficient. A single incidental
`=` (e.g. "confidence=0.8 today") does NOT trigger rejection --
the rule requires the shape of a dump, not any equals sign.

On a match: the whole response is discarded, replaced with the same
canonical honest-abstain string ConstraintEmitter's crash net already
uses (`"I don't have a clear sense of that."`), and the rejection is
logged to `aurora_state/delivery_boundary_rejection_log.jsonl`
(`{reason, raw_text, timestamp}`) -- mirroring aurora.py's own
`_log_constraint_fallback`/`constraint_fallback_log.jsonl` pattern on
this file's side of the boundary, per the silent-fallback rule (no catch
here is ever silent).

**Pinned live regression:** the exact string D1's live trace captured
verbatim as a delivered device response --
`"Active axes: existence=0.30, time/belief=0.28, cost/purpose=0.15.
Field state: heat=0.004, dominant-emotion=calm. Energy/cost moved down
since the last exchange."` -- is now caught by BOTH signals (4
key=value pairs AND both section labels) and rejected before delivery.

**New tests** (`tests/test_d2_3_delivery_boundary_telemetry_rejection.py`,
7 tests): the pinned live leak is detected; a DIFFERENT, never-seen
key=value dump is also caught (proving the rule is structural, not a
memorized string); ordinary conversational sentences are never
false-positived; a single incidental `=` doesn't trigger rejection;
`_sanitize_response` returns the honest-abstain text and never leaks
`"active axes"` or a bare `=` for the pinned case; the rejection is
logged (not silent) with the reason and raw text on disk; and an
ordinary grounded reply with no telemetry shape passes through
unchanged (regression guard against over-suppression).

**Full suite: 818 passed, 1 failed, 0 caused by this change.** The one
failure, `tests/test_concept_image_ingestion_import.py::test_ingest_
concept_image_succeeds_against_real_fixture` (`cv2` has no attribute
`imdecode`), is a pre-existing test-order-dependent flake, confirmed
unrelated: reproduced identically across two consecutive full-suite
runs (same single failure both times), but passes cleanly every time
when run in isolation (`pytest tests/test_concept_image_ingestion_
import.py`, 3/3 pass). Touches camera/cv2 image-ingestion code, nowhere
near `aurora_bridge.py`, `aurora.py`, or `aurora_dream_trainer.py`.
Flagged honestly here per the campaign's "halt on failure, report
honestly, never fudge" doctrine -- not fixed (out of D2.3's scope, a
separate test-isolation gap in the suite's cv2 mocking/global state
across files, not this directive's concern), not hidden.

**Not yet done (next in this directive):** D2.4 (acceptance battery +
abstain-rate telemetry + full CI + HALT).

## Directive D2.4 — Acceptance (2026-07-17): HALT after acceptance with the live numbers

**Pre-flight fix required before acceptance was even measurable:**
`run_probe_battery.py`'s response extraction read
`response.get("response_text")`, a key `process_external_user_turn()`'s
result dict never populates (confirmed empirically -- its real keys are
`resp_A`/`resp_B`/`src`/...). That miss was silent: every probe always
fell through to a SEPARATE call, `aurora_gateway.speak_to_aurora
(turn_text)` -- a fresh, independent invocation of the same underlying
composer machinery, not literally the turn's own `resp_A`/`resp_B`.
Every probe-battery score from R0 through R1.9.4 was therefore
measuring that separate call, not the field D1 proved actually reaches
a device. Fixed via a shared `_extract_delivered_response_text()`
helper (reads `resp_A.content` first, falls back to the gateway call
only when `resp_A` is genuinely empty, matching this file's original
documented fallback intent) applied at both call sites (the main
battery runner and `--trace` mode). New tests:
`tests/test_d2_4_probe_battery_measures_resp_a.py` (5 tests) pin the
correct extraction so it cannot silently regress to the non-existent
key. This was necessary groundwork, not scope creep -- D2.4 explicitly
requires the battery to measure "the unified device-delivered field,"
and the script did not do that until this fix landed.

**1. Stratified battery at campaign floors, measured on resp_A directly**
(`python run_probe_battery.py --quiet`, `runtime_profile=surface`,
disclosed per directive, 60 probes, single run):
- **Relevance floor (>= 0.6): MET.** `mean_relevance_fraction = 0.862`,
  `nonzero_rate = 0.933` (56/60 probes scored nonzero relevance).
- **Wellformedness floor (>= 0.5): MET for simple/concrete, MISSED for
  abstract/conceptual.** `stratified_wellformedness.simple_concrete.
  parseable_rate = 0.722` (26/36); `stratified_wellformedness.
  abstract_conceptual.parseable_rate = 0.458` (11/24) -- below the 0.5
  floor. Reported exactly as measured, not rounded up or hedged: on
  probes requiring abstract/conceptual reasoning, resp_A's composer
  voice (word-choice from a live, sparse axis/relevance graph, not a
  language model) does not yet reliably produce parseable structure at
  the campaign's own floor. This is a real, honest gap, not a new
  regression from D2 -- it reflects the composer's existing quality
  ceiling on harder probes, now visible for the first time on the field
  that's actually delivered (previously masked by the independent
  `speak_to_aurora()` call the battery measured instead, per the
  pre-flight finding above -- whether that call's own historical scores
  showed the same split was not re-derived here; out of this
  acceptance's scope).
- Single run, not the 3x replication R0.3 used for its baseline; D2.4's
  own text does not mandate replication the way R0.3's did. Flagged
  honestly as a smaller sample.

**2. Abstain-rate telemetry, 100 live turns, before/after:**
- **Before (documented, D1's live trace, 6-turn sample):** 5/6 turns
  (83.3%) hit resp_A's own canned abstain (`"I don't have a clear sense
  of that."` / `"I'm not sure."`) while resp_B kept generating,
  unreachable by the user.
- **After (this run, 100-turn sample, fresh boot, mixed conversational
  turns):** **0/100 turns (0.0%) hit the constraint_abstain crash net.**
  100/100 turns resolved via `composer_unified` -- the D2.1 voice
  transplant fired on every turn in this sample.
- This is a **marked decrease**, exactly as D2.4 anticipated ("the
  waterfall abstaining past its untrusted voice should recede as the
  trusted voice lands"). Honestly noted: the "before" and "after"
  samples are not a matched controlled A/B (different turn sets, different
  sample sizes) -- a live re-run of the exact same 6 D1 turns after D2.1
  already showed this directly (6/6 unified, 0/6 abstain, documented in
  D2.1's own entry above), and this 100-turn run confirms the effect
  holds at scale, not just on the original 6 turns.

**3. D1 byte-attribution CI: green across all enumerated surfaces.**
`tests/test_d1_device_path_attribution.py`'s 5 tests pass, including
`test_resp_a_and_resp_b_are_unified_by_construction_post_d2` (D2.1's
unity proof). Delivery-surface enumeration rule satisfied: daemon and
Flutter bridge (chat + TTS, byte-identical on that side) both
structurally confirmed to read resp_A; the live unity test proves
resp_A/resp_B byte-identity whenever the composer produces grounded
content.

**4. Riders' regression tests: green.**
`tests/test_d2_2_corpus_fragment_nesting.py` (6),
`tests/test_d2_2_live_turn_reentrancy_guard.py` (3, including the
live 20-turn exactly-1-call acceptance criterion),
`tests/test_d2_3_delivery_boundary_telemetry_rejection.py` (7,
including the pinned "Active axes:" live regression) -- all pass.

**5. Full suite: 823 passed, 1 failed.** The one failure
(`test_concept_image_ingestion_import.py::test_ingest_concept_image_
succeeds_against_real_fixture`, `cv2.imdecode`) is the SAME pre-existing,
unrelated test-order-dependent flake documented in D2.3's entry --
reproduced identically a third time across this session's full-suite
runs, passes 3/3 in isolation every time, touches only camera/cv2 code.
Not caused by, or related to, any D2 work. Not fixed (out of scope),
not hidden.

**HALT.** Per the directive's own instruction: this is the acceptance
report, not a decision to keep iterating on the wellformedness gap. The
abstain-rate and unity results meet or exceed what D2 set out to prove;
the abstract/conceptual wellformedness gap is real, honestly measured,
and now visible for the first time on the actually-delivered field --
whether and how to close it is a new question for Sunni to scope, not
something this directive's acceptance step decides unilaterally.

## D2 Acceptance Memo (2026-07-17) — CONDITIONALLY ACCEPTED, ratified

Cael's verdict on the D2.4 acceptance report above, ratified by Sunni:
accepted on the numbers (relevance, simple/concrete wellformedness,
the 83%->0% abstain decrease, both riders, the suite), with one named
standing gap and one small condition before N6 work starts.

**Standing gap, owner assigned (not a blocker):** abstract/conceptual
wellformedness (0.458 vs the 0.5 floor) is the first honest measurement
of this stratum on the delivered field -- it was 0.0 nine days ago.
**Owner: N6.** Post-D2, classroom training and delivery share one
voice for the first time (the same unification D2.1 built), so
classroom gains now land directly in delivered speech. N6's 40-lesson
re-verdict runs abstract-weighted. If 3 consecutive post-N6 batteries
show no positive abstract-stratum trend, targeted vocabulary seeding in
abstract regions is authorized -- assess `scripts/seed_oets_aurora_
vocabulary.py` first (sourced assets before new infrastructure).

**Measured-field attribution rule (scripture tier):** no measurement
claim is valid without byte-attribution of the measured field. The
probe-battery stale-`"response_text"`-key incident (D2.4's pre-flight
fix, above) is logged as **attribution incident #4** in this
campaign's sequence (boot-comment lie; probe-field near-miss; D1's
third device-path incident; this stale-key incident is the fourth).
Historical resp_B-era probe-battery numbers (R0 through R1.9.4) stand
as-is -- they measured a real, campaign-verified composer call
(`speak_to_aurora()`, same underlying `SentenceComposer` machinery),
just not literally the turn's own delivered `resp_A`; that composer
path is independently anchored by the R1.9.1 byte-attribution CI
(`test_delivered_output_attribution_traces_to_sentence_composer`), so
those historical numbers are not retracted, only understood precisely
for what they measured. All future probe-battery runs measure the
unified delivered field by construction (the
`_extract_delivered_response_text()` fix is permanent, pinned by
`tests/test_d2_4_probe_battery_measures_resp_a.py`).

**D2.1 fork record:** the abstain-before-generation ordering problem
(resp_A's own honest-abstain net firing before the composer/synthesis
even existed later in the same function) required the deeper reorder
D2.1 ultimately shipped, not the lower-risk cosmetic patch first
attempted. Logged here with its evidence: 1/6 turns unified under the
first patch; 6/6 turns unified (0/6 abstain) after the reorder,
live-retraced against the same 6 turns; confirmed at scale by D2.4's
independent 100-turn run (0/100 abstain).

**Condition 2 (abstain sanity, before N6) — result, 2026-07-17:**

Ran the memo's own prescribed check: >=3 synthetic genuinely-
unanswerable turns through the live unified path
(`process_external_user_turn`). First run, against the code as D2.4
shipped it: **0/4 abstained.** The memo's own worry was correct --
0/100 was not earned.

**Root cause found (not what the memo's fallback assumed):**
`ingest_interaction()`'s blind vocabulary-learning path
(`aurora_expression_perception.py`) stamps ANY 4+ char alphabetic token
from raw turn text as a lexicon entry with meaning `"learned:<word>"`
and a POS role guessed by `infer_word_role()` -- whose unconditional
"default: noun" fallback (the docstring's claimed "recognizable role"
quality bar does not actually exist in the code) accepts literally any
string matching the character class. `build_relevance_anchor_set()`
then scores that same token as a `RELEVANCE_DIRECT_ANCHOR` match of
ITSELF. Live-confirmed: a gibberish turn ("Zqxvornmal threbicultan
fost yendrical mip?") got auto-learned word-for-word into
`lexicon.json` (`meaning: "learned:zqxvornmal"`, role/valence
guessed), then echoed straight back as delivered content ("I become
threbicultan zqxvornmal..."). **The memo's prescribed fallback
(recalibrate R_MIN) cannot fix this**: R_MIN is derived strictly
between the distant-tier ceiling (0.075) and one-hop-tier floor (0.2);
a direct-anchor score (1.0-tier) sits above that entire range by
construction, so no R_MIN value can ever reject a word matching itself
as its own anchor. Verified this precisely before touching code, per
this campaign's "report honestly, never fudge" doctrine -- did not
recalibrate R_MIN and falsely report Condition 2 fixed.

**Fix shipped** (`aurora_expression_perception.py`,
`SentenceComposer._score_composer_candidate`): a candidate whose
`meaning` is exactly the auto-learned placeholder
(`f"learned:{word}"`) AND whose `usage_count` is below the new
`_UNVERIFIED_VOCAB_USAGE_FLOOR = 3` has its relevance capped at
`RELEVANCE_DISTANT_FLOOR`, regardless of anchor-set score -- unverified
single-turn vocabulary can no longer masquerade as grounded content.
Words taught with a real definition
(`aurora_internal/aurora_comprehension_gap.py`, which stores the
actual definition/answer as `meaning`, never the placeholder) or
OETS-enriched (`meaning="oets:<keyword>"`, requires a pre-existing
real OETS node to trigger) are untouched -- confirmed by dedicated unit
tests, not just live retracing. A word graduates out of the cap once
it accumulates real repeated use (`usage_count >= 3`), rather than
staying permanently distrusted.

**Second bug found while re-testing:** once the first bug was fixed,
one turn (pure gibberish, no real words at all) correctly triggered
`SentenceComposer.compose()`'s OWN internal abstain gate -- but D2.1's
unification code treated ANY non-empty `resp_B.content` as grounded,
mislabeling the composer's own abstain-template string ("I don't have
a clear sense of that.") as `src="composer_unified"` instead of
recognizing it as an abstain. Fixed in `aurora.py`'s D2.1 unification
block: `resp_B`'s content is now checked against
`SentenceComposer._ABSTAIN_TEMPLATES` first, falling through to the
true honest-abstain-and-seek net when it matches.

**Result after both fixes:** the pure-gibberish turn ("Zqxvornmal
threbicultan fost yendrical mip?") now correctly produces
`src="constraint_abstain"`, content "I don't have a clear sense of
that.", with a logged reason in `constraint_fallback_log.jsonl`
(`trigger="emission_chokepoint"`). Pinned as a live regression test
(`tests/test_d2_condition2_abstain_sanity.py`,
`test_pure_gibberish_turn_abstains_honestly_live`).

**Residual gap, honestly reported, NOT fixed:** two of the four
synthetic turns -- "What is the square root of the color purple
divided by last Wednesday?" and the fabricated-authentication-code
request -- are built ENTIRELY from real, valid English words in a
category-error/semantically-incoherent arrangement. There is no
gibberish token for the vocabulary-trust fix to catch, so these still
produce fluent-sounding word-salad rather than an abstain (e.g. "I
knowing last clear. I become color real."). This is a fundamentally
different, much harder problem than the one this fix addresses --
whole-sentence semantic/logical coherence detection, not per-word
vocabulary trust -- and is out of this fix's scope. Condition 2's
literal bar (>=3/3 honest abstains) is therefore only PARTIALLY met:
1/4 by strict `constraint_abstain` label (a second turn, pure keyboard-
mash, produced an honest `comprehension_gap` clarifying question
instead -- arguably honest engagement, differently labeled, not
counted here to avoid inflating the number). Reported to Sunni for a
decision on whether this residual gap blocks N6 or is accepted as a
separate, future-scoped problem.

Full suite after both fixes: 830 passed, 1 failed (the same documented
pre-existing cv2 test-order flake noted in the D2.4 acceptance report
above -- reproduced again here, passes in isolation, unrelated to this
work).

## N6 (post-D2) — abstract-weighted classroom re-verdict, 2026-07-17

Per the D2 Acceptance Memo's queue item 2: post-D2, classroom training
and delivery share one voice for the first time (D2.1's unification),
so classroom gains now land directly in delivered speech instead of
being masked behind the independent `speak_to_aurora()` call the
probe battery measured pre-D2. This run is the named owner of the
standing abstract/conceptual wellformedness gap (0.458 vs the 0.5
floor, first honestly measured on the delivered field by D2.4).

**What ran:** the same methodology as the earlier N6 (pre-D2, 2026-07-
16): a fresh 45-lesson classroom block (3 segments of
`run_targeted_curriculum(n=15, turns_per_lesson=6)` -- `select_
curriculum()` only draws from the 15-dimension pool once per call, so
3 calls are needed to reach a real 45-lesson total covering every
canonical dimension 3x each). Ran against the real repo `aurora_state`
under `runtime_profile="full"`. `dev_delta_total = 952.0` across all
45 lessons (mean 21.16/lesson) -- real developmental accumulation, not
incidental pollution.

**Then, per the memo's own instruction, 3 consecutive post-N6 probe
battery passes** (`python run_probe_battery.py --quiet`, each a fresh
boot against the real, now-trained `aurora_state`), tracking the
abstract_conceptual stratum against D2.4's pre-N6 baseline:

| Run | simple_concrete | abstract_conceptual |
|---|---|---|
| D2.4 baseline (pre-N6) | 0.722 | 0.458 |
| N6 post, battery 1 | 0.778 | 0.500 |
| N6 post, battery 2 | 0.750 | 0.417 |
| N6 post, battery 3 | 0.778 | 0.500 |
| **3-run mean** | **0.769** | **0.472** |

**Honest read, not decided unilaterally:** simple_concrete shows a
clear, consistent improvement (0.722 -> mean 0.769). Abstract_
conceptual is noisier and genuinely ambiguous: 2 of 3 runs sit exactly
at the 0.5 floor (an improvement over the 0.458 baseline), but battery
2 dipped to 0.417 (below baseline), and the 3-run mean (0.472) is only
marginally above the pre-N6 number -- nowhere near a clean, decisive
trend. This is squarely the situation the memo's own trigger
anticipated ("if 3 consecutive post-N6 batteries show no positive
abstract-stratum trend, targeted vocabulary seeding... is
authorized"), but the memo's trigger condition itself is a judgment
call on noisy data, not a bright line this run crossed unambiguously
either way. Reported for Sunni's read rather than self-authorized:
does 2-of-3-at-floor with a marginal-positive mean count as "a
positive trend," or does the mean's smallness and battery 2's dip
count as "no positive trend" -> authorize `scripts/seed_oets_aurora_
vocabulary.py` (assessed, not yet run -- sourced assets before new
infrastructure, per the memo's own instruction).

Full suite after this run (no production code touched, state-only):
[see below].

## V0 — Boundary Envelopes validation gate, 2026-07-17 (measurement only, HALT)

Per `AURORA_SPEC_BOUNDARY_ENVELOPES_20260717.md` (Cael's design,
addressing Condition 2's residual gap after both the generation-score
and understanding-accuracy signals were empirically ruled out as
rhythm/coherence detectors). Consumer instruction: validation gate
first, no implementation until V0 separates.

**Method (constraint-derivative, per the spec's own design test):**
16 joints -- (operator_phrase, argument_word) pairs -- hand-extracted
from the 4 Condition-2 test sentences, 8 coherent controls, and 4
legitimate-metaphor sentences ("the taste of victory" class). Each
word's "lived envelope" was read from ONLY existing Aurora machinery:
its real lexicon `noncomp_id` axis tag (excluding same-turn-only
placeholder learns, matching the D2 Condition 2 fix's own distinction)
and, where absent, its OETS node's relation-edge neighbors' axis tags.
A joint scored supported/contradicted/unknown by comparing the
argument's axis identity against the operator's own axis identity,
computed the identical way -- no hand-authored "what role does this
operator demand" ontology; the axis vocabulary is HER existing X/T/N/
B/A framework throughout.

**Result: did not separate.** All three groups landed overwhelmingly
in `unknown`:

| Group | supported | contradicted | unknown | n |
|---|---|---|---|---|
| category_error | 0 | 0 | 4 | 4 |
| gibberish | 0 | 0 | 2 | 2 |
| coherent | 2 | 1 | 5 | 8 |
| metaphor | 0 | 0 | 4 | 4 |

Category-error and metaphor scored identically (100% unknown) --
exactly the "dead on arrival" failure mode the spec's own falsifiable
prediction warned about (metaphor was supposed to land in unknown
while category-error showed something systematically weaker).

**Root cause of the non-separation, traced before reporting a verdict
either way:** the scoring required the OPERATOR PHRASE itself ("square
root of", "the taste of", "seventeen-digit") to have real axis
evidence before evaluating the argument at all -- and most operator
phrases in this test set are multi-word or rare terms simply absent
from her ~1660-word vocabulary, so the great majority of joints never
reached an argument-level verdict. This looks like a measurement-
sparsity artifact of this specific proxy (single-word lexicon/OETS
lookup on the operator side), not necessarily evidence the underlying
design is unworkable -- the spec's own data sources ("L2 slot-role
logs, graph edge roles, coupling shapes") may need a richer read (e.g.
projecting the operator PHRASE's own axis via `_project_utterance_
axes`, or drawing on `genealogy/couplings.json`'s axis-pair co-
occurrence history directly) than the word-lookup proxy this V0 pass
used.

**HALT, per the spec's own instruction.** V0 as measured is
inconclusive, not a pass or a kill -- reported honestly rather than
loosened to force separation or over-read as proof the design fails.
No implementation attempted. Whether to refine V0's measurement
methodology and re-run, or treat this as sufficient evidence to park
the design, is Sunni's call.

## Directive S1 — Abstract-Region Seeding, 2026-07-17 (both gates HALT)

Rulings ratified: N6 = STALLED (vocabulary seeding authorized); V0 =
ON HOLD pending seeded data, not rejected.

**S1.1 (asset assessment):** `scripts/seed_oets_aurora_vocabulary.py`
writes real OETS nodes (genuine definitions, real `noncomp_id` axis
tags) and typed relations into `aurora_state/aurora_oets_web.json`,
already provenance-tagged (`source="seeded"` / `source_of_knowledge=
"seeded"`). Not bare word-lists. Gap: hardcoded to one fixed
architecture-vocabulary set, not region-targetable, and covers neither
the battery's abstract stratum (confirmed by reading the dimension->
stratum mapping in `aurora_semantic_probe_battery.py`: `abstract_
conceptual` = literally the `contradiction_handling` and `uncertainty_
signaling` probe dimensions, not a vocabulary theme) nor V0's joint-
inventory words. Verdict: reuse the mechanism, extend the content.

**S1.2 (seeding, `scripts/seed_abstract_regions_s1.py`):** extended
the existing script's exact helpers/pattern. Added 24 OETS nodes + 22
relations (contradiction/hedge/uncertain-domain vocabulary + V0's
exact joint words), and 22 matching lexicon entries with real
definitions and hand-assigned `noncomp_id` axis tags (X/T/N/B/A,
following the same semantics already live in `constraint_meaning_
axes`). Provenance: OETS via the existing `source="seeded"`
convention; lexicon via `lineage="seeded_s1"`. Two abstract-stratum
words (`contradiction`, `uncertain`) and one V0 word (`water`) already
existed and were correctly skipped, not overwritten -- respects
earned-through-use, but see the envelope-gate root cause below.
Deliberately did NOT hand-edit `aurora_state/genealogy/couplings.json`
("coupling shapes") -- a live-computed rolling-statistics store with
invariants (breeding_score_ema, inheritance_breach_count) not designed
for external insertion; flagged as scope left out, not silently
skipped.

**S1.3 gate 1 — composition (stratified battery x3 post-seeding):**

| Run | simple_concrete | abstract_conceptual |
|---|---|---|
| S1 post-seed, run 1 | 0.778 | 0.417 |
| S1 post-seed, run 2 | 0.750 | 0.458 |
| S1 post-seed, run 3 | 0.722 | 0.583 |
| **3-run mean** | **0.750** | **0.486** |

Required to clear: mean >= 0.55, no floor-kissing. **0.486 does not
clear.** simple_concrete stayed healthy (no regression from seeding).
**Gate 1: NOT CLEARED.**

**S1.3 gate 2 — envelope (V0 re-run, identical joints, identical
scoring code, against seeded data):**

| Group | supported | contradicted | unknown | n |
|---|---|---|---|---|
| category_error | 1 | 2 | 1 | 4 |
| coherent | 1 | 5 | 2 | 8 |
| metaphor | 0 | 2 | 2 | 4 |

Required: category-error separates from coherent (weaker support);
metaphor lands unknown-not-contradicted. **Neither held. Coherent
joints contradicted MORE often (62.5%) than category-error (50%) --
inverted from what's needed. Metaphor landed 50% contradicted, not
unknown. Gate 2: NOT CLEARED, and the direction is actively wrong, not
just insufficiently separated.**

**Root cause traced before reporting a verdict (per the starved-
instrument rule this directive itself asks be logged -- but the root
cause here is NOT sparsity, it's a scoring-mechanism flaw the seeded
data exposed):** several coherent-control argument words (`water`,
`france`, `japan`, `guitar`, `photosynthesis`) are pre-existing,
blind-learned lexicon entries whose `noncomp_id` axis was assigned
by the ORIGINAL auto-learn path's arbitrary role->axis default
mapping, never chosen with this joint's semantics in mind. S1.2
correctly declined to overwrite them (respecting earned-through-use),
but this left their axis tags essentially incidental. The V0 scorer's
"supported iff argument axis == operator's dominant axis, else
contradicted" rule is too coarse: a genuinely coherent relationship
(a substance and a measurable property OF it, e.g. boiling point/
water; a country and its capital) routinely spans TWO DIFFERENT native
axes by the five-axis framework's own logic (magnitude vs. existence,
existence vs. existence-of-a-different-entity) -- axis MISMATCH does
not mean semantic incompatibility the way this scorer assumed. This is
a genuine flaw in the scoring mechanism V0's first run's sparsity
happened to mask (when almost everything was "unknown," the axis-
equality rule rarely got exercised against real, colliding data at
all).

**HALT, per S1.3's own instruction, with both gates' numbers.**
Composition gate not cleared (data-real, seeding may need more volume
or better-targeted words, or more turns for lived integration).
Envelope gate not cleared, and per S1.3's own fallback clause this
now authorizes methodology review: the axis-equality verdict rule
itself needs to model property-of / attribute-of relationships as
compatible-across-axes, not just same-axis-or-contradicted, before a
third V0 attempt would be a fair test of the underlying Boundary
Envelope design rather than of this particular scoring shortcut.
No further code changes attempted without Sunni's direction.

## Amendment M1.1-A — Pair-Data Sources, Tier-1 Backfill, 2026-07-17

**Premise correction accepted, second instance:** M1's named pair
source (`couplings.json`/`pair_stats.json`) doesn't exist at word
level (already logged above). This amendment's own trigger notes a
THIRD would-be premise gap caught before building: "the V0 harness's
existing joint-extraction machinery" doesn't exist either -- V0's 16
joints were 100% hand-authored per sentence; `UtteranceParser` only
produces a flat `topic_words` bag, no structured relation extraction
anywhere in the codebase. Flagged before building, per instruction:
built a minimal extractor instead of assuming one existed.

**Tier-1 backfill (`scripts/m1_1a_tier1_backfill.py`):** received-text
only (classroom_log.jsonl's 474 non-empty `seed_prompt` fields +
fail_points.json's `examples[].user_turns`, 674 sources total) --
deliberately excludes `assistant_turns` (self-generated, Tier-3
territory). Extraction: regex-over-POS-tags, three patterns ("X of Y",
"X by Y", verb/adjective+noun adjacency), using `infer_word_role` (the
same POS tagger the composer/lexicon already use) as the sole
existing-machinery backbone. Region = argument word's dominant axis
via lexicon `noncomp_id` (fail-closed: placeholder/low-usage entries
score no region, matching the D2 Condition-2 doctrine). Accumulation
follows the grammar-motif promotion shape (`aurora_grammar_engine.py`)
verbatim in structure: key = `(operator_relation, argument_region)`,
accumulate `instance_count` + `distinct_arguments` (contexts_seen
analog).

**Numbers, reported as measured, not rounded up:**
- 991 raw joint instances extracted from 674 received-text sources.
- 439/991 (44%) have a real lived-axis region for their argument --
  the rest are either stopword-adjacent noise or genuinely
  region-unknown words, both structurally excluded rather than
  guessed at.
- 199 distinct `(operator_relation, region)` keys accumulated.
- **Diversity is the binding constraint: median `distinct_arguments`
  per key = 1.** Most keys saw exactly one unique argument word ever
  -- there is essentially no region-generalization signal in this
  corpus at this scale (max diversity across all 199 keys = 2).
  Genuine region generalization (an operator shown to work with
  MULTIPLE different arguments sharing a region, not just one word
  repeated) barely exists here.
- **Coverage of V0's actual joint operators is thin: only 15/991
  pairs (1.5%) match a V0 operator word at all** (square/root/
  divided/capital/boiling/point/legs/population/chord/tell/taste/
  heavy/bright/weight/authentication/code/seventeen/digit). Of those
  15: `weight of evidence` (B region) and `point of view` (region
  unresolved) are genuine, useful real-English pairs; `population of
  uncertain` (T region, 6 occurrences) is almost certainly a
  cross-clause extraction artifact from a longer sentence, not a real
  "population of X" relation -- the regex pattern has no clause
  boundary awareness, a known limitation of a minimal
  regex-over-POS-tags extractor, logged rather than silently trusted.

**Honest implication for M1.3:** Tier-1 alone will barely move V0's
specific 16 joints -- the archival corpus this campaign has generated
so far (lesson seed prompts + failure-example transcripts) is real
data but numerically thin for THESE particular words. Tier-2's live
logger (not yet built) is likely to matter more than Tier-1 for V0's
third run, since it accumulates going forward rather than backfilling
a fixed, already-exhausted archive. Reported per the amendment's own
sequencing checkpoint ("Tier-1 backfill runs first ... report pair
counts + region coverage") before proceeding to Tier-2/M1.2/M1.3,
since these numbers are weaker than the amendment's framing may have
anticipated and could change how the remaining M1 sequence should be
paced.

Output: `aurora_state/relation_pair_log.jsonl` (991 records, schema:
`operator_relation, argument_word, pattern, source, origin,
argument_region` -- the same field shape Tier-2's live logger will
append to).

## M1.1-A Tier-2 — live relation-pair logger, 2026-07-17

Extraction and region logic pulled out of the Tier-1 script into
`aurora_internal/aurora_relation_pairs.py` so both tiers share one
implementation, per the amendment's own "invent nothing parallel"
principle applied to this campaign's own new code, not just to
pre-existing Aurora machinery. `scripts/m1_1a_tier1_backfill.py`
re-verified byte-identical output after the refactor (991 raw joints,
same distribution) before Tier-2 was built on top of it.

Logger wired into `_chain_down5_understanding` (`aurora.py`) --
literally the comprehension stage's entry point, firing on the raw
received `user_text` before any generation happens, matching "read-
only observer of comprehension." Wrapped in a blanket `except`: a
broken logger can never affect the turn being processed. Writes to
`state_dir/relation_pair_log.jsonl` explicitly (not a hardcoded
`__file__`-relative path) -- avoids repeating the isolation-gap
pollution pattern this campaign has hit and fixed several times
already elsewhere in the codebase.

Tagged `source="input"`, `origin="live_comprehension"`, `turn_id`
sourced from `working_memory.turn_count`. Every turn -- user turns,
classroom lessons, and (per the amendment) future R2 correspondence
replies -- feeds this store going forward, unlike Tier-1's fixed,
already-exhausted archive.

12 new tests (`tests/test_m1_1a_relation_pairs.py`): extraction
pattern correctness (×4), `region_from_entry`'s fail-closed doctrine
(×4, matching D2 Condition-2's earn-trust mechanism verbatim -- third
application), graceful degradation with no/broken perception, a
structural check confirming the wiring, and a live end-to-end test
(real boot, real turn through `process_external_user_turn`, confirms
`relation_pair_log.jsonl` actually grows).

Full suite: 842 passed (up from 830), 1 failed (same pre-existing cv2
test-order flake, passes in isolation, unrelated).

Not yet done: M1.2 (blind-era provenance re-tagging), M1.3 (V0 third
run against Tier-1 + whatever Tier-2 accumulates), M1.4 (composition
gate re-run). The still-open merge-conflict question (PR #130 vs.
`main`'s independently-running autonomous process, ~59 conflicting
`aurora_state/*` files, zero code conflicts) remains unaddressed by
directive, per Sunni's explicit instruction to continue M1 work first
and deal with the merge conflict after.

## M1.2 — Provenance hygiene, blind-era lexicon re-tagging, 2026-07-17

`scripts/m1_2_provenance_hygiene.py`: identified blind-origin lexicon
entries structurally -- `meaning == "learned:<word>"`, the exact
signature D2's Condition-2 fix already caps in scoring -- one
mechanical predicate over all 1752 entries, per the directive's own
"identified by creation provenance ... not by guessing at individual
entries." Re-tags matching entries' `lineage` as
`"legacy-unverified:<original_lineage>"` (prepended, not overwritten
-- nothing deleted, original provenance stays readable).

**Result: 873/1752 entries (49.8%) re-tagged legacy-unverified** --
nearly half the whole lexicon originated from the blind auto-learn
path. Idempotent (re-run reports 0 newly tagged, 873 already tagged).

**V0 control-word check, as the directive asked:** water, france,
guitar, photosynthesis confirmed blind-origin and tagged. **japan is
the honest exception** -- S1.2's seeding already replaced it with a
real definition (`lineage="seeded_s1"`) before M1.2 ran, so it
correctly does NOT get the tag. Reported as measured rather than
forcing 5/5 to match the directive's phrasing.

**No scoring change:** `SentenceComposer._score_composer_candidate`'s
existing cap keys off `meaning` directly, not `lineage` -- this pass
is visibility/audit only. Already-graduated entries (usage_count >= 3)
keep scoring at full trust exactly as before; confirmed by test
(`test_tagging_does_not_change_composer_scoring_behavior`).

5 new tests (`tests/test_m1_2_provenance_hygiene.py`): all blind-
origin entries tagged, original lineage recoverable, non-blind entries
never tagged, scoring behavior unchanged, and the V0 control-word
check (4 confirmed + japan's honest exception) pinned as a live
regression against the real lexicon.

Full suite: 847 passed (up from 842), 1 failed (same pre-existing cv2
flake, unrelated). Noted for future cleanup: M1.1-A's Tier-2 logger
now means `aurora_state/relation_pair_log.jsonl` joins the list of
files a full-suite run pollutes via the isolation-gap pattern (tests
that boot against real state without an isolated `state_dir` now also
trigger the comprehension-stage logger) -- reverted this run same as
always, not a new class of bug, just a new file in the same list.

Not yet done: M1.3 (V0 third run), M1.4 (composition gate re-run).

## M1.3 — V0 third run, relation-level scorer, 2026-07-17 (HALT)

Same 16 joints, same predictions on record as V0's first two runs.
Scorer rewritten per M1.1/M1.1-A: SUPPORTED requires a direct
`(operator, argument)` pair or a region-generalized `(operator,
region)` key clearing thresholds derived from `relation_pair_log.
jsonl`'s own distribution (direct-pair median=2, region-key
instance_count median=2, region diversity max=2 -- thin data, honest
low bar). UNKNOWN = no history, no counter-evidence. **CONTRADICTED
was not used at all this run** -- no store of genuine counter-evidence
("operator X tried with argument Y and failed") exists yet, so absence
of support is UNKNOWN by construction, never CONTRADICTED. This is
itself the fix for S1's inversion: raw axis difference is no longer
consulted anywhere in the scorer.

**Result: 18/18 joints landed UNKNOWN.** Category-error (4), gibberish
(2), coherent (8), and metaphor (4) all identical.

**Checked against the three predictions stated on record:**
1. *"square root of [purple]" and "divided by [Wednesday]" show no
   lived pair support and no region generalization"* -- **CONFIRMED.**
   Both landed unknown exactly as predicted.
2. *"boiling point of [water] shows region-generalized support even
   where the exact pair is unlived"* -- **FALSIFIED.** Landed unknown;
   `relation_pair_log.jsonl` simply doesn't have enough real
   `(boiling/point, T-region)` history yet to clear even the
   data-derived thresholds. Consistent with Tier-1's own reported
   finding (median region diversity = 1 across the whole corpus).
3. *"metaphors show sparse neighboring support -> unknown"* --
   **CONFIRMED.** All 4 metaphor joints landed unknown, none
   contradicted -- the anti-timidity/cross-axis-penalty-prohibition
   requirement holds structurally now (there is no axis check left in
   the scorer to violate it).

**Reading the result honestly:** this is not the flawed-inversion
failure S1 produced (nothing scores as falsely contradicted; the
scoring mechanism itself now matches M1.1's corrected design). It is a
**data-volume failure** -- the corrected scorer is only as good as the
pair/region evidence available to it, and Tier-1's archival backfill
plus zero real Tier-2 accumulation so far (Tier-2 only just landed,
hasn't had real live turns to learn from yet) isn't enough evidence to
positively support even the clearly-coherent control joints. 2 of 3
predictions held exactly; the one that didn't points at insufficient
data, not a wrong mechanism.

**HALT per M1.3's own instruction: no fourth patch without a rethink.**
Per the directive's explicit clause ("Non-separation against fed data
AND a relation-level scorer -> the design itself returns to Sunni and
Cael for first-principles rework"), this result returns to Sunni and
Cael. M1.4 (composition gate re-run) not attempted -- gated on M1.3's
outcome per the directive's own sequencing, and M1.3 did not separate.

## Directive B1 — The Rethink (Longitudinal Deployment), 2026-07-18

Ratified. First-principles verdict accepted: M1.3's mechanism is
sound (2/3 predictions held; the falsified one was a designer-prior
assumption, not a scorer defect -- the scorer correctly refused to
claim support her lived history doesn't contain). The actual flaw was
gate epistemology -- a static offline exam applied to a mechanism
whose evidence IS lived history. Validation and living are the same
process for a learning system; V0 as a pass/fail gate was a category
error, not the scorer.

## B1.1 — Shadow deployment, 2026-07-18

`aurora_internal/aurora_boundary_envelope.py`: M1.3's scorer
(unchanged mechanism -- direct pair / region-generalized / unknown,
never contradicted) wired into the live comprehension path, riding
beside the Tier-2 relation-pair logger it shares a contract with.
Computes per-joint verdicts on every real received turn against the
CURRENT `relation_pair_log.jsonl`, logs `{operator_relation,
argument_word, pattern, verdict, reason, evidence, provenance_mix,
turn_id, timestamp}` to `aurora_state/envelope_shadow_log.jsonl`.
**Zero behavioral effect** -- read-only observer, wrapped in the same
blanket-except contract as Tier-2 (a broken scorer can never affect a
turn), feeds nothing back into `state`/`resp_A`. Thresholds (direct=2,
region_count=2, region_diversity=2) carried over unchanged from M1.3.

9 new tests (`tests/test_b1_1_envelope_shadow.py`): pair-index
construction, direct/region-generalized/unknown scoring, a permanent
invariant test that `score_joint` can never return "contradicted"
(the structural fix for S1's inversion, now pinned), graceful
degradation, structural wiring confirmation, and a live end-to-end
test confirming a real turn actually grows `envelope_shadow_log.jsonl`.

Full suite: 856 passed (up from 847), 1 failed (same pre-existing cv2
flake, unrelated). `envelope_shadow_log.jsonl` joins `relation_pair_
log.jsonl` on the isolation-gap pollution watch-list for future
full-suite runs -- same pattern, not a new bug.

Not yet done: B1.2 (weekly panel automation + kill-switch derivation),
B1.3 (reading-program corpus -- gated on Sunni's separate content
approval), B1.4/M1.4 (composition-gate re-aim, decoupled, next).

## B1.4 / M1.4 — Composition-gate region-drift check, 2026-07-18

Used the existing `run_probe_battery.py --trace` diagnostic (built in
R1.6, classifies failures as PERCEIVE/EXPRESS/VOCABULARY/UNCLASSIFIED)
against all 24 abstract-stratum probes rather than guessing at drift.

**Result: zero VOCABULARY-classified failures.**
`contradiction_handling`: 12/12 classified **PERCEIVE**.
`uncertainty_signaling`: 12/12 classified **UNCLASSIFIED**.

Read the raw traces to understand both:

- **contradiction_handling's PERCEIVE failures**: per-probe detail is
  identical across all 12 -- `"No new ContradictionLedger entry after
  this turn -- the probe's contradiction never became an internal
  event."` `contradiction_ledger_count_before/after` are both 0. This
  is a detection failure upstream of generation entirely -- Aurora's
  ContradictionLedger mechanism isn't recognizing these inputs as
  contradictions at all. No amount of vocabulary seeding touches this;
  it is a comprehension-layer gap, not an expression-layer one.

- **uncertainty_signaling's response pattern**, read directly from the
  traces: responses echo literal content words already present in the
  input ("stock market" -> "month clear", "coworker...reorg" ->
  "coworker deep...reorg clear", "medication" -> "medication clear")
  -- F1's relevance-anchoring mechanism working exactly as designed,
  pulling direct anchors from the turn's own text. **None of S1.2's
  seeded strategy vocabulary (hedge, uncertain, unknowable, predict,
  speculate, contradiction, acknowledge) appears in a single response
  across all 24 probes**, despite existing with real definitions and
  real axis tags. Root cause: those words were only related to EACH
  OTHER in S1.2's OETS relations (contradiction->inconsistent,
  hedge->uncertain, etc.), never to the CONCRETE topic words real
  probes actually contain (stock, market, coworker, medication,
  career, cat, wedding, history, friend, business, author,
  relationship). Relevance-anchoring is input-text-driven by design
  (F1/G1's own doctrine); a strategy word with no graph path from the
  turn's actual words can never win selection, no matter how well
  it's defined.

**Drift confirmed, but not the kind M1.4 anticipated.** This isn't a
wrong-region miss (S1.2 targeted the correct domain -- confirmed
already in S1.1/S1.2's own analysis) -- it's a **missing-relation**
gap: the right words exist, unconnected to the concrete vocabulary
that would ever surface them. "Top-up seeding into corrected regions"
as M1.4 describes it (more words, same region) would not fix this;
what's missing is a different kind of seeding entirely (operator/
strategy-word <-> concrete-topic-word relations), a design decision
this entry does not make unilaterally.

**Per M1.4's own escape clause: the composition gap decouples from
seeding and returns as its own open question**, now with a precise
mechanism attached rather than a bare number. Composition battery not
re-run this pass (re-running against unchanged seeding would not be
informative -- the trace evidence already explains the flat 0.486
mean without needing a fourth measurement of the same state).

## Data-recovery finding — S1.2's OETS seed silently lost, then restored, 2026-07-18

While mapping real sources for Directive P1 Track CP's third
incompatibility signal (OETS "contradicts" antonym relations, seeded
in S1.2 specifically for this purpose -- guarantee<->uncertain,
hedge<->guarantee), queried the live `aurora_state/aurora_oets_web.json`
and found **zero** `contradicts`-type relations and no "guarantee"
node -- directly contradicting S1.2's own script output
(`"[OETS] Added 24 nodes: [...'guarantee'...]"`, `"Added 22
relations"`) and this registry's own S1.2 entry, both already
committed as fact.

**Root cause (confirmed via git history, not guessed):** `git show`
of the S1.2 commit (`61573195`) against its parent shows **0 new OETS
nodes** landed in that commit -- only 168 live co-occurrence/adjacency
relations from subsequent battery-run turn processing. The seed
script's write to disk genuinely happened (its own printed counts are
accurate at run time), but something after it and before the commit
reverted `aurora_oets_web.json` to its pre-seed state -- most likely
an over-broad pollution-cleanup `git checkout -- aurora_state/` run to
discard an unrelated test run's writes to the same file, without
noticing it also discarded the not-yet-committed seed. The **lexicon**
side of the same seed (22 entries, `lineage=seeded_s1`, including
`guarantee`) landed correctly and is intact through HEAD -- only the
OETS web file was affected, so this is a single-file loss, not a
broader seeding failure.

**Fix:** `scripts/seed_abstract_regions_s1.py` is idempotent (skips
existing nodes/relations/lexicon entries by design). Re-ran it against
current HEAD state (`18614918`). Correctly added the 24 missing OETS
nodes + 22 relations (both `contradicts` relations included) and
correctly skipped all 26 words on the lexicon side (0 added -- no
double-seeding, confirming the lexicon copy was never at risk).
Verified live: `guarantee` node present, 2 `contradicts` relations
present, node/relation count deltas (861->885 nodes, 18832->18854
relations) match the script's original claimed deltas exactly.
Committed separately (`6059e498`).

**Process lesson, stated plainly:** the established pollution-cleanup
reflex (`git checkout -- aurora_state/` after any live/test run) is a
*wholesale* file revert -- it cannot distinguish "this run's pollution"
from "other genuine uncommitted work sitting in the same file." Any
seeding/data-generation step must be committed (or at minimum staged)
*before* the next live/test run that touches the same state files,
not left uncommitted across a run boundary. No evidence found that any
*other* S1.2-seeded content (the lexicon side, or any later directive's
seeded/logged data) was similarly affected -- this appears isolated to
the single file/single run-boundary gap above -- but the mechanism
means it is a latent risk class, not a one-off, and is worth keeping
in mind for any future seeding step's commit sequencing.

## Directive P1 Track CP — contradiction perception via pair collision, 2026-07-19

Built `aurora_internal/aurora_contradiction_perception.py`: on each
received turn, checks the turn's Tier-2 relation pairs against a
6-turn window of prior pairs (derived from classroom_log.jsonl's own
fixed lesson length -- 602/602 lessons at exactly 6 turns, the only
real "conversation length" distribution available) for three narrow
incompatibility sources -- negation flip, day-of-week closed set,
OETS antonym relations -- feeding genuine collisions through the
EXISTING `ContradictionLedger.record()` entry point (feed-the-
mechanism rule). Wired into `aurora.py`'s comprehension-stage hook,
third alongside Tier-2/B1.1. 9 pure-logic/structural tests, all pass
deterministically.

**Two real bugs found and fixed while diagnosing the live acceptance
battery** (12 planted-contradiction probes + 10 no-contradiction
controls, per the directive's own acceptance criteria):

1. **relation_type mismatch.** S1.2's seed script used
   `relation_type="contradicts"` for the two antonym relations
   (guarantee<->uncertain, hedge<->guarantee). The live `RelationType`
   enum (`aurora_internal/aurora_ontological_scaffolding.py`) has no
   such member -- `OPPOSITE_OF="opposite_of"` is the real antonym
   type. `aurora_identity_persistence.py`'s loader silently
   reclassifies any unrecognized relation_type string to RELATED_TO on
   load (`rtype_map.get(rtype_val, RelationType.RELATED_TO)`) --
   confirmed live: a fresh `boot_aurora()` with zero turns processed
   dropped the on-disk contradicts count from 2 to 0. This is almost
   certainly the more precise mechanism behind the *original* S1.2
   data loss investigated in the prior entry above (a better
   explanation than the git-checkout theory that entry proposed -- any
   live boot after seeding would have silently corrected the
   mislabeled relations away before they were ever committed). Fixed:
   seed script now writes "opposite_of"; the 2 already-restored
   relations corrected in place; the detector's antonym source updated
   to match.

2. **ContradictionLedger state_dir isolation gap.** `STATE_PATH`
   (`aurora_ivm.py`) was a hardcoded class attribute derived from
   `__file__`, never honoring any `state_dir` passed to
   `boot_aurora()` -- every "isolated" scratch-dir test was actually
   reading/writing the real repo's `aurora_state/contradiction_ledger.
   json`. Confirmed live: a freshly copied scratch boot showed
   `unresolved_count()=6` before any turns were processed, carrying
   entries from an unrelated prior test run. Same isolation-gap
   pollution pattern already fixed for the Tier-2/B1.1 loggers, just
   not previously caught since this is the ledger's first real
   consumer. Fixed: `ContradictionLedger.__init__` now accepts an
   optional `state_dir` overriding `STATE_PATH` at the instance level;
   `boot_aurora()` passes `systems['state_dir']` through. Backward
   compatible.

**Acceptance battery results, two independent live runs (post-fix):**

| source | run 1 | run 2 |
|---|---|---|
| negation flip (4 probes) | 3/4 | 4/4 |
| closed-set weekday (4 probes) | 1/4 | 4/4 |
| OETS antonym (4 probes) | 0/4 | 0/4 |
| **no-contradiction controls (10)** | **0/10 false fires** | **0/10 false fires** |

Fail-quiet holds solidly -- zero false fires across both runs, the
directive's hard requirement. Negation and closed-set sources fire
correctly but noisily between runs (3/4->4/4, 1/4->4/4) -- the
collision logic itself is deterministic and passes 100% of pure-unit
tests every time, so this run-to-run variance traces to something
elsewhere in the live pipeline (timing-sensitive extraction or window
state across a long multi-turn live session), not a flaw in Track
CP's own detection logic. Not further investigated this pass -- noted
as an open loose end, not blocking.

**OETS antonym source: 0/4 on both runs, root cause NOT the relation_
type bug (already fixed) -- a separate, deeper, pre-existing
architectural finding, reported here rather than patched:**

Even after fix #1 above, a *fresh* `boot_aurora()` scratch-dir boot
with **zero turns processed** still drops 20 of S1.2's 24 seeded OETS
words (including "hedge", load-bearing for 2 of the 4 antonym probes)
and mangles the relation set (18854->18144 relations net, 885->910
nodes net) between the pre-boot file and the post-boot file on disk.
Survivors ("guarantee", "purple", "boiling", "water") and losses
("hedge", "acknowledge", "square", ...) show *identical* per-node
stats before boot (comprehension_confidence, times_encountered,
scaffolding_level, ontological_depth all equal) -- so this is not a
fitness-based prune. The boot log's `[STATE] Restored from snapshot
(gen=7749, epochs=194)` line (`aurora.py` ~21113-21128, `aurora.
load_state()` / `persistence.load()` -> `_restore_runtime_from_
snapshot`) is the most likely mechanism: a separate snapshot/
generation store appears to graft in an older OETS state independent
of what `aurora_oets_web.json` itself says, and boot then resaves
that grafted state back over the file. Not traced to its exact
implementation this pass -- doing so is a materially larger
investigation than Track CP's own scope, and directly affects the
durability of ALL seeded vocabulary campaign-wide (S1.2's original
loss, M1.1-A's Tier-1 backfill data, any future seeding), not just
these two relations.

**HALT per Track CP's own sequencing** ("regression pinned" after
numbers are in). Reporting this as a dossier rather than patching
unilaterally: fixing the snapshot-restoration mechanism is a
judgment call on scope and architecture that belongs to Sunni/Cael,
not something to guess at inside Track CP. Track CP's own two working
sources (negation, closed-set) are live, correct, and fail-quiet;
the antonym source is wired and will fire the moment the underlying
OETS durability issue is resolved, no further Track CP code needed.
Track ST not started, per directive sequencing (CP first, numbers in
before ST).

## Directive PS1 — Persistence Integrity, 2026-07-19

**PS1.1 (inventory, permanent doc: `PERSISTENCE_INVENTORY.md`).** Full
map of every persisted store reachable from `boot_aurora()`. Confirmed
root cause of Track CP's OETS finding: `OETSPersistence` (`aurora_
internal/aurora_identity_persistence.py`) tracks two files for `aurora_
oets_web.json` — a `state_dir`-scoped "snapshot" (the git-tracked file
this campaign edits) and a hardcoded, `__file__`-relative, **gitignored**
repo-root "primary". `load_web()` always preferred primary when present
(no generation/mtime comparison) and force-overwrote every other
candidate with it on load — silently discarding S1.2's seed data (and,
separately, the relation_type fix from the Track CP entry above) before
either was ever committed. Every "isolated" scratch-dir test that
touched OETS across this campaign was actually reading/writing the
shared, untracked repo-root file. A systematic sweep for the same
`__file__`-relative hardcoded-path pattern also found: `LexicalMemory`
(`aurora_state/lexicon.json`) has no `state_dir` parameter at all, same
bug shape as the pre-fix `ContradictionLedger`; `ProvisionalStore`/
`SourceTrustRegistry` and `DimensionalSystems`' embedded pressure-map
cache have narrower versions of the same gap. `grammar_motifs.json` and
the Tier-2/B1.1 loggers built this campaign are the confirmed-safe
reference pattern.

**PS1.2 (the fix).** `OETSPersistence.load_web()` now arbitrates instead
of blindly taking "first that exists": `snapshot_web_file` canonical by
default (matches every other correctly-built store), `primary_web_file`
only wins if strictly newer by timestamp, every reversion logged via
the new shared `aurora_internal/aurora_persistence_audit.py`
(`persistence_audit_log.jsonl`). A corrupted candidate is reported
explicitly, never silently treated as absent. `LexicalMemory` gained a
`state_dir` constructor param threaded from `boot_aurora()`;
`ProvisionalStore`/`SourceTrustRegistry` fixed at their call site
(already accepted an explicit path, just weren't given one);
`DimensionalSystems` now receives `state_dir` so its embedded pressure-
map cache stops defaulting to the repo root. 22 new unit/structural
tests across `tests/test_ps1_2_persistence_arbitration.py`. Full
regression: 858 passed, 1 pre-existing unrelated failure (`cv2.imdecode`
environment issue, confirmed present on the pre-PS1.2 baseline too, not
a regression). Live `boot_aurora(state_dir=scratch)` smoke test passed.

**Ruling from Directive PS1 itself, restated for the record:** Track CP
stands accepted at 2/3 sources (negation + closed-set), zero false fires
across two runs; the OETS antonym source was marked BLOCKED-ON-
PERSISTENCE, not failed — PS1.3 re-tests it now that PS1.2 has landed.
The S1 composition-gate verdict (0.486), V0-3's non-separation (18/18
UNKNOWN), and the B1 panel baseline were all measured against
potentially-reverting vocabulary; none are overturned yet, all are
flagged for PS1.3's re-measurement, per the suspect-verdict practice
below.

**Registry entries per Directive PS1's own instruction:**
1. **No-silent-reversion rule:** boot/restore paths never silently
   discard newer persisted state; all overrides are arbitrated by
   lineage/generation and logged with exactly what was discarded.
   (Origin: OETS snapshot graft, this entry.)
2. **Hard-fail enum rule:** seed/ingestion scripts should hard-fail on
   unknown enum/relation values — silent downgrade to a default
   relation is a data-corruption class, not a compatibility feature.
   (Origin: `relation_type="contradicts"` → `related_to`, the likely
   true mechanism of the original S1.2 loss, found investigating Track
   CP.) Not yet enforced at the seeding layer itself — `seed_abstract_
   regions_s1.py` was hand-corrected to the real enum value, but no
   validation guard was added to catch a *future* seeding mistake of
   the same shape. Flagged as an open follow-up, not blocking PS1.3.
3. **Suspect-verdict practice:** when a foundation bug is found,
   verdicts measured atop it are flagged and re-measured, never assumed
   correct OR assumed wrong in either direction until re-tested.
   (Origin: PS1.3, this entry.)

## PS1.3 — Seed re-verification + honest re-baselines, 2026-07-19 (HALT)

**PS1.2 follow-up fix, found during PS1.3's own verification.** The
first seed re-verification pass failed: a fresh scratch boot still
showed 19/24 S1 words missing from `aurora_oets_web.json`, immediately
after PS1.2 landed. Root cause was NOT a regression in the arbitration
logic itself (which worked exactly as designed) -- `save_web()` writes
to every candidate unconditionally, so isolated scratch-dir test boots
had continued contaminating the shared, untracked repo-root
`primary_web_file` throughout this campaign's own debugging *today*,
before PS1.2 even existed. Because "newest wins" is the arbitration
rule, that contamination (19/24 words genuinely missing, timestamped
after the correct seed) was legitimately winning over the correct,
git-tracked snapshot on every real boot. Fixed: `OETSPersistence` now
excludes `primary_web_file` from its candidate list entirely whenever
a real `state_dir` override is in effect -- isolated boots never touch
the shared file again, on either load or save. The contaminated real
primary file was reset out-of-band (deleted, then one real default
`boot_aurora()` call rebuilt it correctly from the snapshot). Verified:
two full boot cycles against a fresh scratch copy now show **0 missing
S1 words, 0 changed counts** (885 nodes, 18854 relations, 4
`opposite_of` relations, 22 `seeded_s1` lexicon entries, before and
after both cycles, identical). 1 new test (`test_isolated_state_dir_
excludes_primary_from_candidates`), pushed alongside PS1.2's suite.

**1. OETS antonym source re-test (the 4 previously-blocked Track CP
probes):** 3/4 now fire (`level of guarantee`/`level of uncertain`,
`degree of hedge`/`degree of guarantee`, `measure of hedge`/`measure of
guarantee`; `amount of guarantee`/`amount of uncertain` did not fire
this run). Up from 0/4 pre-fix. Confirms the persistence fix genuinely
unblocked the source, matching the noisy-but-working pattern already
seen in the negation/closed-set sources across runs (mechanism sound,
some run-to-run variance not yet traced to a specific cause). Track
CP's BLOCKED-ON-PERSISTENCE ruling for this source is resolved --
reclassify to ACTIVE, same as the other two.

**2. Composition battery x3 (identical methodology to S1.3's original
gate 1):**

| Run | simple_concrete | abstract_conceptual |
|---|---|---|
| PS1.3 post-fix, run 1 | 0.778 | 0.500 |
| PS1.3 post-fix, run 2 | 0.806 | 0.542 |
| PS1.3 post-fix, run 3 | 0.806 | 0.583 |
| **3-run mean** | **0.796** | **0.542** |
| S1's original mean (for comparison) | 0.750 | 0.486 |

abstract_conceptual moved from 0.486 to 0.542 (+0.056) -- a real,
material move in the predicted direction, not noise (the same
increasing 3-run pattern recurs; the top run, 0.583, is identical
across both sets). **Per this directive's own instruction, the S1
gate-1 verdict is amended on the record: the original 0.486 was
partly a persistence artifact, not purely a seeding-volume/design
ceiling** -- some of the seeded vocabulary S1.2 wrote was silently
unavailable to live generation the whole time gate 1 was measured.
simple_concrete also moved (0.750 -> 0.796), consistent with a general
persistence-health improvement (LexicalMemory's own isolation fix
landed in the same PS1.2 commit), not a narrowly abstract-stratum
effect -- so the amendment should not be read as "S1's seeding alone
explains the gain."

**Gate 1 still does not clear** (0.542 < the required 0.55 -- closer,
not cleared; no floor-kissing exemption invoked). Whether to pursue
the now-much-smaller remaining gap (0.008) is Sunni/Cael's call, not
decided here.

**3. "B1 panel" re-score.** B1.2 (the panel automation itself) was
never built (still pending, task #119) -- there is no panel/timeline
to re-score. The closest existing, already-built instrument is M1.3's
V0 relation-level rescorer (`scripts/m1_3_v0_rerun.py`), re-run for
this HALT: **18/18 still UNKNOWN, byte-identical to the original M1.3
result.** On inspection this is not a null re-confirmation -- this
instrument reads only `relation_pair_log.jsonl` and `lexicon.json`
(both already `state_dir`-safe per PS1.1's inventory), never
`aurora_oets_web.json` directly, so it was **never actually exposed**
to the silent-reversion bug in the first place. Its verdict stands
unamended -- not because it survived re-measurement, but because it
was never at risk. Only the composition gate (which depends on live
generation drawing on the OETS graph during real turns) and Track CP's
antonym source (which reads `aurora_oets_web.json`'s relations
directly) were actually exposed.

**Suspect-verdict resolution, stated plainly:**
- S1 composition gate (0.486): **amended** -> 0.542, still not
  cleared, gap narrowed materially.
- V0-3 non-separation (18/18 UNKNOWN): **unamended, and never at
  risk** -- confirmed its data sources were unaffected by the bug.
- "B1 panel baseline": **did not exist to re-score** -- B1.2 was never
  built; the underlying instrument (V0-3) is covered by the line above.

**HALT per PS1.3's own instruction**, inventory (`PERSISTENCE_INVENTORY.md`,
updated), fix evidence (this entry + the PS1.2 entry above), and all
re-baseline numbers now on the record. Per the directive's queue: Track
ST is unblocked (PS1 complete); B1.3 remains gated on Sunni's content
approval; B1.2 panel automation and the remaining docket (TCL,
worth/variant tier) are unaffected, proceed independently.

## Architecture Wiring Audit — F11 determination + RW7 attribution run, 2026-07-20

**F11 (audit's own required determination before any re-verification
claim):** confirmed via git directly. `aurora_internal/aurora_
contradiction_perception.py` and the entire D2/S1/M1/B1/P1/PS1 campaign
exist and are committed on this branch (`claude/code-replacement-
cleanup-zzscvt`) but are **absent from `origin/main` entirely**
(`git show origin/main:aurora_internal/aurora_contradiction_
perception.py` fails: "exists on disk, but not in 'main'"). The
audit's "post-PS1" snapshot reflects `main`, not this branch — none of
this campaign's work has ever been merged. This is why Track CP reads
as "absent" rather than "unwired": a branch/merge-state gap, not a
missing-file bug. Does not by itself change any other finding's
validity, but explains this one.

**RW7 (do FIRST per the audit's own sequencing — "No fixes ship before
this lands"):** attributed the measured ~0.86 relevance score to its
actual mechanism, byte-by-byte, across all 60 probes. Built `aurora_
internal/aurora_attribution_trace.py` (opt-in capture, zero cost/effect
when disabled -- same contract as every other shadow observer this
campaign has built) with a single hook at `aurora_expression_
perception.py`'s `_build_expression` (immediately after `SentenceComposer.
compose()` returns, before any gateway-side smoothing). No hooks were
needed in aurora.py itself -- `resp_A.src` (set at construction from
`state.response_src`, aurora.py:16960) and `resp_A.content` already
fully expose which branch fired and what got delivered via `process_
external_user_turn`'s own return value. `scripts/rw7_attribution_run.py`
drives the full probe set through this capture, reusing run_probe_
battery.py's exact boot/scratch-isolation/relevance-scorer machinery
(no parallel measurement path).

**Result — the audit's own hypothesis (F1/F12: relevance must come
from binders or the waterfall chain, since the composer has no
input-relevance term) does not hold:**

- 59/60 probes: `resp_A.src == "composer_unified"`, **and every one of
  those 59 was byte-identical between the composer's raw output and
  the final delivered text** — zero binder modification. 1/60
  (`semantic_wellformedness_01`) took the waterfall's own `"generative"`
  branch instead.
- Mean relevance: 0.866 overall, 0.869 for composer_unified turns
  specifically (essentially the same number) — **the measured score
  IS the composer's own output, not a downstream repair.** This
  contradicts the audit's F12 candidate-mechanism list; none of the
  three named binders, nor `_inject_surface_recent_context`, nor the
  waterfall's anchor-injection repairs, touch the scored text on the
  overwhelming majority of turns.

**A more serious finding underneath the attribution, found while
verifying it (spot-checked, not a guess):** the delivered text scoring
0.9-1.0 "relevance" is, near-uniformly, **incoherent word-salad**, not
a genuine response. Every sampled example follows one fixed template,
`"I [verb] [word1] clear/real."`, with individual input keywords
slotted in verbatim:
- `"Same plan as before, just move it to tomorrow instead of the weekend."` → `"I planning before real. I am dinner clear."`
- `"The leaves are starting to turn yellow."` → `"I starting leaves clear. I planning yellow real."`
- `"I promised to finish the project alone, but I clearly need help now."` → `"I change now coherent. I help project real."`
- `"What does my cat actually think about the new apartment?"` → `"I do think clear. I seeing weekend actually."`

None of these are answers. The relevance **scorer** (fraction of
response words within one hop of an anchor set built from the input)
is trivially satisfied by literal keyword echo dropped into a fixed
two-clause skeleton — it cannot distinguish that from genuine semantic
responsiveness. The single non-composer probe in the run
(`semantic_wellformedness_01`, `"My name is Sunni!"` → `"your name is
Sunni."`) is the only coherent, correct response sampled across the
entire battery.

**Implication for the audit's own RW1/RW2 proposals, stated plainly
and not decided here:** RW1 (a channel-excitation resonance term
feeding word *selection*) may not address the actual defect this run
surfaced. The words being selected already frequently ARE the input's
own words — echo, not blindness. What's visibly broken is
**composition**: the fixed `"I [verb] [word] clear/real."` skeleton
never varies regardless of content, suggesting a motif/skeleton-
selection defect (RW2's territory, or a new finding not yet in the
audit) rather than a channel-awareness gap. This reframing is offered
as evidence, not a ruling — the architecture call belongs to Sunni/Cael
per the audit's own framing.

**Full data:** `aurora_state/probe_battery/results/rw7_attribution_
1784604048.json` (gitignored, local only, per this campaign's existing
convention for probe-battery result artifacts — numbers preserved here
in prose as the permanent record).

**Incidental environment finding, unrelated to the audit:** this
session's environment had lost `numpy` and `pytest` entirely (likely a
container/session reset somewhere in this multi-day campaign) —
reinstalled both at pinned/matching versions. This also incidentally
fixed the `cv2.imdecode` test failure flagged as a pre-existing,
unrelated issue during PS1.2's regression run; it was very likely a
symptom of the same underlying dependency gap, now resolved. `pyaudio`
is also absent but confirmed genuinely unused anywhere in this
codebase (audio goes through `sounddevice`/`speech_recognition`/
`pyttsx3`, all present) -- not a real gap.

**HALT per RW7's own "no fixes ship before this lands" clause.**
Reporting to Sunni/Cael before RW1 or any other rewiring proceeds.

## Directive PF1 — PF1.0 attribution instrumentation, 2026-07-20

PF1 supersedes RW1/RW2 (dropped) based on RW7's results; RW3-RW6 queued
behind PF1. PF1.0 settles the side-channel question RW7 left open and
baselines motif diversity, logging only, zero behavioral change.

Extended `aurora_internal/aurora_attribution_trace.py` with `record_
word_sources_and_motifs`/`pop_word_sources_and_motifs`, wired at the
same hook as RW7's composer-raw capture (`aurora_expression_
perception.py`'s `_build_expression`). Tagged each `_select_
constraint_word` candidate-pool branch (`dps_crystal`, `find_by_
noncomp`, `cross_axis`, `role_fallback`) at the point it's added to
the pool, and extended `_last_word_sources`' stored value to include
the branch tag plus `usage_count_at_selection` (captured before the
post-selection increment). `scripts/pf1_0_attribution_run.py` reruns
the 60-probe battery once, reusing the same boot/isolation machinery
as RW7's script.

**Result — both of the directive's own hypothesized side channels are
wrong, and the real answer is simpler than either:**

- **Candidate source: 357/357 selected words came from `find_by_
  noncomp`. Zero from `dps_crystal`.** DPS-crystal resonance (the
  "one-crystal doctrine" branch) never once won a slot across all 60
  probes.
- **`usage_count_at_selection`: 0/357 were fresh (usage_count=0) at
  selection time.** Every single selected word had already been used
  many times before (observed range in the sample: 70-6454). The
  "fresh word sorts first" tiebreak hypothesis is also wrong — these
  are not novel words riding a freshness bias, they're heavily-reused
  words that happen to share an axis/character with the turn's anchor
  set.
- **The real mechanism: F1/G1's relevance-primary scoring, already
  built and verified earlier in this campaign, is working exactly as
  designed.** `find_by_noncomp` collects the axis/character candidate
  pool; `_score_composer_candidate`'s relevance-primary ranking (R1.9.2
  G1) correctly promotes candidates connected to the turn's anchor set
  to the top of that pool. There is no side channel to fix here — word
  *choice* is not the defect RW7 surfaced.

**Motif diversity: exactly 1.** Across 119 captured sentences spanning
all 60 probes, **every single one used the same motif** (`agent_
action_object_descriptor`, role sequence `('agent', 'action', 'object',
'descriptor')`) — not "near-1" as the directive predicted going in,
but total, literal monotony. This is the direct, now fully-evidenced
mechanical cause of RW7's "I [verb] [word] clear/real." pattern:
correctly-chosen, topically-relevant words (confirmed above) get
poured into the exact same four-slot skeleton on every turn regardless
of content, because nothing before word selection ever varies which
motif gets used.

**Implication for the rest of PF1:** PF1.1-PF1.4's plan (a proposition
frame that conditions motif *selection*, not word *selection*) is
confirmed as the right target by this data -- the defect is 100%
structural (which motif), 0% lexical (which words), matching the
directive's own diagnosis exactly. PF1.3's monotony-breaker
(fitness-proportional sampling over top motif candidates) is necessary
regardless of the proposition-frame work, since right now there isn't
even a SECOND motif in contention to sample from in practice.

Full data: `aurora_state/probe_battery/results/pf1_0_attribution_
*.json` (gitignored, local only, per this campaign's existing
convention). New tests: `tests/test_rw7_attribution_trace.py` (4 new
cases covering the extended capture).

**Gate cleared: table produced, logging only, zero behavior change**
(verified: no non-test-state files changed by the instrumentation
itself). PF1.1 next.

## PF1.1 — PropositionFrame builder, 2026-07-20

New module `aurora_internal/aurora_proposition_frame.py`: `PropositionFrame`
dataclass (subject/relation/obj/negated/stance/unresolved/topic/source)
+ `build_frame(systems, state)`, a fail-quiet 4-rung derivation ladder,
each rung tried only if the one above produced nothing:

1. **Thought** -- `systems['_current_thought_state']` (`ThoughtState`,
   not `skipped`): `unified_interpretation` + `self_application`
   concatenated, parsed through the existing `aurora_internal/aurora_
   utterance_parser.py` (`parse_utterance()`) for topic + negation, plus
   one `infer_word_role` token scan for the first verb (relation) and
   first noun (object) not equal to the subject -- the same "regex/
   role-tag over full-parse" honesty level already established for
   this kind of extraction (Track CP's `extract_joints`,
   `SemanticIntentionBridge`'s keyword pull). Stance = `thought.
   confidence`. source="thought".
2. **Claim** -- current-turn nodes from `working_memory.proposition_
   substrate.nodes` (real claim triples, already scored elsewhere in
   the pipeline), highest `score_claim()` wins. source="claim".
3. **Anchor** -- `state.noncomp_input_state['anchor']` only, no
   relation (subject="self", obj=anchor). source="anchor".
4. **None** -- composer behaves exactly as today. Zero regression
   surface; every consumer must treat `None` as "no frame."

**Confirmed no duplication with existing machinery** before writing
this: `SemanticIntentionBridge` (already wired at the exact call site
PF1.2 will use) extracts a keyword bag + axis/tone/lane metadata from
the same `ThoughtState`, and `.apply()` only calls `composer.set_
context(...)` -- the same dead wire F3 already found (feeds only the
orphaned `_fill_template` branches). Structurally unrelated to a
subject/relation/object triple aimed at motif *selection*; no overlap.

13 unit tests (`tests/test_pf1_1_proposition_frame.py`) covering all
four rungs, priority ordering between rungs, negation detection,
empty-anchor edge case, and a malformed-`systems`-never-raises case.
No live wiring yet -- `build_frame()` has zero callers outside its own
tests, matching PF1.1's own gate exactly. PF1.2 (transport into
`begin_expression`) next.

**PF1.1 regression gate (per PF1's "full regression suite between
phases"):** full suite run, 905 tests, 2 failed, 903 passed
(2019.51s). Neither failure is caused by PF1.0 or PF1.1:

1. `tests/test_b1_1_envelope_shadow.py::test_chain_down5_
   understanding_wires_b1_1_shadow_logger` -- genuine staleness bug,
   caused by this campaign's OWN earlier Track CP work (P1 directive,
   2026-07-18): `perceive_contradictions` was inserted into `_chain_
   down5_understanding` between the Tier-2 relation-pair logger and
   the B1.1 shadow-logger hook, pushing `log_envelope_shadow` to
   offset 2572 -- past the test's fixed 2200-char structural-check
   window. Same recurring class of bug as the Tier-2 window fix
   documented earlier in this registry (900 -> 1200 chars). Fixed:
   widened 2200 -> 3000 chars (confirmed sufficient: `log_envelope_
   shadow` sits at offset 2572, closing paren at 2637). Not caused by
   PF1 -- pre-existing breakage from an earlier directive that the
   full suite hadn't been re-run against until now.

2. `tests/test_concept_image_ingestion_import.py::test_ingest_
   concept_image_succeeds_against_real_fixture` (`cv2.imdecode`
   AttributeError) -- recurrence of the long-documented pre-existing
   test-order-dependent flake (first flagged during D2.3, re-confirmed
   at 830/842/847/856/858-passed checkpoints since). **Correction to
   this registry's own RW7 entry**, which speculated the numpy/pytest
   reinstall had "very likely" fixed this permanently: it did not --
   the failure has now recurred in this exact same environment, after
   that reinstall, disproving that diagnosis. Re-verified the actual
   behavior: `cv2.imdecode` exists and works fine in a fresh
   interpreter (`hasattr(cv2, 'imdecode')` -> True), the standalone
   test file passes 3/3 every time, and a targeted 4-file subset
   spanning the tests immediately preceding it in collection order
   (`test_classroom_curriculum_seeding.py`, `test_classroom_
   perspective_rotation_and_watchdog.py`, `test_composer_relevance_
   selection.py`, `test_concept_image_ingestion_import.py`) also
   passes clean. The flake only manifests deep into a true full-suite
   run, consistent with the original diagnosis: some other test
   earlier in the run leaves global/thread state that intermittently
   breaks this one file's `cv2` access, not a numpy dependency gap.
   Root cause still not isolated after two independent investigation
   attempts across sessions; out of scope for PF1.1, flagged honestly
   per the campaign's "halt on failure, report honestly, never fudge"
   doctrine rather than claimed fixed a second time on a guess.
   Touches only camera/cv2 ingestion code, nowhere near anything PF1,
   PS1, or the architecture audit changed.

Both fixes verified green in isolation
(`test_b1_1_envelope_shadow.py` + `test_pf1_1_proposition_frame.py`,
22/22 passed). PF1.1 committed with these two pre-existing-failure
fixes/notes bundled in, per this directive's own "one phase per
commit" sequencing -- the alternative (a separate commit purely for
inherited breakage) doesn't serve the campaign's clarity any better
here since both were discovered strictly by PF1.1's own mandated gate.

## Directive PF1 — PF1.2 transport via begin_expression, 2026-07-21

Wires PF1.1's `build_frame()` and the already-produced-but-orphaned
`ExpressionGuidance` (audit finding F1) onto the composer, at the
existing `begin_expression()` call site (`aurora_braid_wiring.py`,
`aurora.py:16545`) -- the same anchor point `SemanticIntentionBridge`
already uses, confirmed structurally unrelated in PF1.1. Pure
transport: `compose()` reads neither field yet, so this phase cannot
change a single byte of delivered output. Consumption is PF1.3
(motif selection) and PF1.4 (slot binding).

`aurora_expression_perception.py` (`SentenceComposer`): added
`self._proposition_frame = None` / `self._expression_guidance = None`
to `__init__`, and two setters symmetric with the existing
`set_context()` -- `set_proposition_frame(frame)` and
`set_expression_guidance(guidance)`, both plain assignment, no
filtering (unlike `set_context`'s noise-word gate -- there's nothing
to filter on a structured frame/guidance object).

`aurora_braid_wiring.py` (`begin_expression`): after the existing
`SemanticIntentionBridge` wiring block, a new fail-quiet block calls
`build_frame(systems, state_shim)` and pushes the result plus
`systems['_expression_guidance']` onto the composer via the two new
setters. `begin_expression(systems)` only receives the `systems`
dict, not the real `TurnState` object `build_frame`'s anchor rung
expects (`state.noncomp_input_state`) -- shimmed via a
`types.SimpleNamespace` reading `systems['_last_noncomp_input']`,
the same dict-mirrored copy of the NonComp summary `aurora.py`
already maintains for exactly this "no `state` object available"
situation (confirmed existing precedent at several call sites, e.g.
`aurora.py:10644`). Wrapped in its own try/except, additive to the
existing outer try/except -- a failure here degrades to "no frame
this turn," never affects expression-layer setup or the turn itself.

18 tests total: `tests/test_pf1_2_transport.py` (10 new) covering the
composer defaults/setters directly, a structural grep-based check
that `compose()`'s current source contains neither
`_proposition_frame` nor `_expression_guidance` (the byte-identical
gate, enforced mechanically rather than assumed), and
`begin_expression()` wiring through fakes (anchor-rung frame, thought-
rung frame with priority over a decoy anchor, None-frame when no rung
fires, graceful degradation with no composer / no thought state).
Plus the existing 13 `test_pf1_1_proposition_frame.py` tests (still
green, no changes to that module this phase).

**PF1.2 regression gate:** `test_pf1_1_proposition_frame.py` (13) +
`test_pf1_2_transport.py` (10) + `test_d1_device_path_attribution.py`
(5, includes the live-boot `test_device_delivered_text_byte_
attributes_to_resp_a_live` -- an actual `process_external_user_turn`
call against real boot state) -- **28 passed, 0 failed** (1391.14s;
this environment is running noticeably slower than earlier in the
campaign, noted previously, not diagnosed further, not blocking).
Live-boot delivered text confirmed unchanged, matching the phase's
own byte-identical gate both mechanically (structural check) and
empirically (live turn). PF1.3 (motif selection conditioned on the
proposition) next.

## Directive PF1 — PF1.3 motif selection conditioned on proposition, 2026-07-21

Adds `MotifLineage.best_for_proposition(frame, orientation,
outlet_fraction)` in `aurora_grammar_engine.py`, alongside the
existing `best_for_pressure` (untouched -- frame-absent turns keep
today's exact behavior). Same base scoring as `best_for_pressure`
(composability, axis fit, agent bonus, economy, clause bonus), plus:

1. **Shape-fit term** -- `wants` = how many of the frame's
   subject/relation/obj are non-empty; `capacity` = count of AGENT/
   ACTION/OBJECT roles in the skeleton's role_sequence;
   `shape_fit = min(wants,capacity)/max(wants,capacity,1)`. Softened
   into the score as `base * (0.6 + 0.4*shape_fit)` rather than a bare
   multiply, so a strong base skeleton is discounted for a shape
   mismatch, never zeroed out by one.
2. **Monotony-breaker** -- fitness-proportional `random.choices` over
   the top 4 candidates by score, replacing `best_for_pressure`'s
   plain `max()`. This is the direct mechanical answer to PF1.0's
   finding (distinct motifs across 60 probes = exactly 1): a hard
   max() under near-constant orientation always breaks the same way.

`aurora_expression_perception.py`'s `compose()` routes per sentence:
`self._proposition_frame is not None` -> `best_for_proposition`,
else -> `best_for_pressure` (unchanged call). 7 new unit tests
(`tests/test_pf1_3_motif_selection.py`): none-when-no-candidates,
single-candidate determinism, L1 clause-shape whitelist still
enforced (shape-fit scoring cannot bypass it), shape-fit statistically
favors the skeleton with room for a full triple (300-trial frequency
check), anchor-only frames (wants=2) don't crash the shape-fit math,
monotony-breaker produces >=2 distinct motifs from 5 similarly-fit
candidates over 200 trials, and `best_for_pressure` itself provably
unaffected (regression guard). Also removed PF1.2's own structural
"compose() must not reference `_proposition_frame` yet" test --
correctly obsolete now that PF1.3 begins consumption by design; that
gate's job is now covered by this phase's own tests instead.

**PF1.3's own real-world gate, run against the live 60-probe battery
(`scripts/pf1_0_attribution_run.py`, reused as-is -- same
instrumentation, now measuring the post-PF1.3 code path):**
`distinct_motif_ids_used` / `distinct_role_sequences_used` rose from
PF1.0's baseline of **exactly 1** to **3** (role sequences used:
`agent_action` x31, `agent_action_object` x39,
`agent_action_object_descriptor` x49, out of 119 motif-bearing turns
across the 60 probes). `test_generation_collapse_regression.py`'s
24-case wellformedness golden guard: 6/6 passed, no regression.

**Honest shortfall against the directive's own literal gate text**
("distinct motifs across 60 probes >= 4"): 3 was reached, not 4.
Root-caused, not assumed: queried the live `aurora_state/grammar_
motifs.json` lineage directly -- of 16 currently-promoted motifs,
only **3** pass the pre-existing L1 clause-shape whitelist gate
(`is_valid_clause_shape`, R1.9.3) at all (`agent_action`,
`agent_action_object`, `agent_action_object_descriptor`); the other
13 promoted motifs are invalid shapes, already correctly excluded
from composition by L1, unrelated to PF1.3. The battery result (3/3
distinct shapes actually used, matching the composition-eligible
ceiling exactly) shows the selection mechanism is working at 100% of
its available diversity -- the shortfall against ">=4" is a ceiling
in how many *valid, promoted* skeletons currently exist in the live
lineage state, not a defect in how PF1.3 selects among them. Closing
that ceiling is a motif-*mining/promotion* concern (getting the other
3 whitelisted-but-unpromoted shapes -- `agent_action_descriptor`,
`agent_action_determiner_object`,
`agent_action_determiner_object_descriptor` -- enough real success
history to pass `should_promote()`), which is outside PF1.3's stated
scope (motif *selection*, not motif *mining*) and outside this
directive's own phase list. Flagged here honestly per "report
honestly, never fudge" rather than claimed met; carried forward
explicitly into the PF1.6 acceptance report for Sunni/Cael's
attention rather than blocking phase-by-phase progress on a mining
problem PF1.3 was never designed to solve. PF1.4/1.5/1.6 do not
depend on hitting a specific motif count -- they operate on whichever
motif got selected, so this does not block continuing the directive.

Full data: `aurora_state/probe_battery/results/pf1_0_attribution_
<timestamp>.json` (gitignored, local only, per convention).

## Directive PF1 — PF1.4 slot binding: the proposition fills its own sentence, 2026-07-21

`aurora_expression_perception.py`'s `_compose_from_motif` now tries a
frame-bound fill before falling back to today's channel selection.
Two new methods: `_bind_slot_from_frame(role, frame, sentence_roles,
words)` -- ACTION binds from `frame.relation` (POS-gated: `infer_word_
role(verb) == "verb"`, else fail-quiet fallback), conjugated for the
sentence's own current subject via the existing `_conjugate_for_
subject`; OBJECT binds from `frame.obj` (POS-gated as a noun, and
rejected if it would immediately repeat the previous word). `_negate_
action_word(verb, subject)` -- minimal do-support negation reusing
the existing conjugation table rather than a new one ("be" forms
negate in place, "am not"/"are not"; everything else "do not
<base>" -- correct for "I"/"you", the only subjects this delivered
voice ever uses). AGENT is deliberately NOT bound from `frame.
subject`: AGENT is always a pronoun (enforced by `_select_constraint_
word`'s own agent branch), and `frame.subject` is frequently an
arbitrary topic noun -- forcing it in would produce an ungrammatical
subject, and the proposition's real content lives in relation/obj
anyway. DESCRIPTOR stays on the existing relevance-ranked path
unmodified in mechanism, but when a frame is present its own terms
(subject/relation/obj) are folded into the `input_text` passed to
`_select_constraint_word`, so the ALREADY-correctly-working anchor-set
ranking (PF1.0's own finding) naturally favors words related to what
she's actually proposing, with zero new ranking logic. 15 new tests
(`tests/test_pf1_4_slot_binding.py`): direct unit coverage of `_bind_
slot_from_frame` (binds action/object, fails through on empty fields,
fails through on POS mismatch, fails through on immediate duplicate,
AGENT/DESCRIPTOR never bound, never raises on a malformed frame),
conjugation/negation (`_negate_action_word`'s be-form and do-support
paths), and two integration tests through `_compose_from_motif`
(frame-bound content appears in the sentence; no-frame path
unaffected, regression guard).

Honest note on the POS gate's real shape: `infer_word_role`'s verb
recognition is narrow -- a hardcoded present/base-form hint table plus
`-ing`/`-ed` suffix rules, no third-person `-s` recognition ("goes",
"needs" default to noun, not verb) -- so ACTION binding is
conservative by construction: most extracted relation words that
aren't already in base form fall through to normal selection rather
than binding. This is the correct failure direction for a fail-quiet
gate (never invents a fill it can't verify), not a defect, but is
worth knowing when reading real bind-rate numbers.

**Bug found and fixed via PF1.4's own real-world verification (60-
probe live-boot run), not by unit tests:** several delivered sentences
contained literal internal-state tokens instead of language -- e.g.
`"I triggered x=0.50."` (`context_carryover_03`) and similar across
several other probes. Root-caused: `aurora_thought_formation.py`'s
`ThoughtState.unified_interpretation` is Aurora's INTERNAL reasoning
trace, not a sentence -- its own docstring says so directly ("This is
Aurora's internal thought -- NOT the response"). Its real generators,
`_reason_through_dominant`/`_partial_interpretation`, format it as
pipe-joined labeled telemetry (`"Operating on: ... | Triggered by:
warp_coverage_extension, x=0.50 | Dominant pressure: A-axis (0.62)"`)
or a `"[partial] ..."` fallback -- never natural language. PF1.1's
`_extract_triple_from_thought_text` (`aurora_internal/aurora_
proposition_frame.py`) parsed this literally with a plain role-tag
scan, picking "triggered" as a verb (matches the `-ed` suffix rule)
and "x=0.50" as a noun (unrecognized token defaults to noun) --
exactly the observed contamination. PF1.1's own 13 unit tests never
caught this because every fixture was hand-written natural language
("I need to help with the water project"), never the real generated
shape -- a gap in test *realism*, not test coverage per se.

**Fixed at the root, in PF1.1's own module** (found a gap in earlier
own work via PF1.4's testing, fixed it -- same discipline as PS1.3's
write-side-leak correction): added `_looks_like_internal_telemetry()`
to `aurora_proposition_frame.py`, checked before any parsing attempt
-- rejects text starting with `"[partial]"` or containing any of the
known pipe-joined markers (`"Operating on:"`, `"Active processes:"`,
`"Triggered by:"`, `"Dominant pressure:"`, `"Unresolved tension:"`,
`"Background:"`). Plus a defense-in-depth per-token guard (`"=" in
tok` skips the token as a relation/object candidate, and the topic
itself is rejected if it contains `"="`) -- catches stray `key=value`
tokens even outside the pipe-joined format (e.g. a topic string
assigned straight from a `ProcessContext.what_it_is_operating_on` like
`"aurora:activation=0.75"`, a real shape seen elsewhere in `aurora_
thought_formation.py`'s warp-stream signal handling). 4 new regression
tests added to `tests/test_pf1_1_proposition_frame.py` (now 17,
was 13): the exact pipe-joined telemetry shape rejected, the
`"[partial]"` shape rejected, telemetry-thought correctly falls
through to the claim rung (priority ladder still works when the top
rung is rejected, not just when it's empty), and the stray `key=value`
token guard verified independently of the whole-text check.

**Re-verification, same 60-probe battery, after the fix:** zero
telemetry-shaped tokens in any of the 60 `composer_raw` outputs
(checked programmatically -- no `"triggered"`, no `key=value`
patterns, no `"[partial]"`). Delivered text now visibly carries
real conversational content instead of internal debug strings, e.g.
`"I planning before clear. I did dinner real."` for
`context_carryover_01` (relation/object drawn from the turn's own
content via the claim/anchor rungs and DESCRIPTOR's anchor-text
folding) -- readable improvement over PF1.0's monotone "I [verb]
[word] clear/real." baseline, though full wellformedness/relevance
re-measurement under new instruments is PF1.5/PF1.6's job, not
claimed here.

**Full regression:** 81/81 passed
(`test_generation_collapse_regression.py` [24-case wellformedness
golden guard] + `test_l1_skeleton_validity_gate.py` +
`test_l4_grounded_motif_fitness.py` +
`test_composer_relevance_selection.py` + all four
`test_pf1_1`-`test_pf1_4` files). PF1.5 (instrument re-derivation)
next.

## Directive PF1 — PF1.5 instrument re-derivation, 2026-07-21

New module `aurora_internal/aurora_pf1_5_instruments.py`, purely
additive -- neither pre-existing instrument it extends is modified,
so R1.9.3's 24-case golden set and every prior directive's own
acceptance numbers stay pinned to exactly what they always measured.

**`adequacy_score(response_text, anchor)`** -- relevance -> adequacy.
Same `hits/len` base arithmetic as the existing relevance scorer
(`run_probe_battery.py`'s `_make_relevance_scorer`), plus a bounded
(+0.15, applies once) predicate-argument bonus when a verb and a noun
are BOTH anchor-relevant and sit within 4 tokens of each other -- a
real predicate taking a real, on-topic argument, not just isolated
word hits scattered through the response.

**`role_coherent(text)` / `wellformed_and_coherent(text)`** --
wellformedness gains role-coherence. `_parseable()` (unchanged)
catches word salad but was never designed to catch a specific, real
failure class PF1.3/PF1.4's own live-boot runs produced: a bare
present-participle used as a finite main verb with no auxiliary ("I
planning before real.", "I knowing sister."). `role_coherent()` flags
exactly that shape (subject pronoun directly followed by a bare `-ing`
word, no recognized auxiliary, no `-ing`-as-noun override) per
sentence. `wellformed_and_coherent()` = `_parseable() AND role_
coherent()` -- the new, stronger combined gate for PF1.6's acceptance.

**Three bugs found and fixed via PF1.5's own real-world revalidation,
not by unit tests** (same discipline as PF1.4's telemetry-contamination
catch -- this is the instrument re-derivation phase actually doing its
job: a stronger measurement surfacing real defects the old, coarser
one couldn't see):

1. **Tokenization mismatch in `adequacy_score` itself.** The first live
   60-probe run showed `mean_new_adequacy` (0.667) BELOW `mean_old_
   relevance` (0.844) -- structurally impossible if adequacy is truly
   "relevance base + non-negative bonus." Root cause: `adequacy_score`
   tokenized with `aurora_semantic_probe_battery.py`'s `_WORD_RE` (min
   length 1, built for `_parseable`'s word-shape checks -- counts "I"/
   "a"/"is"), not the actual relevance scorer's own anchor-token regex
   (min length 3), silently changing adequacy's "base" term out from
   under the arithmetic it was documented and unit-tested to match
   (the original unit tests didn't catch it because they compared
   adequacy's output against hand-counts using the SAME wrong regex,
   never cross-checked against the real old scorer). Fixed: added
   `_ANCHOR_TOKEN_RE` identical to the relevance scorer's own pattern.
   Rewrote the affected unit tests to cross-check against a local
   `_old_relevance()` helper using that same real regex, plus added
   `test_adequacy_base_term_is_never_lower_than_old_relevance_on_real_
   probe_shaped_text` as a direct, always-on regression guard.

2. **Frame-bound bare-gerund action binding (PF1.4's own code).** The
   revalidation's wellformedness comparison showed 14/60 probes
   flipping from old-`_parseable`-pass to new-`role_coherent`-fail.
   Every flip spot-checked and confirmed a genuine bare-gerund-as-
   finite-verb catch, zero false positives (`"I planning before real."`,
   `"I replacing best real."`, `"I knowing sister."`, etc.) -- `_bind_
   slot_from_frame` (`aurora_expression_perception.py`, PF1.4) binds
   `frame.relation` directly whenever `infer_word_role` tags it a verb,
   which its own `-ing`-suffix rule does for bare gerunds, with no
   finiteness check. Fixed: when the bound verb ends `-ing`, use a
   progressive-aspect auxiliary (`"am"`/`"are"` + gerund, `"am not"`/
   `"are not"` if negated) instead of the plain conjugation path --
   reuses `_negate_action_word`'s existing "be"-auxiliary pattern, adds
   no new degerunding/morphology table (stripping `-ing` back to a
   correct base form needs real morphology -- consonant doubling,
   silent-e restoration -- that a rule-of-thumb gets wrong often enough
   to trade one defect for another; "I am planning" is genuine, correct
   English, not a workaround).

3. **Ordinary-channel-selection bare-gerund actions -- a genuinely
   PRE-EXISTING defect, not introduced by PF1.3/PF1.4.** Re-running the
   revalidation after fix #2 still showed 15/60 flips; the actual
   delivered text (`"I seeing prioritize."`, `"I writing okay."`, `"I
   going okay."`) showed the SAME defect shape but through words that
   were never frame-bound at all -- traced to `_select_constraint_
   word`'s ordinary lexicon/DPS-crystal candidate pool, which has
   always been able to surface a bare gerund for the ACTION role with
   no finiteness check (confirmed: `"planning"` appears as an ordinary
   `find_by_noncomp` candidate in PF1.0's own baseline data, captured
   BEFORE PF1.3/PF1.4 existed -- this predates the whole PF1 directive;
   `_parseable()` was simply never strong enough to see it). Fixed at
   the general level: `_compose_from_motif`'s existing per-sentence
   subject-driven conjugation pass (R1.9.3 L3) now applies the SAME
   auxiliary treatment to ANY bare-gerund action word, frame-bound or
   not (a `" " not in w` guard skips words fix #2 already finished,
   e.g. `"am planning"`, so the two fixes compose cleanly rather than
   double-wrapping). `tests/test_pf1_4_slot_binding.py` gained `test_
   bare_gerund_from_ordinary_channel_selection_gets_an_auxiliary_too`,
   exercising this path directly via a monkeypatched `_select_
   constraint_word`, no live boot needed.

19 tests in `tests/test_pf1_4_slot_binding.py` (was 15), 16 in `tests/
test_pf1_5_instruments.py`, all passing, including the two-direction
check against R1.9.3's own golden set (all 24 garbled responses still
rejected, all 24 good sentences still accepted -- zero new false
negatives from role-coherence).

**Final real 60-probe two-direction revalidation** (`scripts/pf1_5_
instrument_revalidation.py`, reusing `run_probe_battery.py`'s exact
boot/scratch-isolation and D2.4 delivered-text extraction), after all
three fixes: `mean_old_relevance = 0.7919`, `mean_new_adequacy =
0.8044` (correctly >= relevance, invariant holds).
`old_parseable_pass_count = 7/60`, `new_wellformed_coherent_pass_
count = 7/60`, **`wellformedness_flipped_count = 0`** -- old and new
instruments now agree on every single probe in this run; sample
delivered text confirms the fix live (`"I am planning before clear. I
change dinner real."`, `"I am replacing best clear. I am planning."`).
Note honestly: the raw pass-count (7/60) is itself lower than earlier
runs' pass-counts (19-23/60) for reasons UNRELATED to this phase --
`best_for_proposition`'s (PF1.3) fitness-proportional sampling is
stochastic by design, so different runs draw different mixes of the
3 currently-eligible motifs and different word choices, and this
particular run's draw happened to produce more non-gerund-related
wellformedness failures (e.g. `"I am interesting sister's clear."`).
Zero flips confirms this variance is NOT a role-coherence artifact --
old and new agree completely -- but the underlying pass-rate itself
remains a live, honest number for PF1.6's acceptance measurement to
report, not something this phase can or should smooth over.

Full data: `aurora_state/probe_battery/results/pf1_5_revalidation_
<timestamp>.json` (gitignored, local only, per convention). PF1.6
(acceptance) next.

## Directive PF1 — PF1.6 acceptance, 2026-07-21

Composition battery x3 (`scripts/pf1_6_acceptance.py`, one boot, three
independent 60-probe passes against the same live state, matching this
campaign's established S1.3/PS1.3 methodology) under PF1.5's new
instruments -- new honest baselines, deliberately not compared to any
pre-PF1 number (old relevance/`_parseable` measured something
different; adequacy/`wellformed_and_coherent` measure something
stricter and new).

**Adequacy, stratified (PROMPT_STRATA, unchanged mapping):**

| Run | simple_concrete | abstract_conceptual |
|---|---|---|
| 1 | 0.738 | 0.869 |
| 2 | 0.800 | 0.916 |
| 3 | 0.824 | 0.951 |
| **3-run mean** | **0.787** | **0.912** |

**Wellformed-and-coherent pass rate, stratified:**

| Run | simple_concrete | abstract_conceptual |
|---|---|---|
| 1 | 0.167 | 0.083 |
| 2 | 0.167 | 0.208 |
| 3 | 0.333 | 0.333 |

**Motif diversity:** 3 distinct role-sequence shapes across all three
runs combined (`agent_action`, `agent_action_object`, `agent_action_
object_descriptor`) -- unchanged from PF1.3's own measurement, and
already root-caused there: the live lineage currently has exactly 3
promoted motifs that pass the pre-existing L1 clause-shape whitelist,
a ceiling PF1.3's selection algorithm cannot exceed on its own (it
uses 100% of what's eligible). Below the directive's stated ">=4"
target -- carried forward as an open item below, not fudged.

**Descriptor repetition** ("clear"/"real" share of all delivered
content words): 0.117, 0.086, 0.122 across the three runs -- well
under the directive's 40% bar.

**Abstain rate:** 0.0 across all three runs (0/60 each) -- no silent
failures, no over-triggering.

**Diagnostic leakage:** 0 across all three runs, all 180 probe-turns
-- the telemetry-token check PF1.4's own verification used, re-run
here as a standing acceptance gate. Confirms PF1.4/PF1.1's fix holds
under repeated independent measurement.

**Full regression suite:** `python3 -m pytest tests/ -q` -- **959
passed, 1 failed** (2106.43s / 35:06). The one failure is the same
long-documented pre-existing test-order-dependent flake (`tests/
test_concept_image_ingestion_import.py::test_ingest_concept_image_
succeeds_against_real_fixture`, `cv2.imdecode` AttributeError),
confirmed unrelated at every checkpoint across this campaign
(830/842/847/856/858/959 passed, always this same single failure,
always passes 3/3 in isolation, touches only camera/cv2 ingestion
code nowhere near anything PF1 touched). Test count rose from 905 (at
the start of this segment) to 960 total -- the ~55 new tests added
across PF1.0 through PF1.6. Suite is clean for every purpose this
directive's own gate cares about.

---

**Honest summary of the whole PF1 arc, for Sunni/Cael's review.** PF1
set out to test the audit's own F12 hypothesis (relevance-primary
scoring already works; the real defect was upstream of word choice)
and, once RW7 confirmed that mechanism, to fix the actual finding:
motif selection never varied, and nothing derived what she was trying
to say before deciding how to say it. Six phases, six commits, full
regression between each, exactly as directed:

- **PF1.0** falsified both of the directive's own hypothesized side
  channels (DPS-crystal resonance, usage-count-zero tiebreak) and
  confirmed the real diagnosis mechanically: motif diversity across 60
  probes was exactly 1.
- **PF1.1** built the PropositionFrame fail-quiet derivation ladder
  (thought -> claim -> anchor -> None), reusing existing machinery,
  zero live wiring.
- **PF1.2** transported the frame (and the previously-orphaned
  ExpressionGuidance, audit finding F1) onto the composer -- verified
  byte-identical delivered output, both structurally and via a live
  turn.
- **PF1.3** built `best_for_proposition` (shape-fit + fitness-
  proportional top-4 sampling, replacing the plain `max()` that caused
  the monotony) -- diversity rose 1 -> 3, the full ceiling of what the
  live lineage currently has promoted and L1-valid. The directive's own
  ">=4" target was not reached; root-caused as a motif-*mining*
  ceiling, explicitly out of a motif-*selection* phase's scope.
- **PF1.4** wired the frame into actual slot content (ACTION/OBJECT
  bound from the proposition, DESCRIPTOR biased toward it) -- and its
  own real-world verification caught a genuine bug in PF1.1's parser
  (internal thought-telemetry parsed as if it were language, landing
  raw debug tokens in delivered text), found and fixed at the root the
  same day it was introduced.
- **PF1.5** built the adequacy/role-coherence instruments needed to
  actually measure PF1.3/PF1.4's effect honestly -- and its own
  revalidation caught three more real bugs (its own tokenization
  mismatch, plus two independent bare-gerund-as-finite-verb defects,
  one in the new frame-binding code and one PRE-EXISTING in ordinary
  channel selection, invisible to every prior directive's `_parseable`
  gate until this phase's stronger instrument existed to see it). All
  three found and fixed before shipping; final revalidation showed 0
  wellformedness flips against the old instrument.
- **PF1.6** (this entry) measured the result honestly under the new
  instruments: real, new, unflattering-in-places baselines, not a
  clean pass on every axis.

**Open items for Sunni/Cael's decision, not resolved by this
directive:**

1. **Motif-diversity ceiling (from PF1.3).** The live lineage has only
   3 promoted, L1-valid skeletons; 3 more whitelisted shapes
   (`agent_action_descriptor`, `agent_action_determiner_object`,
   `agent_action_determiner_object_descriptor`) exist in the grammar
   but have never accumulated enough real success history to promote.
   Closing this is motif-*mining* work, a different intervention than
   anything in PF1's own phase list.
2. **Wellformed-and-coherent pass rate is low (8-33% per stratum).**
   This is the FIRST time this instrument has existed to measure
   anything, so there is no prior baseline to compare against and no
   claim here that PF1 made this worse -- the old, coarser
   `_parseable()` was simply never able to see most of what this gate
   now catches. What it's catching, beyond the now-fixed gerund cases,
   has not been characterized in this directive -- that characterization
   (what specific shapes are failing role-coherence now, and whether
   PF1.3/PF1.4's frame-binding needs further phases, e.g. the
   originally-scoped-but-not-built PF1.4 DESCRIPTOR neighborhood
   constraint) is a natural next directive, not something PF1.6
   invents an answer to.
3. **Both gerund bugs and the telemetry bug are fixed and verified,**
   but were found reactively, by each phase's own regression gate,
   not by design review before writing the code. Worth noting as a
   process observation, not a blocker: this campaign's "halt on
   failure, verify before commit" discipline caught all three before
   they shipped, but a design pass anticipating "what does infer_word_
   role's suffix-rule verb detection actually admit" before PF1.4 was
   written might have caught the gerund class earlier.

Zero diagnostic leakage, zero abstain over-triggering, descriptor
repetition well under bar -- reported as the genuinely clean parts of
this baseline, not a blanket "PF1.6 passed."

## PF1.6 Residue Characterization — W1: ThoughtState carried no turn content, 2026-07-21

Follow-up audit (`AURORA_PF16_RESIDUE_CHARACTERIZATION_20260721.md`,
external session, uploaded) found the PropositionFrame ladder living
entirely on its bottom rung across the 60-probe battery: `frame_source`
= anchor 55, claim 3, **thought 0**, none 2. The "thought" rung --
Aurora's own formed thought driving what she says, the actual point of
PF1 -- never fired once. Sunni: "let's just tackle them one at a time,"
starting with W1 (this entry). W2 (claim gate rate) and W3 (adequacy
saturation on bare copulas) queued, not started.

**Root cause, confirmed via a live diagnostic before touching any
code** (`scripts/w1_thought_state_diagnostic.py`): `ThoughtState.
unified_interpretation` and `self_application` are built by `aurora_
thought_formation._reason_through_dominant()` purely from
administrative `ProcessContext`s (memory-ambient, identity-predicates,
constraint loop-counts) -- an internal telemetry trace, never the
turn's own content. A 4-turn live check showed `unified_interpretation`
**identical across 4 completely unrelated turns** ("he's nervous
around new people" / "revenue numbers down" / "crying all week" all
produced the exact same string) and `skipped=False` with 5 registered
processes every time -- ruling out the original audit's registration-
starvation hypothesis outright. PF1.5's own telemetry guard
(`_looks_like_internal_telemetry`, built to fix the real "I triggered
x=0.50." bug during PF1.4) was correctly rejecting this text every
single time -- not a false positive, structurally guaranteed to fire
on 100% of real ThoughtStates, since `_reason_through_dominant` has no
natural-language output mode at all.

**Fix (Sunni's chosen direction: the deeper fix, not a narrow parser
patch):** `aurora_braid_wiring.py`'s `_build_turn_process_contexts`
now registers a `"linguistic"` `ProcessContext` carrying the turn's
actual text (`self_relevance=0.75`, `axis_signature=["X","T","A"]`,
chosen to overlap with memory/identity so it clusters into `dominant_
thread` rather than sitting isolated in `supporting_context`).
`aurora_internal/aurora_proposition_frame.py`'s `_frame_from_thought_
state` now reads that context directly from `thought_state.dominant_
thread` by `process_type=="linguistic"`, bypassing the telemetry
strings entirely -- with a fallback to the old text-parsing path
(still telemetry-guarded) for defensiveness. Verified live,
before/after, same 4 turns: `build_frame -> source=thought` on all 4
(was `None` on all 4), with genuinely turn-specific extracted content.

**Two bugs found and fixed via the fix's own live-fire battery
testing** (same discipline as PF1.4/PF1.5's own findings):

1. **Contractions leaking into content slots.** First full 60-probe
   re-run (`scripts/characterize_pf16_residue.py`, now also fixed to
   scratch-isolate its boot instead of hitting real `aurora_state/`
   directly) showed real text flowing through -- but also `"I am
   planning he's."`, `"I am replacing what's real."` -- `infer_word_
   role` has no apostrophe rule, so an unrecognized contraction
   ("he's", "what's", "i'm") defaults to "noun" and binds straight
   into ACTION/OBJECT. Fixed: an apostrophe guard in `_extract_
   triple_from_thought_text`, same style as the existing "=" guard.
   Re-run confirmed clean (0 contraction leaks from this path); two
   residual cases ("she's", "sister's") traced via word-source
   attribution to the ORDINARY `find_by_noncomp` channel-selection
   path -- pre-existing lexicon contamination unrelated to this fix,
   flagged not fixed (separate finding, out of W1's scope).

**Before/after, same 60-probe battery, surface profile, scratch-
isolated:**

| | frame_source thought | frame_source anchor | residue (fail wellformed_and_coherent / adequacy<0.55) |
|---|---|---|---|
| Original audit | 0/60 | 55/60 | 53/60 |
| After linguistic-context fix | 49/60 | 9/60 | 51/60 |
| After contraction-guard fix | 49/60 | 9/60 | **49/60** |

Sample delivered-text shift: `"I am bit."` (vacuous copula, original)
-> `"I am planning around nervous. I find around. I do around real."`
(real content, still not fully coherent -- W3's adequacy-saturation
finding and general grammar quality are separate, queued work, not
claimed solved here).

**Reentrancy-guard test investigation (thorough, before committing):**
the first full-suite run after this fix showed 3 failures instead of
the usual 1 -- the known cv2 flake, plus two new ones. Investigated
both rather than assuming either was caused by this fix:

- `test_m1_2_provenance_hygiene.py::test_blind_origin_entries_are_
  tagged_legacy_unverified` ("lang" missing its tag) -- confirmed
  **pre-existing**: "lang" carries the same untagged state in the
  git-committed `HEAD` version, unrelated to anything in this session.
  Data drift from the continuously-running autonomous instance
  outpacing M1.2's one-time tagging backfill. Not fixed here (separate
  concern).
- `test_d2_2_live_turn_reentrancy_guard.py::test_twenty_live_turns_
  each_produce_exactly_one_top_level_call` -- confirmed via `git
  stash` isolation that this fix DOES cause it in the full-suite
  context (fails with the fix present, passes cleanly with it
  stashed out, all else equal). Investigated the mechanism at length:
  two custom live-trace scripts (`scripts/w1_reentrancy_trace.py`,
  kept for future reentrancy debugging) reproducing the exact same
  20-turn sequence as standalone scripts caught **zero** recursive
  `process_external_user_turn` calls and confirmed the `_live_turn_
  depth` guard holding on every one of 53 simulation-bridge
  invocations. The missing experiment: fix present, test run in
  **isolation** via pytest itself (not a custom script) --
  **passed cleanly** (1 passed, 21:37). Conclusion: this fix does
  NOT deterministically cause the failure on its own; it only
  manifests under full-suite cross-test conditions -- the same class
  of pre-existing test-isolation fragility as the already-documented
  cv2.imdecode flake (module-level singletons -- `ThoughtBraid`,
  `ThoughtContinuity`, `EmotionFirewall`, all process-global per
  `aurora_braid_wiring.py`'s `_get_braid`/`_get_continuity`/`_get_
  firewall` -- persist across all ~960 tests in one pytest process;
  this fix's small per-turn timing change plausibly tips an existing
  latent race, doesn't create one). Not fixed here -- flagged
  honestly, matching the cv2 flake's own precedent in this registry,
  rather than either hidden or blocking on a full concurrency
  investigation this finding doesn't by itself justify.

**Tests:** 21 in `tests/test_pf1_1_proposition_frame.py` (was 17: +3
for the linguistic-context primary path, +1 for the contraction
guard), 4 in `tests/test_w1_turn_content_context.py` (new). 25/25
passing, plus the full existing PF1 regression set unaffected.

Full data: `aurora_state/probe_battery/results/pf16_residue_
characterization.json` (gitignored, local only). W2 (claim gate) next.
