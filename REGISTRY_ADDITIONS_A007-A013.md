# Known Fixes Registry — Additions (Session: Language Stack Repair + Fixed-Path Weld)
# Authors: Sunni (Sir) Morningstar & Cael Devo
# Append these entries to aurora-preemptive-hardening/references/known_fixes_registry.md

## FIX-A007: SemanticCrystalNode Legacy Facet Restore (ARCHITECTURAL)
Persisted semantic state may lack `audio_facet`/`visual_facet` (pre-facet seed
schema). `SemanticCrystalNode.from_dict` must derive them from `lane` via the
canonical `LANE_LABEL` mapping so restore never hard-fails and the 6-facet
crystal always boots. First seen: seed_sensory_crystals.py schema drift caused
`[SENSORY-CRYSTAL] Unavailable` on every boot.

## FIX-A008: Grammar Engine Write-Path Wiring (ARCHITECTURAL)
`GrammarEngine.observe_exchange()` is the ONLY write path for motif fitness.
It had a latent NameError (`tone`/`passion`/`drive` used but not declared as
parameters) proving it never ran. It must be wired post-turn in aurora.py AND
per-pair in corpus_runner passes. Without it: 0 promoted motifs forever, the
`>= 8 promoted` restructuring gate never opens, output degrades to plain join.
Rule: any new training entry point MUST call observe_exchange per exchange.

## FIX-A009: Lexicon Persistence (ARCHITECTURAL)
`LexicalMemory.save()` had zero call sites — all vocabulary died at process
exit, resetting to 28 seeds every boot. `_DEFAULT_PATH` was cwd-relative and
must stay anchored to the module directory (mirror GrammarEngine's pattern).
Rule: post-turn and end-of-training, always flush the lexicon.

## FIX-A010: Corpus Absorption Role Flattening (BEHAVIORAL)
Never absorb words as `role="noun", meaning="absorbed"` with no valence or
noncomp mapping — flattened words are invisible to noncomp-driven expression.
Use `infer_word_role()` / `infer_word_valence()` from
aurora_expression_perception and tag `lineage="corpus"`.

## FIX-A011: Daemon-less Training Field Energization (ARCHITECTURAL)
Subsurface tension comes from constraint drift driven by daemon wall-clock
cycles. Daemon-less training runs in a dead field (tension=0 → resonance=0 →
no FORMING attention → no meaning nucleus → ignition Stage 5 fails). Use
`aurora_training_pulse.TrainingPulse` to time-compress the daemon cadence
around every training exchange. NOTE: NoncompField exposes live axis pressure
under `status()['axis_pressures']` — `pressure_topology` does NOT exist
(aurora_language_field.py `_axis_pressures` still reads the dead key and
silently falls back to flat 0.3s — open item).

## FIX-A012: Corpus Format Visibility (BEHAVIORAL)
Aurora's training corpora use `[{"user": ..., "assistant": ...}]` pair format.
MotifMiner (mine_corpus AND mine_discourse) only understood ChatGPT-export /
`messages` formats — every existing corpus mined 0 patterns. Both miners must
include the user/assistant branch. After fix: batch_corpus.json mines 400
structural + 23 discourse patterns.

## FIX-A013: Corpus Runner API Contract (ARCHITECTURAL)
corpus_runner.py depends on three APIs that never existed on the live classes
(proof it never completed a run against the live stack):
  - `LexicalMemory.size` (property) — now implemented
  - `ExpressionPerceptionEngine.save_lexicon()` — now implemented
  - `AuroraSensoryCrystal.concept_registry_summary()` → {'total', 'by_stage'}
    — now implemented from the `_semantic` registry
Rule: before writing code that calls a method on a live system object, verify
the method exists on the class actually bound at runtime (the file contains a
dead duplicate lexicon class body — check which class `perception.lexicon`
really is).

## FIXED-PATH GUARANTEE (process rule)
All training MUST flow through paths that carry the weld:
  - Live turns: aurora.py post-turn block (FIX-A008/A009)
  - Corpus ingestion: run_corpus_ingestion's internal weld (pulse +
    observe_exchange in observer AND responder passes + final flushes)
  - Canonical entry: `aurora_experiential_sim.py` (curriculum or --corpus)
Any NEW training entry point must either route through run_corpus_ingestion /
_run_live_response_turn, or explicitly wire TrainingPulse + observe_exchange +
lexicon/motif flushes itself.
