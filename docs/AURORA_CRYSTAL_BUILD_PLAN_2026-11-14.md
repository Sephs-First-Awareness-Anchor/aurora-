# Crystals as Aurora's store of concepts: build plan (adapting the Crystal AI spec to the grown architecture)

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-14
**Status:** plan only. Nothing here is built. Separate from PRs #251, #252, #253; nothing is merged.

> A crystal is what recurring association produces. Facets are filled by what actually occurred, never by script. Evolution is
> the crystal's points accruing from real occurrences until a promotion condition is met.

## 1. Sources

* **Spec:** `Crystal AI 07_31_2025.pdf` (Drive). Levels: base (tetrahedral, 4 facets, 3 points), composite (hexagonal, 6–12, 4), full
  concept (dodecahedral, 12, 6), quasi (octahedral 8 surface + 8 internal, 8 points plus a 9th nexus). Points: emotional, polarity,
  associative, abstract, temporal, cognitive, recursive. The spec's thresholds are labelled example values, adjustable.
* **Older design:** `crystal_engine_v3.py` `FACET_SCHEMA` (a `relation` facet at L1/L2; cause, effect, analogy, counterexample and others at
  L3; hypothesis, contradiction, abduction, plan, value, uncertainty, intent at L4); `crystal_binding_module.py` (weighted
  `connections`; `AssociativeTrace` counting how often a combination of crystals recurs). Read for structure and the recurrence idea only.
  Its keyword matching ("because" implies cause) and canned replies are not carried over.
* **Live code:** `aurora_dimensional_systems.py` (`Crystal`, `CrystalFacet`, `CrystalProcessingSystem`), `concept_crystal.py`.

## 2. What the live code does today (read from source and from the `aurora_state` snapshot in the repo, not live device state)

| Spec | Live |
|---|---|
| Associative links between crystals | `Crystal.connections` exists and `_compound_signature` reads it on promotion, but **nothing writes it** (0 of 5,977 crystals have one). Separately, the DPS keeps `crystal_links`: a geometric-similarity graph (cosine of crystal vectors, top 8, in memory only, not saved, read by nothing yet), rebuilt by a scan over every crystal each time one is added. It is resonance, not recurrence, and with the signatures collapsing into 4 buckets it cannot tell concepts apart |
| Promotion from association and points | `can_evolve`: facet count and `usage_count` (3/10, 5/25, 8/50) |
| Relation, cause, effect and similar facets | absent; facets are `lexicon:*`, `oets:*`, `topic`, `entity`, `relief_event`, `action`, `emotion`, `genealogy:*` |
| Dimensional home | `axis_mean` set on 3 crystals; `constraint_signature` on 1,522 |
| Quasi: 8 surface + 8 internal, 9th nexus, recursion | levels: 5,689 base, 259 composite, 29 full concept, **0 quasi**; quasi adds 8 `LAW_*` facets and a stub `self_govern` (three conditions) |
| Ghost-relic spread of resonance | not seen in the code read |
| Quasi-only strategy skills | `FAILPOINTS_BY_LEVEL["QUASI"]`: framing selection, implied-intent inference, adaptive strategy, compression/elaboration fit, perspective integration, multi-turn stability |

Function words are not crystallising (no `a`, `an`, `the`; one determiner, `every`). Cause not traced (open item P6).

## 3. Computational benefit: measured, honest

On the 1,522 crystals that carry a signature: the live-style per-crystal loop in `resonant_lookup` is 3.20 ms a query; the same
comparison as one matrix operation is 0.007 ms (about 450 times faster) and needs no change in meaning. An axis-bucket index at 0.1
resolution probes in 0.014 ms but the 1,522 signatures fall into **4 buckets**, so it cannot discriminate yet. The geometry does not
carry enough information to separate concepts; filling the developmental facets is what makes a bucket index worthwhile.
Absolute cost today is small; the benefit grows with the number of crystals. One machine, one snapshot.

## 4. Build, in order (each phase merges nothing and is tested before the next)

