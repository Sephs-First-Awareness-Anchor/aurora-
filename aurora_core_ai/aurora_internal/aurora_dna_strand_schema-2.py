#!/usr/bin/env python3
"""
AURORA DNA STRAND SCHEMA — STEP 14
=====================================
Formal constraint-operator event chain format.

WHAT A DNA STRAND IS:
    A DNA strand is the formal, serialisable record of HOW a VariantRecord
    came to exist — the full causal chain of constraint events from the
    moment the intake first arrived (Step 9) through Worth evaluation (Step 10),
    Solidification (Step 11), and Variant Promotion (Step 13).

    Each event in the strand is a StrandBead:
        {constraint, non_comp_channel, direction, layer_depth, tick,
         magnitude_delta, polarity_state}

    The sequence of StrandBeads is the DNA strand. It describes the exact
    path through constraint space that this variant took to crystallize.

    A strand is NOT a trace log. It is NOT a debug record. It is the
    genetic memory of a first-class variant — the chain of constraint
    events that, when they recur in the same order, cause the system to
    respond faster and cheaper (because the path is worn).

NON-COMP CHANNEL:
    Each bead identifies which of the five representational dimensions
    of the constraint was the primary channel:
        P    = POLARITY    — the toroidal phase gradient shifted
        M    = MAGNITUDE   — the activation intensity changed
        O    = OPERATOR    — the invariant transformation rule was applied
        D    = COST        — energy redistribution occurred
        DIFF = DIFFERENCE  — Δ channel event; deviation-from-reference signal fired

DIRECTION:
    Each bead has a direction relative to its constraint's I-State pair:
        POSITIVE = toward the affirmative pole (is, can, do, saw, did)
        NEGATIVE = toward the negative pole (isn't, can't, don't, saunt, didn't)
        NEUTRAL  = passing through the transition (polarity ≈ 0)

STRAND PROPERTIES:
    length       — number of beads (one per distinct constraint event)
    depth_span   — from shallowest to deepest constraint in the strand
    polarity_arc — net signed change in polarity from start to end of strand
    cost_total   — total energy consumed across all beads in this strand

STRAND LIBRARY:
    The StrandLibrary stores all active variant strands and supports:
        - signature matching: can a new event sequence match a known strand?
        - partial matching: does an incoming event sequence prefix-match?
        - strand degradation: unused strands decay in influence over time
          (measured in ticks without a match event)

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from aurora_internal.aurora_noncomp_registry import REGISTRY, NonCompDimension
from aurora_constraint_engine import ExistenceMode
from aurora_internal.aurora_variant_promotion import VariantRecord
from aurora_internal.aurora_cost_diff_score import score_from_cost, CostDiffScore
from aurora_internal.aurora_difference_buffer import DifferenceSnapshot


# ===========================================================================
# SECTION 1 — ENUMS
# ===========================================================================

class NonCompChannel(Enum):
    """Which Non-Comp representational dimension was the primary channel."""
    P    = "polarity"     # Toroidal phase gradient
    M    = "magnitude"    # Activation intensity
    O    = "operator"     # Invariant transformation rule
    D    = "cost"         # Energy redistribution
    DIFF = "difference"   # Δ channel — deviation-from-reference signal


class BeadDirection(Enum):
    """Signed direction relative to the constraint's I-State pair."""
    POSITIVE = "positive"   # toward affirmative pole
    NEGATIVE = "negative"   # toward negative pole
    NEUTRAL  = "neutral"    # transition (|polarity| < threshold)


# ===========================================================================
# SECTION 2 — STRAND BEAD
# ===========================================================================

