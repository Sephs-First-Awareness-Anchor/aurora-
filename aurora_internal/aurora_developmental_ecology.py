"""Boundary contract for Aurora's external developmental ecology.

This module deliberately lives at the membrane between Aurora and a persistent
outside world.  It does not teach Aurora, inspect her private cognitive state,
or write developmental state directly.  It only defines ordinary external
occurrences and the provenance required to admit them through Aurora's canonical
live-turn boundary.

Governing law:
    Give Aurora experience. Never give her the development the experience is
    supposed to produce.

The ecology may maintain world state, actors, unfinished situations and
consequences.  Aurora remains the only system allowed to interpret those events
into her own memory, identity, representations, genealogy and development.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import time
import uuid


ECOLOGY_SOURCE_PREFIX = "developmental_ecology"
ECOLOGY_SESSION_PREFIX = "ecology"

# External kinds are intentionally about what happened in the world, not what
# Aurora is supposed to learn from it.
ALLOWED_EVENT_KINDS = frozenset({
    "utterance",
    "observation",
    "situation",
    "consequence",
    "evidence",
    "world_change",
    "entity_action",
})

# These keys would turn the environment into a hidden teacher or an internal
# state editor.  They are rejected at the membrane even if an ecology operator
# accidentally supplies them.
FORBIDDEN_METADATA_KEYS = frozenset({
    "correct_answer",
    "target_meaning",
    "target_representation",
    "target_genealogy",
    "target_identity",
    "target_pressure",
    "reward",
    "score",
    "grade",
    "desired_response",
    "sedimemory_write",
    "identity_write",
    "representation_write",
})


class EcologyBoundaryError(ValueError):
    """Raised when an external event tries to cross the membrane unlawfully."""


@dataclass(frozen=True)
class ExperienceEnvelope:
    """One externally observable occurrence offered to Aurora.

    `text` is the ordinary content Aurora can perceive.  The remaining fields
    preserve world provenance and temporal/consequence relations outside her.
    They are transport metadata, not cognitive conclusions.
    """

    world_id: str
    actor_id: str
    kind: str
    text: str
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    parent_event_id: str = ""
    consequence_of: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "ExperienceEnvelope":
        if not self.world_id.strip():
            raise EcologyBoundaryError("world_id is required")
        if not self.actor_id.strip():
            raise EcologyBoundaryError("actor_id is required")
        if self.kind not in ALLOWED_EVENT_KINDS:
            raise EcologyBoundaryError(f"unsupported ecology event kind: {self.kind}")
        if not self.text.strip():
            raise EcologyBoundaryError("ecology occurrences must contain perceivable content")
        forbidden = FORBIDDEN_METADATA_KEYS.intersection(self.metadata)
        if forbidden:
            raise EcologyBoundaryError(
                "ecology metadata may not prescribe Aurora's development: "
                + ", ".join(sorted(forbidden))
            )
        return self

    @property
    def source_label(self) -> str:
        actor = _safe_token(self.actor_id)
        return f"{ECOLOGY_SOURCE_PREFIX}:{actor}"

    @property
    def session_id(self) -> str:
        return f"{ECOLOGY_SESSION_PREFIX}:{_safe_token(self.world_id)}"

    def canonical_turn_kwargs(self) -> Dict[str, Any]:
        """Arguments for aurora.process_external_user_turn().

        The ecology never requests a training shortcut.  The event is recorded
        as a real exchange, participates in the normal interactive/lived state,
        and uses the same evolutionary trace and maintenance machinery as other
        admitted live occurrences.
        """
        self.validate()
        return {
            "source_label": self.source_label,
            "session_id": self.session_id,
            "auto_search_enabled": False,
            "record_exchange": True,
            "update_interactive_state": True,
            "track_evolutionary_trace": True,
            "run_periodic_maintenance": True,
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ExperienceEnvelope":
        return cls(**dict(raw)).validate()


@dataclass
class WorldEventRecord:
    envelope: ExperienceEnvelope
    aurora_reply: str = ""
    reply_recorded_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope": self.envelope.to_dict(),
            "aurora_reply": self.aurora_reply,
            "reply_recorded_at": self.reply_recorded_at,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "WorldEventRecord":
        return cls(
            envelope=ExperienceEnvelope.from_dict(dict(raw.get("envelope") or {})),
            aurora_reply=str(raw.get("aurora_reply") or ""),
            reply_recorded_at=float(raw.get("reply_recorded_at") or 0.0),
        )


class DevelopmentalWorldJournal:
    """Persistent memory belonging to the *world*, not to Aurora.

    It remembers what the ecology did so later consequences and revisitations can
    be temporally real without reaching into SediMemory.  Aurora's own memory is
    still exclusively Aurora's responsibility.
    """

    def __init__(self, path: str | Path, *, world_id: str):
        self.path = Path(path)
        self.world_id = str(world_id)
        self._records: List[WorldEventRecord] = []
        self._load()

    @property
    def records(self) -> tuple[WorldEventRecord, ...]:
        return tuple(self._records)

    def append_occurrence(self, envelope: ExperienceEnvelope) -> None:
        envelope.validate()
        if envelope.world_id != self.world_id:
            raise EcologyBoundaryError("event belongs to a different developmental world")
        if any(r.envelope.event_id == envelope.event_id for r in self._records):
            raise EcologyBoundaryError("duplicate ecology event_id")
        self._records.append(WorldEventRecord(envelope=envelope))
        self._save()

    def record_reply(self, event_id: str, reply: str) -> None:
        for record in self._records:
            if record.envelope.event_id == event_id:
                record.aurora_reply = str(reply or "")
                record.reply_recorded_at = time.time()
                self._save()
                return
        raise EcologyBoundaryError("cannot attach a reply to an unknown ecology event")

    def unfinished(self) -> tuple[WorldEventRecord, ...]:
        """World events that have not yet received Aurora's outward response."""
        return tuple(r for r in self._records if not r.aurora_reply)

    def causal_children(self, event_id: str) -> tuple[WorldEventRecord, ...]:
        return tuple(
            r for r in self._records
            if r.envelope.parent_event_id == event_id
            or r.envelope.consequence_of == event_id
        )

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if str(raw.get("world_id") or "") != self.world_id:
            raise EcologyBoundaryError("journal world_id does not match requested world")
        self._records = [WorldEventRecord.from_dict(x) for x in raw.get("records", [])]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "aurora.developmental_ecology.world.v1",
            "world_id": self.world_id,
            "records": [r.to_dict() for r in self._records],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)


def build_consequence(
    cause: ExperienceEnvelope,
    *,
    actor_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ExperienceEnvelope:
    """Create a later world consequence without declaring what it means."""
    return ExperienceEnvelope(
        world_id=cause.world_id,
        actor_id=actor_id,
        kind="consequence",
        text=text,
        consequence_of=cause.event_id,
        metadata=dict(metadata or {}),
    ).validate()


def _safe_token(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value).strip())
    return cleaned[:96] or "unknown"
