# Aurora PR #264 architectural-loss audit

## Scope and evidence

Original machine-readable comparison:
`knowledge_graph/comparisons/INTEGRATION_COMPARISON.json`
compares knowledge-graph base `b649850b28ff` with integration head
`0d0794ec21a4`, **not** today's final integration head.

Its `relationships.lost` contains **211 inferred graph edges**:
127 IMPORTS, 49 FEEDS, 16 CALLS, 5 MEMBER_OF, 4 READS, 4 WRITES,
4 REFERENCES, 1 PART_OF, 1 USES_ORGAN. **All 211 have observed=false**.
This is a difference in *static graph extraction*; no individual edge
has a measured failing runtime invocation in this comparison. These numbers
must not be reported as 211 observed capability regressions.

The comparison additionally classifies 1,452 consolidated, 313 retargeted,
7 delegated, 77 folded into shared, 216 observed only in the base run, and
136 removed with code. The changed-identity manifest includes shared clamp
and DictRecord extractions, Dart widget relocations and Kotlin overlay work.

## Higher-risk relationships and direct source checks

1. **Praxis voice-gate forwarding.** The old `_last_voice_gate -> last_spoke`
   static FEEDS edge was not retained, but live
   `aurora_praxis_messenger.PraxisMessenger.handle_message` still reads
   `systems["_last_voice_gate"]`, checks channel, age and own-voice
   outcomes, and *withholds* non-authorized replies before durable delivery.
   The focused Praxis suite passes on the repaired head. This is evidence of
   surviving behavior, not proof that every old graph edge is equivalent.
2. **Home/surface epoch, ownership, outbox, delivery.** The original
   `strata_link.StrataLinkClient` epoch/role and `DurableOutbox` FEEDS edges
   changed with the new wire state. Current `StrataLinkServer.handle_sync`
   separately authenticates the owner epoch, applies uplinks by ordered seq,
   persists acknowledgments and tracks duplicates. The focused strata
   fencing and state-transfer suites pass. Network-specific timing remains
   a physical deployment test.
3. **Predictive queue persistence.** The original literal
   `predictive_frame_queue.json` READS/WRITES graph edges were based on a
   global pathname. `predictive_stager._load_queue(state_dir)` now obtains
   the path from the caller's `state_dir`; the queue remains present and
   scoped to the live organism. A new graph should follow the parameterized
   storage edge rather than reintroducing a shared global store.
4. **Late phone expression.** The old `_late_surface_response` FEEDS edge
   sits alongside changed surface response transport. Phone UI and
   strata tests exercise late receipt; the relative timing and visibility
   still require phone testing.
5. **Dart/Kotlin UI.** Several old CALLS edges resolve to Flutter widget
   constructor functions (`Row`, `Icon`, `SimpleDialogOption`) whose
   declaring widget layout moved. These are low-confidence static
   function-resolution artifacts, not proof of a missing builder.

## Remediation on this PR

- Restored Build 725's native semantic representation, typed evidence,
  receiver-specific local pressure discharge, speaker-grounded semantic
  selection and off-thread afterthought dispatch from the original commit
  `e9dca7d`, reconciled with current memory baseline and source behavior.
- Desktop resident now starts the existing weekly `LearningProbe` on the
  canonical shared field, in addition to Praxis bridge, messenger and
  optional experiential archive. Does not boot a second organism.
- Recovered evidence-grounded reflective self-inquiry while retaining the
  Build 613 strict same-turn source/hash gate and blocking unrelated-world
  introspection leakage.

## Verification standard

1. A graph source-hash check alone does **not** classify the 211 edges.
   Rebuild the committed graph from the final head, then diff the previous
   graph base against that fresh head and inspect the unresolved list.
2. Treat each lost *runtime-observed* relationship as a merge blocker.
   Any lost unobserved IMPORT/FEEDS/CALLS edge in the primary dialogue,
   Praxis, memory, strata, home or surface pathways needs source tracing
   or regression coverage. Do not fabricate missing calls merely to make
   the static graph match.
3. The focused Build 725, reflective, desktop, Praxis and strata suite
   passed 152 tests with 2 skips on commit `6c626e2`; verify it again on
   the final graph-synchronized head.
4. The full matrix is a separate gate. Compare against the preexisting
   repository baseline, distinguish inherited failures and environmental
   skips, and do not call a partial suite a complete success.
5. Device-ready means software merge + reproducible HP backup/deployment
   plan, *not* physical HP or phone performance already proven.

The fresh comparison will be recorded as
`knowledge_graph/comparisons/PR264_FINAL_COMPARISON.{md,json}`.

## Verified replacements after merge

Rebuilt on main `df368c4` with fresh runtime recordings, the final
comparison shows 227 lost relationships, 4 of them runtime-observed. Each
is traced to an intentional replacement and listed with its evidence in
`knowledge_graph/comparisons/PR264_VERIFIED_REPLACEMENTS.json`:

- The old `_run_afterthought_episode_bg` thread is replaced by
  `_dispatch_afterthought_subsurface`; the recording shows three
  afterthought threads, each running the simulation episode.
- Three `ConsciousLearner` / `_topic_from_seed_prompt` calls into the
  regex topic parser and the templated understanding sentence were removed
  by the Build 725 restoration: semantic topics now come only from her
  native meaning layer, and outcomes stay structured evidence. Both
  helpers remain in the module but nothing calls them.
