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

# Surface-side modules: must never hold a ScoutBroker instance or call
# .poll_reports() -- that instance would also expose .claim_next()/
# .submit_report(), none of which Surface may ever touch. Build 694 step
# 9 tightens this further than the prior build's step 10: Surface no
# longer even dispatches a ScoutRequest itself (dispatch_scout_request()
# included) -- it only publishes an evidence_need event via
# subsurface_presence.write_evidence_need(); Subsurface owns the actual
# dispatch from there (integrate_evidence_need_event()).
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


def test_surface_modules_never_import_scout_broker_class():
    # Must never import the ScoutBroker class itself -- holding an
    # instance would also hand Surface .poll_reports()/.claim_next()/
    # .submit_report(), none of which it may ever call.
    for rel in _SURFACE_MODULES:
        tree = _parse(os.path.join(_REPO_ROOT, rel))
        imported_symbols = _imported_symbols(tree)
        assert "ScoutBroker" not in imported_symbols, f"{rel} must never import the ScoutBroker class"


def test_surface_modules_never_import_anything_from_scouting_broker():
    # Build 694 step 9: Surface no longer reaches into
    # aurora_internal.scouting.broker AT ALL (not even the thin
    # dispatch_scout_request() free function) -- it only ever describes
    # a need via subsurface_presence.write_evidence_need(). Subsurface is
    # the sole module that imports scouting.broker to actually dispatch.
    for rel in _SURFACE_MODULES:
        tree = _parse(os.path.join(_REPO_ROOT, rel))
        imported_modules = _imported_names(tree)
        assert "aurora_internal.scouting.broker" not in imported_modules, (
            f"{rel} must never import aurora_internal.scouting.broker directly"
        )


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
    # aurora_daemon.py IS allowed to import dispatch_scout_request from
    # aurora_internal.scouting.broker (spec step 11: Subsurface's own
    # recurring-issue self-diagnostic research dispatches a ScoutRequest,
    # same as Surface does in step 10 -- broker.py's own docstring says
    # "Surface/Subsurface -> dispatch()"). What it must never do is hold
    # a ScoutBroker instance directly for polling -- consume_scout_reports()
    # in the bridge remains the sole poll_reports() call site (proven by
    # test_subsurface_bridge_is_the_only_module_calling_broker_poll_reports
    # above, which scans the whole repo, not just this one file).
    tree = _parse(os.path.join(_REPO_ROOT, "aurora_daemon.py"))
    imported_modules = _imported_names(tree)
    imported_symbols = _imported_symbols(tree)
    assert "aurora_internal.scouting.subsurface_scout_bridge" in imported_modules
    assert "consume_scout_reports" in imported_symbols
    assert "ScoutBroker" not in imported_symbols


def test_aurora_publishes_evidence_need_via_subsurface_presence():
    # Positive coverage for Build 694 step 9: aurora.py IS allowed to
    # reach subsurface_presence.write_evidence_need() (imported inside
    # _try_poedex_lookup) -- this is the other half of the boundary the
    # tests above enforce negatively. A dynamic import check (not just
    # source text) proves the real module actually exports the name
    # aurora.py expects.
    from aurora_internal.dual_strata.subsurface_presence import write_evidence_need
    assert callable(write_evidence_need)

    tree = _parse(os.path.join(_REPO_ROOT, "aurora.py"))
    found = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "aurora_internal.dual_strata.subsurface_presence"
        and any(alias.name == "write_evidence_need" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert found, "aurora.py should publish evidence needs via subsurface_presence.write_evidence_need()"


def test_aurora_no_longer_imports_dispatch_scout_request_directly():
    # Negative coverage: the old direct-dispatch path this replaces.
    tree = _parse(os.path.join(_REPO_ROOT, "aurora.py"))
    found = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "aurora_internal.scouting.broker"
        and any(alias.name == "dispatch_scout_request" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert not found, "aurora.py must not import dispatch_scout_request directly anymore (Build 694 step 9)"
