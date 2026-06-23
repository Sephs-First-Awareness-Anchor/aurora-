#!/usr/bin/env python3
"""
AURORA MANIFOLD DIRECTORY READER  (runtime)
=============================================
Module: aurora_manifold_directory_reader.py
Layer: Constraint Ontology — Noncomp Manifold Runtime Access

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: April 2026

PURPOSE
-------
Aurora's runtime interface to the pre-compiled manifold directory.

She never recomputes. She never holds more than one manifold in memory
at a time. She reads from disk, uses it, and releases it.

MEMORY MODEL
------------
    Always in memory:
        ManifoldDirectory (the index) — ~125 entries, ~50KB

    Loaded on demand, released after use:
        One NoncompManifold at a time — ~100KB (no semantics)
                                       ~380KB (with semantics)

    Never in memory simultaneously:
        More than one manifold's 625 slots

USAGE
-----
    from aurora_manifold_directory_reader import ManifoldDirectory

    # Load index once at startup
    directory = ManifoldDirectory("aurora_manifold_directory")

    # Lookup by noncomp name — loads from disk, returns manifold
    meaning = directory.load("Boundary_Operator_of_Boundary")
    print(meaning.anchor_slot_id)
    print(meaning.dense_clusters[:3])

    # Query slots — streamed, no full load into a list
    for slot in meaning.stream_slots(min_evo=0.70):
        ...  # process one at a time

    # Slot lookup by coordinates
    slot = meaning.get_slot("B", "OPERATOR", "A", "OPERATOR")

    # Context manager — auto-releases after block
    with directory.open("Boundary_Operator_of_Boundary") as meaning:
        top = meaning.top_slots(n=10)

    # Cross-noncomp lookup (loads each manifold, queries, releases)
    results = directory.query_across(
        nc_names   = ["Boundary_Operator_of_Boundary",
                       "Agentive_Operator_of_Boundary"],
        min_evo    = 0.80,
        col_law_c  = "A",
        col_law_d  = "OPERATOR",
    )
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any, Dict, Generator, Iterator, List,
    Optional, Tuple,
)

class _SignatureDesc:
    def __init__(self, sig: str):
        u = "".join(dict.fromkeys(c for c in str(sig or "") if c in "XTNBA"))
        self._sig = u
        n = len(u)
        self.tier = "tier0" if n <= 1 else ("tier1" if n == 2 else ("tier2" if n == 3 else ("tier3" if n == 4 else "tier4")))
    def to_dict(self) -> Dict:
        return {"signature": self._sig, "tier": self.tier}

def describe_signature(sig: str) -> _SignatureDesc:
    return _SignatureDesc(sig)

# ── Slot view (lightweight wrapper over raw dict) ────────────────────────────

class SlotView:
    """
    Thin wrapper over a raw slot dict from the JSON.
    No copying — reads fields directly from the dict.
    Released when the parent manifold is released.
    """
    __slots__ = ("_d",)

    def __init__(self, d: Dict) -> None:
        self._d = d

    @property
    def slot_id(self)         -> str:   return self._d["slot_id"]
    @property
    def sub_law_c(self)       -> str:   return self._d["sub_law_c"]
    @property
    def sub_law_d(self)       -> str:   return self._d["sub_law_d"]
    @property
    def sub_cluster(self)     -> str:   return self._d["sub_cluster"]
    @property
    def sub_is_diagonal(self) -> bool:  return self._d["sub_is_diagonal"]
    @property
    def col_law_c(self)       -> str:   return self._d["col_law_c"]
    @property
    def col_law_d(self)       -> str:   return self._d["col_law_d"]
    @property
    def is_resonant(self)     -> bool:  return self._d["is_resonant"]
    @property
    def is_anchor(self)       -> bool:  return self._d["is_anchor"]
    @property
    def cluster_pair(self)    -> str:   return self._d["cluster_pair"]
    @property
    def evolution_grade(self) -> float: return self._d["evolution_grade"]
    @property
    def leverage_class(self)  -> str:   return self._d["leverage_class"]
    @property
    def depth_score(self)     -> float: return self._d["depth_score"]
    @property
    def combined_cost(self)   -> float: return self._d["combined_cost"]
    @property
    def accountability_weight(self) -> float:
        return self._d["accountability_weight"]
    @property
    def semantic(self) -> Optional[str]:
        return self._d.get("semantic")
    @property
    def with_semantics(self) -> bool:
        return self._d.get("with_semantics", False)
    @property
    def semantic_entries(self) -> List[Dict]:
        return list(self._d.get("semantic_entries", []) or [])

    def viable_semantic_entries(
        self,
        *,
        allow_suppressed: bool = False,
        conditional_available: bool = True,
        marginal_available: bool = False,
        perceptual_path_available: bool = False,
    ) -> List[Dict]:
        """
        Return FGAE entries that satisfy the slot's live Clause I/II/III state.
        The slot remains the grammar/viability address; runtime only chooses
        among entries already placed at that coordinate.
        """
        viable: List[Dict] = []
        for entry in self.semantic_entries:
            if entry.get("clause_i_level") == "I-C" and not allow_suppressed:
                continue
            clause_ii = entry.get("clause_ii_level")
            if clause_ii == "II-B" and not conditional_available:
                continue
            if clause_ii == "II-C" and not marginal_available:
                continue
            if entry.get("clause_iii_influence") == "III-B" and not perceptual_path_available:
                continue
            if entry.get("entry_type") != "word":
                continue
            word = str(entry.get("word_or_phrase", "")).strip()
            if not word or " " in word:
                continue
            viable.append(entry)
        return viable

    def select_semantic_entry(
        self,
        *,
        commitment_level: float = 0.5,
        allow_suppressed: bool = False,
        conditional_available: bool = True,
        marginal_available: bool = False,
        perceptual_path_available: bool = False,
    ) -> Optional[Dict]:
        """
        Select the live word entry for this slot using FGAE's viability-first
        rule, then closest accountability fit for the current commitment level.
        """
        entries = self.viable_semantic_entries(
            allow_suppressed=allow_suppressed,
            conditional_available=conditional_available,
            marginal_available=marginal_available,
            perceptual_path_available=perceptual_path_available,
        )
        if not entries:
            return None
        target = max(0.0, min(1.0, float(commitment_level or 0.0)))

        def rank(entry: Dict) -> Tuple[float, float, str]:
            acct_delta = abs(self.accountability_weight - target)
            source = str(entry.get("lexicon_source") or "")
            source_bonus = 0.02 if "oets" in source or "lexicon" in source else 0.0
            return (-acct_delta + source_bonus, self.evolution_grade, str(entry.get("word_or_phrase") or ""))

        return max(entries, key=rank)

    def to_dict(self) -> Dict:
        return self._d

    def __repr__(self) -> str:
        return (
            f"SlotView({self.slot_id!r}, "
            f"evo={self.evolution_grade:.3f}, "
            f"acct={self.accountability_weight:.3f})"
        )


# ── Sub-position view ────────────────────────────────────────────────────────

class SubPositionView:
    """Thin wrapper over a raw sub-position dict."""
    __slots__ = ("_d",)

    def __init__(self, d: Dict) -> None:
        self._d = d

    @property
    def sub_id(self)         -> str:  return self._d["sub_id"]
    @property
    def law_c(self)          -> str:  return self._d["law_c"]
    @property
    def law_d(self)          -> str:  return self._d["law_d"]
    @property
    def is_diagonal(self)    -> bool: return self._d["is_diagonal"]
    @property
    def is_self_family(self) -> bool: return self._d["is_self_family"]
    @property
    def cluster(self)        -> str:  return self._d["cluster"]
    @property
    def name(self)           -> str:  return self._d["name"]
    @property
    def depth_score(self)    -> float: return self._d["depth_score"]
    @property
    def leverage_class(self) -> str:  return self._d["leverage_class"]
    @property
    def semantic(self)       -> Optional[str]: return self._d.get("semantic")


# ── Loaded manifold ──────────────────────────────────────────────────────────

class NoncompManifold:
    """
    One noncomp's 625-slot manifold loaded from disk.

    All slot access is via streaming or single-slot lookup.
    The raw slot list is held in _data["slots"] — a plain Python list
    of dicts. No further copies are made unless you explicitly call
    list(manifold.stream_slots()), which you generally shouldn't.

    Release by letting this object go out of scope (or use the
    directory.open() context manager).
    """

    def __init__(self, data: Dict) -> None:
        self._data = data

    # ── Identity ─────────────────────────────────────────────────────────────

    @property
    def nc_name(self)     -> str:  return self._data["nc_name"]
    @property
    def nc_law_c(self)    -> str:  return self._data["nc_law_c"]
    @property
    def nc_dim(self)      -> str:  return self._data["nc_dim"]
    @property
    def nc_target(self)   -> str:  return self._data["nc_target"]
    @property
    def nc_domain(self)   -> str:  return self._data["nc_domain"]
    @property
    def lineage_signature(self) -> str: return self._data.get("lineage_signature", "")
    @property
    def lineage_tier(self) -> str: return self._data.get("lineage_tier", describe_signature(self.lineage_signature or self.nc_target).tier)
    @property
    def lineage_description(self) -> Dict: return self._data.get("lineage_description", describe_signature(self.lineage_signature or self.nc_target).to_dict())
    @property
    def nc_cluster(self)  -> str:  return self._data["nc_cluster"]
    @property
    def nc_is_diagonal(self) -> bool: return self._data["nc_is_diagonal"]
    @property
    def representational_anchor(self) -> Optional[str]:
        return self._data.get("representational_anchor")
    @property
    def nc_semantic_summary(self) -> str:
        return self._data.get("nc_semantic_summary", "")
    @property
    def anchor_slot_id(self) -> str:
        return self._data["anchor_slot_id"]
    @property
    def with_semantics(self) -> bool:
        return self._data.get("with_semantics", False)
    @property
    def slot_count(self) -> int:
        return self._data.get("slot_count", 625)
    @property
    def runtime_regime(self) -> Dict:
        return dict(self._data.get("runtime_regime", {}))
    @property
    def language_projection(self) -> Dict:
        return dict(self._data.get("language_projection", {}))

    # ── Geometry ──────────────────────────────────────────────────────────────

    @property
    def dense_clusters(self) -> List[Dict]:
        """Top accountability clusters in this manifold's geometric field."""
        return self._data["geometry"]["dense_clusters"]

    @property
    def top_evolved_slots(self) -> List[Dict]:
        """Pre-computed top-5 evolved slots (no full scan needed)."""
        return self._data["geometry"]["top_evolved_slots"]

    # ── Sub-positions ─────────────────────────────────────────────────────────

    def stream_sub_positions(self) -> Iterator[SubPositionView]:
        """Stream all 25 sub-positions."""
        for d in self._data["sub_positions"]:
            yield SubPositionView(d)

    def get_sub_position(self, law_c: str, law_d: str) -> Optional[SubPositionView]:
        """Get a specific sub-position by law coordinates."""
        for d in self._data["sub_positions"]:
            if d["law_c"] == law_c and d["law_d"] == law_d:
                return SubPositionView(d)
        return None

    @property
    def diagonal_sub(self) -> Optional[SubPositionView]:
        """The identity sub-position (self-application of the noncomp)."""
        for d in self._data["sub_positions"]:
            if d["is_diagonal"]:
                return SubPositionView(d)
        return None

    # ── Slot access ───────────────────────────────────────────────────────────

    def map_environmental_pressure(self, env: Dict[str, Any]) -> List[Tuple[SubPositionView, float]]:
        """
        Rank the 25 channels (sub-positions) by resonance with the environment.
        env: {
            "visual": ["saw sharp angular", ...],
            "audio": ["heard dissonant tension", ...],
            "time": 0.0-1.0 (day cycle),
            "pressure": {"X": 0.5, "T": 0.2, ...}
        }
        """
        results = []
        pressure = env.get("pressure", {})
        visual = env.get("visual", [])
        audio = env.get("audio", [])
        time_val = env.get("time", 0.5)

        for sub in self.stream_sub_positions():
            score = 0.0
            
            # 1. Base Pressure Alignment (Axis-to-Axis)
            # sub.law_c is the channel's category, sub.law_d is its dimension.
            score += pressure.get(sub.law_c, 0.0) * 0.4
            
            # 2. Sensory Grounding
            if sub.law_c in ("B", "X"): # Boundary/Existence linked to Vision
                if any(v in sub.name.lower() for v in visual):
                    score += 0.3
            if sub.law_c in ("N", "T"): # Energy/Time linked to Audio
                if any(a in sub.name.lower() for a in audio):
                    score += 0.3
            
            # 3. Temporal Influence
            if sub.law_c == "T":
                # Noon (0.5) favors fast/intense, night (0.0/1.0) favors slow/persistent
                if "magnitude" in sub.law_d.lower():
                    score += (1.0 - abs(time_val - 0.5)) * 0.2
            
            # 4. Identity Resonance
            if sub.is_diagonal:
                score += 0.15

            results.append((sub, score))
            
        # Sort by resonance score
        return sorted(results, key=lambda x: x[1], reverse=True)

    def stream_slots(
        self,
        min_evo:       float = 0.0,
        max_evo:       float = 1.0,
        col_law_c:     Optional[str] = None,
        col_law_d:     Optional[str] = None,
        sub_law_c:     Optional[str] = None,
        sub_law_d:     Optional[str] = None,
        sub_cluster:   Optional[str] = None,
        leverage_class: Optional[str] = None,
        resonant_only: bool = False,
        anchor_only:   bool = False,
    ) -> Iterator[SlotView]:
        """
        Stream slots with optional filters. Never materialises the full list.

        Filters are applied inline — only matching slots are yielded.
        Memory: O(1) regardless of how many slots match.
        """
        for d in self._data["slots"]:
            if d["evolution_grade"] < min_evo:          continue
            if d["evolution_grade"] > max_evo:          continue
            if col_law_c  and d["col_law_c"]  != col_law_c:  continue
            if col_law_d  and d["col_law_d"]  != col_law_d:  continue
            if sub_law_c  and d["sub_law_c"]  != sub_law_c:  continue
            if sub_law_d  and d["sub_law_d"]  != sub_law_d:  continue
            if sub_cluster and d["sub_cluster"] != sub_cluster: continue
            if leverage_class and d["leverage_class"] != leverage_class: continue
            if resonant_only and not d["is_resonant"]: continue
            if anchor_only   and not d["is_anchor"]:   continue
            yield SlotView(d)

    def get_slot(
        self,
        sub_law_c: str,
        sub_law_d: str,
        col_law_c: str,
        col_law_d: str,
    ) -> Optional[SlotView]:
        """Direct slot lookup by full coordinates. O(n) scan."""
        for d in self._data["slots"]:
            if (d["sub_law_c"] == sub_law_c and
                d["sub_law_d"] == sub_law_d and
                d["col_law_c"] == col_law_c and
                d["col_law_d"] == col_law_d):
                return SlotView(d)
        return None

    def get_anchor(self) -> Optional[SlotView]:
        """The geometric anchor — sub diagonal × col operator of nc's own constraint."""
        return self.get_slot(
            self.nc_law_c, self.nc_dim,
            self.nc_law_c, self.nc_dim,
        )

    def select_semantic_entry_for_sub_position(
        self,
        sub_law_c: str,
        sub_law_d: str,
        *,
        preferred_col_law_c: Optional[str] = None,
        preferred_col_law_d: Optional[str] = None,
        commitment_level: float = 0.5,
        allow_suppressed: bool = False,
        conditional_available: bool = True,
        marginal_available: bool = False,
        perceptual_path_available: bool = False,
    ) -> Optional[Tuple[SlotView, Dict]]:
        """
        FGAE runtime selector for one active sub-position.
        Scans that sub-position's 25 column slots and returns the viable word
        entry with highest evolution grade plus accountability fit.
        """
        candidates: List[Tuple[float, SlotView, Dict]] = []
        target = max(0.0, min(1.0, float(commitment_level or 0.0)))
        for slot in self.stream_slots(sub_law_c=sub_law_c, sub_law_d=sub_law_d):
            entry = slot.select_semantic_entry(
                commitment_level=target,
                allow_suppressed=allow_suppressed,
                conditional_available=conditional_available,
                marginal_available=marginal_available,
                perceptual_path_available=perceptual_path_available,
            )
            if not entry:
                continue
            exact_col_bonus = 0.40 if (
                preferred_col_law_c
                and preferred_col_law_d
                and slot.col_law_c == preferred_col_law_c
                and slot.col_law_d == preferred_col_law_d
            ) else 0.0
            direct_bonus = 0.03 if entry.get("clause_iii_influence") == "III-A" else 0.0
            accountability_fit = 1.0 - abs(slot.accountability_weight - target)
            score = (
                slot.evolution_grade * 0.55
                + accountability_fit * 0.30
                + slot.depth_score * 0.10
                + exact_col_bonus
                + direct_bonus
            )
            candidates.append((score, slot, entry))
        if not candidates:
            return None
        _score, slot, entry = max(candidates, key=lambda item: item[0])
        return slot, entry

    def top_slots(self, n: int = 10) -> List[SlotView]:
        """
        Top-N slots by evolution_grade. Partial sort — doesn't sort all 625.
        Uses a min-heap capped at n.
        """
        import heapq
        heap: List[Tuple[float, int, Dict]] = []
        for i, d in enumerate(self._data["slots"]):
            heapq.heappush(heap, (d["evolution_grade"], i, d))
            if len(heap) > n:
                heapq.heappop(heap)
        return [SlotView(d) for _, _, d in sorted(heap, key=lambda x: -x[0])]

    def cluster_pair_summary(self) -> Dict[str, int]:
        """Count of slots per cluster_pair. One pass, no list copy."""
        counts: Dict[str, int] = {}
        for d in self._data["slots"]:
            cp = d["cluster_pair"]
            counts[cp] = counts.get(cp, 0) + 1
        return dict(sorted(counts.items()))

    def accountability_map(self) -> Dict[str, float]:
        """
        Mean accountability weight per cluster_pair.
        The geometric field's density map — high = dense cluster region.
        """
        sums:   Dict[str, float] = {}
        counts: Dict[str, int]   = {}
        for d in self._data["slots"]:
            cp = d["cluster_pair"]
            sums[cp]   = sums.get(cp, 0.0)   + d["accountability_weight"]
            counts[cp] = counts.get(cp, 0)   + 1
        return {
            cp: round(sums[cp] / counts[cp], 4)
            for cp in sorted(sums, key=lambda k: -sums[k] / counts[k])
        }

    def __repr__(self) -> str:
        anchor = f"  anchor={self.representational_anchor!r}" if self.representational_anchor else ""
        return (
            f"NoncompManifold({self.nc_name!r}, "
            f"domain={self.nc_domain!r},"
            f"{anchor} "
            f"slots={self.slot_count})"
        )


