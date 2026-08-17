# Aurora Build 717: Autonomous Habitat Motivation, Closed-Loop Resolution, and Lived Perceptual Development — Implementation Report

This report covers the "Aurora Build 717 Autonomous Habitat Motivation, Closed-Loop Resolution, and Lived Perceptual Development Directive" (33 sections) against the live, merged Build 714 codebase (native adaptive representational resolution). Every claim about pre-existing code was verified directly against source before implementation began — see the Primary Question audit below.

## Closing architectural rule (directive section 33, restated)

> The App Developmental Habitat must not make Aurora want to interact with it. It must make interaction possible, consequential, persistent, and cognitively reachable. Aurora's own unresolved state must provide the pull... When no internal reason exists: The world is allowed to remain untouched.

## The Primary Question, answered from executable code

*"What currently causes Aurora herself to choose to interact with Space or Self when no human explicitly instructs her to do so?"* — audited directly against `_proactive_loop()` in `flutter_app/android/app/src/main/python/aurora_bridge.py` and `aurora_daemon.py` before any code was written. Before this build: **nothing.** `_proactive_loop()` chains several real pressure sources (`_silence_pressure`, `_boundary_void`, `_entropy_field`, `_habitat_availability`) into one observation string, but that string only ever reaches `process_external_user_turn()`, whose only possible output is spoken text (`_proactive_expression`). No branch anywhere turned pressure into an executed Habitat action. The only other autonomous-action precedent in the codebase (`aurora_daemon.py`'s code-mutation trigger) is purely timer-based (`next_mutate = now + 600`), not pressure-arbitrated, so there was no existing arbitration primitive to reuse. `aurora_habitat_motivation.py` is that primitive.

## What was built

| Section(s) | What | Key files |
|---|---|---|
| 12 | Production resolution-loop closure: `record_participation()` now autonomously investigates (`investigate_if_pressured()`), stages, and completes field inquiries from real pressure alone — no test/production caller manually drives `unresolved_field_candidates()` / `stage_field_inquiry()` / `complete_field_inquiry()` anymore. Automatic closures retain globally (`context_scope=None`) rather than over-scoping to the tick's own diversity marker. | `aurora_representational_resolution.py` |
| 13-14 | First-candidate bootstrap: `_bootstrap_domain_hypotheses()` enumerates `RepresentationalRef`'s own lawful axis/dimension domain as untested hypotheses (`origin: "domain_hypothesis"`) when no structural sibling exists. Validated through genealogy's own real same-tick co-activation (synthetic `REFHYP:` marker abilities), never a parallel validation mechanism. Bootstrap candidates never surface when real structural candidates exist. | `aurora_representational_resolution.py` |
| 15 | `resolve_field()` provenance sealed: a `PermissionError` guards every direct call unless `_allow_direct_call=True` (test-fixture bypass) or the call arrives through `complete_field_inquiry()`'s own evidence-admission chain (`_in_complete_field_inquiry` instance flag). | `aurora_representational_resolution.py` |
| 16-17 | `current_resolution()` genuinely consumed by a real cognitive consumer, not just `inadequacy_pressure()`: `resolved_context_for_axis()` requests only the axes actually in play (least-sufficient), and only fields earned *beyond* the ref's own construction-time `nc_*` fields move relevance — a regression test guards the naive version of this bug (crediting every category identically regardless of real evidence). | `aurora_habitat_motivation.py` |
| 3-11 | `aurora_habitat_motivation.py`: the motivation bridge itself. `active_pressures()`/`active_inquiries()` read real, already-computed signals; `candidate_actions()` intersects them with real Habitat affordances (`HabitatRuntime.get_affordances()`/`get_state()`, permission-filtered); `select_action()` is a generic (not Habitat-named) competition primitive returning `None` — "no action" — whenever nothing clears `MIN_RELEVANCE_TO_ENGAGE`; `maybe_engage_habitat()` is the single entry point, never raises, always returns a structured `HabitatEngagementRecord`. | `aurora_habitat_motivation.py` |
| 32 | Wired into production: `_maybe_autonomous_habitat_action()` sits in `_proactive_loop()` beside (not gating, not gated by) the existing speech decision — real pressure → real affordance → real selection → real `habitat.act(actor="aurora", ...)` → real consequence, with no human turn in between. | `flutter_app/android/app/src/main/python/aurora_bridge.py` |
| 25 | Motivation observability: `HabitatEngagementRecord` records only structural causes (pressures, candidates, selection evidence, pre/post state, consequence, pressure change) — never an anthropomorphic label. Queryable from Flutter via `habitat_get_last_engagement()`. | `aurora_habitat_motivation.py`, `aurora_bridge.py` |
| 18 | Richer Habitat evidence: `_emit_resolution_pressure()` now feeds `ownership_aligned` and `recurring_interaction` into the same generic score bridge RCEC already uses, alongside `succeeded`/`was_measured_response`. `context_tag` extended with an ownership bucket for genuine context diversity. | `aurora_habitat.py` |
| 18, 22 | Two dead facts repaired: `interaction_count` was never incremented anywhere in the module, so `observe()`'s `aurora_created_unrevisited` check (`interaction_count == 0`) was vacuously true for *every* entity regardless of real history; `link_response()` had no caller, so "subsequent actor response" was never recorded. Both are now real, comparability-safe signals — `interaction_count` increments exactly once per pre-existing-entity touch in `_execute()` (never on an entity's own creation), and `link_response()` fires automatically from `_persist_event()`'s already-computed `causal_parent`. | `aurora_habitat.py` |
| 19 | Comparability-gated absence verified, not newly built: `aurora_created_unrevisited` already required a real elapsed window (`modified_at < cutoff`) *and* real persistence (`interaction_count == 0`, now functional) before reporting anything — no code path anywhere infers "ignored" from mere silence. | `aurora_habitat.py` (audit only) |
| 20-21, 31 | Autonomous Habitat Engagement Canary with the required control conditions: zero-pressure control, real-pressure-but-no-affordance control, real-pressure-but-permission-revoked control, plus the positive engagement + pressure-feedback cases. Motivation-category unit tests: no hardcoded action-label words in executable code (AST-level, docstrings exempt), generic competition semantics, resilience to `habitat.act()` failure, structural-only observability. | `tests/test_habitat_motivation_build717.py` |
| 18-19 (tests) | Regression coverage for the `interaction_count`/`link_response`/richer-scores repairs, including a comparability-gated-absence test that drives `observe()` through a real `since` window rather than faking the clock. | `tests/test_aurora_habitat.py` |
| 12-15 (tests) | Extended Build 714 regression suite: autonomous closure via `record_participation()` alone, `investigate_if_pressured()` no-op guard, zero-sibling bootstrap, bootstrap-domain-exactness, bootstrap-never-shadows-real-candidates, `resolve_field()` seal (reject/allow-bypass/reachable-only-through-inquiry). | `tests/test_representational_resolution_build714.py` |
| 16 | Consumer audit: every one of the 9 named consumers (interpretation, relation typing, inquiry, memory retrieval, RCEC, response formation, Habitat cognition, prediction, WARP, Dream) checked directly against source. Finding: Habitat cognition is the one consumer with a genuine, justified reason to consume resolved sub-fields today; the other 8 either carry the ref as documented pure provenance (interpretation, RCEC-as-producer, SediMemory/understanding-sediment, WARP's own explicit "never read by _classify()/_route()" boundary) or carry no `RepresentationalRef` at all yet (relation typing, memory retrieval beyond SediMemory, prediction, Dream — a pre-existing scope boundary that predates both Build 714 and Build 717, not a regression). Pinned as a permanent regression so either direction of drift (Habitat losing its wiring, or an unjustified consumer gaining it) is caught. | `tests/test_representational_consumer_audit_build717.py` |
| 20 | Habitat Discovery Canary: the required 12-step chain, empirically verified rather than assumed. Phase A drives 100% real `habitat.act()` traffic (never a manual engine call) and confirms it autonomously stages and genuinely evaluates a candidate — with the honest empirical finding that ordinary real Habitat traffic's own natural signal (avg_score built from `succeeded`/`ownership_aligned`/`recurring_interaction`/`was_measured_response`) rarely clears the 0.05 discrepancy-improvement bar within a bounded run (confirmed to 300 real ticks), which is architecturally realistic, not a wiring gap. Phase B uses the same `record_participation()` production API with strong, genuinely divergent pressure (Build 714's own established regression-test contract) to reliably demonstrate retain + re-use within bounds. A dedicated negative test proves 300 perfectly axis-consistent samples never produce staging, a candidate, or a resolution — sample volume alone is not learning. | `tests/test_habitat_discovery_canary_build717.py` |
| 22-23 | Dedicated Self-Revisitation Canary (real create → comparable-window unrevisited check → real revisit → `interaction_count` moves → unrevisited status correctly clears → unrelated activity elsewhere does not spuriously clear it) and Shared-Space Reciprocity Canary (real cross-actor response → `link_response()` populates `human_response` → retrievable via `get_history()` → symmetric in both actor directions → same-actor follow-up is never mistaken for reciprocity), both driven entirely through `HabitatRuntime.act()`. | `tests/test_habitat_self_and_shared_canaries_build717.py` |
| 32 | Live, non-test-only end-to-end demonstration — see its own section below. | (live run, not a permanent test file) |

