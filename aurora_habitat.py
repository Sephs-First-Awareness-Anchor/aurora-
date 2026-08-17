# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_habitat.py

Aurora App Developmental Habitat (Build 712).

The Habitat is a persistent, manipulable world substrate shared by two
application territories -- Space (jointly manipulable by Aurora and a
human) and Self (Aurora-owned, with a real, technically-enforced
ownership boundary rather than a decorative UI label).

Governing principle (spec section 1): build affordances, not lessons.
This module defines a small, general, physical vocabulary -- entities,
positions, colors, connections, ownership, transfer -- and executes it
under neutral physical/ownership rules. It never assigns meaning to
what Aurora builds, moves, keeps, or removes. That interpretation is
Aurora's own developmental work, performed by her existing cognitive
architecture (constraint physics, SediMemory, genealogy, introspection)
against the raw environmental facts this module produces -- never
invented here.

Architecture integrity rules this module exists to honor (spec section
44), restated as code-level constraints:

  Rule 3  No operation here maps an internal Aurora state to a
          predetermined visual/animation outcome. HabitatEntity
          properties (color, position, shape...) are set only by
          explicit EnvironmentAction parameters an actor supplied.
  Rule 4  Every action and its consequence is persisted as
          developmental evidence (habitat_events.jsonl,
          entity_lineage.jsonl), not disposable telemetry.
  Rule 6  Constraint evidence (see _emit_constraint_evidence) and
          long-term memory deposit (see _deposit_sediment) route
          through Aurora's REAL existing constraint-physics and
          SediMemory machinery (aurora_waveform_pressure.py,
          aurora_sedimemory.py) -- this module does not invent a
          parallel learning system.
  Rule 9  Aurora and humans read/write exactly one canonical
          HabitatRuntime/world state; there is no separate "Aurora's
          copy" of the world.
  Rule 10 Self ownership is enforced in _check_permission() and in
          the create/act() dispatch below, not merely implied by
          screen layout.
