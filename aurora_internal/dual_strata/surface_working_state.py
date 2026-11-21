"""Portable present-frame state; durable developmental stores stay at the hub.

No pickle or arbitrary class loading. Unknown owned values stop a handoff instead
of being silently omitted. Live locks and the injected contradiction ledger are
organ connections, reconnected by the destination boot rather than copied.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from aurora_internal.desktop.common import read_json, write_json

FILENAME = "surface_working_state.json"
_CONNECTIONS = {"_stated_facts_lock", "_contradiction_ledger"}
_SESSION_FIELDS = ("_interactive_turn_tick", "_session_turn_buffer", "_last_pipeline_state",
                   "_last_active_ability_ids", "surface_owned_state")


def encode(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {"$": "dict", "items": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, (list, tuple, set, deque)):
        return {"$": type(value).__name__, "items": [encode(x) for x in value],
                "maxlen": value.maxlen if isinstance(value, deque) else None}
    from aurora_internal.aurora_proposition_substrate import PropositionSubstrate
    if isinstance(value, PropositionSubstrate):
        return {"$": "proposition_substrate", "state": encode(vars(value))}
    from aurora_perception_primitives import DimensionalPattern, PatternType
    if isinstance(value, DimensionalPattern):
        return {"$": "dimensional_pattern", "state": encode(vars(value))}
    if isinstance(value, PatternType):
        return {"$": "pattern_type", "name": value.name}
    import numpy as np
    if isinstance(value, np.ndarray) and value.dtype.kind in "biuf":
        return {"$": "array", "dtype": str(value.dtype), "items": value.tolist()}
    if isinstance(value, np.generic) and value.dtype.kind in "biuf":
        return encode(value.item())
    raise TypeError(f"unsupported surface-owned state: {type(value).__name__}")


def decode(value):
    if not isinstance(value, dict):
        return value
    kind = value.get("$")
    if kind == "dict":
        return {decode(k): decode(v) for k, v in value["items"]}
    if kind in {"list", "tuple", "set", "deque"}:
        items = [decode(x) for x in value["items"]]
        if kind == "deque":
            return deque(items, maxlen=value.get("maxlen"))
        return {"list": list, "tuple": tuple, "set": set}[kind](items)
    if kind == "proposition_substrate":
        from aurora_internal.aurora_proposition_substrate import PropositionSubstrate
        obj = PropositionSubstrate()
        obj.__dict__.update(decode(value["state"]))
        return obj
    if kind == "dimensional_pattern":
        from aurora_perception_primitives import DimensionalPattern
        return DimensionalPattern(**decode(value["state"]))
    if kind == "pattern_type":
        from aurora_perception_primitives import PatternType
        return PatternType[value["name"]]
    if kind == "array":
        import numpy as np
        dtype = np.dtype(value["dtype"])
        if dtype.kind not in "biuf":
            raise ValueError("unsupported surface array dtype")
        return np.asarray(value["items"], dtype=dtype)
    raise ValueError("unknown surface-state encoding")


def capture(systems, state_dir, *, app_state=None):
    wm = systems.get("working_memory")
    if wm is None:
        raise ValueError("no working memory to transfer")
    bindings = [k for k, v in vars(wm).items() if callable(v)]
    result = {"schema": 1, "bindings": bindings,
              "working_memory": encode({k: v for k, v in vars(wm).items() if k not in _CONNECTIONS and k not in bindings}),
              "session": encode({k: systems[k] for k in _SESSION_FIELDS if k in systems}),
              "app_state": encode(app_state or {})}
    write_json(Path(state_dir) / FILENAME, result)
    return result


def restore(systems, state_dir):
    data = read_json(Path(state_dir) / FILENAME)
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("missing or unsupported portable surface checkpoint")
    # Decode the entire checkpoint first; a failure leaves the living state alone.
    wm_state, session, app = decode(data["working_memory"]), decode(data["session"]), decode(data["app_state"])
    if set(wm_state) & _CONNECTIONS:
        raise ValueError("checkpoint contains live organ connections")
    wm = systems.get("working_memory")
    if wm is None:
        raise ValueError("destination working memory is unavailable")
    bindings = set(data.get("bindings", []))
    if any(not callable(getattr(wm, name, None)) for name in bindings):
        raise ValueError("destination is missing a boot-owned working-memory binding")
    for key in list(vars(wm)):
        if key not in _CONNECTIONS and key not in bindings:
            delattr(wm, key)
    wm.__dict__.update(wm_state)
    systems.update(session)
    return app
