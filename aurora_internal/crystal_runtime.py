# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The crystal pass, run against the live registry (Sir, 2026-11-15): every subsystem's stored data woven into the crystals it belongs to.

One call weaves what each subsystem has stored (the OETS web, the genealogy, her abilities, conversations, development, the waveform operations), reads her
word-use profiles and finds the classes of words that stand in for one another, places the lexical signals with the standing each earned, and writes the
result into the registry's crystals: links, facets by kind, and the maturity points that decide growth.  Generalizations that hold counted members get a
crystal of their own and stand above what they hold.  Everything is ADDITIVE (an existing facet or link is kept, the stronger value wins; nothing is
removed), and the whole pass is fail-safe: it never raises, so a failure cannot reach a turn or a save (whatever it had already written is additive and stays).

Called from `_full_save`, just before the registry is persisted, at most once per `MIN_INTERVAL` seconds.  `AURORA_CRYSTAL_WEAVE=0` turns it off.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Mapping, Optional

from aurora_internal import crystal_associations as _A
from aurora_internal import crystal_facets as _F
from aurora_internal import crystal_grammar as _G
from aurora_internal import crystal_interior as _I
from aurora_internal import crystal_sensory as _SN
from aurora_internal import crystal_promotion as _P
from aurora_internal import crystal_store as _CS
from aurora_internal import crystal_substitutability as _S
from aurora_internal import crystal_weave as _W

MIN_INTERVAL = 600.0        # seconds between passes
VOCAB = 150                 # the most-seen words considered for classes (bounds the cost)
CLASSES = 8                 # classes kept per pass (`top` only limits how many are kept)
LEX_ROLE = "hyp:lex:structure"
_WORD = re.compile(r"[a-z']+")
_last = {"t": None}


def enabled() -> bool:
    return str(os.environ.get("AURORA_CRYSTAL_WEAVE", "1")).strip().lower() not in ("0", "false", "off", "no")


def _read(state_dir: str, *parts: str) -> Any:
    try:
        with open(os.path.join(state_dir, *parts), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def word_profiles(crystals: Mapping[str, Any], state_dir: str) -> _S.ContextProfiles:
    """Her word-use profiles: her kept use of words (conversation she took part in), else what her lexical structure kept, plus older stored text."""
    from aurora_internal import aurora_word_use as _U
    prof = _S.ContextProfiles()
    use = _U.load_profiles(state_dir)
    if use is not None:
        prof.merge(use.state())
    else:                                   # the kept use counts the live turns; the lexical feed would count them a second time
        for c in crystals.values():
            for f in getattr(c, "facets", {}).values():
                if str(getattr(f, "role", "")) == LEX_ROLE:
                    try:
                        st = json.loads(str(f.content)) if not isinstance(f.content, dict) else f.content
                        if st.get("contexts"):
                            prof.merge(st["contexts"])
                    except Exception:
                        pass
    mem = _read(state_dir, "aurora_conversation_memory.json") or {}
    for e in mem.get("entries") or []:
        for field in ("user_said", "aurora_said"):
            for sent in re.split(r"[.!?;\n]+", str(e.get(field) or "")):
                ws = _WORD.findall(sent.lower())
                if ws:
                    prof.observe(ws)
    return prof


def _role_lookup() -> Dict[str, str]:
    try:
        from aurora_internal.aurora_utterance_parser import _WORD_ROLES
        return {str(w): str(getattr(r, "value", r)) for w, r in _WORD_ROLES.items()}
    except Exception:
        return {}


REPORT_FILE = "crystal_pass_report.json"
REPORT_HISTORY = 24


def _write_report(state_dir: str, report: Mapping[str, Any], at: float) -> None:
    """Keep the latest pass report, and a short history of the passes before it, for the hub to read.  Fail-safe: never reaches a turn or a save."""
    try:
        path = os.path.join(str(state_dir), REPORT_FILE)
        history: List[Any] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
            history = [h for h in (old.get("history") or []) if isinstance(h, dict)]
        except (OSError, ValueError, AttributeError):
            pass
        brief = {"at": at, "seconds": report.get("seconds")}
        brief.update({k: v for k, v in report.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in brief})
        for key, sub_key in (("links", "links"), ("facets", "facets"), ("held", "facets")):          # the counts inside a part's own report
            part = report.get(key)
            if isinstance(part, Mapping) and isinstance(part.get(sub_key), (int, float)):
                brief[key] = part[sub_key]
        history = (history + [brief])[-REPORT_HISTORY:]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"at": at, "report": report, "history": history}, fh, default=str)
        os.replace(tmp, path)
    except Exception:
        pass


