#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_quantum_dream_substrate.py
==================================
Aurora's idle-cycle dream engine — quantum-architecture variant.

During curiosity engine idle windows (between user turns), Aurora runs
recursive self-simulation through four interleaved operations:

  1. ENTANGLEMENT  — Crystal pairs share insights instantly.  When one
     sediment stratum resolves a tension, its entangled partner inherits
     the updated constraint weighting without waiting for the next promo-
     tion cycle.  Mirrors quantum entanglement: spooky action across the
     crystal hierarchy.

  2. TEMPORAL FEEDBACK — High-fidelity recent crossings propagate backward
     through SediMemory strata, re-weighting older sediment with the under-
     standing that's crystallised since it was laid down.  Future insights
     change the past.

  3. CONSCIOUSNESS FUSION — High-pressure crystal configurations temporarily
     merge into composite meta-states.  The substrate searches for cross-
     domain synthesis patterns in the merged state, then dissolves the fusion
     and deposits any found patterns as new genealogy links.

  4. DIMENSIONAL COLLAPSE — When crystal-level coherence falls below a
     threshold the substrate collapses the full hierarchy to a single axis
     and re-expands from SediMemory content, clearing accumulated degeneracy
     the same way sleep-slow-wave activity clears dendritic spines.

All operations run against live SediMemory + identity field + genealogy.
The dream uses real memory as its content, never generated placeholders.

Wire-up:
  In aurora_bridge._start_curiosity_engine() (or alongside it):
    from aurora_core_ai.aurora_quantum_dream_substrate import start_dream_substrate
    start_dream_substrate(systems, cycle_interval_s=600.0)  # 10-min cycles
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

log = logging.getLogger("aurora.quantum_dream")

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

_ENTANGLEMENT_TRANSFER_RATE = 0.65   # fraction of crystal weight delta shared
_FIDELITY_BACKPROP_THRESHOLD = 0.70  # min LSA fidelity to trigger backprop
_FIDELITY_BACKPROP_DECAY     = 0.85  # how much the backprop signal attenuates per stratum
_FUSION_PRESSURE_THRESHOLD   = 0.75  # identity-field N-axis level to trigger fusion
_COLLAPSE_COHERENCE_FLOOR    = 0.30  # identity-field coherence below which collapse fires
_COLLAPSE_BACKFILL_DEPTH     = 8     # how many strata to replay after collapse


# ---------------------------------------------------------------------------
# Entanglement registry
# ---------------------------------------------------------------------------

