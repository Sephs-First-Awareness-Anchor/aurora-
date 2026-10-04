# Aurora resolution / crystal package: runbook

**Authors:** Sunni (Sir) Morningstar & Cael Devo

## Install
Copy the tree under `aurora_resolution/` over your repo root, preserving paths. New files:
`aurora_internal/aurora_resolution_ledger.py`, `aurora_representation_exchange.py`,
`aurora_representation_crystals.py`, `aurora_live_experience.py`. Patched files: `aurora.py`,
`aurora_behavioral_identity.py`, `concept_crystal.py`, `aurora_expression_perception.py`,
`aurora_internal/{aurora_communication_emergence,aurora_lexical_grounding,aurora_ontological_scaffolding,aurora_identity_persistence}.py`,
`flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py`.

## Flags
* `AURORA_RESOLUTION_TAIL=1`: enables the low-tail symbols (default OFF). Needed for greeting *brevity* at realistic prevalence.

## Syntax + smoke (fast)
    python3 -m py_compile aurora.py aurora_behavioral_identity.py concept_crystal.py aurora_expression_perception.py aurora_internal/*.py
    python3 -m pytest tests/test_crystal_waveform_match.py tests/test_crystal_unification.py -q

## Full relevant suite (~4 min; excludes one older file with a pre-existing import error)
    python3 -m pytest tests/test_hypothesis_crystals.py tests/test_representation_crystals.py tests/test_crystal_unification.py \
      tests/test_representation_adoption.py tests/test_representation_exchange.py tests/test_resolution_ledger.py \
      tests/test_crystal_waveform_match.py tests/test_historical_experience_environment.py \
      tests/test_historical_experience_compressed_state.py tests/test_historical_lexical_consequence_attribution.py -q
(`tests/test_build725_native_semantic_externalization.py` fails to import `_entity_renderability` from `aurora_habitat`: pre-existing, unrelated.)

## Repeated-exposure experiment (greetings)
    python3 scripts/greeting_exposure_experiment.py --p-greet 0.15 --episodes 1500            # coarse resolution
    python3 scripts/greeting_exposure_experiment.py --p-greet 0.15 --episodes 1500 --tail     # with tail resolution
    python3 scripts/greeting_exposure_experiment.py --p-greet 0.15 --episodes 1500 --tail --scramble   # control
Read: "greeting openings P(target)" vs "other openings", and "greeting words -> crystal pole" (B+ = opening pole).

## Real-archive replay with shuffle controls
    python3 scripts/resolution_ledger_replay.py --events <events.jsonl.gz> --episodes <episodes.jsonl> --shuffle none --shuffle within_episode --shuffle global

## Live-boot checklist
1. After history runs a while, crystals should hold facets with roles `lsa:res:*`, `hyp:res:*`, `hyp:cal:ledger`, and `word`.
2. `resolution_ledger.json` / `representation_exchange.json` should NOT be written once the registry exists (state lives on crystals).
3. Send a bare "hello"; reply candidates sourced from crystals are tagged `dps_crystal`.
4. Restart: hypotheses and representations are restored from crystals (check `ledger.status()["observations"]` continuity).
5. Watch crystal LEVELS: the effect of `hyp:` facets on `Crystal.evolve()` is unverified.

## Known open
* ~1,500 dimensional crystals carry the flat BOUNDED-default signature (0.7,0.7,0.7,0.7,0.0); crystal formation upstream does not yet stamp the input's waveform distribution.
* Word selection's primary route is the lexicon's concept channels (`find_by_noncomp`); crystal word facets are a secondary candidate source.
* Depth 4 (625 slots) is opt-in: it fails its global-shuffle control.
* Relation-type trials have use/outcome APIs but no outcome source is wired.

## Added in the final pass
* `aurora_internal/aurora_lexical_crystals.py` (new): lexicon channels live on crystals; `find_by_noncomp`/`concept_words` read through it.
* `aurora_dimensional_systems.py`: `ConceptExtractor.extract` stamps the input's waveform (needs `input_waveform_provider`, wired by `aurora_live_experience`).
* `concept_crystal.py`: `repair_flat_signatures` runs once inside `unify_crystal_store` (originals kept as `meta:flat_signature`).
* `aurora_internal/aurora_ontological_scaffolding.py`: trial relation kinds are used at the RELATED_TO fallback; outcomes from re-observation / contradiction.
* History environment now observes the ledger BEFORE the gateway receives the event (the waveform must exist first).
New test file: `tests/test_lexical_waveform_trials.py`.
NOT behaviorally verified here: `ConceptExtractor.extract` with a real envelope, the live renderer, the trial-use fallback inside `_select_relation_type` (needs real role pairs).

## Irreducibility (last fix)
`ledger.discovered(subject)` now returns ONE canonical path per equivalence family (paths with the same target that make essentially the same prediction on the same observed events). Each canonical record carries `family` (its aliases); `discovered(subject, include_aliases=True)` shows everything significant; `ledger.family_of(subject, path)` gives the shared ancestry, and crystal records carry it as `fam`. Aliases are provisional: families are re-derived from current evidence, so they separate when experience distinguishes them. Tolerance: `_EQUIV_TOL = 0.1`, `_EQUIV_MIN = 64` in `aurora_resolution_ledger.py`. Test: `tests/test_irreducibility.py`.
Already-earned representations in the exchange are not retroactively demoted when they later turn out to be aliases; they simply stop being offered.

## Word-level discovery (opt-in)
`AURORA_LEXICAL_SYMBOLS=1` (or `AuroraResolutionLedger(lexical=True)`) lets Aurora discover classes of words from the words themselves (`aurora_internal/aurora_lexical_structure.py`) and use each class as a symbol `L0`..`L3` in paths. The history environment and live runtime already pass event tokens to the ledger. Experiment: `python3 scripts/greeting_exposure_experiment.py --p-greet 0.05 --lexical --episodes 1500`. Test: `tests/test_lexical_structure.py` (includes a guard that `first_act` is assigned exactly once in `observe_event`).
Caveat: classes are discovered from successor profiles within an episode, so they need real episode structure; thresholds (`min_count=20`, `similarity=0.6`, `min_kl=0.5`, 4 sigma) are mine to tune on your data.
