#!/usr/bin/env python3
"""
AURORA GENEALOGY CO-OCCURRENCE OBSERVATORY (Phase 3A.1)
=============================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Instruments the REAL live pair-forming call path -- not a replay of static
JSON (that was Phase 3A) -- to distinguish three architecturally different
explanations for the floor effect Phase 3A found:

  1. DIFFERENCE is genuinely not computed anywhere near pair-forming calls.
  2. DIFFERENCE IS computed elsewhere at the same tick, but the specific
     caller that forms the pair has no reference to it and so can't pass it.
  3. A DifferenceSnapshot exists and gets passed, but it's stale relative to
     the pair event -- a temporal/lifecycle mismatch, not an absence.

STILL NO BEHAVIORAL WIRING.
---------------------------------------------------------------------------
`install()` wraps `ConstraintGenealogyLogger.observe` with a sidecar that:
  (a) calls the REAL, ORIGINAL observe() FIRST, with every argument passed
      through completely unchanged, and returns its real result unmodified
      -- promotion, PairStats, and every existing side effect are identical
      to an uninstrumented call, verified by
      `test_wrapped_observe_produces_identical_result_and_side_effects`.
  (b) only AFTER that real call completes, independently records what it
      can observe -- read-only, wrapped in try/except so a sidecar failure
      can never break or alter the real call.
The recorded DifferenceSnapshot (when found) is stored ONLY in the sidecar's
own sink list; it is never passed to PairStats.update(), _try_promote(), or
back into the logger in any form. Verified,
`test_sidecar_never_feeds_difference_back_into_pairstats`.

WHAT "AVAILABLE ANYWHERE UPSTREAM" CAN AND CANNOT HONESTLY MEAN
---------------------------------------------------------------------------
`DifferenceHistoryBuffer` is instance-scoped (`self._diff_buffer` on
whichever evolution-chamber-shaped object owns one --
aurora_internal/aurora_evolution_chamber.py:1089) -- there is no global
registry this sidecar could consult to answer "is DIFFERENCE available
ANYWHERE in the live process right now" in general. What it CAN honestly
do: read the direct `difference_snapshot` argument (always exactly knowable
-- this alone distinguishes possibility 3 from 1/2, via `.tick` vs the
pair's own tick), and, when that argument is None, use read-only stack-
frame introspection (`inspect`, never `sys.settrace`, never mutates
anything) to check whether the CALLER's own `self` holds a
`DifferenceHistoryBuffer` or `DifferenceSnapshot` instance attribute it
simply didn't pass -- this distinguishes possibility 2 (found, unreachable
only because it wasn't threaded through) from possibility 1 (not found on
the caller at all, from this specific call site). It cannot rule out that
some OTHER, unrelated object elsewhere in the process happens to hold one;
it reports what it can verify from the actual call, not a claim about the
whole system. When a buffer is found this way, only its most recently
RECORDED tick is read (`buffer._history[-1]`, a read-only peek at an
already-populated ring buffer entry) -- computing a fresh DifferenceSnapshot
would require calling `.snapshot(tick, magnitudes)` with live magnitudes
this sidecar has no legitimate way to obtain without guessing, so it
doesn't; `difference_values` is left `None` in that case, honestly, rather
than fabricated.

CONFIRMED, REAL CALL SITES THIS WAS RUN AGAINST (not merely inspected):
---------------------------------------------------------------------------
- `aurora_grammar_engine.py`'s `GrammarEngine._log_relief_to_genealogy()`
  (hardcodes `difference_snapshot=None`, constant.py:1563) -- a real,
  organic, multi-item-trace, pair-forming caller, exercised directly
  (`GrammarEngine()` is cheap to construct -- no heavy boot).
- A direct, real `DifferenceHistoryBuffer`/`DifferenceSnapshot` pairing
  (`aurora_internal/aurora_difference_buffer.py`), used the exact same way
  `aurora_evolution_chamber.py:1402` uses it (`_diff_buffer.snapshot(tick,
  magnitudes)`), to exercise the case where a caller genuinely does pass a
  real snapshot -- without needing to construct the full, heavier
  `EvolutionChamber` class, which is not required to exercise this exact
  code path honestly.

Results and full interpretation: docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md
section 12.

NOTE ON A SIDE EFFECT DISCOVERED WHILE BUILDING THIS (not this module's
doing, and not fixable from here): exercising real observe() calls that
reach real promotion-gate rejections triggers
`PressureExperienceLedger.get()` (aurora_internal/aurora_pressure_ledger.py:114)
-- a process-wide singleton with a hardcoded file path -- regardless of
which (throwaway) ConstraintGenealogyLogger triggered it. A wrapped or
unwrapped `observe()` call are identical here too (this sidecar changes
nothing about it), but it means even a fully isolated, temp-directory
logger instance cannot avoid touching that one real, shared file if a
promotion gate actually rejects something. Tests in this repo that exercise
real observe() calls guard this with an autouse fixture that snapshots and
restores that file (tests/test_genealogy_cooccurrence_observatory.py);
scripts run standalone do not, and say so in their own docstrings.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

AXES = ("X", "T", "N", "B", "A")


@dataclass
class CooccurrenceObservation:
    tick: int
    pair_eligible: bool
    trace_length: int
    pair_keys: List[Tuple[str, str]] = field(default_factory=list)
    relief: Dict[str, float] = field(default_factory=dict)
    cost: Dict[str, float] = field(default_factory=dict)
    x_risk: float = 0.0

    difference_passed: bool = False
    difference_source: Optional[str] = None       # "argument" | "caller_frame:<Class>.<attr>" | None
    difference_tick: Optional[int] = None
    difference_values: Optional[Dict[str, float]] = None
    difference_age_ticks: Optional[int] = None
    difference_unavailable_reason: Optional[str] = None

    caller_qualname: Optional[str] = None
    caller_class: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def _resolve_effective_trace(logger: Any, trace: List[Any]) -> List[Any]:
    """Mirror the same trace-rewrite step _accumulate_pairs() applies before
    pairing (constraint_genealogy.py:5381-5384), read-only (rewrite_trace()
    returns a new list, does not mutate logger state)."""
    try:
        if getattr(logger.cfg, "TRACE_REWRITE_ON_PROMOTE", False) and getattr(logger, "_links_by_parents", None):
            rewritten = logger.rewrite_trace(trace)
            if rewritten:
                return rewritten
    except Exception:
        pass
    return trace


def _find_upstream_difference_buffer(frame) -> Tuple[Optional[Any], Optional[str]]:
    """Best-effort, read-only introspection of the caller's frame for a
    reachable DifferenceHistoryBuffer/DifferenceSnapshot the caller holds
    but did not pass. Never raises; never mutates anything it finds."""
    try:
        from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer, DifferenceSnapshot

        if frame is None:
            return None, None
        local_self = frame.f_locals.get("self")
        if local_self is None:
            return None, None
        for attr_name, attr_val in vars(local_self).items():
            if isinstance(attr_val, (DifferenceHistoryBuffer, DifferenceSnapshot)):
                return attr_val, f"{type(local_self).__name__}.{attr_name}"
    except Exception:
        pass
    return None, None


def _classify_difference_state(
    logger: Any,
    difference_snapshot: Optional[Any],
    caller_frame,
) -> Tuple[bool, Optional[str], Optional[int], Optional[Dict[str, float]], Optional[int], Optional[str]]:
    if difference_snapshot is not None:
        try:
            snap_dict = difference_snapshot.to_dict()
            diff_tick = snap_dict.get("tick")
            values = snap_dict.get("values")
            age = None
            if isinstance(diff_tick, int):
                age = logger.tick_count - diff_tick
            return True, "argument", diff_tick, values, age, None
        except Exception:
            return True, "argument", None, None, None, "difference_snapshot argument present but to_dict() failed"

    found, source = _find_upstream_difference_buffer(caller_frame)
    if found is None:
        return (
            False, None, None, None, None,
            "no difference_snapshot argument passed, and no DifferenceHistoryBuffer/"
            "DifferenceSnapshot instance attribute found on the caller's `self` via "
            "frame introspection (does not rule out one existing elsewhere in the "
            "process this sidecar has no reference to)",
        )
    try:
        from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer

        if isinstance(found, DifferenceHistoryBuffer) and found._history:
            last_tick, _magnitudes = found._history[-1]
            age = logger.tick_count - last_tick
            return (
                False, f"caller_frame:{source}", last_tick, None, age,
                "found a reachable DifferenceHistoryBuffer on the caller with a recorded "
                "tick, but not passed to this observe() call; a full DifferenceSnapshot "
                "was not computed here (would require live magnitudes this sidecar has "
                "no legitimate access to)",
            )
        # A bare DifferenceSnapshot sitting on the caller, unused.
        snap_dict = found.to_dict()
        diff_tick = snap_dict.get("tick")
        age = (logger.tick_count - diff_tick) if isinstance(diff_tick, int) else None
        return (
            False, f"caller_frame:{source}", diff_tick, snap_dict.get("values"), age,
            "found a DifferenceSnapshot instance on the caller, but it was not passed "
            "to this observe() call",
        )
    except Exception:
        return (
            False, f"caller_frame:{source}", None, None, None,
            "found a reachable buffer/snapshot on the caller, but reading it raised",
        )


def _record_observation(
    logger: Any,
    trace: List[Any],
    relief_obj: Any,
    cost_total: Dict[str, float],
    difference_snapshot: Optional[Any],
    caller_frame,
    sink: List[CooccurrenceObservation],
) -> None:
    effective_trace = _resolve_effective_trace(logger, list(trace or []))
    trace_length = len(effective_trace)
    pair_eligible = trace_length >= 2
    pair_keys: List[Tuple[str, str]] = []
    if pair_eligible:
        pair_keys = [
            (getattr(effective_trace[i], "id", None), getattr(effective_trace[i + 1], "id", None))
            for i in range(trace_length - 1)
        ]

    x_risk = 0.0
    try:
        for item in effective_trace:
            ability = logger._resolve_ability(item)
            if ability is not None:
                x_risk += ability.x_risk()
    except Exception:
        pass

    relief_dict: Dict[str, float] = {}
    try:
        relief_dict = relief_obj.to_dict() if relief_obj is not None else {}
    except Exception:
        pass

    (
        difference_passed, difference_source, difference_tick, difference_values,
        difference_age_ticks, difference_unavailable_reason,
    ) = _classify_difference_state(logger, difference_snapshot, caller_frame)

    caller_qualname = None
    caller_class = None
    try:
        if caller_frame is not None:
            caller_qualname = caller_frame.f_code.co_qualname if hasattr(caller_frame.f_code, "co_qualname") else caller_frame.f_code.co_name
            caller_self = caller_frame.f_locals.get("self")
            if caller_self is not None:
                caller_class = type(caller_self).__name__
    except Exception:
        pass

    sink.append(CooccurrenceObservation(
        tick=logger.tick_count,
        pair_eligible=pair_eligible,
        trace_length=trace_length,
        pair_keys=pair_keys,
        relief=relief_dict,
        cost=dict(cost_total or {}),
        x_risk=x_risk,
        difference_passed=difference_passed,
        difference_source=difference_source,
        difference_tick=difference_tick,
        difference_values=difference_values,
        difference_age_ticks=difference_age_ticks,
        difference_unavailable_reason=difference_unavailable_reason,
        caller_qualname=caller_qualname,
        caller_class=caller_class,
    ))


def install(logger: Any) -> Tuple[List[CooccurrenceObservation], Callable[[], None]]:
    """
    Wrap `logger.observe` (a bound method on a real ConstraintGenealogyLogger)
    with the sidecar. Returns (sink, uninstall) -- `sink` fills with
    CooccurrenceObservations as real observe() calls happen; call
    `uninstall()` to restore the original method exactly.
    """
    sink: List[CooccurrenceObservation] = []
    original_observe = type(logger).observe

    def wrapped_observe(self, pressure_before, trace, pressure_after,
                         state_sig_before="", state_sig_after="",
                         notes=None, difference_snapshot=None):
        caller_frame = inspect.currentframe().f_back
        result = original_observe(
            self, pressure_before, trace, pressure_after,
            state_sig_before=state_sig_before, state_sig_after=state_sig_after,
            notes=notes, difference_snapshot=difference_snapshot,
        )
        try:
            cost_total = result.trace_cost_total if result is not None else {}
            relief_obj = result.relief if result is not None else pressure_after.relief_from(pressure_before)
            _record_observation(self, trace, relief_obj, cost_total, difference_snapshot, caller_frame, sink)
        except Exception:
            pass
        return result

    logger.observe = wrapped_observe.__get__(logger, type(logger))

    def uninstall() -> None:
        try:
            del logger.observe
        except AttributeError:
            pass

    return sink, uninstall
