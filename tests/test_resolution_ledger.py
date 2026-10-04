# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_resolution_ledger: representations as (subject, axis-path).

Resolution is axis-path length (0 event, 1 roots, 2 transitions, 3 triples,
4 channel-through-channel) on Aurora's existing REC_* depths.  The controls
matter more than the happy path:

  * a dependence that lives in one transition (T>N) is found at length 2 and
    nothing deeper is kept (a deeper path must beat its parent);
  * a dependence invisible at length 2 (an exclusive-or of two temporal
    states) is found only at length 3, as T>T>N;
  * the same stream with the dependence removed discovers nothing;
  * observation is idempotent, a saved ledger resumes identically, and WARP
    receives MISSING_REPRESENTATION demands whose REC_* coordinate is the
    path length.
"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_resolution_ledger import (  # noqa: E402
    AXES,
    REC_DIMS,
    AuroraResolutionLedger,
)
from aurora_warp_protocol import WarpTrigger  # noqa: E402

_VALID_PROFILE_KEYS = {
    "I_IS", "I_ISNT", "I_CAN", "I_CANNOT", "I_DO", "I_DONOT",
    "I_SAW", "I_SOUGHT", "I_DID", "I_DIDNT",
} | set(REC_DIMS)


def _stream(n, mode, seed=11):
    """One long episode, alternating actors; only T and N carry information.

    mode: "null"   N independent of T
          "pair"   N follows the previous T            (T>N, length 2)
          "xor"    N follows T[-1] xor T[-2]           (T>T>N, length 3)
          "persist" N repeats the previous N                  (N>N, length 2; no deeper path may ride on it)
    """
    rng = random.Random(seed)
    t_hist = [0, 0]
    n_prev = False
    for i in range(n):
        t_now = rng.random() < 0.5
        if mode == "pair":
            n_high = bool(t_hist[-1]) if rng.random() < 0.9 else rng.random() < 0.5
        elif mode == "persist":
            n_high = n_prev if rng.random() < 0.9 else rng.random() < 0.5
        elif mode == "xor":
            n_high = (bool(t_hist[-1]) != bool(t_hist[-2])) if rng.random() < 0.9 else rng.random() < 0.5
        else:
            n_high = rng.random() < 0.5
        t_hist.append(int(t_now))
        n_prev = n_high
        yield dict(
            event_index=i,
            event_id=f"e{i}",
            episode_id="ep0",
            actor="a" if i % 2 == 0 else "b",
            text_length=int(400 * rng.uniform(0.7, 1.3)) if n_high else int(20 * rng.uniform(0.7, 1.3)),
            elapsed_seconds=120.0 if t_now else 2.0,
            episode_gap_seconds=None,
        )


def _run(mode, n=9000, warp_field=None, state_dir=None, max_path=3):
    ledger = AuroraResolutionLedger(state_dir=state_dir or tempfile.mkdtemp(), persist=bool(state_dir), max_path=max_path)
    for ev in _stream(n, mode):
        ledger.observe_event(warp_field=warp_field, **ev)
    return ledger


def _found(ledger):
    return {(s, r["path"]) for s in ledger.status()["subjects"] for r in ledger.discovered(s)}


class _Warp:
    def __init__(self):
        self.demands = []

    def submit(self, demand):
        self.demands.append(demand)


def test_a_single_transition_is_found_at_length_two_and_nothing_deeper_is_kept():
    paths = {p for _, p in _found(_run("pair"))}
    assert "T>N" in paths, paths
    assert all(len(p.split(">")) == 2 for p in paths), paths


def test_a_dependence_invisible_at_length_two_is_found_only_at_length_three():
    ledger = _run("xor")
    paths = {p for _, p in _found(ledger)}
    assert "T>T>N" in paths, paths
    assert "T>N" not in paths, paths
    naturals = [ledger.natural_resolution(s) for s in ledger.status()["subjects"]]
    assert all(n["N"] == 3 for n in naturals), naturals


def test_a_deeper_path_cannot_ride_on_a_stronger_shallower_path_it_contains():
    paths = {p for _, p in _found(_run("persist"))}
    assert "N>N" in paths, paths
    assert all(len(p.split(">")) == 2 for p in paths), paths


def test_no_dependence_means_nothing_is_discovered():
    assert _found(_run("null")) == set()


def test_observe_is_idempotent_on_event_index():
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    events = list(_stream(600, "pair"))
    for ev in events:
        ledger.observe_event(**ev)
    before = ledger.status()["observations"]
    again = ledger.observe_event(**events[10])
    assert again["observed"] is False
    assert ledger.status()["observations"] == before


def test_resume_is_equivalent_to_uninterrupted_run():
    events = list(_stream(4000, "pair"))
    whole = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    for ev in events:
        whole.observe_event(**ev)
    directory = tempfile.mkdtemp()
    first = AuroraResolutionLedger(state_dir=directory, max_path=3)
    for ev in events[:2000]:
        first.observe_event(**ev)
    assert first.save()
    resumed = AuroraResolutionLedger(state_dir=directory, max_path=3)
    assert resumed.next_event_index() == 2000
    for ev in events[2000:]:
        resumed.observe_event(**ev)
    assert resumed.status()["discovered"] == whole.status()["discovered"]
    assert resumed.status()["observations"] == whole.status()["observations"]


def test_warp_demand_carries_the_path_length_on_the_rec_axis():
    warp = _Warp()
    _run("xor", warp_field=warp)
    assert warp.demands, "a discovered path should be confessed as a missing representation"
    demand = warp.demands[-1]
    assert demand.trigger == WarpTrigger.MISSING_REPRESENTATION
    assert demand.source == "resolution_ledger"
    assert demand.persistence_key.startswith("resolution:")
    assert set(demand.profile) <= _VALID_PROFILE_KEYS
    assert demand.expected["path"] == "T>T>N"
    assert demand.profile["REC_DEEP"] == 1.0
    assert 0.0 < demand.severity <= 0.88


def test_unstructured_stream_confesses_nothing():
    warp = _Warp()
    _run("null", warp_field=warp)
    assert warp.demands == []


def test_representations_are_coordinates_plus_paths_linked_by_composition():
    ledger = _run("xor")
    reps = ledger.representations()
    coords = [r for r in reps if r["kind"] == "coordinate"]
    paths = [r for r in reps if r["kind"] == "path"]
    assert {r["path"] for r in coords} == set(AXES)
    assert paths
    for rec in paths:
        length = len(rec["path"].split(">"))
        assert rec["length"] == length and rec["resolution"] == REC_DIMS[length]
        assert (rec["baseline"] is None) == (length == 2)
        if rec["baseline"] is not None:
            assert rec["baseline"].split(">")[-1] == rec["path"].split(">")[-1]
    assert AXES == ("X", "T", "N", "B", "A")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as exc:
                failures += 1
                print("FAIL", name, exc)
    sys.exit(1 if failures else 0)
