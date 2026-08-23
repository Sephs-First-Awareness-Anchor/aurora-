#!/usr/bin/env python3
"""Regression coverage for compressed historical-experience state."""

import gzip
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py"
)
SPEC = importlib.util.spec_from_file_location("aurora_historical_experience_compressed_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
HistoricalExperienceEnvironment = MODULE.HistoricalExperienceEnvironment


class HistoricalExperienceCompressedStateTests(unittest.TestCase):
    def test_prepare_uses_existing_compressed_event_state(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            root = Path(state_dir)
            archive = root / "experiential_baseline_v1.zip"
            manifest = {"schema": "test", "event_count": 1, "episode_count": 1}
            event = {"event_id": "evt1", "episode_id": "ep1", "actor": "user", "text": "preserved"}
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("manifest.json", json.dumps(manifest))
                bundle.writestr("episodes.jsonl", json.dumps({"episode_id": "ep1"}) + "\n")
                bundle.writestr("events.jsonl", json.dumps(event) + "\n")

            baseline = root / "historical_experience" / "baseline_v1"
            baseline.mkdir(parents=True)
            compressed = baseline / "events.jsonl.gz"
            with gzip.open(compressed, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")

            environment = HistoricalExperienceEnvironment({}, state_dir=state_dir, archive_path=str(archive))
            environment._prepare()
            self.assertFalse((baseline / "events.jsonl").exists())
            with environment._open_events() as handle:
                self.assertEqual(json.loads(handle.readline())["text"], "preserved")


if __name__ == "__main__":
    unittest.main()
