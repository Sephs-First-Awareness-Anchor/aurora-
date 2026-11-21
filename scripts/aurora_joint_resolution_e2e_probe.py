#!/usr/bin/env python3
"""Read-only Aurora LIVE-turn A/B trial of an experimental joint projection.

Uses two independent Python processes and throwaway copies of aurora_state.
Experimental projection synthesis occurs only in this process, by monkey-
patching the existing perspective builder, never writing production code.

A joint candidate is provisional, from *different* actually discovered native
structural sources. Zero candidates or zero actualized effects = INCONCLUSIVE.
The trial does not teach interpretations or count replies as ground truth.
"""
from __future__ import annotations
import argparse
import contextlib
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
os.environ.setdefault("AURORA_SKIP_HARDWARE_IMPORTS", "1")
os.environ.setdefault("AURORA_SKIP_OETS_IMPORTS", "1") if False else None

TURNS = [
    "Mara sees the lantern shine when the switch is on and the battery is connected.",
    "The switch is on today, but the battery is disconnected.",
    "What happens to the lantern under those conditions?",
    "Now the switch is on and the battery is connected.",
    "What changed about the lantern and what contributed to that change?",
    "Remember the earlier situation when the switch was on but the battery was disconnected?",
]
SEED = 20261121

def _reply(result):
    if not isinstance(result, dict):
        return str(result or "")
    for name in ("resp_A", "resp_B"):
        value = result.get(name)
        content = getattr(value, "content", None)
        if content:
            return str(content)
    return str(result.get("text") or result.get("response") or "")

def _joint_candidate(rr, ref, views):
    """Combine two complementary *existing views*, not hypothetical values."""
    for i, first in enumerate(views):
        for second in views[i+1:]:
            aid = str(first.get("counterpart_ability_id") or "")
            bid = str(second.get("counterpart_ability_id") or "")
            if not aid or not bid or aid == bid:
                continue
            a, b = dict(first.get("exposed_fields") or {}), dict(second.get("exposed_fields") or {})
            if not a or not b or not (set(a) - set(b)) or not (set(b) - set(a)):
                continue
            if any(a[k] != b[k] for k in set(a) & set(b)):
                continue
            union = dict(a)
            union.update(b)
            try:
                projected = replace(ref, **union)
                encoded = projected.encode()
            except (TypeError, ValueError):
                continue
            if encoded in {first.get("projected_ref"), second.get("projected_ref")}:
                continue
            axes = list(dict.fromkeys(list(first.get("pressure_perspective") or []) +
                                      list(second.get("pressure_perspective") or [])))
            payload = "|".join((ref.encode(), *sorted((aid, bid)), encoded))
            pid = "rproj_joint_exp_" + hashlib.sha256(payload.encode()).hexdigest()[:20]
            evidence = {
                "origin": "experimental_structural_joint_view_NOT_EARNED",
                "structural_pressure": min(
                    float((first.get("evidence") or {}).get("structural_pressure", 0) or 0),
                    float((second.get("evidence") or {}).get("structural_pressure", 0) or 0)),
                "source_representation_ids": sorted((aid, bid)),
            }
            item = {
                "mode": "perspective_projection",
                "projection_id": pid, "projection_view_key": rr._projection_view_key({"projected_ref": encoded}),
                "field": sorted(union)[0], "candidate_value": union[sorted(union)[0]],
                "projected_ref": encoded, "source_ref": first["source_ref"],
                "source": "experimental_joint_view_from_native_structural_sources",
                "origin": "test_only_joint", "counterpart_ability_id": "|".join(sorted((aid, bid))),
                "joint_sources": [first["source_ref"], second["source_ref"]],
                "pressure_perspective": axes, "exposed_fields": union,
                "evidence": evidence,
            }
            return item
    return None

