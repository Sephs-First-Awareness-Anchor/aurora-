#!/usr/bin/env python3
"""
aurora_development_experiment.py -- is her learning history-dependent?

Sunni, 2026-11-08: "Same historical experiences. Same underlying
architecture. Different developmental histories preceding the encounter.
That's the variable we're interested in." ... "I wouldn't change her learning
mechanisms to make the experiment work. I'd instrument the existing ones,
preserve the observations, and let the differences emerge or fail to emerge."

This module only WATCHES.  Nothing here feeds back into her or into the
clone harvest; it boots clones of her, lets them live parts of her history
through her own HistoricalExperienceEnvironment (witness + rehearsing
Sunni's side, FIX-A104), and records what each message did in her.

DESIGN (all clones start from the same repository state S0, same seeds):
  phase 1   A    : S0 lives History A            -> trace, frozen state S_A
            B    : S0 lives History B            -> trace, frozen state S_B
            A_rep: S0 lives History A again      -> trace (the noise floor)
  phase 2   AB   : S_A lives History B           -> trace, final state S_AB
            BA   : S_B lives History A           -> trace, final state S_BA
  analysis
    1. noise floor        A  vs A_rep  on History A
    2. B's history on A   A  vs BA     on History A   (same messages, B came first)
    3. A's history on B   B  vs AB     on History B
    4. order              S_AB vs S_BA : does A->B develop her as B->A does?

    Seeds are fixed, but her machinery runs on the clock (EMAs, decays,
    timestamps), so two identical runs are not identical: A_rep measures
    how far apart identical histories land.  A difference only counts where
    it goes beyond that floor.

WHAT IS TRACED, per message:
  * engaged relations -- every relation in her ontological web among that
    message's content words after she processed it, whether it formed then
    or was brought from earlier history.  "Clone B recognized a relationship
    Clone A overlooked" = a relation BA engaged on a message where neither A
    nor A_rep engaged it;
  * births -- paths carved, operations / word groundings born or promoted,
    abilities born, unformed patterns opened or formed, during that message;
  * on a rehearsal turn: her reply, the relational form she heard, the
    landings (meaning, action, operation, dominant axis, abilities), the
    remembered path offered (and where that path was born), the voice-gate
    outcome, the unformed residue, and when Sunni's real reply arrives, the
    comparison with it.
  "Why": a relation, path or ability that made a difference is traced back
  to the message in the clone's own earlier history where it was born.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import random
import subprocess
import sys
import tarfile
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

EXPERIMENT_VERSION = "aurora_development_experiment_v1"
CONTENT_ROLES = ("noun", "verb", "adjective", "adverb")
MAX_ENGAGED = 400
_STRIP = ".,!?;:'\"()-"
# A relation is "engaged" on a message only once it carries some weight in
# her web: a single fresh co-occurrence (strength 0.2) is still noise.
ENGAGED_STRENGTH = 0.25


def _f(v: Any) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0


def seed_everything(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed % (2 ** 32))
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Choosing the two histories
# ----------------------------------------------------------------------------

def pick_histories(episodes: List[Tuple[str, int]], *, start: int, target_messages: int) -> Tuple[List[str], List[str]]:
    """Two adjacent, contiguous stretches of whole conversations -- adjacent
    in her life, so what one teaches has a chance to bear on the other."""
    out: List[List[str]] = [[], []]
    idx, which, acc = max(0, start), 0, 0
    while idx < len(episodes) and which < 2:
        eid, n = episodes[idx]
        out[which].append(eid)
        acc += max(1, int(n or 1))
        idx += 1
        if acc >= target_messages:
            which, acc = which + 1, 0
    return out[0], out[1]


# ----------------------------------------------------------------------------
# What a message engaged in her, and what was born while she lived it
# ----------------------------------------------------------------------------

def find_web(systems: Mapping[str, Any]) -> Any:
    oets = systems.get("oets")
    if oets is None:
        perception = systems.get("perception")
        oets = perception.get("oets") if isinstance(perception, dict) else getattr(perception, "oets", None)
    return getattr(oets, "web", None)


def content_words(web: Any, text: str) -> List[str]:
    """The same cleaning OntologicalScaffoldingEngine.process_interaction uses."""
    out, seen = [], set()
    nodes = getattr(web, "nodes", {}) or {}
    for raw in str(text or "").lower().split():
        w = raw.strip(_STRIP)
        if len(w) > 1 and w not in seen and w in nodes and getattr(nodes[w], "role", "") in CONTENT_ROLES:
            seen.add(w)
            out.append(w)
    return out


def engaged_relations(web: Any, words: List[str]) -> List[List[Any]]:
    if web is None or not words:
        return []
    inside = set(words)
    by_source = getattr(web, "_relations_by_source", {}) or {}
    relations = getattr(web, "relations", {}) or {}
    found = []
    for w in words:
        for rid in list(by_source.get(w, ()) or ()):
            rel = relations.get(rid)
            if rel is None or rel.target_word not in inside:
                continue
            strength = _f(getattr(rel, "strength", 0.0))
            if strength < ENGAGED_STRENGTH:
                continue
            rtype = getattr(getattr(rel, "relation_type", None), "value", str(getattr(rel, "relation_type", "")))
            found.append([rel.source_word, str(rtype), rel.target_word, round(strength, 3)])
    found.sort(key=lambda r: -r[3])
    return found[:MAX_ENGAGED]


def organ_keys(systems: Mapping[str, Any]) -> Dict[str, Dict[str, str]]:
    """Cheap per-message view of what exists in her organs, and in what state."""
    out: Dict[str, Dict[str, str]] = {}
    rp = systems.get("reasoning_paths")
    if rp is not None:
        out["path"] = {pid: "carved" for pid in dict(getattr(rp, "paths", {}) or {})}
    ce = systems.get("communication_emergence")
    if ce is not None:
        out["operation"] = {cid: str(getattr(op, "status", "")) for cid, op in dict(getattr(ce, "_operations", {}) or {}).items()}
    lg = systems.get("lexical_grounding")
    if lg is not None:
        out["word_grounding"] = {cid: f"{getattr(c, 'word', '')}:{getattr(c, 'status', '')}"
                                 for cid, c in dict(getattr(lg, "_candidates", {}) or {}).items()}
    up = systems.get("unformed_patterns")
    if up is not None:
        out["unformed"] = {pid: str(dict(p).get("status", "")) for pid, p in dict(getattr(up, "patterns", {}) or {}).items()}
    gen = systems.get("genealogy")
    if gen is not None and hasattr(gen, "abilities"):
        out["ability"] = {aid: "exists" for aid in dict(getattr(gen, "abilities", {}) or {})}
    return out


def births(before: Mapping[str, Mapping[str, str]], after: Mapping[str, Mapping[str, str]]) -> List[List[str]]:
    out = []
    for organ, items in after.items():
        prev = dict(before.get(organ) or {})
        for key, state in items.items():
            if key not in prev:
                out.append([organ, key, "born", state])
            elif prev[key] != state:
                out.append([organ, key, "became", state])
    return out


def _turn_view(systems: Mapping[str, Any], held: Mapping[str, Any]) -> Dict[str, Any]:
    from aurora_internal.aurora_reasoning_paths import landings as _landings
    ps = dict(systems.get("_last_pipeline_state") or {})
    abilities = list(systems.get("_last_active_ability_ids") or [])
    offer = dict(ps.get("remembered_path") or {})
    gate = dict(systems.get("_last_voice_gate") or {})
    unformed = dict(systems.get("_last_unformed") or {})
    try:
        lands = _landings(ps, abilities)
    except Exception:
        lands = {}
    return {"reply": str(held.get("reply", "") or "")[:400],
            "heard_form": {k: v for k, v in dict(held.get("form") or {}).items()
                           if k in ("subject", "relation", "obj", "object", "form", "query", "polarity", "tense")},
            "landings": lands,
            "offered_path": ({"path_id": offer.get("path_id"), "weight": offer.get("weight"),
                              "resonance": offer.get("resonance")} if offer.get("path_id") else None),
            "voice_gate": str(gate.get("outcome", "") or gate.get("source", "") or ""),
            "unformed": {k: unformed.get(k) for k in ("status", "pattern_id", "departure", "residue") if k in unformed}}


# ----------------------------------------------------------------------------
# Living a history, traced
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


def live_traced(systems: Mapping[str, Any], env: Any, episodes: List[str], *, arm: str,
                trace_path: str, log=print) -> Dict[str, Any]:
    web = find_web(systems)
    wanted = set(episodes)
    done: Set[str] = set()
    t0 = time.time()
    n = 0
    keys = organ_keys(systems)
    with gzip.open(trace_path, "wt", encoding="utf-8") as out:
        out.write(json.dumps({"kind": "header", "version": EXPERIMENT_VERSION, "arm": arm,
                              "episodes": list(episodes), "started": t0}) + "\n")
        for event in _events(env):
            eid = str(event.get("episode_id", "") or "")
            if eid not in wanted:
                if done == wanted:
                    break
                continue
            done.add(eid)
            actor = env._actor_label(str(event.get("actor", "") or ""))
            before_turn = id(env._rehearsal) if getattr(env, "_rehearsal", None) else None
            result = {}
            try:
                result = dict(env._witness(event) or {})
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            env._state["current_episode_id"] = eid
            after = organ_keys(systems)
            text = str(event.get("text", "") or "")
            rec: Dict[str, Any] = {"kind": "event", "n": n, "event_id": event.get("event_id"), "episode_id": eid,
                                   "actor": actor, "engaged": engaged_relations(web, content_words(web, text)),
                                   "births": births(keys, after)}
            keys = after
            rehearsal = dict(result.get("rehearsal") or {})
            held = getattr(env, "_rehearsal", None)
            # Both positions (FIX-A112): a message can judge the rehearsal
            # held before it AND be answered by a new one.
            if held and id(held) != before_turn:
                rec["turn"] = {**_turn_view(systems, held), "position": held.get("position", "sunni")}
            if rehearsal.get("compared"):
                rec["comparison"] = {k: rehearsal.get(k) for k in ("label", "score", "precision", "uptake", "shared",
                                                                    "outcome")}
                rec["comparison"]["position"] = dict(getattr(env, "last_rehearsal", {}) or {}).get("position", "sunni")
            if rehearsal.get("skipped") or result.get("error"):
                rec["note"] = rehearsal.get("skipped") or result.get("error")
            out.write(json.dumps(rec, default=str) + "\n")
            n += 1
            if n % 25 == 0:
                log(f"  [{arm}] {n} messages, {len(done)}/{len(wanted)} conversations, {time.time() - t0:.0f}s", flush=True)
        out.write(json.dumps({"kind": "footer", "messages": n, "seconds": round(time.time() - t0, 1),
                              "rehearsal": dict(getattr(env, "rehearsal_counters", {}) or {})}) + "\n")
    return {"messages": n, "seconds": round(time.time() - t0, 1)}


def fingerprint(systems: Mapping[str, Any]) -> Dict[str, Any]:
    """Her developed state, in comparable form -- for A->B vs B->A."""
    from aurora_internal.aurora_communication_emergence import clone_operation_key
    from aurora_internal.aurora_lexical_grounding import clone_candidate_key
    out: Dict[str, Any] = {}
    rp = systems.get("reasoning_paths")
    if rp is not None:
        out["paths"] = [{"shape": p.get("shape"), "centroid": p.get("centroid"), "landings": p.get("landings"),
                         "weight": p.get("weight")} for p in dict(getattr(rp, "paths", {}) or {}).values()]
    ce = systems.get("communication_emergence")
    if ce is not None:
        out["operations"] = {clone_operation_key(op.to_dict()): op.status for op in dict(getattr(ce, "_operations", {}) or {}).values()}
    lg = systems.get("lexical_grounding")
    if lg is not None:
        out["word_groundings"] = {clone_candidate_key(c.to_dict()): c.status for c in dict(getattr(lg, "_candidates", {}) or {}).values()}
    up = systems.get("unformed_patterns")
    if up is not None:
        from aurora_internal.aurora_unformed_patterns import UnformedPatterns
        out["unformed"] = [{"core": UnformedPatterns.core(p), "status": p.get("status")}
                           for p in dict(getattr(up, "patterns", {}) or {}).values()]
    web = find_web(systems)
    if web is not None:
        rels = {}
        for rel in list(getattr(web, "relations", {}).values()):
            s = _f(getattr(rel, "strength", 0.0))
            if s >= ENGAGED_STRENGTH:
                rtype = getattr(getattr(rel, "relation_type", None), "value", str(getattr(rel, "relation_type", "")))
                rels[f"{rel.source_word}|{rtype}|{rel.target_word}"] = round(s, 3)
        out["relations"] = rels
    gen = systems.get("genealogy")
    if gen is not None and hasattr(gen, "abilities"):
        out["abilities"] = sorted(dict(getattr(gen, "abilities", {}) or {}))
    return out


# ----------------------------------------------------------------------------
# Freezing a clone's learned state
# ----------------------------------------------------------------------------

def _modified_sources(repo_root: str) -> List[str]:
    """Her autoevolver writes into source files: they are part of what she
    became, so a frozen state carries them."""
    try:
        out = subprocess.run(["git", "ls-files", "-m"], cwd=repo_root, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    return [p for p in out.split() if p and not p.startswith("aurora_state/")]


def freeze(repo_root: str, state_dir: str, out_tar: str) -> Dict[str, Any]:
    sources = _modified_sources(repo_root)
    count = 0
    with tarfile.open(out_tar, "w:gz") as tar:
        for root, dirs, files in os.walk(os.path.join(repo_root, state_dir)):
            dirs[:] = [d for d in dirs if d != "baseline_v1"]
            for f in files:
                full = os.path.join(root, f)
                tar.add(full, arcname=os.path.relpath(full, repo_root))
                count += 1
        for p in sources:
            tar.add(os.path.join(repo_root, p), arcname=p)
    return {"files": count, "sources": sources}


def thaw(repo_root: str, tar_path: str) -> None:
    with tarfile.open(tar_path, "r:gz") as tar:
        members = [m for m in tar.getmembers() if not (m.name.startswith("/") or ".." in m.name.split("/"))]
        tar.extractall(repo_root, members=members)


# ----------------------------------------------------------------------------
# One arm
# ----------------------------------------------------------------------------

def run_arm(arm: str, history: List[str], *, repo_root: str, state_dir: str, out_dir: str,
            seed: int, thaw_from: Optional[str] = None, freeze_to: Optional[str] = None, log=print) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    if thaw_from:
        thaw(repo_root, thaw_from)
    seed_everything(seed)
    import aurora as A
    from aurora_historical_experience_environment import HistoricalExperienceEnvironment
    from aurora_internal import aurora_turn_persistence as TP
    t0 = time.time()
    systems = A.boot_aurora(state_dir=state_dir, verbose=False)
    env = HistoricalExperienceEnvironment(systems, state_dir=state_dir, initial_delay_s=0.0)
    env._prepare()
    env.rehearse = True
    env.skip_absorbed = False
    seed_everything(seed)                 # again, after boot's own draws
    log(f"[{arm}] boot {time.time() - t0:.0f}s, {len(history)} conversations", flush=True)
    stats = live_traced(systems, env, history, arm=arm, trace_path=os.path.join(out_dir, f"trace_{arm}.jsonl.gz"), log=log)
    try:
        TP.flush_all()
    except Exception:
        pass
    with gzip.open(os.path.join(out_dir, f"state_{arm}.json.gz"), "wt", encoding="utf-8") as fh:
        json.dump(fingerprint(systems), fh)
    if freeze_to:
        stats["frozen"] = freeze(repo_root, state_dir, freeze_to)
    log(f"[{arm}] done: {stats}", flush=True)
    return stats


# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------

def load_trace(path: str) -> Dict[str, Any]:
    header, footer, events = {}, {}, []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("kind") == "header":
                header = rec
            elif rec.get("kind") == "footer":
                footer = rec
            else:
                events.append(rec)
    return {"header": header, "footer": footer, "events": events}


def _rel_set(event: Mapping[str, Any]) -> Set[str]:
    return {f"{r[0]}|{r[1]}|{r[2]}" for r in list(event.get("engaged") or [])}


def _jacc(a: Set[Any], b: Set[Any]) -> float:
    return 1.0 if not a and not b else len(a & b) / max(1, len(a | b))


def _births_index(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Where in this clone's own life each relation / path / ability first appeared."""
    rel_first, item_first = {}, {}
    for e in trace["events"]:
        for r in _rel_set(e):
            rel_first.setdefault(r, (e["episode_id"], e["event_id"], e["n"]))
        for organ, key, change, state in list(e.get("births") or []):
            item_first.setdefault(f"{organ}:{key}", (e["episode_id"], e["event_id"], e["n"], change, state))
    return {"relations": rel_first, "items": item_first}


