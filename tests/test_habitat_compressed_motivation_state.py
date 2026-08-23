#!/usr/bin/env python3
"""Regression coverage for lossless Habitat motivation-state packaging."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from aurora_habitat import HabitatRuntime


class HabitatCompressedMotivationStateTests(unittest.TestCase):
    def test_new_events_use_compressed_appendable_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            runtime = HabitatRuntime(state_dir)
            runtime.record_motivation_event({"event_id": "new", "value": 7})

            path = Path(state_dir) / "habitat" / "habitat_motivation_events.jsonl.gz"
            self.assertTrue(path.exists())
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                self.assertEqual(json.loads(handle.readline())["event_id"], "new")

            restored = HabitatRuntime(state_dir)
            self.assertEqual(restored.get_motivation_history()[0]["event_id"], "new")

    def test_legacy_and_compressed_history_restore_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            habitat_dir = Path(state_dir) / "habitat"
            habitat_dir.mkdir(parents=True)
            legacy_path = habitat_dir / "habitat_motivation_events.jsonl"
            legacy_path.write_text(json.dumps({"event_id": "legacy"}) + "\n", encoding="utf-8")
            compressed_path = habitat_dir / "habitat_motivation_events.jsonl.gz"
            with gzip.open(compressed_path, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps({"event_id": "compressed"}) + "\n")

            restored = HabitatRuntime(state_dir)
            self.assertEqual(
                [event["event_id"] for event in restored.get_motivation_history()],
                ["legacy", "compressed"],
            )


if __name__ == "__main__":
    unittest.main()
