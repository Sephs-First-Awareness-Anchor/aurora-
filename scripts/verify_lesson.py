# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Teach a lesson through the live path, then ask whether it took.

    python3 scripts/verify_lesson.py alphabet_order [--state-dir DIR] [--only after]

A lesson is two files in lessons/:
    <name>.txt     what is said to her, one utterance per line ('#' lines are not said).
                   A line `#@correction` ends the lesson proper: the lines after it are said
                   only after the [after] probes (a correction, as people make them).
    <name>.probes  what is asked afterwards, and what the answer must (or must not) contain

The lesson is said the way a person says it: one turn at a time through
`process_external_user_turn`, exactly as a message from Sir arrives.  Nothing is
written into her web and no answer is ever fed to her.  A probe is a QUESTION
(it must end in '?'), asked through the same path, and its reply is judged from
her words only.  Probes under [before] are asked before the lesson (what she
does not yet know); probes under [after] are asked once it has been said; probes under [after-correction]
once the correction block has been said too (they are skipped when there is none).

.probes format ('#' lines and blank lines are ignored):

    [before]
    What comes after b? => !c
    [after]
    What comes after b? => c
    [after-correction]
    Is b after a? => not after
    Is a after b? => not after | not sure ;; !is after a

    question => term ;; term ;; term      every term must hold
    term                                  a word or phrase in the reply, case-insensitive, whole words
    term1 | term2                         either
    !term                                 the reply must NOT contain it

Passing a few expected phrases is not evidence that a lesson took, so a run also checks:

    lint        before anything is said: a lesson may not prescribe her replies ("you say hello",
                "when I ..., you ..."), assign her feelings or wants ("you feel ...", "you like ..."),
                or state personal identity as fact ("My name is ...", "X is my brother") unless the line is
                said explicitly as an example ("Suppose that ...", "Imagine that ...").
    paraphrase  `ask one? || ask two? || ask three? => terms`: every phrasing must hold.
    transfer    `@twin mara=nia teo=omar`: the whole lesson is said again to a fresh copy with the
                names/letters replaced, and the probes are asked with the same replacement.  What was
                learned about Mara must be learned about Nia; a phrase memorised from the lesson would not.
    control     the [after] probes are also asked of a fresh copy that was taught nothing; a probe that
                already "holds" untaught is not evidence.  It is not counted as held, and a lesson with
                one is NOT READY until the probe is made to ask something only the lesson can answer.
                A run that skipped the control (--quick) cannot say READY.
    gaps        `[gap]` probes are things she should be able to do and cannot yet.  A lesson with a failing
                gap is NOT READY (exit 2) however many other probes pass; a gap that now holds is flagged
                so it can be promoted to [after].

The run is on COPIES of the state directory; the original is never touched.
Exit status: 0 ready, 1 a probe or transfer failed, 2 not ready (open gaps, a probe that holds
untaught, or a control that was not run), 3 lint findings.
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
_SCRATCH: List[Path] = []                       # scratch copies of the state this run made
SECTIONS = ("before", "after", "after-correction", "gap")
CORRECTION_MARK = "#@correction"


def parse_lesson_blocks(text: str) -> Dict[str, List[str]]:
    """{"teach": [...], "correction": [...]}: the line `#@correction` ends the lesson proper; what
    follows is said only after the [after] probes, as people correct what they said."""
    blocks: Dict[str, List[str]] = {"teach": [], "correction": []}
    here = "teach"
    for ln in (x.strip() for x in str(text).splitlines()):
        if ln == CORRECTION_MARK:
            here = "correction"
        elif ln and not ln.startswith("#"):
            blocks[here].append(ln)
    return blocks


def parse_lesson(text: str) -> List[str]:
    """The utterances of the lesson proper: every line that is not blank and not a '#' comment,
    up to a `#@correction` line."""
    return parse_lesson_blocks(text)["teach"]



