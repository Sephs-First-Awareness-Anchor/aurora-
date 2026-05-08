# Selected Lineage Path: proposition_understanding

- `path_id`: `LIN:proposition_understanding:0538f1cf4d`
- `strategy`: `constraint_recapitulation_v1`
- `rationale`: Directed recapitulation from 5-constraint seed stages into late-stage proposition understanding without skipping promotion layers.

## Stages

### G1 `claim_atom`
- label: Claim Atom
- kind: seed
- dominant_axis: `X`
- constraints: `X`
- purpose_lane: `meaning`
- operator_action: `admissibility_gating`
- parents: `seed`
- summary: Minimal admissible proposition shell with subject, relation, and object slots.
- target_files: `aurora.py, aurora_internal/aurora_ontological_scaffolding.py`
- ripple: Enables claim-shaped storage instead of surface-only fact text.
- ripple: Makes admissibility the root of proposition formation.
- writeback: `working_memory.claim_atoms` <- `increment` `1`
- writeback: `oets.proposition_nodes` <- `increment` `1`
- writeback: `pipeline.active_schemas` <- `append_unique` `claim_atom`

### G1 `turn_binding`
- label: Turn Binding
- kind: seed
- dominant_axis: `T`
- constraints: `T`
- purpose_lane: `communication`
- operator_action: `temporal_orchestration`
- parents: `seed`
- summary: Carries one proposition shell across adjacent turns without topic collapse.
- target_files: `aurora.py, aurora_internal/aurora_language_state.py`
- ripple: Creates temporal continuity for later discourse links.
- ripple: Lets follow-up turns inherit a stable active proposition.
- writeback: `working_memory.temporal_bindings` <- `increment` `1`
- writeback: `expression.meaning_anchor_depth` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `multi_turn_stability`

### G1 `speaker_boundary`
- label: Speaker Boundary
- kind: seed
- dominant_axis: `B`
- constraints: `B, X`
- purpose_lane: `meaning`
- operator_action: `boundary_shaping`
- parents: `seed`
- summary: Separates user, Aurora, and external-source ownership around the same claim shell.
- target_files: `aurora.py, aurora_internal/aurora_comprehension_gap.py`
- ripple: Prevents one speaker's claim from overwriting another's.
- ripple: Creates the first branchable distinction surface for contradiction handling.
- writeback: `working_memory.speaker_boundaries` <- `increment` `1`
- writeback: `gap_system.referent_repair_depth` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `ambiguity_handling`

### G1 `uncertainty_weight`
- label: Uncertainty Weight
- kind: seed
- dominant_axis: `N`
- constraints: `N, X`
- purpose_lane: `meaning`
- operator_action: `energy_economics`
- parents: `seed`
- summary: Attaches salience, confidence, and compression weight to proposition shells.
- target_files: `aurora.py, aurora_internal/aurora_language_state.py`
- ripple: Lets weak claims decay and strong claims persist.
- ripple: Makes uncertainty part of proposition state rather than style only.
- writeback: `working_memory.weighted_claims` <- `increment` `1`
- writeback: `expression.uncertainty_channel` <- `max` `0.35`
- writeback: `rubric.target_dimensions` <- `append_unique` `uncertainty_signaling`

### G1 `repair_choice`
- label: Repair Choice
- kind: seed
- dominant_axis: `A`
- constraints: `A, B`
- purpose_lane: `communication`
- operator_action: `agency_direction`
- parents: `seed`
- summary: Chooses ask, defer, infer, or commit when branch pressure rises.
- target_files: `aurora.py, aurora_internal/aurora_comprehension_gap.py`
- ripple: Turns ambiguity into action policy rather than passive confusion.
- ripple: Creates an agency surface for revising meaning paths.
- writeback: `gap_system.branch_repair_enabled` <- `set` `True`
- writeback: `working_memory.repair_policies` <- `increment` `1`
- writeback: `pipeline.active_schemas` <- `append_unique` `repair_choice`

