#!/usr/bin/env python3
"""
Regression coverage for the Aurora Build 694 spec's step 5: Android
must actually start the lightweight SubsurfacePresenceRuntime after
boot_aurora() succeeds inside aurora_bridge.initialize() -- never a
second full Aurora (aurora_daemon.main() or a second boot_aurora()).
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ANDROID_PY_DIR = os.path.join(_REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")
_BRIDGE_PATH = os.path.join(_ANDROID_PY_DIR, "aurora_bridge.py")


def _bridge_source() -> str:
    with open(_BRIDGE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _initialize_source() -> str:
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "initialize":
            return ast.get_source_segment(_bridge_source(), node) or ""
    raise AssertionError("aurora_bridge.py has no top-level initialize() function")


def test_initialize_imports_and_calls_start_subsurface_presence_runtime():
    source = _initialize_source()
    assert "start_subsurface_presence_runtime" in source
    assert "from aurora_internal.dual_strata.subsurface_presence_runtime import" in source


def test_initialize_starts_the_runtime_only_after_boot_aurora_succeeds():
    source = _initialize_source()
    boot_idx = source.find("boot_aurora(")
    runtime_idx = source.find("start_subsurface_presence_runtime(")
    assert boot_idx != -1 and runtime_idx != -1
    assert runtime_idx > boot_idx, "presence runtime must start AFTER boot_aurora(), not before"


def test_aurora_bridge_never_calls_aurora_daemon_main():
    # Spec section 5: "Do not start a second full Aurora inside Android.
    # Do not call aurora_daemon.main() from the app." AST-based (real
    # Call nodes), not a substring search -- this file's own comments
    # explaining what NOT to do would otherwise trip a naive check.
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("main", "run")
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "aurora_daemon"
        ):
            raise AssertionError(f"aurora_bridge.py must never call aurora_daemon.{node.func.attr}()")


def test_aurora_bridge_never_imports_aurora_daemon_module():
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert "aurora_daemon" not in imported


def test_presence_runtime_start_site_wraps_failure_so_boot_cannot_be_broken_by_it():
    # A presence-runtime start failure must degrade gracefully, never
    # take down Aurora's boot entirely -- confirmed structurally: the
    # Call node for start_subsurface_presence_runtime() must sit inside
    # a Try node's own body (its own try/except), not bare in
    # initialize()'s top-level statement list where an exception would
    # propagate out and fail the whole boot.
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    init_fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "initialize"
    )

    def _call_is_named(node, name):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
        )

    found_in_try = False
    for node in ast.walk(init_fn):
        if not isinstance(node, ast.Try):
            continue
        for inner in ast.walk(node):
            if inner is node:
                continue
            if any(_call_is_named(c, "start_subsurface_presence_runtime") for c in ast.walk(inner)):
                # Confirm the call is inside node.body (the try clause
                # itself), not inside node.handlers/orelse/finalbody.
                for stmt in node.body:
                    if any(_call_is_named(c, "start_subsurface_presence_runtime") for c in ast.walk(stmt)):
                        found_in_try = True
                break
        if found_in_try:
            break

    assert found_in_try, "start_subsurface_presence_runtime() call must be inside its own try: block"
