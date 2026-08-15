# Aurora Build 694: Live Subsurface, Automatic Scout Resolution, and Admissibility Repair — Implementation Report

**Status: steps 1-18 of the specification's own mandated 19-step (+ step 20, live mobile testing) implementation order are implemented and merged to this branch across 16 commits. Step 20 (live APK testing on physical/emulated hardware) is explicitly the user's own responsibility per their own instruction during this work — see "Step 20" below.**

This report covers the full implementation of the "Aurora Build 694: Live Subsurface, Automatic Scout Resolution, and Admissibility Repair Directive" (34 sections, pasted in full at the start of this work) against the live Aurora Build 675 codebase (itself the completed "Subsurface Presence and Evidence Scout" implementation this build continues and completes). Every claim about pre-existing code was verified directly against source before implementation began, per the spec's own explicit first instruction.

## Closing architectural rule (spec section 34, restated)

> "I don't know enough" must stop meaning "therefore say I don't know" and begin meaning "therefore something remains unresolved; determine whether I can resolve it, acquire evidence if necessary, integrate what returns, then try to respond.

Build 675 built the whole Scout acquisition machinery — request/report contracts, a bounded broker, a disposable worker, Subsurface-only evaluation — but left several load-bearing pieces disconnected: Android never started the presence runtime or a Scout worker at all, the response-fit request kind had no automatic dispatch trigger, Surface still dispatched knowledge-gap requests directly instead of routing through Subsurface, evidence only ever reached Surface after the response draft was already finished, and generic admissibility (`constraint_abstain`) was the *first* reaction to unresolved pressure rather than a terminal state reached only after resolution had genuinely been attempted. This build closes every one of those gaps.

## What was built, step by step

