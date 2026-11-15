# Crystal architecture over the unmerged work (integration branch)

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-15
**Branch:** `ceph/crystal-integration-20261115` = the #251/#252/#253 stack (evidence qualification, input identity, genealogy redistribution, FIX-A142/A143) + the crystal build (P1 associations, P2 convergence, P3 maturity, facet placement) + `crystal_weave`. Nothing merged to main. Nothing wired into the running system; every writer is dry-run by default.

## What now works together

* `crystal_weave.place_event` takes an evidence-contract event and places it as an occasion on a facet entry: counts only if `evidence_qualification.counts` says so (a recollection, dreamed, imagined, simulated, overheard, supposed, inferred or unknown occasion is kept and earns nothing; a negated one is evidence against); occurrence, context, ancestry and consequence travel with it.
* `genealogy_associations` turns the genealogy's pair ledger and promoted links into typed associations by recurrence (each exposure worth 0.1, n exposures 1-(0.9)^n), and carries the qualification by kind of occurrence when a link has one (lived counted; hypothetical and overheard kept, uncounted; externally demonstrated inputs are inside lived, not extra).
* `weave(state_dir)` runs every adapter (OETS nodes and relations, assertions, genealogy, waveform cycle) and returns a facet book, an association store and a summary. `consequence` measures what the links change.
* `scripts/measure_crystal_weave.py --state-dir <dir>` prints all of it. Reads only.

## Measured on the repository snapshot (not live state)

| Measure | Value |
|---|---|
| Concepts woven (OETS + genealogy) | 1,369; 565 have a crystal, 804 do not |
| Associations held | 15,926 records: recurrence 11,197, heuristic 6,450 (OETS and genealogy), looked_up 1,411, unattributed 228, unknown 59, seeded 20 |
| Crystals that would gain any link | 382 of 5,977 (6.4%); 4,171 links |
| Reach of `sunni` | 9 crystals in one step, 190 in two (3.2% of all crystals) |
| Wholes formed by `is_a` from counted evidence | 0 (its 54 edges come from axis_embodiment, foundational, seeded, definition_analysis and `conversation`, none counted) |
| Genealogy ids that have a crystal | 0 of 404 |
| Links with an evidence qualification | 0 of 356 (all predate FIX-A144 recording) |

## What this says about "the links would be consequential"

* The mechanism is in place: weaving does place everything in its facet once with its occasions, and the links do form a web. On today's snapshot the web is thin because most of what she holds has no earned evidence behind it, not because the architecture cannot hold it.
* The category skeleton (`is_a`) is entirely uncounted. Until her categories rest on occurrence, no whole forms by convergence. Her `conversation`-sourced `is_a` edges (10) have a source the evidence table does not map; they stay unknown rather than being read as told.
* Representations and abilities (the genealogy) have no crystals at all. The facets can be placed in the book, but no crystal exists to receive them. Operation crystals for abilities (mapping A4) would create crystals, which nothing here does.
* Usage examples and valence carry no recorded occurrence, so they stay uncounted; the input-identity work records it from now on.

## Decisions for Sir

1. May operation crystals be created for abilities and promoted links (the only way genealogy data reaches a crystal)?
2. Is `conversation`-sourced evidence addressed (told) or not? The code does not say; it is not guessed.
3. Wiring: this branch changes nothing live. Which writer, if any, runs first on a copy of state?
