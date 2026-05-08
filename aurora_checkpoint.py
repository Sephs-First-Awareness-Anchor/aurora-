#!/usr/bin/env python3
"""
AURORA CHECKPOINT SYSTEM
========================
Crash-safe persistence for corpus ingestion and memory writes.

FEATURES:
  - Atomic writes: temp file → fsync → rename (never partial writes)
  - Corpus cursor: resume exactly where ingestion left off
  - Memory write integrity gate: schema + coherence + IVM heat validation
  - Rolling stats that survive crashes
  - Save triggers: every N items, every T seconds, on SIGTERM/SIGINT, on exception
  - Quarantine buffer for writes that fail heat/coherence threshold

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import json
import time
import signal
import hashlib
import tempfile
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: CHECKPOINT DATA STRUCTURES
# ============================================================================

class WriteResult(Enum):
    COMMITTED  = "committed"
    QUARANTINED = "quarantined"
    REJECTED   = "rejected"


@dataclass
class CorpusCursor:
    """Tracks exact position in corpus ingestion."""
    file_id:    str   = ""
    file_path:  str   = ""
    byte_offset: int  = 0
    line_index: int   = 0
    chunk_id:   str   = ""
    pass_name:  str   = ""   # observer / responder / reverse
    total_items_processed: int = 0
    last_item_hash: str = ""
    last_save_time: float = field(default_factory=time.time)

    def advance(self, line_index: int, byte_offset: int, item_hash: str,
                chunk_id: str = ""):
        self.line_index   = line_index
        self.byte_offset  = byte_offset
        self.last_item_hash = item_hash
        self.chunk_id     = chunk_id
        self.total_items_processed += 1

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "CorpusCursor":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RollingStats:
    """Rolling statistics that survive crashes."""
    defs_learned:      int   = 0
    relations_added:   int   = 0
    clusters_formed:   int   = 0
    memory_commits:    int   = 0
    quarantined:       int   = 0
    rejected:          int   = 0
    session_start:     float = field(default_factory=time.time)
    total_save_count:  int   = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "RollingStats":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CheckpointRecord:
    """Full checkpoint snapshot."""
    version:     str   = "1.0"
    cursor:      Dict  = field(default_factory=dict)
    stats:       Dict  = field(default_factory=dict)
    timestamp:   float = field(default_factory=time.time)
    checksum:    str   = ""

    def compute_checksum(self) -> str:
        data = json.dumps({"cursor": self.cursor, "stats": self.stats,
                           "timestamp": self.timestamp}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["checksum"] = self.compute_checksum()
        return d

    def is_valid(self) -> bool:
        expected = self.compute_checksum()
        return self.checksum == expected


# ============================================================================
# SECTION 2: WRITE VALIDATION
# ============================================================================

class WriteValidator:
    """
    Validates memory writes before committing to disk.
    Prevents corrupted or contradictory writes from poisoning memory.
    """

    # Required fields for each write type
    SCHEMAS: Dict[str, List[str]] = {
        "semantic_node": ["word", "definitions", "ontological_depth"],
        "relation":      ["source_word", "target_word", "relation_type"],
        "study_event":   ["timestamp", "studied_items"],
        "memory":        ["timestamp", "content"],
        "state":         ["version", "generation"],
    }

    def __init__(self,
                 coherence_threshold: float = 0.3,
                 heat_limit: float = 0.85,
                 ivm_lattice=None):
        self.coherence_threshold = coherence_threshold
        self.heat_limit = heat_limit
        self._ivm_lattice = ivm_lattice  # Optional: IVMLattice for heat check

    def set_ivm(self, lattice):
        self._ivm_lattice = lattice

    def validate(self, write_type: str, payload: Dict,
                 coherence: float = 1.0) -> WriteResult:
        """
        Validate a write before committing.
        Returns COMMITTED, QUARANTINED, or REJECTED.
        """
        # 1. Schema validation
        required = self.SCHEMAS.get(write_type, [])
        for field_name in required:
            if field_name not in payload:
                logger.debug(f"[Checkpoint] Schema fail: missing '{field_name}' in {write_type}")
                return WriteResult.REJECTED

        # 2. Coherence threshold
        if coherence < self.coherence_threshold:
            logger.debug(f"[Checkpoint] Coherence too low ({coherence:.2f}) — quarantining {write_type}")
            return WriteResult.QUARANTINED

        # 3. IVM heat limit
        if self._ivm_lattice is not None:
            try:
                heat = self._ivm_lattice.get_global_heat()
                if heat > self.heat_limit:
                    logger.debug(f"[Checkpoint] IVM heat {heat:.2f} > limit — quarantining {write_type}")
                    return WriteResult.QUARANTINED
            except Exception:
                pass

        return WriteResult.COMMITTED


# ============================================================================
# SECTION 3: ATOMIC WRITER
# ============================================================================

class AtomicWriter:
    """Atomic file write: temp → fsync → rename. Never leaves partial files."""

    @staticmethod
    def write(path: str, data: Dict) -> bool:
        """Write dict as JSON atomically. Returns True on success."""
        dir_path = os.path.dirname(os.path.abspath(path))
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)  # atomic on POSIX
                return True
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"[AtomicWriter] Failed writing {path}: {e}")
            return False

    @staticmethod
    def append_jsonl(path: str, record: Dict) -> bool:
        """Append a JSON record to a .jsonl file (not atomic, but safe for logs)."""
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(record) + "\n")
            return True
        except Exception as e:
            logger.error(f"[AtomicWriter] Failed appending to {path}: {e}")
            return False


# ============================================================================
# SECTION 4: CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager:
    """
    Central checkpoint coordinator.

    Usage:
        ckpt = CheckpointManager("aurora_state/checkpoint.json")
        ckpt.restore()               # load last checkpoint on startup
        ckpt.advance(cursor_kwargs)  # update position after each item
        ckpt.save()                  # explicit save
        ckpt.start_auto_save(300)    # background thread saves every 5 min
    """

    QUARANTINE_PATH_SUFFIX = "_quarantine.jsonl"

    def __init__(self,
                 checkpoint_path: str = "aurora_state/checkpoint.json",
                 save_every_n: int = 500,
                 save_every_t: float = 300.0,
                 coherence_threshold: float = 0.3,
                 heat_limit: float = 0.85):

        self.checkpoint_path = checkpoint_path
        self.quarantine_path = checkpoint_path.replace(".json", self.QUARANTINE_PATH_SUFFIX)
        self.save_every_n    = save_every_n
        self.save_every_t    = save_every_t

        self.cursor  = CorpusCursor()
        self.stats   = RollingStats()
        self.validator = WriteValidator(coherence_threshold, heat_limit)

        self._lock           = threading.Lock()
        self._last_save_time = time.time()
        self._items_since_save = 0
        self._auto_save_thread: Optional[threading.Thread] = None
        self._running        = False
        self._on_save_callbacks: List[Callable] = []

        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT,  self._signal_handler)
        except (OSError, ValueError):
            pass  # Not in main thread — skip

    # ----------------------------------------------------------------
    # Signal / shutdown
    # ----------------------------------------------------------------

    def _signal_handler(self, signum, frame):
        logger.info(f"[Checkpoint] Signal {signum} — saving before exit")
        self.save()
        raise SystemExit(0)

    # ----------------------------------------------------------------
    # Restore
    # ----------------------------------------------------------------

    def restore(self) -> bool:
        """Load last checkpoint. Returns True if restored."""
        if not os.path.exists(self.checkpoint_path):
            return False
        try:
            with open(self.checkpoint_path) as f:
                raw = json.load(f)
            record = CheckpointRecord(**raw)
            if not record.is_valid():
                logger.warning("[Checkpoint] Checksum mismatch — ignoring corrupt checkpoint")
                return False
            self.cursor = CorpusCursor.from_dict(record.cursor)
            self.stats  = RollingStats.from_dict(record.stats)
            logger.info(f"[Checkpoint] Restored from {self.checkpoint_path} "
                        f"(line {self.cursor.line_index}, "
                        f"{self.cursor.total_items_processed} items processed)")
            return True
        except Exception as e:
            logger.error(f"[Checkpoint] Restore failed: {e}")
            return False

    # ----------------------------------------------------------------
    # Cursor advance
    # ----------------------------------------------------------------

    def advance(self, line_index: int = 0, byte_offset: int = 0,
                item_hash: str = "", chunk_id: str = "",
                file_path: str = "", pass_name: str = ""):
        """Update cursor position. Triggers auto-save if thresholds met."""
        with self._lock:
            if file_path:
                self.cursor.file_path = file_path
            if pass_name:
                self.cursor.pass_name = pass_name
            self.cursor.advance(line_index, byte_offset, item_hash, chunk_id)
            self._items_since_save += 1

        # Check thresholds (outside lock to avoid deadlock with auto-save thread)
        self._maybe_save()

    def _maybe_save(self):
        n_trigger = self._items_since_save >= self.save_every_n
        t_trigger = (time.time() - self._last_save_time) >= self.save_every_t
        if n_trigger or t_trigger:
            self.save()

    # ----------------------------------------------------------------
    # Stats update
    # ----------------------------------------------------------------

    def record(self, **kwargs):
        """Increment rolling stats. kwargs: defs_learned=1, relations_added=3, etc."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.stats, k):
                    setattr(self.stats, k, getattr(self.stats, k) + v)

    # ----------------------------------------------------------------
    # Memory write transaction
    # ----------------------------------------------------------------

    def write_transaction(self, write_type: str, payload: Dict,
                          coherence: float = 1.0,
                          target_path: Optional[str] = None) -> WriteResult:
        """
        Validate + atomically write a memory record.
        If validation fails → quarantine buffer.
        """
        result = self.validator.validate(write_type, payload, coherence)

        if result == WriteResult.COMMITTED:
            if target_path:
                AtomicWriter.write(target_path, payload)
            self.stats.memory_commits += 1
        elif result == WriteResult.QUARANTINED:
            quarantine_record = {
                "timestamp": time.time(),
                "write_type": write_type,
                "payload": payload,
                "coherence": coherence,
                "reason": "failed_validation"
            }
            AtomicWriter.append_jsonl(self.quarantine_path, quarantine_record)
            self.stats.quarantined += 1
        else:
            self.stats.rejected += 1

        return result

    # ----------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------

    def save(self) -> bool:
        """Atomically save checkpoint."""
        with self._lock:
            record = CheckpointRecord(
                cursor=self.cursor.to_dict(),
                stats=self.stats.to_dict(),
                timestamp=time.time(),
            )
            d = record.to_dict()
            ok = AtomicWriter.write(self.checkpoint_path, d)
            if ok:
                self._last_save_time = time.time()
                self._items_since_save = 0
                self.stats.total_save_count += 1
                for cb in self._on_save_callbacks:
                    try:
                        cb(record)
                    except Exception:
                        pass
            return ok

    def on_save(self, callback: Callable):
        """Register a callback called after each successful save."""
        self._on_save_callbacks.append(callback)

    # ----------------------------------------------------------------
    # Auto-save background thread
    # ----------------------------------------------------------------

    def start_auto_save(self, interval_seconds: float = None):
        """Start background thread that saves every interval_seconds."""
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            return
        interval = interval_seconds or self.save_every_t
        self._running = True

        def _loop():
            while self._running:
                time.sleep(interval)
                if self._running:
                    self.save()

        self._auto_save_thread = threading.Thread(target=_loop, daemon=True,
                                                   name="CheckpointAutoSave")
        self._auto_save_thread.start()

    def stop_auto_save(self):
        self._running = False

    # ----------------------------------------------------------------
    # IVM integration
    # ----------------------------------------------------------------

    def set_ivm(self, lattice):
        self.validator.set_ivm(lattice)

    # ----------------------------------------------------------------
    # Status
    # ----------------------------------------------------------------

    def status(self) -> Dict:
        with self._lock:
            return {
                "cursor": self.cursor.to_dict(),
                "stats":  self.stats.to_dict(),
                "checkpoint_path": self.checkpoint_path,
                "items_since_save": self._items_since_save,
                "auto_save_running": (self._auto_save_thread is not None and
                                      self._auto_save_thread.is_alive()),
            }