@dataclass(frozen=True)
class StrandBead:
    """
    One event in a DNA strand — the formal minimal event unit.

    All seven fields are required. No field is optional.

    constraint      : which constraint this event touched
    channel         : which Non-Comp representational dimension was primary
    direction       : toward positive pole, negative pole, or neutral
    layer_depth     : ExistenceMode active when this event occurred
    tick            : system tick when this event was recorded
    magnitude_delta : signed magnitude change (positive = increase)
                      zero is valid (polarity-only shift)
    polarity_state  : cos(phase) at the END of this event ∈ [-1, +1]
    """
    constraint:      Constraint
    channel:         NonCompChannel
    direction:       BeadDirection
    layer_depth:     ExistenceMode
    tick:            int
    magnitude_delta: float
    polarity_state:  float  # always in [-1, +1]

    def __post_init__(self) -> None:
        if not (-1.0 <= self.polarity_state <= 1.0):
            raise ManifoldViolation(
                f"StrandBead.polarity_state must be in [-1, 1], got {self.polarity_state}"
            )

    def cost(self) -> float:
        """Energy cost of this bead's magnitude delta."""
        return REGISTRY.cost(self.constraint).shift_cost_coeff * abs(self.magnitude_delta)

    def cost_diff_score(
        self,
        snapshot: Optional[DifferenceSnapshot] = None,
    ) -> CostDiffScore:
        """
        Live cost score fusing this bead's static cost with the current
        cross-dimensional pressure from the DifferenceSnapshot.

        When snapshot is None or the system is calm (all C:D ≈ 0),
        live_score ≈ bead.cost(). Under cross-dimensional drift,
        live_score reflects the true operating cost in the current
        constraint environment.
        """
        return score_from_cost(self.cost(), snapshot)

    def bead_id(self) -> str:
        """Compact deterministic ID for this bead."""
        raw = (
            f"{self.constraint.name}:{self.channel.value}:"
            f"{self.direction.value}:{self.tick}"
        )
        return hashlib.sha1(raw.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, object]:
        return {
            "constraint":      self.constraint.name,
            "channel":         self.channel.value,
            "direction":       self.direction.value,
            "layer_depth":     self.layer_depth.name,
            "tick":            self.tick,
            "magnitude_delta": round(self.magnitude_delta, 6),
            "polarity_state":  round(self.polarity_state, 6),
        }

    @staticmethod
    def direction_from_polarity(polarity: float, threshold: float = 0.05) -> BeadDirection:
        """Classify a polarity value into a BeadDirection."""
        if polarity > threshold:
            return BeadDirection.POSITIVE
        if polarity < -threshold:
            return BeadDirection.NEGATIVE
        return BeadDirection.NEUTRAL


# ===========================================================================
# SECTION 3 — DNA STRAND
# ===========================================================================

@dataclass
class DNAStrand:
    """
    The full ordered sequence of StrandBeads for one VariantRecord.

    Immutable after sealing. Beads are appended during construction;
    seal() freezes the strand and computes derived properties.

    variant_id      — the VariantRecord this strand describes
    beads           — ordered list of events (chronological)
    strand_id       — unique hash of the full bead sequence
    sealed          — True once sealed (no further beads allowed)
    """
    variant_id: str
    beads:      List[StrandBead] = field(default_factory=list)
    strand_id:  str              = field(default="", init=False)
    sealed:     bool             = field(default=False, init=False)

    # Derived properties (computed on seal)
    _length:       int   = field(default=0, init=False, repr=False)
    _cost_total:   float = field(default=0.0, init=False, repr=False)
    _polarity_arc: float = field(default=0.0, init=False, repr=False)
    _depth_span:   Tuple[ExistenceMode, ExistenceMode] = field(
        default=(ExistenceMode.TRANSIENT, ExistenceMode.TRANSIENT),
        init=False, repr=False
    )

    def append(self, bead: StrandBead) -> None:
        """Add a bead to an unsealed strand."""
        if self.sealed:
            raise RuntimeError(f"DNAStrand {self.strand_id} is sealed — cannot append.")
        self.beads.append(bead)

    def seal(self) -> str:
        """
        Seal the strand and compute all derived properties.
        Returns the strand_id.
        """
        if not self.beads:
            raise RuntimeError("Cannot seal an empty DNAStrand.")
        self.sealed = True
        self._length = len(self.beads)
        self._cost_total = sum(b.cost() for b in self.beads)
        self._polarity_arc = self.beads[-1].polarity_state - self.beads[0].polarity_state

        depths = [b.layer_depth for b in self.beads]
        self._depth_span = (min(depths, key=lambda d: d.value),
                            max(depths, key=lambda d: d.value))

        # Strand ID: hash of all bead IDs in order
        raw = ":".join(b.bead_id() for b in self.beads)
        self.strand_id = "DNA:" + hashlib.sha1(raw.encode()).hexdigest()[:14]
        return self.strand_id

    @property
    def length(self) -> int:
        return self._length if self.sealed else len(self.beads)

    @property
    def cost_total(self) -> float:
        return self._cost_total

    def cost_diff_score_total(
        self,
        snapshot: Optional[DifferenceSnapshot] = None,
    ) -> CostDiffScore:
        """
        Live total cost for this entire strand fused with cross-dimensional
        pressure. The base_cost is the sum of all bead costs (same as
        cost_total). The amplifier reflects current operator-typed drift.

        Each bead may touch different constraints, but the strand-level
        score uses the system's global cross-dimensional state — because
        when topology is displaced (B:D) or agency is eroding (A:D),
        every bead in the strand pays a share of that environmental cost.
        """
        return score_from_cost(self.cost_total, snapshot)

    @property
    def polarity_arc(self) -> float:
        return self._polarity_arc

    @property
    def depth_span(self) -> Tuple[ExistenceMode, ExistenceMode]:
        return self._depth_span

    def constraint_sequence(self) -> List[Constraint]:
        """Return the ordered list of constraints across all beads."""
        return [b.constraint for b in self.beads]

    def signature(self) -> str:
        """
        Compact constraint+channel sequence signature for matching.
        Format: "X.M:T.P:B.D:A.M" etc.
        """
        return ":".join(f"{b.constraint.name}.{b.channel.value[0].upper()}" for b in self.beads)

    def prefix_matches(self, other_beads: List[StrandBead]) -> bool:
        """
        True if other_beads is a prefix of this strand's bead sequence.
        Uses constraint+channel+direction for matching (not tick or magnitude).
        """
        if len(other_beads) > len(self.beads):
            return False
        for mine, theirs in zip(self.beads[:len(other_beads)], other_beads):
            if (mine.constraint != theirs.constraint or
                    mine.channel != theirs.channel or
                    mine.direction != theirs.direction):
                return False
        return True

    def to_jsonl_dict(self) -> Dict[str, object]:
        return {
            "strand_id":    self.strand_id,
            "variant_id":   self.variant_id,
            "length":       self.length,
            "cost_total":   round(self.cost_total, 6),
            "polarity_arc": round(self.polarity_arc, 6),
            "depth_span":   [self.depth_span[0].name, self.depth_span[1].name],
            "signature":    self.signature(),
            "beads":        [b.to_dict() for b in self.beads],
        }


