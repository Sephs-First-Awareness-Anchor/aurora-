# Aurora progressive perspective consumption

## Purpose

This closes two seams left after PRs #227 and #228 without adding a new cognitive subsystem.

Aurora already has two distinct perspective mechanisms that occur at different causal moments:

1. The live possibility frontier uses Subsurface's canonical X/T/N/B/A pressure perspectives before a new turn-level RepresentationalRef exists. These perspectives support several uncommitted continuations from one frozen ThoughtBraid/self/King occurrence.
2. Build 714 adaptive representational resolution operates only once a real RepresentationalRef participates in measurable consequence. Its new perspective precursor asks whether a structurally connected representation can expose the needed distinction transiently before Aurora acquires additional representational resolution.

These mechanisms share perspective physics but must not be collapsed into one data type. The live possibility frontier must never fabricate a RepresentationalRef merely to call the resolution engine.

## Gap 1: fixed five-view truncation

PR #228 reused `MAX_CANDIDATE_FIELDS_PER_PASS` as the maximum number of perspective projections considered before field inquiry. That constant was originally a bounded candidate-search control, not an epistemic statement that five views exhaust Aurora's available perspective space.

The corrected path now reads the complete *currently available* structural frontier returned by genealogy's existing bounded collision/gap machinery, constructs every distinct lawful projection available from those real counterpart representations, and orders the views by:

1. least-dimensional X/T/N/B/A lens first;
2. strongest native structural pressure next;
3. stable projection identity only as a neutral tie order.

Only one projection is staged at a time. This preserves DCF-style progressive computation while removing the false epistemic cutoff. A `frontier_exhausted` event is emitted only when every currently available distinct structural projection has actually failed. Only then may Build 714 stage a field inquiry.

The later field-candidate pass is allowed to see the complete typed field/value capacity of the unresolved ref. That capacity is derived from the existing RepresentationalRef domains, not an arbitrary new budget.

## Gap 2: observers are not consumers

A subsystem can carry a RepresentationalRef as provenance and report measured consequence without having used that representation to form its own prediction. Such a subsystem is a valid source of inadequacy pressure but is not a legitimate tester of a staged projected or refined value.

`record_pressure_observation()` now preserves that distinction. It routes the real pressure delta through genealogy while holding the resolution gate closed. Therefore an observer:

- can increase or reduce the canonical consequence profile;
- cannot stage a projection merely by mentioning a ref;
- cannot complete a pending projection or field inquiry owned by another consumer;
- cannot create causal credit for a value it never used.

`record_ref_participation_from_scores()` now uses this pressure-only path when no `candidate_evaluation` is supplied. When a caller does provide a real candidate-conditioned evaluation, the full Build 714 participation path remains available.

Current production classification:

- RCEC causal evaluation: pressure observer. It evaluates world-state causality and carries `representational_ref` as provenance, but the ref does not alter the causal score computation.
- Habitat ambient consequence axes: pressure observers.
- Habitat motivation candidate evaluation: real projection/refinement consumer. It reads `provisional_resolution()`, records the concrete downstream difference, acts, and later joins the observed consequence back through `candidate_evaluation`.

## Combined causal shape

```text
one actual occurrence
    -> frozen ThoughtBraid / ActiveSelfState / King
    -> Subsurface pressure-perspective possibility frontier
    -> several uncommitted continuations
    -> Pareto evidence
    -> deeper self-simulation only if still needed
    -> King / Agency actualizes one continuation
    -> lived cognition proceeds
    -> a real RepresentationalRef participates in consequence
    -> inadequacy pressure, if any
    -> inspect all currently available lawful structural projections progressively
         -> projection sufficient: reuse the transient view; no representational growth
         -> projection insufficient: try the next relevant view
    -> structural perspective frontier exhausted
    -> Build 714 field inquiry / causal evidence / retention economics
```

Possibility breadth, perspective, resolution, simulation, and actuality therefore remain distinct operations with distinct costs and causal authority.

## Runtime/testing note

The connector environment used for this patch cannot clone or execute the full repository. The new projection-frontier and observer/consumer mechanics were exercised in an isolated Python harness using the same public extension code and stubbed Build 714/genealogy interfaces. Full phone behavior still requires the normal Aurora runtime or repository CI; no unrun suite is represented as passing.
