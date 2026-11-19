#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_inquiry_tiers.py -- one inquiry across her two strata (surface
restructure 4b, Sir's two-tier inquiry).

These pin:
  * a whole-mind device is unchanged: an exhausted frontier stages Build 714's
    field inquiry locally;
  * on a surface, the same exhausted frontier is carried home with what she
    lived, never staged as retained growth here, and carried again only when
    there is new lived evidence;
  * home feels the surface's lived evidence as observation;
  * home works raised questions in the order of its own felt pressure, and a
    question home does not feel is not forced;
  * what home stages for a raised question comes back to the surface over the
    real link; the surface reads its view, lives its consequence and sends
    that home; only home completes it, and its close reaches the surface;
  * on a surface-only device the resolution ledgers are not rewritten.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import aurora_representational_resolution as rr
from aurora_representational_address import RepresentationalRef
from aurora_internal import aurora_store_ownership as gate
from aurora_internal.dual_strata import inquiry_tiers as tiers
from aurora_internal.dual_strata import strata_link as sl

_P0 = {"X": 0.4, "T": 0.4, "N": 0.4, "B": 0.4, "A": 0.4}
_P1 = {"X": 0.3, "T": 0.4, "N": 0.4, "B": 0.4, "A": 0.4}


def _coarse(axis="X", dim="MAGNITUDE", law="A"):
    return RepresentationalRef.for_c1(axis, dim, law)


def _domain_candidate():
    return {"field": "sub_law_c", "candidate_value": "T",
            "source": "domain_hypothesis:sub_law_c=T",
            "counterpart_ability_id": "REFHYP:test", "evidence": {"origin": "lawful_domain"},
            "origin": "domain_hypothesis"}


def _bare_engine(pressure=0.7):
    engine = rr.RepresentationalResolutionEngine.__new__(rr.RepresentationalResolutionEngine)
    engine.genealogy = SimpleNamespace(abilities={}, tick_count=0, observed=[])
    engine.genealogy.observe = lambda *a, **k: engine.genealogy.observed.append((a, k))
    engine.root = None
    engine._genealogy_records = {}
    engine._active_resolutions = {}
    engine._resolution_events = []
    engine._cost_ledger = {}
    engine._active_stage_for_ref = {}
    engine._provisional_reads = {}
    engine._candidate_downstream_effects = {}
    engine._candidate_attempt_counts = {}
    engine._in_complete_field_inquiry = False
    engine._projection_state()
    engine.ensure_registered = lambda ref, notes="": "REFAB:" + ref.encode()
    engine.pressure = {}
    engine.inadequacy_pressure = lambda ref: engine.pressure.get(ref.encode(), pressure)
    engine.unresolved_field_candidates = lambda ref: [_domain_candidate()]
    return engine


class _FakeTier:
    def __init__(self):
        self.up, self.evidence, self.down = [], [], []

    def pass_up(self, payload):
        self.up.append(payload)
        return True

    def send_evidence(self, payload):
        self.evidence.append(payload)
        return True

    def inbox(self):
        out, self.down = self.down, []
        return out


@pytest.fixture(autouse=True)
def _whole_again():
    rr.set_home_tier(None)
    gate.disable_surface_only()
    yield
    rr.set_home_tier(None)
    gate.disable_surface_only()


def test_a_whole_mind_still_stages_its_own_field_inquiry():
    engine, ref = _bare_engine(), _coarse()
    engine.stage_field_inquiry = lambda ref, candidate, consumer: [{"stage_id": "s1"}]
    staged = engine.investigate_if_pressured(ref, consumer="reader")
    assert staged["mode"] == "field_inquiry"


def test_on_a_surface_the_exhausted_frontier_goes_home_with_what_she_lived():
    tier = _FakeTier()
    rr.set_home_tier(tier)
    engine, ref = _bare_engine(), _coarse()
    engine.stage_field_inquiry = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("retained growth is never staged on a surface"))
    engine.record_pressure_observation(ref, pressure_before=_P0, pressure_after=_P1,
                                       source="turn", context_tag="kitchen")
    passed = engine.investigate_if_pressured(ref, consumer="reader")
    assert passed["mode"] == "passed_home"
    assert ref.encode() not in engine._active_stage_for_ref
    (up,) = tier.up
    assert up["ref"] == ref.encode() and up["pressure"] == pytest.approx(0.7)
    assert [e["context_tag"] for e in up["evidence"]] == ["kitchen"]

    # Nothing new lived: nothing carried again, however often she reads it.
    engine.provisional_resolution(ref, consumer="reader")
    engine.investigate_if_pressured(ref, consumer="reader")
    assert len(tier.up) == 1

    # A new lived consequence goes up, and only that one.
    engine.record_pressure_observation(ref, pressure_before=_P1, pressure_after=_P0,
                                       source="turn", context_tag="garden")
    engine.investigate_if_pressured(ref, consumer="reader")
    assert len(tier.up) == 2
    assert [e["context_tag"] for e in tier.up[1]["evidence"]] == ["garden"]


