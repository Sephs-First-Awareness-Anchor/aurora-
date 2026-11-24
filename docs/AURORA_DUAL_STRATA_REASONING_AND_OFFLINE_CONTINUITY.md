# Dual-strata reasoning and offline continuity

**Authors:** Sunni (Sir) Morningstar and Cael Devo
**Directive:** AURORA_DUAL_STRATA_REASONING_AND_OFFLINE_CONTINUITY_DIRECTIVE
**Branch:** `claude/aurora-update-20261121`, on current `main` (which already holds #266, #269 and #270).

This branch is one whole update for review. It carries, in one merge:

- this directive (dual strata and offline continuity);
- #268, learned resolution and contextual recall through the uniform crystal facets;
- #272, the desktop resident and phone pairing over the encrypted relay, with the desktop and Linux installers;
- experiential recall (directive V2), what she held then kept apart from what she holds now.

Merging it replaces #268 and #272; nothing else needs merging first.

She is one mind on two strata. Her surface (the phone) owns the present and
runs her whole cognitive loop, offline too. Her subsurface (the HP desktop,
home) owns her deep developmental stores and does the slow work. Work is
split by latency, depth and cost, never by taking an ability away from one
stratum. Both strata read the same uniform crystals, with one identity per
concept.

This document holds the audit, the before and after architecture, the
dataflow, the offline protocol, the measured results, the deploy and
rollback steps, and what still needs the real hardware.

---

## 1. Audit: what was true before this change

Evidence came from reading the code and from probes that boot the real
surface profile on a copy of `aurora_state`, with home unreachable (a
pairing line that points at an address that never answers).

| Finding | Evidence | Consequence |
|---|---|---|
| On a surface-only phone, every write to a home-owned store was declined. | Probe: 4,060 writes declined across 28 stores in a four-turn session (lexicon, grammar motifs, interaction memory, reasoning paths, understanding stores, ...). | What she learned on the phone while home was unreachable was lost at the next restart. The directive's section 8 (offline learning without split-brain) was not met. |
| 10 home-owned files were written straight past the gate. | Probe: `changed_home_owned` listed `developmental_timeline.jsonl`, `reflective_readdressing_history.jsonl`, `relation_pair_log.jsonl`, `representation_communication_outcomes.json`, `universal_function_constraints.json`, `universal_function_lineage.json`, `vision_index.json`, `constraint_fallback_log.jsonl`, `envelope_shadow_log.jsonl`, `system_introspection_index.json`. | Two versions of the same store: the phone's local copy diverged from home's, and home's growth would later overwrite it. This is the "modules write around the one-state guard" gap. |
| 5 learning stores were declined outright rather than kept. | `reasoning_paths.json`, `unformed_patterns.json`, `live_lineage_journal.json`, `recursive_causal_reasoning_waveform_history.jsonl`, `study_log.jsonl` used the yes/no gate. | Same loss as the first row. |
| The recommendation hub on the phone redid the same work every start. | Probe: about 3,900 declined writes to `aurora_recommendation_actions.jsonl` in a three-turn session. The hub aged out the same stale items each start, could not record that it had, and so did it again. A high-priority item could be raised with Sunni repeatedly for the same reason. | Wasted phone compute every start (computational health), and a risk of repeating herself. |
| Home's downlink carried no crystal facets. | `PredictiveStager` frames are axis-lens hypotheses with no facet references; the surface harvest pops them with `epoch=None`. | Home could not hand her what it had grown on the same crystals since the phone last started. The pairing gave no measurable reasoning benefit on a turn. |
| The surface already runs the full turn offline. | Probe: surface boot 19 to 21 s; turns 0.1 to 2.9 s with home unreachable; no turn waits on the link. | Acceptance 1 and 3 already held; this change keeps them. |
| A competence limit, not a strata problem. | "If the kettle is unplugged, can it boil water?" gets silence in every configuration, the whole mind included. Turn 3 and 4 replies differ between runs regardless of the gate. | Reported honestly; not caused or fixed by this change. |

#268 adds `crystal_context_for_turn` in `aurora_live_experience.py`, which
reads `fk:*` facets from the canonical crystal registry through
`dimensional.concept_index`. It is the one reader live cognition uses outside
the crystal modules, and home's facet views are built through the same
reader, so the surface and home read her crystals one way.

---

## 2. Architecture: before and after

### Before

```
PHONE (surface-only)                               HOME (HP subsurface)
 turn pipeline ── reads ──> local copies of        authoritative stores
                            home's stores            ^
 write to home store ──> gate: DECLINED (lost)       | continuity uplink, integrated once
 10 writers ──────────────> local copy changed  ✗    |
 lived moments ── outbox ───────────────────────────-┘
                 <── growth (installed at start) ── home's stores
                 <── predictive frames (axis lenses, no facets)
```

### After

```
PHONE (surface-only)                                         HOME (HP subsurface)
 turn pipeline ── reads ──> local copies (+ her provisional   authoritative stores
                            view laid over them at start)       ^
 write to home store ──> store_write_path ──> provisional/<store>  | continuity uplink
                          (bounded, journalled, never sent as state)| integrated once
 lived moments ── outbox (durable) ─────────────────────────────────┘
                 <── growth (skips bytes her view grew from;
                      a replaced copy retires her view)
 raw input ───── outbox ───────────────> raw_input.json ──> idle home reads
                                                              its own crystals
                 <── facet_view (read-only, provenance) <─── facet_views_home.json
 next turn: her facets first, home's view beside them, marked as home's
```

Same crystals, same reasoning: the phone and home run the same
`recall_contextual_facets` on the same canonical registry. Home's view is
that read on home's newer crystals; nothing new is invented for it.

---

## 3. What changed, file by file

| Area | Files | What |
|---|---|---|
| Provisional view | `aurora_internal/aurora_store_ownership.py` | New gate class `provisional` (moves with her). `store_write_path(path, mode)` returns where a write lands: the store itself on a whole-mind device or for her own stores; `provisional/<store>` for a home-owned store on a surface-only phone; `None` (declined, counted) when the 96 MB budget is spent. A manifest records, per store, the canonical bytes the view grew from. `restore_provisional` lays the view back at start. Status on the hub. |
| Writers | `aurora_persistence_utils.py` (both twins), `aurora_toroidal_circulation.py`, `aurora_understanding_sediment.py`, `aurora_representational_resolution_base.py`, `aurora_expression_perception.py`, `aurora_grammar_engine.py`, `aurora_dream_trainer.py`, `aurora_interaction_memory.py`, `aurora_developmental_log.py`, `aurora_image_ingestion.py`, `aurora_internal/aurora_primitive_perspective.py`, `aurora_icc_ledger.py`, `aurora_strategic_horizon.py`, `aurora_pressure_ledger.py`, `aurora_reflective_readdressing.py`, `aurora_relation_pairs.py`, `aurora_reasoning_paths.py`, `aurora_unformed_patterns.py`, `aurora_live_lineage_journal.py`, `aurora_recursive_causal_reasoning_waveform.py`, `aurora_ontological_scaffolding.py`, `dual_strata/topology_tracker.py`, the bridge's relational claims | Write to `store_write_path(...)`. Snapshot writers rewrite their view; append writers append to it and never trim it (it is laid over home's copy by byte offset). |
| Declined on purpose | `aurora_universal_function_lineage.py`, `aurora_recommendation_hub.py`, `cers_deprecation.py`, runtime-fault timeline lines | Derived from code or operator-facing; home rebuilds them. Declined and counted, not kept. |
| Re-deciding fix | `aurora_internal/aurora_recommendation_hub.py` | On a surface-only phone the hub decides an item once per run and leaves aging out to home. |
| Start order | `flutter_app/.../aurora_bridge.py` | Growth installed, then her provisional view restored, then the gate armed, then organs load. |
| Growth | `dual_strata/home_growth.py` | Skips a store whose provisional view grew from exactly home's current bytes. |
| Handoff | `dual_strata/strata_link.py`, `strata_state_transfer.py` | The view is never pushed as state; a whole-state copy tolerates a file that vanished mid-copy. |
| Facet views | new `aurora_internal/dual_strata/anticipatory_facets.py`; `desktop/runtime.py`; `strata_link.py`; `aurora_live_experience.py` | Home builds a view per raw input while idle; the downlink relays it once; the phone caches it in its own store; a turn merges it read-only. |
| Hub | `aurora_hub.py`, `hub_panels.py` | Shows writes kept provisionally and the budget used. |

