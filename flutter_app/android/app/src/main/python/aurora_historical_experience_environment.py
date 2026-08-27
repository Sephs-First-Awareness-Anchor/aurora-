from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

try:
    from aurora_persistence_utils import atomic_write_json
except Exception:
    atomic_write_json = None


_REQUIRED_ARCHIVE_MEMBERS = ("manifest.json", "episodes.jsonl", "events.jsonl")
_STATE_SCHEMA = "aurora_historical_experience_runtime_v2"
_DEFAULT_ARCHIVE_NAME = "experiential_baseline_v1.zip"
_MAX_PENDING_USER_TEXT = 12000


def _safe_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def _utc_iso(timestamp: Any) -> str:
    value = _safe_float(timestamp)
    if value is None:
        return ""
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    except Exception:
        return ""


def _stable_baseline_id(manifest: Mapping[str, Any], archive_path: Path) -> str:
    material = {
        "schema": str(manifest.get("schema", "")),
        "event_count": int(manifest.get("event_count", 0) or 0),
        "episode_count": int(manifest.get("episode_count", 0) or 0),
        "first_event_utc": str(manifest.get("first_event_utc", "")),
        "last_event_utc": str(manifest.get("last_event_utc", "")),
        "archive_size": int(archive_path.stat().st_size if archive_path.exists() else 0),
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class HistoricalExperienceEnvironment:
    """Chronological witness environment for prior dialogue records.

    This runtime deliberately does not classify historical statements as facts,
    does not compare Aurora against a historical assistant response, and does
    not submit historical turns through the live user-turn pipeline.  Each
    event is admitted as an observed environmental signal with its provenance,
    actor, chronology, and epistemic status intact.  Aurora's existing physics
    decide what, if anything, becomes durable structure afterward.
    """

    def __init__(
        self,
        systems: Mapping[str, Any],
        *,
        state_dir: str,
        archive_path: Optional[str] = None,
        field_lock: Optional[threading.Lock] = None,
        live_idle: Optional[Callable[[], bool]] = None,
        initial_delay_s: float = 8.0,
        crystal_checkpoint_interval: int = 100,
    ) -> None:
        self.systems = systems if isinstance(systems, dict) else dict(systems or {})
        self.state_dir = Path(state_dir or "aurora_state")
        self.archive_path = Path(archive_path) if archive_path else self.state_dir / _DEFAULT_ARCHIVE_NAME
        self.runtime_dir = self.state_dir / "historical_experience"
        self.extract_dir = self.runtime_dir / "baseline_v1"
        self.state_path = self.runtime_dir / "runtime_state.json"
        self.ledger_path = self.runtime_dir / "experience_ledger.jsonl"
        self.field_lock = field_lock
        self.live_idle = live_idle or (lambda: True)
        self.initial_delay_s = max(0.0, float(initial_delay_s or 0.0))
        self.crystal_checkpoint_interval = max(1, int(crystal_checkpoint_interval or 100))

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._prepared = False
        self._manifest: Dict[str, Any] = {}
        self._episodes: Dict[str, Dict[str, Any]] = {}
        self._baseline_id = ""
        self._state: Dict[str, Any] = {}
        self._state_guard = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        if not self.archive_path.exists():
            with self._state_guard:
                self._state = {
                    "schema": _STATE_SCHEMA,
                    "status": "baseline_missing",
                    "archive_path": str(self.archive_path),
                    "updated_at": time.time(),
                }
            self._persist_state()
            return False
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="aurora_historical_experience",
        )
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, float(timeout or 0.0)))
        self._thread = None

    def pause(self) -> None:
        self._pause.set()
        with self._state_guard:
            self._state["status"] = "paused"
            self._state["updated_at"] = time.time()
        self._persist_state()

    def resume(self) -> None:
        self._pause.clear()
        with self._state_guard:
            if not self._state.get("completed"):
                self._state["status"] = "running"
            self._state["updated_at"] = time.time()
        self._persist_state()

    def status(self) -> Dict[str, Any]:
        with self._state_guard:
            state = dict(self._state or {})
        state.setdefault("schema", _STATE_SCHEMA)
        state["thread_alive"] = bool(self._thread and self._thread.is_alive())
        state["paused"] = self._pause.is_set()
        state["archive_present"] = self.archive_path.exists()
        total = int(self._manifest.get("event_count", 0) or state.get("total_events", 0) or 0)
        done = int(state.get("events_experienced", 0) or 0)
        state["total_events"] = total
        state["progress"] = round(done / total, 6) if total else 0.0
        return state

    # ------------------------------------------------------------------
    # Preparation / persistence
    # ------------------------------------------------------------------

    def _last_ledger_record(self) -> Dict[str, Any]:
        """Read only the last committed witness record, if any."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size <= 0:
            return {}
        try:
            with self.ledger_path.open("rb") as fh:
                fh.seek(0, os.SEEK_END)
                end = fh.tell()
                pos = end
                buf = b""
                while pos > 0 and b"\n" not in buf:
                    step = min(4096, pos)
                    pos -= step
                    fh.seek(pos)
                    buf = fh.read(step) + buf
                lines = [line for line in buf.splitlines() if line.strip()]
                if not lines:
                    return {}
                return json.loads(lines[-1].decode("utf-8"))
        except Exception:
            return {}

    def _events_path(self) -> Path:
        legacy = self.extract_dir / "events.jsonl"
        compressed = self.extract_dir / "events.jsonl.gz"
        return legacy if legacy.exists() else compressed

    def _open_events(self):
        path = self._events_path()
        if path.suffix == ".gz":
            return gzip.open(path, "rt", encoding="utf-8")
        return path.open("r", encoding="utf-8")

    def _prepare(self) -> None:
        if self._prepared:
            return
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(self.archive_path, "r") as zf:
            names = set(zf.namelist())
            missing = [name for name in _REQUIRED_ARCHIVE_MEMBERS if name not in names]
            if missing:
                raise ValueError(f"historical baseline missing required members: {missing}")
            for name in _REQUIRED_ARCHIVE_MEMBERS:
                target = self.extract_dir / name
                compressed_target = target.with_suffix(target.suffix + ".gz")
                if target.exists() and target.stat().st_size > 0:
                    continue
                if name == "events.jsonl" and compressed_target.exists() and compressed_target.stat().st_size > 0:
                    continue
                # Codex review, PR #176: extracting straight to `target`
                # meant that if the process died mid-extraction (Android
                # can kill it at any time), a nonempty but truncated file
                # was left behind -- and the check above ("exists and
                # size > 0") would then treat that truncated file as
                # already-extracted on the next boot forever, silently
                # dropping the rest of the baseline. Extract to a sibling
                # temp file, verify its size against the archive's own
                # record of the uncompressed member size, and only then
                # atomically rename it into place -- `target` never exists
                # in a partially-written state.
                expected_size = zf.getinfo(name).file_size
                tmp_target = target.with_suffix(target.suffix + ".part")
                with zf.open(name, "r") as src, tmp_target.open("wb") as dst:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                actual_size = tmp_target.stat().st_size
                if actual_size != expected_size:
                    try:
                        tmp_target.unlink()
                    except OSError:
                        pass
                    raise ValueError(
                        f"historical baseline extraction incomplete for {name}: "
                        f"expected {expected_size} bytes, got {actual_size}"
                    )
                tmp_target.replace(target)

        self._manifest = json.loads((self.extract_dir / "manifest.json").read_text(encoding="utf-8"))
        self._baseline_id = _stable_baseline_id(self._manifest, self.archive_path)

        episodes: Dict[str, Dict[str, Any]] = {}
        with (self.extract_dir / "episodes.jsonl").open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                eid = str(record.get("episode_id", "") or "")
                if eid:
                    episodes[eid] = record
        self._episodes = episodes

        previous: Dict[str, Any] = {}
        if self.state_path.exists():
            try:
                previous = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        if str(previous.get("baseline_id", "")) != self._baseline_id:
            previous = {}

        # The witness ledger is appended immediately after a successful
        # environmental admission and before runtime_state.json is advanced.
        # If Android kills the process in that narrow interval, reconcile from
        # the ledger so the already-lived event is not replayed on restart.
        ledger_tail = self._last_ledger_record()
        if (
            str(ledger_tail.get("baseline_id", "")) == self._baseline_id
            and int(ledger_tail.get("event_index_after", 0) or 0)
                > int(previous.get("event_index", 0) or 0)
        ):
            previous = {
                **previous,
                "event_index": int(ledger_tail.get("event_index_after", 0) or 0),
                "byte_offset": int(ledger_tail.get("next_byte_offset", 0) or 0),
                "events_experienced": int(ledger_tail.get("events_experienced_after", 0) or 0),
                "episodes_entered": int(ledger_tail.get("episodes_entered_after", previous.get("episodes_entered", 0)) or 0),
                "current_episode_id": str(ledger_tail.get("episode_id", "") or ""),
                "last_event_id": str(ledger_tail.get("event_id", "") or ""),
                "last_actor": str(ledger_tail.get("actor", "") or ""),
                "last_observed_timestamp": ledger_tail.get("observed_timestamp"),
            }

        # Runtime cursor/ledger records are not durable developmental evidence
        # unless the crystal substrate was checkpointed at the same position.
        # On restart, replay any witnessed-but-uncheckpointed tail so Aurora does
        # not claim experiences whose retained crystal consequences were lost.
        durable = previous.get("crystal_checkpoint") if isinstance(previous.get("crystal_checkpoint"), dict) else None
        if durable is None:
            # New baseline runtime (or pre-checkpoint migration): no crystal-backed
            # historical cursor has been proven yet.
            durable = {
                "event_index": 0, "byte_offset": 0, "events_experienced": 0,
                "episodes_entered": 0, "current_episode_id": "",
                "last_event_id": "", "last_actor": "",
                "last_observed_timestamp": None,
            }
        if int(previous.get("event_index", 0) or 0) > int(durable.get("event_index", 0) or 0):
            previous = {
                **previous,
                **durable,
                # A user surface witnessed after the last durable substrate
                # checkpoint cannot remain paired with an assistant surface
                # that will be replayed.  Restore the checkpoint's exact
                # apprenticeship boundary instead.
                "communication_apprenticeship": dict(
                    durable.get("communication_apprenticeship") or {}
                ),
                "completed": False,
            }

        self._state = {
            "schema": _STATE_SCHEMA,
            "baseline_id": self._baseline_id,
            "status": "completed" if bool(previous.get("completed")) else "running",
            "completed": bool(previous.get("completed", False)),
            "event_index": int(previous.get("event_index", 0) or 0),
            "byte_offset": int(previous.get("byte_offset", 0) or 0),
            "events_experienced": int(previous.get("events_experienced", 0) or 0),
            "episodes_entered": int(previous.get("episodes_entered", 0) or 0),
            "current_episode_id": str(previous.get("current_episode_id", "") or ""),
            "last_event_id": str(previous.get("last_event_id", "") or ""),
            "last_actor": str(previous.get("last_actor", "") or ""),
            "last_observed_timestamp": previous.get("last_observed_timestamp"),
            "last_error": str(previous.get("last_error", "") or ""),
            "started_at": previous.get("started_at") or time.time(),
            "updated_at": time.time(),
            "completed_at": previous.get("completed_at"),
            "total_events": int(self._manifest.get("event_count", 0) or 0),
            "total_episodes": int(self._manifest.get("episode_count", 0) or 0),
            "archive_path": str(self.archive_path),
            "crystal_checkpoint": dict(durable),
            "crystal_checkpoint_event_index": int(durable.get("event_index", 0) or 0),
            "crystal_checkpoint_at": previous.get("crystal_checkpoint_at"),
            "communication_apprenticeship": dict(
                previous.get("communication_apprenticeship") or {
                    "pairs_observed": 0,
                    "structural_possibilities": 0,
                    "representable_gaps": 0,
                    "counterfactual_observations": 0,
                    "pending_user": {},
                }
            ),
        }
        self._persist_state()
        self._prepared = True
        self._backfill_communication_apprenticeship()

    def _backfill_communication_apprenticeship(self) -> None:
        """Migrate an already-witnessed prefix into communication development.

        Builds prior to runtime-v2 admitted historical events only through the
        sensor gateway.  Replaying those events through the gateway would
        duplicate lived experience and crystals, so this migration reads only
        their chronological exchange boundary and submits paired structural
        possibilities directly to the existing communication cultivator.
        Possibility IDs are durable and idempotent inside that cultivator.
        """
        communication = self.systems.get("communication_emergence")
        if communication is None or not hasattr(communication, "observe_structural_possibility"):
            return
        state = dict(self._state.get("communication_apprenticeship") or {})
        durable_index = int(self._state.get("event_index", 0) or 0)
        backfilled = int(state.get("backfilled_through_event_index", 0) or 0)
        if durable_index <= 0 or backfilled >= durable_index:
            return

        pending: Dict[str, Any] = dict(state.get("pending_user") or {}) if backfilled else {}
        pairs = int(state.get("pairs_observed", 0) or 0)
        supports = int(state.get("structural_possibilities", 0) or 0)
        gaps = int(state.get("representable_gaps", 0) or 0)
        admitted = int(state.get("counterfactual_observations", 0) or 0)
        last_pair: Dict[str, Any] = dict(state.get("last_pair") or {})
        processed = 0
        try:
            with self._open_events() as fh:
                for index, line in enumerate(fh):
                    if index >= durable_index:
                        break
                    if index < backfilled or not line.strip():
                        continue
                    try:
                        event = dict(json.loads(line) or {})
                    except Exception:
                        continue
                    processed = index + 1
                    actor = self._actor_label(str(event.get("actor", "") or ""))
                    episode_id = str(event.get("episode_id", "") or "")
                    if pending and str(pending.get("episode_id", "") or "") != episode_id:
                        pending = {}
                    if actor == "historical_user":
                        raw = str(event.get("text", "") or "").strip()
                        pending = {
                            "event_id": str(event.get("event_id", "") or ""),
                            "episode_id": episode_id,
                            "text": raw[:_MAX_PENDING_USER_TEXT],
                            "observed_timestamp": event.get("timestamp"),
                        } if raw else {}
                        continue
                    if actor != "historical_other_assistant" or not pending:
                        continue
                    pairs += 1
                    event_id = str(event.get("event_id", "") or "")
                    result = dict(communication.observe_structural_possibility(
                        raw_text=str(pending.get("text", "") or ""),
                        observed_response_text=str(event.get("text", "") or ""),
                        possibility_id=(
                            f"{self._baseline_id}:{pending.get('event_id', '')}:{event_id}"
                        ),
                        observed_source="historical_other_assistant",
                        epistemic_status=str(
                            event.get("epistemic_status", "observation_not_truth")
                            or "observation_not_truth"
                        ),
                        causal_status=str(
                            event.get("causal_status", "sequence_observed_causality_not_asserted")
                            or "sequence_observed_causality_not_asserted"
                        ),
                        defer_persistence=True,
                    ) or {})
                    if result.get("structural_support"):
                        supports += 1
                    if result.get("representable_gap"):
                        gaps += 1
                    if result.get("admitted"):
                        admitted += 1
                    last_pair = {
                        "user_event_id": str(pending.get("event_id", "") or ""),
                        "possibility_event_id": event_id,
                        "possibility_id": str(result.get("possibility_id", "") or ""),
                        "representable_gap": bool(result.get("representable_gap", False)),
                        "trial_component_id": str(result.get("trial_component_id", "") or ""),
                    }
                    pending = {}
        except Exception as exc:
            state["backfill_error"] = f"{type(exc).__name__}: {exc}"[:240]
            self._state["communication_apprenticeship"] = state
            return

        # Commit the communication/WARP substrate before claiming the prefix
        # in runtime state.  If the process dies first, stable possibility IDs
        # make the next attempt harmless.
        try:
            saved = bool(communication.save()) if hasattr(communication, "save") else False
        except Exception:
            saved = False
        if not saved:
            state["backfill_error"] = "communication checkpoint failed"
            self._state["communication_apprenticeship"] = state
            return

        state.update({
            "pairs_observed": pairs,
            "structural_possibilities": supports,
            "representable_gaps": gaps,
            "counterfactual_observations": admitted,
            "pending_user": pending,
            "last_pair": last_pair,
            "backfilled_through_event_index": max(backfilled, processed),
            "backfill_status": "completed",
            "backfill_completed_at": time.time(),
        })
        state.pop("backfill_error", None)
        self._state["communication_apprenticeship"] = state
        durable = dict(self._state.get("crystal_checkpoint") or {})
        durable["communication_apprenticeship"] = dict(state)
        self._state["crystal_checkpoint"] = durable
        self._state["updated_at"] = time.time()
        self._persist_state()

    def _durable_checkpoint_from_state(self) -> Dict[str, Any]:
        return {
            "event_index": int(self._state.get("event_index", 0) or 0),
            "byte_offset": int(self._state.get("byte_offset", 0) or 0),
            "events_experienced": int(self._state.get("events_experienced", 0) or 0),
            "episodes_entered": int(self._state.get("episodes_entered", 0) or 0),
            "current_episode_id": str(self._state.get("current_episode_id", "") or ""),
            "last_event_id": str(self._state.get("last_event_id", "") or ""),
            "last_actor": str(self._state.get("last_actor", "") or ""),
            "last_observed_timestamp": self._state.get("last_observed_timestamp"),
            "communication_apprenticeship": dict(
                self._state.get("communication_apprenticeship") or {}
            ),
        }

    def _save_crystal_substrate(self) -> bool:
        """Persist the crystal containers that retain historical development.

        Historical witnessing deliberately bypasses the live-user turn path, so
        it must checkpoint the same crystal substrate explicitly.  A cursor is
        considered durable only after these saves succeed.
        """
        saved_any = False
        success = True
        dimensional = self.systems.get("dimensional")
        if dimensional is not None and hasattr(dimensional, "save_state"):
            saved_any = True
            try:
                ok = dimensional.save_state(str(self.state_dir))
                success = bool(ok) and success
            except Exception:
                success = False

        registry = self.systems.get("_concept_crystal_registry")
        if registry is not None and hasattr(registry, "save"):
            saved_any = True
            try:
                registry.save(str(self.state_dir))
            except Exception:
                success = False

        communication = self.systems.get("communication_emergence")
        if communication is not None and hasattr(communication, "save"):
            saved_any = True
            try:
                success = bool(communication.save()) and success
            except Exception:
                success = False

        # If neither crystal surface exists, do not advance the durable cursor.
        return bool(saved_any and success)

    def _checkpoint_crystals(self) -> bool:
        try:
            if self.field_lock is not None:
                with self.field_lock:
                    ok = self._save_crystal_substrate()
            else:
                ok = self._save_crystal_substrate()
        except Exception:
            ok = False
        if not ok:
            return False

        with self._state_guard:
            durable = self._durable_checkpoint_from_state()
            self._state["crystal_checkpoint"] = durable
            self._state["crystal_checkpoint_event_index"] = durable["event_index"]
            self._state["crystal_checkpoint_at"] = time.time()
            self._state["updated_at"] = time.time()
        self._persist_state()
        return True

    def _persist_state(self) -> None:
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            with self._state_guard:
                payload = dict(self._state or {})
            if atomic_write_json is not None:
                atomic_write_json(self.state_path, payload, indent=2, default=str)
            else:
                tmp = self.state_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
                os.replace(tmp, self.state_path)
        except Exception:
            pass

    def _append_ledger(self, record: Mapping[str, Any]) -> None:
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            with self.ledger_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(dict(record or {}), ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Witnessing
    # ------------------------------------------------------------------

    def _gateway_parts(self):
        aurora = self.systems.get("aurora")
        gateway = getattr(aurora, "gateway", None) if aurora is not None else None
        stream_type = self.systems.get("StreamType")
        existence_mode = self.systems.get("ExistenceMode")
        if gateway is None or stream_type is None or existence_mode is None:
            return None, None, None
        return gateway, stream_type, existence_mode

    @staticmethod
    def _actor_label(actor: str) -> str:
        raw = str(actor or "").strip().lower()
        if raw == "user":
            return "historical_user"
        if raw in {"historical_other_assistant", "assistant"}:
            return "historical_other_assistant"
        return f"historical_{raw or 'unknown_participant'}"

    def _observation_text(self, event: Mapping[str, Any]) -> str:
        actor = self._actor_label(str(event.get("actor", "") or ""))
        text = str(event.get("text", "") or "").strip()
        # Keep the wrapper deliberately small.  Provenance, epistemic status,
        # exact timing, and sequence details travel in packet metadata below;
        # repeating those labels inside all 50k semantic payloads would itself
        # become the dominant experience.
        return f"[{actor}] {text}"

    def _observe_communication_possibility(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        """Bridge chronological exchange structure into Aurora's cultivator.

        The user surface supplies the proposition.  A following other-assistant
        surface in the same episode is admitted only as a structurally possible
        representation—not a fact, answer key, Aurora memory, or receiver
        validation.  The communication cultivator decides whether that
        possibility exposes a representable gap in Aurora's own current
        constraint-derived response.
        """
        actor = self._actor_label(str(event.get("actor", "") or ""))
        episode_id = str(event.get("episode_id", "") or "")
        event_id = str(event.get("event_id", "") or "")
        text = str(event.get("text", "") or "").strip()
        state = dict(self._state.get("communication_apprenticeship") or {})
        state.setdefault("pairs_observed", 0)
        state.setdefault("structural_possibilities", 0)
        state.setdefault("representable_gaps", 0)
        state.setdefault("counterfactual_observations", 0)
        pending = dict(state.get("pending_user") or {})

        if pending and str(pending.get("episode_id", "") or "") != episode_id:
            pending = {}

        if actor == "historical_user":
            state["pending_user"] = {
                "event_id": event_id,
                "episode_id": episode_id,
                "text": text[:_MAX_PENDING_USER_TEXT],
                "observed_timestamp": event.get("timestamp"),
                "epistemic_status": str(
                    event.get("epistemic_status", "observation_not_truth")
                    or "observation_not_truth"
                ),
                "causal_status": str(
                    event.get("causal_status", "sequence_observed_causality_not_asserted")
                    or "sequence_observed_causality_not_asserted"
                ),
            } if text else {}
            state["last_status"] = "awaiting_structural_possibility" if text else "empty_user_surface"
            self._state["communication_apprenticeship"] = state
            return {
                "status": state["last_status"],
                "pending_user_event_id": event_id if text else "",
            }

        if actor != "historical_other_assistant" or not pending:
            state["pending_user"] = pending
            state["last_status"] = "no_exchange_pair"
            self._state["communication_apprenticeship"] = state
            return {"status": "no_exchange_pair"}

        # Consume exactly one chronological pair.  Later adjacent assistant
        # surfaces cannot silently accumulate authority over the same user
        # proposition.
        state["pending_user"] = {}
        state["pairs_observed"] = int(state.get("pairs_observed", 0) or 0) + 1
        communication = self.systems.get("communication_emergence")
        if communication is None or not hasattr(communication, "observe_structural_possibility"):
            state["last_status"] = "communication_cultivator_unavailable"
            self._state["communication_apprenticeship"] = state
            return {
                "status": state["last_status"],
                "user_event_id": str(pending.get("event_id", "") or ""),
                "possibility_event_id": event_id,
            }

        try:
            result = dict(communication.observe_structural_possibility(
                raw_text=str(pending.get("text", "") or ""),
                observed_response_text=text,
                possibility_id=f"{self._baseline_id}:{pending.get('event_id', '')}:{event_id}",
                observed_source="historical_other_assistant",
                epistemic_status=str(
                    event.get("epistemic_status", "observation_not_truth")
                    or "observation_not_truth"
                ),
                causal_status=str(
                    event.get("causal_status", "sequence_observed_causality_not_asserted")
                    or "sequence_observed_causality_not_asserted"
                ),
                # The environment checkpoints communication state alongside
                # crystals; do not advance one durable substrate ahead of the
                # other between checkpoint boundaries.
                defer_persistence=True,
            ) or {})
        except Exception as exc:
            state["last_status"] = "communication_cultivator_error"
            state["last_error"] = f"{type(exc).__name__}: {exc}"[:240]
            self._state["communication_apprenticeship"] = state
            return {
                "status": state["last_status"],
                "user_event_id": str(pending.get("event_id", "") or ""),
                "possibility_event_id": event_id,
            }

        # Build 771 PR 7: a second, independent observer of the SAME
        # chronological pair the call above just processed -- not a
        # parallel pipeline (it reuses AuroraLexicalGrounding's own
        # observe_lexical_context() entrance internally), and never
        # gated on whether communication_emergence found this pair
        # representable. Best-effort and silent on failure: a missing or
        # misbehaving lexical-grounding system must never disturb the
        # communication-emergence bookkeeping this method exists to do.
        try:
            from aurora_internal.aurora_lexical_grounding import get_lexical_grounding
            lexical_grounding = self.systems.get("lexical_grounding") or get_lexical_grounding()
            lexical_grounding.observe_historical_lexical_possibility(
                raw_text=str(pending.get("text", "") or ""),
                observed_response_text=text,
                possibility_id=f"{self._baseline_id}:{pending.get('event_id', '')}:{event_id}",
                observed_source="historical_other_assistant",
                epistemic_status=str(
                    event.get("epistemic_status", "observation_not_truth")
                    or "observation_not_truth"
                ),
                causal_status=str(
                    event.get("causal_status", "sequence_observed_causality_not_asserted")
                    or "sequence_observed_causality_not_asserted"
                ),
            )
        except Exception:
            pass

        if bool(result.get("structural_support", False)):
            state["structural_possibilities"] = int(
                state.get("structural_possibilities", 0) or 0
            ) + 1
        if bool(result.get("representable_gap", False)):
            state["representable_gaps"] = int(state.get("representable_gaps", 0) or 0) + 1
        if bool(result.get("admitted", False)):
            state["counterfactual_observations"] = int(
                state.get("counterfactual_observations", 0) or 0
            ) + 1
        state["last_status"] = "possibility_admitted" if result.get("admitted") else str(
            result.get("reason", "possibility_not_admitted") or "possibility_not_admitted"
        )
        state["last_pair"] = {
            "user_event_id": str(pending.get("event_id", "") or ""),
            "possibility_event_id": event_id,
            "possibility_id": str(result.get("possibility_id", "") or ""),
            "representable_gap": bool(result.get("representable_gap", False)),
            "trial_component_id": str(result.get("trial_component_id", "") or ""),
        }
        state.pop("last_error", None)
        self._state["communication_apprenticeship"] = state
        compact = {
            "status": state["last_status"],
            **state["last_pair"],
            "structural_support": bool(result.get("structural_support", False)),
            "candidate_available": bool(result.get("candidate_available", False)),
        }
        self.systems["_historical_communication_apprenticeship"] = dict(compact)
        return compact

    def _witness(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        gateway, stream_type, existence_mode = self._gateway_parts()
        if gateway is None:
            raise RuntimeError("historical experience requires Aurora gateway, StreamType, and ExistenceMode")

        event_id = str(event.get("event_id", "") or "")
        episode_id = str(event.get("episode_id", "") or "")
        actor = self._actor_label(str(event.get("actor", "") or ""))
        episode = self._episodes.get(episode_id, {})
        is_new_episode = episode_id != str(self._state.get("current_episode_id", "") or "")

        metadata = {
            "historical_experience": True,
            "event_id": event_id,
            "episode_id": episode_id,
            "actor": actor,
            "observed_timestamp": event.get("timestamp"),
            "observed_timestamp_utc": _utc_iso(event.get("timestamp")),
            "delta_seconds_from_previous_turn": event.get("delta_seconds_from_previous_turn"),
            "episode_boundary": bool(is_new_episode),
            "previous_episode_gap_seconds": episode.get("previous_episode_gap_seconds") if is_new_episode else None,
            "epistemic_status": str(event.get("epistemic_status", "observation_not_truth") or "observation_not_truth"),
            "causal_status": str(event.get("causal_status", "sequence_observed_causality_not_asserted") or "sequence_observed_causality_not_asserted"),
            "autobiographical_status": str(event.get("autobiographical_status", "not_aurora_memory") or "not_aurora_memory"),
            "provenance": str(event.get("provenance", "chatgpt_export_active_branch") or "chatgpt_export_active_branch"),
        }

        response = gateway.receive(
            content=self._observation_text(event),
            stream_type=stream_type.SENSOR_DATA,
            source=f"historical_experience:{actor}",
            metadata=metadata,
            mode=existence_mode.BOUNDED,
        )

        # Expose only current environmental context, not a parallel semantic
        # interpretation.  Existing Aurora organs may inspect it if relevant.
        self.systems["_historical_experience_context"] = {
            "baseline_id": self._baseline_id,
            "event_id": event_id,
            "episode_id": episode_id,
            "actor": actor,
            "observed_timestamp": event.get("timestamp"),
            "epistemic_status": metadata["epistemic_status"],
            "causal_status": metadata["causal_status"],
            "event_index": int(self._state.get("event_index", 0) or 0),
            "total_events": int(self._manifest.get("event_count", 0) or 0),
        }
        communication_apprenticeship = self._observe_communication_possibility(event)
        self.systems["_historical_experience_context"]["communication_apprenticeship"] = dict(
            communication_apprenticeship or {}
        )

        return {
            "baseline_id": self._baseline_id,
            "event_id": event_id,
            "episode_id": episode_id,
            "actor": actor,
            "episode_boundary": bool(is_new_episode),
            "observed_timestamp": event.get("timestamp"),
            "gateway_response_id": str(getattr(response, "response_id", "") or ""),
            "gateway_confidence": float(getattr(response, "confidence", 0.0) or 0.0),
            "communication_apprenticeship": dict(communication_apprenticeship or {}),
            "observed_at": time.time(),
        }

    # ------------------------------------------------------------------
    # Stream / cadence
    # ------------------------------------------------------------------

    def _next_event(self, fh) -> Optional[Dict[str, Any]]:
        offset = int(self._state.get("byte_offset", 0) or 0)
        fh.seek(offset)
        while True:
            line = fh.readline()
            if not line:
                return None
            new_offset = fh.tell()
            if not line.strip():
                self._state["byte_offset"] = new_offset
                continue
            try:
                event = json.loads(line)
            except Exception:
                self._state["byte_offset"] = new_offset
                self._state["event_index"] = int(self._state.get("event_index", 0) or 0) + 1
                continue
            event["_next_byte_offset"] = new_offset
            return event

    def _experience_delay(self, event: Mapping[str, Any], episode_boundary: bool) -> float:
        # Chronology stays ordered and retains some felt spacing without
        # pretending that 2.5 historical years can literally elapse again.
        # Exact source intervals remain in metadata; this only provides a
        # monotonic compressed cadence for the witness environment itself.
        gap = event.get("delta_seconds_from_previous_turn")
        if episode_boundary:
            episode = self._episodes.get(str(event.get("episode_id", "") or ""), {})
            gap = episode.get("previous_episode_gap_seconds", gap)
        seconds = max(0.0, _safe_float(gap) or 0.0)
        if seconds <= 0.0:
            return 0.04
        delay = 0.04 + math.log1p(seconds) / 22.0
        if episode_boundary:
            return min(1.5, max(0.18, delay))
        return min(0.75, max(0.04, delay))

    def _wait_until_available(self) -> bool:
        while not self._stop.is_set():
            if self._pause.is_set():
                time.sleep(0.25)
                continue
            try:
                if not bool(self.live_idle()):
                    time.sleep(0.35)
                    continue
            except Exception:
                pass
            return True
        return False

    def _run(self) -> None:
        try:
            if self.initial_delay_s > 0 and self._stop.wait(self.initial_delay_s):
                return
            self._prepare()
            if self._state.get("completed"):
                return

            with self._open_events() as fh:
                while not self._stop.is_set():
                    if not self._wait_until_available():
                        break

                    with self._state_guard:
                        event = self._next_event(fh)
                    if event is None:
                        # Final completion is only durable once the crystal
                        # substrate is checkpointed at the terminal cursor.
                        if not self._checkpoint_crystals():
                            with self._state_guard:
                                self._state["status"] = "checkpoint_error"
                                self._state["last_error"] = "crystal checkpoint failed at baseline completion"
                                self._state["updated_at"] = time.time()
                            self._persist_state()
                            if self._stop.wait(2.0):
                                break
                            continue
                        with self._state_guard:
                            self._state["completed"] = True
                            self._state["status"] = "completed"
                            self._state["completed_at"] = time.time()
                            self._state["updated_at"] = time.time()
                        self._persist_state()
                        self.systems["_historical_experience_complete"] = True
                        break

                    previous_episode = str(self._state.get("current_episode_id", "") or "")
                    episode_id = str(event.get("episode_id", "") or "")
                    boundary = bool(episode_id and episode_id != previous_episode)

                    try:
                        if self.field_lock is not None:
                            with self.field_lock:
                                ledger = self._witness(event)
                        else:
                            ledger = self._witness(event)
                    except Exception as exc:
                        with self._state_guard:
                            self._state["status"] = "error"
                            self._state["last_error"] = f"{type(exc).__name__}: {exc}"
                            self._state["updated_at"] = time.time()
                        self._persist_state()
                        if self._stop.wait(2.0):
                            break
                        continue

                    with self._state_guard:
                        next_offset = int(event.get("_next_byte_offset", self._state.get("byte_offset", 0)) or 0)
                        next_index = int(self._state.get("event_index", 0) or 0) + 1
                        next_experienced = int(self._state.get("events_experienced", 0) or 0) + 1
                        next_episodes = int(self._state.get("episodes_entered", 0) or 0) + (1 if boundary else 0)
                        self._state["byte_offset"] = next_offset
                        self._state["event_index"] = next_index
                        self._state["events_experienced"] = next_experienced
                        self._state["episodes_entered"] = next_episodes
                        self._state["current_episode_id"] = episode_id
                        self._state["last_event_id"] = str(event.get("event_id", "") or "")
                        self._state["last_actor"] = str(ledger.get("actor", "") or "")
                        self._state["last_observed_timestamp"] = event.get("timestamp")
                        self._state["last_error"] = ""
                        self._state["status"] = "running"
                        self._state["updated_at"] = time.time()
                        ledger.update({
                            "next_byte_offset": next_offset,
                            "event_index_after": next_index,
                            "events_experienced_after": next_experienced,
                            "episodes_entered_after": next_episodes,
                        })
                    # Commit witness evidence first, then advance the compact
                    # cursor state. _prepare() reconciles from this ledger if a
                    # process death lands between these two durable writes.
                    self._append_ledger(ledger)
                    self._persist_state()

                    if next_experienced % self.crystal_checkpoint_interval == 0:
                        if not self._checkpoint_crystals():
                            with self._state_guard:
                                self._state["status"] = "checkpoint_error"
                                self._state["last_error"] = (
                                    f"crystal checkpoint failed at event {next_experienced}"
                                )
                                self._state["updated_at"] = time.time()
                            self._persist_state()

                    delay = self._experience_delay(event, boundary)
                    if delay > 0 and self._stop.wait(delay):
                        break
        except Exception as exc:
            with self._state_guard:
                self._state.setdefault("schema", _STATE_SCHEMA)
                self._state["status"] = "error"
                self._state["last_error"] = f"{type(exc).__name__}: {exc}"
                self._state["updated_at"] = time.time()
            self._persist_state()


def start_historical_experience_environment(
    systems: Mapping[str, Any],
    *,
    state_dir: str,
    archive_path: Optional[str] = None,
    field_lock: Optional[threading.Lock] = None,
    live_idle: Optional[Callable[[], bool]] = None,
    initial_delay_s: float = 8.0,
    crystal_checkpoint_interval: int = 100,
) -> HistoricalExperienceEnvironment:
    env = HistoricalExperienceEnvironment(
        systems,
        state_dir=state_dir,
        archive_path=archive_path,
        field_lock=field_lock,
        live_idle=live_idle,
        initial_delay_s=initial_delay_s,
        crystal_checkpoint_interval=crystal_checkpoint_interval,
    )
    env.start()
    return env
