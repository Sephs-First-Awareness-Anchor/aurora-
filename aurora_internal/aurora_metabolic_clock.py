"""The metabolic clock: a tick is a span of real time, not a message.

Authors: Sunni (Sir) Morningstar and Cael Devo

Two clocks (docs: AURORA_TICK_CLOCK_MAP.md):

  * the EVENT clock is the turn: perceive, understand the message, answer;
  * the METABOLIC clock is this one: erosion, relaxation, memory aging, consolidation, on real time.

Until now every message was a tick: the live turn called `_sedi.tick(1.0)`, so a message aged her
memory by one full unit whether it came three seconds or three days after the last. Here a tick is
`tick_seconds` of real time (default five minutes), so an exchange of several turns happens INSIDE
one tick.

The rules, as decided:

  1. No mid-turn close-outs. Nothing consolidates while a turn is in flight. A tick that comes due
     during a turn is deferred to the moment the turn closes, and the elapsed time still counts:
     nothing is lost, only moved. (`turn()` is the gate; `close_if_due()` refuses while one is open.)
  2. The turn answers at turn speed. A turn never waits for a tick; the close runs after it, on a
     thread when `background=True`. If a close is already running when the next turn arrives, the
     turn waits for it (briefly, bounded) rather than interleave with it.

A step is `fn(delta_t, systems)`, where `delta_t` is the elapsed time in TICKS (elapsed / tick_seconds,
at least 1.0 for a scheduled close) -- continuous quantities take it as a duration, so a long gap is
one application with a large `delta_t`, not a loop of ticks (the tide that came in while she was gone).
One step failing never stops the others.
"""
import contextlib
import json
import math
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_TICK_SECONDS = 300.0
_MAX_TURN_WAIT_FOR_CLOSE = 30.0     # a turn never waits longer than this on a running close
# How far a wall clock may drift from the monotonic one before it counts as SET rather than slewed (NTP
# corrections are small; a person setting the clock is not).
_CLOCK_TOLERANCE_SECONDS = 5.0


def _default_monotonic():
    """The reference clock for telling a wall clock that was SET from time that PASSED, and whether it counts
    time the device slept.

    CLOCK_MONOTONIC stops while a device is suspended, so against it an overnight suspend (a phone backgrounded
    and frozen, not killed) looks exactly like someone setting the clock forward by eight hours, and the night
    was discarded: she never rested. CLOCK_BOOTTIME keeps counting through suspend, so a wall clock that runs
    ahead of THAT really was set. Where it does not exist the two cannot be told apart, and the forward check
    is turned off: crediting a clock-jump as rest is harmless (rest saturates), discarding a real night is not."""
    boot = getattr(time, "CLOCK_BOOTTIME", None)
    if boot is not None:
        try:
            time.clock_gettime(boot)
            return (lambda: time.clock_gettime(boot)), True
        except (OSError, AttributeError, ValueError):
            pass
    return time.monotonic, False


