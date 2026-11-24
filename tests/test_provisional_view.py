#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_provisional_view.py -- offline learning without split-brain (dual-strata
directive, section 8).

On a phone that is the surface of a paired home, home owns her deep stores.
What she lives while home cannot take it is kept as a bounded PROVISIONAL view
beside home's copy, and survives a restart.  These pin:
  * a whole-mind device writes straight to the store (nothing changes there);
  * on a surface-only device a home-owned write lands under provisional/,
    and home's canonical copy is untouched;
  * the next start lays a snapshot view over the copy it grew from;
  * an append view adds only what is new, once, across several restarts;
  * when home's growth has replaced the copy, the view retires: home's
    integration of the same occurrences is the authority, never both;
  * home's growth does not re-install bytes the view grew from;
  * the view is never sent as state (it is hers, and moves with her);
  * the budget is honoured: past it a write is declined and counted;
  * the writers that used to slip past the gate now honour it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aurora_internal import aurora_store_ownership as gate  # noqa: E402
from aurora_internal.aurora_store_ownership import (  # noqa: E402
    APPEND,
    PROVISIONAL,
    SNAPSHOT,
    classify,
    provisional_canon_shas,
    restore_provisional,
    store_write_path,
)


@pytest.fixture(autouse=True)
def _gate_off_after():
    gate.disable_surface_only()
    yield
    gate.disable_surface_only()


def _state(tmp_path: Path) -> Path:
    state = tmp_path / "aurora_state"
    state.mkdir()
    return state


def test_provisional_is_hers_and_moves_with_her():
    assert classify("provisional/lexicon.json") == PROVISIONAL
    assert classify("provisional/_provisional.json") == PROVISIONAL
    assert "provisional/*" in gate.MOVES_WITH_HER


def test_whole_mind_device_writes_the_store_itself(tmp_path):
    state = _state(tmp_path)
    target = state / "lexicon.json"
    assert store_write_path(target) == target
    assert not (state / "provisional").exists()


def test_surface_write_lands_in_the_view_and_home_copy_is_untouched(tmp_path):
    state = _state(tmp_path)
    canon = state / "lexicon.json"
    canon.write_text('{"words": 1}', encoding="utf-8")
    gate.enable_surface_only(state)
    target = store_write_path(canon, SNAPSHOT)
    assert target == (state / "provisional" / "lexicon.json").resolve()
    target.write_text('{"words": 2}', encoding="utf-8")
    assert canon.read_text(encoding="utf-8") == '{"words": 1}'
    status = gate.gate_status()
    assert status["writes_provisional"] == 1 and status["writes_declined"] == 0
    # Her own present is not home's: never redirected.
    assert store_write_path(state / "surface_working_state.json") == state / "surface_working_state.json"


def test_restart_lays_a_snapshot_view_over_the_copy_it_grew_from(tmp_path):
    state = _state(tmp_path)
    canon = state / "lexicon.json"
    canon.write_text('{"words": 1}', encoding="utf-8")
    gate.enable_surface_only(state)
    store_write_path(canon, SNAPSHOT).write_text('{"words": 2}', encoding="utf-8")
    gate.disable_surface_only()                       # the process ends

    report = restore_provisional(state)                # the next start, before the gate
    assert report["restored"] == ["lexicon.json"] and not report["retired"]
    assert canon.read_text(encoding="utf-8") == '{"words": 2}'

    # She keeps learning on top of what she lived, and it survives again.
    gate.enable_surface_only(state)
    store_write_path(canon, SNAPSHOT).write_text('{"words": 3}', encoding="utf-8")
    gate.disable_surface_only()
    assert restore_provisional(state)["restored"] == ["lexicon.json"]
    assert canon.read_text(encoding="utf-8") == '{"words": 3}'


def test_append_view_adds_only_what_is_new_across_restarts(tmp_path):
    state = _state(tmp_path)
    canon = state / "pressure_experiences.jsonl"
    canon.write_text("home-1\n", encoding="utf-8")
    gate.enable_surface_only(state)
    with open(store_write_path(canon, APPEND), "a", encoding="utf-8") as fh:
        fh.write("lived-1\n")
    gate.disable_surface_only()
    assert restore_provisional(state)["appended"] == ["pressure_experiences.jsonl"]
    assert canon.read_text(encoding="utf-8") == "home-1\nlived-1\n"

    # A start with nothing new appends nothing (each occurrence once).
    assert restore_provisional(state)["appended"] == []
    assert canon.read_text(encoding="utf-8") == "home-1\nlived-1\n"

    gate.enable_surface_only(state)
    with open(store_write_path(canon, APPEND), "a", encoding="utf-8") as fh:
        fh.write("lived-2\n")
    gate.disable_surface_only()
    restore_provisional(state)
    assert canon.read_text(encoding="utf-8") == "home-1\nlived-1\nlived-2\n"