def _install_joint(rr, stats):
    original = rr.build_perspective_projections
    def joint_builder(ref, structural_sources, *, max_projections=rr.MAX_CANDIDATE_FIELDS_PER_PASS):
        stats["projection_builder_calls"] += 1
        if len(structural_sources) > 1:
            stats["multi_source_frontiers"] += 1
        native = original(ref, structural_sources, max_projections=max_projections)
        if len(native) < 2 or len(structural_sources) < 2:
            return native
        candidate = _joint_candidate(rr, ref, native)
        if candidate is None:
            return native
        stats["joint_candidates_built"] += 1
        if max_projections is not None and len(native) >= max_projections:
            return native
        # Keep native existing priority and do not replace any candidate.
        if any(x.get("projected_ref") == candidate["projected_ref"] for x in native):
            return native
        return native + [candidate]
    rr.build_perspective_projections = joint_builder
    original_stage = rr.RepresentationalResolutionEngine._stage_projection
    original_event = rr.RepresentationalResolutionEngine._projection_event
    def staged(self, ref, candidate, **kwargs):
        if str(candidate.get("projection_id", "")).startswith("rproj_joint_exp_"):
            stats["joint_candidates_staged"] += 1
        return original_stage(self, ref, candidate, **kwargs)
    def event(self, ref, pending, outcome, evaluation=None):
        candidate = dict(pending.get("candidate") or {})
        if str(candidate.get("projection_id", "")).startswith("rproj_joint_exp_"):
            d=stats["joint_outcomes"]
            d[outcome]=d.get(outcome,0)+1
        return original_event(self, ref, pending, outcome, evaluation)
    rr.RepresentationalResolutionEngine._stage_projection = staged
    rr.RepresentationalResolutionEngine._projection_event = event

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("baseline", "joint"))
    ap.add_argument("--out", required=True)
    args=ap.parse_args()
    random.seed(SEED)
    try:
        import numpy as np
        np.random.seed(SEED & 0xffffffff)
    except ImportError:
        pass
    from aurora_representational_resolution import RepresentationalResolutionEngine
    import aurora_representational_resolution as rr
    import aurora
    stats = {
        "projection_builder_calls":0, "multi_source_frontiers":0, "joint_candidates_built":0,
        "joint_candidates_staged":0, "joint_outcomes":{}
    }
    if args.arm == "joint":
        _install_joint(rr, stats)
    scratch=Path(tempfile.mkdtemp(prefix="aurora_joint_e2e_"))
    results={"arm":args.arm,"seed":SEED,"status":"starting","turns":[],"instrumentation":stats}
    try:
        state=scratch/"aurora_state"
        shutil.copytree(ROOT/"aurora_state",state)
        # Existing boot and actual process_external_user_turn are unmodified.
        started=time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            systems=aurora.boot_aurora(state_dir=str(state),verbose=False)
        results["boot_wall_s"]=round(time.perf_counter()-started,4)
        for idx,text in enumerate(TURNS):
            started=time.perf_counter()
            error=None
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    out=aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui",session_id="joint_e2e_trial",
                        auto_search_enabled=False, record_exchange=True,
                        update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=False,mode_name="BOUNDED")
                    reply=_reply(out)
                except Exception as exc:
                    error=f"{type(exc).__name__}: {exc}"
                    reply=""
            results["turns"].append({"turn":idx+1,"input":text,"reply":reply,
                                     "wall_s":round(time.perf_counter()-started,4),
                                     "error":error})
            if error:
                break
        exchange=systems.get("representation_exchange")
        if exchange is not None and callable(getattr(exchange,"status",None)):
            status=exchange.status()
            results["exchange"]={"consumers":exchange.consumers() if hasattr(exchange,"consumers") else [],
                                 "status":{k:v for k,v in dict(status).items() if k in ("consumer_stats","representations")}}
        engine=systems.get("representational_resolution_engine")
        if engine is not None:
            events=engine.recent_projection_events(limit=200) if hasattr(engine,"recent_projection_events") else []
            results["native_projection_outcomes"]={}
            for ev in events:
                k=str(ev.get("outcome",""))
                results["native_projection_outcomes"][k]=results["native_projection_outcomes"].get(k,0)+1
        results["status"]="ok" if len(results["turns"])==len(TURNS) and not any(t["error"] for t in results["turns"]) else "incomplete"
    except Exception as exc:
        results["status"]="error"
        results["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(scratch,ignore_errors=True)
        outfile=Path(args.out)
        outfile.parent.mkdir(parents=True,exist_ok=True)
        outfile.write_text(json.dumps(results,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps({"arm":args.arm,"status":results["status"],
                          "turns":len(results["turns"]),
                          "instrumentation":stats,
                          "error":results.get("error")},indent=2))
    if results["status"]!="ok":
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
