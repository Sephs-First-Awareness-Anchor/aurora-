#!/usr/bin/env python3
"""Regression coverage for compressed genealogy snapshot restoration."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from aurora_runtime import _restore_genealogy_state


class CompressedGenealogyStateTests(unittest.TestCase):
    def test_runtime_restores_compressed_abilities_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            record = {
                "ability:test": {
                    "id": "ability:test",
                    "axis": "X",
                    "requires": [],
                    "cost": {},
                    "risk": {},
                    "effect_tags": ["test"],
                    "notes": "compressed",
                }
            }
            with gzip.open(Path(state_dir) / "abilities.json.gz", "wt", encoding="utf-8") as handle:
                json.dump(record, handle)
            logger = SimpleNamespace(
                cfg=SimpleNamespace(
                    ABILITIES_FILE="abilities.json",
                    LINKS_FILE="links.json",
                    EVENTS_FILE="events.jsonl",
                ),
                abilities={},
                links={},
            )

            restored = _restore_genealogy_state(logger, state_dir)
            self.assertEqual(restored["abilities"], 1)
            self.assertEqual(logger.abilities["ability:test"].notes, "compressed")


if __name__ == "__main__":
    unittest.main()