"""
from __future__ import annotations

import json
import os
import time
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
except Exception:  # pragma: no cover - faults module always present in the real tree
    def _aurora_record_exception_from_locals(*_a, **_k) -> None:
        pass


# ── Vocabulary (spec sections 5, 6, 33) ─────────────────────────────────────
# A small, general, physical vocabulary. Additions belong here as the
# substrate grows (spec section 40); nothing here encodes what any of
# these are FOR.

TERRITORIES = ("space", "self")
OWNERS = ("aurora", "human", "shared")
ENTITY_TYPES = ("shape", "text", "mark_path", "connector", "group")

# Phase A operations (spec section 33/36). "delete" is soft (tombstoned,
# not erased) so "restore" (spec section 6, Existence) has something
# real to restore.
OPERATIONS = (
    "create", "duplicate", "delete", "restore",
    "move", "resize", "rotate", "recolor",
    "connect", "disconnect", "group", "ungroup",
    "transfer", "grant_permission", "revoke_permission",
)

# Neutral physical consequence vocabulary.  These labels describe what a
# successful operation can observably change; they never say why that change
# should matter.  Motivation consumers compare this surface with Aurora's own
# active structure instead of treating every N/B/X operation as equivalent.
CONSEQUENCE_DIMENSION_AXES: Dict[str, Dict[str, float]] = {
    "existence":            {"X": 1.0, "T": 0.35},
    "persistence":          {"T": 1.0, "X": 0.25},
    "spatial_relation":     {"X": 0.45, "N": 0.70, "B": 0.55},
    "extent_magnitude":     {"X": 0.45, "N": 0.75},
    "orientation":          {"N": 0.65, "B": 0.45},
    "appearance":           {"X": 0.45, "N": 0.55, "B": 0.25},
    "relational_structure": {"T": 0.35, "N": 0.35, "B": 1.0},
    "containment":          {"T": 0.35, "B": 1.0},
    "ownership":            {"T": 0.25, "B": 0.75, "A": 0.80},
    "territory_boundary":   {"T": 0.25, "B": 1.0, "A": 0.35},
    "permission_boundary":  {"T": 0.30, "B": 1.0, "A": 0.45},
}

_OPERATION_CONSEQUENCE_DIMENSIONS: Dict[str, Tuple[str, ...]] = {
    "create": ("existence", "persistence", "spatial_relation", "extent_magnitude", "orientation", "appearance"),
    "duplicate": ("existence", "persistence", "spatial_relation", "extent_magnitude", "orientation", "appearance"),
    "delete": ("existence", "persistence"),
    "restore": ("existence", "persistence"),
    "move": ("spatial_relation",),
    "resize": ("extent_magnitude",),
    "rotate": ("orientation",),
    "recolor": ("appearance",),
    "connect": ("relational_structure",),
    "disconnect": ("relational_structure",),
    "group": ("containment", "relational_structure"),
    "ungroup": ("containment", "relational_structure"),
    "transfer": ("ownership", "territory_boundary"),
    "grant_permission": ("permission_boundary",),
    "revoke_permission": ("permission_boundary",),
}


def operation_consequence_dimensions(operation: str) -> Tuple[str, ...]:
    """Physical distinctions an operation can reveal or alter."""
    return _OPERATION_CONSEQUENCE_DIMENSIONS.get(str(operation), ())


def consequence_axis_profile(dimensions: List[str] | Tuple[str, ...]) -> Dict[str, float]:
    """Project physical consequence dimensions into the native five axes."""
    profile = {axis: 0.0 for axis in "XTNBA"}
    for dimension in dimensions:
        for axis, value in CONSEQUENCE_DIMENSION_AXES.get(str(dimension), {}).items():
            profile[axis] += float(value)
    peak = max(profile.values()) if profile else 0.0
    if peak > 0.0:
        profile = {axis: value / peak for axis, value in profile.items()}
    return profile

_PERMISSION_KEYS = (
    "visible_to_aurora", "visible_to_human",
    "modifiable_by_aurora", "modifiable_by_human",
    "transferable",
)

# How recently a same-territory action by a DIFFERENT actor touching the
# same entity counts as a structurally-linked response (spec section 17).
# A neutral temporal-adjacency window, not an inferred agreement/
# disagreement judgment -- Aurora performs that inference herself from
# the preserved sequence.
_RESPONSE_LINK_WINDOW_S = 3600.0

# Recent-history bound kept in memory / returned by get_history(); the
# on-disk ledgers (habitat_events.jsonl, entity_lineage.jsonl) are the
# unbounded record.
_RECENT_EVENTS_MAXLEN = 200


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _clamp01(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.0


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


# ── Entity model (spec section 5) ───────────────────────────────────────────

@dataclass
class HabitatEntity:
    id: str
    entity_type: str
    creator: str            # "aurora" | "human"
    owner: str              # "aurora" | "human" | "shared"
    territory: str          # "space" | "self"
    created_at: float = field(default_factory=_now)
    modified_at: float = field(default_factory=_now)
    position: List[float] = field(default_factory=lambda: [0.5, 0.5])
    dimensions: List[float] = field(default_factory=lambda: [0.1, 0.1])
    orientation: float = 0.0
    layer: int = 0
    visual_properties: Dict[str, Any] = field(default_factory=dict)
    temporal_properties: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    group_membership: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    interaction_permissions: Dict[str, bool] = field(default_factory=dict)
    lineage: Dict[str, Any] = field(default_factory=dict)
    deleted: bool = False
    revision_count: int = 0
    interaction_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "HabitatEntity":
        known = {f for f in cls.__dataclass_fields__.keys()}
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})

    def is_visible_to(self, actor: str) -> bool:
        key = f"visible_to_{actor}"
        return bool(self.interaction_permissions.get(key, True))

    def is_modifiable_by(self, actor: str) -> bool:
        key = f"modifiable_by_{actor}"
        return bool(self.interaction_permissions.get(key, False))


def _default_permissions(territory: str, owner: str) -> Dict[str, bool]:
    """Neutral default permission set for a freshly-created entity.

    Space defaults to fully open (both parties made it together).
    Self defaults to human-visible (she is not hiding that something
    exists) but not human-modifiable -- the technically-real boundary
    spec section 3.3 requires, not a decorative label. Aurora may
    subsequently grant/revoke on any entity via grant_permission/
    revoke_permission (spec section 6, Boundary)."""
    if territory == "space":
        return {
            "visible_to_aurora": True, "visible_to_human": True,
            "modifiable_by_aurora": True, "modifiable_by_human": True,
            "transferable": True,
        }
    # territory == "self"
    return {
        "visible_to_aurora": True, "visible_to_human": True,
        "modifiable_by_aurora": True,
        "modifiable_by_human": (owner == "human"),
        "transferable": True,
    }


# ── Action / Consequence protocol (spec sections 9, 10) ────────────────────

@dataclass
class EnvironmentAction:
    action_id: str
    actor: str               # "aurora" | "human"
    territory: str
    operation: str
    target_ids: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    intention_context: str = ""
    # Optional structural handoff from the agency arbitration that selected
    # this concrete action.  The Habitat never interprets it; it persists the
    # causal trace and returns the real consequence to the originating
    # representational inquiry.
    causal_context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentConsequence:
    action_id: str
    success: bool
    actor: str
    operation: str
    resulting_state: Dict[str, Any] = field(default_factory=dict)
    state_delta: Dict[str, Any] = field(default_factory=dict)
    affected_entities: List[str] = field(default_factory=list)
    permission_result: str = "n/a"   # "n/a" | "granted" | "denied:<reason>"
    rejected_reason: str = ""
    causal_parent: Optional[str] = None   # action_id this structurally follows (spec section 17)
    human_response: Optional[str] = None  # action_id of a later response, filled in by link_response()
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)
    # Build 717 (follow-up): a legally-executed, permission-granted action
    # can still produce zero observable effect (moving an entity to its own
    # current position, restoring an already-live entity, connecting two
    # already-linked entities...). `success` answers "was this legal";
    # `state_changed` answers "did anything actually change" -- the two
    # are deliberately independent so a no-op is never silently counted as
    # a genuine developmental consequence downstream (resolution pressure,
    # autonomous-engagement observability). Defaults True for operations
    # that structurally cannot no-op (create/duplicate/group always mint a
    # new real entity given they were reached at all).
    state_changed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_ENTITY_BOOKKEEPING_FIELDS = frozenset({"modified_at", "revision_count", "interaction_count"})


def _entity_state_changed(pre: Dict[str, Any], post: Dict[str, Any]) -> bool:
    """Real semantic-diff between an entity's before/after dict, ignoring
    bookkeeping fields that mutate on every call by construction (they
    would otherwise make every action look like a real change even when
    nothing observable actually moved)."""
    for key in set(pre.keys()) | set(post.keys()):
        if key in _ENTITY_BOOKKEEPING_FIELDS:
            continue
        if pre.get(key) != post.get(key):
            return True
    return False


def _expectation_error(expected: Any, actual: Any) -> float:
    """Set-distance used only for candidate-conditioned consequence credit."""
    expected_set = {str(x) for x in (expected or [])}
    actual_set = {str(x) for x in (actual or [])}
    if not expected_set and not actual_set:
        return 0.0
    union = expected_set | actual_set
    return 1.0 - (len(expected_set & actual_set) / max(1, len(union)))


def _parameter_error(expected: Any, actual: Any) -> float:
    expected_dict = dict(expected or {})
    actual_dict = dict(actual or {})
    if not expected_dict:
        return 0.0
    matches = sum(1 for key, value in expected_dict.items() if actual_dict.get(key) == value)
    return 1.0 - (matches / len(expected_dict))


# ── Constraint / memory bridges (Rule 6: use the real machinery) ───────────

def _actual_consequence_dimensions(
    action: EnvironmentAction,
    consequence: EnvironmentConsequence,
    pre_state: Optional[Dict[str, Any]],
    post_state: Optional[Dict[str, Any]],
) -> Tuple[str, ...]:
    """Dimensions the executed before/after evidence says really changed.

    A denied or vacuous action produces no dimensions.  For a genuine state
    change the operation's neutral physical contract supplies the candidate
    dimensions; simple mutations are narrowed by their concrete before/after
    fields where the snapshots make that distinction directly observable.
    """
    if not consequence.success or not consequence.state_changed:
        return ()
    operation = action.operation
    if operation == "transfer":
        before = pre_state if isinstance(pre_state, dict) else {}
        after = post_state if isinstance(post_state, dict) else {}
        ids = set(before) | set(after)
        changed: List[str] = []
        if any((before.get(eid) or {}).get("owner") != (after.get(eid) or {}).get("owner")
               for eid in ids):
            changed.append("ownership")
        if any((before.get(eid) or {}).get("territory") != (after.get(eid) or {}).get("territory")
               for eid in ids):
            changed.append("territory_boundary")
        return tuple(changed)
    if operation in ("move", "resize", "rotate", "recolor", "connect", "disconnect",
                     "group", "ungroup", "grant_permission", "revoke_permission"):
        return operation_consequence_dimensions(operation)
    if operation in ("create", "duplicate", "delete", "restore"):
        return operation_consequence_dimensions(operation)
    return ()


def _consequence_axis_amplitudes(
    action: EnvironmentAction,
    consequence: EnvironmentConsequence,
    pre_state: Optional[Dict[str, Any]] = None,
    post_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Project the observed consequence into Aurora's native axes.

    This deliberately does not classify operation names as X/N/B families.
    The intermediate object is the neutral physical distinction that really
    occurred. Agency amplitude comes from the actor's completed/attempted
    action itself, independent of which operation was chosen; a denied action
    also exposes a small boundary fact because a real permission boundary
    held.
    """
    dimensions = _actual_consequence_dimensions(
        action, consequence, pre_state, post_state,
    )
    profile = consequence_axis_profile(dimensions)
    scale = 0.60 if consequence.success and consequence.state_changed else 0.0
    amplitudes = {
        axis: round(float(profile.get(axis, 0.0)) * scale, 6)
        for axis in "XTNBA"
    }
    amplitudes["A"] = max(amplitudes["A"], 0.35 if consequence.success else 0.15)
    if not consequence.success:
        amplitudes["B"] = max(amplitudes["B"], 0.20)
    return amplitudes


