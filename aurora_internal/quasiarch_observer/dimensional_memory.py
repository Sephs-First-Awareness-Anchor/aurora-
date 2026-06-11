"""
dimensional_memory_constant_standalone_demo.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Authors : Sunni (Sir) Morningstar and Cael Devo
Purpose : Persistence substrate — the nervous system.
          Stores crystal instances, lineage edges, collapsed genealogy layers,
          issue-family indexes, and quasicrystal retrieval surfaces.
          Does NOT define semantics (crystal_engine).
          Does NOT manage promotion/lifecycle (dimensional_processing).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Storage architecture
  Nodes     — one DataNode per CrystalInstance (keyed by crystal_id)
  Edges     — LineageEdge records linking parent → child across orders
  Indexes   — IssueFamilyIndex, StrategyIndex, TargetIndex for fast retrieval
  Relics    — archived lower-order states after collapse (compressed, read-only)
  Journal   — append-only operation log for traceability
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import itertools
import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from .crystal_engine import CrystalEngine, CrystalOrder
from .dimensional_processing import (
    CrystalInstance,
    DoctrineObject,
    QuasiInnerStrata,
    RelationalPoint,
    RotationResult,
)
from .ghost_relics import GhostRelicSystem


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(obj: Any) -> Any:
    """JSON serialisation fallback for custom types."""
    if isinstance(obj, CrystalOrder):
        return obj.name
    if isinstance(obj, QuasiInnerStrata):
        return {
            "representative_base_events": obj.representative_base_events,
            "recurrence_summary"        : obj.recurrence_summary,
            "strategy_success_stats"    : obj.strategy_success_stats,
            "failure_counterexamples"   : obj.failure_counterexamples,
            "coherence_index"           : obj.coherence_index,
            "novelty_index"             : obj.novelty_index,
            "genealogy_depth"           : obj.genealogy_depth,
            "formation_timestamp"       : obj.formation_timestamp,
        }
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def _unique_preserve_order(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _split_compound_field(raw_value: str) -> List[str]:
    if not raw_value:
        return []
    separators = ("  |  ", " OR ", "|", ";")
    values = [raw_value]
    for sep in separators:
        if sep in raw_value:
            values = [part.strip() for part in raw_value.split(sep)]
            break
    return [value for value in values if value and value.lower() != "none"]


# ══════════════════════════════════════════════════════════════════════════════
# DATA NODE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DataNode:
    """
    A persistent record of a CrystalInstance.

    This is what gets written to disk and indexed.  It is a serialisable
    snapshot of the crystal at a given moment.  The live CrystalInstance is
    the working object; the DataNode is the durable record.

    Attributes
    ----------
    node_id        : Matches the CrystalInstance.crystal_id.
    order          : CrystalOrder name string.
    payload        : Serialised facet_values dict.
    point_scores   : Dict of point_name → score (lightweight point record).
    resolution_fidelity : Float from the live crystal.
    base_event_ids : List of contributing base event IDs.
    parent_ids     : Parent node IDs in the lineage graph.
    child_ids      : Child node IDs.
    tags           : String labels for retrieval.
    quasi_strata   : Serialised QuasiInnerStrata if order == QUASI.
    rotation_history : Rotation result records.
    lineage_meta    : Versioning metadata for issue-family evolution.
    created_at     : ISO timestamp of original formation.
    persisted_at   : ISO timestamp of this node write.
    is_relic       : True if this node is archived after collapse.
    checksum       : Lightweight hash for corruption detection.
    """
    node_id             : str
    order               : str
    payload             : Dict[str, Any]
    point_scores        : Dict[str, float]
    resolution_fidelity : float
    base_event_ids      : List[str]
    parent_ids          : List[str]
    child_ids           : List[str]
    tags                : List[str]
    quasi_strata        : Optional[Dict[str, Any]]
    rotation_history    : List[Dict[str, Any]]
    lineage_meta        : Dict[str, Any]
    created_at          : str
    persisted_at        : str
    is_relic            : bool
    checksum            : str

    @classmethod
    def from_crystal(cls, crystal: CrystalInstance, is_relic: bool = False) -> "DataNode":
        """Build a DataNode from a live CrystalInstance."""
        point_scores = {
            k: v.score for k, v in crystal.relational_points.items()
        }
        strata_dict = None
        if crystal.quasi_strata is not None:
            strata_dict = {
                "representative_base_events": crystal.quasi_strata.representative_base_events,
                "recurrence_summary"        : crystal.quasi_strata.recurrence_summary,
                "strategy_success_stats"    : crystal.quasi_strata.strategy_success_stats,
                "failure_counterexamples"   : crystal.quasi_strata.failure_counterexamples,
                "coherence_index"           : crystal.quasi_strata.coherence_index,
                "novelty_index"             : crystal.quasi_strata.novelty_index,
                "genealogy_depth"           : crystal.quasi_strata.genealogy_depth,
                "formation_timestamp"       : crystal.quasi_strata.formation_timestamp,
            }

        payload = dict(crystal.facet_values)
        checksum = cls._compute_checksum(crystal.crystal_id, payload)

        return cls(
            node_id             = crystal.crystal_id,
            order               = crystal.order.name,
            payload             = payload,
            point_scores        = point_scores,
            resolution_fidelity = crystal.resolution_fidelity,
            base_event_ids      = list(crystal.base_event_ids),
            parent_ids          = list(crystal.parent_ids),
            child_ids           = list(crystal.child_ids),
            tags                = list(crystal.tags),
            quasi_strata        = strata_dict,
            rotation_history    = list(crystal.rotation_history),
            lineage_meta        = dict(crystal.lineage_meta),
            created_at          = crystal.created_at,
            persisted_at        = _utcnow(),
            is_relic            = is_relic,
            checksum            = checksum,
        )

    @staticmethod
    def _compute_checksum(node_id: str, payload: Dict[str, Any]) -> str:
        """Simple deterministic checksum for corruption detection."""
        import hashlib
        raw = node_id + json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def verify_checksum(self) -> bool:
        """Return True if payload has not been corrupted since write."""
        expected = self._compute_checksum(self.node_id, self.payload)
        return expected == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id"             : self.node_id,
            "order"               : self.order,
            "payload"             : self.payload,
            "point_scores"        : self.point_scores,
            "resolution_fidelity" : self.resolution_fidelity,
            "base_event_ids"      : self.base_event_ids,
            "parent_ids"          : self.parent_ids,
            "child_ids"           : self.child_ids,
            "tags"                : self.tags,
            "quasi_strata"        : self.quasi_strata,
            "rotation_history"    : self.rotation_history,
            "lineage_meta"        : self.lineage_meta,
            "created_at"          : self.created_at,
            "persisted_at"        : self.persisted_at,
            "is_relic"            : self.is_relic,
            "checksum"            : self.checksum,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataNode":
        return cls(
            node_id             = d["node_id"],
            order               = d["order"],
            payload             = d["payload"],
            point_scores        = d.get("point_scores", {}),
            resolution_fidelity = d.get("resolution_fidelity", 0.0),
            base_event_ids      = d.get("base_event_ids", []),
            parent_ids          = d.get("parent_ids", []),
            child_ids           = d.get("child_ids", []),
            tags                = d.get("tags", []),
            quasi_strata        = d.get("quasi_strata"),
            rotation_history    = d.get("rotation_history", []),
            lineage_meta        = d.get("lineage_meta", {}),
            created_at          = d.get("created_at", ""),
            persisted_at        = d.get("persisted_at", ""),
            is_relic            = d.get("is_relic", False),
            checksum            = d.get("checksum", ""),
        )


# ══════════════════════════════════════════════════════════════════════════════
# LINEAGE EDGE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LineageEdge:
    """
    A directed edge in the crystal lineage graph.

    parent_id → child_id across an order transition.
    Stores the transition type for audit trails.
    """
    edge_id        : str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id      : str = ""
    parent_order   : str = ""
    child_id       : str = ""
    child_order    : str = ""
    transition_type: str = ""   # "promotion" | "collapse" | "rotation_spawn"
    created_at     : str = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id"        : self.edge_id,
            "parent_id"      : self.parent_id,
            "parent_order"   : self.parent_order,
            "child_id"       : self.child_id,
            "child_order"    : self.child_order,
            "transition_type": self.transition_type,
            "created_at"     : self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LineageEdge":
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL INDEXES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IssueFamilyIndex:
    """
    Maps issue_category → set of node_ids at each crystal order.
    Primary retrieval surface for issue-based queries.
    """
    issue_category : str
    base_ids       : List[str] = field(default_factory=list)
    composite_ids  : List[str] = field(default_factory=list)
    higher_ids     : List[str] = field(default_factory=list)
    quasi_ids      : List[str] = field(default_factory=list)
    active_ids     : Dict[str, str] = field(default_factory=dict)
    latest_versions: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_category" : self.issue_category,
            "base_ids"       : self.base_ids,
            "composite_ids"  : self.composite_ids,
            "higher_ids"     : self.higher_ids,
            "quasi_ids"      : self.quasi_ids,
            "active_ids"     : self.active_ids,
            "latest_versions": self.latest_versions,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IssueFamilyIndex":
        return cls(**d)


@dataclass
class StrategyIndex:
    """
    Maps strategy_class → set of node_ids at higher-order and quasi levels.
    Used for strategy-based retrieval and comparison.
    """
    strategy_class  : str
    higher_ids      : List[str] = field(default_factory=list)
    quasi_ids       : List[str] = field(default_factory=list)
    avg_confidence  : float     = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_class" : self.strategy_class,
            "higher_ids"     : self.higher_ids,
            "quasi_ids"      : self.quasi_ids,
            "avg_confidence" : self.avg_confidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyIndex":
        return cls(**d)


@dataclass
class TargetIndex:
    """
    Maps target_identifier → set of node_ids across all orders.
    Used for target-location-based retrieval.
    """
    target_id   : str
    node_ids    : List[str] = field(default_factory=list)
    issue_categories : List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id"        : self.target_id,
            "node_ids"         : self.node_ids,
            "issue_categories" : self.issue_categories,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TargetIndex":
        return cls(**d)


@dataclass
class LogicTierIndex:
    """
    Maps logic_tier → node_ids at all crystal orders.
    Used for tier-based retrieval and cross-tier analysis.
    """
    logic_tier : str
    node_ids   : List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"logic_tier": self.logic_tier, "node_ids": self.node_ids}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LogicTierIndex":
        return cls(**d)


@dataclass
class QuasiArchetypeIndex:
    """
    Maps issue_archetype → quasicrystal node_ids.
    The primary quasicrystal retrieval surface for pattern matching.
    """
    archetype : str
    quasi_ids : List[str] = field(default_factory=list)
    max_confidence : float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype"     : self.archetype,
            "quasi_ids"     : self.quasi_ids,
            "max_confidence": self.max_confidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QuasiArchetypeIndex":
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# JOURNAL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class JournalEntry:
    """Append-only audit record for all memory operations."""
    entry_id   : str = field(default_factory=lambda: str(uuid.uuid4()))
    operation  : str = ""   # "write_node" | "write_relic" | "write_edge" | "update_index" | "load" | "delete"
    node_id    : str = ""
    order      : str = ""
    detail     : str = ""
    timestamp  : str = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id" : self.entry_id,
            "operation": self.operation,
            "node_id"  : self.node_id,
            "order"    : self.order,
            "detail"   : self.detail,
            "timestamp": self.timestamp,
        }


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE BACKEND
# ══════════════════════════════════════════════════════════════════════════════

class FileStorageBackend:
    """
    JSON-file-based storage backend.

    Directory layout
    ----------------
    base_dir/
      nodes/
        base/         — one .json per base DataNode
        composite/
        higher_order/
        quasi/
      relics/         — archived lower-order nodes post-collapse
      edges/          — one .json per LineageEdge
      indexes/
        issue_family/ — one .json per issue category
        strategy/     — one .json per strategy class
        target/       — one .json per target identifier
        logic_tier/   — one .json per logic tier
        quasi_archetype/ — one .json per archetype
      journal.jsonl   — append-only journal (newline-delimited JSON)
    """

    ORDER_DIRS = {
        "BASE"        : "base",
        "COMPOSITE"   : "composite",
        "HIGHER_ORDER": "higher_order",
        "QUASI"       : "quasi",
    }

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self._init_dirs()

    def _init_dirs(self) -> None:
        for order_dir in self.ORDER_DIRS.values():
            (self.base_dir / "nodes" / order_dir).mkdir(parents=True, exist_ok=True)
        (self.base_dir / "relics").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "edges").mkdir(parents=True, exist_ok=True)
        for idx in ("issue_family", "strategy", "target", "logic_tier", "quasi_archetype"):
            (self.base_dir / "indexes" / idx).mkdir(parents=True, exist_ok=True)

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def _node_path(self, node_id: str, order: str, is_relic: bool = False) -> Path:
        if is_relic:
            return self.base_dir / "relics" / f"{node_id}.json"
        order_dir = self.ORDER_DIRS.get(order, "base")
        return self.base_dir / "nodes" / order_dir / f"{node_id}.json"

    def write_node(self, node: DataNode) -> None:
        path = self._node_path(node.node_id, node.order, node.is_relic)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(node.to_dict(), fh, indent=2, default=str)

    def read_node(self, node_id: str, order: str, is_relic: bool = False) -> Optional[DataNode]:
        path = self._node_path(node_id, order, is_relic)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        node = DataNode.from_dict(data)
        if not node.verify_checksum():
            raise RuntimeError(
                f"Checksum mismatch on node {node_id} — possible corruption."
            )
        return node

    def delete_node(self, node_id: str, order: str, is_relic: bool = False) -> bool:
        path = self._node_path(node_id, order, is_relic)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_nodes(self, order: str, relics: bool = False) -> List[str]:
        if relics:
            return [p.stem for p in (self.base_dir / "relics").glob("*.json")]
        order_dir = self.ORDER_DIRS.get(order, "base")
        return [
            p.stem for p in (self.base_dir / "nodes" / order_dir).glob("*.json")
        ]

    def iter_nodes(self, order: str) -> Iterator[DataNode]:
        for node_id in self.list_nodes(order):
            node = self.read_node(node_id, order)
            if node:
                yield node

    # ── Edges ─────────────────────────────────────────────────────────────────

    def write_edge(self, edge: LineageEdge) -> None:
        path = self.base_dir / "edges" / f"{edge.edge_id}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(edge.to_dict(), fh, indent=2)

    def read_edges_for(self, node_id: str) -> List[LineageEdge]:
        """Return all edges where node_id is parent or child."""
        result = []
        for path in (self.base_dir / "edges").glob("*.json"):
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("parent_id") == node_id or data.get("child_id") == node_id:
                result.append(LineageEdge.from_dict(data))
        return result

    def list_edges(self) -> List[str]:
        return [p.stem for p in (self.base_dir / "edges").glob("*.json")]

    # ── Indexes ───────────────────────────────────────────────────────────────

    def _index_path(self, index_type: str, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(" ", "_")[:100]
        return self.base_dir / "indexes" / index_type / f"{safe_key}.json"

    def _write_index(self, index_type: str, key: str, data: Dict[str, Any]) -> None:
        path = self._index_path(index_type, key)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _read_index(self, index_type: str, key: str) -> Optional[Dict[str, Any]]:
        path = self._index_path(index_type, key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _list_index_keys(self, index_type: str) -> List[str]:
        return [
            p.stem for p in (self.base_dir / "indexes" / index_type).glob("*.json")
        ]

    def write_issue_family_index(self, idx: IssueFamilyIndex) -> None:
        self._write_index("issue_family", idx.issue_category, idx.to_dict())

    def read_issue_family_index(self, issue_category: str) -> Optional[IssueFamilyIndex]:
        data = self._read_index("issue_family", issue_category)
        return IssueFamilyIndex.from_dict(data) if data else None

    def list_issue_families(self) -> List[str]:
        return self._list_index_keys("issue_family")

    def write_strategy_index(self, idx: StrategyIndex) -> None:
        self._write_index("strategy", idx.strategy_class, idx.to_dict())

    def read_strategy_index(self, strategy_class: str) -> Optional[StrategyIndex]:
        data = self._read_index("strategy", strategy_class)
        return StrategyIndex.from_dict(data) if data else None

    def list_strategies(self) -> List[str]:
        return self._list_index_keys("strategy")

    def write_target_index(self, idx: TargetIndex) -> None:
        self._write_index("target", idx.target_id, idx.to_dict())

    def read_target_index(self, target_id: str) -> Optional[TargetIndex]:
        data = self._read_index("target", target_id)
        return TargetIndex.from_dict(data) if data else None

    def list_targets(self) -> List[str]:
        return self._list_index_keys("target")

    def write_logic_tier_index(self, idx: LogicTierIndex) -> None:
        self._write_index("logic_tier", idx.logic_tier, idx.to_dict())

    def read_logic_tier_index(self, tier: str) -> Optional[LogicTierIndex]:
        data = self._read_index("logic_tier", tier)
        return LogicTierIndex.from_dict(data) if data else None

    def list_logic_tiers(self) -> List[str]:
        return self._list_index_keys("logic_tier")

    def write_quasi_archetype_index(self, idx: QuasiArchetypeIndex) -> None:
        self._write_index("quasi_archetype", idx.archetype, idx.to_dict())

    def read_quasi_archetype_index(self, archetype: str) -> Optional[QuasiArchetypeIndex]:
        data = self._read_index("quasi_archetype", archetype)
        return QuasiArchetypeIndex.from_dict(data) if data else None

    def list_quasi_archetypes(self) -> List[str]:
        return self._list_index_keys("quasi_archetype")

    # ── Journal ───────────────────────────────────────────────────────────────

    def append_journal(self, entry: JournalEntry) -> None:
        journal_path = self.base_dir / "journal.jsonl"
        with journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def read_journal(self, tail: int = 50) -> List[Dict[str, Any]]:
        journal_path = self.base_dir / "journal.jsonl"
        if not journal_path.exists():
            return []
        lines = journal_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines[-tail:]]

    def read_journal_for_node(self, node_id: str) -> List[Dict[str, Any]]:
        """Return all journal entries referencing a given node_id."""
        journal_path = self.base_dir / "journal.jsonl"
        if not journal_path.exists():
            return []
        result = []
        for line in journal_path.read_text(encoding="utf-8").strip().splitlines():
            entry = json.loads(line)
            if entry.get("node_id") == node_id:
                result.append(entry)
        return result


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY STORE
# ══════════════════════════════════════════════════════════════════════════════

class DimensionalMemory:
    """
    Public interface to the persistence layer.

    Provides:
      - persist(crystal)         — write a CrystalInstance to storage
      - relic(crystal)           — archive a crystal as a collapsed relic
      - register_lineage_edge()  — record a parent→child transition
      - retrieve_by_*()          — retrieval surfaces
      - get_ancestry()           — full lineage trace for a node
      - get_quasi_by_archetype() — primary quasicrystal retrieval
      - live_save()              — flush all in-memory state to disk
      - load_all()               — hydrate in-memory cache from disk
    """

    def __init__(self, storage_dir: str = "./crystal_memory") -> None:
        self._backend  = FileStorageBackend(storage_dir)
        self._cache    : Dict[str, DataNode]     = {}   # node_id → DataNode
        self._edges    : Dict[str, LineageEdge]  = {}   # edge_id → LineageEdge
        self._issue_idx: Dict[str, IssueFamilyIndex]     = {}
        self._strat_idx: Dict[str, StrategyIndex]        = {}
        self._target_idx: Dict[str, TargetIndex]         = {}
        self._tier_idx : Dict[str, LogicTierIndex]       = {}
        self._arch_idx : Dict[str, QuasiArchetypeIndex]  = {}

    # ── Persist ───────────────────────────────────────────────────────────────

    def persist(self, crystal: CrystalInstance) -> DataNode:
        """
        Write a crystal to persistent storage and update all indexes.
        Returns the DataNode that was written.
        """
        node = DataNode.from_crystal(crystal, is_relic=False)
        self._backend.write_node(node)
        self._cache[node.node_id] = node
        self._update_indexes(node)
        self._backend.append_journal(JournalEntry(
            operation=f"write_node",
            node_id=node.node_id,
            order=node.order,
            detail=f"fidelity={node.resolution_fidelity:.3f}  tags={node.tags}",
        ))
        return node

    def relic(self, crystal: CrystalInstance) -> DataNode:
        """
        Archive a crystal as a relic.  Relics are read-only compressed ancestry
        records retained after collapse.  They are not indexed for active retrieval
        but are traceable via lineage edges.
        """
        node = DataNode.from_crystal(crystal, is_relic=True)
        self._backend.write_node(node)
        self._cache[node.node_id] = node
        self._backend.append_journal(JournalEntry(
            operation="write_relic",
            node_id=node.node_id,
            order=node.order,
            detail=f"archived as relic after collapse",
        ))
        return node

    # ── Lineage ───────────────────────────────────────────────────────────────

    def register_lineage_edge(
        self,
        parent: CrystalInstance,
        child: CrystalInstance,
        transition_type: str,
    ) -> LineageEdge:
        """Record a directed lineage edge from parent → child."""
        edge = LineageEdge(
            parent_id      = parent.crystal_id,
            parent_order   = parent.order.name,
            child_id       = child.crystal_id,
            child_order    = child.order.name,
            transition_type= transition_type,
        )
        self._backend.write_edge(edge)
        self._edges[edge.edge_id] = edge
        self._backend.append_journal(JournalEntry(
            operation="write_edge",
            node_id=edge.edge_id,
            order=f"{parent.order.name}→{child.order.name}",
            detail=f"{parent.crystal_id[:8]}→{child.crystal_id[:8]}  [{transition_type}]",
        ))
        return edge

    def register_lineage_edge_ids(
        self,
        parent_id: str,
        parent_order: str,
        child_id: str,
        child_order: str,
        transition_type: str,
    ) -> LineageEdge:
        """Record a directed lineage edge without requiring live crystal objects."""
        edge = LineageEdge(
            parent_id=parent_id,
            parent_order=parent_order,
            child_id=child_id,
            child_order=child_order,
            transition_type=transition_type,
        )
        self._backend.write_edge(edge)
        self._edges[edge.edge_id] = edge
        self._backend.append_journal(JournalEntry(
            operation="write_edge",
            node_id=edge.edge_id,
            order=f"{parent_order}→{child_order}",
            detail=f"{parent_id[:8]}→{child_id[:8]}  [{transition_type}]",
        ))
        return edge

    # ── Node retrieval ────────────────────────────────────────────────────────

    def get_node(
        self,
        node_id: str,
        order: Optional[str] = None,
        is_relic: bool = False,
    ) -> Optional[DataNode]:
        """
        Retrieve a node by ID.  Checks in-memory cache first, then disk.
        If order is not supplied, searches all order directories.
        """
        if node_id in self._cache:
            return self._cache[node_id]

        if order:
            node = self._backend.read_node(node_id, order, is_relic)
            if node:
                self._cache[node_id] = node
            return node

        # Search all orders
        for order_name in ("BASE", "COMPOSITE", "HIGHER_ORDER", "QUASI"):
            node = self._backend.read_node(node_id, order_name, is_relic=False)
            if node:
                self._cache[node_id] = node
                return node
        # Try relics
        node = self._backend.read_node(node_id, "", is_relic=True)
        if node:
            self._cache[node_id] = node
        return node

    def get_all_nodes_by_order(self, order: str) -> List[DataNode]:
        """Return all nodes at a given crystal order."""
        return list(self._backend.iter_nodes(order))

    def update_node_payload(
        self,
        node_id: str,
        order: str,
        updates: Dict[str, Any],
    ) -> Optional[DataNode]:
        """
        Live-update a node's payload dict with new key/value pairs.
        Rewrites the node to disk and refreshes the cache.
        """
        node = self.get_node(node_id, order)
        if node is None:
            return None
        node.payload.update(updates)
        node.persisted_at = _utcnow()
        node.checksum = DataNode._compute_checksum(node.node_id, node.payload)
        self._backend.write_node(node)
        self._cache[node_id] = node
        self._backend.append_journal(JournalEntry(
            operation="update_payload",
            node_id=node_id,
            order=order,
            detail=f"keys updated: {list(updates.keys())}",
        ))
        return node

    def update_node_lineage_meta(
        self,
        node_id: str,
        order: str,
        updates: Dict[str, Any],
    ) -> Optional[DataNode]:
        """
        Live-update a node's lineage metadata and refresh any affected indexes.
        """
        node = self.get_node(node_id, order)
        if node is None:
            return None
        node.lineage_meta.update(updates)
        node.persisted_at = _utcnow()
        self._backend.write_node(node)
        self._cache[node_id] = node
        self._update_indexes(node)
        self._backend.append_journal(JournalEntry(
            operation="update_lineage_meta",
            node_id=node_id,
            order=order,
            detail=f"keys updated: {list(updates.keys())}",
        ))
        return node

    # ── Retrieval surfaces ────────────────────────────────────────────────────

    def retrieve_by_issue_family(
        self,
        issue_category: str,
        order: Optional[str] = None,
    ) -> List[DataNode]:
        """
        Return all nodes belonging to the given issue family.
        Optionally filter by crystal order.
        """
        idx = self._issue_idx.get(issue_category) or \
              self._backend.read_issue_family_index(issue_category)
        if not idx:
            return []

        id_list: List[str] = []
        if order is None:
            id_list = (
                idx.base_ids + idx.composite_ids +
                idx.higher_ids + idx.quasi_ids
            )
        elif order == "BASE":
            id_list = idx.base_ids
        elif order == "COMPOSITE":
            id_list = idx.composite_ids
        elif order == "HIGHER_ORDER":
            id_list = idx.higher_ids
        elif order == "QUASI":
            id_list = idx.quasi_ids

        result = []
        for nid in id_list:
            node = self.get_node(nid)
            if node:
                result.append(node)
        return result

    def retrieve_by_strategy_class(
        self,
        strategy_class: str,
    ) -> List[DataNode]:
        """Return all higher-order and quasi nodes using a given strategy class."""
        idx = self._strat_idx.get(strategy_class) or \
              self._backend.read_strategy_index(strategy_class)
        if not idx:
            return []
        ids = idx.higher_ids + idx.quasi_ids
        return [n for n in (self.get_node(nid) for nid in ids) if n]

    def retrieve_by_target(self, target_id: str) -> List[DataNode]:
        """Return all nodes associated with a given target location."""
        idx = self._target_idx.get(target_id) or \
              self._backend.read_target_index(target_id)
        if not idx:
            return []
        return [n for n in (self.get_node(nid) for nid in idx.node_ids) if n]

    def retrieve_by_logic_tier(self, logic_tier: str) -> List[DataNode]:
        """Return all nodes in a given logic tier."""
        idx = self._tier_idx.get(logic_tier) or \
              self._backend.read_logic_tier_index(logic_tier)
        if not idx:
            return []
        return [n for n in (self.get_node(nid) for nid in idx.node_ids) if n]

    def get_quasi_by_archetype(
        self,
        archetype: str,
        min_confidence: float = 0.0,
    ) -> List[DataNode]:
        """
        Primary quasicrystal retrieval surface.
        Returns quasicrystal nodes matching an archetype, sorted by confidence.
        """
        idx = self._arch_idx.get(archetype) or \
              self._backend.read_quasi_archetype_index(archetype)
        if not idx:
            return []

        nodes = []
        for qid in idx.quasi_ids:
            node = self.get_node(qid, "QUASI")
            if node:
                conf = float(node.payload.get("confidence", 0.0))
                if conf >= min_confidence:
                    nodes.append(node)

        nodes.sort(
            key=lambda n: float(n.payload.get("confidence", 0.0)),
            reverse=True,
        )
        return nodes

    def get_all_quasi_archetypes(self) -> List[str]:
        """Return all registered quasicrystal archetypes."""
        return self._backend.list_quasi_archetypes()

    def get_active_issue_family_node(
        self,
        issue_category: str,
        order: str,
    ) -> Optional[DataNode]:
        """Return the active version head for an issue family at a given order."""
        idx = self._issue_idx.get(issue_category) or \
              self._backend.read_issue_family_index(issue_category)
        if not idx:
            return None
        node_id = idx.active_ids.get(order, "")
        if not node_id:
            return None
        return self.get_node(node_id, order)

    def get_latest_issue_family_version(
        self,
        issue_category: str,
        order: str,
    ) -> int:
        """Return the highest recorded version number for an issue family stage."""
        idx = self._issue_idx.get(issue_category) or \
              self._backend.read_issue_family_index(issue_category)
        if not idx:
            return 0
        return int(idx.latest_versions.get(order, 0) or 0)

    def find_issue_family_node_by_signature(
        self,
        issue_category: str,
        order: str,
        signature: str,
    ) -> Optional[DataNode]:
        """Find an existing stage node with the same lineage signature."""
        matches = [
            node for node in self.retrieve_by_issue_family(issue_category, order=order)
            if str(node.lineage_meta.get("signature", "")) == signature
        ]
        if not matches:
            return None
        matches.sort(
            key=lambda node: (
                bool(node.lineage_meta.get("is_active_version", False)),
                int(node.lineage_meta.get("version", 0) or 0),
            ),
            reverse=True,
        )
        return matches[0]

    def hydrate_crystal(
        self,
        node_id: str,
        order: Optional[str] = None,
        is_relic: bool = False,
    ) -> Optional[CrystalInstance]:
        """
        Reconstruct a live CrystalInstance from a persisted DataNode.
        """
        node = self.get_node(node_id, order, is_relic=is_relic)
        if node is None:
            return None

        order_name = order or node.order
        crystal = CrystalInstance(
            crystal_id=node.node_id,
            order=CrystalOrder[order_name],
            facet_values=dict(node.payload),
            resolution_fidelity=node.resolution_fidelity,
            base_event_ids=list(node.base_event_ids),
            parent_ids=list(node.parent_ids),
            child_ids=list(node.child_ids),
            created_at=node.created_at,
            tags=list(node.tags),
            rotation_history=list(node.rotation_history),
            lineage_meta=dict(node.lineage_meta),
        )
        if node.quasi_strata:
            crystal.quasi_strata = QuasiInnerStrata(
                representative_base_events=list(
                    node.quasi_strata.get("representative_base_events", [])
                ),
                recurrence_summary=dict(
                    node.quasi_strata.get("recurrence_summary", {})
                ),
                strategy_success_stats=dict(
                    node.quasi_strata.get("strategy_success_stats", {})
                ),
                failure_counterexamples=list(
                    node.quasi_strata.get("failure_counterexamples", [])
                ),
                coherence_index=float(
                    node.quasi_strata.get("coherence_index", 0.0) or 0.0
                ),
                novelty_index=float(
                    node.quasi_strata.get("novelty_index", 0.0) or 0.0
                ),
                genealogy_depth=int(node.quasi_strata.get("genealogy_depth", 0) or 0),
                formation_timestamp=str(
                    node.quasi_strata.get("formation_timestamp", "")
                ),
            )

        engine = CrystalEngine()
        point_laws = engine.get_all_points(CrystalOrder[order_name])
        for point_name, score in node.point_scores.items():
            law = point_laws.get(point_name)
            if law is None:
                continue
            crystal.add_point(RelationalPoint(
                law=law,
                score=score,
                evidence="hydrated_from_persistence",
            ))
        return crystal

    def get_doctrine(self, quasi_id: str) -> Optional[DoctrineObject]:
        """Reconstruct an actionable doctrine object from a persisted quasicrystal."""
        node = self.get_node(quasi_id, "QUASI")
        if not node:
            return None
        strata = node.quasi_strata or {}
        lineage_meta = dict(node.lineage_meta)
        return DoctrineObject(
            quasi_id=node.node_id,
            family_key=str(lineage_meta.get("family_key", "")),
            lineage_version=int(lineage_meta.get("version", 0) or 0),
            is_active_version=bool(lineage_meta.get("is_active_version", False)),
            supersedes=str(lineage_meta.get("supersedes", "")),
            superseded_by=str(lineage_meta.get("superseded_by", "")),
            issue_archetype=str(node.payload.get("issue_archetype", "unknown")),
            primary_strategy=str(node.payload.get("primary_strategy", "unknown")),
            secondary_strategy=str(node.payload.get("secondary_strategy", "none")),
            applicability_boundary=str(node.payload.get("applicability_boundary", "")),
            confidence=float(node.payload.get("confidence", 0.0)),
            failure_indicators=_split_compound_field(
                str(node.payload.get("failure_indicators", ""))
            ),
            expected_effects=_split_compound_field(
                str(node.payload.get("expected_effects", ""))
            ),
            escalation_trigger=str(node.payload.get("escalation_trigger", "")),
            representative_base_events=list(
                strata.get("representative_base_events", [])
            ),
            recurrence_summary=dict(strata.get("recurrence_summary", {})),
            strategy_success_stats=dict(strata.get("strategy_success_stats", {})),
            failure_counterexamples=list(
                strata.get("failure_counterexamples", [])
            ),
            genealogy_depth=int(strata.get("genealogy_depth", 0) or 0),
            coherence_index=float(strata.get("coherence_index", 0.0) or 0.0),
            novelty_index=float(strata.get("novelty_index", 0.0) or 0.0),
            available_rotations=["issue_centric", "logic_tier", "strategy", "outcome"],
            rotation_history=list(node.rotation_history),
        )

    def get_doctrines_by_archetype(
        self,
        archetype: str,
        min_confidence: float = 0.0,
    ) -> List[DoctrineObject]:
        """Retrieve persisted doctrine objects by quasicrystal archetype."""
        return [
            doctrine
            for doctrine in (
                self.get_doctrine(node.node_id)
                for node in self.get_quasi_by_archetype(archetype, min_confidence)
            )
            if doctrine is not None
        ]

    # ── Lineage tracing ───────────────────────────────────────────────────────

    def get_ancestry(
        self,
        node_id: str,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Walk the lineage graph upward from a given node.
        Returns a list of dicts describing the ancestry chain:
          [{node_id, order, resolution_fidelity, parent_ids, created_at}, ...]
        """
        visited: Set[str]             = set()
        ancestry: List[Dict[str, Any]] = []
        queue = [node_id]

        for _ in range(max_depth):
            if not queue:
                break
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            node = self.get_node(current_id)
            if node:
                ancestry.append({
                    "node_id"            : node.node_id,
                    "order"              : node.order,
                    "resolution_fidelity": node.resolution_fidelity,
                    "parent_ids"         : node.parent_ids,
                    "created_at"         : node.created_at,
                    "is_relic"           : node.is_relic,
                    "tags"               : node.tags,
                })
                queue.extend(node.parent_ids)

        return ancestry

    def get_descendants(
        self,
        node_id: str,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """Walk the lineage graph downward from a given node."""
        visited: Set[str]             = set()
        descendants: List[Dict[str, Any]] = []
        queue = [node_id]

        for _ in range(max_depth):
            if not queue:
                break
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            node = self.get_node(current_id)
            if node:
                descendants.append({
                    "node_id"  : node.node_id,
                    "order"    : node.order,
                    "child_ids": node.child_ids,
                })
                queue.extend(node.child_ids)

        return descendants

    # ── Live save / load ──────────────────────────────────────────────────────

    def live_save(self) -> int:
        """Flush all in-memory state to disk.  Returns count of nodes written."""
        count = 0
        for node in self._cache.values():
            self._backend.write_node(node)
            count += 1
        for edge in self._edges.values():
            self._backend.write_edge(edge)
        for idx in self._issue_idx.values():
            self._backend.write_issue_family_index(idx)
        for idx in self._strat_idx.values():
            self._backend.write_strategy_index(idx)
        for idx in self._target_idx.values():
            self._backend.write_target_index(idx)
        for idx in self._tier_idx.values():
            self._backend.write_logic_tier_index(idx)
        for idx in self._arch_idx.values():
            self._backend.write_quasi_archetype_index(idx)
        return count

    def load_all(self, max_per_type: int = 10_000) -> Dict[str, int]:
        """
        Hydrate in-memory cache from disk.
        Returns counts of loaded objects per type.

        max_per_type: cap on how many nodes/edges to load per category.
        Prevents boot hangs when the state directory has grown to millions of files.
        Default 10_000 keeps boot fast while preserving recent history.
        Pass max_per_type=0 to disable the cap (original behaviour, risky on large state).
        """
        counts: Dict[str, int] = {
            "nodes": 0, "edges": 0, "indexes": 0,
        }

        def _cap(iterable: Iterator, limit: int) -> Iterator:
            """Yield at most `limit` items; 0 = unlimited."""
            if limit <= 0:
                yield from iterable
            else:
                yield from itertools.islice(iterable, limit)

        for order in ("BASE", "COMPOSITE", "HIGHER_ORDER", "QUASI"):
            for node in _cap(self._backend.iter_nodes(order), max_per_type):
                self._cache[node.node_id] = node
                counts["nodes"] += 1

        # Load edges — sort by mtime descending so we get the most recent ones
        # when the cap kicks in, rather than arbitrary filesystem order.
        edges_dir = self._backend.base_dir / "edges"
        try:
            edge_paths = sorted(
                edges_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            edge_paths = []
        for path in _cap(iter(edge_paths), max_per_type):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                edge = LineageEdge.from_dict(data)
                self._edges[edge.edge_id] = edge
                counts["edges"] += 1
            except Exception:
                pass

        # Load indexes (small number of files per type — no cap needed here)
        for issue_cat in self._backend.list_issue_families():
            idx = self._backend.read_issue_family_index(issue_cat)
            if idx:
                self._issue_idx[issue_cat] = idx
                counts["indexes"] += 1

        for strategy in self._backend.list_strategies():
            idx = self._backend.read_strategy_index(strategy)
            if idx:
                self._strat_idx[strategy] = idx
                counts["indexes"] += 1

        for target in self._backend.list_targets():
            idx = self._backend.read_target_index(target)
            if idx:
                self._target_idx[target] = idx
                counts["indexes"] += 1

        for tier in self._backend.list_logic_tiers():
            idx = self._backend.read_logic_tier_index(tier)
            if idx:
                self._tier_idx[tier] = idx
                counts["indexes"] += 1

        for archetype in self._backend.list_quasi_archetypes():
            idx = self._backend.read_quasi_archetype_index(archetype)
            if idx:
                self._arch_idx[archetype] = idx
                counts["indexes"] += 1

        return counts

    # ── Index management ──────────────────────────────────────────────────────

    def _update_indexes(self, node: DataNode) -> None:
        """Update all retrieval indexes from a freshly written DataNode."""
        issue_categories = self._extract_issue_categories(node)
        target_ids = self._extract_target_ids(node)
        tiers = self._extract_logic_tiers(node)

        # Issue family index
        for issue_cat in issue_categories:
            if issue_cat not in self._issue_idx:
                self._issue_idx[issue_cat] = IssueFamilyIndex(issue_category=issue_cat)
            idx = self._issue_idx[issue_cat]
            order = node.order
            if order == "BASE" and node.node_id not in idx.base_ids:
                idx.base_ids.append(node.node_id)
            elif order == "COMPOSITE" and node.node_id not in idx.composite_ids:
                idx.composite_ids.append(node.node_id)
            elif order == "HIGHER_ORDER" and node.node_id not in idx.higher_ids:
                idx.higher_ids.append(node.node_id)
            elif order == "QUASI" and node.node_id not in idx.quasi_ids:
                idx.quasi_ids.append(node.node_id)
            version = int(node.lineage_meta.get("version", 0) or 0)
            if version > 0:
                idx.latest_versions[order] = max(
                    int(idx.latest_versions.get(order, 0) or 0),
                    version,
                )
            if (
                not node.is_relic
                and node.lineage_meta.get("is_active_version", True)
                and order in ("COMPOSITE", "HIGHER_ORDER", "QUASI")
            ):
                idx.active_ids[order] = node.node_id
            self._backend.write_issue_family_index(idx)

        # Target index
        if not node.is_relic:
            for target_id in target_ids:
                if target_id not in self._target_idx:
                    self._target_idx[target_id] = TargetIndex(target_id=target_id)
                tidx = self._target_idx[target_id]
                if node.node_id not in tidx.node_ids:
                    tidx.node_ids.append(node.node_id)
                for issue_cat in issue_categories:
                    if issue_cat not in tidx.issue_categories:
                        tidx.issue_categories.append(issue_cat)
                self._backend.write_target_index(tidx)

        # Logic tier index
        if not node.is_relic:
            for tier in tiers:
                if tier not in self._tier_idx:
                    self._tier_idx[tier] = LogicTierIndex(logic_tier=tier)
                lti = self._tier_idx[tier]
                if node.node_id not in lti.node_ids:
                    lti.node_ids.append(node.node_id)
                self._backend.write_logic_tier_index(lti)

        # Strategy index (higher-order and quasi only)
        if node.order in ("HIGHER_ORDER", "QUASI"):
            strategies = self._extract_strategy_keys(node)
            for sc in strategies:
                if sc not in self._strat_idx:
                    self._strat_idx[sc] = StrategyIndex(strategy_class=sc)
                si = self._strat_idx[sc]
                if node.order == "HIGHER_ORDER" and node.node_id not in si.higher_ids:
                    si.higher_ids.append(node.node_id)
                if node.order == "QUASI" and node.node_id not in si.quasi_ids:
                    si.quasi_ids.append(node.node_id)
                conf_vals = [
                    float(self._cache[qid].payload.get("confidence", 0.0))
                    for qid in si.quasi_ids
                    if qid in self._cache
                ]
                si.avg_confidence = sum(conf_vals) / len(conf_vals) if conf_vals else 0.0
                self._backend.write_strategy_index(si)

        # Quasi archetype index
        if node.order == "QUASI":
            archetype = str(node.payload.get("issue_archetype", ""))
            conf      = float(node.payload.get("confidence", 0.0))
            if archetype:
                if archetype not in self._arch_idx:
                    self._arch_idx[archetype] = QuasiArchetypeIndex(archetype=archetype)
                ai = self._arch_idx[archetype]
                if node.node_id not in ai.quasi_ids:
                    ai.quasi_ids.append(node.node_id)
                ai.max_confidence = max(ai.max_confidence, conf)
                self._backend.write_quasi_archetype_index(ai)

        self._backend.append_journal(JournalEntry(
            operation="update_index",
            node_id=node.node_id,
            order=node.order,
            detail=(
                f"issues={issue_categories[:3]}  "
                f"targets={target_ids[:3]}  tiers={tiers[:3]}"
            ),
        ))

    def _extract_issue_categories(self, node: DataNode) -> List[str]:
        direct_issue = str(node.payload.get("issue", "")).strip()
        if direct_issue:
            return [direct_issue]
        strata_events = (node.quasi_strata or {}).get("representative_base_events", [])
        issues = [
            str(event.get("issue", "")).strip()
            for event in strata_events
            if event.get("issue")
        ]
        return _unique_preserve_order(issues)

    def _extract_target_ids(self, node: DataNode) -> List[str]:
        direct_target = str(node.payload.get("target", "")).strip()
        if direct_target:
            return [direct_target]
        strata_events = (node.quasi_strata or {}).get("representative_base_events", [])
        targets = [
            str(event.get("target", "")).strip()
            for event in strata_events
            if event.get("target")
        ]
        return _unique_preserve_order(targets)

    def _extract_logic_tiers(self, node: DataNode) -> List[str]:
        direct_tier = str(node.payload.get("logic_tier", "")).strip()
        if direct_tier:
            return [direct_tier]
        strata_events = (node.quasi_strata or {}).get("representative_base_events", [])
        tiers = [
            str(event.get("logic_tier", "")).strip()
            for event in strata_events
            if event.get("logic_tier")
        ]
        return _unique_preserve_order(tiers)

    def _extract_strategy_keys(self, node: DataNode) -> List[str]:
        if node.order == "HIGHER_ORDER":
            strategy_class = str(node.payload.get("strategy_class", "")).strip()
            return [strategy_class] if strategy_class else []
        strategies = [
            str(node.payload.get("primary_strategy", "")).strip(),
            str(node.payload.get("secondary_strategy", "")).strip(),
        ]
        return _unique_preserve_order(
            [strategy for strategy in strategies if strategy and strategy.lower() != "none"]
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return counts and summary statistics across the store."""
        base_nodes    = self._backend.list_nodes("BASE")
        comp_nodes    = self._backend.list_nodes("COMPOSITE")
        higher_nodes  = self._backend.list_nodes("HIGHER_ORDER")
        quasi_nodes   = self._backend.list_nodes("QUASI")
        relic_nodes   = self._backend.list_nodes("", relics=True)
        edges         = self._backend.list_edges()
        issue_families= self._backend.list_issue_families()
        strategies    = self._backend.list_strategies()
        archetypes    = self._backend.list_quasi_archetypes()

        return {
            "node_counts" : {
                "base"        : len(base_nodes),
                "composite"   : len(comp_nodes),
                "higher_order": len(higher_nodes),
                "quasi"       : len(quasi_nodes),
                "relics"      : len(relic_nodes),
            },
            "edge_count"        : len(edges),
            "issue_families"    : issue_families,
            "strategy_classes"  : strategies,
            "quasi_archetypes"  : archetypes,
            "cache_size"        : len(self._cache),
        }

    # ── Journal access ────────────────────────────────────────────────────────

    def get_journal(self, tail: int = 50) -> List[Dict[str, Any]]:
        return self._backend.read_journal(tail)

    def get_journal_for_node(self, node_id: str) -> List[Dict[str, Any]]:
        return self._backend.read_journal_for_node(node_id)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATED MEMORY PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class IntegratedMemoryPipeline:
    """
    Combines CrystalLifecycle (dimensional_processing) with DimensionalMemory.

    This is the full stack: ingest → form → promote → collapse → persist.
    The memory layer sees every crystal the lifecycle produces and persists it
    immediately, registering lineage edges at each transition.
    """

    def __init__(self, storage_dir: str = "./crystal_memory") -> None:
        from .dimensional_processing import CrystalLifecycle
        self.lifecycle = CrystalLifecycle()
        self.memory    = DimensionalMemory(storage_dir)
        self.ghost_relics = GhostRelicSystem(
            storage_path=os.path.join(storage_dir, "ghost_relics.json")
        )

    def _family_key(self, issue_category: str) -> str:
        normalized = "".join(
            ch.lower() if ch.isalnum() else "_"
            for ch in str(issue_category or "unknown")
        ).strip("_")
        return f"issue_family::{normalized or 'unknown'}"

    def _build_anchor_refs(
        self,
        crystal: CrystalInstance,
        issue_category: str,
    ) -> List[str]:
        refs: List[str] = [
            f"family:{self._family_key(issue_category)}",
            f"stage:{crystal.order.name.lower()}",
        ]
        for field_name in (
            "issue",
            "target",
            "logic_tier",
            "intervention",
            "recurrence_pattern",
            "distribution_context",
            "strategy_class",
            "issue_archetype",
            "primary_strategy",
            "secondary_strategy",
        ):
            value = str(crystal.get_facet(field_name) or "").strip()
            if not value or value.lower() in {"none", "unknown", "unknown_issue", "unknown_strategy"}:
                continue
            refs.append(f"{field_name}:{value}")
        for tag in list(crystal.tags or [])[:8]:
            refs.append(f"tag:{tag}")
        return _unique_preserve_order(refs)

    def _capture_ghost_relic(
        self,
        crystal: Optional[CrystalInstance],
        issue_category: str,
        reason: str,
    ) -> None:
        if crystal is None:
            return
        try:
            refs = self._build_anchor_refs(crystal, issue_category)
            self.ghost_relics.create_relic(crystal, anchor_refs=refs, reason=reason)
        except Exception:
            return

    def _maybe_apply_ghost_relic(
        self,
        crystal: CrystalInstance,
        issue_category: str,
    ) -> None:
        refs = self._build_anchor_refs(crystal, issue_category)
        relic, match_score = self.ghost_relics.find_best_relic(
            refs,
            original_order=crystal.order.name,
        )
        if relic is None:
            return
        try:
            self.ghost_relics.apply_relic(relic, crystal, match_score=match_score)
        except Exception:
            return

    def get_ghost_relic_stats(self) -> Dict[str, Any]:
        return self.ghost_relics.stats()

    def _register_live_crystal(self, crystal: CrystalInstance) -> None:
        if crystal.order == CrystalOrder.COMPOSITE:
            self.lifecycle._composites[crystal.crystal_id] = crystal
        elif crystal.order == CrystalOrder.HIGHER_ORDER:
            self.lifecycle._higher_orders[crystal.crystal_id] = crystal
        elif crystal.order == CrystalOrder.QUASI:
            self.lifecycle._quasicrystals[crystal.crystal_id] = crystal

    def _build_stage_signature(self, crystal: CrystalInstance) -> str:
        import hashlib

        fields_by_order = {
            CrystalOrder.COMPOSITE: (
                "issue",
                "logic_tier",
                "intervention",
                "recurrence_pattern",
                "distribution_context",
            ),
            CrystalOrder.HIGHER_ORDER: (
                "issue",
                "logic_tier",
                "intervention",
                "recurrence_pattern",
                "distribution_context",
                "strategy_class",
                "strategy_outcome_profile",
                "failure_modes",
                "applicability_conditions",
            ),
            CrystalOrder.QUASI: (
                "issue_archetype",
                "primary_strategy",
                "secondary_strategy",
                "applicability_boundary",
                "confidence",
                "failure_indicators",
                "expected_effects",
                "escalation_trigger",
            ),
        }
        relevant_fields = fields_by_order.get(crystal.order, tuple())
        payload = {
            "order": crystal.order.name,
            "base_event_ids": sorted(str(base_id) for base_id in crystal.base_event_ids),
            "facets": {
                field_name: crystal.get_facet(field_name)
                for field_name in relevant_fields
            },
        }
        if crystal.order == CrystalOrder.QUASI and crystal.quasi_strata is not None:
            payload["quasi_strata"] = {
                "recurrence_summary": dict(crystal.quasi_strata.recurrence_summary),
                "strategy_success_stats": dict(crystal.quasi_strata.strategy_success_stats),
                "failure_counterexamples": list(crystal.quasi_strata.failure_counterexamples),
                "coherence_index": crystal.quasi_strata.coherence_index,
                "novelty_index": crystal.quasi_strata.novelty_index,
                "genealogy_depth": crystal.quasi_strata.genealogy_depth,
            }
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def _stamp_lineage_meta(
        self,
        crystal: CrystalInstance,
        issue_category: str,
        version: int,
        signature: str,
        supersedes_node_id: str = "",
    ) -> None:
        lineage_meta = dict(crystal.lineage_meta or {})
        lineage_meta.update({
            "family_key": self._family_key(issue_category),
            "issue_category": issue_category,
            "stage": crystal.order.name,
            "version": version,
            "signature": signature,
            "is_active_version": True,
            "supersedes": supersedes_node_id,
            "superseded_by": "",
        })
        crystal.lineage_meta = lineage_meta

    def _persist_versioned_stage(
        self,
        crystal: CrystalInstance,
        issue_category: str,
    ) -> Tuple[DataNode, str]:
        self._maybe_apply_ghost_relic(crystal, issue_category)
        stage = crystal.order.name
        signature = self._build_stage_signature(crystal)
        existing = self.memory.find_issue_family_node_by_signature(
            issue_category,
            stage,
            signature,
        )
        if existing is not None:
            hydrated = self.memory.hydrate_crystal(existing.node_id, existing.order)
            if hydrated is not None:
                self._register_live_crystal(hydrated)
            return existing, "reused"

        prior_active = self.memory.get_active_issue_family_node(issue_category, stage)
        next_version = self.memory.get_latest_issue_family_version(issue_category, stage) + 1
        self._stamp_lineage_meta(
            crystal,
            issue_category=issue_category,
            version=next_version,
            signature=signature,
            supersedes_node_id=prior_active.node_id if prior_active else "",
        )
        self._register_live_crystal(crystal)
        node = self.memory.persist(crystal)

        if prior_active and prior_active.node_id != node.node_id:
            prior_crystal = self.memory.hydrate_crystal(prior_active.node_id, prior_active.order)
            self._capture_ghost_relic(
                prior_crystal,
                issue_category=issue_category,
                reason=f"superseded_{stage.lower()}",
            )
            self.memory.update_node_lineage_meta(
                prior_active.node_id,
                prior_active.order,
                {
                    "is_active_version": False,
                    "superseded_by": node.node_id,
                },
            )
            self.memory.register_lineage_edge_ids(
                prior_active.node_id,
                prior_active.order,
                node.node_id,
                node.order,
                "version_update",
            )
        return node, "created"

    def ingest_and_persist(
        self,
        event: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Optional[DataNode]:
        """Ingest a diagnostic event, form a base crystal, and persist it."""
        crystal, messages = self.lifecycle.ingest_event(event, tags)
        if crystal is None:
            return None
        issue_category = str(event.get("issue", "unknown"))
        event_context: Dict[str, Any] = {}
        for key in ("constraint_context", "system_pressure", "genealogy_refs"):
            value = event.get(key)
            if value:
                event_context[key] = value
        crystal.lineage_meta = {
            "family_key": self._family_key(issue_category),
            "issue_category": issue_category,
            "stage": crystal.order.name,
            "event_signature": self._build_stage_signature(crystal),
            "is_active_version": True,
        }
        if event_context:
            crystal.lineage_meta["event_context"] = event_context
            genealogy_refs = list(event_context.get("genealogy_refs", []) or [])
            ability_tags = []
            for ref in genealogy_refs:
                if not isinstance(ref, dict):
                    continue
                ability_id = str(ref.get("ability_id", "") or "").strip()
                mutation_id = str(ref.get("mutation_id", "") or "").strip()
                seed_lineage_id = str(ref.get("seed_lineage_id", "") or "").strip()
                if ability_id:
                    ability_tags.append(f"ability_id:{ability_id}")
                if mutation_id:
                    ability_tags.append(f"mutation_id:{mutation_id}")
                if seed_lineage_id:
                    ability_tags.append(f"seed_lineage_id:{seed_lineage_id}")
            if ability_tags:
                crystal.tags = _unique_preserve_order(list(crystal.tags) + ability_tags)
        node = self.memory.persist(crystal)
        return node

    def observe_intervention_event(
        self,
        event: Dict[str, Any],
        tags: Optional[List[str]] = None,
        auto_advance: bool = False,
        rotate_doctrine: bool = True,
    ) -> Dict[str, Any]:
        """
        Record one intervention event and optionally advance its issue family.

        This is the observer-facing entrypoint: record first, then decide
        whether to promote the accumulated family into pattern/strategy/doctrine.
        """
        base_node = self.ingest_and_persist(event, tags)
        summary: Dict[str, Any] = {
            "base_node": base_node,
            "issue_category": str(event.get("issue", "")),
            "advance_summary": None,
        }
        if auto_advance and summary["issue_category"]:
            summary["advance_summary"] = self.advance_issue_family(
                summary["issue_category"],
                rotate_doctrine=rotate_doctrine,
            )
        return summary

    def promote_and_persist_composite(
        self,
        issue_category: str,
    ) -> Tuple[Optional[DataNode], str]:
        """Attempt composite formation and persist if successful."""
        comp, eval_result = self.lifecycle.attempt_composite_formation(issue_category)
        if comp is None:
            return None, "not_formed"
        node, status = self._persist_versioned_stage(comp, issue_category)
        if status == "created":
            for base_crystal in self.lifecycle.get_all_base_crystals():
                if comp.crystal_id in base_crystal.child_ids:
                    self.memory.register_lineage_edge(base_crystal, comp, "promotion")
        return node, status

    def promote_and_persist_higher(
        self,
        composite_id: str,
        issue_category: str,
    ) -> Tuple[Optional[DataNode], str]:
        """Attempt higher-order formation and persist if successful."""
        higher, eval_result = self.lifecycle.attempt_higher_order_formation(composite_id)
        if higher is None:
            return None, "not_formed"
        node, status = self._persist_versioned_stage(higher, issue_category)
        comp = self.lifecycle.get_composite(composite_id)
        if comp and status == "created":
            self.memory.register_lineage_edge(comp, higher, "promotion")
        return node, status

    def collapse_and_persist_quasi(
        self,
        higher_id: str,
        issue_category: str,
        relic_higher: bool = True,
    ) -> Tuple[Optional[DataNode], str]:
        """
        Attempt quasicrystal collapse, persist the quasi, and optionally
        archive the higher-order crystal as a relic.
        """
        quasi, eval_result = self.lifecycle.attempt_quasi_collapse(higher_id)
        if quasi is None:
            return None, "not_formed"
        node, status = self._persist_versioned_stage(quasi, issue_category)
        higher = self.lifecycle.get_higher_order(higher_id)
        if higher and status == "created":
            self.memory.register_lineage_edge(higher, quasi, "collapse")
            if relic_higher:
                self.memory.relic(higher)
                self._capture_ghost_relic(
                    higher,
                    issue_category=issue_category,
                    reason="quasi_collapse",
                )
        return node, status

    def rotate_and_record(
        self,
        quasi_id: str,
        rotation_name: str,
    ) -> Optional[RotationResult]:
        """Apply rotation and record the result in the quasi node's payload."""
        result = self.lifecycle.rotate_quasi(quasi_id, rotation_name)
        if result is None:
            return None
        quasi = self.lifecycle.get_quasi(quasi_id)
        if quasi:
            self.memory.update_node_payload(
                quasi_id, "QUASI",
                {
                    "last_rotation"      : rotation_name,
                    "rotation_hypotheses": result.hypotheses,
                }
        )
        return result

    def advance_issue_family(
        self,
        issue_category: str,
        rotate_doctrine: bool = True,
        relic_higher: bool = True,
    ) -> Dict[str, Any]:
        """
        Advance one issue family through pattern, strategy, and doctrine stages.
        """
        summary: Dict[str, Any] = {
            "issue_category": issue_category,
            "composite_node": None,
            "composite_status": "not_attempted",
            "higher_node": None,
            "higher_status": "not_attempted",
            "quasi_node": None,
            "quasi_status": "not_attempted",
            "doctrine": None,
            "rotations": [],
        }

        comp_node, comp_status = self.promote_and_persist_composite(issue_category)
        summary["composite_status"] = comp_status
        if not comp_node:
            return summary
        summary["composite_node"] = comp_node

        higher_node, higher_status = self.promote_and_persist_higher(
            comp_node.node_id,
            issue_category=issue_category,
        )
        summary["higher_status"] = higher_status
        if not higher_node:
            return summary
        summary["higher_node"] = higher_node

        quasi_node, quasi_status = self.collapse_and_persist_quasi(
            higher_node.node_id,
            issue_category=issue_category,
            relic_higher=relic_higher,
        )
        summary["quasi_status"] = quasi_status
        if not quasi_node:
            return summary
        summary["quasi_node"] = quasi_node
        summary["doctrine"] = self.get_actionable_doctrine(quasi_node.node_id)

        if rotate_doctrine:
            for rotation_name in ("issue_centric", "logic_tier", "strategy", "outcome"):
                rotation = self.rotate_and_record(quasi_node.node_id, rotation_name)
                if rotation:
                    summary["rotations"].append(rotation)
        return summary

    def get_actionable_doctrine(self, quasi_id: str) -> Optional[DoctrineObject]:
        """Return the doctrine surface for a persisted or live quasicrystal."""
        doctrine = self.memory.get_doctrine(quasi_id)
        if doctrine is not None:
            return doctrine
        return self.lifecycle.build_doctrine(quasi_id)

    def get_doctrine_candidates_for_event(
        self,
        new_event: Dict[str, Any],
        min_confidence: float = 0.5,
    ) -> List[DoctrineObject]:
        """Retrieve doctrine objects relevant to a new diagnostic event."""
        doctrines: List[DoctrineObject] = []
        for node in self.retrieve_quasi_for_event(new_event, min_confidence=min_confidence):
            doctrine = self.get_actionable_doctrine(node.node_id)
            if doctrine is not None:
                doctrines.append(doctrine)
        doctrines.sort(key=lambda doctrine: doctrine.confidence, reverse=True)
        return doctrines

    def retrieve_quasi_for_event(
        self,
        new_event: Dict[str, Any],
        min_confidence: float = 0.5,
    ) -> List[DataNode]:
        """
        Retrieve quasicrystals relevant to a new diagnostic event.
        Uses archetype matching with confidence filtering.
        """
        from .dimensional_processing import (
            StrategyHypothesisGenerator,
        )
        from .crystal_engine import CrystalOrder as CO
        issue = str(new_event.get("issue", "")).lower()

        # Map issue to potential archetypes
        archetype_candidates = []
        archetype_keywords = {
            "attribute_contract_violation": ["attribute", "mismatch", "rename"],
            "label_registry_gap"          : ["label", "registry", "variant"],
            "pipeline_shard_dropout"      : ["shard", "ingestion", "dropout"],
            "persistence_boundary_failure": ["persist", "stats", "save"],
            "module_provision_gap"        : ["module", "missing", "boot"],
            "constraint_physics_violation": ["constraint", "pressure", "outlet"],
            "context_thread_break"        : ["context", "followup", "carryover", "callback", "thread"],
            "grounding_repair_gap"        : ["ground", "lookup", "meaning", "anchor", "clarify"],
            "uncertainty_signal_gap"      : ["uncertainty", "hedge", "guess"],
            "repair_path_breakdown"       : ["repair", "contradiction", "resolve", "fix"],
        }
        for arch, keywords in archetype_keywords.items():
            if any(kw in issue for kw in keywords):
                archetype_candidates.append(arch)

        if not archetype_candidates:
            archetype_candidates = self.memory.get_all_quasi_archetypes()

        result = []
        for arch in archetype_candidates:
            nodes = self.memory.get_quasi_by_archetype(arch, min_confidence)
            result.extend(nodes)

        return result

    def full_pipeline_demo(
        self,
        events: List[Dict[str, Any]],
        issue_category: str,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline on a list of events.
        Returns a summary of what was formed and persisted.
        """
        summary: Dict[str, Any] = {
            "base_count"   : 0,
            "composite_id" : None,
            "composite_status": "not_attempted",
            "higher_id"    : None,
            "higher_status": "not_attempted",
            "quasi_id"     : None,
            "quasi_status": "not_attempted",
            "rotations"    : [],
            "journal_tail" : [],
        }

        # Ingest events
        for ev in events:
            node = self.ingest_and_persist(ev)
            if node:
                summary["base_count"] += 1

        # Promote composite
        comp_node, comp_status = self.promote_and_persist_composite(issue_category)
        summary["composite_status"] = comp_status
        if comp_node:
            summary["composite_id"] = comp_node.node_id
            # Promote higher
            higher_node, higher_status = self.promote_and_persist_higher(
                comp_node.node_id,
                issue_category=issue_category,
            )
            summary["higher_status"] = higher_status
            if higher_node:
                summary["higher_id"] = higher_node.node_id
                # Collapse quasi
                quasi_node, quasi_status = self.collapse_and_persist_quasi(
                    higher_node.node_id,
                    issue_category=issue_category,
                )
                summary["quasi_status"] = quasi_status
                if quasi_node:
                    summary["quasi_id"] = quasi_node.node_id
                    # Rotate all perspectives
                    from .crystal_engine import ALL_ROTATIONS
                    for rname in ALL_ROTATIONS:
                        rot = self.rotate_and_record(quasi_node.node_id, rname)
                        if rot:
                            summary["rotations"].append({
                                "name"     : rname,
                                "hypotheses": rot.hypotheses,
                            })

        summary["journal_tail"] = self.memory.get_journal(tail=10)
        summary["store_stats"]  = self.memory.stats()
        return summary


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — integrated pipeline demo
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile
    import shutil

    print("Dimensional Memory — Integrated Pipeline Demo")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp(prefix="crystal_memory_demo_")
    print(f"Storage directory: {tmpdir}")

    pipeline = IntegratedMemoryPipeline(storage_dir=tmpdir)

    events = [
        {
            "target"         : f"aurora_runtime.ability_registry.slot_{i}",
            "issue"          : "outlet_push_fraction_permanently_zero",
            "logic_tier"     : "constraint_physics",
            "intervention"   : "add_label_to_variant_map",
            "intended_effect": "ensure_label_resolves_to_ability_variant",
            "observed_effect": effect,
        }
        for i, effect in enumerate([
            "resolved_fully", "resolved_fully", "resolved_fully",
            "resolved_partially", "resolved_fully", "resolved_fully",
            "resolved_fully", "no_change_observed", "resolved_fully",
            "resolved_fully",
        ])
    ]

    summary = pipeline.full_pipeline_demo(
        events,
        issue_category="outlet_push_fraction_permanently_zero",
    )

    print(f"\nBase events formed   : {summary['base_count']}")
    print(f"Composite ID         : {(summary['composite_id'] or 'not formed')[:12]}…")
    print(f"Higher-order ID      : {(summary['higher_id'] or 'not formed')[:12]}…")
    print(f"Quasicrystal ID      : {(summary['quasi_id'] or 'not formed')[:12]}…")

    print("\nStore statistics:")
    for k, v in summary["store_stats"].items():
        print(f"  {k}: {v}")

    print("\nRotation results:")
    for rot in summary["rotations"]:
        print(f"  [{rot['name']}] {len(rot['hypotheses'])} hypotheses")

    print("\nJournal tail (last 10):")
    for entry in summary["journal_tail"]:
        print(f"  [{entry['timestamp'][:19]}] {entry['operation']:16s}  {entry['detail'][:60]}")

    # ── Demonstrate retrieval surfaces ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Retrieval surface demonstration:")

    mem = pipeline.memory

    print(f"\n  retrieve_by_issue_family('outlet_push_fraction_permanently_zero'):")
    nodes = mem.retrieve_by_issue_family("outlet_push_fraction_permanently_zero")
    for n in nodes:
        print(f"    [{n.order}] {n.node_id[:12]}…  fidelity={n.resolution_fidelity:.2f}")

    print(f"\n  retrieve_by_logic_tier('constraint_physics'):")
    nodes = mem.retrieve_by_logic_tier("constraint_physics")
    for n in nodes:
        print(f"    [{n.order}] {n.node_id[:12]}…")

    print(f"\n  retrieve_by_strategy_class('label_registry_repair'):")
    nodes = mem.retrieve_by_strategy_class("label_registry_repair")
    for n in nodes:
        print(f"    [{n.order}] {n.node_id[:12]}…")

    print(f"\n  get_quasi_by_archetype('constraint_physics_violation', min_confidence=0.4):")
    nodes = mem.get_quasi_by_archetype("constraint_physics_violation", min_confidence=0.4)
    for n in nodes:
        print(f"    [QUASI] {n.node_id[:12]}…  confidence={n.payload.get('confidence')}")
        doctrine = mem.get_doctrine(n.node_id)
        if doctrine:
            print(f"      doctrine.primary_strategy={doctrine.primary_strategy}")
            print(f"      doctrine.failure_indicators={doctrine.failure_indicators}")

    # ── Ancestry trace ────────────────────────────────────────────────────────
    if summary["quasi_id"]:
        print(f"\n  Ancestry for quasi {summary['quasi_id'][:12]}…:")
        ancestry = mem.get_ancestry(summary["quasi_id"])
        for a in ancestry:
            print(f"    [{a['order']}] {a['node_id'][:12]}…  "
                  f"fidelity={a['resolution_fidelity']:.2f}  "
                  f"relic={a['is_relic']}")

    # ── New event retrieval ───────────────────────────────────────────────────
    print(f"\n  Retrieve quasi for new event {{issue: 'outlet_pressure_path_stuck_zero'}}:")
    new_ev = {"issue": "outlet_pressure_path_stuck_zero", "logic_tier": "constraint_physics"}
    matches = pipeline.retrieve_quasi_for_event(new_ev, min_confidence=0.3)
    for n in matches:
        print(f"    {n.node_id[:12]}…  archetype={n.payload.get('issue_archetype')}  "
              f"conf={n.payload.get('confidence')}")
    print(f"\n  Doctrine candidates for new event:")
    for doctrine in pipeline.get_doctrine_candidates_for_event(new_ev, min_confidence=0.3):
        print(f"    [DOCTRINE] {doctrine.quasi_id[:12]}…  primary={doctrine.primary_strategy}  "
              f"conf={doctrine.confidence:.2f}")

    # ── Live save ─────────────────────────────────────────────────────────────
    saved = mem.live_save()
    print(f"\n  live_save(): {saved} nodes flushed to disk")

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"\nDemo storage cleaned up.  Pipeline complete.")
