# Native Language Interface Blueprint (reflecting the live manifold)

The blueprint below is the same structure you outlined, but every section now references Aurora’s actual semantic substrate: the five **target domains** (`X=Information`, `T=Belief`, `N=Purpose`, `B=Meaning`, `A=Understanding`), the five **law families** (`Existential`, `Temporal`, `Energetic`, `Boundary`, `Agentive`), and the five **representational dimensions** (`POLARITY`, `MAGNITUDE`, `OPERATOR`, `COST`, `DIFFERENCE`). The canonical inventory of those 125 laws lives in [`NONCOMP_SEMANTIC_INVENTORY.md`](NONCOMP_SEMANTIC_INVENTORY.md). Use diagonal operators (`Existential_Operator_of_Existence`, etc.) as the core anchors whenever you need a definitive rule for a domain.

## 1. Objective (reaffirmed with manifold detail)

Aurora must:

- receive human or sensorial language,
- map it directly into the existing `domain × family × dimension` manifold,
- keep processing inside the same semantic substrate and combinatory logic,
- resolve expression via that manifold (multiple law bundles per stance),
- render those law bundles into human language,
- and loop the rendered text back in with metadata that names the exact laws involved and any drift.

## 2. Existing System Assumptions (explicitized)

- The `aurora_manifold_directory` already defines all 125 non-comps—25 per domain—covering every combination of law family (`Existential`, `Temporal`, `Energetic`, `Boundary`, `Agentive`) and dimension (`POLARITY`, `MAGNITUDE`, `OPERATOR`, `COST`, `DIFFERENCE`).
- `aurora_internal/aurora_noncomp_registry.py` enforces those as the only laws; the register indexes canonical polarity/lineage formulas and the `MAGNITUDE`, `IMPACT`, and `AXIS_NC_DIM` relationships.
- `aurora_internal/aurora_meaning_evolution.py` provides shared axis aliases and canonical meaning pairs that anchor domain-level semantics (e.g., `Meaning = (Boundary × Belief × Information) / Purpose`).
- The diagonal operators (`Existential_Operator_of_Existence`, `Temporal_Operator_of_Temporal`, `Energetic_Operator_of_Energetic`, `Boundary_Operator_of_Boundary`, `Agentive_Operator_of_Agency`) are the highest-confidence “rule anchors” for each domain.
- Input, rendering, and reflection must all operate within this manifold; no parallel ontologies.

## 3. Locked Conceptual Model (replaced with manifold grammar)

Model the substrate as **triplets** rather than single layers:

1. **Target domain** – which semantic “field” the sequence is about (`Information`, `Belief`, `Purpose`, `Meaning`, `Understanding`).
2. **Law family** – which primary constraint family is exerting influence (`Existential`, `Temporal`, `Energetic`, `Boundary`, `Agentive`).
3. **Dimension** – how that family is expressed (`POLARITY`, `MAGNITUDE`, `OPERATOR`, `COST`, `DIFFERENCE`).

Every meaning object you build must enumerate the active triplets (e.g., `Boundary_Operator_of_Boundary`, `Temporal_Polarity_of_Belief`, `Agentive_Magnitude_of_Understanding`), including the diagonal operator for the chosen domain.

## 4. Build Goal (manifold-aware components)

The five components remain, but each now deals with explicit manifold coordinates:

### 4.1 Input Mapping Interface

Purpose: convert raw text/speech into a list of candidate triplets (domain, family, dimension) plus confidence/ambiguity.

Responsibilities:

- parse pragmatic signals (from `UtteranceParser`) and axis contexts (`AxisProjector`).
- map tokens/frames to canonical laws using the inventory (e.g., “holds together” → `Boundary_Operator_of_Boundary`; uncertainty → `Temporal_Difference` or `Agentive_Polarity`).
- flag diagonal anchors (`Existential_Operator_of_Existence`, etc.) when a phrase asserts what counts as valid/owned/persistent.
- output `domain_candidates`, `family_strengths`, `dimension_hotspots`, `law_bindings`, `confidence_distribution`, `ambiguity_tags`.

### 4.2 Native Meaning Object Builder

Purpose: gather the mapped law bindings, resolve them into a native packet, and preserve lineage.

Minimum fields:

