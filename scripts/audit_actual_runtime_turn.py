#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _short(value: Any, limit: int = 500) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = value
    elif isinstance(value, dict):
        text = {
            str(k): _short(v, 120)
            for k, v in list(value.items())[:12]
        }
    elif isinstance(value, (list, tuple)):
        text = [_short(v, 120) for v in list(value)[:8]]
    else:
        text = repr(value)
    if isinstance(text, str) and len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


class TracedSystems(dict):
    def __init__(self, initial: Dict[str, Any], events: List[Dict[str, Any]]):
        super().__init__(initial)
        self._events = events

    def __setitem__(self, key: str, value: Any) -> None:
        existed = key in self
        old = self.get(key)
        super().__setitem__(key, value)
        self._events.append({
            "kind": "systems_write",
            "key": str(key),
            "status": "OVERWRITTEN" if existed else "EXECUTED",
            "old": _short(old, 180),
            "new": _short(value, 300),
            "ts": time.time(),
        })

    def setdefault(self, key: str, default: Any = None) -> Any:
        existed = key in self
        result = super().setdefault(key, default)
        if not existed:
            self._events.append({
                "kind": "systems_write",
                "key": str(key),
                "status": "EXECUTED",
                "old": None,
                "new": _short(default, 300),
                "ts": time.time(),
            })
        return result

    def pop(self, key: str, default: Any = None) -> Any:
        existed = key in self
        result = super().pop(key, default)
        if existed:
            self._events.append({
                "kind": "systems_write",
                "key": str(key),
                "status": "OVERWRITTEN",
                "old": _short(result, 180),
                "new": "<deleted>",
                "ts": time.time(),
            })
        return result


def _wrap_function(module: Any, name: str, events: List[Dict[str, Any]]) -> None:
    original = getattr(module, name, None)
    if not callable(original):
        events.append({"kind": "function", "name": name, "status": "SKIPPED", "reason": "missing"})
        return

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        events.append({"kind": "function", "name": name, "event": "enter", "status": "EXECUTED", "ts": time.time()})
        try:
            result = original(*args, **kwargs)
            detail: Dict[str, Any] = {}
            if name == "_classify_input_intent":
                detail["return"] = _short(result)
            elif name == "_build_comprehension_response":
                detail["return"] = _short(result)
            elif name == "_select_tool":
                detail["return"] = _short(result)
            elif name == "_apply_pipeline_modulation":
                detail["return"] = _short(result)
            elif name == "_evolutionary_response_refinement":
                detail["return"] = _short(result)
            elif name == "_understanding_pass":
                detail["return"] = None
            events.append({"kind": "function", "name": name, "event": "exit", "status": "EXECUTED", "ts": time.time(), **detail})
            return result
        except Exception as exc:
            events.append({
                "kind": "function",
                "name": name,
                "event": "error",
                "status": "EMPTY",
                "error": f"{exc.__class__.__name__}: {exc}",
                "ts": time.time(),
            })
            raise

    setattr(module, name, wrapped)


