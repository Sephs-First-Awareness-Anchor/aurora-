# Aurora progressive perspective consumption

## Purpose

This closes the two integration seams left after PRs #227 and #228 without adding a new cognitive subsystem.

Aurora already has two distinct perspective mechanisms that occur at different causal moments:

1. The live possibility frontier uses Subsurface's canonical X/T/N/B/A pressure perspectives before a new turn-level RepresentationalRef exists. These perspectives support several uncommitted continuations from one frozen ThoughtBraid/self/King occurrence.
2. Build 714 adaptive representational resolution operates only once a real RepresentationalRef participates in measurable consequence. Its perspective precursor asks whether a structurally connected representation can expose the needed distinction transiently before Aurora acquires additional representational resolution.

These mechanisms share perspective physics but must not be collapsed into one data type. The live possibility frontier must never fabricate a RepresentationalRef merely to call the resolution engine.

## Gap 1: fixed five-view truncation

PR #228 reused `MAX_CANDIDATE_FIELDS_PER_PASS` as the maximum number of perspective projections considered before field inquiry. That constant was originally a bounded candidate-search control, not an epistemic statement that five views exhaust Aurora's available perspective space.

The corrected path now reads the complete *currently available* structural frontier returned by genealogy's existing bounded collision/gap machinery, constructs every distinct lawful projection available from those real counterpart representations, and orders consumable views by:

1. least-dimensional X/T/N/B/A lens first;
2. strongest native structural pressure next;
3. stable projection identity only as a neutral tie order.

Different lenses or source representations that expose the exact same projected RepresentationalRef collapse to one consumable view. Aurora therefore never pays twice for a distinction that is identical at the consumer boundary.

Only one projection is staged at a time. This preserves DCF-style progressive computation while removing the false epistemic cutoff.

### Search-cost discipline

Genealogy collision/gap discovery is historically one of Aurora's expensive operations. The projection frontier therefore amortizes that cost:

- the first real consumer demand performs one structural scan and caches only the transient frontier for that inadequacy episode;
- failed lenses advance through that cached frontier without rescanning genealogy;
- when the cached frontier is exhausted, exactly one refresh is permitted to catch genuinely new structural information;
- if that refresh exposes no untried view, the frontier is declared exhausted and Build 714 may proceed to field inquiry.

The cache is runtime-only. It has no persistence or knowledge authority and is cleared when the inadequacy is resolved through an adequate projection.

The later field-candidate pass is allowed to see the complete typed field/value capacity of the unresolved ref. That capacity is derived from the existing RepresentationalRef domains, not an arbitrary new budget.

## Gap 2: observers are not consumers

A subsystem can carry a RepresentationalRef as provenance and report measured consequence without having used that representation to form its own prediction. Such a subsystem is a valid source of inadequacy pressure but is not a legitimate tester of a staged projected or refined value.

`record_pressure_observation()` preserves that distinction. It routes the real pressure delta through genealogy while holding the resolution gate closed. Therefore an observer:

- can increase or reduce the canonical consequence profile;
- cannot stage a projection merely by mentioning a ref;
- cannot complete a pending projection or field inquiry owned by another consumer;
- cannot create causal credit for a value it never used.

`record_ref_participation_from_scores()` uses this pressure-only path when no `candidate_evaluation` is supplied. When a caller does provide a real candidate-conditioned evaluation, the full Build 714 participation path remains available.

### Consumer demand edge

Pressure alone should not launch representational work, but pressure must still be able to produce development once a representation is actually needed.

`provisional_resolution()` is now that demand edge. When a real subsystem asks to use a provisional representation and inadequacy pressure exists with no experiment already active, the read itself opens the perspective frontier before returning the view. Existing one-argument callers remain compatible.

This yields the causal sequence:

```text
observer measures consequence
    -> inadequacy pressure exists
    -> no projection is staged yet
real consumer asks to use the representation
    -> provisional_resolution()
    -> cheapest untried structural perspective is staged
    -> projected view participates in the consumer's real calculation
    -> consumer records the downstream Difference
    -> observed consequence tests whether the projection was sufficient
```

Current production classification:

- RCEC causal evaluation: pressure observer. It evaluates world-state causality and carries `representational_ref` as provenance, but the ref does not alter the causal score computation.
- Habitat ambient consequence axes: pressure observers.
- Habitat motivation: real projection/refinement consumer. Its `resolved_context_for_axis()` reads `provisional_resolution()`, affordance scoring compares the baseline and provisional refs, `record_candidate_downstream_effect()` seals any real ranking/prediction difference, and Habitat later joins the observed consequence back through `candidate_evaluation`.

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
    -> observers may create inadequacy pressure
    -> a real consumer requests provisional representation
    -> cached progressive perspective frontier
         -> projection sufficient: reuse transient view; no representational growth
         -> projection insufficient: try next cached view
         -> cached frontier exhausted: one structural refresh
    -> structural perspective frontier genuinely exhausted
    -> Build 714 field inquiry / causal evidence / retention economics
```

Possibility breadth, perspective, resolution, simulation, and actuality therefore remain distinct operations with distinct costs and causal authority.

## Runtime/testing note

The connector environment used for this patch cannot execute the full Aurora repository/phone runtime. The projection-frontier mechanics were exercised in an isolated Python harness, including six distinct lawful views, cheapest-lens deduplication, one-at-a-time widening, and a total of two structural scans across complete frontier exhaustion (initial discovery plus the single permitted refresh). Full phone behavior still requires the normal Aurora runtime or repository CI; no unrun suite is represented as passing.
