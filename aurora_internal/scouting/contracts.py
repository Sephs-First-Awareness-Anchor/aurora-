"""Scout request/report contracts for Aurora's model-free evidence Scouts.

A Scout is a retrieval limb only. It may carry an Aurora-formulated inquiry to
a retrieval source and return raw, provenance-bearing observations. It may not
interpret the user, classify response operations, explain response fit, decide
what Aurora should believe, or draft a response.

The legacy response_relationships / fit_rationales / contradictions fields stay
in ScoutReport only so older persisted reports can still be deserialized. The
contract forcibly clears them in __post_init__; no live Scout can use those
fields as a covert cognitive channel.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# Legacy wire compatibility only. Scouts are prohibited from populating these.
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

REQUEST_KINDS = ("response_fit", "knowledge_gap", "self_diagnostic")


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
    # Carried through from the originating ScoutRequest by the worker
    # (spec step 11) so Subsurface's evaluator can tell a turn-scoped
    # report from a self_diagnostic one (Subsurface's own autonomous
    # research, never scoped to a live user turn) without needing to
    # still hold the request itself, which is long gone by report time.
    request_kind: str = "response_fit"
    # Echo the originating inquiry metadata through the report so
    # Subsurface can bind knowledge evidence to the exact unresolved
    # target without reopening Scout request storage.
    inquiry: str = ""
    evidence_needed: str = ""
    interpreted_input: str = ""
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    # Legacy-only fields. __post_init__ clears them unconditionally so
    # interpretation cannot cross the Scout boundary.
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
        # Hard architectural prohibition: a retrieval worker cannot pass an
        # interpretation disguised as report metadata. Older persisted payloads
        # deserialize safely, but their semantic labels are discarded.
        self.response_relationships = []
        self.fit_rationales = []
        self.contradictions = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ScoutReport":
        known = {f for f in cls.__dataclass_fields__.keys()}
        payload = {k: v for k, v in (raw or {}).items() if k in known}
        return cls(**payload)
