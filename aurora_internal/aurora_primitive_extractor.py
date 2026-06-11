#!/usr/bin/env python3
"""
AURORA PRIMITIVE EXTRACTOR
===========================
Module: aurora_primitive_extractor.py

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026

PURPOSE
-------
Reads the live ConstraintGenealogyLogger at any moment and surfaces:

  1. DOMINANT PAIRINGS       — which constraint pairs are producing the most
                               consistent relief across the five axes, ranked
                               by positive relief signal strength.

  2. FORMING CHAINS          — DAG paths through promoted Links, tracing the
                               evolutionary lineage from raw abilities up to
                               the deepest current compound primitives.
                               Expressed as readable ancestry chains:
                               "A:COMMIT → B:ENCAPSULATE → L:abc123 → L:def456"

  3. CURRENT VOCABULARY      — the universe's discovered primitive vocabulary
                               at this moment: which axis combinations dominate,
                               which depth layers are populated, what emergent
                               tags are present, and what the constraint
                               grammar looks like so far.

  4. OUTCOME BIAS DISTANCE   — you declare a target bias as a 5-axis weight
                               vector. The extractor computes the current
                               universe's "center of gravity" in that space
                               and returns the distance + axis gap + steering
                               suggestion — without injecting the result.
                               The physics still has to get there on its own.

DOCTRINE
--------
  This module READS the fossil record. It does not write to it.
  It does not inject traces, does not modify PairStats, does not
  touch the chamber. It is a lens, not a hand.

  The outcome bias distance tells you how far away you are and
  which axis to pressure next. It does not move you there.
  That's what steering actions are for.

USAGE
-----
    from aurora_internal.aurora_primitive_extractor import PrimitiveExtractor, OutcomeBias

    extractor = PrimitiveExtractor(genealogy)

    # See what's forming
    extractor.report()

    # Declare where you want the universe to end up
    bias = OutcomeBias(
        axis_weights={"A": 0.5, "B": 0.3, "X": 0.2, "T": 0.0, "N": 0.0},
        label="agency-boundary dominance",
    )
    gap = extractor.bias_distance(bias)
    print(gap.steering_suggestion)

    # Export the primitive vocabulary as JSON
    vocab = extractor.vocabulary()
    import json; print(json.dumps(vocab, indent=2))

INTEGRATION WITH aurora_runtime.py
------------------------------------
    extractor = PrimitiveExtractor(runtime.systems.genealogy)
    extractor.report()                      # full print
    extractor.pairings(top_n=10)            # top pairings
    extractor.chains(max_chains=5)          # deepest chain paths
    extractor.bias_distance(my_bias).show() # distance to goal
"""

from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Set, Tuple

# =============================================================================
# AXIS CONSTANTS
# =============================================================================

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

_AXIS_NAMES: Dict[str, str] = {
    "X": "Existence (Admissibility)",
    "T": "Time (Sequence)",
    "N": "Energy (Cost)",
    "B": "Boundary (Topology)",
    "A": "Agency (Action)",
}

