#!/usr/bin/env python3
"""
aurora_dream_substrate.py

AURORA DREAM SUBSTRATE, FAIL-STREAM, POSITIVE-AFFECT, DEVELOPMENTAL
WRITEBACK, AND NATIVE INTERMEDIATE RESOLUTION DIRECTIVE, Sections 11-21.

A narrow, read-only gathering layer over signals Aurora's own architecture
already produces, for Dream synthesis to draw on. This module does not
generate Dream episodes, does not decide what a Dream should be about, and
does not write anything back into any subsystem -- it only reads and
abstracts.

Reused native signals (per this pass's own code audit, not assumption):
  - CrystalProcessingSystem ("dps", reached via systems['dimensional'].dps)
    facets stamped "achievement"/"misstep" (aurora_dimensional_systems.py
    FailPointLedger.record_failpoint_update -> CrystalProcessingSystem.
    record_failpoint_update) and "relief_event" (note_relief_event).
    These are Aurora's own existing salience stamps -- this module does not
    invent a new emotional classifier; it reads the one that already exists.
  - FailPointLedger.rich_stream (aurora_dream_trainer.py, added by this same
    directive) for the temporally-ordered fail/pressure stream and for
    recurrence links already established by RichFailStream's own native
    exact-match recurrence detection.

What is deliberately NOT done here:
  - No literal waking text (user_turns/assistant_turns/response bodies) is
    exposed by this module. Fragments carry only: a concept/topic label
    (already-abstracted crystal concept name, or a topic/action_type
    identifier already produced by UnderstandingContract -- never raw
    sentences), a salience channel, a confidence, and a recency timestamp.
  - No wiring into DreamTrainer.train_on_bundle / SimulationSession.
    run_episode / DreamCurriculumQueue's actual prompt construction. Per
    this directive's Repair Authority (Section 66), deciding how much
    weight abstracted-fragment material should carry relative to today's
    literal corpus-text seeding, or what a resulting Dream scenario should
    be built to teach, is an architecturally significant decision this
    pass does not make. This module makes the substrate real and testable;
    it does not redesign Dream's existing generation call sites.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

POSITIVE_FACET_ROLES = ("achievement", "relief_event")
NEGATIVE_FACET_ROLES = ("misstep",)
SALIENT_FACET_ROLES = POSITIVE_FACET_ROLES + NEGATIVE_FACET_ROLES


@dataclass
class DreamFragment:
    """One abstracted unit eligible for Dream synthesis. Never literal text."""
    concept: str
    facet_role: str
    salience_channel: str          # "positive" | "negative"
    confidence: float
    content_tag: str               # already-compact native content, e.g. "context_carryover:0.412" or "X@37"
    last_accessed: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "facet_role": self.facet_role,
            "salience_channel": self.salience_channel,
            "confidence": round(float(self.confidence), 4),
            "content_tag": self.content_tag,
            "last_accessed": self.last_accessed,
        }


@dataclass
class DreamSubstrate:
    """
    Conceptual structure named in Section 21:
        DreamSubstrate = { FailPressureStream, SalientFragments,
                            PositiveFragments, HistoricalRecurrence }
    Reuses existing native structures (FailPointLedger.rich_stream,
    CrystalProcessingSystem facets) -- no duplicate memory system created.
    """
    fail_pressure_stream: List[Dict[str, Any]] = field(default_factory=list)
    salient_fragments: List[Dict[str, Any]] = field(default_factory=list)
    positive_fragments: List[Dict[str, Any]] = field(default_factory=list)
    historical_recurrence: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_fail_load: float = 0.0
    positive_opportunity_weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fail_pressure_stream": self.fail_pressure_stream,
            "salient_fragments": self.salient_fragments,
            "positive_fragments": self.positive_fragments,
            "historical_recurrence": self.historical_recurrence,
            "unresolved_fail_load": round(self.unresolved_fail_load, 4),
            "positive_opportunity_weight": round(self.positive_opportunity_weight, 4),
        }


def _get_dps(systems: Dict[str, Any]):
    dimensional = systems.get("dimensional") if isinstance(systems, dict) else None
    return getattr(dimensional, "dps", None)


def gather_salient_fragments(systems: Dict[str, Any], limit: int = 40) -> List[DreamFragment]:
    """
    Read Aurora's own existing salience stamps (crystal facets) rather than
    scoring waking experience with a new classifier. Section 11/49.
    """
    dps = _get_dps(systems)
    if dps is None or not hasattr(dps, "crystals"):
        return []
    fragments: List[DreamFragment] = []
    for crystal in dps.crystals.values():
        facets = getattr(crystal, "facets", None) or {}
        for facet in facets.values():
            role = getattr(facet, "role", "")
            if role not in SALIENT_FACET_ROLES:
                continue
            channel = "positive" if role in POSITIVE_FACET_ROLES else "negative"
            fragments.append(DreamFragment(
                concept=str(getattr(crystal, "concept", "") or ""),
                facet_role=role,
                salience_channel=channel,
                confidence=float(getattr(facet, "confidence", 0.0) or 0.0),
                content_tag=str(getattr(facet, "content", "") or "")[:60],
                last_accessed=float(getattr(facet, "last_accessed", 0.0) or 0.0),
            ))
    fragments.sort(key=lambda f: f.last_accessed, reverse=True)
    return fragments[:limit]


def unresolved_fail_load(dream_trainer: Any) -> float:
    """
    0..1, derived entirely from FailPointLedger's own existing top-fail
    score (the exact quantity that already drives
    flush_lessons_to_simulation()'s curriculum targeting) -- no fabricated
    weighting introduced (Section 38: "do not invent arbitrary weighting
    if a native pressure measure already exists"). A smooth saturating
    normalization (x / (x + 1)) is used only to bound an unbounded score
    into [0, 1) for the continuum required by Section 39 -- it does not
    change what the ledger considers a fail or how severely.
    """
    ledger = getattr(dream_trainer, "ledger", None)
    if ledger is None or not hasattr(ledger, "get_top_fails"):
        return 0.0
    top = ledger.get_top_fails(5)
    if not top:
        return 0.0
    total = sum(max(0.0, float(score)) for _, score in top)
    return total / (total + 1.0)


def positive_opportunity_weight(dream_trainer: Any) -> float:
    """
    Continuous complement of unresolved_fail_load -- Section 39's required
    continuum ("avoid binary switches"), Section 16's
    "FailureLoad decreasing => PositiveDreamOpportunity increasing".
    """
    return 1.0 - unresolved_fail_load(dream_trainer)


def gather_dream_substrate(systems: Dict[str, Any], limit: int = 40) -> DreamSubstrate:
    """
    Assemble the conceptual DreamSubstrate from real, already-audited
    native signals. Read-only: makes no state changes anywhere. Does not
    fabricate a failure when unresolved load is low (Section 19/52) --
    fail_pressure_stream and historical_recurrence are simply empty when
    the underlying rich stream has nothing recorded yet.
    """
    dream_trainer = systems.get("dream_trainer") if isinstance(systems, dict) else None
    ledger = getattr(dream_trainer, "ledger", None)
    rich_stream = getattr(ledger, "rich_stream", None)

    fail_pressure_stream: List[Dict[str, Any]] = []
    historical_recurrence: List[Dict[str, Any]] = []
    if rich_stream is not None and hasattr(rich_stream, "ordered"):
        events = rich_stream.ordered()
        fail_pressure_stream = [e.to_dict() for e in events]
        historical_recurrence = [e.to_dict() for e in events if e.recurrence_of is not None]

    fragments = gather_salient_fragments(systems, limit=limit)
    salient = [f.to_dict() for f in fragments]
    positive = [f.to_dict() for f in fragments if f.salience_channel == "positive"]

    load = unresolved_fail_load(dream_trainer) if dream_trainer is not None else 0.0
    opportunity = 1.0 - load

    return DreamSubstrate(
        fail_pressure_stream=fail_pressure_stream,
        salient_fragments=salient,
        positive_fragments=positive,
        historical_recurrence=historical_recurrence,
        unresolved_fail_load=load,
        positive_opportunity_weight=opportunity,
    )