---

## 4. Dataflow

**A lived experience (offline or online).**
1. The turn runs entirely on the phone.
2. Each lived moment is stamped `(surface_id, epoch, seq)` and appended to the
   durable outbox (unchanged).
3. Each organ that updates a home-owned store writes to her provisional view.
4. When the link is up, the outbox drains; home admits each stamped moment
   once into its integrated ledger and its own stores.
5. Home's grown stores reach the phone as growth at its next start.

**A home facet view.**
1. The phone publishes the raw input it just heard (disposable, 30 s).
2. Home's resident reads it when its own live work is idle, once per input.
3. Home runs the same bounded facet read on its registry and writes a view:
   `view_id`, `input_id`, the words, the holder `epoch`, `at`, `expires_at`
   (10 minutes), `basis`, and per entry the facet address (concept, facet
   role, key), degree, occasions, and `evidence_class`: `earned`,
   `corrected`, `hypothesis` or `simulated`.
4. The downlink collector relays each unexpired view once.
5. The phone keeps the last 32 in `strata_link/facet_views.json` (its own
   store).
6. On each turn, after her own facet read, valid views (unexpired, same epoch,
   about words she is hearing) are merged: her entries first and unchanged;
   a home entry she does not hold is added with `source: home_view` and
   `read_only: true`; a home entry she does hold annotates hers with home's
   degree. One small file read, cached by modification time. Nothing waits.