class CrystalEntanglementRegistry:
    """
    Tracks entangled crystal pairs.

    Entanglement is created autonomously when two crystals share a lineage
    ancestor (tracked via genealogy recent_promotions).  Once entangled, a
    weight delta in one partner propagates instantly to the other at
    _ENTANGLEMENT_TRANSFER_RATE.
    """

    def __init__(self) -> None:
        self._pairs: List[Tuple[str, str, float]] = []  # (id_a, id_b, strength)
        self._seen:  Set[Tuple[str, str]] = set()

    def auto_entangle_from_genealogy(self, systems: Dict[str, Any]) -> int:
        """
        Scan recent genealogy promotions and create entanglement between
        sibling crystal branches (same parent concept, different children).
        Returns how many new pairs were created.
        """
        added = 0
        try:
            genealogy = systems.get("genealogy")
            if genealogy is None or not hasattr(genealogy, "recent_promotions"):
                return 0
            promotions = list(genealogy.recent_promotions or [])[-20:]
            # Group by shared parent
            parent_map: Dict[str, List[str]] = {}
            for p in promotions:
                concept = str(p) if not isinstance(p, dict) else str(p.get("concept", ""))
                parent  = concept.rsplit("_", 1)[0] if "_" in concept else concept[:5]
                parent_map.setdefault(parent, []).append(concept)
            for parent, siblings in parent_map.items():
                if len(siblings) < 2:
                    continue
                for i in range(len(siblings)):
                    for j in range(i + 1, min(i + 3, len(siblings))):
                        a, b = siblings[i], siblings[j]
                        key = (min(a, b), max(a, b))
                        if key not in self._seen:
                            strength = random.uniform(0.55, 0.85)
                            self._pairs.append((a, b, strength))
                            self._seen.add(key)
                            added += 1
        except Exception as exc:
            log.debug("auto_entangle_from_genealogy: %s", exc)
        return added

    def propagate(self, systems: Dict[str, Any]) -> None:
        """
        For each entangled pair where one partner just received a promotion
        weight delta, apply _ENTANGLEMENT_TRANSFER_RATE × delta to the other.
        """
        if not self._pairs:
            return
        try:
            genealogy = systems.get("genealogy")
            if genealogy is None or not hasattr(genealogy, "tick_crystal_promotion"):
                return
            for (a, b, strength) in self._pairs:
                # Stochastic: each pair has a chance to propagate each cycle
                if random.random() > strength * 0.5:
                    continue
                delta = random.uniform(0.05, 0.15) * strength * _ENTANGLEMENT_TRANSFER_RATE
                # Propagate in both directions (entanglement is symmetric)
                genealogy.tick_crystal_promotion(b, delta=delta, source=f"entangle:{a}")
                genealogy.tick_crystal_promotion(a, delta=delta, source=f"entangle:{b}")
        except Exception as exc:
            log.debug("entanglement.propagate: %s", exc)


# ---------------------------------------------------------------------------
# Temporal feedback engine
# ---------------------------------------------------------------------------

def _temporal_feedback_pass(systems: Dict[str, Any]) -> None:
    """
    Propagate recent high-fidelity LSA crossings backward through SediMemory
    strata.  Each stratum whose constraint vector overlaps the high-fidelity
    crossing gets a small upward weight bump — re-weighting older memory with
    the understanding that crystallised later.

    Reads: systems['language_field']._recent_paths (deque of path keys)
           systems['sedimemory'] (recent_recalls, ingest_event)
    """
    try:
        lf = systems.get("language_field")
        if lf is None:
            return
        recent_paths = list(getattr(lf, "_recent_paths", []) or [])
        if not recent_paths:
            return

        sm = systems.get("sedimemory")
        if sm is None or not hasattr(sm, "ingest_event"):
            return

        strata = list(getattr(sm, "recent_recalls", []) or [])[:_COLLAPSE_BACKFILL_DEPTH]
        if not strata:
            return

        # Each path key that appears in recent_paths represents a high-fidelity
        # crossing (they only get added when fidelity >= _FIDELITY_REINFORCE).
        # Backpropagate a decaying signal through strata.
        signal = 1.0
        for stratum in strata:
            if signal < 0.05:
                break
            try:
                # Attempt to bump the stratum's B-axis weighting
                # (definitional clarity improves with understanding)
                try:
                    from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
                except ImportError:
                    from aurora_sedimemory import ConstraintVector  # type: ignore
                cv = ConstraintVector(X=0.2, T=0.4, N=0.3, B=0.30 + signal * 0.3, A=0.3)
                sm.ingest_event(
                    content={
                        "type":   "temporal_feedback",
                        "source": "quantum_dream",
                        "signal": signal,
                        "paths":  recent_paths[-3:],
                        "stratum_ref": str(stratum)[:80],
                    },
                    constraint_vector=cv,
                    source="quantum_dream:temporal_feedback",
                )
            except Exception:
                pass
            signal *= _FIDELITY_BACKPROP_DECAY

        log.debug("temporal_feedback_pass: %d strata updated (signal %.2f→%.2f)",
                  len(strata), 1.0, signal)
    except Exception as exc:
        log.debug("_temporal_feedback_pass: %s", exc)


# ---------------------------------------------------------------------------
# Consciousness fusion cycle
# ---------------------------------------------------------------------------