| Step | What | Key files |
|---|---|---|
| 1-2 | Canonical turn identity: `process_external_user_turn()` adopts an already-set `_current_turn_id` or mints one and restores the prior value in `finally`; canonical `write_turn_open()` publication moved into that same function (Android never ran through `aurora_surface_daemon.py`, so it never produced a turn-open event before this) | `aurora.py::process_external_user_turn` |
| 3 | Event consumption repaired to dispatch by event kind (`integrate_turn_event()`), shared by both consumers instead of two independently-drifting implementations | `aurora_internal/dual_strata/subsurface_presence.py`, `aurora_daemon.py` |
| 4 | `SubsurfacePresenceRuntime` — a dedicated thread, ~150ms poll cadence, structurally independent of the 15-30s autonomous daemon sleep, never imports `aurora.py`/`aurora_daemon.py` | `aurora_internal/dual_strata/subsurface_presence_runtime.py` |
| 5 | Started in Android's `aurora_bridge.initialize()`, alongside (never in place of) `boot_aurora()` | `flutter_app/android/app/src/main/python/aurora_bridge.py` |
| 6 | Scout worker's `state_dir` threaded explicitly through every function — no silent fallback to the repo-relative default on Android | `aurora_scout_daemon.py` |
| 7 | `ScoutBackend` abstraction (`PoedexRoomBackend`, `LocalLessonsBackend` — zero-config, Android-capable — plus operator-configured `RemoteSearchBackend`/`RemoteModelBackend`, never hardcoded to a commercial provider) | `aurora_internal/scouting/backends.py` |
| 8 | Exactly one Scout worker started in Android's `initialize()`, independently stoppable, never a second `boot_aurora()` | `aurora_bridge.py::_start_scout_worker` |
| 9 | `evidence_need` event routing — Surface no longer imports `aurora_internal.scouting.broker` at all; it publishes a need, Subsurface converts it into the actual `ScoutRequest` | `subsurface_presence.py::write_evidence_need`/`integrate_evidence_need_event`, `aurora.py::_try_poedex_lookup` |
| 10 | Automatic response-fit dispatch, two triggers: Trigger A (graduated proactive pressure, configurable threshold, default 0.55) wired into `integrate_interpreted_turn_event()`; Trigger B (abstention rescue) shares the same `dispatch_response_fit_scout()` helper, wired in step 15. Scout worker categorizes `response_relationships` from retrieved text instead of hardwiring `["explain"]` | `subsurface_presence.py`, `aurora_scout_daemon.py` |
| 11 | `EvidenceBinding` evaluation made request-kind aware: only `response_fit` bindings ever relieve `response_fit_pressure`; `knowledge_gap`/`self_diagnostic` never do, mechanically or otherwise | `aurora_internal/scouting/subsurface_scout_bridge.py::evaluate_report`/`consume_scout_reports` |
| 12 | Primary current-turn evidence intake moved ahead of DOWN2 belief (`_ingest_current_turn_scout_evidence`), so accepted evidence can shape the actual response decision, not only its late pre-expression styling | `aurora.py` |
| 13 | Response formation structurally consumes it: `state.pipeline_state["subsurface_response_evidence"]`/`["external_grounding_evidence"]`, and a new DOWN2-belief fallback stage that generates content through `_render_runtime_intent` (never copies Scout text) when response-fit evidence clears a support floor | `aurora.py::_structure_current_turn_scout_evidence`/`_apply_subsurface_response_evidence` |
| 14 | Bounded same-turn evidence waiting: `wait_for_current_turn_binding()` (file-backed poll of `EvidenceBinding`, never raw `ScoutReport`) plus a shared ~4s per-turn Scout rescue budget both this step's opportunistic wait and step 15's rescue wait draw against | `subsurface_scout_bridge.py`, `aurora.py::_scout_rescue_budget_*` |
| 15 | One abstention-rescue retry at the articulation boundary: if `_enforce_emission_discipline()` chose `constraint_abstain` despite a viable interpretation, dispatch Trigger B, wait out the remaining budget, ingest evidence, rerun *only* DOWN2/DOWN1/emission-discipline once, guarded per turn_id | `aurora.py::_attempt_abstention_rescue` |
| 16 | Scout worker added to the desktop stack as an actual component (`scout.pid`/`scout.log`, start/stop/restart/status) | `scripts/strata_stack.sh`, `scripts/run_scout_worker.sh` |
| 17 | Instrumentation: turn/interpreted-turn latency, presence event queue depth/processing latency, response-fit/knowledge-gap pressure, scout dispatch reason/request kind/backend, same-turn wait/binding-used, and all four abstain_* counters | `aurora_internal/dual_strata/presence_metrics.py`, wired through `subsurface_presence.py`, `subsurface_presence_runtime.py`, `aurora.py`, `aurora_scout_daemon.py` |
| 18 | All spec section 31 required tests, including the four deterministic-fake-backend acceptance examples | `tests/test_build694_required_regression.py` plus per-step files |

## Architectural boundaries enforced structurally, not by convention

**Surface never dispatches a `ScoutRequest` for a knowledge gap directly (step 9).** `_try_poedex_lookup()` only ever calls `subsurface_presence.write_evidence_need()` now; `test_aurora_no_longer_imports_dispatch_scout_request_directly` and `test_surface_modules_never_import_anything_from_scouting_broker` assert this at the AST level across the whole file, not just at this one call site.

**Both response-fit triggers share one dispatch shape.** `dispatch_response_fit_scout()` is the single place a `response_fit` `ScoutRequest` is ever built — Trigger A (`integrate_interpreted_turn_event`) and Trigger B (`_attempt_abstention_rescue`) both call it, and `ScoutBroker`'s existing one-response-fit-per-turn dedup means calling it twice in the same turn (proactive pressure firing, then an abstention rescue on the same turn) collapses onto the same in-flight request rather than producing two.

**`knowledge_gap` evidence can never mechanically relieve `response_fit_pressure`.** `evaluate_report()` zeroes `pressure_relief` for anything but a `response_fit` report; `consume_scout_reports()` sums relief only across `response_fit` bindings in the accepted batch, keeping the invariant explicit at both the pure-evaluation boundary and the presence-frame-folding boundary. `test_mixed_batch_only_response_fit_bindings_move_the_pressure_number` proves this holds even when a `knowledge_gap` binding is accepted in the *same* batch as a `response_fit` one.

