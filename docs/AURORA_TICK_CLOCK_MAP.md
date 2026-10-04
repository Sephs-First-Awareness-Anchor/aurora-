# Aurora Tick Clock Map (v10)

Authors: Sunni (Sir) Morningstar and Cael Devo

Status: design survey. Nothing in her was changed to produce this. Call sites are from a static read of
`aurora.py` and the modules named; per-turn counts are measurements from live surface-profile sessions.
"Decided" means Sir said so. "Proposed" means mine, for the directive to accept or change.

---

## 0. Progress

**v10: Sir's four binding decisions, built and checked live.**
1. **One finite recovery capacity (D7).** Rest creates one capacity that coherence recovery and consolidation both draw
   from, allocated by their relative unresolved need. No fixed percentage; no free repayment. Section 6.
2. **Sediment is never dilated (D8).** It ages by elapsed time only. Core dilation decides how many internal processes
   may operate on it in a span; operations alter it and cost. `step_sediment_dilation` and `tick(dilate=)` are gone.
3. **Genealogy stays event-generated (D9).** Time alone creates no genealogical event. No wall-clock lineage generator.
4. **Replays are internal (D10).** Exempt from entropy's conversational repeat penalty; still processed in full.

Checked live on the real system (surface profile, injected clock, throwaway state): with no debt, recovery 0.4289 =
the expected `0.5 * (1 - 0.85 ** 12)`; with recovery complete, recovery 0 and all of the capacity (0.1025, 68 lattice
steps) to consolidation; the sediment tick was 12.0 at governor dilation 3,000 AND 10,000,000 (core passes 1 and 8):
the governor changes how much runs, never how old sediment is; genealogy write-path calls over all the idle rest and
core consolidation: 0, against 81 from one real turn (the control that proves the spy sees genealogy); six internal
replays left entropy untouched while six identical replays without the marker took coherence 0.9 -> 0.4 (novelty 1.0 ->
0.885, vitality pressure 0.00001 -> 0.2115, stagnation 0 -> 0.1), and the internal replays still moved the dimensional,
lattice and sediment subsystems and returned responses; the first turn after a rest ran no consolidation. After a
wearing conversation the live rest went coherence 0.974 -> 0.976 (one 5-minute close, queue 6 -> 4) -> 0.990 (an hour,
queue 0) -> 1.000 (five hours), backlog 17.5 -> 0 by the end of a long night.
Tests: the 8 files that encode these rules pass together (348), the 2 new decision files (27), and the stub gateway in
`test_zip_directed_training_fitness_gate` was brought to the real `receive(..., metadata=)` signature (a strict stub made the
trainer's boundary handler swallow the replay silently: a real regression of this round, caught by the regression run).

**Regression, on the final code (test files: 369).** Passing on the final code: 107 files. Passing earlier on code these changes cannot reach (recorded before this round, file does not touch a changed symbol): 191. Failing or collecting nothing: 30, of which 30 give the identical result on the pristine upload (pre-existing) and 0 are worse than pristine. No verdict yet (slow boot-based files not run to completion): 41. Unverified: b1_1_envelope_shadow, comm_credit_phase_g_live_wiring, comm_credit_phase_h_corpus_bridge, communication_architecture_repair_directive, communication_integrity_repair, conversation_desktop, crest_compression_placeholder_guard, d1_device_path_attribution, d2_2_live_turn_reentrancy_guard, d2_condition2_abstain_sanity, dmm_thought_intent_derivation, dream_as_new_experience, dream_trainer_genealogy_wiring, evolution_chamber_live_driveshaft, evolution_hook_override_none_handling, governance_liveness, ivm_lattice_live_driveshaft, m1_1a_relation_pairs, modulation_event_representational_ref, native_surface_projection_scope_reconciliation, p1_track_cp_contradiction, p2_3_stance_composer_wiring, praxis_same_device_loop, rcec_closed_loop_orchestrator, rcec_state_isolation_and_lifecycle, reflective_introspection_misrouting_live, representational_consequence_binding, representational_live_propagation, representational_restart_replay, runtime_lineage_connection, rw4_relation_to_self, rw5_boot_parity, rw6c_track1_wiring, sedimemory_d2_625, sedimemory_representational_ref, semantic_bridge_live_state, zip_active_turn_state_frame_source, zip_directed_training_fitness_gate, zip_gap_research_router, zip_pipeline_learning_oets_promotion, zip_semantic_intention_reset.


- `aurora_internal/aurora_metabolic_clock.py`: `MetabolicClock` with the turn gate, deferral of a due tick to
  turn close (elapsed time counted), background close, per-step fault isolation, and persistence of the last
  close in `state_dir/metabolic_clock.json` (so it works on the phone, which has no persistence calls of its own).
- The outermost turn entry `process_external_user_turn` is gated (decorator; signature preserved; a systems
  dict booted without a clock runs as before).
- Sediment is the first clock step. The live turn no longer calls `_sedi.tick(1.0)` when the clock drives it.
- `SediMemory.tick` advances by the elapsed time only. (v9 made it read the governor's real API; v10, D8, removed that:
  sediment is never dilated.)
- `AURORA_TICK_SECONDS` overrides the 300 s default.
- Live check on an injected clock: six turns inside one tick made zero sediment ticks; a tick that came due
  mid-turn was refused, then closed once after the turn with `delta_t = 1.733` (the time inside the turn counted);
  the close took 1.7 ms.

**Done (step 3): entropy split.**
- `EntropicPressure.register_input()` is the EVENT half: a new input boosts novelty and relieves stagnation; a
  repeat fades novelty, grows stagnation and costs coherence. `EntropicPressure.erode(operating_ticks)` is the
  METABOLIC half: coherence decay, alignment drift, novelty fading, stagnation growth. `apply()` is unchanged
  (the heartbeat still uses it).
- Erosion is charged per OPERATING tick, not per wall-clock tick. The clock records which tick-slots had a turn
  in them; a tick without one is a resting tick and does not erode her. Without that, an 8-hour gap is 96 ticks of
  decay (1.34 of coherence) and wipes her. Steps read `clock.span`: `operating_ticks`, `rest_ticks`, `turns`.
- Live, on an injected clock: three turns left coherence at exactly 1.000; an 8-hour idle close aged sediment by
  96 ticks and left coherence and novelty untouched; the first turn back was normal.
- Rest ticks are where the rest economy (step 6) will restore her. Until then they are neutral.

**Done: one registration per input.** The live turn synthesizes each input twice by design (`gateway.receive` with
the raw text, then `_run_reasoning_pipeline`'s own `gw._synthesize` with recall-enriched text and the dual-strata
evidence). Both reached entropy, so a repeat cost twice the penalty (about 0.2 coherence). The second synthesis is
now marked `input_already_registered` in its own evidence and the engine skips registering it. Live: each repeated
input registers once (`+1`, a cost of exactly `REPETITION_PENALTY`).

**Step 4 (lattice, chamber, DER): findings, one decision, no code.**
- **Chamber: no change.** It is already time-gated: `now - last_chamber_tick >= governor.recommended_sleep(...)`.
  It is metabolic already, and moving it would discard the governor's logic.
- **Lattice: measured, left as is.** A tick costs 3 to 5 ms (no speed to gain by moving it), and its dynamics are slow
  (existence velocity 0.629 -> 0.426 over 40 steps). The question is cadence, not cost: the original heartbeat ticked
  about once a second, which is about 300 steps per 5-minute tick, orders of magnitude more than today's one step per
  turn. Open decision 11.
- **DER: cannot take `delta_t` directly.** Its decay is `energies *= (1 - current_decay * dt)` with `base_decay_rate`
  0.15, designed for `dt` near 1. A night at `dt = 96` would give a factor of `1 - 14.4` (negative energy). Its presence
  monitor also compares REAL elapsed seconds against `dt`. DER ticking comes with the rest ledger (step 6), because
  turning decay on without recovery would only drain her.
- **The surface/core cost asymmetry already exists in her physics.** `ToroidalVertexSystem.tick(dt, level)` charges
  `T_COST_MULTIPLIER[level]`: SURFACE 1x, SHALLOW 2x, MODERATE 4x, DEEP 8x, and the docstring says CORE ticks cost 32x
  a SURFACE tick. That is the natural cost model for dilated core time in the rest ledger.

**Done (step 4): the Dimensional Energy Regulator and the lattice.**
- DER (`aurora_dimensional_systems.py`): `tick(dt, actual_dt=None)`. Decay is `(1 - decay) ** dt`; dispersal scales
  with `dt` (one hop per elapsed tick, bounded at 64; it ignored `dt` before); curiosity injections scale with `dt`
  (about one per ten ticks). Identical at `dt = 1`. `actual_dt` lets the presence monitor compare in the same unit.
  On the clock it dissipates on OPERATING ticks only; resting restores (step 6).
- Lattice (`aurora_internal/aurora_metabolic_steps.py`): `tick_seconds / 1 s` steps per tick (300 by default) at
  the CORE level, preemptible between steps (a turn arriving asks the step to stop; the remainder is carried as
  debt, itself bounded to one close's worth), with a 5 s time budget per close. The per-turn lattice step is KEPT
  (it couples node admission to a step; removing it would leave the constraint field stale between closes). The
  fast internal steps are added on the clock.
- All four steps now live in `aurora_metabolic_steps.py`: sediment, entropy, der, lattice.
- Measured live: 480 lattice steps took 2.33 s (about 5 ms each). Node energy was not eroded (22.0 -> 24.947 with
  three new nodes). The lattice settled between closes (existence velocity 1.0171 -> 0.0002). CORE-level T-energy
  spent went 6.75 -> 146.1: that is the internal cost the rest ledger will draw from. A turn arriving during a
  background close took a normal 2.3 s; the lattice stopped after 30 steps and carried 370 as debt.

**Done (step 6): the rest ledger. She wakes already consolidated and rested.**
- Currency: coherence, because it is what operating actually wears (entropy erodes it per operating tick) and the
  understanding contract's N-cost is `1 - coherence`, so "gaining N" is relief of that cost. The Dimensional Energy
  Regulator is NOT the currency: it is injected on every turn (about +2.5 per turn) and capped at its 25.0 budget, so
  after any conversation it sits near full and a rest would have no gap to restore.
- Gain: geometric, `gap * (1 - (1 - r) ** rest_ticks)`: saturates at the gap, composes, never exceeds full. The
  resting rate `r` is the Dimensional Energy Regulator's own rate (0.15), the rate at which it wears, so the system's
  restoring rate equals its wearing rate and no constant is introduced.
- SUPERSEDED in v10 (D7): this section once capped what consolidation could spend at what she keeps (`KEEP_FRACTION = 0.5`,
  a judgment, not derived) and gave it a free repayment on top. Both are gone: one finite capacity, shared by need.
- Consolidation is demand-driven: what operating produced, not how long she rests. Core time is 32x denser, so one
  operating tick needs 300 / 32 core steps, which prices consolidating a tick at exactly what operating it wore
  (0.014 each). She pays for what she did and can always afford it.
- The lattice's fast core steps ARE the consolidation, run only during rest, paid before they run, preemptible.
  Dreams and any other job plug into the same ledger when they exist in-process (dream evolution is deferred to the
  subsurface runtime in the surface profile).
- The idle heartbeat (`MetabolicClock.start_heartbeat`): closes due ticks while she is idle, never mid-turn. Without
  it a rest would be credited at the next turn's exit, AFTER her first reply back. Started at boot, stopped in shutdown.
- (v9 accounting, kept as history.) Live, real time, no help: after a wearing conversation the heartbeat alone took coherence 0.562 -> 0.771 in 30 s
  (6 s tick); on the injected clock she went 0.386 -> 0.860 (hour 1: gained 0.527, spent 0.052, kept 0.475) ->
  0.980 -> 1.000 (N-cost 0.000), owing nothing, first turn back 1.9 s.

**Regression: what was and was not run (Sir called the testing off).** The rerun set was 120 files: every previously recorded
non-pass, every test that references a symbol changed this round, and the 2 new decision files. Results: the 31 fast non-pass
files give the IDENTICAL result on pristine and on this copy (their failures are pre-existing, none are from this work);
`test_zip_directed_training_fitness_gate` passes 7 here against 6 passed and 1 failed on pristine. NO VERDICT on these slow
boot-based files, which exceeded the 250 to 285 s single-call cap: `governance_liveness`, `p1_track_cp_contradiction`,
`rcec_closed_loop_orchestrator`, `rcec_state_isolation_and_lifecycle`, `communication_integrity_repair`,
`d2_2_live_turn_reentrancy_guard`, `comm_credit_phase_g_live_wiring`; and 31 further files that only boot the system were not
rerun this round. The live end-to-end run above exercised boot, a conversation, rest closes and replays on the final code.

**Provenance.** Twice, work was written in response attempts that were discarded and not remembered, while the files stayed
on disk. First (step 5): the contract split, the governor step, the ledger's repayment and carry, the clock's wall-clock
hardening and their tests; reviewed rather than trusted, and the rest found and fixed by testing it (the `CLOCK_BOOTTIME`
change, the ledger caps, the randomized property tests). Second (this round, after Sir's four decisions): two test files
(decisions 3 and 4), progress-log claims ("e2e 20/20 PASS") and a partial regression file. Those claims were NOT relied on:
the tests were read and run, the live verification above was re-run, and the partial regression was checked (separately, my own parallel runner had a duplicated `-q` that hid
pytest's summary line and mislabeled 71 results as timeouts; those were discarded and the runner fixed). The source changes themselves
(`aurora_rest_ledger.py`, `aurora_metabolic_steps.py`, `aurora_sedimemory.py`, `aurora_consciousness_engine.py`,
`aurora_dream_trainer.py`, a comment in `aurora.py`) are this round's, written and checked in the open.

**Found along the way.**
- DER (the Dimensional Energy Regulator) is NOT live: `DimensionalSystems.tick` is only reached from the uncalled heartbeat,
  so the energy pool is static in a live session. The rest economy needs DER ticking as a clock step.
  `DER.tick` also measures real elapsed time against `dt`, so it should be called with the real elapsed seconds.
- Sediment has a second, space-driven path: `_force_compress` at deposit when a basin is at capacity (about 18
  compressions of ~64 fragments in one turn). It does not depend on time. With fewer ticks, fragments mature less
  between deposits, so more of the culling will be forced compaction. Recall of a taught fact held across it.

## 1. Decided

**Two clocks.** The event clock (the turn: perceive, understand the message, answer) and the metabolic
clock (the tick: a fixed span of real time, default 5 minutes).

- **Rule 1. No mid-turn close-outs.** Nothing consolidates while a turn is in flight. If a tick boundary
  passes during a turn, the tick waits for the turn to close and the elapsed time still counts.
- **Rule 2. The turn answers at turn speed.** Perception and response never wait for a tick.
- **D1. Understanding ticks on its own clock**, as its variation between surface and core. Confirmed:
  surface understanding goes with the exchange; core understanding is the deeper variant (section 5).
- **D1b. The core processes faster than the surface.** Core time runs on a dilated clock, many core ticks
  per surface tick. (Correction to v2, which had the core slow. What is slow is deep memory's decay, its
  persistence. Processing speed is a different thing.)
- **D2. Thoughts stay as they are.** The per-turn discharge on a completed Thought is unchanged.
- **D3. Rest economy.** (Revised by D7.) When she is not operating, rest repays what operating wore, and consolidation
  (the lattice, core Understanding, dreams when in-process) is paid out of that same rest. She wakes rested and
  consolidated. (Built: section 6.)
- **D5. The lattice is an internal process, so it processes fast.** It runs on the core clock, many steps per
  surface tick, not one per message.
- **D6. The Dimensional Energy Regulator is not linear in time.** Its decay and dispersal are geometric in `dt`,
  `(1 - rate) ** dt`: identical to the old step at `dt = 1`, never negative, and composable, so any span is safe.
  The principle behind D5 and D6: internal processes use exact, stable integration so they can take whatever time
  the clock gives them.
- **D7. One finite recovery capacity (Sir's decision, v10).** Rest creates ONE finite capacity; coherence recovery and
  consolidation both draw from it, allocated by their relative unresolved need. No debt: all of it restores her. Recovery
  complete and debt left: all of it goes to consolidation. Both owed: their current state sets the share. Consolidation is
  paid during the rest, so there is no wake-up cost, and there is no fixed percentage and no free repayment.
- **D8. Sediment is never dilated (Sir's decision, v10).** Sediment evolves by metabolic/wall elapsed time. Core dilation
  determines how many internal processes can operate on sediment in a span; operations performed on it may alter it and
  incur cost; faster thinking does not make sediment older.
- **D9. Genealogy stays causally generated (Sir's decision, v10).** Time passing alone creates no genealogical event or
  ancestry. Existing time-dependent maturation, persistence or decay is allowed only where it already follows from genealogy's
  own physics; there is no wall-clock lineage generator. (The deferred core Understanding records nothing in genealogy: the
  event is written at surface time by `run_reflection_cycle`.)
- **D10. Training and dream replays are internal (Sir's decision, v10).** They are exempt from the external/conversational
  repeat penalty; they still incur their processing cost and are for the systems that own internal rehearsal to age.
- **D4. Operating means surface.** If it is not surface it is internal. Dreaming is not operating, so the rest
  gain keeps accruing while she dreams, and internal work has no environmental cost to pay: its only cost is the
  internal N in the ledger.

---

## 2. Today: what advances per message

| # | Clock | Call site | Notes | Proposed |
|---|-------|-----------|-------|----------|
| 1 | Sediment aging | `aurora.py:26219` `_sedi.tick(1.0)` | `SediMemory.tick` already takes `delta_t`; live passes a constant 1.0 | Metabolic: `delta_t = elapsed / tick_length` |
| 2 | Entropy erosion | `ConsciousnessEngine.process()` -> `entropy.apply()` per thought | 2 per turn; decay is per call | Split: repetition/novelty stays an event; decay becomes metabolic |
| 3 | Earned coherence | `recalibrate_salience` in the Understanding cascade | fires only on a reconciled turn | Understanding's clock (D1) |
| 4 | Lattice | `aurora.py:35477` `_lattice_live.tick()` | one per turn | Metabolic |
| 5 | Evolution chamber | `aurora.py:35531` `_chamber_live.tick()` | one per turn | Metabolic |
| 6 | Attention engine | `aurora.py:34687` `_ae_pt.tick(turn_tick, ...)` | indexed by the turn counter | Event |
| 7 | Geological baseline | `aurora.py:36622` `_gb_pt.tick(...)` | by its boot message; confirm the class | Metabolic (confirm) |
| 8 | Surface dispatcher | `aurora.py:24997` `_sd.tick(...)` | forwards evidence to the subsurface | Event |
| 9 | Intake accountant | `aurora.py:33412` `accountant.tick()` | confirm what it meters | Needs a look |
| 10 | Genealogy tick count | increments per `observe()` | about 14.5 per turn | Keep observation-indexed |
| 11 | Understanding `time_index` | the contract's T axis | per turn | Event |
| 12 | Identity field | injections on input; discharge per completed Thought and per Understanding | | Thought discharge: unchanged (D2). Understanding discharge: with D1 |
| 13 | Tensor downward pass | per Understanding cascade, 0.05 step | | Understanding's clock (D1) |
| 14 | Emotional rebase | `update_emotional_state`, once per turn | driven by axis activation | Event |

## 3. Already on a wall clock

Concurrent with turns today, which is why Rule 1 needs a real guard: ThoughtBraid (2 s), ConnectivityMonitor
(30 s), AutonomyEngine loop (5 to 10 s), the working-memory surface window (`WINDOW_SECONDS = 600`, i.e. two
ticks), and the desktop-only `ConsciousnessEngine.tick()` heartbeat the live path never calls.

## 4. Where the turn-close boundary goes

One choke point at the outermost turn entry. On entry: set `turn_in_flight`. On exit, after the reply is
delivered and the turn's own bookkeeping is done: clear it, then `clock.close_if_due()`. An idle timer only
calls `close_if_due()` while `turn_in_flight` is false. `close_if_due()` applies the metabolic steps once with
`delta_t = elapsed / tick_length` and keeps the remainder. Needs an injectable time source (fast-forward in
tests) and a persisted `last_tick_close` (the phone bridge currently has no persistence calls).

---

## 5. Understanding's own clock (D1, D1b): BUILT
Understanding exists as a surface variant and a core variant on two clocks.
| Variant | Clock | What it does |
|---------|-------|--------------|
| **Surface** | with the exchange | `run_reflection_cycle`: the genealogy `understanding` event, pressure discharge, salience recalibration, the tensor downward pass, prediction priors, the surface write on unresolved tension |
| **Core** | rest, on the core clock | `process_core_queue`: the geological write (B/A strata), then identity shaped by what the strata now hold, `passes` times |
**Seam.** The last line of `_trigger_downward_cascade`. With a clock attached the contract's `core_deferred` is True:
the deep half is queued (`core_queue` in the contract's own saved state, bounded at 32; a full queue runs the oldest
rather than losing a memory) and runs during rest. With no clock attached both halves run inline, exactly as before.
**Paid, preemptible.** `afford(passes)` is asked before each item, `pay(passes)` after, `should_stop()` between items,
so it never runs unpaid and a turn arriving never waits. What it cannot afford stays queued. The queue persists across
a clean shutdown and across a kill (checked live).
**Speed.** `step_governor` feeds the `TimeDilationGovernor` real signals (fitness = coherence; variance and trend from
its own history; error rate from failed steps). `core_passes` = its normalized factor, rounded, bounded at 8
(`CORE_MAX_PASSES`); each pass costs one core tick. Fast when stable, slower when fragile, brake on collapse.
**Speed versus persistence.** How fast the core PROCESSES (passes) is separate from how long deep memory LASTS (each
basin's own `tick_rate`; the A stratum's 0.0001), which a time multiplier does not change.
**Sediment and the governor (D8).** Sediment is never dilated, by any governor. It ages by the time that actually elapsed
(`step_sediment` -> `SediMemory.tick(delta_t)`; the `dilate` keyword and `step_sediment_dilation` are removed, and `tick`
ignores any attached governor). Why: attaching the real governor would have scaled her real-time aging (measured with three
understandings: deep mass 30 -> 41 in ONE tick at maximum dilation, 47 over a night), manufacturing depth she did not earn.
What a faster core changes is how many operations may act on sediment in a span (core Understanding's geological writes);
those alter it, and cost. (The v9 design let a paid extra compression time through; Sir decided against it.)
---
## 6. Rest economy (D3, D7): BUILT
**Currency: wear, read in one place.** The ledger settles in WEAR (`recoverable_wear` / `restore_wear` in
`aurora_metabolic_steps.py`: today the gap to full coherence, because operating erodes it). It is NOT N: N is Energy
(activation pressure, metabolic cost); coherence influences the contract's N-cost (`1 - coherence`) and reflects condition,
but N does not collapse into it. (An earlier version of the ledger said "her N is coherence"; that was wrong.) What "gaining N
at rest" should mean (relaxing the Dimensional Energy Regulator's activation, or a reserve that does not exist yet) is open.
**One capacity (D7).** Per resting tick the capacity is `rate * max(wear, debt)`, the resting rate on the larger need, split
between the needs in proportion to their CURRENT size. Both needs therefore relax at the same rate
`rho = rate * max(wear, debt) / (wear + debt)`, between `rate / 2` (equal needs, fully contested) and `rate` (one need alone,
or one dominating). `rate` is the DER's own `base_decay_rate` (0.15): the rate at which it wears is the rate at which rest
restores. Closed form, geometric (saturates), and it composes exactly (two rests equal one longer rest, fractional ticks
included). `RestLedger(recovery, consolidation, carry)`: recovery is credited in full when the rest closes (apportioned
before the work, so nothing is charged afterwards); consolidation spends only its own share, before each job runs; unspent
share carries to the next rest (bounded by what is still owed, and never apportioned twice). `settle` completes funding
within a millionth of what is owed: a geometric relaxation only approaches "all of it", and a rest taken a tick at a time
never reached the snap that one long rest does (the last queued item took 137 closes against ~88).
**Demand.** What needs consolidating is what she did. One operating tick adds `tick_seconds / 1 s / 32` core steps (core
time is 32x denser), which prices consolidating a tick at what operating it wore (0.014 each).
**Measured allocation** (`allocate_rest(wear, debt, 12 ticks)`, rate 0.15): no debt, recovery 0.5147 (= the pure geometric
`0.6 * (1 - 0.85 ** 12)`); recovery complete, consolidation 0.0429 (= `0.05 * (1 - 0.85 ** 12)`); wear 0.6 with debt 0.3:
0.4305 and 0.2153 against 0.5147 and 0.2573 standing alone (each loses ~16%: the capacity is finite); wear 0.614 with debt
0.052: 0.5111 and 0.0433 against 0.5267 and 0.0446 (a small debt neither starves nor slows); equal needs 0.4 and 0.4: each
at `rate / 2 = 0.075`. An earlier draft gave each need `rate * share * size` (size counted twice), which starved a small debt
for hours; the closed form above replaced it.
**Checked** over 60 randomized histories through the real steps, plus the unit tests: neither need is resolved beyond its own
size; each is resolved no more than it would be standing alone; spending never exceeds what consolidation was apportioned;
recovery is credited in full and coherence never drops across a rest or exceeds 1.0; carried share never exceeds what is
still owed. Consolidation finishes within the number of ticks the rate needs: for a debt alone about `ln(1e-6)/ln(1-rate)` =
85 ticks (measured 86 closes for one unit at a 6 s tick; bound 88), and in the worst contested case the half rate
(`ln(1e-6)/ln(1-rate/2)` = 177 ticks; measured 101 to 110 closes).
**Heartbeat.** `MetabolicClock.start_heartbeat` closes due ticks while she is idle, never mid-turn, so a rest is credited
before her first reply back. **Clock hardening.** The reference that tells a wall clock that was SET from time that
PASSED is `CLOCK_BOOTTIME` (counts suspend); with `CLOCK_MONOTONIC` an overnight suspend looked like a clock set forward
and the night was discarded. Where no such reference exists the forward check is off (crediting a jump is harmless,
discarding a night is not). A clock set backwards re-anchors.
---
## 7. Open decisions
**Resolved by Sir (v10):** consolidation is not partly free and there is no `KEEP_FRACTION` (D7); sediment is never dilated (D8);
genealogy stays event-generated with no wall-clock sibling (D9); replays are exempt from the repeat penalty (D10).
**Still open, for Sir:**
1. **What "gaining N at rest" means.** The ledger settles in wear (the coherence stand-in). The DER is activation: injected
   every turn (about +2.5, capped at 25) and dissipating when she is not engaged. Relax that activation, restore a reserve that
   does not exist yet, or something else? Nothing here pretends to have answered it.
2. **Diminishing novelty for internal rehearsal.** D10 exempts replays from the conversational penalty and says the systems
   that own rehearsal may age them. No such mechanism was found in the trainer's staging (`stage_pipeline_learning`: only
   within-call dedupe), and none was built. As it stands a replay never goes stale.
3. **Replay cost through the ledger.** Replays run the full pipeline (so they cost what processing costs) but the trainer is
   not a clock step, so they are not paid out of the rest ledger. Making them a ledger-paid job is the follow-up.
4. **Other internal producers.** `aurora_response_teacher.py` and `aurora_reasoning_games.py` also call `gateway.receive`;
   they are not marked internal. `aurora_praxis_bridge.py` is environmental and deliberately not exempt.
**Resolved earlier:** the Understanding split (section 5); cost table (every core job is priced in core ticks); wake trigger
(none needed: she consolidates during rest and the heartbeat closes ticks while idle); backlog policy (the queue is oldest
first, bounded, backpressure runs the oldest); core dilation during rest (the governor's stability rule decides how many
operations run, and the ledger pays for them); the lattice cadence (D5); repeats counted once per input; the DER's decay is
live on operating ticks.
**Caveats:** (a) with only a debt owed, the last indivisible queue item takes about 85 resting ticks (about 7 hours of 5-minute
closes); the old faster pace came from counting carried credit twice, which was the partly-free consolidation Sir rejected.
(b) a tick under about 30 s makes one core step cost more than a rest tick funds, so a one-step job waits several closes
(bounded by the rate, measured above); harmless at the 5-minute default. (c) the idle heartbeat is a thread, so a suspended
app pauses it; on resume one large `delta_t` arrives (operating 0, rest N), which counts because the reference
(`CLOCK_BOOTTIME`) counts suspend. (d) dreams are not in-process in the surface profile; they plug into the same ledger
(`can_afford` before, `spend` as it runs).
---

## 8. Suggested order when the directive lands (each step shippable alone)

1. `MetabolicClock` and a turn gate, with tests on an injected clock. (DONE)
2. Sediment `delta_t` from elapsed time. (DONE)
3. Entropy decay moved off the per-thought path. (DONE)
4. Lattice and chamber ticks, and the Dimensional Energy Regulator. (DONE; the chamber is already time-gated.)
5. Split Understanding into its surface and core clocks; govern core speed. (DONE; the governor decides how many
   operations run and is never applied to sediment's time, see section 5.)
6. The rest ledger. (DONE; currency is coherence, see section 0.)
7. Budgeted consolidation (DONE, during rest, with `can_afford` before every job; dreams plug in when in-process).
8. The idle heartbeat thread, gated on `turn_in_flight`. (DONE)
