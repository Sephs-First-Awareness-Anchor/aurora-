#!/usr/bin/env python3
"""
AURORA FGAE MANIFOLD SEMANTICS COMPILER
========================================
Module: aurora_fgae_manifold_semantics.py
Layer:  FGAE — First Principle Generative Articulate Emergence
        Manifold Population Pass

Authors: Sunni (Sir) Morningstar & Cael Devo
Created: April 2026  |  Specification: FGAE_SPECIFICATION v2 (2026-04-13)

PURPOSE
-------
Populates the three FGAE semantic fields on every slot across all 125 NonComps
in the aurora_manifold_directory.  This pass is idempotent — re-running it
refines already-populated slots without losing prior data.

WHAT IS ADDED PER SLOT (per spec §11.2)
----------------------------------------
Tier 1 (diagonal NCs — 5 total):
    domain_character    — one-sentence expressive description
    oets_query_profile  — derived from §12 tables

Tier 2 (self-family non-diagonal NCs — 20 total):
    semantic_role       — grammatical position this slot assigns
    family_character    — this family's version of that role
    position_in_sentence — pre-verbal | pre-nominal | post-verbal | boundary

Tier 3 (cross-family NCs — 100 total):
    domain_character    — cluster_pair interpretation of nc_semantic_summary
    oets_query_profile  — derived from §12 tables, primary_domain = nc_target

OETS QUERY PROFILE DERIVATION  (spec §12 — authoritative)
-----------------------------------------------------------
clause_i_floor:
    0.80–1.00  → I-A
    0.40–0.79  → I-B
    0.10–0.39  → I-D
    0.00–0.09  → I-C

clause_ii_required:
    leverage  → II-A
    neutral   → II-B
    overhead  → II-C

accountability_band:
    >= 0.70     → {min:0.6, max:1.0}
    0.40–0.69   → {min:0.3, max:0.7}
    < 0.40      → {min:0.0, max:0.45}

cost_band (combined_cost):
    <= 90       → {min:0,   max:100}
    91–150      → {min:75,  max:175}
    151–200     → {min:125, max:225}
    > 200       → {min:175, max:999}

register_eligible:
    resonant + depth>=0.8 + acct>=0.7  → [intimate, formal]
    resonant + depth>=0.4              → [formal, neutral]
    !resonant + depth>=0.4             → [neutral, technical]
    depth<0.4 + leverage               → [neutral, colloquial]
    depth<0.4 + overhead               → [colloquial]

resonance_required: mirrors is_resonant
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── canonical paths ──────────────────────────────────────────────────────────
_STRATA_ROOT = Path(__file__).parent
_MANIFOLD_DIR = _STRATA_ROOT / "aurora_manifold_directory"
_INDEX_PATH   = _MANIFOLD_DIR / "_index.json"

# ── Tier classification constants ────────────────────────────────────────────
AXES = ("X", "T", "N", "B", "A")

TIER1_ANCHOR_WORDS: Dict[str, str] = {
    "X": "Information",
    "T": "Belief",
    "N": "Purpose",
    "B": "Meaning",
    "A": "Understanding",
}

# Tier 2 grammatical positions per dimension (spec §4 Tier 2 table)
_DIM_TO_ROLE: Dict[str, str] = {
    "POLARITY":   "stance_marker",
    "MAGNITUDE":  "intensifier",
    "COST":       "modal",
    "DIFFERENCE": "delimiter",
}

# Family character descriptions per axis × dimension (spec §4)
_FAMILY_CHARACTER: Dict[Tuple[str, str], str] = {
    ("X", "POLARITY"):   "whether something registers at all — existential presence or absence",
    ("X", "MAGNITUDE"):  "signal weight — how much information is present in the claim",
    ("X", "COST"):       "evidential — what the data requires to be treated as real",
    ("X", "DIFFERENCE"): "scope — what this information covers versus does not cover",
    ("T", "POLARITY"):   "temporal orientation — before or after, toward or away in time",
    ("T", "MAGNITUDE"):  "duration — how persistent or momentary the belief is",
    ("T", "COST"):       "commitment over time — what is held versus what is provisional",
    ("T", "DIFFERENCE"): "sequence — what comes before versus what comes after",
    ("N", "POLARITY"):   "energetic direction — toward gain or toward cost",
    ("N", "MAGNITUDE"):  "load — how much energy is involved in this purpose",
    ("N", "COST"):       "sustainability — what can be maintained versus what burns out",
    ("N", "DIFFERENCE"): "trade-off — what is given up in exchange for what is gained",
    ("B", "POLARITY"):   "semantic polarity — affirm or negate the meaning claim",
    ("B", "MAGNITUDE"):  "clarity — how defined versus how ambiguous the meaning is",
    ("B", "COST"):       "meaning obligation — what this means and cannot mean otherwise",
    ("B", "DIFFERENCE"): "frame — inside versus outside this meaning boundary",
    ("A", "POLARITY"):   "ownership stance — claimed versus disclaimed agency",
    ("A", "MAGNITUDE"):  "agency weight — how much Aurora owns this action or statement",
    ("A", "COST"):       "accountability modal — what she must answer for",
    ("A", "DIFFERENCE"): "authority limit — what falls within versus outside her agency",
}

_DIM_TO_POSITION: Dict[str, str] = {
    "POLARITY":   "pre-verbal",
    "MAGNITUDE":  "pre-nominal",
    "COST":       "post-verbal",
    "DIFFERENCE": "boundary",
}

# Tier 1 domain character templates per cluster_pair component
_CLUSTER_ROLE: Dict[str, str] = {
    "ORIENTATION": "directional",
    "INTENSITY":   "degree-weighted",
    "ECONOMY":     "cost-efficient",
    "CROSS_RULE":  "rule-crossing",
    "IDENTITY":    "self-referential",
}

_DIM_ROLE: Dict[str, str] = {
    "POLARITY":   "orientation",
    "MAGNITUDE":  "intensity",
    "OPERATOR":   "operation",
    "COST":       "cost-bearing",
    "DIFFERENCE": "boundary-defining",
}

# ─────────────────────────────────────────────────────────────────────────────
# § 12  OETS QUERY PROFILE DERIVATION TABLES
# ─────────────────────────────────────────────────────────────────────────────

def _derive_clause_i(depth_score: float) -> str:
    if depth_score >= 0.80:
        return "I-A"
    if depth_score >= 0.40:
        return "I-B"
    if depth_score >= 0.10:
        return "I-D"
    return "I-C"


def _derive_clause_ii(leverage_class: str) -> str:
    return {"leverage": "II-A", "neutral": "II-B", "overhead": "II-C"}.get(
        leverage_class, "II-B"
    )


def _derive_accountability_band(aw: float) -> Dict[str, float]:
    if aw >= 0.70:
        return {"min": 0.6, "max": 1.0}
    if aw >= 0.40:
        return {"min": 0.3, "max": 0.7}
    return {"min": 0.0, "max": 0.45}


def _derive_cost_band(combined_cost: float) -> Dict[str, float]:
    if combined_cost <= 90:
        return {"min": 0.0, "max": 100.0}
    if combined_cost <= 150:
        return {"min": 75.0, "max": 175.0}
    if combined_cost <= 200:
        return {"min": 125.0, "max": 225.0}
    return {"min": 175.0, "max": 999.0}


def _derive_register(is_resonant: bool, depth_score: float,
                     accountability_weight: float, leverage_class: str) -> List[str]:
    if is_resonant and depth_score >= 0.80 and accountability_weight >= 0.70:
        return ["intimate", "formal"]
    if is_resonant and depth_score >= 0.40:
        return ["formal", "neutral"]
    if not is_resonant and depth_score >= 0.40:
        return ["neutral", "technical"]
    if depth_score < 0.40 and leverage_class == "leverage":
        return ["neutral", "colloquial"]
    return ["colloquial"]


def derive_oets_query_profile(slot: Dict[str, Any],
                               primary_domain: str) -> Dict[str, Any]:
    """
    Build the oets_query_profile for a single slot.
    primary_domain must be set to nc_target (per spec §11.3).
    All fields derived from §12 tables — no manual override.
    """
    depth  = slot.get("depth_score", 0.0)
    lev    = slot.get("leverage_class", "neutral")
    aw     = slot.get("accountability_weight", 0.0)
    cost   = slot.get("combined_cost", 0.0)
    res    = slot.get("is_resonant", False)
    cp     = slot.get("cluster_pair", "")

    return {
        "primary_domain":             primary_domain,
        "required_cluster_character": cp,
        "min_evolution_grade":        round(depth * 0.6, 4),
        "clause_i_floor":             _derive_clause_i(depth),
        "clause_ii_required":         _derive_clause_ii(lev),
        "accountability_band":        _derive_accountability_band(aw),
        "cost_band":                  _derive_cost_band(cost),
        "register_eligible":          _derive_register(res, depth, aw, lev),
        "resonance_required":         res,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN CHARACTER GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def _tier1_domain_character(slot: Dict[str, Any], nc: Dict[str, Any]) -> str:
    """
    Tier 1 — diagonal NonComp.  Every slot expresses some aspect of the
    anchor concept filtered through its cluster_pair.
    spec §14-T1-1, T1-2.
    """
    anchor   = nc.get("representational_anchor") or TIER1_ANCHOR_WORDS.get(nc.get("nc_law_c", "X"), "existence")
    cp       = slot.get("cluster_pair", "")
    is_anc   = slot.get("is_anchor", False)

    if is_anc:
        return (
            f"The canonical center of this NonComp — the primary anchor of the "
            f"{anchor} semantic field; all other slots in this NonComp derive "
            f"their character from proximity to this coordinate."
        )

    parts = cp.split(":", 1) if ":" in cp else [cp, cp]
    sub_c  = _CLUSTER_ROLE.get(parts[0], parts[0].lower())
    col_d  = _DIM_ROLE.get(parts[1] if len(parts) > 1 else "", "expressive")

    return (
        f"The {sub_c}, {col_d} expression of {anchor} — "
        f"a coordinate where {anchor.lower()} appears as "
        f"{sub_c} {col_d} pressure within the {nc.get('nc_domain', 'constraint')} domain."
    )


def _tier2_semantic_role_data(nc: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Returns (semantic_role, family_character, position_in_sentence) for a Tier 2 NC.
    spec §13.
    """
    dim    = nc.get("nc_dim", "")
    axis   = nc.get("nc_law_c", "X")
    role   = _DIM_TO_ROLE.get(dim, "modifier")
    fchar  = _FAMILY_CHARACTER.get((axis, dim), f"{axis}-family {dim.lower()} character")
    pos    = _DIM_TO_POSITION.get(dim, "modifier")
    return role, fchar, pos


