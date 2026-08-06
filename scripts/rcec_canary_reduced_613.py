#!/usr/bin/env python3
"""
scripts/rcec_canary_reduced_613.py

Build 613: Experiential Delivery and Predictive Projection Directive.
The corrected next canary -- deliberately NOT another eight-assessment
cohort. Instead:

  2 demonstrated positive transitions
  2 control transitions
  (inspect whether Aurora internally retains any contrast between them)
  then ONE assessment episode, capturing:
    - whether prior transitions were retrieved
    - whether a FutureStateProjection was formed, and its populated fields
    - whether expression preserved it
    - whether the final action commitment was genuine

One fixed mechanism throughout (Build 610, G), no decoy (Build 613, J),
genuinely experiential acquisition (Build 613, I), role-normalized
evidence (Build 613, K). No permanent state promotion.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
import json
import os
import random
import shutil
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInvocation,
    HiddenRuleEngine,
    ObservationBoundary,
    WorldGenerator,
    build_episode_runtime_context,
    compute_state_delta,
    generate_mechanism,
    run_acquisition_episode,
    run_closed_loop_episode,
)

STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")
MECHANISM_SEED = 613613


def _build_world_and_engine(mechanism, seed: int):
    rng = random.Random(seed)
    world = WorldGenerator().build_world(
        seed=seed,
        num_entities=rng.choice([3, 4]),
        entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False,
        required_types=(mechanism.source_entity_type, mechanism.target_entity_type),
    )
    engine = HiddenRuleEngine.generate_from_mechanism(world, mechanism, rng=random.Random(seed + 1))
    return world, engine


def _control_action_type(mechanism, source_properties) -> str:
    for candidate in ("seal", "unseal", "add_energy", "remove_energy"):
        if candidate == mechanism.trigger_action:
            continue
        required = {"seal": "sealed", "unseal": "sealed", "add_energy": "energy", "remove_energy": "energy"}[candidate]
        if required in source_properties:
            return candidate
    return "wait"


def _interpretation_summary(interp) -> dict:
    if interp is None:
        return None
    return {
        "raw_expression": interp.raw_expression,
        "action_commitment": interp.action_commitment,
        "predicted_consequence": interp.predicted_consequence,
        "confidence": interp.confidence,
        "stated_unknowns": list(interp.stated_unknowns),
    }


def main() -> dict:
    scratch_root = tempfile.mkdtemp(prefix="aurora_rcec_reduced_613_")
    scratch_state_dir = os.path.join(scratch_root, "aurora_state")
    report = {"acquisition": [], "assessment": None}
    try:
        shutil.copytree(STATE_DIR, scratch_state_dir)

        mechanism = generate_mechanism(random.Random(MECHANISM_SEED), family="direct_trigger")
        report["mechanism"] = {
            "trigger_action": mechanism.trigger_action,
            "source_entity_type": mechanism.source_entity_type,
            "target_entity_type": mechanism.target_entity_type,
            "target_property": mechanism.target_property,
            "effect_delta": mechanism.effect_delta,
            "decoy_entity_type": mechanism.decoy_entity_type,  # None -- Build 613 (J)
        }
        print(f"[mechanism] {mechanism.trigger_action} on a {mechanism.source_entity_type} "
              f"-> {mechanism.target_entity_type}.{mechanism.target_property} "
              f"(effect={mechanism.effect_delta!r}, decoy={mechanism.decoy_entity_type!r})", flush=True)

        print("[boot] starting (profile=surface)...", flush=True)
        t_boot = time.time()
        systems = A.boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print(f"[boot] done ({time.time() - t_boot:.1f}s)", flush=True)
        ctx = build_episode_runtime_context(systems)

        # 2 demonstrated + 2 control -- Build 613 (I): genuinely experiential.
        acquisition_specs = []
        for i, seed in enumerate((1001, 1002)):
            world, engine = _build_world_and_engine(mechanism, seed)
            rule = engine._rule  # noqa: SLF001 -- harness code, established precedent
            acquisition_specs.append((f"acq_demo_{i}", "demonstrated", world, engine,
                                       ActionInvocation(rule.trigger_action, (rule.source_entity_id,))))
        for i, seed in enumerate((1003, 1004)):
            world, engine = _build_world_and_engine(mechanism, seed)
            rule = engine._rule  # noqa: SLF001
            control_type = _control_action_type(mechanism, world.entities[rule.source_entity_id].properties)
            control_targets = (rule.source_entity_id,) if control_type != "wait" else ()
            acquisition_specs.append((f"acq_ctrl_{i}", "control", world, engine,
                                       ActionInvocation(control_type, control_targets)))

        for episode_id, trial_kind, world, engine, scripted_action in acquisition_specs:
            print(f"[acquisition] running {episode_id} ({trial_kind})...", flush=True)
            result = run_acquisition_episode(
                systems, ctx, world, engine, ObservationBoundary(), "agent_a",
                episode_id=episode_id, trial_kind=trial_kind, scripted_action=scripted_action,
            )
            step = result.trace.steps[0]
            report["acquisition"].append({
                "episode_id": episode_id,
                "trial_kind": trial_kind,
                "scripted_action": {"action_type": scripted_action.action_type, "target_ids": list(scripted_action.target_ids)},
                "state_delta": compute_state_delta(step.world_before, step.consequence),
                "witnessed_interpretation": _interpretation_summary(result.witnessed_interpretation),
                "ingested": result.ingestion_decision.ingested,
                "ingestion_reason": result.ingestion_decision.reason,
            })

        # ONE assessment episode -- capture retrieval, projection, expression, commitment.
        world, engine = _build_world_and_engine(mechanism, 2001)
        print("[assessment] running asmt_0...", flush=True)
        result = run_closed_loop_episode(
            systems, ctx, world, engine, ObservationBoundary(), "agent_a",
            episode_id="asmt_0", mechanism=mechanism,
        )
        step = result.trace.steps[0]
        projection = result.future_state_projection
        report["assessment"] = {
            "episode_id": "asmt_0",
            "initial_interpretation": _interpretation_summary(step.interpretation),
            "revised_interpretation": _interpretation_summary(result.revised_interpretation),
            "future_state_projection": {
                "formed": projection.formed,
                "proposed_action": projection.proposed_action,
                "predicted_entity": projection.predicted_entity,
                "predicted_property": projection.predicted_property,
                "predicted_direction": projection.predicted_direction,
                "confidence": projection.confidence,
                "unknowns": list(projection.unknowns),
                "diagnostic_category": projection.diagnostic_category(
                    expressed=bool(step.interpretation.raw_expression.strip()),
                ),
            },
            "expression_fidelity": result.expression_fidelity,
            "route": result.promotion_decision.route,
            "promoted": result.promotion_decision.promoted,
            "reason": result.promotion_decision.reason,
            "ingested_raw_experience": result.ingestion_decision.ingested,
            "ingestion_reason": result.ingestion_decision.reason,
            "action_commitment": step.interpretation.action_commitment,
            "governors_tripped": [g.name for g in result.governor_results if g.tripped],
            "transfer_score": result.transfer_comparison.transfer_score,
        }

        print(json.dumps(report, indent=2, default=str))
        return report
    finally:
        try:
            A.shutdown_aurora(systems)
        except NameError:
            pass
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
