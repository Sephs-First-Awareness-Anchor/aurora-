from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
from aurora_warp_protocol import WarpField


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_MODULE = (
    ROOT / "flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py"
)


def _field(
    state_dir: Path, *, persist: bool = True, genealogy=None
) -> AuroraCommunicationEmergence:
    field = AuroraCommunicationEmergence(
        state_dir=str(state_dir), persist=persist, genealogy=genealogy
    )
    warp = WarpField()
    warp.register_warp_capable("communication_emergence", field)
    field.attach_systems({"warp_field": warp, "genealogy": genealogy})
    return field


_PAIRS = (
    ("What does standard voice mean?", "Standard voice means the regular audio mode."),
    ("What does bounded mode mean?", "Bounded mode means operation within a defined limit."),
    ("What does active state mean?", "Active state means the process is currently operating."),
    ("What does stable path mean?", "Stable path means a route that keeps its relation over time."),
)


class BaselineCommunicationApprenticeshipTests(unittest.TestCase):
    def test_possibility_evidence_seeds_trial_without_becoming_truth_or_validation(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            results = []
            for index, (user, observed) in enumerate(_PAIRS):
                results.append(field.observe_structural_possibility(
                    raw_text=user,
                    observed_response_text=observed,
                    possibility_id=f"pair:{index}",
                    observed_source="historical_other_assistant",
                    epistemic_status="observation_not_truth",
                    causal_status="sequence_observed_causality_not_asserted",
                ))

            self.assertTrue(all(item.get("admitted") for item in results))
            self.assertEqual(field.status()["trial_operations"], 1)
            self.assertEqual(field.status()["promoted_operations"], 0)
            self.assertEqual(field.status()["pending_receiver_validation"], 0)
            self.assertEqual(field.status()["environmental_possibilities_seen"], 4)
            self.assertTrue(results[-1]["candidate_available"])
            self.assertFalse(results[-1]["receiver_validation_eligible"])

            persisted = json.loads(Path(field.storage_path).read_text(encoding="utf-8"))
            encoded = json.dumps(persisted)
            self.assertNotIn(_PAIRS[0][1], encoded)
            observation = persisted["observations"][-1]
            self.assertEqual(observation["observation_context"], "environmental_counterfactual")
            self.assertFalse(observation["receiver_validation_eligible"])
            self.assertFalse(observation["possibility_evidence"]["truth_assumed"])
            self.assertFalse(
                observation["possibility_evidence"]["receiver_validation_assumed"]
            )

    def test_trial_and_warp_lifecycle_survive_restart_and_remain_operational(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td)
            field = _field(state_dir)
            for index, (user, observed) in enumerate(_PAIRS[:3]):
                field.observe_structural_possibility(
                    raw_text=user,
                    observed_response_text=observed,
                    possibility_id=f"restart:{index}",
                )
            component_id = field.active_operations()[0]["component_id"]

            restored = _field(state_dir)
            self.assertIn(component_id, restored._warp_trials)
            self.assertEqual(restored.status()["trial_operations"], 1)
            result = restored.observe_structural_possibility(
                raw_text=_PAIRS[3][0],
                observed_response_text=_PAIRS[3][1],
                possibility_id="restart:3",
            )
            self.assertTrue(result["candidate_available"])
            self.assertEqual(result["trial_component_id"], component_id)
            self.assertEqual(result["candidate_alignment"]["score"], 1.0)

    def test_trial_retains_explicit_genealogy_parentage(self):
        class Genealogy:
            def __init__(self):
                self.links = {}
                self.abilities = {
                    "B:PRIOR_BOUNDARY_RELIEF": SimpleNamespace(
                        axis="B",
                        requires=("X", "T", "B"),
                        effect_tags=("relation_preservation",),
                    )
                }

            def pressure_orientation(self):
                return {"X": 0.18, "T": 0.20, "N": 0.12, "B": 0.35, "A": 0.15}

        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td), genealogy=Genealogy())
            for index, (user, observed) in enumerate(_PAIRS[:3]):
                field.observe_structural_possibility(
                    raw_text=user,
                    observed_response_text=observed,
                    possibility_id=f"genealogy:{index}",
                )
            operation = field.active_operations()[0]
            self.assertIn("B:PRIOR_BOUNDARY_RELIEF", operation["parent_ids"])
            self.assertTrue(operation["canonical_signature"])

    def test_historical_environment_pairs_once_and_never_claims_causality(self):
        spec = importlib.util.spec_from_file_location(
            "historical_environment_apprenticeship_test", HISTORICAL_MODULE
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        class Probe:
            def __init__(self):
                self.calls = []

            def observe_structural_possibility(self, **kwargs):
                self.calls.append(dict(kwargs))
                return {
                    "admitted": True,
                    "structural_support": True,
                    "representable_gap": True,
                    "possibility_id": kwargs["possibility_id"],
                    "trial_component_id": "warp-test",
                    "candidate_available": False,
                }

        with tempfile.TemporaryDirectory() as td:
            probe = Probe()
            env = module.HistoricalExperienceEnvironment(
                {"communication_emergence": probe},
                state_dir=td,
                archive_path=str(Path(td) / "unused.zip"),
                initial_delay_s=0.0,
            )
            env._baseline_id = "baseline"
            env._state = {"communication_apprenticeship": {}}
            user = {
                "event_id": "u1",
                "episode_id": "ep1",
                "actor": "user",
                "text": "What does the boundary mean?",
                "epistemic_status": "observation_not_truth",
                "causal_status": "sequence_observed_causality_not_asserted",
            }
            other = {
                "event_id": "a1",
                "episode_id": "ep1",
                "actor": "assistant",
                "text": "It describes the current limit.",
                "epistemic_status": "observation_not_truth",
                "causal_status": "sequence_observed_causality_not_asserted",
            }
            self.assertEqual(
                env._observe_communication_possibility(user)["status"],
                "awaiting_structural_possibility",
            )
            admitted = env._observe_communication_possibility(other)
            self.assertEqual(admitted["status"], "possibility_admitted")
            self.assertEqual(len(probe.calls), 1)
            call = probe.calls[0]
            self.assertEqual(call["observed_source"], "historical_other_assistant")
            self.assertEqual(call["epistemic_status"], "observation_not_truth")
            self.assertEqual(
                call["causal_status"], "sequence_observed_causality_not_asserted"
            )
            self.assertTrue(call["defer_persistence"])
            self.assertEqual(
                env._observe_communication_possibility(other)["status"],
                "no_exchange_pair",
            )
            self.assertEqual(len(probe.calls), 1)


if __name__ == "__main__":
    unittest.main()