def test_view_retires_when_home_has_replaced_the_copy(tmp_path):
    state = _state(tmp_path)
    canon = state / "lexicon.json"
    canon.write_text('{"words": 1}', encoding="utf-8")
    gate.enable_surface_only(state)
    store_write_path(canon, SNAPSHOT).write_text('{"words": 2}', encoding="utf-8")
    gate.disable_surface_only()
    canon.write_text('{"words": 9, "integrated_at_home": true}', encoding="utf-8")   # home's growth
    report = restore_provisional(state)
    assert report["retired"] == ["lexicon.json"] and not report["restored"]
    assert json.loads(canon.read_text(encoding="utf-8"))["integrated_at_home"] is True
    assert not (state / "provisional" / "lexicon.json").exists()


def test_growth_does_not_reinstall_the_bytes_the_view_grew_from(tmp_path):
    from aurora_internal.dual_strata.home_growth import _wanted
    state = _state(tmp_path)
    canon = state / "lexicon.json"
    canon.write_text('{"words": 1}', encoding="utf-8")
    import hashlib
    home_sha = hashlib.sha256(canon.read_bytes()).hexdigest()
    gate.enable_surface_only(state)
    store_write_path(canon, SNAPSHOT).write_text('{"words": 2}', encoding="utf-8")
    gate.disable_surface_only()
    restore_provisional(state)
    assert provisional_canon_shas(state)["lexicon.json"] == home_sha
    same = [{"path": "lexicon.json", "size": 12, "sha256": home_sha}]
    assert _wanted(state, same) == []                 # home has nothing new there
    newer = [{"path": "lexicon.json", "size": 40, "sha256": "f" * 64}]
    assert [r["path"] for r in _wanted(state, newer)] == ["lexicon.json"]


def test_view_is_never_sent_as_state(tmp_path):
    from aurora_internal.dual_strata import strata_state_transfer as st
    state = _state(tmp_path)
    (state / "provisional").mkdir()
    (state / "provisional" / "lexicon.json").write_text("{}", encoding="utf-8")
    (state / "lexicon.json").write_text("{}", encoding="utf-8")
    listed = [rel for rel in st.list_transferable(state) if not rel.startswith("provisional/")]
    assert "lexicon.json" in listed and all(not r.startswith("provisional/") for r in listed)
    # A file that vanished mid-copy is not an error when strict is off.
    rows = st.snapshot_state(state, tmp_path / "snap", rel_paths=listed + ["gone.json"], strict=False)
    assert isinstance(rows, list) and all(r.get("path") != "gone.json" for r in rows if isinstance(r, dict))


def test_budget_spent_declines_and_counts(tmp_path, monkeypatch):
    state = _state(tmp_path)
    gate.enable_surface_only(state)
    monkeypatch.setattr(gate, "_within_budget", lambda prov: False)
    assert store_write_path(state / "lexicon.json", SNAPSHOT) is None
    status = gate.gate_status()
    assert status["writes_declined"] == 1 and status["writes_provisional"] == 0


def test_bypassing_writers_now_honour_the_gate(tmp_path):
    import aurora_developmental_log as devlog
    from aurora_internal.aurora_reflective_readdressing import _append_jsonl, _atomic_json
    state = _state(tmp_path)
    gate.enable_surface_only(state)
    devlog._append_capped(str(state / "developmental_timeline.jsonl"), {"event": "x"})
    _append_jsonl(state / "reflective_readdressing_history.jsonl", {"a": 1})
    _atomic_json(state / "reflective_readdressing_last.json", {"a": 1})
    for name in ("developmental_timeline.jsonl", "reflective_readdressing_history.jsonl",
                 "reflective_readdressing_last.json"):
        assert not (state / name).exists(), name
        assert (state / "provisional" / name).exists(), name


def test_universal_lineage_is_declined_not_kept(tmp_path):
    from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
    state = _state(tmp_path)
    gate.enable_surface_only(state)
    lin = UniversalFunctionLineage.__new__(UniversalFunctionLineage)
    lin.manifest_path = (state / "universal_function_lineage.json").resolve()
    lin.constraint_index_path = lin.manifest_path.with_name("universal_function_constraints.json")
    lin._manifest, lin._functions = {}, {}
    lin._write_manifest()
    lin._write_constraint_index()
    assert not lin.manifest_path.exists() and not lin.constraint_index_path.exists()
    assert not (state / "provisional").exists()
    assert gate.gate_status()["writes_declined"] == 2