- `id`, `creation_timestamp`
- `target_domains: Dict[domain, float]` (confidence per domain)
- `law_bindings: List[{domain, family, dimension, strength}]`
- `dominant_diagonal_anchor` (one of the diagonal operators)
- `existence_profile`, `time_profile`, etc., now as `field_vectors` containing {family → dimension weights}
- `ambiguity_map` (which triplets were ambiguous)
- `source_origin` (human_language / sensory_visual / sensory_auditory / internal_generation)
- `semantic_lineage` (link to inventory entries, e.g., `Boundary_Operator_of_Boundary`).

### 4.3 Expression Resolution Engine

Purpose: turn the meaning packet into stance candidates by combining law bundles.

Process:

1. Group the `law_bindings` into candidate bundles leaning on contiguous domains/families (e.g., boundary + agentive combination for accountability, or temporal + existential for persistence claims).
2. For each bundle, compute:
   - `semantic_fidelity_score` (how many high-confidence law bindings it preserves)
   - `dominant_dimension_profile` (Polarity vs Magnitude vs Cost vs Difference emphasis)
   - `relation_signature` (which axes/domains are being referenced)
   - `human_legibility_bias` (does the bundle prefer concise boundary-driven phrasing or diffuse agentive reflection?)
3. Present multiple stance candidates (e.g., `precise-correction` vs `cautious-exploration`) that differ in their chosen law bundles but keep fidelity.

### 4.4 Human Rendering Layer

Purpose: render a selected stance candidate into text while mirroring the chosen law bundle.

Inputs:

- selected stance candidate (with law bundle)
- native meaning object
- `target_audience` / style constraints

Responsibilities:

- When law bundle emphasizes `POLARITY`, favor binary framing (“this is valid / not valid”).
- When `MAGNITUDE` is high, intensify adjectives/clause depth.
- When `OPERATOR` leg is diagonal, mention the governing rule (“what counts as a signal is…”).
- When `COST` dominates, articulate burden/effort.
- When `DIFFERENCE` dominates, highlight mismatches/drift (“there is a gap between…”).
- Preserve non-comp lineages by linking rendered claims to inventory entries (e.g., `Boundary_Operator_of_Boundary` → mention framing/separation).
- Record metadata: `render_id`, `tone_estimate`, `drift_score`, `law_bindings_represented`.

### 4.5 Reflection / Feedback Loop

Purpose: compare the intended law bundle with what the renderer actually expressed.

Inputs:

- native meaning object
- stance candidate metadata
- rendered output + metadata

Responsibilities:

- Parse/rendered text back into law triplets (reuse Input Mapping logic).
- Tag drifts: e.g., `law_diff` between intended diagonal anchor and expressed anchor.
- Update `reflection_record` with `preserved_elements` (triplets preserved), `shifted_elements` (law combos that shifted), and `future_bias_notes`.
- Feed tags into memory/logging so Aurora learns which bundles survive expression without drift.

## 5. Minimum Viable Build (domain-anchored pilot)

Do not try all five domains simultaneously.

1. Pick one target domain (recommended: `B = Meaning` or `A = Understanding`).
2. Within that domain, pilot a “bundle” of five laws (one per law family):
   - `Existential_Operator_of_Boundary` (clarifies what counts as a distinct meaning structure),
   - `Temporal_Magnitude_of_Boundary` (persistence strength),
   - `Energetic_Cost_of_Boundary` (effort to maintain meaning),
   - `Boundary_Operator_of_Boundary` (framing rules),
   - `Agentive_Difference_of_Boundary` (ownership mismatch/resolution).
3. Build one input mapping pass that recognizes those law signals, one meaning object schema that records them, one stance candidate derived from the bundle, one rendered sentence, and one reflection record measuring law drift.

## 6. Success Criteria (manifold-aware)

- Human input maps into at least one high-confidence `domain × family × dimension` bundle.
- Native meaning objects preserve those law bindings, including the diagonal anchor.
- Expression resolution produces multiple stance candidates that differ by law bundles and clearly show agency vs boundary vs temporal emphasis.
- Rendered text reflects the chosen law bundle (e.g., a `Boundary`-driven bundle uses framing language, an `Agentive`-driven bundle signals commitment).
- Reflection detects law drift and records which law bindings misaligned.
- No new ontology steps outside of the 125-law manifold.

## 7. Failure Conditions to Avoid

- Don’t collapse the manifold back into five coarse layers or generic “understanding/meaning/purpose”.
- Don’t let rendering bypass the exact law binding (e.g., render a diagonal operator without naming its frame or rule).
- Don’t let reflection flag only tone; it must compare law triplets.
- Don’t hardcode templates that ignore the dimension (`COST` vs `POLARITY`) differences.
