#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_kg_observe.py -- runtime evidence for Aurora's knowledge graph.

The static graph says which connections the code CAN make.  This script runs
Aurora against a COPY of her state and records which ones she actually made:

  * every call from one repo function into another, on every thread, counted
    (sys.monitoring PY_START; a call that came through library code such as
    threading or a callback registry is marked indirect);
  * every file she opened and in which mode (audit hook "open"), so persisted
    state is tied to the function that touched it;
  * every thread she started and the function it runs (audit hooks
    "_thread.start_joinable_thread" and "_thread.start_new_thread"), so delayed
    and background work is visible;
  * which class actually sits in each systems["key"] organ slot after boot;
  * the turn's pipeline-state writes, reads and missing reads, reusing the
    WatchedState instrumentation of scripts/map_turn_information_flow.py.

Scenarios:
  desktop   boot_aurora, then the four turns of map_turn_information_flow
            through process_external_user_turn.  Writes observations-desktop_boot.json
            and observations-desktop_turns.json.
  phone     the phone's Python entry, aurora_bridge.initialize, under a deadline.
            Writes observations-phone_init.json, with the last boot stage reached
            and whether initialize returned.

Nothing in Aurora is changed.  No reply text, user text or state content is
written: only code locations, counts, file names relative to the state copy,
and organ class names.

Usage:
  python scripts/aurora_kg_observe.py desktop --state aurora_state --out knowledge_graph/runtime
  python scripts/aurora_kg_observe.py phone --state aurora_state --deadline 900
  python scripts/aurora_knowledge_graph.py build --runtime knowledge_graph/runtime
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "aurora.kg_observations/1"
AUTHORS = "Sunni (Sir) Morningstar & Cael Devo"
TOOL_ID = 4          # sys.monitoring tool slot (0-5); 4 is not claimed by debuggers or coverage tools
SKIP_FILES = ("aurora_kg_observe.py", "map_turn_information_flow.py")


class Recorder:
    """Counts repo-to-repo calls, file opens and thread starts while active."""

    def __init__(self, root: Path) -> None:
        self.root = str(root.resolve()) + os.sep
        self.state_prefix = ""
        self.active = False
        self.calls: Dict[Tuple[Any, Any, bool], int] = defaultdict(int)
        self.io: Dict[Tuple[Any, str, str], int] = defaultdict(int)
        self.threads: Dict[Tuple[Any, Any, str], int] = defaultdict(int)
        self._repo: Dict[Any, bool] = {}

    def in_repo(self, code: Any) -> bool:
        r = self._repo.get(code)
        if r is None:
            fn = code.co_filename
            r = fn.startswith(self.root) and not fn.endswith(SKIP_FILES)
            self._repo[code] = r
        return r

    def _repo_frame(self, frame: Any, limit: int = 12) -> Tuple[Any, int]:
        hops = 0
        while frame is not None and hops < limit:
            if self.in_repo(frame.f_code):
                return frame, hops
            frame = frame.f_back
            hops += 1
        return None, hops

    # sys.monitoring callback
    def on_start(self, code: Any, offset: int) -> Any:
        if not self.in_repo(code):
            return sys.monitoring.DISABLE
        if not self.active:
            return None
        frame = sys._getframe(1)
        back, hops = self._repo_frame(frame.f_back)
        self.calls[(back.f_code if back is not None else None, code, hops > 0)] += 1
        return None

    def audit(self, event: str, args: Tuple[Any, ...]) -> None:
        if not self.active:
            return
        if event == "open":
            path = args[0]
            if isinstance(path, int) or path is None:
                return
            try:
                path = os.fsdecode(path)
            except Exception:
                return
            if not self.state_prefix or not path.startswith(self.state_prefix):
                return
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"
            frame, _ = self._repo_frame(sys._getframe(1))
            if frame is None:
                return
            rel = path[len(self.state_prefix):].lstrip("/\\")
            kind = "write" if any(c in mode for c in "wax+") else "read"
            self.io[(frame.f_code, rel, kind)] += 1
        elif event in ("_thread.start_new_thread", "_thread.start_joinable_thread"):
            fn = args[0]
            owner = getattr(fn, "__self__", None)
            target = getattr(owner, "_target", None) or fn
            target = getattr(target, "__func__", target)
            code = getattr(target, "__code__", None)
            if code is None and owner is not None:
                run = getattr(type(owner), "run", None)
                code = getattr(run, "__code__", None)
            frame, _ = self._repo_frame(sys._getframe(1))
            name = getattr(owner, "name", "") if owner is not None else ""
            self.threads[(frame.f_code if frame is not None else None, code, str(name)[:60])] += 1

    def install(self) -> None:
        mon = sys.monitoring
        mon.use_tool_id(TOOL_ID, "aurora-kg-observe")
        mon.register_callback(TOOL_ID, mon.events.PY_START, self.on_start)
        mon.set_events(TOOL_ID, mon.events.PY_START)
        sys.addaudithook(self.audit)

    def reset(self) -> None:
        self.calls.clear()
        self.io.clear()
        self.threads.clear()

    def loc(self, code: Any) -> Optional[List[Any]]:
        if code is None:
            return None
        fn = code.co_filename
        rel = fn[len(self.root):] if fn.startswith(self.root) else fn
        return [rel.replace(os.sep, "/"), getattr(code, "co_qualname", code.co_name), code.co_firstlineno]

    def export(self) -> Dict[str, Any]:
        calls = []
        for (caller, callee, indirect), n in sorted(self.calls.items(), key=lambda kv: -kv[1]):
            calls.append({"caller": self.loc(caller), "callee": self.loc(callee), "indirect": indirect, "count": n})
        io_rows = [{"code": self.loc(c), "path": p, "mode": k, "count": n} for (c, p, k), n in self.io.items()]
        threads = [{"starter": self.loc(s), "target": self.loc(t), "name": nm, "count": n}
                   for (s, t, nm), n in self.threads.items()]
        return {"calls": calls, "file_io": io_rows, "threads": threads}


