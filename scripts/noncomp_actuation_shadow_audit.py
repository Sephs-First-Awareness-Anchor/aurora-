#!/usr/bin/env python3
"""
Shadow audit for runtime noncomp actuation.

Boots Aurora against fresh temp state for each probe so we can inspect:
  - selected noncomp manifold cell
  - constraint / dimension classification
  - behavior actuation effects + runtime flags
  - resulting response text

This is meant to verify that manifold selection is behaviorally live, not just
diagnostic, without touching Aurora's real state directory.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora import boot_aurora, process_external_user_turn


DEFAULT_PROBES: List[Dict[str, Any]] = [
    {
        "label": "temporal_recall",
        "setup": ["my signal word is obsidian"],
        "turn": "what is my signal word?",
    },
    {
        "label": "existence_lookup",
        "setup": [],
        "turn": "what does reciprocity mean?",
    },
    {
        "label": "energetic_cost",
        "setup": [],
        "turn": "what would it cost me to commit to this?",
    },
    {
        "label": "boundary_repair",
        "setup": [],
        "turn": "that's not what I meant at the boundary",
    },
    {
        "label": "agency_clarification",
        "setup": [],
        "turn": "can you clarify what you meant?",
    },
]


def _run_turn(systems: Dict[str, Any], text: str, *, session_id: str) -> Dict[str, Any]:
    return process_external_user_turn(
        systems,
        text,
        source_label="noncomp_shadow_audit",
        session_id=session_id,
        auto_search_enabled=False,
        record_exchange=True,
        update_interactive_state=False,
        track_evolutionary_trace=True,
        run_periodic_maintenance=False,
    )


def _run_probe(root: Path, probe: Dict[str, Any]) -> Dict[str, Any]:
    label = str(probe.get("label", "probe") or "probe")
    state_dir = root / label
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    systems = boot_aurora(state_dir=str(state_dir), verbose=False)
    for setup_turn in list(probe.get("setup", []) or []):
        _run_turn(systems, str(setup_turn), session_id=f"{label}:setup")

    result = _run_turn(
        systems,
        str(probe.get("turn", "") or ""),
        session_id=f"{label}:main",
    )
    noncomp_input = dict(result.get("noncomp_input") or {})
    actuation = dict(noncomp_input.get("behavior_actuation") or {})
    response = str(getattr(result.get("resp_A"), "content", "") or "")

    return {
        "label": label,
        "turn": str(probe.get("turn", "") or ""),
        "setup": list(probe.get("setup", []) or []),
        "state_dir": str(state_dir),
        "frame": noncomp_input.get("frame"),
        "query_type": noncomp_input.get("query_type"),
        "semantic_override": noncomp_input.get("semantic_override"),
        "constraint": noncomp_input.get("constraint"),
        "dimension": noncomp_input.get("dimension"),
        "nc_name": noncomp_input.get("nc_name"),
        "field_region": noncomp_input.get("field_region"),
        "remedy": noncomp_input.get("remedy"),
        "effects": list(actuation.get("effects") or []),
        "flags": list(actuation.get("flags") or []),
        "runtime_flags": dict(actuation.get("runtime_flags") or {}),
        "response": response,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fresh-state noncomp actuation shadow audit.")
    parser.add_argument(
        "--state-root",
        default="/tmp/aurora_noncomp_shadow_audit",
        help="Temp state root used for isolated probe boots.",
    )
    parser.add_argument(
        "--probes-json",
        default="",
        help="Optional JSON file overriding the default probe list.",
    )
    args = parser.parse_args()

    root = Path(str(args.state_root or "/tmp/aurora_noncomp_shadow_audit"))
    root.mkdir(parents=True, exist_ok=True)

    probes = DEFAULT_PROBES
    if args.probes_json:
        probes = json.loads(Path(args.probes_json).read_text())

    rows = [_run_probe(root, probe) for probe in probes]
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
