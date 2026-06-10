"""
quasiarch_diag.py
─────────────────────────────────────────────────────────────────────────────
QuasiArch Diagnostic Runner — external dev tool, ZERO cost to Aurora.

What this does:
  1. Bridge export()  — reads Aurora's abilities/links (read-only) and
                        converts them to quasicrystal doctrine nodes.
  2. Researcher scan  — pure AST/file scan of AuroraO codebase, matches
                        known failure archetypes from doctrine.
  3. Proposal report  — writes human-readable JSON report to aurora_state/.
                        No code is changed, no enforcer is called.

What this does NOT do:
  - Does NOT call bridge.feedback() (no verdicts pushed to Aurora's chamber)
  - Does NOT call the Enforcer (no auto code changes)
  - Does NOT touch Aurora's governor, pressure logs, evolver, or any
    runtime API — purely a file reader / AST analyzer.

Run manually:
    python3 quasiarch_diag.py

Run on a schedule (from aurora_daemon.py or cron):
    python3 quasiarch_diag.py --quiet

Authors: Sunni (Sir) Morningstar and Cael Devo
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── paths ─────────────────────────────────────────────────────────────────────

AURORA_ROOT       = Path(__file__).parent.resolve()
QUASIARCH_STATE   = Path.home() / ".quasiarch"
OBSERVER_STATE    = QUASIARCH_STATE / "crystal_state"
RESEARCHER_STATE  = QUASIARCH_STATE / "researcher_state"
REPORT_PATH       = AURORA_ROOT / "aurora_state" / "quasiarch_diag_report.json"
LOG_PATH          = AURORA_ROOT / "aurora_state" / "quasiarch_diag.log"
STATE_DIR         = AURORA_ROOT / "aurora_state"
QAO_RUNTIME_PATH  = STATE_DIR / "quasiarch_observer" / "runtime_state.json"
QAO_JOURNAL_PATH  = STATE_DIR / "quasiarch_observer" / "journal.jsonl"
POEDEX_QUERY_PATH = STATE_DIR / "poedex_query_queue.json"
POEDEX_RESULT_PATH = STATE_DIR / "poedex_query_result.json"

# Minimum doctrine confidence to scan against (low — we want broad coverage)
MIN_CONFIDENCE = 0.25

# ── logging ───────────────────────────────────────────────────────────────────

def _log(msg: str, quiet: bool = False) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}]  {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if not quiet:
        print(line)


# ── bridge export (read-only) ─────────────────────────────────────────────────

def run_export(quiet: bool) -> Dict[str, int]:
    """
    Translate Aurora's abilities.json / links.json → quasicrystal doctrine nodes.
    Pure read from Aurora side — nothing written back to Aurora.
    """
    try:
        from quasiarch_bridge import AuroraQuasiArchBridge
        bridge = AuroraQuasiArchBridge(
            aurora_root          = str(AURORA_ROOT),
            observer_state_dir   = str(OBSERVER_STATE),
            researcher_state_dir = str(RESEARCHER_STATE),
            min_confidence       = MIN_CONFIDENCE,
        )
        counts = bridge.export(from_abilities=True, from_links=True, from_operations=False)
        _log(f"Bridge export: {counts}", quiet)
        return counts
    except Exception as exc:
        _log(f"Bridge export error (non-fatal): {exc}", quiet)
        return {"written": 0, "skipped_confidence": 0, "skipped_duplicate": 0}


# ── researcher scan ───────────────────────────────────────────────────────────

def _load_committed_skip_set() -> set:
    """
    Return a set of (file, action_prefix) tuples for proposals already committed
    by the enforcer. Proposals matching these are excluded from new scan output.
    """
    skip = set()
    try:
        if not ENFORCER_LEDGER.exists():
            return skip
        records = json.loads(ENFORCER_LEDGER.read_text())
        if not isinstance(records, list):
            records = [records]
        for rec in records:
            if rec.get("status") in ("committed", "applied"):
                f = rec.get("file", "")
                a = (rec.get("proposed_action") or "")[:60]
                if f:
                    skip.add((f, a))
    except Exception:
        pass
    return skip


def run_scan(quiet: bool) -> List[Dict[str, Any]]:
    """
    Scan AuroraO codebase with AST pattern matching against doctrine.
    No Aurora runtime calls — pure file reads and AST analysis.
    """
    proposals_out: List[Dict[str, Any]] = []
    try:
        from quasiarch_researcher.researcher import Researcher
        from quasiarch_researcher.scanner.codebase_scanner import CodebaseScanner
        from quasiarch_researcher.hypothesis.hypothesis_engine import HypothesisEngine

        researcher = Researcher(
            observer_state_dir = str(OBSERVER_STATE),
            state_dir          = str(RESEARCHER_STATE),
            auto_run_tests     = False,
            auto_simulate      = False,
        )

        # Ingest any new quasicrystals from the observer state
        new_records = researcher.ingest()
        _log(f"Researcher: ingested {len(new_records)} new doctrine nodes", quiet)

        # Only use diagnostically meaningful doctrine archetypes — not the
        # bridge-exported ability/link patterns (admissibility_gating, X_axis_pattern:*
        # etc.) which are evolutionary artifacts, not code-bug doctrine.
        DIAGNOSTIC_ARCHETYPES = {
            "general_diagnostic_anomaly",
            "persistence_boundary_failure",
            "constraint_physics_violation",
            "data_source_mismatch",
            "sensory_session_fixation",
            "difficulty_cap_bypass",
            "memory_clobber_on_write",
            "threshold_miscalibration",
        }
        all_records = researcher.registry.all()
        custody_records = [
            r for r in all_records
            if getattr(r, "issue_archetype", "") in DIAGNOSTIC_ARCHETYPES
        ]
        _log(f"Researcher: {len(custody_records)}/{len(all_records)} diagnostic "
             f"doctrine nodes to scan", quiet)

        # Active runtime scripts — only files Aurora actually loads during operation.
        # Keeps scan fast and focused on code that matters.
        # constraint_genealogy.py and aurora_hub.py are >150KB so excluded by size limit;
        # they're also in active use but their size makes AST scanning O(n²) slow.
        ACTIVE_SCRIPTS: List[str] = [
            "aurora_daemon.py",
            "corpus_runner.py",
            "aurora_expression_perception.py",
            "aurora_simulation_engine.py",
            "aurora_dream_trainer.py",
            "aurora_consciousness_engine.py",
            "aurora_dimensional_systems.py",
            "quasiarch_diag.py",
            "aurora_internal/aurora_leverage_relief.py",
            "aurora_internal/aurora_runtime_constraint_governor.py",
            "aurora_internal/aurora_sensory_crystal.py",
            "aurora_internal/aurora_pressure_adapter.py",
            "aurora_internal/aurora_noncomp_registry.py",
            "aurora_internal/aurora_evolution_chamber.py",
        ]
        # Resolve to absolute paths that actually exist
        scan_targets = [
            AURORA_ROOT / rel for rel in ACTIVE_SCRIPTS
            if (AURORA_ROOT / rel).exists()
        ]
        _log(f"Scanning {len(scan_targets)} active runtime scripts", quiet)

        # One scanner per file (target_dir doesn't matter since we pass root_dir)
        scanner = CodebaseScanner(
            target_dir       = str(AURORA_ROOT),
            max_file_size_kb = 300,
        )

        import ast as _ast

        def _scan_file_targeted(path, record):
            """Scan a single file against one doctrine record, returning matches."""
            # Inline a fast AST scan that avoids the O(n²) _enclosing_function
            # for large files. We use the scanner's pattern library but do our
            # own node walk with a pre-built parent map for cheap function lookup.
            try:
                source = path.read_text(errors="replace")
                tree   = _ast.parse(source, filename=str(path))
            except Exception:
                return []

            lines   = source.splitlines()
            # Build lineno → enclosing function name map in O(n) once per file
            fn_map: dict = {}
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                    name  = getattr(node, "name", "")
                    start = getattr(node, "lineno", 0)
                    end   = getattr(node, "end_lineno", start)
                    for ln in range(start, end + 1):
                        if ln not in fn_map:
                            fn_map[ln] = name

            from quasiarch_researcher.scanner.codebase_scanner import (
                _ARCHETYPE_PATTERNS, ScanMatch,
            )
            patterns = list(_ARCHETYPE_PATTERNS.get(record.issue_archetype, []))
            patterns += _ARCHETYPE_PATTERNS.get("_all", [])
            seen = set(); unique_patterns = []
            for p in patterns:
                if id(p) not in seen:
                    seen.add(id(p)); unique_patterns.append(p)
            if not unique_patterns:
                return []

            try:
                rel_file = str(path.relative_to(AURORA_ROOT))
            except ValueError:
                rel_file = str(path)

            matches = []
            module  = rel_file.replace("/", ".").removesuffix(".py")
            for node in _ast.walk(tree):
                for pat_fn in unique_patterns:
                    try:
                        reason = pat_fn(node, lines)
                    except Exception:
                        reason = None
                    if not reason:
                        continue
                    lineno = getattr(node, "lineno", 0)
                    fname  = fn_map.get(lineno, "")
                    target = f"{module}:{fname}" if fname else f"{module}:line_{lineno}"
                    start  = max(0, lineno - 3)
                    end    = min(len(lines), lineno + 3)
                    snippet = "\n".join(lines[start:end])
                    matches.append(ScanMatch(
                        file             = rel_file,
                        line             = lineno,
                        target           = target,
                        match_reason     = reason,
                        issue_archetype  = record.issue_archetype,
                        primary_strategy = record.primary_strategy,
                        confidence       = record.confidence * 0.8,
                        snippet          = snippet,
                    ))
                    break  # one match per node
            return matches

        for record in custody_records:
            quasi_id = getattr(record, "quasi_id", "")
            if not quasi_id:
                continue
            all_matches = []
            for fpath in scan_targets:
                try:
                    file_matches = _scan_file_targeted(fpath, record)
                    all_matches.extend(file_matches)
                except Exception:
                    pass
            if not all_matches:
                continue
            # Generate proposals for top matches (cap at 1 per record to reduce dupes)
            for match in all_matches[:1]:
                new_proposals = researcher.engine.generate(record, match, n_templates=1)
                for p in new_proposals:
                    proposals_out.append(
                        p.to_dict() if hasattr(p, "to_dict") else dict(p.__dict__)
                    )

        # Deduplicate: same (file, line, proposed_action) is the same fix
        # Also skip anything already committed by the enforcer
        skip_set = _load_committed_skip_set()
        seen_keys: set = set()
        deduped: List[Dict[str, Any]] = []
        for p in proposals_out:
            file_val   = p.get("file", "")
            action_pre = (p.get("proposed_action") or "")[:60]
            if (file_val, action_pre) in skip_set:
                continue
            key = (file_val, int(p.get("line", 0)), (p.get("proposed_action") or "")[:80])
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(p)
        proposals_out = deduped

        _log(f"Researcher: {len(proposals_out)} unique proposals after dedup/skip", quiet)

    except Exception as exc:
        _log(f"Researcher scan error (non-fatal): {exc}", quiet)

    return proposals_out


# ── report writer ─────────────────────────────────────────────────────────────

def _safe_json_load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _load_daemon_status() -> Dict[str, Any]:
    data = _safe_json_load(_DAEMON_STATUS, {})
    return data if isinstance(data, dict) else {}


def _load_qao_runtime_state() -> Dict[str, Any]:
    data = _safe_json_load(QAO_RUNTIME_PATH, {})
    return data if isinstance(data, dict) else {}


def _recent_qao_issue_counts(limit: int = 60) -> List[Dict[str, Any]]:
    state = _load_qao_runtime_state()
    recent = list(state.get("recent_events") or [])[-limit:]
    counts: Dict[str, int] = {}
    for evt in recent:
        if not isinstance(evt, dict):
            continue
        issue = str(evt.get("issue_category", "") or "").strip()
        if not issue:
            continue
        counts[issue] = counts.get(issue, 0) + 1
    if not counts:
        for issue, count in dict(state.get("issue_counts") or {}).items():
            issue = str(issue or "").strip()
            if issue:
                counts[issue] = int(count or 0)
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [{"issue": issue, "count": count} for issue, count in ranked[:5]]


def _build_report_summary(proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
    status = _load_daemon_status()
    fail_summary = list(status.get("fail_summary") or [])
    qao_recent = int(status.get("qao_recent_events", 0) or 0)
    recent_qao = _recent_qao_issue_counts()
    top_issue = str(status.get("qao_top_issue", "") or (recent_qao[0]["issue"] if recent_qao else "?"))
    worst_sev = max((float(item.get("avg_sev", 0.0) or 0.0) for item in fail_summary), default=0.0)
    qao_penalty = min(0.30, qao_recent / 320.0)
    prop_penalty = min(0.20, len(proposals) / 20.0)
    health_score = round(max(0.0, min(1.0, 1.0 - (worst_sev * 0.65) - qao_penalty - prop_penalty)), 3)
    return {
        "health_score": health_score,
        "qao_recent_events": qao_recent,
        "qao_top_issue": top_issue,
        "recent_qao_issues": recent_qao,
        "fail_summary": fail_summary,
        "runtime_governor_mode": status.get("runtime_governor_mode", ""),
        "runtime_recent_blocked": status.get("runtime_recent_blocked", []),
    }


def write_report(proposals: List[Dict[str, Any]], export_counts: Dict[str, int]) -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "aurora_root": str(AURORA_ROOT),
        "export_counts": export_counts,
        "proposal_count": len(proposals),
        "summary": _build_report_summary(proposals),
        "proposals": proposals,
        "note": (
            "Dev-only diagnostic. No code was changed. "
            "Bridge feedback() was NOT called — Aurora's chamber is untouched."
        ),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


# ── summary printer ───────────────────────────────────────────────────────────

def print_summary(proposals: List[Dict[str, Any]], quiet: bool) -> None:
    if not proposals:
        _log("No proposals generated — codebase looks clean against current doctrine.", quiet)
        return

    # Group by archetype
    by_arch: Dict[str, List[Dict]] = {}
    for p in proposals:
        arch = p.get("issue_archetype", "unknown")
        by_arch.setdefault(arch, []).append(p)

    _log(f"\n{'─'*70}", quiet)
    _log(f"  QUASIARCH DIAGNOSTIC SUMMARY  ({len(proposals)} proposals)", quiet)
    _log(f"{'─'*70}", quiet)
    for arch, ps in sorted(by_arch.items(), key=lambda x: -len(x[1])):
        _log(f"\n  [{arch}]  ({len(ps)} matches)", quiet)
        for p in ps[:3]:  # cap at 3 per archetype in console
            target   = p.get("target", "?")
            fpath    = p.get("file", "?")
            line     = p.get("line", "?")
            strategy = p.get("primary_strategy", "?")
            conf     = p.get("confidence", 0.0)
            action   = p.get("proposed_action", "")
            hint     = p.get("code_hint", "")
            _log(f"    {target}  ({fpath}:{line})", quiet)
            _log(f"    strategy={strategy}  conf={conf:.2f}", quiet)
            if action:
                _log(f"    action: {action}", quiet)
            if hint:
                _log(f"    hint:   {hint}", quiet)
        if len(ps) > 3:
            _log(f"    ... +{len(ps)-3} more (see report)", quiet)
    _log(f"\n  Full report: {REPORT_PATH}", quiet)
    _log(f"{'─'*70}\n", quiet)


# ── enforcer learning feedback ────────────────────────────────────────────────

ENFORCER_LEDGER = Path.home() / ".quasiarch" / "enforcer_state" / "enforcer_ledger.json"
_LEARN_WATERMARK = AURORA_ROOT / "aurora_state" / "quasiarch_learn_watermark.json"


def run_learn(quiet: bool) -> None:
    """
    Feed recent enforcer verdicts back into the Researcher so ClaudeTrainer
    can update strategy templates for stuck archetypes.

    Reads enforcer_ledger.json, records each new verdict via
    researcher.record_outcome(), then calls researcher.sleep_cycle() which
    triggers ClaudeTrainer.train() if any archetypes are stuck.

    Zero cost to Aurora — never touches governor, evolver, or pressure budget.
    """
    try:
        from quasiarch_researcher.researcher import Researcher
        researcher = Researcher(
            observer_state_dir = str(OBSERVER_STATE),
            state_dir          = str(RESEARCHER_STATE),
            auto_run_tests     = False,
            auto_simulate      = False,
        )
    except Exception as exc:
        _log(f"[learn] Researcher init failed (non-fatal): {exc}", quiet)
        return

    # Load watermark — last ledger record we already processed
    watermark_idx = 0
    try:
        if _LEARN_WATERMARK.exists():
            watermark_idx = json.loads(_LEARN_WATERMARK.read_text()).get("processed_count", 0)
    except Exception:
        pass

    # Load ledger records
    try:
        if not ENFORCER_LEDGER.exists():
            _log("[learn] No enforcer ledger yet — nothing to learn from", quiet)
            return
        records = json.loads(ENFORCER_LEDGER.read_text())
        if not isinstance(records, list):
            records = [records]
    except Exception as exc:
        _log(f"[learn] Ledger read error (non-fatal): {exc}", quiet)
        return

    new_records = records[watermark_idx:]
    if not new_records:
        _log("[learn] No new enforcer verdicts since last learn run", quiet)
        return

    learned = 0
    for rec in new_records:
        proposal_id = rec.get("proposal_id") or rec.get("enforcement_id", "")
        status      = rec.get("status", "")
        success     = status in ("committed", "applied")
        # Surface failure dimensions from the record if available
        fail_dims   = rec.get("fail_dims", [])
        if not proposal_id:
            continue
        try:
            researcher.record_outcome(proposal_id, success=success, fail_dims=fail_dims)
            learned += 1
        except Exception as exc:
            _log(f"[learn] record_outcome({proposal_id}) error: {exc}", quiet)

    _log(f"[learn] Recorded {learned} new verdict(s) from enforcer ledger", quiet)

    # Trigger ClaudeTrainer for stuck archetypes (if any)
    try:
        researcher.sleep_cycle()
        _log("[learn] sleep_cycle() complete — ClaudeTrainer ran if archetypes were stuck", quiet)
    except Exception as exc:
        _log(f"[learn] sleep_cycle() error (non-fatal): {exc}", quiet)

    # Advance watermark
    try:
        _LEARN_WATERMARK.parent.mkdir(parents=True, exist_ok=True)
        _LEARN_WATERMARK.write_text(json.dumps({"processed_count": len(records)}))
    except Exception:
        pass


# ── GPT/Poedex research for unknown anomalies ───────────────────────────────

_GPT_KEY_FILE   = AURORA_ROOT / "aurora_state" / "gpt_api_key.txt"
_DAEMON_STATUS  = AURORA_ROOT / "aurora_state" / "daemon_status.json"

# Anomaly types/dims that are semantic (behavioral/pressure) rather than static code bugs.
# These get the pseudocode path: Aurora's variable names are sent as context so GPT
# can write changes that map directly to her codebase.
_SEMANTIC_ANOMALY_TYPES = frozenset({
    "axis_depleted", "axis_imbalance", "coherence_drift",
    "pressure_imbalance", "behavioral", "governor_block",
    "fail_summary", "qao_recurring_issue",
})
_SEMANTIC_DIMS = frozenset({
    "n_axis", "t_axis", "b_axis", "a_axis", "x_axis",
    "coherence_maintenance", "coherence", "pressure",
    "governor", "emotional_calibration", "perspective_integration",
    "context_carryover", "conversational_grounding_gap",
    "meaning_tension", "developmental_pressure_gap",
    "grounding_lookup_instability",
})

# Context primer injected BEFORE the anomaly question for semantic queries.
# Describes Aurora's actual variable names so GPT writes pseudocode that fits.
_AURORA_AXIS_PRIMER = """\
AURORA SYSTEM CONTEXT — read this before answering.

