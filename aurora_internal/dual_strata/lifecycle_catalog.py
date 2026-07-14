# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/lifecycle_catalog.py
====================================================
MTSL, live-wired 2026-07-14: a single, read-only, queryable view over
every lifecycle-tagged structure Aurora already tracks -- semantic
variants (semantic_variant_registry.py), crystal facets
(aurora_dimensional_systems.py), and WARP components (aurora_warp_
protocol.py's WarpCapable hosts) -- answering one question uniformly
across all three: alive, or dead?

NO NEW STORAGE. This module owns no state of its own and persists
nothing; it reads through to the crystal registry and each
WarpCapable host's own trial/promoted bookkeeping, the same "not a
parallel database" discipline semantic_variant_registry.py already
documents for itself. Restart the process and the catalog rebuilds
itself identically from whatever's already durable -- there is
nothing here to lose.

Alive/dead calls, per structure kind (first-pass; not spec-pinned):

  semantic variant   alive: provisional, reinforced, promoted
                      dead: merged, retired
                      (SemanticVariant.status, semantic_variant_registry.py)

  crystal facet      alive: active, decaying (still contributing,
                             just weakening)
                      dead: relic
                      (CrystalFacet.state, aurora_dimensional_systems.py)

  WARP component     alive: trial (unconfirmed), promoted (confirmed)
                      dead: counted, not listed -- a failed trial is
                            pruned from the host's own _warp_trials by
                            evaluate_warp_trials() itself (WarpCapable
                            discipline: dissolved components are
                            removed, not archived), so no per-component
                            dead record survives to read back. The
                            host's own running _warp_dissolved_count
                            (added alongside this module) is the only
                            "it happened" signal left.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

_ALIVE_VARIANT_STATUSES = ("provisional", "reinforced", "promoted")
_DEAD_VARIANT_STATUSES = ("merged", "retired")

_DEAD_FACET_STATE = "relic"


def _catalog_semantic_variants(dps: Any) -> Dict[str, Any]:
    alive: List[Dict[str, Any]] = []
    dead: List[Dict[str, Any]] = []
    crystals = getattr(dps, "crystals", None) if dps is not None else None
    if isinstance(crystals, dict):
        for crystal in crystals.values():
            concept = getattr(crystal, "concept", "") or ""
            if not concept.startswith("tensor_variant:"):
                continue
            for facet in getattr(crystal, "facets", {}).values():
                if getattr(facet, "role", "") != "variant_state":
                    continue
                try:
                    data = json.loads(facet.content)
                except Exception:
                    continue
                status = str(data.get("status", "") or "")
                entry = {
                    "variant_id": data.get("variant_id"),
                    "manifold_slot_id": data.get("manifold_slot_id"),
                    "status": status,
                    "confidence": data.get("confidence"),
                    "observation_count": data.get("observation_count"),
                    "merged_into": data.get("merged_into"),
                }
                if status in _DEAD_VARIANT_STATUSES:
                    dead.append(entry)
                elif status in _ALIVE_VARIANT_STATUSES:
                    alive.append(entry)
                # unrecognized/blank status: neither counted nor lost --
                # simply not classified until the field carries a known value.
                break  # one variant_state facet per crystal (registry invariant)
    return {"alive_count": len(alive), "dead_count": len(dead), "alive": alive, "dead": dead}


def _catalog_crystal_facets(dps: Any) -> Dict[str, Any]:
    alive: List[Dict[str, Any]] = []
    dead: List[Dict[str, Any]] = []
    crystals = getattr(dps, "crystals", None) if dps is not None else None
    if isinstance(crystals, dict):
        for crystal in crystals.values():
            for facet in getattr(crystal, "facets", {}).values():
                state = getattr(facet, "state", None)
                state_value = getattr(state, "value", state)
                entry = {
                    "crystal_id": getattr(crystal, "crystal_id", None),
                    "concept": getattr(crystal, "concept", None),
                    "facet_id": getattr(facet, "facet_id", None),
                    "role": getattr(facet, "role", None),
                    "state": state_value,
                    "confidence": round(float(getattr(facet, "confidence", 0.0)), 4),
                }
                if state_value == _DEAD_FACET_STATE:
                    dead.append(entry)
                else:
                    alive.append(entry)
    return {"alive_count": len(alive), "dead_count": len(dead), "alive": alive, "dead": dead}


def _catalog_warp_components(warp_hosts: Dict[str, Any]) -> Dict[str, Any]:
    alive: List[Dict[str, Any]] = []
    dead_count = 0
    for host_name, host in (warp_hosts or {}).items():
        if host is None:
            continue
        for comp in (getattr(host, "_warp_trials", None) or {}).values():
            alive.append({
                "host": host_name,
                "component_id": getattr(comp, "component_id", None),
                "name": getattr(comp, "name", None),
                "level": getattr(comp, "level", None),
                "lifecycle": "trial",
                "trial_tick": getattr(comp, "trial_tick", 0),
                "trial_score_ema": round(float(getattr(comp, "trial_score_ema", 0.0)), 4),
                "topology_gap_ref": getattr(comp, "topology_gap_ref", None),
            })
        for comp in (getattr(host, "_warp_promoted", None) or {}).values():
            alive.append({
                "host": host_name,
                "component_id": getattr(comp, "component_id", None),
                "name": getattr(comp, "name", None),
                "level": getattr(comp, "level", None),
                "lifecycle": "promoted",
                "topology_gap_ref": getattr(comp, "topology_gap_ref", None),
            })
        dead_count += int(getattr(host, "_warp_dissolved_count", 0) or 0)
    return {
        "alive_count": len(alive), "dead_count": dead_count, "alive": alive,
        "dead_note": "dissolved WARP components are pruned from live state, not archived -- dead_count is a running total, not a list",
    }


def catalog_lifecycle(*, dps: Any = None, warp_hosts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the full alive/dead catalog across everything already
    tracked: semantic variants and crystal facets (both read through
    `dps`), and WARP components (read through each entry of
    `warp_hosts`, e.g. {"dps": dps, "language_field": ..., ...}).
    Degrades gracefully -- a missing/malformed dps or empty warp_hosts
    just yields empty sections, never raises."""
    try:
        semantic = _catalog_semantic_variants(dps)
    except Exception:
        semantic = {"alive_count": 0, "dead_count": 0, "alive": [], "dead": []}
    try:
        facets = _catalog_crystal_facets(dps)
    except Exception:
        facets = {"alive_count": 0, "dead_count": 0, "alive": [], "dead": []}
    try:
        warp = _catalog_warp_components(warp_hosts or {})
    except Exception:
        warp = {"alive_count": 0, "dead_count": 0, "alive": [], "dead_note": ""}

    return {
        "generated_at": time.time(),
        "semantic_variants": semantic,
        "crystal_facets": facets,
        "warp_components": warp,
        "alive_total": semantic["alive_count"] + facets["alive_count"] + warp["alive_count"],
        "dead_total": semantic["dead_count"] + facets["dead_count"] + warp["dead_count"],
    }


def collect_warp_hosts(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort collection of every known WarpCapable host reachable
    off a live `systems` dict (the same top-level dict aurora.py's
    boot() builds and threads everywhere). Every lookup degrades to
    "absent" rather than raising -- language_field and _thought_braid
    are both allowed to be None/missing per their own conditional
    construction in boot()."""
    hosts: Dict[str, Any] = {}
    dimensional = (systems or {}).get("dimensional")
    dps = getattr(dimensional, "dps", None)
    if dps is not None:
        hosts["dps"] = dps
    perception = (systems or {}).get("perception")
    if perception is not None:
        hosts["perception"] = perception
    language_field = (systems or {}).get("language_field")
    if language_field is not None:
        hosts["language_field"] = language_field
    thought_braid = (systems or {}).get("_thought_braid")
    if thought_braid is not None:
        hosts["thought_braid"] = thought_braid
    return hosts


def catalog_lifecycle_from_systems(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience entry point for a live boot: reads dps off
    systems['dimensional'] for the semantic-variant/crystal-facet
    sections and auto-collects every known WarpCapable host (see
    collect_warp_hosts) for the WARP section."""
    dimensional = (systems or {}).get("dimensional")
    dps = getattr(dimensional, "dps", None)
    return catalog_lifecycle(dps=dps, warp_hosts=collect_warp_hosts(systems))