A view is context, never a reply and never learned from. Her expression
decides what she says.

---

## 5. Offline protocol (directive section 8)

1. **Journal.** Lived moments go to the durable outbox, as before. This is
   what home admits; it is the authority.
2. **Bounded provisional view.** What her organs would write to home's stores
   is kept under `provisional/`, at most 96 MB. Past the budget a write is
   declined and counted (shown on the hub). A snapshot view holds the store
   as she now has it; an append view holds only the lines she added.
3. **Restart.** At start, after growth and before the gate: for each store in
   the manifest, if the local copy is still the copy the view grew from, the
   view is laid over it (snapshot: replaced; append: only the bytes not yet
   applied are appended, so a line is never applied twice).
4. **Reconnect.** The outbox drains; home admits each occurrence once.
5. **Home's growth wins.** When home's growth replaces a copy, the view on it
   retires at the next start. Home has admitted those same occurrences from
   the journal, so the integrated version is authoritative and there are
   never two. A growth row whose bytes equal what the view grew from is
   skipped, so an unchanged home never erases what she lived since.
6. **One state.** The view is hers and moves with her
   (`MOVES_WITH_HER`); it is never pushed as state to home. Ownership
   transfer stays the existing explicit, epoch-fenced handoff.

Known edge: if home's copy changes for an unrelated reason before her
journal has drained, her view on that store retires early. Nothing is lost:
the moments are still in the outbox and come back through home's growth
after they are admitted. Until then that store reads home's version.

---

## 6. Results

### Surface-only, home unreachable (real boot, copy of `aurora_state`)

| Measure | Before | After |
|---|---|---|
| Home-owned files changed on the phone | 10 | **0** |
| Writes declined in a short session | ~4,060 over 28 stores | 1 to 4 per store over 9 stores; recommendation actions about 3,900 before the fix (see below) |
| Writes kept in her provisional view | 0 | 100 over 23 stores (11.8 MB) |
| Boot | 19 to 21 s | 19.3 to 21.1 s |
| Turn time | 0.1 to 2.9 s | 0.97 to 3.4 s (same pipeline; varies with the sentence) |
| Restore at start | n/a | 0.04 s for 23 stores |

### Restart continuity (the test that matters)

Session 1 (home unreachable): "A zephyrine is a small blue kettle that sings
when the power is on." Then the phone restarts, still offline.

| | Lexicon at next start | Knows "zephyrine" | Knows "kettle" | Reply to "What is a zephyrine?" |
|---|---|---|---|---|
| Before (no restore) | 4,207 (unchanged) | no | no | silence |
| After (restore) | 4,234 | **yes** | **yes** | "I am zephyrine. I am truth. I am happy." |

She keeps what she learned offline. The reply itself is poor; that is her
current expression, not the strata.

### Paired benefit (home's facet views reaching the surface)

Home booted a copy of `aurora_state` as the whole mind, lived three teaching
turns about a zephyrine and a kettle, and wove its crystals as it does on
save (1,385 facets, 7.3 s). The surface booted a separate copy that had not
lived those turns, received home's views, and read three follow-up turns.

| Measure | Result |
|---|---|
| Home builds a view | 0.17 to 0.51 ms per input, 12 entries each, all evidence class "earned" |
| Surface reads her own facets | 0.02 to 0.05 ms, 0 entries (her copy holds no woven facets) |
| Surface adds home's view | 0.1 to 0.4 ms, 6 read-only entries per turn, marked as home's |

