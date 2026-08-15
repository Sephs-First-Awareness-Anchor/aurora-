#!/usr/bin/env python3
"""
Regression coverage for Subsurface Presence and Evidence Scout spec,
section 11: "Only Subsurface may consume ScoutReport... Surface must
never directly read scout_results."

These are source-level structural checks, not behavioral ones on
purpose -- the guarantee this spec section makes is about which MODULES
are even allowed to call ScoutBroker.poll_reports() / read
scout_reports/, and that has to hold whether or not a given test run
happens to exercise the code path. A future contributor adding
`from aurora_internal.scouting.broker import ScoutBroker` inside
aurora_surface_daemon.py or aurora.py should fail these tests even if
they never call poll_reports() at all.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Surface-side modules: must never import the Scout broker at all.
_SURFACE_MODULES = ["aurora_surface_daemon.py", "aurora.py"]

# The one module allowed to actually poll ScoutBroker for reports.
_SUBSURFACE_CONSUMER = "aurora_internal/scouting/subsurface_scout_bridge.py"


# Everything below inspects real AST nodes (imports, attribute/call
# names), never raw substrings -- so prose in a docstring or comment
# that happens to mention "ScoutBroker" or "poll_reports" (as this very
# file's own docstrings do, and as aurora_daemon.py's explanatory
# comments do) can never produce a false positive or false negative.

def _parse(path: str) -> ast.Module:
    with open(path, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _imported_names(tree: ast.Module) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def _imported_symbols(tree: ast.Module) -> set:
    symbols = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            for alias in node.names:
                symbols.add(alias.asname or alias.name)
    return symbols


def _poll_reports_call_sites(tree: ast.Module) -> list:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "poll_reports"
    ]


def test_surface_modules_never_import_scout_broker():
    for rel in _SURFACE_MODULES:
        tree = _parse(os.path.join(_REPO_ROOT, rel))
        imported_modules = _imported_names(tree)
        imported_symbols = _imported_symbols(tree)
        assert "aurora_internal.scouting.broker" not in imported_modules, (
            f"{rel} must never import from the Scout broker module -- only "
            f"{_SUBSURFACE_CONSUMER} (via aurora_daemon.py) may poll scout reports"
        )
        assert "ScoutBroker" not in imported_symbols, f"{rel} must never import ScoutBroker"


def test_surface_modules_never_call_poll_reports():
    for rel in _SURFACE_MODULES:
        tree = _parse(os.path.join(_REPO_ROOT, rel))
        assert _poll_reports_call_sites(tree) == [], f"{rel} must never call .poll_reports()"


def test_subsurface_bridge_is_the_only_module_calling_broker_poll_reports():
    # Walk the whole repo's top-level *.py and aurora_internal/**/*.py,
    # excluding tests/ and the broker's own definition, and confirm the
    # bridge is the only production module with a real .poll_reports()
    # call site (an AST Call node, not just the substring appearing in
    # documentation prose somewhere).
    hits = []
    for dirpath, dirnames, filenames in os.walk(_REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "tests", "__pycache__", "flutter_app", "node_modules")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, _REPO_ROOT)
            if rel in ("aurora_internal/scouting/broker.py", _SUBSURFACE_CONSUMER):
                continue
            if _poll_reports_call_sites(_parse(full)):
                hits.append(rel)
    assert hits == [], f"unexpected poll_reports() callers outside the Subsurface bridge: {hits}"


def test_aurora_daemon_wires_the_subsurface_bridge_not_the_broker_directly():
    tree = _parse(os.path.join(_REPO_ROOT, "aurora_daemon.py"))
    imported_modules = _imported_names(tree)
    imported_symbols = _imported_symbols(tree)
    assert "aurora_internal.scouting.subsurface_scout_bridge" in imported_modules
    assert "consume_scout_reports" in imported_symbols
    assert "aurora_internal.scouting.broker" not in imported_modules
    assert "ScoutBroker" not in imported_symbols
