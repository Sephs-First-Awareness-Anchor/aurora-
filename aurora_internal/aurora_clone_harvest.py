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
HARVEST_FILE = "aurora_clone_harvest.json.gz"   # bundled with the app (gradle copies aurora_internal/**/*.json.gz)
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


def _grown(start: Mapping[str, Any], end: Mapping[str, Any], trials_start: Mapping[str, Any],
           trials_end: Mapping[str, Any], *, keep, ident, record_key: str) -> List[Dict[str, Any]]:
    out = []
    for cid, rec in end.items():
        before = {ident(e) for e in list(dict(start.get(cid) or {}).get("evidence") or [])}
        fresh = [dict(e) for e in list(rec.get("evidence") or []) if ident(e) not in before and keep(e)]
        if not fresh:
            continue
        out.append({record_key: {**rec, "evidence": fresh},
                    "trial": dict(trials_end.get(cid) or trials_start.get(cid) or {}),
                    "status_in_clone": rec.get("status")})
    return out


def clone_yield(start: Mapping[str, Any], end: Mapping[str, Any], *, clone_id: str,
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
            "operations": ce, "candidates": lg,
            "unformed": {"reference": reference, "patterns": patterns}}


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
                g = groups[key] = {record_key: {**rec, "evidence": []}, "trial": dict(item.get("trial") or {}),
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
    counters: Dict[str, int] = {}
    for y in yields:
        for k, v in dict(y.get("counters") or {}).items():
            if isinstance(v, (int, float)):
                counters[k] = counters.get(k, 0) + int(v)
    body = {"paths": paths, "worn": worn, "operations": ops, "candidates": cands,
            "unformed": merge_unformed(yields)}
    return {"version": HARVEST_VERSION, "harvest_id": "CH:" + _sha([sorted(y["clone_id"] for y in yields), episodes, body]),
            "created_at": time.time(), "clones": len(yields), "episodes": episodes,
            "lived_episodes": sorted(set(lived_before) | set(episodes)), "counters": counters,
            "divergences": {"paths": path_div, "operations": op_div, "candidates": cand_div}, **body}


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


def absorb_harvest(systems: Mapping[str, Any], *, harvest_path: Optional[str] = None,
                   state_dir: Optional[str] = None) -> Dict[str, Any]:
    state_dir = str(state_dir or systems.get("state_dir") or "aurora_state")
    path = harvest_path or DEFAULT_HARVEST_PATH
    if not os.path.exists(path):
        return {"status": "no_harvest"}
    try:
        harvest = load_harvest(path)
    except Exception as exc:
        return {"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}
    if harvest.get("version") != HARVEST_VERSION:
        return {"status": "unknown_version"}
    ledger = load_ledger(state_dir)
    hid = str(harvest.get("harvest_id") or "")
    if hid in ledger["absorbed"]:
        return {"status": "already_absorbed", "harvest_id": hid, **dict(ledger["absorbed"][hid])}
    lived = set(ledger.get("episodes") or [])
    new_eps = [e for e in list(harvest.get("episodes") or []) if e not in lived]
    if harvest.get("episodes") and not new_eps:
        ledger["absorbed"][hid] = {"at": time.time(), "skipped": "every conversation already lived"}
        _write_ledger(state_dir, ledger)
        return {"status": "already_lived", "harvest_id": hid}

    results: Dict[str, Any] = {}

    def _organ(name, key, fn):
        organ = systems.get(key)
        if organ is None:
            results[name] = {"status": "absent"}
            return
        try:
            results[name] = fn(organ)
        except Exception as exc:
            results[name] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    _organ("paths", "reasoning_paths",
           lambda o: {**o.absorb_clone_paths(list(harvest.get("paths") or [])),
                      "worn": _apply_wear(o, list(harvest.get("worn") or []))})
    _organ("operations", "communication_emergence",
           lambda o: o.absorb_clone_operations(list(harvest.get("operations") or [])))
    _organ("candidates", "lexical_grounding",
           lambda o: o.absorb_clone_candidates(list(harvest.get("candidates") or [])))
    _organ("unformed", "unformed_patterns",
           lambda o: o.absorb_clone_patterns(dict(harvest.get("unformed") or {})))

    record = {"at": time.time(), "clones": int(harvest.get("clones", 0) or 0),
              "episodes": len(new_eps), "results": results,
              "divergences": {k: len(v or []) for k, v in dict(harvest.get("divergences") or {}).items()}}
    ledger["absorbed"][hid] = record
    ledger["episodes"] = sorted(lived | set(new_eps))
    ledger["last"] = {"harvest_id": hid, **record}
    _write_ledger(state_dir, ledger)
    return {"status": "absorbed", "harvest_id": hid, **record}


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


def run_clone(index: int, count: int, *, state_dir: str = "aurora_state", out_path: str,
              max_seconds: float = 18000.0, harvest_path: Optional[str] = None,
              log=print) -> Dict[str, Any]:
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

    lived_before: List[str] = []
    try:
        lived_before = list(load_harvest(harvest_path or DEFAULT_HARVEST_PATH).get("lived_episodes") or [])
    except Exception:
        pass
    lived_set = set(lived_before)
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
    y = clone_yield(start, end, clone_id=f"clone-{index:03d}-of-{count}", episodes=done, counters=counters)
    y["stopped"] = stopped
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        json.dump(y, fh)
    log(f"clone {index} done: {counters} paths={len(y['paths'])} ops={len(y['operations'])} "
        f"cands={len(y['candidates'])} patterns={len(y['unformed']['patterns'])} stopped={stopped or 'no'}")
    return y


def load_yield(path: str) -> Dict[str, Any]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return dict(json.load(fh) or {})


load_harvest = load_yield


def write_harvest(path: str, harvest: Mapping[str, Any]) -> None:
    opener = gzip.open if str(path).endswith(".gz") else open
    tmp = str(path) + ".tmp"
    with opener(tmp, "wt", encoding="utf-8") as fh:
        json.dump(harvest, fh, separators=(",", ":"))
    os.replace(tmp, path)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clone")
    c.add_argument("--index", type=int, required=True)
    c.add_argument("--count", type=int, required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--max-seconds", type=float, default=18000.0)
    c.add_argument("--state-dir", default="aurora_state")
    m = sub.add_parser("merge")
    m.add_argument("--out", default=DEFAULT_HARVEST_PATH)
    m.add_argument("yields", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "clone":
        run_clone(args.index, args.count, state_dir=args.state_dir, out_path=args.out,
                  max_seconds=args.max_seconds)
        os._exit(0)                      # her background threads must not hold the job open
    yields = []
    for p in args.yields:
        try:
            yields.append(load_yield(p))
        except Exception as exc:
            print(f"skip {p}: {exc}")
    lived_before: List[str] = []
    try:
        lived_before = list(load_harvest(args.out).get("lived_episodes") or [])
    except Exception:
        pass
    harvest = merge_yields(yields, lived_before=lived_before)
    write_harvest(args.out, harvest)
    print(json.dumps({k: harvest[k] for k in ("harvest_id", "clones", "counters")}),
          f"episodes={len(harvest['episodes'])} paths={len(harvest['paths'])} ops={len(harvest['operations'])} "
          f"cands={len(harvest['candidates'])} patterns={len(harvest['unformed']['patterns'])} "
          f"divergences={ {k: len(v) for k, v in harvest['divergences'].items()} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
