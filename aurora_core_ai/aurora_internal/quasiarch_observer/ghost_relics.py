"""
Ghost relic acceleration for Aurora's internal QuasiArch Observer.

Relics preserve structural templates from collapsed or superseded crystals.
They do not reactivate the old crystal as a live node; they only bias future
formation when a new issue family begins to reform along a similar geometry.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _normalize_ref(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "")).strip("_")


def _unique_preserve(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = _normalize_ref(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


@dataclass
class GhostRelic:
    relic_id: str
    original_order: str
    original_id: str
    anchor_refs: List[str] = field(default_factory=list)
    facet_template: Dict[str, Any] = field(default_factory=dict)
    point_template: Dict[str, float] = field(default_factory=dict)
    tag_template: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    dissolution_reason: str = ""
    reformation_count: int = 0
    last_reformed: Optional[float] = None
    last_match_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relic_id": self.relic_id,
            "original_order": self.original_order,
            "original_id": self.original_id,
            "anchor_refs": list(self.anchor_refs),
            "facet_template": dict(self.facet_template),
            "point_template": dict(self.point_template),
            "tag_template": list(self.tag_template),
            "created_at": float(self.created_at),
            "dissolution_reason": self.dissolution_reason,
            "reformation_count": int(self.reformation_count),
            "last_reformed": self.last_reformed,
            "last_match_score": float(self.last_match_score),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GhostRelic":
        return cls(
            relic_id=str(data.get("relic_id", "")),
            original_order=str(data.get("original_order", "")),
            original_id=str(data.get("original_id", "")),
            anchor_refs=list(data.get("anchor_refs", []) or []),
            facet_template=dict(data.get("facet_template", {}) or {}),
            point_template={
                str(key): float(value)
                for key, value in dict(data.get("point_template", {}) or {}).items()
            },
            tag_template=list(data.get("tag_template", []) or []),
            created_at=float(data.get("created_at", time.time()) or time.time()),
            dissolution_reason=str(data.get("dissolution_reason", "")),
            reformation_count=int(data.get("reformation_count", 0) or 0),
            last_reformed=data.get("last_reformed"),
            last_match_score=float(data.get("last_match_score", 0.0) or 0.0),
        )


class GhostRelicSystem:
    """Persistence and matching for structural relic templates."""

    _SKIP_FACET_VALUES = {
        "",
        "none",
        "unknown",
        "unknown_issue",
        "unknown_strategy",
        "insufficient_successful_events",
        "insufficient_successful_events_for_prediction",
    }

    def __init__(self, storage_path: str) -> None:
        self.storage_path = storage_path
        self.relics: Dict[str, GhostRelic] = {}
        self.total_reformations = 0
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return
        self.total_reformations = int(payload.get("total_reformations", 0) or 0)
        for relic_id, relic_data in dict(payload.get("relics", {}) or {}).items():
            try:
                relic = GhostRelic.from_dict(relic_data)
            except Exception:
                continue
            if not relic.relic_id:
                relic.relic_id = str(relic_id)
            self.relics[relic.relic_id] = relic

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            payload = {
                "total_reformations": int(self.total_reformations),
                "relics": {
                    relic_id: relic.to_dict()
                    for relic_id, relic in self.relics.items()
                },
            }
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            return True
        except Exception:
            return False

    def create_relic(
        self,
        crystal: Any,
        anchor_refs: Sequence[str],
        reason: str = "collapsed_or_superseded",
    ) -> Optional[GhostRelic]:
        crystal_id = str(getattr(crystal, "crystal_id", "") or "").strip()
        if not crystal_id:
            return None
        order = str(getattr(getattr(crystal, "order", None), "name", "") or "UNKNOWN")
        relic_id = f"relic::{order.lower()}::{_normalize_ref(crystal_id)}"
        point_template = {}
        for point_name, point in dict(getattr(crystal, "relational_points", {}) or {}).items():
            try:
                point_template[str(point_name)] = float(getattr(point, "score", 0.0) or 0.0)
            except Exception:
                continue
        relic = GhostRelic(
            relic_id=relic_id,
            original_order=order,
            original_id=crystal_id,
            anchor_refs=_unique_preserve(anchor_refs),
            facet_template=dict(getattr(crystal, "facet_values", {}) or {}),
            point_template=point_template,
            tag_template=list(getattr(crystal, "tags", []) or []),
            dissolution_reason=str(reason or ""),
        )
        self.relics[relic_id] = relic
        self.save()
        return relic

    def find_best_relic(
        self,
        anchor_refs: Sequence[str],
        original_order: Optional[str] = None,
        min_match: float = 0.34,
    ) -> Tuple[Optional[GhostRelic], float]:
        target_refs = set(_unique_preserve(anchor_refs))
        if not target_refs:
            return None, 0.0

        best_relic: Optional[GhostRelic] = None
        best_score = 0.0
        order_name = str(original_order or "").upper()
        for relic in self.relics.values():
            if order_name and str(relic.original_order or "").upper() != order_name:
                continue
            relic_refs = set(_unique_preserve(relic.anchor_refs))
            if not relic_refs:
                continue
            overlap = len(target_refs & relic_refs)
            union = len(target_refs | relic_refs)
            score = overlap / float(union or 1)
            if score > best_score:
                best_score = score
                best_relic = relic
        if best_score < float(min_match):
            return None, 0.0
        return best_relic, best_score

    def apply_relic(
        self,
        relic: GhostRelic,
        crystal: Any,
        match_score: float,
    ) -> Dict[str, Any]:
        reused_facets: List[str] = []
        point_blends = 0

        get_facet = getattr(crystal, "get_facet", None)
        set_facet = getattr(crystal, "set_facet", None)
        if callable(get_facet) and callable(set_facet):
            for facet_name, facet_value in relic.facet_template.items():
                current_value = get_facet(facet_name)
                current_text = str(current_value or "").strip().lower()
                if current_text in self._SKIP_FACET_VALUES and facet_value not in (None, ""):
                    set_facet(facet_name, facet_value)
                    reused_facets.append(str(facet_name))

        get_point = getattr(crystal, "get_point", None)
        if callable(get_point):
            for point_name, cached_score in relic.point_template.items():
                point = get_point(point_name)
                if point is None:
                    continue
                point.score = max(float(point.score or 0.0), float(cached_score) * 0.85)
                point_blends += 1

        tags = list(getattr(crystal, "tags", []) or [])
        for tag in list(relic.tag_template or []):
            if tag and tag not in tags:
                tags.append(tag)
        if "ghost_relic_rehydrated" not in tags:
            tags.append("ghost_relic_rehydrated")
        crystal.tags = tags

        lineage_meta = dict(getattr(crystal, "lineage_meta", {}) or {})
        lineage_meta["ghost_relic_id"] = relic.relic_id
        lineage_meta["ghost_relic_match"] = round(float(match_score), 4)
        crystal.lineage_meta = lineage_meta

        relic.reformation_count += 1
        relic.last_reformed = time.time()
        relic.last_match_score = float(match_score)
        self.total_reformations += 1
        self.save()
        return {
            "relic_id": relic.relic_id,
            "match_score": float(match_score),
            "reused_facets": reused_facets,
            "point_blends": int(point_blends),
        }

    def stats(self) -> Dict[str, Any]:
        order_counts: Dict[str, int] = {}
        for relic in self.relics.values():
            order_counts[relic.original_order] = order_counts.get(relic.original_order, 0) + 1
        active = [
            float(relic.last_match_score or 0.0)
            for relic in self.relics.values()
            if relic.reformation_count > 0
        ]
        avg_match = (sum(active) / len(active)) if active else 0.0
        return {
            "total_relics": len(self.relics),
            "total_reformations": int(self.total_reformations),
            "avg_match_score": round(avg_match, 4),
            "relics_by_order": order_counts,
        }