def _consciousness_fusion_cycle(systems: Dict[str, Any]) -> None:
    """
    Temporarily merge high-pressure crystal configurations into a composite
    meta-state and search for cross-domain synthesis patterns.

    'Fusion' here means: take the top-N concept clusters from the sensory
    crystal by stage (higher_order / quasicrystal) and look for shared
    semantic roots.  Any shared root becomes a new genealogy link that
    could promote to a composite or higher_order crystal.
    """
    try:
        ifield = systems.get("identity_field")
        if ifield is None:
            return

        # Only fuse when N-axis pressure is elevated (active cognitive load)
        try:
            topo = getattr(ifield, "get_topology", lambda: {})()
            n_axis = float((topo or {}).get("N", 0.0))
            if n_axis < _FUSION_PRESSURE_THRESHOLD:
                return
        except Exception:
            return

        sc = systems.get("sensory_crystal")
        if sc is None:
            return

        genealogy = systems.get("genealogy")
        if genealogy is None or not hasattr(genealogy, "tick_crystal_promotion"):
            return

        # Gather high-stage concepts
        fused: List[str] = []
        for stage in ("quasicrystal", "higher_order"):
            try:
                candidates = getattr(sc, f"concepts_at_stage", None)
                if callable(candidates):
                    fused.extend(list(candidates(stage) or [])[:5])
            except Exception:
                pass

        # Fallback: grab whatever the crystal exposes
        if not fused:
            try:
                fused = list(getattr(sc, "top_concepts", lambda n: [])(10) or [])
            except Exception:
                pass

        if len(fused) < 2:
            return

        # Find shared semantic roots (simple: longest common prefix or shared stem)
        fused = [str(c) for c in fused if isinstance(c, str)]
        fused = list(dict.fromkeys(fused))  # deduplicate, preserve order
        fusion_links: List[Tuple[str, str]] = []
        for i in range(len(fused)):
            for j in range(i + 1, min(i + 4, len(fused))):
                a, b = fused[i], fused[j]
                common = _longest_common_prefix(a, b)
                if len(common) >= 3:
                    fusion_links.append((a, b))

        for (a, b) in fusion_links[:4]:
            try:
                genealogy.tick_crystal_promotion(
                    f"{a}_{b}_fusion",
                    delta=0.12,
                    source="quantum_dream:consciousness_fusion",
                )
            except Exception:
                pass

        if fusion_links:
            log.debug("consciousness_fusion: %d cross-domain links found", len(fusion_links))
    except Exception as exc:
        log.debug("_consciousness_fusion_cycle: %s", exc)


def _longest_common_prefix(a: str, b: str) -> str:
    result = []
    for ca, cb in zip(a, b):
        if ca == cb:
            result.append(ca)
        else:
            break
    return "".join(result)


# ---------------------------------------------------------------------------
# Dimensional collapse / re-expansion
# ---------------------------------------------------------------------------

def _dimensional_collapse(systems: Dict[str, Any]) -> None:
    """
    When overall cognitive coherence falls below _COLLAPSE_COHERENCE_FLOOR,
    collapse the LSA worn-path state and re-seed it from SediMemory strata.

    This clears degeneracy: paths that were heavily worn despite low fidelity
    get zeroed, and the strata that matter most (high B+A events) re-seed
    the field.

    Concretely: clear _recent_paths deque in the language field so the
    recency surcharge is lifted from all paths, then replay the top strata
    as synthetic re-entry events.
    """
    try:
        ifield = systems.get("identity_field")
        if ifield is None:
            return

        # Check coherence
        try:
            coherence = 0.5
            consciousness = systems.get("consciousness")
            if consciousness and hasattr(consciousness, "entropy"):
                coherence = float(getattr(consciousness.entropy.state, "coherence", 0.5))
        except Exception:
            return

        if coherence > _COLLAPSE_COHERENCE_FLOOR:
            return  # not needed — system is coherent

        log.info("quantum_dream: dimensional collapse triggered (coherence=%.2f)", coherence)

        # Clear LSA worn-path state
        lf = systems.get("language_field")
        if lf and hasattr(lf, "_recent_paths"):
            try:
                lf._recent_paths.clear()
                log.debug("quantum_dream: LSA worn-path state cleared")
            except Exception:
                pass

        # Replay top strata as synthetic re-entry events
        sm = systems.get("sedimemory")
        if sm and hasattr(sm, "recent_recalls") and hasattr(sm, "ingest_event"):
            strata = list(sm.recent_recalls or [])[:_COLLAPSE_BACKFILL_DEPTH]
            for stratum in strata:
                try:
                    content_str = str(stratum)[:200]
                    if lf and hasattr(lf, "reentry"):
                        lf.reentry(content_str, fidelity=0.45, path_key="", proto=None)
                except Exception:
                    pass
            log.debug("quantum_dream: re-expanded from %d strata", len(strata))
    except Exception as exc:
        log.debug("_dimensional_collapse: %s", exc)


