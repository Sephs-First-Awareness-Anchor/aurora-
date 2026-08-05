# Build 591 Bare Interrogative OBJECT-Slot Repair

This correction closes the path where a question marker such as `who` could
fall through `infer_word_role()` as a noun and be inserted verbatim into a
declarative OBJECT slot.

## Corrected modules

- `aurora_expression_perception.py`
  - Classifies core interrogatives as non-noun grammatical roles.
  - Normalizes question punctuation in `infer_word_role()`.
  - Rejects bare interrogatives at `_bind_slot_from_frame()`.
  - Rejects stale persisted lexicon entries that still label wh-words as nouns.
  - Applies the same exclusion to legacy primitive, semantic, cluster, and
    abstract template fillers.
  - Preserves multiword embedded clauses such as `who made Aurora`.

- `aurora_internal/aurora_proposition_frame.py`
  - Sanitizes bare interrogative objects from claim, turn-local claim, and
    anchor frame sources before they reach composition.

- `aurora_internal/aurora_semantic_probe_battery.py`
  - Adds `whose` to the shared structural-function-word set.

- `tests/test_cir_wh_object_slot_guard.py`
  - Adds 64 direct regressions covering role inference, punctuation, direct
    frames, claim frames, turn-local frames, anchor frames, stale lexicons,
    legacy template filling, and valid embedded clauses.

## Verification

- 218 focused proposition/composer/semantic tests passed.
- 20 non-runtime communication-integrity tests passed.
- A live `runtime_profile="surface"` boot answered `Who made you?` with:
  `My creator is Sunni (Sir) Morningstar.`
- The malformed composer candidate was empty and did not override the grounded
  relational response.

A separate full-profile governance test remains expensive because build 591's
manual code-lineage assimilation can exceed the execution window. The surface
runtime and all tests directly covering this correction completed successfully.