class HabitatRuntime:
    """Canonical Habitat action/consequence/state authority (spec section
    20). Aurora and humans both act through .act(); nobody -- Flutter,
    Kotlin, or Aurora's own turn pipeline -- reads or writes habitat
    state any other way (spec section 9)."""

    def __init__(self, state_dir: Any, *, systems: Optional[Dict[str, Any]] = None) -> None:
        self.root = Path(str(state_dir)) / "habitat"
        self.systems = systems
        self._lock = threading.RLock()
        self._entities: Dict[str, HabitatEntity] = {}
        self._recent_events: List[Dict[str, Any]] = []
        self._recent_motivation_events: List[Dict[str, Any]] = []
        self._load()

    # ── persistence ─────────────────────────────────────────────────────

    def _world_state_path(self) -> Path:
        return self.root / "world_state.json"

    def _events_path(self) -> Path:
        return self.root / "habitat_events.jsonl"

    def _lineage_path(self) -> Path:
        return self.root / "entity_lineage.jsonl"

    def _motivation_events_path(self) -> Path:
        return self.root / "habitat_motivation_events.jsonl"

    def _load(self) -> None:
        path = self._world_state_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8") or "{}")
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_habitat.py:HabitatRuntime._load",
                    exc=_aurora_boundary_exc,
                    context={"function": "_load", "source_file": "aurora_habitat.py"},
                )
                raw = {}
            for eid, edict in (raw.get("entities") or {}).items():
                try:
                    self._entities[eid] = HabitatEntity.from_dict(edict)
                except Exception:
                    continue
        self._recent_events = self._load_jsonl_tail(self._events_path(), _RECENT_EVENTS_MAXLEN)
        self._recent_motivation_events = self._load_jsonl_tail(
            self._motivation_events_path(), _RECENT_EVENTS_MAXLEN,
        )
        # human_response is an index over the persisted causal_parent facts.
        # Rebuild it after restart instead of pretending that an in-memory
        # mutation of an earlier JSONL line was durable.
        by_id = {str(ev.get("event_id")): ev for ev in self._recent_events}
        for event in self._recent_events:
            parent = by_id.get(str(event.get("causal_parent") or ""))
            if parent is not None:
                parent["human_response"] = event.get("event_id")

    @staticmethod
    def _load_jsonl_tail(path: Path, limit: int) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        records: deque = deque(maxlen=max(1, int(limit)))
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    value = json.loads(line)
                    if isinstance(value, dict):
                        records.append(value)
        except Exception:
            return list(records)
        return list(records)

    def _save_world_state(self) -> None:
        payload = {
            "saved_at": _now(),
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
        }
        _atomic_write_json(self._world_state_path(), payload)

    def _persist_event(self, action: EnvironmentAction, consequence: EnvironmentConsequence,
                        pre_state: Optional[Dict[str, Any]], post_state: Optional[Dict[str, Any]],
                        session_id: str = "") -> None:
        consequence_dimensions = _actual_consequence_dimensions(
            action, consequence, pre_state, post_state,
        )
        record = {
            "event_id": _new_id("hev"),
            "action_id": action.action_id,
            "timestamp": consequence.timestamp,
            "actor": action.actor,
            "event_type": action.operation,
            "territory": action.territory,
            # consequence.affected_entities, not action.target_ids: a
            # create/duplicate/group action's target didn't exist yet
            # when the action was constructed -- only the executed
            # consequence knows the resulting entity id(s).
            "entity_ids": list(consequence.affected_entities),
            "pre_state": pre_state or {},
            "post_state": post_state or {},
            "causal_parent": consequence.causal_parent,
            "session_id": session_id,
            "success": consequence.success,
            "state_changed": consequence.state_changed,
            "rejected_reason": consequence.rejected_reason,
            "parameters": dict(action.parameters),
            "intention_context": action.intention_context,
            "causal_context": dict(action.causal_context),
            "consequence_dimensions": list(consequence_dimensions),
        }
        _append_jsonl(self._events_path(), record)
        self._recent_events.append(record)
        if len(self._recent_events) > _RECENT_EVENTS_MAXLEN:
            self._recent_events = self._recent_events[-_RECENT_EVENTS_MAXLEN:]
        # Build 717 (directive section 18): the prior event this one is a
        # structural response to (already computed, real, recency-window-
        # bound adjacency -- consequence.causal_parent) now genuinely gets
        # its OWN "a subsequent actor response exists" fact recorded too.
        # link_response() previously had no caller anywhere in this module;
        # "subsequent actor response" was on the directive's list of
        # available-but-unused rich facts because of that gap.
        if record.get("causal_parent"):
            self.link_response(record["causal_parent"], record["event_id"])

    def _persist_lineage(self, entity_id: str, event: str, *, parent_ids: Optional[List[str]] = None,
                          action_id: str = "") -> None:
        record = {
            "entity_id": entity_id,
            "event": event,   # created | duplicated | transformed | combined | transferred | deleted | restored
            "parent_ids": list(parent_ids or []),
            "action_id": action_id,
            "timestamp": _now(),
        }
        _append_jsonl(self._lineage_path(), record)

    # ── read side (spec sections 8, 20, 37) ─────────────────────────────

    def get_entity(self, entity_id: str, *, actor: Optional[str] = None) -> Optional[Dict[str, Any]]:
        e = self._entities.get(entity_id)
        if e is None or e.deleted:
            return None
        if actor and not e.is_visible_to(actor):
            return None
        return e.to_dict()

    def get_state(self, *, territory: Optional[str] = None, actor: Optional[str] = None,
                  include_deleted: bool = False) -> Dict[str, Any]:
        """Structural perception (spec section 8) -- objective facts
        only, no rendering, no interpretation."""
        with self._lock:
            entities = []
            for e in self._entities.values():
                if not include_deleted and e.deleted:
                    continue
                if territory and e.territory != territory:
                    continue
                if actor and not e.is_visible_to(actor):
                    continue
                entities.append(e.to_dict())
            return {
                "territory": territory or "all",
                "entity_count": len(entities),
                "entities": entities,
                "as_of": _now(),
            }

    def get_history(self, *, entity_id: Optional[str] = None, territory: Optional[str] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        events = self._recent_events
        if entity_id:
            events = [ev for ev in events if entity_id in (ev.get("entity_ids") or [])]
        if territory:
            events = [ev for ev in events if ev.get("territory") == territory]
        return events[-max(1, int(limit)):]

    def record_motivation_event(self, record: Dict[str, Any]) -> None:
        """Persist structural arbitration/consequence telemetry.

        This is evidence about why a Habitat action was considered and what
        followed, not a second memory or motive system.  Candidate generation
        reads it only to measure whether repeated equivalent actions continued
        producing useful distinction.
        """
        payload = dict(record or {})
        payload.setdefault("timestamp", _now())
        with self._lock:
            _append_jsonl(self._motivation_events_path(), payload)
            self._recent_motivation_events.append(payload)
            if len(self._recent_motivation_events) > _RECENT_EVENTS_MAXLEN:
                self._recent_motivation_events = self._recent_motivation_events[-_RECENT_EVENTS_MAXLEN:]

    def get_motivation_history(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._recent_motivation_events[-max(1, int(limit)):])

    def get_lineage(self, entity_id: str) -> List[Dict[str, Any]]:
        """Full on-disk lineage for one entity -- real history, not a
        synthetic summary (spec section 13's own requirement)."""
        path = self._lineage_path()
        if not path.exists():
            return []
        out = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("entity_id") == entity_id:
                    out.append(rec)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_habitat.py:HabitatRuntime.get_lineage",
                exc=_aurora_boundary_exc,
                context={"function": "get_lineage", "source_file": "aurora_habitat.py"},
            )
        return out

    def get_affordances(self) -> Dict[str, Any]:
        """Discoverable vocabulary (spec section 27) -- what is
        possible, never what it is for."""
        return {
            "entity_types": list(ENTITY_TYPES),
            "territories": list(TERRITORIES),
            "owners": list(OWNERS),
            "operations": list(OPERATIONS),
            "consequence_dimensions": {
                operation: list(operation_consequence_dimensions(operation))
                for operation in OPERATIONS
            },
            "consequence_axis_profiles": {
                operation: consequence_axis_profile(operation_consequence_dimensions(operation))
                for operation in OPERATIONS
            },
            "permission_keys": list(_PERMISSION_KEYS),
        }

    # ── write side (spec sections 9, 10, 22) ────────────────────────────

    def act(self, *, actor: str, territory: str, operation: str,
            target_ids: Optional[List[str]] = None, parameters: Optional[Dict[str, Any]] = None,
            intention_context: str = "", session_id: str = "",
            causal_context: Optional[Dict[str, Any]] = None) -> EnvironmentConsequence:
        """The one canonical entry point for every environmental change,
        by Aurora or a human alike (spec section 9)."""
        action = EnvironmentAction(
            action_id=_new_id("hact"), actor=actor, territory=territory, operation=operation,
            target_ids=list(target_ids or []), parameters=dict(parameters or {}),
            intention_context=intention_context, causal_context=dict(causal_context or {}),
        )
        with self._lock:
            consequence = self._execute(action)
            pre_state = consequence.state_delta.get("_pre")
            post_state = consequence.state_delta.get("_post")
            consequence.state_delta.pop("_pre", None)
            consequence.state_delta.pop("_post", None)
            consequence.causal_parent = self._find_causal_parent(action)
            self._persist_event(action, consequence, pre_state, post_state, session_id=session_id)
            if consequence.success:
                self._save_world_state()
        # Deliberately outside the lock: none of these mutate habitat
        # state, and constraint/SediMemory/genealogy have their own
        # internals.
        self._emit_constraint_evidence(action, consequence, pre_state, post_state)
        if consequence.success:
            self._deposit_sediment(action, consequence, pre_state, post_state)
        self._emit_resolution_pressure(action, consequence, pre_state, post_state)
        return consequence

    def _find_causal_parent(self, action: EnvironmentAction) -> Optional[str]:
        """Structural adjacency only (spec section 17): the most recent
        action by a DIFFERENT actor that touched one of the same
        entities, within the recency window. No inference about
        agreement/disagreement/intent -- that belongs to Aurora."""
        if not action.target_ids:
            return None
        cutoff = action.timestamp - _RESPONSE_LINK_WINDOW_S
        for ev in reversed(self._recent_events):
            if ev.get("actor") == action.actor:
                continue
            if ev.get("timestamp", 0.0) < cutoff:
                break
            if set(ev.get("entity_ids") or []) & set(action.target_ids):
                return ev.get("event_id")
        return None

    def link_response(self, original_action_event_id: str, response_event_id: str) -> None:
        """Explicit causal link when a caller already knows two events
        are related (used by _find_causal_parent's callers or by
        higher-level code that wants to force a link outside the
        recency-window heuristic)."""
        for ev in self._recent_events:
            if ev.get("event_id") == original_action_event_id:
                ev["human_response"] = response_event_id
                break

    # ── permission law (spec sections 10, 24; Rule 10) ──────────────────

    def _check_permission(self, actor: str, territory: str, operation: str,
                           entities: List[HabitatEntity]) -> Tuple[bool, str]:
        if operation == "create":
            if territory == "self" and actor != "aurora":
                return False, "self_territory_is_aurora_owned"
            return True, ""
        for e in entities:
            if e.deleted and operation != "restore":
                return False, "entity_deleted"
            if operation == "transfer":
                if not e.interaction_permissions.get("transferable", True):
                    return False, "not_transferable"
                continue
            if operation in ("grant_permission", "revoke_permission"):
                if e.owner not in (actor, "shared"):
                    return False, "only_owner_grants_permission"
                continue
            if not e.is_modifiable_by(actor):
                return False, "not_modifiable_by_actor"
        return True, ""

    # ── operation dispatch ───────────────────────────────────────────────

    def _execute(self, action: EnvironmentAction) -> EnvironmentConsequence:
        op = action.operation
        if op not in OPERATIONS:
            return EnvironmentConsequence(
                action_id=action.action_id, success=False, actor=action.actor, operation=op,
                permission_result="denied:unknown_operation", rejected_reason="unknown_operation",
            )
        targets = [self._entities[t] for t in action.target_ids if t in self._entities]
        ok, reason = self._check_permission(action.actor, action.territory, op, targets)
        if not ok:
            return EnvironmentConsequence(
                action_id=action.action_id, success=False, actor=action.actor, operation=op,
                affected_entities=action.target_ids,
                permission_result=f"denied:{reason}", rejected_reason=reason,
            )

        handler = getattr(self, f"_op_{op}", None)
        if handler is None:
            return EnvironmentConsequence(
                action_id=action.action_id, success=False, actor=action.actor, operation=op,
                permission_result="denied:no_handler", rejected_reason="no_handler",
            )
        try:
            consequence = handler(action, targets)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation=f"exception_handler:aurora_habitat.py:_op_{op}",
                exc=_aurora_boundary_exc,
                context={"function": f"_op_{op}", "source_file": "aurora_habitat.py"},
            )
            return EnvironmentConsequence(
                action_id=action.action_id, success=False, actor=action.actor, operation=op,
                permission_result="denied:execution_error", rejected_reason="execution_error",
            )
        if consequence.success:
            # Build 717 (directive section 18/22): `targets` is the set of
            # entities that already existed BEFORE this action -- for
            # create/duplicate that is the source being duplicated (a real
            # re-interaction), never the newly-minted entity itself (whose
            # own creation must not count as a "revisit"). This is the only
            # place interaction_count is incremented anywhere in this
            # module -- previously it was written nowhere, so observe()'s
            # aurora_created_unrevisited check (interaction_count == 0) was
            # vacuously true for every entity regardless of real history.
            for e in targets:
                e.interaction_count += 1
        return consequence

    def _op_create(self, action: EnvironmentAction, _targets: List[HabitatEntity]) -> EnvironmentConsequence:
        p = action.parameters
        entity_type = str(p.get("entity_type", "shape"))
        if entity_type not in ENTITY_TYPES:
            entity_type = "shape"
        owner = str(p.get("owner") or ("shared" if action.territory == "space" else action.actor))
        if owner not in OWNERS:
            owner = action.actor
        entity = HabitatEntity(
            id=_new_id("e"), entity_type=entity_type, creator=action.actor, owner=owner,
            territory=action.territory,
            position=[_clamp01(x) for x in (p.get("position") or [0.5, 0.5])][:2] or [0.5, 0.5],
            dimensions=[_clamp01(x) for x in (p.get("dimensions") or [0.1, 0.1])][:2] or [0.1, 0.1],
            orientation=float(p.get("orientation", 0.0) or 0.0),
            layer=int(p.get("layer", 0) or 0),
            visual_properties=dict(p.get("visual_properties") or {}),
            temporal_properties=dict(p.get("temporal_properties") or {}),
            content=dict(p.get("content") or {}),
            interaction_permissions=_default_permissions(action.territory, owner),
            lineage={"parent_ids": [], "origin_action_id": action.action_id, "generation": 0},
        )
        self._entities[entity.id] = entity
        self._persist_lineage(entity.id, "created", action_id=action.action_id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="create",
            affected_entities=[entity.id], permission_result="granted",
            state_delta={"_post": entity.to_dict()},
            resulting_state={"created": entity.id},
        )

    def _op_duplicate(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        src = targets[0]
        pre = src.to_dict()
        dup = HabitatEntity.from_dict(src.to_dict())
        dup.id = _new_id("e")
        dup.creator = action.actor
        dup.created_at = _now()
        dup.modified_at = dup.created_at
        dup.revision_count = 0
        dup.interaction_count = 0
        dup.lineage = {"parent_ids": [src.id], "origin_action_id": action.action_id,
                        "generation": int((src.lineage or {}).get("generation", 0)) + 1}
        self._entities[dup.id] = dup
        self._persist_lineage(dup.id, "duplicated", parent_ids=[src.id], action_id=action.action_id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="duplicate",
            affected_entities=[src.id, dup.id], permission_result="granted",
            state_delta={"_pre": pre, "_post": dup.to_dict()},
            resulting_state={"duplicated_from": src.id, "new_id": dup.id},
        )

    def _op_delete(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        affected = []
        pre, post = {}, {}
        for e in targets:
            pre[e.id] = e.to_dict()
            e.deleted = True
            e.modified_at = _now()
            post[e.id] = e.to_dict()
            affected.append(e.id)
            self._persist_lineage(e.id, "deleted", action_id=action.action_id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="delete",
            affected_entities=affected, permission_result="granted",
            state_delta={"_pre": pre, "_post": post},
        )

    def _op_restore(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        affected = []
        pre, post = {}, {}
        any_changed = False
        for e in targets:
            pre[e.id] = e.to_dict()
            was_deleted = e.deleted
            e.deleted = False
            if was_deleted:
                e.modified_at = _now()
                any_changed = True
                self._persist_lineage(e.id, "restored", action_id=action.action_id)
            post[e.id] = e.to_dict()
            affected.append(e.id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="restore",
            affected_entities=affected, permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=any_changed,
        )

    def _mutate_simple(self, action: EnvironmentAction, targets: List[HabitatEntity],
                        apply_fn) -> EnvironmentConsequence:
        """Build 717 (follow-up): apply_fn's own effect is measured via a
        real before/after semantic diff -- revision_count/modified_at/
        lineage persistence (developmental evidence) only advance when
        something actually, observably changed, never on a legally-granted
        but vacuous call (e.g. move with no real displacement)."""
        if not targets:
            return self._deny(action, "no_target")
        affected = []
        pre, post = {}, {}
        any_changed = False
        for e in targets:
            pre_dict = e.to_dict()
            pre[e.id] = pre_dict
            apply_fn(e, action.parameters)
            post_dict = e.to_dict()
            changed = _entity_state_changed(pre_dict, post_dict)
            if changed:
                e.modified_at = _now()
                e.revision_count += 1
                post_dict = e.to_dict()
                self._persist_lineage(e.id, "transformed", action_id=action.action_id)
                any_changed = True
            post[e.id] = post_dict
            affected.append(e.id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation=action.operation,
            affected_entities=affected, permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=any_changed,
        )

    def _op_move(self, action, targets):
        def apply(e, p):
            e.position = [_clamp01(p.get("x", e.position[0])), _clamp01(p.get("y", e.position[1]))]
        return self._mutate_simple(action, targets, apply)

    def _op_resize(self, action, targets):
        def apply(e, p):
            e.dimensions = [
                max(0.0, min(1.0, float(p.get("width", e.dimensions[0])))),
                max(0.0, min(1.0, float(p.get("height", e.dimensions[1])))),
            ]
        return self._mutate_simple(action, targets, apply)

    def _op_rotate(self, action, targets):
        def apply(e, p):
            e.orientation = float(p.get("degrees", e.orientation)) % 360.0
        return self._mutate_simple(action, targets, apply)

    def _op_recolor(self, action, targets):
        def apply(e, p):
            for key in ("color", "opacity", "border", "texture"):
                if key in p:
                    e.visual_properties[key] = p[key]
        return self._mutate_simple(action, targets, apply)

    def _op_connect(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if len(targets) < 2:
            return self._deny(action, "connect_requires_two_targets")
        a, b = targets[0], targets[1]
        pre = {a.id: a.to_dict(), b.id: b.to_dict()}
        changed = False
        if b.id not in a.links:
            a.links.append(b.id)
            changed = True
        if a.id not in b.links:
            b.links.append(a.id)
            changed = True
        if changed:
            a.modified_at = b.modified_at = _now()
            self._persist_lineage(a.id, "combined", parent_ids=[b.id], action_id=action.action_id)
        post = {a.id: a.to_dict(), b.id: b.to_dict()}
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="connect",
            affected_entities=[a.id, b.id], permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=changed,
        )

    def _op_disconnect(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if len(targets) < 2:
            return self._deny(action, "disconnect_requires_two_targets")
        a, b = targets[0], targets[1]
        pre = {a.id: a.to_dict(), b.id: b.to_dict()}
        changed = (b.id in a.links) or (a.id in b.links)
        a.links = [x for x in a.links if x != b.id]
        b.links = [x for x in b.links if x != a.id]
        if changed:
            a.modified_at = b.modified_at = _now()
        post = {a.id: a.to_dict(), b.id: b.to_dict()}
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="disconnect",
            affected_entities=[a.id, b.id], permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=changed,
        )

    def _op_group(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        owner = str(action.parameters.get("owner") or ("shared" if action.territory == "space" else action.actor))
        group = HabitatEntity(
            id=_new_id("e"), entity_type="group", creator=action.actor, owner=owner,
            territory=action.territory,
            interaction_permissions=_default_permissions(action.territory, owner),
            lineage={"parent_ids": [t.id for t in targets], "origin_action_id": action.action_id, "generation": 0},
        )
        pre = {t.id: t.to_dict() for t in targets}
        for t in targets:
            t.group_membership = group.id
            t.modified_at = _now()
        self._entities[group.id] = group
        post = {t.id: t.to_dict() for t in targets}
        post[group.id] = group.to_dict()
        self._persist_lineage(group.id, "combined", parent_ids=[t.id for t in targets], action_id=action.action_id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="group",
            affected_entities=[group.id] + [t.id for t in targets], permission_result="granted",
            state_delta={"_pre": pre, "_post": post},
            resulting_state={"group_id": group.id},
        )

    def _op_ungroup(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        group = targets[0]
        members = [e for e in self._entities.values() if e.group_membership == group.id]
        pre = {m.id: m.to_dict() for m in members}
        for m in members:
            m.group_membership = None
            m.modified_at = _now()
        group.deleted = True
        post = {m.id: m.to_dict() for m in members}
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="ungroup",
            affected_entities=[group.id] + [m.id for m in members], permission_result="granted",
            state_delta={"_pre": pre, "_post": post},
        )

    def _op_transfer(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        """Boundary transition (spec section 23): the entity keeps its
        identity (same id, full lineage) while territory/owner change.
        This is the only place ownership or territory changes."""
        if not targets:
            return self._deny(action, "no_target")
        p = action.parameters
        new_owner = str(p.get("owner", "shared"))
        if new_owner not in OWNERS:
            new_owner = "shared"
        new_territory = str(p.get("territory") or targets[0].territory)
        if new_territory not in TERRITORIES:
            new_territory = targets[0].territory
        affected, pre, post = [], {}, {}
        any_changed = False
        for e in targets:
            pre[e.id] = e.to_dict()
            changed = (e.owner != new_owner) or (e.territory != new_territory)
            e.owner = new_owner
            e.territory = new_territory
            if changed:
                e.modified_at = _now()
                # Crossing into Self resets to Self's conservative default
                # unless the acting owner explicitly overrides; crossing
                # into Space opens up, matching each territory's own law.
                e.interaction_permissions = _default_permissions(new_territory, new_owner)
                self._persist_lineage(e.id, "transferred", action_id=action.action_id)
                any_changed = True
            post[e.id] = e.to_dict()
            affected.append(e.id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation="transfer",
            affected_entities=affected, permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=any_changed,
            resulting_state={"new_owner": new_owner, "new_territory": new_territory},
        )

    def _op_grant_permission(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        return self._set_permission(action, targets, True)

    def _op_revoke_permission(self, action: EnvironmentAction, targets: List[HabitatEntity]) -> EnvironmentConsequence:
        return self._set_permission(action, targets, False)

    def _set_permission(self, action: EnvironmentAction, targets: List[HabitatEntity], value: bool) -> EnvironmentConsequence:
        if not targets:
            return self._deny(action, "no_target")
        key = str(action.parameters.get("permission", ""))
        if key not in _PERMISSION_KEYS:
            return self._deny(action, "unknown_permission_key")
        affected, pre, post = [], {}, {}
        any_changed = False
        for e in targets:
            pre[e.id] = e.to_dict()
            changed = e.interaction_permissions.get(key) != value
            e.interaction_permissions[key] = value
            if changed:
                e.modified_at = _now()
                any_changed = True
            post[e.id] = e.to_dict()
            affected.append(e.id)
        return EnvironmentConsequence(
            action_id=action.action_id, success=True, actor=action.actor, operation=action.operation,
            affected_entities=affected, permission_result="granted",
            state_delta={"_pre": pre, "_post": post}, state_changed=any_changed,
        )

    def _deny(self, action: EnvironmentAction, reason: str) -> EnvironmentConsequence:
        return EnvironmentConsequence(
            action_id=action.action_id, success=False, actor=action.actor, operation=action.operation,
            permission_result=f"denied:{reason}", rejected_reason=reason,
        )

    # ── consequence reaching Aurora's real cognition (Rule 5, Rule 6) ───

    def _emit_constraint_evidence(
        self,
        action: EnvironmentAction,
        consequence: EnvironmentConsequence,
        pre_state: Optional[Dict[str, Any]] = None,
        post_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Route habitat events into Aurora's REAL constraint physics
        (spec section 22) via the same WaveformPressurePump entry point
        perceptual subsystems already use -- never a bespoke habitat-only
        learning channel (Rule 6)."""
        systems = self.systems
        if not systems:
            return
        ifield = systems.get("identity_field")
        pump = systems.get("pressure_pump")
        if ifield is None or pump is None:
            return
        try:
            from aurora_waveform_pressure import PressureDisturbance
            amps = _consequence_axis_amplitudes(
                action, consequence, pre_state, post_state,
            )
            disturbance = PressureDisturbance(
                source=f"habitat:{action.territory}:{action.operation}",
                axis_amplitudes=amps,
                intensity=0.55 if consequence.success else 0.30,
                coupling_mode="full",
            )
            pump.inject(disturbance, ifield, qao=systems.get("quasiarch_observer"))
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_habitat.py:_emit_constraint_evidence",
                exc=_aurora_boundary_exc,
                context={"function": "_emit_constraint_evidence", "source_file": "aurora_habitat.py"},
            )

    def _deposit_sediment(
        self,
        action: EnvironmentAction,
        consequence: EnvironmentConsequence,
        pre_state: Optional[Dict[str, Any]] = None,
        post_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Deposit the raw event into SediMemory as real experience
        (spec section 19) -- content only, no interpretation of what it
        means (spec section 13)."""
        systems = self.systems
        if not systems:
            return
        sedimemory = systems.get("sedimemory")
        if sedimemory is None or not hasattr(sedimemory, "ingest_event"):
            return
        try:
            from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
            from foundational_contract import ExistenceMode
            amps = _consequence_axis_amplitudes(
                action, consequence, pre_state, post_state,
            )
            cv = ConstraintVector(
                X=max(0.05, amps["X"]), T=0.2, N=amps["N"], B=amps["B"], A=amps["A"],
            )
            content = {
                "source": "habitat", "territory": action.territory, "operation": action.operation,
                "actor": action.actor, "affected_entities": list(consequence.affected_entities),
                # Stable environmental identity is preserved as provenance so
                # an ordinary SediMemory reactivation can bind back to the same
                # Habitat entity without a Habitat-only memory index.
                "entity_ids": list(consequence.affected_entities),
                "action_id": action.action_id,
                "success": consequence.success,
                "state_changed": consequence.state_changed,
                "consequence_dimensions": list(_actual_consequence_dimensions(
                    action, consequence, pre_state, post_state,
                )),
                "intention_context": action.intention_context,
            }
            sedimemory.ingest_event(
                content=content, constraint_vector=cv, source="habitat",
                existence_mode=ExistenceMode.AGENTIC if action.actor == "aurora" else ExistenceMode.PERSISTENT,
            )
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_habitat.py:_deposit_sediment",
                exc=_aurora_boundary_exc,
                context={"function": "_deposit_sediment", "source_file": "aurora_habitat.py"},
            )

    def _emit_resolution_pressure(
        self,
        action: EnvironmentAction,
        consequence: EnvironmentConsequence,
        pre_state: Optional[Dict[str, Any]] = None,
        post_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Route the real consequence through adaptive resolution.

        A staged candidate receives credit only when the selecting consumer
        supplied a candidate-conditioned counterfactual and this exact action
        produced the consequence being compared.  Ambient aggregate
        discrepancy remains useful pressure, but cannot by itself retain a
        candidate value.
        """
        try:
            from aurora_representational_address import RepresentationalRef
            from aurora_representational_resolution import record_ref_participation_from_scores
        except Exception:
            return
        try:
            entity_type = "unknown"
            owner_bucket = "none"
            scores = {
                "succeeded": 1.0 if (consequence.success and consequence.state_changed) else 0.0,
                "state_changed": 1.0 if consequence.state_changed else 0.0,
                "was_measured_response": 1.0 if consequence.causal_parent else 0.0,
            }
            for eid in consequence.affected_entities:
                entity = self._entities.get(eid)
                if entity is None:
                    continue
                entity_type = entity.entity_type
                if entity.owner == action.actor:
                    owner_bucket = "own"
                    scores["ownership_aligned"] = 1.0
                elif entity.owner in ("aurora", "human"):
                    owner_bucket = "other"
                    scores["ownership_aligned"] = 0.0
                else:
                    owner_bucket = entity.owner or "none"
                scores["recurring_interaction"] = 1.0 if entity.interaction_count > 1 else 0.0
                break
            context_tag = f"{action.territory}:{entity_type}:{action.actor}:{owner_bucket}"
            actual_dimensions = list(_actual_consequence_dimensions(
                action, consequence, pre_state, post_state,
            ))
            axis_profile = consequence_axis_profile(actual_dimensions)
            participating_refs = {
                RepresentationalRef.for_c1(axis, "OPERATOR", "A").encode(): weight
                for axis, weight in axis_profile.items()
                if float(weight) > 0.0
            }
            # A real choice/attempt is agency evidence regardless of which
            # physical operation happened to instantiate it.
            agency_ref = RepresentationalRef.for_c1("A", "OPERATOR", "A").encode()
            participating_refs[agency_ref] = max(
                float(participating_refs.get(agency_ref, 0.0)),
                0.35 if consequence.success else 0.15,
            )
            if not consequence.success:
                boundary_ref = RepresentationalRef.for_c1("B", "OPERATOR", "A").encode()
                participating_refs[boundary_ref] = max(
                    float(participating_refs.get(boundary_ref, 0.0)), 0.20,
                )
            evaluated_refs = set()
            for evaluation in list((action.causal_context or {}).get("candidate_evaluations") or []):
                ref_encoded = str(evaluation.get("ref_encoded") or "")
                if not ref_encoded:
                    continue
                baseline_dimensions = list(evaluation.get("expected_dimensions_without_candidate") or [])
                conditioned_dimensions = list(evaluation.get("expected_dimensions_with_candidate") or [])
                baseline_error = _expectation_error(baseline_dimensions, actual_dimensions)
                conditioned_error = _expectation_error(conditioned_dimensions, actual_dimensions)

                baseline_parameters = dict(evaluation.get("parameters_without_candidate") or {})
                conditioned_parameters = dict(evaluation.get("parameters_with_candidate") or {})
                if baseline_parameters != conditioned_parameters:
                    baseline_error = (baseline_error + _parameter_error(baseline_parameters, action.parameters)) / 2.0
                    conditioned_error = (conditioned_error + _parameter_error(conditioned_parameters, action.parameters)) / 2.0

                candidate_evaluation = dict(evaluation)
                candidate_evaluation.update({
                    "actual_consequence": {
                        "action_id": action.action_id,
                        "operation": action.operation,
                        "parameters": dict(action.parameters),
                        "success": bool(consequence.success),
                        "state_changed": bool(consequence.state_changed),
                        "affected_entities": list(consequence.affected_entities),
                        "consequence_dimensions": actual_dimensions,
                    },
                    "candidate_conditioned_error": round(conditioned_error, 6),
                    "baseline_error": round(baseline_error, 6),
                })
                # The caller-owned evaluation list is the same causal record
                # later persisted by motivation telemetry. Join the measured
                # outcome back into it so the arbitration and resolution
                # ledgers expose one inspectable before/after chain.
                evaluation.update({
                    "actual_consequence": dict(candidate_evaluation["actual_consequence"]),
                    "candidate_conditioned_error": candidate_evaluation["candidate_conditioned_error"],
                    "baseline_error": candidate_evaluation["baseline_error"],
                })
                candidate_scores = dict(scores)
                candidate_scores["conditioned_consequence_match"] = max(0.0, 1.0 - conditioned_error)
                candidate_scores["physical_consequence_axis_weight"] = float(
                    participating_refs.get(ref_encoded, 0.0)
                )
                record_ref_participation_from_scores(
                    self.systems, ref_encoded, candidate_scores,
                    source="habitat", context_tag=context_tag,
                    extra_trace_ids=[f"HABITAT_CTX:{context_tag}"],
                    candidate_evaluation=candidate_evaluation,
                )
                evaluated_refs.add(ref_encoded)

            # Preserve the real consequence stream for every native axis the
            # physical dimensions intersect. If a ref was candidate-
            # conditioned above, do not complete it twice.
            for ref_encoded, weight in participating_refs.items():
                if ref_encoded in evaluated_refs:
                    continue
                axis_scores = dict(scores)
                axis_scores["physical_consequence_axis_weight"] = float(weight)
                record_ref_participation_from_scores(
                    self.systems, ref_encoded, axis_scores,
                    source="habitat", context_tag=context_tag,
                    extra_trace_ids=[f"HABITAT_CTX:{context_tag}"],
                )
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_habitat.py:_emit_resolution_pressure",
                exc=_aurora_boundary_exc,
                context={"function": "_emit_resolution_pressure", "source_file": "aurora_habitat.py"},
            )

    # ── attention-surface for the proactive loop (spec sections 15, 28) ─

    def observe(self, *, actor: str = "aurora", territory: Optional[str] = None,
                since: Optional[float] = None) -> Dict[str, Any]:
        """Environmental availability for the caller's own attention/
        curiosity/pressure machinery to select from (spec section 15) --
        this method never decides that anything matters, only reports
        what exists to be attended to."""
        cutoff = since if since is not None else (_now() - 3600.0)
        recent = [ev for ev in self._recent_events if ev.get("timestamp", 0.0) >= cutoff]
        recent_by_human = [ev for ev in recent if ev.get("actor") == "human"]
        recent_by_aurora = [ev for ev in recent if ev.get("actor") == "aurora"]
        with self._lock:
            unvisited = [
                e.id for e in self._entities.values()
                if not e.deleted and e.creator == "aurora"
                and e.modified_at < cutoff and e.interaction_count == 0
            ]
        return {
            "as_of": _now(),
            "state": self.get_state(territory=territory, actor=actor),
            "recent_events": recent[-20:],
            "recent_human_actions": len(recent_by_human),
            "recent_aurora_actions": len(recent_by_aurora),
            "aurora_created_unrevisited": unvisited[:20],
        }

    def integrity_report(self) -> Dict[str, Any]:
        """Human-facing diagnostic counts only (spec section 46) -- raw
        evidence, no developmental judgments."""
        with self._lock:
            entities = list(self._entities.values())
        live = [e for e in entities if not e.deleted]
        transfers = 0
        try:
            for line in (self._lineage_path().read_text(encoding="utf-8").splitlines()
                         if self._lineage_path().exists() else []):
                if line.strip() and json.loads(line).get("event") == "transferred":
                    transfers += 1
        except Exception:
            pass
        events_on_disk = 0
        try:
            if self._events_path().exists():
                with self._events_path().open("r", encoding="utf-8") as f:
                    events_on_disk = sum(1 for _ in f)
        except Exception:
            pass
        return {
            "entity_count": len(live),
            "deleted_count": len(entities) - len(live),
            "aurora_created": sum(1 for e in live if e.creator == "aurora"),
            "human_created": sum(1 for e in live if e.creator == "human"),
            "territory_transitions": transfers,
            "event_count_on_disk": events_on_disk,
            "recent_event_count": len(self._recent_events),
            "world_state_exists": self._world_state_path().exists(),
            "persistence_health": "ok" if self._world_state_path().exists() or not live else "unsaved",
        }

    # ── human-only maintenance (spec section 32) ────────────────────────

    def backup(self, backups_dir: Optional[Path] = None) -> str:
        dest_dir = Path(backups_dir) if backups_dir else (self.root / "backups")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"world_state_{int(_now())}.json"
        if self._world_state_path().exists():
            dest.write_text(self._world_state_path().read_text(encoding="utf-8"), encoding="utf-8")
        else:
            self._save_world_state()
            dest.write_text(self._world_state_path().read_text(encoding="utf-8"), encoding="utf-8")
        return str(dest)

    def restore_from_backup(self, backup_path: str) -> bool:
        p = Path(backup_path)
        if not p.exists():
            return False
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return False
        with self._lock:
            self._entities = {}
            for eid, edict in (raw.get("entities") or {}).items():
                try:
                    self._entities[eid] = HabitatEntity.from_dict(edict)
                except Exception:
                    continue
            self._save_world_state()
        return True

    def isolate_corrupt_entities(self) -> List[str]:
        """Move entities that fail to round-trip through HabitatEntity
        into a quarantined, non-live state rather than crashing normal
        operation. Returns the isolated entity ids."""
        isolated = []
        with self._lock:
            for eid, e in list(self._entities.items()):
                try:
                    HabitatEntity.from_dict(e.to_dict())
                except Exception:
                    e.deleted = True
                    e.visual_properties["_quarantined"] = True
                    isolated.append(eid)
            if isolated:
                self._save_world_state()
        return isolated

    def reset(self) -> None:
        """Full Habitat reset -- human-only, never reachable from a
        normal environmental action (spec section 32)."""
        with self._lock:
            self._entities = {}
            self._recent_events = []
            self._recent_motivation_events = []
            self._save_world_state()
