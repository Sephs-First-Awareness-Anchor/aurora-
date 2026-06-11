#!/usr/bin/env python3
"""Persistence and retrieval layer for interaction quasicrystals."""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from aurora_interaction_engine import InteractionEngine
from aurora_persistence_utils import atomic_write_json, checksum_dict


@dataclass
class InteractionNode:
    node_id: str
    order: str
    payload: Dict[str, Any]
    point_scores: Dict[str, float]
    resolution_fidelity: float
    base_event_ids: List[str]
    parent_ids: List[str]
    child_ids: List[str]
    tags: List[str]
    quasi_inner_strata: Optional[Dict[str, Any]]
    lineage_meta: Dict[str, Any]
    execution_surface: Dict[str, Any]
    created_at: str
    persisted_at: float
    is_relic: bool
    checksum: str

    @classmethod
    def from_crystal(cls, crystal: Any, is_relic: bool = False) -> "InteractionNode":
        strata = getattr(crystal, "quasi_strata", None)
        if hasattr(strata, "to_dict"):
            strata_payload = strata.to_dict()
        elif isinstance(strata, dict):
            strata_payload = dict(strata)
        else:
            strata_payload = None
        payload = dict(getattr(crystal, "facet_values", {}) or {})
        return cls(
            node_id=str(getattr(crystal, "crystal_id")),
            order=str(getattr(getattr(crystal, "order", None), "name", getattr(crystal, "order", "BASE"))),
            payload=payload,
            point_scores={
                name: float(getattr(point, "score", 0.0) or 0.0)
                for name, point in (getattr(crystal, "relational_points", {}) or {}).items()
            },
            resolution_fidelity=float(getattr(crystal, "resolution_fidelity", 0.0) or 0.0),
            base_event_ids=list(getattr(crystal, "base_event_ids", []) or []),
            parent_ids=list(getattr(crystal, "parent_ids", []) or []),
            child_ids=list(getattr(crystal, "child_ids", []) or []),
            tags=list(getattr(crystal, "tags", []) or []),
            quasi_inner_strata=strata_payload,
            lineage_meta=dict(getattr(crystal, "lineage_meta", {}) or {}),
            execution_surface=dict(getattr(crystal, "execution_surface", {}) or {}),
            created_at=str(getattr(crystal, "created_at", "")),
            persisted_at=time.time(),
            is_relic=bool(is_relic),
            checksum=checksum_dict(payload),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "order": self.order,
            "payload": self.payload,
            "point_scores": self.point_scores,
            "resolution_fidelity": self.resolution_fidelity,
            "base_event_ids": self.base_event_ids,
            "parent_ids": self.parent_ids,
            "child_ids": self.child_ids,
            "tags": self.tags,
            "quasi_inner_strata": self.quasi_inner_strata,
            "lineage_meta": self.lineage_meta,
            "execution_surface": self.execution_surface,
            "created_at": self.created_at,
            "persisted_at": self.persisted_at,
            "is_relic": self.is_relic,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InteractionNode":
        return cls(
            node_id=str(data.get("node_id") or ""),
            order=str(data.get("order") or "BASE"),
            payload=dict(data.get("payload") or {}),
            point_scores={k: float(v or 0.0) for k, v in dict(data.get("point_scores") or {}).items()},
            resolution_fidelity=float(data.get("resolution_fidelity") or 0.0),
            base_event_ids=list(data.get("base_event_ids") or []),
            parent_ids=list(data.get("parent_ids") or []),
            child_ids=list(data.get("child_ids") or []),
            tags=list(data.get("tags") or []),
            quasi_inner_strata=dict(data.get("quasi_inner_strata") or {}) or None,
            lineage_meta=dict(data.get("lineage_meta") or {}),
            execution_surface=dict(data.get("execution_surface") or {}),
            created_at=str(data.get("created_at") or ""),
            persisted_at=float(data.get("persisted_at") or 0.0),
            is_relic=bool(data.get("is_relic")),
            checksum=str(data.get("checksum") or ""),
        )


@dataclass
class InteractionLineageEdge:
    parent_id: str
    parent_order: str
    child_id: str
    child_order: str
    transition_type: str
    created_at: float = field(default_factory=time.time)
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "parent_id": self.parent_id,
            "parent_order": self.parent_order,
            "child_id": self.child_id,
            "child_order": self.child_order,
            "transition_type": self.transition_type,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InteractionLineageEdge":
        return cls(
            parent_id=str(data.get("parent_id") or ""),
            parent_order=str(data.get("parent_order") or "BASE"),
            child_id=str(data.get("child_id") or ""),
            child_order=str(data.get("child_order") or "BASE"),
            transition_type=str(data.get("transition_type") or "promotion"),
            created_at=float(data.get("created_at") or time.time()),
            edge_id=str(data.get("edge_id") or str(uuid.uuid4())),
        )


class InteractionMemory:
    """Persistence substrate for interaction crystal nodes and quasi retrieval."""

    def __init__(self, storage_dir: str = "./aurora_state/interaction_memory", engine: Optional[InteractionEngine] = None) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine or InteractionEngine()
        self.nodes_path = self.storage_dir / "nodes.json"
        self.edges_path = self.storage_dir / "edges.json"
        self.indexes_path = self.storage_dir / "indexes.json"
        self.journal_path = self.storage_dir / "journal.jsonl"
        self._nodes: Dict[str, InteractionNode] = {}
        self._edges: Dict[str, InteractionLineageEdge] = {}
        self._indexes: Dict[str, Dict[str, List[str]]] = {
            "interpretive_issue": {},
            "response_strategy": {},
            "input_signature": {},
            "processing_tier": {},
            "interaction_archetype": {},
        }
        self._load()

    def persist(self, crystal: Any, *, is_relic: bool = False) -> InteractionNode:
        node = InteractionNode.from_crystal(crystal, is_relic=is_relic)
        self._nodes[node.node_id] = node
        if not is_relic:
            self._update_indexes(node)
        self._save()
        self._append_journal({
            "timestamp": time.time(),
            "operation": "write_relic" if is_relic else "write_node",
            "node_id": node.node_id,
            "order": node.order,
            "detail": node.payload.get("interaction_archetype") or node.payload.get("interpretive_issue") or "",
        })
        return node

    def relic(self, crystal: Any) -> InteractionNode:
        return self.persist(crystal, is_relic=True)

    def register_lineage_edge(self, parent: Any, child: Any, transition_type: str) -> InteractionLineageEdge:
        edge = InteractionLineageEdge(
            parent_id=str(getattr(parent, "crystal_id")),
            parent_order=str(getattr(getattr(parent, "order", None), "name", getattr(parent, "order", "BASE"))),
            child_id=str(getattr(child, "crystal_id")),
            child_order=str(getattr(getattr(child, "order", None), "name", getattr(child, "order", "BASE"))),
            transition_type=transition_type,
        )
        self._edges[edge.edge_id] = edge
        self._save()
        self._append_journal({
            "timestamp": time.time(),
            "operation": "write_edge",
            "edge_id": edge.edge_id,
            "detail": f"{edge.parent_id[:8]}->{edge.child_id[:8]} [{transition_type}]",
        })
        return edge

    def get_node(self, node_id: str) -> Optional[InteractionNode]:
        return self._nodes.get(str(node_id))

    def retrieve_by_interpretive_issue(self, interpretive_issue: str, order: Optional[str] = None) -> List[InteractionNode]:
        return self._retrieve_indexed("interpretive_issue", interpretive_issue, order=order)

    def retrieve_by_response_strategy(self, strategy_class: str) -> List[InteractionNode]:
        return self._retrieve_indexed("response_strategy", strategy_class, order=None)

    def retrieve_by_input_signature(self, input_signature: str, order: Optional[str] = None) -> List[InteractionNode]:
        return self._retrieve_indexed("input_signature", input_signature, order=order)

    def retrieve_by_processing_tier(self, processing_tier: str, order: Optional[str] = None) -> List[InteractionNode]:
        return self._retrieve_indexed("processing_tier", processing_tier, order=order)

    def get_quasi_by_archetype(self, interaction_archetype: str, min_confidence: float = 0.0) -> List[InteractionNode]:
        nodes = self._retrieve_indexed("interaction_archetype", interaction_archetype, order="QUASI")
        nodes = [node for node in nodes if float(node.payload.get("confidence", 0.0) or 0.0) >= min_confidence]
        nodes.sort(key=lambda node: float(node.payload.get("confidence", 0.0) or 0.0), reverse=True)
        return nodes

    def retrieve_best_interaction_quasi(self, intake_signature: Mapping[str, Any], min_confidence: float = 0.0, top_k: int = 3) -> List[Dict[str, Any]]:
        candidates = self._candidate_quasis(intake_signature, min_confidence=min_confidence)
        scored: List[Dict[str, Any]] = []
        for node in candidates:
            match = self.engine.match_quasi(node.payload, intake_signature)
            scored.append({
                "node": node,
                "match_score": match,
                "confidence": float(node.payload.get("confidence", 0.0) or 0.0),
                "execution_surface": dict(node.execution_surface or self.engine.build_execution_surface(node.payload)),
            })
        scored.sort(key=lambda item: (item["match_score"], item["confidence"]), reverse=True)
        return scored[:max(1, int(top_k or 1))]

    def get_journal(self, tail: int = 50) -> List[Dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        lines = self.journal_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-tail:] if line.strip()]

    def get_ancestry(self, node_id: str) -> Dict[str, Any]:
        roots: List[Dict[str, Any]] = []
        frontier = [str(node_id)]
        seen = set(frontier)
        while frontier:
            current = frontier.pop(0)
            node = self.get_node(current)
            if node is not None:
                roots.append(node.to_dict())
            for edge in self._edges.values():
                if edge.child_id != current or edge.parent_id in seen:
                    continue
                seen.add(edge.parent_id)
                frontier.append(edge.parent_id)
        return {
            "node_id": str(node_id),
            "nodes": roots,
            "edges": [edge.to_dict() for edge in self._edges.values() if edge.child_id in seen or edge.parent_id in seen],
        }

    def _candidate_quasis(self, intake_signature: Mapping[str, Any], min_confidence: float = 0.0) -> List[InteractionNode]:
        buckets: List[InteractionNode] = []
        input_signature = str(intake_signature.get("input_signature") or "")
        issue = str(intake_signature.get("interpretive_issue") or "")
        tier = str(intake_signature.get("processing_tier") or "")
        if input_signature:
            buckets.extend(self.retrieve_by_input_signature(input_signature, order="QUASI"))
        if issue:
            buckets.extend(self.retrieve_by_interpretive_issue(issue, order="QUASI"))
        if tier:
            buckets.extend(self.retrieve_by_processing_tier(tier, order="QUASI"))
        if not buckets:
            buckets = [node for node in self._nodes.values() if node.order == "QUASI" and not node.is_relic]
        deduped: Dict[str, InteractionNode] = {}
        for node in buckets:
            if float(node.payload.get("confidence", 0.0) or 0.0) < min_confidence:
                continue
            deduped[node.node_id] = node
        return list(deduped.values())

    def _retrieve_indexed(self, index_name: str, key: str, order: Optional[str]) -> List[InteractionNode]:
        key = str(key or "").strip()
        if not key:
            return []
        node_ids = list(self._indexes.get(index_name, {}).get(key, []))
        nodes = []
        for node_id in node_ids:
            node = self._nodes.get(node_id)
            if node is None or node.is_relic:
                continue
            if order and node.order != order:
                continue
            nodes.append(node)
        return nodes

    def _update_indexes(self, node: InteractionNode) -> None:
        values_by_index = {
            "interpretive_issue": [str(node.payload.get("interpretive_issue") or "")],
            "response_strategy": [
                str(node.payload.get("response_strategy_class") or ""),
                str(node.payload.get("primary_response_strategy") or ""),
                str(node.payload.get("secondary_response_strategy") or ""),
            ],
            "input_signature": [str(node.payload.get("input_signature") or "")],
            "processing_tier": [str(node.payload.get("processing_tier") or "")],
            "interaction_archetype": [str(node.payload.get("interaction_archetype") or "")],
        }
        for index_name, values in values_by_index.items():
            bucket = self._indexes.setdefault(index_name, {})
            for value in self._unique(values):
                ids = bucket.setdefault(value, [])
                if node.node_id not in ids:
                    ids.append(node.node_id)

    def _load(self) -> None:
        if self.nodes_path.exists():
            data = json.loads(self.nodes_path.read_text(encoding="utf-8"))
            self._nodes = {item["node_id"]: InteractionNode.from_dict(item) for item in data.get("nodes", [])}
        if self.edges_path.exists():
            data = json.loads(self.edges_path.read_text(encoding="utf-8"))
            self._edges = {item["edge_id"]: InteractionLineageEdge.from_dict(item) for item in data.get("edges", [])}
        if self.indexes_path.exists():
            data = json.loads(self.indexes_path.read_text(encoding="utf-8"))
            self._indexes.update({k: dict(v) for k, v in dict(data.get("indexes") or {}).items()})

    def _save(self) -> None:
        atomic_write_json(self.nodes_path, {"nodes": [node.to_dict() for node in self._nodes.values()]})
        atomic_write_json(self.edges_path, {"edges": [edge.to_dict() for edge in self._edges.values()]})
        atomic_write_json(self.indexes_path, {"indexes": self._indexes})

    def _append_journal(self, entry: Mapping[str, Any]) -> None:
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(entry), sort_keys=True, default=str) + "\n")

    def _unique(self, values: Iterable[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result
