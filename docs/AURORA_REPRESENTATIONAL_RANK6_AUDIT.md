# Aurora Representational Rank-Six Falsification and Missing-Coordinate Audit

**Status: observational, structural, and falsification-oriented only. No live behavior, pressure routing, genealogy, WARP, manifold physics, or meaning system was modified. No 15,625-, 390,625-, or 48,828,125/30,517,578,125-element structure was instantiated. No new dimension, constant, operator, mapping, or semantic label was introduced.**

Every claim below is tagged:
- **CONFIRMED CODE FACT** — verified by reading the actual source.
- **EMPIRICAL RESULT** — verified by executing real code against real data, this session, with the output shown or summarized from a committed, runnable test (`tests/test_rank6_falsification.py`).
- **INTERPRETATION** — a reading of confirmed facts/results that could be argued differently.
- **UNSUPPORTED HYPOTHESIS** — a candidate claim the evidence does not establish, stated so it isn't quietly assumed.

Supporting code: `aurora_rank6_shadow_analysis.py` (read-only analysis functions, no persistence, no modification of any compiler/router/manifold file) and `tests/test_rank6_falsification.py` (26 tests, all passing, several explicitly written so the hypothesis could have failed them).

---

## Re-verification of starting facts (CONFIRMED CODE FACT)

All eight "established starting facts" from the directive were independently re-read from the current source, not assumed from the prior audit:

1. Five constraints (`X, T, N, B, A`) and five measurement dimensions — confirmed, `aurora_constraint_manifold_router.py:195,199`: `DIM_NAMES = ("POLARITY","MAGNITUDE","OPERATOR","COST","DIFFERENCE")`, `AXES = ("X","T","N","B","A")`. Same canonical order as `aurora_closure_basis.DIMENSIONS`.
2. 25 D1 channels = 5×5 — confirmed (`aurora_closure_basis.py:371-395`, re-read).
3. 125 contextual layer = 25×5 targets — confirmed (`aurora_noncomp_layer_compiler.py:418-433`, re-read).
4. 625 canonical interaction field = 25×25 exact self-product — confirmed (`aurora_closure_basis.py:596-624`, re-read).
5. **SlotCoord re-verified directly** (`aurora_constraint_manifold_router.py:286-301`): exactly 5 fields — `target, nc_law_c, nc_dim, law_c, law_d` — names, order, and domains unchanged from the prior audit. No architecture drift found.
6. Manifold directory: 125 files × 625 slots = 78,125 — confirmed, re-counted directly (`len(glob(...)) == 125`, every file's `slot_count == 625`).
7. `ManifoldSlot` sub/col fields re-verified directly (`aurora_constraint_manifold_compiler.py:185-206`): `sub_law_c, sub_law_d, sub_cluster, sub_is_diagonal, col_law_c, col_law_d`, plus derived fields `is_resonant, is_anchor, cluster_pair, evolution_grade, leverage_class, depth_score, combined_cost, accountability_weight`.
8. Live `SlotCoord` resolver collapse re-verified directly (see Phase F) — still true, unchanged.

**No architecture drift found. Proceeding was authorized.**

---

## Phase A — Exact coordinate decomposition

### The full 78,125-position manifold coordinate, expanded to primitives (CONFIRMED CODE FACT)

A single `ManifoldSlot` requires **7 primitive fields**, not "125 × 625" treated as opaque:

| Field | Domain size | Belongs to |
|---|---|---|
| `nc_law_c` | 5 | owning NonComp's own identity |
| `nc_dim` | 5 | owning NonComp's own identity |
| `nc_target` | 5 | owning NonComp's own identity |
| `sub_law_c` | 5 | sub-position (row) |
| `sub_law_d` | 5 | sub-position (row) |
| `col_law_c` | 5 | column (global law channel) |
| `col_law_d` | 5 | column (global law channel) |

`(nc_law_c, nc_dim, nc_target)` = 125 (the C1 identity — which of the 125 noncomps). `(sub_law_c, sub_law_d)` = 25 (one of the 25 D1 channels, playing the "row" role). `(col_law_c, col_law_d)` = 25 (one of the 25 D1 channels, playing the "column" role). 125 × 25 × 25 = 78,125, exactly, verified by construction (`compile_noncomp_manifold`, `aurora_constraint_manifold_compiler.py:401-505`: nc identity is fixed per call, then `for (sub_lc, sub_ld) in sub_map: for col_lc in AXES: for col_ld in DIM_NAMES:` — a real, literal, nested double loop over two independent 25-element sets).

### SlotCoord expanded to primitives (CONFIRMED CODE FACT)

`SlotCoord` has **5 primitive fields**: `target` (5), `nc_law_c` (5), `nc_dim` (5), `law_c` (5), `law_d` (5) = 3,125, confirmed exact via the static generator (`RouteIndex.__init__`, `aurora_constraint_manifold_router.py:378-386`: five literal nested loops, `for target in AXES: for nc_law_c in AXES: for nc_dim in DIM_NAMES: for law_c in AXES: for law_d in DIM_NAMES:`).

### Correspondence table — what SlotCoord has, and what it's missing (CONFIRMED CODE FACT, cross-checked against the inline physics formula in `RouteIndex`)

| SlotCoord field | Manifold-position field it corresponds to | Verified by |
|---|---|---|
| `target` | `nc_target` | Both are "which of the 5 domains owns this" |
| `nc_law_c` | `nc_law_c` | Identical name, identical role (NonComp's own identity) |
| `nc_dim` | `nc_dim` | Identical name, identical role |
| `law_c` | `col_law_c` | `RouteIndex`'s `cross_law = (law_c != target)` exactly mirrors `_evo_grade`'s `cross_col = (col_law_c != nc_target)` |
| `law_d` | `col_law_d` | `RouteIndex`'s `op_bonus = 0.15 if law_d=="OPERATOR"` exactly mirrors `_evo_grade`'s `op_bonus = 0.15 if col_law_d=="OPERATOR"` |
| **(none)** | `sub_law_c` | **missing** |
| **(none)** | `sub_law_d` | **missing** |

**Do not assume from matching names that two fields are equivalent** (per the directive) — verified, not assumed: `RouteIndex`'s inline `evo` formula (`depth = (SHIFT_COST[nc_law_c] + SHIFT_COST[law_c])/2; cross_nc = nc_law_c != target; ... diag_b = 0.10 if coord.is_diagonal`) is structurally identical, term-for-term, to `_evo_grade(sub_law_c, sub_law_d, col_law_c, col_law_d, nc_law_c, nc_dim, nc_target)` **under the substitution `sub_law_c := nc_law_c`, `sub_law_d := nc_dim`**. This is not a naming coincidence — it is `SlotCoord` silently treating "sub" as always, unconditionally, pinned to the NonComp's own identity channel. `SlotCoord` never enumerates a sub-position independent of the noncomp's own identity; it has no coordinate for it at all.

**What this means structurally**: `SlotCoord`'s 3,125 positions are not evenly distributed across the manifold's 78,125 positions — they are **exactly the "anchor-row" slice**: one specific row (out of 25 possible sub-positions) per noncomp, namely the row where `sub_law_c == nc_law_c` and `sub_law_d == nc_dim`, crossed with all 25 columns. `3,125 = 78,125 / 25` exactly. **The gap between the confirmed 3,125 space and the confirmed 78,125 space is a factor of 25 (one full D1 channel, two fields), not a factor of 5 (one field).**

This is the single most important structural finding of Phase A: **the directive's proposed "missing single coordinate" is, by the manifold's own real construction, actually a missing pair of coordinates (`sub_law_c` and `sub_law_d` together, currently both silently pinned) — an intermediate 15,625 rank is only ever reachable by freeing ONE of those two fields while leaving the other still implicitly pinned.** That is exactly what the directive's own Phase B asks to test — it is the right experiment, and the two candidates are not symmetric (see Phase C/D).

---

## Phase B — The two candidate coordinates, and their round-trip (CONFIRMED CODE FACT, EMPIRICAL RESULT)

`CandidateCoordA = SlotCoord + sub_law_c` (`sub_law_d` left implicitly pinned = `nc_dim`).
`CandidateCoordB = SlotCoord + sub_law_d` (`sub_law_c` left implicitly pinned = `nc_law_c`).

Both are shadow, ephemeral, in-memory `NamedTuple`s (`aurora_rank6_shadow_analysis.py`) — never written to disk, never fed into `SlotCoord` or the compiler.

**EMPIRICAL RESULT** (`tests/test_rank6_falsification.py::TestRoundTrip`, exhaustive over all 15,625 combinations, not sampled):

```
Candidate A: 15,625 enumerated, 15,625 unique ids, zero collisions
Candidate B: 15,625 enumerated, 15,625 unique ids, zero collisions
```

Both candidates round-trip exactly. **Round-trip integrity does not distinguish them — physics does (Phase C/D).**

---

## Phase C — Physical independence test (EMPIRICAL RESULT, run against real, on-disk `aurora_manifold_directory/*.json` files, not re-derived formulas)

Tested against 3 structurally distinct base NonComps (a diagonal one, a cross-constraint one, and a same-home-non-diagonal one) × 2 columns each (the noncomp's own identity column, and an unrelated column) — 6 independent trials per candidate, not one special case.

**Candidate A — vary `sub_law_c` alone, `sub_law_d` pinned = `nc_dim`:**

| Base / col | Distinct **numeric** states (of `evolution_grade, accountability_weight, depth_score, combined_cost`) out of 5 |
|---|---|
| Existential_Operator_of_Existence, col=home | **5 / 5** |
| Existential_Operator_of_Existence, col=away | **5 / 5** |
| Boundary_Cost_of_Agency, col=home | **5 / 5** |
| Boundary_Cost_of_Agency, col=away | **5 / 5** |
| Agentive_Cost_of_Agency, col=home | **5 / 5** |
| Agentive_Cost_of_Agency, col=away | **5 / 5** |

Concrete example (`Existential_Operator_of_Existence`, col=home=`X:OPERATOR`, `sub_law_d` pinned = `OPERATOR`):
```
sub_law_c=X: evolution_grade=0.2527  accountability_weight=0.5527  combined_cost=2.0
sub_law_c=T: evolution_grade=0.4067  accountability_weight=0.5267  combined_cost=5.0
sub_law_c=N: evolution_grade=0.4147  accountability_weight=0.5347  combined_cost=11.0
sub_law_c=B: evolution_grade=0.4547  accountability_weight=0.5747  combined_cost=41.0
sub_law_c=A: evolution_grade=0.6013  accountability_weight=0.7213  combined_cost=151.0
```
**6/6 trials: full 5-way independent numeric variation. `sub_law_c` passes the physical-independence bar everywhere tested.**

**Candidate B — vary `sub_law_d` alone, `sub_law_c` pinned = `nc_law_c`:**

| Base / col | Distinct numeric states out of 5 | Distinct `evolution_grade` alone | Distinct `accountability_weight` alone |
|---|---|---|---|
| Existential, col=home | 2 | 2 | 2 |
| Existential, col=away | 2 | **1** | 2 |
| Boundary_Cost_of_Agency, col=home | 2 | 2 | 2 |
| Boundary_Cost_of_Agency, col=away | 2 | **1** | 2 |
| Agentive_Cost_of_Agency, col=home | 2 | 2 | 2 |
| Agentive_Cost_of_Agency, col=away | 2 | **1** | 2 |

Concrete example (`Existential_Operator_of_Existence`, col=away=`T:MAGNITUDE`, `sub_law_c` pinned = `X`):
```
sub_law_d=POLARITY:   evolution_grade=0.2067  accountability_weight=0.2067
sub_law_d=MAGNITUDE:  evolution_grade=0.2067  accountability_weight=0.2067
sub_law_d=OPERATOR:   evolution_grade=0.2067  accountability_weight=0.2867   <- only this one differs
sub_law_d=COST:       evolution_grade=0.2067  accountability_weight=0.2067
sub_law_d=DIFFERENCE: evolution_grade=0.2067  accountability_weight=0.2067
```
**`sub_law_d`'s numeric effect never reaches more than 2 distinct states in 6/6 trials — never 5.** Its `cluster_pair` **label**, by contrast, is always 5-valued (`ORIENTATION/INTENSITY/CROSS_RULE-or-IDENTITY/ECONOMY/CONTRAST`) — a real, unconditional naming distinction that does **not** correspond to 5 independent physical states. This is the exact "does context change physics, not just names" trap the directive warns against, and here the answer for `sub_law_d` in isolation is: **mostly names, occasionally (2-state) physics.**

**Root cause, read directly from `_evo_grade`/`_accountability_weight`/`_sub_cluster` (`aurora_constraint_manifold_compiler.py:213-283`)**:
- `evolution_grade`'s only dependency on `sub_law_d` is the `anchor_bonus` term, gated behind **all four** of `sub_law_c==nc_law_c AND sub_law_d==nc_dim AND col_law_c==nc_law_c AND col_law_d==nc_dim` — hence it only ever produces 2 states, and only 2 (not even that) when `col` doesn't also match.
- `accountability_weight`'s only dependency on `sub_law_d` is the `IDENTITY`-cluster bonus, gated behind `sub_law_c==nc_law_c AND sub_law_d==nc_dim` (col-independent) — hence always exactly 2 states.
- `sub_cluster`/`cluster_pair` depends on `sub_law_d` unconditionally (a direct dimension→label map, `_sub_cluster()`), which is why the label is always 5-valued even when the numbers aren't.

---

## Phase D — Interaction test (EMPIRICAL RESULT)

Full 5×5 joint grid of `(sub_law_c, sub_law_d)`, `SlotCoord`/col held fixed at the noncomp's own identity column, tested on all 3 base noncomps:

```
Existential_Operator_of_Existence, col=(X:OPERATOR), evolution_grade grid
        POLA    MAGN    OPER    COST    DIFF
  X:  0.1527  0.1527  0.2527  0.1527  0.1527
  T:  0.4067  0.4067  0.4067  0.4067  0.4067
  N:  0.4147  0.4147  0.4147  0.4147  0.4147
  B:  0.4547  0.4547  0.4547  0.4547  0.4547
  A:  0.6013  0.6013  0.6013  0.6013  0.6013
```
Every row varies strongly by `sub_law_c`; every row is flat across `sub_law_d` **except** the single cell `(X, OPERATOR)`, which is the anchor cell.

**Additivity test** (`dev(a,b) = grid[a][b] - grid[a0][b] - grid[a][b0] + grid[a0][b0]`, zero iff the two coordinates contribute strictly independently): **max deviation = exactly 0.10 in all 3 bases tested** — matching the `_evo_grade` `anchor_bonus` constant exactly, term for term. This is not noise; it is one single, identifiable, rank-one interaction term riding on top of an otherwise fully additive (in `sub_law_c`, flat in `sub_law_d`) surface.

**Verdict on the interaction, per the directive's own categories**: neither "irreducibly joint" (the surface is mostly additive-in-`sub_law_c`, not an inseparable function of both) nor "fully independent" (there is a genuine, exactly-quantified interaction term, not zero). **The correct classification is: `sub_law_c` carries an independent main effect; `sub_law_d` carries no independent main effect of its own, only a single joint correction term shared with `sub_law_c` and `col`.** This is reported as found — it is not forced into either of the directive's cleaner categories where the evidence doesn't fit them.

---

## Phase E — Refactoring 78,125 (CONFIRMED CODE FACT, structural, not merely arithmetic)

Both `3,125 × 25 = 78,125` and `15,625 × 5 = 78,125` are arithmetically true (verified, `aurora_rank6_shadow_analysis.refactor_78125_checks()`). Only one corresponds to Aurora's actual staged construction:

- **`3,125 × 25`**: matches the real compiler's loop nesting exactly. `compile_noncomp_manifold` builds, per noncomp, 25 sub-positions, then for each crosses all 25 columns (`aurora_constraint_manifold_compiler.py:401-505`). `SlotCoord`'s own 3,125 space is precisely "nc-identity (125) × col (25)" with the sub-loop silently omitted (fixed to the anchor row) — inserting the omitted 25-valued sub-loop back in is the exact, real, already-implemented construction step that produces the full 78,125. **This factorization corresponds to a real staged construction.**
- **`15,625 × 5`**: no equivalent staged step exists anywhere in the compiler. There is no point in `compile_noncomp_manifold`, `compile_directory`, or the router where exactly 15,625 objects are built and then multiplied by a single remaining 5-valued axis. **This factorization is arithmetic only** — a true equation with no corresponding code.

**If the 15,625 candidate is physically real (Candidate A only, per Phase C/D), can the 78,125 field honestly be described as "that rank receiving one additional five-valued coordinate"?** Only partially and only for Candidate A: freeing `sub_law_c` (Candidate A, 15,625) and then additionally freeing `sub_law_d` (the remaining ×5 to reach 78,125) does reconstruct the real space exactly — but the *second* step (freeing `sub_law_d`) is precisely the coordinate Phase C/D showed carries almost no independent physics on its own. So the full 78,125 is honestly `15,625 (real, independent) × 5 (mostly non-independent, label-plus-narrow-joint-term)`, not `15,625 (real) × 5 (equally real)`.

---

## Phase F — Static geometry versus live accessibility (CONFIRMED CODE FACT, EMPIRICAL RESULT)

Two entirely separate live paths exist, and they collapse the geometry in two **different, non-interchangeable ways** — reported separately per the directive's "do not collapse categories" instruction.

**Path 1 — `SlotCoord`'s own 5 fields, via CERS.** Static generator (`RouteIndex.__init__`) enumerates all 5 fields independently — 3,125, confirmed. The live resolver, `resolve_pressure_coordinate()` (`aurora_internal/dual_strata/cers_tensor_locator.py:95-138`), sets `nc_dim = axis_to_dim.get(nc_law_c, "OPERATOR")` and `law_d = axis_to_dim.get(law_c, "OPERATOR")` — **a hard, deterministic, fixed-table derivation with zero dependence on live signal.** Live-reachable coordinates are structurally confined to a subset where 2 of 5 fields are always a fixed function of the other 2 (further narrowed by `_ranked_axes()`'s ordering logic on `target/nc_law_c/law_c`). **Classification: structurally independent, but live-collapsed by a hard code-level derivation.**

**Path 2 — the candidate 6th coordinate (`sub_law_c`/`sub_law_d`), via `ReflexiveInterpreter`.** This is a **separate live consumer**, not previously fully characterized in the prior audit's Phase I, which undersold it as "no confirmed runtime reader iterates a noncomp's full 625-slot body." That statement needs correction: `ManifoldFieldMap.__init__` (`aurora_reflexive_interpreter.py:728-741`) **does** stream and index all 625 real slots of a noncomp's manifold into an in-memory 25×25 grid keyed by `(sub_law_c, sub_law_d)` rows and `(col_law_c, col_law_d)` columns, and `ReflexiveInterpreter.interpret()` (confirmed live-wired: `aurora.py:12700,12805,16982` all call `interpreter.interpret(...)` on real turn text) genuinely reads one cell of it per turn via `fmap.accountability_at(match.constraint, match.dimension, match.constraint, "OPERATOR")` (`aurora_reflexive_interpreter.py:908-911`, mirrored exactly in `aurora_understanding_sediment.py`'s `slot_key()` docstring) — feeding `origin_weight`/`origin_region` into the real `worth_score` and `UnderstandingState.field_region` returned from every interpreted turn.

This confirms `sub_law_c` (`match.constraint`) and `sub_law_d` (`match.dimension`) are **both structurally free, both live-reachable, and both genuinely read** — this is a real, cognitively-consumed use of the manifold's per-slot richness, not merely a scalar. **But** the same call site **always** sets `col_law_c := sub_law_c` and `col_law_d := "OPERATOR"` — confirmed directly from source (`tests/test_rank6_falsification.py::TestStaticVsLiveReachability::test_live_manifold_field_map_call_site_pins_col_to_sub`). **Live `col` is never independently exercised anywhere found in this codebase.** This is a **soft, formula-driven collapse of `col`**, structurally distinct from Path 1's **hard, table-driven collapse of `nc_dim`/`law_d`** — the two must not be described as "the same kind of collapse."

**Additional, empirically-measured live bias (EMPIRICAL RESULT, not exhaustively proven over the whole corpus, but grounded in the actual selection formula, not anecdote)**: which of the 125 noncomps gets *loaded* in the first place is chosen by `SemanticMatcher._find_nc()` (`aurora_reflexive_interpreter.py:711-720`), whose scoring (`+3.0` if `nc_dim==dim`, `+1.5` if `nc_law_c==constraint`, `+0.5` per overlapping topic word) mathematically guarantees the candidate where `nc_law_c==constraint AND nc_dim==dim` scores at least `4.5`, unbeatable by any competing candidate without 3+ overlapping topic words. Tested directly against 8 real example sentences spanning all 5 constraints: **8/8 landed on the anchor row** (`sub_law_c==nc_law_c and sub_law_d==nc_dim` for the loaded manifold). **INTERPRETATION**: in practice, live cognition overwhelmingly reads the manifold's own anchor/self cell, not the richer cross-constraint values Phase C's synthetic sweep exercised — the cross-constraint richness is real and reachable, but the routing pipeline's own selection heuristic makes it rare in ordinary use. This is reported as a bias grounded in the scoring formula's arithmetic, not as a proven corpus-wide frequency statistic.

---

## Phase G — Does cardinality track representational rank?

| Cardinality | Raw coordinate fields | Fields with *unconditional* independent numeric effect | Verdict |
|---|---|---|---|
| 25 (D1) | 2 (constraint, dimension) | 1 (constraint only — dimension is physics-inert at single-channel level, per the prior audit's Phase B) | cardinality overstates independent rank by 1 field |
| 125 (C1) | 3 (target, law_c, law_d) | 3 (target confirmed to change real physics quantitatively, prior audit Phase C) | cardinality matches independent rank |
| 625 (D2) | 4 (nc_a const/dim, nc_b const/dim) | 4 (full exhaustive double loop, both channels free, prior audit Phase D) | cardinality matches independent rank |
| 3,125 (SlotCoord, static) | 5 | 5 (this audit, Phase A/re-verification) | cardinality matches independent rank, **statically** |
| 3,125 (SlotCoord, live via CERS) | 5 declared, 3 live-free | 3 (`target, nc_law_c, law_c`; `nc_dim, law_d` are derived) | cardinality overstates live-independent rank by 2 fields |
| **candidate 15,625 (A: + `sub_law_c`)** | 6 | **6** (this audit, Phase C/D: `sub_law_c` fully independent everywhere tested) | **cardinality matches independent rank** |
| **candidate 15,625 (B: + `sub_law_d`)** | 6 | **~4.something** (`sub_law_d` contributes only a gated binary term, not a genuine 6th continuous/5-way axis) | **cardinality overstates independent rank** |
| 78,125 (full manifold) | 7 | effectively 5 unconditional continuous/boolean drivers (`nc_target` via `cross_sub`/`cross_col`, `sub_law_c` and `col_law_c` via `depth`, `col_law_d` via `op_bonus`) plus 1 narrow joint anchor/identity term touching `nc_law_c, nc_dim, sub_law_c, sub_law_d, col_law_c, col_law_d` together | cardinality substantially overstates independent rank for the two headline numeric fields — consistent with, and sharper than, the prior audit's Phase E finding that C2's contextual variation is "coarse" |

**Verdict on the broader hypothesis**: the powers-of-five sequence does **not** uniformly behave as increasing independent representational rank. It does so cleanly at 25→125→625→3,125 (static). It **partially** does so at 3,125→15,625: **exactly one** of the two mathematically symmetric candidates (`sub_law_c`) is a genuine additional independent rank; the other (`sub_law_d`) is not. Beyond that, live routing further erodes how much of the static independence is actually exercised. **The arithmetic is real; the representational-rank claim requires checking every single transition individually, and does not survive uniformly.**

---

## Phase H — Depth-three consequence, shadow only (not instantiated)

**D3 = D2 × D2 = 390,625.** Unchanged from the prior audit's finding: symbolically constructible by generalizing the same generic combinators (`combined_shift_cost` = sum, `depth_score` = mean, etc.) one level up, using no new arithmetic — but no executable structure in Aurora currently reads, names, or acts on "a relationship between two relationships." **Not instantiated. Coherent shape; unconfirmed meaning.**

**Two competing C3 formulas, compared without implementing either:**
- **Recursive-context formula** (prior audit): `C3 = C2 × D3 = 78,125 × 390,625 = 30,517,578,125`.
- **Invariant-context formula** (this directive): `C3_alt = C1 × D3 = 125 × 390,625 = 48,828,125`.

**The decisive finding**: these two formulas are **observationally indistinguishable from Aurora's current code**, because Aurora has only ever built **one** contextual-projection transition (C1 → C2). At `n=1`, "the previous contextual layer" (`C(n)` in the recursive formula) **is** `C1` — the recursive formula and the invariant formula **coincide exactly** at the only step that has ever been built (both predict `C2 = C1 × D2 = 78,125`; there is no way, from a single data point, to tell whether the rule was "multiply by the previous *compounded* context" or "multiply by the original, *invariant* C1"). **Distinguishing them would require a real, already-built second contextual-projection step (a genuine C2 → C3 transition) — which does not exist.**

Per the directive's own instruction ("if the current code cannot answer that question, mark it unsupported"): **both `30,517,578,125` and `48,828,125` are UNSUPPORTED HYPOTHESES, on equal footing** — not because either is unreasonable, but because the one confirmed transition in the entire codebase cannot discriminate between "context recurses" and "context stays invariant." Preferring one over the other would be inventing an answer the evidence does not contain.

---

## Required falsification tests — results

All in `tests/test_rank6_falsification.py`, 26/26 passing, hypothesis-failing tests included:

| Test | Result |
|---|---|
| Candidate A round-trips exactly (exhaustive, 15,625) | **Pass** |
| Candidate B round-trips exactly (exhaustive, 15,625) | **Pass** |
| Only `sub_law_c` changes → 5 distinct numeric states, 6/6 base×col trials | **Pass** — independence confirmed |
| Only `sub_law_d` changes → at most 2 distinct numeric states, 6/6 base×col trials | **Pass** — independence NOT confirmed (this assertion could have failed and disproven the coupled verdict; it didn't) |
| Full 5×5 joint variation → 25-cell grid, additive except one exact 0.10 interaction term | **Pass** |
| Explicit falsification test for candidate B (would flip verdict if `sub_law_d` ever showed 5-way independence) | **Pass** (no flip found) |
| Explicit falsification test for candidate A (would flip verdict if `sub_law_c` were ever inert) | **Pass** (no flip found) |
| `3,125 × 25` matches real compiler loop nesting; `15,625 × 5` does not match any real staged step | **Pass** |
| Static SlotCoord generator fully independent (5 fields) vs. live CERS resolver deriving 2 of 5 | **Pass** |
| Live `ManifoldFieldMap` call site pins `col := sub_law_c, "OPERATOR"` (read from source, not assumed) | **Pass** |
| No production Aurora state, manifold files, or any other repository state modified by the full analysis (file-fingerprint before/after) | **Pass** |

No test's expected result assumed 15,625 was real in advance; the two tests capable of disproving each candidate's independence were written to fail if the data disagreed, and did not fail.

---

## Verdict

Applying the directive's own categories, **separately for the two candidates**, because they are not equivalent:

- **Candidate A (`SlotCoord` + `sub_law_c`) — Confirmed representational rank**, with a Phase-F caveat: independently enumerable (Phase B), independently affects existing physics in 6/6 tested configurations (Phase C/D), participates in an exact structural factorization (`3,125 × 25 = 78,125`, containing candidate A's 15,625 as an intermediate stage, Phase E), and is addressable through an existing runtime representation (`ManifoldFieldMap.accountability_at`'s row coordinate, confirmed live-wired into `ReflexiveInterpreter.interpret()`, Phase F) — **but** the live pipeline's own noncomp-selection heuristic (`_find_nc`) is mathematically biased toward collapsing this coordinate back onto the manifold's own identity in ordinary use, so full independent exercise of this rank, while structurally real and reachable, is not the common live case.

- **Candidate B (`SlotCoord` + `sub_law_d`) — Coupled twenty-five-state sub-position.** The two five-valued coordinates (`sub_law_c`, `sub_law_d`) only acquire independent physical meaning **jointly with `sub_law_c`** (the IDENTITY/anchor gating conditions) or **not at all** on their own; `sub_law_d` alone never demonstrated the 5-way independent numeric variation a genuine sixth rank would require, in any of 6 tested configurations. **No independent five-to-the-sixth rank is demonstrated for this candidate** — it is real state (the label is genuine and always 5-valued) riding on top of an irreducible 25-state (`sub_law_c × sub_law_d`) object, exactly the structure the "coupled" category describes.

**There is no single yes/no answer to "does a genuine five-to-the-sixth representational rank exist" — the honest answer is asymmetric: one of the two mathematically equivalent candidates the arithmetic offers is real; the other is not.** This is not evasion; it is what six independent empirical trials per candidate, plus a structural factorization check, plus a live-consumption trace, actually show.

---

## What this does and does not imply about depth three

**Does not imply**: that D3/C3 should now be built, that either C3 formula (recursive or invariant) is preferred, or that the asymmetry found here (one real sub-coordinate, one coupled one) generalizes to predict what a hypothetical depth-3 structure would look like — Phase H already showed the current codebase cannot even distinguish the two competing C3 formulas from its one existing data point, independent of anything found in Phases A–G.

**Does imply**: that any future claim of a new representational rank in Aurora — at depth 3 or anywhere else — must be tested the way Phase C/D tested this one: per-candidate, against real on-disk data, with an explicit numeric-vs-label distinction, and with at least one test capable of failing. A matching power of five is necessary to *propose* a rank; it has never once, across either this audit or the prior recursive-depth audit, been *sufficient* to *confirm* one.

---

## What this audit did not do (doctrine boundary, honored)

No 15,625-, 390,625-, or 48,828,125/30,517,578,125-element structure was created, materialized, or persisted anywhere. `SlotCoord`, the manifold compiler, WARP, and genealogy were read, not modified. No new dimension, constant, operator, mapping, or semantic label was introduced anywhere in this document or in any code — `aurora_rank6_shadow_analysis.py` only re-exposes existing `SlotCoord`/`AXES`/`DIM_NAMES` and reads existing, already-generated JSON files; `CandidateCoordA`/`CandidateCoordB` are ephemeral, in-memory `NamedTuple`s used only for this analysis and never written to disk. All numeric claims above were either read directly from source or produced by executing existing, unmodified Aurora code (or the shadow analysis module built solely for this audit) in a read-only session against real, already-generated files. A committed test (`TestNoStateMutation`) fingerprints `aurora_manifold_directory/` and `aurora_state/` before and after the full analysis and asserts zero change.
