"""
aurora_state_context.py
========================

Build 608 (RCEC Closed-Loop Activation, D1): a minimal, single-point
fallback so the handful of hardcoded `Path(__file__)`-relative
aurora_state/ defaults scattered through the codebase (the "isolation-gap"
bug class -- see known_fixes_registry.md) resolve against the state_dir
the ACTIVE boot_aurora() call actually used, when no explicit state_dir/
systems was threaded through to them, instead of silently falling all the
way to the real repo's aurora_state/.

This does NOT replace explicit state_dir threading -- that is still the
correct fix, and is what most of the codebase already does. This module is
a safety-net LAST RESORT for the two confirmed cases where explicit
threading isn't practical as a single narrow change: AuroraEvolvedSurface
Engine's ~20 independent module-level lazy-singleton call sites (each
would need its own edit), and aurora_runtime_faults.py's swallowed-
exception handlers, which run inside arbitrary call scopes that may not
have state_dir/systems in their immediate locals().

Deliberately a bare module-level global, not a contextvars.ContextVar:
the resources this patches (background threads in particular) are spawned
across real OS threads, which do not inherit a contextvar set in the
thread that called boot_aurora(). A bare global is last-writer-wins across
concurrent boots in the same process -- a pre-existing limitation shared
by every global-singleton pattern this module patches (confirmed live:
AuroraEvolvedSurfaceEngine's own module-level cache already has this
constraint), not a new one introduced here.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

from typing import Optional

_active_state_dir: Optional[str] = None


def set_active_state_dir(state_dir: Optional[str]) -> None:
    """Called by boot_aurora() near its start. Last-writer-wins."""
    global _active_state_dir
    _active_state_dir = str(state_dir) if state_dir else None


def get_active_state_dir() -> Optional[str]:
    return _active_state_dir


def clear_active_state_dir() -> None:
    global _active_state_dir
    _active_state_dir = None
