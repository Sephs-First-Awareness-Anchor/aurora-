"""
Constraint-native proposition substrate for lineage-activated discourse state.

This module keeps proposition structure small and executable:
  - proposition nodes derived from claim atoms
  - continuation / support / contradiction / revision / causal edges
  - provenance-weighted confidence per proposition

It is intentionally lightweight so it can be activated from lineage artifacts
without pulling the rest of the runtime into a heavy import chain.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


class PropositionSubstrate:
    def __init__(self) -> None:
        self.max_nodes: int = 256
        self.max_edges: int = 1024
        self.active_window: int = 32
        self.graph_relations: List[str] = [
            "continuation",
            "support",
            "contradiction",
            "revision",
            "causal",
            "provenance",
        ]
        self.source_confidence: Dict[str, float] = {
            "user": 0.74,
            "aurora": 0.66,
            "memory": 0.70,
            "external": 0.84,
        }
        self.flags: Dict[str, Any] = {
            "belief_revision_enabled": True,
            "causal_mesh_enabled": True,
            "provenance_enabled": True,
            "weighted_lookup_enabled": True,
        }
        self.target_ability: str = ""
        self.lineage_output_id: str = ""
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Deque[Dict[str, Any]] = deque()
        self._node_order: Deque[str] = deque()
        self._claim_index: Dict[Tuple[str, str, str, bool, str], str] = {}
        self._active_ids: Deque[str] = deque()

    def configure(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        runtime_contract = dict(manifest.get("runtime_contract", {}) or {})
        schema = dict(runtime_contract.get("working_memory_schema", {}) or {})
        shadow_state = dict(manifest.get("shadow_state", {}) or {})
        pipeline = dict(shadow_state.get("pipeline", {}) or {})
        self.max_nodes = max(64, int(schema.get("max_nodes", self.max_nodes) or self.max_nodes))
        self.max_edges = max(128, int(schema.get("max_edges", self.max_edges) or self.max_edges))
        self.active_window = max(8, int(schema.get("active_window", self.active_window) or self.active_window))
        self.graph_relations = list(schema.get("graph_relations", self.graph_relations) or self.graph_relations)
        self.source_confidence = dict(self.source_confidence)
        self.source_confidence.update(dict(schema.get("source_confidence", {}) or {}))
        self.flags = {
            "belief_revision_enabled": bool(
                schema.get("belief_revision_enabled", pipeline.get("belief_revision_enabled", False))
            ),
            "causal_mesh_enabled": bool(
                schema.get("causal_mesh_enabled", pipeline.get("causal_mesh_enabled", False))
            ),
            "provenance_enabled": bool(
                schema.get("provenance_enabled", shadow_state.get("working_memory", {}).get("source_weighting_enabled", False))
            ),
            "weighted_lookup_enabled": bool(
                schema.get("weighted_lookup_enabled", pipeline.get("weighted_claim_lookup", False))
            ),
        }
        self.target_ability = str(manifest.get("target_ability", "") or "")
        self.lineage_output_id = str(manifest.get("final_output_id", "") or "")
        return self.report()

    def _claim_key(self, claim: Dict[str, Any]) -> Tuple[str, str, str, bool, str]:
        return (
            str(claim.get("subject", "")).strip(),
            str(claim.get("relation", "")).strip(),
            str(claim.get("object", "")).strip(),
            bool(claim.get("negated", False)),
            str(claim.get("source", "")).strip(),
        )

    def _branch_key(self, claim: Dict[str, Any]) -> str:
        raw = json.dumps(
            {
                "subject": str(claim.get("subject", "")).strip(),
                "relation": str(claim.get("relation", "")).strip(),
                "source": str(claim.get("source", "")).strip(),
                "object": str(claim.get("object", "")).strip(),
                "negated": bool(claim.get("negated", False)),
            },
            sort_keys=True,
        )
        return "BR:" + hashlib.sha1(raw.encode()).hexdigest()[:10]

    def _node_id(self, claim: Dict[str, Any]) -> str:
        raw = json.dumps(self._claim_key(claim), sort_keys=True)
        return "P:" + hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _edge_id(self, kind: str, left_id: str, right_id: str) -> str:
        raw = f"{kind}:{left_id}:{right_id}"
        return "E:" + hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _source_weight(self, source: str) -> float:
        token = str(source or "").strip().lower()
        return float(self.source_confidence.get(token, self.source_confidence.get("memory", 0.68)))

    def _claim_overlap(self, left: Dict[str, Any], right: Dict[str, Any]) -> int:
        terms_left = set()
        terms_right = set()
        for bucket, terms in ((left, terms_left), (right, terms_right)):
            for key in ("subject", "object", "topic"):
                for part in str(bucket.get(key, "")).split():
                    if len(part) >= 3:
                        terms.add(part)
            for part in str(bucket.get("relation", "")).replace("_", " ").split():
                if len(part) >= 3:
                    terms.add(part)
        return int(len(terms_left & terms_right))

    def _upsert_edge(
        self,
        kind: str,
        left_id: str,
        right_id: str,
        *,
        turn: int,
        weight: float = 0.5,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not left_id or not right_id or left_id == right_id:
            return
        edge_id = self._edge_id(kind, left_id, right_id)
        for edge in list(self.edges)[-48:]:
            if edge.get("edge_id") == edge_id:
                edge["weight"] = max(float(edge.get("weight", 0.0)), float(weight))
                edge["last_turn"] = int(turn)
                if meta:
                    merged_meta = dict(edge.get("meta", {}) or {})
                    merged_meta.update(meta)
                    edge["meta"] = merged_meta
                return

        self.edges.append({
            "edge_id": edge_id,
            "kind": kind,
            "source_id": left_id,
            "target_id": right_id,
            "weight": _clamp(weight, 0.0, 1.0),
            "created_at": float(time.time()),
            "turn": int(turn),
            "last_turn": int(turn),
            "meta": dict(meta or {}),
        })
        while len(self.edges) > self.max_edges:
            self.edges.popleft()

    def _trim_nodes(self) -> None:
        while len(self.nodes) > self.max_nodes and self._node_order:
            old_id = self._node_order.popleft()
            node = self.nodes.pop(old_id, None)
            if not node:
                continue
            self._claim_index.pop(self._claim_key(node), None)
            self.edges = deque(
                [
                    edge
                    for edge in self.edges
                    if edge.get("source_id") != old_id and edge.get("target_id") != old_id
                ]
            )

    def _edge_summary(self, proposition_id: str) -> Dict[str, int]:
        out = {name: 0 for name in self.graph_relations}
        for edge in self.edges:
            if edge.get("source_id") == proposition_id or edge.get("target_id") == proposition_id:
                kind = str(edge.get("kind", "")).strip()
                out[kind] = int(out.get(kind, 0)) + 1
        return out

    def _refresh_confidence(self, proposition_id: str) -> None:
        node = self.nodes.get(str(proposition_id))
        if not node:
            return
        base = self._source_weight(str(node.get("source", "") or "memory"))
        evidence_bonus = min(0.18, 0.03 * max(0, int(node.get("evidence_count", 1)) - 1))
        summary = self._edge_summary(str(proposition_id))
        support_bonus = min(0.12, 0.03 * int(summary.get("support", 0)))
        continuation_bonus = min(0.08, 0.02 * int(summary.get("continuation", 0)))
        causal_bonus = 0.05 if int(summary.get("causal", 0)) > 0 else 0.0
        contradiction_penalty = min(0.30, 0.08 * int(summary.get("contradiction", 0)))
        revision_penalty = min(0.12, 0.04 * int(summary.get("revision", 0)))
        node["confidence"] = _clamp(
            base + evidence_bonus + support_bonus + continuation_bonus + causal_bonus
            - contradiction_penalty - revision_penalty,
            0.10,
            0.99,
        )

    def note_claim(self, claim: Dict[str, Any], recent_claims: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
        key = self._claim_key(claim)
        proposition_id = self._claim_index.get(key, "")
        turn = int(claim.get("turn", 0) or 0)
        if proposition_id and proposition_id in self.nodes:
            node = self.nodes[proposition_id]
            node["last_turn"] = turn
            node["evidence_count"] = int(node.get("evidence_count", 1)) + 1
            if claim.get("text"):
                node["text"] = str(claim.get("text", ""))[:280]
            if claim.get("topic"):
                node["topic"] = str(claim.get("topic", "")).strip()
        else:
            proposition_id = self._node_id(claim)
            node = {
                "proposition_id": proposition_id,
                "branch_id": self._branch_key(claim),
                "subject": str(claim.get("subject", "")).strip(),
                "relation": str(claim.get("relation", "")).strip(),
                "object": str(claim.get("object", "")).strip(),
                "negated": bool(claim.get("negated", False)),
                "source": str(claim.get("source", "")).strip(),
                "topic": str(claim.get("topic", "")).strip(),
                "text": str(claim.get("text", ""))[:280],
                "turn": turn,
                "created_at": float(time.time()),
                "last_turn": turn,
                "evidence_count": 1,
                "confidence": self._source_weight(str(claim.get("source", "") or "memory")),
            }
            self.nodes[proposition_id] = node
            self._claim_index[key] = proposition_id
            self._node_order.append(proposition_id)
            self._trim_nodes()

        linked = 0
        for prior in list(recent_claims or [])[:8]:
            prior_id = str(prior.get("proposition_id", "")).strip()
            if not prior_id:
                prior_id = self._claim_index.get(self._claim_key(prior), "")
            if not prior_id or prior_id == proposition_id or prior_id not in self.nodes:
                continue

            same_subject = str(prior.get("subject", "")).strip() == str(claim.get("subject", "")).strip()
            same_relation = str(prior.get("relation", "")).strip() == str(claim.get("relation", "")).strip()
            same_source = str(prior.get("source", "")).strip() == str(claim.get("source", "")).strip()
            same_object = str(prior.get("object", "")).strip() == str(claim.get("object", "")).strip()
            same_negation = bool(prior.get("negated", False)) == bool(claim.get("negated", False))
            overlap = self._claim_overlap(prior, claim)

            if same_subject and same_relation and ((not same_object) or (not same_negation)):
                edge_kind = "revision" if same_source and self.flags.get("belief_revision_enabled", False) else "contradiction"
                self._upsert_edge(edge_kind, prior_id, proposition_id, turn=turn, weight=0.88, meta={"overlap": overlap})
                linked += 1
            elif same_subject and same_relation:
                self._upsert_edge("support", prior_id, proposition_id, turn=turn, weight=0.62, meta={"overlap": overlap})
                linked += 1
            elif overlap > 0:
                self._upsert_edge(
                    "continuation",
                    prior_id,
                    proposition_id,
                    turn=turn,
                    weight=min(0.75, 0.32 + (0.08 * overlap)),
                    meta={"overlap": overlap},
                )
                linked += 1

            if linked >= 4:
                break

        if self.flags.get("provenance_enabled", False):
            prov_id = "SRC:" + hashlib.sha1(str(node.get("source", "")).encode()).hexdigest()[:10]
            self._upsert_edge(
                "provenance",
                prov_id,
                proposition_id,
                turn=turn,
                weight=self._source_weight(str(node.get("source", "") or "memory")),
                meta={"source": str(node.get("source", "") or "")},
            )

        self._active_ids.append(proposition_id)
        while len(self._active_ids) > self.active_window:
            self._active_ids.popleft()
        self._refresh_confidence(proposition_id)

        claim["proposition_id"] = proposition_id
        claim["branch_id"] = str(node.get("branch_id", "") or "")
        claim["confidence"] = float(node.get("confidence", 0.0) or 0.0)
        return dict(node)

    def note_claim_bundle(self, claims: Iterable[Dict[str, Any]], raw_text: str = "") -> None:
        claim_list = [dict(claim) for claim in claims if claim]
        if len(claim_list) < 2 or not self.flags.get("causal_mesh_enabled", False):
            return
        raw_low = str(raw_text or "").lower()
        causal_markers = ("because", "so ", "therefore", "thus", "which means", "leads to", "causes", "requires", "blocks")
        if not any(marker in raw_low for marker in causal_markers) and not any(
            str(claim.get("relation", "")).strip() in {"causes", "requires", "blocks", "breaks"}
            for claim in claim_list
        ):
            return
        for left, right in zip(claim_list, claim_list[1:]):
            left_id = str(left.get("proposition_id", "")).strip()
            right_id = str(right.get("proposition_id", "")).strip()
            if not left_id or not right_id or left_id == right_id:
                continue
            self._upsert_edge("causal", left_id, right_id, turn=int(right.get("turn", 0) or 0), weight=0.72)
            self._refresh_confidence(left_id)
            self._refresh_confidence(right_id)

    def node_for_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        proposition_id = str(claim.get("proposition_id", "")).strip()
        if not proposition_id:
            proposition_id = self._claim_index.get(self._claim_key(claim), "")
        if not proposition_id or proposition_id not in self.nodes:
            return {}
        node = dict(self.nodes.get(proposition_id, {}) or {})
        node["edge_summary"] = self._edge_summary(proposition_id)
        return node

    def score_claim(self, claim: Dict[str, Any]) -> float:
        node = self.node_for_claim(claim)
        if not node:
            return 0.0
        summary = dict(node.get("edge_summary", {}) or {})
        score = float(node.get("confidence", 0.0) or 0.0)
        score += min(0.12, 0.03 * int(summary.get("continuation", 0)))
        score += min(0.10, 0.05 * int(summary.get("causal", 0)))
        score -= min(0.20, 0.05 * int(summary.get("contradiction", 0)))
        if str(node.get("proposition_id", "")) in self._active_ids:
            score += 0.08
        return _clamp(score, 0.0, 1.25)

    def report(self) -> Dict[str, Any]:
        kind_counts: Dict[str, int] = {}
        for edge in self.edges:
            kind = str(edge.get("kind", "")).strip() or "unknown"
            kind_counts[kind] = int(kind_counts.get(kind, 0)) + 1
        return {
            "target_ability": self.target_ability,
            "lineage_output_id": self.lineage_output_id,
            "node_count": int(len(self.nodes)),
            "edge_count": int(len(self.edges)),
            "active_count": int(len(self._active_ids)),
            "flags": dict(self.flags),
            "edge_kinds": kind_counts,
        }