def _turn_landing(e: Mapping[str, Any]) -> Dict[str, Any]:
    t = dict(e.get("turn") or {})
    return dict(t.get("landings") or {})


def compare_on_history(original: Mapping[str, Any], cross: Mapping[str, Any], replicate: Optional[Mapping[str, Any]],
                       prior: Optional[Mapping[str, Any]], *, label: str) -> Dict[str, Any]:
    """Same messages; `cross` had lived another history first.  `prior` is the
    trace of that other history (for tracing a difference back to where it
    was born)."""
    def by_event(trace):
        return {e["event_id"]: e for e in trace["events"]}
    o, c = by_event(original), by_event(cross)
    r = by_event(replicate) if replicate else {}
    born = _births_index(prior) if prior else {"relations": {}, "items": {}}
    shared = [eid for eid in o if eid in c]
    noise_rel = [1 - _jacc(_rel_set(o[e]), _rel_set(r[e])) for e in shared if e in r]
    floor = (sum(noise_rel) / len(noise_rel)) if noise_rel else 0.0
    recognized, overlooked, landing_shifts, score_shifts = [], [], [], []
    for eid in shared:
        eo, ec = o[eid], c[eid]
        so, sc = _rel_set(eo), _rel_set(ec)
        sr = _rel_set(r[eid]) if eid in r else set()
        for rel in sorted(sc - so - sr):
            src = born["relations"].get(rel)
            recognized.append({"event_id": eid, "episode_id": eo["episode_id"], "relation": rel,
                               "from_prior_history": ({"episode_id": src[0], "event_id": src[1], "message": src[2]}
                                                      if src else None)})
        stable = (so & sr) if eid in r else so      # what the first encounter reliably engaged
        for rel in sorted(stable - sc):
            overlooked.append({"event_id": eid, "episode_id": eo["episode_id"], "relation": rel})
        lo, lc = _turn_landing(eo), _turn_landing(ec)
        if lo or lc:
            diff = {k: [lo.get(k), lc.get(k)] for k in set(lo) | set(lc) if lo.get(k) != lc.get(k)}
            lr = _turn_landing(r[eid]) if eid in r else None
            noisy = bool(lr) and any(lr.get(k) != lo.get(k) for k in diff)
            if diff and not noisy:
                offered = dict(dict(ec.get("turn") or {}).get("offered_path") or {})
                why = None
                if offered.get("path_id"):
                    why = born["items"].get(f"path:{offered['path_id']}")
                abilities_from_prior = []
                for aid in list(lc.get("abilities") or []):
                    src = born["items"].get(f"ability:{aid}")
                    if src:
                        abilities_from_prior.append({"ability": aid, "episode_id": src[0], "event_id": src[1]})
                landing_shifts.append({"event_id": eid, "episode_id": eo["episode_id"], "differences": diff,
                                       "original_reply": dict(eo.get("turn") or {}).get("reply", "")[:160],
                                       "cross_reply": dict(ec.get("turn") or {}).get("reply", "")[:160],
                                       "path_offered_from_prior": why,
                                       "abilities_born_in_prior": abilities_from_prior})
        co, cc = dict(eo.get("comparison") or {}), dict(ec.get("comparison") or {})
        if co and cc:
            rr = dict(r[eid].get("comparison") or {}) if eid in r else {}
            delta = _f(cc.get("score")) - _f(co.get("score"))
            noise = abs(_f(rr.get("score")) - _f(co.get("score"))) if rr else 0.0
            score_shifts.append({"event_id": eid, "delta": round(delta, 4), "noise": round(noise, 4),
                                 "original": co.get("label"), "cross": cc.get("label")})
    beyond = [s for s in score_shifts if abs(s["delta"]) > s["noise"] + 1e-9]
    traced = [x for x in recognized if x["from_prior_history"]]
    return {"label": label, "messages_compared": len(shared),
            "noise_floor_relation_difference": round(floor, 4),
            "relation_difference": round(sum(1 - _jacc(_rel_set(o[e]), _rel_set(c[e])) for e in shared) / max(1, len(shared)), 4),
            "recognized_relations": len(recognized), "recognized_traced_to_prior_history": len(traced),
            "overlooked_relations": len(overlooked),
            "landing_shifts_beyond_noise": len(landing_shifts),
            "rehearsal_scores": {"compared": len(score_shifts),
                                 "better_beyond_noise": sum(1 for s in beyond if s["delta"] > 0),
                                 "worse_beyond_noise": sum(1 for s in beyond if s["delta"] < 0),
                                 "mean_delta": round(sum(s["delta"] for s in score_shifts) / max(1, len(score_shifts)), 4)},
            "examples": {"recognized_from_prior": traced[:25], "landing_shifts": landing_shifts[:15],
                         "score_shifts": sorted(beyond, key=lambda s: -abs(s["delta"]))[:15]}}