_AXIS_SHORT: Dict[str, str] = {
    "X": "Existence",
    "T": "Time",
    "N": "Energy",
    "B": "Boundary",
    "A": "Agency",
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _norm(vec: Dict[str, float]) -> Dict[str, float]:
    """Normalize a 5-axis dict to sum=1 (safe — returns zeros if all zero)."""
    total = sum(abs(v) for v in vec.values())
    if total < 1e-12:
        return {a: 0.0 for a in AXES}
    return {a: vec.get(a, 0.0) / total for a in AXES}


def _l2(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Euclidean distance between two 5-axis vectors."""
    return math.sqrt(sum((a.get(ax, 0.0) - b.get(ax, 0.0)) ** 2 for ax in AXES))


def _cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity. Returns 0 if either vector is zero."""
    dot = sum(a.get(ax, 0.0) * b.get(ax, 0.0) for ax in AXES)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if mag_a < 1e-12 or mag_b < 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


# =============================================================================
# OUTCOME BIAS  — what you're trying to evolve toward
# =============================================================================

@dataclass
class OutcomeBias:
    """
    A declared target state for the universe's primitive distribution.

    axis_weights : Dict[str, float]
        Target proportion of relief activity per axis.
        Does NOT need to sum to 1 — it will be normalized internally.
        Zero weight means you don't care about that axis.

        Example — agency+boundary dominant:
            {"A": 0.5, "B": 0.3, "X": 0.2, "T": 0.0, "N": 0.0}

        Example — time+energy process-heavy:
            {"T": 0.4, "N": 0.4, "B": 0.2, "X": 0.0, "A": 0.0}

        Example — balanced across all five:
            {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}

    label : str
        Human name for this bias target. Used in reports.

    min_depth : int
        If set, primitives must reach at least this DAG depth before the
        bias is considered satisfiable. Default 1 (any promoted link counts).

    required_tags : List[str]
        If set, at least one promoted link must carry all of these effect
        tags before the bias is satisfiable. Optional.
    """
    axis_weights: Dict[str, float]
    label: str = "unnamed bias"
    min_depth: int = 1
    required_tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Fill missing axes with zero
        for ax in AXES:
            if ax not in self.axis_weights:
                self.axis_weights[ax] = 0.0

    def normalized(self) -> Dict[str, float]:
        return _norm(self.axis_weights)


# =============================================================================
# PAIRING RESULT
# =============================================================================

@dataclass
class PairingResult:
    """
    One ranked constraint pairing from the pair stats accumulator.
    """
    left_id: str
    right_id: str
    count: int
    dominant_axis: str
    mean_pos_relief: Dict[str, float]   # positive-only mean per axis
    pos_fraction: Dict[str, float]      # fraction of ticks with positive relief
    mean_cost: Dict[str, float]
    mean_x_risk: float
    promoted: bool                      # True if this pair became a Link
    link_id: Optional[str]              # the Link id if promoted

    @property
    def relief_score(self) -> float:
        """Single scalar signal strength — weighted positive relief."""
        weights = {"X": 0.30, "T": 0.15, "N": 0.15, "B": 0.20, "A": 0.20}
        return sum(weights.get(a, 0.0) * self.mean_pos_relief.get(a, 0.0)
                   for a in AXES)

    def describe(self) -> str:
        dom = _AXIS_SHORT.get(self.dominant_axis, self.dominant_axis)
        promo = f"→ {self.link_id}" if self.promoted else "(not yet promoted)"
        return (f"{self.left_id} + {self.right_id}  "
                f"[{dom}]  count={self.count}  "
                f"score={self.relief_score:.6f}  {promo}")


# =============================================================================
# CHAIN PATH
# =============================================================================

@dataclass
class ChainPath:
    """
    One evolutionary lineage path through the DAG.

    root_ids : list of raw ability IDs at the base
    link_ids : ordered list of Link IDs from depth-1 up to deepest
    full_path : human-readable string of the full ancestry
    max_depth : deepest Link depth in this path
    dominant_axis : axis that dominates across all links in the path
    total_count : sum of observation counts across all links in path
    total_relief : sum of dominant-axis relief across all links in path
    """
    root_ids: List[str]
    link_ids: List[str]
    full_path: str
    max_depth: int
    dominant_axis: str
    total_count: int
    total_relief: float


# =============================================================================
# VOCABULARY
# =============================================================================

@dataclass
class UniverseVocabulary:
    """
    The universe's current primitive vocabulary — a structured snapshot of
    what has been discovered so far through constraint physics.
    """
    # Layer 0: raw abilities that have appeared in relief events
    active_abilities: List[str]

    # Layer 1+: promoted Links, grouped by depth
    links_by_depth: Dict[int, List[str]]          # depth → [link_ids]

    # Axis distribution of promoted links
    axis_distribution: Dict[str, int]             # axis → link count

    # Normalized axis weight vector (current center of gravity)
    axis_center: Dict[str, float]                 # axis → fractional weight

    # Tag cloud from all promoted links
    tag_frequencies: Dict[str, int]               # tag → occurrence count

    # Deepest known depth
    max_depth: int

    # Total promoted links
    total_links: int

    # Total relief events observed
    total_relief_events: int

    # Top 5 most-observed ability IDs (raw frequency in relief events)
    most_active_abilities: List[Tuple[str, int]]  # [(ability_id, count)]

    # Snapshot timestamp
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_abilities": self.active_abilities,
            "links_by_depth": {str(k): v for k, v in self.links_by_depth.items()},
            "axis_distribution": self.axis_distribution,
            "axis_center": {a: round(v, 6) for a, v in self.axis_center.items()},
            "tag_frequencies": self.tag_frequencies,
            "max_depth": self.max_depth,
            "total_links": self.total_links,
            "total_relief_events": self.total_relief_events,
            "most_active_abilities": self.most_active_abilities,
            "timestamp": self.timestamp,
        }


# =============================================================================
# BIAS DISTANCE RESULT
# =============================================================================

@dataclass
class BiasDistanceResult:
    """
    Result of measuring the current universe's distance from an OutcomeBias.
    """
    bias: OutcomeBias

    # Current universe axis center of gravity (normalized)
    current_center: Dict[str, float]

    # Normalized target from OutcomeBias
    target_center: Dict[str, float]

    # Raw Euclidean distance in 5-axis space (0.0 = perfect alignment)
    euclidean_distance: float

    # Cosine similarity (1.0 = perfect alignment, 0.0 = orthogonal)
    cosine_similarity: float

    # Per-axis gap: target - current (positive = underrepresented)
    axis_gap: Dict[str, float]

    # Axes most underrepresented relative to target
    underrepresented: List[str]   # sorted by gap descending

    # Axes most overrepresented relative to target
    overrepresented: List[str]    # sorted by excess descending

    # Whether all min_depth + required_tags conditions are met
    structurally_satisfiable: bool
    satisfiable_reason: str

    # What to do next (steering suggestion — no shortcuts)
    steering_suggestion: str

    # Whether the current state is already within this distance of the target
    within_threshold: bool
    threshold: float = 0.10       # default convergence threshold

    def show(self) -> None:
        """Print a human-readable distance report."""
        print()
        print(f"  OUTCOME BIAS DISTANCE — '{self.bias.label}'")
        print(f"  {'─'*54}")
        print(f"  Euclidean distance  : {self.euclidean_distance:.6f}  "
              f"({'CONVERGED' if self.within_threshold else 'not converged'})")
        print(f"  Cosine similarity   : {self.cosine_similarity:.4f}  "
              f"(1.0 = perfect)")
        print()
        print(f"  Current center      : "
              + "  ".join(f"{a}={self.current_center.get(a,0):.3f}" for a in AXES))
        print(f"  Target center       : "
              + "  ".join(f"{a}={self.target_center.get(a,0):.3f}" for a in AXES))
        print()
        print(f"  Per-axis gap (target - current):")
        for ax in AXES:
            gap = self.axis_gap.get(ax, 0.0)
            bar = "▲" if gap > 0.01 else ("▼" if gap < -0.01 else "·")
            print(f"    {ax} ({_AXIS_SHORT[ax]:<10}) {bar}  {gap:+.4f}")
        print()
        print(f"  Underrepresented : {', '.join(self.underrepresented) or 'none'}")
        print(f"  Overrepresented  : {', '.join(self.overrepresented) or 'none'}")
        print()
        print(f"  Structurally satisfiable : {self.structurally_satisfiable}")
        if not self.structurally_satisfiable:
            print(f"  Reason : {self.satisfiable_reason}")
        print()
        print(f"  STEERING SUGGESTION:")
        for line in self.steering_suggestion.splitlines():
            print(f"    {line}")
        print()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bias_label": self.bias.label,
            "euclidean_distance": round(self.euclidean_distance, 8),
            "cosine_similarity": round(self.cosine_similarity, 6),
            "current_center": {a: round(v, 6) for a, v in self.current_center.items()},
            "target_center": {a: round(v, 6) for a, v in self.target_center.items()},
            "axis_gap": {a: round(v, 6) for a, v in self.axis_gap.items()},
            "underrepresented": self.underrepresented,
            "overrepresented": self.overrepresented,
            "structurally_satisfiable": self.structurally_satisfiable,
            "within_threshold": self.within_threshold,
            "steering_suggestion": self.steering_suggestion,
        }


