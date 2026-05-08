#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AURORA_ROOT = Path(__file__).parent.resolve()
STATE_DIR = AURORA_ROOT / "aurora_state"
REPORT_PATH = STATE_DIR / "quasiarch_diag_report.json"
OVERLAY_PATH = STATE_DIR / "governor_sweep_overlay.json"
ACTIVITY_PATH = STATE_DIR / "aurora_room_activity.json"
NOTES_PATH = STATE_DIR / "aurora_room_notes.json"
BRIDGE_EXPORT_PATH = STATE_DIR / "quasiarch_bridge_export.json"
ENFORCER_DIR = Path.home() / ".quasiarch" / "enforcer_state"
ENFORCER_LEDGER = ENFORCER_DIR / "enforcer_ledger.json"

_TASK_AXIS_RE = re.compile(
    r"_TASK_PROFILES\['(?P<task>[^']+)'\]\['axes'\]\['(?P<axis>[A-Z])'\]\s*=\s*(?P<value>[-+]?\d*\.?\d+)"
)
_TASK_FIELD_RE = re.compile(
    r"_TASK_PROFILES\['(?P<task>[^']+)'\]\['(?P<field>floor|cost|retry)'\]\s*=\s*(?P<value>[-+]?\d*\.?\d+)"
)
_GLOBAL_AXIS_RE = re.compile(
    r'"axis_weights"\s*:\s*\{\s*"(?P<axis>[A-Z])"\s*:\s*(?P<value>[-+]?\d*\.?\d+)'
)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _append_activity(action: str, detail: str, category: str = "change") -> None:
    activity = _read_json(ACTIVITY_PATH, [])
    if not isinstance(activity, list):
        activity = []
    activity.append({
        "ts": time.time(),
        "ts_str": time.strftime("%H:%M:%S"),
        "action": action,
        "detail": detail,
        "category": category,
    })
    _write_json(ACTIVITY_PATH, activity[-500:])


def _append_note(title: str, content: str, source: str = "quasiarch_bridge") -> None:
    notes = _read_json(NOTES_PATH, [])
    if not isinstance(notes, list):
        notes = []
    notes.append({
        "ts": time.time(),
        "ts_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": title,
        "content": content,
        "source": source,
    })
    _write_json(NOTES_PATH, notes[-200:])


def _load_overlay() -> Dict[str, Any]:
    overlay = _read_json(OVERLAY_PATH, {})
    return overlay if isinstance(overlay, dict) else {}


def _load_report() -> Dict[str, Any]:
    report = _read_json(REPORT_PATH, {})
    return report if isinstance(report, dict) else {}


def _find_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    for proposal in list(_load_report().get("proposals") or []):
        if str(proposal.get("proposal_id") or "") == proposal_id:
            return dict(proposal)
    return None


def _parse_overlay_patch(proposal: Dict[str, Any]) -> Dict[str, Any]:
    code_hint = str(proposal.get("code_hint") or "").strip()
    patch: Dict[str, Any] = {"active": True}
    task_overrides: Dict[str, Dict[str, Any]] = {}
    global_axis: Dict[str, float] = {}

    if code_hint.startswith("{"):
        try:
            parsed = json.loads(code_hint)
            if isinstance(parsed, dict):
                patch.update(parsed)
        except Exception:
            pass

    axis_match = _TASK_AXIS_RE.search(code_hint)
    if axis_match:
        task = axis_match.group("task")
        axis = axis_match.group("axis")
        value = float(axis_match.group("value"))
        task_overrides.setdefault(task, {}).setdefault("axes", {})[axis] = value

    field_match = _TASK_FIELD_RE.search(code_hint)
    if field_match:
        task = field_match.group("task")
        field = field_match.group("field")
        value = float(field_match.group("value"))
        task_overrides.setdefault(task, {})[field] = value

    global_axis_match = _GLOBAL_AXIS_RE.search(code_hint)
    if global_axis_match:
        global_axis[global_axis_match.group("axis")] = float(global_axis_match.group("value"))

    if isinstance(patch.get("task_overrides"), dict):
        for task, override in dict(patch.get("task_overrides") or {}).items():
            if not isinstance(override, dict):
                continue
            task_overrides.setdefault(str(task), {}).update(override)
    if isinstance(patch.get("axis_weights"), dict):
        for axis, value in dict(patch.get("axis_weights") or {}).items():
            try:
                global_axis[str(axis).upper()[:1]] = float(value)
            except Exception:
                continue

    if task_overrides:
        patch["task_overrides"] = task_overrides
    if global_axis:
        patch["axis_weights"] = global_axis

    action = str(proposal.get("proposed_action") or "").lower()
    issue = str(proposal.get("quasi_id") or proposal.get("issue_archetype") or "")
    if "coherence" in issue or "coherence" in action:
        patch.setdefault("heat_hint", "medium")
    elif "meaning" in issue:
        patch.setdefault("heat_hint", "medium")
    elif "grounding" in issue:
        patch.setdefault("heat_hint", "normal")

    return patch