Aurora is an AI with a 5-axis constraint field:
  X axis = existence    (what information is present/real, the gate)
  T axis = belief/time  (temporal patterns and recurrence)
  N axis = energy/cost  (resource pressure — what is worth doing)
  B axis = meaning      (boundary — what falls within significance)
  A axis = agency       (cross-domain integration and direction)

Her runtime governor controls which tasks execute based on per-axis budget.
The key data structure is _TASK_PROFILES in aurora_runtime_constraint_governor.py:

_TASK_PROFILES = {
    "response_turn": {"axes": {"X": 0.30, "T": 0.20, "N": 0.20, "B": 0.15, "A": 0.20},
                      "floor": 0.18, "cost": 0.30, "retry": 60,  "critical": True},
    "study":         {"axes": {"X": 0.15, "T": 0.25, "N": 0.30, "B": 0.10, "A": 0.25},
                      "floor": 0.42, "cost": 0.35, "retry": 300},
    "dream":         {"axes": {"X": 0.10, "T": 0.10, "N": 0.15, "B": 0.35, "A": 0.35},
                      "floor": 0.50, "cost": 0.95, "retry": 1800},
    "browser_ritual":{"axes": {"X": 0.20, "T": 0.10, "N": 0.25, "B": 0.15, "A": 0.30},
                      "floor": 0.60, "cost": 0.82, "retry": 1800},
    "assimilation":  {"axes": {"X": 0.15, "T": 0.15, "N": 0.25, "B": 0.25, "A": 0.20},
                      "floor": 0.56, "cost": 0.78, "retry": 900},
    "mutation":      {"axes": {"X": 0.15, "T": 0.10, "N": 0.20, "B": 0.25, "A": 0.30},
                      "floor": 0.68, "cost": 0.98, "retry": 2400},
    "pressure_routing":{"axes": {"X": 0.10, "T": 0.20, "N": 0.25, "B": 0.25, "A": 0.20},
                        "floor": 0.50, "cost": 0.60, "retry": 600},
    "distill":       {"axes": {"X": 0.20, "T": 0.20, "N": 0.20, "B": 0.20, "A": 0.20},
                      "floor": 0.55, "cost": 0.70, "retry": 1800},
}

