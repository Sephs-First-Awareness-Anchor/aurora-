# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Durable evidence journal between the Surface and the Subsurface genealogy (directive VIII, Stage E; test 8).

The Surface process observes during a live turn and keeps only its own session state; the canonical genealogy lives in the
Subsurface runtime.  This module is the transfer between them and nothing else: an append-only journal of observations, each
with a durable identity (origin, seq), and the record of which have already been consolidated.  It holds no developmental
state of its own and never decides anything about evidence -- the genealogy replays the records through its own `observe`.

Identity
    event id = (origin, seq).  `origin` is one Surface logger run; `seq` is that run's own counter.  The same event read twice,
    from the journal or from a rotated copy of it, is the same event.
Order
    records are consolidated per origin in seq order.  A gap (a seq the journal does not hold: a crash before a flush, a rotation
    the consumer did not catch) is recorded, never filled in and never allowed to stop later events.
Idempotence
    `AppliedLedger` records, per origin, the highest contiguous seq applied plus any applied above a gap.  An applied event is
    skipped, so consolidating twice, or from overlapping files, applies it once.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

JOURNAL_NAME = "evidence_journal.jsonl"
APPLIED_NAME = "journal_applied.json"
MAX_BYTES = 8 * 1024 * 1024
MAX_ORIGINS = 256
MAX_GAPS = 64
_SCALAR = (str, int, float, bool, type(None))


def event_id(origin: str, seq: int) -> str:
    return f"{origin}:{int(seq)}"


