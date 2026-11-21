# Reposition dream entanglement as perceptual-affective interpretation

Historical audit from November 16, 2026. The findings below describe the pre-fix implementation. Current `main` retains regression coverage in `tests/test_dream_entanglement_evidence_boundary.py`.


Parent #257; focused draft PR #258.

## Architectural decision
The speculative association discovered by `CrystalEntanglementRegistry` belongs to **perceptual-affective hypothesis formation**. It may bias attention, tension, salience, curiosity, and further observation, but must not directly increment earned crystal promotion.

## Verified existing interfaces
- `aurora_internal/aurora_attention_engine.py::AttentionEngine.tick(tick, external_stimuli, internal_drift)` resolves external salience and subsurface tension into a frame. **Do not** mislabel dream-internal stimuli as external perception.
- `aurora_internal/dual_strata/dce_bridge.py::DualStrataBridge.build_snapshot` constructs `salience_weights`, `candidate_interpretations` including `affective_attention`, and `action_bias_candidates` from real pressure and tracked affect. Do not insert canned interpretation strings into speech.
- `aurora_internal/dual_strata/micro_reasoning.py::generate_micro_reasoning` consumes pressure/contract/salience signals for bounded hypotheses.
- `aurora_quantum_dream_substrate.py::CrystalEntanglementRegistry.propagate` currently calls `genealogy.tick_crystal_promotion` from randomly generated delta, without observing a real recent delta.

## Correct ownership and circulation
1. **Origin:** source-tagged dream/internal association, grounded in actual canonical concept IDs and verified genealogy relationships; no prefix-derived ancestry.
2. **Perceptual classifier:** classify as a *candidate association* with source, uncertainty, contextual resonance, and relevant X/T/N/B/A pressure signature. Reuse an existing perception/attention contract; avoid creating a new storage domain.
3. **Affective interpretation:** determine whether the association actually changes existing salience, tension, ambiguity, curiosity or resonance. Zero change is a legitimate outcome.
4. **Conscious surface:** surface receives only contextually useful, freshness-qualified consequences via the existing dual-strata path. The surface remains the owner of conscious sense; the subsurface may anticipate and precompute.
5. **Learning:** only observed outcomes and existing promotion gates may upgrade confidence/maturity. Dream rehearsal and hypothetical association remain clearly marked as such.
6. **Lifecycle:** transient association must expire or decay when unreinforced; no duplicated crystal identity, no repeated event credit, no endless reclassification per cycle.

## Implementation blockers to verify before wiring
- Confirm the real scheduler entry point and the deployed system's live `attention_engine`/DCE objects and their input contracts.
- Check whether `genealogy.tick_crystal_promotion` exists on the runtime genealogy instance, and whether it already rejects unearned source labels.
- Confirm `AttentionEngine.tick` is not an appropriate direct dream callback: it expects `DifferenceSnapshot` and external stimuli. A dream association must not impersonate a sensor observation.
- Identify the established **internal** salience/pressure input consumed by DCE or attention; route through it once verified. If none exists, expose the missing contract explicitly rather than invent a parallel classifier.
- Compare original and candidate traces for latency, promotion state, salience, attention, memory and dream stages.

## Acceptance tests
- Dream-only association can affect an internal candidate/attention response when warranted, but never earned promotion.
- Unrelated lexical-prefix matches do not establish ancestry.
- No new association means no new affective or attention pressure.
- Fresh waking evidence may independently earn promotion through existing genealogy.
- Replay and save/restore do not double count; stale projection does not influence the surface.
- Existing dream perturbation, encounter, temporal feedback, and consciousness stages remain operational.

**Status:** Architecture placement confirmed by source inspection; runtime routing not yet changed. Do not claim completed redirect until producer-to-consumer execution and tests are demonstrated.
