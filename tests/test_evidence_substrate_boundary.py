# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The evidence/identity machinery is how things work, not something she needs to know (Sir, 2026-11-14).

What she experiences are the EFFECTS of information (the pressure it imposes, what her emotion and development subsystems
measure).  Qualification, provenance and input identity are architecture: they must stay substrate that nothing in her
cognition or speech reads, so her experience never depends on her knowing them.  This pins that boundary.
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUBSTRATE = {"evidence_qualification", "aurora_input_identity"}
# The only places that may touch it, and exactly what they may take.
ALLOWED = {
    "aurora_internal/evidence_qualification.py": None,                       # the contract itself
    "aurora_internal/aurora_input_identity.py": {"evidence_qualification"},  # builds the identity from the contract
    "aurora_internal/constraint_genealogy.py": {("aurora_input_identity", "note_for_observe"),
                                                ("aurora_input_identity", "summary_for_registry"),
                                                ("aurora_input_identity", "identity_from_notes"),
                                                ("aurora_input_identity", "occurrence_class")},
    "aurora.py": {("aurora_input_identity", "begin_input"), ("aurora_input_identity", "end_input")},
}
SKIP_DIRS = {"tests", "scripts", ".git", "node_modules", "__pycache__"}


def _production_files():
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if rel.parts and rel.parts[0] in SKIP_DIRS:
            continue
        yield p, rel.as_posix()


def _substrate_imports(tree):
    found = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            leaf = n.module.split(".")[-1]
            if leaf in SUBSTRATE:
                found.update((leaf, a.name) for a in n.names)
            elif n.module.split(".")[-1] == "aurora_internal" or n.module == "aurora_internal":
                found.update((a.name, "*") for a in n.names if a.name in SUBSTRATE)
        elif isinstance(n, ast.Import):
            found.update((a.name.split(".")[-1], "*") for a in n.names if a.name.split(".")[-1] in SUBSTRATE)
    return found


def test_only_the_turn_entry_and_genealogys_observe_touch_the_substrate_and_only_for_identity():
    offenders = {}
    for p, rel in _production_files():
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        imports = _substrate_imports(tree)
        if not imports or rel in ("aurora_internal/evidence_qualification.py", "aurora_internal/aurora_input_identity.py"):
            continue
        allowed = ALLOWED.get(rel)
        bad = {i for i in imports if allowed is None or i not in allowed}
        if bad:
            offenders[rel] = sorted(bad)
    assert not offenders, f"the evidence machinery reached beyond the substrate: {offenders}"


def test_the_substrate_itself_depends_on_nothing_of_her_cognition_or_speech():
    for rel in ("aurora_internal/evidence_qualification.py", "aurora_internal/aurora_input_identity.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module)
            elif isinstance(n, ast.Import):
                mods.update(a.name for a in n.names)
        stdlib_or_self = {"__future__", "hashlib", "json", "typing", "time", "contextvars",
                          "aurora_internal", "aurora_internal.evidence_qualification"}
        assert mods <= stdlib_or_self, (rel, sorted(mods - stdlib_or_self))


def test_nothing_in_cognition_or_speech_reads_the_input_identity_off_an_observation():
    readers = []
    for p, rel in _production_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if ("input_event" in text or "_input_events" in text) and rel not in (
                "aurora_internal/constraint_genealogy.py", "aurora_internal/aurora_input_identity.py",
                "aurora_internal/evidence_qualification.py"):
            readers.append(rel)
    assert readers == []