def test_a_handed_down_experiment_is_lived_here_and_completed_only_at_home():
    tier = _FakeTier()
    rr.set_home_tier(tier)
    engine, ref = _bare_engine(), _coarse()
    key = ref.encode()
    from dataclasses import replace
    view = replace(ref, sub_law_c="T").encode()
    tier.down.append({"kind": "stage", "ref": key, "inquiry_id": "inq-1", "view": view,
                      "stage_mode": "field_inquiry", "candidate": _domain_candidate()})
    assert engine.provisional_resolution(ref, consumer="reader").encode() == view
    engine.complete_field_inquiry = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("only home completes"))
    effect = engine.record_candidate_downstream_effect(
        ref, consumer="reader", downstream_difference={"ranking_changed": True},
        action_or_prediction_affected="relevance")
    assert effect["inquiry_id"] == "inq-1"
    engine.record_participation(ref, pressure_before=_P0, pressure_after=_P1, source="turn",
                                consumer="reader",
                                candidate_evaluation={"actual_consequence": 1.0})
    (sent,) = tier.evidence
    assert sent["inquiry_id"] == "inq-1" and sent["provisional_reads"] == 1
    assert sent["downstream_effect"]["downstream_difference_produced"] == {"ranking_changed": True}
    assert sent["candidate_evaluation"] == {"actual_consequence": 1.0}
    assert engine._active_stage_for_ref[key]["mode"] == "home_inquiry"    # still home's

    tier.down.append({"kind": "closed", "ref": key, "inquiry_id": "inq-1", "outcome": "retained"})
    engine.provisional_resolution(ref, consumer="reader")
    assert engine._active_stage_for_ref.get(key, {}).get("mode") != "home_inquiry"


def test_her_own_lens_finishes_before_homes_experiment_is_taken_up():
    tier = _FakeTier()
    rr.set_home_tier(tier)
    engine, ref = _bare_engine(), _coarse()
    key = ref.encode()
    engine._active_stage_for_ref[key] = {"mode": "perspective_projection", "stage": None,
                                         "candidate": {"projected_ref": key}, "consumer": "x",
                                         "context_scope": None}
    from dataclasses import replace
    tier.down.append({"kind": "stage", "ref": key, "inquiry_id": "inq-2",
                      "view": replace(ref, sub_law_c="T").encode(), "candidate": _domain_candidate()})
    engine._take_home_inquiries()
    assert engine._active_stage_for_ref[key]["mode"] == "perspective_projection"
    engine._active_stage_for_ref.pop(key)
    engine._take_home_inquiries()
    assert engine._active_stage_for_ref[key]["inquiry_id"] == "inq-2"


def _home_engine():
    engine = _bare_engine()
    engine.stage_field_inquiry = lambda ref, candidate, consumer: [{"stage_id": "home-stage"}]
    engine.completed = []

    def complete(ref, candidate, stage, **kwargs):
        engine.completed.append({"reads": engine._provisional_reads.get(ref.encode(), 0),
                                 "evaluation": kwargs.get("candidate_evaluation"),
                                 "effect": dict(engine._candidate_downstream_effects.get(ref.encode()) or {})})
        engine.pressure[ref.encode()] = 0.0
        engine._resolution_events.append({"ref_before_encoded": ref.encode(), "outcome": "retained"})
        return {"representational_resolution_outcome": "retained"}
    engine.complete_field_inquiry = complete
    return engine


@pytest.fixture()
def strata(tmp_path, monkeypatch):
    home, phone = tmp_path / "home", tmp_path / "phone"
    home.mkdir()
    phone.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    sl.link_dir(home).joinpath("downlink_enabled").write_text("1")

    def transport(body, headers):
        status, out, extra = server.handle_http(body, headers)
        if status != 200:
            raise OSError(f"http {status}")
        return out, extra
    client = sl.StrataLinkClient(phone, endpoint="http://home", secret=server.secret, transport=transport)
    monkeypatch.setattr(sl, "_CLIENT", client)
    client.sync_once()
    assert client.role == "active"
    home_engine = _home_engine()
    desk = tiers.HomeInquiryDesk(home, {"representational_resolution_engine": home_engine})
    return SimpleNamespace(home=home, phone=phone, client=client, desk=desk, home_engine=home_engine,
                           offset=0)