# ── Index entry ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IndexEntry:
    """One row in the directory index — always in memory, no slots."""
    nc_name:              str
    nc_law_c:             str
    nc_dim:               str
    nc_target:            str
    lineage_signature:    str
    lineage_tier:         str
    nc_domain:            str
    nc_cluster:           str
    nc_is_diagonal:       bool
    representational_anchor: Optional[str]
    file:                 str
    slot_count:           int
    anchor_slot_id:       str
    with_semantics:       bool
    dense_top3:           List[str]

    @property
    def nc_axis(self) -> str:
        return self.nc_target


# ── Directory ────────────────────────────────────────────────────────────────

class ManifoldDirectory:
    """
    Aurora's interface to the pre-compiled manifold directory.

    Load once at startup. Access manifolds by name on demand.
    Never holds more than one manifold's slots in memory at once.

    Usage:
        directory = ManifoldDirectory("aurora_manifold_directory")
        with directory.open("Boundary_Operator_of_Boundary") as m:
            for slot in m.stream_slots(min_evo=0.70):
                ...
    """

    def __init__(self, directory: str) -> None:
        self._root = Path(directory)
        self._index: Dict[str, IndexEntry] = {}
        self._load_index()

    def _load_index(self) -> None:
        index_path = self._root / "_index.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"No _index.json found in {self._root}. "
                f"Run aurora_constraint_manifold_compiler.py first."
            )
        with open(index_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for e in raw["entries"]:
            self._index[e["nc_name"]] = IndexEntry(
                nc_name              = e["nc_name"],
                nc_law_c             = e["nc_law_c"],
                nc_dim               = e["nc_dim"],
                nc_target            = e["nc_target"],
                lineage_signature    = e.get("lineage_signature", ""),
                lineage_tier         = e.get("lineage_tier", describe_signature(e.get("lineage_signature", e["nc_target"])).tier),
                nc_domain            = e["nc_domain"],
                nc_cluster           = e["nc_cluster"],
                nc_is_diagonal       = e["nc_is_diagonal"],
                representational_anchor = e.get("representational_anchor"),
                file                 = e["file"],
                slot_count           = e["slot_count"],
                anchor_slot_id       = e["anchor_slot_id"],
                with_semantics       = e.get("with_semantics", False),
                dense_top3           = e.get("dense_top3", []),
            )

    # ── Index queries (no disk I/O) ───────────────────────────────────────────

    @property
    def noncomp_names(self) -> List[str]:
        return list(self._index.keys())

    @property
    def total(self) -> int:
        return len(self._index)

    def get_index_entry(self, nc_name: str) -> Optional[IndexEntry]:
        return self._index.get(nc_name)

    def entries_for_axis(self, axis: str) -> List[IndexEntry]:
        return [e for e in self._index.values() if e.nc_target == axis]

    def diagonal_entries(self) -> List[IndexEntry]:
        return [e for e in self._index.values() if e.nc_is_diagonal]

    def entries_by_cluster(self, cluster: str) -> List[IndexEntry]:
        return [e for e in self._index.values() if e.nc_cluster == cluster]

    def find_by_domain(self, domain: str) -> Optional[IndexEntry]:
        for e in self._index.values():
            if e.nc_domain.lower() == domain.lower():
                if e.nc_is_diagonal:
                    return e
        return None

    # ── Manifold loading (disk I/O, one at a time) ────────────────────────────

    def load(self, nc_name: str) -> NoncompManifold:
        """
        Load one manifold from disk. Returns a NoncompManifold.

        The caller is responsible for releasing (letting it go out of scope).
        For automatic release, use open() instead.
        """
        entry = self._index.get(nc_name)
        if entry is None:
            raise KeyError(
                f"Unknown noncomp: {nc_name!r}. "
                f"Available: {list(self._index.keys())[:5]}..."
            )
        file_path = self._root / entry.file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return NoncompManifold(data)

    @contextmanager
    def open(self, nc_name: str) -> Generator[NoncompManifold, None, None]:
        """
        Context manager — loads manifold, yields it, releases on exit.

        with directory.open("Boundary_Operator_of_Boundary") as m:
            slot = m.get_anchor()
        # manifold released here
        """
        manifold = self.load(nc_name)
        try:
            yield manifold
        finally:
            del manifold

    # ── Cross-noncomp queries (load → query → release, one at a time) ─────────

    def query_across(
        self,
        nc_names:      List[str],
        col_law_c:     Optional[str] = None,
        col_law_d:     Optional[str] = None,
        sub_law_c:     Optional[str] = None,
        min_evo:       float = 0.0,
        resonant_only: bool  = False,
        max_per_nc:    int   = 5,
    ) -> Dict[str, List[Dict]]:
        """
        Query multiple manifolds with the same filter, loading each in turn.

        Returns {nc_name → [slot dicts]} — never holds two manifolds at once.
        """
        results: Dict[str, List[Dict]] = {}
        for nc_name in nc_names:
            with self.open(nc_name) as m:
                matched = []
                for slot in m.stream_slots(
                    min_evo       = min_evo,
                    col_law_c     = col_law_c,
                    col_law_d     = col_law_d,
                    sub_law_c     = sub_law_c,
                    resonant_only = resonant_only,
                ):
                    matched.append(slot.to_dict())
                    if len(matched) >= max_per_nc:
                        break
                results[nc_name] = matched
        return results

    def stream_anchors(self) -> Generator[Tuple[IndexEntry, SlotView], None, None]:
        """
        Stream the geometric anchor slot from each diagonal noncomp.
        Loads each manifold, yields anchor, releases. One at a time.
        """
        for entry in self.diagonal_entries():
            with self.open(entry.nc_name) as m:
                anchor = m.get_anchor()
                if anchor:
                    yield entry, anchor

    def dense_cluster_report(self) -> Dict[str, List[Dict]]:
        """
        Return the top-3 dense clusters from the index for each noncomp.
        No disk I/O — purely from the index.
        """
        return {
            e.nc_name: e.dense_top3
            for e in self._index.values()
        }

    def __repr__(self) -> str:
        return (
            f"ManifoldDirectory({str(self._root)!r}, "
            f"entries={self.total}, "
            f"total_slots={self.total * 625:,})"
        )


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    DIRECTORY = sys.argv[1] if len(sys.argv) > 1 else "aurora_manifold_directory"

    print("=" * 65)
    print("AURORA MANIFOLD DIRECTORY READER")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 65)

    directory = ManifoldDirectory(DIRECTORY)
    print(f"\n{directory}")

    print("\n--- Index: diagonal entries (representational domains) ---")
    for e in directory.diagonal_entries():
        print(
            f"  [{e.nc_target}]  {e.nc_name:<45}"
            f"  domain={e.nc_domain}"
        )

    print("\n--- Load: Boundary_Operator_of_Boundary (Meaning Manifold) ---")
    with directory.open("Boundary_Operator_of_Boundary") as m:
        print(f"  {m}")
        print(f"  Anchor slot: {m.anchor_slot_id}")
        print(f"  Semantic:    {m.nc_semantic_summary}")

        print("\n  Top 5 dense accountability clusters:")
        for c in m.dense_clusters[:5]:
            print(
                f"    {c['cluster_pair']:<35}"
                f"  mean_acct={c['mean_acct']:.4f}"
                f"  total={c['total_acct']:.3f}"
            )

        print("\n  Top 5 evolved slots:")
        for s in m.top_slots(n=5):
            print(
                f"    evo={s.evolution_grade:.4f}"
                f"  acct={s.accountability_weight:.4f}"
                f"  {s.cluster_pair:<30}"
                f"  resonant={s.is_resonant}"
            )

        print("\n  Anchor slot (geometric centre):")
        anchor = m.get_anchor()
        if anchor:
            print(f"    {anchor.slot_id}")
            print(f"    evo={anchor.evolution_grade:.4f}"
                  f"  acct={anchor.accountability_weight:.4f}"
                  f"  anchor={anchor.is_anchor}")
            if anchor.semantic:
                print(f"    semantic: {anchor.semantic[:120]}...")

        print("\n  Stream: leverage-class slots, min_evo=0.80 (first 4):")
        count = 0
        for slot in m.stream_slots(min_evo=0.80, leverage_class="leverage"):
            print(
                f"    {slot.slot_id[:60]}"
                f"  evo={slot.evolution_grade:.3f}"
            )
            count += 1
            if count >= 4:
                break

    print("\n  (Meaning manifold released from memory)")

    print("\n--- Cross-noncomp query: A:OPERATOR column across B noncomps ---")
    b_names = [e.nc_name for e in directory.entries_for_axis("B")][:3]
    results = directory.query_across(
        nc_names  = b_names,
        col_law_c = "A",
        col_law_d = "OPERATOR",
        min_evo   = 0.60,
        max_per_nc = 2,
    )
    for nc_name, slots in results.items():
        print(f"\n  {nc_name}:")
        for s in slots:
            print(
                f"    evo={s['evolution_grade']:.3f}"
                f"  acct={s['accountability_weight']:.3f}"
                f"  {s['cluster_pair']}"
            )

    print("\n--- Diagonal anchor stream (all 5 representational domains) ---")
    for entry, anchor in directory.stream_anchors():
        print(
            f"  [{entry.nc_target}]  {entry.nc_name:<45}"
            f"  evo={anchor.evolution_grade:.4f}"
            f"  acct={anchor.accountability_weight:.4f}"
        )

    print("\nDone.")
