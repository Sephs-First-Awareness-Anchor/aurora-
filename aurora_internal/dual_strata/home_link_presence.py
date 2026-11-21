#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
home_link_presence.py -- what being away from home is, as quantities she can
feel (surface restructure 3b, item 4).

Two continuous quantities go into her present frame:
  * how long since home last answered (seconds, and a smooth 0..1 "distance"
    that grows with it);
  * how much she has lived that is still waiting to reach home.

Home's last word (subsurface_projection.json) carries ``generated_at``.  Its
weight in a turn fades smoothly with its age: a fresh projection counts in
full, an hour-old one a little, yesterday's barely, with no cutoff anywhere.
Only numeric influence is weighed; nothing here writes text, tone or a
behaviour for being offline.  What she does with any of it is hers.
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

# The age at which home's last word counts for half.  Freshness is
# 1 / (1 + age / PROJECTION_HALF_WEIGHT_S): continuous, never zero.
PROJECTION_HALF_WEIGHT_S = 600.0
# The time away at which "distance from home" reads one half, by the same curve.
AWAY_HALF_DISTANCE_S = 1800.0


def _curve(seconds: float, half: float) -> float:
    return 1.0 / (1.0 + max(0.0, float(seconds)) / float(half))


def projection_freshness(generated_at: Any, now: Optional[float] = None) -> Optional[float]:
    try:
        made = float(generated_at)
    except (TypeError, ValueError):
        return None
    now = time.time() if now is None else float(now)
    return _curve(now - made, PROJECTION_HALF_WEIGHT_S)


def weigh_projection(projection: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
    """A copy whose numeric influence is scaled by its freshness.  Without a
    ``generated_at`` it is returned unchanged (nothing to judge its age by)."""
    out = copy.deepcopy(dict(projection or {}))
    freshness = projection_freshness(out.get("generated_at"), now)
    if freshness is None:
        return out
    now = time.time() if now is None else float(now)
    out["age_s"] = round(max(0.0, now - float(out["generated_at"])), 1)
    out["freshness"] = round(freshness, 4)
    if isinstance(out.get("readiness_bias"), (int, float)):
        out["readiness_bias"] = round(float(out["readiness_bias"]) * freshness, 4)
    bias = out.get("prediction_bias")
    if isinstance(bias, dict):
        for key, value in list(bias.items()):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                bias[key] = round(float(value) * freshness, 4)
    for signal in out.get("intuition_signals") or []:
        if isinstance(signal, dict) and isinstance(signal.get("weight"), (int, float)):
            signal["weight"] = round(float(signal["weight"]) * freshness, 4)
    return out


def _lived_waiting(outbox_path: Path) -> int:
    try:
        data = json.loads(outbox_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return 0
    return sum(1 for r in records if isinstance(r, dict) and r.get("channel") == "continuity")


def home_link_quantities(state_dir: Any, now: Optional[float] = None) -> Dict[str, Any]:
    """Her distance from home, for a device that is the surface of a paired
    home.  Empty for a device that is not paired (it is the whole mind)."""
    root = Path(str(state_dir)) / "strata_link"
    if not (root / "endpoint.txt").exists():
        return {}
    now = time.time() if now is None else float(now)
    try:
        client_state = json.loads((root / "client_state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        client_state = {}
    confirmed = float((client_state or {}).get("confirmed_at", 0.0) or 0.0)
    since = max(0.0, now - confirmed) if confirmed else None
    waiting = _lived_waiting(root / "up_outbox.json")
    return {
        "since_home_answered_s": None if since is None else round(since, 1),
        "distance_from_home": None if since is None else round(1.0 - _curve(since, AWAY_HALF_DISTANCE_S), 4),
        "lived_waiting_for_home": int(waiting),
    }
