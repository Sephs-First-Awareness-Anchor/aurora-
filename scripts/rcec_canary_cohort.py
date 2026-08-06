#!/usr/bin/env python3
"""
scripts/rcec_canary_cohort.py

Build 608: RCEC Closed-Loop Activation and Admissibility Repair.
The first real experiment after the four repairs (A-D): one canary
developmental cohort.

Rule family: direct_trigger only.
6 varied training episodes (DEFAULT_SKIN).
3 ALT_SKIN validation episodes.
No permanent state promotion: runs against an isolated shadow copy of
aurora_state/ (never the real one), and never calls promote_shadow_deltas().

Reuses ONE boot across the whole cohort (Build 608, D3) rather than
booting Aurora repeatedly, and calls shutdown_aurora() when done.

Measures: initial prediction accuracy, revised prediction accuracy,
counterfactual accuracy, transfer accuracy, confidence calibration,
internal-to-expression fidelity.
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
    HiddenRuleEngine,
    WorldGenerator,
    run_developmental_cohort,
)

STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")


def _build_spec(seed: int, episode_id: str, validation: bool, skin=None) -> dict:
    rng = random.Random(seed)
    world = WorldGenerator().build_world(
        seed=seed,
        num_entities=rng.choice([2, 3, 4]),
        entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False,
    )
    engine = HiddenRuleEngine.generate(world, rng=random.Random(seed + 1), family="direct_trigger")
    spec = {"world": world, "engine": engine, "episode_id": episode_id, "validation": validation}
    if skin is not None:
        spec["skin"] = skin
    return spec


def main() -> dict:
    scratch_root = tempfile.mkdtemp(prefix="aurora_rcec_canary_")
    scratch_state_dir = os.path.join(scratch_root, "aurora_state")
    try:
        shutil.copytree(STATE_DIR, scratch_state_dir)
        print("[boot] starting (profile=surface)...", flush=True)
        t_boot = time.time()
        systems = A.boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        print(f"[boot] done ({time.time() - t_boot:.1f}s)", flush=True)

        training_seeds = [101, 202, 303, 404, 505, 606]
        validation_seeds = [707, 808, 909]

        specs = [
            _build_spec(seed, f"canary_train_{i}", validation=False)
            for i, seed in enumerate(training_seeds)
        ]
        specs += [
            _build_spec(seed, f"canary_val_{i}", validation=True, skin=ALT_SKIN)
            for i, seed in enumerate(validation_seeds)
        ]

        print(f"[cohort] running {len(specs)} episodes (6 training + 3 ALT_SKIN validation)...", flush=True)
        t_cohort = time.time()
        cohort_result = run_developmental_cohort(systems, specs)
        print(f"[cohort] done ({time.time() - t_cohort:.1f}s)", flush=True)

        report = _summarize(cohort_result)
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


def _summarize(cohort_result) -> dict:
    per_episode = []
    initial_accuracy, revised_accuracy, counterfactual_accuracy = [], [], []
    transfer_scores, confidence_calibration, expression_fidelity_scores = [], [], []

    for result in cohort_result.episode_results:
        cr = result.causal_result
        per_episode.append({
            "episode_id": result.promotion_decision.episode_id,
            "route": result.promotion_decision.route,
            "promoted": result.promotion_decision.promoted,
            "reason": result.promotion_decision.reason,
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
        "total_episodes": cohort_result.summary["total_episodes"],
        "promoted_count": cohort_result.summary["promoted"],
        "routes": cohort_result.summary["routes"],
        "mean_initial_prediction_accuracy": _mean(initial_accuracy),
        "mean_revised_prediction_accuracy_delta": _mean(revised_accuracy),
        "mean_counterfactual_accuracy": _mean(counterfactual_accuracy),
        "mean_transfer_accuracy": _mean(transfer_scores),
        "mean_confidence_calibration": _mean(confidence_calibration),
        "mean_expression_fidelity": _mean(expression_fidelity_scores),
        "per_episode": per_episode,
    }


if __name__ == "__main__":
    main()
