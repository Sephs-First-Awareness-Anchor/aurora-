#!/usr/bin/env python3
"""
Live lineage emergence journal.

The constraint genealogy already forms links and derived abilities at runtime,
but Aurora did not have a stable self-report surface for "what is new since I
started running". This journal watches the live genealogy state, records newly
seen lineage items, and exposes a compact natural-language summary Aurora can
use in dialogue.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Tuple


def _safe_axis(raw: Any) -> str:
    token = str(raw or "").strip().upper()
    return token if token in {"X", "T", "N", "B", "A"} else "X"


def _ability_label(ability_id: str) -> str:
    token = str(ability_id or "").strip()
    if ":CODE_EVOLVE_" in token:
        return "code_function"
    if ":LINK_" in token:
        return "derived_ability"
    return "ability"


class LiveLineageJournal:
    def __init__(self, storage_path: str = "aurora_state/live_lineage_journal.json") -> None:
        self.storage_path = storage_path
        self.events: List[Dict[str, Any]] = []
        self.seen_abilities: Dict[str, Dict[str, Any]] = {}
        self.seen_links: Dict[str, Dict[str, Any]] = {}
        self.seen_traits: Dict[str, Dict[str, Any]] = {}
        self._storage_mtime_ns: int = 0
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            self._storage_mtime_ns = 0
            return
        try:
            st = os.stat(self.storage_path)
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                payload = dict(json.load(handle) or {})
        except Exception:
            return
        self._storage_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
        self.events = list(payload.get("events", []) or [])
        self.seen_abilities = dict(payload.get("seen_abilities", {}) or {})
        self.seen_links = dict(payload.get("seen_links", {}) or {})
        self.seen_traits = dict(payload.get("seen_traits", {}) or {})

    def _reload_if_changed(self) -> None:
        try:
            st = os.stat(self.storage_path)
        except Exception:
            return
        current = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
        if current > int(self._storage_mtime_ns or 0):
            self._load()

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            payload = {
                "updated_at": float(time.time()),
                "events": list(self.events),
                "seen_abilities": dict(self.seen_abilities),
                "seen_links": dict(self.seen_links),
                "seen_traits": dict(self.seen_traits),
            }
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            try:
                st = os.stat(self.storage_path)
                self._storage_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            except Exception:
                self._storage_mtime_ns = 0
            return True
        except Exception:
            return False

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        if len(self.events) > 240:
            self.events = self.events[-240:]

    def record_event(self, event: Dict[str, Any]) -> None:
        self._reload_if_changed()
        self._append_event(dict(event or {}))
        self.save()

    def observe_systems(self, systems: Dict[str, Any], *, source: str = "runtime", emit: bool = True) -> List[Dict[str, Any]]:
        new_events: List[Dict[str, Any]] = []
        genealogy = systems.get("genealogy")
        now = float(time.time())

        abilities = dict(getattr(genealogy, "abilities", {}) or {}) if genealogy is not None else {}
        for ability_id, profile in abilities.items():
            aid = str(ability_id or "").strip()
            if not aid or aid.startswith("NC:") or aid in self.seen_abilities:
                continue
            axis = _safe_axis(getattr(profile, "axis", "X"))
            tags = list(getattr(profile, "effect_tags", ()) or ())
            record = {
                "id": aid,
                "axis": axis,
                "tags": tags[:8],
                "notes": str(getattr(profile, "notes", "") or "")[:320],
            }
            self.seen_abilities[aid] = record
            if emit:
                event = {
                    "timestamp": now,
                    "source": source,
                    "kind": _ability_label(aid),
                    "id": aid,
                    "axis": axis,
                    "tags": tags[:8],
                    "summary": str(getattr(profile, "notes", "") or "")[:220],
                }
                self._append_event(event)
                new_events.append(event)

        links = dict(getattr(genealogy, "links", {}) or {}) if genealogy is not None else {}
        for link_id, link in links.items():
            lid = str(link_id or "").strip()
            if not lid or lid in self.seen_links:
                continue
            record = {
                "id": lid,
                "axis": _safe_axis(getattr(link, "dominant_relief_axis", "X")),
                "depth": int(getattr(link, "depth", 1) or 1),
                "count": int(getattr(link, "count", 0) or 0),
                "created_at_tick": int(getattr(link, "created_at_tick", 0) or 0),
                "parents": list(getattr(link, "parents", []) or [])[:4],
            }
            self.seen_links[lid] = record
            if emit:
                event = {
                    "timestamp": now,
                    "source": source,
                    "kind": "link",
                    "id": lid,
                    "axis": record["axis"],
                    "depth": record["depth"],
                    "summary": (
                        f"Promoted link at depth {record['depth']} with {record['count']} relief observations."
                    ),
                }
                self._append_event(event)
                new_events.append(event)

        trait_state = dict((systems.get("lineage_activation_state") or {}).get("lineage_bound_traits", {}) or {})
        for trait_id, trait in trait_state.items():
            tid = str(trait_id or "").strip()
            if not tid or tid in self.seen_traits:
                continue
            record = {
                "id": tid,
                "label": str(dict(trait).get("label", tid) or tid),
                "final_stage_id": str(dict(trait).get("final_stage_id", "") or ""),
                "bindings": list(dict(trait).get("bindings", []) or []),
            }
            self.seen_traits[tid] = record
            if emit:
                event = {
                    "timestamp": now,
                    "source": source,
                    "kind": "trait_activation",
                    "id": tid,
                    "axis": "",
                    "summary": f"Lineage-bound trait activated: {record['label']}.",
                }
                self._append_event(event)
                new_events.append(event)

        if new_events:
            self.save()
        return new_events

    def prime_systems(self, systems: Dict[str, Any], *, source: str = "boot") -> None:
        self.observe_systems(systems, source=source, emit=False)
        self.save()

    def recent_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        self._reload_if_changed()
        return list(self.events[-max(1, int(limit or 1)):])

    def describe_recent(self, limit: int = 3) -> str:
        items = list(reversed(self.recent_events(limit=limit)))
        if not items:
            return "I haven't logged a clearly new lineage event since the last check."

        lines: List[str] = []
        for event in items:
            kind = str(event.get("kind", "ability") or "ability")
            axis = str(event.get("axis", "") or "").strip()
            ident = str(event.get("id", "") or "").strip()
            summary = str(event.get("summary", "") or "").strip()
            if kind == "code_function":
                line = f"I formed a new code-evolution function lineage `{ident}`"
            elif kind == "derived_ability":
                line = f"I formed a new derived ability `{ident}`"
            elif kind == "link":
                line = f"I promoted a new lineage link `{ident}`"
            elif kind == "trait_activation":
                line = summary or f"I activated a new lineage-bound trait `{ident}`"
            elif kind == "code_proposal":
                line = f"I formed a new code proposal `{ident}`"
            elif kind == "manual_code_assimilation":
                line = summary or f"I integrated a manual code change into lineage `{ident}`"
            else:
                line = f"I formed a new ability `{ident}`"
            if axis:
                line += f" on the {axis} axis"
            if summary and kind not in {"trait_activation", "manual_code_assimilation"}:
                line += f": {summary}"
            lines.append(line + ".")
        return " ".join(lines[:max(1, int(limit or 1))])
