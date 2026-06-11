#!/usr/bin/env python3
"""
AURORA ABILITY LINEAGE COMPILER
================================
Constraint-native directed recapitulation for missing abilities.

This module does not bolt on a finished capability. It:

1. Selects a target ability phenotype.
2. Traces that phenotype back to constraint-native seed stages.
3. Writes the full staged lineage path to disk.
4. Replays the lineage through ConstraintGenealogyLogger.observe()
   so composite stages are promoted as real couplings rather than
   appearing as direct late-stage insertions.

Current built-in target:
  - proposition_understanding
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

# Genealogy replay is an offline structural task; prevent import-time
# hardware initialization from the broader Aurora stack.
os.environ.setdefault("AURORA_SKIP_HARDWARE_IMPORTS", "1")

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    EnvironmentVector,
    GenealogyConfig,
    PressureVec,
    TraceItem,
    _augment_ability_profile_with_origin,
    _operator_action_for_axis,
)


TARGET_ALIASES: Dict[str, str] = {
    "proposition_understanding": "proposition_understanding",
    "discourse_understanding": "proposition_understanding",
    "belief_graph": "proposition_understanding",
    "proposition_graph": "proposition_understanding",
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def _slug(token: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(token or "").strip().lower()).strip("_")


def _wb(subsystem: str, key: str, mode: str, value: Any) -> SystemWriteback:
    return SystemWriteback(subsystem=subsystem, key=key, mode=mode, value=value)


@dataclass(frozen=True)
class SystemWriteback:
    subsystem: str
    key: str
    mode: str
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "key": self.key,
            "mode": self.mode,
            "value": self.value,
        }


@dataclass(frozen=True)
class LineageStage:
    stage_id: str
    generation: int
    label: str
    kind: str
    dominant_axis: str
    constraints: Tuple[str, ...]
    summary: str
    purpose_lane: str = "meaning"
    operator_action: str = ""
    parents: Tuple[str, ...] = tuple()
    target_files: Tuple[str, ...] = tuple()
    ripple_effects: Tuple[str, ...] = tuple()
    system_writebacks: Tuple[SystemWriteback, ...] = tuple()
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "generation": int(self.generation),
            "label": self.label,
            "kind": self.kind,
            "dominant_axis": self.dominant_axis,
            "constraints": list(self.constraints),
            "summary": self.summary,
            "purpose_lane": self.purpose_lane,
            "operator_action": self.operator_action or _operator_action_for_axis(self.dominant_axis),
            "parents": list(self.parents),
            "target_files": list(self.target_files),
            "ripple_effects": list(self.ripple_effects),
            "system_writebacks": [wb.to_dict() for wb in self.system_writebacks],
            "notes": self.notes,
        }


@dataclass
class CompiledLineagePath:
    path_id: str
    target_ability: str
    selected_strategy: str
    rationale: str
    stages: List[LineageStage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "target_ability": self.target_ability,
            "selected_strategy": self.selected_strategy,
            "rationale": self.rationale,
            "created_at": float(self.created_at),
            "stages": [stage.to_dict() for stage in self.stages],
        }


@dataclass
class MaterializedStage:
    stage_id: str
    kind: str
    output_kind: str
    output_id: str
    generation: int
    attempts: int = 0
    parents: Tuple[str, ...] = tuple()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "kind": self.kind,
            "output_kind": self.output_kind,
            "output_id": self.output_id,
            "generation": int(self.generation),
            "attempts": int(self.attempts),
            "parents": list(self.parents),
        }


@dataclass
class MaterializationResult:
    path_id: str
    target_ability: str
    run_dir: str
    materialized_stages: List[MaterializedStage] = field(default_factory=list)
    final_output_id: str = ""
    final_output_kind: str = ""
    links_promoted: int = 0
    relief_events: int = 0
    ripple_log_path: str = ""
    activation_manifest_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "target_ability": self.target_ability,
            "run_dir": self.run_dir,
            "final_output_id": self.final_output_id,
            "final_output_kind": self.final_output_kind,
            "links_promoted": int(self.links_promoted),
            "relief_events": int(self.relief_events),
            "ripple_log_path": self.ripple_log_path,
            "activation_manifest_path": self.activation_manifest_path,
            "materialized_stages": [stage.to_dict() for stage in self.materialized_stages],
        }


def _proposition_understanding_blueprint() -> List[LineageStage]:
    return [
        LineageStage(
            stage_id="claim_atom",
            generation=1,
            label="Claim Atom",
            kind="seed",
            dominant_axis="X",
            constraints=("X",),
            purpose_lane="meaning",
            summary="Minimal admissible proposition shell with subject, relation, and object slots.",
            target_files=("aurora.py", "aurora_internal/aurora_ontological_scaffolding.py"),
            ripple_effects=(
                "Enables claim-shaped storage instead of surface-only fact text.",
                "Makes admissibility the root of proposition formation.",
            ),
            system_writebacks=(
                _wb("working_memory", "claim_atoms", "increment", 1),
                _wb("oets", "proposition_nodes", "increment", 1),
                _wb("pipeline", "active_schemas", "append_unique", "claim_atom"),
            ),
        ),
        LineageStage(
            stage_id="turn_binding",
            generation=1,
            label="Turn Binding",
            kind="seed",
            dominant_axis="T",
            constraints=("T",),
            purpose_lane="communication",
            summary="Carries one proposition shell across adjacent turns without topic collapse.",
            target_files=("aurora.py", "aurora_internal/aurora_language_state.py"),
            ripple_effects=(
                "Creates temporal continuity for later discourse links.",
                "Lets follow-up turns inherit a stable active proposition.",
            ),
            system_writebacks=(
                _wb("working_memory", "temporal_bindings", "increment", 1),
                _wb("expression", "meaning_anchor_depth", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "multi_turn_stability"),
            ),
        ),
        LineageStage(
            stage_id="speaker_boundary",
            generation=1,
            label="Speaker Boundary",
            kind="seed",
            dominant_axis="B",
            constraints=("B", "X"),
            purpose_lane="meaning",
            summary="Separates user, Aurora, and external-source ownership around the same claim shell.",
            target_files=("aurora.py", "aurora_internal/aurora_comprehension_gap.py"),
            ripple_effects=(
                "Prevents one speaker's claim from overwriting another's.",
                "Creates the first branchable distinction surface for contradiction handling.",
            ),
            system_writebacks=(
                _wb("working_memory", "speaker_boundaries", "increment", 1),
                _wb("gap_system", "referent_repair_depth", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "ambiguity_handling"),
            ),
        ),
        LineageStage(
            stage_id="uncertainty_weight",
            generation=1,
            label="Uncertainty Weight",
            kind="seed",
            dominant_axis="N",
            constraints=("N", "X"),
            purpose_lane="meaning",
            summary="Attaches salience, confidence, and compression weight to proposition shells.",
            target_files=("aurora.py", "aurora_internal/aurora_language_state.py"),
            ripple_effects=(
                "Lets weak claims decay and strong claims persist.",
                "Makes uncertainty part of proposition state rather than style only.",
            ),
            system_writebacks=(
                _wb("working_memory", "weighted_claims", "increment", 1),
                _wb("expression", "uncertainty_channel", "max", 0.35),
                _wb("rubric", "target_dimensions", "append_unique", "uncertainty_signaling"),
            ),
        ),
        LineageStage(
            stage_id="repair_choice",
            generation=1,
            label="Repair Choice",
            kind="seed",
            dominant_axis="A",
            constraints=("A", "B"),
            purpose_lane="communication",
            summary="Chooses ask, defer, infer, or commit when branch pressure rises.",
            target_files=("aurora.py", "aurora_internal/aurora_comprehension_gap.py"),
            ripple_effects=(
                "Turns ambiguity into action policy rather than passive confusion.",
                "Creates an agency surface for revising meaning paths.",
            ),
            system_writebacks=(
                _wb("gap_system", "branch_repair_enabled", "set", True),
                _wb("working_memory", "repair_policies", "increment", 1),
                _wb("pipeline", "active_schemas", "append_unique", "repair_choice"),
            ),
        ),
        LineageStage(
            stage_id="claim_continuity",
            generation=2,
            label="Claim Continuity",
            kind="coupling",
            dominant_axis="T",
            constraints=("X", "T"),
            parents=("claim_atom", "turn_binding"),
            purpose_lane="meaning",
            summary="An admissible claim now persists as the same object across turns.",
            target_files=("aurora.py",),
            ripple_effects=(
                "Follow-up reasoning can target the same proposition repeatedly.",
                "Turn order becomes part of proposition identity.",
            ),
            system_writebacks=(
                _wb("working_memory", "active_propositions", "increment", 1),
                _wb("pipeline", "proposition_threads", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "context_carryover"),
            ),
        ),
        LineageStage(
            stage_id="owned_claim",
            generation=2,
            label="Owned Claim",
            kind="coupling",
            dominant_axis="B",
            constraints=("X", "B"),
            parents=("claim_atom", "speaker_boundary"),
            purpose_lane="meaning",
            summary="A claim becomes owned by a speaker/source instead of existing as anonymous content.",
            target_files=("aurora.py", "aurora_internal/aurora_identity_persistence.py"),
            ripple_effects=(
                "Speaker attribution becomes native to proposition storage.",
                "The system can keep multiple incompatible claims without flattening them.",
            ),
            system_writebacks=(
                _wb("memory", "source_scoped_claims", "increment", 1),
                _wb("working_memory", "speaker_owned_claims", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "contradiction_handling"),
            ),
        ),
        LineageStage(
            stage_id="repairable_branch",
            generation=2,
            label="Repairable Branch",
            kind="coupling",
            dominant_axis="A",
            constraints=("B", "A"),
            parents=("speaker_boundary", "repair_choice"),
            purpose_lane="communication",
            summary="A boundary split can now trigger targeted repair instead of forcing immediate collapse.",
            target_files=("aurora.py", "aurora_internal/aurora_comprehension_gap.py"),
            ripple_effects=(
                "Competing interpretations can stay live long enough to be resolved.",
                "Clarification becomes branch management rather than a loose prompt.",
            ),
            system_writebacks=(
                _wb("gap_system", "active_branches", "increment", 1),
                _wb("working_memory", "repairable_branches", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "misunderstanding_repair"),
            ),
        ),
        LineageStage(
            stage_id="weighted_claim",
            generation=2,
            label="Weighted Claim",
            kind="coupling",
            dominant_axis="N",
            constraints=("X", "N"),
            parents=("claim_atom", "uncertainty_weight"),
            purpose_lane="meaning",
            summary="An admissible claim now carries confidence and retention pressure.",
            target_files=("aurora.py", "aurora_internal/aurora_language_state.py"),
            ripple_effects=(
                "Weakly grounded claims no longer compete equally with strong claims.",
                "Uncertainty can shape retrieval, reply tone, and revision priority.",
            ),
            system_writebacks=(
                _wb("memory", "weighted_recall_paths", "increment", 1),
                _wb("expression", "uncertainty_channel", "max", 0.5),
                _wb("pipeline", "weighted_claim_lookup", "set", True),
            ),
        ),
        LineageStage(
            stage_id="proposition_lineage",
            generation=3,
            label="Proposition Lineage",
            kind="coupling",
            dominant_axis="T",
            constraints=("X", "T", "B"),
            parents=("claim_continuity", "owned_claim"),
            purpose_lane="meaning",
            summary="A proposition becomes a tracked lineage with temporal continuity and speaker ownership.",
            target_files=("aurora.py", "aurora_internal/constraint_genealogy.py"),
            ripple_effects=(
                "Claims can be revised instead of replaced.",
                "Contradiction and support edges gain a stable object to point at.",
            ),
            system_writebacks=(
                _wb("genealogy", "proposition_lineages", "increment", 1),
                _wb("oets", "proposition_nodes", "increment", 2),
                _wb("pipeline", "proposition_graph_enabled", "set", True),
            ),
        ),
        LineageStage(
            stage_id="provenance_weighting",
            generation=3,
            label="Provenance Weighting",
            kind="coupling",
            dominant_axis="N",
            constraints=("X", "B", "N"),
            parents=("owned_claim", "weighted_claim"),
            purpose_lane="meaning",
            summary="Claim confidence now depends on both evidence strength and source ownership.",
            target_files=("aurora.py", "aurora_internal/aurora_identity_persistence.py"),
            ripple_effects=(
                "User-asserted, Aurora-inferred, and external claims can be ranked separately.",
                "Provenance starts to regulate memory and answer selection.",
            ),
            system_writebacks=(
                _wb("memory", "provenance_edges", "increment", 2),
                _wb("working_memory", "source_weighting_enabled", "set", True),
                _wb("rubric", "target_dimensions", "append_unique", "semantic_precision"),
            ),
        ),
        LineageStage(
            stage_id="belief_revision_graph",
            generation=4,
            label="Belief Revision Graph",
            kind="coupling",
            dominant_axis="A",
            constraints=("X", "T", "B", "A"),
            parents=("proposition_lineage", "repairable_branch"),
            purpose_lane="intelligence",
            summary="Tracked propositions can now branch, repair, retract, and reconverge.",
            target_files=("aurora.py", "aurora_internal/constraint_genealogy.py"),
            ripple_effects=(
                "Contradictions become navigable graph events instead of dead ends.",
                "Revision policy becomes native to proposition structure.",
            ),
            system_writebacks=(
                _wb("working_memory", "belief_branches", "increment", 2),
                _wb("genealogy", "revision_paths", "increment", 1),
                _wb("pipeline", "belief_revision_enabled", "set", True),
            ),
        ),
        LineageStage(
            stage_id="causal_commitment",
            generation=3,
            label="Causal Commitment",
            kind="coupling",
            dominant_axis="A",
            constraints=("X", "T", "A"),
            parents=("claim_continuity", "repair_choice"),
            purpose_lane="intelligence",
            summary="The system can choose and preserve causal reading paths through an active proposition.",
            target_files=("aurora.py", "aurora_internal/aurora_ontological_scaffolding.py"),
            ripple_effects=(
                "Why-questions gain a native path through proposition state.",
                "Reasoning can carry forward selected causal commitments across turns.",
            ),
            system_writebacks=(
                _wb("oets", "causal_edges", "increment", 1),
                _wb("working_memory", "causal_paths", "increment", 1),
                _wb("rubric", "target_dimensions", "append_unique", "implied_intent_inference"),
            ),
        ),
        LineageStage(
            stage_id="causal_proposition_mesh",
            generation=4,
            label="Causal Proposition Mesh",
            kind="coupling",
            dominant_axis="T",
            constraints=("X", "T", "B", "A"),
            parents=("proposition_lineage", "causal_commitment"),
            purpose_lane="intelligence",
            summary="Propositions are now linked by continuity, ownership, and selected causal paths.",
            target_files=("aurora.py", "aurora_internal/aurora_ontological_scaffolding.py"),
            ripple_effects=(
                "Multi-turn reasoning can stay on the same proposition while answering why/how questions.",
                "Causal support stops being a one-shot surface explanation.",
            ),
            system_writebacks=(
                _wb("oets", "causal_edges", "increment", 2),
                _wb("pipeline", "causal_mesh_enabled", "set", True),
                _wb("expression", "meaning_anchor_depth", "increment", 1),
            ),
        ),
        LineageStage(
            stage_id="proposition_understanding",
            generation=5,
            label="Proposition Understanding",
            kind="coupling",
            dominant_axis="X",
            constraints=("X", "T", "N", "B", "A"),
            parents=("causal_proposition_mesh", "provenance_weighting"),
            purpose_lane="meaning",
            summary="Full proposition substrate: claim identity, temporal continuity, provenance weighting, branching repair, and causal mesh.",
            target_files=(
                "aurora.py",
                "aurora_internal/aurora_ontological_scaffolding.py",
                "aurora_internal/aurora_language_state.py",
            ),
            ripple_effects=(
                "Meaning continuity becomes proposition-native instead of topic-word-native.",
                "Communication, reasoning, and grounding can now evolve against the same shared substrate.",
            ),
            system_writebacks=(
                _wb("pipeline", "proposition_understanding", "set", True),
                _wb("expression", "proposition_voice_enabled", "set", True),
                _wb("rubric", "target_dimensions", "append_unique", "coherence_maintenance"),
                _wb("rubric", "target_dimensions", "append_unique", "multi_turn_stability"),
            ),
        ),
    ]


def _lineage_blueprint_for(target: str) -> List[LineageStage]:
    canonical = TARGET_ALIASES.get(_slug(target), "")
    if canonical == "proposition_understanding":
        return _proposition_understanding_blueprint()
    raise ValueError(f"unsupported target ability: {target}")


class AbilityLineageCompiler:
    """
    Compiles target abilities into constraint-native staged lineage paths and
    optionally materializes them through a dedicated genealogy replay run.
    """

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "ability_lineages")):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def compile_target(
        self,
        target_ability: str,
        strategy: str = "constraint_recapitulation_v1",
    ) -> CompiledLineagePath:
        canonical = TARGET_ALIASES.get(_slug(target_ability), _slug(target_ability))
        stages = _lineage_blueprint_for(canonical)
        digest = hashlib.sha1(f"{canonical}:{strategy}:{time.time()}".encode()).hexdigest()[:10]
        path_id = f"LIN:{canonical}:{digest}"
        return CompiledLineagePath(
            path_id=path_id,
            target_ability=canonical,
            selected_strategy=strategy,
            rationale=(
                "Directed recapitulation from 5-constraint seed stages into late-stage "
                "proposition understanding without skipping promotion layers."
            ),
            stages=stages,
        )

    def autowrite_selected_path(self, path: CompiledLineagePath) -> Dict[str, str]:
        target_dir = os.path.join(self.storage_dir, path.target_ability)
        runs_dir = os.path.join(target_dir, "runs")
        os.makedirs(runs_dir, exist_ok=True)

        json_payload = path.to_dict()
        version_json = os.path.join(runs_dir, f"{_slug(path.path_id)}.json")
        selected_json = os.path.join(target_dir, "selected_path.json")
        version_md = os.path.join(runs_dir, f"{_slug(path.path_id)}.md")
        selected_md = os.path.join(target_dir, "selected_path.md")

        for out_path in (version_json, selected_json):
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(json_payload, fh, indent=2)

        md_text = self._render_markdown(path)
        for out_path in (version_md, selected_md):
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(md_text)

        return {
            "selected_json": selected_json,
            "selected_md": selected_md,
            "version_json": version_json,
            "version_md": version_md,
        }

    def materialize_path(
        self,
        path: CompiledLineagePath,
        *,
        k_min: int = 4,
        max_attempts_per_stage: int = 24,
    ) -> MaterializationResult:
        target_dir = os.path.join(self.storage_dir, path.target_ability)
        run_dir = os.path.join(target_dir, "materialized", _slug(path.path_id))
        os.makedirs(run_dir, exist_ok=True)

        cfg = GenealogyConfig(
            K_MIN=max(3, int(k_min)),
            RELIEF_EPS=0.004,
            RELIEF_TOTAL_EPS=0.010,
            RELIEF_PROMOTE_MIN=0.005,
            RELIEF_STDEV_MAX=0.08,
            NET_MIN=0.001,
            # Synthetic recapitulation stages are scaffold-forming, not
            # production policies. Give late composite stages enough admissibility
            # slack to form without tripping the live-system X-risk ceiling.
            X_RISK_MAX=0.25,
            TRACE_REWRITE_ON_PROMOTE=True,
            RUBRIC_MIN_EVENTS=max(4, int(k_min)),
        )
        logger = ConstraintGenealogyLogger(run_id=_slug(path.path_id), config=cfg, output_dir=run_dir)

        stage_outputs: Dict[str, Dict[str, str]] = {}
        materialized: List[MaterializedStage] = []
        shadow_state = self._initial_shadow_state(path)
        ripple_log: List[Dict[str, Any]] = []

        try:
            for stage in path.stages:
                if stage.kind == "seed":
                    ability_id = self._register_seed_stage(logger, path, stage)
                    stage_outputs[stage.stage_id] = {"kind": "ABILITY", "id": ability_id}
                    materialized.append(MaterializedStage(
                        stage_id=stage.stage_id,
                        kind=stage.kind,
                        output_kind="ABILITY",
                        output_id=ability_id,
                        generation=stage.generation,
                    ))
                    self._apply_stage_writebacks(
                        shadow_state,
                        stage,
                        output_id=ability_id,
                        output_kind="ABILITY",
                        ripple_log=ripple_log,
                    )
                    continue

                parent_items = [stage_outputs[parent_id] for parent_id in stage.parents]
                link_id, attempts = self._materialize_coupling_stage(
                    logger,
                    path,
                    stage,
                    parent_items,
                    max_attempts=self._attempt_budget_for_stage(stage, max_attempts_per_stage),
                )
                stage_outputs[stage.stage_id] = {"kind": "LINK", "id": link_id}
                materialized.append(MaterializedStage(
                    stage_id=stage.stage_id,
                    kind=stage.kind,
                    output_kind="LINK",
                    output_id=link_id,
                    generation=stage.generation,
                    attempts=attempts,
                    parents=tuple(stage.parents),
                ))
                self._apply_stage_writebacks(
                    shadow_state,
                    stage,
                    output_id=link_id,
                    output_kind="LINK",
                    ripple_log=ripple_log,
                )

            logger.flush_files()
        finally:
            logger.close()

        final_stage = materialized[-1] if materialized else MaterializedStage("", "", "", "", 0)
        ripple_log_path = os.path.join(run_dir, "system_ripple_log.json")
        with open(ripple_log_path, "w", encoding="utf-8") as fh:
            json.dump({
                "path_id": path.path_id,
                "target_ability": path.target_ability,
                "shadow_state": shadow_state,
                "ripple_log": ripple_log,
            }, fh, indent=2)

        result = MaterializationResult(
            path_id=path.path_id,
            target_ability=path.target_ability,
            run_dir=run_dir,
            materialized_stages=materialized,
            final_output_id=final_stage.output_id,
            final_output_kind=final_stage.output_kind,
            links_promoted=len(logger.links),
            relief_events=int(logger.relief_event_count),
            ripple_log_path=ripple_log_path,
        )

        activation_manifest = self._build_activation_manifest(
            path=path,
            result=result,
            shadow_state=shadow_state,
            ripple_log=ripple_log,
        )
        activation_paths = self._write_activation_artifacts(
            path=path,
            activation_manifest=activation_manifest,
        )
        result.activation_manifest_path = str(activation_paths.get("selected_json", "") or "")

        result_path = os.path.join(run_dir, "materialization_result.json")
        with open(result_path, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2)

        summary_path = os.path.join(target_dir, "selected_materialization.json")
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2)

        return result

    def _render_markdown(self, path: CompiledLineagePath) -> str:
        lines = [
            f"# Selected Lineage Path: {path.target_ability}",
            "",
            f"- `path_id`: `{path.path_id}`",
            f"- `strategy`: `{path.selected_strategy}`",
            f"- `rationale`: {path.rationale}",
            "",
            "## Stages",
            "",
        ]
        for stage in path.stages:
            parent_text = ", ".join(stage.parents) if stage.parents else "seed"
            lines.extend([
                f"### G{stage.generation} `{stage.stage_id}`",
                f"- label: {stage.label}",
                f"- kind: {stage.kind}",
                f"- dominant_axis: `{stage.dominant_axis}`",
                f"- constraints: `{', '.join(stage.constraints)}`",
                f"- purpose_lane: `{stage.purpose_lane}`",
                f"- operator_action: `{stage.operator_action or _operator_action_for_axis(stage.dominant_axis)}`",
                f"- parents: `{parent_text}`",
                f"- summary: {stage.summary}",
            ])
            if stage.target_files:
                lines.append(f"- target_files: `{', '.join(stage.target_files)}`")
            if stage.ripple_effects:
                for ripple in stage.ripple_effects:
                    lines.append(f"- ripple: {ripple}")
            if stage.system_writebacks:
                for wb in stage.system_writebacks:
                    lines.append(
                        f"- writeback: `{wb.subsystem}.{wb.key}` <- `{wb.mode}` `{wb.value}`"
                    )
            if stage.notes:
                lines.append(f"- notes: {stage.notes}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _register_seed_stage(
        self,
        logger: ConstraintGenealogyLogger,
        path: CompiledLineagePath,
        stage: LineageStage,
    ) -> str:
        seed_token = hashlib.sha1(f"{path.path_id}:{stage.stage_id}".encode()).hexdigest()[:8]
        ability_id = f"{stage.dominant_axis}:LINEAGE_{stage.stage_id.upper()}_{seed_token}"
        if ability_id in logger.abilities:
            return ability_id

        base = 0.0018 + (0.0002 * max(1, stage.generation))
        cost = {axis: 0.35 * base for axis in AXES}
        for axis in stage.constraints:
            cost[axis] = cost.get(axis, 0.0) + (0.30 * base)
        cost[stage.dominant_axis] = cost.get(stage.dominant_axis, 0.0) + (0.55 * base)

        risk = {axis: 0.0 for axis in AXES}
        risk["X"] = 0.015 if (stage.dominant_axis == "X" or "X" in stage.constraints) else 0.006
        if stage.dominant_axis != "X":
            risk[stage.dominant_axis] = 0.012

        tags = [
            "synthetic_lineage",
            "lineage_compiler",
            "artificial_seed:true",
            f"seed_lineage_id:{path.path_id}",
            f"artificial_seed_influence:{_clamp(0.78 + (0.03 * stage.generation), 0.0, 0.95):.3f}",
            f"steering_target_generation:{int(stage.generation)}",
            f"lineage_target:{path.target_ability}",
            f"lineage_stage:{stage.stage_id}",
            f"stage_kind:{stage.kind}",
            f"compiler_purpose_lane:{stage.purpose_lane}",
            f"compiler_operator_action:{stage.operator_action or _operator_action_for_axis(stage.dominant_axis)}",
        ]
        for ripple in stage.ripple_effects[:4]:
            tags.append(f"ripple:{_slug(ripple)[:48]}")

        profile = AbilityProfile(
            id=ability_id,
            axis=stage.dominant_axis,
            requires=tuple(stage.constraints),
            cost=cost,
            risk=risk,
            effect_tags=tuple(tags),
            notes=(
                f"Synthetic lineage seed for target={path.target_ability}; stage={stage.stage_id}; "
                f"summary={stage.summary}; purpose_lane={stage.purpose_lane}; "
                f"operator_action={stage.operator_action or _operator_action_for_axis(stage.dominant_axis)}; "
                f"artificial_seed=true"
            ),
        )
        logger.abilities[ability_id] = _augment_ability_profile_with_origin(profile)
        return ability_id

    def _attempt_budget_for_stage(self, stage: LineageStage, base_attempts: int) -> int:
        """
        Directed recapitulation should spend more replay exposure on later,
        higher-complexity couplings. This is staged developmental runway, not
        blind retrying.
        """
        base = max(4, int(base_attempts))
        if stage.kind != "coupling":
            return base
        generation_budget = max(0, int(stage.generation) - 2) * 20
        constraint_budget = len(stage.constraints) * 6
        return base + generation_budget + constraint_budget

    def _materialize_coupling_stage(
        self,
        logger: ConstraintGenealogyLogger,
        path: CompiledLineagePath,
        stage: LineageStage,
        parent_items: List[Dict[str, str]],
        *,
        max_attempts: int,
    ) -> Tuple[str, int]:
        if len(parent_items) != 2:
            raise ValueError(f"stage {stage.stage_id} requires exactly 2 parents for materialization")

        parent_ids = [str(item["id"]) for item in parent_items]
        parent_kinds = [str(item["kind"]) for item in parent_items]
        trace = [
            TraceItem(
                kind=kind,
                id=item_id,
                env=EnvironmentVector(
                    module="ability_lineage_compiler",
                    stream_type="synthetic_lineage",
                    axis_context=stage.dominant_axis,
                    call_tag=stage.stage_id,
                ),
            )
            for kind, item_id in zip(parent_kinds, parent_ids)
        ]
        pressure_before, pressure_after = self._pressure_for_stage(stage)
        expected_parent_set = set(parent_ids)

        for attempt in range(1, max(1, int(max_attempts)) + 1):
            logger.observe(
                pressure_before=pressure_before,
                trace=trace,
                pressure_after=pressure_after,
                notes={
                    "artificial_seed": True,
                    "bypass_natural": True,
                    "seed_lineage_id": path.path_id,
                    "target_generation": int(stage.generation),
                    "target_purpose_lane": stage.purpose_lane,
                    "target_operator_action": stage.operator_action or _operator_action_for_axis(stage.dominant_axis),
                    "artificial_seed_weight": _clamp(0.82 + (0.02 * stage.generation), 0.0, 0.96),
                    "lineage_stage_id": stage.stage_id,
                    "lineage_target": path.target_ability,
                    "lineage_summary": stage.summary,
                },
            )
            link_id = self._find_link_for_parents(logger, expected_parent_set)
            if link_id:
                return link_id, attempt

        raise RuntimeError(
            f"failed to promote coupling stage {stage.stage_id} after {max_attempts} attempts"
        )

    def _find_link_for_parents(
        self,
        logger: ConstraintGenealogyLogger,
        expected_parent_set: Iterable[str],
    ) -> str:
        expected = set(str(x) for x in expected_parent_set)
        for link_id, link in logger.links.items():
            parents = set(str(p) for p in getattr(link, "parents", []) or [])
            if parents == expected:
                return str(link_id)
        return ""

    def _pressure_for_stage(self, stage: LineageStage) -> Tuple[PressureVec, PressureVec]:
        before = {axis: 0.12 for axis in AXES}
        after = dict(before)
        for axis in stage.constraints:
            before[axis] = 0.18
            after[axis] = 0.14
        before[stage.dominant_axis] = 0.26
        after[stage.dominant_axis] = 0.16
        if "X" in stage.constraints or stage.dominant_axis == "X":
            before["X"] = max(before["X"], 0.20)
            after["X"] = max(0.12, min(after["X"], 0.16))
        return PressureVec(**before), PressureVec(**after)

    def _initial_shadow_state(self, path: CompiledLineagePath) -> Dict[str, Any]:
        return {
            "path_id": path.path_id,
            "target_ability": path.target_ability,
            "working_memory": {
                "claim_atoms": 0,
                "temporal_bindings": 0,
                "speaker_boundaries": 0,
                "weighted_claims": 0,
                "repair_policies": 0,
                "active_propositions": 0,
                "speaker_owned_claims": 0,
                "repairable_branches": 0,
                "source_weighting_enabled": False,
                "belief_branches": 0,
                "causal_paths": 0,
            },
            "memory": {
                "source_scoped_claims": 0,
                "weighted_recall_paths": 0,
                "provenance_edges": 0,
            },
            "oets": {
                "proposition_nodes": 0,
                "causal_edges": 0,
            },
            "gap_system": {
                "branch_repair_enabled": False,
                "referent_repair_depth": 0,
                "active_branches": 0,
            },
            "expression": {
                "meaning_anchor_depth": 0,
                "uncertainty_channel": 0.0,
                "proposition_voice_enabled": False,
            },
            "pipeline": {
                "active_schemas": [],
                "proposition_threads": 0,
                "weighted_claim_lookup": False,
                "proposition_graph_enabled": False,
                "belief_revision_enabled": False,
                "causal_mesh_enabled": False,
                "proposition_understanding": False,
            },
            "rubric": {
                "target_dimensions": [],
            },
            "genealogy": {
                "proposition_lineages": 0,
                "revision_paths": 0,
                "materialized_outputs": [],
            },
        }

    def _apply_stage_writebacks(
        self,
        shadow_state: Dict[str, Any],
        stage: LineageStage,
        *,
        output_id: str,
        output_kind: str,
        ripple_log: List[Dict[str, Any]],
    ) -> None:
        shadow_state.setdefault("genealogy", {}).setdefault("materialized_outputs", []).append({
            "stage_id": stage.stage_id,
            "output_kind": output_kind,
            "output_id": output_id,
        })

        applied: List[Dict[str, Any]] = []
        for wb in stage.system_writebacks:
            bucket = shadow_state.setdefault(wb.subsystem, {})
            current = bucket.get(wb.key)
            if wb.mode == "increment":
                bucket[wb.key] = int(current or 0) + int(wb.value)
            elif wb.mode == "set":
                bucket[wb.key] = wb.value
            elif wb.mode == "max":
                bucket[wb.key] = max(float(current or 0.0), float(wb.value))
            elif wb.mode == "append_unique":
                values = list(current or [])
                if wb.value not in values:
                    values.append(wb.value)
                bucket[wb.key] = values
            else:
                raise ValueError(f"unsupported writeback mode: {wb.mode}")
            applied.append(wb.to_dict())

        ripple_log.append({
            "stage_id": stage.stage_id,
            "generation": int(stage.generation),
            "output_kind": output_kind,
            "output_id": output_id,
            "summary": stage.summary,
            "applied_writebacks": applied,
            "state_snapshot": json.loads(json.dumps(shadow_state)),
        })

    def _build_activation_manifest(
        self,
        *,
        path: CompiledLineagePath,
        result: MaterializationResult,
        shadow_state: Dict[str, Any],
        ripple_log: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        working_memory = dict(shadow_state.get("working_memory", {}) or {})
        memory = dict(shadow_state.get("memory", {}) or {})
        oets = dict(shadow_state.get("oets", {}) or {})
        gap_system = dict(shadow_state.get("gap_system", {}) or {})
        expression = dict(shadow_state.get("expression", {}) or {})
        pipeline = dict(shadow_state.get("pipeline", {}) or {})
        rubric = dict(shadow_state.get("rubric", {}) or {})
        genealogy = dict(shadow_state.get("genealogy", {}) or {})
        stage_index = {stage.stage_id: stage for stage in path.stages}

        graph_relations = [
            "continuation",
            "support",
            "contradiction",
            "revision",
            "causal",
            "provenance",
        ]
        graph_span = (
            int(oets.get("proposition_nodes", 0) or 0)
            + int(memory.get("provenance_edges", 0) or 0)
            + int(oets.get("causal_edges", 0) or 0)
            + int(genealogy.get("revision_paths", 0) or 0)
        )
        working_memory_schema = {
            "enable_proposition_substrate": bool(
                pipeline.get("proposition_understanding", False)
                or pipeline.get("proposition_graph_enabled", False)
            ),
            "max_nodes": max(192, 64 * max(1, int(oets.get("proposition_nodes", 0) or 0))),
            "max_edges": max(384, 96 * max(1, int(graph_span))),
            "active_window": 32,
            "graph_relations": list(graph_relations),
            "source_confidence": {
                "user": 0.74,
                "aurora": 0.66,
                "memory": 0.70,
                "external": 0.84,
            },
            "belief_revision_enabled": bool(pipeline.get("belief_revision_enabled", False)),
            "causal_mesh_enabled": bool(pipeline.get("causal_mesh_enabled", False)),
            "provenance_enabled": bool(working_memory.get("source_weighting_enabled", False)),
            "weighted_lookup_enabled": bool(pipeline.get("weighted_claim_lookup", False)),
            "target_dimensions": list(rubric.get("target_dimensions", []) or []),
        }

        stage_outputs: List[Dict[str, Any]] = []
        for materialized_stage in result.materialized_stages:
            stage = stage_index.get(materialized_stage.stage_id)
            record = materialized_stage.to_dict()
            if stage is not None:
                record["dominant_axis"] = stage.dominant_axis
                record["constraints"] = list(stage.constraints)
                record["summary"] = stage.summary
                record["purpose_lane"] = stage.purpose_lane
                record["operator_action"] = stage.operator_action or _operator_action_for_axis(stage.dominant_axis)
            stage_outputs.append(record)

        runtime_patch_plan = [
            {
                "step_id": f"{path.target_ability}.systems.merge_state",
                "target": "systems",
                "action": "merge_state",
                "payload": {
                    "lineage_runtime_state": shadow_state,
                    "lineage_runtime_targets": [path.target_ability],
                    "lineage_runtime_outputs": list(genealogy.get("materialized_outputs", []) or []),
                },
            },
            {
                "step_id": f"{path.target_ability}.working_memory.activation",
                "target": "working_memory",
                "action": "apply_lineage_activation",
                "payload": {
                    "working_memory_schema": working_memory_schema,
                    "lineage_output_id": result.final_output_id,
                },
            },
            {
                "step_id": f"{path.target_ability}.gap_system.flags",
                "target": "comprehension_gap_system",
                "action": "set_attrs",
                "payload": {
                    "branch_repair_enabled": bool(gap_system.get("branch_repair_enabled", False)),
                    "referent_repair_depth": int(gap_system.get("referent_repair_depth", 0) or 0),
                    "lineage_activation_target": path.target_ability,
                },
            },
            {
                "step_id": f"{path.target_ability}.language.flags",
                "target": "language_orchestra",
                "action": "set_attrs",
                "payload": {
                    "proposition_voice_enabled": bool(expression.get("proposition_voice_enabled", False)),
                    "uncertainty_channel_floor": float(expression.get("uncertainty_channel", 0.0) or 0.0),
                    "lineage_target_dimensions": list(rubric.get("target_dimensions", []) or []),
                },
            },
            {
                "step_id": f"{path.target_ability}.perception.flags",
                "target": "perception",
                "action": "set_attrs",
                "payload": {
                    "proposition_understanding_enabled": bool(pipeline.get("proposition_understanding", False)),
                    "causal_mesh_enabled": bool(pipeline.get("causal_mesh_enabled", False)),
                },
            },
            {
                "step_id": f"{path.target_ability}.oets.flags",
                "target": "perception.oets",
                "action": "set_attrs",
                "payload": {
                    "proposition_understanding_enabled": bool(pipeline.get("proposition_understanding", False)),
                    "proposition_graph_enabled": bool(pipeline.get("proposition_graph_enabled", False)),
                    "belief_revision_enabled": bool(pipeline.get("belief_revision_enabled", False)),
                    "causal_mesh_enabled": bool(pipeline.get("causal_mesh_enabled", False)),
                    "proposition_nodes_expected": int(oets.get("proposition_nodes", 0) or 0),
                    "causal_edges_expected": int(oets.get("causal_edges", 0) or 0),
                },
            },
            {
                "step_id": f"{path.target_ability}.genealogy.state",
                "target": "genealogy",
                "action": "merge_state",
                "payload": {
                    "lineage_runtime_outputs": list(genealogy.get("materialized_outputs", []) or []),
                    "lineage_runtime_targets": [path.target_ability],
                    "lineage_runtime_final_output": result.final_output_id,
                },
            },
        ]

        return {
            "manifest_version": 1,
            "created_at": float(time.time()),
            "target_ability": path.target_ability,
            "path_id": path.path_id,
            "final_output_id": result.final_output_id,
            "final_output_kind": result.final_output_kind,
            "run_dir": result.run_dir,
            "shadow_state": shadow_state,
            "stage_outputs": stage_outputs,
            "runtime_contract": {
                "working_memory_schema": working_memory_schema,
                "pipeline_flags": pipeline,
                "rubric_targets": list(rubric.get("target_dimensions", []) or []),
                "graph_relations": graph_relations,
            },
            "runtime_patch_plan": runtime_patch_plan,
            "ripple_log_excerpt": list(ripple_log[-6:]),
        }

    def _render_activation_markdown(self, activation_manifest: Dict[str, Any]) -> str:
        runtime_contract = dict(activation_manifest.get("runtime_contract", {}) or {})
        working_memory_schema = dict(runtime_contract.get("working_memory_schema", {}) or {})
        lines = [
            f"# Selected Runtime Activation: {activation_manifest.get('target_ability', '')}",
            "",
            f"- `path_id`: `{activation_manifest.get('path_id', '')}`",
            f"- `final_output_id`: `{activation_manifest.get('final_output_id', '')}`",
            f"- `run_dir`: `{activation_manifest.get('run_dir', '')}`",
            f"- `proposition_substrate`: `{bool(working_memory_schema.get('enable_proposition_substrate', False))}`",
            f"- `max_nodes`: `{int(working_memory_schema.get('max_nodes', 0) or 0)}`",
            f"- `max_edges`: `{int(working_memory_schema.get('max_edges', 0) or 0)}`",
            "",
            "## Runtime Patch Plan",
            "",
        ]
        for step in list(activation_manifest.get("runtime_patch_plan", []) or []):
            lines.append(f"- `{step.get('step_id', '')}` -> `{step.get('target', '')}` / `{step.get('action', '')}`")
        lines.append("")
        return "\n".join(lines)

    def _write_activation_artifacts(
        self,
        *,
        path: CompiledLineagePath,
        activation_manifest: Dict[str, Any],
    ) -> Dict[str, str]:
        target_dir = os.path.join(self.storage_dir, path.target_ability)
        runs_dir = os.path.join(target_dir, "runs")
        os.makedirs(runs_dir, exist_ok=True)
        selected_json = os.path.join(target_dir, "selected_activation.json")
        selected_md = os.path.join(target_dir, "selected_activation.md")
        version_json = os.path.join(runs_dir, f"{_slug(path.path_id)}_activation.json")
        version_md = os.path.join(runs_dir, f"{_slug(path.path_id)}_activation.md")

        for out_path in (selected_json, version_json):
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(activation_manifest, fh, indent=2)

        md_text = self._render_activation_markdown(activation_manifest)
        for out_path in (selected_md, version_md):
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(md_text)

        return {
            "selected_json": selected_json,
            "selected_md": selected_md,
            "version_json": version_json,
            "version_md": version_md,
        }


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Compile and materialize constraint-native ability lineages.")
    parser.add_argument("--target", default="proposition_understanding", help="Target ability phenotype.")
    parser.add_argument("--storage-dir", default="aurora_state/ability_lineages", help="Where lineage artifacts are written.")
    parser.add_argument("--skip-materialize", action="store_true", help="Only write the lineage path, do not replay it.")
    parser.add_argument("--k-min", type=int, default=4, help="Promotion threshold for the dedicated replay run.")
    parser.add_argument("--max-attempts", type=int, default=24, help="Maximum observe() replays per coupling stage.")
    args = parser.parse_args()

    compiler = AbilityLineageCompiler(storage_dir=args.storage_dir)
    path = compiler.compile_target(args.target)
    written = compiler.autowrite_selected_path(path)
    out: Dict[str, Any] = {
        "compiled_path": path.to_dict(),
        "written_files": written,
    }

    if not args.skip_materialize:
        materialized = compiler.materialize_path(
            path,
            k_min=args.k_min,
            max_attempts_per_stage=args.max_attempts,
        )
        out["materialization"] = materialized.to_dict()

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