def run_pass(dps: Any, state_dir: str, *, force: bool = False, clock=time.time, min_interval: float = MIN_INTERVAL) -> Dict[str, Any]:
    """Weave and write into `dps.crystals` / `dps.concept_index`.  Returns a report; never raises."""
    if not enabled():
        return {"skipped": "disabled"}
    now = clock()
    if not force and _last["t"] is not None and now - _last["t"] < min_interval:
        return {"skipped": "interval"}
    try:
        t0 = time.time()
        folded = _CS.fold_duplicates(dps)                      # one crystal per word, whatever label it arrived under
        crystals, idx = dps.crystals, _CS.primary_index(dps)
        r = _W.weave(state_dir)
        store, book = r["store"], r["book"]
        prof = word_profiles(crystals, state_dir)
        vocab = sorted(prof.vocabulary(), key=lambda w: (-prof.count(w), w))[:VOCAB]
        near = _S.neighbours(prof, vocab)
        classes = {f"S:{h}": _S.class_members(h, m) for h, _, m in _S.exemplar_classes(prof, vocab, top=CLASSES, near=near)}
        links_subst = _S.place_substitutes(store, prof, vocab, near=near)
        roles = _role_lookup()
        _G.place_scaffold(store, roles)
        cands = list(((_read(state_dir, "lexical_grounding_state.json") or {}).get("candidates") or {}).values())
        _G.place_families(store, cands)
        _G.place_classes(store, classes)
        _G.join_groups(store, roles, classes)
        # a generalization that holds counted members is a crystal in its own right
        candidates = sorted({b for _, b, t in store.records() if t == "is_a"})
        hubs = [b for b in candidates if store.incoming(b, "is_a")]
        created = 0
        make = getattr(dps, "_get_or_create", None)
        for hub in hubs:
            if hub not in idx and make is not None:
                make(hub)
                created += 1
        sensory_made = 0
        for concept in _SN.concepts_with_evidence(book):       # a sensory facet that counted perception stands behind is a crystal (one per facet)
            if concept not in idx and make is not None:
                make(concept)
                sensory_made += 1
        idx = _CS.primary_index(dps)                          # (a generalization crystal just made is in it)
        links = _A.apply_to_crystals(store, idx, crystals, dry_run=False)
        facets = _F.apply_to_crystals(book, idx, crystals, dry_run=False)
        held = _F.apply_held_to_crystals(book, idx, crystals, dry_run=False)          # what was given or derived, not lived: visible, never counted
        mat = _W.apply_maturity(store, book, idx, crystals, dry_run=False)
        interior = _I.apply_to_crystals(store, idx, crystals, dry_run=False)         # complex crystals deepen inward instead of spawning more
        # a generalization stands above what it holds, by the degree it classifies them (never to the top level: that is earned by evidence)
        levels = {c: float(int(crystals[i].level)) for c, i in idx.items() if i in crystals}
        raised = 0
        for hub in hubs:
            cr = crystals.get(idx.get(hub))
            if cr is None:
                continue
            target = min(3, int(round(_P.level_under(store, hub, levels))))
            if target > int(cr.level):
                cr.level = type(cr.level)(target)
                getattr(cr, "_unlock_failpoints", lambda: None)()
                raised += 1
        _last["t"] = now
        report = {"ok": True, "seconds": round(time.time() - t0, 2), "links": links, "facets": facets, "held": held, "folded": folded, "maturity": mat, "interior": interior, "classes": len(classes),
                "substitute_links": links_subst, "generalizations": len(hubs), "generalization_crystals_created": created, "sensory_crystals_created": sensory_made, "generalizations_raised": raised}
        _write_report(state_dir, report, now)
        return report
    except Exception as exc:          # fail-safe: a failure here must never reach a turn or a save
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