def _merge_overlay(base: Dict[str, Any], patch: Dict[str, Any], proposal_id: str) -> Dict[str, Any]:
    out = dict(base or {})
    out["active"] = bool(patch.get("active", True))
    out["written_at"] = time.time()
    out["written_by"] = "quasiarch_bridge"
    out["proposal_id"] = proposal_id
    if "heat_hint" in patch:
        out["heat_hint"] = str(patch.get("heat_hint") or "medium")
    if "maintenance_mult" in patch:
        out["maintenance_mult"] = float(patch.get("maintenance_mult") or 0.1)
    if "n_floor_override" in patch:
        out["n_floor_override"] = float(patch.get("n_floor_override") or 0.1)
    if isinstance(patch.get("axis_weights"), dict):
        axis_weights = dict(out.get("axis_weights") or {})
        axis_weights.update(patch.get("axis_weights") or {})
        out["axis_weights"] = axis_weights
    if isinstance(patch.get("task_overrides"), dict):
        task_overrides = dict(out.get("task_overrides") or {})
        for task, override in dict(patch.get("task_overrides") or {}).items():
            current = dict(task_overrides.get(task) or {})
            if isinstance(override, dict):
                if isinstance(override.get("axes"), dict):
                    axes = dict(current.get("axes") or {})
                    axes.update(override.get("axes") or {})
                    current["axes"] = axes
                for key, value in override.items():
                    if key == "axes":
                        continue
                    current[key] = value
            task_overrides[task] = current
        out["task_overrides"] = task_overrides
    return out


def _load_ledger() -> List[Dict[str, Any]]:
    ledger = _read_json(ENFORCER_LEDGER, [])
    return ledger if isinstance(ledger, list) else []


def _write_ledger(records: List[Dict[str, Any]]) -> None:
    ENFORCER_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(ENFORCER_LEDGER, records[-500:])


def apply_proposal(proposal_id: str) -> Dict[str, Any]:
    proposal = _find_proposal(proposal_id)
    if not proposal:
        return {"ok": False, "reason": "proposal_not_found", "proposal_id": proposal_id}

    before = _load_overlay()
    patch = _parse_overlay_patch(proposal)
    after = _merge_overlay(before, patch, proposal_id)
    _write_json(OVERLAY_PATH, after)

    ledger = _load_ledger()
    ledger.append({
        "ts": time.time(),
        "proposal_id": proposal_id,
        "status": "applied",
        "file": proposal.get("file", "aurora_state/governor_sweep_overlay.json"),
        "proposed_action": proposal.get("proposed_action", ""),
        "code_hint": proposal.get("code_hint", ""),
        "before_overlay": before,
        "after_overlay": after,
        "bridge_mode": "runtime_overlay",
    })
    _write_ledger(ledger)

    _append_activity(
        "subsurface enforcer applied proposal",
        f"{proposal_id} -> runtime overlay for {proposal.get('issue_archetype') or proposal.get('quasi_id') or 'repair'}",
    )
    _append_note(
        "quasiarch_enforcement",
        (
            "AUTONOMOUS ENFORCER ACTION\n\n"
            f"Proposal: {proposal_id}\n"
            f"Action: {proposal.get('proposed_action')}\n"
            f"Hint: {proposal.get('code_hint')}\n\n"
            "Applied as a live runtime overlay so subsurface can correct behavior safely."
        ),
    )
    return {"ok": True, "proposal_id": proposal_id, "overlay": after}


