# Aurora Persistence Inventory
# Authors: Sunni (Sir) Morningstar & Cael Devo
# Directive: PS1.1 (Persistence Integrity — No Silent Reversions), 2026-07-19

Permanent reference. Every persisted store reachable from `boot_aurora()`'s
live path, mapped for: what file(s) it can read from, whether it honors
`state_dir` (the parameter every isolated test/scratch boot is supposed to
be able to rely on), whether it has a dual-source silent-overwrite risk,
and whether `boot_aurora()` actually threads `state_dir` into it.

Trigger: Track CP found that `boot_aurora()` silently grafts an older OETS
generation over `aurora_state/aurora_oets_web.json` on every boot, even
with zero turns processed — 20/24 of S1.2's seeded words vanished. This
document is the full map that finding demanded before any fix is designed
(assess-before-architect, per PS1.1's own instruction).

## The confirmed root cause: `OETSPersistence` dual-path silent overwrite

`aurora_internal/aurora_identity_persistence.py:393-413` (`OETSPersistence`)
tracks **two** candidate files for the OETS ontology web:

- `primary_web_file` = `Path(__file__).resolve().parents[1] / "aurora_oets_web.json"`
  — a **repo-root**, `__file__`-relative path (`:410`), overridable only by
  the `AURORA_OETS_WEB_FILE` env var, **never by `state_dir`**.
- `snapshot_web_file` = `self.state_dir / "aurora_oets_web.json"` (`:412`)
  — the `state_dir`-aware candidate, i.e. `aurora_state/aurora_oets_web.json`,
  the git-tracked file this campaign has been editing throughout S1/M1/B1/P1.

`_web_candidates()` (`:417-429`) orders them `[primary, snapshot]`.
`load_web()` (`:533-711`) loops the existing candidates, loads the **first
one that parses successfully** (`primary` wins whenever it exists — no
generation, mtime, or lineage comparison of any kind), and — critically —
on success it **writes that same data back over every other candidate**
(`:691-701`), unconditionally, before returning. `save_web()` (`:440-531`)
also always writes to **every** candidate (`:522-527`).

Net effect: `primary_web_file` is authoritative, always. `snapshot_web_file`
(the git-tracked, campaign-edited file) is **read only if primary is
missing**, and is **overwritten** on every successful boot regardless of
what it contained. `primary_web_file` is gitignored (`.gitignore:49`) —
untracked, no history, shared by every process on this machine (including
any concurrent long-running "autonomous run" process), and **not
`state_dir`-scoped even when `boot_aurora(state_dir=scratch)` is called** —
`OETSPersistence.__init__(self, state_dir=...)` (`:402`) only threads
`state_dir` into `snapshot_web_file`, never into `primary_web_file`.

This is the exact mechanism behind:
- The original S1.2 seed data "loss" (a prior commit's git-checkout theory
  was a reasonable but incorrect guess — the real explanation is this file).
- The `relation_type="contradicts"` → `related_to` silent downgrade found
  investigating Track CP (loading `primary_web_file`'s stale generation,
  which never had the corrected value, then force-overwriting the fixed
  `snapshot_web_file` with it).
- Every "scratch-isolated" test boot in this campaign that touched OETS
  actually read/wrote the shared, untracked repo-root file — a test
  isolation gap of the same shape as the already-fixed `ContradictionLedger`
  bug, but with a live-data-loss consequence attached, since it also
  overwrites the git-tracked snapshot.

`boot_aurora()` correctly threads the real `state_dir` down to
`EnhancedStatePersistence(state_dir=state_dir)` (`aurora.py:20973`) →
`OETSPersistence(state_dir)` (`aurora_internal/aurora_identity_persistence.py:1657`)
— **the plumbing is not the bug**; the bug is entirely inside
`OETSPersistence`'s own candidate-priority and overwrite logic.

## Full inventory table

| Store / class | File(s) it can read from | `state_dir`-aware? | Dual-path silent-overwrite risk? | `boot_aurora()` passes `state_dir`? | Risk |
|---|---|---|---|---|---|
| `ContradictionLedger` (`aurora_ivm.py:1828-1851`) | `<state_dir>/contradiction_ledger.json` | **Yes (fixed, Track CP)** — `__init__(self, state_dir=None)` overrides class `STATE_PATH` at instance level | No — single path, already fixed | Yes (`aurora.py:20474`) | Fixed — reference baseline |
| `OETSPersistence` (`aurora_internal/aurora_identity_persistence.py:393-711`) | repo-root `aurora_oets_web.json` (primary, `__file__`-relative, gitignored) **or** `<state_dir>/aurora_oets_web.json` (snapshot) | Partial — constructor takes `state_dir`, but it only governs the *losing* candidate | **Yes — confirmed root cause.** First-that-exists wins on load, force-overwrite of all other candidates on both load and save, no generation/mtime/lineage arbitration | Yes, but `state_dir` never reaches `primary_web_file` | **Critical — PS1.2's primary target** |
| `LexicalMemory` (`aurora_expression_perception.py:263-480`) | `_DEFAULT_PATH` = repo-root `aurora_state/lexicon.json` (`__file__`-relative class attribute, `:269-270`) | **No** — constructor takes no `state_dir`/path param at all; `save()`/`load()` default to `_DEFAULT_PATH` whenever called with no explicit path | N/A (single path, but that single path is hardcoded and shared) | `ExpressionPerceptionEngine(contract)` (`aurora.py:20598`) constructs it with no override; live saves (`aurora.py:16740`, `:25279`) call `.save()` with no path arg | **Critical — same shape as `ContradictionLedger` pre-fix.** Every "isolated" boot's vocabulary writes actually land in the real repo's `aurora_state/lexicon.json` |
| `SourceTrustRegistry` / `ProvisionalStore` (`aurora_offline_resilience.py:38-217`) | module-level `_STATE_DIR` = repo-root `aurora_state`, `__file__`-relative | **No** — no `state_dir` param on either class | N/A (single path, hardcoded) | `ProvisionalStore()` instantiated with zero args inside `boot_aurora()`'s online callback (`aurora.py:21725`) | **High** — holds provisionally-trusted, not-yet-verified knowledge; both backing files are gitignored (`.gitignore:69-70`), so no git history either |
| `DimensionalSystems` embedded `Aurora625PressureMap` (`aurora_dimensional_systems.py:2314-2389`) | `state_dir` constructor default = repo-root `aurora_state`, `__file__`-relative | Partial — the class *has* a `state_dir` param and correctly-parametrized `save_state()`/`load_state()` methods, but... | No (single path per call) | ...`boot_aurora()` calls `DimensionalSystems(lattice)` with **no `state_dir`** (`aurora.py:20134`), so the constructor-time pressure-map cache load always hits the repo-root default even on isolated boots | **Medium/High** — narrower than the others; only the embedded cache leaks, the main DPS crystal save/load path is fine |
| `GrammarEngine` / `grammar_motifs.json` (`aurora_grammar_engine.py:1172-1176`) | `<state_dir>/grammar_motifs.json` | **Yes** | No | Yes (`aurora.py:20638`) | Safe — reference pattern |
| `log_relation_pairs_from_turn` (Tier-2 relation-pair log, `aurora_internal/aurora_relation_pairs.py:90-149`) | `<state_dir>/relation_pair_log.jsonl` | **Yes**, explicitly built this way in M1.1-A specifically to avoid this bug class | No | Yes, via `systems.get("state_dir")` (`aurora.py:14929-14932`) | Safe — but region tags it writes depend on `lexicon.entries`, so a poisoned lexicon can indirectly taint an otherwise-safe log |
| `log_envelope_shadow` (B1.1 shadow scorer, `aurora_internal/aurora_boundary_envelope.py`) | `<state_dir>/envelope_shadow_log.jsonl` | **Yes** | No | Yes | Safe — reference pattern |
| `aurora_contradiction_perception.perceive_contradictions` (Track CP) | reads `<state_dir>/relation_pair_log.jsonl` + `<state_dir>/aurora_oets_web.json` | **Yes** for its own reads | No new risk introduced, but its antonym source (OETS `opposite_of` relations) is only as reliable as `OETSPersistence` above | Yes | Safe on its own terms — currently starved by the `OETSPersistence` bug, not broken itself |
| `ThoughtContinuity` log (`aurora_thought_formation.py:919-991`) | repo-root `aurora_logs/thought_chain.jsonl`, `__file__`-relative | No | N/A | Module singleton, no `state_dir` | Low/vestigial — `_log_thought()` is now a no-op; the constant is dead code |
| `aurora_tool_mind.py` intention/identity-delta logs | repo-root `aurora_logs/tool_intention_log.jsonl`, `identity_delta.jsonl` | No | N/A | Write-only, never re-loaded as state | Low — pollution risk only, not a reversion risk |
| `_resolve_oets_web_paths()` (`aurora_daemon.py:42-95, 5477-5492`) | env var → repo-root `aurora_oets_web.json` → `<state_dir>/aurora_oets_web.json` | No `state_dir` param (daemon-global) | Read-only "first exists wins," diagnostic print only, no write-back | N/A — separate daemon process, not part of in-process `boot_aurora()` | Low (diagnostic-only) — mirrors the root-cause candidate order; worth watching if ever extended to write |
| `VOICE_CORPUS_PATH` (`aurora_voice.py:78-81, 1192-1200`) | repo-root `conversations.json` + `aurora_state/...` fallbacks | No `state_dir` param, env var override only | Read-only corpus-source selection, not authoritative learned state | N/A — separate voice daemon | Low — training-corpus input, not state reloaded as truth |

## Gitignored top-level (non-`aurora_state/`) state-like files

Same shape as the root-cause file: untracked, no git history, shared
across every process on this machine unless the code touching them is
made `state_dir`-aware.

| File | `.gitignore` line | Notes |
|---|---|---|
| `aurora_oets_web.json` | `:49` | The confirmed root-cause file (`OETSPersistence.primary_web_file`) |
| `conversations.json` | `:51` | Training-corpus source (`aurora_voice.py`), low risk (read-only corpus input) |
| `interval_corpus.json` | `:75` | Ad hoc training corpus (`run_intensive_intervals.py` / `aurora_daemon.py`), low risk |
| `large_batch.json` | `:76` | Same category |

Also gitignored but *inside* `aurora_state/` — expected to already be
`state_dir`-scoped, and mostly are, **except** `provisional_knowledge.json`
and `source_trust.json`, whose backing classes (`SourceTrustRegistry`/
`ProvisionalStore`, row above) still resolve them via the repo's own
`aurora_state/`, not whatever `state_dir` a given boot specified.

## Named candidates from the directive, confirmed

- **`lexicon.json`** — **not safe**. See `LexicalMemory` row above.
- **`grammar_motifs`** — **safe**. See `GrammarEngine` row above.
- **`relation_pair_log`** — **safe**. See row above; only indirectly exposed
  through the lexicon it reads from.
- **Seeded S1 relations** (`scripts/seed_abstract_regions_s1.py`) — writes
  directly to `aurora_state/aurora_oets_web.json`, i.e. exactly
  `OETSPersistence.snapshot_web_file`. This is precisely the file that
  gets silently overwritten by `primary_web_file` on the next boot — S1's
  seeded relations are not a separate bug, they are a direct symptom of
  the `OETSPersistence` root cause above.

## Scope for PS1.2

Per the directive's invariant requirement ("boot never silently discards
newer persisted state... per store, chosen from what PS1.1 shows each
store's actual role is — no blanket guess"):

1. **`OETSPersistence`** — primary fix target. Needs generation/lineage
   arbitration between `primary_web_file` and `snapshot_web_file` (or a
   canonical-source decision that retires the dual-path design), plus
   no-silent-reversion audit logging.
2. **`LexicalMemory`** — needs a `state_dir` constructor parameter,
   threaded from `boot_aurora()`, matching the pattern already used by
   `GrammarEngine`/`ContradictionLedger`(fixed)/Tier-2/B1.1.
3. **`ProvisionalStore`** — needs the same `state_dir` threading.
4. **`DimensionalSystems`** — needs `boot_aurora()` to actually pass
   `state_dir` into its constructor so the embedded pressure-map cache
   load stops defaulting to the repo-root path.
5. Log-only / read-only / offline-tool entries (`ThoughtContinuity`,
   `aurora_tool_mind.py` logs, `aurora_daemon.py`'s diagnostic path,
   `aurora_voice.py`'s corpus discovery) are lower priority — flagged
   here for completeness, not blocking PS1.2/PS1.3.
