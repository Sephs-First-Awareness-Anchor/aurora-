# Selected Runtime Activation: proposition_understanding

- `path_id`: `LIN:proposition_understanding:0538f1cf4d`
- `final_output_id`: `L:2fd80d3d26`
- `run_dir`: `aurora_state/ability_lineages/proposition_understanding/materialized/lin_proposition_understanding_0538f1cf4d`
- `proposition_substrate`: `True`
- `max_nodes`: `192`
- `max_edges`: `864`

## Runtime Patch Plan

- `proposition_understanding.systems.merge_state` -> `systems` / `merge_state`
- `proposition_understanding.working_memory.activation` -> `working_memory` / `apply_lineage_activation`
- `proposition_understanding.gap_system.flags` -> `comprehension_gap_system` / `set_attrs`
- `proposition_understanding.language.flags` -> `language_orchestra` / `set_attrs`
- `proposition_understanding.perception.flags` -> `perception` / `set_attrs`
- `proposition_understanding.oets.flags` -> `perception.oets` / `set_attrs`
- `proposition_understanding.genealogy.state` -> `genealogy` / `merge_state`