def revert_proposal(proposal_id: str) -> Dict[str, Any]:
    ledger = _load_ledger()
    record = next((rec for rec in reversed(ledger) if str(rec.get("proposal_id") or "") == proposal_id and rec.get("status") == "applied"), None)
    if not record:
        return {"ok": False, "reason": "applied_record_not_found", "proposal_id": proposal_id}

    before = _load_overlay()
    restore = dict(record.get("before_overlay") or {})
    if restore:
        _write_json(OVERLAY_PATH, restore)
    else:
        _write_json(OVERLAY_PATH, {"active": False, "written_at": time.time(), "written_by": "quasiarch_bridge"})

    ledger.append({
        "ts": time.time(),
        "proposal_id": proposal_id,
        "status": "reverted",
        "file": record.get("file", "aurora_state/governor_sweep_overlay.json"),
        "proposed_action": record.get("proposed_action", ""),
        "before_overlay": before,
        "after_overlay": restore,
        "bridge_mode": "runtime_overlay",
    })
    _write_ledger(ledger)

    _append_activity("subsurface enforcer reverted proposal", proposal_id)
    _append_note(
        "quasiarch_revert",
        (
            "AUTONOMOUS ENFORCER REVERT\n\n"
            f"Proposal: {proposal_id}\n"
            "The live runtime overlay was restored to its prior state."
        ),
    )
    return {"ok": True, "proposal_id": proposal_id, "overlay": restore}


class AuroraQuasiArchBridge:
    def __init__(
        self,
        aurora_root: str,
        observer_state_dir: str,
        researcher_state_dir: str = "",
        min_confidence: float = 0.25,
    ) -> None:
        self.aurora_root = Path(aurora_root).resolve()
        self.observer_state_dir = Path(observer_state_dir)
        self.researcher_state_dir = Path(researcher_state_dir) if researcher_state_dir else self.observer_state_dir.parent / "researcher_state"
        self.min_confidence = float(min_confidence)

    def export(
        self,
        *,
        from_abilities: bool = True,
        from_links: bool = True,
        from_operations: bool = False,
    ) -> Dict[str, Any]:
        genealogy_dir = self.aurora_root / "aurora_state" / "genealogy"
        abilities = _read_json(genealogy_dir / "abilities.json", []) if from_abilities else []
        links = _read_json(genealogy_dir / "links.json", []) if from_links else []
        abilities_count = len(abilities) if isinstance(abilities, list) else len(dict(abilities or {}))
        links_count = len(links) if isinstance(links, list) else len(dict(links or {}))
        payload = {
            "ts": time.time(),
            "aurora_root": str(self.aurora_root),
            "abilities_count": abilities_count,
            "links_count": links_count,
            "from_operations": bool(from_operations),
            "min_confidence": self.min_confidence,
        }
        _write_json(BRIDGE_EXPORT_PATH, payload)
        return {
            "written": abilities_count + links_count,
            "skipped_confidence": 0,
            "skipped_duplicate": 0,
            "quasi_dir": str(self.observer_state_dir / "nodes" / "quasi"),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", default="")
    parser.add_argument("--revert", default="")
    args = parser.parse_args()

    if args.apply:
        result = apply_proposal(str(args.apply))
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    if args.revert:
        result = revert_proposal(str(args.revert))
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