def _tier3_domain_character(slot: Dict[str, Any], nc: Dict[str, Any]) -> str:
    """
    Tier 3 — cross-family NonComp.
    domain_character = "{cluster_pair interpretation} of {nc_semantic_summary}"
    spec §15-T3-2.
    Must be specific to this exact slot_id, distinct from adjacent slots.
    """
    nc_summary = nc.get("nc_semantic_summary", "the intersection of two constraint families")
    cp         = slot.get("cluster_pair", "")
    is_anc     = slot.get("is_anchor", False)
    law_c      = nc.get("nc_law_c", "?")
    target     = nc.get("nc_target", "?")
    nc_name    = nc.get("nc_name", "")

    if is_anc:
        return (
            f"Anchor slot for {nc_name}: the purest expression of "
            f"{nc_summary} — where {law_c}-law pressure acts most directly "
            f"on {target}-domain meaning."
        )

    parts  = cp.split(":", 1) if ":" in cp else [cp, cp]
    sub_c  = _CLUSTER_ROLE.get(parts[0], parts[0].lower())
    col_d  = _DIM_ROLE.get(parts[1] if len(parts) > 1 else "", "expressive")

    return (
        f"The {sub_c}, {col_d} mode of {nc_summary} — "
        f"{law_c}-law acting on {target}-domain content through "
        f"a {sub_c} sub-position and {col_d} column constraint."
    )


