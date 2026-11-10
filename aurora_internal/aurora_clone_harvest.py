#!/usr/bin/env python3
"""
aurora_clone_harvest.py -- many Auroras rehearse her history; she takes in
what they carved.

Sunni, 2026-11-08: "clone her ... for the simple use of parsing ... those
convos ... All through the exact same machinery and mechanisms.  Once
processed tho we feed the original aurora the processed parts only."  And on
what to carry: "those established paths are exactly where she would gain
especially when multiple different auroras carved paths overlap revealing to
her more relationships she may otherwise have missed."

THE CLONES (run_clone)
  Each clone is a full boot of her from the repository state.  It takes a
  contiguous run of whole conversations (plan_shards, balanced by message
  count) and lives them through her own HistoricalExperienceEnvironment --
  witnessing every event and REHEARSING Sunni's side (FIX-A104): she answers
  the other side through process_external_user_turn and Sunni's real reply
  judges her through the same receiver path the messenger uses.  Nothing
  about the machinery differs from her phone.  A clone stops only at a
  conversation boundary, so every conversation it reports was lived whole.

THE YIELD (clone_yield) -- what rehearsal changed in her, nothing else
  * reasoning paths carved or deepened, and paths that were worn down;
  * communication-emergence operations and lexical-grounding candidates
    whose VALIDATED, receiver-facing evidence grew.  Validated only: both
    organs' promotion rules count nothing else (an unvalidated parse is not
    understanding), and it keeps the harvest small enough to ship in the app.
    Witness-only evidence stays out: her phone witnesses every event itself,
    so carrying it would count it twice;
  * the unformed-pattern reference (understood, carried turns) and the
    patterns that recurred.

THE MERGE (merge_yields) -- convergence decides weight
  * paths: clones' paths that met the same pressure (shape + axis resonance)
    and landed the same way are ONE path; its weight is the clones' carvings
    combined as independent confirmations, w = 1 - prod(1 - w_i), so a path
    many clones carved arrives strong.  Where clones met the same pressure
    and landed DIFFERENTLY, every landing is kept as a divergence, weighted
    by its share of the clones -- her live verdicts settle it;
  * operations / candidates: the same structure grown by several clones
    unions their evidence (distinct surfaces and validated outcomes are what
    her own promotion rules count); structures that answer the same gap
    family differently are recorded as divergences;
  * unformed patterns: residues sharing a core (her SIMILAR rule) are one
    pattern across clones; the reference is additive.

ABSORPTION (absorb_harvest) -- on her, once per harvest
  Each organ takes the harvest through its own method (absorb_clone_paths,
  absorb_clone_operations, absorb_clone_candidates, absorb_clone_patterns):
  nothing arrives promoted; her own rules decide.  The conversations the
  clones lived are recorded so her history stream still WITNESSES them but
  no longer spends a full turn rehearsing them (rehearsal is ~80% of the
  cost of a historical event).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

HARVEST_VERSION = "aurora_clone_harvest_v1"
# JSON lines, gzipped: a header line, then one record per line, so her phone
# absorbs it in small chunks and never holds the whole harvest decoded.
# Bundled with the app (gradle copies aurora_internal/**/*.jsonl.gz).
HARVEST_FILE = "aurora_clone_harvest.jsonl.gz"
# What a clone reports, by organ.  A harvest segment names the organs it
# carries; a run can re-live history for organs that did not exist when it was
# first lived (FIX-A115: motifs, propositions, concepts) without the organs
# that were already harvested counting it twice.
LEGACY_ORGANS = ("paths", "operations", "candidates", "unformed")
ALL_ORGANS = LEGACY_ORGANS + ("motifs", "propositions", "concepts")
_ORGAN_FIELDS = {"paths": ("paths", "worn"), "operations": ("operations",), "candidates": ("candidates",),
                 "unformed": ("unformed",), "motifs": ("motifs",), "propositions": ("propositions",),
                 "concepts": ("concepts",)}


def parse_organs(spec: Any) -> Tuple[str, ...]:
    if not spec or str(spec).strip().lower() == "all":
        return ALL_ORGANS
    wanted = [o.strip().lower() for o in str(spec).split(",") if o.strip()]
    return tuple(o for o in ALL_ORGANS if o in wanted) or ALL_ORGANS


def segment_organs(header: Mapping[str, Any]) -> Tuple[str, ...]:
    return tuple(header.get("organs") or LEGACY_ORGANS)
ABSORB_CHUNK = 200
LEDGER_FILE = "clone_harvest_absorbed.json"
DEFAULT_HARVEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), HARVEST_FILE)
# A wear/dissolution in one clone is evidence, not a verdict: a path worn in
# a clone loses this share of its weight in her (scaled by how many of the
# clones that met it wore it).
WEAR_SHARE = 0.5
# A clone that runs past its budget mid-conversation still drops that
# conversation from what it reports (it was not lived whole).
HARD_STOP_FACTOR = 1.15


def _f(v: Any) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0


def _sha(payload: Any, n: int = 16) -> str:
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:n]


# ----------------------------------------------------------------------------
# Sharding
# ----------------------------------------------------------------------------

def plan_shards(episodes: List[Tuple[str, int]], clone_count: int) -> List[List[str]]:
    """Contiguous runs of whole conversations, balanced by message count.

    Contiguous, because consecutive conversations often continue each other
    -- a clone lives a stretch of her history the way she would."""
    clone_count = max(1, int(clone_count or 1))
    total = sum(max(1, int(n or 1)) for _, n in episodes)
    target = total / clone_count
    shards: List[List[str]] = [[] for _ in range(clone_count)]
    acc, idx = 0.0, 0
    for eid, n in episodes:
        weight = max(1, int(n or 1))
        if idx < clone_count - 1 and acc >= target * (idx + 1):
            idx += 1
        shards[idx].append(eid)
        acc += weight
    return shards


# ----------------------------------------------------------------------------
# Snapshots and the per-clone yield
# ----------------------------------------------------------------------------

def organ_snapshot(systems: Mapping[str, Any]) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    rp = systems.get("reasoning_paths")
    if rp is not None:
        snap["paths"] = copy.deepcopy(dict(getattr(rp, "paths", {}) or {}))
    ce = systems.get("communication_emergence")
    if ce is not None:
        snap["ce_ops"] = {cid: op.to_dict() for cid, op in dict(getattr(ce, "_operations", {}) or {}).items()}
        snap["ce_trials"] = {cid: asdict(c) for cid, c in dict(getattr(ce, "_warp_trials", {}) or {}).items()}
    lg = systems.get("lexical_grounding")
    if lg is not None:
        snap["lg_cands"] = {cid: c.to_dict() for cid, c in dict(getattr(lg, "_candidates", {}) or {}).items()}
        snap["lg_trials"] = {cid: asdict(c) for cid, c in dict(getattr(lg, "_warp_trials", {}) or {}).items()}
    try:                                   # FIX-A115: what was said, and where concepts sit
        from aurora_internal.aurora_confluence import _find_web
        web = _find_web(systems)
    except Exception:
        web = None
    if web is not None:
        snap["assertions"] = {
            f"{r.source_word}|{r.target_word}|{getattr(r.relation_type, 'value', r.relation_type)}": {
                "s": r.source_word, "t": r.target_word, "type": str(getattr(r.relation_type, "value", r.relation_type)),
                "a": copy.deepcopy(dict(r.assertion))}
            for r in list(dict(getattr(web, "relations", {}) or {}).values()) if getattr(r, "assertion", None)}
        snap["concepts"] = {w: {"p": dict(getattr(n, "axis_profile", {}) or {}), "n": int(getattr(n, "axis_samples", 0) or 0)}
                            for w, n in dict(getattr(web, "nodes", {}) or {}).items()
                            if int(getattr(n, "axis_samples", 0) or 0) > 0}
    ge = systems.get("grammar_engine")
    lineage = getattr(ge, "_lineage", None)
    if lineage is not None:
        # FIX-A113: her motif lineage travels too -- what rehearsal credited or
        # failed in each sentence shape, and in which contexts.
        snap["motifs"] = {pid: {"seq": [r.value for r in m.role_sequence], "s": int(m.success_count),
                                "f": int(m.fail_count), "ctx": sorted(m.contexts_seen)}
                          for pid, m in dict(getattr(lineage, "_motifs", {}) or {}).items()}
    up = systems.get("unformed_patterns")
    if up is not None:
        snap["unformed"] = copy.deepcopy({"ref_n": up.ref_n, "ref_counts": dict(up.ref_counts),
                                          "ref_axis_sum": dict(up.ref_axis_sum),
                                          "ref_axis_sq": dict(up.ref_axis_sq),
                                          "patterns": dict(up.patterns)})
    return snap


def _ce_evidence_id(e: Mapping[str, Any]) -> str:
    return "|".join((str(e.get("observation_id", "") or ""), str(e.get("response_id", "") or ""),
                     str(e.get("surface_hash", "") or "")))


# A trial's `parameters` are read only by _integrate_warp at its birth, which
# absorption bypasses (it builds the operation/candidate directly), so a trial
# travels slim -- the harvest is decoded on her phone.
_TRIAL_FIELDS = ("level", "axis_profile", "parent_ids", "name", "sixth_axis_signal", "topology_gap_ref")


def _slim_trial(trial: Mapping[str, Any], *, drop_profile: bool = False) -> Dict[str, Any]:
    out = {k: trial[k] for k in _TRIAL_FIELDS if k in dict(trial or {})}
    if drop_profile:
        out.pop("axis_profile", None)        # the candidate carries the same profile
    return out


def _grown(start: Mapping[str, Any], end: Mapping[str, Any], trials_start: Mapping[str, Any],
           trials_end: Mapping[str, Any], *, keep, ident, record_key: str) -> List[Dict[str, Any]]:
    out = []
    for cid, rec in end.items():
        before = {ident(e) for e in list(dict(start.get(cid) or {}).get("evidence") or [])}
        fresh = [dict(e) for e in list(rec.get("evidence") or []) if ident(e) not in before and keep(e)]
        if not fresh:
            continue
        out.append({record_key: {**rec, "evidence": fresh},
                    "trial": _slim_trial(dict(trials_end.get(cid) or trials_start.get(cid) or {}),
                                         drop_profile=record_key == "candidate"),
                    "status_in_clone": rec.get("status")})
    return out


def clone_yield(start: Mapping[str, Any], end: Mapping[str, Any], *, clone_id: str,
                episodes: List[str], counters: Mapping[str, Any],
                organs: Tuple[str, ...] = ALL_ORGANS) -> Dict[str, Any]:
    y = _clone_yield_all(start, end, clone_id=clone_id, episodes=episodes, counters=counters)
    y["organs"] = list(organs)
    for organ, fields in _ORGAN_FIELDS.items():
        if organ not in organs:
            for f in fields:
                y[f] = {"reference": {}, "patterns": []} if f == "unformed" else []
    return y


def _clone_yield_all(start: Mapping[str, Any], end: Mapping[str, Any], *, clone_id: str,
                     episodes: List[str], counters: Mapping[str, Any]) -> Dict[str, Any]:
    """What rehearsal changed in this clone -- the processed parts only."""
    paths, worn = [], []
    p0, p1 = dict(start.get("paths") or {}), dict(end.get("paths") or {})
    for pid, path in p1.items():
        w1 = _f(path.get("weight"))
        old = p0.get(pid)
        if old is None:
            gain = w1
        else:
            w0 = _f(old.get("weight"))
            if w1 <= w0:
                if w1 < w0:
                    worn.append({"shape": path.get("shape"), "centroid": path.get("centroid"),
                                 "landings": path.get("landings"), "factor": round(w1 / w0 if w0 else 0.0, 4)})
                continue
            gain = 1.0 - (1.0 - w1) / max(1e-6, 1.0 - w0)
        paths.append({"shape": path.get("shape"), "centroid": path.get("centroid"),
                      "landings": path.get("landings"), "weight": round(gain, 4),
                      "confirmations": int(path.get("confirmations", 0) or 0)
                      - int(dict(old or {}).get("confirmations", 0) or 0) or 1,
                      "misled": int(path.get("misled", 0) or 0) - int(dict(old or {}).get("misled", 0) or 0)})
    for pid, old in p0.items():
        if pid not in p1:
            worn.append({"shape": old.get("shape"), "centroid": old.get("centroid"),
                         "landings": old.get("landings"), "factor": 0.0})

    ce = _grown(dict(start.get("ce_ops") or {}), dict(end.get("ce_ops") or {}),
                dict(start.get("ce_trials") or {}), dict(end.get("ce_trials") or {}),
                keep=lambda e: bool(e.get("validated"))
                and str(e.get("observation_context", "") or "") != "environmental_counterfactual",
                ident=_ce_evidence_id, record_key="operation")
    lg = _grown(dict(start.get("lg_cands") or {}), dict(end.get("lg_cands") or {}),
                dict(start.get("lg_trials") or {}), dict(end.get("lg_trials") or {}),
                keep=lambda e: bool(e.get("validated"))
                and str(e.get("provenance", "") or "") not in ("historical_possibility", "developmental_replay"),
                ident=lambda e: str(e.get("evidence_id", "") or ""), record_key="candidate")

    u0, u1 = dict(start.get("unformed") or {}), dict(end.get("unformed") or {})
    reference = {"n": int(u1.get("ref_n", 0)) - int(u0.get("ref_n", 0)),
                 "counts": {f: int(c) - int(dict(u0.get("ref_counts") or {}).get(f, 0))
                            for f, c in dict(u1.get("ref_counts") or {}).items()
                            if int(c) - int(dict(u0.get("ref_counts") or {}).get(f, 0)) > 0},
                 "axis_sum": {ax: _f(v) - _f(dict(u0.get("ref_axis_sum") or {}).get(ax))
                              for ax, v in dict(u1.get("ref_axis_sum") or {}).items()},
                 "axis_sq": {ax: _f(v) - _f(dict(u0.get("ref_axis_sq") or {}).get(ax))
                             for ax, v in dict(u1.get("ref_axis_sq") or {}).items()}}
    patterns = []
    for pid, p in dict(u1.get("patterns") or {}).items():
        old = dict(dict(u0.get("patterns") or {}).get(pid) or {})
        occ = int(p.get("occurrences", 0)) - int(old.get("occurrences", 0) or 0)
        covered = int(p.get("covered", 0)) - int(old.get("covered", 0) or 0)
        if occ <= 0 and covered <= 0:
            continue
        counts = {f: int(c) - int(dict(old.get("feature_counts") or {}).get(f, 0))
                  for f, c in dict(p.get("feature_counts") or {}).items()}
        patterns.append({"feature_counts": {f: c for f, c in counts.items() if c > 0},
                         "occurrences": max(0, occ), "covered": max(0, covered),
                         "axis_sum": {ax: _f(v) - _f(dict(old.get("axis_sum") or {}).get(ax))
                                      for ax, v in dict(p.get("axis_sum") or {}).items()}})
    return {"version": HARVEST_VERSION, "clone_id": clone_id, "episodes": list(episodes),
            "counters": dict(counters), "paths": paths, "worn": worn,
            "operations": ce, "candidates": lg, "motifs": motif_deltas(start, end),
            "propositions": proposition_deltas(start, end), "concepts": concept_deltas(start, end),
            "unformed": {"reference": reference, "patterns": patterns}}


MOTIF_CONTEXT_CAP = 40


def motif_deltas(start: Mapping[str, Any], end: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Validated motif evidence this clone gathered: success and failure
    counts (demonstration credit, receiver outcomes) and the new contexts."""
    m0, m1 = dict(start.get("motifs") or {}), dict(end.get("motifs") or {})
    out = []
    for pid, m in m1.items():
        old = dict(m0.get(pid) or {})
        ds = int(m.get("s", 0)) - int(old.get("s", 0) or 0)
        df = int(m.get("f", 0)) - int(old.get("f", 0) or 0)
        if ds <= 0 and df <= 0:
            continue
        ctx = sorted(set(m.get("ctx") or []) - set(old.get("ctx") or []))[:MOTIF_CONTEXT_CAP]
        out.append({"seq": list(m.get("seq") or []), "s": max(0, ds), "f": max(0, df), "ctx": ctx})
    return out


