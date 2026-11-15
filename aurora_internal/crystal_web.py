# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The concept web: look up and walk her concept crystals (Sir, 2026-11-15).

A read-only view over the ONE crystal store (`dps_crystals.json`).  It never imports Aurora's stack and never writes: it is what the desktop subsurface hub
shows of what she knows, as a searchable web.

  * `search(text)`            concepts ranked by how the text matches them (exact, a labelled name's word, prefix, word, anywhere), then by how much each carries.
  * `lookup(name)`            everything a crystal holds, grouped: level and maturity, facets by kind, placed evidence (`fk:`), ties by name, interior layers, provenance.
  * `neighborhood(name, ...)` the web around a concept: its strongest ties outward, `depth` steps, bounded in nodes, with the ties among them.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from aurora_internal.crystal_store import canonical

LEVELS = {1: "BASE", 2: "COMPOSITE", 3: "FULL_CONCEPT", 4: "QUASI"}
MAX_TEXT = 200
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def _short(v: Any, n: int = MAX_TEXT) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
    return s if len(s) <= n else s[: n - 1] + "…"


def _group_of(role: str) -> str:
    r = str(role)
    if r.startswith("fk:"):
        return "evidence"
    if r.startswith("provenance:"):
        return "provenance"
    for head in ("lexicon", "oets", "hyp", "rep", "word", "sensory", "genealogy", "relief_event", "cers_visit", "topic"):
        if r == head or r.startswith(head + ":") or r.startswith(head + "_"):
            return head
    return "other"


class ConceptWeb:
    def __init__(self, crystals: Mapping[str, Mapping[str, Any]]) -> None:
        self._c = dict(crystals)
        self._name: Dict[str, str] = {cid: str(c.get("concept", "")) for cid, c in self._c.items()}
        self._by: Dict[str, str] = {}
        for cid, name in self._name.items():
            self._by.setdefault(name.lower(), cid)
        self._nb: Dict[str, Dict[str, float]] = {}
        for cid, c in self._c.items():                       # a tie is as strong as the stronger of its two sides
            for other, s in (c.get("connections") or {}).items():
                if other in self._c and other != cid:
                    s = float(s)
                    self._nb.setdefault(cid, {})[other] = max(self._nb.get(cid, {}).get(other, 0.0), s)
                    self._nb.setdefault(other, {})[cid] = max(self._nb.get(other, {}).get(cid, 0.0), s)

    # -- loading --------------------------------------------------------------------------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: str) -> "ConceptWeb":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(data.get("crystals", data) if isinstance(data, dict) else {})

    @classmethod
    def from_state_dir(cls, state_dir: str) -> "ConceptWeb":
        return cls.from_file(os.path.join(state_dir, "dps_crystals.json"))

    def __len__(self) -> int:
        return len(self._c)

    # -- finding ----------------------------------------------------------------------------------------------------------------------------------------
    def resolve(self, name: str) -> Optional[str]:
        """A crystal id for a name: exact, then (for a word under a bookkeeping label) the word, then case-insensitively."""
        n = str(name or "").strip()
        if n in self._name:
            return n
        for key in (n.lower(), canonical(n)[0].lower()):
            if key in self._by:
                return self._by[key]
        return None

    def _weight(self, cid: str) -> float:
        c = self._c[cid]
        return float(c.get("usage_count") or 0) + len(self._nb.get(cid, {})) + 0.5 * len(c.get("facets") or {})

    def search(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = str(text or "").strip().lower()
        if not q:
            return []
        qbare = canonical(q)[0].lower()
        hits: List[Tuple[int, float, str, str]] = []
        for cid, name in self._name.items():
            low = name.lower()
            if low == q:
                tier = 0
            elif low == qbare:
                tier = 1
            elif low.startswith(q):
                tier = 2
            elif q in _WORD.findall(low):
                tier = 3
            elif q in low:
                tier = 4
            else:
                continue
            hits.append((tier, -self._weight(cid), name, cid))
        hits.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
        out = []
        for tier, _w, name, cid in hits[: max(1, min(int(limit), 100))]:
            c = self._c[cid]
            out.append({"id": cid, "concept": name, "level": int(c.get("level") or 1), "usage": int(c.get("usage_count") or 0), "ties": len(self._nb.get(cid, {})),
                        "match": ("exact", "word", "prefix", "whole word", "contains")[tier]})
        return out

    # -- one crystal ------------------------------------------------------------------------------------------------------------------------------------
    def lookup(self, name: str, top_ties: int = 40) -> Optional[Dict[str, Any]]:
        cid = self.resolve(name)
        if cid is None:
            return None
        c = self._c[cid]
        level = int(c.get("level") or 1)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        evidence: List[Dict[str, Any]] = []
        for f in (c.get("facets") or {}).values():
            role, content = str(f.get("role", "")), f.get("content")
            g = _group_of(role)
            if g == "evidence" and isinstance(content, dict):
                for e in content.get("entries") or []:
                    evidence.append({"kind": role[3:], "key": _short(e.get("key", ""), 80), "content": _short(e.get("content", "")), "degree": round(float(e.get("degree", 0.0)), 4)})
                continue
            groups.setdefault(g, []).append({"role": role, "content": _short(content), "confidence": round(float(f.get("confidence", 0.0)), 3)})
        for rows in groups.values():
            rows.sort(key=lambda r: (-r["confidence"], r["role"], r["content"]))
        evidence.sort(key=lambda e: (-e["degree"], e["kind"], e["key"]))
        ties = sorted(({"concept": self._name[o], "id": o, "strength": round(s, 4), "level": int(self._c[o].get("level") or 1)} for o, s in self._nb.get(cid, {}).items()),
                      key=lambda t: (-t["strength"], t["concept"]))
        mat = c.get("maturity")
        standing = None
        if isinstance(mat, dict):
            try:
                from aurora_internal.crystal_maturity import memberships
                standing = {str(k): round(float(v), 4) for k, v in memberships(mat).items()}
            except Exception:
                standing = None
        interior = c.get("interior") or {}
        layers = [{"anchor": l.get("anchor"), "members": sorted((l.get("members") or {}), key=lambda m: (-l["members"][m], m)), "weight": l.get("weight"),
                   "inner": len(l.get("inner") or [])} for l in (interior.get("layers") or [])]
        return {"id": cid, "concept": self._name[cid], "level": level, "level_name": LEVELS.get(level, str(level)), "usage": int(c.get("usage_count") or 0),
                "maturity": ({k: (None if v is None else round(float(v), 4)) for k, v in mat.items()} if isinstance(mat, dict) else None), "standing": standing,
                "facets": groups, "evidence": evidence[:60], "ties": ties[: max(1, int(top_ties))], "tie_count": len(ties),
                "interior": {"depth": int(interior.get("depth") or 0), "standing": interior.get("standing"), "layers": layers}}

    # -- the web ------------------------------------------------------------------------------------------------------------------------------------------
    def neighborhood(self, name: str, depth: int = 1, max_nodes: int = 60, fan: int = 12) -> Optional[Dict[str, Any]]:
        """The concept and its strongest ties outward, `depth` steps (at most 3), at most `max_nodes` concepts, with every tie among them."""
        root = self.resolve(name)
        if root is None:
            return None
        depth, max_nodes, fan = max(1, min(int(depth), 3)), max(2, min(int(max_nodes), 300)), max(1, min(int(fan), 40))
        seen: Dict[str, int] = {root: 0}
        frontier = [root]
        for d in range(1, depth + 1):
            nxt: List[str] = []
            for cid in frontier:
                for other, _ in sorted(self._nb.get(cid, {}).items(), key=lambda kv: (-kv[1], self._name[kv[0]]))[:fan]:
                    if other not in seen and len(seen) < max_nodes:
                        seen[other] = d
                        nxt.append(other)
            frontier = nxt
        edges, done = [], set()
        for a in seen:
            for b, s in self._nb.get(a, {}).items():
                if b in seen and (b, a) not in done:
                    done.add((a, b))
                    edges.append({"a": a, "b": b, "strength": round(s, 4)})
        edges.sort(key=lambda e: (-e["strength"], e["a"], e["b"]))
        nodes = [{"id": cid, "concept": self._name[cid], "depth": d, "level": int(self._c[cid].get("level") or 1), "usage": int(self._c[cid].get("usage_count") or 0),
                  "ties": len(self._nb.get(cid, {}))} for cid, d in sorted(seen.items(), key=lambda kv: (kv[1], self._name[kv[0]]))]
        return {"root": root, "nodes": nodes, "edges": edges, "truncated": len(seen) >= max_nodes}

    def overview(self, top: int = 40) -> Dict[str, Any]:
        """The shape of the whole store at a glance: how many crystals at each level, how many carry ties, and the most connected concepts."""
        by_level: Dict[str, int] = {}
        for c in self._c.values():
            k = LEVELS.get(int(c.get("level") or 1), "?")
            by_level[k] = by_level.get(k, 0) + 1
        hubs = sorted(self._nb, key=lambda cid: (-len(self._nb[cid]), self._name[cid]))[: max(1, int(top))]
        return {"crystals": len(self._c), "with_ties": len(self._nb), "levels": by_level,
                "hubs": [{"id": cid, "concept": self._name[cid], "ties": len(self._nb[cid]), "level": int(self._c[cid].get("level") or 1)} for cid in hubs]}