def parse_probes(text: str) -> List[Dict[str, Any]]:
    """[{section, ask, asks, terms:[(alternatives, forbid)], line}] -- or ValueError naming the line.
    `ask` is the first phrasing, `asks` all of them (`a? || b? || c? => ...`).  A `@twin a=b c=d` line
    is read by `parse_twin`, not here."""
    out: List[Dict[str, Any]] = []
    section = "after"
    for n, raw in enumerate(str(text).splitlines(), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#") or ln.startswith("@"):
            continue
        m = re.fullmatch(r"\[([\w-]+)\]", ln)
        if m:
            section = m.group(1).lower()
            if section not in SECTIONS:
                raise ValueError(f"line {n}: unknown section [{m.group(1)}] (use {', '.join(SECTIONS)})")
            continue
        if "=>" not in ln:
            raise ValueError(f"line {n}: a probe is 'question => expected'")
        ask, _, expect = ln.partition("=>")
        asks = [a.strip() for a in ask.split("||") if a.strip()]
        expect = expect.strip()
        if not asks or any(not a.endswith("?") for a in asks):
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
        out.append({"section": section, "ask": asks[0], "asks": asks, "terms": terms, "line": n})
    return out


def parse_twin(text: str) -> Dict[str, str]:
    """`@twin mara=nia teo=omar` -> {"mara": "nia", "teo": "omar"} (lowercase words; none -> {})."""
    mapping: Dict[str, str] = {}
    for raw in str(text).splitlines():
        ln = raw.strip()
        if ln.startswith("@twin"):
            for pair in ln.split()[1:]:
                a, _, b = pair.partition("=")
                if not a or not b:
                    raise ValueError(f"bad @twin pair {pair!r} (use old=new)")
                mapping[a.lower()] = b.lower()
    return mapping


def substitute(text: str, mapping: Dict[str, str]) -> str:
    """Whole-word replacement keeping the capital of the original ("Mara" -> "Nia", "mara" -> "nia")."""
    if not mapping:
        return text

    def one(m: "re.Match[str]") -> str:
        new = mapping[m.group(0).lower()]
        return new.capitalize() if m.group(0)[:1].isupper() else new
    pat = r"(?<![\w])(" + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r")(?![\w])"
    return re.sub(pat, one, str(text), flags=re.I)


def substitute_terms(terms, mapping):
    return [([substitute(a, mapping).lower() for a in alts], forbid) for alts, forbid in terms]


# -- lint: what a lesson may not do ------------------------------------------------------

_ACT = r"(say|answer|respond|reply|comfort|greet|help|tell|thank|ask|give|smile|apologi[sz]e|worry|care)"
_PRESCRIBE = [
    (re.compile(r"^\s*(when|whenever|if|after|every time)\b.*\byou\s+(\w+\s+)?" + _ACT + r"\b", re.I),
     "prescribes what she does in response (a condition on someone else, then 'you ...')"),
    (re.compile(r"\byou\s+(\w+\s+)?" + _ACT + r"\b.*\b(if|when|whenever)\b", re.I),
     "prescribes what she does in response ('you ...' on a condition)"),
    (re.compile(r"\byou\s+(should|must|always|never|have to|need to|ought to|will)\b", re.I),
     "tells her what she must, should or will do"),
    (re.compile(r"\b(i want|i need|i expect)\s+you\s+to\b", re.I), "tells her what is wanted of her"),
]
_ASSIGN = [
    (re.compile(r"\byou\s+(feel|felt|are\s+(happy|sad|angry|afraid|calm|curious|lonely|proud|jealous)|"
                r"like|love|want|need|hate|enjoy|fear|miss)\b", re.I),
     "assigns her a feeling or want -- hers is her own state, not a statement told to her"),
    (re.compile(r"\b(aurora)\s+(feels?|is\s+(happy|sad|angry|afraid|calm|curious)|likes?|loves?|wants?)\b", re.I),
     "assigns her a feeling or want"),
]
_IDENTITY = [
    (re.compile(r"\b(my|your)\s+name\s+is\b", re.I), "states a name as fact"),
    (re.compile(r"\b(?i:i am|i'm|you are|you're)\s+[A-Z][a-z]+\b"), "states who someone is as fact"),
    (re.compile(r"\b[A-Z][a-z]+\s+is\s+(not\s+)?(my|your|the)\s+(brother|sister|mother|father|son|daughter|"
                r"friend|wife|husband|partner|child|parent)\b"), "states a kinship as fact"),
    (re.compile(r"\b[A-Z][a-z]+\s+is\s+(not\s+)?(a|an)\s+(person|human|machine|ai|robot|man|woman|child)\b"),
     "states what someone is as fact"),
    (re.compile(r"\b(devlin|sunni|aurora)\s+is\b", re.I), "states something about a real person or about her"),
]


def lint_lesson(lines: Sequence[str]) -> List[Dict[str, str]]:
    """Findings for lines a lesson may not contain.  An example said as an example ("Suppose that ...") is
    not a statement of fact, so it is exempt from the identity rules only."""
    sys.path.insert(0, str(ROOT))
    from aurora_internal.aurora_propositional_understanding import _SUPPOSE
    out: List[Dict[str, str]] = []
    for line in lines:
        rules = list(_PRESCRIBE) + list(_ASSIGN)
        if not _SUPPOSE.match(line):
            rules += _IDENTITY
        for pat, why in rules:
            if pat.search(line):
                out.append({"line": line, "why": why})
                break
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
    root = Path(tempfile.mkdtemp(prefix="verify_lesson_"))
    _SCRATCH.append(root)                       # removed when the run ends (each copy of the state is large)
    scratch = root / "aurora_state"
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



def _play(aurora: Any, systems: Any, extract: Any, probes: List[Dict[str, Any]], lesson: List[str],
          correction: List[str], mapping: Dict[str, str], sections: Sequence[str], teach: bool = True) -> List[Dict[str, Any]]:
    """Say the lesson (when `teach`), asking each section's probes at its place.  Replies to teaching are
    not judged.  Returns one result per probe phrasing."""
    results: List[Dict[str, Any]] = []

    def ask(section: str) -> None:
        for p in probes:
            if p["section"] != section or section not in sections:
                continue
            terms = substitute_terms(p["terms"], mapping)
            for q in p["asks"]:
                got = _turn(aurora, systems, extract, substitute(q, mapping))
                ok, why = judge(got["reply"], terms)
                results.append({"section": section, "ask": substitute(q, mapping), "reply": got["reply"],
                                "src": got["src"], "ok": ok, "why": why})

    ask("before")
    if teach:
        for line in lesson:
            _turn(aurora, systems, extract, substitute(line, mapping))
    ask("after")
    ask("gap")
    if teach and correction:
        for line in correction:
            _turn(aurora, systems, extract, substitute(line, mapping))
        ask("after-correction")
    return results


def run(name: str, state_dir: Path, only: Optional[str] = None, quick: bool = False) -> Dict[str, Any]:
    probes_text = (LESSONS / f"{name}.probes").read_text(encoding="utf-8")
    blocks = parse_lesson_blocks((LESSONS / f"{name}.txt").read_text(encoding="utf-8"))
    lesson, correction = blocks["teach"], blocks["correction"]
    probes, twin = parse_probes(probes_text), parse_twin(probes_text)
    report: Dict[str, Any] = {"lesson": name, "said": len(lesson) + len(correction), "results": [],
                              "lint": lint_lesson(lesson + correction), "twin": twin, "transfer": [],
                              "control": [], "control_run": False}
    if report["lint"]:
        return report                                     # nothing is said to her until it passes lint
    sections = [x for x in SECTIONS if not only or x == only]
    aurora, systems, extract = _boot(state_dir)
    report["results"] = _play(aurora, systems, extract, probes, lesson, correction, {}, sections)
    if not quick:
        # control: a fresh copy, taught nothing, asked what the lesson would have taught it
        a2, s2, e2 = _boot(state_dir)
        report["control_run"] = True
        for r in _play(a2, s2, e2, probes, lesson, correction, {}, ("after",), teach=False):
            if r["ok"]:
                report["control"].append(r)
        # a probe that holds with nothing taught shows nothing about the lesson: it does not count as held
        untaught = {r["ask"] for r in report["control"]}
        for r in report["results"]:
            if r["section"] == "after" and r["ask"] in untaught:
                r["uninformative"] = True
        if twin:
            a3, s3, e3 = _boot(state_dir)
            report["transfer"] = _play(a3, s3, e3, probes, lesson, correction, twin,
                                       [x for x in sections if x in ("after", "after-correction")])
    gaps = [r for r in report["results"] if r["section"] == "gap"]
    rest = [r for r in report["results"] if r["section"] != "gap"]
    report["failed"] = sum(1 for r in rest if not r["ok"]) + sum(1 for r in report["transfer"] if not r["ok"])
    report["uninformative"] = sum(1 for r in rest if r.get("uninformative"))
    report["open_gaps"] = sum(1 for r in gaps if not r["ok"])
    report["gaps_now_held"] = sum(1 for r in gaps if r["ok"])
    return report


def status(report: Dict[str, Any]) -> Tuple[int, str]:
    if report["lint"]:
        return 3, "NOT SAID: lint findings"
    if report["failed"]:
        return 1, "FAILED"
    if report["open_gaps"]:
        return 2, f"NOT READY: {report['open_gaps']} open gap(s)"
    if report.get("uninformative"):
        return 2, (f"NOT READY: {report['uninformative']} probe(s) hold even untaught -- they are not evidence "
                   "(ask something only the lesson can answer)")
    if not report.get("control_run"):
        return 2, "NOT READY: the untaught control was not run, so nothing here shows the lesson did the work"
    return 0, "READY (probes held, transfer held, no open gaps)" if report["twin"] else "READY (no transfer twin declared -- generalization unchecked)"


def render(report: Dict[str, Any]) -> str:
    lines = [f"lesson {report['lesson']}: {report['said']} utterances"]
    for f in report["lint"]:
        lines.append(f"  LINT  {f['line']}\n        -> {f['why']}")
    for r in report["results"]:
        mark = ("PASS" if r["ok"] else "GAP " if r["section"] == "gap" else "FAIL")
        if r.get("uninformative"):
            mark = "PASS but NOT EVIDENCE (holds untaught)"
        if r["section"] == "gap" and r["ok"]:
            mark = "PASS (gap now holds -- promote it to [after])"
        lines.append(f"  [{r['section']}] {mark}  {r['ask']}")
        lines.append(f"        she said: {r['reply'] or '(nothing)'}   [{r['src'] or '-'}]")
        for w in r["why"]:
            lines.append(f"        -> {w}")
    if report["twin"]:
        lines.append("  transfer (twin: " + " ".join(f"{a}={b}" for a, b in report["twin"].items()) + ")")
        for r in report["transfer"]:
            lines.append(f"    [{r['section']}] {'PASS' if r['ok'] else 'FAIL'}  {r['ask']}  ->  {r['reply'] or '(nothing)'}")
            for w in r["why"]:
                lines.append(f"        -> {w}")
    for r in report["control"]:
        lines.append(f"  CONTROL  holds even untaught (not evidence): {r['ask']}  ->  {r['reply']}")
    code, word = status(report)
    n = len([r for r in report["results"] if r["section"] != "gap"])
    held = sum(1 for r in report["results"] if r["section"] != "gap" and r["ok"] and not r.get("uninformative"))
    lines.append(f"{held}/{n} probes held as evidence; {word}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lesson")
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"), help="copied; never modified")
    ap.add_argument("--only", choices=SECTIONS)
    ap.add_argument("--quick", action="store_true", help="skip the control and twin runs (one boot)")
    ap.add_argument("--lint-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.lint_only:
        blocks = parse_lesson_blocks((LESSONS / f"{a.lesson}.txt").read_text(encoding="utf-8"))
        findings = lint_lesson(blocks["teach"] + blocks["correction"])
        for f in findings:
            print(f"LINT  {f['line']}\n      -> {f['why']}")
        print("lint clean" if not findings else f"{len(findings)} finding(s)")
        return 3 if findings else 0
    report = run(a.lesson, Path(a.state_dir), a.only, a.quick)
    print(json.dumps(report, indent=1) if a.json else render(report))
    return status(report)[0]


def _cleanup() -> None:
    for d in _SCRATCH:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    try:
        code = main()
    finally:
        _cleanup()
    sys.stdout.flush()
    os._exit(code)          # her background threads must not hold the process open