# ─────────────────────────────────────────────────────────────────────────────
# FGAE VIOLATION SCANNER  (spec §17)
# ─────────────────────────────────────────────────────────────────────────────

def scan_violations(nc: Dict[str, Any], tier: int) -> List[str]:
    """Return list of FGAE violation codes found in this NC."""
    violations: List[str] = []
    for slot in nc.get("slots", []):
        # V01 — phrase in word_or_phrase
        for entry in slot.get("semantic_entries", []):
            wp = entry.get("word_or_phrase", "")
            if " " in str(wp):
                violations.append(f"FGAE-V01:{slot.get('slot_id','?')}")

        # V09 — with_semantics but no oets_query_profile
        if slot.get("with_semantics") and not slot.get("oets_query_profile"):
            if tier != 2:  # Tier 2 gets semantic_role not oets_query_profile
                violations.append(f"FGAE-V09:{slot.get('slot_id','?')}")

        # V10 — Tier 2 slot has oets_query_profile instead of semantic_role
        if tier == 2 and slot.get("oets_query_profile"):
            violations.append(f"FGAE-V10:{slot.get('slot_id','?')}")

        # V03 — Tier 2 missing semantic_role
        if tier == 2 and not slot.get("semantic_role"):
            violations.append(f"FGAE-V03:{slot.get('slot_id','?')}")

        # V04 — Tier 1 anchor slot domain_character doesn't mention anchor word
        if tier == 1 and slot.get("is_anchor"):
            dc = slot.get("domain_character", "")
            anchor = nc.get("representational_anchor", "")
            if anchor and anchor.lower() not in dc.lower():
                violations.append(f"FGAE-V04:{slot.get('slot_id','?')}")

        # V05 — Tier 3 oets_query_profile.primary_domain != nc_target
        if tier == 3:
            qp = slot.get("oets_query_profile")
            if qp and qp.get("primary_domain") != nc.get("nc_target"):
                violations.append(f"FGAE-V05:{slot.get('slot_id','?')}")

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# NC FILE COMPILER
# ─────────────────────────────────────────────────────────────────────────────

