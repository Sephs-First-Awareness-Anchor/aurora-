#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_undefined_names_in_live_paths.py -- names that raised NameError at run
time on main, and a guard so no new one slips into these modules.

Fixed (each confirmed by reading the code, not only by pyflakes):

- aurora._build_comprehension_response passed `search_prompt_text`, a local
  of _run_live_response_turn, to _poedex_lookup_evidence at both of its
  explicit-lookup sites.  The NameError was swallowed by the surrounding
  boundary handler, so every explicit lookup on this path silently did
  nothing.  It now derives the prompt the way _run_live_response_turn does.
- aurora_bridge.habitat_reset (phone) imported json as _json and then called
  json.dumps, so the Hub's reset always raised.
- aurora_hub: five Tk callbacks formatted `exc` inside a lambda run after the
  except block ended (Python deletes the name there), so the error line never
  printed; `_run_learn` called subprocess, which the module never imports.

Left as they are, because none of them runs: string annotations of names that
are only types ("TurnLedger", "tk.Frame", "GeologicalBaseline",
"ConstraintEvolutionarySimulator"), and statements after a `return` in
aurora.py (lines that reference meaning_profile_for_signature/value and
verbose).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_APP_PY = _REPO / "flutter_app" / "android" / "app" / "src" / "main" / "python"

# Known, harmless: only ever annotations, or code after a return.
_ALLOWED = {
    "aurora.py": {"meaning_profile_for_signature", "value", "TurnLedger", "verbose"},
    "aurora_hub.py": {"tk"},
    "flutter_app/android/app/src/main/python/aurora_bridge.py": {
        "GeologicalBaseline", "ConstraintEvolutionarySimulator"},
}


def _undefined_names(rel_path: str):
    checker_mod = pytest.importorskip("pyflakes.checker")
    from pyflakes import messages
    source = (_REPO / rel_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=rel_path)
    checker = checker_mod.Checker(tree, filename=rel_path)
    return {m.message_args[0] for m in checker.messages
            if isinstance(m, messages.UndefinedName)}


@pytest.mark.parametrize("rel_path", sorted(_ALLOWED))
def test_no_new_undefined_names(rel_path):
    found = _undefined_names(rel_path)
    assert found <= _ALLOWED[rel_path], sorted(found - _ALLOWED[rel_path])


def test_comprehension_lookup_derives_its_own_prompt_text():
    source = (_REPO / "aurora.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == "_build_comprehension_response")
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert "search_prompt_text" not in names
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "_poedex_lookup_evidence"]
    assert len(calls) == 2
    for call in calls:
        kw = {k.arg: ast.unparse(k.value) for k in call.keywords}
        assert "lookup_request" in kw["request_text"]
        assert "user_text" in kw["request_text"]


def test_phone_habitat_reset_answers_when_no_habitat(monkeypatch):
    if not (_APP_PY / "aurora_bridge.py").exists():
        pytest.skip("app aurora_bridge.py not found")
    monkeypatch.syspath_prepend(str(_APP_PY))
    ab = pytest.importorskip("aurora_bridge")
    monkeypatch.setattr(ab, "_habitat", None)
    assert json.loads(ab.habitat_reset()) == {"error": "habitat_not_initialized"}


def test_phone_habitat_reset_reports_success(monkeypatch):
    if not (_APP_PY / "aurora_bridge.py").exists():
        pytest.skip("app aurora_bridge.py not found")
    monkeypatch.syspath_prepend(str(_APP_PY))
    ab = pytest.importorskip("aurora_bridge")

    class _Habitat:
        reset_calls = 0

        def reset(self):
            _Habitat.reset_calls += 1

    monkeypatch.setattr(ab, "_habitat", _Habitat())
    assert json.loads(ab.habitat_reset()) == {"success": True}
    assert _Habitat.reset_calls == 1
