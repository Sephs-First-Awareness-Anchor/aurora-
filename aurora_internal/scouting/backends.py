"""
ScoutBackend abstraction (Aurora Build 694, step 7).

The Scout worker (aurora_scout_daemon.py) used to have exactly one
retrieval path hardcoded into it: check whether aurora_room.py is
running (a `pgrep` process check) and, if so, talk to its Poedex
per-request-file queue. On Android that check can never succeed --
there is no separate aurora_room.py process, no desktop service
manager, nothing for `pgrep -f aurora_room.py` to find -- so the worker
was structurally unusable on that platform no matter how it was
started.

A ScoutBackend is a small, swappable retrieval strategy:

    is_available() -> bool          cheap, no side effects
    retrieve(request, state_dir) -> str   raw retrieved text, or ""

Normalizing that raw text into a ScoutReport (truncation, evidence_items
shape, provenance, confidence, the "explain"-by-default relationship --
soon to be more structured, spec step 13) stays entirely
aurora_scout_daemon.py's job, unchanged regardless of which backend
produced the text. Backends only ever return a string; none of them
constructs a ScoutReport itself, so no backend can smuggle a
final_response through by construction.

Included here:

    PoedexRoomBackend    desktop's existing behavior, unchanged in
                          effect -- still requires aurora_room.py
    LocalLessonsBackend  Android-capable: searches Aurora's own
                          persisted bound-lesson corpus
                          (poedex_lessons.json), a local file read with
                          no pgrep, no second process, no network call
                          at all
    TestBackend          deterministic canned-result backend for tests
    RemoteSearchBackend  operator-configured external search -- takes a
                          caller-supplied fetch_fn, never a hardcoded
                          provider (spec: "Do not hardcode a specific
                          commercial provider into Aurora's cognitive
                          architecture. Provider selection belongs in
                          backend configuration.")
    RemoteModelBackend   same pattern, for an operator-configured model
                          query function

RemoteSearchBackend/RemoteModelBackend are real, usable classes -- an
operator wires a real provider in by passing a callable at
construction time -- but neither one is wired to any concrete
commercial API in this codebase, which is exactly what the spec asks
for. resolve_backend_chain() below defaults to
[PoedexRoomBackend, LocalLessonsBackend], both fully functional with no
external configuration required, which is what makes Android capable
out of the box: PoedexRoomBackend.is_available() is simply False there
(no Room process to find), and LocalLessonsBackend never depended on
one in the first place.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, List, Optional

from aurora_internal.scouting.contracts import ScoutRequest


def _resolve(state_dir: Any) -> Path:
    return Path(str(state_dir))


class ScoutBackend:
    """Base class -- exists mainly so isinstance()/subclassing has a
    real anchor and every backend documents the same two-method shape.
    Duck typing (any object with these two methods) works too; nothing
    in this file requires the base class specifically."""

    name: str = "abstract"

    def is_available(self) -> bool:
        raise NotImplementedError

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        raise NotImplementedError


class PoedexRoomBackend(ScoutBackend):
    """Desktop's existing behavior, moved here unchanged in effect: the
    same per-request-file protocol _poedex_ask() (aurora_daemon.py)
    uses against aurora_room.py's queue, reimplemented minimally rather
    than imported (avoids dragging in aurora_daemon.py's heavy import
    graph -- see aurora_scout_daemon.py's own module docstring)."""

    name = "poedex_room"

    def is_available(self) -> bool:
        try:
            proc = subprocess.run(
                ["pgrep", "-f", "aurora_room.py"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        state_dir = _resolve(state_dir)
        queue_dir = state_dir / "poedex_queue"
        result_dir = state_dir / "poedex_results"
        queue_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)

        question = request.inquiry
        if request.interpreted_input:
            question = f"{request.inquiry} (context: Aurora already interprets the input as: {request.interpreted_input})"

        qid = f"scout_{time.time():.4f}_{os.getpid()}"
        query_path = queue_dir / f"{qid}.json"
        result_path = result_dir / f"{qid}.json"

        try:
            query_path.write_text(json.dumps({
                "id": qid, "question": question, "cat": "researcher", "lane": "self",
                "status": "pending", "submitted": time.time(),
            }, indent=2), encoding="utf-8")
        except Exception:
            return ""

        remaining = request.deadline - time.time()
        timeout = max(5.0, min(45.0, remaining))
        deadline = time.time() + max(1.0, timeout)
        while time.time() < deadline:
            time.sleep(0.4)
            if result_path.exists():
                try:
                    r = json.loads(result_path.read_text(encoding="utf-8"))
                    if r.get("id") == qid and r.get("status") == "done":
                        result = str(r.get("result", "") or "")
                        result_path.unlink(missing_ok=True)
                        return result
                except Exception:
                    pass

        try:
            query_path.unlink(missing_ok=True)
        except Exception:
            pass
        return ""


class LocalLessonsBackend(ScoutBackend):
    """Android-capable by construction: searches poedex_lessons.json,
    the same bound-lesson corpus aurora._try_poedex_lookup()'s instant
    (non-Room) step already reads -- a real, existing, persisted store
    of things Aurora has actually been taught, not a fabricated data
    source. No pgrep, no second process, no network call. Bounded to
    what's already in that corpus rather than open-ended retrieval,
    which is an honest limitation, not a disguised one."""

    name = "local_lessons"

    def is_available(self) -> bool:
        return True  # a local file read is always attemptable

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        state_dir = _resolve(state_dir)
        lessons_path = state_dir / "poedex_lessons.json"
        if not lessons_path.exists():
            return ""
        try:
            lessons = json.loads(lessons_path.read_text(encoding="utf-8") or "[]")
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/backends.py:LocalLessonsBackend.retrieve",
                exc=_aurora_boundary_exc,
                context={"function": "LocalLessonsBackend.retrieve", "source_file": "aurora_internal/scouting/backends.py"},
            )
            return ""
        if not isinstance(lessons, list):
            return ""

        query = str(request.inquiry or request.interpreted_input or "").lower().strip()
        if not query:
            return ""
        query_kw = set(re.findall(r"[a-z]{4,}", query))

        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            question = str(lesson.get("question", "") or "").lower()
            answer = str(lesson.get("lesson", "") or "").strip()
            if not (answer and len(answer) > 20):
                continue
            if query and (query in question or question in query):
                return answer
            question_kw = set(re.findall(r"[a-z]{4,}", question))
            answer_kw = set(re.findall(r"[a-z]{4,}", answer.lower()))
            if query_kw and len(query_kw & (question_kw | answer_kw)) >= max(2, len(query_kw) // 2):
                return answer
        return ""


class TestBackend(ScoutBackend):
    """Deterministic, test-only: always returns whatever canned_result
    it was constructed with, regardless of the request. Used by spec
    section 31's required acceptance scenarios ("Use a deterministic
    fake Scout backend")."""

    # Tells pytest not to try collecting this as a test class just
    # because its name starts with "Test" -- the name itself is the
    # spec's own naming, kept as-is rather than renamed to dodge the
    # collector.
    __test__ = False

    name = "test"

    def __init__(self, canned_result: str = "", *, available: bool = True):
        self.canned_result = canned_result
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        return self.canned_result


class RemoteSearchBackend(ScoutBackend):
    """Operator-configured external search. Deliberately not wired to
    any concrete commercial provider here (spec: "Do not hardcode a
    specific commercial provider into Aurora's cognitive architecture.
    Provider selection belongs in backend configuration.") -- a
    deploying operator supplies fetch_fn: str -> str at construction
    time. Unconfigured (fetch_fn=None), it is simply unavailable, the
    same honest degrade as PoedexRoomBackend when Room isn't running."""

    name = "remote_search"

    def __init__(self, fetch_fn: Optional[Callable[[str], str]] = None):
        self.fetch_fn = fetch_fn

    def is_available(self) -> bool:
        return callable(self.fetch_fn)

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if not callable(self.fetch_fn):
            return ""
        try:
            return str(self.fetch_fn(str(request.inquiry or "")) or "")
        except Exception:
            return ""


class RemoteModelBackend(ScoutBackend):
    """Same operator-configuration pattern as RemoteSearchBackend, for
    an operator-supplied model-query function taking (inquiry,
    interpreted_input) -> str."""

    name = "remote_model"

    def __init__(self, query_fn: Optional[Callable[[str, str], str]] = None):
        self.query_fn = query_fn

    def is_available(self) -> bool:
        return callable(self.query_fn)

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if not callable(self.query_fn):
            return ""
        try:
            return str(self.query_fn(str(request.inquiry or ""), str(request.interpreted_input or "")) or "")
        except Exception:
            return ""


_BACKEND_REGISTRY = {
    "poedex_room": PoedexRoomBackend,
    "local_lessons": LocalLessonsBackend,
    "test": TestBackend,
    "remote_search": RemoteSearchBackend,
    "remote_model": RemoteModelBackend,
}

# Both fully functional with zero external configuration -- this is
# what makes the DEFAULT chain already Android-capable: PoedexRoomBackend
# just reports itself unavailable there (no Room process to find) and
# LocalLessonsBackend never needed one. Order matters: Room (when
# running) is tried first since it can reach genuinely open-ended
# evidence Room's own web lookup provides; the local corpus is the
# fallback everywhere, including the only backend Android ever reaches.
DEFAULT_BACKEND_NAMES = ("poedex_room", "local_lessons")


def resolve_backend_chain(names: Optional[List[str]] = None) -> List[ScoutBackend]:
    """Config-driven backend selection (spec: "Provider selection
    belongs in backend configuration," not hardcoded into the worker).
    `names` explicit > SCOUT_BACKENDS env var (comma-separated) >
    DEFAULT_BACKEND_NAMES. Unknown names are skipped, not fatal --
    a typo in configuration should degrade to fewer backends, never
    crash the worker."""
    if names is None:
        env_value = os.environ.get("SCOUT_BACKENDS", "")
        names = [n.strip() for n in env_value.split(",") if n.strip()] if env_value else list(DEFAULT_BACKEND_NAMES)

    chain: List[ScoutBackend] = []
    for name in names:
        backend_cls = _BACKEND_REGISTRY.get(name)
        if backend_cls is None:
            continue
        try:
            chain.append(backend_cls())
        except Exception:
            continue
    return chain