### G2 `claim_continuity`
- label: Claim Continuity
- kind: coupling
- dominant_axis: `T`
- constraints: `X, T`
- purpose_lane: `meaning`
- operator_action: `temporal_orchestration`
- parents: `claim_atom, turn_binding`
- summary: An admissible claim now persists as the same object across turns.
- target_files: `aurora.py`
- ripple: Follow-up reasoning can target the same proposition repeatedly.
- ripple: Turn order becomes part of proposition identity.
- writeback: `working_memory.active_propositions` <- `increment` `1`
- writeback: `pipeline.proposition_threads` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `context_carryover`

### G2 `owned_claim`
- label: Owned Claim
- kind: coupling
- dominant_axis: `B`
- constraints: `X, B`
- purpose_lane: `meaning`
- operator_action: `boundary_shaping`
- parents: `claim_atom, speaker_boundary`
- summary: A claim becomes owned by a speaker/source instead of existing as anonymous content.
- target_files: `aurora.py, aurora_internal/aurora_identity_persistence.py`
- ripple: Speaker attribution becomes native to proposition storage.
- ripple: The system can keep multiple incompatible claims without flattening them.
- writeback: `memory.source_scoped_claims` <- `increment` `1`
- writeback: `working_memory.speaker_owned_claims` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `contradiction_handling`

### G2 `repairable_branch`
- label: Repairable Branch
- kind: coupling
- dominant_axis: `A`
- constraints: `B, A`
- purpose_lane: `communication`
- operator_action: `agency_direction`
- parents: `speaker_boundary, repair_choice`
- summary: A boundary split can now trigger targeted repair instead of forcing immediate collapse.
- target_files: `aurora.py, aurora_internal/aurora_comprehension_gap.py`
- ripple: Competing interpretations can stay live long enough to be resolved.
- ripple: Clarification becomes branch management rather than a loose prompt.
- writeback: `gap_system.active_branches` <- `increment` `1`
- writeback: `working_memory.repairable_branches` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `misunderstanding_repair`

### G2 `weighted_claim`
- label: Weighted Claim
- kind: coupling
- dominant_axis: `N`
- constraints: `X, N`
- purpose_lane: `meaning`
- operator_action: `energy_economics`
- parents: `claim_atom, uncertainty_weight`
- summary: An admissible claim now carries confidence and retention pressure.
- target_files: `aurora.py, aurora_internal/aurora_language_state.py`
- ripple: Weakly grounded claims no longer compete equally with strong claims.
- ripple: Uncertainty can shape retrieval, reply tone, and revision priority.
- writeback: `memory.weighted_recall_paths` <- `increment` `1`
- writeback: `expression.uncertainty_channel` <- `max` `0.5`
- writeback: `pipeline.weighted_claim_lookup` <- `set` `True`

### G3 `proposition_lineage`
- label: Proposition Lineage
- kind: coupling
- dominant_axis: `T`
- constraints: `X, T, B`
- purpose_lane: `meaning`
- operator_action: `temporal_orchestration`
- parents: `claim_continuity, owned_claim`
- summary: A proposition becomes a tracked lineage with temporal continuity and speaker ownership.
- target_files: `aurora.py, aurora_internal/constraint_genealogy.py`
- ripple: Claims can be revised instead of replaced.
- ripple: Contradiction and support edges gain a stable object to point at.
- writeback: `genealogy.proposition_lineages` <- `increment` `1`
- writeback: `oets.proposition_nodes` <- `increment` `2`
- writeback: `pipeline.proposition_graph_enabled` <- `set` `True`