# ===========================================================================
# SECTION 4 — STRAND BUILDER (constructs DNAStrand from VariantRecord)
# ===========================================================================

class StrandBuilder:
    """
    Constructs a DNAStrand from a VariantRecord + a sequence of constraint events.

    The caller provides the ordered list of (Constraint, channel, delta, polarity, tick)
    tuples that represent the causal history of the variant. The builder
    classifies each event into a StrandBead, assembles the strand, and seals it.

    INTEGRATION:
        The caller is the evolution chamber or intake metabolizer, which
        has logged the sequence of constraint events that led to this variant.
        In the current stack, the closest source is ActionTrace + relief events
        from constraint_genealogy.py.
    """

    def build(
        self,
        variant: VariantRecord,
        events: List[Tuple[Constraint, NonCompChannel, float, float, int, ExistenceMode]],
    ) -> DNAStrand:
        """
        Build and seal a DNAStrand.

        events: List of (constraint, channel, magnitude_delta, polarity_state, tick, layer_depth)
        """
        strand = DNAStrand(variant_id=variant.variant_id)
        for (constraint, channel, mag_delta, polarity, tick, depth) in events:
            direction = StrandBead.direction_from_polarity(
                polarity,
                threshold=REGISTRY.polarity(constraint).flip_threshold * 0.1,
            )
            bead = StrandBead(
                constraint      = constraint,
                channel         = channel,
                direction       = direction,
                layer_depth     = depth,
                tick            = tick,
                magnitude_delta = mag_delta,
                polarity_state  = max(-1.0, min(1.0, polarity)),
            )
            strand.append(bead)
        strand.seal()
        return strand


# ===========================================================================
# SECTION 5 — STRAND LIBRARY
# ===========================================================================

