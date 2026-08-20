"""
Real-time research dispatch for live comprehension gaps.

ResearchStudyMode.execute_research_cycle() already does real research
(dictionary + DuckDuckGo lookups, wired via set_fetch_callback() at boot)
and deposits results into OETS -- but it only ran on aurora_daemon.py's
periodic background cycle, so a gap opened mid-conversation only got a
research_priority boost and had to wait to be noticed by the next
scheduled scan, possibly minutes away.

Sunni, 2026-08-21: "she should be able to research in real time while
surface handles the space between research and understanding material
accumulation. hell if the research stacks just make another agent to
distribute the load."

This module gives a comprehension-gap topic a direct, immediate path to
research the moment the gap opens, using a small pool of worker threads
so a burst of gaps doesn't serialize behind one at a time -- "make
another agent to distribute the load" is exactly what the worker pool is.

Design: workers only do the network-bound fetch (ResearchStudyMode.
_research_word(), the dictionary/DuckDuckGo call), which touches no
shared Aurora state and is safe to run concurrently. Integrating a result
into OETS (add_node/add_definition/add_relation) DOES mutate shared
state -- ResearchStudyMode/OntologicalWeb were never built for concurrent
callers -- so that step is funneled through a single lock instead of
trusted to bare dict/list mutations racing across threads.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import logging
import queue as _queue
import threading
from typing import Any, Dict, Optional

log = logging.getLogger("aurora_research_dispatch")

_WORKER_COUNT = 2

_dispatch_queue: "_queue.Queue" = _queue.Queue()
_integration_lock = threading.Lock()

_pending_words: set = set()
_pending_lock = threading.Lock()

_workers_started = False
_workers_lock = threading.Lock()


def request_research(systems: Optional[Dict[str, Any]], word: str) -> bool:
    """Enqueue a word for immediate research on a background worker.

    Safe to call from any thread (this is called from the same live-turn
    path that opens a seeking flag). Silently a no-op if the word is
    already queued/in-flight, or if research isn't wired for this boot
    (no perception.oets, no fetch callback set). Returns whether the
    word was actually enqueued, for callers/tests that want to know.
    """
    word = str(word or "").strip().lower()
    if not word or systems is None:
        return False

    with _pending_lock:
        if word in _pending_words:
            return False
        _pending_words.add(word)

    try:
        _ensure_workers_started()
        _dispatch_queue.put_nowait((systems, word))
        return True
    except Exception as _aurora_boundary_exc:
        with _pending_lock:
            _pending_words.discard(word)
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_research_dispatch.py:request_research",
            exc=_aurora_boundary_exc,
            context={"function": "request_research", "source_file": "aurora_research_dispatch.py"},
        )
        return False


def _ensure_workers_started() -> None:
    global _workers_started
    if _workers_started:
        return
    with _workers_lock:
        if _workers_started:
            return
        for i in range(_WORKER_COUNT):
            threading.Thread(
                target=_worker_loop, args=(i,), daemon=True,
                name=f"aurora_research_worker_{i}",
            ).start()
        _workers_started = True


def _worker_loop(worker_id: int) -> None:
    while True:
        systems, word = _dispatch_queue.get()
        try:
            _research_one(systems, word)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_research_dispatch.py:_worker_loop",
                exc=_aurora_boundary_exc,
                context={"function": "_worker_loop", "source_file": "aurora_research_dispatch.py"},
            )
        finally:
            with _pending_lock:
                _pending_words.discard(word)
            _dispatch_queue.task_done()


def _research_one(systems: Dict[str, Any], word: str) -> None:
    perception = (systems or {}).get("perception")
    scaffolding = getattr(perception, "oets", None) if perception else None
    research = getattr(scaffolding, "research", None) if scaffolding else None
    web = getattr(scaffolding, "web", None) if scaffolding else None
    if research is None or web is None or not hasattr(research, "_research_word"):
        return

    # Network-bound fetch -- no shared Aurora state touched here, safe to
    # run concurrently with other workers researching different words.
    result = research._research_word(word)
    if not getattr(result, "success", False):
        return

    # Everything past this point mutates OETS (nodes/relations) -- serialize.
    with _integration_lock:
        try:
            # _integrate_result() silently no-ops if the node doesn't
            # already exist (self.web.nodes.get(word) -> None -> return).
            # A comprehension gap can open on a word Aurora has never
            # stored a node for at all, so ensure one exists before
            # handing the fetched result to it -- otherwise a real,
            # successful lookup would just be discarded.
            if hasattr(web, "has_node") and hasattr(web, "add_node") and not web.has_node(word):
                web.add_node(word, role="noun", valence=0.0)
            research._integrate_result(word, result)
            if hasattr(scaffolding, "cluster_engine") and hasattr(scaffolding.cluster_engine, "discover_clusters"):
                scaffolding.cluster_engine.discover_clusters()
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_research_dispatch.py:_research_one:integrate",
                exc=_aurora_boundary_exc,
                context={"function": "_research_one", "source_file": "aurora_research_dispatch.py"},
            )