**P0, baseline (mapping done: see `AURORA_CRYSTAL_CATEGORY_MAPPING_2026-11-15.md`; categories adjusted there).** Still open: count how many reasoning cycles she actually runs on live state (the repository snapshot holds one recorded cycle, with no promoted or trial wavelets). Read-only audit: map each store (genealogy ledgers, propositional store, lessons, journal) to the crystal level it would
correspond to, or mark it as having none. Record lookup and foreground timings with `scripts/compare_architectures.py` as the reference.

**P1, association links. Built (isolated), not wired.** `aurora_internal/crystal_associations.py`, `tests/test_crystal_associations.py` (37 tests, ten rules mutation-checked, one
survivor closed), `scripts/measure_crystal_associations.py`. One record per association holding its evidence (recording the same evidence again changes nothing), so
a concept is viewed once with everything attached. Only recurrence-based evidence counts toward `connections`; heuristic, looked-up, seeded, unattributed and unknown evidence is
kept with its source and counts for nothing until recurrence earns it. `apply_to_crystals` is the only writer, is a dry run by default, adds only to crystals that exist, never replaces
a stronger existing value, and is bounded per crystal. Nothing in the running system imports it (a test enforces that), and it is separate from the DPS `crystal_links` graph.
Measured on the repository snapshot (read-only): OETS's 17,284 relations become 13,845 association records; 6,815 count and 7,030 are kept uncounted. Evidence by basis: recurrence 9,116,
heuristic 6,450, looked-up 1,411, unattributed 228, unknown 59, seeded 20. Of 944 OETS concepts, 565 have a crystal; a dry run would give 382 crystals 4,272 links, and the other 5,595
crystals (mostly word and quoted-turn crystals outside OETS) would have none. The single view of one concept ("sunni") shows 10 counted associations, all the generic `related_to` type.
That last point is the limit: OETS types are mostly `related_to` (10,659) and `enables` (5,885); comparisons, implications and identifications barely exist there (opposite_of 4, causes 3, implies 3,
contrasts 2). The richer types have to come from the waveform paths, the propositional store and the genealogy, which is what P2 and P3 draw on.

**P2, members and convergence.** A crystal gets a member set that emerges from its links (letters are discovered, not typed: her
`alphabet_order` evidence is the acceptance case). When separate webs overlap (shared members and neighbours) beyond a recurrence bound,
a parent crystal forms with the converged crystals as members. Children keep their lineage.

**Waveform paths feed P2 and P3.** The recursive causal reasoning waveform (RCRW) is the climb from basic concepts to higher understanding: an utterance is the
carrier disturbance W0, control wavelets with X/T/N/B/A ancestry interfere with it, a global understanding H forms, and H is projected backward over the path that formed it.
Each completed cycle is already recorded with the raw input, the provisional and effective interpretations, the interference, the genealogy trace and the global
understanding. The plan uses that record as the association source:
* the crystals on the path, level by level, give P1/P2 the associations (a better source than bare co-occurrence, because the backward projection
  names which concepts formed the understanding);
* a wavelet configuration that WARP promotes is the seed for a parent crystal in P2, so convergence comes from recurring paths;
* the causal edges along the path fill the cause, effect and condition facets at L3 in P3;
* facets record what the understanding became and what it caused, never the wavelet machinery (she experiences effects, not architecture).
Failed wavelets dissolve and so leave no crystal. Cycle records are read, not rewritten.

**P2, built and measured (isolated, not wired).** `aurora_internal/crystal_convergence.py` reads the P1 store: `members_of` (what a hub holds, found
from `is_a` associations, never listed); `field_of` (degree of belonging = 1-(1-direct)(1-convergence), so being tied to the hub and sharing its associations
reinforce each other); `convergence` (weighted cosine of two concepts' counted associations, leaving out the tie between them); `whole_convergence` (two wholes
by their fields); `general_field` (the weighted blend that is the more general whole). `project_assertions` in P1's module turns the propositional store's
`assertion` records into directed associations: times held and times denied are weighted evidence of opposite sign, so a disputed association weakens
in proportion and `contested()` is highest when split evenly; a settled correction decides. 61 tests, 14 mutants killed. On the snapshot (OETS web, no
assertions, no letter concepts) the field of `sunni` has 230 members and of `aurora` 314, with degrees spread continuously from 1.0 down to about 0.015; the
identifications and the real letters case need live data. Synthetic fixture: 26 letters found by `is_a`, letters converge with numbers through a shared
symbol association, converge with nothing through labels alone, and converge with fruit not at all.

