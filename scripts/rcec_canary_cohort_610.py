#!/usr/bin/env python3
"""
scripts/rcec_canary_cohort_610.py

Build 610: RCEC Closed-Loop Activation and Admissibility Repair -- E-H.
The corrected first canary, replacing Build 608's (which shared one task
id across nine episodes whose actual rules contradicted each other, and
whose transfer/promotion machinery could never be exercised because every
episode's response was an honest abstain).

ONE fixed direct-trigger mechanism, shared across every trial (Build 610,
G) -- entity labels, distractors, ordering, and initial values vary per
trial; the mechanism itself (trigger action, source/target roles, target
property, effect) does not.

Acquisition (Build 610, E): creates raw experience, no prediction
required, can never reach an admissibility route.
  - 2 demonstrated trials: a scripted action that DOES trigger the
    mechanism, applied directly (not parsed from Aurora's expression).
  - 2 control trials: a scripted action that does NOT trigger the
    mechanism, applied to the same source entity -- contrast evidence.
  - 2 exploration trials: Aurora genuinely selects her own action,
    subject to Build 610 (F)'s real action-commitment check.

Assessment (Build 610, H): only these may qualify for an admissibility
route. All three sub-groups run the full run_closed_loop_episode()
sequence (prediction -> backprojection -> counterfactual -> ALT_SKIN
transfer, the transfer preserving THIS SAME mechanism) -- they differ in
which parts of that sequence the report highlights.
  - 3 prediction-before-action trials (DEFAULT_SKIN, non-validation).
  - 2 counterfactual trials (DEFAULT_SKIN, non-validation, an explicit
    counterfactual_alter chosen to probe the mechanism's target property
    from a meaningfully different starting value).
  - 3 ALT_SKIN transfer trials (skin=ALT_SKIN, validation=True -- Build
    608's established "ALT_SKIN validation episode" convention).

No permanent state promotion: runs against an isolated shadow copy of
aurora_state/ (never the real one), and never calls promote_shadow_deltas().
Reuses ONE boot across the whole cohort (Build 608, D3).
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
    ALT_SKIN,
    ActionInvocation,
    HiddenRuleEngine,
    ObservationBoundary,
    WorldGenerator,
    generate_mechanism,
    run_developmental_cohort,
)

STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")
MECHANISM_SEED = 610610  # fixed -- one mechanism for the whole cohort


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


def _build_acquisition_spec(mechanism, seed: int, episode_id: str, trial_kind: str) -> dict:
    world, engine = _build_world_and_engine(mechanism, seed)
    rule = engine._rule  # noqa: SLF001 -- experiment harness, not Aurora; established precedent elsewhere in this test suite
    spec = {
        "kind": "acquisition", "world": world, "engine": engine,
        "episode_id": episode_id, "trial_kind": trial_kind,
    }
    if trial_kind == "demonstrated":
        spec["scripted_action"] = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    elif trial_kind == "control":
        source_props = world.entities[rule.source_entity_id].properties
        control_type = _control_action_type(mechanism, source_props)
        spec["scripted_action"] = ActionInvocation(control_type, (rule.source_entity_id,) if control_type != "wait" else ())
    return spec


def _build_assessment_spec(mechanism, seed: int, episode_id: str, *, skin=None, validation=False, counterfactual_alter=None) -> dict:
    world, engine = _build_world_and_engine(mechanism, seed)
    spec = {
        "kind": "assessment", "world": world, "engine": engine,
        "episode_id": episode_id, "validation": validation, "mechanism": mechanism,
    }
    if skin is not None:
        spec["skin"] = skin
    if counterfactual_alter is not None:
        spec["counterfactual_alter"] = counterfactual_alter
    return spec


def _explicit_counterfactual_alter(mechanism, world, engine):
    rule = engine._rule  # noqa: SLF001
    current = world.entities[rule.target_entity_id].properties.get(rule.target_property)
    if isinstance(current, bool):
        new_value = not current
    elif isinstance(current, (int, float)):
        new_value = current + 5  # a more aggressive perturbation than the auto-picked default (+3)
    else:
        from aurora_internal.aurora_cognitive_experience_chamber import PROPERTIES
        spec = PROPERTIES.get(rule.target_property)
        choices = [v for v in (spec.domain or ()) if v != current]
        new_value = choices[0] if choices else current
    return {"entity_id": rule.target_entity_id, "property": rule.target_property, "value": new_value}


def main() -> dict:
    scratch_root = tempfile.mkdtemp(prefix="aurora_rcec_canary_610_")
    scratch_state_dir = os.path.join(scratch_root, "aurora_state")
    try:
        shutil.copytree(STATE_DIR, scratch_state_dir)

        mechanism = generate_mechanism(random.Random(MECHANISM_SEED), family="direct_trigger")
        print(f"[mechanism] {mechanism.trigger_action} on a {mechanism.source_entity_type} "
              f"-> {mechanism.target_entity_type}.{mechanism.target_property} "
              f"(effect={mechanism.effect_delta!r}) [id={mechanism.mechanism_id}]", flush=True)

        print("[boot] starting (profile=surface)...", flush=True)
        t_boot = time.time()
        systems = A.boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print(f"[boot] done ({time.time() - t_boot:.1f}s)", flush=True)

        specs = []
        # Acquisition: 2 demonstrated + 2 control + 2 exploration.
        specs.append(_build_acquisition_spec(mechanism, 1001, "acq_demo_0", "demonstrated"))
        specs.append(_build_acquisition_spec(mechanism, 1002, "acq_demo_1", "demonstrated"))
        specs.append(_build_acquisition_spec(mechanism, 1003, "acq_ctrl_0", "control"))
        specs.append(_build_acquisition_spec(mechanism, 1004, "acq_ctrl_1", "control"))
        specs.append(_build_acquisition_spec(mechanism, 1005, "acq_explore_0", "exploration"))
        specs.append(_build_acquisition_spec(mechanism, 1006, "acq_explore_1", "exploration"))

        # Assessment: 3 prediction-before-action + 2 counterfactual + 3 ALT_SKIN transfer.
        for i, seed in enumerate((2001, 2002, 2003)):
            specs.append(_build_assessment_spec(mechanism, seed, f"asmt_predict_{i}"))
        for i, seed in enumerate((2004, 2005)):
            world, engine = _build_world_and_engine(mechanism, seed)
            alter = _explicit_counterfactual_alter(mechanism, world, engine)
            spec = {
                "kind": "assessment", "world": world, "engine": engine,
                "episode_id": f"asmt_counterfactual_{i}", "validation": False,
                "mechanism": mechanism, "counterfactual_alter": alter,
            }
            specs.append(spec)
        for i, seed in enumerate((2006, 2007, 2008)):
            specs.append(_build_assessment_spec(mechanism, seed, f"asmt_transfer_{i}", skin=ALT_SKIN, validation=True))

        print(f"[cohort] running {len(specs)} episodes "
              f"(6 acquisition + 8 assessment)...", flush=True)
        t_cohort = time.time()
        cohort_result = run_developmental_cohort(systems, specs)
        print(f"[cohort] done ({time.time() - t_cohort:.1f}s)", flush=True)

        report = _summarize(mechanism, cohort_result)
        print(json.dumps(report, indent=2, default=str))
        return report
    finally:
        try:
            A.shutdown_aurora(systems)
        except NameError:
            pass
        shutil.rmtree(scratch_root, ignore_errors=True)


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _summarize(mechanism, cohort_result) -> dict:
    per_acquisition = [{
        "episode_id": r.trace.episode_id,
        "trial_kind": r.trial_kind,
        "action_commitment": r.trace.steps[0].interpretation.action_commitment,
        "action": {"action_type": r.trace.steps[0].action.action_type, "target_ids": list(r.trace.steps[0].action.target_ids)},
        "ingested": r.ingestion_decision.ingested,
        "ingestion_reason": r.ingestion_decision.reason,
    } for r in cohort_result.acquisition_results]

    per_assessment = []
    initial_accuracy, revised_accuracy, counterfactual_accuracy = [], [], []
    transfer_scores, confidence_calibration, expression_fidelity_scores = [], [], []

    for result in cohort_result.episode_results:
        cr = result.causal_result
        per_assessment.append({
            "episode_id": result.promotion_decision.episode_id,
            "action_commitment": result.trace.steps[0].interpretation.action_commitment,
            "route": result.promotion_decision.route,
            "promoted": result.promotion_decision.promoted,
            "reason": result.promotion_decision.reason,
            "ingested_raw_experience": result.ingestion_decision.ingested,
            "ingestion_reason": result.ingestion_decision.reason,
            "initial_prediction_accuracy": cr.prediction_accuracy,
            "revision_quality": cr.revision_quality,
            "counterfactual_consistency": cr.counterfactual_consistency,
            "confidence_calibration": cr.confidence_calibration,
            "transfer_score": result.transfer_comparison.transfer_score,
            "expression_fidelity": result.expression_fidelity,
            "governors_tripped": [g.name for g in result.governor_results if g.tripped],
        })
        if cr.prediction_accuracy is not None:
            initial_accuracy.append(cr.prediction_accuracy)
        if cr.revision_quality is not None:
            revised_accuracy.append(cr.revision_quality)
        if cr.counterfactual_consistency is not None:
            counterfactual_accuracy.append(cr.counterfactual_consistency)
        if result.transfer_comparison.transfer_score is not None:
            transfer_scores.append(result.transfer_comparison.transfer_score)
        if cr.confidence_calibration is not None:
            confidence_calibration.append(cr.confidence_calibration)
        fidelity_values = [v for v in (result.expression_fidelity or {}).values() if isinstance(v, (int, float))]
        if fidelity_values:
            expression_fidelity_scores.append(sum(fidelity_values) / len(fidelity_values))

    return {
        "mechanism": {
            "trigger_action": mechanism.trigger_action,
            "source_entity_type": mechanism.source_entity_type,
            "target_entity_type": mechanism.target_entity_type,
            "target_property": mechanism.target_property,
            "effect_delta": mechanism.effect_delta,
        },
        "total_episodes": cohort_result.summary["total_episodes"],
        "acquisition_episodes": cohort_result.summary["acquisition_episodes"],
        "assessment_episodes": cohort_result.summary["assessment_episodes"],
        "ingested_raw_experience": cohort_result.summary["ingested_raw_experience"],
        "promoted_count": cohort_result.summary["promoted"],
        "routes": cohort_result.summary["routes"],
        "mean_initial_prediction_accuracy": _mean(initial_accuracy),
        "mean_revised_prediction_accuracy_delta": _mean(revised_accuracy),
        "mean_counterfactual_accuracy": _mean(counterfactual_accuracy),
        "mean_transfer_accuracy": _mean(transfer_scores),
        "mean_confidence_calibration": _mean(confidence_calibration),
        "mean_expression_fidelity": _mean(expression_fidelity_scores),
        "per_acquisition": per_acquisition,
        "per_assessment": per_assessment,
    }


if __name__ == "__main__":
    main()
