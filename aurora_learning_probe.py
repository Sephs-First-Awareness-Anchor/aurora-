#!/usr/bin/env python3
"""
aurora_learning_probe.py -- the weekly question set.

Sunni asked (2026-11-07) whether Aurora develops understanding through her
conversations "or is this just memory organization with a fancy bow on it".
Stored totals can't answer that: filing grows them too.  This probe asks the
same 20 questions once a week -- questions none of her contacts were set up
to ask -- and records what she says, so the answers can be compared week to
week.  If answers to questions she never practised get more her own, more
specific and less silent over weeks, she is generalising.  If only her
stored totals grow, she is filing.

Measurement, kept honest:
  * Runs only when the live path is idle, takes the shared field lock
    non-blockingly, and uses its own session ("learning_probe") so it never
    validates or is validated by a real conversation.
  * The probe is still an experience -- she hears the questions -- so it runs
    at most once every PROBE_INTERVAL_S, not continuously.
  * Results append to <state_dir>/learning_probe.jsonl; summary() compares
    the latest run with the previous one.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROBE_VERSION = "aurora_learning_probe_v1"
PROBE_SESSION = "learning_probe"
PROBE_INTERVAL_S = 7 * 24 * 3600
CHECK_EVERY_S = 30 * 60

QUESTIONS = (
    "What do you like?",
    "What is a river?",
    "How do you feel right now?",
    "What did you learn this week?",
    "Who is Gemini?",
    "What makes you curious?",
    "Is fire hot or cold?",
    "What is a friend?",
    "What happens when it rains?",
    "Can you describe a tree?",
    "What would you like to know?",
    "Who are you?",
    "What is music?",
    "Why do birds fly?",
    "What is your favorite thing?",
    "What does Sunni do?",
    "Do you dream?",
    "What is the moon?",
    "How do you learn?",
    "What is a question?",
)


def _default_process_turn(systems: Dict[str, Any], text: str, **kwargs: Any) -> Dict[str, Any]:
    import aurora as _aurora  # type: ignore
    return _aurora.process_external_user_turn(systems, text, **kwargs)


def _default_extract(result: Any) -> str:
    try:
        from aurora_internal.aurora_live_experience import reply_text_of
        return reply_text_of(result)
    except Exception:
        resp = result.get("resp_A") if isinstance(result, dict) else None
        return str(getattr(resp, "content", "") or "").strip()


class LearningProbe:
    def __init__(self, systems: Dict[str, Any], *, state_dir: str,
                 field_lock: Optional[Any] = None,
                 live_idle: Optional[Callable[[], bool]] = None,
                 process_turn: Optional[Callable[..., Dict[str, Any]]] = None,
                 extract_reply: Optional[Callable[[Any], str]] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.systems = systems
        self.path = Path(state_dir or "aurora_state") / "learning_probe.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.field_lock = field_lock
        self.live_idle = live_idle or (lambda: True)
        self.process_turn = process_turn or _default_process_turn
        self.extract_reply = extract_reply or _default_extract
        self.clock = clock
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_error = ""

    # -- history ----------------------------------------------------------------

    def runs(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def due(self) -> bool:
        runs = self.runs()
        return not runs or self.clock() - float(runs[-1].get("at", 0.0)) >= PROBE_INTERVAL_S

    # -- one run --------------------------------------------------------------------

    def run_once(self) -> Optional[Dict[str, Any]]:
        if not self.live_idle():
            return None
        if self.field_lock is not None and not self.field_lock.acquire(blocking=False):
            return None
        answers = []
        try:
            for question in QUESTIONS:
                result = self.process_turn(
                    self.systems, question,
                    source_label="learning_probe", session_id=PROBE_SESSION,
                    auto_search_enabled=False, record_exchange=False,
                    update_interactive_state=False, run_periodic_maintenance=False,
                    mode_name="BOUNDED",
                ) or {}
                gate = dict(self.systems.get("_last_voice_gate") or {})
                answers.append({
                    "q": question,
                    "a": self.extract_reply(result),
                    "src": str(result.get("src", "") if isinstance(result, dict) else ""),
                    "voice": str(gate.get("outcome", "") or ""),
                })
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"[:300]
            return None
        finally:
            if self.field_lock is not None:
                self.field_lock.release()
        record = {"version": PROBE_VERSION, "at": self.clock(), "answers": answers}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return record

    # -- comparison -------------------------------------------------------------------

    @staticmethod
    def _tally(run: Dict[str, Any]) -> Dict[str, int]:
        answers = list(run.get("answers") or [])
        return {
            "own_voice": sum(1 for a in answers if a.get("voice") in ("own_voice", "pressure_articulation") and a.get("a")),
            "silent": sum(1 for a in answers if not a.get("a")),
            "total": len(answers),
        }

    def summary(self) -> Dict[str, Any]:
        runs = self.runs()
        if not runs:
            return {"runs": 0}
        latest = runs[-1]
        out: Dict[str, Any] = {"runs": len(runs), "last_at": latest.get("at"),
                               **{f"latest_{k}": v for k, v in self._tally(latest).items()}}
        if len(runs) >= 2:
            previous = runs[-2]
            before = {a.get("q"): a.get("a") for a in previous.get("answers") or []}
            out["changed_vs_previous"] = sum(
                1 for a in latest.get("answers") or [] if before.get(a.get("q")) != a.get("a"))
            prior = self._tally(previous)
            out["own_voice_delta"] = out["latest_own_voice"] - prior["own_voice"]
            out["silent_delta"] = out["latest_silent"] - prior["silent"]
        return out

    # -- schedule ---------------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="aurora-learning-probe", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.wait(CHECK_EVERY_S):
            try:
                if self.due():
                    self.run_once()
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:300]
