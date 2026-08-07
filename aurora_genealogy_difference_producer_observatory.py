#!/usr/bin/env python3
"""
AURORA GENEALOGY DIFFERENCE PRODUCER OBSERVATORY (Phase 3A.2)
====================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Phase 3A.1 instrumented the CONSUMER boundary (ConstraintGenealogyLogger
.observe()). This phase instruments the PRODUCER boundary --
DifferenceHistoryBuffer.record()/.snapshot() (aurora_internal
/aurora_difference_buffer.py) -- read-only, still no behavioral wiring, to
answer: when DIFFERENCE is actually computed, what execution contexts
produce it, and do any of those contexts temporally or causally coincide
with organic pair formation?

STILL NO BEHAVIORAL WIRING.
---------------------------------------------------------------------------
`install_producer_observatory()` wraps `DifferenceHistoryBuffer.record` and
`.snapshot` AT THE CLASS LEVEL (every instance, process-wide -- this is the
actual production boundary, and there is no per-instance way to reach it
generically, since instances are created independently by whichever object
owns one; see Phase 3A.1's finding that this buffer is instance-scoped, not
a singleton). Each wrapped method calls the real, original method FIRST
with every argument unchanged, and returns its real result unmodified.
Recording happens only afterward, read-only, try/except-guarded. No
observation is ever passed to anything -- not back into the buffer, not
into any ConstraintGenealogyLogger, not into PairStats or promotion.
Verified: `test_wrapped_snapshot_and_record_produce_identical_results`,
`test_producer_sidecar_never_feeds_anything_back`.

REAL PRODUCER CALL SITES FOUND (hand-verified by reading, not by an
automated data-flow tracer -- grep found the call sites; reading confirmed
what each one does):
---------------------------------------------------------------------------
- `aurora_internal/aurora_evolution_chamber.py:1402` -- the evolution
  chamber's own per-tick processing (already known from Phase 3A.1).
- `aurora_internal/aurora_evolution_chamber.py:1847` -- a second call site
  on the same class, a "last computed" accessor (`diff_snapshot` property).
- `aurora.py:31448`, inside `_run_live_response_turn` -- computes a REAL
  `DifferenceSnapshot` on every ordinary conversational turn (not gated on
  dream/artificial-seed state at all), then stores it at
  `systems['_last_diff_snapshot']` (line 31449).
- `aurora_training_pulse.py:247`, inside `TrainingPulse._record_and_snapshot()`
  -- its own docstring calls itself "Mirror of aurora.py's per-turn diff
  buffer record + snapshot" -- does the same thing for the training-pulse
  simulation path, also storing to `self._systems["_last_diff_snapshot"]`.

REAL CONSUMER (pair-forming, promotion-adjacent) CALL SITES FOUND, SAME
METHOD:
---------------------------------------------------------------------------
- `aurora_grammar_engine.py:1547` (`GrammarEngine._log_relief_to_genealogy`)
  -- hardcodes `difference_snapshot=None` (Phase 3A/3A.1's original finding).
- `aurora.py:17728` (inside `_log_modulation_event`) -- 2-item trace, omits
  `difference_snapshot` entirely (defaults to `None`).
- `aurora.py:17830` (inside `_log_claim_resolution_relief`) -- 2-item
  trace, also omits `difference_snapshot` entirely.
- `aurora.py:4362` (inside a field-balance injector) -- passes
  `difference_snapshot={}`, a plain dict, NOT a `DifferenceSnapshot`
  instance. **This is a real, separate, confirmed bug**, found as a side
  effect of this investigation, not something this phase set out to find:
  `observe()`'s own body (`constraint_genealogy.py:1975-1976`) calls
  `difference_snapshot.to_dict()` unconditionally whenever the argument
  `is not None` -- `{}.to_dict()` raises `AttributeError`, live-verified
  (`test_confirmed_empty_dict_difference_snapshot_bug`). The call site's
  own surrounding `try/except` silently swallows it, so this caller's
  relief event never gets logged AT ALL when it fires, not merely without
  DIFFERENCE. Not fixed here -- out of scope (a live-behavior change to a
  file this project has not touched anywhere else) -- reported so it isn't
  lost.

**`systems['_last_diff_snapshot']` (written at `aurora.py:31449` and
`aurora_training_pulse.py:248`) is never read anywhere else in the
repository** -- confirmed by grep across the full codebase. Every real
producer call site's output is either stored somewhere nothing reads, or
(evolution chamber) passed directly into that chamber's own `.observe()`
call for its OWN traces, which in the one real corpus available (Phase
3A/3A.1) are single-item dream-episode replays, never pair-forming.

This is now a code-level finding, not merely a corpus-limited one: across
every real call site located on both sides, there is no code path,
anywhere in this repository, connecting a value a producer call site wrote
to an argument any consumer call site reads. See
docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md section 13 for the full
producer/consumer catalog and the Case A/B/C analysis.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_IDENTITY_ATTR_HINTS = ("id", "episode", "session", "run_id", "lineage", "turn", "tick_count", "chamber")


@dataclass
class ProducerObservation:
    method: str                          # "record" | "snapshot"
    tick: Optional[int]
    producer_class: str
    producer_instance_id: int            # id() of the DifferenceHistoryBuffer instance
    call_path: List[str] = field(default_factory=list)     # nearest-first qualnames
    axis_values: Optional[Dict[str, float]] = None           # only for "snapshot"
    causal_context: Dict[str, Any] = field(default_factory=dict)  # best-effort identity hints

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def _capture_call_path(frame, depth: int = 5) -> List[str]:
    path: List[str] = []
    f = frame
    try:
        for _ in range(depth):
            if f is None:
                break
            code = f.f_code
            qual = getattr(code, "co_qualname", None) or code.co_name
            self_obj = f.f_locals.get("self")
            if self_obj is not None:
                qual = f"{type(self_obj).__name__}.{qual.split('.')[-1]}"
            path.append(qual)
            f = f.f_back
    except Exception:
        pass
    return path


def _capture_causal_context(frame) -> Dict[str, Any]:
    """Best-effort, read-only: look at the immediate caller's `self` for
    attributes whose NAME suggests an identity/lifecycle context (episode,
    session, run_id, lineage, turn, chamber, tick_count) -- exactly what
    the directive asked for "where naturally available". Only scalar-ish
    values (str/int/float/bool) are captured; objects are skipped rather
    than risking an expensive or unsafe repr(). Aurora's common pattern is a
    `self._systems` (or similarly named) dict-of-subsystems registry rather
    than direct instance attributes (confirmed: TrainingPulse, aurora.py's
    turn processing) -- one level into any dict-valued attribute is also
    scanned for the same name hints, read-only, no recursion beyond that."""
    context: Dict[str, Any] = {}
    try:
        if frame is None:
            return context
        self_obj = frame.f_locals.get("self")
        if self_obj is None:
            return context
        owner = type(self_obj).__name__
        for attr_name, attr_val in vars(self_obj).items():
            lowered = attr_name.lower()
            if any(hint in lowered for hint in _IDENTITY_ATTR_HINTS):
                if isinstance(attr_val, (str, int, float, bool)) or attr_val is None:
                    context[f"{owner}.{attr_name}"] = attr_val
            if isinstance(attr_val, dict):
                for key, val in attr_val.items():
                    key_lowered = str(key).lower()
                    if any(hint in key_lowered for hint in _IDENTITY_ATTR_HINTS):
                        if isinstance(val, (str, int, float, bool)) or val is None:
                            context[f"{owner}.{attr_name}['{key}']"] = val
    except Exception:
        pass
    return context


def install_producer_observatory() -> Tuple[List[ProducerObservation], "callable"]:
    """
    Wraps DifferenceHistoryBuffer.record and .snapshot AT THE CLASS LEVEL --
    every instance, process-wide, for the lifetime of this installation.
    Returns (sink, uninstall).
    """
    from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer

    sink: List[ProducerObservation] = []
    original_record = DifferenceHistoryBuffer.record
    original_snapshot = DifferenceHistoryBuffer.snapshot

    def wrapped_record(self, tick, magnitudes):
        result = original_record(self, tick, magnitudes)
        try:
            caller_frame = inspect.currentframe().f_back
            sink.append(ProducerObservation(
                method="record",
                tick=tick,
                producer_class=type(self).__name__,
                producer_instance_id=id(self),
                call_path=_capture_call_path(caller_frame),
                axis_values=None,
                causal_context=_capture_causal_context(caller_frame),
            ))
        except Exception:
            pass
        return result

    def wrapped_snapshot(self, tick=None, magnitudes=None):
        result = original_snapshot(self, tick, magnitudes)
        try:
            caller_frame = inspect.currentframe().f_back
            axis_values = None
            try:
                axis_values = result.to_dict().get("values")
            except Exception:
                pass
            sink.append(ProducerObservation(
                method="snapshot",
                tick=(result.tick if hasattr(result, "tick") else tick),
                producer_class=type(self).__name__,
                producer_instance_id=id(self),
                call_path=_capture_call_path(caller_frame),
                axis_values=axis_values,
                causal_context=_capture_causal_context(caller_frame),
            ))
        except Exception:
            pass
        return result

    DifferenceHistoryBuffer.record = wrapped_record
    DifferenceHistoryBuffer.snapshot = wrapped_snapshot

    def uninstall() -> None:
        DifferenceHistoryBuffer.record = original_record
        DifferenceHistoryBuffer.snapshot = original_snapshot

    return sink, uninstall


# ---------------------------------------------------------------------------
# Correlation (producer sink x consumer sink from Phase 3A.1)
# ---------------------------------------------------------------------------

@dataclass
class CorrelationFinding:
    case: str    # "A_no_proximity" | "B_same_tick_no_link" | "C_temporal_offset" | "insufficient_data"
    detail: Dict[str, Any] = field(default_factory=dict)


def correlate_producer_consumer(
    producer_obs: List[ProducerObservation],
    consumer_obs: List[Any],   # List[CooccurrenceObservation] from Phase 3A.1
    tick_window: int = 5,
) -> CorrelationFinding:
    """
    Correlates producer-side observations against consumer-side
    (pair-eligible) observations from aurora_genealogy_cooccurrence_observatory.
    Classifies into the three cases the directive described:

      A: no producer observation falls within `tick_window` ticks of ANY
         pair-eligible consumer observation (and vice versa) -- consistent
         with genuine architectural separation between developmental regimes.
      B: at least one producer/consumer pair shares a tick within
         `tick_window`, but no shared causal_context key/value between them
         -- a cross-organ information boundary: same moment, no link.
      C: a consistent temporal offset exists (producer reliably N ticks
         before or after the nearest pair-eligible consumer event) -- a
         lifecycle/temporal question rather than an architectural one.
    """
    eligible_consumers = [o for o in consumer_obs if getattr(o, "pair_eligible", False)]
    if not producer_obs or not eligible_consumers:
        return CorrelationFinding(case="insufficient_data", detail={
            "producer_count": len(producer_obs), "pair_eligible_consumer_count": len(eligible_consumers),
        })

    ticked_producers = [p for p in producer_obs if p.tick is not None]

    # For each pair-eligible consumer, pair it with its single NEAREST
    # producer observation (by absolute tick distance), not every producer
    # within the window -- an all-pairs join over a loose window drifts
    # into spurious cross-pairs whenever sequences overlap, which would
    # corrupt the offset-consistency check below.
    proximate_pairs: List[Tuple[ProducerObservation, Any, int]] = []
    for c in eligible_consumers:
        if c.tick is None or not ticked_producers:
            continue
        nearest = min(ticked_producers, key=lambda p: abs(c.tick - p.tick))
        delta = c.tick - nearest.tick
        if abs(delta) <= tick_window:
            proximate_pairs.append((nearest, c, delta))

    if not proximate_pairs:
        return CorrelationFinding(case="A_no_proximity", detail={
            "producer_count": len(producer_obs),
            "pair_eligible_consumer_count": len(eligible_consumers),
            "tick_window": tick_window,
        })

    deltas = [delta for (_, _, delta) in proximate_pairs]
    all_same_sign_and_consistent = len(set(deltas)) == 1 and deltas[0] != 0
    if all_same_sign_and_consistent:
        return CorrelationFinding(case="C_temporal_offset", detail={
            "consistent_offset_ticks": deltas[0],
            "n_pairs": len(proximate_pairs),
        })

    shared_context_pairs = 0
    for (p, c, _delta) in proximate_pairs:
        consumer_context = {"caller_class": getattr(c, "caller_class", None), "caller_qualname": getattr(c, "caller_qualname", None)}
        if any(
            str(v) in {str(x) for x in p.causal_context.values()}
            for v in consumer_context.values() if v is not None
        ):
            shared_context_pairs += 1

    return CorrelationFinding(case="B_same_tick_no_link", detail={
        "n_proximate_pairs": len(proximate_pairs),
        "n_with_shared_causal_context": shared_context_pairs,
        "tick_window": tick_window,
    })
