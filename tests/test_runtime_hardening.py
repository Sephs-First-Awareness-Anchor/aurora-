# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Regression tests for operational readiness and release boundaries."""

import json
import tempfile
import unittest
from pathlib import Path

from aurora_internal.aurora_fault_audit import audit_source_tree
from aurora_internal.aurora_runtime_faults import fault_summary, record_runtime_fault
from aurora_internal.aurora_runtime_health import compute_runtime_health


class RuntimeHardeningTests(unittest.TestCase):
    def test_degraded_is_not_ready_without_explicit_permission(self):
        systems = {"state_dir": tempfile.mkdtemp()}
        record_runtime_fault(
            systems,
            subsystem="test",
            operation="optional_boundary",
            exc=RuntimeError("optional subsystem failed"),
        )
        denied = compute_runtime_health(systems)
        allowed = compute_runtime_health(systems, allow_degraded=True)
        self.assertEqual(denied["overall"], "degraded")
        self.assertFalse(denied["ready"])
        self.assertTrue(allowed["ready"])

    def test_unready_can_never_be_ready(self):
        systems = {"_runtime_unready": True, "_runtime_unready_reason": "boot failed"}
        self.assertFalse(compute_runtime_health(systems)["ready"])
        self.assertFalse(compute_runtime_health(systems, allow_degraded=True)["ready"])

    def test_fault_is_written_to_active_state_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            systems = {"state_dir": tmp}
            record_runtime_fault(
                systems,
                subsystem="test",
                operation="write_boundary",
                exc=ValueError("visible"),
            )
            payload = Path(tmp, "runtime_faults.jsonl").read_text(encoding="utf-8")
            self.assertIn("visible", payload)

    def test_persisted_invariant_fault_marks_runtime_unready(self):
        with tempfile.TemporaryDirectory() as tmp:
            systems = {"state_dir": tmp}
            Path(tmp, "runtime_faults.jsonl").write_text(
                json.dumps({
                    "schema_version": 2,
                    "timestamp": 1.0,
                    "subsystem": "boot",
                    "operation": "required_constructor",
                    "severity": "invariant_violation",
                    "exception_type": "TypeError",
                    "message": "required argument missing",
                    "traceback_hash": "boot-hash",
                    "context": {},
                }) + "\n",
                encoding="utf-8",
            )
            health = compute_runtime_health(systems)
            self.assertEqual(health["overall"], "unready")
            self.assertFalse(health["ready"])
            self.assertEqual(health["faults"]["invariant_count"], 1)

    def test_persisted_and_memory_faults_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            event = {
                "schema_version": 2,
                "timestamp": 1.0,
                "subsystem": "boot",
                "operation": "same_event",
                "severity": "subsystem_degradation",
                "exception_type": "RuntimeError",
                "message": "same event",
                "traceback_hash": "same-hash",
                "context": {},
            }
            Path(tmp, "runtime_faults.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
            systems = {"state_dir": tmp, "_runtime_faults": [dict(event)]}
            summary = fault_summary(systems)
            self.assertEqual(summary["total"], 1)
            self.assertEqual(summary["count"], 1)

    def test_expected_fallback_warning_does_not_change_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            systems = {"state_dir": tmp}
            record_runtime_fault(
                systems,
                subsystem="optional",
                operation="missing_cache",
                exc=FileNotFoundError("cache not created yet"),
            )
            health = compute_runtime_health(systems)
            self.assertEqual(health["overall"], "healthy")
            self.assertTrue(health["ready"])
            self.assertEqual(health["faults"]["warning_count"], 1)

    def test_production_fault_audit_parses(self):
        report = audit_source_tree(Path(__file__).resolve().parents[1])
        self.assertFalse(report["parse_errors"])
        self.assertIsInstance(report["unreported"], int)


if __name__ == "__main__":
    unittest.main()