Each task runs when its budget score >= profile["floor"].
Budget score = weighted average of per-axis runtime budgets × profile["axes"] weights.

Runtime budgets are computed by _runtime_budgets() using host metrics:
  budgets["N"] = _clamp(max(0.10, 1.0 - load_ratio*0.40 - mem_pressure*0.38 - disk_penalty))
  budgets["T"] = _clamp(1.0 - heat*0.35 - load_ratio*0.25 + pressure_axes.get("T",0.2)*0.10)
  budgets["B"] = _clamp(1.0 - max(0,load_ratio-0.80)*0.60 + pressure_axes.get("B",0.2)*0.10)
  budgets["A"] = _clamp(0.55 + pressure_axes.get(dominant_axis,0.2)*0.35 - heat*0.20)
  budgets["X"] = _clamp(1.0 - load_penalty - mem_penalty - disk_penalty)

Governor overlay file (aurora_state/governor_sweep_overlay.json) can override at runtime
without editing source — useful for temporary pressure adjustments:
  {"axis_weights": {"N": 0.85}, "task_overrides": {"study": {"axes": {"N": 0.25}}}}

The energy income system (governor.record_income) adds budget credits per event:
  "study_complete": {"axes": ["N","T"], "amount": 0.20, "half_life": 3600}
  "response_turn":  {"axes": ["X","A"], "amount": 0.08, "half_life": 600}

