# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
bridge_tensor_occupancy_to_warp.py

Periodic driver for tensor_occupancy_warp_bridge.py: reads new lines from
aurora_state/tensor_occupancy.jsonl (written by tensor_occupancy_hook.py,
installed automatically from ConstraintEngine.__init__), feeds each
deposit's vector through TensorOccupancyWarpBridge.process_entry(), then
runs one evaluate_warp_trials() cycle. Newly-integrated components are
already appended to aurora_state/tensor_occupancy_warp_components.jsonl by
the bridge itself (_integrate_warp); this script additionally prints an
anomaly/status summary each run.

Idempotent across runs the same way bridge_ledger_to_noncomps.py is: a
small cursor file (aurora_state/.tensor_occupancy_warp_cursor) tracks how
many lines have been consumed, so re-running only processes new entries.

Cross-run state (anomaly log, gap-persistence counter, live trial/promoted
components) is loaded from aurora_state/tensor_occupancy_warp_bridge_state.json
on construction and saved back at the end of every run -- see
tensor_occupancy_warp_bridge.py's load_state()/save_state(). The bridge is
constructed and its trial cycle advanced even when there are no new
occupancy entries, so persisted trials keep progressing toward promotion or
dissolution between deposit bursts instead of stalling.

Run this script periodically (e.g. end of a boot/test cycle).
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tensor_occupancy_warp_bridge import TensorOccupancyWarpBridge

LOG_PATH = Path("aurora_state/tensor_occupancy.jsonl")
CURSOR_PATH = Path("aurora_state/.tensor_occupancy_warp_cursor")


def run(log_path: Path = LOG_PATH, cursor_path: Path = CURSOR_PATH) -> dict:
    new_lines: list[str] = []
    total_lines = 0

    if log_path.exists():
        with open(log_path, "r") as f:
            lines = f.readlines()
        total_lines = len(lines)
        start = 0
        try:
            start = int(cursor_path.read_text().strip())
        except Exception:
            start = 0
        new_lines = lines[start:]
    else:
        print(f"No occupancy log found at {log_path} -- nothing new to process, "
              f"still advancing any persisted trial components.")

    # Construct (and save) even with zero new entries -- persisted trial
    # components must keep advancing toward promotion/dissolution between
    # deposit bursts, not stall until the next batch of new lines arrives.
    bridge = TensorOccupancyWarpBridge()
    spawned = 0
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if bridge.process_entry(entry) is not None:
            spawned += 1

    bridge.run_cycle()
    bridge.save_state()

    if total_lines:
        try:
            cursor_path.parent.mkdir(exist_ok=True)
            cursor_path.write_text(str(total_lines))
        except Exception:
            pass

    status = bridge.warp_status()
    anomalies = bridge._warp_generator.anomaly_summary()
    return {
        "processed":  len(new_lines),
        "components": spawned,
        "trials":     status["trials"],
        "promoted":   status["promoted"],
        "anomalies":  len(anomalies),
        "candidates": [a for a in anomalies if a["candidate"]],
    }


if __name__ == "__main__":
    result = run()
    print(
        f"Processed {result['processed']} occupancy entries -> "
        f"{result.get('components', 0)} components spawned this run "
        f"({result.get('trials', 0)} trials, {result.get('promoted', 0)} promoted), "
        f"{result.get('anomalies', 0)} anomaly signatures logged"
        + (f", {len(result['candidates'])} promoted to 6th-axis candidate" if result.get('candidates') else "")
    )
