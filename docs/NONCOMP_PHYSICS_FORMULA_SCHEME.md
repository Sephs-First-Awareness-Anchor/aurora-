# Noncomp Mathematical Representation Scheme
**Authors: Sunni (Sir) Morningstar & Cael Devo**
**Status: v1 — applied to all 125 top-level noncomp identity files**

---

## 1. The governing equation

Every target constraint `C` (X, T, N, B, A) is a state variable following a
controlled relaxation process — the same first-order dynamic that governs
nuclear decay, RC discharge, and population kinetics:

```
dC/dt = -lambda_C * C
        + sum_L [ b_{L,C} * sgn_{L,C}(t) * L(t) ]      <- MAGNITUDE x POLARITY x OPERATOR
        - sum_L [ kappa_{L,C} * |L(t)| ]                <- COST
        + sum_L [ d_{L,C} * (dL/dt) ]                   <- DIFFERENCE
```

`lambda_C` is C's own dissolution/decay rate. The sum runs over all five laws
`L` (X, T, N, B, A) acting on C — this is exactly the 5x5 = 25 noncomp grid
under each target folder.

## 2. Dimension -> role mapping

Sourced from the manifold's own lineage-signature correspondence
(POLARITY->A, MAGNITUDE->B, OPERATOR->X, COST->N, DIFFERENCE->T):

| Dimension  | Role in dC/dt                          | Formula piece                     |
|------------|-----------------------------------------|------------------------------------|
| OPERATOR   | driving state term                      | `L(t)`                             |
| POLARITY   | directional gate (helps or drains C)    | `sgn(dL/dt)`                       |
| MAGNITUDE  | scaled pressure                         | `b_{L,C} * \|L(t)\|`               |
| COST       | metabolic price paid out of dC/dt       | `kappa_{L,C} * \|L(t)\|`           |
| DIFFERENCE | temporal-gradient contribution          | `d_{L,C} * (dL/dt)`                |

## 3. The diagonal anchor

When `L == C` and `dim == OPERATOR`, the noncomp is the self-application
slot already flagged `is_anchor: true` / `is_diagonal: true` in the existing
manifold files. Under this scheme its formula is simply `C(t)` — the raw
state variable the whole equation is written in terms of. This matches the
existing architecture rather than requiring any change to it.

## 4. What was added, what wasn't touched

Each of the 125 top-level noncomp JSONs (`aurora_manifold_directory/{X,T,N,B,A}/*.json`)
now carries three new keys, added alongside everything already there:

- `mathematical_form` — plain-language statement of the physical role
- `formula` — compact symbolic form
- `formula_role` — which of X/T/N/B/A this dimension maps to

Nothing existing was modified or removed. The nested `sub_positions` and
`slots` arrays (the 625-slot recursion inside each noncomp) were **not**
touched in this pass — extending the same scheme down into that layer is a
natural next step once this top-level pass is confirmed correct, but it's a
separate, larger job (125 x 625 = 78,125 positions) worth its own directive.

## 4.5 v2 upgrade — combinatory meaning + sourced coefficients

v1 wrote generic axis-letter formulas. v2 fixes two gaps: it weaves in each
noncomp's own `nc_semantic_summary` and `nc_domain` so the formula reads in
terms of what the combination actually means, and it derives
`formula_coefficient` from the mean `accountability_weight` already present
in that noncomp's `slots` array instead of a placeholder symbol. It also
adds a `development_tracking` scaffold pointing at the real
`PressureExperienceLedger.record()` in `aurora_internal/aurora_pressure_ledger.py`
so future measured values have somewhere real to land.

## 5. Open question carried over

The lambda_C (decay rate) and b/kappa/d coefficients per (L, C) pair aren't
derived yet — this pass gives every noncomp its symbolic role in the
equation, not yet a fitted numeric value. Whether those coefficients come
from the existing `combined_cost` / `accountability_weight` fields (they
look like they already encode an axis-distance metric that could seed this)
or need fresh derivation is the next decision point.