Variable naming conventions in pseudocode:
  _TASK_PROFILES['<task>']['axes']['<axis>']  — per-task axis weight (0.0–1.0, sum ≈ 1.0)
  _TASK_PROFILES['<task>']['floor']           — minimum score to run (0.0–1.0)
  _TASK_PROFILES['<task>']['cost']            — resource cost (0.0–1.0)
  budgets['<axis>']                           — live runtime budget for that axis
  governor_sweep_overlay["task_overrides"]    — runtime patch without source edit
"""

# Map known anomaly dimensions → most relevant active script(s) to show GPT
_DIM_TO_FILES: Dict[str, List[str]] = {
    "emotional_calibration":    ["aurora_consciousness_engine.py", "aurora_dream_trainer.py"],
    "coherence_maintenance":    ["aurora_consciousness_engine.py", "aurora_dimensional_systems.py"],
    "context_carryover":        ["aurora_consciousness_engine.py", "aurora_daemon.py"],
    "perspective_integration":  ["aurora_dimensional_systems.py", "aurora_consciousness_engine.py"],
    "conversational_grounding_gap": ["aurora_interaction_processing.py", "aurora_consciousness_engine.py", "aurora_daemon.py"],
    "meaning_tension":          ["aurora_consciousness_engine.py", "aurora_dimensional_systems.py", "aurora_daemon.py"],
    "developmental_pressure_gap": ["aurora_dream_trainer.py", "aurora_internal/aurora_pressure_adapter.py"],
    "grounding_lookup_instability": ["aurora_daemon.py", "aurora_response_teacher.py"],
    "n_axis":                   ["aurora_internal/aurora_runtime_constraint_governor.py"],
    "governor":                 ["aurora_internal/aurora_runtime_constraint_governor.py"],
    "memory":                   ["aurora_internal/aurora_leverage_relief.py", "aurora_daemon.py"],
    "pressure":                 ["aurora_internal/aurora_pressure_adapter.py",
                                 "aurora_internal/aurora_runtime_constraint_governor.py"],
}

_CONTEXT_LINES_GPT = 60   # lines of code to include per file in the GPT prompt


def _load_api_key() -> str:
    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AURORA_GPT_API_KEY")
    if env_key:
        return env_key.strip()
    if _GPT_KEY_FILE.exists():
        try:
            return _GPT_KEY_FILE.read_text().strip()
        except Exception:
            return ""
    return ""


def _gpt_client():
    """External API client — disabled, no client connected."""
    return None


def _strip_fences(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _issue_keywords(dim: str, atype: str = "") -> List[str]:
    parts = []
    for raw in (dim, atype):
        raw = str(raw or "")
        parts.extend(token for token in raw.replace(":", "_").split("_") if len(token) >= 3)
    parts.append(str(dim or ""))
    return [p for p in parts if p]


def _read_code_context(rel_path: str, keywords: Optional[List[str]] = None,
                       max_lines: int = _CONTEXT_LINES_GPT) -> str:
    """Read a focused code window, preferring the first keyword match."""
    fpath = AURORA_ROOT / rel_path
    if not fpath.exists():
        return ""
    try:
        lines = fpath.read_text(errors="replace").splitlines()
    except Exception:
        return ""

    start = 0
    if keywords:
        lowered = [k.lower() for k in keywords if len(k) >= 3]
        for idx, line in enumerate(lines):
            hay = line.lower()
            if any(k in hay for k in lowered):
                start = max(0, idx - max_lines // 3)
                break
    end = min(len(lines), start + max_lines)
    window = lines[start:end]
    return "\n".join(f"{start + i + 1:4}: {line}" for i, line in enumerate(window))


def _guess_target_line(rel_path: str, keywords: List[str]) -> int:
    fpath = AURORA_ROOT / rel_path
    if not fpath.exists():
        return 1
    try:
        for idx, line in enumerate(fpath.read_text(errors="replace").splitlines(), start=1):
            hay = line.lower()
            if any(k.lower() in hay for k in keywords if len(k) >= 3):
                return idx
    except Exception:
        pass
    return 1


def _normalize_file_path(file_val: str, candidates: List[str]) -> str:
    file_val = str(file_val or "").strip()
    if file_val and (AURORA_ROOT / file_val).exists():
        return file_val
    wanted_name = Path(file_val).name if file_val else ""
    for cand in candidates:
        if wanted_name and Path(cand).name == wanted_name:
            return cand
    return candidates[0] if candidates else file_val


def _chat_completion(system_msg: str, user_msg: str, max_tokens: int = 1200) -> str:
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.25,
    }

    client = _gpt_client()
    if client is not None:
        try:
            response = client.chat.completions.create(**payload)
            return str(response.choices[0].message.content or "").strip()
        except Exception:
            pass

    key = _load_api_key()
    if not key:
        return ""
    try:
        import urllib.request as _ur
        req = _ur.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with _ur.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return str(data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""


def _poedex_research_lookup(question: str, timeout: float = 18.0) -> str:
    if not POEDEX_QUERY_PATH.parent.exists():
        return ""
    qid = f"diag-{time.time():.6f}"
    try:
        POEDEX_QUERY_PATH.write_text(json.dumps({
            "id": qid,
            "question": question,
            "cat": "researcher",
            "lane": "service",
            "status": "pending",
            "submitted": time.time(),
        }, indent=2))
    except Exception:
        return ""

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.4)
        try:
            result = _safe_json_load(POEDEX_RESULT_PATH, {})
            if isinstance(result, dict) and result.get("id") == qid and result.get("status") == "done":
                return str(result.get("result", "") or "").strip()
        except Exception:
            pass
    return ""


def _coerce_fix_list(raw: str) -> List[Dict[str, Any]]:
    cleaned = _strip_fences(raw)
    if not cleaned:
        return []
    data = json.loads(cleaned)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _collect_research_anomalies(status: Dict[str, Any], existing_proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}

    def _add(atype: str, dim: str, severity: float, **extra: Any) -> None:
        key = f"{atype}:{dim}"
        payload = {"type": atype, "dim": dim, "severity": round(float(severity or 0.0), 3)}
        payload.update(extra)
        current = seen.get(key)
        if current is None or payload["severity"] > float(current.get("severity", 0.0) or 0.0):
            seen[key] = payload

    for fail in status.get("telemetry_fails", []):
        dim = str(fail.get("dim", "") or "").strip()
        sev = float(fail.get("severity", 0.0) or 0.0)
        if dim and sev >= 0.50:
            _add("telemetry_fail", dim, sev)

    n_val = float((status.get("runtime_governor_axes", {}) or {}).get("N", 1.0) or 1.0)
    if n_val < 0.15:
        _add("axis_depleted", "n_axis", 1.0 - n_val)

    for blocked in status.get("runtime_recent_blocked", []) or []:
        reason = str(blocked.get("reason", "") or "")
        if "axis_budget" in reason or "saturation" in reason:
            _add(
                "task_blocked",
                reason or str(blocked.get("task", "blocked_task") or "blocked_task"),
                float(blocked.get("score", 0.55) or 0.55),
                task=str(blocked.get("task", "") or ""),
            )

    for fail in sorted(status.get("fail_summary", []) or [], key=lambda item: -float(item.get("avg_sev", 0.0) or 0.0)):
        dim = str(fail.get("dim", "") or "").strip()
        avg = float(fail.get("avg_sev", 0.0) or 0.0)
        fails = int(fail.get("fails", 0) or 0)
        if dim and (avg >= 0.20 or fails >= 100):
            _add("fail_summary", dim, max(avg, min(0.85, fails / 500.0)), fails=fails)

    for item in _recent_qao_issue_counts(limit=60):
        issue = str(item.get("issue", "") or "").strip()
        count = int(item.get("count", 0) or 0)
        if issue and count >= 3:
            _add("qao_recurring_issue", issue, min(0.85, 0.20 + count * 0.05), count=count)

    ranked = sorted(seen.values(), key=lambda item: float(item.get("severity", 0.0) or 0.0), reverse=True)
    existing_files = {str(p.get("file", "") or "") for p in existing_proposals}
    filtered: List[Dict[str, Any]] = []
    for anomaly in ranked:
        dim = str(anomaly.get("dim", "") or "")
        rel_files: List[str] = []
        for key in _DIM_TO_FILES:
            if key in dim:
                rel_files.extend(_DIM_TO_FILES[key])
        if not rel_files:
            rel_files = ["aurora_internal/aurora_runtime_constraint_governor.py"]
        if all(file_val in existing_files for file_val in rel_files[:1]):
            continue
        filtered.append(anomaly)
    return filtered[:4]


def run_gpt_research(quiet: bool, existing_proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Query Poedex first, then GPT fallback, for fix hypotheses on anomalies not covered
    by doctrine proposals. Uses fail_summary and recurring QAO signals in addition to
    telemetry_fails so the researcher reacts to the same issues Aurora already knows.
    """
    import uuid as _uuid

    status = _load_daemon_status()
    if not status:
        _log("[gpt_research] Cannot read daemon_status — skipping", quiet)
        return []

    anomalies = _collect_research_anomalies(status, existing_proposals)
    if not anomalies:
        _log("[gpt_research] No unresolved anomalies above threshold — skipping", quiet)
        return []

    _log(f"[gpt_research] Querying Poedex/GPT for {len(anomalies)} anomaly(s)", quiet)
    new_proposals: List[Dict[str, Any]] = []

    for anomaly in anomalies:
        dim = str(anomaly.get("dim", "unknown") or "unknown")
        atype = str(anomaly.get("type", "") or "")
        sev = float(anomaly.get("severity", 0.5) or 0.5)
        keywords = _issue_keywords(dim, atype)

        is_semantic = (
            atype in _SEMANTIC_ANOMALY_TYPES
            or any(sd in dim for sd in _SEMANTIC_DIMS)
        )

        rel_files: List[str] = []
        for key in _DIM_TO_FILES:
            if key in dim:
                rel_files.extend(_DIM_TO_FILES[key])
        if not rel_files:
            rel_files = ["aurora_internal/aurora_runtime_constraint_governor.py"] if is_semantic else ["aurora_daemon.py"]
        seen_files = set()
        rel_files = [f for f in rel_files if not (f in seen_files or seen_files.add(f))]

        code_sections = []
        for rel in rel_files[:2]:
            snippet = _read_code_context(rel, keywords=keywords)
            if snippet:
                code_sections.append(f"### {rel}\n```python\n{snippet}\n```")
        code_block = "\n\n".join(code_sections)

        fixes: List[Dict[str, Any]] = []
        source_strategy = "heuristic_hypothesis"

        poedex_question = (
            "Aurora diagnostic issue. Return ONLY a valid JSON array with up to 3 targeted "
            "fix hypotheses. Each item must have file, line, proposed_action, code_hint, confidence.\n\n"
            f"issue_type: {atype}\n"
            f"issue_dim: {dim}\n"
            f"severity: {sev:.2f}\n"
            f"runtime_governor_mode: {status.get('runtime_governor_mode', '?')}\n"
            f"qao_recent_events: {status.get('qao_recent_events', 0)}\n"
            f"fail_summary: {status.get('fail_summary', [])[:4]}\n"
            f"runtime_recent_blocked: {status.get('runtime_recent_blocked', [])[:3]}\n"
            f"relevant_files: {rel_files[:2]}\n\n"
            + (f"Relevant source code:\n{code_block}\n\n" if code_block else "")
            + "Keep the fixes small and specific to Aurora's current codebase."
        )
        poedex_raw = _poedex_research_lookup(poedex_question, timeout=18.0)
        if poedex_raw:
            try:
                fixes = _coerce_fix_list(poedex_raw)
                if fixes:
                    source_strategy = "poedex_hypothesis"
            except Exception:
                fixes = []

        if not fixes:
            if not _load_api_key():
                gpt_raw = ""
            else:
                if is_semantic:
                    system_msg = (
                        "You are a constraint-system advisor for an AI called Aurora. "
                        "When asked about a pressure imbalance or behavioral anomaly, you write "
                        "small targeted pseudocode fixes using her exact variable names. "
                        "If a Poedex clue is provided, incorporate it but keep the fix minimal."
                    )
                    user_msg = (
                        f"{_AURORA_AXIS_PRIMER}\n---\n"
                        f"CURRENT RUNTIME STATE:\n"
                        f"  anomaly_type     : {atype}\n"
                        f"  affected_dim     : {dim}\n"
                        f"  severity         : {sev:.2f}\n"
                        f"  governor_mode    : {status.get('runtime_governor_mode', '?')}\n"
                        f"  live_axis_budgets: {status.get('runtime_governor_axes', {})}\n"
                        f"  fail_summary     : {status.get('fail_summary', [])[:4]}\n"
                        f"  qao_recent_events: {status.get('qao_recent_events', 0)}\n"
                        + (f"\nPoedex clue:\n{poedex_raw}\n" if poedex_raw else "")
                        + (f"\nRelevant source code:\n{code_block}\n" if code_block else "")
                        + "\nReturn ONLY a valid JSON array. Each entry must have file, line, proposed_action, code_hint, confidence."
                    )
                else:
                    system_msg = (
                        "You are a senior Python debugging assistant. Propose concrete, minimal "
                        "code fixes for Aurora's runtime anomaly. If a Poedex clue is provided, "
                        "use it to target the smallest useful change."
                    )
                    user_msg = (
                        f"Aurora has a persistent runtime anomaly:\n"
                        f"  type     : {atype}\n"
                        f"  dimension: {dim}\n"
                        f"  severity : {sev:.2f}\n"
                        f"  governor_mode: {status.get('runtime_governor_mode', '?')}\n"
                        + (f"\nPoedex clue:\n{poedex_raw}\n" if poedex_raw else "")
                        + (f"\nRelevant source code:\n{code_block}\n" if code_block else "")
                        + "\nReturn ONLY a valid JSON array. Each fix must have file, line, proposed_action, code_hint, confidence."
                    )
                gpt_raw = _chat_completion(system_msg, user_msg, max_tokens=1200)
            if gpt_raw:
                try:
                    fixes = _coerce_fix_list(gpt_raw)
                    if fixes:
                        source_strategy = "gpt_hypothesis"
                except Exception:
                    fixes = []

        if not fixes:
            file_val = rel_files[0]
            line_val = _guess_target_line(file_val, keywords)
            hint = poedex_raw.strip() if poedex_raw else (
                f"Inspect the control path for {dim} and add a small targeted fix or guard in {file_val}. "
                f"Use the current fail summary and recurring QAO signals as the trigger condition."
            )
            fixes = [{
                "file": file_val,
                "line": line_val,
                "proposed_action": f"Inspect {dim} handling and add the smallest targeted repair path for this recurring anomaly.",
                "code_hint": hint,
                "confidence": 0.68 if poedex_raw else 0.55,
            }]
            source_strategy = "poedex_clue" if poedex_raw else "heuristic_hypothesis"

        for fix in fixes:
            file_val = _normalize_file_path(str(fix.get("file", rel_files[0]) or rel_files[0]), rel_files)
            line_guess = _guess_target_line(file_val, keywords)
            line_val = int(fix.get("line", line_guess) or line_guess)
            action = str(fix.get("proposed_action", "") or "").strip()
            hint = str(fix.get("code_hint", "") or "").strip()
            conf = float(fix.get("confidence", 0.65) or 0.65)
            if not action:
                continue
            new_proposals.append({
                "proposal_id": str(_uuid.uuid4()),
                "quasi_id": f"{source_strategy}:{dim}",
                "issue_archetype": f"{source_strategy}:{atype or dim}",
                "primary_strategy": source_strategy,
                "target": f"{file_val.replace('/', '.').removesuffix('.py')}:line_{line_val}",
                "file": file_val,
                "line": line_val,
                "match_reason": f"{source_strategy.replace('_', ' ')} for {dim} (sev={sev:.2f})",
                "proposed_action": action,
                "code_hint": hint,
                "confidence": round(max(0.55, min(0.95, conf)), 3),
                "template_id": source_strategy,
                "test_command": "",
            })

        _log(f"[gpt_research] {dim}: {len(fixes)} fix(es) proposed via {source_strategy}", quiet)

    _log(f"[gpt_research] Total new proposals: {len(new_proposals)}", quiet)
    return new_proposals