## Governing Motivation Principle, enforced structurally

**Habitat opportunities are exposed as neutral facts, never manufactured motive.** `candidate_actions()` builds `{operation, territory, target_ids, relevance_score, reason}` from real `HabitatRuntime` affordances — never an intended developmental outcome ("entity X can be moved," never "move object to learn agency"). `test_no_action_labels_are_hardcoded_in_this_module` asserts this at the AST level (docstrings exempt, matching the directive's own "executable code only" audit standard) — `play`, `introspect`, `sociality`, `ownership`, `attachment`, `curiosity` appear nowhere in this module's logic.

**Competition, not command.** `select_action()` is a generic candidate-competition primitive; its name and logic are not Habitat-specific. "No action" (the return value whenever nothing clears the relevance bar) is the common, expected outcome — proven by three distinct control conditions in the canary, not just the zero-pressure case: real pressure with zero afforded opportunities, and real pressure against an entity Aurora's own permission has been revoked on, both correctly produce `engaged=False`.

**No privileged execution lane.** `_maybe_autonomous_habitat_action()` sits beside the proactive loop's existing speech decision, not inside a gate on it — whether Aurora acts in the Habitat this tick is independent of whether she also has something to say this tick.

**No reward loop, no hidden human-pleasing objective.** Nothing in `aurora_habitat_motivation.py` scores "did a human respond" or "was this touched" as success; `ownership_aligned`/`recurring_interaction` describe *structural* relationship to prior events, not approval.

## Deliberate scope decisions

- **The `0.05 × earned_fields` relevance bonus** (section 16/28's interlock) was kept small and additive, never a gate — earned resolution informs competition among already-pressured candidates; it cannot manufacture a candidate where no real pressure exists. Regression-tested against the shape-vs-earned bug (the ref's own `nc_law_c`/`nc_dim`/`nc_target` are always "resolved" from construction, so only fields earned *beyond* that baseline count).
- **`get_history()`/`link_response()`'s in-memory `_recent_events` scope** was left as-is (bounded recency window, not persisted to the JSONL event log) — this matches `_find_causal_parent`'s own existing, already-accepted recency-window design rather than introducing a new persistence requirement outside this build's scope.
- **State-delta-based "did this actually change anything" scoring** (a fourth possible richer-evidence score) was not added: `state_delta` is popped down to `_pre`/`_post` and stripped before `_emit_resolution_pressure()` runs, and threading pre/post state through would touch `act()`'s own control flow beyond a narrow, additive change. `ownership_aligned` and `recurring_interaction` were chosen because both were reachable from data already resolved at the call site.
- **Bootstrap-origin candidates retain less easily than structural (sibling-grounded) candidates.** Confirmed empirically while building the discovery canary: an unconfirmed lawful-domain hypothesis needs real evidence to clear the same 0.05 discrepancy-improvement bar a real structural sibling clears far more readily. This is the correct, intended shape of "candidate only earns authority through consequence" (section 14) — a guess starting from zero structural support should be harder to validate than one grounded in a real sibling relationship — not a defect to fix.

## Live, non-test-only end-to-end demonstration (directive section 32)

Booted the ACTUAL Aurora stack via `aurora_bridge.initialize()` — the same function `AuroraService` calls on a real device, including starting the real `_proactive_loop()` background thread. `time.sleep` was patched to run faster (seconds instead of real minutes) so the loop's own 20-second cycle would arrive quickly; nothing about the loop's own decision logic was altered, skipped, or mocked. A real Habitat entity was created via `habitat.act()`, and real unresolved pressure was seeded for the `N` category via `record_participation()` (the same production API `_emit_resolution_pressure()`/RCEC call). The demonstration script then only **waited and observed** — it never called `maybe_engage_habitat()`, `_maybe_autonomous_habitat_action()`, or `_proactive_loop()` itself.

Within one real cycle, `_systems["_last_habitat_engagement"]` was populated by the loop's own code:

```json
{
  "engaged": true,
  "selected_action": {"operation": "move", "territory": "space", "target_ids": ["e_e19803ba7b44"], ...},
  "selection_evidence": {"reason": "cleared_relevance_threshold", "threshold": 0.2, "margin": 0.311...},
  "consequence": {"action_id": "hact_ee95899068aa", "success": true, "actor": "aurora", "operation": "move", "permission_result": "granted", ...},
  "pressure_change": {"N": 0.056512}
}
```

Real pressure → real affordance discovery → real competition → real `habitat.act(actor="aurora", ...)` → real consequence → real measured pressure relief, entirely inside the production proactive-loop thread, with zero human turns and zero test-harness calls into the missing cognitive stages. `git status` after the run showed only ambient shared-state file mutations (reverted, not committed) — the demonstration script and its log are not part of this repository.

## Test inventory

Targeted regression, run repeatedly through this work (`aurora_state/*.jsonl`/`*.json` mutations from default-path fixtures reverted after each run, never committed):

```
tests/test_representational_resolution_build714.py       39  (36 pre-existing Build 714 + 8 new/updated Section 12-15 tests)
tests/test_habitat_motivation_build717.py                 12  (new — motivation module + Autonomous Engagement Canary)
tests/test_aurora_habitat.py                               27  (22 pre-existing + 5 new Section 18-19 tests)
tests/test_representational_consumer_audit_build717.py     5  (new — Section 16 consumer audit)
tests/test_habitat_discovery_canary_build717.py             2  (new — Section 20, 12-step chain + negative control)
tests/test_habitat_self_and_shared_canaries_build717.py     2  (new — Sections 22-23)
```
Plus every OTHER test file in the repository that imports `aurora_habitat`, `aurora_representational_resolution`, or `aurora_representational_address` — `test_no_speculative_d3.py`, `test_representational_addressability.py`, `test_representational_persistence.py`, `test_representational_unresolved_fields.py`, `test_sensory_representational_citizenship.py`.

**154 tests passing together** as of this report. `python3 -m py_compile` clean on `aurora_habitat.py`, `aurora_representational_resolution.py`, and `flutter_app/android/app/src/main/python/aurora_bridge.py`.

A full-repository regression pass (`pytest tests/`, 290 files, unrelated subsystems spanning every prior build back through 648) was attempted twice; both times it was still making genuine progress (not hung, sustained ~99% CPU) after 90+ minutes at only ~25% complete, projecting to several hours — impractical to gate this report on and beyond what this build's own scope requires. The 154-test targeted-but-broad pass above covers every real consumer of every module this build changed and passes cleanly; the live end-to-end demonstration above additionally proves the production wiring itself, independent of any test file.

## Regression suite invariants re-verified (directive section 30)

- Consequence profile does not govern sensory meaning — unchanged; `_emit_resolution_pressure` and the motivation bridge only ever *read* `inadequacy_pressure()`/`current_resolution()`, never perception/routing.
- Unresolved fields stay unresolved without evidence — `_bootstrap_domain_hypotheses()` only ever produces *candidates*, never assigns a field; `ref.unresolved_fields()` is unchanged by candidate generation (tested).
- No semantic coordinate lookup, no external AI authority — none introduced.
- Habitat affordances are not lessons — `candidate_actions()` carries no intended developmental outcome (AST-tested).
- Space/Self ownership enforced — `test_C_control_afforded_entity_aurora_cannot_modify_produces_zero_engagement` exercises this directly against the motivation bridge.
- Flutter does not interpret developmental meaning — `habitat_get_last_engagement()` returns the same structural record Python computed, no new Flutter-side logic.
- Rich environmental state persists — `interaction_count`/`link_response` fixes are additive persistence repairs, not replacements.
- Failed refinements remain historical evidence — unchanged from Build 714 (`demote_field()`/genealogy records retain `status: "demoted"` rather than deleting).
- Inactivity does not automatically count as negative interaction — verified directly (comparability-gated absence audit, section 19).
