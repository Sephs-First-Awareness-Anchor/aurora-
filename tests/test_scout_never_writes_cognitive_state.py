#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_scout_never_writes_cognitive_state.py -- the Scout worker is a
courier, not cortex (spec section 4). Structurally, it must never even
import the modules that hold Aurora's cognitive state (understanding
pipeline, working memory, belief/consequence systems), let alone write
to them -- checked at import time, the same "has to hold even without
the code path being exercised" discipline as
test_scout_report_routes_only_to_subsurface.py.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Modules that hold or mutate Aurora's cognitive state -- a Scout worker
# has no legitimate reason to import any of these.
_COGNITIVE_STATE_MODULES = (
    "aurora",
    "aurora_daemon",
    "aurora_internal.aurora_turn_chain",
    "aurora_internal.aurora_working_memory",
    "aurora_working_memory",
)


def _imported_names(path: str) -> set:
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def test_scout_daemon_never_imports_any_cognitive_state_module():
    imported = _imported_names(os.path.join(_REPO_ROOT, "aurora_scout_daemon.py"))
    hits = imported & set(_COGNITIVE_STATE_MODULES)
    assert hits == set(), f"aurora_scout_daemon.py must never import cognitive-state modules, found: {hits}"


def test_scout_daemon_never_imports_at_runtime_either():
    # Belt and suspenders: the import-time check above is static; this
    # confirms it holds after actually importing and using the module,
    # same pattern as test_scout_worker.py's isolation test.
    before = set(sys.modules.keys())
    import aurora_scout_daemon  # noqa: F401
    after = set(sys.modules.keys())
    newly_imported = after - before
    assert not (newly_imported & set(_COGNITIVE_STATE_MODULES))


def test_scout_report_has_no_field_capable_of_addressing_cognitive_state():
    # Structural: ScoutReport's fields are all evidence-shaped
    # (status/evidence_items/response_relationships/fit_rationales/
    # contradictions/provenance/confidence) -- none of them is a
    # reference, path, or handle that could point at or mutate
    # TurnUnderstandingState, WorkingMemory, or any belief/consequence
    # store.
    from aurora_internal.scouting.contracts import ScoutReport
    field_names = set(ScoutReport.__dataclass_fields__.keys())
    forbidden_shapes = {"state_ref", "working_memory_ref", "belief_update", "consequence_write", "understanding_state"}
    assert not (field_names & forbidden_shapes)


def test_broker_worker_side_methods_never_take_a_systems_or_state_argument():
    # claim_next()/submit_report() are the only two methods a Scout
    # worker process calls -- neither accepts anything resembling
    # Aurora's live systems dict or cognitive state object, structurally
    # ruling out a worker writing into it even by accident.
    import inspect
    from aurora_internal.scouting.broker import ScoutBroker

    for method_name in ("claim_next", "submit_report"):
        sig = inspect.signature(getattr(ScoutBroker, method_name))
        param_names = set(sig.parameters.keys()) - {"self"}
        assert not (param_names & {"systems", "state", "understanding_state"})
