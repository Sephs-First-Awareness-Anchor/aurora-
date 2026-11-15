# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The lexicon, in the one crystal store (Sir, 2026-11-15).

`lexicon.json` was keyed by word AND by bookkeeping label (`learned:come` beside `come`), so a word had two entries and two crystals.  Here:

  * `fold_entries` / `fold_file`  one entry per word: the bare word's own fields win, a label's entry only fills what is blank, usage adds up, the more recent
    use is kept, and a real meaning is never replaced by a placeholder.  Nothing is dropped that carried information.
  * `place`                       what each entry knows goes to the facet it belongs to: the word's role and channel (`lexicon`), a real meaning (`definition`,
    never a bookkeeping placeholder), its valence (`emotion`).  Every one carries its true basis: a given meaning is `seeded`, a mapping reached through an
    i-state lineage is `unattributed`; neither is experience, so neither counts toward growth, and both stay visible on the crystal as `held:` facets.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Tuple

from aurora_internal.crystal_facets import FacetBook, content_key
from aurora_internal.crystal_store import canonical, is_placeholder_meaning

# a lexicon meaning that is a pointer or a label, not something said about the word
def is_real_meaning(word: str, text: Any) -> bool:
    return not is_placeholder_meaning(word, text)


def _blank(v: Any) -> bool:
    return v is None or v == "" or v == 0 or v == 0.0


def merge_entry(bare: Mapping[str, Any], other: Mapping[str, Any]) -> Dict[str, Any]:
    """The bare word's entry, with a label's entry filling blanks.  Usage adds, last use is the later, a real meaning outranks a placeholder."""
    out = dict(bare)
    for k in ("role", "lineage", "noncomp_id", "emotional_valence"):
        if _blank(out.get(k)) and not _blank(other.get(k)):
            out[k] = other[k]
    out["usage_count"] = int(bare.get("usage_count") or 0) + int(other.get("usage_count") or 0)
    out["last_used"] = max(float(bare.get("last_used") or 0.0), float(other.get("last_used") or 0.0))
    if not is_real_meaning("", out.get("meaning")) and is_real_meaning("", other.get("meaning")):
        out["meaning"] = other["meaning"]
    return out


def fold_entries(entries: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    """One entry per word.  Order-independent; a label whose word has no entry of its own becomes the word's entry."""
    out: Dict[str, Dict[str, Any]] = {}
    labelled = []
    for key, e in entries.items():
        bare = canonical(key)[0]
        if bare == key:
            out[key] = dict(e)
        else:
            labelled.append((bare, e))
    merged = renamed = 0
    for bare, e in sorted(labelled, key=lambda t: t[0]):
        if bare in out:
            out[bare] = merge_entry(out[bare], e)
            merged += 1
        else:
            out[bare] = dict(e)
            renamed += 1
    return out, {"merged": merged, "renamed": renamed, "entries": len(out)}


def read_entries(state_dir: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(os.path.join(str(state_dir), "lexicon.json"), "r", encoding="utf-8") as fh:
            d = json.load(fh)
        e = d.get("entries") if isinstance(d, dict) else None
        return {str(k): v for k, v in e.items() if isinstance(v, dict)} if isinstance(e, dict) else {}
    except (OSError, ValueError):
        return {}


def fold_file(state_dir: str) -> Dict[str, int]:
    """Fold `lexicon.json` in place (atomically) when it holds label-keyed entries.  Only for a lexicon nobody is holding in memory."""
    path = os.path.join(str(state_dir), "lexicon.json")
    with open(path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    folded, rep = fold_entries(d.get("entries") or {})
    if rep["merged"] or rep["renamed"]:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(d, entries=folded)))
        os.replace(tmp, path)
    return rep


def place(book: FacetBook, entries: Mapping[str, Mapping[str, Any]]) -> Dict[str, int]:
    """Put each (folded) entry's information into the facet book at its kind, each with the basis it really has."""
    n = {"lexicon": 0, "definition": 0, "emotion": 0}
    for word, e in entries.items():
        word = canonical(word)[0]
        seeded = not str(e.get("lineage") or "")
        src = "lexicon_seed" if seeded else "lexicon_lineage"
        role, nid = str(e.get("role") or ""), str(e.get("noncomp_id") or "")
        if role or nid:
            n["lexicon"] += bool(book.add(word, "lexicon", f"{role}|{nid}", {"role": role, "noncomp_id": nid, "lineage": str(e.get("lineage") or "")},
                                          ref=f"lexicon:{word}", source=src))
        text = " ".join(str(e.get("meaning") or "").split())
        if is_real_meaning(word, text):
            n["definition"] += bool(book.add(word, "definition", content_key(text), {"text": text}, ref=f"lexdef:{word}:{content_key(text)}", source=src))
        if float(e.get("emotional_valence") or 0.0):
            n["emotion"] += bool(book.add(word, "emotion", "valence", {"valence": float(e["emotional_valence"])}, ref=f"lexval:{word}", source=src))
    return n
