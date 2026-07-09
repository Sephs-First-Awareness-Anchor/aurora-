# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the CERS shadow-pass error visibility fix.

ConsciousnessEngine._attach_dual_strata_snapshot() runs CERSBridge.build_snapshot()
as a read-only shadow pass and wraps it in `except Exception: pass` --
correctly, since CERS is experimental and must never break a live turn. But
a bare `pass` means a broken shadow regulator is invisible forever: if
CERSBridge starts raising on every turn, nothing on disk would ever show it.
This locks in that a CERS failure is now captured to a private
cers_error_log.jsonl (never read by the surface daemon) instead of vanishing
silently, while the caller still sees no exception.
"""
import json
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_consciousness_engine import ConsciousnessEngine


class _FakeSnapshot:
    subsurface_state = {"sub_crests": []}
    conscious_frame = {}


class _FakeDualStrata:
    def build_snapshot(self, *args, **kwargs):
        return _FakeSnapshot()


class _RaisingCersBridge:
    def __init__(self, state_dir):
        self.state_dir = state_dir

    def build_snapshot(self, *args, **kwargs):
        raise RuntimeError("simulated CERS failure")


def _make_bare_engine(state_dir):
    engine = object.__new__(ConsciousnessEngine)
    engine.dual_strata = _FakeDualStrata()
    engine.cers_bridge = _RaisingCersBridge(state_dir)
    engine.lattice = None
    return engine


def test_cers_failure_is_logged_privately_and_never_raises(tmp_path):
    engine = _make_bare_engine(tmp_path)

    result = engine._attach_dual_strata_snapshot(
        types.SimpleNamespace(),
        payload="hello",
        payload_type="text",
        evidence={},
        frame_name="balanced",
    )

    assert result is not None, "the shadow pass failing must not break the real turn"

    log_path = tmp_path / "cers_error_log.jsonl"
    assert log_path.exists(), "a swallowed CERS exception must be captured somewhere"
    entries = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    assert len(entries) == 1
    assert "simulated CERS failure" in entries[0]["error"]
    assert abs(entries[0]["ts"] - time.time()) < 5


def test_cers_success_writes_no_error_log(tmp_path):
    engine = object.__new__(ConsciousnessEngine)
    engine.dual_strata = _FakeDualStrata()
    engine.lattice = None

    class _OkCersBridge:
        state_dir = tmp_path

        def build_snapshot(self, *args, **kwargs):
            return _FakeSnapshot()

    engine.cers_bridge = _OkCersBridge()

    engine._attach_dual_strata_snapshot(
        types.SimpleNamespace(),
        payload="hello",
        payload_type="text",
        evidence={},
        frame_name="balanced",
    )

    assert not (tmp_path / "cers_error_log.jsonl").exists()
