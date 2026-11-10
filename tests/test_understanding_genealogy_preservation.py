"""The optimized understanding path must still retain its full genealogy.

Every observation-validation and response-application projection is its own
causal event with its own distinct before/after pressure, trace and state
signatures. They must not be conflated merely to reduce computation.
"""
from __future__ import annotations

import copy

from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract


class RecordingGenealogy:
    def __init__(self):
        self.abilities = {}
        self.events = []
        self._last_observe_profile = {}

    def observe(self, **kwargs):
        self.events.append(kwargs)
        self._last_observe_profile = {
            "tick": len(self.events), "lock_wait_ms": 0.0, "compute_ms": 0.0,
        }
        return None


def test_observation_and_application_projection_keep_distinct_evidence(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    genealogy = RecordingGenealogy()
    systems = {"genealogy": genealogy}

    before = copy.deepcopy(contract.state)
    observed = copy.deepcopy(before)
    observed["X"]["score"] = 0.74
    applied = copy.deepcopy(observed)
    applied["N"]["total"] = 0.18

    contract._record_genealogy_event(
        systems, phase="observation_validation", before_state=before,
        after_state=observed, notes={"source": "heard", "time_index": 1},
    )
    contract._record_genealogy_event(
        systems, phase="application_projection", before_state=observed,
        after_state=applied, notes={"source": "answered", "time_index": 2},
    )
    assert len(genealogy.events) == 2
    first, second = genealogy.events
    assert first["notes"]["source"] == "heard"
    assert second["notes"]["source"] == "answered"
    assert first["state_sig_before"] != first["state_sig_after"]
    assert second["state_sig_before"] != second["state_sig_after"]
    assert first["state_sig_after"] != second["state_sig_before"], (
        "Phase remains part of event identity even when the physical state is shared"
    )
    assert first["pressure_after"].X != first["pressure_before"].X
    assert second["pressure_after"].N != second["pressure_before"].N
    assert first["trace"] and second["trace"]
    assert [t.id for t in first["trace"]] == [t.id for t in second["trace"]]
    assert all(t.kind == "ABILITY" for t in first["trace"])
    assert len(genealogy.abilities) >= len(first["trace"])
