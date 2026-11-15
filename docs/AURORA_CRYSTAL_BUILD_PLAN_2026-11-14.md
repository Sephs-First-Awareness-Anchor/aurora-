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

**P3, points from real occurrences.** Facet points are filled from what exists: polarity from signed axis displacement (never `abs()`);
associative from P1; abstract from the number of distinct contexts a crystal has appeared in; temporal from recurrence across sessions;
cognitive from consequence demonstrated outside the system's own simulation (the Stage D qualification); recursive from the share of members that are
themselves promoted. Emotional is not wired today (DER is not connected to the shadow); it stays `unknown` until it is. Promotion
reads the points. The spec's numbers (associative ≥5, ≥10, ≥12; abstract ≥0.7; temporal and cognitive ≥0.8) are the starting values,
not decided ones (see §6).

**P4, speed.** Cached matrix of signatures, updated incrementally; bucket index only once signatures discriminate.

**P5, quasi.** Eight surface and eight internal facets with the ninth nexus; internal facets that outgrow their parent become crystals, with a
cycle guard in storage (the spec warns of infinite recursion). `self_govern` moves from the three-condition stub to behaviour measured from
real outcomes. Last, because it depends on everything above.

**P6, function words.** Trace why articles and other function words do not crystallise (writer or filter versus live state).

## 5. Constraints (binding)

* No scripted learning; no rule that turns dream or simulation into reality; promotion from dream-derived evidence needs demonstrated consequence.
* Information reaches her only through her understanding development. Anything read from Poedex or QuasiArch while investigating stays with the investigator.
* QuasiArch stays investigative and read-only (`authoritative: False`); not called from cognition or speech.
* Any optimisation that suppresses legitimate learning is a regression. Learning equivalence is checked with the digest method used for #253
  (`PYTHONHASHSEED=0`, original versus new, reference loggers fed the same experience).
* Each phase has a rollback (additive fields and a switch that is off by default; no stored state rewritten), mutation-checked rules, and a report that separates
  implemented / isolated / integrated / device-validated.

## 6. Decisions for Sir

1. Keep the spec's fixed example thresholds as the first values, or derive promotion from the distribution of points?
2. Which stores move onto crystals first (P0 will list candidates)?
3. ~~`l3_quasicrystal.py` calls a 12-sided crystal "quasi"; the PDF puts quasi at L4.~~ Settled by Sir (2026-11-15): L4 is quasi.
4. Is the emotional point to be wired from DER before P3 or left `unknown`?

## 7. Not verified

Contents of `Full Crystal System Realized Potential.zip`, `Core_Crystal_Systems.py` and `unified_crystal_engine.py` beyond their openings; the live device state (this is the repository snapshot);
whether the 8 surface facets and the 9th nexus exist anywhere in the live code beyond what was grepped.