### G3 `provenance_weighting`
- label: Provenance Weighting
- kind: coupling
- dominant_axis: `N`
- constraints: `X, B, N`
- purpose_lane: `meaning`
- operator_action: `energy_economics`
- parents: `owned_claim, weighted_claim`
- summary: Claim confidence now depends on both evidence strength and source ownership.
- target_files: `aurora.py, aurora_internal/aurora_identity_persistence.py`
- ripple: User-asserted, Aurora-inferred, and external claims can be ranked separately.
- ripple: Provenance starts to regulate memory and answer selection.
- writeback: `memory.provenance_edges` <- `increment` `2`
- writeback: `working_memory.source_weighting_enabled` <- `set` `True`
- writeback: `rubric.target_dimensions` <- `append_unique` `semantic_precision`

### G4 `belief_revision_graph`
- label: Belief Revision Graph
- kind: coupling
- dominant_axis: `A`
- constraints: `X, T, B, A`
- purpose_lane: `intelligence`
- operator_action: `agency_direction`
- parents: `proposition_lineage, repairable_branch`
- summary: Tracked propositions can now branch, repair, retract, and reconverge.
- target_files: `aurora.py, aurora_internal/constraint_genealogy.py`
- ripple: Contradictions become navigable graph events instead of dead ends.
- ripple: Revision policy becomes native to proposition structure.
- writeback: `working_memory.belief_branches` <- `increment` `2`
- writeback: `genealogy.revision_paths` <- `increment` `1`
- writeback: `pipeline.belief_revision_enabled` <- `set` `True`

### G3 `causal_commitment`
- label: Causal Commitment
- kind: coupling
- dominant_axis: `A`
- constraints: `X, T, A`
- purpose_lane: `intelligence`
- operator_action: `agency_direction`
- parents: `claim_continuity, repair_choice`
- summary: The system can choose and preserve causal reading paths through an active proposition.
- target_files: `aurora.py, aurora_internal/aurora_ontological_scaffolding.py`
- ripple: Why-questions gain a native path through proposition state.
- ripple: Reasoning can carry forward selected causal commitments across turns.
- writeback: `oets.causal_edges` <- `increment` `1`
- writeback: `working_memory.causal_paths` <- `increment` `1`
- writeback: `rubric.target_dimensions` <- `append_unique` `implied_intent_inference`

### G4 `causal_proposition_mesh`
- label: Causal Proposition Mesh
- kind: coupling
- dominant_axis: `T`
- constraints: `X, T, B, A`
- purpose_lane: `intelligence`
- operator_action: `temporal_orchestration`
- parents: `proposition_lineage, causal_commitment`
- summary: Propositions are now linked by continuity, ownership, and selected causal paths.
- target_files: `aurora.py, aurora_internal/aurora_ontological_scaffolding.py`
- ripple: Multi-turn reasoning can stay on the same proposition while answering why/how questions.
- ripple: Causal support stops being a one-shot surface explanation.
- writeback: `oets.causal_edges` <- `increment` `2`
- writeback: `pipeline.causal_mesh_enabled` <- `set` `True`
- writeback: `expression.meaning_anchor_depth` <- `increment` `1`

### G5 `proposition_understanding`
- label: Proposition Understanding
- kind: coupling
- dominant_axis: `X`
- constraints: `X, T, N, B, A`
- purpose_lane: `meaning`
- operator_action: `admissibility_gating`
- parents: `causal_proposition_mesh, provenance_weighting`
- summary: Full proposition substrate: claim identity, temporal continuity, provenance weighting, branching repair, and causal mesh.
- target_files: `aurora.py, aurora_internal/aurora_ontological_scaffolding.py, aurora_internal/aurora_language_state.py`
- ripple: Meaning continuity becomes proposition-native instead of topic-word-native.
- ripple: Communication, reasoning, and grounding can now evolve against the same shared substrate.
- writeback: `pipeline.proposition_understanding` <- `set` `True`
- writeback: `expression.proposition_voice_enabled` <- `set` `True`
- writeback: `rubric.target_dimensions` <- `append_unique` `coherence_maintenance`
- writeback: `rubric.target_dimensions` <- `append_unique` `multi_turn_stability`