# ── main ──────────────────────────────────────────────────────────────────────

def run_sweep(quiet: bool, window_secs: int = 90, dry_run: bool = False) -> None:
    """
    Run the ParameterSweep — systematically vary governor levers, snapshot
    daemon_status.json after each window, emit proposals from observed deltas.
    """
    try:
        from quasiarch_researcher.sweep.parameter_sweep import ParameterSweep
    except ImportError as exc:
        _log(f"[sweep] ParameterSweep import failed: {exc}", quiet)
        return

    _log(f"[sweep] Initialising ParameterSweep (window={window_secs}s, dry_run={dry_run})", quiet)

    def _on_progress(msg: str) -> None:
        _log(msg, quiet)

    sweep = ParameterSweep()
    results = sweep.run(window_secs=window_secs, on_progress=_on_progress, dry_run=dry_run)

    # Merge sweep proposals into the standard diag report so the hub can display them
    all_proposals: List[Dict[str, Any]] = []
    for res in results:
        all_proposals.extend(res.proposals)

    if all_proposals:
        # Read existing report and merge
        report_path = AURORA_ROOT / "aurora_state" / "quasiarch_diag_report.json"
        existing: Dict[str, Any] = {}
        try:
            if report_path.exists():
                existing = json.loads(report_path.read_text())
        except Exception:
            pass
        merged = list(existing.get("proposals", [])) + all_proposals
        existing["proposals"] = merged
        existing["sweep_completed_at"] = time.time()
        existing["sweep_configs_run"] = len(results)
        report_path.write_text(json.dumps(existing, indent=2, default=str))
        _log(f"[sweep] {len(all_proposals)} proposals merged into diag report", quiet)

    ranked = sorted(
        [(r.score, r.label, r.config.get("notes", "")) for r in results if r.snapshot],
        reverse=True,
    )
    _log("[sweep] Results (ranked best → worst):", quiet)
    for score, label, notes in ranked[:5]:
        _log(f"  {label}: score={score:.3f}  {notes}", quiet)


