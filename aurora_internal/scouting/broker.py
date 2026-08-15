"""
Scout broker (Subsurface Presence and Evidence Scout spec, section 10):
enqueue/dedupe/cancel-stale/track-ownership/accept-reports/enforce-
concurrency/enforce-TTL/prevent-proliferation, all via the same
per-request-file transport this codebase's existing Poedex queue
(_poedex_ask() in aurora_daemon.py) already uses -- but WITHOUT its
synchronous wait-for-result loop (spec section 9/15: retrieval must
never block the caller).

Three directories under state_dir/scout_queue/ and state_dir/scout_reports/:

    scout_queue/pending/{request_id}.json   dispatched, unclaimed
    scout_queue/claimed/{request_id}.json   a worker is processing it
    scout_reports/{request_id}.json         a finished ScoutReport

Callers, by role:
    Surface/Subsurface  -> dispatch()               (enqueue)
                         -> poll_reports()           (drain finished work)
                         -> expire_stale_requests()  (housekeeping)
    Scout worker         -> claim_next()             (atomically take one)
                         -> submit_report()          (finish one)

Bounded queue + one-response-fit-Scout-per-turn + duplicate-inquiry
collapse all live in dispatch(), so a caller that dispatches
aggressively (e.g. a runaway retry loop) cannot flood this broker --
the broker itself is the backstop, not caller discipline.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport

# spec section 9/10 initial safeguards, given the captured runtime's
# survival-mode memory pressure: no more than one Scout in flight, and a
# small bounded pending queue so a burst of dispatch() calls degrades to
# "requests get dropped/deduped" rather than unbounded growth.
DEFAULT_MAX_CONCURRENT = 1
DEFAULT_MAX_QUEUE_DEPTH = 5


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


class ScoutBroker:
    def __init__(
        self,
        state_dir: Any = None,
        *,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH,
    ):
        self.state_dir = state_dir
        self.max_concurrent = max(1, int(max_concurrent))
        self.max_queue_depth = max(1, int(max_queue_depth))
        root = _resolve(state_dir)
        self.pending_dir = root / "scout_queue" / "pending"
        self.claimed_dir = root / "scout_queue" / "claimed"
        self.reports_dir = root / "scout_reports"
        for d in (self.pending_dir, self.claimed_dir, self.reports_dir):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/scouting/broker.py:__init__:mkdir",
                    exc=_aurora_boundary_exc,
                    context={"function": "ScoutBroker.__init__", "source_file": "aurora_internal/scouting/broker.py"},
                )

    def _list_json(self, d: Path) -> List[Path]:
        try:
            return sorted(d.glob("*.json"))
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/broker.py:_list_json",
                exc=_aurora_boundary_exc,
                context={"function": "ScoutBroker._list_json", "source_file": "aurora_internal/scouting/broker.py"},
            )
            return []

    def _read_request(self, path: Path) -> Optional[ScoutRequest]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return ScoutRequest.from_dict(raw)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/broker.py:_read_request",
                exc=_aurora_boundary_exc,
                context={"function": "ScoutBroker._read_request", "source_file": "aurora_internal/scouting/broker.py"},
            )
            return None

    # ── Surface/Subsurface side ─────────────────────────────────────────

    def dispatch(self, request: ScoutRequest) -> Optional[str]:
        """Enqueue a ScoutRequest. Returns the request_id that will
        eventually produce a report -- which may be an EXISTING pending
        request's id, not a new one, if this call was deduped. Returns
        None only when the request was rejected outright (queue full,
        one-per-turn cap hit) with no equivalent already in flight --
        the caller proceeds on internal state either way, per spec
        section 17 ("Scout failure must never block Aurora")."""
        pending_paths = self._list_json(self.pending_dir)

        # One response-fit Scout per turn (spec section 10).
        if request.request_kind == "response_fit":
            for p in pending_paths:
                existing = self._read_request(p)
                if existing and existing.turn_id == request.turn_id and existing.request_kind == "response_fit":
                    return existing.request_id
            for p in self._list_json(self.claimed_dir):
                existing = self._read_request(p)
                if existing and existing.turn_id == request.turn_id and existing.request_kind == "response_fit":
                    return existing.request_id

        # Duplicate-inquiry collapse (same inquiry text already pending,
        # regardless of turn -- avoids re-researching the same question
        # a second time just because it recurred on a later turn while
        # the first request is still in flight).
        for p in pending_paths:
            existing = self._read_request(p)
            if existing and existing.inquiry and existing.inquiry == request.inquiry:
                return existing.request_id

        if len(pending_paths) + len(self._list_json(self.claimed_dir)) >= self.max_queue_depth:
            return None

        try:
            path = self.pending_dir / f"{request.request_id}.json"
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(request.to_dict(), indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/broker.py:dispatch:write",
                exc=_aurora_boundary_exc,
                context={"function": "ScoutBroker.dispatch", "source_file": "aurora_internal/scouting/broker.py"},
            )
            return None

        return request.request_id

    def poll_reports(self) -> List[ScoutReport]:
        """Drain every finished ScoutReport since the last call. Only
        Subsurface (via subsurface_scout_bridge.py) is meant to call
        this -- Surface must never read scout_reports directly (spec
        section 11)."""
        reports: List[ScoutReport] = []
        for path in self._list_json(self.reports_dir):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                reports.append(ScoutReport.from_dict(raw))
                path.unlink(missing_ok=True)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/scouting/broker.py:poll_reports",
                    exc=_aurora_boundary_exc,
                    context={"function": "ScoutBroker.poll_reports", "source_file": "aurora_internal/scouting/broker.py"},
                )
        return reports

    def expire_stale_requests(self) -> int:
        """Remove pending/claimed requests past their deadline with no
        report yet -- a request a worker never got to, or one whose
        worker died mid-flight. Removing it here just means no report
        ever arrives for it; that's a normal, silent outcome, not an
        error Subsurface needs to react to."""
        now = time.time()
        expired = 0
        for d in (self.pending_dir, self.claimed_dir):
            for path in self._list_json(d):
                req = self._read_request(path)
                if req is None or now > req.deadline:
                    try:
                        path.unlink(missing_ok=True)
                        expired += 1
                    except Exception as _aurora_boundary_exc:
                        _aurora_record_exception_from_locals(
                            locals(), module=__name__,
                            operation="exception_handler:aurora_internal/scouting/broker.py:expire_stale_requests",
                            exc=_aurora_boundary_exc,
                            context={"function": "ScoutBroker.expire_stale_requests", "source_file": "aurora_internal/scouting/broker.py"},
                        )
        return expired

    def queue_depth(self) -> int:
        return len(self._list_json(self.pending_dir))

    def active_count(self) -> int:
        return len(self._list_json(self.claimed_dir))

    # ── Scout worker side ────────────────────────────────────────────────

    def claim_next(self) -> Optional[ScoutRequest]:
        """Atomically take the oldest unclaimed, unexpired request, if
        concurrency allows. `Path.rename` is atomic on the same
        filesystem, so two workers racing on the same file can never
        both succeed -- the loser's rename raises and it just moves on
        to the next candidate."""
        if self.active_count() >= self.max_concurrent:
            return None

        now = time.time()
        for path in self._list_json(self.pending_dir):
            req = self._read_request(path)
            if req is None:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                continue
            if now > req.deadline:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                continue
            try:
                claimed_path = self.claimed_dir / path.name
                os.rename(str(path), str(claimed_path))
            except FileNotFoundError:
                continue  # another worker claimed it first
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/scouting/broker.py:claim_next",
                    exc=_aurora_boundary_exc,
                    context={"function": "ScoutBroker.claim_next", "source_file": "aurora_internal/scouting/broker.py"},
                )
                continue
            return req
        return None

    def submit_report(self, report: ScoutReport) -> None:
        """Worker calls this exactly once per claimed request, success
        or failure -- writing a "failed"/"cancelled" status report is
        still submit_report(), not a raised exception, so a broken
        Scout can never leave Subsurface waiting on nothing."""
        try:
            path = self.reports_dir / f"{report.request_id}.json"
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/broker.py:submit_report:write",
                exc=_aurora_boundary_exc,
                context={"function": "ScoutBroker.submit_report", "source_file": "aurora_internal/scouting/broker.py"},
            )
        finally:
            claimed_path = self.claimed_dir / f"{report.request_id}.json"
            try:
                claimed_path.unlink(missing_ok=True)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/scouting/broker.py:submit_report:cleanup",
                    exc=_aurora_boundary_exc,
                    context={"function": "ScoutBroker.submit_report", "source_file": "aurora_internal/scouting/broker.py"},
                )
