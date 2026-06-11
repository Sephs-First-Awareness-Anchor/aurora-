#!/usr/bin/env python3
"""
Aurora stack-wide developmental trace instrumentation.

This module wraps active runtime call surfaces so methods/functions emit
evolutionary trace records with pressure-before/after and applied effects.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Dict

from aurora_constraint_unit_adapter import build_constraint_profile


_INSTRUMENTED_IDS = set()


def _is_wrappable_callable(fn: Any) -> bool:
    if not callable(fn):
        return False
    name = getattr(fn, "__name__", "")
    if name.startswith("__") and name.endswith("__"):
        return False
    return True


def _safe_name(obj: Any) -> str:
    try:
        return str(getattr(obj, "__name__", "")) or str(type(obj).__name__)
    except Exception:
        return "unknown"


def _derive_applied_effects(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    out = {"operator_gradient_delta": {}, "heat_delta": 0.0}
    b_ops = (before or {}).get("operator_gradients", {}) or {}
    a_ops = (after or {}).get("operator_gradients", {}) or {}
    for k in sorted(set(b_ops.keys()) | set(a_ops.keys())):
        out["operator_gradient_delta"][k] = float(a_ops.get(k, 0.0) or 0.0) - float(b_ops.get(k, 0.0) or 0.0)
    try:
        hb = float(((before or {}).get("heat", {}) or {}).get("score", 0.0) or 0.0)
        ha = float(((after or {}).get("heat", {}) or {}).get("score", 0.0) or 0.0)
        out["heat_delta"] = ha - hb
    except Exception:
        out["heat_delta"] = 0.0
    return out


def _make_wrapper(
    fn: Callable[..., Any],
    qualname: str,
    systems: Dict[str, Any],
    pressure_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Callable[..., Any]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        mem = systems.get("conversation_memory")
        before = pressure_fn(systems)
        opened_here = False
        trace_id = ""

        if mem and hasattr(mem, "open_evolutionary_trace") and hasattr(mem, "close_evolutionary_trace"):
            active = getattr(mem, "_active_trace", None)
            if active and isinstance(active, dict):
                trace_id = str(active.get("trace_id", ""))
                if hasattr(mem, "_record_mutation_with_trace"):
                    mem._record_mutation_with_trace("stack_call", {"call": qualname})  # pylint: disable=protected-access
            else:
                try:
                    trace_id = mem.open_evolutionary_trace(
                        input_text=f"call:{qualname}",
                        tick=int(time.time()),
                        pressure_before=before,
                        causal_chain=[
                            "call_entry",
                            "constraint_eval",
                            "execution",
                            "state_effect",
                            "call_exit",
                        ],
                    )
                    opened_here = True
                except Exception:
                    trace_id = ""

        try:
            result = fn(*args, **kwargs)
            if mem and trace_id and hasattr(mem, "_record_mutation_with_trace"):
                mem._record_mutation_with_trace("stack_call_result", {  # pylint: disable=protected-access
                    "call": qualname,
                    "ok": True,
                })
            return result
        except Exception as exc:
            if mem and trace_id and hasattr(mem, "_record_mutation_with_trace"):
                mem._record_mutation_with_trace("stack_call_result", {  # pylint: disable=protected-access
                    "call": qualname,
                    "ok": False,
                    "error": str(exc)[:180],
                })
            raise
        finally:
            if opened_here and mem and trace_id:
                after = pressure_fn(systems)
                effects = _derive_applied_effects(before, after)
                try:
                    mem.close_evolutionary_trace(  # type: ignore[attr-defined]
                        trace_id=trace_id,
                        pressure_after=after,
                        applied_effects=effects,
                    )
                except Exception:
                    pass

    setattr(wrapped, "_aurora_trace_wrapped", True)
    return wrapped


def _wrap_instance_methods(
    obj: Any,
    systems: Dict[str, Any],
    pressure_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> int:
    count = 0
    cls = type(obj)
    # Walk MRO dicts to avoid triggering dynamic property access through dir().
    seen = set()
    for c in getattr(cls, "__mro__", (cls,)):
        cdict = getattr(c, "__dict__", {}) or {}
        for name, raw in cdict.items():
            if name in seen:
                continue
            seen.add(name)
            if name.startswith("__"):
                continue
            if isinstance(raw, property):
                continue
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            if not _is_wrappable_callable(attr):
                continue
            if getattr(attr, "_aurora_trace_wrapped", False):
                continue
            mod = str(getattr(attr, "__module__", "") or "")
            if not (mod.startswith("aurora") or mod.startswith("foundational_contract")):
                continue
            try:
                wrapped = _make_wrapper(attr, f"{type(obj).__name__}.{name}", systems, pressure_fn)
                setattr(obj, name, wrapped)
                count += 1
            except Exception:
                continue
    return count


def instrument_stack(
    systems: Dict[str, Any],
    pressure_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Instrument active stack call surfaces.
    Returns counts of wrapped components/functions.
    """
    wrapped_methods = 0
    wrapped_layer_funcs = 0

    targets = []
    target_keys = (
        "contract", "lattice", "collective", "dimensional", "consciousness",
        "perception", "sensory", "hardware", "sensory_integration",
        "vision_bootstrap", "identity", "simulation", "aurora",
        "search_adapter", "autonomy", "drive_sync", "checkpoint",
        "chamber", "genealogy",
    )
    for k in target_keys:
        v = systems.get(k)
        if v is None:
            continue
        obj_id = id(v)
        if obj_id in _INSTRUMENTED_IDS:
            continue
        targets.append((k, v))

    for key, obj in targets:
        # Skip memory object itself to avoid recursion loops.
        if key == "conversation_memory":
            continue
        try:
            wrapped_methods += _wrap_instance_methods(obj, systems, pressure_fn)
            _INSTRUMENTED_IDS.add(id(obj))
        except Exception:
            continue

    # Wrap consolidated layer function map so exported call surface is also traced.
    layer_funcs = systems.get("base_layer_functions", {}) or {}
    for layer_id, fn_map in layer_funcs.items():
        if not isinstance(fn_map, dict):
            continue
        for alias, fn in list(fn_map.items()):
            if not _is_wrappable_callable(fn):
                continue
            if getattr(fn, "_aurora_trace_wrapped", False):
                continue
            wrapped = _make_wrapper(fn, f"{layer_id}.{alias}", systems, pressure_fn)
            fn_map[alias] = wrapped
            wrapped_layer_funcs += 1

    result: Dict[str, Any] = {
        "methods": wrapped_methods,
        "layer_functions": wrapped_layer_funcs,
    }
    profile = _trace_constraint_profile(systems, wrapped_methods, wrapped_layer_funcs, pressure_fn)
    result["lineage_signature"] = profile.weighted_signature()
    result["runtime_regime"] = profile.runtime_regime()
    result["language_projection"] = profile.language_projection()
    result["universal_representation"] = {
        **profile.universal_representation(),
        "unit_state": {
            "methods": wrapped_methods,
            "layer_functions": wrapped_layer_funcs,
            "instrumented_objects": len(_INSTRUMENTED_IDS),
        },
    }

    if verbose:
        print(
            f"  [TRACE] Instrumented stack calls: methods={wrapped_methods}, "
            f"layer_functions={wrapped_layer_funcs}"
        )

    return result


