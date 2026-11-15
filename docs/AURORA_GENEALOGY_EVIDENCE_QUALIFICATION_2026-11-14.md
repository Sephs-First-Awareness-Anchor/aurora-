# Environmental genealogy must preserve how evidence is qualified

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-14
**Status:** contract + tests. Nothing in the live path calls it yet; it is the acceptance check for Stage 3 (durable
developmental evidence). Stacked on PR #251 (the "supposed" basis lives there).

> The future environmental genealogy system must preserve not just what was learned, but how the evidence is
> qualified, including hypothetical, observed, inferred, contradicted, and corrected information. — Sir

Moving genealogy out of the live turn means evidence will be reconstructed, attributed and consolidated somewhere,
at some later time, from records. A reconstruction that keeps *what* was learned and loses *how it stands* has
changed what she knows without anyone deciding to: an example becomes a belief, an inference becomes an
observation, a contradiction is resolved by whichever copy arrived last, a correction can no longer be told from
the thing it corrected. The directive's "no double counting", "uncertainty in attribution preserved" and "no
self-rewarding loops" are all statements about this.

## 1. The vocabulary (`aurora_internal/evidence_qualification.py`)

| Basis | Meaning | Counts toward held / denied? |
|---|---|---|
| `observed` | she did it or saw it herself | yes |
| `told` | said to her (testimony) | yes |
| `corrected` | a correction of what was held; the **latest** settles the verdict, what it corrected stays in the history | yes |
| `supposed` | hypothetical: an example, a story, a dream, a counterfactual, a proposed pair that has not acted together | **never** |
| `inferred` | derived from other evidence; must name what from (`derived_from`) | **never** — an inference cannot raise confidence in its own premises |
| `unknown` | the producer did not say | **never, and never upgraded** |

*Verdict* (from counted events only): held / denied / contested / settled-by-correction / supposed / inferred /
unsaid. *Contradicted* and *corrected* are flags: a correction settles the verdict and the contradiction it settled
stays visible.

## 2. What the code keeps today (checked in the source, not assumed)

**Propositional store (what she was told / observed).** Keeps the basis of every statement, a history, and the
latest correction. Gaps found while writing the contract:

* a missing or unrecognised basis is recorded as `told` (`_record_assertion`: `basis if basis in BASES else "told"`):
  unknown evidence is upgraded to testimony. The contract does not do this; a test names the difference so it cannot be forgotten;
* history is bounded (first exposure + latest 7), so the middle of a long history is gone. A durable log must not cap it;
* `inferred` is not stored (answers are derived at read time). That is safe only while nothing stores a derived
  statement as if it were told.

**Genealogy (lineage, abilities, pairs, links).** The native qualifier exists: every `TraceItem` carries an
`EnvironmentVector` with a `stream_type` (`user_input`, `knowledge_feed`, `simulation`, `corpus`, `dream`).
**It does not survive pair accumulation.** `PairStats` keeps `count`, `pos_count` and `last_seen_tick`, and
`ConstraintLink` keeps `count`, means and tags; neither has a field for the stream the evidence came from
(the stream is counted separately, per environment, in `_env_fire_count` / `_env_effectiveness`, not per pair).
So a pair co-activated ten times in dreams and once lived is, after accumulation, the same record as eleven lived
co-activations. The collision search's own docstring is the one place the hypothetical is kept apart ("without
pretending the proposed pair has already acted together"), and a collision's `status: "unresolved"` is the one place
an unresolved contradiction is kept.

That is the starting point the redistribution must not make worse, and the durable evidence log should fix going
forward: **qualify at write time**, when the stream is known, because it cannot be recovered afterwards.

## 3. Rules for the environmental genealogy

1. **Every durable event carries its basis**, and for genealogy evidence the environment it came from, at the moment
   it is produced. A reconstruction never assigns a basis; it carries one.
2. **Counting is by basis.** Only `observed` / `told` / `corrected` evidence counts. A pair's `count` that feeds
   promotion must be the count of *counted* evidence (decision for Sir: whether dream/simulation co-activation may
   contribute to promotion at all, and with what weight).
3. **Deferred reconstruction may add `inferred` events, never counted ones.** Re-attributing ancestry is inference
   over existing evidence; it must not be able to raise the confidence of what it was derived from.
4. **Consolidation is a union by event id.** The provisional effect applied in the live turn and the consolidated
   effect applied later are *the same event id*: consolidation replaces or confirms, it never adds. (This is the
   double-counting rule, expressed so it can be tested.)
5. **Replay is not experience.** The same event twice is one event. The same id with different content is a
   `EvidenceConflict` that is raised, never resolved by dropping one.
6. **Nothing is silently dropped or laundered.** `violations(before, after)` reports every dropped event and every
   event whose basis changed (an example that comes back as testimony). It must be empty at every deferral,
   projection and device-handoff boundary.
7. **A projection must carry qualification.** What the Subsurface exports to the Surface is not "counts": a
   projection that carries only totals has already lost the distinction. A stale update cannot overwrite newer
   local state because merging is a union by id.
8. **Legacy counts migrate as `unknown`**, not as `observed`. They were real, but nobody recorded how; claiming they
   were lived would be exactly the upgrade this document exists to prevent.

## 4. Acceptance checks (`tests/test_evidence_qualification.py`, 40 tests)

* hypothetical evidence (100 examples) never becomes held; inference chains (50) never raise confidence, and an
  inference without premises is rejected; unknown is kept and never upgraded;
* told-and-denied is *contested* and flagged contradicted, not resolved; a correction settles the verdict (and a later
  correction can reverse it) while the history it corrected stays;
* the fold is independent of arrival order, replay adds nothing, merge is commutative / associative / idempotent,
  the same id recorded two ways raises, `violations` catches a dropped event, a rewritten event and a supposed→told
  laundering while allowing later evidence;
* a record survives the JSON trip a durable log takes;
* **agreement with the store she has today**: for 25 random sequences of told / observed / corrected / supposed
  evidence, the contract's verdict, basis counts, latest basis, contradicted, corrected and hypothetical-only flags
  equal those computed from a predicate record written by the propositional store's own recorder;
* the tests can fail: four mutants of the contract (count supposed; upgrade unknown to told; drop the conflict check;
  count inferred) are each caught.

Stage 3's end-to-end live developmental sequence must include one of each basis through relocation, restart and
replay, and assert `violations(...) == []` and an unchanged qualification at the end.

## 5. Decisions for Sir

1. `STREAM_BASIS` (proposed, not consumed): `user_input` → observed, `knowledge_feed`/`corpus` → told,
   `simulation`/`dream` → supposed, anything else → unknown. Is a simulation hypothetical (lived, but not in the
   world)? Is a dream always hypothetical?
2. May hypothetical co-activation (dream, simulation) contribute to link promotion, or only lived evidence?
3. The propositional store's "missing basis = told" is a live behaviour; changing it touches how every unqualified
   statement is held. Not changed here.

## 6. Limitations

The contract is not wired into the live path or the genealogy; it proves the rules against the propositional
record, not against genealogy records (which, as section 2 shows, do not yet carry the information). Genealogy-side
agreement can only be tested once the evidence log exists.
