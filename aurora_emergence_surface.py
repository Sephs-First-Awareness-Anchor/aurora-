#!/usr/bin/env python3
"""
AURORA EMERGENCE SURFACE
========================
Watches the constraint genealogy for newly promoted Links and surfaces them
as operational capabilities without hand-programming.

Per ACMS §VII (Language System Rebuild) and §9 (Learning and Evolution):
  - Evolution = constraint reinforcement, not feature addition
  - Skills form when recurring pressure-relief patterns are strong enough to
    become stable promoted Links in the genealogy
  - Once promoted, a Link IS an ability; this module makes it operational

The path:
    genealogy.observe() → pair accumulation → Link promoted →
    _register_link_ability() → EmergenceMonitor.tick() discovers it →
    OETS concept added → emergence manifest written →
    ability is now part of Aurora's conceptual vocabulary

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

_AXES = ("X", "T", "N", "B", "A")

# Map dominant relief axis to a human-readable operational label that can seed
# OETS concept nodes.  These are starting points; the full character of the
# emerged ability comes from its effect_tags.
_AXIS_CONCEPT_PREFIX = {
    "X": "grounding",
    "T": "sequencing",
    "N": "compression",
    "B": "containment",
    "A": "enacting",
}


class EmergenceMonitor:
    """
    Discovers newly promoted constraint Links and surfaces them as operational
    capabilities.

    On each tick():
      1. Detects new promoted links by comparing links_promoted counter
      2. For each new link, reads its AbilityProfile from genealogy.abilities
      3. Writes the ability to the emerged_abilities manifest (persistent)
      4. Registers the ability's semantic character with OETS so Aurora can
         reason about and express the new capability
    """

    def __init__(
        self,
        genealogy: Any,
        oets: Optional[Any] = None,
        state_dir: str = "aurora_state",
    ) -> None:
        self._genealogy = genealogy
        self._oets = oets
        self._state_dir = state_dir
        self._manifest_path = os.path.join(state_dir, "emerged_abilities.json")
        self._candidate_path = os.path.join(state_dir, "emergence_candidates.json")
        self._status_path = os.path.join(state_dir, "emergence_monitor_status.json")
        self._emerged: Dict[str, dict] = {}
        self._candidates: Dict[str, dict] = {}
        self._last_link_count: int = 0
        self._suspend_manifest_save = False
        self._suspend_candidate_save = False
        self._load_manifest()

    # ── public ────────────────────────────────────────────────────────────────

    def tick(self) -> List[str]:
        """
        Surface newly operational abilities.

        Link-derived abilities are operational when the genealogy promotes the
        link. Code/manual-derived abilities are stable when the genealogy says
        they were accepted/adopted. High-confidence rejected dream/code records
        are surfaced as transient pressure abilities: constraint-real enough to
        learn from and route around, but not presented as persisted source-code
        implementations. Real does not mean permanent here; persistence is a
        separate stability claim.
        """
        current_count = int(getattr(self._genealogy, "links_promoted", 0) or 0)
        new_ids: List[str] = []
        self._suspend_manifest_save = True
        self._suspend_candidate_save = True
        try:
            links = getattr(self._genealogy, "links", {}) or {}
            for link in links.values():
                aid = self._ability_id_for_link(link)
                if aid is None or aid in self._emerged:
                    continue
                ability = (getattr(self._genealogy, "abilities", {}) or {}).get(aid)
                if ability is None:
                    continue
                self._surface(link, ability, aid, source="promoted_link", operational_status="operational")
                new_ids.append(aid)

            abilities = getattr(self._genealogy, "abilities", {}) or {}
            transient_surfaced = 0
            max_transient_per_tick = 128
            for aid, ability in list(abilities.items()):
                aid = str(aid or "")
                if not aid or aid in self._emerged:
                    continue
                status = self._ability_operational_status(aid, ability)
                if status in {"operational", "transient"}:
                    if status == "transient":
                        if transient_surfaced >= max_transient_per_tick:
                            self._record_candidate(aid, ability, "latent_transient_backlog")
                            continue
                        transient_surfaced += 1
                    self._surface(None, ability, aid, source="ability_record", operational_status=status)
                    new_ids.append(aid)
                elif status.startswith("latent"):
                    self._record_candidate(aid, ability, status)
        finally:
            self._last_link_count = current_count
            self._suspend_manifest_save = False
            self._suspend_candidate_save = False
        if new_ids:
            self._save_manifest()
        if self._candidates:
            self._save_candidates()
        self._save_status(new_ids)
        return new_ids

    def status(self) -> Dict[str, Any]:
        emerged_values = list(self._emerged.values())
        candidate_values = list(self._candidates.values())
        return {
            "emerged_count": len(self._emerged),
            "candidate_count": len(self._candidates),
            "watched_link_count": self._last_link_count,
            "operational_count": sum(1 for item in emerged_values if item.get("operational_status") == "operational"),
            "transient_count": sum(1 for item in emerged_values if item.get("operational_status") == "transient"),
            "runtime_operationalized_count": sum(1 for item in emerged_values if item.get("operationalized_in_runtime") is True),
            "source_code_implemented_count": sum(1 for item in emerged_values if item.get("implemented_in_code") is True),
            "latent_candidate_count": sum(1 for item in candidate_values if str(item.get("operational_status", "")).startswith("latent")),
            "ability_ids": list(self._emerged.keys()),
            "candidate_ids": list(self._candidates.keys())[-50:],
        }

    # ── internal ──────────────────────────────────────────────────────────────

    def _ability_id_for_link(self, link: Any) -> Optional[str]:
        try:
            if hasattr(self._genealogy, "_link_ability_id"):
                return self._genealogy._link_ability_id(link)
            axis = str(getattr(link, "dominant_relief_axis", "X") or "X").upper()
            suffix = str(getattr(link, "id", "")).replace(":", "_")
            return f"{axis}:LINK_{suffix}"
        except Exception:
            return None

    def _ability_value(self, ability: Any, key: str, default: Any = None) -> Any:
        if isinstance(ability, dict):
            return ability.get(key, default)
        return getattr(ability, key, default)

    def _ability_tags(self, ability: Any) -> List[str]:
        return [str(t) for t in list(self._ability_value(ability, "effect_tags", []) or []) if str(t)]

    def _tag_value(self, tags: List[str], prefix: str, default: str = "") -> str:
        for tag in tags:
            if str(tag).startswith(prefix):
                return str(tag).split(":", 1)[1]
        return default

    def _tag_int(self, tags: List[str], prefix: str, default: int = 0) -> int:
        raw = self._tag_value(tags, prefix, "")
        try:
            return int(float(raw))
        except Exception:
            return int(default)

    def _tag_float(self, tags: List[str], prefix: str, default: float = 0.0) -> float:
        raw = self._tag_value(tags, prefix, "")
        try:
            return float(raw)
        except Exception:
            return float(default)

    def _ability_operational_status(self, aid: str, ability: Any) -> str:
        tags = self._ability_tags(ability)
        tag_set = set(tags)
        if ":LINK_" in aid:
            return "operational"
        if ":CODE_LINEAGE_" in aid or "manual_code_lineage" in tag_set:
            return "operational"
        if ":CODE_EVOLVE_" in aid or "code_evolution" in tag_set:
            mutation_status = self._tag_value(tags, "mutation_status:", "unknown")
            changed_files = self._tag_int(tags, "mutation_changed_files:", 0)
            targets = self._tag_int(tags, "mutation_targets:", 0)
            mutation_score = self._tag_float(tags, "mutation_score:", 0.0)
            promotion_weight = self._tag_float(tags, "promotion_weight:", mutation_score)
            if mutation_status == "accepted" and (changed_files > 0 or targets > 0):
                return "operational"
            if mutation_score >= 0.95 or promotion_weight >= 0.95:
                return "transient"
            return f"latent_{mutation_status or 'candidate'}"
        if "adaptive_compression" in tag_set:
            return "operational"
        return "base_or_unpromoted"

    def _surface(
        self,
        link: Any,
        ability: Any,
        aid: str,
        *,
        source: str,
        operational_status: str,
    ) -> None:
        dominant = str(self._ability_value(ability, "axis", "X") or "X").upper()
        tags = self._ability_tags(ability)
        depth = int(getattr(link, "depth", 1) or 1) if link is not None else 1
        count = int(getattr(link, "count", 0) or 0) if link is not None else 1
        mean_relief = dict(getattr(link, "mean_relief", {}) or {}) if link is not None else {}
        cost = dict(self._ability_value(ability, "cost", {}) or {})
        risk = dict(self._ability_value(ability, "risk", {}) or {})
        implementation = self._implementation_metadata(aid, tags, source, operational_status)

        self._emerged[aid] = {
            "id": aid,
            "dominant_axis": dominant,
            "effect_tags": tags,
            "link_depth": depth,
            "link_count": count,
            "mean_relief": {a: round(float(mean_relief.get(a, 0.0)), 6) for a in _AXES},
            "cost": {a: round(float(cost.get(a, 0.0)), 8) for a in _AXES},
            "risk": {a: round(float(risk.get(a, 0.0)), 8) for a in _AXES},
            "source": source,
            "operational_status": operational_status,
            **implementation,
            "emerged_at": round(time.time(), 3),
        }
        if not self._suspend_manifest_save:
            self._save_manifest()
        self._register_with_oets(aid, dominant, tags, mean_relief)

    def _record_candidate(self, aid: str, ability: Any, status: str) -> None:
        if aid in self._candidates:
            self._candidates[aid] = self._normalize_candidate_entry(aid, self._candidates[aid])
            return
        tags = self._ability_tags(ability)
        self._candidates[aid] = {
            "id": aid,
            "dominant_axis": str(self._ability_value(ability, "axis", "X") or "X").upper(),
            "effect_tags": tags[:24],
            "operational_status": status,
            "reality_status": "latent",
            "stability_state": "latent",
            "persistence_claim": "not_active",
            "evidence_basis": "latent_evolution_candidate",
            "implemented_in_code": False,
            "operationalized_in_runtime": False,
            "mutation_status": self._tag_value(tags, "mutation_status:", ""),
            "mutation_score": self._tag_value(tags, "mutation_score:", ""),
            "mutation_changed_files": self._tag_int(tags, "mutation_changed_files:", 0),
            "mutation_targets": self._tag_int(tags, "mutation_targets:", 0),
            "observed_at": round(time.time(), 3),
        }
        # Keep this as a bounded diagnostic surface, not a second giant genealogy.
        if len(self._candidates) > 2000:
            keep = list(self._candidates.items())[-2000:]
            self._candidates = dict(keep)
        if not self._suspend_candidate_save:
            self._save_candidates()

    def _implementation_metadata(
        self,
        aid: str,
        tags: List[str],
        source: str,
        operational_status: str,
    ) -> Dict[str, Any]:
        source_code_implemented = False
        evidence_basis = "surfaced_constraint_record"
        if ":CODE_LINEAGE_" in aid or "manual_code_lineage" in set(tags):
            source_code_implemented = True
            evidence_basis = "manual_code_lineage"
        elif ":CODE_EVOLVE_" in aid or "code_evolution" in set(tags):
            mutation_status = self._tag_value(tags, "mutation_status:", "unknown")
            changed_files = self._tag_int(tags, "mutation_changed_files:", 0)
            targets = self._tag_int(tags, "mutation_targets:", 0)
            source_code_implemented = mutation_status == "accepted" and (changed_files > 0 or targets > 0)
            evidence_basis = "accepted_code_evolution" if source_code_implemented else "high_confidence_evolution_pressure"
        elif source == "promoted_link":
            evidence_basis = "promoted_genealogy_link"
        elif "adaptive_compression" in set(tags):
            evidence_basis = "adaptive_compression"

        return {
            "reality_status": "constraint_real" if operational_status in {"operational", "transient"} else "latent",
            "implemented_in_code": bool(source_code_implemented),
            "operationalized_in_runtime": bool(operational_status in {"operational", "transient"}),
            "stability_state": "stable" if operational_status == "operational" else "transient",
            "persistence_claim": "persistent" if operational_status == "operational" else "unstable_nonpersistent",
            "evidence_basis": evidence_basis,
        }

    def _register_with_oets(
        self,
        aid: str,
        dominant_axis: str,
        tags: List[str],
        mean_relief: Dict[str, float],
    ) -> None:
        """
        Add the emerged ability to Aurora's OETS semantic web so she can reason
        about and express it.  Registers as a verb node (it's a capability,
        something she can do) with valence proportional to total relief.
        """
        if self._oets is None:
            return
        try:
            concept_name = self._concept_name(aid, tags, dominant_axis)
            valence = min(1.0, sum(max(0.0, float(mean_relief.get(a, 0.0))) for a in _AXES))
            meaning = self._meaning(dominant_axis, tags)
            lineage_tag = f"emerged:{aid}"

            oets_web = getattr(self._oets, "web", None)
            if oets_web is not None and hasattr(oets_web, "add_node"):
                oets_web.add_node(
                    concept_name,
                    role="verb",
                    valence=valence,
                    meaning=meaning,
                    lineage=lineage_tag,
                )
            # Also try the higher-level grounding API if available
            if hasattr(self._oets, "ground"):
                self._oets.ground(concept_name, meaning)
        except Exception:
            pass

    def _concept_name(self, aid: str, tags: List[str], dominant_axis: str) -> str:
        skip = {"derived_link", "composite", "derived_operation",
                "derived_from_link", "lineage_reinforced"}
        for tag in tags:
            t = str(tag).lower()
            if t and t not in skip:
                return t.replace("_", " ")
        prefix = _AXIS_CONCEPT_PREFIX.get(dominant_axis, "operating")
        suffix = aid.split("_")[-1][:6] if "_" in aid else aid[-6:]
        return f"{prefix} {suffix}"

    def _meaning(self, dominant_axis: str, tags: List[str]) -> str:
        skip = {"derived_link", "composite", "derived_operation"}
        tag_str = ", ".join(
            str(t) for t in tags[:3] if str(t).lower() not in skip
        )
        prefix = _AXIS_CONCEPT_PREFIX.get(dominant_axis, "operating")
        if tag_str:
            return f"emergent {prefix} capability: {tag_str}"
        return f"emergent {dominant_axis}-axis operational mode"

    def _load_manifest(self) -> None:
        try:
            if os.path.exists(self._manifest_path):
                with open(self._manifest_path, encoding="utf-8") as f:
                    self._emerged = json.load(f)
                if isinstance(self._emerged, dict):
                    self._emerged = {
                        str(aid): self._normalize_emerged_entry(str(aid), entry)
                        for aid, entry in self._emerged.items()
                        if isinstance(entry, dict)
                    }
                else:
                    self._emerged = {}
                self._last_link_count = len(self._emerged)
        except Exception:
            self._emerged = {}
            self._last_link_count = 0
        try:
            if os.path.exists(self._candidate_path):
                with open(self._candidate_path, encoding="utf-8") as f:
                    self._candidates = json.load(f)
                if isinstance(self._candidates, dict):
                    self._candidates = {
                        str(aid): self._normalize_candidate_entry(str(aid), entry)
                        for aid, entry in self._candidates.items()
                        if isinstance(entry, dict)
                    }
                else:
                    self._candidates = {}
        except Exception:
            self._candidates = {}

    def _normalize_emerged_entry(self, aid: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        tags = [str(t) for t in list(entry.get("effect_tags", []) or []) if str(t)]
        status = str(entry.get("operational_status") or "")
        source = str(entry.get("source") or "")
        if not status:
            status = "operational" if ":LINK_" in aid else self._ability_operational_status(aid, entry)
        if not source:
            source = "promoted_link" if ":LINK_" in aid else "ability_record"
        merged = dict(entry)
        merged.setdefault("source", source)
        merged.setdefault("operational_status", status)
        for key, value in self._implementation_metadata(aid, tags, source, status).items():
            merged.setdefault(key, value)
        return merged

    def _normalize_candidate_entry(self, aid: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(entry)
        merged.setdefault("reality_status", "latent")
        merged.setdefault("stability_state", "latent")
        merged.setdefault("persistence_claim", "not_active")
        merged.setdefault("evidence_basis", "latent_evolution_candidate")
        merged.setdefault("implemented_in_code", False)
        merged.setdefault("operationalized_in_runtime", False)
        return merged

    def _save_manifest(self) -> None:
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            tmp = self._manifest_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._emerged, f, indent=2)
            os.replace(tmp, self._manifest_path)
        except Exception:
            pass

    def _save_candidates(self) -> None:
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            self._candidates = {
                str(aid): self._normalize_candidate_entry(str(aid), entry)
                for aid, entry in self._candidates.items()
                if isinstance(entry, dict)
            }
            tmp = self._candidate_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._candidates, f, indent=2)
            os.replace(tmp, self._candidate_path)
        except Exception:
            pass

    def _save_status(self, new_ids: List[str]) -> None:
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            payload = {
                "updated_at": round(time.time(), 3),
                "emerged_count": len(self._emerged),
                "candidate_count": len(self._candidates),
                "new_emerged_ids": list(new_ids or [])[-50:],
                "new_operational_ids": [
                    aid for aid in list(new_ids or [])[-50:]
                    if (self._emerged.get(aid) or {}).get("operational_status") == "operational"
                ],
                "new_transient_ids": [
                    aid for aid in list(new_ids or [])[-50:]
                    if (self._emerged.get(aid) or {}).get("operational_status") == "transient"
                ],
                "watched_link_count": int(self._last_link_count),
                "genealogy_ability_count": len(getattr(self._genealogy, "abilities", {}) or {}),
            }
            payload.update({k: v for k, v in self.status().items() if k.endswith("_count")})
            tmp = self._status_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self._status_path)
        except Exception:
            pass
