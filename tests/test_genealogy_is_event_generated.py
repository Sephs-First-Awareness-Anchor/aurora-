"""Genealogy stays causally / event generated: time passing alone creates no genealogical events or ancestry.

Authors: Sunni (Sir) Morningstar and Cael Devo

Sir's decision: existing genealogy may have time-dependent maturation, persistence or decay where that already follows
from its own physics, but there is no separate wall-clock lineage generator that creates events merely because time
elapsed. The metabolic clock's steps therefore never create, record or observe a genealogical event.
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aurora_internal.aurora_metabolic_steps as M  # noqa: E402

READ_ONLY = ("axis_relief", "get_", "read_", "status", "summary", "snapshot")


class GenealogySpy:
    """Records every call made on it. Reading its state is allowed; creating or recording events is not."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*a, **k):
            self.calls.append(name)
            return {}
        return call

    def writes(self):
        return [n for n in self.calls if not n.startswith(READ_ONLY)]


def _src(*parts):
    return open(os.path.join(REPO_ROOT, *parts), encoding="utf-8").read().lower()


def test_the_clocks_steps_contain_no_genealogy_or_lineage_generator():
    assert "genealogy" not in _src("aurora_internal", "aurora_metabolic_steps.py")
    assert "lineage" not in _src("aurora_internal", "aurora_metabolic_steps.py")


def test_the_clock_itself_contains_no_genealogy_or_lineage_generator():
    assert "genealogy" not in _src("aurora_internal", "aurora_metabolic_clock.py")
    assert "lineage" not in _src("aurora_internal", "aurora_metabolic_clock.py")


def test_the_core_variant_of_understanding_does_not_dispatch_to_genealogy():
    """run_reflection_cycle records the Understanding as its own genealogy event at SURFACE time (event-caused);
    the deferred core half must not record it a second time or invent ancestry."""
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_understanding_contract.py"), encoding="utf-8").read()
    assert "no longer dispatched" in src, "the cascade documents that genealogy is not dispatched from it"
    start = src.index("def process_core_queue")
    body = src[start:src.index("\n    def ", start + 10)]
    assert "genealogy" not in body.lower()


def test_processing_the_core_queue_and_the_lattice_during_a_long_rest_writes_no_genealogy():
    from test_core_understanding import _core_sys
    s, c = _core_sys(4, gross=10.0)
    spy = GenealogySpy()
    s["genealogy"] = spy
    s["constraint_genealogy"] = spy
    M.step_core_understanding(1.0, s)
    M.step_lattice(1.0, s)
    assert c.core_pending == 0, "the work really ran"
    assert spy.writes() == [], f"time/core work must not create events; saw {spy.writes()}"


@pytest.mark.parametrize("rest_ticks", [1.0, 12.0, 96.0, 288.0, 5000.0])
def test_a_rest_of_any_length_opens_and_closes_without_touching_genealogy(rest_ticks):
    from test_core_understanding import _rested_sys
    s, c = _rested_sys(3, coherence=0.8, rest=rest_ticks)
    spy = GenealogySpy()
    s["genealogy"] = spy
    s["constraint_genealogy"] = spy
    M.step_rest_open(rest_ticks, s)
    M.step_core_understanding(rest_ticks, s)
    M.step_lattice(rest_ticks, s)
    M.step_rest_close(rest_ticks, s)
    assert spy.calls == [], f"a rest of {rest_ticks} ticks touched genealogy: {spy.calls}"