_AXES = ("X", "T", "N", "B", "A")


def _count_delta(new: Mapping[str, Any], old: Mapping[str, Any]) -> Dict[str, int]:
    out = {k: int(v) - int(dict(old or {}).get(k, 0) or 0) for k, v in dict(new or {}).items()}
    return {k: v for k, v in out.items() if v > 0}


def _psum(prof: Mapping[str, Any], n: int) -> Dict[str, float]:
    return {ax: _f(dict(prof or {}).get(ax)) * n for ax in _AXES}


def proposition_deltas(start: Mapping[str, Any], end: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """FIX-A115: what the clone heard asserted -- per relation, the predicates
    (counts, denials, modalities), who said them, when, and the summed meaning
    profile, as deltas over what she already held."""
    a0, a1 = dict(start.get("assertions") or {}), dict(end.get("assertions") or {})
    out = []
    for key, rec in a1.items():
        new = dict(rec.get("a") or {})
        old = dict(dict(a0.get(key) or {}).get("a") or {})
        dn = int(new.get("n", 0)) - int(old.get("n", 0) or 0)
        if dn <= 0:
            continue
        preds = {}
        for pred, p in dict(new.get("predicates") or {}).items():
            q = dict(dict(old.get("predicates") or {}).get(pred) or {})
            n = int(p.get("n", 0)) - int(q.get("n", 0) or 0)
            if n > 0:
                preds[pred] = {"n": n, "denied": max(0, int(p.get("denied", 0)) - int(q.get("denied", 0) or 0)),
                               "modal": _count_delta(p.get("modal") or {}, q.get("modal") or {}),
                               "surface": str(p.get("surface") or pred)}
        p1, p0 = _psum(new.get("profile"), int(new.get("n", 0))), _psum(old.get("profile"), int(old.get("n", 0) or 0))
        out.append({"s": rec["s"], "t": rec["t"], "type": rec["type"], "n": dn, "predicates": preds,
                    "by": _count_delta(new.get("by") or {}, old.get("by") or {}),
                    "times": _count_delta(new.get("times") or {}, old.get("times") or {}),
                    "psum": {ax: round(p1[ax] - p0[ax], 4) for ax in _AXES},
                    "contexts": [c for c in list(new.get("contexts") or []) if c not in list(old.get("contexts") or [])]})
    return out


def concept_deltas(start: Mapping[str, Any], end: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """FIX-A115: how many statements each concept lived in during the clone's
    life, and the summed meaning of them."""
    c0, c1 = dict(start.get("concepts") or {}), dict(end.get("concepts") or {})
    out = []
    for word, c in c1.items():
        old = dict(c0.get(word) or {})
        dn = int(c.get("n", 0)) - int(old.get("n", 0) or 0)
        if dn <= 0:
            continue
        p1, p0 = _psum(c.get("p"), int(c.get("n", 0))), _psum(old.get("p"), int(old.get("n", 0) or 0))
        out.append({"w": word, "n": dn, "psum": {ax: round(p1[ax] - p0[ax], 4) for ax in _AXES}})
    return out


def _add_counts(into: Dict[str, Any], more: Mapping[str, Any]) -> None:
    for k, v in dict(more or {}).items():
        into[k] = int(into.get(k, 0) or 0) + int(v or 0)


def merge_propositions(yields: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Clones heard different conversations: what was asserted adds up."""
    merged: Dict[str, Dict[str, Any]] = {}
    for y in yields:
        for rec in list(y.get("propositions") or []):
            key = f"{rec.get('s')}|{rec.get('t')}|{rec.get('type')}"
            agg = merged.setdefault(key, {"s": rec.get("s"), "t": rec.get("t"), "type": rec.get("type"), "n": 0,
                                          "predicates": {}, "by": {}, "times": {},
                                          "psum": {ax: 0.0 for ax in _AXES}, "contexts": [], "clones": 0})
            agg["n"] += int(rec.get("n", 0))
            agg["clones"] += 1
            for pred, p in dict(rec.get("predicates") or {}).items():
                q = agg["predicates"].setdefault(pred, {"n": 0, "denied": 0, "modal": {}, "surface": pred})
                q["n"] += int(p.get("n", 0))
                q["denied"] += int(p.get("denied", 0))
                _add_counts(q["modal"], p.get("modal") or {})
                q["surface"] = str(p.get("surface") or q["surface"])
            _add_counts(agg["by"], rec.get("by") or {})
            _add_counts(agg["times"], rec.get("times") or {})
            for ax in _AXES:
                agg["psum"][ax] = round(agg["psum"][ax] + _f(dict(rec.get("psum") or {}).get(ax)), 4)
            agg["contexts"] = (agg["contexts"] + list(rec.get("contexts") or []))[-5:]
    return [merged[k] for k in sorted(merged)]


def merge_concepts(yields: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for y in yields:
        for rec in list(y.get("concepts") or []):
            agg = merged.setdefault(str(rec.get("w")), {"w": rec.get("w"), "n": 0, "psum": {ax: 0.0 for ax in _AXES}})
            agg["n"] += int(rec.get("n", 0))
            for ax in _AXES:
                agg["psum"][ax] = round(agg["psum"][ax] + _f(dict(rec.get("psum") or {}).get(ax)), 4)
    return [merged[k] for k in sorted(merged)]


def merge_motifs(yields: List[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Clones lived different conversations, so their motif evidence adds up
    -- as it would have if she had lived them all.  A shape some clones found
    working and others found failing is kept, and reported as a divergence."""
    merged: Dict[str, Dict[str, Any]] = {}
    for y in yields:
        for rec in list(y.get("motifs") or []):
            key = "_".join(rec.get("seq") or [])
            if not key:
                continue
            agg = merged.setdefault(key, {"seq": list(rec["seq"]), "s": 0, "f": 0, "ctx": set(),
                                          "clones": 0, "_up": 0, "_down": 0})
            agg["s"] += int(rec.get("s", 0))
            agg["f"] += int(rec.get("f", 0))
            agg["ctx"].update(rec.get("ctx") or [])
            agg["clones"] += 1
            agg["_up" if int(rec.get("s", 0)) >= int(rec.get("f", 0)) else "_down"] += 1
    out, divergent = [], []
    for key, agg in sorted(merged.items()):
        if agg["_up"] and agg["_down"]:
            divergent.append({"seq": agg["seq"], "working": agg["_up"], "failing": agg["_down"]})
        out.append({"seq": agg["seq"], "s": agg["s"], "f": agg["f"], "clones": agg["clones"],
                    "ctx": sorted(agg["ctx"])[:MOTIF_CONTEXT_CAP * 2]})
    return out, divergent


# ----------------------------------------------------------------------------
# The merge: convergence decides weight
# ----------------------------------------------------------------------------

def _path_tools():
    from aurora_internal.aurora_reasoning_paths import (RESONANCE_FLOOR, CLONE_WEIGHT_CAP, _cosine,
                                                         _unit, compare)
    return RESONANCE_FLOOR, CLONE_WEIGHT_CAP, _cosine, _unit, compare


def _cluster_paths(items: List[Tuple[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    floor, cap, cosine, unit, compare = _path_tools()
    clusters: List[Dict[str, Any]] = []
    for clone_id, item in items:
        centroid = unit(item.get("centroid") or {})
        landings = dict(item.get("landings") or {})
        home = None
        for c in clusters:
            if (c["shape"] == item.get("shape") and cosine(c["centroid"], centroid) >= floor
                    and compare(c["landings"], landings)["agreement"] >= 0.999):
                home = c
                break
        if home is None:
            home = {"shape": item.get("shape"), "centroid": centroid, "landings": landings,
                    "_sum": {}, "_n": 0, "_keep": 1.0, "clones": set(), "confirmations": 0,
                    "misled": 0, "factors": []}
            clusters.append(home)
        home["clones"].add(clone_id)
        home["_n"] += 1
        for ax, v in centroid.items():
            home["_sum"][ax] = home["_sum"].get(ax, 0.0) + v
        home["centroid"] = unit({ax: v / home["_n"] for ax, v in home["_sum"].items()})
        home["_keep"] *= 1.0 - min(cap, max(0.0, _f(item.get("weight"))))
        home["confirmations"] += int(item.get("confirmations", 0) or 0)
        home["misled"] += int(item.get("misled", 0) or 0)
        if "factor" in item:
            home["factors"].append(_f(item.get("factor")))
    return clusters


def merge_paths(yields: List[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    floor, cap, cosine, unit, compare = _path_tools()
    clusters = _cluster_paths([(y["clone_id"], p) for y in yields for p in list(y.get("paths") or [])])
    paths: List[Dict[str, Any]] = []
    for c in clusters:
        paths.append({"shape": c["shape"], "centroid": c["centroid"], "landings": c["landings"],
                      "weight": round(min(cap, 1.0 - c["_keep"]), 4), "clones": len(c["clones"]),
                      "confirmations": c["confirmations"], "misled": c["misled"]})
    # Same pressure, different landings: a divergence -- every landing kept,
    # at its share of the clones that met that pressure.
    divergences: List[Dict[str, Any]] = []
    seen = set()
    for i, a in enumerate(paths):
        if i in seen:
            continue
        group = [i] + [j for j, b in enumerate(paths) if j != i and j not in seen
                       and b["shape"] == a["shape"] and cosine(a["centroid"], b["centroid"]) >= floor]
        if len(group) < 2:
            continue
        seen.update(group)
        total = sum(paths[k]["clones"] for k in group) or 1
        major = max(group, key=lambda k: (paths[k]["clones"], paths[k]["weight"]))
        for k in group:
            share = paths[k]["clones"] / total
            paths[k]["share"] = round(share, 4)
            paths[k]["weight"] = round(paths[k]["weight"] * share, 4)
            paths[k]["divergent_with"] = len(group) - 1
            if k != major:
                paths[k]["differences"] = compare(paths[major]["landings"], paths[k]["landings"])["differences"]
        divergences.append({"shape": a["shape"], "landings": len(group),
                            "clones": [paths[k]["clones"] for k in group]})
    worn_clusters = _cluster_paths([(y["clone_id"], {**w, "weight": 0.0})
                                    for y in yields for w in list(y.get("worn") or [])])
    worn = [{"shape": c["shape"], "centroid": c["centroid"], "landings": c["landings"],
             "clones": len(c["clones"]),
             "factor": round(sum(c["factors"]) / max(1, len(c["factors"])), 4)} for c in worn_clusters]
    return paths, worn, divergences


def _merge_evidence_groups(yields: List[Mapping[str, Any]], field: str, record_key: str, keyfn, ident,
                           family_fn) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for y in yields:
        for item in list(y.get(field) or []):
            rec = dict(item.get(record_key) or {})
            if not any(dict(e or {}).get("validated") for e in list(rec.get("evidence") or [])):
                continue                 # nothing consequence-checked: nothing her rules would count
            key = keyfn(rec)
            g = groups.get(key)
            if g is None:
                g = groups[key] = {record_key: {**rec, "evidence": []},
                                   "trial": _slim_trial(dict(item.get("trial") or {}),
                                                        drop_profile=record_key == "candidate"),
                                   "clones": set(), "_ids": set(), "promoted_in": 0}
            g["clones"].add(y["clone_id"])
            if item.get("status_in_clone") == "promoted":
                g["promoted_in"] += 1
            for e in list(rec.get("evidence") or []):
                if not dict(e or {}).get("validated"):
                    continue
                i = ident(e)
                if i not in g["_ids"]:
                    g["_ids"].add(i)
                    g[record_key]["evidence"].append(dict(e))
    out, families = [], {}
    for key, g in groups.items():
        out.append({record_key: g[record_key], "trial": g["trial"], "clones": len(g["clones"]),
                    "promoted_in": g["promoted_in"]})
        families.setdefault(family_fn(g[record_key]), []).append(len(g["clones"]))
    divergences = [{"family": fam, "structures": len(c), "clones": c} for fam, c in families.items() if len(c) > 1]
    return out, divergences


def merge_unformed(yields: List[Mapping[str, Any]]) -> Dict[str, Any]:
    from aurora_internal.aurora_unformed_patterns import SIMILAR, UnformedPatterns, _jaccard
    ref = {"n": 0, "counts": {}, "axis_sum": {}, "axis_sq": {}}
    patterns: List[Dict[str, Any]] = []
    for y in yields:
        u = dict(y.get("unformed") or {})
        r = dict(u.get("reference") or {})
        ref["n"] += int(r.get("n", 0) or 0)
        for f, c in dict(r.get("counts") or {}).items():
            ref["counts"][f] = ref["counts"].get(f, 0) + int(c or 0)
        for k in ("axis_sum", "axis_sq"):
            for ax, v in dict(r.get(k) or {}).items():
                ref[k][ax] = ref[k].get(ax, 0.0) + _f(v)
        for p in list(u.get("patterns") or []):
            core = UnformedPatterns.core(p) or sorted(p.get("feature_counts") or {})
            home = None
            for q in patterns:
                if _jaccard(core, UnformedPatterns.core(q) or sorted(q["feature_counts"])) >= SIMILAR:
                    home = q
                    break
            if home is None:
                home = {"feature_counts": {}, "occurrences": 0, "covered": 0, "axis_sum": {}, "_clones": set()}
                patterns.append(home)
            home["_clones"].add(y["clone_id"])
            home["occurrences"] += int(p.get("occurrences", 0) or 0)
            home["covered"] += int(p.get("covered", 0) or 0)
            for f, c in dict(p.get("feature_counts") or {}).items():
                home["feature_counts"][f] = home["feature_counts"].get(f, 0) + int(c or 0)
            for ax, v in dict(p.get("axis_sum") or {}).items():
                home["axis_sum"][ax] = home["axis_sum"].get(ax, 0.0) + _f(v)
    for p in patterns:
        p["clones"] = len(p.pop("_clones"))
    return {"reference": ref, "patterns": patterns}


def merge_yields(yields: List[Mapping[str, Any]], *, lived_before: Iterable[str] = ()) -> Dict[str, Any]:
    from aurora_internal.aurora_communication_emergence import clone_operation_key
    from aurora_internal.aurora_lexical_grounding import clone_candidate_key
    yields = [y for y in yields if y and y.get("version") == HARVEST_VERSION]
    paths, worn, path_div = merge_paths(yields)
    ops, op_div = _merge_evidence_groups(
        yields, "operations", "operation", clone_operation_key, _ce_evidence_id,
        lambda r: f"{r.get('structural_family', '')}|{r.get('applicability_family', '')}")
    cands, cand_div = _merge_evidence_groups(
        yields, "candidates", "candidate", clone_candidate_key, lambda e: str(e.get("evidence_id", "") or ""),
        lambda r: f"{r.get('word', '')}|{r.get('applicability_family', '')}")
    episodes = sorted({e for y in yields for e in list(y.get("episodes") or [])})
    organs = [o for o in ALL_ORGANS if any(o in (y.get("organs") or LEGACY_ORGANS) for y in yields)]
    counters: Dict[str, int] = {}
    for y in yields:
        for k, v in dict(y.get("counters") or {}).items():
            if isinstance(v, (int, float)):
                counters[k] = counters.get(k, 0) + int(v)
    motifs, motif_div = merge_motifs(yields)
    body = {"paths": paths, "worn": worn, "operations": ops, "candidates": cands, "motifs": motifs,
            "propositions": merge_propositions(yields), "concepts": merge_concepts(yields),
            "unformed": merge_unformed(yields)}
    return {"version": HARVEST_VERSION, "harvest_id": "CH:" + _sha([sorted(y["clone_id"] for y in yields), episodes, body]),
            "created_at": time.time(), "clones": len(yields), "episodes": episodes, "organs": organs,
            "lived_episodes": sorted(set(lived_before) | set(episodes)), "counters": counters,
            "divergences": {"paths": path_div, "operations": op_div, "candidates": cand_div,
                            "motifs": motif_div}, **body}


# ----------------------------------------------------------------------------
# Absorption -- on her
# ----------------------------------------------------------------------------

def _ledger_path(state_dir: str) -> str:
    return os.path.join(state_dir or "aurora_state", LEDGER_FILE)


def load_ledger(state_dir: str) -> Dict[str, Any]:
    try:
        with open(_ledger_path(state_dir), "r", encoding="utf-8") as fh:
            raw = dict(json.load(fh) or {})
    except Exception:
        raw = {}
    raw.setdefault("absorbed", {})
    raw.setdefault("episodes", [])
    return raw


def _ledger_lived(ledger: Mapping[str, Any], organ: str) -> set:
    """Episodes she has absorbed this organ's harvest for.  A ledger from
    before organs were tracked covers the legacy organs only."""
    by = dict(ledger.get("episodes_by_organ") or {})
    if organ in by:
        return set(by[organ] or [])
    return set(ledger.get("episodes") or []) if organ in LEGACY_ORGANS else set()


def absorbed_episodes(state_dir: str) -> set:
    return set(load_ledger(state_dir).get("episodes") or [])


def _apply_wear(rp: Any, worn: List[Mapping[str, Any]]) -> int:
    count = 0
    for w in worn:
        pid = rp.find_same_path(str(w.get("shape") or ""), w.get("centroid") or {}, w.get("landings") or {})
        if pid is None:
            continue
        path = rp.paths[pid]
        factor = 1.0 - WEAR_SHARE * (1.0 - max(0.0, min(1.0, _f(w.get("factor")))))
        path["weight"] = round(_f(path.get("weight")) * factor, 4)
        count += 1
    if count:
        rp.flush_write_batch()
    return count


def _add_result(total: Dict[str, Any], part: Mapping[str, Any]) -> None:
    for k, v in dict(part or {}).items():
        if isinstance(v, bool) or not isinstance(v, (int, float, list)):
            total[k] = v
        elif isinstance(v, list):
            total.setdefault(k, [])
            total[k] = list(total[k]) + list(v)
        else:
            total[k] = total.get(k, 0) + v


WEB = "__web__"


def _propositional():
    from aurora_internal import aurora_propositional_understanding as P
    return P


def _organ(systems: Mapping[str, Any], key: str) -> Any:
    if key == WEB:
        from aurora_internal.aurora_confluence import _find_web
        return _find_web(systems)
    return systems.get(key)


def _organs() -> Dict[str, Tuple[str, str, Any]]:
    return {"path": ("paths", "reasoning_paths", lambda o, recs: o.absorb_clone_paths(recs)),
            "worn": ("paths", "reasoning_paths", lambda o, recs: {"worn": _apply_wear(o, recs)}),
            "operation": ("operations", "communication_emergence",
                          lambda o, recs: o.absorb_clone_operations(recs)),
            "candidate": ("candidates", "lexical_grounding",
                          lambda o, recs: o.absorb_clone_candidates(recs, save=False)),
            "motif": ("motifs", "grammar_engine",
                      lambda o, recs: o.absorb_clone_motifs(recs, save=False)),
            "proposition": ("propositions", WEB,
                            lambda o, recs: _propositional().absorb_clone_propositions(o, recs)),
            "concept": ("concepts", WEB,
                        lambda o, recs: _propositional().absorb_clone_concepts(o, recs)),
            "pattern": ("unformed", "unformed_patterns",
                        lambda o, recs: o.absorb_clone_patterns({"reference": {}, "patterns": recs})),
            "unformed_reference": ("unformed", "unformed_patterns",
                                   lambda o, recs: o.absorb_clone_patterns({"reference": recs[0], "patterns": []}))}


def absorb_harvest(systems: Mapping[str, Any], *, harvest_path: Optional[str] = None,
                   state_dir: Optional[str] = None) -> Dict[str, Any]:
    """Absorb every segment of a harvest she has not absorbed yet, streaming
    each in chunks of ABSORB_CHUNK records.  The returned record is the last
    segment absorbed (plus "segments": what happened to each)."""
    state_dir = str(state_dir or systems.get("state_dir") or "aurora_state")
    path = harvest_path or DEFAULT_HARVEST_PATH
    if not os.path.exists(path):
        return {"status": "no_harvest"}
    # Every boot passes through here: recognise an already-absorbed file from
    # its bytes' signature, without decoding any of it.
    try:
        with open(path, "rb") as fh:
            file_sig = hashlib.file_digest(fh, "sha1").hexdigest()[:16]
        ledger = load_ledger(state_dir)
        seen_files = dict(ledger.get("files") or {})
        if file_sig in seen_files:
            return {"status": "already_absorbed", "harvest_id": seen_files[file_sig]}
    except Exception as exc:
        return {"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}

    organs = _organs()
    segments: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {"header": None, "skip": True, "results": {}, "buffers": {}}

    def _flush(kind: str) -> None:
        recs = state["buffers"].pop(kind, [])
        if not recs:
            return
        name, key, fn = organs[kind]
        organ = _organ(systems, key)
        total = state["results"].setdefault(name, {})
        if organ is None:
            total["status"] = "absent"
            return
        if kind == "motif" and organ.clone_motifs_absorbed(str(state["header"].get("harvest_id") or "")):
            total["status"] = "already_applied"
            return
        try:
            _add_result(total, fn(organ, recs))
        except Exception as exc:
            total["status"] = "error"
            total["error"] = f"{type(exc).__name__}: {exc}"

    def _close_segment() -> None:
        header = state["header"]
        if header is None:
            return
        hid = str(header.get("harvest_id") or "")
        if state["skip"]:
            segments.append({"harvest_id": hid, "status": state["skip_reason"]})
            return
        for kind in list(state["buffers"]):
            _flush(kind)
        results = state["results"]
        lexical = systems.get("lexical_grounding")
        if (results.get("candidates", {}).get("evidence")
                and getattr(lexical, "persist", False) and not lexical.save()):
            raise OSError("clone lexical candidates could not be saved")
        motifs = results.get("motifs", {})
        if motifs.get("status") == "error":
            raise RuntimeError(motifs.get("error") or "clone motif absorption failed")
        if motifs.get("absorbed") or motifs.get("status") == "already_applied":
            if not systems["grammar_engine"].commit_clone_motifs(hid):
                raise OSError("clone motifs could not be saved")
        for name, key in (("paths", "reasoning_paths"), ("operations", "communication_emergence"),
                          ("candidates", "lexical_grounding"), ("motifs", "grammar_engine"),
                          ("propositions", WEB), ("concepts", WEB), ("unformed", "unformed_patterns")):
            if name not in results and _organ(systems, key) is None:
                results[name] = {"status": "absent"}
        lived = set(ledger.get("episodes") or [])
        new_eps = [e for e in list(header.get("episodes") or []) if e not in lived]
        by_organ = ledger.setdefault("episodes_by_organ", {})
        for o in segment_organs(header):
            by_organ[o] = sorted(_ledger_lived(ledger, o) | set(header.get("episodes") or []))
        record = {"at": time.time(), "clones": int(header.get("clones", 0) or 0),
                  "episodes": len(new_eps), "results": results,
                  "divergences": {k: len(v or []) for k, v in dict(header.get("divergences") or {}).items()}}
        ledger["absorbed"][hid] = record
        ledger["episodes"] = sorted(lived | set(new_eps))
        ledger["last"] = {"harvest_id": hid, **record}
        segments.append({"harvest_id": hid, "status": "absorbed", **record})

    def _open_segment(header: Dict[str, Any]) -> None:
        state.update({"header": header, "results": {}, "buffers": {}, "skip": False, "skip_reason": ""})
        hid = str(header.get("harvest_id") or "")
        if header.get("version") != HARVEST_VERSION:
            state.update({"skip": True, "skip_reason": "unknown_version"})
        elif hid in ledger["absorbed"]:
            state.update({"skip": True, "skip_reason": "already_absorbed"})
        else:
            organs = segment_organs(header)
            lived = set.intersection(*[_ledger_lived(ledger, o) for o in organs]) if organs else set()
            if header.get("episodes") and not [e for e in header["episodes"] if e not in lived]:
                ledger["absorbed"][hid] = {"at": time.time(), "skipped": "every conversation already lived"}
                state.update({"skip": True, "skip_reason": "already_lived"})

    try:
        for rec in iter_harvest(path):
            kind = str(rec.pop("kind", "") or "")
            if kind == "header":
                _close_segment()
                _open_segment(rec)
                continue
            if state["skip"] or kind not in organs:
                continue
            state["buffers"].setdefault(kind, []).append(rec)
            if kind == "unformed_reference" or len(state["buffers"][kind]) >= ABSORB_CHUNK:
                _flush(kind)
        _close_segment()
        ledger.setdefault("files", {})[file_sig] = ",".join(str(x.get("harvest_id", "")) for x in segments)
    except Exception as exc:
        segments.append({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    _write_ledger(state_dir, ledger)
    import gc
    gc.collect()
    absorbed = [x for x in segments if x.get("status") == "absorbed"]
    if absorbed:
        return {"status": "absorbed", **absorbed[-1], "segments": segments}
    if segments and segments[-1].get("status") == "error":
        return {**segments[-1], "segments": segments}
    statuses = {x.get("status") for x in segments}
    status = ("already_lived" if statuses == {"already_lived"} else
              "unknown_version" if statuses == {"unknown_version"} else "already_absorbed")
    return {"status": status, "harvest_id": (segments[-1].get("harvest_id") if segments else ""),
            "segments": segments}


def _write_ledger(state_dir: str, ledger: Mapping[str, Any]) -> None:
    os.makedirs(state_dir or ".", exist_ok=True)
    target = _ledger_path(state_dir)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh)
    os.replace(tmp, target)


def harvest_status(state_dir: str) -> Dict[str, Any]:
    ledger = load_ledger(state_dir)
    last = dict(ledger.get("last") or {})
    return {"harvests": len(ledger.get("absorbed") or {}), "episodes_lived_by_clones": len(ledger.get("episodes") or []),
            "last": last}


# ----------------------------------------------------------------------------
# One clone
# ----------------------------------------------------------------------------

def _events(env: Any):
    src = str(env._events_path())
    opener = gzip.open if src.endswith(".gz") else open
    with opener(src, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def _log(*parts: Any) -> None:
    # Flushed: the CLI ends with os._exit, which skips stdout's buffer, so
    # unflushed progress lines never reached the Actions log.
    print(*parts, flush=True)


def run_clone(index: int, count: int, *, state_dir: str = "aurora_state", out_path: str,
              max_seconds: float = 18000.0, harvest_path: Optional[str] = None,
              organs: Tuple[str, ...] = ALL_ORGANS, log=_log) -> Dict[str, Any]:
    """Boot one Aurora and live her shard of history through her own machinery."""
    t0 = time.time()
    import aurora as A
    from aurora_historical_experience_environment import HistoricalExperienceEnvironment
    from aurora_internal import aurora_turn_persistence as TP

    systems = A.boot_aurora(state_dir=state_dir, verbose=False)
    env = HistoricalExperienceEnvironment(systems, state_dir=state_dir, initial_delay_s=0.0)
    env._prepare()
    env.rehearse = True
    env.skip_absorbed = False            # a clone lives its shard whatever any ledger says

    # The conversations every organ this run reports has already been
    # harvested for.  A re-living pass for new organs lives the rest.
    try:
        lived_set = lived_for(read_header(harvest_path or DEFAULT_HARVEST_PATH), organs)
    except Exception:
        lived_set = set()
    ordered = [(eid, int(dict(rec).get("message_count", 1) or 1))
               for eid, rec in env._episodes.items() if eid not in lived_set]
    shard = plan_shards(ordered, count)[index]
    mine = set(shard)
    log(f"clone {index}/{count}: {len(shard)} conversations, {sum(n for e, n in ordered if e in mine)} messages, "
        f"boot {time.time() - t0:.0f}s")

    start = organ_snapshot(systems)
    done: List[str] = []
    current, events = "", 0
    stopped = ""
    for event in _events(env):
        eid = str(event.get("episode_id", "") or "")
        if eid not in mine:
            if current:
                done.append(current)
                current = ""
                if len(done) == len(shard):
                    break
            continue
        if eid != current:
            if current:
                done.append(current)
            if time.time() - t0 >= max_seconds:
                stopped = "budget"
                current = ""
                break
            current = eid
        if time.time() - t0 >= max_seconds * HARD_STOP_FACTOR:
            stopped = "hard_stop_mid_conversation"
            current = ""
            break
        try:
            env._witness(event)
        except Exception as exc:
            env.rehearsal_counters["errors"] = int(env.rehearsal_counters.get("errors", 0)) + 1
            log(f"witness error: {type(exc).__name__}: {exc}")
        env._state["current_episode_id"] = eid
        events += 1
        if events % 100 == 0:
            log(f"  {events} events, {len(done)} conversations, {time.time() - t0:.0f}s, {env.rehearsal_counters}")
    if current:
        done.append(current)
    try:
        TP.flush_all()
    except Exception:
        pass
    end = organ_snapshot(systems)
    counters = {**env.rehearsal_counters, "events": events, "conversations": len(done),
                "seconds": int(time.time() - t0)}
    y = clone_yield(start, end, clone_id=f"clone-{index:03d}-of-{count}", episodes=done, counters=counters,
                    organs=organs)
    y["stopped"] = stopped
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        json.dump(y, fh)
    log(f"clone {index} done: {counters} paths={len(y['paths'])} ops={len(y['operations'])} "
        f"cands={len(y['candidates'])} patterns={len(y['unformed']['patterns'])} stopped={stopped or 'no'}")
    return y


LISTEN_ORGANS = ("motifs", "propositions", "concepts")
_LISTEN_SPEAKER = {"user": "sunni", "historical_user": "sunni",
                   "assistant": "gpt", "historical_other_assistant": "gpt"}


_PARSER: List[Any] = []


def _parser() -> Any:
    if not _PARSER:
        from aurora_internal.aurora_utterance_parser import UtteranceParser
        _PARSER.append(UtteranceParser())
    return _PARSER[0]


def listen_to(systems: Mapping[str, Any], event: Mapping[str, Any], previous: Optional[Mapping[str, Any]],
              organs: Tuple[str, ...]) -> Dict[str, int]:
    """One message of her history, heard -- no turn of her own.

    What the three listening organs take from a message needs no reply from
    her: who asserted which predicate of what (propositions), where the
    concepts in it sit in X/T/N/B/A (concepts) -- both from her own utterance
    parser and axis projection, the same ones her pipeline runs -- and, when
    the message is a reply, its sentence shapes credited as a demonstration in
    the context it answered (motifs) -- the same call rehearsal makes with the
    real reply."""
    import aurora as A
    from aurora_internal import aurora_propositional_understanding as P
    from aurora_internal.aurora_confluence import _find_web
    out = {"statements": 0, "placed": 0, "motifs": 0}
    text = str(event.get("text", "") or "").strip()
    if not text:
        return out
    speaker = _LISTEN_SPEAKER.get(str(event.get("actor", "") or "").lower(), "sunni")
    listener = "gpt" if speaker == "sunni" else "sunni"
    web = _find_web(systems)
    if web is not None and ("propositions" in organs or "concepts" in organs):
        try:
            profile = P._profile(A._project_utterance_axes(text[:2000], systems))
        except Exception:
            profile = {}
        if "propositions" in organs:
            acts = P._acts(text[:2000])
            for st in P.statements_in(text, web=web):
                out["statements"] += len(P.integrate_form(web, st, heard=text[:400], speaker=speaker,
                                                          listener=listener, profile=profile, acts=acts))
        if "concepts" in organs and profile:
            try:
                topics = list(_parser().parse(text[:2000]).get("topic_words", []) or [])[:8]
            except Exception:
                topics = []
            for word in topics:
                node = web.nodes.get(str(word).lower())
                if node is not None:
                    P.place_concept(node, profile, weight=0.5)
                    out["placed"] += 1
    if "motifs" in organs and previous is not None and str(previous.get("actor")) != str(event.get("actor")):
        grammar = systems.get("grammar_engine")
        if grammar is not None and hasattr(grammar, "observe_demonstration"):
            out["motifs"] = int(grammar.observe_demonstration(
                text, context_text=str(previous.get("text", "") or "")[:2000],
                max_sentences=4 if speaker == "sunni" else 8) or 0)
    return out


def run_listen(index: int, count: int, *, state_dir: str = "aurora_state", out_path: str,
               max_seconds: float = 18000.0, harvest_path: Optional[str] = None,
               organs: Tuple[str, ...] = LISTEN_ORGANS, log=_log) -> Dict[str, Any]:
    """A clone that HEARS her shard of history for the listening organs
    (FIX-A115).  Minutes for the whole history, where rehearsing costs a full
    turn per message per position."""
    t0 = time.time()
    organs = tuple(o for o in organs if o in LISTEN_ORGANS) or LISTEN_ORGANS
    import aurora as A
    from aurora_historical_experience_environment import HistoricalExperienceEnvironment
    from aurora_internal import aurora_turn_persistence as TP
    systems = A.boot_aurora(state_dir=state_dir, verbose=False)
    env = HistoricalExperienceEnvironment(systems, state_dir=state_dir, initial_delay_s=0.0)
    env._prepare()
    try:
        lived_set = lived_for(read_header(harvest_path or DEFAULT_HARVEST_PATH), organs)
    except Exception:
        lived_set = set()
    ordered = [(eid, int(dict(rec).get("message_count", 1) or 1))
               for eid, rec in env._episodes.items() if eid not in lived_set]
    shard = plan_shards(ordered, count)[index]
    mine = set(shard)
    log(f"listen {index}/{count}: {len(shard)} conversations, {sum(n for e, n in ordered if e in mine)} messages, "
        f"boot {time.time() - t0:.0f}s")
    start = organ_snapshot(systems)
    done: List[str] = []
    totals = {"statements": 0, "placed": 0, "motifs": 0, "events": 0}
    current, previous, stopped = "", None, ""
    for event in _events(env):
        eid = str(event.get("episode_id", "") or "")
        if eid not in mine:
            continue
        if eid != current:
            if current:
                done.append(current)
            if time.time() - t0 >= max_seconds:
                stopped, current = "budget", ""
                break
            current, previous = eid, None
        try:
            for k, v in listen_to(systems, event, previous, organs).items():
                totals[k] += v
        except Exception as exc:
            totals["errors"] = totals.get("errors", 0) + 1
            log(f"listen error: {type(exc).__name__}: {exc}")
        previous = event
        totals["events"] += 1
        if totals["events"] % 1000 == 0:
            log(f"  {totals['events']} messages, {len(done)} conversations, {time.time() - t0:.0f}s, {totals}")
    if current:
        done.append(current)
    try:
        TP.flush_all()
    except Exception:
        pass
    end = organ_snapshot(systems)
    counters = {**totals, "conversations": len(done), "seconds": int(time.time() - t0), "mode": 0}
    y = clone_yield(start, end, clone_id=f"listen-{index:03d}-of-{count}", episodes=done, counters=counters,
                    organs=organs)
    y["stopped"] = stopped
    y["mode"] = "listen"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        json.dump(y, fh)
    log(f"listen {index} done: {counters} motifs={len(y['motifs'])} propositions={len(y['propositions'])} "
        f"concepts={len(y['concepts'])} stopped={stopped or 'no'}")
    return y


def load_yield(path: str) -> Dict[str, Any]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return dict(json.load(fh) or {})


_BODY = (("paths", "path"), ("worn", "worn"), ("operations", "operation"), ("candidates", "candidate"),
         ("motifs", "motif"), ("propositions", "proposition"), ("concepts", "concept"))


def write_harvest(path: str, harvest: Mapping[str, Any], *, keep_previous: bool = True) -> None:
    """Write a harvest as a new SEGMENT after every earlier segment in the file.

    FIX-A115 (Sunni, 2026-11-09: "ensure the aurora ready for download is the
    one with all the clone output absorbed"): a merge used to replace the file,
    so a phone that had not booted on run N's harvest never received it once
    run N+1 merged.  Each run is now appended as its own segment with its own
    harvest id; the phone absorbs every segment it has not absorbed yet."""
    tmp = str(path) + ".tmp"
    dump = lambda rec: json.dumps(rec, separators=(",", ":")) + "\n"
    new_id = str(harvest.get("harvest_id") or "")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        if keep_previous and os.path.exists(path):
            keep = True
            for line in _raw_lines(path):
                rec_kind = line[:40]
                if '"kind":"header"' in rec_kind:
                    keep = json.loads(line).get("harvest_id") != new_id
                if keep:
                    fh.write(line if line.endswith("\n") else line + "\n")
        header = {k: v for k, v in harvest.items()
                  if k not in ("paths", "worn", "operations", "candidates", "motifs", "propositions",
                               "concepts", "unformed")}
        fh.write(dump({"kind": "header", **header}))
        for field, kind in _BODY:
            for rec in list(harvest.get(field) or []):
                fh.write(dump({"kind": kind, **rec}))
        unformed = dict(harvest.get("unformed") or {})
        fh.write(dump({"kind": "unformed_reference", **dict(unformed.get("reference") or {})}))
        for rec in list(unformed.get("patterns") or []):
            fh.write(dump({"kind": "pattern", **rec}))
    os.replace(tmp, path)


def _raw_lines(path: str):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield line


def iter_harvest(path: str):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def read_headers(path: str) -> List[Dict[str, Any]]:
    """Every segment's header, oldest first."""
    out = []
    for line in _raw_lines(path):
        if '"kind":"header"' in line[:40]:
            rec = json.loads(line)
            out.append({k: v for k, v in rec.items() if k != "kind"})
    return out


def read_header(path: str) -> Dict[str, Any]:
    """The newest segment's header, with lived_episodes covering every segment."""
    headers = read_headers(path)
    if not headers:
        return {}
    out = dict(headers[-1])
    lived = set()
    by_organ: Dict[str, set] = {o: set() for o in ALL_ORGANS}
    for h in headers:
        eps = set(h.get("episodes") or [])            # what THIS segment's clones lived
        lived |= eps | set(h.get("lived_episodes") or [])
        for o in segment_organs(h):
            by_organ.setdefault(o, set()).update(eps)
    out["lived_episodes"] = sorted(lived)
    out["lived_by_organ"] = {o: sorted(e) for o, e in by_organ.items()}
    out["segments"] = len(headers)
    return out


def lived_for(header: Mapping[str, Any], organs: Iterable[str]) -> set:
    """Episodes ANY of these organs has already been harvested for -- a run
    never re-reports an organ for a conversation it already reported, so
    organ groups are lived in separate passes (e.g. motifs,propositions,
    concepts over all history; the legacy organs over what they have not
    covered)."""
    by = dict(header.get("lived_by_organ") or {})
    out: set = set()
    for o in organs:
        out |= set(by.get(o) or [])
    return out


def load_harvest(path: str) -> Dict[str, Any]:
    """The newest segment as one dict -- for the merge job and tests, never the phone."""
    out: Dict[str, Any] = {"paths": [], "worn": [], "operations": [], "candidates": [], "motifs": [],
                           "propositions": [], "concepts": [],
                           "unformed": {"reference": {}, "patterns": []}}
    kinds = {kind: field for field, kind in _BODY}
    segments = 0
    for rec in iter_harvest(path):
        kind = rec.pop("kind", "")
        if kind == "header":
            segments += 1
            out = {"paths": [], "worn": [], "operations": [], "candidates": [], "motifs": [],
                   "propositions": [], "concepts": [], "unformed": {"reference": {}, "patterns": []}}
            out.update(rec)
            out["segments"] = segments
        elif kind in kinds:
            out[kinds[kind]].append(rec)
        elif kind == "unformed_reference":
            out["unformed"]["reference"] = rec
        elif kind == "pattern":
            out["unformed"]["patterns"].append(rec)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clone")
    c.add_argument("--index", type=int, required=True)
    c.add_argument("--count", type=int, required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--max-seconds", type=float, default=18000.0)
    c.add_argument("--state-dir", default="aurora_state")
    c.add_argument("--organs", default="all", help="all, or a comma list of " + ",".join(ALL_ORGANS))
    c.add_argument("--mode", default="rehearse", choices=["rehearse", "listen"],
                   help="rehearse: live it with her turns; listen: hear it (motifs, propositions, concepts only)")
    m = sub.add_parser("merge")
    m.add_argument("--out", default=DEFAULT_HARVEST_PATH)
    m.add_argument("yields", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "clone":
        runner = run_listen if args.mode == "listen" else run_clone
        organs = parse_organs(args.organs)
        if args.mode == "listen" and str(args.organs).strip().lower() == "all":
            organs = LISTEN_ORGANS
        runner(args.index, args.count, state_dir=args.state_dir, out_path=args.out,
               max_seconds=args.max_seconds, organs=organs)
        os._exit(0)                      # her background threads must not hold the job open
    yields = []
    for p in args.yields:
        try:
            yields.append(load_yield(p))
        except Exception as exc:
            print(f"skip {p}: {exc}")
    lived_before: List[str] = []
    try:
        lived_before = list(read_header(args.out).get("lived_episodes") or [])
    except Exception:
        pass
    harvest = merge_yields(yields, lived_before=lived_before)
    harvest["counters"] = dict(harvest.get("counters") or {})
    write_harvest(args.out, harvest)
    print(json.dumps({k: harvest[k] for k in ("harvest_id", "clones", "counters")}),
          f"episodes={len(harvest['episodes'])} paths={len(harvest['paths'])} ops={len(harvest['operations'])} "
          f"cands={len(harvest['candidates'])} patterns={len(harvest['unformed']['patterns'])} "
          f"divergences={ {k: len(v) for k, v in harvest['divergences'].items()} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
