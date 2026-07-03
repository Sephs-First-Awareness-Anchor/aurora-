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

POSSIBILITY-SELVES subsystem is now COMPLETE end-to-end: birth -> assess -> bridge
(provoke) -> durable works/doesn't cheat-code -> dream residence -> dialogue ->
feedback split -> persistence. She meets Ember/Wane/Riven only in dreams; they
influence her only by what they make her re-encounter; her own machinery decides every
outcome; what she earns feeds her growth; they persist as distinct continuous beings.
