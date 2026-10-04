"""What the genealogy's pressure curves have learned must survive a restart.

pressure_orientation() -- the grammar engine's designed orientation source -- reads each axis's
curve correction. The curves were reported (get_stats) but never saved, so the orientation reset
to a flat 1.0 on every boot and had to be relearned from nothing, in every process that carries
a genealogy.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import json
import os
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem  # noqa: E402
from aurora_internal.constraint_genealogy import PressureComplexityCurve  # noqa: E402


def _logger(d=None):
    return ConstraintGenealogyLogger(run_id="t", config=GenealogyConfig(), output_dir=d or tempfile.mkdtemp())


def _learn(g, n=12):
    """Drive real observations so the per-axis curves move off their birth value."""
    for i in range(n):
        before = PressureVec(X=0.9, T=0.5, N=0.2 + 0.05 * (i % 4), B=0.7, A=0.1)
        after = PressureVec(X=0.4, T=0.5, N=0.2, B=0.3, A=0.1)
        g.observe(pressure_before=before, trace=[TraceItem(kind="ABILITY", id="a_%d" % (i % 3))],
                  pressure_after=after, state_sig_before="s%d" % i, state_sig_after="s%d" % (i + 1), notes={})
    return g


# ---- the curve ----------------------------------------------------------------------------------

def _moved_curve():
    c = PressureComplexityCurve()
    for t in range(1, 30):
        c.record_tick(10 + t, 3, 1.5 + 0.1 * (t % 5), t)
        c.record_outcome(0.4 + 0.02 * (t % 7))
    return c


def test_a_curve_round_trips_what_it_learned():
    a = _moved_curve()
    b = PressureComplexityCurve()
    assert b.load_state(json.loads(json.dumps(a.to_state())))
    assert b.correction == pytest.approx(a.correction) and b.phase == a.phase
    assert b._net_ema == pytest.approx(a._net_ema) and b._error_ema == pytest.approx(a._error_ema)
    assert list(b._samples) == list(a._samples) and list(b._predictions) == list(a._predictions)


def test_a_restored_curve_keeps_its_windows_bounded():
    a = _moved_curve()
    b = PressureComplexityCurve()
    b.load_state(a.to_state())
    for t in range(500):
        b.record_tick(5, 1, 1.0, 100 + t)
    assert len(b._samples) <= PressureComplexityCurve.WINDOW


def test_the_prediction_in_flight_is_not_carried_across_a_restart():
    a = _moved_curve()
    a._pending_prediction = {"stale": True}
    b = PressureComplexityCurve()
    b.load_state(a.to_state())
    assert b._pending_prediction is None


@pytest.mark.parametrize("bad", [None, {}, "oops", {"_correction": "x"}, {"_correction": 1.0}])
def test_unusable_state_leaves_the_curve_untouched(bad):
    c = PressureComplexityCurve()
    before = c.to_state()
    assert c.load_state(bad) is False
    assert c.to_state() == before


# ---- the logger -----------------------------------------------------------------------------------

def test_orientation_survives_a_restart():
    d = tempfile.mkdtemp()
    g = _learn(_logger(d))
    learned = g.pressure_orientation()
    assert len({round(v, 3) for v in learned.values()}) > 1, "something must have been learned to persist"
    g._write_tick_state_file()
    g2 = _logger(d)
    assert g2.pressure_orientation() == {ax: 1.0 for ax in learned}, "a fresh logger starts flat"
    assert g2.restore_tick_state() is True
    assert g2.pressure_orientation() == pytest.approx(learned)


def test_the_curves_ride_in_the_existing_tick_state_file():
    d = tempfile.mkdtemp()
    g = _learn(_logger(d))
    g._write_tick_state_file()
    raw = json.load(open(os.path.join(d, "tick_state.json")))
    assert {"tick_count", "last_promotion_tick", "curves"} <= set(raw)
    assert set(raw["curves"]["axes"]) == {"X", "T", "N", "B", "A"}


def test_a_tick_state_file_from_before_curves_still_restores():
    d = tempfile.mkdtemp()
    json.dump({"tick_count": 77, "last_promotion_tick": 5}, open(os.path.join(d, "tick_state.json"), "w"))
    g = _logger(d)
    assert g.restore_tick_state() is True and g.tick_count == 77
    assert g.pressure_orientation() == {ax: 1.0 for ax in "XTNBA"}


def test_curves_restore_even_without_a_tick_count():
    d = tempfile.mkdtemp()
    g = _learn(_logger(d))
    g.tick_count = 0
    g._write_tick_state_file()
    g2 = _logger(d)
    assert g2.restore_tick_state() is True
    assert g2.pressure_orientation() == pytest.approx(g.pressure_orientation())


def test_a_corrupt_curve_block_does_not_lose_the_tick_state():
    d = tempfile.mkdtemp()
    json.dump({"tick_count": 9, "last_promotion_tick": 1, "curves": {"axes": {"X": "junk"}, "global": 5}},
              open(os.path.join(d, "tick_state.json"), "w"))
    g = _logger(d)
    assert g.restore_tick_state() is True and g.tick_count == 9


# ---- who writes what ----------------------------------------------------------------------------------

def test_the_canonical_logger_flushes_everything():
    g = _learn(_logger())
    called = []
    g.flush_files = lambda: called.append("flush")
    g.persist_session_state()
    assert called == ["flush"]


def test_the_surface_logger_writes_only_its_own_session_state():
    d = tempfile.mkdtemp()
    g = _learn(_logger(d))
    g.persist_scope = "session_state"
    g.persist_session_state()
    assert sorted(os.listdir(d)) == ["tick_state.json"], "never the canonical abilities/links/pair files"


def test_the_surface_boot_scopes_its_logger_and_the_daemon_saves_it():
    boot = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = boot.index("_surface_genealogy.persist_scope = \"session_state\"")
    assert boot.index("_restore_genealogy_state(_surface_genealogy, _gen_src)") > i, "scoped before it restores"
    daemon = open(os.path.join(REPO_ROOT, "aurora_daemon.py"), encoding="utf-8").read()
    assert "persist_session_state()" in daemon and 'persist_scope", "") == "session_state"' in daemon
