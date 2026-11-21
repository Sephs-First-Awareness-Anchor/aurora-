#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_surface_store_gate.py -- on a phone that is the surface of a paired home,
her deep developmental stores are home's to write (surface restructure 3f).

These pin:
  * every store has an owner, and an unknown store defaults to home;
  * transient suffixes (.tmp, .settle) are classed by the store they belong to;
  * the gate is off on a whole-mind device, so nothing changes there;
  * on a surface-only device a home-owned write is declined, counted per
    store and shown on the hub, and is never a fault;
  * the surface's own present, its journals and caches are still written;
  * the real writers honour the gate: atomic_write_json, the interaction
    memory journal, the pressure-experience log (the felt pressure stays in
    the buffer) and the understanding sediment overlay;
  * paths outside her state directory are never touched by the gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aurora_internal import aurora_store_ownership as gate  # noqa: E402
from aurora_internal.aurora_store_ownership import (  # noqa: E402
    CACHE,
    HOME_DEVELOPMENTAL,
    JOURNAL,
    SURFACE_PRESENT,
    classify,
)


@pytest.fixture(autouse=True)
def _gate_off_after():
    gate.disable_surface_only()
    yield
    gate.disable_surface_only()


def test_every_store_has_an_owner_and_unknown_is_home():
    assert classify("strata_link/outbox.jsonl") == SURFACE_PRESENT
    assert classify("surface_working_state.json") == SURFACE_PRESENT
    assert classify("last_turn_trace.json") == SURFACE_PRESENT
    assert classify("runtime_faults.jsonl") == JOURNAL
    assert classify("aurora.log") == JOURNAL
    assert classify("interaction_memory/nodes.lock") == CACHE
    assert classify("cache/anything.bin") == CACHE
    assert classify("expression_lexicon.json") == HOME_DEVELOPMENTAL
    assert classify("grammar_engine_state.json") == HOME_DEVELOPMENTAL
    assert classify("some_new_organ_nobody_listed.json") == HOME_DEVELOPMENTAL


def test_transient_suffix_is_classed_by_its_store():
    assert classify("expression_lexicon.json.tmp") == HOME_DEVELOPMENTAL
    assert classify("surface_working_state.json.tmp") == SURFACE_PRESENT
    assert classify("understanding_sediment.json.settle") == HOME_DEVELOPMENTAL


def test_gate_is_off_on_a_whole_mind_device(tmp_path):
    assert gate.surface_only_root() is None
    assert gate.store_write_allowed(tmp_path / "expression_lexicon.json") is True
    assert gate.gate_status()["surface_only"] is False


def test_surface_only_declines_home_stores_and_counts_them(tmp_path):
    gate.enable_surface_only(tmp_path)
    assert gate.store_write_allowed(tmp_path / "expression_lexicon.json") is False
    assert gate.store_write_allowed(tmp_path / "expression_lexicon.json.tmp") is False
    assert gate.store_write_allowed(str(tmp_path / "interaction_memory" / "nodes.json")) is False

    assert gate.store_write_allowed(tmp_path / "surface_working_state.json") is True
    assert gate.store_write_allowed(tmp_path / "runtime_faults.jsonl") is True
    assert gate.store_write_allowed(tmp_path / "strata_link" / "client_state.json") is True

    status = gate.gate_status()
    assert status["surface_only"] is True
    assert status["by_store"]["expression_lexicon.json"]["declined"] == 2
    assert status["stores_declined"] == 2
    assert status["writes_declined"] == 3


def test_paths_outside_the_state_dir_are_not_gated(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    gate.enable_surface_only(state)
    assert gate.store_write_allowed(tmp_path / "elsewhere" / "expression_lexicon.json") is True


def test_hub_view_is_written_beside_the_link(tmp_path):
    gate.enable_surface_only(tmp_path)
    gate.store_write_allowed(tmp_path / "grammar_engine_state.json")
    gate.flush_status()
    shown = json.loads((tmp_path / "strata_link" / "store_gate.json").read_text())
    assert shown["surface_only"] is True
    assert "grammar_engine_state.json" in shown["by_store"]


def test_a_declined_write_is_not_a_fault(tmp_path, monkeypatch):
    from aurora_internal import aurora_runtime_faults as faults

    recorded = []
    monkeypatch.setattr(faults, "record_runtime_fault",
                        lambda *a, **k: recorded.append((a, k)), raising=False)
    gate.enable_surface_only(tmp_path)
    assert gate.store_write_allowed(tmp_path / "expression_lexicon.json") is False
    assert recorded == []


def test_atomic_write_json_honours_the_gate(tmp_path):
    from aurora_persistence_utils import atomic_write_json

    home_store = tmp_path / "lexical_grounding_state.json"
    present = tmp_path / "surface_working_state.json"
    gate.enable_surface_only(tmp_path)
    assert atomic_write_json(home_store, {"x": 1}) is True
    assert atomic_write_json(present, {"y": 2}) is True
    assert not home_store.exists()
    assert json.loads(present.read_text()) == {"y": 2}

    gate.disable_surface_only()
    atomic_write_json(home_store, {"x": 1})
    assert json.loads(home_store.read_text()) == {"x": 1}


def test_interaction_memory_journal_is_home_owned(tmp_path):
    from aurora_interaction_memory import InteractionMemory

    memory = InteractionMemory(storage_dir=str(tmp_path / "interaction_memory"))
    journal = Path(memory.journal_path)
    before = journal.read_text() if journal.exists() else None
    gate.enable_surface_only(tmp_path)
    memory._append_journal({"event": "lived on the surface"})
    after = journal.read_text() if journal.exists() else None
    assert after == before


def test_pressure_log_is_home_owned_but_still_felt(tmp_path):
    from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger

    ledger = PressureExperienceLedger(state_dir=str(tmp_path))
    gate.enable_surface_only(tmp_path)
    exp = ledger.record(anchor="rain", meaning="water falling", pursuing="understand",
                        causal_action="ask", consequence={"answered": True},
                        outcome={"settled": True}, source="test")
    assert exp in list(ledger._buffer)
    assert not (tmp_path / "pressure_experiences.jsonl").exists()


def test_understanding_sediment_is_home_owned(tmp_path):
    from aurora_understanding_sediment import UnderstandingSedimentOverlay

    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    overlay._dirty = True
    gate.enable_surface_only(tmp_path)
    assert overlay.save() is False
    assert not Path(overlay._path).exists()
