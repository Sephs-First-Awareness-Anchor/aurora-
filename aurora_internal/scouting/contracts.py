"""
Scout request/report contracts (Subsurface Presence and Evidence Scout
spec, sections 7-8). Plain, JSON-serializable dataclasses -- the wire
format between Subsurface/Surface (which formulate ScoutRequests) and
the Scout worker (which produces ScoutReports).

Two hard architectural boundaries encoded directly in these shapes,
not left to convention:

- ScoutRequest.interpreted_input is what a response-fit Scout receives
  as authoritative input -- never the raw user utterance. A Scout
  reinterpreting raw text on Aurora's behalf is exactly what section 4
  forbids.
- ScoutReport has NO final_response field, on purpose. It cannot
  represent "the answer Aurora should give" even accidentally -- only
  response_relationships (named categories: acknowledge, explain,
  clarify, etc.) and fit_rationales, which are evidence ABOUT response
  fit, not a drafted response.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# spec section 8: named response-relationship categories a Scout may
# report evidence about -- never a drafted response itself.
RESPONSE_RELATIONSHIP_KINDS = (
    "acknowledge",
    "continue_exploration",
    "explain",
    "answer_directly",
    "invite_continuation",
    "challenge",
    "reassure",
    "clarify",
    "remain_conversationally_present",
)

REQUEST_KINDS = ("response_fit", "knowledge_gap")


@dataclass
class ScoutRequest:
    turn_id: str
    request_kind: str = "response_fit"
    interpreted_input: str = ""
    inquiry: str = ""
    evidence_needed: str = ""
    representation_refs: List[str] = field(default_factory=list)
    priority: float = 0.5
    max_evidence_items: int = 5
    max_result_chars: int = 1200
    ttl_s: float = 30.0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)

    @property
    def deadline(self) -> float:
        return self.created_at + float(self.ttl_s or 30.0)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["deadline"] = self.deadline
        return d

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ScoutRequest":
        known = {f for f in cls.__dataclass_fields__.keys()}
        payload = {k: v for k, v in (raw or {}).items() if k in known}
        return cls(**payload)


@dataclass
class ScoutReport:
    request_id: str
    turn_id: str
    status: str = "ok"  # "ok" | "no_evidence" | "failed" | "cancelled"
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    response_relationships: List[str] = field(default_factory=list)
    fit_rationales: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)
    confidence: float = 0.0
    elapsed_ms: float = 0.0
    completed_at: float = field(default_factory=time.time)
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        # Architectural guard, not just a convention: a Scout must never
        # be able to smuggle a drafted response through evidence_items.
        # Strip anything that looks like an attempt at one rather than
        # trusting every future caller to remember not to add it.
        cleaned = []
        for item in self.evidence_items:
            if isinstance(item, dict):
                item = {k: v for k, v in item.items() if k != "final_response"}
                item["emittable"] = False
            cleaned.append(item)
        self.evidence_items = cleaned
        self.response_relationships = [
            r for r in self.response_relationships if r in RESPONSE_RELATIONSHIP_KINDS
        ]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ScoutReport":
        known = {f for f in cls.__dataclass_fields__.keys()}
        payload = {k: v for k, v in (raw or {}).items() if k in known}
        return cls(**payload)