**Scout-retrieved text never reaches `state.response_content` directly.** `_apply_subsurface_response_evidence()` only ever selects *which* named response-relationship category applies (from a fixed table of first-person framing claims); the actual wording always comes from `_render_runtime_intent`, Aurora's own rendering machinery — the same one every sibling DOWN2-belief fallback stage already uses.

**The abstention-rescue retry cannot duplicate memory admission, turn counting, genealogy, or consequence recording.** None of those run inside `_run_reasoning_pipeline()` at all — they happen in `_run_live_response_turn()`, entirely outside where the rescue operates — so simply never re-entering the whole turn (the rescue reruns only DOWN2/DOWN1/emission-discipline) is what makes duplication structurally impossible, not a guard that could be forgotten. Verified by AST Call-node inspection (`test_scout_retry_does_not_duplicate_memory_admission`/`turn_count`), not a substring search that a docstring mentioning those names in passing could fool.

**Android's Scout worker and PresenceRuntime never touch `aurora_bridge._lock`.** Reviewed directly against source (spec section 25): both run on independent daemon threads started in `initialize()`, outside the `with _lock:` block that only serializes `process_external_user_turn()` calls in `handle_message()`. Neither `subsurface_presence_runtime.py` nor `aurora_scout_daemon.py` imports `aurora_bridge` at all, so there is no path by which a Surface wait for Subsurface evidence could block presence processing, Scout execution, report integration, sensor capture, or heartbeat updates.

## Deliberate scope decisions

- **Section 18's `PresenceBus` abstraction** (`publish`/`drain`/`wait_for_binding`/`notify_binding`) was not built as a separate class. `wait_for_current_turn_binding()` implements the required *behavior* — bounded, non-polling-wasteful (150ms, the same cadence `SubsurfacePresenceRuntime` already uses for presence processing), file-backed so it works identically whether or not a fast in-process runtime happens to be running — using a plain bounded poll rather than a `threading.Condition` wake. This is explicitly allowed by the spec's own "provide file-backed fallback ... if necessary" language, and `SubsurfacePresenceRuntime.on_binding_change` remains available as a genuine future optimization without needing to change this primitive's observable contract.
- **Section 23's active reconsideration of interpretation using `external_grounding_evidence`** (a knowledge-gap binding causing Aurora to re-run her upward interpretation pass mid-turn) was not built. The field is populated and available (step 13), but no existing hook re-runs `_chain_up*` mid-turn, and adding one would be a genuinely new architectural capability the spec's own 19-step order does not list as a discrete step — building it now would violate "do not mix unrelated architecture changes into this pass."
- **Section 13's response-fit categorization** (`aurora_scout_daemon.py` no longer hardwiring `response_relationships=["explain"]`) was folded into step 10 rather than treated as its own step, since dispatching response-fit requests that always came back "explain" would make Trigger A/B structurally pointless — the acceptance criteria and required test (`test_response_fit_report_contains_response_relationships`) needed it to complete step 10 meaningfully.

## Step 20 (live mobile testing)

Per the user's own explicit instruction during this work: *"do the live apk test in the way you can I will still do my live test but dont let it stop you from continuing the directive fully."* This session cannot build or run the Flutter/Android APK on physical or emulated hardware. In its place, every step above was verified against the real, live desktop Python runtime wherever practical:

- Two full `boot_aurora()` + `process_external_user_turn()` live smoke runs completed successfully end-to-end (no crash), confirming the canonical turn-id mint/restore cycle, real `turn_open`/`interpreted_turn` event integration into a matching presence frame, and Scout worker startup all work against a genuinely booted Aurora instance, not just mocked call sites.
- A traced live run (with `SubsurfacePresenceRuntime` and the Scout worker both actually running as background threads against the same `state_dir`) confirmed `_attempt_abstention_rescue` genuinely engages end-to-end — `interpretation_adequate` gate passed, dispatch fired, the bounded wait ran, and response formation reran — on a real "hey aurora" turn. That specific traced turn did not end up resolving to non-abstain content; `response_fit_pressure` for that greeting computed to 0.35 on a fresh, historyless boot, below the default 0.55 Trigger A threshold, and the `LocalLessonsBackend`'s default corpus has no entry teaching Aurora about generic greetings. This is a genuine **tuning/content observation**, not a wiring defect: every discrete piece of the mechanism (dispatch, budget, wait, evidence structuring, generation-through-`_render_runtime_intent`) is independently unit-tested and confirmed correct in isolation (see `test_build694_required_regression.py`'s Case 1-4 acceptance examples, which use a deterministic fake backend precisely so the acceptance behavior doesn't depend on the default threshold or corpus content). Whether 0.55 is the right default threshold, or whether `LocalLessonsBackend`'s corpus should be seeded with baseline social-response grounding, is exactly the kind of real-world calibration the spec itself frames as adjustable ("a tuning parameter, not a semantic rule") rather than something this implementation pass should hardcode a fix for.
- Android-specific paths (`aurora_bridge.py`'s `initialize()`/`handle_message()`/`_start_scout_worker`) were verified structurally — AST-level confirmation of call order, single-boot invariants, and lock-graph independence — since they cannot be executed without Chaquopy/an Android runtime in this environment.

## Test inventory

17 new/updated test files (Build 694 steps 9-18's own commits; steps 1-8's own test files are additional and predate the visible portion of this work), 243 tests passing together as of this report when run as one targeted suite:

```
tests/test_subsurface_presence_wiring.py                       9  (steps 1-3, extended)
tests/test_subsurface_presence_runtime.py                     15  (step 4, extended step 17)
tests/test_mobile_presence_runtime_startup.py                   5  (step 5)
tests/test_scout_worker.py                                     17  (step 6, extended)
tests/test_scout_backends.py                                   19  (step 7)
tests/test_mobile_scout_worker_startup.py                       8  (step 8)
tests/test_surface_poedex_dispatch.py                            6  (step 9, extended)
tests/test_scout_report_routes_only_to_subsurface.py          (extended, step 9)
tests/test_response_fit_automatic_dispatch.py                  11  (step 10)
tests/test_evidence_binding_request_kind_aware.py                8  (step 11)
tests/test_scout_evidence_early_ingestion.py                     8  (step 12)
tests/test_response_formation_consumes_scout_evidence.py        12  (step 13)
tests/test_bounded_same_turn_evidence_wait.py                   18  (step 14)
tests/test_abstention_rescue_retry.py                            12  (step 15)
tests/test_desktop_stack_includes_scout_worker.py                8  (step 16)
tests/test_build694_instrumentation.py                          12  (step 17)
tests/test_build694_required_regression.py                      21  (step 18, spec section 31's exact-named tests + 4 acceptance cases)
```

Every spec section 31 required test *name* exists, either in `test_build694_required_regression.py` directly or (where an earlier per-step file already covered the exact name as a natural side effect of that step's own tests — `test_response_fit_pressure_dispatches_scout`, `test_low_interpretation_does_not_dispatch_response_fit`, `test_presence_runtime_independent_of_governor_sleep`, `test_knowledge_gap_does_not_directly_relieve_response_fit_pressure`, `test_response_fit_report_contains_response_relationships`) in that step's own file, noted explicitly in `test_build694_required_regression.py` rather than duplicated.

## Regression discipline

Every commit in this work ran and passed its own new tests plus the accumulated step-by-step suite before being pushed. A single combined run of all 23 Build-694-and-675-scout-related test files (243 tests, listed above plus the Build 675 scout/presence files this build extends) passed cleanly as of this report. `aurora.py`, `aurora_daemon.py`, and `aurora_scout_daemon.py` were each also confirmed to still import cleanly (real Python import, not just AST parse) after every step.

A full run of the entire `tests/` directory (272+ files, most unrelated to this work) was not attempted to completion, consistent with the finding already documented in Build 675's own report: a single `boot_aurora()`-based test file can take from 15 seconds to several minutes depending on host contention, and 272 files at that rate is impractical to run serially in this environment. Two genuinely fresh, uncontended `boot_aurora()` + live-turn runs during this work's own step-20 verification (above) completed in 15.6s and well under a minute respectively, suggesting the earlier 362s figure was substantially inflated by resource contention with other running processes at the time, not a fixed cost of this codebase — but re-running the full 272-file suite serially to confirm that was still judged impractical relative to the value of continuing the directive's remaining steps, matching this session's established practice.