def compare_states(ab: Mapping[str, Any], ba: Mapping[str, Any], traces: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """A->B vs B->A: does the order of experience change what she becomes?"""
    out: Dict[str, Any] = {}
    for organ in ("operations", "word_groundings", "relations"):
        a, b = dict(ab.get(organ) or {}), dict(ba.get(organ) or {})
        common = set(a) & set(b)
        out[organ] = {"A_then_B": len(a), "B_then_A": len(b), "shared": len(common),
                      "jaccard": round(_jacc(set(a), set(b)), 4),
                      "same_status": sum(1 for k in common if a[k] == b[k]),
                      "only_A_then_B": sorted(set(a) - set(b))[:30], "only_B_then_A": sorted(set(b) - set(a))[:30]}
    out["abilities"] = {"jaccard": round(_jacc(set(ab.get("abilities") or []), set(ba.get("abilities") or [])), 4),
                        "only_A_then_B": len(set(ab.get("abilities") or []) - set(ba.get("abilities") or [])),
                        "only_B_then_A": len(set(ba.get("abilities") or []) - set(ab.get("abilities") or []))}
    try:
        from aurora_internal.aurora_reasoning_paths import RESONANCE_FLOOR, _cosine, compare as _cmp
        pa, pb = list(ab.get("paths") or []), list(ba.get("paths") or [])
        matched = sum(1 for p in pa if any(p.get("shape") == q.get("shape")
                                            and _cosine(p.get("centroid") or {}, q.get("centroid") or {}) >= RESONANCE_FLOOR
                                            and _cmp(p.get("landings") or {}, q.get("landings") or {})["agreement"] >= 0.999
                                            for q in pb))
        out["paths"] = {"A_then_B": len(pa), "B_then_A": len(pb), "same_path_in_both": matched}
    except Exception as exc:
        out["paths"] = {"error": str(exc)}
    # Where did order-unique relations come from?
    for side, key, first, second in (("only_A_then_B", "A_then_B", "A", "AB"), ("only_B_then_A", "B_then_A", "B", "BA")):
        idx_first = _births_index(traces[first]) if first in traces else {"relations": {}}
        idx_second = _births_index(traces[second]) if second in traces else {"relations": {}}
        # "outside_message_words": formed from words that never shared a
        # message (her own replies, definitions, taxonomy) -- not untraceable,
        # just not visible in the per-message view.
        where = {"first_history": 0, "second_history": 0, "outside_message_words": 0}
        for rel in out["relations"][side]:
            if rel in idx_first["relations"]:
                where["first_history"] += 1
            elif rel in idx_second["relations"]:
                where["second_history"] += 1
            else:
                where["outside_message_words"] += 1
        out["relations"][f"{side}_born_in"] = where
    return out


def analyze(in_dir: str) -> Dict[str, Any]:
    traces = {}
    for arm in ("A", "B", "A_rep", "AB", "BA"):
        p = os.path.join(in_dir, f"trace_{arm}.jsonl.gz")
        if os.path.exists(p):
            traces[arm] = load_trace(p)
    states = {}
    for arm in ("AB", "BA"):
        p = os.path.join(in_dir, f"state_{arm}.json.gz")
        if os.path.exists(p):
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                states[arm] = json.load(fh)
    report: Dict[str, Any] = {"version": EXPERIMENT_VERSION, "arms": {a: {"messages": t["footer"].get("messages"),
                                                                           "seconds": t["footer"].get("seconds"),
                                                                           "rehearsal": t["footer"].get("rehearsal")}
                                                                       for a, t in traces.items()}}
    if "A" in traces and "A_rep" in traces:
        report["noise_floor"] = compare_on_history(traces["A"], traces["A_rep"], None, None, label="A vs A_rep (identical histories)")
    if "A" in traces and "BA" in traces:
        report["B_history_on_A"] = compare_on_history(traces["A"], traces["BA"], traces.get("A_rep"), traces.get("B"),
                                                      label="History A: first encounter (A) vs after History B (BA)")
    if "B" in traces and "AB" in traces:
        report["A_history_on_B"] = compare_on_history(traces["B"], traces["AB"], None, traces.get("A"),
                                                      label="History B: first encounter (B) vs after History A (AB)")
    if "AB" in states and "BA" in states:
        report["order"] = compare_states(states["AB"], states["BA"], traces)
    return report


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = ["# Is Aurora's learning history-dependent?", "",
             "Authors: Sunni (Sir) Morningstar & Cael Devo", ""]
    for arm, s in dict(report.get("arms") or {}).items():
        lines.append(f"- **{arm}**: {s.get('messages')} messages in {s.get('seconds')} s; rehearsal {s.get('rehearsal')}")
    for key in ("noise_floor", "B_history_on_A", "A_history_on_B"):
        c = report.get(key)
        if not c:
            continue
        lines += ["", f"## {c['label']}",
                  f"- messages compared: {c['messages_compared']}",
                  f"- relation difference per message: {c['relation_difference']} (noise floor {c['noise_floor_relation_difference']})",
                  f"- relations recognized that the first encounter did not engage: {c['recognized_relations']}"
                  f" ({c['recognized_traced_to_prior_history']} traced to where they formed in the earlier history)",
                  f"- relations the first encounter engaged and this one did not: {c['overlooked_relations']}",
                  f"- reasoning landings that shifted beyond noise: {c['landing_shifts_beyond_noise']}",
                  f"- rehearsal vs Sunni's real replies: {c['rehearsal_scores']}"]
        for ex in c["examples"]["recognized_from_prior"][:8]:
            src = ex["from_prior_history"]
            lines.append(f"  - `{ex['relation']}` on {ex['event_id']} -- formed at {src['event_id']} ({src['episode_id']})")
        for ex in c["examples"]["landing_shifts"][:5]:
            lines.append(f"  - landing shift on {ex['event_id']}: {ex['differences']}"
                         + (f" (path offered, born at {ex['path_offered_from_prior'][1]})" if ex.get("path_offered_from_prior") else "")
                         + (f" (abilities born in the earlier history: "
                            f"{[(a['ability'], a['event_id']) for a in ex['abilities_born_in_prior']]})"
                            if ex.get("abilities_born_in_prior") else ""))
    o = report.get("order")
    if o:
        lines += ["", "## Order: A->B vs B->A"]
        for organ in ("relations", "operations", "word_groundings"):
            x = o[organ]
            lines.append(f"- {organ}: {x['A_then_B']} vs {x['B_then_A']}, shared {x['shared']}, jaccard {x['jaccard']},"
                         f" same status {x['same_status']}")
            if organ == "relations":
                lines.append(f"  - only in A->B, born in: {x.get('only_A_then_B_born_in')}; only in B->A, born in: {x.get('only_B_then_A_born_in')}")
        lines.append(f"- abilities: {o['abilities']}")
        lines.append(f"- paths: {o['paths']}")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Is her learning history-dependent?")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--start", type=int, default=100)
    p.add_argument("--messages", type=int, default=100)
    p.add_argument("--out", required=True)
    r = sub.add_parser("arm")
    r.add_argument("--arm", required=True, choices=["A", "B", "A_rep", "AB", "BA"])
    r.add_argument("--plan", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--seed", type=int, default=20261108)
    r.add_argument("--thaw")
    r.add_argument("--freeze")
    r.add_argument("--state-dir", default="aurora_state")
    a = sub.add_parser("analyze")
    a.add_argument("--in-dir", required=True)
    a.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "plan":
        eps = []
        with open(os.path.join("aurora_state", "historical_experience", "baseline_v1", "episodes.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    e = json.loads(line)
                    eps.append((e["episode_id"], int(e.get("message_count", 1) or 1)))
        ha, hb = pick_histories(eps, start=args.start, target_messages=args.messages)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"A": ha, "B": hb, "start": args.start, "messages": args.messages}, fh)
        print(f"History A: {len(ha)} conversations; History B: {len(hb)} conversations", flush=True)
        return 0
    if args.cmd == "arm":
        with open(args.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
        history = plan["B"] if args.arm in ("B", "AB") else plan["A"]
        run_arm(args.arm, history, repo_root=os.getcwd(), state_dir=args.state_dir, out_dir=args.out_dir,
                seed=args.seed, thaw_from=args.thaw, freeze_to=args.freeze)
        os._exit(0)
    report = analyze(args.in_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=str)
    md = render_markdown(report)
    with open(os.path.join(args.out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