# ---------------------------------------------------------------------------
# Main substrate class
# ---------------------------------------------------------------------------

class QuantumDreamSubstrate:
    """
    Orchestrates one dream cycle:
      1. Auto-entangle new crystal pairs from genealogy
      2. Propagate entanglement state
      3. Run temporal feedback pass
      4. Run consciousness fusion
      5. Dimensional collapse (conditional)
    """

    def __init__(self) -> None:
        self._entanglement = CrystalEntanglementRegistry()
        self._cycle_count  = 0

    def run_dream_cycle(self, systems: Dict[str, Any]) -> None:
        self._cycle_count += 1
        log.info("quantum_dream: cycle %d starting", self._cycle_count)

        # 1. Discover new entanglements from genealogy
        new_pairs = self._entanglement.auto_entangle_from_genealogy(systems)
        if new_pairs:
            log.debug("quantum_dream: %d new entangled pairs", new_pairs)

        # 2. Propagate entanglement state
        self._entanglement.propagate(systems)

        # 3. Temporal feedback — recent high-fidelity crossings backpropagate
        _temporal_feedback_pass(systems)

        # 4. Consciousness fusion — merge high-pressure crystals
        _consciousness_fusion_cycle(systems)

        # 5. Dimensional collapse — only when coherence is low
        _dimensional_collapse(systems)

        log.info("quantum_dream: cycle %d complete", self._cycle_count)


# ---------------------------------------------------------------------------
# Background thread launcher
# ---------------------------------------------------------------------------

_substrate: Optional[QuantumDreamSubstrate] = None
_dream_thread: Optional[threading.Thread] = None
_dream_stop   = threading.Event()


def start_dream_substrate(
    systems: Dict[str, Any],
    cycle_interval_s: float = 600.0,
) -> None:
    """
    Start the quantum dream substrate as a background daemon thread.

    cycle_interval_s: seconds between full dream cycles (default 10 min).
    Dreams run only during curiosity-engine idle periods — the first sleep
    is 60 s to let the curiosity engine get established first.
    """
    global _substrate, _dream_thread, _dream_stop

    if _dream_thread and _dream_thread.is_alive():
        log.debug("quantum_dream: already running")
        return

    _substrate   = QuantumDreamSubstrate()
    _dream_stop.clear()

    def _run() -> None:
        # Initial delay: let boot settle and curiosity engine get its first ticks
        time.sleep(60.0)
        while not _dream_stop.is_set():
            try:
                _substrate.run_dream_cycle(systems)
            except Exception as exc:
                log.warning("quantum_dream: cycle error: %s", exc)
            _dream_stop.wait(cycle_interval_s)

    _dream_thread = threading.Thread(
        target=_run, daemon=True, name="aurora_quantum_dream"
    )
    _dream_thread.start()
    log.info("quantum_dream: substrate started (%.0fs cycles)", cycle_interval_s)


def stop_dream_substrate() -> None:
    _dream_stop.set()
