# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Teach a lesson through the live path, then ask whether it took.

    python3 scripts/verify_lesson.py alphabet_order [--state-dir DIR] [--only after]

A lesson is two files in lessons/:
    <name>.txt     what is said to her, one utterance per line ('#' lines are not said)
    <name>.probes  what is asked afterwards, and what the answer must (or must not) contain

The lesson is said the way a person says it: one turn at a time through
`process_external_user_turn`, exactly as a message from Sir arrives.  Nothing is
written into her web and no answer is ever fed to her.  A probe is a QUESTION
(it must end in '?'), asked through the same path, and its reply is judged from
her words only.  Probes under [before] are asked before the lesson (what she
does not yet know); probes under [after] are asked once it has been said.

.probes format ('#' lines and blank lines are ignored):

    [before]
    What comes after b? => !c
    [after]
    What comes after b? => c
    Is a after b? => not after | not sure ;; !is after a

    question => term ;; term ;; term      every term must hold
    term                                  a word or phrase in the reply, case-insensitive, whole words
    term1 | term2                         either
    !term                                 the reply must NOT contain it

The run is on a COPY of the state directory; the original is never touched.
Exit status is 1 if any probe fails.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "lessons"
SECTIONS = ("before", "after")


def parse_lesson(text: str) -> List[str]:
    """The utterances: every line that is not blank and not a '#' comment."""
    return [ln.strip() for ln in str(text).splitlines() if ln.strip() and not ln.strip().startswith("#")]


def parse_probes(text: str) -> List[Dict[str, Any]]:
    """[{section, ask, terms:[(alternatives:list[str], forbid:bool)], line}] -- or ValueError naming the line."""
    out: List[Dict[str, Any]] = []
    section = "after"
    for n, raw in enumerate(str(text).splitlines(), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.fullmatch(r"\[(\w+)\]", ln)
        if m:
            section = m.group(1).lower()
            if section not in SECTIONS:
                raise ValueError(f"line {n}: unknown section [{m.group(1)}] (use {', '.join(SECTIONS)})")
            continue
        if "=>" not in ln:
            raise ValueError(f"line {n}: a probe is 'question => expected'")
        ask, _, expect = ln.partition("=>")
        ask, expect = ask.strip(), expect.strip()
        if not ask.endswith("?"):
            raise ValueError(f"line {n}: a probe must be a question (ending '?'); a statement would teach her")
        terms: List[Tuple[List[str], bool]] = []
        for term in (t.strip() for t in expect.split(";;")):
            if not term:
                continue
            forbid = term.startswith("!")
            body = term[1:].strip() if forbid else term
            alts = [a.strip().lower() for a in body.split("|") if a.strip()]
            if not alts:
                raise ValueError(f"line {n}: empty expectation")
            terms.append((alts, forbid))
        if not terms:
            raise ValueError(f"line {n}: nothing expected")
        out.append({"section": section, "ask": ask, "terms": terms, "line": n})
    return out


def judge(reply: str, terms: Sequence[Tuple[Sequence[str], bool]]) -> Tuple[bool, List[str]]:
    """(passed, the terms that failed, in words).  Her reply only; nothing else counts."""
    low = str(reply or "").lower()
    failed: List[str] = []
    for alts, forbid in terms:
        hit = any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", low) for a in alts)    # whole words: "c" is not in "comes"
        if forbid and hit:
            failed.append("contains " + " | ".join(repr(a) for a in alts))
        elif not forbid and not hit:
            failed.append("lacks " + " | ".join(repr(a) for a in alts))
    return (not failed), failed


# -- the live path --------------------------------------------------------------------

def _boot(state_src: Path):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch = Path(tempfile.mkdtemp(prefix="verify_lesson_")) / "aurora_state"
    shutil.copytree(state_src, scratch)
    import aurora
    import aurora_internal.aurora_clone_harvest as clone_harvest
    clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
    from run_probe_battery import _extract_delivered_response_text
    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
    finally:
        sys.stdout = real
    return aurora, systems, _extract_delivered_response_text


def _turn(aurora: Any, systems: Any, extract: Any, text: str) -> Dict[str, str]:
    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        r = dict(aurora.process_external_user_turn(
            systems, text, source_label="flutter_ui", session_id="lesson", auto_search_enabled=False,
            record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
            run_periodic_maintenance=True, mode_name="BOUNDED") or {})
        reply = extract(r, text, systems.get("aurora"))
    finally:
        sys.stdout = real
    return {"reply": str(reply or ""), "src": str(r.get("response_src") or r.get("src") or "")}


def run(name: str, state_dir: Path, only: Optional[str] = None) -> Dict[str, Any]:
    lesson = parse_lesson((LESSONS / f"{name}.txt").read_text(encoding="utf-8"))
    probes = parse_probes((LESSONS / f"{name}.probes").read_text(encoding="utf-8"))
    aurora, systems, extract = _boot(state_dir)
    report: Dict[str, Any] = {"lesson": name, "said": len(lesson), "results": []}

    def ask(section: str) -> None:
        for p in probes:
            if p["section"] != section or (only and only != section):
                continue
            got = _turn(aurora, systems, extract, p["ask"])
            ok, why = judge(got["reply"], p["terms"])
            report["results"].append({"section": section, "ask": p["ask"], "reply": got["reply"],
                                      "src": got["src"], "ok": ok, "why": why})

    ask("before")
    for line in lesson:
        _turn(aurora, systems, extract, line)         # said, not recorded: her replies to teaching are not judged
    ask("after")
    report["failed"] = sum(1 for r in report["results"] if not r["ok"])
    return report


def render(report: Dict[str, Any]) -> str:
    lines = [f"lesson {report['lesson']}: {report['said']} utterances said"]
    for r in report["results"]:
        mark = "PASS" if r["ok"] else "FAIL"
        lines.append(f"  [{r['section']}] {mark}  {r['ask']}")
        lines.append(f"        she said: {r['reply'] or '(nothing)'}   [{r['src'] or '-'}]")
        for w in r["why"]:
            lines.append(f"        -> {w}")
    n = len(report["results"])
    lines.append(f"{n - report['failed']}/{n} probes held")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lesson")
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"), help="copied; never modified")
    ap.add_argument("--only", choices=SECTIONS)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    report = run(a.lesson, Path(a.state_dir), a.only)
    print(json.dumps(report, indent=1) if a.json else render(report))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)          # her background threads must not hold the process open
