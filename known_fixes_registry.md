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

**Recommended fix order (not yet ratified, not yet implemented):**
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