def _wrap_method(obj: Any, label: str, name: str, events: List[Dict[str, Any]]) -> None:
    original = getattr(obj, name, None)
    stage = f"{label}.{name}"
    if not callable(original):
        events.append({"kind": "function", "name": stage, "status": "SKIPPED", "reason": "missing"})
        return

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        events.append({"kind": "function", "name": stage, "event": "enter", "status": "EXECUTED", "ts": time.time()})
        try:
            result = original(*args, **kwargs)
            detail: Dict[str, Any] = {"return": _short(result, 400)}
            if name == "integrate" and hasattr(result, "to_dict"):
                detail["return"] = result.to_dict()
            elif name == "_validate":
                detail["verdict"] = str(getattr(result, "verdict", "") or "")
            elif name == "_synthesize":
                assembly = getattr(result, "assembly", None)
                detail["assembly"] = {
                    "present": bool(assembly),
                    "dominant_axis": str(getattr(assembly, "dominant_axis", "") or ""),
                    "quality": _short(getattr(assembly, "quality", None)),
                    "conscious_frame_keys": sorted(list(dict(getattr(assembly, "conscious_frame", {}) or {}).keys())),
                }
            elif name == "_express":
                detail["response"] = {
                    "content": _short(getattr(result, "content", ""), 500),
                    "tone": _short(getattr(result, "emotional_tone", "")),
                    "confidence": _short(getattr(result, "confidence", "")),
                }
            events.append({"kind": "function", "name": stage, "event": "exit", "status": "EXECUTED", "ts": time.time(), **detail})
            return result
        except Exception as exc:
            events.append({
                "kind": "function",
                "name": stage,
                "event": "error",
                "status": "EMPTY",
                "error": f"{exc.__class__.__name__}: {exc}",
                "ts": time.time(),
            })
            raise

    setattr(obj, name, wrapped)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default="Aurora, what are you feeling about your response pipeline right now?")
    parser.add_argument("--out", default="/tmp/aurora_actual_runtime_turn_trace.json")
    parser.add_argument("--full-profile", action="store_true", help="Capture every Python call/return in the main runtime files.")
    args = parser.parse_args()

    import aurora as aurora_mod
    import aurora_thought_formation as thought_mod
    import aurora_self_grounding as grounding_mod

    events: List[Dict[str, Any]] = []
    call_depth = {"value": 0}
    profile_files = {
        "aurora.py",
        "aurora_thought_formation.py",
        "aurora_self_grounding.py",
        "aurora_governance_persistence_gateway.py",
        "aurora_expression_perception.py",
        "aurora_internal/aurora_language_state.py",
        "aurora_internal/dual_strata/dce_bridge.py",
        "aurora_internal/dual_strata/subsurface_projection.py",
    }

    def _profile(frame: Any, event: str, arg: Any) -> None:
        if event not in {"call", "return", "exception"}:
            return
        try:
            path = Path(frame.f_code.co_filename).resolve()
            rel = path.relative_to(ROOT).as_posix()
        except Exception:
            return
        if rel not in profile_files:
            return
        if len(events) > 30000:
            return
        if event == "call":
            call_depth["value"] += 1
            events.append({
                "kind": "py_call",
                "event": "enter",
                "status": "EXECUTED",
                "name": f"{rel}:{frame.f_code.co_name}",
                "line": frame.f_lineno,
                "depth": call_depth["value"],
                "ts": time.time(),
            })
        elif event == "return":
            events.append({
                "kind": "py_call",
                "event": "return",
                "status": "EXECUTED",
                "name": f"{rel}:{frame.f_code.co_name}",
                "line": frame.f_lineno,
                "depth": call_depth["value"],
                "return": _short(arg, 240),
                "ts": time.time(),
            })
            call_depth["value"] = max(0, call_depth["value"] - 1)
        elif event == "exception":
            events.append({
                "kind": "py_call",
                "event": "exception",
                "status": "EMPTY",
                "name": f"{rel}:{frame.f_code.co_name}",
                "line": frame.f_lineno,
                "depth": call_depth["value"],
                "error": _short(arg, 240),
                "ts": time.time(),
            })

    for fn_name in (
        "process_external_user_turn",
        "dual_question_pipeline",
        "_classify_input_intent",
        "_select_tool",
        "_extract_pipeline_signals",
        "_build_comprehension_response",
        "_apply_pipeline_modulation",
        "_evolutionary_response_refinement",
        "_understanding_pass",
        "_synthesize_pipeline_diagnostic",
    ):
        _wrap_function(aurora_mod, fn_name, events)

    _wrap_method(thought_mod.ThoughtIntegrationSpace, "ThoughtIntegrationSpace", "register", events)
    _wrap_method(thought_mod.ThoughtIntegrationSpace, "ThoughtIntegrationSpace", "integrate", events)
    _wrap_method(grounding_mod.SelfGroundingFallback, "SelfGroundingFallback", "ground", events)

    base_systems = aurora_mod.boot_aurora(
        state_dir="aurora_state",
        verbose=False,
        use_quasiarch=False,
        runtime_profile="diagnostic",
    )
    systems = TracedSystems(base_systems, events)

    gateway = getattr(systems.get("aurora"), "gateway", None)
    for method_name in ("_validate", "_synthesize", "_express", "_integrate"):
        _wrap_method(gateway, "gateway", method_name, events)

    if args.full_profile:
        sys.setprofile(_profile)
    try:
        result = aurora_mod.process_external_user_turn(
            systems,
            args.prompt,
            source_label="actual_runtime_audit",
            auto_search_enabled=False,
            record_exchange=False,
            update_interactive_state=False,
            track_evolutionary_trace=True,
            run_periodic_maintenance=False,
        )
    finally:
        if args.full_profile:
            sys.setprofile(None)
    resp_a = result.get("resp_A")
    resp_b = result.get("resp_B")
    thought_state = systems.get("_active_thought_state")

    payload = {
        "prompt": args.prompt,
        "final": {
            "resp_A": {
                "content": _short(getattr(resp_a, "content", ""), 1200),
                "src": _short(getattr(resp_a, "src", "")),
                "tone": _short(getattr(resp_a, "emotional_tone", "")),
                "confidence": _short(getattr(resp_a, "confidence", "")),
            },
            "resp_B": {
                "content": _short(getattr(resp_b, "content", ""), 1200),
                "tone": _short(getattr(resp_b, "emotional_tone", "")),
                "confidence": _short(getattr(resp_b, "confidence", "")),
            },
            "error": str(result.get("error", "") or ""),
            "last_surface_candidates": systems.get("_last_surface_candidates", []),
            "pipeline_state_grounding": {
                "latest_semantic_interpretation": _short(systems.get("_latest_semantic_interpretation", {}), 800),
                "last_self_grounding": _short(systems.get("_last_self_grounding", {}), 800),
            },
            "unified_meaning_packet": _short(systems.get("_last_unified_meaning_packet", {}), 1800),
            "internal_reasoning": _short(result.get("internal_reasoning", ""), 1200),
            "active_thought_state": thought_state.to_dict() if hasattr(thought_state, "to_dict") else _short(thought_state, 800),
        },
        "events": events,
    }
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({
        "trace_file": args.out,
        "response": payload["final"]["resp_A"],
        "thought_state": payload["final"]["active_thought_state"],
        "candidate_count": len(payload["final"]["last_surface_candidates"]),
        "event_count": len(events),
    }, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
