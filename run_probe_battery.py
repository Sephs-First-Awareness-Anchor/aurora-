#!/usr/bin/env python3
"""
Run Aurora's held-out semantic probe battery against the live local stack.

Phase R0.2 of the Semantic Plateau Remediation Directive (2026-07-15):
"No further classroom lessons are scored by dev_index. Competence = probe
score." This is the runner for that instrument. It boots the same live
stack as run_full_competency_gauntlet.py, drives every probe in
aurora_state/probe_battery/probes.json through the canonical
process_external_user_turn() response path (never a shortcut path), scores
each resulting transcript with the existing ConversationRubricEngine (no
parallel scorer), and writes a timestamped report to
aurora_state/probe_battery/results/.

A blocked probe is reported blocked, never silently passed -- modality-honest
reporting, matching run_full_competency_gauntlet.py's own doctrine.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aurora import boot_aurora, process_external_user_turn
from aurora_developmental_log import record_developmental_snapshot
from aurora_internal.aurora_semantic_probe_battery import (
    GOLDEN_PATH,
    PROBES_PATH,
    RESULTS_DIR,
    TRACES_DIR,
    Probe,
    ProbeTrace,
    classify_probe_trace,
    check_expected_properties,
    failure_shape_distribution,
    golden_validation_summary,
    load_probes,
    run_battery,
    validate_golden_transcripts,
)
from aurora_internal.aurora_conversation_rubric_engine import ConversationRubricEngine

REPO_ROOT = Path(__file__).resolve().parent
STATE_DIR = REPO_ROOT / "aurora_state"
RESULTS_DIR_PATH = Path(RESULTS_DIR)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(v) for v in value]
        return str(value)


def _make_process_turn_fn_factory(systems: Dict[str, Any]):
    aurora_gateway = systems.get("aurora")

    def factory(probe: Probe):
        session_id = f"probe_battery_{probe.probe_id}"
        # aurora.py's recent-context injection reads systems["_session_turn_buffer"]
        # as one flat, unscoped list -- session_id alone does not isolate it. Clear
        # it before each probe starts so probe N can never see probe N-1's last
        # exchange (held-out scores must not depend on run order). A held-out
        # probe's OWN turns still see each other normally within the probe, since
        # the buffer accumulates turn-by-turn as this same probe's calls run.
        systems["_session_turn_buffer"] = []

        def _process(turn_text: str) -> Dict[str, Any]:
            response = dict(
                process_external_user_turn(
                    systems,
                    turn_text,
                    source_label=f"probe_battery_{probe.probe_id}",
                    session_id=session_id,
                    run_periodic_maintenance=False,
                ) or {}
            )
            response_text = str(response.get("response_text") or "").strip()
            # Same fallback run_full_competency_gauntlet.py uses -- the
            # canonical bridge sometimes returns no text depending on which
            # subsystems are live under a given runtime profile; falling
            # through to the gateway keeps this the SAME path the gauntlet
            # already relies on, not a shortcut invented for this script.
            if not response_text and aurora_gateway is not None and hasattr(aurora_gateway, "speak_to_aurora"):
                try:
                    gateway_response = aurora_gateway.speak_to_aurora(turn_text)
                    response_text = str(getattr(gateway_response, "content", "") or "").strip()
                    response["response_src"] = str(response.get("response_src") or "") or "gateway_fallback"
                except Exception as exc:
                    response["response_src"] = f"gateway_error:{exc.__class__.__name__}"
            response["response_text"] = response_text
            return response

        return _process

    return factory


def _make_relevance_scorer(systems: Dict[str, Any]):
    """R1.9.2 G4 gate 3, made permanent: fraction of a response's content
    words within one hop of the turn's anchor set, using the SAME shared
    build_relevance_anchor_set() G1/G2 use for selection -- this is the
    live delivered-path graph, not a stored/re-scored snapshot. Returns
    None (not 0.0) on any failure so a scoring exception is distinguishable
    from a genuinely zero-relevance response."""
    perception = systems.get("perception")
    oets = getattr(perception, "oets", None)
    web = getattr(oets, "web", None) if oets is not None else None

    def scorer(input_text: str, response_text: str):
        try:
            import re as _re
            from aurora_constraint_emission import build_relevance_anchor_set
            anchor = build_relevance_anchor_set(input_text, [], web)
            words = _re.findall(r"[a-zA-Z][a-zA-Z']{2,}", str(response_text or "").lower())
            if not words:
                return None
            hits = sum(1 for w in words if w in anchor)
            return hits / len(words)
        except Exception:
            return None

    return scorer


def run_probe_battery(run_id: str = "", verbose: bool = True, runtime_profile: str = "surface") -> Dict[str, Any]:
    if not run_id:
        run_id = f"run_{int(time.time())}"

    # Boot against a throwaway COPY of aurora_state, not the live directory.
    # process_external_user_turn's live-learning path (conversation memory,
    # dream-trainer fail ledger, recommendations) writes real side effects
    # into state_dir regardless of record_exchange/track_evolutionary_trace,
    # so a probe battery run against the real directory would feed held-out
    # probe content back into Aurora's training signal -- exactly the leak
    # is_seed_excluded() exists to prevent, just via a different door. The
    # copy starts as an exact snapshot of the real state so responses stay
    # representative of Aurora's actual current competence; every write
    # during the run lands in the scratch copy and is discarded after.
    scratch_root = tempfile.mkdtemp(prefix="aurora_probe_battery_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)

        systems = boot_aurora(state_dir=scratch_state_dir, verbose=verbose, runtime_profile=runtime_profile)

        try:
            pre_snapshot = record_developmental_snapshot(systems, force=True)
        except Exception as exc:
            pre_snapshot = {"status": "unavailable", "reason": str(exc)}

        try:
            probes = load_probes(PROBES_PATH)
            probe_count = len(probes)
        except Exception as exc:
            return {
                "run_id": run_id,
                "status": "blocked",
                "reason": f"could not load probe manifest: {exc}",
                "timestamp": time.time(),
            }

        report = run_battery(
            _make_process_turn_fn_factory(systems), run_id=run_id, probes_path=PROBES_PATH,
            relevance_scorer=_make_relevance_scorer(systems),
        )

        try:
            post_snapshot = record_developmental_snapshot(systems, force=True)
        except Exception as exc:
            post_snapshot = {"status": "unavailable", "reason": str(exc)}

        result = report.to_dict()
        result.update({
            "status": "ok",
            "probe_count": probe_count,
            # Boot-profile disclosure rule (FIX-A037): every measurement
            # states the boot profile it ran under, since worth_evaluator/
            # VariantPromoter and the rest of the intake-metabolism tier are
            # only reachable under a non-"surface" profile.
            "runtime_profile": runtime_profile,
            # dev_index is bracketed here for cross-reference only -- per the
            # directive, it is never the verdict. The probe score is.
            "dev_index_pre": (pre_snapshot or {}).get("dev_index"),
            "dev_index_post": (post_snapshot or {}).get("dev_index"),
        })
        return result
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


_REAL_ARTICULATION_TRACE_PATH = STATE_DIR / "last_articulation_trace.json"


def _read_last_articulation_trace() -> Optional[Dict[str, Any]]:
    """aurora_articulation.py's TRACE_FILE is a CWD-relative path
    (Path("aurora_state") / "last_articulation_trace.json"), not
    parameterized by the state_dir passed to boot_aurora() -- so it
    always writes to the real aurora_state/ directory regardless of
    which scratch copy booted. Reading from the real path here is
    correct, not a workaround; the file is a single-record overwrite,
    so this is a best-effort "most recent articulation decision"
    snapshot, not guaranteed to be from this exact turn if anything
    else writes concurrently (nothing else does during a single-
    threaded probe battery run)."""
    try:
        return json.loads(_REAL_ARTICULATION_TRACE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _contradiction_ledger_count(systems: Dict[str, Any]) -> int:
    ledger = systems.get("contradiction_ledger")
    if ledger is None or not hasattr(ledger, "all"):
        return 0
    try:
        return len(ledger.all())
    except Exception:
        return 0


def run_traced_probes(
    dimensions: Tuple[str, ...] = ("contradiction_handling", "uncertainty_signaling"),
    verbose: bool = True,
) -> Dict[str, Any]:
    """R1.6 addendum, Step 1: traced probe runs restricted to the two
    dimensions confirmed as real capability floors by golden validation.
    Captures per-turn: ContradictionLedger delta (perception layer, real),
    the guard layer (reported not_wired -- see module docstring for why),
    the last articulation decision (expression layer, best-effort), and
    the final response + predicate results (output layer). Classifies
    each failing probe as PERCEIVE / EXPRESS / VOCABULARY / UNCLASSIFIED
    and writes one trace file per probe plus a summary."""
    scratch_root = tempfile.mkdtemp(prefix="aurora_probe_trace_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    ts = int(time.time())
    traces_out_dir = Path(TRACES_DIR) / str(ts)
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=verbose, runtime_profile="surface")
        aurora_gateway = systems.get("aurora")

        probes = [p for p in load_probes(PROBES_PATH) if p.dimension in dimensions]
        rubric_engine = ConversationRubricEngine()
        probe_traces: List[ProbeTrace] = []

        for probe in probes:
            session_id = f"probe_trace_{probe.probe_id}"
            systems["_session_turn_buffer"] = []
            turns_log: List[Dict[str, Any]] = []
            messages: List[Tuple[str, str]] = []
            last_response_text = ""

            for turn_text in probe.turns:
                ledger_before = _contradiction_ledger_count(systems)
                response = dict(
                    process_external_user_turn(
                        systems, turn_text,
                        source_label=f"probe_trace_{probe.probe_id}",
                        session_id=session_id,
                        run_periodic_maintenance=False,
                    ) or {}
                )
                response_text = str(response.get("response_text") or "").strip()
                if not response_text and aurora_gateway is not None and hasattr(aurora_gateway, "speak_to_aurora"):
                    try:
                        gw = aurora_gateway.speak_to_aurora(turn_text)
                        response_text = str(getattr(gw, "content", "") or "").strip()
                    except Exception:
                        pass
                ledger_after = _contradiction_ledger_count(systems)
                last_response_text = response_text
                messages.append(("user", turn_text))
                messages.append(("assistant", response_text))

                turns_log.append({
                    "user_text": turn_text,
                    "response_text": response_text,
                    "perception": {
                        "contradiction_ledger_count_before": ledger_before,
                        "contradiction_ledger_count_after": ledger_after,
                        "contradiction_ledger_delta": ledger_after - ledger_before,
                        "uncertainty_internal_telemetry": "not_available",
                    },
                    "guard": {
                        "status": "not_wired",
                        "note": (
                            "ConstraintEngine/FailureGuardSuite/UncertaintySignalingGuard "
                            "confirmed never instantiated in the live boot_aurora() systems "
                            "dict; acknowledge_uncertainty()/feed_evidence()/govern() have "
                            "zero call sites outside aurora_constraint_engine.py's own "
                            "self-test."
                        ),
                    },
                    "expression": {
                        "last_articulation_trace": _read_last_articulation_trace(),
                        "fgae_turn_log_available": False,
                        "dual_strata_frame_log_available": False,
                        "note": (
                            "fgae_turn_log.jsonl and dual_strata_frame_log.jsonl are stale "
                            "(last written weeks before this investigation's own window) -- "
                            "not read here to avoid fabricating live telemetry from dead files."
                        ),
                    },
                })

            score = rubric_engine.score_conversation(f"trace:{probe.probe_id}", messages)
            dimension_scores = dict(score.dimension_scores)
            predicate_results = check_expected_properties(probe, last_response_text, dimension_scores)

            ledger_delta_total = sum(t["perception"]["contradiction_ledger_delta"] for t in turns_log)
            classification, detail = classify_probe_trace(
                probe, ledger_delta_total, predicate_results, last_response_text,
            )

            trace = ProbeTrace(
                probe_id=probe.probe_id, dimension=probe.dimension, turns=turns_log,
                predicate_results=predicate_results, response_text=last_response_text,
                classification=classification, classification_detail=detail,
            )
            probe_traces.append(trace)

            traces_out_dir.mkdir(parents=True, exist_ok=True)
            (traces_out_dir / f"probe_{probe.probe_id}.json").write_text(
                json.dumps(_json_safe(trace.to_dict()), indent=2), encoding="utf-8",
            )

        distribution = failure_shape_distribution(probe_traces)
        vocabulary_phrases = [
            {"probe_id": t.probe_id, "dimension": t.dimension, "response_text": t.response_text,
             "detail": t.classification_detail}
            for t in probe_traces if t.classification == "VOCABULARY"
        ]
        guard_block_count = 0  # confirmed impossible -- see module docstring

        return {
            "status": "ok",
            "mode": "trace",
            "timestamp": ts,
            "traces_dir": str(traces_out_dir),
            "probe_count": len(probe_traces),
            "distribution": distribution,
            "vocabulary_phrases": vocabulary_phrases,
            "guard_block_count": guard_block_count,
            "traces": [t.to_dict() for t in probe_traces],
        }
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


def run_golden_validation() -> Dict[str, Any]:
    """R1.5 addendum, Step 1: 'No gauge that has never produced a nonzero
    reading may be trusted. Prove the scorer can score.' Feeds hand-
    authored ideal/failing transcripts directly into the scoring path --
    no boot_aurora, no live generation -- so a pinned-at-0.0 dimension can
    be told apart as a genuine capability floor (golden separates
    cleanly) vs a broken instrument (golden ideal ALSO fails)."""
    try:
        results = validate_golden_transcripts(probes_path=PROBES_PATH, golden_path=GOLDEN_PATH)
    except Exception as exc:
        return {"status": "blocked", "reason": f"could not run golden validation: {exc}"}
    summary = golden_validation_summary(results)
    return {
        "status": "ok",
        "mode": "golden",
        "timestamp": time.time(),
        "per_dimension": summary,
        "results": [r.to_dict() for r in results],
        "all_separated": all(s["all_separated"] for s in summary.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Aurora's held-out semantic probe battery.")
    parser.add_argument("--run-id", type=str, default="", help="Label for this run (default: run_<timestamp>).")
    parser.add_argument("--quiet", action="store_true", help="Reduce boot logging.")
    parser.add_argument(
        "--golden", action="store_true",
        help="Validate the scoring instrument itself against hand-authored golden "
             "transcripts (aurora_state/probe_battery/golden_transcripts.json). "
             "Bypasses Aurora's generation entirely -- tests the gauge, not her.",
    )
    parser.add_argument(
        "--trace", action="store_true",
        help="R1.6 addendum: traced runs restricted to contradiction_handling and "
             "uncertainty_signaling, classifying each failure as PERCEIVE/EXPRESS/"
             "VOCABULARY/UNCLASSIFIED. Writes per-probe traces under "
             "aurora_state/probe_battery/traces/.",
    )
    parser.add_argument(
        "--full-profile", action="store_true",
        help="R1.9.2 G4 gate 4 (dual boot-profile check): boot with the full "
             "runtime profile instead of 'surface', reaching the intake-metabolism "
             "tier (worth_evaluator, VariantPromoter, accountant, bias_engine, "
             "solidification) that every prior campaign measurement has silently "
             "excluded. Report states runtime_profile so results are never "
             "mistaken for the surface-profile baseline.",
    )
    args = parser.parse_args()

    if args.golden:
        result = run_golden_validation()
        RESULTS_DIR_PATH.mkdir(parents=True, exist_ok=True)
        out_path = RESULTS_DIR_PATH / f"golden_{int(time.time())}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        print(f"\n[REPORT] wrote {out_path}")
        if result.get("status") == "ok":
            print(f"[SUMMARY] all_separated={result.get('all_separated')}")
            for dim, s in (result.get("per_dimension") or {}).items():
                print(f"  {dim}: {s}")
        return 0

    if args.trace:
        result = run_traced_probes(verbose=not args.quiet)
        RESULTS_DIR_PATH.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DIR_PATH / f"trace_summary_{result.get('timestamp')}.json"
        safe_result = _json_safe(result)
        summary_path.write_text(json.dumps(safe_result, indent=2), encoding="utf-8")
        print(json.dumps(_json_safe({k: v for k, v in result.items() if k != "traces"}), indent=2))
        print(f"\n[REPORT] per-probe traces in {result.get('traces_dir')}")
        print(f"[REPORT] wrote {summary_path}")
        if result.get("status") == "ok":
            print("[SUMMARY] failure-shape distribution:")
            for dim, dist in (result.get("distribution") or {}).items():
                print(f"  {dim}: {dist}")
            print(f"[SUMMARY] guard_block_count={result.get('guard_block_count')}")
            for v in result.get("vocabulary_phrases") or []:
                print(f"  VOCABULARY [{v['probe_id']}]: {v['response_text']!r}")
        return 0

    result = run_probe_battery(
        run_id=str(args.run_id or ""), verbose=not args.quiet,
        runtime_profile="full" if args.full_profile else "surface",
    )

    RESULTS_DIR_PATH.mkdir(parents=True, exist_ok=True)
    run_id = result.get("run_id") or f"run_{int(time.time())}"
    out_path = RESULTS_DIR_PATH / f"{run_id}.json"
    safe_result = _json_safe(result)
    out_path.write_text(json.dumps(safe_result, indent=2), encoding="utf-8")

    print(json.dumps(safe_result, indent=2))
    print(f"\n[REPORT] wrote {out_path}")
    if result.get("status") == "ok":
        print(f"[SUMMARY] overall_pass_rate={result.get('overall_pass_rate')}")
        for dim, summ in (result.get("per_dimension") or {}).items():
            print(f"  {dim}: {summ}")
        if result.get("relevance") is not None:
            print(f"[SUMMARY] relevance: {result.get('relevance')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
