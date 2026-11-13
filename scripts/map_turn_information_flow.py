#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
map_turn_information_flow.py -- the information-circulation and consequence
map (Unified Directive, Part XVII deliverable 2), generated from Aurora's
running code rather than from anyone's reading of it.

What it records, on real live turns against a COPY of her state:

  * every write to the turn's pipeline state: which function wrote which
    signal, in what order -- the path information actually takes;
  * every direct read of a signal, including reads of signals NOBODY wrote
    (a consumer waiting on something that is never produced).

What it adds from the source, because copies of the pipeline state are read
all over the codebase and a copy cannot be watched:

  * for every signal, every place in the code that reads that name;
  * for every `systems["_..."]` bus key, where it is written and read;
  * the registry decisions (FIX-A###) cited inside each writing function, so
    a standing decision is shown at the place it governs.

It changes nothing in her.  It only watches, and writes a document.

Usage:  python scripts/map_turn_information_flow.py --out docs/AURORA_INFORMATION_CIRCULATION_MAP.md
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TURNS = [
    "Hey Aurora, how are you today?",
    "I spent the morning fixing the fence behind the house.",
    "What do you remember about what I was working on?",
    "Do you like music?",
]

_SKIP_FRAMES = ("map_turn_information_flow", "aurora_evolution_hook", "aurora_evolved_surfaces",
                "aurora_metabolic_clock")


def _caller() -> str:
    frame = sys._getframe(2)
    while frame is not None:
        name = os.path.basename(frame.f_code.co_filename)
        if not any(skip in name for skip in _SKIP_FRAMES):
            return f"{name[:-3] if name.endswith('.py') else name}.{frame.f_code.co_name}"
        frame = frame.f_back
    return "?"


class Watch:
    def __init__(self) -> None:
        self.clock = 0
        self.writes: "OrderedDict[str, OrderedDict[str, int]]" = OrderedDict()
        self.reads: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.missing_reads: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.first_write_by_fn: "OrderedDict[str, int]" = OrderedDict()

    def wrote(self, key: Any, who: str) -> None:
        self.clock += 1
        key = str(key)
        self.writes.setdefault(key, OrderedDict()).setdefault(who, self.clock)
        self.first_write_by_fn.setdefault(who, self.clock)

    def read(self, key: Any, who: str, present: bool) -> None:
        (self.reads if present else self.missing_reads)[str(key)][who] += 1


WATCH = Watch()


class WatchedState(dict):
    """The turn's pipeline state, watched.  A dict in every respect."""
    __slots__ = ()

    def __setitem__(self, key, value):
        WATCH.wrote(key, _caller())
        dict.__setitem__(self, key, value)

    def setdefault(self, key, default=None):
        if not dict.__contains__(self, key):
            WATCH.wrote(key, _caller())
        return dict.setdefault(self, key, default)

    def update(self, *args, **kwargs):
        who = _caller()
        incoming = dict(*args, **kwargs)
        for key in incoming:
            WATCH.wrote(key, who)
        dict.update(self, incoming)

    def __getitem__(self, key):
        WATCH.read(key, _caller(), dict.__contains__(self, key))
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        WATCH.read(key, _caller(), dict.__contains__(self, key))
        return dict.get(self, key, default)

    def pop(self, key, *default):
        WATCH.read(key, _caller(), dict.__contains__(self, key))
        return dict.pop(self, key, *default)


# ---------------------------------------------------------------------------
# Source index
# ---------------------------------------------------------------------------

def _source_files() -> List[Path]:
    files = [p for p in ROOT.glob("*.py")] + [p for p in (ROOT / "aurora_internal").rglob("*.py")]
    files += [p for p in (ROOT / "flutter_app" / "android" / "app" / "src" / "main" / "python").glob("*.py")]
    return [p for p in files if "/tests/" not in str(p) and not p.name.startswith("test_")]


_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", re.M)
_READ = re.compile(r"""(?:\.get\(\s*|\[\s*)["']([A-Za-z_][A-Za-z0-9_]*)["']\s*(\]|,|\))(?!\s*=[^=])""")
_BUS_WRITE = re.compile(r"""systems\[\s*["'](_[A-Za-z0-9_]+)["']\s*\]\s*=[^=]""")
_BUS_READ = re.compile(r"""systems\.(?:get|pop)\(\s*["'](_[A-Za-z0-9_]+)["']|systems\[\s*["'](_[A-Za-z0-9_]+)["']\s*\](?!\s*=[^=])""")
_FIX = re.compile(r"FIX-A\d+")


def index_sources():
    reads: Dict[str, set] = defaultdict(set)
    bus_w: Dict[str, set] = defaultdict(set)
    bus_r: Dict[str, set] = defaultdict(set)
    fixes: Dict[str, List[str]] = {}
    for path in _source_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        module = path.stem
        defs = [(m.start(), m.group(1)) for m in _DEF.finditer(text)]
        starts = [d[0] for d in defs]

        def owner(pos: int) -> str:
            i = bisect.bisect_right(starts, pos) - 1
            return f"{module}.{defs[i][1]}" if i >= 0 else f"{module}.<module>"

        for m in _READ.finditer(text):
            reads[m.group(1)].add(owner(m.start()))
        for m in _BUS_WRITE.finditer(text):
            bus_w[m.group(1)].add(owner(m.start()))
        for m in _BUS_READ.finditer(text):
            bus_r[m.group(1) or m.group(2)].add(owner(m.start()))
        for i, (pos, name) in enumerate(defs):
            end = defs[i + 1][0] if i + 1 < len(defs) else len(text)
            found = sorted(set(_FIX.findall(text[pos:end])), key=lambda f: int(f[5:]))
            if found:
                fixes[f"{module}.{name}"] = found
    return reads, bus_w, bus_r, fixes


# ---------------------------------------------------------------------------

def run_turns(state_dir: str) -> List[Dict[str, Any]]:
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    work = Path(tempfile.mkdtemp(prefix="aurora_map_"))
    shutil.copytree(state_dir, work / "aurora_state")
    import aurora

    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        systems = aurora.boot_aurora(state_dir=str(work / "aurora_state"), verbose=False)
    finally:
        sys.stdout = real

    original = aurora._extract_pipeline_signals

    def watched_extract(*args, **kwargs):
        seed = original(*args, **kwargs)
        state = WatchedState()
        for key, value in dict(seed or {}).items():
            WATCH.wrote(key, "aurora._extract_pipeline_signals")
            dict.__setitem__(state, key, value)
        return state

    aurora._extract_pipeline_signals = watched_extract
    outcomes = []
    for text in TURNS:
        sys.stdout = io.StringIO()
        try:
            result = aurora.process_external_user_turn(
                systems, text, source_label="flutter_ui", session_id="map",
                auto_search_enabled=False, record_exchange=True, update_interactive_state=True,
                track_evolutionary_trace=True, run_periodic_maintenance=True, mode_name="BOUNDED")
        finally:
            sys.stdout = real
        gate = dict(systems.get("_last_voice_gate") or {})
        outcomes.append({"said": text,
                         "reply": str(getattr(result.get("resp_A"), "content", "") or ""),
                         "src": str(getattr(result.get("resp_A"), "src", "") or ""),
                         "gate": {k: gate.get(k) for k in ("blocked", "outcome", "articulation", "confluence")}})
    shutil.rmtree(work, ignore_errors=True)
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", default="")
    parser.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    args = parser.parse_args()

    outcomes = run_turns(args.state_dir)
    static_reads, bus_w, bus_r, fixes = index_sources()

    signals = []
    for key, writers in WATCH.writes.items():
        writer_names = list(writers)
        live_readers = sorted(WATCH.reads.get(key, {}), key=lambda f: -WATCH.reads[key][f])
        source_readers = sorted(static_reads.get(key, set()))
        outside = [r for r in source_readers if r not in writer_names]
        signals.append({"signal": key, "writers": writer_names, "first_write": min(writers.values()),
                        "live_readers": live_readers, "source_readers": source_readers,
                        "read_outside_writer": bool(outside or [r for r in live_readers if r not in writer_names])})
    never_read = [s for s in signals if not s["read_outside_writer"]]
    # The strongest verdict: the signal's NAME appears nowhere in the source
    # except where it is written.  No reader can exist, by any route.
    corpus = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in _source_files())
    for s in never_read:
        mentions = len(re.findall(r"""["']%s["']""" % re.escape(s["signal"]), corpus))
        s["name_only_at_writer"] = mentions <= max(1, len(s["writers"]))
    dead = [s for s in never_read if s["name_only_at_writer"]]
    unclear = [s for s in never_read if not s["name_only_at_writer"]]
    awaited = []
    for key, who in WATCH.missing_reads.items():
        if key not in WATCH.writes:
            awaited.append({"signal": key, "readers": sorted(who, key=lambda f: -who[f]),
                            "reads": int(sum(who.values())),
                            "written_anywhere_in_source": bool(re.search(
                                r"""["']%s["']\s*(\]\s*=[^=]|:)""" % re.escape(key),
                                "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                                          for p in _source_files() if p.name == "aurora.py")))})
    awaited.sort(key=lambda a: -a["reads"])

    stages = []
    for fn, first in WATCH.first_write_by_fn.items():
        wrote = [k for k, w in WATCH.writes.items() if fn in w]
        stages.append({"stage": fn, "order": first, "signals": wrote, "decisions": fixes.get(fn, [])})

    bus = []
    for key in sorted(set(bus_w) | set(bus_r)):
        bus.append({"key": key, "writers": sorted(bus_w.get(key, ())), "readers": sorted(bus_r.get(key, ()))})
    bus_unread = [b for b in bus if b["writers"] and not b["readers"]]
    bus_unwritten = [b for b in bus if b["readers"] and not b["writers"]]

    data = {"commit": os.popen(f"git -C {ROOT} rev-parse --short HEAD").read().strip(),
            "generated_at": time.strftime("%Y-%m-%d"), "turns": outcomes, "stages": stages,
            "signals": signals, "never_read": [s["signal"] for s in never_read],
            "never_read_no_reader_possible": [s["signal"] for s in never_read if s.get("name_only_at_writer")],
            "awaited_never_written": awaited, "bus": bus}
    if args.json:
        Path(args.json).write_text(json.dumps(data, indent=1), encoding="utf-8")

    out: List[str] = []
    w = out.append
    w("# Aurora — Information Circulation and Consequence Map")
    w("")
    w("**Authors:** Sunni (Sir) Morningstar & Cael Devo  ")
    w(f"**Generated:** {data['generated_at']} at commit `{data['commit']}` by `scripts/map_turn_information_flow.py`")
    w("")
    w("This document is produced by watching her run. Nothing in it is anyone's "
      "reading of how she is supposed to work. Regenerate it after any change; "
      "a fix is placed on this map before it is written.")
    w("")
    w("## How to read it")
    w("")
    w("- A **signal** is one named entry in the turn's pipeline state — the shared "
      "record every stage of a live turn writes to and reads from.")
    w("- **Stage order** is the order functions first wrote during real turns.")
    w("- **Never read** means: written during a live turn, and no code anywhere "
      "reads that name outside the function that wrote it. Information that "
      "circulates nowhere.")
    w("- **Awaited, never written** means: read during a live turn, and never "
      "written in any of them. A consumer waiting on a producer.")
    w("- Decisions (`FIX-A…`) are the registry entries cited inside that stage's code.")
    w("")
    w("**Limits.** Reader lists come from matching the signal's name in source, so a "
      "common name (`confidence`) lists readers of unrelated dictionaries; a "
      "*never read* verdict has no such weakness. Only the pipeline state is "
      "watched live; fields on the turn-understanding object and each organ's "
      "private state are not on this map. Four turns were run; a path no turn "
      "took is not shown.")
    w("")
    w("## The turns that were run")
    w("")
    w("| Said | Reply | Source | Gate outcome |")
    w("|---|---|---|---|")
    for t in outcomes:
        g = t["gate"]
        w(f"| {t['said']} | {t['reply'] or '—'} | {t['src']} | "
          f"{g.get('outcome') or ''}{' · blocked: ' + str(g['blocked']) if g.get('blocked') else ''}"
          f"{' · articulation: ' + str(g['articulation']) if g.get('articulation') else ''}"
          f"{' · confluence: ' + str(g['confluence']) if g.get('confluence') else ''} |")
    w("")
    w("## Totals")
    w("")
    w(f"- Signals written during live turns: **{len(signals)}**, by **{len(stages)}** stages")
    w(f"- Never read outside their writer: **{len(never_read)}** — of these, **{len(dead)}** have a name "
      f"that appears nowhere else in the source (no reader can exist), and **{len(unclear)}** are named "
      f"elsewhere without being read there (each needs a look)")
    w(f"- Awaited but never written: **{len(awaited)}**")
    w(f"- `systems[\"_…\"]` bus keys in source: **{len(bus)}** — written and never read: "
      f"**{len(bus_unread)}**; read and never written by assignment: **{len(bus_unwritten)}**")
    w("")
    w("## 1. Signals written and never read")
    w("")
    w("### 1a. No reader can exist: the name appears only where it is written")
    w("")
    w("| Signal | Written by |")
    w("|---|---|")
    for s in sorted(dead, key=lambda s: s["first_write"]):
        w(f"| `{s['signal']}` | {', '.join(s['writers'][:3])} |")
    w("")
    w("### 1b. Named elsewhere, but not read there")
    w("")
    w("| Signal | Written by |")
    w("|---|---|")
    for s in sorted(unclear, key=lambda s: s["first_write"]):
        w(f"| `{s['signal']}` | {', '.join(s['writers'][:3])} |")
    w("")
    w("## 2. Signals awaited and never written")
    w("")
    w("| Signal | Read by | Reads | Assigned anywhere in aurora.py |")
    w("|---|---|---|---|")
    for a in awaited[:80]:
        w(f"| `{a['signal']}` | {', '.join(a['readers'][:3])} | {a['reads']} | "
          f"{'yes' if a['written_anywhere_in_source'] else '**no**'} |")
    if len(awaited) > 80:
        w(f"| … {len(awaited) - 80} more in the JSON | | | |")
    w("")
    w("## 3. Stage order — the path a live turn takes")
    w("")
    w("| # | Stage | Signals it writes | Decisions cited there |")
    w("|---|---|---|---|")
    for i, st in enumerate(stages, 1):
        sig = ", ".join(f"`{k}`" for k in st["signals"][:8]) + (f" … +{len(st['signals']) - 8}" if len(st["signals"]) > 8 else "")
        w(f"| {i} | {st['stage']} | {sig} | {', '.join(st['decisions'][-6:])} |")
    w("")
    w("## 4. Every signal: who writes it, who reads it")
    w("")
    w("| Signal | Writers | Read live by | Read in source by (count) |")
    w("|---|---|---|---|")
    for s in sorted(signals, key=lambda s: s["first_write"]):
        w(f"| `{s['signal']}` | {', '.join(s['writers'][:2])} | {', '.join(s['live_readers'][:3]) or '—'} | "
          f"{len(s['source_readers'])} |")
    w("")
    w("## 5. The `systems` bus: written and never read")
    w("")
    w("| Key | Written by |")
    w("|---|---|")
    for b in bus_unread:
        w(f"| `{b['key']}` | {', '.join(b['writers'][:3])} |")
    w("")
    w("## 6. The `systems` bus: read, never written by assignment")
    w("")
    w("These may be set by `setdefault`/`update` or by another process; each needs a look, none is proven dead.")
    w("")
    w("| Key | Read by |")
    w("|---|---|")
    for b in bus_unwritten:
        w(f"| `{b['key']}` | {', '.join(b['readers'][:3])} |")
    w("")
    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"signals {len(signals)} · stages {len(stages)} · never read {len(never_read)} · "
          f"awaited {len(awaited)} · bus {len(bus)} (unread {len(bus_unread)}, unwritten {len(bus_unwritten)})")
    for t in outcomes:
        print(f"  {t['said'][:44]!r:48} -> {t['reply'][:40]!r} [{t['src']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
