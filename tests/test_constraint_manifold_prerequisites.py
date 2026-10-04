"""The constraint manifold is the foundation language is meant to emerge from.

These pin the defects that kept it from existing at all in the real process:
  * an import cycle through dead imports switched the manifold OFF whenever
    aurora_ivm (or `aurora`, the real entry point) was imported first, so no node
    ever carried a constraint vector;
  * the developmental gate's Clause I read a field no envelope has;
  * MemoryEvent.from_envelope ignored the envelope's own vector;
  * the expression-misfit deposit omitted the geometry ingest_event requires.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import ast
import inspect
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _manifold_available_after_importing(first: str) -> str:
    code = (
        f"import importlib; importlib.import_module({first!r}); "
        "import aurora_ivm as I; print('AVAILABLE=' + str(I.CONSTRAINT_MANIFOLD_AVAILABLE))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                         capture_output=True, text=True, timeout=240)
    lines = [l for l in out.stdout.splitlines() if l.startswith("AVAILABLE=")]
    assert lines, out.stderr[-400:]
    return lines[-1]


# ---- the import cycle ------------------------------------------------------------

@pytest.mark.parametrize("first", [
    "aurora_ivm",
    "aurora_internal.aurora_noncomp_registry",
    "aurora_constraint_manifold",
    "aurora_constraint_engine",
])
def test_manifold_is_available_whichever_module_is_imported_first(first):
    assert _manifold_available_after_importing(first) == "AVAILABLE=True"


def test_manifold_is_available_through_the_real_entry_point():
    """`import aurora` is what the app and the CLI do; it used to give False."""
    assert _manifold_available_after_importing("aurora") == "AVAILABLE=True"


def test_registry_has_no_import_time_edge_back_to_ivm():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_noncomp_registry.py"),
               encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.ImportFrom):
            assert node.module != "aurora_ivm", "module-level import of aurora_ivm closes the cycle"


def test_registry_still_forwards_the_names_it_used_to_import():
    from aurora_internal import aurora_noncomp_registry as reg
    import aurora_ivm
    for name in ("ALIGNMENT_VOTE_WEIGHT", "REACT_GAIN", "ALIGN_GAIN", "LEVEL_TO_AXIS"):
        assert getattr(reg, name) is getattr(aurora_ivm, name)
    with pytest.raises(AttributeError):
        reg.NOT_A_REAL_NAME


# ---- Clause I ----------------------------------------------------------------------

def test_clause_i_reads_the_constraint_vector_the_envelope_actually_has():
    from aurora_consciousness_engine import _envelope_has_constraint_origin as has
    assert has(SimpleNamespace(constraint_vector=object())) is True
    assert has(SimpleNamespace(constraint_vector=None)) is False
    assert has(SimpleNamespace()) is False
    assert has(SimpleNamespace(constraint_signature={"X": 1.0}, constraint_vector=None)) is True


# ---- the memory event's geometry ------------------------------------------------------

def _cv(**kw):
    from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
    return ConstraintVector(**kw)


def test_memory_event_takes_the_envelopes_own_constraint_vector():
    from aurora_sedimemory import MemoryEvent
    cv = _cv(X=1.0, T=0.2, N=0.3, B=0.4, A=0.9)
    ev = MemoryEvent.from_envelope(SimpleNamespace(constraint_vector=cv, data="hello", mode=None))
    got = ev.constraint_vector
    assert (got.X, got.T, got.N, got.B, got.A) == (1.0, 0.2, 0.3, 0.4, 0.9)


def test_memory_event_legacy_weight_fallback_is_unchanged():
    from aurora_sedimemory import MemoryEvent
    ev = MemoryEvent.from_envelope(SimpleNamespace(
        existence_weight=0.9, temporal_weight=0.1, energy_weight=0.2,
        boundary_weight=0.3, agency_weight=0.4))
    got = ev.constraint_vector
    assert (got.X, got.T, got.N, got.B, got.A) == (0.9, 0.1, 0.2, 0.3, 0.4)


# ---- the shared aggregate vector ------------------------------------------------------

def test_aggregate_constraint_vector_helper():
    import aurora
    dim = SimpleNamespace(get_constraint_aggregate=lambda: {"X": 0.0, "T": 0.6, "N": 0.2, "B": 0.1, "A": 0.4})
    v = aurora._aggregate_constraint_vector({"dimensional": dim})
    assert v is not None and v.X == 0.01 and v.T == 0.6 and v.A == 0.4
    assert aurora._aggregate_constraint_vector({}) is None
    assert aurora._aggregate_constraint_vector({"dimensional": SimpleNamespace(get_constraint_aggregate=lambda: {})}) is None
    assert aurora._aggregate_constraint_vector(None) is None


# ---- static guard: every ingest_event call supplies its geometry --------------------------

def test_no_ingest_event_call_omits_the_constraint_vector():
    """SediMemory.ingest_event(content, constraint_vector, ...) requires the vector. A call
    with only a content dict raised TypeError inside a swallowing handler, silently."""
    from aurora_sedimemory import SediMemory
    assert "constraint_vector" in inspect.signature(SediMemory.ingest_event).parameters
    offenders = []
    for fname in ("aurora.py", "aurora_warp_protocol.py", "aurora_constraint_emission.py"):
        src = open(os.path.join(REPO_ROOT, fname), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "ingest_event"):
                kws = {k.arg for k in node.keywords}
                if len(node.args) < 2 and "constraint_vector" not in kws:
                    offenders.append(f"{fname}:{node.lineno}")
    assert not offenders, offenders