class StrandLibrary:
    """
    Stores all active variant DNA strands and supports matching operations.

    STRAND DEGRADATION:
        Strands that are not matched for _DECAY_TICKS ticks lose influence.
        Influence decays linearly: strength = 1.0 - (ticks_unused / _DECAY_TICKS).
        At strength = 0, the strand is archived but no longer matched against.
        It is never deleted — it remains in the fossil record.

    MATCHING:
        Exact match: incoming bead sequence matches a strand exactly
        Prefix match: incoming bead sequence is a valid prefix of a strand
                      (means the system is "walking into" a known strand)
    """

    # Ticks without a match event before a strand loses influence
    _DECAY_TICKS: int = 200  # conservative — strands earn their persistence

    def __init__(self) -> None:
        self._strands: Dict[str, DNAStrand] = {}   # strand_id → strand
        self._last_match: Dict[str, int]    = {}   # strand_id → tick of last match
        self._archive: Deque[str]           = deque(maxlen=1024)
        self._total_registered: int         = 0
        self._total_matches: int            = 0

    def register(self, strand: DNAStrand, current_tick: int) -> None:
        """Add a sealed DNAStrand to the library."""
        if strand.strand_id in self._strands:
            return
        self._strands[strand.strand_id] = strand
        self._last_match[strand.strand_id] = current_tick
        self._archive.append(strand.strand_id)
        self._total_registered += 1

    def match_exact(self, beads: List[StrandBead], current_tick: int) -> Optional[DNAStrand]:
        """
        Return the active strand whose full bead sequence matches beads exactly.
        None if no match.
        """
        incoming_sig = ":".join(
            f"{b.constraint.name}.{b.channel.value[0].upper()}" for b in beads
        )
        for sid, strand in self._strands.items():
            if self._strand_strength(sid, current_tick) <= 0.0:
                continue
            if strand.signature() == incoming_sig:
                self._last_match[sid] = current_tick
                self._total_matches += 1
                return strand
        return None

    def match_prefix(self, beads: List[StrandBead], current_tick: int) -> List[DNAStrand]:
        """
        Return all active strands for which beads is a valid prefix.
        """
        results: List[DNAStrand] = []
        for sid, strand in self._strands.items():
            if self._strand_strength(sid, current_tick) <= 0.0:
                continue
            if strand.prefix_matches(beads):
                results.append(strand)
        return results

    def _strand_strength(self, strand_id: str, current_tick: int) -> float:
        """Influence strength ∈ [0, 1]. Zero = archived (no longer matched)."""
        last = self._last_match.get(strand_id, 0)
        ticks_unused = current_tick - last
        return max(0.0, 1.0 - ticks_unused / self._DECAY_TICKS)

    def active_strand_count(self) -> int:
        return sum(1 for sid in self._strands if self._strand_strength(sid, 0) > 0.0)

    def stats(self) -> Dict[str, int]:
        return {
            "total_registered": self._total_registered,
            "total_matches":    self._total_matches,
            "currently_stored": len(self._strands),
        }


# ===========================================================================
# SECTION 6 — FACTORY
# ===========================================================================

def make_strand_library() -> StrandLibrary:
    return StrandLibrary()

def make_strand_builder() -> StrandBuilder:
    return StrandBuilder()


# ===========================================================================
# SECTION 7 — SELF-VERIFICATION (14 checks)
# ===========================================================================

