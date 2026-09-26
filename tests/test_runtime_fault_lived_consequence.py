from aurora_internal.aurora_runtime_faults import record_runtime_fault


class FakeSediMemory:
    def __init__(self):
        self.events = []

    def ingest_event(self, **kwargs):
        self.events.append(kwargs)
        return 1


def test_runtime_fault_enters_lived_experience(tmp_path):
    sedi = FakeSediMemory()
    systems = {"state_dir": str(tmp_path), "sedimemory": sedi}

    record = record_runtime_fault(
        systems,
        subsystem="test_subsystem",
        operation="attempted_transition",
        exc=RuntimeError("transition refused"),
        severity="subsystem_degradation",
        context={"attempt_id": "a-1"},
    )

    assert record["severity"] == "subsystem_degradation"
    assert len(sedi.events) == 1
    event = sedi.events[0]
    assert event["source"] == "internal_runtime"
    assert event["content"]["occurrence_type"] == "runtime_fault"
    assert event["content"]["operation"] == "attempted_transition"
    assert event["content"]["message"] == "transition refused"
    assert event["content"]["context"]["attempt_id"] == "a-1"
    assert systems["_last_lived_runtime_fault"]["traceback_hash"] == record["traceback_hash"]


def test_fault_experience_failure_does_not_recurse_or_hide_original_fault(tmp_path):
    class BrokenSediMemory:
        def ingest_event(self, **kwargs):
            raise RuntimeError("memory unavailable")

    systems = {"state_dir": str(tmp_path), "sedimemory": BrokenSediMemory()}
    record = record_runtime_fault(
        systems,
        subsystem="test_subsystem",
        operation="original_failure",
        exc=ValueError("original"),
        severity="invariant_violation",
    )

    assert record["message"] == "original"
    assert systems["_runtime_unready"] is True
    assert len(systems["_runtime_faults"]) == 1
    assert "_runtime_fault_experience_guard" not in systems


def test_fault_without_live_sedimemory_remains_operationally_recorded(tmp_path):
    systems = {"state_dir": str(tmp_path)}
    record = record_runtime_fault(
        systems,
        subsystem="early_boot",
        operation="before_sedimemory",
        exc=RuntimeError("not yet connected"),
    )

    assert record
    assert systems["_last_runtime_fault"]["operation"] == "before_sedimemory"
    assert "_last_lived_runtime_fault" not in systems