The path works end to end and never holds a turn up. What it carries is
weak today: the bounded read takes the words she hears in alphabetical
order, so its budget is spent on the commonest words ("can", "does",
"what") before "kettle" or "zephyrine" are read. How the read should choose
among the words she hears is a design question for her recall, not for the
strata, so it is left as it is and reported here.

This measurement also found that the live facet read returned nothing on a
real boot: it looked for the concept index on `DimensionalSystems` and
resolved ids in the concept crystal registry, while the index and the woven
`fk:*` facets sit on `DimensionalSystems.dps`. That is fixed in
`crystal_facets.recall_contextual_facets`, with a test on the real layout,
and it is what makes #268's read and experiential recall reach her woven
facets at all.

### Tests

Full suite, one lane, on this branch and on `main`:

| | Passed | Failed |
|---|---|---|
| `main` | 5,911 | 31 |
| This branch, before the last fixes | 5,977 | 33 |
| This branch, now | about 5,980 | 30 to 31, every one also failing on `main` |

Of the three that failed only here, two are fixed (home's view now reads
through the live cognition reader; the strata.1 verdict is refreshed from a
knowledge-graph build of this branch). The third,
`test_default_state_files_unchanged_by_boot_and_live_turn`, passes alone and
fails on `main` too when run after the same four test files: an earlier
test leaves the pressure ledger pointed at the real `aurora_state`. One test
that fails on `main` passes here
(`test_composites_and_exercises_match_the_source`).

---

## 7. Deploy and rollback

### HP Windows subsurface (home)

1. Stop the resident: end the `AuroraDesktop` task (or close the foreground
   `serve`). Wait until it has exited.
2. Back up the state directory (default `%LOCALAPPDATA%\Aurora\state`) to a
   folder outside it.
3. Either install the packaged app (the `Aurora-Windows-Installer` artifact
   from the "Desktop app installers" workflow, `Aurora-Setup-Windows-x64`,
   installed under `%LOCALAPPDATA%\Programs\Aurora`; see
   `AURORA_HOME_AND_SURFACE_SETUP.md` and `packaging/desktop/README.md`), or
   in the repository `git fetch` and check out the merged commit (or this
   branch for testing).
4. Start it again from the app, or with
   `.\.venv\Scripts\python.exe -m aurora_internal.desktop serve --open`.
5. Check the hub's strata panel: the store gate line and the new "kept
   provisionally" line appear once a phone has synced.

Rollback: stop the resident, check out the previous commit (or reinstall
the previous installer), start it, and restore the backup from step 2 only
if the state itself is in doubt. The only new home file is `strata_link/facet_views_home.json`; an older build
ignores it.

### Android surface

1. Let the phone sync with home first if it can (so its journal is drained).
2. Install the APK built from this branch (the `build-apk` workflow).
3. Open the app; the log line "Her provisional view on this start" appears
   only when there was a view to restore or retire.

Rollback: install the previous APK. An older build ignores `provisional/`
and keeps declining home-owned writes as before. Anything in the view that
home has not yet admitted stays in the outbox journal and still reaches home.
To drop the view entirely, delete `provisional/` from the app's state
directory while the app is closed.

---

## 8. What still needs the real hardware

1. Boot and turn times on the actual Android phone (all numbers here are
   from a Linux container).
2. A real offline period on the phone, then reconnect to the HP: the outbox
   drains, home admits each moment once, and the next start retires the views
   home has replaced.
3. Home building facet views while Sunni talks on the phone over the real
   link: how often a view arrives before the follow-up turn.
4. The provisional budget against the phone's storage, and write cost on
   flash.
5. A handoff from phone to desktop and back with a non-empty view.

---

## 9. Left as it was, with reasons

- **Form generation on the phone** (`generate_form` in `aurora.py`) still
  confesses the gap and leaves accommodation to home. Accommodation extends
  her language field, which is retained growth; running it inside a phone
  turn needs a latency measurement first so Sunni is never held up. It is a
  candidate for a budgeted run off the turn.
- **Evolution, curiosity, scout, clone harvest, Praxis** stay deferred to
  home at phone start as before.

## 10. Overlaps

- **Experiential recall directive V2** is carried here. It also works in
  `crystal_context_for_turn` and `recall_contextual_facets`. Home views are
  added by a wrapper (`_with_home_views`) after her own read, and home builds
  its views through `crystal_context_for_turn`, so a change to how recall
  reads facets carries into home views without edits here.
- **#268 and #272** are carried whole, at their current heads. If either
  changes before this merges, this branch takes the change in.