# =============================================================================
# AXIS → STEERING ACTIONS MAP
# =============================================================================

# For each axis, the named actions (from DEFAULT_ACTION_CYCLE) that feed it
# most directly. Used to generate steering suggestions without hard-coding outcomes.
_AXIS_TO_ACTIONS: Dict[str, List[str]] = {
    "X": ["admit_state", "resolve", "full_assert", "commit_choice"],
    "T": ["defer_work", "batch_process", "reorder", "resolve"],
    "N": ["reuse_cache", "defer_work", "batch_process", "spend_energy"],
    "B": ["seal_boundary", "separate", "reuse_cache", "batch_process", "pure_boundary"],
    "A": ["commit_choice", "release_outlet", "spend_energy", "full_assert",
          "full_commit", "pure_agency"],
}


# =============================================================================
# PRIMITIVE EXTRACTOR — the main class
# =============================================================================

class PrimitiveExtractor:
    """
    Reads a live ConstraintGenealogyLogger and extracts the discovered
    primitive structure of the universe at this moment.

    This is a read-only lens. It does not modify the genealogy.

    Parameters
    ----------
    genealogy : ConstraintGenealogyLogger
        The live logger instance from aurora_runtime or run_chain.
    """

    def __init__(self, genealogy: Any) -> None:
        self._g = genealogy

    # ------------------------------------------------------------------
    # 1. DOMINANT PAIRINGS
    # ------------------------------------------------------------------

    def pairings(self,
                 top_n: int = 20,
                 min_count: int = 5,
                 print_results: bool = True) -> List[PairingResult]:
        """
        Rank all observed constraint pairings by relief signal strength.

        Parameters
        ----------
        top_n     : how many top pairings to return
        min_count : only include pairs seen at least this many times
        print_results : if True, print a formatted table

        Returns list of PairingResult sorted by relief_score descending.
        """
        pair_stats  = getattr(self._g, "_pair_stats", {})
        links       = getattr(self._g, "links", {})
        links_by_parents = getattr(self._g, "_links_by_parents", {})

        results: List[PairingResult] = []

        for (left_id, right_id), ps in pair_stats.items():
            if ps.count < min_count:
                continue

            mr_pos   = ps.mean_pos_relief()
            pf       = ps.pos_fraction()
            mc       = ps.mean_cost()
            mx_risk  = ps.mean_x_risk_val()

            # Dominant axis by positive relief
            dominant = max(AXES, key=lambda a: mr_pos.get(a, 0.0))

            key = (left_id, right_id)
            link_id = links_by_parents.get(key)

            result = PairingResult(
                left_id=left_id,
                right_id=right_id,
                count=ps.count,
                dominant_axis=dominant,
                mean_pos_relief={a: mr_pos.get(a, 0.0) for a in AXES},
                pos_fraction={a: pf.get(a, 0.0) for a in AXES},
                mean_cost={a: mc.get(a, 0.0) for a in AXES},
                mean_x_risk=mx_risk,
                promoted=link_id is not None,
                link_id=link_id,
            )
            results.append(result)

        results.sort(key=lambda r: r.relief_score, reverse=True)
        top = results[:top_n]

        if print_results:
            print()
            print(f"  TOP CONSTRAINT PAIRINGS  (min_count={min_count})")
            print(f"  {'─'*68}")
            if not top:
                print("  (no pairs with sufficient observations yet)")
            for i, r in enumerate(top, 1):
                promo = f"  ✓ {r.link_id}" if r.promoted else ""
                ax = _AXIS_SHORT.get(r.dominant_axis, r.dominant_axis)
                print(f"  {i:>2}. {r.left_id} + {r.right_id}")
                print(f"       [{ax}]  count={r.count}  "
                      f"score={r.relief_score:.6f}  "
                      f"x_risk={r.mean_x_risk:.4f}{promo}")
            print()

        return top

    # ------------------------------------------------------------------
    # 2. FORMING CHAINS  — DAG path extraction
    # ------------------------------------------------------------------

    def chains(self,
               max_chains: int = 10,
               min_depth: int = 1,
               print_results: bool = True) -> List[ChainPath]:
        """
        Extract the deepest evolutionary lineage paths from the DAG.

        Traces each promoted Link back to its raw ability roots and
        returns the full ancestry as a readable chain.

        Parameters
        ----------
        max_chains : how many chains to return (deepest first)
        min_depth  : only include chains with at least this many link layers
        print_results : if True, print formatted chains

        Returns list of ChainPath sorted by max_depth descending.
        """
        links = getattr(self._g, "links", {})
        if not links:
            if print_results:
                print("\n  (no chains yet — run chain_burst() to build the DAG)\n")
            return []

        chain_paths: List[ChainPath] = []

        # Find the deepest links — these are the tips of evolutionary chains
        deepest_links = sorted(
            links.values(),
            key=lambda l: l.depth,
            reverse=True,
        )[:max_chains * 3]  # oversample, filter by min_depth after

        seen_roots: Set[FrozenSet[str]] = set()

        for tip_link in deepest_links:
            if tip_link.depth < min_depth:
                continue

            # Walk ancestry to build the full path
            path_nodes: List[str] = []
            root_abilities: List[str] = []
            link_sequence: List[str] = []

            self._walk_ancestry(tip_link.id, links,
                                path_nodes, root_abilities, link_sequence,
                                visited=set())

            root_key = frozenset(root_abilities)
            if root_key in seen_roots:
                continue
            seen_roots.add(root_key)

            # Dominant axis across the chain
            axis_counts: Dict[str, int] = defaultdict(int)
            total_count = 0
            total_relief = 0.0
            for lid in link_sequence:
                lnk = links.get(lid)
                if lnk:
                    ax = lnk.dominant_relief_axis or "X"
                    axis_counts[ax] += lnk.count
                    total_count += lnk.count
                    total_relief += lnk.mean_relief.get(ax, 0.0)

            dom_axis = max(axis_counts, key=axis_counts.get) if axis_counts else "X"

            # Build human-readable path string
            path_str = self._format_path(root_abilities, link_sequence, links)

            cp = ChainPath(
                root_ids=root_abilities,
                link_ids=link_sequence,
                full_path=path_str,
                max_depth=tip_link.depth,
                dominant_axis=dom_axis,
                total_count=total_count,
                total_relief=total_relief,
            )
            chain_paths.append(cp)

            if len(chain_paths) >= max_chains:
                break

        chain_paths.sort(key=lambda c: c.max_depth, reverse=True)

        if print_results:
            print()
            print(f"  FORMING EVOLUTIONARY CHAINS  (top {len(chain_paths)})")
            print(f"  {'─'*68}")
            if not chain_paths:
                print("  (no chains of sufficient depth yet)")
            for i, cp in enumerate(chain_paths, 1):
                ax = _AXIS_SHORT.get(cp.dominant_axis, cp.dominant_axis)
                print(f"  Chain {i}  depth={cp.max_depth}  "
                      f"dominant={ax}  count={cp.total_count}")
                print(f"    {cp.full_path}")
                print()

        return chain_paths

    # ------------------------------------------------------------------
    # 3. CURRENT VOCABULARY
    # ------------------------------------------------------------------

    def vocabulary(self,
                   print_results: bool = True) -> UniverseVocabulary:
        """
        Build the current primitive vocabulary of the universe.

        Surveys the fossil record to find which abilities have been
        active, how links distribute across axes and depths,
        and what tags have emerged.

        Returns a UniverseVocabulary dataclass (also serializable via .to_dict()).
        """
        links          = getattr(self._g, "links", {})
        abilities      = getattr(self._g, "abilities", {})
        event_log      = getattr(self._g, "_event_log", deque())
        relief_count   = getattr(self._g, "relief_event_count", 0)

        # Active abilities — those that appeared in at least one relief event
        ability_count: Dict[str, int] = defaultdict(int)
        for record in event_log:
            trace = getattr(record, "trace", [])
            for item in trace:
                if getattr(item, "kind", "") == "ABILITY":
                    ability_count[item.id] += 1

        active_abilities = sorted(ability_count.keys())
        most_active = sorted(ability_count.items(), key=lambda x: x[1], reverse=True)[:5]

        # Links by depth
        links_by_depth: Dict[int, List[str]] = defaultdict(list)
        axis_distribution: Dict[str, int] = defaultdict(int)
        tag_frequencies: Dict[str, int] = defaultdict(int)
        max_depth = 0

        for lnk in links.values():
            links_by_depth[lnk.depth].append(lnk.id)
            ax = lnk.dominant_relief_axis or "X"
            axis_distribution[ax] += 1
            max_depth = max(max_depth, lnk.depth)
            for tag in getattr(lnk, "tags", []):
                tag_frequencies[tag] += 1

        # Axis center of gravity (weighted by link count on that axis)
        axis_center_raw: Dict[str, float] = {a: 0.0 for a in AXES}
        total_links = len(links)
        if total_links > 0:
            for ax in AXES:
                axis_center_raw[ax] = axis_distribution.get(ax, 0) / total_links
        axis_center = _norm(axis_center_raw) if total_links > 0 else {a: 0.0 for a in AXES}

        vocab = UniverseVocabulary(
            active_abilities=active_abilities,
            links_by_depth=dict(links_by_depth),
            axis_distribution=dict(axis_distribution),
            axis_center=axis_center,
            tag_frequencies=dict(sorted(tag_frequencies.items(),
                                        key=lambda x: x[1], reverse=True)),
            max_depth=max_depth,
            total_links=total_links,
            total_relief_events=relief_count,
            most_active_abilities=most_active,
        )

        if print_results:
            self._print_vocabulary(vocab)

        return vocab

    # ------------------------------------------------------------------
    # 4. OUTCOME BIAS DISTANCE
    # ------------------------------------------------------------------

    def bias_distance(self,
                      bias: OutcomeBias,
                      threshold: float = 0.10,
                      print_results: bool = True) -> BiasDistanceResult:
        """
        Measure the current universe's distance from a declared OutcomeBias.

        Parameters
        ----------
        bias      : the OutcomeBias you're steering toward
        threshold : euclidean distance below which we consider it converged
        print_results : if True, call result.show() automatically

        Returns BiasDistanceResult.
        """
        vocab = self.vocabulary(print_results=False)
        links = getattr(self._g, "links", {})

        current_center = vocab.axis_center
        target_center  = bias.normalized()

        # Euclidean distance
        dist = _l2(current_center, target_center)

        # Cosine similarity
        cos_sim = _cosine_sim(current_center, target_center)

        # Per-axis gap: target - current (positive = underrepresented)
        axis_gap: Dict[str, float] = {
            a: target_center.get(a, 0.0) - current_center.get(a, 0.0)
            for a in AXES
        }

        # Under/over represented
        underrepresented = sorted(
            [a for a in AXES if axis_gap[a] > 0.01],
            key=lambda a: axis_gap[a], reverse=True
        )
        overrepresented = sorted(
            [a for a in AXES if axis_gap[a] < -0.01],
            key=lambda a: axis_gap[a]
        )

        # Structural satisfiability check
        satisfiable = True
        reason = "ok"

        if vocab.max_depth < bias.min_depth:
            satisfiable = False
            reason = (f"max DAG depth is {vocab.max_depth}, "
                      f"bias requires {bias.min_depth}. "
                      f"Keep running chain_burst() to deepen the DAG.")

        if bias.required_tags:
            found_tags = set(vocab.tag_frequencies.keys())
            missing = [t for t in bias.required_tags if t not in found_tags]
            if missing:
                satisfiable = False
                reason = (f"required tags not yet in vocabulary: {missing}. "
                          f"Apply actions that involve those constraint effects.")

        # Steering suggestion — tells you WHAT to inject, not what will happen
        suggestion_lines = self._build_steering_suggestion(
            underrepresented, overrepresented, axis_gap, vocab, bias
        )

        result = BiasDistanceResult(
            bias=bias,
            current_center=current_center,
            target_center=target_center,
            euclidean_distance=dist,
            cosine_similarity=cos_sim,
            axis_gap=axis_gap,
            underrepresented=underrepresented,
            overrepresented=overrepresented,
            structurally_satisfiable=satisfiable,
            satisfiable_reason=reason,
            steering_suggestion="\n".join(suggestion_lines),
            within_threshold=dist <= threshold,
            threshold=threshold,
        )

        if print_results:
            result.show()

        return result

    # ------------------------------------------------------------------
    # 5. FULL REPORT  — everything at once
    # ------------------------------------------------------------------

    def report(self,
               top_pairings: int = 10,
               top_chains: int = 5,
               bias: Optional[OutcomeBias] = None) -> Dict[str, Any]:
        """
        Print a full primitive extraction report:
          - Vocabulary summary
          - Top pairings
          - Forming chains
          - Bias distance (if bias provided)

        Returns a dict of all extracted data for programmatic use.
        """
        print()
        print("═" * 70)
        print("  AURORA PRIMITIVE EXTRACTOR")
        print("  Authors: Sunni (Sir) Morningstar and Cael Devo")
        print("═" * 70)

        vocab   = self.vocabulary(print_results=True)
        pairs   = self.pairings(top_n=top_pairings, print_results=True)
        ch      = self.chains(max_chains=top_chains, print_results=True)

        bias_result_dict: Optional[Dict[str, Any]] = None
        if bias is not None:
            br = self.bias_distance(bias, print_results=True)
            bias_result_dict = br.to_dict()

        return {
            "vocabulary": vocab.to_dict(),
            "top_pairings": [
                {
                    "left": p.left_id, "right": p.right_id,
                    "dominant_axis": p.dominant_axis,
                    "count": p.count,
                    "relief_score": round(p.relief_score, 8),
                    "promoted": p.promoted,
                    "link_id": p.link_id,
                }
                for p in pairs
            ],
            "chains": [
                {
                    "full_path": c.full_path,
                    "max_depth": c.max_depth,
                    "dominant_axis": c.dominant_axis,
                    "total_count": c.total_count,
                }
                for c in ch
            ],
            "bias_distance": bias_result_dict,
        }

    # ------------------------------------------------------------------
    # CONVENIENCE: export snapshot to JSON file
    # ------------------------------------------------------------------

    def export(self,
               path: str,
               bias: Optional[OutcomeBias] = None) -> None:
        """
        Export the full primitive snapshot to a JSON file.

        Parameters
        ----------
        path  : file path to write (will overwrite)
        bias  : optional OutcomeBias to include distance measurement
        """
        data = self.report(print_results=False,
                           bias=bias)
        data["exported_at"] = time.time()
        data["run_id"] = getattr(self._g, "run_id", "unknown")

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

        print(f"  [EXTRACTOR] Snapshot exported → {path}")

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _walk_ancestry(self,
                       node_id: str,
                       links: Dict[str, Any],
                       path_nodes: List[str],
                       root_abilities: List[str],
                       link_sequence: List[str],
                       visited: Set[str]) -> None:
        """
        Recursively walk the DAG from node_id toward its ability roots.
        Populates path_nodes, root_abilities, and link_sequence in place.
        """
        if node_id in visited:
            return
        visited.add(node_id)

        lnk = links.get(node_id)
        if lnk is None:
            # It's a raw ability — it's a root
            if node_id not in root_abilities:
                root_abilities.append(node_id)
            return

        # It's a Link — record it and walk parents
        if node_id not in link_sequence:
            link_sequence.append(node_id)

        for parent_id in lnk.parents:
            self._walk_ancestry(parent_id, links,
                                path_nodes, root_abilities, link_sequence,
                                visited)

    def _format_path(self,
                     roots: List[str],
                     link_sequence: List[str],
                     links: Dict[str, Any]) -> str:
        """
        Build a human-readable chain string.
        Sorts links by depth so the path reads shallow → deep.
        """
        if not roots and not link_sequence:
            return "(empty)"

        # Sort links shallow → deep
        sorted_links = sorted(
            link_sequence,
            key=lambda lid: links[lid].depth if lid in links else 0
        )

        # Abbreviate link IDs
        def _abbrev(lid: str) -> str:
            if lid.startswith("L:"):
                return f"L:{lid[2:8]}"
            return lid

        parts: List[str] = []

        # Show unique roots
        for r in sorted(set(roots)):
            parts.append(r)

        # Arrow into first link, then chain
        for lid in sorted_links:
            depth = links[lid].depth if lid in links else "?"
            ax = links[lid].dominant_relief_axis if lid in links else "?"
            parts.append(f"→ {_abbrev(lid)}(d{depth},{ax})")

        return "  ".join(parts)

    def _print_vocabulary(self, v: UniverseVocabulary) -> None:
        """Print formatted vocabulary summary."""
        print()
        print(f"  UNIVERSE VOCABULARY  (tick snapshot)")
        print(f"  {'─'*54}")
        print(f"  Total promoted links   : {v.total_links}")
        print(f"  Total relief events    : {v.total_relief_events}")
        print(f"  Max DAG depth          : {v.max_depth}")
        print()

        print(f"  Axis distribution (links by dominant axis):")
        for ax in AXES:
            count = v.axis_distribution.get(ax, 0)
            pct   = (count / v.total_links * 100) if v.total_links > 0 else 0.0
            bar   = "█" * int(pct / 5)
            print(f"    {ax} {_AXIS_SHORT[ax]:<10}  {count:>4}  "
                  f"({pct:5.1f}%)  {bar}")
        print()

        print(f"  Axis center of gravity (normalized):")
        print(f"    " + "  ".join(
            f"{a}={v.axis_center.get(a, 0):.3f}" for a in AXES
        ))
        print()

        print(f"  Depth layer population:")
        for depth in sorted(v.links_by_depth.keys()):
            ids = v.links_by_depth[depth]
            print(f"    Depth {depth} : {len(ids):>4} link(s)")
        print()

        if v.tag_frequencies:
            print(f"  Top emergent tags:")
            top_tags = list(v.tag_frequencies.items())[:10]
            for tag, freq in top_tags:
                print(f"    {tag:<28} {freq}")
        print()

        if v.most_active_abilities:
            print(f"  Most active raw abilities in relief events:")
            for ab_id, cnt in v.most_active_abilities:
                print(f"    {ab_id:<28} {cnt}x")
        print()

    def _build_steering_suggestion(self,
                                   underrepresented: List[str],
                                   overrepresented: List[str],
                                   axis_gap: Dict[str, float],
                                   vocab: UniverseVocabulary,
                                   bias: OutcomeBias) -> List[str]:
        """
        Build steering suggestion lines.
        Tells you which actions to inject — not what results to expect.
        """
        lines: List[str] = []

        if not underrepresented:
            lines.append("Current axis distribution already aligns with bias.")
            lines.append("Continue running chain_burst() to deepen the DAG.")
            return lines

        lines.append(f"To steer toward '{bias.label}':")
        lines.append("")

        for ax in underrepresented[:3]:
            gap = axis_gap.get(ax, 0.0)
            ax_name = _AXIS_NAMES.get(ax, ax)
            actions = _AXIS_TO_ACTIONS.get(ax, [])
            lines.append(f"  [{ax}] {ax_name}  — underweight by {gap:.3f}")
            if actions:
                lines.append(f"      Inject: {', '.join(actions[:3])}")
                lines.append(f"      Command: inject {actions[0]}  OR  "
                             f"custom my_{ax.lower()} {ax}")
            lines.append("")

        if overrepresented:
            lines.append(f"  Overrepresented axes (reduce pressure here): "
                         f"{', '.join(overrepresented)}")
            lines.append(f"  Reduce frequency of: " + ", ".join(
                act for ax in overrepresented
                for act in _AXIS_TO_ACTIONS.get(ax, [])[:2]
            ))
            lines.append("")

        # Depth advice
        if vocab.max_depth < bias.min_depth:
            lines.append(f"  DAG depth {vocab.max_depth} < required {bias.min_depth}.")
            lines.append(f"  Run: chain <N>  with N ≥ 10,000 to deepen the genealogy.")
            lines.append("")

        lines.append("Remember: you inject pressure. The physics produces relief.")
        lines.append("The universe arrives at the bias through its own constraint physics.")

        return lines


