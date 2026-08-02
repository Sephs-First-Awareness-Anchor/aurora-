# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW3 of the Architecture Wiring Audit (2026-07-20, F4): QuasiArch is a real,
fed diagnostic lattice that the live system never actually asked anything --
its read/consult surfaces (record_warp_emergence, get_pressure_trace,
waveform_turn_summary, get_doctrine_candidates) had zero callers anywhere.

record_warp_emergence was found already wired (aurora.py's
_h_surface_emergence pathway handler, registered for WarpPathway.
SURFACE_EMERGENCE) by the time this landed -- no change needed there.

This closes the remaining two:
  1. scripts/aurora_ci_segment.py's _run_quasiarch_maintenance_consult()
     -- waveform_turn_summary() recorded every autonomous segment;
     get_doctrine_candidates() consulted weekly (gated by a persisted
     timestamp) against the observer's own real issue_counts, appended
     to an append-only ratification queue, never auto-applied.
  2. aurora.py's _emit_honest_abstain_and_seek() -- the honest-abstain
     chokepoint (the system's clearest, most concentrated failure
     signal) now also calls quasiarch.reason_about_event(), directly and
     synchronously alongside the existing warp_guard() confession.
"""
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.aurora_ci_segment import _run_quasiarch_maintenance_consult  # noqa: E402
import scripts.aurora_ci_segment as ci_segment  # noqa: E402


class _FakeQuasiArch:
    def __init__(self, issue_counts=None, waveform=None, doctrine_candidates=None,
                 raise_on_waveform=False, raise_on_doctrine=False):
        self.issue_counts = issue_counts or {}
        self._waveform = waveform if waveform is not None else {"disturbances": 3}
        self._doctrine_candidates = doctrine_candidates if doctrine_candidates is not None else []
        self.observations = []
        self.doctrine_calls = []
        self._raise_on_waveform = raise_on_waveform
        self._raise_on_doctrine = raise_on_doctrine

    def waveform_turn_summary(self):
        if self._raise_on_waveform:
            raise RuntimeError("waveform unavailable")
        return dict(self._waveform)

    def record_observation(self, target, data, source="OBSERVER", timestamp=None):
        self.observations.append({"target": target, "data": data, "source": source})

    def get_doctrine_candidates(self, issue_category, charge_cost=True, **kw):
        if self._raise_on_doctrine:
            raise RuntimeError("doctrine pipeline unavailable")
        self.doctrine_calls.append({"issue_category": issue_category, "charge_cost": charge_cost})
        return list(self._doctrine_candidates)


def _patch_state_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(ci_segment, "SD", str(tmp_path))


def test_no_quasiarch_observer_is_a_noop(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": None})
    assert summary == {"waveform_recorded": False, "doctrine_consult_ran": False, "doctrine_candidates": 0}


def test_waveform_summary_recorded_every_run(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    qa = _FakeQuasiArch(waveform={"disturbances": 5, "dominant_axes": ["N"]})
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})

    assert summary["waveform_recorded"] is True
    assert len(qa.observations) == 1
    assert qa.observations[0]["target"] == "waveform_turn_summary"
    assert qa.observations[0]["data"] == {"disturbances": 5, "dominant_axes": ["N"]}
    assert qa.observations[0]["source"] == "ci_segment_maintenance"


def test_waveform_failure_is_swallowed(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    qa = _FakeQuasiArch(raise_on_waveform=True)
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})
    assert summary["waveform_recorded"] is False


def test_doctrine_consult_skipped_when_no_real_issues_recorded(tmp_path, monkeypatch):
    """No fabricated placeholder category -- if nothing real has ever been
    recorded via record_intervention_event, there's nothing honest to
    consult doctrine about yet."""
    _patch_state_dir(monkeypatch, tmp_path)
    qa = _FakeQuasiArch(issue_counts={})
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})

    assert summary["doctrine_consult_ran"] is False
    assert qa.doctrine_calls == []
    # marker file still written -- the weekly gate must not re-check on
    # every single run just because there was nothing to consult about.
    assert os.path.exists(os.path.join(str(tmp_path), "quasiarch_doctrine_consult_last_run.json"))


def test_doctrine_consult_runs_on_first_call_with_real_issues(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    qa = _FakeQuasiArch(
        issue_counts={"topic_starvation": 3, "carryover_leak": 9},
        doctrine_candidates=[{"quasi_id": "q1"}, {"quasi_id": "q2"}],
    )
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})

    assert summary["doctrine_consult_ran"] is True
    assert summary["doctrine_candidates"] == 2
    # most frequent real issue category, not an arbitrary/first one
    assert qa.doctrine_calls == [{"issue_category": "carryover_leak", "charge_cost": False}]

    queue_path = os.path.join(str(tmp_path), "quasiarch_doctrine_ratification_queue.jsonl")
    assert os.path.exists(queue_path)
    with open(queue_path) as f:
        entry = json.loads(f.readline())
    assert entry["issue_category"] == "carryover_leak"
    assert entry["candidates"] == [{"quasi_id": "q1"}, {"quasi_id": "q2"}]


def test_doctrine_consult_does_not_repeat_within_the_week(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    marker_path = os.path.join(str(tmp_path), "quasiarch_doctrine_consult_last_run.json")
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(marker_path, "w") as f:
        json.dump({"ts": time.time() - 3600}, f)  # 1 hour ago, well under a week

    qa = _FakeQuasiArch(issue_counts={"topic_starvation": 3})
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})

    assert summary["doctrine_consult_ran"] is False
    assert qa.doctrine_calls == []


def test_doctrine_consult_runs_again_after_a_week(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    marker_path = os.path.join(str(tmp_path), "quasiarch_doctrine_consult_last_run.json")
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(marker_path, "w") as f:
        json.dump({"ts": time.time() - (8 * 24 * 3600)}, f)  # 8 days ago

    qa = _FakeQuasiArch(issue_counts={"topic_starvation": 3})
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})

    assert summary["doctrine_consult_ran"] is True


def test_doctrine_consult_failure_is_swallowed(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    qa = _FakeQuasiArch(issue_counts={"topic_starvation": 3}, raise_on_doctrine=True)
    # Must not raise.
    summary = _run_quasiarch_maintenance_consult({"quasiarch_observer": qa})
    assert summary["doctrine_consult_ran"] is False


def test_honest_abstain_consults_reason_about_event():
    """aurora.py's _emit_honest_abstain_and_seek() now also calls
    quasiarch.reason_about_event() directly, alongside its existing
    warp_guard() confession -- read-only, no forced behavior."""
    import aurora as A

    calls = []

    class _FakeState:
        parsed = {}
        response_content = ""
        response_tone = ""
        response_confidence = 0.0
        response_src = ""

    class _FakeQuasiArchForAbstain:
        def reason_about_event(self, **kwargs):
            calls.append(kwargs)
            return {"analyses": []}

    systems = {"quasiarch_observer": _FakeQuasiArchForAbstain(), "constraint_emitter": None}
    A._emit_honest_abstain_and_seek("what is the meaning of xyzzyplugh", systems, _FakeState(), trigger="test")

    assert len(calls) == 1
    call = calls[0]
    assert call["issue_category"] == "honest_abstain"
    assert call["phase"] == "abstain_test"
    assert call["charge_cost"] is False


def test_honest_abstain_degrades_gracefully_without_quasiarch_observer():
    import aurora as A

    class _FakeState:
        parsed = {}
        response_content = ""
        response_tone = ""
        response_confidence = 0.0
        response_src = ""

    systems = {"quasiarch_observer": None, "constraint_emitter": None}
    # Must not raise.
    A._emit_honest_abstain_and_seek("anything", systems, _FakeState(), trigger="test")


def test_honest_abstain_swallows_reason_about_event_exceptions():
    import aurora as A

    class _FakeState:
        parsed = {}
        response_content = ""
        response_tone = ""
        response_confidence = 0.0
        response_src = ""

    class _AlwaysRaisesQuasiArch:
        def reason_about_event(self, **kwargs):
            raise RuntimeError("doctrine pipeline down")

    systems = {"quasiarch_observer": _AlwaysRaisesQuasiArch(), "constraint_emitter": None}
    # Must not raise.
    A._emit_honest_abstain_and_seek("anything", systems, _FakeState(), trigger="test")