def small_notes(notes: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    """The scalar notes an observation carries, and the names of those left out (so a loss is stated, not silent)."""
    kept: Dict[str, Any] = {}
    left: List[str] = []
    for k, v in (notes or {}).items():
        if isinstance(v, _SCALAR) and not (isinstance(v, str) and len(v) > 240):
            kept[str(k)] = v
        else:
            left.append(str(k))
    return kept, left


def make_record(origin: str, seq: int, t: float, before: Dict[str, float], after: Dict[str, float],
                trace: Iterable[Any], notes: Optional[Dict[str, Any]], input_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    kept, left = small_notes(notes)
    rec: Dict[str, Any] = {"v": 1, "origin": str(origin), "seq": int(seq), "t": float(t),
                           "before": {k: float(x) for k, x in before.items()}, "after": {k: float(x) for k, x in after.items()},
                           "trace": [t_.to_dict() for t_ in trace], "notes": kept}
    if left:
        rec["notes_left_out"] = left
    if input_summary:
        rec["input"] = dict(input_summary)
    return rec


class JournalWriter:
    """Buffered append-only writer.  A crash loses at most the buffer, and the loss shows as a seq gap on the consumer."""

    def __init__(self, path: str, flush_every: int = 64):
        self.path = path
        self.flush_every = int(flush_every)
        self._buf: List[str] = []
        self.sent_inputs: set = set()
        self.written = 0

    def append(self, rec: Dict[str, Any]) -> None:
        self._buf.append(json.dumps(rec, sort_keys=True, separators=(",", ":")))
        if len(self._buf) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buf:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            if os.path.exists(self.path) and os.path.getsize(self.path) > MAX_BYTES:
                os.replace(self.path, self.path + ".1")                       # one rotated copy; the consumer reads both
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(self._buf) + "\n")
            self.written += len(self._buf)
            self._buf = []
        except Exception:
            pass                                                              # the journal must never break an observation


def read_records(path: str) -> Tuple[List[Dict[str, Any]], int]:
    """Every readable record from the rotated copy then the journal; (records, malformed lines).  A torn last line is skipped."""
    out: List[Dict[str, Any]] = []
    bad = 0
    for p in (path + ".1", path):
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                        if isinstance(r, dict) and isinstance(r.get("origin"), str) and isinstance(r.get("seq"), int):
                            out.append(r)
                        else:
                            bad += 1
                    except Exception:
                        bad += 1
        except Exception:
            bad += 1
    return out, bad


def _parse(lines: Iterable[bytes]) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    bad = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            r = json.loads(raw.decode("utf-8"))
            if isinstance(r, dict) and isinstance(r.get("origin"), str) and isinstance(r.get("seq"), int):
                out.append(r)
            else:
                bad += 1
        except Exception:
            bad += 1
    return out, bad


def read_since(path: str, offset: int, inode: Optional[int] = None) -> Tuple[List[Dict[str, Any]], int, int, int, bool]:
    """Records appended to `path` after byte `offset`, so a consumer need not parse the whole journal every call.
    Returns (records, malformed, new_offset, inode, restarted).  Only complete lines are consumed (a line still being written is
    left for next time).  If the file was replaced (rotation) or shrank, the read restarts from the beginning of the rotated copy and
    the current file (`restarted` is True); anything already applied is skipped by the applied ledger, so a restart only costs time."""
    try:
        st = os.stat(path)
    except OSError:
        return [], 0, 0, 0, False
    restarted = bool(offset) and (st.st_size < offset or (inode is not None and st.st_ino != inode))
    if restarted:
        offset = 0
    recs: List[Dict[str, Any]] = []
    bad = 0
    if offset == 0 and os.path.exists(path + ".1"):
        try:
            with open(path + ".1", "rb") as fh:
                r, b = _parse(fh.read().splitlines())
            recs += r
            bad += b
        except Exception:
            bad += 1
    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            chunk = fh.read()
    except Exception:
        return recs, bad + 1, offset, st.st_ino, restarted
    end = chunk.rfind(b"\n") + 1                                   # complete lines only
    r, b = _parse(chunk[:end].splitlines())
    return recs + r, bad + b, offset + end, st.st_ino, restarted


def ordered(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per origin in seq order; origins in the order they first appear; an event present twice appears once."""
    seen: Dict[Tuple[str, int], Dict[str, Any]] = {}
    first: Dict[str, int] = {}
    for r in records:
        first.setdefault(r["origin"], len(first))
        seen.setdefault((r["origin"], r["seq"]), r)
    return [seen[k] for k in sorted(seen, key=lambda k: (first[k[0]], k[1]))]


class AppliedLedger:
    """Which events were consolidated.  Per origin: `through` (every seq <= through is applied) and `extra` (applied above a gap)."""

    def __init__(self) -> None:
        self.origins: Dict[str, Dict[str, Any]] = {}
        self.gaps: List[Dict[str, Any]] = []
        self.applied_total = 0
        self.duplicates_skipped = 0
        self.late_applied = 0

    def is_applied(self, origin: str, seq: int) -> bool:
        row = self.origins.get(origin)
        return bool(row) and (seq <= row["through"] or seq in row["extra"])

    def mark(self, origin: str, seq: int) -> None:
        row = self.origins.setdefault(origin, {"through": 0, "extra": []})
        if seq <= row["through"] or seq in row["extra"]:
            return
        row["extra"] = sorted(set(row["extra"]) | {int(seq)})
        while row["extra"] and row["extra"][0] == row["through"] + 1:
            row["through"] = row["extra"].pop(0)
        self.applied_total += 1
        while len(self.origins) > MAX_ORIGINS:
            self.origins.pop(next(iter(self.origins)))

    def note_gap(self, origin: str, lo: int, hi: int) -> None:
        g = {"origin": origin, "missing_from": int(lo), "missing_to": int(hi)}
        if g not in self.gaps:
            self.gaps.append(g)
            del self.gaps[:-MAX_GAPS]

    def open_gaps(self) -> List[Dict[str, Any]]:
        """Gaps whose missing events have still not been applied (a late arrival can fill one)."""
        return [g for g in self.gaps
                if any(not self.is_applied(g["origin"], q) for q in range(g["missing_from"], min(g["missing_to"], g["missing_from"] + 10000) + 1))]

    def through(self, origin: str) -> int:
        return int((self.origins.get(origin) or {}).get("through", 0))

    def to_dict(self) -> Dict[str, Any]:
        return {"version": 1, "origins": self.origins, "gaps": self.gaps, "applied_total": self.applied_total,
                "duplicates_skipped": self.duplicates_skipped, "late_applied": self.late_applied}

    @classmethod
    def from_dict(cls, d: Any) -> "AppliedLedger":
        led = cls()
        if isinstance(d, dict):
            for o, row in (d.get("origins") or {}).items():
                if isinstance(row, dict) and isinstance(row.get("through"), int):
                    led.origins[str(o)] = {"through": int(row["through"]),
                                           "extra": sorted(int(x) for x in row.get("extra", []) if isinstance(x, int))}
            led.gaps = [g for g in (d.get("gaps") or []) if isinstance(g, dict)][-MAX_GAPS:]
            led.applied_total = int(d.get("applied_total", 0) or 0)
            led.duplicates_skipped = int(d.get("duplicates_skipped", 0) or 0)
            led.late_applied = int(d.get("late_applied", 0) or 0)
        return led