# =============================================================================
# STANDALONE ENTRY POINT  — for testing without a live runtime
# =============================================================================

def _demo() -> None:
    """
    Minimal self-demo. Boots the minimum required stack, runs a burst,
    then runs the extractor on the result.
    """
    import sys
    import os

    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)

    print("=" * 70)
    print("  AURORA PRIMITIVE EXTRACTOR — demo mode")
    print("  Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)

    try:
        from foundational_contract import FoundationalContract
        from aurora_ivm import IVMLattice
        from aurora_internal.aurora_evolution_chamber import EvolutionaryChamber, ActionTrace, WorldConstants
        from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig
    except ImportError as e:
        print(f"\n[ERROR] Cannot import required modules: {e}")
        print("Run from the project directory alongside the Aurora stack.\n")
        return

    run_id = f"extractor_demo_{int(time.time())}"
    out    = "extractor_demo_output"
    os.makedirs(out, exist_ok=True)

    contract  = FoundationalContract()
    lattice   = IVMLattice(contract)
    genealogy = ConstraintGenealogyLogger(run_id=run_id, config=GenealogyConfig(),
                                          output_dir=out)
    chamber   = EvolutionaryChamber(lattice=lattice, genealogy=genealogy,
                                    run_id=run_id, output_dir=out)

    # Sample action cycle
    cycle = [
        ActionTrace("communicate",   frozenset({"agency","boundary","temporal"}),   meta={}),
        ActionTrace("admit_state",   frozenset({"existence","agency"}),              meta={}),
        ActionTrace("seal_boundary", frozenset({"boundary","existence"}),            meta={}),
        ActionTrace("defer_work",    frozenset({"temporal","energy"}),               meta={}),
        ActionTrace("spend_energy",  frozenset({"energy","agency"}),                 meta={}),
        ActionTrace("full_assert",   frozenset({"existence","temporal","energy",
                                               "boundary","agency"}),               meta={}),
    ]

    print(f"\nRunning 5,000 ticks...")
    for i in range(5000):
        chamber.tick(cycle[i % len(cycle)])

    print(f"Done. Building primitive report...\n")

    extractor = PrimitiveExtractor(genealogy)

    # Declare an outcome bias
    bias = OutcomeBias(
        axis_weights={"A": 0.45, "B": 0.30, "X": 0.15, "T": 0.05, "N": 0.05},
        label="agency-boundary dominant",
        min_depth=2,
    )

    extractor.report(top_pairings=8, top_chains=4, bias=bias)

    # Export snapshot
    extractor.export(os.path.join(out, "primitive_snapshot.json"), bias=bias)

    genealogy.flush_files()
    print(f"\nOutput written to: {out}/\n")


if __name__ == "__main__":
    _demo()

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_primitive_extractor'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'PrimitiveExtractor.chains': {'ability_hits': 19,
                               'alignment_gap': 0.391,
                               'alignment_target_score': 1.023,
                               'best_coupling_signature': 'T^2*B^1',
                               'constraints': ['temporal'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 1,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': 'Extract the deepest evolutionary '
                                                                'lineage paths from the DAG.',
                                                    'effect_density': 2,
                                                    'kwonly_args': 0,
                                                    'optional_args': 3,
                                                    'required_args': 0,
                                                    'return_hint': 'List[ChainPath]',
                                                    'signature_text': "(self, max_chains: 'int' = "
                                                                      "10, min_depth: 'int' = 1, "
                                                                      "print_results: 'bool' = "
                                                                      "True) -> 'List[ChainPath]'",
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 2,
                               'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                               'effect_phrases': ['function growth reflected through '
                                                  'aurora_internal.aurora_primitive_extractor',
                                                  'PrimitiveExtractor.chains changed downstream '
                                                  'system pressure'],
                               'genealogy_pressure': 0.809108,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 36,
                               'module': 'aurora_internal.aurora_primitive_extractor',
                               'op_id': 'aurora_internal.aurora_primitive_extractor.PrimitiveExtractor.chains',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.955393,
                               'representation_score': 0.519331,
                               'rewrite_bias': 'generic',
                               'rewrite_feedback': {'acceptance_rate': 0.0,
                                                    'accepted_count': 0,
                                                    'adaptation_mode': 'conservative',
                                                    'adoption_count': 0,
                                                    'confidence': 0.36,
                                                    'mean_mutation_score': 0.25,
                                                    'rejected_count': 2,
                                                    'rejection_rate': 1.0,
                                                    'timing_credit': 0.0,
                                                    'timing_penalty': 0.0,
                                                    'trial_count': 2},
                               'rewrite_profile': 'generic',
                               'signature': 'T^2*B^1',
                               'surface_score': 0.632,
                               'sustainability_score': 0.405355,
                               'target_kind': 'function'}}

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

def chains_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_primitive_extractor.PrimitiveExtractor.chains', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains')(payload=payload, **kwargs)

if _aurora_get_target(['PrimitiveExtractor', 'chains']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['PrimitiveExtractor.chains'] = _aurora_get_target(['PrimitiveExtractor', 'chains'])
    _aurora_assign_target(['PrimitiveExtractor', 'chains'], _aurora_make_override('chains_evolved', 'PrimitiveExtractor.chains'))
    _AURORA_NATIVE_EVOLVED_LAST['PrimitiveExtractor.chains'] = {'alignment_gap': 0.391, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_primitive_extractor.PrimitiveExtractor.chains': 'chains_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_primitive_extractor.PrimitiveExtractor.chains': {'export': 'chains_evolved',
                                                                          'mode': 'callable_override',
                                                                          'target': 'PrimitiveExtractor.chains'}}
# AURORA_EVOLVED_NATIVE_END
