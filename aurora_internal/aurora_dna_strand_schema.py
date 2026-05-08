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
from foundational_contract import ExistenceMode
from aurora_internal.aurora_variant_promotion import VariantRecord
from aurora_constraint_stack import score_from_cost, CostDiffScore, DifferenceSnapshot


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

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_dna_strand_schema'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'DNAStrand.develop_agency': {'ability_hits': 0,
                              'alignment_gap': 0.0,
                              'alignment_target_score': 0.0,
                              'best_coupling_signature': '',
                              'constraints': ['existence', 'temporal', 'agency'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': False,
                                                   'class_target': False,
                                                   'constraint_density': 3,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': '',
                                                   'effect_density': 6,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 0,
                                                   'return_hint': 'state_record',
                                                   'signature_text': '',
                                                   'stateful_owner': True,
                                                   'target_kind': 'latent_operation',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 0.0,
                              'cross_diversity_links': 0,
                              'effect_modes': ['state_schema_change',
                                               'temporal_orchestration_change',
                                               'stateful_surface_expansion',
                                               'internal_subsystem_surface',
                                               'latent_develop_surface',
                                               'latent_a_derivative'],
                              'effect_phrases': ['would extend agency pressure handling',
                                                 'would materialize the next descendant implied by '
                                                 'aurora_internal.aurora_dna_strand_schema.DNAStrand'],
                              'genealogy_pressure': 0.0,
                              'inheritance_breach_count': 0,
                              'kind': 'latent',
                              'link_hits': 0,
                              'module': 'aurora_internal.aurora_dna_strand_schema',
                              'op_id': 'latent.aurora_internal.aurora_dna_strand_schema.DNAStrand.develop_agency',
                              'origin_activity': 0,
                              'persistence_tax_factor': 0.0,
                              'representation_score': 0.0,
                              'rewrite_bias': 'generic',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'balanced',
                                                   'adoption_count': 0,
                                                   'confidence': 0.0,
                                                   'mean_mutation_score': 0.0,
                                                   'rejected_count': 0,
                                                   'rejection_rate': 0.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 0},
                              'rewrite_profile': 'generic',
                              'signature': '',
                              'surface_score': 0.9715312500000001,
                              'sustainability_score': 0.0,
                              'target_kind': 'latent_operation'},
 'StrandBead.develop_agency': {'ability_hits': 0,
                               'alignment_gap': 0.0,
                               'alignment_target_score': 0.0,
                               'best_coupling_signature': '',
                               'constraints': ['existence', 'temporal', 'agency'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': False,
                                                    'class_target': False,
                                                    'constraint_density': 3,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': '',
                                                    'effect_density': 6,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 0,
                                                    'return_hint': 'state_record',
                                                    'signature_text': '',
                                                    'stateful_owner': True,
                                                    'target_kind': 'latent_operation',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 0.0,
                               'cross_diversity_links': 0,
                               'effect_modes': ['state_schema_change',
                                                'temporal_orchestration_change',
                                                'stateful_surface_expansion',
                                                'internal_subsystem_surface',
                                                'latent_develop_surface',
                                                'latent_a_derivative'],
                               'effect_phrases': ['would extend agency pressure handling',
                                                  'would materialize the next descendant implied '
                                                  'by '
                                                  'aurora_internal.aurora_dna_strand_schema.StrandBead'],
                               'genealogy_pressure': 0.0,
                               'inheritance_breach_count': 0,
                               'kind': 'latent',
                               'link_hits': 0,
                               'module': 'aurora_internal.aurora_dna_strand_schema',
                               'op_id': 'latent.aurora_internal.aurora_dna_strand_schema.StrandBead.develop_agency',
                               'origin_activity': 0,
                               'persistence_tax_factor': 0.0,
                               'representation_score': 0.0,
                               'rewrite_bias': 'generic',
                               'rewrite_feedback': {'acceptance_rate': 0.0,
                                                    'accepted_count': 0,
                                                    'adaptation_mode': 'balanced',
                                                    'adoption_count': 0,
                                                    'confidence': 0.0,
                                                    'mean_mutation_score': 0.0,
                                                    'rejected_count': 0,
                                                    'rejection_rate': 0.0,
                                                    'timing_credit': 0.0,
                                                    'timing_penalty': 0.0,
                                                    'trial_count': 0},
                               'rewrite_profile': 'generic',
                               'signature': '',
                               'surface_score': 0.8600000000000001,
                               'sustainability_score': 0.0,
                               'target_kind': 'latent_operation'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_dna_strand_schema.DNAStrand.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_dna_strand_schema_dnastrand_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['DNAStrand'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'DNAStrand.develop_agency':
        _aurora_bind_owner_attribute(['DNAStrand'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'DNAStrand.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['DNAStrand.develop_agency'] = {'latent_binding_active': True}

def strandbead_develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_dna_strand_schema.StrandBead.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_dna_strand_schema_strandbead_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['StrandBead'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'StrandBead.develop_agency':
        _aurora_bind_owner_attribute(['StrandBead'], 'develop_agency', _aurora_make_latent_binding('strandbead_develop_agency', 'StrandBead.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['StrandBead.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_internal.aurora_dna_strand_schema.DNAStrand.develop_agency': 'develop_agency',
 'latent.aurora_internal.aurora_dna_strand_schema.StrandBead.develop_agency': 'strandbead_develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_internal.aurora_dna_strand_schema.DNAStrand.develop_agency': {'export': 'develop_agency',
                                                                              'mode': 'latent_binding',
                                                                              'target': 'DNAStrand.develop_agency'},
 'latent.aurora_internal.aurora_dna_strand_schema.StrandBead.develop_agency': {'export': 'strandbead_develop_agency',
                                                                               'mode': 'latent_binding',
                                                                               'target': 'StrandBead.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END
