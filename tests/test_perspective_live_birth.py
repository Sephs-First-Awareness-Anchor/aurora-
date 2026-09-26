#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_perspective_live_birth.py -- the user's own words crystallize, with
perspective, on the real dialogue intake.

Boots Aurora once (module scope) and drives real turns through
aurora._chain_up1_information, the main dialogue intake.  Before this work
every user turn entered as REFERENCE, below the crystal gate, and the intake
never invoked Layer 3 -- so no user words could be born as a crystal at all.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

import aurora


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    state_dir = str(tmp_path_factory.mktemp("perspective_live"))
    systems = aurora.boot_aurora(state_dir)
    return systems, state_dir


def _turn(systems, text):
    state = SimpleNamespace(parsed={"query_type": "statement"}, pipeline_state={})
    aurora._chain_up1_information(text, systems, state)
    return state.pipeline_state


def test_engine_is_attached_at_boot_to_the_real_state_dir(live):
    systems, state_dir = live
    engine = systems.get("perspective")
    assert engine is not None
    assert engine.state_dir == os.path.join(state_dir, "perspective")
    assert systems["collective"].perspective is engine


def test_a_user_turn_is_born_as_crystals_carrying_both_lineages(live):
    systems, _ = live
    dps = systems["dimensional"].dps
    before = set(dps.crystals)
    birth = _turn(systems, "the lighthouse keeper counts the passing ships")["perspective_birth"]
    assert birth["born"] is True
    assert birth["retained"] == {"P0": True, "P1": True}
    new = [dps.crystals[c] for c in set(dps.crystals) - before]
    assert new
    for crystal in new:
        assert crystal.perspective_support() == ["P0", "P1"]


def test_recurrence_accumulates_evidence_in_each_lineage(live):
    systems, _ = live
    _turn(systems, "the lighthouse beam sweeps the water")
    _turn(systems, "the lighthouse beam sweeps the water")
    crystal = systems["dimensional"].dps.get_crystal("lighthouse")
    assert crystal is not None
    counts = {k: v["evidence_count"] for k, v in crystal.perspective_profiles.items()}
    assert counts["P0"] >= 2 and counts["P1"] >= 2


def test_lineage_development_persists_to_disk(live):
    systems, state_dir = live
    _turn(systems, "harbour lights at dusk")
    assert os.path.exists(os.path.join(state_dir, "perspective", "perspective_lineages.json"))


def test_turn_existence_evidence_is_persistent_not_more(live):
    """Only the two facts the intake genuinely knows are declared: the turn
    is temporal and conserved.  Identity and agency are not claimed."""
    import inspect
    source = inspect.getsource(aurora._chain_up1_information)
    start = source.index("_turn_evidence = {")
    # The intent line itself contains "{}", so find the dict's own closing
    # brace (on a line of its own) rather than the first "}" after start.
    block = source[start:source.index("\n            }", start)]
    assert '"has_temporality": True' in block and '"conserves_state": True' in block
    assert "has_identity" not in block and "initiates_change" not in block