def _home_pass(strata):
    requests, strata.offset = sl.read_home_requests(strata.home, strata.offset)
    for req in requests:
        strata.desk.take(req)
    strata.desk.tick()


def test_one_inquiry_crosses_the_real_link_and_home_completes_it(strata):
    tier = tiers.SurfaceInquiryTier(strata.phone)
    rr.set_home_tier(tier)
    surface, ref = _bare_engine(), _coarse()
    key = ref.encode()
    surface.record_pressure_observation(ref, pressure_before=_P0, pressure_after=_P1,
                                        source="turn", context_tag="kitchen")
    assert surface.investigate_if_pressured(ref, consumer="reader")["mode"] == "passed_home"

    strata.client.sync_once()                     # up: the question and what she lived
    _home_pass(strata)
    (felt,) = strata.home_engine.genealogy.observed                 # felt at home
    assert felt[1]["notes"]["representational_resolution"]["source"] == "surface:turn"
    assert strata.home_engine._active_stage_for_ref[key]["consumer"] == "surface:reader"
    assert strata.desk.status()["holding"] == [key]

    strata.client.sync_once()                     # down: home's experiment
    view = surface.provisional_resolution(ref, consumer="reader")
    assert view.sub_law_c == "T"
    surface.record_candidate_downstream_effect(
        ref, consumer="reader", downstream_difference={"ranking_changed": True},
        action_or_prediction_affected="relevance")
    surface.record_participation(
        ref, pressure_before=_P0, pressure_after=_P1, source="turn", consumer="reader",
        candidate_evaluation={"actual_consequence": 1.0, "baseline_error": 0.5,
                              "candidate_conditioned_error": 0.2})

    strata.client.sync_once()                     # up: the consequence she lived
    _home_pass(strata)
    (done,) = strata.home_engine.completed
    assert done["reads"] == 1
    assert done["evaluation"]["candidate_conditioned_error"] == 0.2
    assert done["effect"]["downstream_difference_produced"] == {"ranking_changed": True}

    strata.client.sync_once()                     # down: the close
    surface.provisional_resolution(ref, consumer="reader")
    assert key not in surface._active_stage_for_ref
    assert surface._passed_home[key]["home_outcome"] == "retained"
    assert strata.client.outbox.stats()["pending"] == 0


def test_a_question_home_does_not_feel_is_not_forced(strata):
    ref = _coarse()
    strata.home_engine.pressure[ref.encode()] = 0.0
    strata.home_engine.stage_field_inquiry = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("not forced"))
    strata.desk.take({"kind": "inquiry", "from": "phone",
                      "payload": {"ref": ref.encode(), "pressure": 0.9, "evidence": []}})
    strata.desk.tick()
    assert strata.desk.questions == {}
    down, _ = tiers._read_lines_since(sl.link_dir(strata.home) / tiers.DOWN_FILENAME, 0)
    assert down[-1]["kind"] == "closed" and down[-1]["outcome"] == "not_felt_at_home"


def test_home_works_questions_in_the_order_of_its_own_pressure(strata, monkeypatch):
    monkeypatch.setattr(tiers, "INVESTIGATIONS_PER_PASS", 1)
    low, high = _coarse("X", "MAGNITUDE", "A"), _coarse("T", "POLARITY", "B")
    strata.home_engine.pressure.update({low.encode(): 0.2, high.encode(): 0.8})
    for ref in (low, high):
        strata.desk.take({"kind": "inquiry", "from": "phone",
                          "payload": {"ref": ref.encode(), "pressure": 0.5, "evidence": []}})
    strata.desk.tick()
    assert list(strata.home_engine._active_stage_for_ref) == [high.encode()]
    strata.desk.tick()
    assert set(strata.home_engine._active_stage_for_ref) == {high.encode(), low.encode()}


def test_resolution_ledgers_are_not_rewritten_on_a_surface(tmp_path):
    engine = _bare_engine()
    engine.root = tmp_path / "representational_resolution"
    engine.root.mkdir()
    gate.enable_surface_only(tmp_path)
    engine._save()
    assert list(engine.root.iterdir()) == []
    gate.disable_surface_only()
    engine._save()
    assert (engine.root / "resolution_genealogy.json").exists()


def test_the_surfaces_own_genealogy_is_hers_to_write():
    assert gate.classify("genealogy_surface/genealogy_state.json") == gate.SURFACE_PRESENT
    assert gate.classify("representational_resolution/active_resolutions.json") == gate.HOME_DEVELOPMENTAL
