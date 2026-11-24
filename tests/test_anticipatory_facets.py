#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_anticipatory_facets.py -- home's read of her own crystals, handed to her
surface (dual-strata directive, section 6).

These pin:
  * home's view is the same bounded facet read the surface makes, on home's
    crystals, with provenance (input_id, words, epoch, validity window) and
    an evidence class per entry (earned, corrected, hypothesis, simulated);
  * a view is built once per raw input and relayed once;
  * the surface keeps views in its own cache (never a home-owned store);
  * a turn reads her own facets first; home entries she does not hold are
    added read-only and marked as home's; one she holds is annotated, never
    overwritten;
  * an expired view, a view from another holder epoch, or one about other
    words is ignored;
  * a whole-mind device does not read home views at all;
  * the recommendation hub on a surface decides an item once per run, and
    leaves aging out to home.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aurora_internal import aurora_store_ownership as gate  # noqa: E402
from aurora_internal.dual_strata import anticipatory_facets as af  # noqa: E402


@pytest.fixture(autouse=True)
def _clean():
    gate.disable_surface_only()
    af._cache.clear()
    yield
    gate.disable_surface_only()
    af._cache.clear()


def _facet(role, entries):
    return SimpleNamespace(role=role, content={"entries": entries})


def _systems(state, crystals):
    """crystals: concept -> list of facets."""
    index = {c: f"c_{c}" for c in crystals}
    by_id = {f"c_{c}": SimpleNamespace(facets={i: f for i, f in enumerate(fs)}) for c, fs in crystals.items()}
    registry = SimpleNamespace(crystal_by_id=lambda cid: by_id.get(cid))
    return {"state_dir": str(state), "_concept_crystal_registry": registry,
            "dimensional": SimpleNamespace(concept_index=index)}


def _home(tmp_path):
    state = tmp_path / "home"
    state.mkdir()
    return state, _systems(state, {
        "kettle": [_facet("fk:relation", [
            {"key": "needs", "content": "power", "degree": 0.8, "contexts": 2,
             "occasions": [{"source": "conversation", "basis": "observed", "occurrence_class": "observed"}]},
            {"key": "boils", "content": "unplugged", "degree": 0.0, "contexts": 1,
             "occasions": [{"source": "conversation", "basis": "corrected", "occurrence_class": "observed"}]},
        ]), _facet("fk:uncertainty", [
            {"key": "sings", "content": "?", "degree": 0.2, "occasions": []},
        ])],
        "zephyrine": [_facet("fk:context", [
            {"key": "is", "content": "kettle", "degree": 0.5,
             "occasions": [{"source": "dream", "basis": "simulated", "occurrence_class": "dream"}]},
        ])],
    })


def test_home_view_carries_provenance_and_evidence_classes(tmp_path):
    state, systems = _home(tmp_path)
    view = af.build_home_view(systems, "Can an unplugged kettle boil?", input_id="in1", state_dir=state)
    assert view["input_id"] == "in1" and "kettle" in view["terms"]
    assert view["expires_at"] > view["at"] and view["basis"] == "home_crystal_read"
    classes = {e["key"]: e["evidence_class"] for e in view["entries"]}
    assert classes == {"needs": "earned", "boils": "corrected", "sings": "hypothesis"}
    dream = af.build_home_view(systems, "zephyrine", state_dir=state)
    assert dream["entries"][0]["evidence_class"] == "simulated"
    assert af.build_home_view(systems, "nothing known here", state_dir=state) is None


def test_staged_once_per_input_and_relayed_once(tmp_path):
    state, systems = _home(tmp_path)
    systems["_anticipatory_input"] = {"input_id": "in1", "text": "the kettle", "expires_at": time.time() + 30}
    assert af.stage_from_anticipatory_input(systems, state) is not None
    assert af.stage_from_anticipatory_input(systems, state) is None          # same input
    sent = []
    outbox = SimpleNamespace(append=lambda ch, kind, payload: sent.append((ch, payload)))
    memo = {}
    assert af.relay_down(state, outbox, memo) == 1
    assert af.relay_down(state, outbox, memo) == 0
    assert sent[0][0] == af.DOWN_CHANNEL


