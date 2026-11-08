#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Commit and pull for ability-origin derivation (2026-11-08): an ability is
pulled only when its state is a committed FIXED POINT of the derivation, so
what she holds is always what a full re-derivation would give."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.constraint_genealogy as CG  # noqa: E402


def _logger(tmp_path, abilities):
    g = object.__new__(CG.ConstraintGenealogyLogger)
    g.output_dir = str(tmp_path)
    g.abilities = dict(abilities)
    return g


def _ab(aid, axis="X", tags=()):
    return CG.AbilityProfile(id=aid, axis=axis, requires=(axis,), cost={a: 0.1 for a in "XTNBA"},
                             risk={a: 0.0 for a in "XTNBA"}, effect_tags=tuple(tags))


def test_second_boot_pulls_and_matches_full_derivation(tmp_path, monkeypatch):
    seeds = {f"{ax}:OP{i}": _ab(f"{ax}:OP{i}", ax) for i in range(20) for ax in "XTB"}
    first = _logger(tmp_path, seeds)
    first.normalize_ability_origins()
    assert first._origin_pulled_last == 0
    derived = dict(first.abilities)
    for _ in range(3):                      # let the derivation converge
        nxt = _logger(tmp_path, derived)
        nxt.normalize_ability_origins()
        derived = dict(nxt.abilities)

    calls = []
    real = CG._augment_ability_profile_with_origin
    monkeypatch.setattr(CG, "_augment_ability_profile_with_origin", lambda ap: calls.append(ap.id) or real(ap))
    second = _logger(tmp_path, derived)
    second.normalize_ability_origins()
    assert second._origin_pulled_last == len(derived) and calls == []
    for aid, ap in second.abilities.items():
        assert real(ap) == ap


def test_non_fixed_points_are_never_pulled(tmp_path, monkeypatch):
    real = CG._augment_ability_profile_with_origin
    n = {"k": 0}

    def drifting(ap):                       # gains a new tag on every pass
        out = real(ap)
        if ap.id == "X:DRIFT":
            n["k"] += 1
            out = CG.AbilityProfile(**{**out.__dict__, "effect_tags": tuple(out.effect_tags) + (f"pass:{n['k']}",)})
        return out
    monkeypatch.setattr(CG, "_augment_ability_profile_with_origin", drifting)
    held = {"X:DRIFT": _ab("X:DRIFT"), "X:STILL": _ab("X:STILL")}
    for _ in range(4):
        again = _logger(tmp_path, held)
        again.normalize_ability_origins()
        held = dict(again.abilities)
    assert again._origin_pulled_last == 1                 # only the fixed point
    assert any(t.startswith("pass:") for t in again.abilities["X:DRIFT"].effect_tags)


def test_code_or_data_change_rederives_everything(tmp_path, monkeypatch):
    g = _logger(tmp_path, {"X:A": _ab("X:A")})
    g.normalize_ability_origins()
    monkeypatch.setattr(CG.ConstraintGenealogyLogger, "_origin_code_version", staticmethod(lambda: "new-code"))
    again = _logger(tmp_path, g.abilities)
    again.normalize_ability_origins()
    assert again._origin_pulled_last == 0
