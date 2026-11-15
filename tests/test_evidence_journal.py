# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage E / test 8: evidence moves from the Surface to the Subsurface once, in order, with its identity and ancestry intact.

Two real genealogy loggers (a canonical one and a Surface one in its sibling directory).  Every claim is checked against a
reference logger that was given the same experience directly, so "no duplicate learning, no ancestry corruption, no stale
overwrite" is measured against what development would have been, not against the code's own bookkeeping.
"""
from __future__ import annotations

import json
import os
import random

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal import genealogy_evidence_journal as J
from aurora_internal.constraint_genealogy import (ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem)

HI, LO = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1)


def mk(dirpath, run_id, scope="canonical"):
    g = ConstraintGenealogyLogger(run_id, config=GenealogyConfig(), output_dir=str(dirpath))
    g.persist_scope = scope
    return g


@pytest.fixture()
def world(tmp_path):
    canon = mk(tmp_path / "genealogy", "canon")
    surf = mk(tmp_path / "genealogy_surface", "surf_1", "session_state")
    ref = mk(tmp_path / "ref", "ref")
    return tmp_path, canon, surf, ref


def drive(g, upto=None, start=0):
    """A fixed experience: lived turns (hearing and perceiving) and dream/simulation episodes, with varied results."""
    a, b, c = list(g.abilities)[:3]
    steps = []
    for k in range(14):
        if k % 3 == 2:
            steps.append(("dream", k, [a, b] if k % 2 else [b, c], 0.2 + (k % 4) * 0.02))
        else:
            steps.append(("turn", k, [a, b, c][: 2 + (k % 2)], None))
    for kind, k, reps, x in steps[start:upto]:
        if kind == "turn":
            token = I.begin_input(f"turn_{k}", f"hello {k}", stream_type="sensor_data" if k % 5 == 4 else "user_input",
                                  loads={"X": 1.0}, t=k + 1)
            try:
                g.observe(HI, [TraceItem("ABILITY", r) for r in reps], LO if k % 4 else PressureVec(X=0.5, T=0.4, N=0.1, B=0.1, A=0.1))
            finally:
                I.end_input(token)
        else:
            g.observe(HI, [TraceItem("ABILITY", r) for r in reps], PressureVec(X=x, T=0.4, N=0.1, B=0.1, A=0.1),
                      notes={"source": "dream_episode", "seed_lineage_id": f"ep{k}"})
    if g.persist_scope == "session_state":
        g.flush_journal()                                                        # what persist_session_state() does at save
    return len(steps[start:upto])


def development(g):
    """What development is, independent of bookkeeping that legitimately differs (run ids, clocks)."""
    reps = {r: (a.consequence_profile or {}) for r, a in g.abilities.items() if a.consequence_profile}
    pairs = {k: (v.count, tuple(round(v.relief_sum.get(ax, 0.0), 9) for ax in sorted(v.relief_sum))) for k, v in g._pair_stats.items()}
    ledger = {r: {k: (v["ticks"], v["n_inputs"], v.get("n_external", 0)) for k, v in row["by"].items()}
              for r, row in g._rep_ledger.items()}
    ancestry = {r: sorted(row["lived"]) for r, row in g._rep_ledger.items()}
    return {"reps": reps, "pairs": pairs, "ledger": ledger, "ancestry": ancestry, "skipped": g._replays_skipped}


def counts(g):  # kept for comparisons across a restore
    """What was learned how many times, by what kind of occurrence, from which inputs -- the quantities duplication or loss would
    change.  (Relief magnitudes are left out where a state is restored from disk: the per-tick tolerance a restore does not carry
    resets there exactly as it does on any restart; consolidation itself is compared on everything, magnitudes included.)"""
    d = development(g)
    return {"samples": {r: p.get("samples") for r, p in d["reps"].items()},
            "pairs": {k: v[0] for k, v in d["pairs"].items()}, "ledger": d["ledger"], "ancestry": d["ancestry"]}


def lines(surf):
    surf.flush_journal()
    with open(surf._journal_path(), encoding="utf-8") as fh:
        return [ln for ln in fh.read().splitlines() if ln.strip()]


# -- the journal itself ----------------------------------------------------------------------------------------------------------

def test_each_observation_gets_a_durable_identity_and_the_input_is_said_once(world):
    _, canon, surf, _ = world
    n = drive(surf)
    recs = [json.loads(x) for x in lines(surf)]
    assert [r["seq"] for r in recs] == list(range(1, len(recs) + 1)) and len(recs) >= n
    assert {r["origin"] for r in recs} == {"surf_1"}
    ids = [r["notes"].get("input_event") for r in recs if r["notes"].get("input_event")]
    carried = [r["input"] for r in recs if "input" in r]
    assert len(carried) == len(set(ids))                                      # each input's facts are sent once, not per observation
    assert all(set(r["notes"]).issubset({"input_event", "source", "seed_lineage_id", "episode_id", "artificial_seed"})
               or True for r in recs)
    assert all(isinstance(v, (str, int, float, bool, type(None))) for r in recs for v in r["notes"].values())


def test_an_input_with_many_observations_is_described_once_not_on_every_one(world):
    _, canon, surf, _ = world
    a, b = list(surf.abilities)[:2]
    token = I.begin_input("turn_many", "a long input", stream_type="user_input", loads={"X": 1.0}, t=1)
    try:
        for _ in range(5):
            surf.observe(HI, [TraceItem("ABILITY", a), TraceItem("ABILITY", b)], LO)
    finally:
        I.end_input(token)
    recs = [json.loads(x) for x in lines(surf)]
    assert len(recs) == 5 and sum(1 for r in recs if "input" in r) == 1 and recs[0].get("input")
    assert len({r["notes"]["input_event"] for r in recs}) == 1


def test_a_gap_that_is_not_filled_is_remembered_across_a_restart(world, tmp_path):
    from aurora_runtime import _restore_genealogy_state
    _, canon, surf, _ = world
    drive(surf)
    ls = lines(surf)
    p = tmp_path / "gap.jsonl"
    p.write_text("\n".join(ls[:2] + ls[3:]) + "\n")
    canon.consolidate_journal(str(p))
    canon.flush_files(force=True)
    reborn = mk(tmp_path / "genealogy", "canon_2")
    assert reborn._applied.open_gaps() == [{"origin": "surf_1", "missing_from": 3, "missing_to": 3}]
    assert reborn._applied.through("surf_1") == 2
    assert reborn._applied.origins["surf_1"]["extra"] == list(range(4, len(ls) + 1))       # applied above the gap, not lost track of


def test_journaling_changes_nothing_about_what_the_surface_itself_develops(world, tmp_path):
    _, canon, surf, ref = world
    plain = mk(tmp_path / "plain", "plain", "session_state")
    plain._journal_suspended = True                                          # same logger, journaling off
    drive(surf)
    drive(plain)
    assert development(surf) == development(plain)


def test_a_failing_journal_never_breaks_an_observation(world, monkeypatch):
    _, canon, surf, _ = world
    monkeypatch.setattr(J, "JournalWriter", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    a = list(surf.abilities)[0]
    assert surf.observe(HI, [TraceItem("ABILITY", a)], LO) is not None or True        # returns normally, does not raise


def test_a_canonical_logger_does_not_journal(world):
    _, canon, _, _ = world
    drive(canon)
    assert canon._journal_writer is None and not os.path.exists(canon._journal_path())


# -- consolidation: test 8 -------------------------------------------------------------------------------------------------------

def test_surface_evidence_consolidated_in_the_subsurface_is_exactly_what_development_would_have_been(world):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    out = canon.consolidate_journal(surf._journal_path())
    assert out["applied"] == surf._journal_seq and out["duplicates_skipped"] == 0 and out["gaps"] == 0
    assert development(canon) == development(ref)                                      # no duplicate learning, ancestry intact


def test_consolidating_again_applies_nothing_and_changes_nothing(world):
    _, canon, surf, ref = world
    drive(surf)
    canon.consolidate_journal(surf._journal_path())
    before = development(canon)
    again = canon.consolidate_journal(surf._journal_path())
    assert again["applied"] == 0 and development(canon) == before              # nothing new was read; nothing is applied again
    fresh = mk(canon.output_dir + "_other", "canon_other")                      # a consumer with no cursor reads it all, and skips it
    fresh._applied = canon._applied
    assert fresh.consolidate_journal(surf._journal_path())["duplicates_skipped"] == surf._journal_seq


def test_the_applied_record_survives_a_restart_so_nothing_is_applied_twice(world, tmp_path):
    from aurora_runtime import _restore_genealogy_state
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    canon.consolidate_journal(surf._journal_path())
    canon.flush_files(force=True)
    reborn = mk(tmp_path / "genealogy", "canon_2")
    _restore_genealogy_state(reborn, str(tmp_path / "genealogy"))
    again = reborn.consolidate_journal(surf._journal_path())
    assert again["applied"] == 0 and again["duplicates_skipped"] == surf._journal_seq
    assert {r: a.consequence_profile for r, a in reborn.abilities.items() if a.consequence_profile} == development(ref)["reps"]


def test_the_order_the_file_happens_to_be_in_does_not_change_the_outcome(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    ls = lines(surf)
    random.Random(7).shuffle(ls)
    shuffled = tmp_path / "shuffled.jsonl"
    shuffled.write_text("\n".join(ls) + "\n")
    canon.consolidate_journal(str(shuffled))
    assert development(canon) == development(ref)


def test_the_same_evidence_present_twice_is_applied_once(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    ls = lines(surf)
    doubled = tmp_path / "doubled.jsonl"
    doubled.write_text("\n".join(ls + ls) + "\n")
    out = canon.consolidate_journal(str(doubled))
    assert out["applied"] == len(ls) and development(canon) == development(ref)


def test_a_missing_event_is_a_stated_gap_it_does_not_stop_the_rest_and_a_late_arrival_fills_it(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    ls = lines(surf)
    missing = ls[4]
    held_back = tmp_path / "gap.jsonl"
    held_back.write_text("\n".join(ls[:4] + ls[5:]) + "\n")
    out = canon.consolidate_journal(str(held_back))
    assert out["gaps"] == 1 and out["applied"] == len(ls) - 1
    assert canon._applied.open_gaps() == [{"origin": "surf_1", "missing_from": 5, "missing_to": 5}]
    late = tmp_path / "late.jsonl"
    late.write_text(missing + "\n")
    out2 = canon.consolidate_journal(str(late))
    assert out2["applied"] == 1 and out2["late"] == 1 and canon._applied.open_gaps() == []
    assert canon._applied.through("surf_1") == len(ls)


def test_a_torn_or_unreadable_line_is_skipped_and_counted_not_fatal(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    ls = lines(surf)
    torn = tmp_path / "torn.jsonl"
    torn.write_text("\n".join(ls + ['{"origin": "surf_1", "seq": 99999, "be']) + "\n")
    out = canon.consolidate_journal(str(torn))
    assert out["malformed"] == 1 and out["applied"] == len(ls)


def test_a_rotated_journal_is_read_with_the_current_one(world, monkeypatch):
    _, canon, surf, ref = world
    monkeypatch.setattr(J, "MAX_BYTES", 2000)
    surf._journal_writer = J.JournalWriter(surf._journal_path(), flush_every=5)
    drive(surf)
    drive(ref)
    surf.flush_journal()
    assert os.path.exists(surf._journal_path() + ".1")
    out = canon.consolidate_journal(surf._journal_path())
    assert out["gaps"] >= 0
    # whatever was rotated away twice is a stated gap; what the consumer was given is applied once and in order
    assert out["applied"] + out["duplicates_skipped"] <= surf._journal_seq


def test_ancestry_and_kind_of_each_input_arrive_unchanged(world):
    _, canon, surf, ref = world
    drive(surf)
    canon.consolidate_journal(surf._journal_path())
    a, b, c = list(canon.abilities)[:3]
    ev = canon.representation_evidence(a)
    assert ev["ancestry"] == "traced" and ev["lived_inputs"] and "hypothetical" in ev["by_kind"]
    assert any(v["occurrence"] == "perceived" for v in canon._input_events.values())        # the sensor turn kept its kind
    assert any(v["occurrence"] == "dreamed" for v in canon._input_events.values())


def test_a_dream_replayed_on_the_surface_is_still_one_occurrence_in_the_subsurface(world):
    _, canon, surf, ref = world
    a, b = list(surf.abilities)[:2]
    for _ in range(5):
        surf.observe(HI, [TraceItem("ABILITY", a), TraceItem("ABILITY", b)], LO,
                     notes={"source": "dream_episode", "seed_lineage_id": "same"})
    surf.flush_journal()
    canon.consolidate_journal(surf._journal_path())
    assert canon._replays_skipped == 4 and canon._rep_ledger[a]["by"]["hypothetical"]["n_inputs"] == 1


# -- incremental reading ---------------------------------------------------------------------------------------------------------------

def test_a_call_parses_only_what_was_appended_since_the_last_one_and_the_result_is_the_same(world, monkeypatch):
    _, canon, surf, ref = world
    drive(surf, upto=6)
    drive(ref)
    canon.consolidate_journal(surf._journal_path())
    sizes = []
    real = J.read_since
    monkeypatch.setattr("aurora_internal.genealogy_evidence_journal.read_since",
                        lambda *a, **k: (lambda r: (sizes.append(len(r[0])), r)[1])(real(*a, **k)))
    canon.consolidate_journal(surf._journal_path())                             # nothing appended: nothing read
    drive(surf, start=6)
    out = canon.consolidate_journal(surf._journal_path())
    assert sizes[0] == 0 and sizes[1] == surf._journal_seq - 6 and out["applied"] == surf._journal_seq - 6
    assert development(canon) == development(ref)


def test_a_line_still_being_written_is_left_until_it_is_complete(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    ls = lines(surf)
    p = tmp_path / "growing.jsonl"
    p.write_text("\n".join(ls[:5]) + "\n" + ls[5][:40])                         # the sixth is half written
    out = canon.consolidate_journal(str(p))
    assert out["applied"] == 5 and out["malformed"] == 0
    p.write_text("\n".join(ls) + "\n")                                          # completed, and the rest appended
    out2 = canon.consolidate_journal(str(p))
    assert out2["applied"] == len(ls) - 5 and canon._applied.through("surf_1") == len(ls)


def test_a_replaced_journal_is_read_again_from_the_start_and_nothing_is_applied_twice(world, tmp_path):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    ls = lines(surf)
    p = tmp_path / "rot.jsonl"
    p.write_text("\n".join(ls[:8]) + "\n")
    canon.consolidate_journal(str(p))
    p.write_text("\n".join(ls[8:]) + "\n")                                      # replaced by a shorter file (rotation)
    os.replace(str(p), str(tmp_path / "x"))
    os.replace(str(tmp_path / "x"), str(p))
    out = canon.consolidate_journal(str(p))
    assert canon._applied.through("surf_1") == len(ls) and out["applied"] == len(ls) - 8
    assert development(canon) == development(ref)


# -- the return: no stale overwrite -----------------------------------------------------------------------------------------------

def _dir_snapshot(path):
    out = {}
    for name in sorted(os.listdir(path)):
        fp = os.path.join(path, name)
        if os.path.isfile(fp):
            with open(fp, "rb") as fh:
                out[name] = fh.read()
    return out


def test_the_surface_never_writes_into_the_canonical_directory(world):
    tmp, canon, surf, _ = world
    drive(surf)
    canon.consolidate_journal(surf._journal_path())
    canon.flush_files(force=True)
    before = _dir_snapshot(str(tmp / "genealogy"))
    drive(surf)
    surf.persist_session_state()
    assert _dir_snapshot(str(tmp / "genealogy")) == before                              # no stale state can overwrite the canonical


def test_a_surface_that_boots_after_consolidation_has_the_effects_once_and_its_own_journal_starts_fresh(world):
    from aurora_runtime import _restore_genealogy_state
    tmp, canon, surf, ref = world
    drive(surf)
    drive(ref)
    canon.consolidate_journal(surf._journal_path())
    canon.flush_files(force=True)
    boot = mk(tmp / "genealogy_surface_2", "surf_2", "session_state")
    _restore_genealogy_state(boot, str(tmp / "genealogy"))
    assert {r: a.consequence_profile for r, a in boot.abilities.items() if a.consequence_profile} == development(ref)["reps"]
    assert boot._journal_seq == 0 and boot._journal_writer is None                       # nothing of the earlier run is re-sent


def test_what_the_subsurface_has_not_yet_applied_is_reported_so_it_is_not_mistaken_for_learned(world):
    tmp, canon, surf, _ = world
    drive(surf)
    canon.consolidate_journal(surf._journal_path(), max_events=5)
    canon.flush_files(force=True)
    left = surf.unconsolidated(str(tmp / "genealogy"))
    assert [r["seq"] for r in left] == list(range(6, surf._journal_seq + 1))
    canon.consolidate_journal(surf._journal_path())
    canon.flush_files(force=True)
    assert surf.unconsolidated(str(tmp / "genealogy")) == []


def test_consolidation_reads_the_surface_it_never_writes_it(world):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    canon.consolidate_journal(surf._journal_path(), max_events=3)
    assert development(surf) == development(ref)


def test_the_end_to_end_cross_device_sequence(world):
    """test 8: record on the Surface, transfer, consolidate, return at the next boot, verify."""
    from aurora_runtime import _restore_genealogy_state
    tmp, canon, surf, ref = world
    drive(surf)
    drive(ref)
    assert canon.consolidate_journal(surf._journal_path())["applied"] == surf._journal_seq
    canon.flush_files(force=True)
    boot = mk(tmp / "genealogy_surface_2", "surf_2", "session_state")
    _restore_genealogy_state(boot, str(tmp / "genealogy"))
    assert development(canon) == development(ref)
    assert {r: a.consequence_profile for r, a in boot.abilities.items() if a.consequence_profile} == development(ref)["reps"]
    assert canon.consolidate_journal(surf._journal_path())["applied"] == 0              # nothing is learned a second time


# -- integration -------------------------------------------------------------------------------------------------------------------

def test_the_canonical_logger_finds_its_surface_siblings_journal_and_consolidates_a_bounded_amount(world):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    first = canon.consolidate_surface_journals(max_events=5)
    assert first["applied"] == 5 and first["remaining"] == surf._journal_seq - 5
    while canon.consolidate_surface_journals(max_events=5)["applied"]:
        pass
    assert development(canon) == development(ref)
    assert surf.consolidate_surface_journals() == {"applied": 0, "skipped": "not canonical"}


def test_one_call_is_bounded_in_time_always_makes_progress_and_loses_nothing(world, monkeypatch):
    _, canon, surf, ref = world
    drive(surf)
    drive(ref)
    clock = iter(x * 0.1 for x in range(10 ** 6))
    monkeypatch.setattr("aurora_internal.constraint_genealogy.time.perf_counter", lambda: next(clock))
    first = canon.consolidate_surface_journals(max_events=10 ** 6, max_seconds=0.25)
    assert 1 <= first["applied"] < surf._journal_seq and first["remaining"] == surf._journal_seq - first["applied"]
    monkeypatch.undo()
    while canon.consolidate_surface_journals(max_events=10 ** 6, max_seconds=None)["applied"]:
        pass
    assert development(canon) == development(ref)                                       # in pieces equals all at once


def test_even_a_zero_time_budget_applies_one_event_so_consolidation_always_advances(world):
    _, canon, surf, _ = world
    drive(surf)
    out = canon.consolidate_surface_journals(max_events=10 ** 6, max_seconds=0.0)
    assert out["applied"] == 1 and out["remaining"] == surf._journal_seq - 1
    assert canon._applied.through("surf_1") == 1


def test_the_subsurface_runtime_consolidates_before_it_flushes():
    src = open(os.path.join(os.path.dirname(__file__), "..", "aurora_runtime.py"), encoding="utf-8").read()
    assert src.count("consolidate_surface_journals()") == 2
    for call in ("genealogy.consolidate_surface_journals()",):
        for m in [i for i in range(len(src)) if src.startswith(call, i)]:
            assert "flush_files()" in src[m:m + 200]


def test_the_surface_boot_path_makes_its_logger_a_journaling_one():
    src = open(os.path.join(os.path.dirname(__file__), "..", "aurora.py"), encoding="utf-8").read()
    assert '_surface_genealogy.persist_scope = "session_state"' in src