def main() -> None:
    parser = argparse.ArgumentParser(description="QuasiArch diagnostic scan — zero cost to Aurora")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output, log only")
    parser.add_argument("--learn", action="store_true",
                        help="Feed recent enforcer verdicts to Researcher (ClaudeTrainer)")
    parser.add_argument("--sweep", action="store_true",
                        help="Run parameter sweep: vary governor levers, record system response")
    parser.add_argument("--sweep-window", type=int, default=90, metavar="SECS",
                        help="Seconds per sweep window (default: 90)")
    parser.add_argument("--sweep-dry-run", action="store_true",
                        help="Dry run sweep: write configs but skip sleep, just snapshot current state")
    args = parser.parse_args()

    if args.learn:
        _log("QuasiArch learn run started", args.quiet)
        run_learn(args.quiet)
        _log("QuasiArch learn run complete", args.quiet)
        return

    if args.sweep:
        _log("QuasiArch parameter sweep started", args.quiet)
        run_sweep(args.quiet, window_secs=args.sweep_window, dry_run=args.sweep_dry_run)
        _log("QuasiArch parameter sweep complete", args.quiet)
        return

    _log("QuasiArch diagnostic started", args.quiet)
    t0 = time.time()

    export_counts  = run_export(args.quiet)
    proposals      = run_scan(args.quiet)

    # GPT research: fills gaps for anomalies doctrine doesn't cover
    gpt_proposals  = run_gpt_research(args.quiet, proposals)
    if gpt_proposals:
        proposals = proposals + gpt_proposals
        _log(f"GPT research added {len(gpt_proposals)} additional proposal(s)", args.quiet)

    write_report(proposals, export_counts)
    print_summary(proposals, args.quiet)

    elapsed = time.time() - t0
    _log(f"QuasiArch diagnostic complete in {elapsed:.1f}s. "
         f"Report: {REPORT_PATH}", args.quiet)


if __name__ == "__main__":
    main()