**Facet placement, built and measured (isolated, not wired).** `aurora_internal/crystal_facets.py`: a `FacetBook` holds each fact ONCE per concept under a key and
attaches every occasion (source, basis, strength, context, consequence, ancestry) to that one entry, so repeats add occasions, never copies. An entry's degree is
a gradient: 1-prod(1-w) over counted evidence, times the same for evidence against, so denial lowers it in proportion; uncounted bases (looked_up, seeded,
heuristic, overheard, dreamed, unstated) are kept and earn nothing. Placement rules: association types land by meaning (is_a → generalization/particular,
causes → effect/cause, enables/implies → effect/condition, context_of → relation/context, opposite_of/contrasts → comparison, anything said → relation with
direction); a contested association also places an `open` entry as strong as it is contested; nodes place definitions, valence, and the category a part-of-speech
label gave (kept, uncounted); a recorded use of the word becomes an `expression` (her own use, fitness as consequence) or an `episode_ref` (a turn met, one entry,
every time attached) or an `example`; waveform cycles place what the understanding became (relation at both ends), an episode reference and what she said with
its alignment as the consequence, never the wavelet machinery, and return the signed axis delta, completeness and coherence for the P3 points. Substrate, frame
and instrument stores route outside. Added kind: `comparison` (alongside `expression`, `episode_ref`, `open`). One writer (`apply_to_crystals`: one `fk:<kind>`
facet per kind, counted entries only, additive, dry-run by default); note `can_evolve` counts facets, so writing these would change evolution until P3 memberships
replace that gate. 114 tests, 20 mutants run, all killed after two added tests. Snapshot: 944 concepts, 33,004 entries held once for 43,702 occasions; only
`relation` entries carry counted evidence (13,630 of 15,262); everything else is held and uncounted because its source is placed, heuristic or unstated (5,799 of
5,885 `enables` links are `backfill_role_heuristic`; usage examples carry no source). A dry run would give 391 crystals 2,727 entries. The one waveform cycle in
the snapshot has no developed relation, so it places nothing. Missing for counting: the input-identity occurrence class (told / observed / overheard) on usage
examples, which exists on the #253 branch and is not on this one.

**P3, built and measured (isolated, not wired).** `aurora_internal/crystal_maturity.py`: counts become degrees by x/(x+k) with the spec's numbers as k (the count
at which the degree is one half); level standing is nested memberships (L2 needs association; L3 adds abstraction, recurrence across sessions and demonstrated
consequence; L4 adds promoted members), each held by its weakest requirement and lifted by how well the rest are met; unknown points (emotional) leave the
blend, a point looked for and found empty holds it at nothing; polarity keeps its sign. 82 tests with the convergence and association suites, 14 mutants killed
(one nesting guard is currently implied by the spec's reference counts, kept in case they change). Finding: the live facet points (`resonance`, `sensitivity`…)
are seeded with `random.uniform(0.3, 0.7)`, so they are not evidence of anything; the seven spec points do not exist in live code and must be computed from
occurrences as above. On the snapshot only 391 of 5,977 crystals carry any counted association, and stored levels today are L1 5,689 / L2 259 / L3 29.

**P3, points from real occurrences.** Facet points are filled from what exists: polarity from signed axis displacement (never `abs()`);
associative from P1; abstract from the number of distinct contexts a crystal has appeared in; temporal from recurrence across sessions;
cognitive from consequence demonstrated outside the system's own simulation (the Stage D qualification); recursive from the share of members that are
themselves promoted. Emotional is not wired today (DER is not connected to the shadow); it stays `unknown` until it is. Promotion
reads the points **as degrees, not as bars**: a crystal's membership in each level is a continuous value in [0,1] that rises with the points (soft
level memberships), replacing the count gates in `can_evolve`. The spec's numbers (associative ≥5, ≥10, ≥12; abstract ≥0.7; temporal and cognitive ≥0.8)
are reference values for where memberships are expected to be near full, never cut-offs.