def test_downlink_channel_lands_in_her_own_cache(tmp_path):
    from aurora_internal.dual_strata.strata_link import apply_downlink_record
    state, systems = _home(tmp_path)
    view = af.build_home_view(systems, "kettle", state_dir=state)
    surface = tmp_path / "surface"
    surface.mkdir()
    assert apply_downlink_record(surface, {"channel": "facet_view", "payload": view}) == "applied"
    assert gate.classify(f"strata_link/{af.SURFACE_VIEWS_FILENAME}") == gate.SURFACE_PRESENT
    assert len(af.valid_views_for(surface, "the kettle again")) == 1


def test_turn_reads_hers_first_and_adds_home_entries_read_only(tmp_path):
    from aurora_internal.aurora_live_experience import crystal_context_for_turn
    state, home_systems = _home(tmp_path)
    surface = tmp_path / "surface"
    surface.mkdir()
    af.receive_down(surface, af.build_home_view(home_systems, "kettle", state_dir=state))
    # Her surface knows one of the kettle entries, with her own degree.
    systems = _systems(surface, {"kettle": [_facet("fk:relation", [
        {"key": "needs", "content": "power", "degree": 0.3, "occasions": [{"source": "conversation"}]}])]})
    systems["runtime_profile"] = "surface"
    facets = crystal_context_for_turn(systems, "is the kettle on?", max_entries=6)["facets"]
    mine = [f for f in facets if f.get("source") != "home_view"]
    home = [f for f in facets if f.get("source") == "home_view"]
    assert facets[0] is mine[0] and mine[0]["degree"] == 0.3                  # hers, unchanged
    assert mine[0]["home_view"]["degree"] == 0.8                              # annotated
    assert {f["key"] for f in home} == {"boils", "sings"}
    assert all(f["read_only"] and f["evidence_class"] for f in home)


def test_stale_foreign_or_unrelated_views_are_ignored(tmp_path):
    state, home_systems = _home(tmp_path)
    surface = tmp_path / "surface"
    surface.mkdir()
    view = af.build_home_view(home_systems, "kettle", state_dir=state)
    af.receive_down(surface, view)
    assert af.valid_views_for(surface, "the weather") == []                   # other words
    assert af.valid_views_for(surface, "kettle", now=view["expires_at"] + 1) == []
    other_epoch = dict(view, view_id="v2", epoch=view["epoch"] + 1)
    af._cache.clear()
    (surface / "strata_link" / af.SURFACE_VIEWS_FILENAME).write_text(
        json.dumps({"views": [other_epoch]}), encoding="utf-8")
    assert af.valid_views_for(surface, "kettle") == []


def test_whole_mind_device_reads_no_home_views(tmp_path):
    from aurora_internal.aurora_live_experience import crystal_context_for_turn
    state, home_systems = _home(tmp_path)
    af.receive_down(state, af.build_home_view(home_systems, "kettle", state_dir=state))
    systems = _systems(state, {})
    systems["runtime_profile"] = "full"
    assert crystal_context_for_turn(systems, "kettle")["facets"] == []


def test_surface_decides_a_recommendation_once_and_leaves_aging_to_home(tmp_path, monkeypatch):
    from aurora_internal import aurora_recommendation_hub as hub
    out = tmp_path / "state"
    out.mkdir()
    hub.enqueue_recommendation(str(out), source="s", run_type="lineage_scan", title="t", body="b",
                               priority=0.9)
    monkeypatch.setattr(hub, "_SURFACE_DECIDED", {})
    monkeypatch.setattr(hub, "_SURFACE_DISCUSSED", [])
    settled = []
    monkeypatch.setattr(hub, "settle_recommendations", lambda *a, **k: settled.append(1))
    gate.enable_surface_only(out)
    calls = []
    first = hub.process_pending_for_aurora(str(out), discuss_callback=lambda m, r: calls.append(m))
    second = hub.process_pending_for_aurora(str(out), discuss_callback=lambda m, r: calls.append(m))
    assert settled == []                       # aging out is home's bookkeeping
    assert len(first) == 1 and first[0]["action"] == "discuss_with_user"
    assert len(second) == 0                    # nothing decided twice in one run
    assert len(calls) == 1                     # never raised with Sunni again and again
