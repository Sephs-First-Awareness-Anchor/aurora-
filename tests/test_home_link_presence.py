#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_home_link_presence.py -- being away from home, as quantities she can
feel (surface restructure 3b, item 4).

These pin:
  * home's last word weighs in proportion to its freshness, falling smoothly
    with age and never cut off;
  * only numeric influence is weighed; its words are left as home wrote them;
  * a projection with no age is left as it is;
  * a paired surface feels how long since home answered and how much lived
    experience waits to reach home; an unpaired device feels nothing of it.
"""
from __future__ import annotations

import json

import pytest

from aurora_internal.dual_strata import home_link_presence as hlp
from aurora_internal.dual_strata import strata_link as sl


def _projection(age_s, now=10_000.0):
    return {"generated_at": now - age_s, "readiness_bias": 0.8, "surface_guidance": "steady",
            "prediction_bias": {"mismatch_hint": 0.6, "continuity_hint": 0.4, "snapshot_trigger": "x"},
            "intuition_signals": [{"label": "clarify", "weight": 0.5, "summary": "stay careful"}]}


def test_home_word_fades_smoothly_with_age_and_never_stops():
    now = 10_000.0
    weights = [hlp.weigh_projection(_projection(age, now), now)["readiness_bias"]
               for age in (0, 60, 600, 3600, 86_400)]
    assert weights[0] == pytest.approx(0.8)
    assert all(a > b for a, b in zip(weights, weights[1:]))      # strictly falling
    assert weights[2] == pytest.approx(0.4)                      # half at the half-weight age
    assert weights[-1] > 0.0                                     # no cutoff


def test_only_numbers_are_weighed():
    now = 10_000.0
    old = hlp.weigh_projection(_projection(3600, now), now)
    assert old["surface_guidance"] == "steady"
    assert old["prediction_bias"]["snapshot_trigger"] == "x"
    assert old["intuition_signals"][0]["summary"] == "stay careful"
    assert old["intuition_signals"][0]["weight"] < 0.5
    assert old["age_s"] == 3600.0 and 0.0 < old["freshness"] < 1.0


def test_a_projection_without_an_age_is_left_alone():
    plain = {"readiness_bias": 0.8}
    assert hlp.weigh_projection(plain) == plain


def test_a_paired_surface_feels_its_distance_from_home(tmp_path):
    assert hlp.home_link_quantities(tmp_path) == {}            # the whole mind: nothing to feel
    link = sl.link_dir(tmp_path)
    link.joinpath("endpoint.txt").write_text("http://home:8791")
    link.joinpath("client_state.json").write_text(json.dumps({"confirmed_at": 1_000.0}))
    outbox = sl.DurableOutbox(link / "up_outbox.json")
    outbox.append("continuity", "event", {"moment": 1})
    outbox.append("continuity", "event", {"moment": 2})
    outbox.append("sensory_snapshot", "state", {"frame": 1})
    near = hlp.home_link_quantities(tmp_path, now=1_010.0)
    far = hlp.home_link_quantities(tmp_path, now=1_000.0 + 7_200.0)
    assert near["lived_waiting_for_home"] == 2
    assert near["since_home_answered_s"] == 10.0
    assert 0.0 < near["distance_from_home"] < far["distance_from_home"] < 1.0