def _trace_constraint_profile(
    systems: Dict[str, Any],
    wrapped_methods: int,
    wrapped_layer_funcs: int,
    pressure_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
):
    pressure = dict(pressure_fn(systems) or {})
    heat_score = float(((pressure.get("heat", {}) or {}).get("score", 0.0) or 0.0)
                       if isinstance(pressure.get("heat", {}), dict)
                       else 0.0)
    op_gradients = dict(pressure.get("operator_gradients", {}) or {})
    axes = {
        "X": min(1.0, 0.20 + wrapped_methods / 120.0),
        "T": min(1.0, 0.25 + wrapped_layer_funcs / 60.0),
        "N": min(1.0, 0.15 + heat_score),
        "B": min(1.0, 0.20 + len(op_gradients) / 20.0),
        "A": min(1.0, 0.20 + (0.25 if systems.get("conversation_memory") else 0.0)),
    }
    pressure_axes = {
        "X": min(1.0, heat_score * 0.5),
        "T": min(1.0, wrapped_layer_funcs / 80.0),
        "N": min(1.0, heat_score),
        "B": min(1.0, len(op_gradients) / 16.0),
        "A": 1.0 if getattr(systems.get("conversation_memory"), "_active_trace", None) else 0.0,
    }
    return build_constraint_profile(
        unit_id="stack_trace_instrumentation",
        unit_kind="intent_trace_instrumentation",
        operational_role="evolutionary_trace_binding",
        genealogy="XTNBAA",
        axis_weights=axes,
        pressure_axes=pressure_axes,
    )
