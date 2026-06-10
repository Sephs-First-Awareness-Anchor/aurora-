#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _wrap_function(module: Any, name: str, trace: List[Dict[str, Any]]) -> None:
    original = getattr(module, name, None)
    if not callable(original):
        trace.append({"stage": name, "event": "missing"})
        return

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        trace.append({"stage": name, "event": "enter", "ts": time.time()})
        try:
            result = original(*args, **kwargs)
            trace.append({"stage": name, "event": "exit", "ts": time.time()})
            return result
        except Exception as exc:
            trace.append({
                "stage": name,
                "event": "error",
                "error": f"{exc.__class__.__name__}: {exc}",
                "ts": time.time(),
            })
            raise

    setattr(module, name, wrapped)


def _wrap_method(obj: Any, name: str, trace: List[Dict[str, Any]]) -> None:
    original = getattr(obj, name, None)
    if not callable(original):
        trace.append({"stage": f"gateway.{name}", "event": "missing"})
        return

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        trace.append({"stage": f"gateway.{name}", "event": "enter", "ts": time.time()})
        try:
            result = original(*args, **kwargs)
            detail: Dict[str, Any] = {}
            if name == "_validate":
                detail["verdict"] = str(getattr(result, "verdict", "") or "")
            elif name == "_synthesize":
                assembly = getattr(result, "assembly", None)
                detail["assembly"] = bool(assembly)
                detail["dominant_axis"] = str(getattr(assembly, "dominant_axis", "") or "")
            elif name == "_express":
                detail["response_len"] = len(str(getattr(result, "content", "") or ""))
            trace.append({"stage": f"gateway.{name}", "event": "exit", "ts": time.time(), **detail})
            return result
        except Exception as exc:
            trace.append({
                "stage": f"gateway.{name}",
                "event": "error",
                "error": f"{exc.__class__.__name__}: {exc}",
                "ts": time.time(),
            })
            raise

    setattr(obj, name, wrapped)


def _stage_positions(trace: List[Dict[str, Any]]) -> Dict[str, int]:
    positions: Dict[str, int] = {}
    for idx, event in enumerate(trace):
        if event.get("event") == "enter":
            positions.setdefault(str(event.get("stage")), idx)
    return positions


def _verify(trace: List[Dict[str, Any]], result: Dict[str, Any]) -> Dict[str, Any]:
    positions = _stage_positions(trace)
    errors = [
        event for event in trace
        if event.get("event") == "error" or event.get("event") == "missing"
    ]
    required = [
        "_classify_input_intent",
        "_build_comprehension_response",
        "gateway._validate",
        "gateway._synthesize",
        "gateway._express",
        "gateway._integrate",
        "_understanding_pass",
    ]
    missing = [stage for stage in required if stage not in positions]
    ordered_pairs = [
        ("_classify_input_intent", "_build_comprehension_response"),
        ("_build_comprehension_response", "gateway._validate"),
        ("gateway._validate", "gateway._synthesize"),
        ("gateway._synthesize", "gateway._express"),
        ("gateway._express", "gateway._integrate"),
    ]
    ordering_failures = [
        [left, right]
        for left, right in ordered_pairs
        if left in positions and right in positions and positions[left] >= positions[right]
    ]
    resp = result.get("resp_A")
    response_text = str(getattr(resp, "content", "") or "")
    return {
        "ok": not errors and not missing and not ordering_failures and bool(response_text),
        "missing": missing,
        "ordering_failures": ordering_failures,
        "errors": errors,
        "response_source": str(getattr(resp, "src", "") or ""),
        "response_tone": str(getattr(resp, "emotional_tone", "") or ""),
        "response_confidence": float(getattr(resp, "confidence", 0.0) or 0.0),
        "response_len": len(response_text),
        "result_error": str(result.get("error", "") or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace Aurora's live external response route.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Aurora, describe what your response pipeline is doing right now.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable trace JSON.")
    args = parser.parse_args()

    import aurora as aurora_mod

    trace: List[Dict[str, Any]] = []
    for fn_name in (
        "_classify_input_intent",
        "_build_comprehension_response",
        "_select_tool",
        "_apply_pipeline_modulation",
        "_evolutionary_response_refinement",
        "_understanding_pass",
    ):
        _wrap_function(aurora_mod, fn_name, trace)

    systems = aurora_mod.boot_aurora(
        state_dir="aurora_state",
        verbose=False,
        use_quasiarch=False,
        runtime_profile="diagnostic",
    )
    gateway = getattr(systems.get("aurora"), "gateway", None)
    for method_name in ("_validate", "_synthesize", "_express", "_integrate"):
        _wrap_method(gateway, method_name, trace)

    trace.append({"stage": "process_external_user_turn", "event": "enter", "ts": time.time()})
    result = aurora_mod.process_external_user_turn(
        systems,
        args.prompt,
        source_label="live_pipeline_trace",
        auto_search_enabled=False,
        record_exchange=False,
        update_interactive_state=False,
        track_evolutionary_trace=True,
        run_periodic_maintenance=False,
    )
    trace.append({"stage": "process_external_user_turn", "event": "exit", "ts": time.time()})

    verdict = _verify(trace, result)
    payload = {
        "prompt": args.prompt,
        "verdict": verdict,
        "trace": trace,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"ok={verdict['ok']} src={verdict['response_source']} tone={verdict['response_tone']} len={verdict['response_len']}")
        if verdict["missing"]:
            print(f"missing={verdict['missing']}")
        if verdict["ordering_failures"]:
            print(f"ordering_failures={verdict['ordering_failures']}")
        if verdict["errors"]:
            print(f"errors={verdict['errors']}")
        for event in trace:
            if event.get("event") in {"enter", "exit", "error", "missing"}:
                detail = ""
                if "verdict" in event:
                    detail = f" verdict={event['verdict']}"
                elif "dominant_axis" in event:
                    detail = f" axis={event['dominant_axis']}"
                elif "response_len" in event:
                    detail = f" len={event['response_len']}"
                elif "error" in event:
                    detail = f" error={event['error']}"
                print(f"{event.get('event'):>7} {event.get('stage')}{detail}")
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