class MetabolicClock:
    def __init__(
        self,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
        time_source: Optional[Callable[[], float]] = None,
        state_path: Optional[str] = None,
        background: bool = False,
        monotonic_source: Optional[Callable[[], float]] = None,
    ) -> None:
        try:
            tick_seconds = float(tick_seconds)
        except (TypeError, ValueError):
            tick_seconds = DEFAULT_TICK_SECONDS
        self.tick_seconds: float = tick_seconds if tick_seconds > 0.0 else DEFAULT_TICK_SECONDS
        self._now: Callable[[], float] = time_source or time.time
        _default_mono, _counts_suspend = _default_monotonic()
        self._mono: Callable[[], float] = monotonic_source or _default_mono
        # Wall-clock jumps inside a RUNNING process can be told from real time passing by a reference that keeps
        # counting through suspend. An injected wall clock with no injected reference (tests) has none, so it is
        # not checked; with the real clocks the check runs only where the reference counts suspend.
        self._check_jumps: bool = (monotonic_source is not None) or (time_source is None and _counts_suspend)
        self.state_path = state_path
        self.background = bool(background)

        self._cv = threading.Condition(threading.RLock())
        self._turns_in_flight = 0
        self._closing = False
        self._steps: List[Tuple[str, Callable[[float, Any], Any]]] = []
        self._systems: Any = None
        self._deferred_pending = False
        self._yield_requested = False      # a turn is waiting on a close: preemptible steps stop early
        # Which ticks of the current span were OPERATING (had a turn in them). A tick without one is a
        # resting tick: time passes for memory, but she is not eroded by it (she wakes rested).
        self._span_turns = 0
        self._span_slots: set = set()
        self.span: Dict[str, Any] = {"delta_t": 0.0, "operating_ticks": 0.0, "rest_ticks": 0.0, "turns": 0}

        self._hb_thread: Optional[threading.Thread] = None
        self._hb_stop = threading.Event()

        self._last_close: float = self._now()
        self._mono_last_close: float = self._mono()
        self.closes = 0
        # Named state other subsystems want to survive a restart (consolidation debt, the governor): each
        # registers a getter and a setter; it is saved with the clock and handed back on registration.
        self._states: Dict[str, Tuple[Callable[[], Any], Callable[[Any], Any]]] = {}
        self._loaded_states: Dict[str, Any] = {}
        # The span a close has consumed and not yet finished: saved BEFORE the steps run, so a death mid-close
        # does not turn the operating time it was accounting for into free rest.
        self._closing_record: Optional[Dict[str, Any]] = None
        self.anomalies: Dict[str, int] = {"clock_backward": 0, "clock_forward": 0, "interrupted_close": 0}
        self._persist_lock = threading.Lock()
        self.deferred_closes = 0           # ticks that came due mid-turn and waited for the turn
        self.last_report: Dict[str, Any] = {}

    # ---- wiring -------------------------------------------------------------------------------

    def bind(self, systems: Any) -> None:
        self._systems = systems

    def register_state(self, name: str, getter: Callable[[], Any], setter: Callable[[Any], Any]) -> None:
        """Make `name` survive a restart. What was saved under it is handed to `setter` now."""
        self._states[name] = (getter, setter)
        raw = self._loaded_states.pop(name, None)
        if raw is not None:
            try:
                setter(raw)
            except Exception:
                pass                    # a state that cannot be restored starts fresh; it never blocks boot

    def register_step(self, name: str, fn: Callable[[float, Any], Any]) -> None:
        self._steps = [(n, f) for n, f in self._steps if n != name] + [(name, fn)]

    @property
    def step_names(self) -> List[str]:
        return [n for n, _ in self._steps]

    # ---- the turn gate (rule 1 and rule 2) ----------------------------------------------------

    @contextlib.contextmanager
    def turn(self):
        """Wrap a turn. Nothing consolidates while it is open; a tick that came due waits for it."""
        deadline = time.monotonic() + _MAX_TURN_WAIT_FOR_CLOSE
        with self._cv:
            if self._closing:
                self._yield_requested = True       # tell a running close to stop at its next safe point
            while self._closing and time.monotonic() < deadline:
                self._cv.wait(timeout=0.25)        # never interleave with a close in progress
            self._turns_in_flight += 1
        try:
            yield self
        finally:
            with self._cv:
                self._turns_in_flight -= 1
                idle = self._turns_in_flight == 0
                # The turn that just closed was operating in the tick slot it fell in.
                self._span_turns += 1
                self._span_slots.add(int(self.elapsed_seconds() // self.tick_seconds))
            self._persist()                # she was operating: that survives a crash or a shutdown
            if idle:
                self.close_if_due(background=self.background)

    def should_yield(self) -> bool:
        """True when a turn is waiting on this close. Preemptible steps check it between their own steps
        (never mid-step) and stop, carrying the rest to the next close: the turn answers at turn speed."""
        return self._yield_requested

    @property
    def in_turn(self) -> bool:
        return self._turns_in_flight > 0

    # ---- time ---------------------------------------------------------------------------------

    def elapsed_seconds(self) -> float:
        return max(0.0, self._now() - self._last_close)

    def _reconcile_clock(self) -> None:
        """Tell a clock that was SET from time that PASSED. Call with the lock held.

        Backwards: `last_close` would sit in the future and no tick could close until the clock caught up,
        silently stopping consolidation; re-anchor (no time passed, so no gain and no penalty).
        Forwards (inside a running process): a wall clock that ran ahead of the monotonic clock did not
        really pass that time, so trust the monotonic one. Across a restart there is no reference, and time
        away counts, however long.
        """
        now = self._now()
        if now < self._last_close - _CLOCK_TOLERANCE_SECONDS:
            self._last_close = now
            self._mono_last_close = self._mono()
            self.anomalies["clock_backward"] += 1
            return
        if self._check_jumps:
            wall = now - self._last_close
            mono = max(0.0, self._mono() - self._mono_last_close)
            if wall > mono + max(_CLOCK_TOLERANCE_SECONDS, 0.1 * mono):
                self._last_close = now - mono
                self.anomalies["clock_forward"] += 1

    def due(self) -> bool:
        return self.elapsed_seconds() >= self.tick_seconds

    # ---- the close ----------------------------------------------------------------------------

    def close_if_due(self, systems: Any = None, *, force: bool = False,
                     background: bool = False) -> Optional[Dict[str, Any]]:
        """Close the tick if one has elapsed -- and only if no turn is open and no close is running.

        Returns the report (foreground), True (a background close was started), or None.
        """
        with self._cv:
            if self._turns_in_flight > 0 or self._closing:
                if self.due() and not self._deferred_pending:
                    self._deferred_pending = True
                    self.deferred_closes += 1
                return None
            self._reconcile_clock()
            if not force and not self.due():
                return None
            self._closing = True
            self._yield_requested = False
            self._deferred_pending = False
            now = self._now()
            elapsed = max(0.0, now - self._last_close)
        target = systems if systems is not None else self._systems
        if background:
            threading.Thread(target=self._run_close, args=(target, now, elapsed),
                             name="MetabolicClockClose", daemon=True).start()
            return {"started": True}
        return self._run_close(target, now, elapsed)

    def _run_close(self, systems: Any, now: float, elapsed: float) -> Dict[str, Any]:
        delta_t = elapsed / self.tick_seconds
        with self._cv:
            slots, turns = len(self._span_slots), self._span_turns
            self._closing_record = {"from": float(self._last_close), "turns": int(turns),
                                    "slots": sorted(int(s) for s in self._span_slots)}
            self._span_slots, self._span_turns = set(), 0
        self._persist()                    # saved BEFORE the steps run: a death mid-close must not lose the span
        operating = min(delta_t, float(slots)) if turns else 0.0
        # Steps read this to tell time that was spent operating from time spent at rest.
        self.span = {"delta_t": delta_t, "operating_ticks": operating,
                     "rest_ticks": max(0.0, delta_t - operating), "turns": turns}
        report: Dict[str, Any] = {"delta_t": round(delta_t, 6), "elapsed_s": round(elapsed, 3),
                                  "operating_ticks": round(operating, 6),
                                  "rest_ticks": round(self.span["rest_ticks"], 6), "turns": turns, "steps": {}}
        started = time.monotonic()
        try:
            for name, fn in list(self._steps):
                t0 = time.monotonic()
                try:
                    fn(delta_t, systems)
                    report["steps"][name] = {"ok": True, "seconds": round(time.monotonic() - t0, 4)}
                except Exception as exc:                  # one step failing never stops the others
                    report["steps"][name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:160]}
                    try:
                        from aurora_internal.aurora_runtime_faults import record_runtime_fault as _rec
                        _rec(systems if isinstance(systems, dict) else None, subsystem="metabolic_clock",
                             operation=f"step:{name}", exc=exc)
                    except Exception:
                        pass
        finally:
            with self._cv:
                self._last_close = now
                self._mono_last_close = self._mono()
                self._closing_record = None
                self.closes += 1
                report["seconds"] = round(time.monotonic() - started, 4)
                report["closes"] = self.closes
                self.last_report = report
                self._closing = False
                self._yield_requested = False
                self._cv.notify_all()
            self._persist()
        return report

    # ---- the idle heartbeat ----------------------------------------------------------------------------
    # Without it a tick only closes at the next turn's exit, AFTER her reply, so a rest would be credited
    # after the first turn back and she would not wake rested for it. The heartbeat closes due ticks while
    # she is idle. It is bound by the same rules: never mid-turn (close_if_due refuses), never during a
    # close in progress.

    def start_heartbeat(self, interval: Optional[float] = None) -> bool:
        if self._hb_thread is not None and self._hb_thread.is_alive():
            return False
        period = float(interval) if interval else max(0.25, min(30.0, self.tick_seconds / 4.0))
        self._hb_stop = threading.Event()
        stop = self._hb_stop

        def _loop() -> None:
            while not stop.wait(period):
                try:
                    self.close_if_due()
                except Exception:
                    pass                      # the heartbeat must never die; a failed close is recorded per step

        self._hb_thread = threading.Thread(target=_loop, name="MetabolicClockHeartbeat", daemon=True)
        self._hb_thread.start()
        return True

    def stop_heartbeat(self, timeout: float = 2.0) -> None:
        self._hb_stop.set()
        thread = self._hb_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self._hb_thread = None

    @property
    def heartbeat_alive(self) -> bool:
        return self._hb_thread is not None and self._hb_thread.is_alive()

    # ---- persistence ---------------------------------------------------------------------------

    def to_state(self) -> Dict[str, Any]:
        with self._cv:
            slots = sorted(int(s) for s in self._span_slots)
            turns = int(self._span_turns)
            closing = dict(self._closing_record) if self._closing_record else None
        states: Dict[str, Any] = {}
        for name, (getter, _) in list(self._states.items()):
            try:
                states[name] = getter()
            except Exception:
                pass
        return {"last_close": float(self._last_close), "closes": int(self.closes),
                "tick_seconds": float(self.tick_seconds), "span_turns": turns, "span_slots": slots,
                "closing": closing, "anomalies": dict(self.anomalies), "states": states}

    def load_state(self, state: Any) -> bool:
        """Restore when the last tick closed, which ticks she was operating in since, and any registered
        state, so time away counts and neither a restart nor a crash forgives or invents anything."""
        if not isinstance(state, dict):
            return False
        try:
            last = float(state["last_close"])
            closes = int(state.get("closes", 0))
        except (KeyError, TypeError, ValueError):
            return False
        if not math.isfinite(last):
            return False
        now = self._now()
        if last > now:                    # a clock set backwards must not make time run negative
            last = now
            self.anomalies["clock_backward"] += 1
        self._last_close, self.closes = last, closes
        # Time away counts in full (the tide that came in while she was gone), so wall and monotonic agree here.
        self._mono_last_close = self._mono() - max(0.0, now - last)
        turns, slots = 0, set()
        try:
            turns = max(0, int(state.get("span_turns", 0) or 0))
            slots = {int(s) for s in (state.get("span_slots") or []) if int(s) >= 0}
        except (TypeError, ValueError):
            turns, slots = 0, set()
        closing = state.get("closing")
        if isinstance(closing, dict):
            # Died mid-close: the span that close had consumed is operating time, and it was never accounted.
            try:
                turns += max(0, int(closing.get("turns", 0) or 0))
                slots |= {int(s) for s in (closing.get("slots") or []) if int(s) >= 0}
                self.anomalies["interrupted_close"] += 1
            except (TypeError, ValueError):
                pass
        with self._cv:
            self._span_turns, self._span_slots = turns, slots
        saved = state.get("anomalies")
        if isinstance(saved, dict):
            for k in self.anomalies:
                try:
                    self.anomalies[k] = max(self.anomalies[k], int(saved.get(k, 0) or 0))
                except (TypeError, ValueError):
                    pass
        raw_states = state.get("states")
        self._loaded_states = dict(raw_states) if isinstance(raw_states, dict) else {}
        for name in list(self._loaded_states):
            if name in self._states:      # already registered: hand it over now
                raw = self._loaded_states.pop(name)
                try:
                    self._states[name][1](raw)
                except Exception:
                    pass
        return True

    def _persist(self) -> None:
        if not self.state_path:
            return
        with self._persist_lock:          # two threads (a turn exit and a close) must not share one temp file
            try:
                tmp = f"{self.state_path}.tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(self.to_state(), fh)
                os.replace(tmp, self.state_path)
            except (OSError, TypeError, ValueError):
                pass

    def restore(self) -> bool:
        if not self.state_path or not os.path.exists(self.state_path):
            return False
        try:
            with open(self.state_path, "r", encoding="utf-8") as fh:
                return self.load_state(json.load(fh))
        except (OSError, ValueError):
            return False

    def status(self) -> Dict[str, Any]:
        return {"tick_seconds": self.tick_seconds, "closes": self.closes,
                "deferred_closes": self.deferred_closes, "in_turn": self.in_turn,
                "closing": self._closing, "elapsed_s": round(self.elapsed_seconds(), 3),
                "due": self.due(), "steps": self.step_names, "last_report": self.last_report}


def turn_gated(fn: Callable) -> Callable:
    """Decorator for the outermost turn entry: `systems` is the first argument. Systems booted
    without a clock (minimal test dicts) run the turn exactly as before."""
    import functools

    @functools.wraps(fn)
    def _wrapper(systems, *args, **kwargs):
        clock = systems.get("metabolic_clock") if isinstance(systems, dict) else None
        if clock is None:
            return fn(systems, *args, **kwargs)
        with clock.turn():
            return fn(systems, *args, **kwargs)
    return _wrapper