def verify_dna_strand_schema() -> Dict[str, object]:
    """
    Checks:
         1. StrandBead rejects polarity_state outside [-1, 1]
         2. StrandBead.direction_from_polarity classifies correctly
         3. StrandBead.cost() = shift_cost_coeff * |magnitude_delta|
         4. StrandBead.to_dict() contains all 7 required fields
         5. DNAStrand.append() fails after seal()
         6. DNAStrand.seal() computes strand_id deterministically
         7. DNAStrand.length = number of beads
         8. DNAStrand.cost_total = sum of bead costs
         9. DNAStrand.signature() encodes constraint+channel per bead
        10. DNAStrand.prefix_matches() correctly matches a prefix
        11. DNAStrand.prefix_matches() correctly rejects a non-prefix
        12. StrandLibrary.register() stores the strand
        13. StrandLibrary.match_exact() returns the right strand
        14. StrandLibrary: strand strength decays after _DECAY_TICKS unused
    """
    from aurora_internal.aurora_variant_promotion import VariantRecord, _compute_moral_weight
    import hashlib

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # Helper bead
    def make_bead(c=Constraint.X, ch=NonCompChannel.M, pol=0.5, delta=0.1, tick=1,
                  depth=ExistenceMode.TRANSIENT) -> StrandBead:
        return StrandBead(
            constraint=c, channel=ch,
            direction=StrandBead.direction_from_polarity(pol),
            layer_depth=depth, tick=tick, magnitude_delta=delta, polarity_state=pol,
        )

    # Helper variant
    def make_variant(vid: str = "V:test") -> VariantRecord:
        return VariantRecord(
            variant_id=vid, source_solid_id="S:test", intake_id="i_test",
            depth_reached=ExistenceMode.BOUNDED, promoted_tick=100,
            recurrence_count=10, context_variety=3, polarity_coherence_rate=0.8,
            constraint_signature="XTNB", deepest_constraint=Constraint.B,
            moral_weight=_compute_moral_weight(10), cost_reduction_factor=0.75,
        )

    # 1. StrandBead rejects bad polarity
    try:
        bad = StrandBead(Constraint.X, NonCompChannel.M, BeadDirection.POSITIVE,
                         ExistenceMode.TRANSIENT, 1, 0.1, 2.0)  # polarity > 1
        check("StrandBead rejects polarity_state > 1", False, "no exception raised")
    except ManifoldViolation:
        check("StrandBead rejects polarity_state > 1", True)

    # 2. direction_from_polarity
    check("POSITIVE for polarity=0.5",
          StrandBead.direction_from_polarity(0.5) == BeadDirection.POSITIVE)
    check("NEGATIVE for polarity=-0.5",
          StrandBead.direction_from_polarity(-0.5) == BeadDirection.NEGATIVE)
    check("NEUTRAL for polarity=0.0",
          StrandBead.direction_from_polarity(0.0) == BeadDirection.NEUTRAL)

    # 3. cost()
    bead3 = make_bead(c=Constraint.A, delta=0.1)
    expected_cost = REGISTRY.cost(Constraint.A).shift_cost_coeff * 0.1
    check("StrandBead.cost() = shift_cost_coeff * |delta|",
          abs(bead3.cost() - expected_cost) < 1e-9,
          f"expected={expected_cost:.3f} got={bead3.cost():.3f}")

    # 4. to_dict() has all 7 fields
    d4 = make_bead().to_dict()
    required_fields = {"constraint","channel","direction","layer_depth","tick","magnitude_delta","polarity_state"}
    check("StrandBead.to_dict() has all 7 required fields",
          required_fields.issubset(d4.keys()),
          f"keys={list(d4.keys())}")

    # 5. append after seal raises
    strand5 = DNAStrand(variant_id="V:t5")
    strand5.append(make_bead(tick=1))
    strand5.seal()
    try:
        strand5.append(make_bead(tick=2))
        check("DNAStrand.append() raises after seal", False, "no exception")
    except RuntimeError:
        check("DNAStrand.append() raises after seal", True)

    # 6. Seal ID is deterministic
    def make_strand_with_beads(vid: str, ticks: List[int]) -> DNAStrand:
        s = DNAStrand(variant_id=vid)
        for t in ticks:
            s.append(make_bead(tick=t))
        s.seal()
        return s
    s6a = make_strand_with_beads("V:t6", [1, 2, 3])
    s6b = make_strand_with_beads("V:t6", [1, 2, 3])
    check("Seal ID is deterministic for same bead sequence",
          s6a.strand_id == s6b.strand_id, f"a={s6a.strand_id} b={s6b.strand_id}")

    # 7. length
    s7 = make_strand_with_beads("V:t7", [1, 2, 3, 4, 5])
    check("DNAStrand.length = number of beads", s7.length == 5, str(s7.length))

    # 8. cost_total
    b8a = make_bead(c=Constraint.X, delta=0.5)
    b8b = make_bead(c=Constraint.A, delta=0.2)
    s8 = DNAStrand(variant_id="V:t8")
    s8.append(b8a); s8.append(b8b)
    s8.seal()
    expected_total = b8a.cost() + b8b.cost()
    check("DNAStrand.cost_total = sum of bead costs",
          abs(s8.cost_total - expected_total) < 1e-9,
          f"expected={expected_total:.4f} got={s8.cost_total:.4f}")

    # 9. signature encoding
    s9 = DNAStrand(variant_id="V:t9")
    s9.append(make_bead(c=Constraint.X, ch=NonCompChannel.M))
    s9.append(make_bead(c=Constraint.B, ch=NonCompChannel.P))
    s9.seal()
    sig9 = s9.signature()
    check("Signature encodes constraint+channel per bead",
          "X.M" in sig9 and "B.P" in sig9, f"sig={sig9}")

    # 10. prefix_matches: correct prefix
    template = make_strand_with_beads("V:t10", [1, 2, 3])
    prefix = [make_bead(tick=1), make_bead(tick=2)]
    check("prefix_matches() True for valid prefix",
          template.prefix_matches(prefix), f"strand_sig={template.signature()}")

    # 11. prefix_matches: rejects non-prefix
    non_prefix = [
        make_bead(c=Constraint.B, ch=NonCompChannel.D, tick=1),
        make_bead(c=Constraint.A, ch=NonCompChannel.O, tick=2),
    ]
    check("prefix_matches() False for non-matching sequence",
          not template.prefix_matches(non_prefix))

    # 12. Library register
    lib12 = make_strand_library()
    s12 = make_strand_with_beads("V:t12", [1, 2])
    lib12.register(s12, current_tick=100)
    check("StrandLibrary.register() stores strand",
          lib12.stats()["total_registered"] == 1)

    # 13. match_exact
    lib13 = make_strand_library()
    s13 = make_strand_with_beads("V:t13", [1, 2, 3])
    lib13.register(s13, current_tick=100)
    query_beads = [make_bead(tick=1), make_bead(tick=2), make_bead(tick=3)]
    match13 = lib13.match_exact(query_beads, current_tick=101)
    check("StrandLibrary.match_exact() returns correct strand",
          match13 is not None and match13.strand_id == s13.strand_id,
          f"matched={match13.strand_id if match13 else 'None'}")

    # 14. Strength decays after _DECAY_TICKS
    lib14 = make_strand_library()
    s14 = make_strand_with_beads("V:t14", [1])
    lib14.register(s14, current_tick=0)
    strength_early = lib14._strand_strength(s14.strand_id, current_tick=1)
    strength_after  = lib14._strand_strength(s14.strand_id, current_tick=StrandLibrary._DECAY_TICKS + 1)
    check("Strand strength decays to 0 after _DECAY_TICKS unused",
          strength_early > 0.0 and strength_after <= 0.0,
          f"early={strength_early:.3f} after_decay={strength_after:.3f}")

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AURORA DNA STRAND SCHEMA — STEP 14")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)

    # Demo: build a strand from simulated constraint events
    from aurora_internal.aurora_variant_promotion import VariantRecord, _compute_moral_weight
    import hashlib

    print("\n--- Demo strand construction ---")
    v = VariantRecord(
        variant_id="V:demo", source_solid_id="S:demo", intake_id="i_demo",
        depth_reached=ExistenceMode.AGENTIC, promoted_tick=50,
        recurrence_count=12, context_variety=4, polarity_coherence_rate=0.83,
        constraint_signature="XTNBA", deepest_constraint=Constraint.A,
        moral_weight=_compute_moral_weight(12), cost_reduction_factor=0.75,
    )

    events = [
        (Constraint.X, NonCompChannel.M, 0.5,  0.7,  10, ExistenceMode.TRANSIENT),
        (Constraint.T, NonCompChannel.P, 0.0,  0.2,  11, ExistenceMode.TRANSIENT),
        (Constraint.N, NonCompChannel.D, 0.3,  0.5,  13, ExistenceMode.PERSISTENT),
        (Constraint.B, NonCompChannel.M, 0.8,  0.6,  15, ExistenceMode.BOUNDED),
        (Constraint.A, NonCompChannel.O, 1.0, -0.1,  18, ExistenceMode.AGENTIC),
    ]

    builder = make_strand_builder()
    strand  = builder.build(v, events)

    print(f"  strand_id:     {strand.strand_id}")
    print(f"  length:        {strand.length}")
    print(f"  cost_total:    {strand.cost_total:.4f}")
    print(f"  polarity_arc:  {strand.polarity_arc:+.4f}")
    print(f"  depth_span:    {strand.depth_span[0].name} → {strand.depth_span[1].name}")
    print(f"  signature:     {strand.signature()}")
    print("\n  Beads:")
    for b in strand.beads:
        print(f"    {b.constraint.name}.{b.channel.value[0].upper()} "
              f"[{b.direction.value:8s}] depth={b.layer_depth.name:9s} "
              f"tick={b.tick:3d} Δmag={b.magnitude_delta:+.2f} pol={b.polarity_state:+.3f}")

    lib = make_strand_library()
    lib.register(strand, current_tick=50)
    print(f"\n  Registered to library. Active strands: {lib.stats()['total_registered']}")

    results = verify_dna_strand_schema()
    print("\n--- Self-Verification ---")
    for c in results["checks"]:
        status = "✓" if c["passed"] else "✗"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  {status} {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{'All' if passed == len(results['checks']) else passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)