def _git(args: List[str]) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT)] + args, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def _organs(systems: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in systems.items():
        if not isinstance(key, str):
            continue
        t = type(value)
        mod = getattr(t, "__module__", "") or ""
        if value is None or isinstance(value, (dict, list, tuple, set, str, int, float, bool)):
            out[key] = f"builtins:{t.__name__}"
        else:
            out[key] = f"{mod}:{getattr(t, '__qualname__', t.__name__)}"
    return out


def _write(out_dir: Path, scenario: str, rec: Recorder, extra: Dict[str, Any], started: float) -> Path:
    doc = {"schema": SCHEMA, "authors": AUTHORS, "scenario": scenario,
           "commit": _git(["rev-parse", "HEAD"]), "python": sys.version.split()[0],
           "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "duration_s": round(time.time() - started, 1)}
    doc.update(rec.export())
    doc.update(extra)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"observations-{scenario}.json"
    path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    print(f"[aurora-kg-observe] {scenario}: {len(doc['calls'])} call pairs, {len(doc['file_io'])} file uses, "
          f"{len(doc['threads'])} thread starts -> {path}", file=sys.stderr, flush=True)
    return path


def _copy_state(state: Path) -> Path:
    work = Path(tempfile.mkdtemp(prefix="aurora_kg_obs_"))
    shutil.copytree(state, work / "aurora_state")
    return work / "aurora_state"


def run_desktop(state: Path, out_dir: Path, turns: Optional[List[str]] = None) -> None:
    import map_turn_information_flow as mtf
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    copy = _copy_state(state)
    rec = Recorder(ROOT)
    rec.state_prefix = str(copy)
    rec.install()
    started = time.time()
    rec.active = True
    import aurora
    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        systems = aurora.boot_aurora(state_dir=str(copy), verbose=False)
    finally:
        sys.stdout = real
    rec.active = False
    _write(out_dir, "desktop_boot", rec, {"organs": _organs(systems),
                                          "entry": "aurora.boot_aurora", "completed": True}, started)
    rec.reset()
    original = aurora._extract_pipeline_signals

    def watched_extract(*args: Any, **kwargs: Any) -> Any:
        seed = original(*args, **kwargs)
        state_obj = mtf.WatchedState()
        for key, value in dict(seed or {}).items():
            dict.__setitem__(state_obj, key, value)
        return state_obj

    aurora._extract_pipeline_signals = watched_extract
    started = time.time()
    done = 0
    errors: List[str] = []
    rec.active = True
    for text in (turns or mtf.TURNS):
        sys.stdout = io.StringIO()
        try:
            aurora.process_external_user_turn(
                systems, text, source_label="flutter_ui", session_id="kg_observe", auto_search_enabled=False,
                record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                run_periodic_maintenance=True, mode_name="BOUNDED")
            done += 1
        except Exception as exc:          # recorded, never re-raised: the run is evidence either way
            errors.append(f"{type(exc).__name__}: {str(exc)[:200]}")
        finally:
            sys.stdout = real
    time.sleep(2.0)   # let timers and background threads started by the turns run once
    rec.active = False
    aurora._extract_pipeline_signals = original
    W = mtf.WATCH
    signals = {"writes": {k: dict(v) for k, v in W.writes.items()},
               "reads": {k: dict(v) for k, v in W.reads.items()},
               "missing_reads": {k: dict(v) for k, v in W.missing_reads.items()}}
    _write(out_dir, "desktop_turns", rec, {"organs": _organs(systems), "signals": signals,
                                           "entry": "aurora.process_external_user_turn", "turns": done,
                                           "turn_errors": errors, "completed": done == len(turns or mtf.TURNS)},
           started)


def run_phone(state: Path, out_dir: Path, deadline: float) -> None:
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    py_root = ROOT / "flutter_app" / "android" / "app" / "src" / "main" / "python"
    sys.path.insert(0, str(py_root))
    copy = _copy_state(state)
    rec = Recorder(ROOT)
    rec.state_prefix = str(copy)
    rec.install()
    import aurora_bridge as ab
    started = time.time()
    result: Dict[str, Any] = {"returned": False}
    stages: List[Tuple[float, str]] = []

    def watch_stages() -> None:
        last = None
        while not result.get("stop"):
            st = dict(getattr(ab, "_boot_state", {}) or {})
            if st.get("stage") != last:
                last = st.get("stage")
                stages.append((round(time.time() - started, 1), str(last)))
            time.sleep(1.0)

    def go() -> None:
        sys.stdout = io.StringIO()
        try:
            result["value"] = str(ab.initialize(str(copy)))[:200]
            result["returned"] = True
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    threading.Thread(target=watch_stages, daemon=True, name="kg-observe-stages").start()
    rec.active = True
    th = threading.Thread(target=go, daemon=True, name="kg-observe-initialize")
    th.start()
    th.join(deadline)
    if result["returned"]:
        time.sleep(5.0)   # give the Praxis thread and other background starts a moment
    rec.active = False
    result["stop"] = True
    extra: Dict[str, Any] = {"entry": "aurora_bridge.initialize", "completed": bool(result["returned"]),
                             "deadline_s": deadline, "boot_stages": stages,
                             "final_boot_state": dict(getattr(ab, "_boot_state", {}) or {}),
                             "initialize_error": result.get("error", "")}
    praxis = {"module_global_set": getattr(ab, "_praxis", None) is not None}
    try:
        praxis["get_praxis_status"] = json.loads(ab.get_praxis_status())
    except Exception as exc:
        praxis["get_praxis_status_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    try:
        stats = json.loads(ab.get_cognitive_stats())
        praxis["cognitive_stats_keys"] = sorted(k for k in stats if "praxis" in k or k == "error")
        praxis["cognitive_stats_praxis"] = {k: stats[k] for k in stats if k.startswith("praxis")}
        praxis["cognitive_stats_error"] = stats.get("error", "")
    except Exception as exc:
        praxis["cognitive_stats_exception"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    systems = getattr(ab, "_systems", None)
    if isinstance(systems, dict):
        extra["organs"] = _organs(systems)
        praxis["systems_slot_set"] = systems.get("praxis_bridge") is not None
    extra["praxis"] = praxis
    _write(out_dir, "phone_init", rec, extra, started)
    os._exit(0)   # background threads of a half-booted runtime must not keep the process alive


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Record which of Aurora's connections actually execute.")
    ap.add_argument("scenario", choices=["desktop", "phone"])
    ap.add_argument("--state", default=str(ROOT / "aurora_state"), help="state directory to COPY (never changed)")
    ap.add_argument("--out", default=str(ROOT / "knowledge_graph" / "runtime"))
    ap.add_argument("--deadline", type=float, default=900.0, help="phone: seconds to wait for initialize")
    args = ap.parse_args(argv)
    state = Path(args.state).resolve()
    if not state.is_dir():
        print(f"[aurora-kg-observe] no state directory at {state}", file=sys.stderr)
        return 2
    if args.scenario == "desktop":
        run_desktop(state, Path(args.out))
    else:
        run_phone(state, Path(args.out), args.deadline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
