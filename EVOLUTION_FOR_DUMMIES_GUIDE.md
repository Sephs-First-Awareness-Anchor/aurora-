# Evolution For Dummies (Constraint-Driven)

This guide defines a simple, repeatable evolution workflow for Aurora structures using the five constraints:
- `X` Existence
- `T` Time
- `N` Cost/Energy
- `B` Boundary
- `A` Agency

## 1. Core Rule
For each operation:
- Measure all 5 constraint weights (`axis_weights_all`), normalized to `1.0`.
- Pick strongest 4 as placement axes (`placement_axes`).
- Use the unused 5th axis as a differentiator (`unused_constraint_axis`, `unused_constraint_weight`).

## 2. Constraint Meaning (Function-Level)
- `X`: state/identity/representation/parsing
- `T`: sequencing/ticks/history/integration
- `N`: pressure/cost/resource optimization
- `B`: interfaces/gating/link surfaces/topology
- `A`: control/policy/override/evolution steering

## 3. Dominance Rule (Main Determining Factor)
Compute from all-5 weights:
- `dominance_axis`: top axis
- `secondary_axis`: second axis
- `dominance_margin = w1 - w2`
- `dominance_ratio = w1 / max(w2, eps)`
- `dominance_level`:
  - `hard` if `margin >= 0.35`
  - `moderate` if `margin >= 0.20`
  - `soft` if `margin >= 0.10`
  - `blended` otherwise

Use these to scale classification confidence.

## 4. Interaction Rules (How Constraints React)
Use these as default interpretation behaviors:
- `X + T`: state over time (tracking, coherence drift)
- `X + N`: value of state (worth, pressure response)
- `X + B`: state at interfaces (eligibility, admissibility)
- `X + A`: state under control (self-directed changes)
- `T + N`: temporal cost (decay, accumulation budgets)
- `T + B`: time-windowed boundaries (phase gates)
- `T + A`: scheduled control (policy cadence)
- `N + B`: constrained optimization (resource-limited interfaces)
- `N + A`: strategic control under pressure (goal-cost tradeoffs)
- `B + A`: governed reconfiguration (safe structural mutation)

## 5. Classification Output Contract
Each evolved operation should emit:
- `axis_weights_all` (all 5)
- `placement_axes` (strongest 4)
- `unused_constraint_axis` + `unused_constraint_weight`
- `dominance_axis`, `secondary_axis`, `dominance_margin`, `dominance_level`
- `primary_slot` and `subslot_key`
- `conceptual_behavior_class`

## 6. Evolution Loop (Deterministic)
1. Measure all-5 weights from operation signals.
2. Compute dominance metrics.
3. Select strongest-4 placement axes.
4. Assign primary slot from strongest-4 + dominance scaling.
5. Split near-collisions using unused axis.
6. Write `subslot_key` from quantized all-5 profile.
7. Update derivative lineage links.
8. Re-score after mutation and compare with parent profile.

## 7. Similarity Rule (For Future Evolutions)
Two operations are "same family" if:
- cosine similarity of `axis_weights_all` is high (e.g. `>= 0.995`), and
- same `dominance_axis` and same `unused_constraint_axis`.

They are "adjacent family" if:
- cosine similarity is high but one of (`secondary_axis`, `unused_constraint_axis`) differs.

## 8. Practical Defaults
- Keep hard deterministic placement for lineage stability.
- Keep weighted projection for manifold coverage.
- Use hybrid matrix for trend reading (`primary + subset` combined).
- Never drop all-5 measurements, even when only strongest-4 drive placement.
