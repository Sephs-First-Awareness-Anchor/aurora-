# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
bridge_ledger_to_noncomps.py

PressureExperienceLedger.record() (aurora_internal/aurora_pressure_ledger.py)
persists every experience to aurora_state/pressure_experiences.jsonl, keyed
by an `anchor` string. It does NOT write into the manifold's noncomp JSON
files -- that log and the manifold directory are two separate things until
something explicitly connects them. This script is that connection.

Match rule: a PressureExperience entry belongs to a noncomp if its `anchor`
field equals that noncomp's `nc_name` (e.g. "Existential_Operator_of_Existence").
Any subsystem that wants its pressure events to land on a specific noncomp's
development_tracking.history just needs to call:

    PressureExperienceLedger.get().record(
        anchor="Existential_Operator_of_Existence",   # <- must equal nc_name
        meaning=..., pursuing=..., causal_action=...,
        consequence={...}, outcome={...}, source="...",
    )

Run this script periodically (e.g. end of a boot/test cycle) to pull new
ledger entries into the matching noncomp files' history arrays. It is
idempotent -- already-ingested experience_ids are skipped on rerun.
"""
from __future__ import annotations
import json
from pathlib import Path

LEDGER_PATH = Path("aurora_state/pressure_experiences.jsonl")


def load_ledger_entries(ledger_path: Path) -> list[dict]:
    if not ledger_path.exists():
        print(f"No ledger file found at {ledger_path} -- nothing to bridge yet.")
        return []
    entries = []
    with open(ledger_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def index_by_anchor(entries: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for e in entries:
        anchor = e.get("anchor", "")
        if not anchor:
            continue
        index.setdefault(anchor, []).append(e)
    return index


def bridge_manifold(manifold_root: str, ledger_path: Path = LEDGER_PATH) -> int:
    entries = load_ledger_entries(ledger_path)
    by_anchor = index_by_anchor(entries)
    if not by_anchor:
        return 0

    root = Path(manifold_root)
    total_appended = 0

    for axis in ["X", "T", "N", "B", "A"]:
        axis_dir = root / axis
        if not axis_dir.is_dir():
            continue
        for path in sorted(axis_dir.glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            nc_name = data.get("nc_name")
            if not nc_name or nc_name not in by_anchor:
                continue

            tracking = data.setdefault("development_tracking", {
                "history": [],
                "sink": "PressureExperienceLedger.record() in aurora_internal/aurora_pressure_ledger.py",
                "note": "",
            })
            history = tracking.setdefault("history", [])
            existing_ids = {h.get("experience_id") for h in history}

            appended_here = 0
            for exp in by_anchor[nc_name]:
                if exp.get("experience_id") in existing_ids:
                    continue
                history.append({
                    "experience_id": exp.get("experience_id"),
                    "timestamp":     exp.get("timestamp"),
                    "source":        exp.get("source"),
                    "meaning":       exp.get("meaning"),
                    "pursuing":      exp.get("pursuing"),
                    "causal_action": exp.get("causal_action"),
                    "consequence":   exp.get("consequence"),
                    "outcome":       exp.get("outcome"),
                })
                appended_here += 1

            if appended_here:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                total_appended += appended_here

    return total_appended


if __name__ == "__main__":
    import sys
    manifold_dir = sys.argv[1] if len(sys.argv) > 1 else "aurora_manifold_directory"
    n = bridge_manifold(manifold_dir)
    print(f"Appended {n} ledger experiences into matching noncomp history arrays.")