**P4, speed.** Cached matrix of signatures, updated incrementally; bucket index only once signatures discriminate.

**P5, quasi.** Eight surface and eight internal facets with the ninth nexus; internal facets that outgrow their parent become crystals, with a
cycle guard in storage (the spec warns of infinite recursion). `self_govern` moves from the three-condition stub to behaviour measured from
real outcomes. Last, because it depends on everything above.

**P6, function words.** Trace why articles and other function words do not crystallise (writer or filter versus live state).

## 5. Constraints (binding)

* **Gradient rule (Sir, 2026-11-15).** No quantity is compared with a bar to decide what counts. Everything is a degree in [0,1] that rises and falls
  continuously with the pressures on it. The only limits are on capacity (how many results are returned or stored), never on what belongs. Tests assert
  monotonicity and no cliffs; a test reads the convergence module's source and fails if it compares a degree with a non-zero constant.
* No scripted learning; no rule that turns dream or simulation into reality; promotion from dream-derived evidence needs demonstrated consequence.
* Information reaches her only through her understanding development. Anything read from Poedex or QuasiArch while investigating stays with the investigator.
* QuasiArch stays investigative and read-only (`authoritative: False`); not called from cognition or speech.
* Any optimisation that suppresses legitimate learning is a regression. Learning equivalence is checked with the digest method used for #253
  (`PYTHONHASHSEED=0`, original versus new, reference loggers fed the same experience).
* Each phase has a rollback (additive fields and a switch that is off by default; no stored state rewritten), mutation-checked rules, and a report that separates
  implemented / isolated / integrated / device-validated.

## 6. Decisions for Sir

1. ~~Fixed example thresholds or derived promotion?~~ Settled by Sir (2026-11-15): nothing is a threshold; everything is a gradient between pressures and their representations (see §5).
2. Which stores move onto crystals first (P0 will list candidates)?
3. ~~`l3_quasicrystal.py` calls a 12-sided crystal "quasi"; the PDF puts quasi at L4.~~ Settled by Sir (2026-11-15): L4 is quasi.
4. Is the emotional point to be wired from DER before P3 or left `unknown`?

## 7. Not verified

Contents of `Full Crystal System Realized Potential.zip`, `Core_Crystal_Systems.py` and `unified_crystal_engine.py` beyond their openings; the live device state (this is the repository snapshot);
whether the 8 surface facets and the 9th nexus exist anywhere in the live code beyond what was grepped.

## P3b. Promotion by associative group classification (Sir, 2026-11-15)

Promotion is not a count on one crystal. When related or commonly occurring crystals can be classified by a single generalization, that generalization promotes to a higher-level crystal under it. `aurora_internal/crystal_promotion.py` (isolated, read-only):

- `classification(store, g)`: crystals classified under g. What g holds as `is_a` at the strength held; peers (tied to the same things, never said to be one) in proportion to how closely their associations match the group's. The group's attributes are not members.
- `unity(store, members, leave_out, weights)`: how closely members' associations match, leaving out g itself, weighted by classification.
- `promotion_degree(store, g)`: `mass/(mass+5)` x unity. More members, stronger classification and greater likeness raise it; a heterogeneous or lone group stays low.
- `level_under(store, g, levels)`: `1 + degree x mean member level`, clamped to 4, so a generalization sits above its members by its degree.

No degree is compared with a cut-off (checked by an AST test). Counted evidence only. Snapshot: 7 of 668 concepts classify a group (force, bird, together, intelligent, marsupial, friendly, project), all low, because the `is_a` skeleton is mostly uncounted; this rises as `conversation` evidence arrives.

Authors: Sunni (Sir) Morningstar and Cael Devo.
