#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Recognising what has yet to form (Sunni, 2026-11-08) -- computed, never named."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.aurora_unformed_patterns as U  # noqa: E402
from aurora_warp_protocol import WarpCapable  # noqa: E402


def ps(*, relation="like", obj="music", unknown="truth", query="factual_general", stance="curious",
       meaning="tension", axis="boundary", axes=None, op="evaluate_proposition"):
    return {"relational_form": {"subject": "you", "relation": relation, "obj": obj, "unknown_role": unknown},
            "parsed": {"query_type": query}, "input_stance": stance, "meaning_label": meaning,
            "dominant_axis": axis, "response_obligation": {"operation": op},
            "axis_activation": axes or {"X": 0.2, "T": 0.15, "N": 0.3, "B": 0.22, "A": 0.16}}


CARRIED = {"outcome": "own_voice"}
UNCARRIED = {"outcome": "silence"}


def understood_reference(u, n=U.REFERENCE_MIN + 3):
    for i in range(n):
        u.observe_turn(ps(), gate=CARRIED, response_id=f"c{i}")
        u.record_receiver_outcome(f"c{i}", "positive")


def open_turn():
    # A shape her reference never carried: open object, manner slot, different stance/meaning.
    return ps(relation="doing", obj="", unknown="manner", query="conversational", stance="warm",
              meaning="presence", axes={"X": 0.1, "T": 0.6, "N": 0.1, "B": 0.1, "A": 0.5})


def test_the_signature_is_her_outputs_not_the_words():
    feats, axes = U.signature(ps(), engaged=["path"])
    assert "slot:obj:filled" in feats and "unknown:truth" in feats and "engaged:path" in feats
    assert not any("music" in f or "like" in f for f in feats)


def test_residue_is_what_departs_from_what_she_represents(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    feats, axes = U.signature(open_turn())
    res = u.residue(feats, axes)
    assert "unknown:manner" in res and "slot:obj:open" in res and "stance:warm" in res
    assert "slot:subject:filled" not in res          # shared with what she represents
    assert any(r.startswith("axis_dev:T+") for r in res)


def test_a_one_off_is_noise_a_recurrence_is_a_gap(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    first = u.observe_turn(open_turn(), gate=UNCARRIED)
    assert first["occurrences"] == 1 and "handoff" not in first
    u.observe_turn(open_turn(), gate=UNCARRIED)
    third = u.observe_turn(open_turn(), gate=UNCARRIED)
    assert third["pattern"] == first["pattern"] and third["occurrences"] == 3
    assert "handoff" in third
    assert u.status()["recurring"] == 1


class FakeSystem(WarpCapable):
    def __init__(self, profiles):
        self.profiles = profiles
        self.extended = []
        self._warp_promoted = {}

    def _get_axis_profiles(self):
        return dict(self.profiles)

    def check_and_extend(self, data_axes, source="", tick=0, topology_gap_ref=None):
        self.extended.append((dict(data_axes), source, topology_gap_ref))
        return None


def test_hand_off_reaches_every_system_where_it_is_a_gap_and_leaves_covered_ones_alone(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    covers_it = FakeSystem({"c": {"X": 0.1, "T": 1.0, "N": 0.1, "B": 0.1, "A": 0.85}})
    misses_it = FakeSystem({"c": {"X": 1.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}})
    systems = {"covers": covers_it, "misses": misses_it, "not_warp": object()}
    for _ in range(3):
        rec = u.observe_turn(open_turn(), gate=UNCARRIED, systems=systems)
    results = rec["handoff"]
    assert results["covers"] == "covered" and covers_it.extended == []
    assert results["misses"] == "gap_counted" and misses_it.extended[0][1] == "unformed_patterns"
    assert misses_it.extended[0][2] == rec["pattern"]        # provenance threaded through
    assert results["warp_field"] == "confessed" and "not_warp" not in results


def test_a_real_warp_system_grows_its_own_trial(tmp_path):
    from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
    ce = AuroraCommunicationEmergence(state_dir=str(tmp_path / "ce"), persist=False)
    before = len(ce._warp_trials)
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    out = None
    for _ in range(8):
        out = u.observe_turn(open_turn(), gate=UNCARRIED, systems={"communication_emergence": ce})
    assert "communication_emergence" in out["handoff"]
    assert len(ce._warp_trials) > before or out["handoff"]["communication_emergence"] == "covered"


def test_understood_turns_carrying_its_core_form_it(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    for _ in range(3):
        rec = u.observe_turn(open_turn(), gate=UNCARRIED)
    pid = rec["pattern"]
    for i in range(U.COVERED_TO_FORM):
        u.observe_turn(open_turn(), gate=CARRIED, response_id=f"f{i}")
        effect = u.record_receiver_outcome(f"f{i}", "positive")["effect"]
    assert effect == f"formed:{pid}" and u.patterns[pid]["status"] == "formed"
    assert "handoff" not in u.observe_turn(open_turn(), gate=UNCARRIED, systems={})


def test_misunderstood_carried_turns_do_not_join_the_reference(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    u.observe_turn(ps(), gate=CARRIED, response_id="x")
    u.record_receiver_outcome("x", "negative")
    assert u.ref_n == 0


def test_state_persists(tmp_path):
    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    for _ in range(3):
        u.observe_turn(open_turn(), gate=UNCARRIED)
    u.flush_write_batch()
    again = U.UnformedPatterns(state_dir=str(tmp_path))
    assert again.ref_n == u.ref_n and again.patterns == u.patterns


def test_one_open_trial_per_pattern_per_system(tmp_path):
    class Growing(FakeSystem):
        def __init__(self):
            super().__init__({"c": {"X": 1.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}})
            self._warp_trials = {}

        def check_and_extend(self, data_axes, source="", tick=0, topology_gap_ref=None):
            from types import SimpleNamespace
            comp = SimpleNamespace(component_id=f"warp_{len(self._warp_trials)}")
            self._warp_trials[comp.component_id] = comp
            self.extended.append(comp.component_id)
            return comp

    u = U.UnformedPatterns(state_dir=str(tmp_path))
    understood_reference(u)
    grow = Growing()
    for _ in range(8):
        rec = u.observe_turn(open_turn(), gate=UNCARRIED, systems={"grow": grow})
    assert grow.extended == ["warp_0"] and rec["handoff"]["grow"] == "trial_open"
    grow._warp_trials.clear()                 # its trial resolved (promoted or dissolved)
    rec = u.observe_turn(open_turn(), gate=UNCARRIED, systems={"grow": grow})
    assert rec["handoff"]["grow"].startswith("extended:") and len(grow.extended) == 2
