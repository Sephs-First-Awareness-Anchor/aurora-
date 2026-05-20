"""
aurora_offline_resilience.py

Mobile connectivity resilience layer for Aurora.

When search/network tools are unavailable (no internet), Aurora falls back to
asking the user or other interactive entities for help with whatever she was
curious about.  Answers are stored as *provisional knowledge* — held at an
epistemic confidence level tied to how reliable that source has proven to be.
When connectivity returns, queued items are verified against the web and either
promoted to sedimemory or flagged as contradicted.

Key pieces
──────────
  check_connectivity()          Quick DNS probe, result cached for 20 s
  SourceTrustRegistry           Tracks per-source reliability over time
  ProvisionalStore              Persisted provisional knowledge with confidence
  write_pending_question()      Surfaces a curiosity gap to the user
  answer_pending_question()     Records the user's response
  run_verification_sweep()      Verifies pending items when back online
  ConnectivityMonitor           Background thread — fires on_online/on_offline
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths (resolved relative to repo root, not this file's parent)
# ---------------------------------------------------------------------------
_STATE_DIR             = Path(__file__).resolve().parent.parent / "aurora_state"
_PROVISIONAL_FILE      = _STATE_DIR / "provisional_knowledge.json"
_SOURCE_TRUST_FILE     = _STATE_DIR / "source_trust.json"
_PENDING_QUESTION_FILE = _STATE_DIR / "pending_curiosity_question.json"

_STATE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _write_json(path: Path, data: Any) -> None:
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        pass


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------
_conn_cache: Dict[str, Any] = {"ok": None, "ts": 0.0}
_CONN_TTL = 20.0  # re-probe at most every 20 s


def check_connectivity(timeout: float = 3.0) -> bool:
    """Return True if the device can reach the internet. Result is cached."""
    now = time.time()
    if now - _conn_cache["ts"] < _CONN_TTL and _conn_cache["ok"] is not None:
        return bool(_conn_cache["ok"])
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("8.8.8.8", 53))
        s.close()
        ok = True
    except Exception:
        ok = False
    _conn_cache.update(ok=ok, ts=time.time())
    return ok


# ---------------------------------------------------------------------------
# Source trust
# ---------------------------------------------------------------------------
@dataclass
class SourceTrust:
    source_id: str
    verified_correct: int = 0
    verified_wrong: int = 0
    total_given: int = 0

    @property
    def trust_score(self) -> float:
        verified = self.verified_correct + self.verified_wrong
        return (self.verified_correct / verified) if verified > 0 else 0.5

    @property
    def absorb_faithfully(self) -> bool:
        """True when this source has proven reliable enough to skip provisional staging."""
        return self.trust_score >= 0.80 and self.verified_correct >= 3


class SourceTrustRegistry:
    """Persisted per-source reliability tracker."""

    def __init__(self, path: Path = _SOURCE_TRUST_FILE) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: Dict[str, SourceTrust] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text("utf-8"))
                known = set(SourceTrust.__dataclass_fields__)
                for sid, vals in raw.items():
                    self._data[sid] = SourceTrust(**{k: v for k, v in vals.items() if k in known})
        except Exception:
            pass

    def _save(self) -> None:
        _write_json(self._path, {sid: asdict(st) for sid, st in self._data.items()})

    def get(self, source_id: str) -> SourceTrust:
        with self._lock:
            if source_id not in self._data:
                self._data[source_id] = SourceTrust(source_id=source_id)
            return self._data[source_id]

    def record_contribution(self, source_id: str) -> None:
        with self._lock:
            self._data.setdefault(source_id, SourceTrust(source_id=source_id)).total_given += 1
            self._save()

    def record_verification(self, source_id: str, correct: bool) -> None:
        with self._lock:
            st = self._data.setdefault(source_id, SourceTrust(source_id=source_id))
            if correct:
                st.verified_correct += 1
            else:
                st.verified_wrong += 1
            self._save()

    def trust_score(self, source_id: str) -> float:
        return self.get(source_id).trust_score

    def absorbs_faithfully(self, source_id: str) -> bool:
        return self.get(source_id).absorb_faithfully


# ---------------------------------------------------------------------------
# Provisional knowledge
# ---------------------------------------------------------------------------
@dataclass
class ProvisionalEntry:
    uid: str
    question: str
    answer: str
    source: str
    source_trust_at_receipt: float
    confidence: float
    absorbed: bool = False
    verify_status: str = "pending"      # pending | verified | contradicted | unverifiable
    contradiction_note: str = ""
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    verify_attempts: int = 0


class ProvisionalStore:
    """
    Persisted store for things Aurora has been told but not yet verified.

    Confidence is initialised from the source's historical trust score.
    When the source has proven highly reliable (absorb_faithfully=True),
    items are marked absorbed immediately — no verification gate required.
    """

    MAX_VERIFY_ATTEMPTS = 3

    def __init__(
        self,
        path: Path = _PROVISIONAL_FILE,
        trust_registry: Optional[SourceTrustRegistry] = None,
    ) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._entries: Dict[str, ProvisionalEntry] = {}
        self._trust = trust_registry or SourceTrustRegistry()
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text("utf-8"))
                known = set(ProvisionalEntry.__dataclass_fields__)
                for uid, vals in raw.items():
                    self._entries[uid] = ProvisionalEntry(
                        **{k: v for k, v in vals.items() if k in known}
                    )
        except Exception:
            pass

    def _save(self) -> None:
        _write_json(self._path, {uid: asdict(e) for uid, e in self._entries.items()})

    def add(self, question: str, answer: str, source: str) -> ProvisionalEntry:
        """Store a provisional answer. Returns the created entry."""
        st = self._trust.get(source)
        self._trust.record_contribution(source)
        uid = f"prov_{int(time.time()*1000)}_{abs(hash(question)) % 9999:04d}"
        entry = ProvisionalEntry(
            uid=uid,
            question=question,
            answer=answer,
            source=source,
            source_trust_at_receipt=st.trust_score,
            confidence=st.trust_score,
            absorbed=st.absorb_faithfully,
        )
        with self._lock:
            self._entries[uid] = entry
            self._save()
        return entry

    def pending_verification(self) -> List[ProvisionalEntry]:
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.verify_status == "pending"
                and e.verify_attempts < self.MAX_VERIFY_ATTEMPTS
            ]

    def mark_verified(self, uid: str, correct: bool, note: str = "") -> None:
        with self._lock:
            e = self._entries.get(uid)
            if e is None:
                return
            e.verify_status = "verified" if correct else "contradicted"
            e.contradiction_note = note
            e.verified_at = time.time()
            e.confidence = min(1.0, e.confidence + 0.3) if correct else max(0.0, e.confidence - 0.3)
            e.absorbed = correct
            self._trust.record_verification(e.source, correct=correct)
            self._save()

    def mark_unverifiable(self, uid: str) -> None:
        with self._lock:
            e = self._entries.get(uid)
            if e is None:
                return
            e.verify_attempts += 1
            if e.verify_attempts >= self.MAX_VERIFY_ATTEMPTS:
                e.verify_status = "unverifiable"
            self._save()

    def summary(self) -> Dict[str, int]:
        with self._lock:
            out: Dict[str, int] = {}
            for e in self._entries.values():
                out[e.verify_status] = out.get(e.verify_status, 0) + 1
            return out


# ---------------------------------------------------------------------------
# Pending question (curiosity → user)
# ---------------------------------------------------------------------------

def write_pending_question(
    question: str,
    context: str = "",
    uid: Optional[str] = None,
    messages_path: Optional[Path] = None,
) -> str:
    """
    Surface a curiosity gap to the user.
    Writes to the pending-question file AND pushes to the proactive message queue
    so the mobile runner speaks it aloud.
    Returns the question UID.
    """
    if uid is None:
        uid = f"q_{int(time.time()*1000)}"

    _write_json(_PENDING_QUESTION_FILE, {
        "uid": uid,
        "question": question,
        "context": context,
        "asked_at": time.time(),
        "answered": False,
        "answer": None,
    })

    msgs_path = messages_path or (_STATE_DIR / "aurora_to_user.json")
    try:
        msgs = _read_json(msgs_path, [])
        if not isinstance(msgs, list):
            msgs = []
        msgs.append({
            "id": uid,
            "text": question,
            "type": "curiosity_question",
            "read": False,
            "created_at": time.time(),
        })
        _write_json(msgs_path, msgs)
    except Exception:
        pass

    return uid


def read_pending_question() -> Optional[Dict[str, Any]]:
    """Return the current unanswered pending question, or None."""
    try:
        if _PENDING_QUESTION_FILE.exists():
            data = json.loads(_PENDING_QUESTION_FILE.read_text("utf-8"))
            if not data.get("answered"):
                return data
    except Exception:
        pass
    return None


def answer_pending_question(answer: str) -> Optional[Dict[str, Any]]:
    """
    Record an answer to the current pending question.
    Returns the question data dict (including the answer), or None if no
    pending question exists.
    """
    try:
        if not _PENDING_QUESTION_FILE.exists():
            return None
        data = json.loads(_PENDING_QUESTION_FILE.read_text("utf-8"))
        if data.get("answered"):
            return None
        data.update(answered=True, answer=answer, answered_at=time.time())
        _write_json(_PENDING_QUESTION_FILE, data)
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Verification sweep
# ---------------------------------------------------------------------------

def run_verification_sweep(
    store: ProvisionalStore,
    verify_fn: Optional[Callable[[str, str], Optional[bool]]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> int:
    """
    Called when connectivity is restored.  Attempts to verify pending provisional
    items using verify_fn(question, answer) → True | False | None.
    Returns the number of items processed.
    """
    if not check_connectivity():
        return 0
    pending = store.pending_verification()
    if not pending:
        return 0
    if log_fn:
        log_fn(f"  [VERIFY] Sweep: {len(pending)} provisional item(s) to check.")
    processed = 0
    for entry in pending:
        if verify_fn is not None:
            try:
                result = verify_fn(entry.question, entry.answer)
                if result is True:
                    store.mark_verified(entry.uid, correct=True)
                    if log_fn:
                        log_fn(f"  [VERIFY] Confirmed: {entry.question[:70]}")
                elif result is False:
                    store.mark_verified(entry.uid, correct=False, note="Contradicted online.")
                    if log_fn:
                        log_fn(f"  [VERIFY] Contradicted: {entry.question[:70]}")
                else:
                    store.mark_unverifiable(entry.uid)
                processed += 1
            except Exception:
                store.mark_unverifiable(entry.uid)
        else:
            store.mark_unverifiable(entry.uid)
            processed += 1
    return processed


# ---------------------------------------------------------------------------
# Connectivity monitor
# ---------------------------------------------------------------------------

class ConnectivityMonitor:
    """
    Background thread that watches for connectivity state transitions.
    Fires on_online() when connection is gained, on_offline() when lost.
    """

    def __init__(
        self,
        on_online: Optional[Callable] = None,
        on_offline: Optional[Callable] = None,
        poll_interval: float = 30.0,
    ) -> None:
        self._on_online = on_online
        self._on_offline = on_offline
        self._interval = poll_interval
        self._last: Optional[bool] = None
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="aurora-connectivity-monitor"
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def is_online(self) -> bool:
        return bool(self._last)

    def _loop(self) -> None:
        _conn_cache["ts"] = 0.0  # force immediate probe on start
        while not self._stop.is_set():
            now = check_connectivity()
            if self._last is not None and now != self._last:
                cb = self._on_online if now else self._on_offline
                if cb:
                    try:
                        cb()
                    except Exception:
                        pass
            self._last = now
            self._stop.wait(self._interval)