def _classify_tier(nc: Dict[str, Any]) -> int:
    """Returns 1, 2, or 3 per spec §4."""
    is_diag   = nc.get("nc_is_diagonal", False)
    law_c     = nc.get("nc_law_c", "")
    nc_target = nc.get("nc_target", "")
    if is_diag and law_c == nc_target:
        return 1
    if (not is_diag) and law_c == nc_target:
        return 2
    return 3


def compile_nc_file(nc_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    Load one NC JSON, populate FGAE fields on every slot, return report.
    Writes file in place unless dry_run=True.
    """
    nc = json.loads(nc_path.read_text(encoding="utf-8"))
    tier = _classify_tier(nc)
    primary_domain = nc.get("nc_target", "X")
    nc_dim   = nc.get("nc_dim", "")
    nc_law_c = nc.get("nc_law_c", "X")

    modified_slots = 0
    for slot in nc.get("slots", []):
        changed = False

        if tier == 1:
            if not slot.get("domain_character"):
                slot["domain_character"] = _tier1_domain_character(slot, nc)
                changed = True
            if not slot.get("oets_query_profile"):
                slot["oets_query_profile"] = derive_oets_query_profile(slot, primary_domain)
                changed = True

        elif tier == 2:
            if not slot.get("semantic_role"):
                role, fchar, pos = _tier2_semantic_role_data(nc)
                slot["semantic_role"]       = role
                slot["family_character"]    = fchar
                slot["position_in_sentence"] = pos
                # Slot activation conditions (spec §13-T2-3)
                depth = slot.get("depth_score", 0.0)
                lev   = slot.get("leverage_class", "neutral")
                if depth >= 0.5:
                    slot["activation_condition"] = "obligatory"
                elif lev == "overhead":
                    slot["activation_condition"] = "high_cost_only"
                else:
                    slot["activation_condition"] = "optional"
                changed = True
            # Tier 2 must NOT have oets_query_profile (V10)
            if "oets_query_profile" in slot:
                del slot["oets_query_profile"]
                changed = True

        else:  # tier 3
            if not slot.get("domain_character"):
                slot["domain_character"] = _tier3_domain_character(slot, nc)
                changed = True
            if not slot.get("oets_query_profile"):
                slot["oets_query_profile"] = derive_oets_query_profile(slot, primary_domain)
                changed = True

        # Ensure with_semantics is stamped
        if not slot.get("with_semantics"):
            slot["with_semantics"] = True
            changed = True

        if changed:
            modified_slots += 1

    # Mark NC-level fields
    nc["with_semantics"] = True
    nc["fgae_tier"] = tier

    violations = scan_violations(nc, tier)

    if not dry_run:
        tmp = nc_path.with_suffix(".json.fgae_tmp")
        tmp.write_text(json.dumps(nc, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(nc_path)

    return {
        "nc_name":        nc.get("nc_name", str(nc_path)),
        "tier":           tier,
        "modified_slots": modified_slots,
        "violations":     violations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MASTER COMPILER  —  entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_manifold_semantics_compile(dry_run: bool = False,
                                   verbose: bool = True) -> Dict[str, Any]:
    """
    Iterate all 125 NC files across all 5 axes, populate FGAE fields,
    update _index.json, return a full report.

    Args:
        dry_run:  if True, compute but do not write files.
        verbose:  if True, print progress.

    Returns:
        Report dict with counts, violations, and timestamp.
    """
    if not _MANIFOLD_DIR.exists():
        raise FileNotFoundError(f"Manifold directory not found: {_MANIFOLD_DIR}")

    report: Dict[str, Any] = {
        "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "dry_run":        dry_run,
        "total_nc":       0,
        "total_slots":    0,
        "modified_slots": 0,
        "tier_counts":    {1: 0, 2: 0, 3: 0},
        "violations":     [],
        "nc_reports":     [],
    }

    for axis in AXES:
        axis_dir = _MANIFOLD_DIR / axis
        if not axis_dir.is_dir():
            continue
        for nc_file in sorted(axis_dir.glob("*.json")):
            try:
                nc_report = compile_nc_file(nc_file, dry_run=dry_run)
                report["total_nc"] += 1
                report["modified_slots"] += nc_report["modified_slots"]
                report["tier_counts"][nc_report["tier"]] += 1
                report["violations"].extend(nc_report["violations"])
                report["nc_reports"].append(nc_report)
                if verbose:
                    print(
                        f"  [{nc_report['tier']}] {nc_report['nc_name']:50s} "
                        f"+{nc_report['modified_slots']:4d} slots"
                        + (f"  VIOLATIONS: {nc_report['violations']}"
                           if nc_report["violations"] else "")
                    )
            except Exception as exc:
                import traceback as _tb
                print(f"  ERROR compiling {nc_file.name}: {exc}")
                _tb.print_exc()

    # Count total slots from index
    if _INDEX_PATH.exists():
        try:
            idx = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
            report["total_slots"] = idx.get("total_slots", 0)

            if not dry_run:
                idx["fgae_semantics_compiled"] = True
                idx["fgae_compile_timestamp"]  = report["timestamp"]
                idx["fgae_violation_count"]    = len(report["violations"])
                _INDEX_PATH.write_text(
                    json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except Exception as exc:
            print(f"  WARNING: could not update _index.json: {exc}")

    if verbose:
        print(
            f"\nFGAE Manifold Semantics Compile complete — "
            f"{report['total_nc']} NCs | "
            f"{report['modified_slots']} slots stamped | "
            f"{len(report['violations'])} violations"
        )

    return report


# ─────────────────────────────────────────────────────────────────────────────
# SLOT READER UTILITY  (used by FGAEEngine + FGAEOETSMapper)
# ─────────────────────────────────────────────────────────────────────────────

class FGAEManifoldReader:
    """
    Lightweight reader that loads NC files on demand and caches them.
    Used by the runtime FGAE engine to look up slot data without loading
    the full 78,125-slot manifold into memory at once.
    """

    def __init__(self, manifold_dir: Path = _MANIFOLD_DIR):
        self._dir   = manifold_dir
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._index: Optional[List[Dict[str, Any]]] = None

    def _load_index(self) -> List[Dict[str, Any]]:
        if self._index is None:
            idx = json.loads((_MANIFOLD_DIR / "_index.json").read_text(encoding="utf-8"))
            self._index = idx.get("entries", [])
        return self._index

    def get_nc(self, nc_name: str) -> Optional[Dict[str, Any]]:
        if nc_name in self._cache:
            return self._cache[nc_name]
        for entry in self._load_index():
            if entry.get("nc_name") == nc_name:
                path = self._dir / entry["file"]
                if path.exists():
                    nc = json.loads(path.read_text(encoding="utf-8"))
                    self._cache[nc_name] = nc
                    return nc
        return None

    def get_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Find a slot by slot_id across all cached / indexed NC files."""
        # slot_id format: NC_MANIFOLD:{nc_name}:{...}
        try:
            nc_name = slot_id.split(":")[1]
        except IndexError:
            return None
        nc = self.get_nc(nc_name)
        if not nc:
            return None
        for slot in nc.get("slots", []):
            if slot.get("slot_id") == slot_id:
                return slot
        return None

    def iter_nc_entries(self):
        """Yield (entry_dict, nc_dict) for all 125 NCs."""
        for entry in self._load_index():
            nc = self.get_nc(entry["nc_name"])
            if nc:
                yield entry, nc

    def tier_of(self, nc: Dict[str, Any]) -> int:
        return _classify_tier(nc)

    def anchor_words(self) -> Dict[str, str]:
        return dict(TIER1_ANCHOR_WORDS)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    print(f"FGAE Manifold Semantics Compiler  {'[DRY RUN]' if dry else ''}")
    print(f"Manifold dir: {_MANIFOLD_DIR}\n")
    report = run_manifold_semantics_compile(dry_run=dry, verbose=True)
    print(f"\nTier breakdown: {report['tier_counts']}")
    if report["violations"]:
        print(f"\nViolations ({len(report['violations'])}):")
        for v in report["violations"][:20]:
            print(f"  {v}")
